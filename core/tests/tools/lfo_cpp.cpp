// The LFOs (scope/lfo.h), today's shapes and drawn ones, for
// core/tests/pieces/lfo_drawn.py. Each mode reads its scenario from the file
// named last, one setting a line:
//
//   shape random            today's shape (lfoShape's words), or "drawn"
//   text 1;0,1,h,r          the drawn shape's text
//   hz 0.37                 the rate
//   rate 48000              the sample rate
//   n 576000                how many samples
//   seed 7                  the Random stream's seed
//   phase 0.25              Phase, as a share of the cycle
//   restart 1000 2000       samples before which it starts again (lfoRestart)
//   adopt 5000              in `run`, today's shape until this sample, then the text
//                           adopted as the editor's first edit adopts it
//
// `lfo_cpp pair <file>`  today's shape through lfoStep beside the text through
//                        the drawn path, each from its own stream of one seed:
//                        `worst <difference> <sample>`, the difference as %a too
// `lfo_cpp run <file>`   one LFO, every value in hexadecimal, one a line, after a
//                        line `segs` listing the point whose line each sample is on
// `lfo_cpp text <file>`  each line of the file a shape's text: `ok|no <count> <written>`
#include <cstdio>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#include "scope/lfo.h"

namespace {
struct Scenario {
  std::string shape = "sine", text;
  double hz = 1, rate = 48000, phase = 0;
  long n = 48000;
  unsigned seed = 1;
  std::vector<long> restarts;
  long adopt = -1;
};

Scenario readScenario(const char* path) {
  Scenario s;
  std::ifstream in(path);
  for (std::string line; std::getline(in, line);) {
    std::istringstream w(line);
    std::string key;
    if (!(w >> key)) continue;
    if (key == "shape") w >> s.shape;
    else if (key == "text") w >> s.text;
    else if (key == "hz") w >> s.hz;
    else if (key == "rate") w >> s.rate;
    else if (key == "n") w >> s.n;
    else if (key == "seed") w >> s.seed;
    else if (key == "phase") w >> s.phase;
    else if (key == "restart") for (long at; w >> at;) s.restarts.push_back(at);
    else if (key == "adopt") w >> s.adopt;
  }
  return s;
}

scope::Lfo make(const std::string& shape, const std::string& text, const Scenario& s) {
  scope::Lfo l;
  l.rate = s.hz;
  l.setDrawn(text);
  l.setPhase0(s.phase);
  l.setShape(shape);
  return l;
}
}  // namespace

int main(int argc, char** argv) {
  if (argc < 3) { std::fprintf(stderr, "usage: lfo_cpp pair|run|text <file>\n"); return 2; }
  const std::string mode = argv[1];
  if (mode == "text") {
    std::ifstream in(argv[2]);
    for (std::string line; std::getline(in, line);) {
      if (line.empty()) continue;
      scope::LfoShape sh;
      const bool ok = scope::lfoShapeRead(line, sh);
      char buf[1024];
      scope::lfoShapeWrite(sh, buf, sizeof buf);
      std::printf("%s %d %s\n", ok ? "ok" : "no", sh.n, buf);
    }
    return 0;
  }
  const Scenario s = readScenario(argv[2]);
  if (mode == "pair") {
    scope::Lfo a = make(s.shape, "", s), b = make("drawn", s.text, s);
    scope::Random ra(s.seed), rb(s.seed);
    double worst = 0;
    long at = -1;
    for (long i = 0; i < s.n; i++) {
      const double va = scope::lfoStep(a, s.rate, ra), vb = scope::lfoStep(b, s.rate, rb);
      const double d = std::fabs(va - vb);
      if (!(d <= worst)) { worst = d; at = i; }
    }
    std::printf("worst %.17g %ld %a\n", worst, at, worst);
    return 0;
  }
  if (mode == "run") {
    scope::Lfo l = make(s.shape, s.adopt >= 0 ? "" : s.text, s);
    scope::Random r(s.seed);
    std::size_t next = 0;
    std::string segs = "segs";
    std::vector<double> out;
    out.reserve(static_cast<std::size_t>(s.n));
    for (long i = 0; i < s.n; i++) {
      while (next < s.restarts.size() && s.restarts[next] == i) { scope::lfoRestart(l); next++; }
      if (i == s.adopt) { l.setDrawn(s.text); l.setShape("drawn"); }
      out.push_back(scope::lfoStep(l, s.rate, r));
      segs += " " + std::to_string(l.segI);
    }
    std::printf("%s\n", segs.c_str());
    for (const double v : out) std::printf("%a\n", v);
    return 0;
  }
  std::fprintf(stderr, "lfo_cpp: no mode %s\n", mode.c_str());
  return 2;
}
