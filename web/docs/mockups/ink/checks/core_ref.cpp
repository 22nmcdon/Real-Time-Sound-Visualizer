// The core's own oscillator and shaper, run for the Ink mockup's checks: the drawings are compared
// with what these print. Built against core/include, nothing copied:
//   g++ -std=c++17 -O2 -I core/include web/docs/mockups/ink/checks/core_ref.cpp -o core_ref
// Usage: core_ref osc shape fm ratio warp warpAt ring sync sub subOct subSine unison cents offsetDeg cycles points [settleSeconds]
//        core_ref shaper drive fold bits      (x from -1 to 1, 2001 points: shapeSample, then crushStep's quantiser)
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <string>
#include "scope/osc.h"
#include "scope/voice.h"
#include "scope/voices.h"
using namespace scope;

int main(int argc, char** argv) {
  if (argc > 1 && std::strcmp(argv[1], "shaper") == 0) {
    VoiceTone t; t.drive = std::atof(argv[2]); t.fold = std::atof(argv[3]); t.crushBits = std::atof(argv[4]);
    Shaping sh; setShaping(sh, t, 0, 0);
    VoiceFx x; voiceFxFor(t, x, false, false, false);
    for (int i = 0; i <= 2000; i++) {
      const double in = -1 + 2.0 * i / 2000;
      double v = shapeSample(sh, in);
      if (x.crushQ > 0) v = jsRound(v * x.crushQ) / x.crushQ;
      std::printf("%.17g\n", v);
    }
    return 0;
  }
  VoiceTone t;
  t.shape = shapeNamed(argv[2]);
  t.fmIndex = std::atof(argv[3]); t.modRatio = std::atof(argv[4]); t.warp = std::atof(argv[5]); t.warpAt = std::atof(argv[6]);
  t.ringMix = std::atof(argv[7]); t.syncRatio = std::atof(argv[8]); t.subLevel = std::atof(argv[9]); t.subOctave = std::atoi(argv[10]);
  t.subSine = std::atoi(argv[11]) != 0; t.unison = std::atof(argv[12]); t.unisonCents = std::atof(argv[13]);
  const double offset = std::atof(argv[14]) * kPi / 180, cycles = std::atof(argv[15]);
  const int points = std::atoi(argv[16]);
  // A sample rate high enough that the band-limiting (polyBlep, the one-sample delay of sync) is
  // under the drawing's pixel, and two seconds of settling for the bend's 5 Hz blocker.
  const double hz = 220, rate = 220.0 * 4096;
  VoiceFx x; x.cap = kUnisonMax; voiceFxFor(t, x, false, false, false);
  x.fmI = std::fmax(0.0, std::fmin(20.0, t.fmIndex)); x.syncR = std::fmax(1.0, std::fmin(8.0, t.syncRatio));
  x.warpA = std::fmax(-0.9, std::fmin(0.9, t.warp)); x.warpC = t.warpAt - std::floor(t.warpAt);
  x.warpDc = x.warpA != 0 ? besselJ1(x.warpA) * std::sin(kTwoPi * x.warpC) : 0;
  x.dcK = poleFor(1000 / (kTwoPi * kBendDcHz), rate);
  Osc o;
  const WaveTables bars;
  // Whole patterns of about two seconds, or, given an 18th argument, that many seconds exactly (for
  // unison's still, where the copies' own phases are what is read and the note's base does not matter).
  long settle = static_cast<long>(rate * 2 / (4096 * cycles)) * static_cast<long>(4096 * cycles);
  if (argc > 17) settle = std::lround(std::atof(argv[17]) * rate);
  const long per = static_cast<long>(4096 * cycles);
  double base = 0;
  const double step = kTwoPi * hz / rate;
  // n == 1 reads the base phase given; keep it wrapped at two cycles, as the generator's phase is.
  long i = 0;
  for (; i < settle; i++) { oscStep(o, base, offset, hz, t, bars, 0, x, rate); base += step; if (base >= kPhaseWrap) base -= kPhaseWrap; }
  for (long k = 0; k < per; k++) {
    const double v = oscStep(o, base, offset, hz, t, bars, 0, x, rate);
    base += step; if (base >= kPhaseWrap) base -= kPhaseWrap;
    if (k % (per / points) == 0) std::printf("%.17g\n", v);
  }
  return 0;
}
