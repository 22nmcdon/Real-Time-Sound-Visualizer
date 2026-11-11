// The voice's oscillator, ported from `makeOsc`, `wrapJump`, `makeVoiceFx`,
// `voiceFxFor`, `unisonAsked`, `shapeAmount` and `oscStep` inside
// `makeGeneratorCore` in web/scope.html: unison copies, FM, ring modulation,
// hard sync with its band-limited reset, and the sub-oscillator.
//
// Every expression keeps the page's order of operations, products included -
// `TWO_PI * hz * det * dtOf` is not the same double as `TWO_PI * (hz * det) *
// dtOf` - because the parity is held to the last bit wherever it can be. Two
// JavaScript behaviours spelled out: `%` on doubles is `std::fmod`, and
// `Math.round` is `jsRound` (see wave.h), not `std::round`.

#pragma once

#include <array>
#include <cmath>

#include "scope/wave.h"

namespace scope {

constexpr int kUnisonMax = 7;
// A phase runs over two cycles, for the drawbars' 16'; see `waveAt`.
constexpr double kPhaseWrap = 2 * kTwoPi;

// The fields of a layer's tone that its oscillator and voice settings read.
struct VoiceTone {
  Shape shape = Shape::Harmonic;
  double width = 0.25, table = 1.5, morph = 0;
  double fmIndex = 0, modRatio = 1, ringMix = 0, syncRatio = 1;
  double warp = 0, warpAt = 0.25;  // the bend (P6c): radians, and where in the cycle
  /* Scan (P7a): how much of the voice is the screen read back, nought to one
     of kScanMost; the running-away hold on it, a quarter to one; and the
     latest table read, which the generator takes at its next tick. The table
     is not the tone's: whoever reads the screen owns it and keeps it alive
     while the generator may read it (ScanTables). */
  double scan = 0, scanHold = 1;
  const CycleTables* scanTable = nullptr;
  double subLevel = 0;
  int subOctave = 1;
  bool subSine = false;
  double unison = 1, unisonCents = 0;
  int vcfType = 0;
  double vcfCutoff = 2000, vcfQ = 0.7071, vcfTrack = 0, vcfEnv = 0;
  double drive = 0, fold = 0, crushBits = 0, crushHz = 0;
};

inline int unisonAsked(const VoiceTone& t) {
  const double rounded = jsRound(t.unison);
  const double n = std::isnan(rounded) || rounded == 0 ? 1 : rounded;
  return static_cast<int>(std::fmax(1.0, std::fmin(static_cast<double>(kUnisonMax), n)));
}

inline double shapeAmount(const VoiceTone& t, double morphPush, double widthPush, double tablePush) {
  if (t.shape == Shape::Pulse) return (t.width > 0 ? t.width : 0.25) + widthPush;
  if (t.shape == Shape::Wavetable) {
    return std::fmax(0.0, std::fmin(3.0, (std::isfinite(t.table) ? t.table : 1.5) + tablePush));
  }
  return std::fmax(0.0, std::fmin(3.0, t.morph + morphPush));
}

inline double wrapJump(Shape shape, double amount) {
  if (shape == Shape::Ramp) return -2;
  if (shape == Shape::Square) return 1.8;
  if (shape == Shape::Pulse) {
    const double w = std::fmax(0.05, std::fmin(0.95, amount > 0 ? amount : 0.5));
    return 0.9 / std::fmax(w, 1 - w);
  }
  if (shape == Shape::Morph) {
    const double at = std::fmax(0.0, std::fmin(3.0, amount)), low = std::floor(at);
    return 1.8 * (low == 3 ? 1 : low == 2 ? at - low : 0);
  }
  return 0;
}

// A layer's voice settings for the block, and this sample's index and ratio.
struct VoiceFx {
  bool on = false, syncing = false, shaping = false, crushing = false, filtering = false;
  double vcfK = 1, vcfPush = 0;
  int n = 1;
  double fmI = 0, syncR = 1, crushQ = 0, warpA = 0, warpC = 0;
  // The bend's offset (the page's oscStep says why): the sine's exact share,
  // the blocker's pole, and how long the oscillator is held on after a bend.
  double warpDc = 0, dcK = 0, dcHold = 0;
  int cap = kUnisonMax;
  std::array<double, kUnisonMax> det {};
  /* Scan: how much of the voice it is this block, the tables it is fading
     from and to, and how far through the tick this sample is - the page's
     `scanX`, which is the core's and is kept here so the voice can read it. */
  double scanW = 0;
  const CycleTables* scanPrev = nullptr;
  const CycleTables* scanNext = nullptr;
  double scanX = 0;
  /* The shaper's share of the voice, nought to one, walked a sample at a
     time towards `shaping` over the generator's switch time, so a shaper
     switched in or out mid-note crossfades rather than steps (the page's
     makeVoiceFx says why). `shapeRun` is whether it runs this sample,
     `shapeFresh` that it has just come in, when its history is emptied. */
  double shapeW = 0;
  bool shapeRun = false, shapeFresh = false;
  int shapeWait = 0;  // samples still to prime, plus one, the page's shapeWait
};

/* SWITCH_MS: how long a stage that a routing switches in or out - the
   voice's shaper, the plane's non-linear stage - takes to cross over, and
   SWITCH_PRIME how many samples it runs unheard first, to fill its emptied
   history (the page's say why). */
inline constexpr double kSwitchMs = 10;
inline constexpr int kSwitchPrime = 64;

// One sample of the shaper's crossfade, the page's shapeFade.
inline void shapeFade(VoiceFx& x, double step, int prime) {
  x.shapeFresh = false;
  if (!x.shaping) x.shapeWait = 0;
  else if (x.shapeW == 0) {
    if (x.shapeWait == 0) { x.shapeFresh = true; x.shapeWait = prime + 1; }
    if (--x.shapeWait > 0) { x.shapeRun = true; return; }
  }
  x.shapeW = x.shaping ? std::fmin(1.0, x.shapeW + step) : std::fmax(0.0, x.shapeW - step);
  x.shapeRun = x.shapeW > 0;
}
// A stage's sample as heard while it fades: all of it once the fade is done, to the bit.
inline double switchBlend(double dry, double wet, double w) { return w >= 1 ? wet : dry + (wet - dry) * w; }

// The voice's shape with Scan in it: `ink` is the shape at this phase, `x`
// how far through the tick the crossfade is, `w` how much of the voice is
// Scan. A layer with no table yet plays its shape, so turning Scan up before
// the first tick is not a step to a sine.
inline double scanMix(double ink, const CycleTables* prev, const CycleTables* next, double phase, double step, double x,
                      double w) {
  const double a = prev ? cycleRead(prev, phase, step) : ink;
  const double b = next == prev ? a : next ? cycleRead(next, phase, step) : ink;
  return ink + (a + (b - a) * x - ink) * w;
}

inline void voiceFxFor(const VoiceTone& t, VoiceFx& x, bool fmRouted, bool syncRouted, bool shapeRouted) {
  x.filtering = t.vcfType > 0;
  x.vcfK = 1 / std::fmax(0.1, t.vcfQ);
  x.shaping = t.drive > 0 || t.fold > 0 || shapeRouted;
  x.crushing = t.crushBits > 0 || t.crushHz > 0;
  x.crushQ = t.crushBits > 0 ? std::pow(2.0, t.crushBits - 1) : 0;
  x.n = std::min(unisonAsked(t), x.cap);
  x.syncing = t.syncRatio != 1 || syncRouted;
  x.on = t.fmIndex > 0 || t.warp != 0 || fmRouted || t.ringMix > 0 || x.syncing || t.subLevel > 0 || x.n > 1;
  for (int k = 0; k < x.n; k++) {
    x.det[static_cast<std::size_t>(k)] =
        x.n == 1 ? 1 : std::pow(2.0, t.unisonCents * (2.0 * k / (x.n - 1) - 1) / 1200);
  }
}

struct Osc {
  int n = 0;
  std::array<double, kUnisonMax> p {}, s {}, m {}, cyc {}, r {};
  double sub = 0, held = 0, dc = 0;
};

// J1 by its series, the page's besselJ1: ten terms are the double's last bit at 0.9.
inline double besselJ1(double a) {
  const double h = a / 2, h2 = h * h;
  double term = h, sum = h;
  for (int k = 1; k < 10; k++) { term *= -h2 / (k * (k + 1)); sum += term; }
  return sum;
}
constexpr double kBendDcHz = 5;  // BEND_DC_HZ

inline double oscStep(Osc& o, double base, double offset, double hz, const VoiceTone& t, const WaveTables& bars,
                      double amount, const VoiceFx& x, double rate) {
  const double dtOf = 1 / rate;
  const int n = x.n;
  if (o.n != n) {
    const double at = base + offset;
    const double inCycle = at - kTwoPi * std::floor(at / kTwoPi);
    for (std::size_t k = 0; k < kUnisonMax; k++) {
      const double back = kTwoPi * hz * x.det[k] * dtOf;
      o.p[k] = base - back; o.s[k] = (inCycle - back) * x.syncR; o.r[k] = 0;
      o.m[k] = std::fmod((inCycle - back) * t.modRatio, kTwoPi); o.cyc[k] = std::floor(at / kTwoPi);
    }
    o.sub = std::fmod(at / (t.subOctave == 2 ? 4 : 2), kTwoPi);
    o.n = n; o.held = 0;
  }
  const double fmI = x.fmI, syncR = x.syncR, ring = t.ringMix;
  const double wrapHalf = x.syncing ? wrapJump(t.shape, amount) / 2 : 0;
  // The bend's offset: the sine's exact, every other shape's by the blocker.
  const bool blocking = x.warpA != 0 && t.shape != Shape::Sine && !x.syncing;
  double sum = 0, owe = 0, bentOff = 0;
  for (std::size_t k = 0; k < static_cast<std::size_t>(n); k++) {
    const double f = hz * x.det[k];
    double master;
    if (n == 1) master = base + offset;
    else {
      o.p[k] += kTwoPi * f * dtOf;
      if (o.p[k] >= kPhaseWrap) o.p[k] -= kPhaseWrap;
      if (o.p[k] < 0) o.p[k] += kPhaseWrap;
      master = o.p[k] + offset;
    }
    o.m[k] += kTwoPi * f * t.modRatio * dtOf;
    if (o.m[k] >= kTwoPi) o.m[k] -= kTwoPi;
    if (o.m[k] < 0) o.m[k] += kTwoPi;
    double pm = fmI > 0 ? fmI * std::sin(o.m[k]) : 0;
    double inst = fmI > 0 ? f * (1 + fmI * t.modRatio * std::cos(o.m[k])) : f;
    const double pm0 = pm, inst0 = inst;
    // The bend: phase modulation at one-to-one, locked to this copy's own
    // phase and turned to `warpC` of the cycle; its rate joins FM's in
    // `inst`, so the band-limiting is asked where the bend has taken it.
    if (x.warpA != 0) {
      const double d = master - kTwoPi * x.warpC;
      pm += x.warpA * std::sin(d);
      inst += f * x.warpA * std::cos(d);
    }
    double v;
    if (x.syncing) {
      const double sHz = f * syncR;
      o.s[k] += kTwoPi * sHz * dtOf;
      const double cyc = std::floor(master / kTwoPi);
      if (cyc != o.cyc[k]) {
        o.cyc[k] = cyc;
        const double past = master - cyc * kTwoPi;
        const double tau = std::fmin(1.0, past / std::fmax(1e-12, kTwoPi * std::fabs(f) * dtOf));
        const double slaveStep = kTwoPi * sHz * dtOf;
        double before = waveAt(t.shape, o.s[k] - tau * slaveStep + pm - 1e-9, 0, bars, amount);
        double restart = waveAt(t.shape, pm, 0, bars, amount);
        double after = waveAt(t.shape, tau * slaveStep + pm, 0, bars, amount);
        if (x.scanW > 0) {
          before = scanMix(before, x.scanPrev, x.scanNext, o.s[k] - tau * slaveStep + pm - 1e-9, 0, x.scanX, x.scanW);
          restart = scanMix(restart, x.scanPrev, x.scanNext, pm, 0, x.scanX, x.scanW);
          after = scanMix(after, x.scanPrev, x.scanNext, tau * slaveStep + pm, 0, x.scanX, x.scanW);
        }
        const double jump = restart - before;
        o.s[k] = tau * slaveStep;
        owe += jump / 2 * tau * tau - o.r[k];
        o.r[k] = 0;
        v = after + jump / 2 * (2 * tau - tau * tau - 1);
      } else {
        if (o.s[k] >= kPhaseWrap) o.s[k] -= kPhaseWrap;
        const double step = std::fabs(inst * syncR) / rate;
        v = waveAt(t.shape, o.s[k] + pm, step, bars, amount);
        if (x.scanW > 0) v = scanMix(v, x.scanPrev, x.scanNext, o.s[k] + pm, step, x.scanX, x.scanW);
        const double sdt = std::fmin(0.49, step), c = cycleOf(o.s[k] + pm);
        o.r[k] = wrapHalf != 0 && sdt > 0 && c > 1 - sdt ? wrapHalf * std::pow((c - 1) / sdt + 1, 2) : 0;
      }
    } else {
      v = waveAt(t.shape, master + pm, std::fabs(inst) / rate, bars, amount);
      if (x.warpA != 0 && !blocking) v += x.warpDc;
      if (x.scanW > 0) v = scanMix(v, x.scanPrev, x.scanNext, master + pm, std::fabs(inst) / rate, x.scanX, x.scanW);
    }
    double plain = 0;
    if (blocking) {
      plain = waveAt(t.shape, master + pm0, std::fabs(inst0) / rate, bars, amount);
      if (x.scanW > 0)
        plain = scanMix(plain, x.scanPrev, x.scanNext, master + pm0, std::fabs(inst0) / rate, x.scanX, x.scanW);
    }
    if (ring > 0) {
      const double g = 1 - ring + ring * std::sin(o.m[k]);
      v *= g; o.r[k] *= g; plain *= g;
    }
    if (blocking) bentOff += v - plain;
    sum += v;
  }
  double total = sum / n;
  owe /= n;
  if (blocking) o.dc += x.dcK * (bentOff / n - o.dc);
  else if (o.dc != 0) { o.dc -= x.dcK * o.dc; if (std::fabs(o.dc) < 1e-12) o.dc = 0; }
  total -= o.dc;
  if (t.subLevel > 0) {
    const double div = t.subOctave == 2 ? 4 : 2;
    o.sub += kTwoPi * hz / div * dtOf;
    if (o.sub >= kTwoPi) o.sub -= kTwoPi;
    if (o.sub < 0) o.sub += kTwoPi;
    const double sub = waveAt(t.subSine ? Shape::Sine : Shape::Square, o.sub, std::fabs(hz) / div / rate);
    total = (total + t.subLevel * sub) / (1 + t.subLevel);
    owe /= 1 + t.subLevel;
  }
  if (x.syncing) { const double out = o.held + owe; o.held = total; return out; }
  return total;
}

}  // namespace scope
