// The voice's oscillator, ported from `makeOsc`, `wrapJump`, `makeVoiceFx`,
// `voiceFxFor`, `unisonAsked`, `shapeAmount` and `oscStep` inside
// `makeGeneratorCore` in web/scope.html: unison copies, FM, ring modulation,
// hard sync with its band-limited reset, and the sub-oscillator.
//
// Every expression keeps the page's order of operations, products included -
// `TWO_PI * hz * det * dtOf` is not the same double as `TWO_PI * (hz * det) *
// dtOf` - because the parity is held to the last bit wherever it can be. Two
// JavaScript behaviours spelled out: `%` on doubles is `std::fmod`, and
// `Math.round` rounds a half upwards where `std::round` rounds it away from
// nought, which is why the unison count uses `floor(x + 0.5)`.

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
  double subLevel = 0;
  int subOctave = 1;
  bool subSine = false;
  double unison = 1, unisonCents = 0;
  int vcfType = 0;
  double vcfQ = 0.707;
  double drive = 0, fold = 0, crushBits = 0, crushHz = 0;
};

inline int unisonAsked(const VoiceTone& t) {
  const double rounded = std::floor(t.unison + 0.5);
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
  double fmI = 0, syncR = 1, crushQ = 0;
  int cap = kUnisonMax;
  std::array<double, kUnisonMax> det {};
};

inline void voiceFxFor(const VoiceTone& t, VoiceFx& x, bool fmRouted, bool syncRouted, bool shapeRouted) {
  x.filtering = t.vcfType > 0;
  x.vcfK = 1 / std::fmax(0.1, t.vcfQ);
  x.shaping = t.drive > 0 || t.fold > 0 || shapeRouted;
  x.crushing = t.crushBits > 0 || t.crushHz > 0;
  x.crushQ = t.crushBits > 0 ? std::pow(2.0, t.crushBits - 1) : 0;
  x.n = std::min(unisonAsked(t), x.cap);
  x.syncing = t.syncRatio != 1 || syncRouted;
  x.on = t.fmIndex > 0 || fmRouted || t.ringMix > 0 || x.syncing || t.subLevel > 0 || x.n > 1;
  for (int k = 0; k < x.n; k++) {
    x.det[static_cast<std::size_t>(k)] =
        x.n == 1 ? 1 : std::pow(2.0, t.unisonCents * (2.0 * k / (x.n - 1) - 1) / 1200);
  }
}

struct Osc {
  int n = 0;
  std::array<double, kUnisonMax> p {}, s {}, m {}, cyc {}, r {};
  double sub = 0, held = 0;
};

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
  double sum = 0, owe = 0;
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
    const double pm = fmI > 0 ? fmI * std::sin(o.m[k]) : 0;
    const double inst = fmI > 0 ? f * (1 + fmI * t.modRatio * std::cos(o.m[k])) : f;
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
        const double before = waveAt(t.shape, o.s[k] - tau * slaveStep + pm - 1e-9, 0, bars, amount);
        const double jump = waveAt(t.shape, pm, 0, bars, amount) - before;
        o.s[k] = tau * slaveStep;
        owe += jump / 2 * tau * tau - o.r[k];
        o.r[k] = 0;
        v = waveAt(t.shape, o.s[k] + pm, 0, bars, amount) + jump / 2 * (2 * tau - tau * tau - 1);
      } else {
        if (o.s[k] >= kPhaseWrap) o.s[k] -= kPhaseWrap;
        const double step = std::fabs(inst * syncR) / rate;
        v = waveAt(t.shape, o.s[k] + pm, step, bars, amount);
        const double sdt = std::fmin(0.49, step), c = cycleOf(o.s[k] + pm);
        o.r[k] = wrapHalf != 0 && sdt > 0 && c > 1 - sdt ? wrapHalf * std::pow((c - 1) / sdt + 1, 2) : 0;
      }
    } else {
      v = waveAt(t.shape, master + pm, std::fabs(inst) / rate, bars, amount);
    }
    if (ring > 0) {
      const double g = 1 - ring + ring * std::sin(o.m[k]);
      v *= g; o.r[k] *= g;
    }
    sum += v;
  }
  double total = sum / n;
  owe /= n;
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
