// The instrument (scope/instrument.h) as the plugin plays it, natively,
// through the same script as instrument_js.mjs, which plays the compiled one
// through the page's wrapper. A line of the script is a JSON array:
//
//   ["make", rate, block, code]      made, and loaded with that setup code
//   ["slider", id, value]            a slider moved on the page
//   ["setup", code]                  a setup loaded on the page
//   ["control", id, value]           a menu or text box (text), a switch (true or false)
//   ["click", id] ["routings", text] ["fade", json]
//   ["midi", b0, b1?, b2?]           a message, for the top of the next block
//   ["feed", periodL?, periodR?]     an input from now on: a saw of periodL samples on the
//                                    left and a triangle of periodR on the right, at half
//                                    scale, by arithmetic alone so both sides make it to the
//                                    bit; one period is a mono input, none is no input
//   ["feedlanes", p0, p1, ...]       a rack's lanes from now on, up to six: lane k a saw of
//                                    pk samples, at half scale
//   ["block", n, stride?]            n frames; every stride-th sample printed (1 when left out)
//
// `instrument_cpp --code NAME...` prints each preset's setup code instead, and
// `instrument_cpp --names` every preset's name.
//
// Out, a line each: `no` for a slider, setup or fade refused; for a block,
// `block` and its heard pair then the picture's six lanes, every sample; `out` and
// the MIDI it sent, if any; `state`, the host's count and the code, if the
// state changed.
#include <cmath>
#include <cstdio>
#include <fstream>
#include <string>
#include <vector>

#include "scope/instrument.h"
#include "scope/presets.h"

namespace {
std::string text(const scope::Json& v) { return v.type == scope::Json::Type::String ? scope::utf16To8(v.s) : std::string(); }
}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) { std::fprintf(stderr, "usage: instrument_cpp <script> | --code PRESET...\n"); return 2; }
  // Every preset's name, a line each, the generator's first.
  if (std::string(argv[1]) == "--names") {
    for (const char* kind : { "generator", "display" })
      for (const auto& preset : scope::presets()) if (preset.kind == kind) std::printf("%s\n", preset.name.c_str());
    return 0;
  }
  // The setup code of each preset named, a line each, for a script to load.
  if (std::string(argv[1]) == "--code") {
    for (int i = 2; i < argc; ++i) {
      const scope::Preset* preset = scope::findPreset(argv[i]);
      const auto code = preset ? scope::encodeSetup(preset->setup) : std::nullopt;
      std::printf("%s\n", code ? code->c_str() : "");
    }
    return 0;
  }
  std::ifstream file(argv[1]);
  scope::Instrument instrument;
  std::vector<std::uint8_t> midi;
  std::vector<std::size_t> lengths;
  std::vector<std::vector<int>> sent;
  double feedL = 0, feedR = 0;
  std::vector<double> feedLanes;
  long long fed = 0;
  std::vector<float> inL, inR;
  instrument.hooks.midiOut = [&](const std::uint8_t* bytes, int length, int) { sent.emplace_back(bytes, bytes + length); };
  for (std::string line; std::getline(file, line);) {
    if (line.empty()) continue;
    const auto parsed = scope::jsonParse(scope::utf8To16(line));
    if (!parsed || parsed->type != scope::Json::Type::Array || parsed->a.empty()) { std::fprintf(stderr, "bad line\n"); return 2; }
    const auto& a = parsed->a;
    const std::string cmd = text(a[0]);
    const auto arg = [&](std::size_t i) -> const scope::Json& { static const scope::Json none; return i < a.size() ? a[i] : none; };
    if (cmd == "make") {
      const auto setup = scope::Instrument::setup(text(arg(3)));
      instrument.prepare(arg(1).n, static_cast<int>(arg(2).n), setup ? *setup->setup : scope::Json::object());
      if (!setup) std::printf("no\n");
    } else if (cmd == "slider") {
      const auto c = scope::Instrument::slider(text(arg(1)), arg(2).type == scope::Json::Type::String ? arg(2).s : u"");
      if (c) instrument.apply(*c); else std::printf("no\n");
    } else if (cmd == "setup") {
      const auto c = scope::Instrument::setup(text(arg(1)));
      if (c) instrument.apply(*c); else std::printf("no\n");
    } else if (cmd == "control") {
      instrument.apply(scope::Instrument::control(text(arg(1)), arg(2).type == scope::Json::Type::Bool ? arg(2) : scope::Json::string(arg(2).s)));
    } else if (cmd == "click") instrument.apply(scope::Instrument::click(text(arg(1))));
    else if (cmd == "routings") instrument.apply(scope::Instrument::routings(text(arg(1))));
    else if (cmd == "fade") {
      const auto c = scope::Instrument::fade(text(arg(1)));
      if (c) instrument.apply(*c); else std::printf("no\n");
    } else if (cmd == "midi") {
      for (std::size_t i = 1; i < a.size() && i < 4; ++i) midi.push_back(static_cast<std::uint8_t>(a[i].n));
      lengths.push_back(std::min<std::size_t>(a.size() - 1, 3));
    } else if (cmd == "feed") {
      feedL = a.size() > 1 ? a[1].n : 0;
      feedR = a.size() > 2 ? a[2].n : 0;
      feedLanes.clear();
    } else if (cmd == "feedlanes") {
      feedLanes.clear();
      for (std::size_t i = 1; i < a.size() && feedLanes.size() < 6; ++i) feedLanes.push_back(a[i].n);
      feedL = feedR = 0;
    } else if (cmd == "block") {
      const std::size_t n = static_cast<std::size_t>(arg(1).n);
      inL.assign(n, 0.0f); inR.assign(n, 0.0f);
      for (std::size_t k = 0; k < n && feedL > 0; ++k, ++fed) {
        const double t = std::fmod(static_cast<double>(fed), feedL) / feedL;
        inL[k] = static_cast<float>(0.5 * (2 * t - 1));
        if (feedR > 0) {
          const double u = std::fmod(static_cast<double>(fed), feedR) / feedR;
          inR[k] = static_cast<float>(0.5 * (u < 0.5 ? 4 * u - 1 : 3 - 4 * u));
        }
      }
      std::vector<std::vector<float>> rack(feedLanes.size(), std::vector<float>(n));
      std::vector<const float*> rackLanes;
      for (std::size_t c = 0; c < feedLanes.size(); ++c) {
        for (std::size_t k = 0; k < n; ++k) {
          const double t = std::fmod(static_cast<double>(fed + static_cast<long long>(k)), feedLanes[c]) / feedLanes[c];
          rack[c][k] = static_cast<float>(0.5 * (2 * t - 1));
        }
        rackLanes.push_back(rack[c].data());
      }
      if (!feedLanes.empty()) fed += static_cast<long long>(n);
      // A pair is lanes too, as the bridge hands over whatever channels it is given: one, or two.
      const float* pairLanes[2] = { inL.data(), inR.data() };
      const scope::Instrument::Input input = feedLanes.empty()
        ? scope::Instrument::Input { inL.data(), feedR > 0 ? inR.data() : nullptr, pairLanes, feedR > 0 ? 2 : 1 }
        : scope::Instrument::Input { rackLanes[0], rackLanes.size() > 1 ? rackLanes[1] : nullptr, rackLanes.data(),
                                     static_cast<int>(rackLanes.size()) };
      std::vector<float> lanes(8 * n);  // the heard pair, then the picture's six lanes
      std::vector<scope::Instrument::Event> events;
      std::size_t at = 0;
      for (const std::size_t length : lengths) { events.push_back({ 0, midi.data() + at, length }); at += length; }
      sent.clear();
      instrument.block(lanes.data(), lanes.data() + n, static_cast<int>(n), events.data(), events.size(), nullptr, nullptr, 0,
                       feedL > 0 || !feedLanes.empty() ? &input : nullptr);
      for (int c = 0; c < scope::Instrument::kRingLanes; ++c)
        instrument.latestLane(c, lanes.data() + (2 + static_cast<std::size_t>(c)) * n, n);
      midi.clear(); lengths.clear();
      const std::size_t stride = arg(2).type == scope::Json::Type::Number && arg(2).n >= 1 ? static_cast<std::size_t>(arg(2).n) : 1;
      std::printf("block");
      for (std::size_t k = 0; k < lanes.size(); k += stride) std::printf(" %.9g", static_cast<double>(lanes[k]));
      std::printf("\n");
      if (!sent.empty()) {
        std::printf("out");
        for (const auto& m : sent) { for (const int b : m) std::printf(" %d", b); std::printf(" ;"); }
        std::printf("\n");
      }
      if (instrument.changed()) {
        std::printf("state %d %s\n", instrument.hostVersion(), instrument.stateCode().c_str());
        instrument.published();
      }
    } else { std::fprintf(stderr, "unknown command %s\n", cmd.c_str()); return 2; }
  }
  return 0;
}
