// The plugin's shell, run without a host or a web view: notes in, the core's
// generator's sound out, the page served, and the picture the page will draw
// carrying what was played. It prints PASS and FAIL lines in the house
// format and exits non-zero on a failure, like the web suite.
#include <algorithm>
#include <array>
#include <cmath>
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
    /* "A sine, sung" has the score on, a step a semiquaver. Its picture is the
       page's until stage 4, so it plays nothing in the plugin, but its
       playhead runs on the bar - and through a host's count-in, two beats
       before the one, it waits: a bar of minus two would be column minus
       eight, and a grid read from there. */
    struct Head : juce::AudioPlayHead {
      juce::Optional<PositionInfo> getPosition() const override {
        PositionInfo p;
        p.setBpm(120); p.setPpqPosition(ppq); p.setIsPlaying(true);
        return p;
      }
      double ppq = -2;
    } head;
    setenv("SCOPE_PRESET", "A sine, sung", 1);
    ScopeProcessor p;
    p.prepareToPlay(rate, block);
    unsetenv("SCOPE_PRESET");
    p.setPlayHead(&head);
    juce::AudioBuffer<float> buf(2, block);
    juce::MidiBuffer none;
    bool waited = true, followed = true, sentNothing = true;
    int counted = 0;
    for (int k = 0; k < 160; ++k) {
      buf.clear();
      none.clear();
      const double at = head.ppq;
      p.processBlock(buf, none);
      sentNothing = sentNothing && none.isEmpty();
      if (at < 0) waited = waited && p.score().col == -1;
      else { followed = followed && p.score().col == static_cast<int>(std::floor(at * 4 + 1e-9)) % 64; counted++; }
      head.ppq += block / rate * 2;
    }
    check("the score's playhead waits through a host's count-in and then follows its bar, a column a semiquaver; with no picture it sends nothing",
          p.score().on && waited && followed && counted > 40 && sentNothing,
          "col " + std::to_string(p.score().col) + " at the end, " + std::to_string(counted) + " blocks after the one");
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
