// What a voice does after its oscillator, ported from inside
// `makeGeneratorCore` in web/scope.html: the filter's cutoff and coefficient
// (`vcfHz`, `vcfCoef`, `makeVcf`), the shaping and its oversampler
// (`shapeSample`, `setShaping`, `lowpassTaps`, `makeShaper`), and the crush
// (`makeCrush`, `crushStep`). The same arithmetic in the same order, held to
// the page by core/tests/parity.py.
//
// One difference of shape, not of sum. In the page the shaping's four
// numbers are the core's own variables, written by `setShaping` for one
// layer and read by every voice's shaper until it is written for the next;
// here they are a `Shaping` passed to the shaper, so the dependence the page
// has by order of statements is one a reader can see.

#pragma once

#include <cmath>
#include <vector>

#include "scope/osc.h"
#include "scope/wave.h"

namespace scope {

// Middle C: where key tracking leaves the cutoff where the slider says.
constexpr double kKeyRef = 261.63;

inline double vcfHz(const VoiceTone& t, double noteHz, double envLevel, double push, double rate) {
  double fc = t.vcfCutoff * std::pow(2.0, t.vcfEnv * envLevel + push);
  if (t.vcfTrack > 0 && noteHz > 0) fc *= std::pow(noteHz / kKeyRef, t.vcfTrack);
  return std::fmax(10.0, std::fmin(0.45 * rate, fc));
}

// A voice's filter: the state-variable filter's integrators, its
// coefficient, and what the coefficient was worked out from, so it is worked
// out again only when one of those has moved. NaN to begin with, which no
// value equals, so the first sample always works it out.
struct VcfState : SvfState {
  double g = 0;
  double lv = std::nan(""), lp = std::nan(""), lf = std::nan(""), lc = std::nan(""), le = std::nan(""), lt = std::nan("");
};

inline double vcfCoef(VcfState& s, const VoiceTone& t, double noteHz, double envLevel, double push, double rate) {
  if (envLevel != s.lv || push != s.lp || noteHz != s.lf || t.vcfCutoff != s.lc
      || t.vcfEnv != s.le || t.vcfTrack != s.lt) {
    s.lv = envLevel; s.lp = push; s.lf = noteHz; s.lc = t.vcfCutoff; s.le = t.vcfEnv; s.lt = t.vcfTrack;
    s.g = svfG(vcfHz(t, noteHz, envLevel, push, rate), rate);
  }
  return s.g;
}

// The drive and the fold as one layer's sample of them sets them.
struct Shaping {
  double drive = 0, driveNorm = 1, fold = 0, foldNorm = 1;
};

inline double shapeSample(const Shaping& sh, double x) {
  if (sh.drive > 0) x = std::tanh(sh.drive * x) * sh.driveNorm;
  if (sh.fold > 0) x = std::sin(sh.fold * x) * sh.foldNorm;
  return x;
}

inline void setShaping(Shaping& sh, const VoiceTone& t, double drivePush, double foldPush) {
  const double d = std::fmax(0.0, std::fmin(1.0, t.drive + drivePush));
  const double f = std::fmax(0.0, std::fmin(1.0, t.fold + foldPush));
  sh.drive = 30 * d * d;
  sh.driveNorm = sh.drive > 0 ? 1 / std::tanh(sh.drive) : 1;
  sh.fold = 6 * kPi * f;
  sh.foldNorm = sh.fold > 0 && sh.fold < kPi / 2 ? 1 / std::sin(sh.fold) : 1;
}

// A Blackman-Harris windowed sinc, 32 taps per step of the factor, cut at the
// base rate's Nyquist and normalised to a gain of one.
inline std::vector<double> lowpassTaps(int factor) {
  const int n = 32 * factor;
  std::vector<double> h(static_cast<std::size_t>(n));
  const double centre = (n - 1) / 2.0, fc = 0.5 / factor;
  double sum = 0;
  for (int i = 0; i < n; i++) {
    const double t = i - centre;
    const double sinc = t == 0 ? 2 * fc : std::sin(2 * kPi * fc * t) / (kPi * t);
    const double a = 2 * kPi * i / (n - 1);
    h[static_cast<std::size_t>(i)] =
        sinc * (0.35875 - 0.48829 * std::cos(a) + 0.14128 * std::cos(2 * a) - 0.01168 * std::cos(3 * a));
    sum += h[static_cast<std::size_t>(i)];
  }
  for (auto& v : h) v /= sum;
  return h;
}

// One voice's oversampled shaper: up by `factor`, shaped, filtered and back
// down. Both histories are rings written twice, a length apart, as in the
// page, so the newest samples are always one unbroken run.
class Shaper {
 public:
  Shaper(int factor, const std::vector<double>& taps)
      : factor_(factor), n_(32 * factor), half_(n_ / 2), h_(taps),
        inX_(2 * kPer, 0.0), up_(static_cast<std::size_t>(2 * n_), 0.0) {}

  int factor() const { return factor_; }

  double step(double x, const Shaping& sh) {
    pos_ = pos_ == 0 ? kPer - 1 : pos_ - 1;
    inX_[pos_] = x; inX_[pos_ + kPer] = x;
    for (int p = 0; p < factor_; p++) {
      double u = 0;
      for (std::size_t k = 0; k < kPer; k++) u += h_[static_cast<std::size_t>(p) + k * static_cast<std::size_t>(factor_)] * inX_[pos_ + k];
      const double y = shapeSample(sh, u * factor_);
      up_[at_] = y; up_[at_ + static_cast<std::size_t>(n_)] = y;
      at_ = at_ + 1 == static_cast<std::size_t>(n_) ? 0 : at_ + 1;
    }
    const std::size_t base = at_ + static_cast<std::size_t>(n_) - 1;
    double d = 0;
    for (std::size_t k = 0; k < static_cast<std::size_t>(half_); k++) {
      d += h_[k] * (up_[base - k] + up_[base - static_cast<std::size_t>(n_) + 1 + k]);
    }
    return d;
  }

 private:
  static constexpr std::size_t kPer = 32;
  int factor_, n_, half_;
  std::vector<double> h_;
  std::vector<double> inX_, up_;
  std::size_t pos_ = 0, at_ = 0;
};

// The crush: held at `crushHz`, then quantised to the layer's step.
struct Crush { double acc = 1, held = 0; };

inline double crushStep(Crush& c, double x, const VoiceTone& t, const VoiceFx& vx, double rate) {
  if (t.crushHz > 0) {
    c.acc += t.crushHz / rate;
    if (c.acc >= 1) { c.acc -= std::floor(c.acc); c.held = x; }
    x = c.held;
  }
  if (vx.crushQ > 0) x = jsRound(x * vx.crushQ) / vx.crushQ;
  return x;
}

}  // namespace scope
