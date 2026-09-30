// The spike's shell, run without a host or a web view: notes in, sound out,
// the envelope in the sound, the page served, and the picture the page will
// draw carrying what was played. It prints PASS and FAIL lines in the house
// format and exits non-zero on a failure, like the web suite.
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
  std::vector<float> out;
  out.reserve(static_cast<std::size_t>(total));
  juce::AudioBuffer<float> buffer(2, block);
  /* The picture is taken mid-note, while a sine is playing. Taken at the end
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
    for (int i = 0; i < block && start + i < total; ++i) out.push_back(buffer.getSample(0, i));
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
  double before = 0;
  for (int i = 0; i < 100; ++i) before = std::fmax(before, std::fabs(out[static_cast<std::size_t>(i)]));
  check("silent until the note is struck, at its own sample and not the block's", before <= 0.0, num(before));

  // The same envelope, by itself, with the plugin's defaults: the sound is
  // 0.3 of it on a sine, so its peak over each cycle of 440 Hz should follow.
  scope::EnvelopeTone tone;
  scope::Envelope alone(rate, tone);
  alone.reset(0);
  std::vector<double> level(static_cast<std::size_t>(total));
  for (int i = 0; i < total; ++i) {
    if (i == 100) alone.gate(true, 1.0);
    if (i == static_cast<int>(rate)) alone.gate(false, 0);
    level[static_cast<std::size_t>(i)] = alone.step();
  }
  double worst = 0;
  for (int i = 100; i < total; ++i) {
    const double bound = 0.3 * level[static_cast<std::size_t>(i)] + 1e-6;
    worst = std::fmax(worst, std::fabs(out[static_cast<std::size_t>(i)]) - bound);
  }
  double heldPeak = 0, tail = 0;
  for (int i = 24000; i < 26000; ++i) heldPeak = std::fmax(heldPeak, std::fabs(out[static_cast<std::size_t>(i)]));
  for (int i = total - 2000; i < total; ++i) tail = std::fmax(tail, std::fabs(out[static_cast<std::size_t>(i)]));
  check("the sound never exceeds the core's envelope, reaches it while held, and is silent after the release",
        worst <= 0 && std::fabs(heldPeak - 0.3) < 0.005 && tail < 1e-6,
        "over by " + num(worst) + ", held peak " + num(heldPeak) + ", tail " + num(tail));

  // The bound above holds for an envelope that is too slow as well as the
  // right one, so the attack is also held to being an attack.
  double early = 0;
  for (int i = 101; i < 110; ++i) early = std::fmax(early, std::fabs(out[static_cast<std::size_t>(i)]));
  check("and the attack is heard as an attack: the first ten samples well under full", early < 0.2, num(early));

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

  const std::vector<float>& frames = midNote;
  const std::size_t n = ScopeProcessor::kPictureFrames;
  double mismatch = frames.size() == n * 2 ? 0 : 1, moving = 0;
  for (std::size_t k = 0; k < n && frames.size() == n * 2; ++k) {
    const float played = out[midNoteEnd - n + k];
    moving = std::fmax(moving, std::fabs(played));
    mismatch = std::fmax(mismatch, std::fabs(frames[k * 2] - played) + std::fabs(frames[k * 2 + 1] - played));
  }
  check("the picture is the last " + std::to_string(n) + " frames played, oldest first, left and right",
        mismatch <= 0.0 && moving > 0.25, "mismatch " + num(mismatch) + ", taken while the note was at " + num(moving));

  std::printf("\n%s\n", failures ? "FAILED" : "the shell plays, serves the page, and hands it the picture");
  return failures ? 1 : 0;
}
