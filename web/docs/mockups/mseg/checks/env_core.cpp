// The core's envelope and voice filter, run as the engine runs them, for the
// MSEG mockup's check (curves_against_core.py). Prints JSON on stdout.
//
// Envelope: for each case "attack decay sustain release upSample samples",
// the level after each step(), the key let go after `upSample` steps.
// Filter: for each case "type hz q", the steady gain in dB of svfStep at each
// test frequency: a two-second sine, its last second (a whole number of cycles
// at every whole-hertz frequency) projected on sine and cosine.
#include <cstdio>
#include <cmath>
#include <vector>
#include "scope/envelope.h"
#include "scope/wave.h"

int main() {
  const double rate = 48000;
  struct E { double a, d, s, r; int up, n; };
  const E env[] = { {8, 120, 0.7, 180, 19200, 30000}, {2, 700, 0.0, 250, 14400, 30000},
                    {200, 300, 0.5, 400, 2880, 30000}, {150, 1000, 0.25, 2000, 96000, 200000} };
  std::printf("{\"env\":[");
  for (int c = 0; c < 4; c++) {
    scope::EnvelopeTone tone; tone.attackMs = env[c].a; tone.decayMs = env[c].d; tone.sustain = env[c].s; tone.releaseMs = env[c].r;
    scope::Envelope e(rate, tone);
    e.reset(0); e.gate(true, 1);
    std::printf("%s[", c ? "," : "");
    for (int n = 0; n < env[c].n; n++) {
      std::printf("%s%.12g", n ? "," : "", e.step());
      if (n + 1 == env[c].up) e.gate(false, 0);
    }
    std::printf("]");
  }
  std::printf("],\"filter\":[");
  struct F { int type; double hz, q; };
  const F fl[] = { {1, 1000, 0.7071}, {1, 1600, 2.06}, {3, 400, 5}, {2, 2000, 1.5} };
  const double freqs[] = {30, 50, 80, 120, 200, 300, 450, 700, 900, 1000, 1200, 1500, 1600, 1800, 2000, 2500, 3000, 4000, 5000, 7000, 9000, 12000, 15000, 19000};
  for (int c = 0; c < 4; c++) {
    std::printf("%s[", c ? "," : "");
    for (int i = 0; i < 24; i++) {
      scope::SvfState st; const double g = scope::svfG(fl[c].hz, rate), k = 1 / std::fmax(0.1, fl[c].q);
      double cs = 0, sn = 0; const int n = 96000, tail = 48000;
      for (int s = 0; s < n; s++) {
        const double ph = 2 * M_PI * freqs[i] * s / rate;
        const double y = scope::svfStep(st, std::sin(ph), g, k, fl[c].type);
        if (s >= n - tail) { sn += y * std::sin(ph); cs += y * std::cos(ph); }
      }
      std::printf("%s%.9g", i ? "," : "", 20 * std::log10(2 * std::hypot(sn, cs) / tail));
    }
    std::printf("]");
  }
  std::printf("]}\n");
}
