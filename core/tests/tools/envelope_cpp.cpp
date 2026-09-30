// The C++ envelope through a scenario, one value per line, as the page's is
// printed by envelope_js.mjs. The scenario reader is the same language; see
// js_core.mjs for it.
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

#include "scope/envelope.h"

namespace {
struct Timed { long at; std::vector<std::string> words; };

std::vector<std::string> split(const std::string& line) {
  std::istringstream in(line);
  std::vector<std::string> words;
  for (std::string w; in >> w;) words.push_back(w);
  return words;
}
}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) { std::fprintf(stderr, "usage: envelope_cpp <scenario>\n"); return 2; }
  std::ifstream file(argv[1]);
  std::vector<std::vector<std::string>> setup;
  std::vector<Timed> timed;
  long run = 0;
  for (std::string raw; std::getline(file, raw);) {
    const std::string line = raw.substr(0, raw.find('#'));
    auto words = split(line);
    if (words.empty()) continue;
    if (words[0] == "run") run = std::stol(words[1]);
    else if (words[0] == "at") timed.push_back({ std::stol(words[1]), { words.begin() + 2, words.end() } });
    else setup.push_back(words);
  }
  std::stable_sort(timed.begin(), timed.end(), [](const Timed& a, const Timed& b) { return a.at < b.at; });

  double rate = 48000;
  bool haveReset = false;
  double resetTo = 0;
  scope::EnvelopeTone tone;
  std::unique_ptr<scope::Envelope> env;
  auto apply = [&](const std::vector<std::string>& w) {
    if (w[0] == "rate") rate = std::stod(w[1]);
    else if (w[0] == "tone") {
      const double v = std::stod(w[2]);
      if (w[1] == "attackMs") tone.attackMs = v;
      else if (w[1] == "decayMs") tone.decayMs = v;
      else if (w[1] == "sustain") tone.sustain = v;
      else if (w[1] == "releaseMs") tone.releaseMs = v;
      else { std::fprintf(stderr, "unknown tone field %s\n", w[1].c_str()); std::exit(2); }
    } else if (w[0] == "reset") {
      if (env) env->reset(std::stod(w[1])); else { haveReset = true; resetTo = std::stod(w[1]); }
    } else if (w[0] == "gate") env->gate(w[1] == "1", w.size() > 2 ? std::stod(w[2]) : 1.0);
    else { std::fprintf(stderr, "unknown command %s\n", w[0].c_str()); std::exit(2); }
  };
  for (const auto& w : setup) apply(w);
  env = std::make_unique<scope::Envelope>(rate, tone);
  if (haveReset) env->reset(resetTo);
  std::size_t k = 0;
  for (long i = 0; i < run; i++) {
    while (k < timed.size() && timed[k].at == i) apply(timed[k++].words);
    std::printf("%.17g\n", env->step());
  }
  return 0;
}
