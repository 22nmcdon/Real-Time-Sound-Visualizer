// The plugin's shell, run without a host or a web view: notes in, the core's
// generator's sound out, the page served, and the picture the page will draw
// carrying what was played. It prints PASS and FAIL lines in the house
// format and exits non-zero on a failure, like the web suite.
#include <array>
#include <cmath>
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
  const auto playDyad = [&](int second, bool routed = false) {
    ScopeProcessor p;
    p.prepareToPlay(rate, block);
    if (routed) { p.matrix().add("lfo1", "gen.freq", 0.5); p.matrix().add("midi.key", "gen.amp", 0.6); }
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
  const auto dyadReference = [&](int second, bool routed = false) {
    std::vector<scope::Lfo> lfos(2);
    lfos[0].rate = 0.2; lfos[0].depth = 0.5; lfos[1].rate = 0.5; lfos[1].depth = 0.3;
    scope::Generator core(rate, scope::slot::Used, lfos);
    scope::GeneratorNotes notes(core);
    scope::Keyboard keys(notes);
    scope::Matrix matrix;
    scope::CoreSources sources(matrix, core, lfos, keys);
    if (routed) { matrix.add("lfo1", "gen.freq", 0.5); matrix.add("midi.key", "gen.amp", 0.6); }
    keys.setPresent(true);
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
