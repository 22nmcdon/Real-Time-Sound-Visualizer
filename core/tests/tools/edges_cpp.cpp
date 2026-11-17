// The instrument at the edges a host can take it to (the outside review, 17
// Nov), one command a run:
//
//   edges_cpp zero FRAMES OFF
//     A note struck in a block of 512, then a block of FRAMES carrying the
//     note's note-off (OFF 1) or nothing (OFF 0) and three MIDI clock ticks,
//     then four blocks of 512. Printed: the voices still held, and the
//     clock's ticks. JUCE's VST3 wrapper calls processBlock with no samples
//     to hand over events, and a block of none played nothing, events
//     included, so the note stuck. OFF 0 is the null: the note held.
//
//   edges_cpp hands N
//     N presses of the header's Editing, Lower and Upper in turn, as a
//     player flicking between the hands makes them, with a block between
//     each. Printed: the hands the state keeps, the state code's length, and
//     the allocations and bytes of what the plugin's publish does on the
//     audio thread once a change is in (stateSetup), averaged over twenty.
//     The hands were never trimmed: 2,000 presses were 48 KB of code to
//     encode on every block that changed anything.
//
//   edges_cpp replay
//     Each hand its own level between flicks of Editing and five presses of
//     the photocell, then the state code loaded into an instrument made new.
//     Printed: the hands kept, then each hand's level, the hand edited and
//     whether the photocell is on, as played and as reopened - which must be
//     the same, or the compaction kept the wrong presses.
//
//   edges_cpp controls
//     The panel's controls asked for by an id it has not got, as a host or a
//     page out of step could: printed, what each answered, where std::map::at
//     threw on the audio thread.
#include <atomic>
#include <cstdio>
#include <cstdlib>
#include <new>
#include <string>
#include <vector>

#include "scope/instrument.h"
#include "scope/presets.h"

#pragma GCC diagnostic ignored "-Wmismatched-new-delete"

namespace {
std::atomic<long> allocations { 0 }, bytes { 0 };
thread_local bool counting = false;
}

void* operator new(std::size_t size) {
  if (counting) { allocations++; bytes += static_cast<long>(size); }
  if (void* p = std::malloc(size ? size : 1)) return p;
  throw std::bad_alloc();
}
void* operator new[](std::size_t size) { return operator new(size); }
void operator delete(void* p) noexcept { std::free(p); }
void operator delete(void* p, std::size_t) noexcept { std::free(p); }
void operator delete[](void* p) noexcept { std::free(p); }
void operator delete[](void* p, std::size_t) noexcept { std::free(p); }

using scope::Instrument;

int main(int argc, char** argv) {
  if (argc < 2) { std::fprintf(stderr, "usage: edges_cpp zero FRAMES OFF | hands N | controls\n"); return 2; }
  const std::string what = argv[1];
  std::vector<float> l(512), r(512);
  const auto held = [](const Instrument& ins) {
    int n = 0;
    for (const auto* pool : { &ins.generator().voices(), &ins.generator().voicesB() })
      for (const auto& v : *pool) n += v.held ? 1 : 0;
    return n;
  };
  if (what == "zero") {
    const int frames = argc > 2 ? std::atoi(argv[2]) : 0;
    const bool off = argc > 3 && std::atoi(argv[3]) != 0;
    Instrument ins;
    ins.prepare(48000, 512, scope::baseSetup());
    static const std::uint8_t on[3] = { 0x90, 60, 100 }, noteOff[3] = { 0x80, 60, 0 }, tick[1] = { 0xF8 };
    const Instrument::Event struck { 0, on, 3 };
    ins.block(l.data(), r.data(), 512, &struck, 1, nullptr, nullptr, 0);
    const int before = held(ins);
    std::vector<Instrument::Event> events;
    if (off) events.push_back({ 0, noteOff, 3 });
    for (int k = 0; k < 3; ++k) events.push_back({ 0, tick, 1 });
    const std::size_t ticks = ins.clock().ticks.size();
    ins.block(l.data(), r.data(), frames, events.data(), events.size(), nullptr, nullptr, 0);
    for (int k = 0; k < 4; ++k) ins.block(l.data(), r.data(), 512, nullptr, 0, nullptr, nullptr, 0);
    std::printf("zero before %d held %d ticks %zu\n", before, held(ins), ins.clock().ticks.size() - ticks);
    return 0;
  }
  if (what == "hands") {
    const int presses = argc > 2 ? std::atoi(argv[2]) : 0;
    Instrument ins;
    const scope::Preset* preset = scope::findPreset("Bass under the pad");  // two hands, so Editing means something
    if (!preset) return 2;
    ins.prepare(48000, 512, preset->setup);
    for (int k = 0; k < presses; ++k) {
      ins.apply(Instrument::click(k % 2 == 0 ? "editHandB" : "editHandA"));
      ins.block(l.data(), r.data(), 512, nullptr, 0, nullptr, nullptr, 0);
    }
    const std::string code = ins.stateCode();
    // A hand moved, so there is a change to publish, and the publish's audio-thread half counted.
    const long a0 = allocations.load(), b0 = bytes.load();
    for (int k = 0; k < 20; ++k) {
      const Instrument::HostSlider moved { "vcfCut", 1000.0 + k };
      ins.block(l.data(), r.data(), 512, nullptr, 0, nullptr, &moved, 1);
      counting = true;
      const scope::Json state = ins.stateSetup();
      counting = false;
      ins.published();
    }
    std::printf("hands %zu code %zu allocations %ld bytes %ld\n", ins.handCount(), code.size(),
                (allocations.load() - a0) / 20, (bytes.load() - b0) / 20);
    return 0;
  }
  if (what == "replay") {
    /* What compaction keeps has to mean what the presses meant: the
       generator unlinked, each hand given its own level between flicks of
       Editing and the photocell, the state code loaded into an instrument
       made new, and each hand's level and the hand edited read off both. */
    const auto playOut = [&](Instrument& ins) {
      for (int k = 0; k < 2; ++k) ins.block(l.data(), r.data(), 512, nullptr, 0, nullptr, nullptr, 0);
    };
    const auto read = [&](Instrument& ins) {
      std::printf(" %.17g %.17g %d %d", ins.tone().amp, ins.toneB().amp, ins.keyboard().edit(), ins.matrix().source("photo.1") ? 1 : 0);
    };
    const scope::Preset* preset = scope::findPreset("Bass under the pad");
    if (!preset) return 2;
    Instrument ins;
    ins.prepare(48000, 512, preset->setup);
    const auto press = [&](const char* id) { ins.apply(Instrument::click(id)); playOut(ins); };
    const auto level = [&](const char16_t* v) { if (const auto c = Instrument::slider("amp", v)) ins.apply(*c); playOut(ins); };
    press("editHandB"); level(u"20");
    press("editHandA"); level(u"70");
    press("editHandB"); press("editHandA"); press("editHandB"); press("editHandB");
    // Four presses of the photocell, which leave it off, and a fifth after a hand between: on. A
    // count that is odd throughout reads the same whether a pair is dropped whole or by one.
    press("photoButton"); press("photoButton"); press("photoButton"); press("photoButton");
    level(u"35");
    press("photoButton");
    press("editHandA"); press("editHandB"); press("editHandA");
    std::printf("replay %zu", ins.handCount());
    read(ins);
    Instrument again;
    again.prepare(48000, 512, scope::decodeSetup(ins.stateCode()).setup);
    playOut(again);
    read(again);
    std::printf("\n");
    return 0;
  }
  if (what == "controls") {
    Instrument ins;
    ins.prepare(48000, 512, scope::baseSetup());
    // An id the panel has not got, through the ways in the audio thread uses.
    const double range = ins.slider("noSuchSlider");
    ins.moveSlider("noSuchSlider", 3);
    if (const auto c = Instrument::slider("noSuchSlider", u"3")) ins.apply(*c);  // refused, as it should be
    ins.apply(Instrument::control("noSuchMenu", scope::Json::string(std::string_view("x"))));
    const Instrument::HostSlider moved { "noSuchSlider", 3 };
    ins.block(l.data(), r.data(), 512, nullptr, 0, nullptr, &moved, 1);
    ins.block(l.data(), r.data(), 512, nullptr, 0, nullptr, nullptr, 0);
    std::printf("controls survived %s\n", std::isnan(range) ? "nan" : std::to_string(range).c_str());
    return 0;
  }
  return 2;
}
