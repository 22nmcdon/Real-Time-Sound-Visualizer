// The plugin's shell, run without a host or a web view: notes in, the core's
// generator's sound out, the page served, and the picture the page will draw
// carrying what was played. It prints PASS and FAIL lines in the house
// format and exits non-zero on a failure, like the web suite.
#include <array>
#include <cmath>
#include <cstdlib>
#include <cstdio>
#include <cstring>
#include <string>
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
