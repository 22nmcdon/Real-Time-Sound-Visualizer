// The core's EQ response, for web/tests/eqeditortest.py: built against core/include, it reads settings
// from stdin and prints the cascade in dB at 241 frequencies, 20 Hz to 20 kHz, from Plane::eqBand.
// Reads settings from stdin: rate low lowHz mid midHz width high highHz cutLowHz cutLowQ cutHighHz cutHighQ (the
// cuts since 23 Nov, each in unless at its end, as Plane::eqSet has them); prints dB at 241 log-spaced freqs 20..20k.
#include "scope/plane.h"
#include <complex>
#include <cstdio>
int main() {
  double rate, g[3], f[3], w, cf[2], cq[2];
  while (std::scanf("%lf %lf %lf %lf %lf %lf %lf %lf %lf %lf %lf %lf", &rate, &g[0], &f[0], &g[1], &f[1], &w, &g[2], &f[2],
                    &cf[0], &cq[0], &cf[1], &cq[1]) == 12) {
    for (int i = 0; i < 241; i++) {
      double hz = 20 * std::pow(1000.0, i / 240.0);
      std::complex<double> H(1, 0), z1 = std::polar(1.0, -2 * M_PI * hz / rate), z2 = z1 * z1;
      for (int k = 0; k < 3; k++) {
        double gk = std::fmax(-24.0, std::fmin(24.0, g[k]));
        if (gk == 0) continue;
        auto c = scope::Plane::eqBand(k, gk, std::fmax(10.0, f[k]), w, rate);
        H *= (c[0] + c[1] * z1 + c[2] * z2) / (1.0 + c[3] * z1 + c[4] * z2);
      }
      for (int j = 0; j < 2; j++) {
        if (j == 0 ? !(cf[j] > 20) : !(cf[j] < 20000)) continue;
        auto c = scope::Plane::eqBand(3 + j, 0, std::fmax(10.0, cf[j]), std::fmax(0.5, std::fmin(4.0, cq[j])), rate);
        H *= (c[0] + c[1] * z1 + c[2] * z2) / (1.0 + c[3] * z1 + c[4] * z2);
      }
      std::printf("%s%.9f", i ? " " : "", 10 * std::log10(std::norm(H)));
    }
    std::printf("\n");
  }
}
