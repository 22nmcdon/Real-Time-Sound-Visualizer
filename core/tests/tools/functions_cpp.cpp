// The C++ ports through the same list of calls as functions_js.mjs, one
// result line per call. See that file for the language.
#include <array>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#include <map>

#include "scope/noise.h"
#include "scope/osc.h"
#include "scope/wave.h"

namespace {
std::vector<std::string> splitOn(const std::string& text, char sep) {
  std::vector<std::string> out;
  std::string part;
  std::istringstream in(text);
  while (std::getline(in, part, sep)) out.push_back(part);
  return out;
}
std::vector<double> numbers(const std::string& text) {
  std::vector<double> out;
  for (const auto& w : splitOn(text, ',')) out.push_back(std::strtod(w.c_str(), nullptr));
  return out;
}
scope::CycleTables tables(const std::string& text) {  // "most:t0;t1;..."
  const auto colon = text.find(':');
  scope::CycleTables c;
  c.most = std::strtod(text.substr(0, colon).c_str(), nullptr);
  for (const auto& t : splitOn(text.substr(colon + 1), ';')) {
    std::vector<float> table;
    for (const double v : numbers(t)) table.push_back(static_cast<float>(v));
    c.levels.push_back(table);
  }
  return c;
}
double num(const std::string& w) { return std::strtod(w.c_str(), nullptr); }
void show(const std::vector<double>& values) {
  for (std::size_t i = 0; i < values.size(); i++) std::printf(i ? " %.17g" : "%.17g", values[i]);
  std::printf("\n");
}
}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) { std::fprintf(stderr, "usage: functions_cpp <calls>\n"); return 2; }
  std::ifstream file(argv[1]);
  for (std::string line; std::getline(file, line);) {
    std::istringstream in(line);
    std::vector<std::string> w;
    for (std::string word; in >> word;) w.push_back(word);
    if (w.empty()) continue;
    const std::string& name = w[0];
    if (name == "noiseRun") {
      scope::Noise shape = scope::Noise::White;
      scope::noiseNamed(w[1], shape);
      const double hz = num(w[4]), rate = num(w[5]);
      scope::Random random(static_cast<std::uint32_t>(num(w[2])));
      scope::NoiseState z(random);
      std::vector<double> out;
      double phase = 0;
      for (long i = 0; i < static_cast<long>(num(w[3])); i++) {
        phase += scope::kTwoPi * hz / rate;
        if (phase >= scope::kPhaseWrap) phase -= scope::kPhaseWrap;
        out.push_back(scope::noiseStep(z, shape, phase, hz / rate, random));
      }
      show(out);
      continue;
    }
    if (name == "oscRun") {
      std::map<std::string, std::string> p;
      for (std::size_t i = 1; i < w.size(); i++) { const auto eq = w[i].find('='); p[w[i].substr(0, eq)] = w[i].substr(eq + 1); }
      auto d = [&](const char* k) { return num(p[k]); };
      scope::VoiceTone t;
      t.shape = scope::shapeNamed(p["shape"]);
      t.fmIndex = d("fm"); t.modRatio = d("mod"); t.ringMix = d("ring"); t.syncRatio = d("sync");
      t.subLevel = d("sub"); t.subOctave = static_cast<int>(d("suboct")); t.subSine = d("subsine") == 1;
      t.unison = d("n"); t.unisonCents = d("cents");
      std::array<double, 9> weights {};
      scope::WaveTables bars;
      if (p["bars"] != "-") { const auto v = numbers(p["bars"]); for (std::size_t k = 0; k < 9; k++) weights[k] = v[k]; bars.weights = &weights; }
      scope::Osc o;
      scope::VoiceFx x;
      const bool fmr = d("fmr") == 1, syncr = d("syncr") == 1;
      scope::voiceFxFor(t, x, fmr, syncr, false);
      const double rate = d("rate");
      const long samples = static_cast<long>(d("samples")), flip = static_cast<long>(d("flip"));
      std::vector<double> out;
      double base = 0;
      for (long i = 0; i < samples; i++) {
        if (i == flip) { t.unison = d("n2"); scope::voiceFxFor(t, x, fmr, syncr, false); }
        const double hz = d("hz") + (d("hz2") - d("hz")) * static_cast<double>(i) / static_cast<double>(samples);
        x.fmI = d("fm");
        x.syncR = d("sync") + d("sweep") * static_cast<double>(i) / static_cast<double>(samples);
        base += scope::kTwoPi * hz / rate;
        if (base >= scope::kPhaseWrap) base -= scope::kPhaseWrap;
        out.push_back(scope::oscStep(o, base, d("offset"), hz, t, bars, d("amount"), x, rate));
      }
      show(out);
      continue;
    }
    if (name == "cycleOf") show({ scope::cycleOf(num(w[1])) });
    else if (name == "polyBlep") show({ scope::polyBlep(num(w[1]), num(w[2])) });
    else if (name == "polyBlamp") show({ scope::polyBlamp(num(w[1]), num(w[2])) });
    else if (name == "drawbarGain") show({ scope::drawbarGain(num(w[1])) });
    else if (name == "drawbarWeights") {
      const auto v = numbers(w[1]);
      std::array<double, 9> levels {}, out {};
      for (std::size_t k = 0; k < 9; k++) levels[k] = v[k];
      scope::drawbarWeights(levels, out);
      show({ out.begin(), out.end() });
    } else if (name == "intervalRatio") show({ scope::intervalRatio(static_cast<int>(num(w[1])), num(w[2]) == 1) });
    else if (name == "svfG") show({ scope::svfG(num(w[1]), num(w[2])) });
    else if (name == "svfRun") {
      scope::SvfState s;
      std::vector<double> out;
      for (const double x : numbers(w[4])) out.push_back(scope::svfStep(s, x, num(w[1]), num(w[2]), static_cast<int>(num(w[3]))));
      show(out);
    } else if (name == "cycleRead") {
      const auto c = tables(w[1].substr(2));
      show({ scope::cycleRead(&c, num(w[2]), num(w[3])) });
    } else if (name == "waveAt") {
      scope::WaveTables bars;
      std::array<double, 9> weights {};
      scope::CycleTables cycle;
      std::vector<scope::CycleTables> bank;
      if (w[4].rfind("T:", 0) == 0) { cycle = tables(w[4].substr(2)); bars.cycle = &cycle; }
      else if (w[4].rfind("B:", 0) == 0) {
        for (const auto& c : splitOn(w[4].substr(2), '!')) bank.push_back(tables(c));
        bars.bank = &bank;
      } else if (w[4] != "-") {
        const auto v = numbers(w[4]);
        for (std::size_t k = 0; k < 9; k++) weights[k] = v[k];
        bars.weights = &weights;
      }
      show({ scope::waveAt(scope::shapeNamed(w[1]), num(w[2]), num(w[3]), bars, num(w[5])) });
    } else { std::fprintf(stderr, "unknown call %s\n", name.c_str()); return 2; }
  }
  return 0;
}
