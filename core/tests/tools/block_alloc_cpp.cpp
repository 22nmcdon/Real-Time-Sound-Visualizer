// Whether a steady block allocates (G8): the instrument as the plugin plays
// it, prepared, put on a path, played for twenty seconds of audio - long
// enough for the picture's meter to fill its fifteen seconds of history and
// start answering, which is when its medians began allocating - and then
// four hundred blocks more with every operator new on this thread counted.
//
//   block_alloc_cpp PATH [BLOCK [PREPARED]]
//
// BLOCK is the host's block, 512 when left out, and PREPARED the block the
// instrument was prepared for, BLOCK when left out: a host may hand over more
// than it promised, which the instrument renders in pieces.
//
// One line: the path, the allocations and bytes in the counted blocks, and a
// number that says the path was doing what it is named for - so a path that
// silently did nothing, and so could not allocate, is told apart from one
// that did and did not. What each number is is said where it is worked out.
// `made PATH` prints what the making allocated instead: the proof the
// counter counts. The path `host`, a host parameter moved every block, is
// the other null: its hand and the state's bookkeeping still allocate, by
// design, so it must read non-zero through the same counter.
//
// `reuse VELOCITY` is what makes the rest safe to believe: a voice that takes
// the quarter-turn ring and the shaper a retired voice left behind sounds
// exactly as one that made them new. Two generators play one history, a
// chord let go until every voice has retired, the first with the quarter
// turn and the drive on - so its voices make rings and shapers and leave
// them - and the second with both off, so none does; then both, with both
// on, strike one note, the first at velocity one and the second at VELOCITY. Printed: the most the two heard pairs differ
// over the note's first 4096 samples, left and right. At VELOCITY one they
// must be the same to the bit; another velocity is the null.
#include <atomic>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <new>
#include <string>
#include <vector>

#include "scope/instrument.h"
#include "scope/presets.h"

// The replacement operator new takes its memory from malloc, so free is the
// matching release; GCC, seeing the standard library's news inlined past it,
// calls the pairing mismatched when it is not.
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
void* operator new(std::size_t size, const std::nothrow_t&) noexcept {
  if (counting) { allocations++; bytes += static_cast<long>(size); }
  return std::malloc(size ? size : 1);
}
void operator delete(void* p) noexcept { std::free(p); }
void operator delete(void* p, std::size_t) noexcept { std::free(p); }
void operator delete[](void* p) noexcept { std::free(p); }
void operator delete[](void* p, std::size_t) noexcept { std::free(p); }

using scope::Instrument;

int main(int argc, char** argv) {
  if (argc < 2) { std::fprintf(stderr, "usage: block_alloc_cpp PATH [BLOCK [PREPARED]] | made PATH | reuse VELOCITY\n"); return 2; }
  if (std::string(argv[1]) == "reuse") {
    const double velocity = argc > 2 ? std::atof(argv[2]) : 1;
    const auto play = [&](bool turnedBefore, double struck) {
      std::vector<scope::Lfo> lfos(2);
      scope::Generator g(48000, scope::slot::Used, lfos);
      g.setGated(true);
      std::vector<float> pl(512), pr(512), hl(512), hr(512), out;
      const auto run = [&](int blocks, bool keep) {
        for (int b = 0; b < blocks; ++b) {
          g.block(pl.data(), pr.data(), 512, hl.data(), hr.data());
          if (keep) for (int i = 0; i < 512; ++i) { out.push_back(hl[static_cast<std::size_t>(i)]); out.push_back(hr[static_cast<std::size_t>(i)]); }
        }
      };
      const auto want = [](int note, const char* role, double vel) {
        scope::NoteWant w;
        w.note = note; w.freq = 440 * std::pow(2.0, (note - 69) / 12.0); w.velocity = vel; w.role = role;
        return w;
      };
      g.set("polyRound", turnedBefore ? 1 : 0);
      g.set("drive", turnedBefore ? 0.5 : 0);
      std::vector<scope::NoteWant> chord { want(60, "x", 1), want(64, "u", 1), want(67, "y", 1) }, none;
      g.setVoices(&chord, 0);
      run(30, false);
      g.setVoices(&none, 0);
      for (int k = 0; k < 2000 && !g.voices().empty(); ++k) run(1, false);
      const bool retired = g.voices().empty();
      g.set("polyRound", 1);
      g.set("drive", 0.5);
      /* A block of silence first, in which the second history's shaper
         crosses in (11 Nov): struck at once it would be fading in where the
         first's had always been on, and the two would differ for that. */
      run(2, false);
      std::vector<scope::NoteWant> note { want(62, "xy", struck) };
      g.setVoices(&note, 0);
      run(8, true);
      return std::make_pair(retired, out);
    };
    const auto [retiredA, a] = play(true, 1);
    const auto [retiredB, b] = play(false, velocity);
    double left = 0, right = 0;
    for (std::size_t i = 0; i + 1 < a.size() && i + 1 < b.size(); i += 2) {
      left = std::fmax(left, std::fabs(static_cast<double>(a[i]) - b[i]));
      right = std::fmax(right, std::fabs(static_cast<double>(a[i + 1]) - b[i + 1]));
    }
    std::printf("reuse %.9g %.9g %d\n", left, right, retiredA && retiredB ? 1 : 0);
    return 0;
  }
  const bool made = std::string(argv[1]) == "made";
  const std::string path = made ? argv[2] : argv[1];
  const int block = !made && argc > 2 ? std::atoi(argv[2]) : 512;
  const int prepared = !made && argc > 3 ? std::atoi(argv[3]) : block;
  const double rate = 48000;
  Instrument ins;
  // Two hands on the paths that want them: the bank's split under the pad. A plain one otherwise -
  // the wheel's two among them, since that split has a Picture of each hand's own, and the wheel
  // moving the lower hand's alone would never take both amounts to nought, which `nought` needs.
  const bool hands = path != "input" && path != "bands" && path != "plain" && path != "turn" && path != "picture" && path != "nought";
  const scope::Preset* preset = scope::findPreset(hands ? "Bass under the pad" : "Turning fifths");
  if (!preset) { std::fprintf(stderr, "no preset\n"); return 2; }
  counting = made;
  ins.prepare(rate, prepared, preset->setup);
  counting = false;
  if (made) { std::printf("made %ld %ld 1\n", allocations.load(), bytes.load()); return 0; }

  const auto str = [](const char* s) { return scope::Json::string(std::string_view(s)); };
  const auto slide = [&](const char* id, const char16_t* v) { ins.apply(*Instrument::slider(id, v)); };
  if (path == "input") ins.apply(Instrument::click("srcMic"));
  if (path == "bands") { ins.apply(Instrument::click("srcMic")); ins.apply(Instrument::control("srcBands", str("1"))); }
  if (path == "rack" || path == "morph" || path == "host") {
    slide("delayMix", u"40"); slide("phaserMix", u"40"); slide("chorusMix", u"40"); slide("reverbMix", u"30"); slide("planeTwist", u"50");
  }
  if (path == "morph" || path == "host") {
    // Two ends apart in the cutoff, the delay's time and Scan, and the first LFO walking the fader between them.
    ins.storeMorph(false);
    slide("vcfCut", u"300"); slide("delayMs", u"200"); slide("oscScan", u"60");
    ins.storeMorph(true);
    ins.apply(Instrument::routings("lfo1>morph.pos@1.000"));
  }
  if (path == "photo") ins.apply(Instrument::click("photoButton"));
  if (path == "yt") ins.apply(Instrument::click("dispYT"));
  if (path == "spect") ins.apply(Instrument::click("dispSpect"));
  if (path == "lag") ins.apply(Instrument::control("lagOn", scope::Json::boolean(true)));
  if (path == "turn") slide("rotate", u"20");
  if (path == "arp") ins.apply(Instrument::control("arpMode", str("up")));
  if (path == "score") ins.apply(Instrument::control("scoreOn", scope::Json::boolean(true)));
  // The wheel given to the Picture amount (11 Nov), as Expression's Wheel menu gives it.
  if (path == "picture" || path == "nought") ins.apply(Instrument::control("midiWheelTo", str("picture")));

  std::vector<float> left(static_cast<std::size_t>(block)), right(left), inL(left), inR(left);
  std::vector<Instrument::Event> events;
  events.reserve(16);
  // A chord across both hands, held from the start: under the split and over it.
  static const std::uint8_t held[3][3] = { { 0x90, 40, 100 }, { 0x90, 64, 100 }, { 0x90, 76, 100 } };
  // And on `notes`, another struck and let go in turn, so voices are born and retired as the blocks go.
  static const std::uint8_t on[3][3] = { { 0x90, 41, 90 }, { 0x90, 65, 90 }, { 0x90, 77, 90 } };
  static const std::uint8_t off[3][3] = { { 0x80, 41, 0 }, { 0x80, 65, 0 }, { 0x80, 77, 0 } };
  for (const auto& m : held) events.push_back({ 0, m, 3 });
  const bool fed = path == "input" || path == "bands";
  long tick = 0;
  double heard = 0, lo = HUGE_VAL, hi = -HUGE_VAL;
  int bornFirst = -1, bornLast = -1;
  const auto newest = [&] {
    int most = 0;
    for (const auto* pool : { &ins.generator().voices(), &ins.generator().voicesB() })
      for (const auto& v : *pool) most = std::max(most, v.born);
    return most;
  };
  const auto play = [&](int count, bool counted) {
    for (int k = 0; k < count; ++k, ++tick) {
      for (int i = 0; i < block; ++i) {
        inL[static_cast<std::size_t>(i)] = static_cast<float>(0.4 * std::sin((tick * block + i) * 0.05));
        inR[static_cast<std::size_t>(i)] = static_cast<float>(0.3 * std::sin((tick * block + i) * 0.031));
      }
      if (path == "notes" && tick % 8 == 0) for (const auto& m : on) events.push_back({ block / 5, m, 3 });
      if (path == "notes" && tick % 8 == 4) for (const auto& m : off) events.push_back({ block / 3, m, 3 });
      // On `wheel`, the pitch wheel and the mod wheel moving every block, as a player's hand on them sends.
      std::uint8_t bend[3] = { 0xE0, 0, static_cast<std::uint8_t>(64 + 40 * std::sin(static_cast<double>(tick) * 0.07)) };
      std::uint8_t mod[3] = { 0xB0, 1, static_cast<std::uint8_t>(64 + 60 * std::sin(static_cast<double>(tick) * 0.03)) };
      if (path == "wheel") { events.push_back({ block / 4, bend, 3 }); events.push_back({ block / 2, mod, 3 }); }
      /* On `picture` the mod wheel on the Picture amount, every block and never
         at nought, so only the stage's depths move; on `nought` past nought and
         back, so its routes are made and dropped, which compiles them - the
         counter's null for `picture`. */
      std::uint8_t swept[3] = { 0xB0, 1, static_cast<std::uint8_t>(std::clamp(64 + 90 * std::sin(static_cast<double>(tick) * 0.03), 0.0, 127.0)) };
      if (path == "picture") events.push_back({ block / 2, mod, 3 });
      if (path == "nought") events.push_back({ block / 2, swept, 3 });
      const Instrument::Input input { inL.data(), inR.data() };
      const Instrument::HostSlider moved { "morphPos", 50 + 40 * std::sin(static_cast<double>(tick) * 0.05) };
      const bool host = path == "host";
      counting = counted;
      ins.block(left.data(), right.data(), block, events.data(), events.size(), nullptr, host ? &moved : nullptr, host ? 1 : 0,
                fed ? &input : nullptr);
      counting = false;
      events.clear();
      if (!counted) continue;
      for (int i = 0; i < block; ++i) heard += std::fabs(left[static_cast<std::size_t>(i)]) + std::fabs(right[static_cast<std::size_t>(i)]);
      const double cut = ins.slider(path == "picture" || path == "nought" ? "pictureAmount" : "vcfCut");
      lo = std::fmin(lo, cut); hi = std::fmax(hi, cut);
    }
  };
  play(static_cast<int>(std::ceil(20 * rate / block)), false);
  bornFirst = newest();
  const double stepsFirst = ins.score().steps;
  const long a0 = allocations.load(), b0 = bytes.load();
  play(400, true);
  const long spent = allocations.load() - a0, size = bytes.load() - b0;
  bornLast = newest();
  /* What the path was doing, as one number that must not be nought:
     - plain, input, bands, yt, spect, lag, turn, photo: what was heard, summed
       (and the input drawn, the bands' four lanes, the display, the lag, the
       screen's turn on the frame and the photocell registered, each or the
       number is nought);
     - held: what was heard, with voices held in both hands;
     - rack: what was heard, with all five of the rack's modules on;
     - morph, host: how far the cutoff the fader walks moved in the blocks;
     - picture, nought: how far the wheel walked the Picture amount;
     - notes, arp: voices born in the blocks;
     - wheel: what was heard, with the bend away from nought at the end;
     - score: the score's steps in the blocks. */
  double did = heard;
  const auto& tone = ins.tone();
  const auto& view = ins.view();
  const auto heldIn = [](const std::vector<scope::Voice>& pool) { for (const auto& v : pool) if (v.held) return true; return false; };
  if (path == "input" && !ins.drawsInput()) did = 0;
  if (path == "bands" && !(ins.bands() && ins.pictureLanes() == 4)) did = 0;
  if (path == "yt" && view.screen.display != "yt") did = 0;
  if (path == "spect" && view.screen.display != "spect") did = 0;
  if (path == "lag" && !view.capture.lagOn) did = 0;
  if (path == "turn" && !ins.picture().frame().turned) did = 0;
  if (path == "photo" && !ins.matrix().source("photo.1")) did = 0;
  if (path == "held" && !(heldIn(ins.generator().voices()) && heldIn(ins.generator().voicesB()))) did = 0;
  if (path == "rack" && !(tone.delayMix > 0 && tone.chorusMix > 0 && tone.phaserMix > 0 && tone.reverbMix > 0 && tone.planeTwist != 0)) did = 0;
  if (path == "morph" || path == "host" || path == "picture" || path == "nought") did = hi - lo;
  if (path == "notes" || path == "arp") did = bornLast - bornFirst;
  if (path == "score") did = ins.score().steps - stepsFirst;
  if (path == "wheel" && ins.keyboard().bend() == 0) did = 0;
  std::printf("%s %ld %ld %.9g\n", path.c_str(), spent, size, did);
  return 0;
}
