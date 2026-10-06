// The plugin's shell, run without a host or a web view: notes in, the core's
// generator's sound out, the page served, and the picture the page will draw
// carrying what was played. It prints PASS and FAIL lines in the house
// format and exits non-zero on a failure, like the web suite.
#include <algorithm>
#include <array>
#include <cmath>
#include <functional>
#include <cstdlib>
#include <cstdio>
#include <cstring>
#include <string>
#include <tuple>
#include <vector>

#include "../src/PluginEditor.h"
#include "../src/PluginProcessor.h"
#include "BinaryData.h"

namespace {
int failures = 0;
void check(const std::string& name, bool ok, const std::string& detail = {}) {
  std::printf("  %s  %s%s%s\n", ok ? "PASS" : "FAIL", name.c_str(), detail.empty() ? "" : "   ", detail.c_str());
  if (!ok) ++failures;
}
std::string num(double v) { char b[64]; std::snprintf(b, sizeof b, "%.6g", v); return b; }
}  // namespace

int main() {
  juce::ScopedJuceInitialiser_GUI juce;
  constexpr double rate = 48000;
  constexpr int block = 512;
  ScopeProcessor processor;
  processor.prepareToPlay(rate, block);

  // Two seconds: a note struck at sample 100 of the first block, let go at one second.
  const int total = static_cast<int>(rate * 2);
  std::vector<float> out, outR;
  out.reserve(static_cast<std::size_t>(total));
  juce::AudioBuffer<float> buffer(2, block);
  /* The picture is taken mid-note, while the note is playing. Taken at the end
     it was silence after the release, which reads the same in any order, and
     a snapshot handed over newest first passed as oldest first. */
  std::vector<float> midNote;
  std::size_t midNoteEnd = 0;
  for (int start = 0; start < total; start += block) {
    buffer.clear();
    juce::MidiBuffer midi;
    if (start == 0) midi.addEvent(juce::MidiMessage::noteOn(1, 69, 1.0f), 100);
    if (start <= rate && rate < start + block) midi.addEvent(juce::MidiMessage::noteOff(1, 69), static_cast<int>(rate) - start);
    processor.processBlock(buffer, midi);
    for (int i = 0; i < block && start + i < total; ++i) {
      out.push_back(buffer.getSample(0, i));
      outR.push_back(buffer.getSample(1, i));
    }
    if (midNote.empty() && start + block >= static_cast<int>(rate / 2)) {
      const auto served = scopeResource("/picture.bin", processor);
      if (served) {
        midNote.resize(served->data.size() / sizeof(float));
        std::memcpy(midNote.data(), served->data.data(), midNote.size() * sizeof(float));
      }
      midNoteEnd = out.size();
    }
  }

  std::printf("\n--- sound ---\n");
  /* The generator by itself, told what the host told the plugin, at the same
     samples: what the plugin plays has to be this, exactly. The engine is
     held to the page by core/tests/parity.py; this holds the plugin's own
     part - events at their own sample, the heard pair to the speakers and
     the picture pair to the page. `reference(101)` is the null: the note a
     sample late, which a plugin that moved events to the block's top, or
     anywhere else, could not tell from right. */
  const auto reference = [&](int on) {
    std::vector<scope::Lfo> lfos(2);
    lfos[0].rate = 0.2; lfos[0].depth = 0.5; lfos[1].rate = 0.5; lfos[1].depth = 0.3;
    scope::Generator core(rate, scope::slot::Used, lfos);
    core.setGated(true);
    std::vector<float> heardL(static_cast<std::size_t>(total)), heardR(heardL), picL(heardL), picR(heardL);
    int done = 0;
    const auto run = [&](int to) {
      core.block(picL.data() + done, picR.data() + done, to - done, heardL.data() + done, heardR.data() + done);
      done = to;
    };
    run(on); core.set("freq", juce::MidiMessage::getMidiNoteInHertz(69)); core.gate(true, 1.0);
    run(static_cast<int>(rate)); core.gate(false, 0);
    run(total);
    return std::array<std::vector<float>, 4> { heardL, heardR, picL, picR };
  };
  const auto expected = reference(100), late = reference(101);
  double off = 0, offLate = 0, before = 0, held = 0, tail = 0;
  for (std::size_t i = 0; i < out.size(); ++i) {
    off = std::fmax(off, std::fabs(out[i] - expected[0][i]) + std::fabs(outR[i] - expected[1][i]));
    offLate = std::fmax(offLate, std::fabs(out[i] - late[0][i]));
  }
  for (int i = 0; i < 100; ++i) before = std::fmax(before, std::fabs(out[static_cast<std::size_t>(i)]));
  for (int i = 24000; i < 26000; ++i) held = std::fmax(held, std::fabs(out[static_cast<std::size_t>(i)]));
  for (int i = total - 2000; i < total; ++i) tail = std::fmax(tail, std::fabs(out[static_cast<std::size_t>(i)]));
  check("the plugin plays the core's generator, sample for sample, told at the note's own sample",
        off == 0 && offLate > 1e-3, "off by " + num(off) + "; a sample late would be off by " + num(offLate));
  check("silent until the note, sounding while it is held, and silent once its release is over",
        before == 0 && held > 0.3 && tail == 0, num(before) + ", " + num(held) + ", " + num(tail));

  /* Two keys, the second struck mid-block in another block, and released two
     ways: a note-on at velocity nought, which is how most keyboards send a
     release, and a note-off. The plugin hands the host's bytes to the core's
     keyboard; the reference tells a keyboard and a generator the same notes
     by name, at the same samples, with a release where the plugin got a
     velocity of nought - so the byte path is what is being held. */
  struct Played { std::vector<float> l, r; };
  const auto playDyad = [&](int second, bool routed = false, const char* preset = nullptr, bool morphed = false) {
    ScopeProcessor p;
    if (preset) setenv("SCOPE_PRESET", preset, 1);
    p.prepareToPlay(rate, block);
    unsetenv("SCOPE_PRESET");
    if (routed) { p.matrix().add("lfo1", "gen.freq", 0.5); p.matrix().add("midi.key", "gen.amp", 0.6); }
    if (morphed) {
      p.moveSlider("amp", 20); p.storeMorph(false);
      p.moveSlider("amp", 120); p.moveSlider("delayMix", 60); p.storeMorph(true);
      p.matrix().add("lfo1", "morph.pos", -1);
    }
    Played got;
    juce::AudioBuffer<float> buf(2, block);
    for (int start = 0; start < total; start += block) {
      buf.clear();
      juce::MidiBuffer m;
      const auto at = [&](int sample, const juce::MidiMessage& msg) {
        if (sample >= start && sample < start + block) m.addEvent(msg, sample - start);
      };
      at(100, juce::MidiMessage::noteOn(1, 57, static_cast<juce::uint8>(100)));
      at(second, juce::MidiMessage::noteOn(1, 64, static_cast<juce::uint8>(90)));
      at(40000, juce::MidiMessage::noteOn(1, 64, static_cast<juce::uint8>(0)));
      at(static_cast<int>(rate), juce::MidiMessage::noteOff(1, 57));
      p.processBlock(buf, m);
      for (int i = 0; i < block && start + i < total; ++i) { got.l.push_back(buf.getSample(0, i)); got.r.push_back(buf.getSample(1, i)); }
    }
    return got;
  };
  const auto dyadReference = [&](int second, bool routed = false, const char* preset = nullptr, bool morphed = false,
                                 bool noTables = false) {
    std::vector<scope::Lfo> lfos(2);
    lfos[0].rate = 0.2; lfos[0].depth = 0.5; lfos[1].rate = 0.5; lfos[1].depth = 0.3;
    scope::Generator core(rate, scope::slot::Used, lfos);
    scope::GeneratorNotes notes(core);
    scope::Keyboard keys(notes);
    scope::Matrix matrix;
    scope::CoreSources sources(matrix, core, lfos, keys);
    scope::Brain brain;
    scope::BrainSources brainSources(matrix, brain);
    keys.setPresent(true);
    if (preset) scope::restoreSetup(scope::findPreset(preset)->setup, brain, core, keys, matrix, lfos);
    if (noTables) { core.setCycle(nullptr); core.setWavetable(nullptr); }  // what the core played before the cycles
    if (routed) { matrix.add("lfo1", "gen.freq", 0.5); matrix.add("midi.key", "gen.amp", 0.6); }
    if (morphed) {
      scope::moveSlider("amp", u"20", brain, core, keys, lfos); scope::morphStore(brain, false);
      scope::moveSlider("amp", u"120", brain, core, keys, lfos); scope::moveSlider("delayMix", u"60", brain, core, keys, lfos);
      scope::morphStore(brain, true);
      matrix.add("lfo1", "morph.pos", -1);
    }
    keys.frame(0);
    std::vector<float> l(static_cast<std::size_t>(total)), r(l), pl(l), pr(l);
    int done = 0;
    // Each block: the keyboard's frame, the matrix's, and the routes held
    // across the block - as the plugin is meant to do it, written out.
    const auto top = [&] {
      const double ms = 1000.0 * block / rate;
      keys.frame(done == 0 ? 0 : ms);
      matrix.setLayered(keys.layersOn());
      matrix.setStrikes(keys.strikes());
      matrix.frame(done * 1000.0 / rate);
      scope::morphStep(brain, core, keys, lfos);
      core.setRoutes(matrix.routes(done * 1000.0 / rate));
    };
    const auto run = [&](int to) {
      while (done < to) {
        if (done % block == 0) top();
        const int end = std::min(to, (done / block + 1) * block);
        core.block(pl.data() + done, pr.data() + done, end - done, l.data() + done, r.data() + done);
        done = end;
      }
    };
    run(100); keys.noteOn(57, 100);
    run(second); keys.noteOn(64, 90);
    run(40000); keys.noteOff(64);
    run(static_cast<int>(rate)); keys.noteOff(57);
    run(total);
    return std::array<std::vector<float>, 4> { l, r, pl, pr };
  };
  const Played dyad = playDyad(1300);
  const auto dyadWant = dyadReference(1300), dyadLate = dyadReference(1301);
  double dyadOff = 0, dyadOffLate = 0;
  for (std::size_t i = 0; i < dyad.l.size(); ++i) {
    dyadOff = std::fmax(dyadOff, std::fabs(dyad.l[i] - dyadWant[0][i]) + std::fabs(dyad.r[i] - dyadWant[1][i]));
    dyadOffLate = std::fmax(dyadOffLate, std::fabs(dyad.l[i] - dyadLate[0][i]) + std::fabs(dyad.r[i] - dyadLate[1][i]));
  }
  check("two keys through the plugin are the core's keyboard playing its generator, a velocity of nought a release",
        dyadOff == 0 && dyadOffLate > 1e-3, "off by " + num(dyadOff) + "; the second key a sample late would be off by " + num(dyadOffLate));
  /* With routings: the matrix's routes reach the generator at the top of each
     block, an LFO on the pitch and the key's velocity ducking the level. The
     same notes with no routings are the null - the routes have to be heard. */
  const Played routed = playDyad(1300, true);
  const auto routedWant = dyadReference(1300, true);
  double routedOff = 0, unrouted = 0;
  for (std::size_t i = 0; i < routed.l.size(); ++i) {
    routedOff = std::fmax(routedOff, std::fabs(routed.l[i] - routedWant[0][i]) + std::fabs(routed.r[i] - routedWant[1][i]));
    unrouted = std::fmax(unrouted, std::fabs(routed.l[i] - dyadWant[0][i]));
  }
  check("routed, the plugin is the core's matrix compiling routes for its generator a block at a time",
        routedOff == 0 && unrouted > 0.05, "off by " + num(routedOff) + "; the same notes unrouted differ by " + num(unrouted));

  /* The morph, swept by an LFO through the matrix: amp from 20 to 120 and the
     echo's mix in with it, B stored and LFO 1 pulling the fader back towards
     A. The plugin walks the sliders after the matrix every block; held to the
     core doing the same written out. The same ends with the fader left alone
     are the null - B the whole way, so the sweep has to be heard. */
  const Played morphed = playDyad(1300, false, nullptr, true);
  const auto morphedWant = dyadReference(1300, false, nullptr, true);
  const Played resting = [&] {
    ScopeProcessor p;
    p.prepareToPlay(rate, block);
    p.moveSlider("amp", 20); p.storeMorph(false);
    p.moveSlider("amp", 120); p.moveSlider("delayMix", 60); p.storeMorph(true);
    Played got;
    juce::AudioBuffer<float> buf(2, block);
    for (int start = 0; start < total; start += block) {
      buf.clear();
      juce::MidiBuffer m;
      const auto at = [&](int sample, const juce::MidiMessage& msg) {
        if (sample >= start && sample < start + block) m.addEvent(msg, sample - start);
      };
      at(100, juce::MidiMessage::noteOn(1, 57, static_cast<juce::uint8>(100)));
      at(1300, juce::MidiMessage::noteOn(1, 64, static_cast<juce::uint8>(90)));
      at(40000, juce::MidiMessage::noteOn(1, 64, static_cast<juce::uint8>(0)));
      at(static_cast<int>(rate), juce::MidiMessage::noteOff(1, 57));
      p.processBlock(buf, m);
      for (int i = 0; i < block && start + i < total; ++i) { got.l.push_back(buf.getSample(0, i)); got.r.push_back(buf.getSample(1, i)); }
    }
    return got;
  }();
  double morphOff = 0, unswept = 0;
  for (std::size_t i = 0; i < morphed.l.size(); ++i) {
    morphOff = std::fmax(morphOff, std::fabs(morphed.l[i] - morphedWant[0][i]) + std::fabs(morphed.r[i] - morphedWant[1][i]));
    unswept = std::fmax(unswept, std::fabs(morphed.l[i] - resting.l[i]));
  }
  check("an LFO on the morph's fader walks the sliders in the plugin as the core walks them, block by block",
        morphOff == 0 && unswept > 0.05, "off by " + num(morphOff) + "; the fader left at B differs by " + num(unswept));

  /* A preset by name, loaded in the plugin through the core's restore: "Wah",
     a ramp through a resonant filter an LFO sweeps. Held to the core told the
     same preset and the same notes directly; the same notes on the preset the
     plugin opens on are the null. */
  const Played wah = playDyad(1300, false, "Wah");
  const auto wahWant = dyadReference(1300, false, "Wah");
  double wahOff = 0, wahVsBoot = 0;
  for (std::size_t i = 0; i < wah.l.size(); ++i) {
    wahOff = std::fmax(wahOff, std::fabs(wah.l[i] - wahWant[0][i]) + std::fabs(wah.r[i] - wahWant[1][i]));
    wahVsBoot = std::fmax(wahVsBoot, std::fabs(wah.l[i] - dyadWant[0][i]));
  }
  check("a preset loaded in the plugin is the core restoring it: \"Wah\", sample for sample",
        wahOff == 0 && wahVsBoot > 0.05, "off by " + num(wahOff) + "; the preset it opens on differs by " + num(wahVsBoot));

  /* "A drawn cycle": the shape is a drawing, its 256 points in the preset's
     code, and restore builds its tables and hands them to the generator.
     Before the cycles were ported the core had no tables and played a sine
     for it, and the same preset with no tables is the null: plugin and core
     restoring alike would agree whether or not either built any. */
  const Played drawn = playDyad(1300, false, "A drawn cycle");
  const auto drawnWant = dyadReference(1300, false, "A drawn cycle");
  const auto drawnSine = dyadReference(1300, false, "A drawn cycle", false, true);
  double drawnOff = 0, drawnVsSine = 0;
  for (std::size_t i = 0; i < drawn.l.size(); ++i) {
    drawnOff = std::fmax(drawnOff, std::fabs(drawn.l[i] - drawnWant[0][i]) + std::fabs(drawn.r[i] - drawnWant[1][i]));
    drawnVsSine = std::fmax(drawnVsSine, std::fabs(drawn.l[i] - drawnSine[0][i]));
  }
  check("a drawn cycle loaded in the plugin plays the tables the core builds from its points",
        drawnOff == 0 && drawnVsSine > 0.05, "off by " + num(drawnOff) + "; with no tables it would differ by " + num(drawnVsSine));

  /* And it is a fifth: the picture's right channel crosses upwards three times
     for the left's two while both keys are held. The one-key run is the null,
     at one to one. */
  const auto ratio = [&](const std::vector<float>& a, const std::vector<float>& b) {
    int ca = 0, cb = 0;
    for (std::size_t i = 4801; i < 38400; ++i) {
      ca += a[i - 1] < 0 && a[i] >= 0;
      cb += b[i - 1] < 0 && b[i] >= 0;
    }
    return ca ? static_cast<double>(cb) / ca : 0.0;
  };
  const double fifth = ratio(dyadWant[2], dyadWant[3]), unison = ratio(expected[2], expected[3]);
  check("and the picture is the fifth the two keys make, its right channel at three to the left's two",
        std::fabs(fifth - 1.5) < 0.01 && std::fabs(unison - 1) < 0.01, num(fifth) + " to one; one key is " + num(unison));

  std::printf("\n--- the clock ---\n");
  /* "Wobble" locks LFO 1 to a quaver: four cycles a second at the page's 120,
     three at a host's 90. A stand-in host plays at 90 from beat 8, then
     stops, then goes away; the same preset with no host is the null. */
  struct Head : juce::AudioPlayHead {
    juce::Optional<PositionInfo> getPosition() const override {
      if (!there) return {};
      PositionInfo p;
      p.setBpm(bpm); p.setPpqPosition(ppq); p.setIsPlaying(playing);
      return p;
    }
    double bpm = 90, ppq = 8;
    bool playing = true, there = true;
  };
  {
    setenv("SCOPE_PRESET", "Wobble", 1);
    ScopeProcessor hosted, alone;
    hosted.prepareToPlay(rate, block); alone.prepareToPlay(rate, block);
    unsetenv("SCOPE_PRESET");
    Head head;
    hosted.setPlayHead(&head);
    juce::AudioBuffer<float> buf(2, block);
    juce::MidiBuffer none;
    const auto blocks = [&](ScopeProcessor& p, int n, bool advance) {
      for (int k = 0; k < n; ++k) {
        buf.clear();
        p.processBlock(buf, none);
        if (advance && head.playing) head.ppq += block / rate * head.bpm / 60;
      }
    };
    blocks(hosted, 40, true); blocks(alone, 40, false);
    const double lastPpq = head.ppq - block / rate * head.bpm / 60;
    const auto& c = hosted.clock();
    check("under a host at 90 the clock is the host's: its tempo, its position for the bar, and a locked oscillator at its quaver",
          c.from == scope::Clock::From::Host && c.bpm == 90 && c.set == 120 && std::fabs(c.beat(c.now()) - lastPpq) < 1e-9
          && std::fabs(hosted.lfoRate(0) - 3) < 1e-12 && std::fabs(alone.lfoRate(0) - 4) < 1e-12
          && alone.clock().from == scope::Clock::From::Internal,
          "bpm " + num(c.bpm) + ", beat " + num(c.beat(c.now())) + " against " + num(lastPpq) + ", LFO " + num(hosted.lfoRate(0))
          + "; with no host " + num(alone.lfoRate(0)));
    head.playing = false;
    blocks(hosted, 3, true);
    check("the host stopped is the bar stopped where the host says it is",
          !c.running && std::fabs(c.beat(c.now() + 500) - head.ppq) < 1e-9, "beat " + num(c.beat(c.now() + 500)));
    head.there = false;
    blocks(hosted, 60, true);
    check("and a host gone quiet for half a second gives the tempo back to the slider", c.from == scope::Clock::From::Internal
          && c.bpm == 120 && std::fabs(hosted.lfoRate(0) - 4) < 1e-12, "bpm " + num(c.bpm) + ", LFO " + num(hosted.lfoRate(0)));
  }
  /* A MIDI clock through the plugin's bytes: ticks at 150, each at its own
     sample. Stamped at the block's top instead, the ticks in one block would
     land at one time and the tempo come out wrong. */
  {
    setenv("SCOPE_PRESET", "Wobble", 1);
    ScopeProcessor p;
    p.prepareToPlay(rate, block);
    unsetenv("SCOPE_PRESET");
    juce::AudioBuffer<float> buf(2, block);
    const double tickSamples = rate * 60 / 150 / 24;
    double next = 300;
    for (int start = 0; start < static_cast<int>(rate); start += block) {
      buf.clear();
      juce::MidiBuffer m;
      for (; next < start + block; next += tickSamples) {
        const std::uint8_t tick = 0xF8;
        m.addEvent(&tick, 1, static_cast<int>(next) - start);
      }
      p.processBlock(buf, m);
    }
    const auto& c = p.clock();
    check("a MIDI clock at 150 through the plugin's bytes, each tick at its own sample, is a tempo of 150 and LFO 1 at five",
          c.from == scope::Clock::From::Midi && std::fabs(c.bpm - 150) < 0.5 && std::fabs(p.lfoRate(0) - c.bpm / 30) < 1e-12,
          "bpm " + num(c.bpm) + ", LFO " + num(p.lfoRate(0)));
  }

  /* The arpeggiator, in "Intervals in turn": a chord struck over 12 ms is
     gathered, and nothing sounds until the first step, 25 ms after the first
     key - 1,200 samples at 48 kHz. The page strikes it on a timer; the plugin
     strikes it at its own sample, where the next block's top would be 1,536. */
  {
    setenv("SCOPE_PRESET", "Intervals in turn", 1);
    ScopeProcessor p;
    p.prepareToPlay(rate, block);
    unsetenv("SCOPE_PRESET");
    std::vector<float> got;
    juce::AudioBuffer<float> buf(2, block);
    for (int start = 0; start < static_cast<int>(rate); start += block) {
      buf.clear();
      juce::MidiBuffer m;
      const auto at = [&](int sample, const juce::MidiMessage& msg) {
        if (sample >= start && sample < start + block) m.addEvent(msg, sample - start);
      };
      at(100, juce::MidiMessage::noteOn(1, 64, static_cast<juce::uint8>(90)));
      at(100 + 384, juce::MidiMessage::noteOn(1, 60, static_cast<juce::uint8>(100)));
      at(100 + 576, juce::MidiMessage::noteOn(1, 67, static_cast<juce::uint8>(80)));
      p.processBlock(buf, m);
      for (int i = 0; i < block; ++i) got.push_back(buf.getSample(0, i));
    }
    std::size_t onset = 0;
    while (onset < got.size() && got[onset] == 0.0f) ++onset;
    const auto loud = [&](std::size_t from, std::size_t to) {
      double most = 0;
      for (std::size_t i = from; i < to && i < got.size(); ++i) most = std::fmax(most, std::fabs(got[i]));
      return most;
    };
    check("an arpeggio's first step sounds 25 ms after the first key, to the sample, and the arpeggio goes on stepping",
          onset >= 1300 && onset < 1303 && loud(1300 + 12000, 1300 + 24000) > 0.05 && loud(36000, 48000) > 0.05,
          "first sound at sample " + std::to_string(onset) + "; later " + num(loud(36000, 48000)));
  }

  std::printf("\n--- MIDI out ---\n");
  /* What the plugin hands back to the host: every message, with its sample
     counted from the start of the run. */
  struct Sent { int sample; std::uint8_t a, b, c; };
  struct Hits : scope::ModSource {
    Hits() : ModSource("test.hits") { event = true; }
    double value() const override { return 0; }
    int count() const override { return n; }
    int n = 0;
  };
  const auto sendOut = [&](const char* preset, const std::vector<std::pair<int, juce::MidiMessage>>& played, int blocksToRun,
                           Hits* hits = nullptr, int hitAt = 0, juce::AudioPlayHead* head = nullptr) {
    setenv("SCOPE_PRESET", preset, 1);
    auto p = std::make_unique<ScopeProcessor>();
    p->prepareToPlay(rate, block);
    unsetenv("SCOPE_PRESET");
    /* The preset's own threshold routing is taken away for a hit of the
       test's own: its pendulums swing from the start, and the level they
       make plucks once by itself (see "the sources", below). */
    if (hits) { p->matrix().remove("threshold", "gen.pluck"); p->matrix().registerSource(hits); p->matrix().add("test.hits", "gen.pluck", 0.8); }
    if (head) p->setPlayHead(head);
    std::vector<Sent> sent;
    juce::AudioBuffer<float> buf(2, block);
    for (int k = 0; k < blocksToRun; ++k) {
      const int start = k * block;
      buf.clear();
      juce::MidiBuffer m;
      for (const auto& [sample, msg] : played)
        if (sample >= start && sample < start + block) m.addEvent(msg, sample - start);
      if (hits && start == hitAt) hits->n++;
      p->processBlock(buf, m);
      for (const auto event : m) {
        const auto* d = event.data;
        sent.push_back({ start + event.samplePosition, d[0], event.numBytes > 1 ? d[1] : std::uint8_t(0),
                         event.numBytes > 2 ? d[2] : std::uint8_t(0) });
      }
    }
    return std::make_pair(std::move(p), sent);
  };
  const auto ons = [](const std::vector<Sent>& sent) {
    std::vector<Sent> out;
    for (const auto& e : sent) if ((e.a & 0xF0) == 0x90 && e.c > 0) out.push_back(e);
    return out;
  };
  const auto offs = [](const std::vector<Sent>& sent) {
    std::vector<Sent> out;
    for (const auto& e : sent) if ((e.a & 0xF0) == 0x80) out.push_back(e);
    return out;
  };
  {
    /* The arpeggio sent as it is played: its first step at sample 1300, 25 ms
       after the first key, where the next block's top is 1536; then a quaver
       at 120 apart, 12,000 samples, each at the first block's top on or after
       its time, as the page steps it in its frame, with the last step's note
       ended first. Four in the second; and the chord let go at sample 40,000,
       which ends the step sounding there and then, at the release's own
       sample. The host's own notes are not sent back. */
    const auto [p, sent] = sendOut("Intervals in turn", { { 100, juce::MidiMessage::noteOn(1, 64, static_cast<juce::uint8>(90)) },
                                                         { 484, juce::MidiMessage::noteOn(1, 60, static_cast<juce::uint8>(100)) },
                                                         { 676, juce::MidiMessage::noteOn(1, 67, static_cast<juce::uint8>(80)) },
                                                         { 40000, juce::MidiMessage::noteOff(1, 64) },
                                                         { 40000, juce::MidiMessage::noteOff(1, 60) },
                                                         { 40000, juce::MidiMessage::noteOff(1, 67) } }, 94);
    const auto on = ons(sent), off = offs(sent);
    bool stepped = on.size() == 4 && off.size() == 4 && off[3].sample == 40000 && off[3].b == on[3].b;
    for (std::size_t k = 1; stepped && k < on.size(); ++k) {
      const int due = 1300 + static_cast<int>(k) * 12000, top = (due + block - 1) / block * block;
      stepped = on[k].sample == top && off[k - 1].sample == top && off[k - 1].b == on[k - 1].b;
    }
    const bool unechoed = std::none_of(sent.begin(), sent.end(), [](const Sent& e) {
      return e.sample == 100 || e.sample == 484 || e.sample == 676 || (e.sample == 40000 && e.b != 64);
    });
    check("the arpeggio goes out to the host as it is struck: its first step at sample 1300, on channel 1, then a step a quaver, each ending the last, the last ended as the chord is let go",
          !on.empty() && on[0].sample == 1300 && on[0].a == 0x90 && stepped && unechoed,
          on.empty() ? "nothing sent" : "first at " + std::to_string(on[0].sample) + ", " + std::to_string(on.size()) + " steps, "
          + std::to_string(off.size()) + " ended");
  }
  {
    /* "Three against two": the crossings on, a note held so the figure is
       drawn, and each crossing of a line sent as its note at velocity 102 and
       ended a tenth of a second on - both at a block's top, the crossings'
       frame. At three against two both lines are crossed together, twice in
       the second. The boot preset, the crossings off, is the null: nothing. */
    const std::vector<std::pair<int, juce::MidiMessage>> held { { 100, juce::MidiMessage::noteOn(1, 57, static_cast<juce::uint8>(100)) } };
    const auto [p, sent] = sendOut("Three against two", held, 94);
    const auto [q, quiet] = sendOut("Harmonic tone", held, 94);
    const auto on = ons(sent), off = offs(sent);
    bool tops = true, notes = true;
    for (const auto& e : on) { tops = tops && e.sample % block == 0; notes = notes && (e.b == 60 || e.b == 67) && e.c == 102; }
    for (const auto& e : off) tops = tops && e.sample % block == 0;
    const bool both = std::any_of(on.begin(), on.end(), [](const Sent& e) { return e.b == 60; })
                      && std::any_of(on.begin(), on.end(), [](const Sent& e) { return e.b == 67; });
    // Each note's own note-off: two notes struck in one block are ended in the other order.
    bool later = on.size() >= 2 && off.size() >= 2;
    for (std::size_t k = 0; later && k < 2; ++k) {
      const auto end = std::find_if(off.begin(), off.end(), [&](const Sent& e) { return e.b == on[k].b; });
      later = end != off.end() && end->sample - on[k].sample >= rate / 10 && end->sample - on[k].sample < rate / 10 + block;
    }
    check("a crossing goes out as its line's note at a block's top, both lines' notes, each ended a tenth of a second on",
          on.size() == 4 && tops && notes && both && later && quiet.empty(),
          std::to_string(on.size()) + " sent, " + std::to_string(off.size()) + " ended"
          + "; with the crossings off " + std::to_string(quiet.size()));
  }
  {
    /* A routing fires the pluck: "Pendulums ring a bell" has it at C5, 72,
       where the core's own stand-in strikes middle C and sends nothing. Struck
       in the block after the hit, sent at velocity 102 and ended 150 ms on. */
    Hits hits;
    const auto [p, sent] = sendOut("Pendulums ring a bell", {}, 40, &hits, 10 * block);
    const auto on = ons(sent), off = offs(sent);
    check("the pluck, fired by a routing, is struck at the setup's pluck note and sent, and ended 150 ms on",
          on.size() == 1 && on[0].b == 72 && on[0].c == 102 && on[0].sample == 10 * block && off.size() == 1 && off[0].b == 72
          && off[0].sample - on[0].sample >= rate * 0.15 && off[0].sample - on[0].sample < rate * 0.15 + block,
          on.empty() ? "nothing sent" : "note " + std::to_string(on[0].b) + " at " + std::to_string(on[0].sample)
          + (off.empty() ? ", never ended" : ", ended at " + std::to_string(off[0].sample)));
  }
  {
    /* "A sine, sung" has the score on, a step a semiquaver, reading the grid
       the plugin draws for itself. Its playhead runs on the bar - and through
       a host's count-in, two beats before the one, it waits: a bar of minus
       two would be column minus eight, and a grid read from there. It sends
       what the grid lights; the same with the spectrogram showing, which no
       beam draws and which leaves the grid dark, sends nothing at all. */
    struct Head : juce::AudioPlayHead {
      juce::Optional<PositionInfo> getPosition() const override {
        PositionInfo p;
        p.setBpm(120); p.setPpqPosition(ppq); p.setIsPlaying(true);
        return p;
      }
      double ppq = -2;
    } head;
    struct Sung { bool on = false, waited = true, followed = true; int counted = 0, ons = 0, col = 0; };
    const auto sing = [&](bool spectrogram) {
      head.ppq = -2;
      setenv("SCOPE_PRESET", "A sine, sung", 1);
      ScopeProcessor p;
      p.prepareToPlay(rate, block);
      unsetenv("SCOPE_PRESET");
      p.setPlayHead(&head);
      if (spectrogram) p.pageClick("dispSpect");
      juce::AudioBuffer<float> buf(2, block);
      juce::MidiBuffer m;
      Sung out;
      for (int k = 0; k < 160; ++k) {
        buf.clear();
        m.clear();
        // A held A3, so there is a sine to draw.
        if (k == 0) m.addEvent(juce::MidiMessage::noteOn(1, 57, static_cast<juce::uint8>(100)), 0);
        const double at = head.ppq;
        p.processBlock(buf, m);
        for (const auto e : m) out.ons += e.getMessage().isNoteOn() ? 1 : 0;
        if (at < 0) out.waited = out.waited && p.score().col == -1;
        else { out.followed = out.followed && p.score().col == static_cast<int>(std::floor(at * 4 + 1e-9)) % 64; out.counted++; }
        head.ppq += block / rate * 2;
      }
      out.on = p.score().on;
      out.col = p.score().col;
      return out;
    };
    const Sung sung = sing(false), dark = sing(true);
    check("the score's playhead waits through a host's count-in and then follows its bar, a column a semiquaver, and plays the grid the plugin draws; on the spectrogram's dark grid it plays nothing",
          sung.on && sung.waited && sung.followed && sung.counted > 40 && sung.ons > 0 && dark.ons == 0,
          "col " + std::to_string(sung.col) + " at the end, " + std::to_string(sung.counted) + " blocks after the one, "
          + std::to_string(sung.ons) + " notes sent, " + std::to_string(dark.ons) + " on the spectrogram");
  }

  std::printf("\n--- the picture, with the window closed ---\n");
  {
    /* No editor is opened anywhere here: the grid, the photocell and the
       picture's sources are the plugin's own, drawn from its picture ring.
       "Pendulums bent by the light" is a harmonograph in X-Y whose photocell
       bends the ratio of the figure it draws - a loop through the picture,
       which the heard pendulums do not carry; "Brightness opens the ellipse"
       turns the phase between a held sine's two channels, and is heard as the
       stereo image opening. Each check against the failure it would show:
       the loop's routings taken away is the null for the loop doing
       anything, and the photocell switched off from the page must be exactly
       that null, picture and sound, since its sources are then not there. */
    struct Run {
      std::vector<float> l, r, picture;
      int frames = 0;
      double lit = 0, most = -1, least = 2;
      bool registered = false;
      std::string display;
    };
    const auto run = [&](const char* preset, bool held, int blocks, const std::function<void(ScopeProcessor&)>& before) {
      setenv("SCOPE_PRESET", preset, 1);
      auto p = std::make_unique<ScopeProcessor>();
      p->prepareToPlay(rate, block);
      unsetenv("SCOPE_PRESET");
      if (before) before(*p);
      Run out;
      juce::AudioBuffer<float> buf(2, block);
      juce::MidiBuffer m;
      for (int k = 0; k < blocks; ++k) {
        buf.clear();
        m.clear();
        if (k == 0 && held) m.addEvent(juce::MidiMessage::noteOn(1, 57, static_cast<juce::uint8>(100)), 0);
        p->processBlock(buf, m);
        for (int i = 0; i < block; ++i) { out.l.push_back(buf.getSample(0, i)); out.r.push_back(buf.getSample(1, i)); }
        if (k >= blocks / 2) {
          const double reading = p->picture().pictures().photo();
          out.most = std::fmax(out.most, reading);
          out.least = std::fmin(out.least, reading);
        }
      }
      out.frames = p->picture().phosphor().frames();
      for (const float c : p->picture().phosphor().grid()) out.lit += c;
      out.registered = p->matrix().source("photo.1") && p->matrix().source("picture.round") && p->matrix().source("picture.bored");
      out.display = p->view().screen.display;
      out.picture = p->pictureSnapshot();
      return out;
    };
    const auto most = [](const std::vector<float>& a, const std::vector<float>& b) {
      double worst = a.size() == b.size() ? 0 : 1;
      for (std::size_t i = 0; i < a.size() && i < b.size(); ++i) worst = std::fmax(worst, std::fabs(a[i] - b[i]));
      return worst;
    };
    const int blocks = static_cast<int>(std::ceil(2 * rate / block));  // two seconds
    const char* bent = "Pendulums bent by the light";
    const Run looped = run(bent, false, blocks, nullptr);
    const Run open = run(bent, false, blocks, [](ScopeProcessor& p) {
      p.matrix().remove("photo.1", "gen.ratio");
      p.matrix().remove("picture.bored", "gen.swing");
    });
    const Run off = run(bent, false, blocks, [](ScopeProcessor& p) { p.pageClick("photoButton"); });
    const Run yt = run(bent, false, blocks, [](ScopeProcessor& p) { p.pageClick("dispYT"); });
    const double seconds = blocks * static_cast<double>(block) / rate;
    const double want = std::floor(seconds * 1000 / scope::kPictureFrameMs) + 1;
    check("the plugin draws its own picture at the page's sixty frames a second: " + std::to_string(looped.frames) + " in "
          + num(seconds) + " s, not one a block (" + std::to_string(blocks) + ")",
          std::fabs(looped.frames - want) <= 1, "wanted " + num(want));
    check("with the photocell on, its sources and the picture's are there, the grid is lit, and the reading moves",
          looped.registered && looped.lit > 1 && looped.most - looped.least > 0.01,
          "lit " + num(looped.lit) + ", reading " + num(looped.least) + " to " + num(looped.most));
    const double bentApart = most(looped.picture, open.picture);
    check("the loop goes round with no window: the photocell bends the figure the pendulums draw, against the same without its routings",
          bentApart > 0.01, "the pictures apart by " + num(bentApart));
    const double offPicture = most(off.picture, open.picture), offSound = most(off.l, open.l) + most(off.r, open.r);
    check("and the photocell switched off from the page is that null exactly, picture and sound, its sources gone",
          offPicture == 0 && offSound == 0 && !off.registered && off.most == 0 && off.least == 0,
          "picture off by " + num(offPicture) + ", sound by " + num(offSound));
    check("and Y-T chosen on the page is the plugin's view, drawn into its grid in place of the figure",
          yt.display == "yt" && looped.display == "xy" && std::fabs(yt.lit - looped.lit) > 1,
          "lit " + num(yt.lit) + " against " + num(looped.lit));
    /* An oscillator on the zoom, sent from the page as its routings: the
       destination is the plugin's, the offset it writes is in the view, and
       the zoom the walk draws at is made again from it after the matrix -
       so the grid differs from the figure at the zoom's own step. And the
       Clear button, with persistence at infinite so everything drawn stays:
       the frame after it starts the grid again. */
    const Run zoomed = run(bent, false, blocks, [](ScopeProcessor& p) {
      p.pageRoutings("photo.1>gen.ratio@0.300;picture.bored>gen.swing@0.300;lfo1>view.zoom@1.000");
    });
    double zoomMod = 0, zoomNow = 0, zoomStep = 0;
    {
      setenv("SCOPE_PRESET", bent, 1);
      ScopeProcessor p;
      p.prepareToPlay(rate, block);
      unsetenv("SCOPE_PRESET");
      p.pageRoutings("photo.1>gen.ratio@0.300;picture.bored>gen.swing@0.300;lfo1>view.zoom@1.000");
      juce::AudioBuffer<float> buf(2, block);
      juce::MidiBuffer m;
      for (int k = 0; k < 40; ++k) { buf.clear(); p.processBlock(buf, m); }
      zoomMod = p.view().zoomMod; zoomNow = p.view().screen.zoom; zoomStep = p.view().zoomStep;
    }
    check("an oscillator on the zoom from the page moves the plugin's picture: the offset in the view, the zoom made again from it",
          zoomMod != 0 && std::fabs(zoomNow - std::pow(2, (zoomStep + zoomMod) / 4)) < 1e-12 && zoomNow != std::pow(2, zoomStep / 4)
          && std::fabs(zoomed.lit - looped.lit) > 1,
          "offset " + num(zoomMod) + ", zoom " + num(zoomNow) + ", lit " + num(zoomed.lit) + " against " + num(looped.lit));
    double kept = 0, cleared = 0;
    {
      setenv("SCOPE_PRESET", bent, 1);
      ScopeProcessor p;
      p.prepareToPlay(rate, block);
      unsetenv("SCOPE_PRESET");
      p.pageControl("persistence", scope::Json::string(std::string_view("-1")));
      juce::AudioBuffer<float> buf(2, block);
      juce::MidiBuffer m;
      const auto litNow = [&] { double lit = 0; for (const float c : p.picture().phosphor().grid()) lit += c; return lit; };
      for (int k = 0; k < blocks; ++k) { buf.clear(); p.processBlock(buf, m); }
      kept = litNow();
      p.pageClick("clearButton");
      // Two blocks: the click at the first one's top, and a frame due in one or the other.
      for (int k = 0; k < 2; ++k) { buf.clear(); p.processBlock(buf, m); }
      cleared = litNow();
    }
    check("with persistence at infinite the grid keeps everything, and the page's Clear starts it again",
          kept > looped.lit * 2 && cleared < kept / 4, "lit " + num(kept) + ", then " + num(cleared));
    /* The frame the plugin draws by is the page's capture of its picture
       ring as the ring stood at the top of that frame's block - which is the
       ring as the block before left it - at the host's rate, within the
       ring's capacity, left as left. At 20 ms a division the window and the
       trigger's search behind it ask for more than the ring holds, so the
       capture has to give way as the page's does for a short buffer. */
    double frameOff = -1, lastLength = 0, lastAsked = 0;
    int compared = 0;
    {
      setenv("SCOPE_PRESET", bent, 1);
      ScopeProcessor p;
      p.prepareToPlay(rate, block);
      unsetenv("SCOPE_PRESET");
      p.pageSlider("timebase", u"7");
      juce::AudioBuffer<float> buf(2, block);
      juce::MidiBuffer m;
      std::vector<float> before;
      scope::View viewBefore;
      int framesBefore = 0;
      for (int k = 0; k < 60; ++k) {
        buf.clear();
        p.processBlock(buf, m);
        if (k > 1 && p.picture().phosphor().frames() != framesBefore) {
          scope::CaptureSource src;
          src.rate = rate; src.capacity = static_cast<double>(ScopeProcessor::kPictureFrames); src.channels = 2;
          src.latest = [&](std::size_t n) {
            std::vector<scope::Lane> out(2, scope::Lane(n, 0.0f));
            const std::size_t have = before.size() / 2, take = std::min(n, have);
            for (std::size_t i = 0; i < take; ++i) {
              out[0][n - take + i] = before[(have - take + i) * 2];
              out[1][n - take + i] = before[(have - take + i) * 2 + 1];
            }
            return out;
          };
          const scope::Frame want = scope::capture(viewBefore, src);
          const scope::Frame& got = p.picture().frame();
          // What it asked the ring for and how short it fell, as well as what it drew.
          double off = want.channels.size() == got.channels.size() && want.length == got.length && want.asked == got.asked
                       && want.starved == got.starved ? 0 : 1;
          for (std::size_t c = 0; c < want.channels.size() && c < got.channels.size(); ++c) {
            if (want.channels[c].size() != got.channels[c].size()) { off = 1; continue; }
            for (std::size_t i = 0; i < want.channels[c].size(); ++i) off = std::fmax(off, std::fabs(want.channels[c][i] - got.channels[c][i]));
          }
          frameOff = std::fmax(frameOff, off);
          compared++;
          lastLength = got.length;
          lastAsked = got.asked;
        }
        framesBefore = p.picture().phosphor().frames();
        before = p.pictureSnapshot();
        viewBefore = p.view().capture;
      }
    }
    check("the frame the plugin draws is the page's capture of its ring as the block before left it, at 20 ms a division, sample for sample",
          frameOff == 0 && compared > 20, std::to_string(compared) + " frames, off by " + num(frameOff) + ", the window "
          + num(lastLength) + " long, asked " + num(lastAsked));
    /* The photocell switched from the page mid-run: off, its sources go and
       its reading is nought; on again from off, the loop starts - which it
       can only do if the routes are compiled again once its sources are
       there. And the Clear button leaves the grid to fill again. */
    const auto midRun = [&](bool startOff) {
      setenv("SCOPE_PRESET", bent, 1);
      auto p = std::make_unique<ScopeProcessor>();
      p->prepareToPlay(rate, block);
      unsetenv("SCOPE_PRESET");
      if (startOff) p->pageClick("photoButton");
      juce::AudioBuffer<float> buf(2, block);
      juce::MidiBuffer m;
      for (int k = 0; k < blocks; ++k) {
        if (k == blocks / 2) p->pageClick("photoButton");
        buf.clear();
        p->processBlock(buf, m);
      }
      return p;
    };
    const auto wentOff = midRun(false), cameOn = midRun(true);
    const double cameApart = most(cameOn->pictureSnapshot(), off.picture);
    check("the photocell switched off mid-run takes its sources away and reads nought; switched on from off, the loop starts",
          !wentOff->matrix().source("photo.1") && !wentOff->matrix().source("picture.bored") && wentOff->picture().pictures().photo() == 0
          && cameOn->matrix().source("photo.1") && cameApart > 0.01, "the picture apart from never on by " + num(cameApart));
    double refilled = 0, clearedNow = 0;
    {
      setenv("SCOPE_PRESET", bent, 1);
      ScopeProcessor p;
      p.prepareToPlay(rate, block);
      unsetenv("SCOPE_PRESET");
      p.pageControl("persistence", scope::Json::string(std::string_view("-1")));
      p.pageClick("clearButton");
      juce::AudioBuffer<float> buf(2, block);
      juce::MidiBuffer m;
      const auto litNow = [&] { double lit = 0; for (const float c : p.picture().phosphor().grid()) lit += c; return lit; };
      for (int k = 0; k < 2; ++k) { buf.clear(); p.processBlock(buf, m); }
      clearedNow = litNow();
      for (int k = 0; k < blocks; ++k) { buf.clear(); p.processBlock(buf, m); }
      refilled = litNow();
    }
    check("and after a Clear the grid fills again, rather than wiping every frame",
          refilled > clearedNow * 4 && refilled > looped.lit * 2, "lit " + num(clearedNow) + ", then " + num(refilled));
    /* The loop's rules: the photocell and the picture's sources are read as
       the picture's, so their pushes are bounded as one, and each holds a
       depth to its reach - half a destination's span, and boredom 0.3. */
    std::string held;
    bool loopFlags = false;
    {
      setenv("SCOPE_PRESET", bent, 1);
      ScopeProcessor p;
      p.prepareToPlay(rate, block);
      unsetenv("SCOPE_PRESET");
      p.pageRoutings("photo.1>gen.ratio@0.900;picture.bored>gen.swing@-0.900");
      juce::AudioBuffer<float> buf(2, block);
      juce::MidiBuffer m;
      for (int k = 0; k < 4; ++k) { buf.clear(); p.processBlock(buf, m); }
      held = scope::Matrix::encode(p.matrix().routings());
      const scope::ModSource* photo = p.matrix().source("photo.1");
      const scope::ModSource* round = p.matrix().source("picture.round");
      loopFlags = photo && round && photo->picture() && round->picture();
    }
    check("the photocell and the picture's sources are the loop's, and hold a depth to their reach: half, and boredom 0.3",
          loopFlags && held == "photo.1>gen.ratio@0.500;picture.bored>gen.swing@-0.300", held);
    /* The view's hands as the state keeps them: a display undoes the one
       before, the photocell's switch keeps every press, and the Clear
       button, which leaves nothing behind it, is not kept - nor does a view
       button undo the keyboard's mode, as an unknown set once would have. */
    std::string viewHands;
    {
      ScopeProcessor p;
      p.prepareToPlay(rate, block);
      for (const char* id : { "midiDyad", "photoButton", "photoButton", "dispXY", "dispYT", "clearButton" }) p.pageClick(id);
      juce::AudioBuffer<float> buf(2, block);
      juce::MidiBuffer m;
      p.processBlock(buf, m);
      const auto decoded = scope::decodeSetup(p.pageState().code);
      const scope::Json* hands = decoded.kind == scope::DecodedSetup::Kind::Read ? decoded.setup.get("pluginHands") : nullptr;
      viewHands = hands ? scope::utf16To8(scope::jsonStringify(*hands)) : "none";
    }
    check("the view's buttons are kept as hands, a display undoing the last, every press of the photocell's switch, and no Clear",
          viewHands == "[[\"k\",\"midiDyad\"],[\"k\",\"photoButton\"],[\"k\",\"photoButton\"],[\"k\",\"dispYT\"]]", viewHands);
    const char* ellipse = "Brightness opens the ellipse";
    // The reticle put on the line the held sine draws, at the middle of the screen, by the page's drag.
    const auto centred = [](ScopeProcessor& p) { p.pageControl("photoReticle", scope::Json::string(std::string_view("0.5,0.5"))); };
    const Run heard = run(ellipse, true, blocks, centred);
    const Run unheard = run(ellipse, true, blocks, [&](ScopeProcessor& p) { centred(p); p.matrix().remove("photo.1", "gen.phase"); });
    const double opened = most(heard.r, unheard.r), sameLeft = most(heard.l, unheard.l);
    check("and the loop reaches the sound: the light turns the phase of the held sine's right channel, and leaves its left alone",
          opened > 0.05 && sameLeft < opened / 10 && heard.most > 0,
          "right apart by " + num(opened) + ", left by " + num(sameLeft) + ", reading in the second second up to " + num(heard.most));
  }

  std::printf("\n--- the sources ---\n");
  /* What the plugin plays, the left channel, for a preset and what the host
     sends; `unrouted` takes one routing away first, for the null. */
  const auto playLeft = [&](const char* preset, const std::vector<std::pair<int, juce::MidiMessage>>& played, int blocksToRun,
                            const char* unroutedFrom = nullptr, const char* unroutedTo = nullptr) {
    setenv("SCOPE_PRESET", preset, 1);
    ScopeProcessor p;
    p.prepareToPlay(rate, block);
    unsetenv("SCOPE_PRESET");
    if (unroutedFrom) p.matrix().remove(unroutedFrom, unroutedTo);
    std::vector<float> got;
    juce::AudioBuffer<float> buf(2, block);
    for (int k = 0; k < blocksToRun; ++k) {
      const int start = k * block;
      buf.clear();
      juce::MidiBuffer m;
      for (const auto& [sample, msg] : played)
        if (sample >= start && sample < start + block) m.addEvent(msg, sample - start);
      p.processBlock(buf, m);
      for (int i = 0; i < block; ++i) got.push_back(buf.getSample(0, i));
    }
    return got;
  };
  const auto apart = [](const std::vector<float>& a, const std::vector<float>& b, std::size_t from, std::size_t to) {
    double most = 0;
    for (std::size_t i = from; i < to && i < a.size() && i < b.size(); ++i) most = std::fmax(most, std::fabs(a[i] - b[i]));
    return most;
  };
  {
    /* "Wheel wah" routes the mod wheel to a band pass. Its routing is loaded
       before the wheel has moved, when there is no such source, and skipped;
       the wheel's first move at sample 20,000 has to bring it in. The same
       chord with the wheel left alone is the null - and the page itself did
       not hear the wheel here until it was fixed for this port. */
    const std::vector<std::pair<int, juce::MidiMessage>> chord { { 100, juce::MidiMessage::noteOn(1, 57, static_cast<juce::uint8>(100)) },
                                                                { 120, juce::MidiMessage::noteOn(1, 64, static_cast<juce::uint8>(100)) } };
    auto wheeled = chord;
    wheeled.push_back({ 20000, juce::MidiMessage::controllerEvent(1, 1, 127) });
    const auto still = playLeft("Wheel wah", chord, 80), moved = playLeft("Wheel wah", wheeled, 80);
    const double before = apart(still, moved, 0, 20000), after = apart(still, moved, 20480 + block, 40960);
    check("a routing from the mod wheel loaded before it moved is heard from its first move, and not a sample before",
          before == 0 && after > 0.05, "before " + num(before) + ", after " + num(after));
  }
  {
    /* "Envelope sync sweep": the envelope on the sync, each note starting
       torn and settling. Held to the core told the same, which has the
       envelope as a source too; the same notes with that routing taken away
       are the null. */
    const Played swept = playDyad(1300, false, "Envelope sync sweep");
    const auto sweptWant = dyadReference(1300, false, "Envelope sync sweep");
    const std::vector<std::pair<int, juce::MidiMessage>> dyadNotes {
      { 100, juce::MidiMessage::noteOn(1, 57, static_cast<juce::uint8>(100)) }, { 1300, juce::MidiMessage::noteOn(1, 64, static_cast<juce::uint8>(90)) },
      { 40000, juce::MidiMessage::noteOn(1, 64, static_cast<juce::uint8>(0)) }, { 48000, juce::MidiMessage::noteOff(1, 57) } };
    const auto plain = playLeft("Envelope sync sweep", dyadNotes, total / block, "env.note", "gen.sync");
    double off = 0;
    for (std::size_t i = 0; i < swept.l.size(); ++i) off = std::fmax(off, std::fabs(swept.l[i] - sweptWant[0][i]) + std::fabs(swept.r[i] - sweptWant[1][i]));
    const double unswept = apart(swept.l, plain, 0, plain.size());
    check("the note envelope as a source sweeps the sync in the plugin as in the core, sample for sample",
          off == 0 && unswept > 0.05, "off by " + num(off) + "; without the routing it differs by " + num(unswept));
  }
  {
    /* "Pendulums ring a bell": the threshold watches the level at 0.40 and
       plucks C5. The pendulums swing from the moment the preset is loaded -
       a drawing is not gated by the keys - and their picture is what the
       level reads, so it rises through the threshold within a few blocks and
       plucks once, and cannot again until the level has fallen back below
       0.35. Read a block at a time: the first firing is on the first block
       whose level is through 0.40, and the pluck is sent at that block's top.
       The same with the threshold's routing taken away is the null: it still
       fires, and nothing is sent. */
    const auto ring = [&](bool routed) {
      setenv("SCOPE_PRESET", "Pendulums ring a bell", 1);
      auto p = std::make_unique<ScopeProcessor>();
      p->prepareToPlay(rate, block);
      unsetenv("SCOPE_PRESET");
      if (!routed) p->matrix().remove("threshold", "gen.pluck");
      std::vector<double> levels;
      std::vector<int> counts;
      std::vector<Sent> sent;
      /* And the level held to the picture: the newest 2048 frames of its left
         channel, as the page is handed them before the block, followed by a
         scope::Level of the test's own. Reading the right channel, or the
         oldest of the ring, fires on the same block for this preset. */
      scope::Level own;
      double levelOff = 0;
      juce::AudioBuffer<float> buf(2, block);
      for (int k = 0; k < 94; ++k) {
        const auto picture = scopeResource("/picture.bin", *p);
        std::vector<float> lane(2048);
        const std::size_t frames = picture->data.size() / sizeof(float) / 2;
        for (std::size_t i = 0; i < lane.size(); ++i)
          std::memcpy(&lane[i], picture->data.data() + ((frames - lane.size() + i) * 2) * sizeof(float), sizeof(float));
        own.update(lane.data(), lane.size(), k == 0 ? 0 : 1000.0 * block / rate);
        buf.clear();
        juce::MidiBuffer m;
        p->processBlock(buf, m);
        levelOff = std::fmax(levelOff, std::fabs(p->level() - own.value()));
        levels.push_back(p->level());
        counts.push_back(p->thresholdCount());
        for (const auto event : m) sent.push_back({ k * block + event.samplePosition, event.data[0], event.data[1], event.data[2] });
      }
      return std::make_tuple(levels, counts, ons(sent), levelOff);
    };
    const auto [levels, counts, on, levelOff] = ring(true);
    const auto [levelsU, countsU, onU, levelOffU] = ring(false);
    const auto first = static_cast<std::size_t>(std::find(counts.begin(), counts.end(), 1) - counts.begin());
    const auto through = static_cast<std::size_t>(std::find_if(levels.begin(), levels.end(), [](double l) { return l >= 0.4; }) - levels.begin());
    check("the pendulums' level rising through the threshold plucks C5 at the top of the block it gets there, once; unrouted, it fires and sends nothing",
          first < counts.size() && first == through && first > 0 && on.size() == 1 && on[0].b == 72
          && on[0].sample == static_cast<int>(first) * block && counts.back() == 1 && countsU == counts && onU.empty()
          && levelOff == 0 && levels[20] > 0.1,
          "fired in block " + std::to_string(first) + ", the level through 0.40 in block " + std::to_string(through) + ", "
          + std::to_string(on.size()) + " plucked" + (on.empty() ? "" : " at " + std::to_string(on[0].sample)) + "; unrouted "
          + std::to_string(onU.size()) + " sent, " + std::to_string(countsU.back()) + " fired; the level off the picture's by " + num(levelOff));
  }

  std::printf("\n--- the hearing ---\n");
  {
    /* "Brightness swirls it": the hearing's brightness on the plane's twist.
       ("Brightness adds points" was the first choice, and showed nothing: the
       star's points are whole, and a brightness of 0.23 held to the
       picture's reach of a half adds less than half a point.) Read a block at a time and held to a scope::HearingSources of
       the test's own, stepped over the picture the page would be handed -
       the newest 4096 frames, left as the trigger's lane and the pair for the
       width - with the held key as its pitch: every value the same, exactly.
       And heard: the same with the routing taken away is the null. */
    const auto listen = [&](bool routed) {
      setenv("SCOPE_PRESET", "Brightness swirls it", 1);
      auto p = std::make_unique<ScopeProcessor>();
      p->prepareToPlay(rate, block);
      unsetenv("SCOPE_PRESET");
      if (!routed) p->matrix().remove("hear.bright", "gen.twist");
      scope::Matrix ownMatrix;
      scope::HearingSources own(ownMatrix);
      own.hears(true);
      double off = 0;
      std::vector<float> out;
      juce::AudioBuffer<float> buf(2, block);
      for (int k = 0; k < 94; ++k) {
        const auto picture = scopeResource("/picture.bin", *p);
        const std::size_t frames = picture->data.size() / sizeof(float) / 2;
        std::vector<float> l(scope::kHearN), r(scope::kHearN);
        for (std::size_t i = 0; i < l.size(); ++i) {
          std::memcpy(&l[i], picture->data.data() + ((frames - l.size() + i) * 2) * sizeof(float), sizeof(float));
          std::memcpy(&r[i], picture->data.data() + ((frames - l.size() + i) * 2 + 1) * sizeof(float), sizeof(float));
        }
        const double now = 1000.0 * k * block / rate;
        own.setNow(now);
        own.step(ownMatrix, true, l.data(), l.data(), r.data(), l.size(), rate, k == 0 ? 0 : 1000.0 * block / rate,
                 k * block > 100 ? std::optional<double>(scope::midiHz(57)) : std::nullopt, now);
        buf.clear();
        juce::MidiBuffer m;
        if (k == 0) m.addEvent(juce::MidiMessage::noteOn(1, 57, static_cast<juce::uint8>(100)), 100);
        p->processBlock(buf, m);
        for (int i = 0; i < block; ++i) out.push_back(buf.getSample(0, i));
        const auto& a = p->hearing();
        const auto& b = own.hearing();
        off = std::fmax(off, std::fabs(a.bright - b.bright) + std::fabs(a.pitch - b.pitch) + std::fabs(a.width - b.width)
                             + std::fabs(a.flux - b.flux) + std::fabs(a.bands[0] - b.bands[0]) + std::fabs(a.bands[1] - b.bands[1])
                             + std::fabs(a.bands[2] - b.bands[2]) + std::fabs(a.bands[3] - b.bands[3]));
      }
      return std::make_tuple(off, out, p->hearing().bright, p->hearing().pitch);
    };
    const auto [off, routed, bright, pitch] = listen(true);
    const auto [offU, plain, brightU, pitchU] = listen(false);
    const double heard = apart(routed, plain, 0, routed.size());
    check("the hearing reads the picture as the page would, block by block, the held A3 its pitch; and brightness on the twist is heard",
          off == 0 && bright > 0.1 && std::fabs(pitch - std::log2(220 / scope::kPitchRef) / 2) < 1e-9 && heard > 0.05,
          "off by " + num(off) + ", brightness " + num(bright) + ", pitch " + num(pitch) + "; without the routing it differs by " + num(heard));
  }
  {
    /* "Hits restart the pendulums": the onset on Swing again. What it hears
       is the generator it would strike, so the routing is refused - every
       strike would be the next onset - and the pendulums play as if it were
       not there, though the onset fires. */
    const std::vector<std::pair<int, juce::MidiMessage>> held { { 100, juce::MidiMessage::noteOn(1, 57, static_cast<juce::uint8>(110)) } };
    const auto routed = playLeft("Hits restart the pendulums", held, 94);
    const auto plain = playLeft("Hits restart the pendulums", held, 94, "hear.onset", "gen.reswing");
    setenv("SCOPE_PRESET", "Hits restart the pendulums", 1);
    ScopeProcessor p;
    p.prepareToPlay(rate, block);
    unsetenv("SCOPE_PRESET");
    juce::AudioBuffer<float> buf(2, block);
    for (int k = 0; k < 94; ++k) {
      buf.clear();
      juce::MidiBuffer m;
      if (k == 0) m.addEvent(juce::MidiMessage::noteOn(1, 57, static_cast<juce::uint8>(110)), 100);
      p.processBlock(buf, m);
    }
    check("an onset hearing the generator it would strike is refused it: the pendulums play as without the routing, though it fires",
          apart(routed, plain, 0, routed.size()) == 0 && p.hearing().onset.count > 0,
          std::to_string(p.hearing().onset.count) + " onsets; apart by " + num(apart(routed, plain, 0, routed.size())));
  }

  std::printf("\n--- the host's parameters, and the state ---\n");
  {
    /* Eight parameters, each a slider of the panel in its units, read back
       from the setup loaded: "Stretched echoes" has its echo at 45, the
       level and the cutoff at the page's defaults, the macros at nought. */
    setenv("SCOPE_PRESET", "Stretched echoes", 1);
    ScopeProcessor p;
    p.prepareToPlay(rate, block);
    unsetenv("SCOPE_PRESET");
    std::string names;
    for (std::size_t i = 0; i < ScopeProcessor::kKnobs.size(); ++i) names += (i ? ", " : "") + p.knob(i)->name.toStdString();
    check("eight parameters for the host, each one of the panel's sliders, read back from the setup it loads",
          p.getParameters().size() == 8 && names == "Macro 1, Macro 2, Macro 3, Macro 4, Morph, Level, Cutoff, Echo"
          && p.knob(7)->get() == 45 && p.knob(5)->get() == 55 && p.knob(6)->get() == 667 && p.knob(0)->get() == 0,
          names + "; echo " + num(p.knob(7)->get()) + ", level " + num(p.knob(5)->get()) + ", cutoff " + num(p.knob(6)->get()));
  }
  /* "Brighten, grit, space, swirl" has a routing from each macro. Automated
     from block 20 - Macro 1 to full, the cutoff from 480 to 900 - each is
     heard from that block and not a sample before; the same unautomated is
     the null. */
  const auto automated = [&](int knobIndex, float value) {
    setenv("SCOPE_PRESET", "Brighten, grit, space, swirl", 1);
    ScopeProcessor p;
    p.prepareToPlay(rate, block);
    unsetenv("SCOPE_PRESET");
    std::vector<float> got;
    juce::AudioBuffer<float> buf(2, block);
    for (int k = 0; k < 60; ++k) {
      if (k == 20 && knobIndex >= 0) p.knob(static_cast<std::size_t>(knobIndex))->setValueNotifyingHost(p.knob(static_cast<std::size_t>(knobIndex))->convertTo0to1(value));
      buf.clear();
      juce::MidiBuffer m;
      if (k == 0) { m.addEvent(juce::MidiMessage::noteOn(1, 57, static_cast<juce::uint8>(100)), 100); m.addEvent(juce::MidiMessage::noteOn(1, 64, static_cast<juce::uint8>(100)), 120); }
      p.processBlock(buf, m);
      for (int i = 0; i < block; ++i) got.push_back(buf.getSample(0, i));
    }
    return std::make_pair(got, std::make_pair(p.slider("macro1"), p.slider("vcfCut")));
  };
  {
    const auto [still, stillSliders] = automated(-1, 0);
    const auto [macro, macroSliders] = automated(0, 100);
    const auto [cutoff, cutoffSliders] = automated(6, 900);
    check("automating Macro 1 or the cutoff is heard from the block it is moved in, and not a sample before",
          apart(still, macro, 0, 20 * block) == 0 && apart(still, macro, 20 * block, still.size()) > 0.02
          && apart(still, cutoff, 0, 20 * block) == 0 && apart(still, cutoff, 20 * block, still.size()) > 0.02
          && macroSliders.first == 100 && cutoffSliders.second == 900,
          "macro apart by " + num(apart(still, macro, 20 * block, still.size())) + ", cutoff by " + num(apart(still, cutoff, 20 * block, still.size()))
          + "; sliders " + num(macroSliders.first) + ", " + num(cutoffSliders.second));
  }
  {
    /* The state round trip. One plugin loads "Brighten, grit, space, swirl",
       has Macro 2 and the echo moved by the host and learns the mod wheel;
       its state, handed to a fresh plugin before it is prepared, is what
       that one loads instead of its own preset. Both then play the same
       notes: the same sound, sample for sample, the same parameters, the
       wheel learned. The fresh plugin without the state is the null. */
    const auto play = [&](ScopeProcessor& p, bool tweak) {
      std::vector<float> got;
      juce::AudioBuffer<float> buf(2, block);
      for (int k = 0; k < 80; ++k) {
        if (k == 0 && tweak) {
          p.knob(1)->setValueNotifyingHost(p.knob(1)->convertTo0to1(70));
          p.knob(7)->setValueNotifyingHost(p.knob(7)->convertTo0to1(30));
        }
        buf.clear();
        juce::MidiBuffer m;
        if (k == 0 && tweak) m.addEvent(juce::MidiMessage::controllerEvent(1, 1, 0), 10);
        if (k == 10) { m.addEvent(juce::MidiMessage::noteOn(1, 60, static_cast<juce::uint8>(100)), 50); m.addEvent(juce::MidiMessage::noteOn(1, 67, static_cast<juce::uint8>(90)), 70); }
        if (k == 50) m.addEvent(juce::MidiMessage::noteOff(1, 60), 0);
        p.processBlock(buf, m);
        if (k >= 10) for (int i = 0; i < block; ++i) got.push_back(buf.getSample(0, i));
      }
      return got;
    };
    setenv("SCOPE_PRESET", "Brighten, grit, space, swirl", 1);
    ScopeProcessor a;
    a.prepareToPlay(rate, block);
    unsetenv("SCOPE_PRESET");
    const auto heardA = play(a, true);
    juce::MemoryBlock state;
    a.getStateInformation(state);
    ScopeProcessor b, none;
    b.setStateInformation(state.getData(), static_cast<int>(state.getSize()));
    b.prepareToPlay(rate, block);
    const float prepared = b.knob(1)->get();  // loaded by prepareToPlay itself, not left for the first block
    none.prepareToPlay(rate, block);
    const auto heardB = play(b, false), heardNone = play(none, false);
    bool same = true;
    for (std::size_t i = 0; i < ScopeProcessor::kKnobs.size(); ++i) same = same && a.knob(i)->get() == b.knob(i)->get();
    check("a state handed to a fresh plugin is the setup it loads: the same sound, the same parameters, the wheel learned",
          apart(heardA, heardB, 0, heardA.size()) == 0 && apart(heardA, heardNone, 0, heardA.size()) > 0.02 && same
          && b.knob(1)->get() == 70 && b.knob(7)->get() == 30 && b.learned() == 1 && none.learned() == 0 && state.getSize() > 20
          && prepared == 70,
          std::to_string(state.getSize()) + " bytes; apart by " + num(apart(heardA, heardB, 0, heardA.size())) + ", from one without it by "
          + num(apart(heardA, heardNone, 0, heardA.size())) + "; learned " + std::to_string(b.learned()));
    /* A parameter applies when the host moves it, and not again: the slider
       moved since by something else - the morph, or a hand once the page is
       the plugin's face - stays where it was put. */
    {
      ScopeProcessor d;
      d.prepareToPlay(rate, block);
      juce::AudioBuffer<float> held(2, block);
      juce::MidiBuffer none2;
      d.knob(5)->setValueNotifyingHost(d.knob(5)->convertTo0to1(100));
      d.processBlock(held, none2);
      const double moved = d.slider("amp");
      d.moveSlider("amp", 20);
      d.processBlock(held, none2);
      check("a parameter applies when the host moves it and not again: the slider moved since stays where it was put",
            moved == 100 && d.slider("amp") == 20, num(moved) + ", then " + num(d.slider("amp")));
    }
    /* And handed over while it plays: loaded at the top of the next block,
       the parameters following. */
    ScopeProcessor c;
    c.prepareToPlay(rate, block);
    juce::AudioBuffer<float> buf(2, block);
    juce::MidiBuffer m;
    c.processBlock(buf, m);
    const float before = c.knob(1)->get();
    c.setStateInformation(state.getData(), static_cast<int>(state.getSize()));
    const float waiting = c.knob(1)->get();
    c.processBlock(buf, m);
    check("a state handed over while it plays is loaded at the next block's top, and its parameters follow",
          before == 0 && waiting == 0 && c.knob(1)->get() == 70 && c.knob(7)->get() == 30,
          num(before) + ", " + num(waiting) + ", then " + num(c.knob(1)->get()));
  }

  std::printf("\n--- the page as the plugin's face ---\n");
  {
    /* A slider moved on the page waits for the next block's top, then is a
       hand on that slider: the same sound, sample for sample, as the same
       move made there directly, and the host's parameter for it follows.
       The state the page is shown has it, without counting it as the host's,
       so the page does not apply its own move back to itself; a parameter
       the host moves counts. */
    const auto played = [&](int how) {
      setenv("SCOPE_PRESET", "Brighten, grit, space, swirl", 1);
      auto p = std::make_unique<ScopeProcessor>();
      p->prepareToPlay(rate, block);
      unsetenv("SCOPE_PRESET");
      std::vector<float> got;
      juce::AudioBuffer<float> buf(2, block);
      double waiting = 0;
      ScopeProcessor::PageState before, after;
      for (int k = 0; k < 60; ++k) {
        if (k == 20) {
          before = p->pageState();
          if (how == 1) { p->pageSlider("vcfCut", u"900"); waiting = p->slider("vcfCut"); }
          if (how == 2) p->moveSlider("vcfCut", 900);
        }
        buf.clear();
        juce::MidiBuffer m;
        if (k == 0) { m.addEvent(juce::MidiMessage::noteOn(1, 57, static_cast<juce::uint8>(100)), 100); m.addEvent(juce::MidiMessage::noteOn(1, 64, static_cast<juce::uint8>(100)), 120); }
        p->processBlock(buf, m);
        if (k == 20) after = p->pageState();
        for (int i = 0; i < block; ++i) got.push_back(buf.getSample(0, i));
      }
      return std::make_tuple(got, waiting, before, after, std::move(p));
    };
    auto [paged, waiting, before, after, p] = played(1);
    auto [direct, w2, b2, a2, q] = played(2);
    auto [still, w3, b3, a3, r] = played(0);
    const auto decoded = scope::decodeSetup(after.code);
    const scope::Json* moved = decoded.kind == scope::DecodedSetup::Kind::Read ? decoded.setup.get("pluginHands") : nullptr;
    const bool says = moved && scope::utf16To8(scope::jsonStringify(*moved)) == "[[\"s\",\"vcfCut\",\"900\"]]";
    check("a slider moved on the page is the same move at the next block's top, sample for sample, its parameter following",
          apart(paged, direct, 0, paged.size()) == 0 && apart(paged, still, 20 * block, paged.size()) > 0.02 && waiting == 480
          && p->knob(6)->get() == 900,
          "apart by " + num(apart(paged, direct, 0, paged.size())) + ", from unmoved by " + num(apart(paged, still, 20 * block, paged.size()))
          + "; before the block " + num(waiting) + ", cutoff parameter " + num(p->knob(6)->get()));
    check("and the state the page is shown carries it, not counted as the host's; a parameter the host moves is counted",
          says && after.version == before.version && after.code != before.code && before.version >= 1,
          "version " + std::to_string(before.version) + " then " + std::to_string(after.version) + (says ? ", vcfCut at 900 in it" : ", not in it"));
    const int was = p->pageState().version;
    p->knob(0)->setValueNotifyingHost(p->knob(0)->convertTo0to1(60));
    juce::AudioBuffer<float> buf(2, block);
    juce::MidiBuffer none;
    p->processBlock(buf, none);
    check("a parameter the host moves is counted as the host's, for the page to apply",
          p->pageState().version == was + 1, std::to_string(was) + " then " + std::to_string(p->pageState().version));
  }
  {
    /* A setup loaded on the page - here "Wah"'s, as its code - is loaded in
       the plugin at the next block's top, as the plugin loads a preset: its
       parameters read back from it, and not counted as the host's. A code
       that does not read is refused and nothing is queued. */
    ScopeProcessor p;
    p.prepareToPlay(rate, block);
    const int was = p.pageState().version;
    const auto code = scope::encodeSetup(scope::findPreset("Wah")->setup);
    const bool refused = !p.pageSetup("not a code");
    const bool took = code && p.pageSetup(*code);
    const double before = p.slider("vcfCut");
    juce::AudioBuffer<float> buf(2, block);
    juce::MidiBuffer none;
    p.processBlock(buf, none);
    setenv("SCOPE_PRESET", "Wah", 1);
    ScopeProcessor wah;
    wah.prepareToPlay(rate, block);
    unsetenv("SCOPE_PRESET");
    bool same = true;
    for (std::size_t i = 0; i < ScopeProcessor::kKnobs.size(); ++i) same = same && p.knob(i)->get() == wah.knob(i)->get();
    check("a setup loaded on the page is loaded at the next block's top as a preset is, its parameters following; a bad code is refused",
          refused && took && before == 667 && p.slider("vcfCut") == wah.slider("vcfCut") && p.slider("vcfCut") != 667 && same
          && p.pageState().version == was,
          "cutoff " + num(before) + " then " + num(p.slider("vcfCut")) + " (Wah's " + num(wah.slider("vcfCut")) + "); version "
          + std::to_string(was) + " then " + std::to_string(p.pageState().version));
  }
  {
    /* A menu, a switch and a button on the page wait for the next block's
       top like a slider, and are each the page's handler there; what the
       plugin does not know - a menu of the view, or no control at all - does
       nothing and is not kept. The state carries them, in order, and a fresh
       plugin given it plays the same, sample for sample, where one without
       it does not. */
    const auto play = [&](ScopeProcessor& p, bool hands) {
      std::vector<float> got;
      juce::AudioBuffer<float> buf(2, block);
      for (int k = 0; k < 60; ++k) {
        if (k == 0 && hands) {
          p.pageControl("shape", scope::Json::string(std::string_view("square")));
          p.pageControl("delayPingPong", scope::Json::boolean(true));
          p.pageClick("tuneEqual");
          p.pageControl("spectroSpan", scope::Json::string(std::string_view("30")));
          p.pageControl("nothing", scope::Json::string(std::string_view("x")));
          p.pageClick("nothing");
        }
        buf.clear();
        juce::MidiBuffer m;
        if (k == 2) { m.addEvent(juce::MidiMessage::noteOn(1, 57, static_cast<juce::uint8>(100)), 10); m.addEvent(juce::MidiMessage::noteOn(1, 61, static_cast<juce::uint8>(100)), 30); }
        p.processBlock(buf, m);
        if (k >= 2) for (int i = 0; i < block; ++i) got.push_back(buf.getSample(0, i));
      }
      return got;
    };
    ScopeProcessor a;
    a.prepareToPlay(rate, block);
    const std::string shapeBefore = a.tone().shapeName;
    const int was = a.pageState().version;
    const auto heardA = play(a, true);
    const auto decoded = scope::decodeSetup(a.pageState().code);
    const scope::Json* hands = decoded.kind == scope::DecodedSetup::Kind::Read ? decoded.setup.get("pluginHands") : nullptr;
    const std::string kept = hands ? scope::utf16To8(scope::jsonStringify(*hands)) : "none";
    juce::MemoryBlock state;
    a.getStateInformation(state);
    ScopeProcessor b, none;
    b.setStateInformation(state.getData(), static_cast<int>(state.getSize()));
    b.prepareToPlay(rate, block);
    none.prepareToPlay(rate, block);
    const auto heardB = play(b, false), heardNone = play(none, false);
    check("a menu, a switch and a button on the page are their handlers in the plugin, and what it does not know is not kept",
          shapeBefore != "square" && a.tone().shapeName == "square" && a.tone().delayPingPong && !a.tone().just
          && kept == "[[\"c\",\"shape\",\"square\"],[\"c\",\"delayPingPong\",true],[\"k\",\"tuneEqual\"]]"
          && a.pageState().version == was,
          "shape " + shapeBefore + " then " + a.tone().shapeName + "; kept " + kept);
    check("and the state carries them: a fresh plugin given it plays the same, sample for sample, and one without it does not",
          apart(heardA, heardB, 0, heardA.size()) == 0 && apart(heardA, heardNone, 0, heardA.size()) > 0.02 && b.tone().shapeName == "square"
          && b.tone().delayPingPong && !b.tone().just,
          "apart by " + num(apart(heardA, heardB, 0, heardA.size())) + ", from one without it by " + num(apart(heardA, heardNone, 0, heardA.size())));
  }
  {
    /* A control moved twice is kept once, at its latest. But the keyboard's
       drive is the kind's chosen at the time, so a drive between two kinds
       keeps its place: the solid driven and the waveform not, both come back.
       Kept as the latest alone, the solid's would have been lost. */
    ScopeProcessor p;
    p.prepareToPlay(rate, block);
    p.pageControl("planeKaleido", scope::Json::string(std::string_view("6")));
    p.pageControl("planeKaleido", scope::Json::string(std::string_view("3")));
    p.pageControl("genMode", scope::Json::string(std::string_view("wireframe")));
    p.pageControl("midiDrive", scope::Json::boolean(true));
    p.pageControl("genMode", scope::Json::string(std::string_view("wave")));
    p.pageControl("midiDrive", scope::Json::boolean(false));
    p.pageClick("tuneJust");
    p.pageClick("tuneEqual");  // the same set of buttons: the later is kept alone
    juce::AudioBuffer<float> buf(2, block);
    juce::MidiBuffer none;
    p.processBlock(buf, none);
    juce::MemoryBlock state;
    p.getStateInformation(state);
    ScopeProcessor q;
    q.setStateInformation(state.getData(), static_cast<int>(state.getSize()));
    q.prepareToPlay(rate, block);
    const auto decoded = scope::decodeSetup(p.pageState().code);
    const scope::Json* hands = decoded.kind == scope::DecodedSetup::Kind::Read ? decoded.setup.get("pluginHands") : nullptr;
    const std::size_t count = hands && hands->type == scope::Json::Type::Array ? hands->a.size() : 0;
    check("a control moved twice is kept once, a button once for its set, and the drive kept in its place between the kinds: all come back",
          p.tone().planeKaleido == 3 && q.tone().planeKaleido == 3 && count == 6 && p.keys().drive[3] && !p.keys().drive[0]
          && q.keys().drive == p.keys().drive && q.tone().modeName == "wave" && !q.tone().just,
          std::to_string(count) + " kept; the solid driven " + (q.keys().drive[3] ? "yes" : "no") + ", the waveform " + (q.keys().drive[0] ? "yes" : "no"));
    // And a setup loaded starts the list again: what was done to the last one is not done to it.
    const auto code = scope::encodeSetup(scope::findPreset("Wah")->setup);
    if (code) p.pageSetup(*code);
    p.processBlock(buf, none);
    const auto after = scope::decodeSetup(p.pageState().code);
    check("a setup loaded starts the list of hands again",
          after.kind == scope::DecodedSetup::Kind::Read && !after.setup.get("pluginHands") && p.tone().planeKaleido == 0,
          after.kind == scope::DecodedSetup::Kind::Read && after.setup.get("pluginHands") ? "still listed" : "");
  }
  {
    /* The routings as an edit on the page left them, every digit of the depth
       kept, where a setup code's routings keep three places. */
    ScopeProcessor p;
    p.prepareToPlay(rate, block);
    p.pageRoutings("lfo1>gen.freq@0.123456789012345");
    juce::AudioBuffer<float> buf(2, block);
    juce::MidiBuffer none;
    p.processBlock(buf, none);
    juce::MemoryBlock state;
    p.getStateInformation(state);
    ScopeProcessor q;
    q.setStateInformation(state.getData(), static_cast<int>(state.getSize()));
    q.prepareToPlay(rate, block);
    const auto& r = p.matrix().routings();
    const auto& rq = q.matrix().routings();
    check("the routings edited on the page are the plugin's, every digit of the depth kept, and saved so",
          r.size() == 1 && r[0].amount == 0.123456789012345 && rq.size() == 1 && rq[0].amount == 0.123456789012345 && rq[0].destId == "gen.freq",
          std::to_string(r.size()) + " routing" + (r.empty() ? "" : ", depth " + scope::jsNumberToString(r[0].amount))
          + (rq.empty() ? "; none saved" : ", saved " + scope::jsNumberToString(rq[0].amount)));
  }
  {
    /* A state saved before the menus reached the plugin listed its sliders
       as "id=value;..." in `pluginSliders`. It still loads, and is saved
       again in the list that replaced it. */
    scope::Json old = scope::findPreset("Harmonic tone")->setup;
    old.set("pluginSliders", scope::Json::string(std::string_view("vcfCut=900;amp=30")));
    const auto code = scope::encodeSetup(old);
    ScopeProcessor p;
    if (code) p.setStateInformation(code->data(), static_cast<int>(code->size()));
    p.prepareToPlay(rate, block);
    const auto decoded = scope::decodeSetup(p.pageState().code);
    const bool gone = decoded.kind == scope::DecodedSetup::Kind::Read && !decoded.setup.get("pluginSliders");
    const scope::Json* hands = decoded.kind == scope::DecodedSetup::Kind::Read ? decoded.setup.get("pluginHands") : nullptr;
    const std::string kept = hands ? scope::utf16To8(scope::jsonStringify(*hands)) : "none";
    check("a state saved with the old list of sliders loads them, and is saved in the new list",
          p.slider("vcfCut") == 900 && p.slider("amp") == 30 && gone
          && kept == "[[\"s\",\"vcfCut\",\"900\"],[\"s\",\"amp\",\"30\"]]",
          "cutoff " + num(p.slider("vcfCut")) + ", amp " + num(p.slider("amp")) + "; " + kept);
  }
  {
    /* With the layers on, the B button on the page puts layer B on the
       plugin's panel as on the page's, so a slider and a menu moved there are
       B's; A's stay where they were. And it is kept: a fresh plugin given the
       state has B as it was left, and A. Without the button, the same hands
       are A's - the null. */
    const auto layered = [&](bool chooseB) {
      auto p = std::make_unique<ScopeProcessor>();
      p->prepareToPlay(rate, block);
      p->pageClick("midiPoly");
      p->pageControl("midiLayers", scope::Json::string(std::string_view("layer")));
      if (chooseB) p->pageClick("midiEditB");
      p->pageSlider("amp", u"80");
      p->pageControl("shape", scope::Json::string(std::string_view("square")));
      juce::AudioBuffer<float> buf(2, block);
      juce::MidiBuffer none;
      p->processBlock(buf, none);
      return p;
    };
    auto withB = layered(true), withA = layered(false);
    juce::MemoryBlock state;
    withB->getStateInformation(state);
    ScopeProcessor q;
    q.setStateInformation(state.getData(), static_cast<int>(state.getSize()));
    q.prepareToPlay(rate, block);
    const auto& a = withB->tone();
    check("with the layers on, B chosen on the page puts B on the plugin's panel: a slider and a menu moved there are B's",
          withB->toneB().amp == 0.8 && withB->toneB().shapeName == "square" && a.amp == 0.55 && a.shapeName != "square"
          && withB->slider("amp") == 80 && withA->tone().amp == 0.8 && withA->toneB().amp != 0.8,
          "B " + num(withB->toneB().amp) + " " + withB->toneB().shapeName + ", A " + num(a.amp) + " " + a.shapeName
          + "; without the button A " + num(withA->tone().amp));
    check("and a fresh plugin given the state has B as it was left, on its panel, and A",
          q.toneB().amp == 0.8 && q.toneB().shapeName == "square" && q.tone().amp == 0.55 && q.slider("amp") == 80,
          "B " + num(q.toneB().amp) + ", A " + num(q.tone().amp) + ", panel " + num(q.slider("amp")));
  }
  {
    /* LFO 2's rate, a slider made when LFO 2 is chosen; and the fade, which
       the page keeps in its own storage and sends whole. Both are kept. */
    ScopeProcessor p;
    p.prepareToPlay(rate, block);
    const double before = p.lfoRate(1);
    p.pageSlider("lfoRate1", u"300");
    p.pageFade(R"({"mode":"both","envs":[{"delay":0.25,"attack":1.5,"attackMid":0.7,"decay":0.4,"decayMid":0.3,"sustain":0.6,)"
               R"("release":3,"releaseMid":0.2,"restart":true,"loop":false},{"attack":0.5}]})");
    p.pageFade("not json");
    juce::AudioBuffer<float> buf(2, block);
    juce::MidiBuffer none;
    p.processBlock(buf, none);
    juce::MemoryBlock state;
    p.getStateInformation(state);
    ScopeProcessor q;
    q.setStateInformation(state.getData(), static_cast<int>(state.getSize()));
    q.prepareToPlay(rate, block);
    const auto& e = p.matrix().fadeEnvelope(0);
    check("LFO 2's rate moved on the page is LFO 2's in the plugin, and kept",
          before == 0.5 && p.lfoRate(1) == 3 && q.lfoRate(1) == 3, num(before) + " then " + num(p.lfoRate(1)) + ", kept " + num(q.lfoRate(1)));
    check("the fade sent from the page is the plugin's, both layers' envelopes, and kept; what does not read is not",
          p.matrix().fadeMode() == scope::FadeMode::Both && e.attack == 1.5 && e.sustain == 0.6 && e.restart
          && p.matrix().fadeEnvelope(1).attack == 0.5 && p.matrix().fadeEnvelope(1).release == 2
          && q.matrix().fadeMode() == scope::FadeMode::Both && q.matrix().fadeEnvelope(0).attack == 1.5,
          "attack " + num(e.attack) + ", B's " + num(p.matrix().fadeEnvelope(1).attack) + "; kept " + num(q.matrix().fadeEnvelope(0).attack));
  }

  std::printf("\n--- the band split ---\n");
  {
    /* The host's input split into the page's four bands (5j): 60 Hz and
       2 kHz together, the one in the Low band and the other in the High mid,
       each far enough from the other's crossover that a band soloed is the
       one tone and not the other. How often the output, or a served lane,
       rises through nought in a second says which tone it is. */
    const auto duo = [&](long long k) {
      const double t = static_cast<double>(k) / rate;
      return static_cast<float>(0.3 * std::sin(2 * 3.14159265358979323846 * 60 * t) + 0.3 * std::sin(2 * 3.14159265358979323846 * 2000 * t));
    };
    const auto rises = [&](const std::vector<float>& x) {
      int n = 0;
      for (std::size_t i = 1; i < x.size(); ++i) if (x[i - 1] < 0 && x[i] >= 0) ++n;
      return n * rate / static_cast<double>(x.size());
    };
    ScopeProcessor split;
    split.enableAllBuses();
    split.prepareToPlay(rate, block);
    long long at = 0;
    // A second of blocks with the duo on both inputs, the output's left kept.
    const auto run = [&](ScopeProcessor& p, int blocks) {
      std::vector<float> out;
      juce::AudioBuffer<float> buf(2, block);
      for (int b = 0; b < blocks; ++b) {
        for (int i = 0; i < block; ++i) { buf.setSample(0, i, duo(at + i)); buf.setSample(1, i, duo(at + i)); }
        juce::MidiBuffer m;
        p.processBlock(buf, m);
        for (int i = 0; i < block; ++i) out.push_back(buf.getSample(0, i));
        at += block;
      }
      return out;
    };
    const auto rms = [](const std::vector<float>& x) { double sum = 0; for (const float v : x) sum += v * v; return std::sqrt(sum / static_cast<double>(x.size())); };
    const int second = static_cast<int>(rate / block);
    split.pageClick("srcMic");
    split.pageControl("srcBands", scope::Json::string(std::u16string(u"1")));
    run(split, 8);
    const auto whole = run(split, second);
    const auto served = split.pictureServed();
    const std::size_t frames = ScopeProcessor::kPictureFrames;
    std::vector<float> low(frames), highMid(frames);
    // What is heard is the four bands summed - not the input, which second-order crossovers do not add back up to.
    double summed = served.size() == frames * 4 ? 0 : 1;
    for (std::size_t k = 0; k < frames && served.size() == frames * 4; ++k) {
      low[k] = served[k * 4]; highMid[k] = served[k * 4 + 2];
      const double sum = static_cast<double>(served[k * 4]) + served[k * 4 + 1] + served[k * 4 + 2] + served[k * 4 + 3];
      summed = std::fmax(summed, std::fabs(whole[whole.size() - frames + k] - sum));
    }
    check("the host's input split into bands: four lanes served, the Low the 60 Hz and the High mid the 2 kHz, and the four summed heard",
          split.bands() && served.size() == frames * 4 && std::abs(rises(low) - 60) < 8 && std::abs(rises(highMid) - 2000) < 30
            && summed < 1e-6 && rms(whole) > 0.15,
          num(static_cast<double>(served.size() / frames)) + " lanes; " + num(rises(low)) + " Hz and " + num(rises(highMid)) + " Hz served; "
            + "heard " + num(summed) + " from the bands summed, at " + num(rms(whole)) + " RMS to the input's 0.3");
    split.pageControl("laneMix", scope::Json::string(std::u16string(u"1,0,0,0")));
    run(split, 4);
    const auto lowHeard = run(split, second);
    split.pageControl("laneMix", scope::Json::string(std::u16string(u"0,0,1,0")));
    run(split, 4);
    const auto highHeard = run(split, second);
    check("a band soloed on the page is the band heard: the Low alone the 60 Hz, the High mid alone the 2 kHz",
          std::abs(rises(lowHeard) - 60) < 3 && std::abs(rises(highHeard) - 2000) < 10,
          num(rises(lowHeard)) + " Hz and " + num(rises(highHeard)) + " Hz");
    // A rack chosen over the split is the rack: its lanes, its generator heard, the split let go.
    {
      ScopeProcessor racked;
      racked.enableAllBuses();
      racked.prepareToPlay(rate, block);
      racked.pageClick("srcMic");
      racked.pageControl("srcBands", scope::Json::string(std::u16string(u"1")));
      run(racked, 2);
      const bool wasSplit = racked.bands();
      racked.pageControl("srcLanes", scope::Json::string(std::u16string(u"4,-1")));
      const auto rackHeard = run(racked, 4);
      check("a rack chosen over the split lets the split go: four lanes of the rack, and none of the input heard",
            wasSplit && !racked.bands() && racked.rack() == 4 && rms(rackHeard) == 0,
            std::string(wasSplit ? "split" : "whole") + " before, " + (racked.bands() ? "split" : "the rack") + " after, heard " + num(rms(rackHeard)));
    }
    // Kept in the project: a state reopened splits the input again, before anything is pressed.
    juce::MemoryBlock saved;
    split.getStateInformation(saved);
    ScopeProcessor reopened;
    reopened.enableAllBuses();
    reopened.setStateInformation(saved.getData(), static_cast<int>(saved.getSize()));
    reopened.prepareToPlay(rate, block);
    run(reopened, 2);
    const bool reopenedSplit = reopened.bands() && reopened.pictureServed().size() == frames * 4;
    split.pageClick("srcMic");
    run(split, 2);
    check("the split is kept in the project and comes back with it, and Mic is the input whole again",
          reopenedSplit && !split.bands() && split.drawsInput() && split.pictureServed().size() == frames * 2,
          std::string(reopenedSplit ? "split" : "whole") + " reopened; " + (split.bands() ? "split" : "whole") + " after Mic");
  }

  std::printf("\n--- the input ---\n");
  {
    /* The host's input bus, turned on, carrying a saw on the left and a
       triangle on the right - two signals unlike each other and unlike
       anything the generator plays, so the output says which it is. The
       page's Mic and Tone buttons choose what is drawn: the input, through
       the plane, or the generator. */
    const auto saw = [](long long k) { return static_cast<float>(0.5 * (2 * std::fmod(static_cast<double>(k), 100.0) / 100.0 - 1)); };
    const auto tri = [](long long k) { const double u = std::fmod(static_cast<double>(k), 73.0) / 73.0;
                                       return static_cast<float>(0.5 * (u < 0.5 ? 4 * u - 1 : 3 - 4 * u)); };
    struct Fed { double apart = 0, peak = 0; std::vector<float> outL; };
    // Blocks with the input in the buffer, as a host hands it over; how far the output is from the input, and how loud.
    const auto feed = [&](ScopeProcessor& p, long long& at, int blocks, const std::function<void(ScopeProcessor&, int)>& hands) {
      Fed f;
      juce::AudioBuffer<float> buf(2, block);
      for (int b = 0; b < blocks; ++b) {
        if (hands) hands(p, b);
        for (int i = 0; i < block; ++i) { buf.setSample(0, i, saw(at + i)); buf.setSample(1, i, tri(at + i)); }
        juce::MidiBuffer m;
        if (b == 0) m.addEvent(juce::MidiMessage::noteOn(1, 57, 1.0f), 0);
        p.processBlock(buf, m);
        for (int i = 0; i < block; ++i) {
          f.apart = std::fmax(f.apart, std::fabs(buf.getSample(0, i) - saw(at + i)) + std::fabs(buf.getSample(1, i) - tri(at + i)));
          f.peak = std::fmax(f.peak, std::fabs(buf.getSample(0, i)));
          f.outL.push_back(buf.getSample(0, i));
        }
        at += block;
      }
      return f;
    };
    ScopeProcessor fx;
    fx.enableAllBuses();
    fx.prepareToPlay(rate, block);
    long long at = 0;
    const Fed tone = feed(fx, at, 8, nullptr);
    check("with the input on and the generator drawn, the output is the generator's, not the input",
          !fx.drawsInput() && tone.apart > 0.3 && fx.getTotalNumInputChannels() == 2,
          "apart by " + num(tone.apart) + ", " + std::to_string(fx.getTotalNumInputChannels()) + " inputs");
    // Mic from the page: the input drawn, and heard, exactly, with nothing on the plane.
    const scope::ModSource* pitch = fx.matrix().source("hear.pitch");
    const bool loopBefore = pitch && pitch->picture();
    fx.pageClick("srcMic");
    feed(fx, at, 1, nullptr);
    const bool loopAfter = pitch && pitch->picture();
    const Fed drawn = feed(fx, at, 8, nullptr);
    const auto snapshot = fx.pictureSnapshot();
    double pictured = 0;
    for (std::size_t k = 0; k < 4096; ++k) {
      const long long i = at - 4096 + static_cast<long long>(k);
      const std::size_t s0 = (ScopeProcessor::kPictureFrames - 4096 + k) * 2;
      pictured = std::fmax(pictured, std::fabs(snapshot[s0] - saw(i)) + std::fabs(snapshot[s0 + 1] - tri(i)));
    }
    check("Mic on the page draws the input and hears it, sample for sample, left as left",
          fx.drawsInput() && drawn.apart == 0 && pictured == 0 && drawn.peak > 0.4,
          "output apart by " + num(drawn.apart) + ", picture by " + num(pictured));
    check("and what it hears is no longer a loop through its own sound: the hearing's sources are counted as loops only before",
          loopBefore && !loopAfter, std::string(loopBefore ? "loop" : "not") + " before, " + (loopAfter ? "loop" : "not") + " after");
    // Through the plane: the kaleidoscope on, the input no longer comes out as it went in.
    fx.pageControl("planeKaleido", scope::Json::string(std::u16string(u"6")));
    feed(fx, at, 1, nullptr);
    const long long from = at;
    const Fed folded = feed(fx, at, 8, nullptr);
    check("and through the plane: the kaleidoscope on, the input comes out folded", folded.apart > 0.1 && folded.peak > 0.1,
          "apart by " + num(folded.apart));
    /* Prepared again while it draws its input - a host changing its rate - it
       still draws it, and still counts what it hears as no loop. */
    {
      ScopeProcessor again2;
      again2.enableAllBuses();
      again2.prepareToPlay(rate, block);
      again2.pageClick("srcMic");
      long long k = 0;
      feed(again2, k, 2, nullptr);
      again2.prepareToPlay(rate / 2, block);
      feed(again2, k, 2, nullptr);
      const scope::ModSource* heard = again2.matrix().source("hear.pitch");
      check("prepared again while drawing its input, it still draws it and still hears no loop",
            again2.drawsInput() && heard && !heard->picture());
    }
    // The state carries the source, and a project reopened draws its input again, through the same plane.
    const auto state = fx.pageState();
    const auto decoded = scope::decodeSetup(state.code);
    const scope::Json* drawnFlag = decoded.kind == scope::DecodedSetup::Kind::Read ? decoded.setup.get("pluginInput") : nullptr;
    juce::MemoryBlock saved;
    fx.getStateInformation(saved);
    ScopeProcessor reopened;
    reopened.enableAllBuses();
    reopened.setStateInformation(saved.getData(), static_cast<int>(saved.getSize()));
    reopened.prepareToPlay(rate, block);
    long long again = from;
    const Fed second = feed(reopened, again, 8, nullptr);
    double same = second.outL.size() == folded.outL.size() ? 0 : 1;
    for (std::size_t i = 0; i < second.outL.size() && i < folded.outL.size(); ++i) same = std::fmax(same, std::fabs(second.outL[i] - folded.outL[i]));
    check("the state says the input is drawn, and the plugin reopened from it draws its input through the same plane",
          drawnFlag && drawnFlag->type == scope::Json::Type::Bool && drawnFlag->b && reopened.drawsInput() && second.apart > 0.1,
          "reopened apart from the input by " + num(second.apart));
    // Not compared sample for sample with the first: the plane's oscillators have run a different time.
    // Tone from the page: back to the generator - its held note, not the input.
    fx.pageClick("srcTone");
    feed(fx, at, 1, nullptr);
    const Fed back = feed(fx, at, 4, nullptr);
    const auto backDecoded = scope::decodeSetup(fx.pageState().code);
    check("Tone on the page draws the generator again, and the state says nothing of an input",
          !fx.drawsInput() && back.apart > 0.3 && back.peak > 0.05 && backDecoded.kind == scope::DecodedSetup::Kind::Read
          && backDecoded.setup.get("pluginInput") == nullptr, "apart from the input by " + num(back.apart));

    /* The generator's live-input modes: a figure whose rate the input's FM
       moves, against the same with the mode off, and the same with the input
       bus off. The null is the mode off, where the input must change nothing. */
    const auto played = [&](bool busOn, const char* mode) {
      ScopeProcessor p;
      if (busOn) p.enableAllBuses();
      p.prepareToPlay(rate, block);
      long long k = 0;
      return feed(p, k, 12, [&](ScopeProcessor& q, int b) {
        if (b == 0) { q.pageControl("genMode", scope::Json::string(std::u16string(u"figure")));
                      q.pageControl("inputMode", scope::Json::string(scope::utf8To16(mode))); }
      }).outL;
    };
    const auto most = [](const std::vector<float>& a, const std::vector<float>& b) {
      double m = a.size() == b.size() ? 0 : 1;
      for (std::size_t i = 0; i < a.size() && i < b.size(); ++i) m = std::fmax(m, std::fabs(a[i] - b[i]));
      return m;
    };
    const double moved = most(played(true, "1"), played(false, "1")), still = most(played(true, "0"), played(false, "0"));
    check("drawing the generator, the input reaches it: FM from the input moves the figure, and with the mode off changes nothing",
          moved > 0.05 && still == 0, "moved " + num(moved) + ", mode off " + num(still));
    /* A rack (5i), as the site's page sends one: what it hears is a loop
       through its own sound only while the trigger is on the generator's
       lane. Three lanes with the generator first; the trigger on it, then on
       the second lane, then a rack with no generator lane at all. */
    {
      ScopeProcessor rack;
      rack.prepareToPlay(rate, block);
      juce::AudioBuffer<float> buf(2, block);
      const auto run = [&](int blocks) { for (int b = 0; b < blocks; ++b) { buf.clear(); juce::MidiBuffer m; rack.processBlock(buf, m); } };
      rack.pageControl("srcLanes", scope::Json::string(std::u16string(u"3,0")));
      run(2);
      const scope::ModSource* heard = rack.matrix().source("hear.pitch");
      const bool onGenerator = heard && heard->picture();
      rack.pageClick("trigSource1");
      run(2);
      const bool onLane = heard && heard->picture();
      rack.pageControl("srcLanes", scope::Json::string(std::u16string(u"3,-1")));
      rack.pageClick("trigSource0");
      run(2);
      const bool noGenerator = heard && heard->picture();
      /* What it hears is the trigger's lane: the generator's lane, with a note
         in it, has a pitch; the plugin's empty lanes have none. And a trigger
         on the third lane holds, three lanes being there. */
      {
        ScopeProcessor pitched;
        pitched.prepareToPlay(rate, block);
        pitched.pageControl("srcLanes", scope::Json::string(std::u16string(u"3,1")));
        juce::AudioBuffer<float> b2(2, block);
        for (int b = 0; b < 40; ++b) {
          b2.clear();
          juce::MidiBuffer m;
          if (b == 0) m.addEvent(juce::MidiMessage::noteOn(1, 57, 1.0f), 0);
          if (b == 0) pitched.pageClick("trigSource1");
          pitched.processBlock(b2, m);
        }
        const double pitchOnGen = pitched.hearing().pitch, onGen = pitched.level();
        pitched.pageClick("trigSource2");
        for (int b = 0; b < 200; ++b) { b2.clear(); juce::MidiBuffer m; pitched.processBlock(b2, m); }
        const double onEmpty = pitched.level();
        check("a rack's ear reads its trigger's lane: the generator's lane, with A3 in it, has A3's pitch and a level, and a trigger on an empty third lane holds and reads silence",
              std::abs(pitchOnGen + 0.125) < 0.01 && onGen > 0.05 && pitched.view().trigSource == 2 && onEmpty < 0.001,
              "pitch " + num(pitchOnGen) + " and level " + num(onGen) + " on the generator's lane, level "
              + num(onEmpty) + " on an empty one, trigger " + num(pitched.view().trigSource));
      }
      check("a rack's trigger on the generator's lane is a loop through its own sound, on another lane or with no generator lane not",
            onGenerator && !onLane && !noGenerator && rack.picture().phosphor().grid().size() > 0,
            std::string(onGenerator ? "loop" : "not") + " on the generator, " + (onLane ? "loop" : "not") + " on a lane, "
              + (noGenerator ? "loop" : "not") + " with none");

      /* A fresh instrument a rack is made on, A3 held in it from the first
         block, run so many blocks with what is asked of it between. */
      const auto racked = [&](const char16_t* lanes, const std::function<void(ScopeProcessor&)>& then, int blocks) {
        auto p = std::make_unique<ScopeProcessor>();
        p->prepareToPlay(rate, block);
        p->pageControl("srcLanes", scope::Json::string(std::u16string(lanes)));
        then(*p);
        juce::AudioBuffer<float> b3(2, block);
        double loud = 0;
        for (int b = 0; b < blocks; ++b) {
          b3.clear();
          juce::MidiBuffer m;
          if (b == 0) m.addEvent(juce::MidiMessage::noteOn(1, 57, 1.0f), 0);
          p->processBlock(b3, m);
          for (int i = 0; i < block; ++i) loud = std::fmax(loud, std::fabs(b3.getSample(0, i)));
        }
        return std::make_pair(std::move(p), loud);
      };
      const auto grid = [](const ScopeProcessor& p) { const auto& g = p.picture().phosphor().grid(); return std::vector<float>(g.begin(), g.end()); };
      const auto lit = [](const std::vector<float>& g) { double sum = 0; for (const float c : g) sum += c; return sum; };
      const auto click = [](const char* id) { return [id](ScopeProcessor& p) { p.pageClick(id); }; };
      /* The width the ear hears is the X-Y pair's: the trigger's lane against
         the pair's other one. The generator's lane against itself is one
         signal; against an empty lane, none of it is shared. */
      {
        auto same = racked(u"3,1", [](ScopeProcessor& p) { p.pageClick("trigSource1"); p.pageControl("xyX", scope::Json::string(std::u16string(u"0")));
                                                           p.pageControl("xyY", scope::Json::string(std::u16string(u"1"))); }, 120);
        auto apart = racked(u"3,1", [](ScopeProcessor& p) { p.pageClick("trigSource1"); p.pageControl("xyX", scope::Json::string(std::u16string(u"1")));
                                                            p.pageControl("xyY", scope::Json::string(std::u16string(u"2"))); }, 120);
        const double one = same.first->hearing().width, none = apart.first->hearing().width;
        check("a rack's heard width is its X-Y pair's: the generator's lane against itself one signal, against an empty lane nothing shared",
              one > 0.9 && std::fabs(none) < 0.1 && apart.first->view().xy[1] == 2, "width " + num(one) + " and " + num(none) + ", the pair " + num(apart.first->view().xy[0]) + " and " + num(apart.first->view().xy[1]));
      }
      /* All a rack's lanes drawn, not the first two: the generator on the
         third lane is ink only a third lane can put there. And a lag asked
         for in a rack is not taken - a lane of the rack's is the second
         lane, as on the page, where lanes and the lag are one or the other. */
      {
        const auto third = racked(u"3,2", click("trigSource2"), 40), none = racked(u"3,-1", click("trigSource2"), 40);
        double apart = 0;
        const auto a = grid(*third.first), b = grid(*none.first);
        for (std::size_t i = 0; i < a.size() && i < b.size(); ++i) apart += std::fabs(a[i] - b[i]);
        check("a rack's lanes are all drawn: the generator on the third lane is ink a two-lane picture never puts there",
              apart > 1 && third.first->pictureLanes() == 3, "apart by " + num(apart) + ", " + num(third.first->pictureLanes()) + " lanes");
        const auto lagOn = [](ScopeProcessor& p) { p.pageClick("trigSource0"); p.pageSlider("lag", u"200");
                                                   p.pageControl("lagOn", scope::Json::boolean(true)); };
        const auto lagged = racked(u"2,0", lagOn, 40), plain = racked(u"2,0", click("trigSource0"), 40);
        const auto alone = [&](bool lag) {
          ScopeProcessor p;
          p.prepareToPlay(rate, block);
          if (lag) { p.pageSlider("lag", u"200"); p.pageControl("lagOn", scope::Json::boolean(true)); }
          juce::AudioBuffer<float> b3(2, block);
          for (int b = 0; b < 40; ++b) { b3.clear(); juce::MidiBuffer m; if (b == 0) m.addEvent(juce::MidiMessage::noteOn(1, 57, 1.0f), 0); p.processBlock(b3, m); }
          return grid(p);
        };
        const auto diff = [](const std::vector<float>& x, const std::vector<float>& y) {
          double d = x.size() == y.size() ? 0 : 1e9;
          for (std::size_t i = 0; i < x.size() && i < y.size(); ++i) d += std::fabs(x[i] - y[i]);
          return d;
        };
        const double inRack = diff(grid(*lagged.first), grid(*plain.first)), onPair = diff(alone(true), alone(false));
        check("a lag asked for in a rack is not taken, the second lane the rack's own; on the generator's pair the same lag moves the picture",
              inRack == 0 && lit(grid(*plain.first)) > 0 && onPair > 1, "apart by " + num(inRack) + " in the rack, " + num(onPair) + " on the pair");
      }
      /* A setup loaded over a rack keeps the rack's lanes: a setup says two
         lanes' worth of view, and the rack is still playing three - and the
         X-Y pair's menus still offer the third. */
      {
        const auto loaded = racked(u"3,1", [](ScopeProcessor& p) {
          if (const auto code = scope::encodeSetup(scope::findPreset("Wah")->setup)) p.pageSetup(*code);
          p.pageControl("xyY", scope::Json::string(std::u16string(u"2"))); }, 4);
        check("a setup loaded over a rack keeps the rack's three lanes in the view, and the pair can take the third",
              loaded.first->view().lanes == 3 && loaded.first->view().capture.channels.size() == 3 && loaded.first->view().xy[1] == 2,
              num(loaded.first->view().lanes) + " lanes, " + num(static_cast<double>(loaded.first->view().capture.channels.size())) + " rows, the pair's Y "
              + num(loaded.first->view().xy[1]));
      }
      /* A rack replaces the input, rather than sitting over it: leaving the
         rack is the generator again, and nothing in the state says input. A
         generator's lane past the rack's count is no lane, and unheard. */
      {
        const auto fromMic = racked(u"0", [](ScopeProcessor& p) {
          p.pageClick("srcMic");
          p.pageControl("srcLanes", scope::Json::string(std::u16string(u"3,1")));
          p.pageControl("srcLanes", scope::Json::string(std::u16string(u"0"))); }, 2);
        const auto decoded = scope::decodeSetup(fromMic.first->pageState().code);
        const bool says = decoded.kind == scope::DecodedSetup::Kind::Read && decoded.setup.get("pluginInput");
        check("a rack replaces the input: from Mic to a rack and out of it is the generator, and the state does not say input",
              !fromMic.first->drawsInput() && !says && fromMic.second > 0.01,
              std::string(fromMic.first->drawsInput() ? "input" : "generator") + (says ? ", the state says input" : "") + ", heard " + num(fromMic.second));
        const auto past = racked(u"3,7", click("trigSource0"), 20), within = racked(u"3,2", click("trigSource0"), 20);
        check("a generator's lane past the rack's count is none: unheard, where the third lane is heard",
              past.second == 0 && within.second > 0.01 && past.first->synthLane() == -1, "heard " + num(past.second) + " and " + num(within.second));
      }
    }
    /* One channel, as the page's worklet takes it: the stereo pair summed and
       halved. The same FM from a mono input bus carrying that mix is the same
       sound to the sample; carrying the left alone, it is not. */
    const auto monoPlayed = [&](bool mix) {
      ScopeProcessor p;
      juce::AudioProcessor::BusesLayout layout;
      layout.inputBuses.add(juce::AudioChannelSet::mono());
      layout.outputBuses.add(juce::AudioChannelSet::stereo());
      p.setBusesLayout(layout);
      p.prepareToPlay(rate, block);
      std::vector<float> outL;
      juce::AudioBuffer<float> buf(2, block);
      for (int b = 0; b < 12; ++b) {
        if (b == 0) { p.pageControl("genMode", scope::Json::string(std::u16string(u"figure")));
                      p.pageControl("inputMode", scope::Json::string(std::u16string(u"1"))); }
        buf.clear();
        for (int i = 0; i < block; ++i) {
          const long long k = static_cast<long long>(b) * block + i;
          buf.setSample(0, i, mix ? (saw(k) + tri(k)) * 0.5f : saw(k));
        }
        juce::MidiBuffer m;
        if (b == 0) m.addEvent(juce::MidiMessage::noteOn(1, 57, 1.0f), 0);
        p.processBlock(buf, m);
        for (int i = 0; i < block; ++i) outL.push_back(buf.getSample(0, i));
      }
      return std::make_pair(outL, p.getTotalNumInputChannels());
    };
    /* A mono input drawn: the one channel on both sides, as the page's insert
       makes two identical halves of a mono microphone. */
    {
      ScopeProcessor mono;
      juce::AudioProcessor::BusesLayout layout;
      layout.inputBuses.add(juce::AudioChannelSet::mono());
      layout.outputBuses.add(juce::AudioChannelSet::stereo());
      mono.setBusesLayout(layout);
      mono.prepareToPlay(rate, block);
      mono.pageClick("srcMic");
      juce::AudioBuffer<float> buf(2, block);
      double apart = 0, peak = 0;
      for (int b = 0; b < 4; ++b) {
        buf.clear();
        for (int i = 0; i < block; ++i) buf.setSample(0, i, saw(static_cast<long long>(b) * block + i));
        juce::MidiBuffer m;
        mono.processBlock(buf, m);
        if (b == 0) continue;
        for (int i = 0; i < block; ++i) {
          const float want = saw(static_cast<long long>(b) * block + i);
          apart = std::fmax(apart, std::fabs(buf.getSample(0, i) - want) + std::fabs(buf.getSample(1, i) - want));
          peak = std::fmax(peak, std::fabs(buf.getSample(1, i)));
        }
      }
      check("a mono input drawn comes out on both sides", apart == 0 && peak > 0.4, "apart by " + num(apart));
    }
    const auto mixed = monoPlayed(true), leftOnly = monoPlayed(false);
    const double asMono = most(played(true, "1"), mixed.first), asLeft = most(played(true, "1"), leftOnly.first);
    check("a stereo input reaches the generator as one channel, the pair summed and halved: a mono bus carrying that is the same sound",
          mixed.second == 1 && asMono == 0 && asLeft > 0.01, "apart by " + num(asMono) + "; the left alone, " + num(asLeft));
  }

  std::printf("\n--- the page and the picture ---\n");
  const auto page = scopeResource("/", processor);
  const std::string head = page ? std::string(reinterpret_cast<const char*>(page->data.data()), 15) : "";
  check("the page is served from inside the plugin, as HTML in UTF-8", page && page->mimeType == "text/html; charset=utf-8"
        && page->data.size() > 100000 && juce::String(head).toLowerCase().startsWith("<!doctype html"),
        page ? std::to_string(page->data.size()) + " bytes" : "none");
  check("and nothing else is: an unknown path is refused", !scopeResource("/elsewhere.js", processor));

  // ASCII throughout, with the script's own characters escaped as script and
  // the markup's as markup - read against the page as it is in the binary,
  // which is the null: that one has characters past ASCII in it.
  std::size_t wide = 0, wideInBinary = 0;
  for (const auto b : page->data) wide += static_cast<unsigned char>(b) > 127 ? 1 : 0;
  for (int i = 0; i < BinaryData::scope_htmlSize; ++i) wideInBinary += static_cast<unsigned char>(BinaryData::scope_html[i]) > 127 ? 1 : 0;
  const std::string served(reinterpret_cast<const char*>(page->data.data()), page->data.size());
  check("the page is served as pure ASCII, the script's middle dot as \\u00B7 and nothing lost",
        wide == 0 && wideInBinary > 0 && served.find("\"trigger.js \\u00B7 \"") != std::string::npos,
        std::to_string(wideInBinary) + " bytes past ASCII in the binary, " + std::to_string(wide) + " served");
  const char* mixed = "<p>\xC2\xB7</p><script>'\xE2\x88\x92\xF0\x9F\x8E\xB5'</script>\xC3\x97";
  const std::string sample = asciiPage(mixed, std::strlen(mixed));
  check("and each character in the language it stands in: an entity in markup, an escape in a script, a pair past the first plane",
        sample == "<p>&#xB7;</p><script>'\\u2212\\uD83C\\uDFB5'</script>&#xD7;", sample);

  /* The picture is the generator's picture pair, left as left: the dyad's
     right channel is a quarter-cycle on from its left, so a picture handed
     over swapped, or as the heard pair of one channel twice, is told apart. */
  const std::vector<float>& frames = midNote;
  const std::size_t n = ScopeProcessor::kPictureFrames;
  double mismatch = frames.size() == n * 2 ? 0 : 1, swapped = 0, moving = 0;
  for (std::size_t k = 0; k < n && frames.size() == n * 2; ++k) {
    const std::size_t i = midNoteEnd - n + k;
    moving = std::fmax(moving, std::fabs(expected[2][i]));
    mismatch = std::fmax(mismatch, std::fabs(frames[k * 2] - expected[2][i]) + std::fabs(frames[k * 2 + 1] - expected[3][i]));
    swapped = std::fmax(swapped, std::fabs(frames[k * 2] - expected[3][i]));
  }
  check("the picture is the last " + std::to_string(n) + " frames of the picture pair, oldest first, left as left",
        mismatch <= 0.0 && swapped > 0.1 && moving > 0.25,
        "mismatch " + num(mismatch) + ", swapped would be " + num(swapped) + ", taken at " + num(moving));

  std::printf("\n%s\n", failures ? "FAILED" : "the shell plays, serves the page, and hands it the picture");
  return failures ? 1 : 0;
}
