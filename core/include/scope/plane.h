// The plane, ported from inside `makeGeneratorCore` in web/scope.html:
// `planeOp` (mirror, twist, kaleidoscope, the clip or fold at a radius, the
// snap), the echo and chorus (`makeTimeFx`, `readLine`, `timeStep`), the
// non-linear stage's oversampler (`makeOversampler`), and the three calls the
// block makes of it - `planeSetup`, `planeTick` and `planeStep`. One plane for
// three pairs: layer A's picture, layer B's, and the heard pair, each with its
// own oversampler and its own delay lines.
//
// Two decisions that differ from the page, neither audible:
//
// - The page makes a pair's delay lines the first time they are wanted, two
//   seconds of them, and keeps them. Here they are made with the plane, since
//   allocating on the audio thread is how a plugin glitches. A line made early
//   holds noughts until it is first written, which is what a line made late
//   starts with, so nothing it plays differs.
// - The page makes new oversamplers when the factor changes, and the change
//   empties their histories. Here they are emptied in place, at the largest
//   size, for the same reason.
//
// The delay lines are Float32Arrays in the page, so they are `float` here: a
// line of doubles would play back values the page never stored.

#pragma once

#include <array>
#include <cmath>
#include <vector>

#include "scope/voice.h"
#include "scope/wave.h"

namespace scope {

// The fields of layer A's tone the plane reads; the page's defaults.
struct PlaneTone {
  int planeMirror = 0;  // a bitmask: 1 folds X onto its positive half, 2 folds Y
  double planeRadius = 0.4;
  double planeOS = 2;
  int planeLimit = 0;  // 0 nothing, 1 the clip, 2 the fold
  double planeScaleX = 1, planeScaleY = 1, planeShear = 0;
  double planeTwist = 0, planeKaleido = 0, planeSnap = 0;
  double delayMix = 0, delayMs = 375, delayFeedback = 0.35;
  bool delayPingPong = false;
  double chorusMix = 0, chorusRate = 0.6, chorusDepthMs = 3, chorusMs = 12, chorusFeedback = 0;
};

class Plane {
 public:
  enum Pair { A = 0, B = 1, Heard = 2 };

  explicit Plane(double rate)
      : rate_(rate), delayMax_(static_cast<int>(std::ceil(2 * rate)) + 4),
        chorusMax_(static_cast<int>(std::ceil(0.05 * rate)) + 4),
        delayGlide_(1 - std::exp(-1 / std::fmax(1.0, 50 * rate / 1000))),
        taps2_(lowpassTaps(2)), taps4_(lowpassTaps(4)) {
    for (auto& fx : fx_) {
      fx.dl.assign(static_cast<std::size_t>(delayMax_), 0.0f);
      fx.dr.assign(static_cast<std::size_t>(delayMax_), 0.0f);
      fx.cl.assign(static_cast<std::size_t>(chorusMax_), 0.0f);
      fx.cr.assign(static_cast<std::size_t>(chorusMax_), 0.0f);
    }
  }

  // What the plane does this block; true if it does anything.
  bool setup(const PlaneTone& t, bool twistRouted, bool echoRouted) {
    const int want = t.planeOS == 4 ? 4 : t.planeOS == 1 ? 1 : 2;
    if (want != factor_) {
      factor_ = want;
      for (auto& os : os_) os.reset(want, want == 4 ? taps4_ : taps2_);
    }
    linearOn_ = t.planeScaleX != 1 || t.planeScaleY != 1 || t.planeShear != 0;
    nonlinearOn_ = t.planeMirror != 0 || t.planeLimit != 0 || t.planeTwist != 0 || twistRouted || t.planeKaleido > 1 ||
                   t.planeSnap > 0;
    delayOn_ = t.delayMix > 0 || echoRouted;
    timeOn_ = delayOn_ || t.chorusMix > 0;
    mirror_ = t.planeMirror;
    limit_ = t.planeLimit;
    kaleido_ = t.planeKaleido;
    snap_ = t.planeSnap > 0 ? 2 / std::pow(2.0, t.planeSnap) : 0;
    return linearOn_ || nonlinearOn_ || timeOn_;
  }

  // This sample's radius, twist and echo from their pushes, and the chorus's
  // sweep. The pushes are the routings' sums, as the page's accumulator holds
  // them.
  void tick(const PlaneTone& t, double radiusPush, double twistPush, double echoPush, double echoTimePush, double dt) {
    radius_ = std::fmax(0.02, std::fmin(1.0, t.planeRadius + radiusPush * 0.5));
    twist_ = std::fmax(-kTwoPi, std::fmin(kTwoPi, t.planeTwist + twistPush * kPi));
    if (delayOn_) {
      echo_ = std::fmax(0.0, std::fmin(1.0, t.delayMix + echoPush * 0.5));
      echoMs_ = echoTimePush == 0 ? t.delayMs : t.delayMs * std::pow(2.0, echoTimePush);
    }
    if (t.chorusMix > 0) {
      chorusPhase_ += kTwoPi * t.chorusRate * dt;
      if (chorusPhase_ >= kTwoPi) chorusPhase_ -= kTwoPi;
      chorusSin_ = std::sin(chorusPhase_); chorusCos_ = std::cos(chorusPhase_);
    }
  }

  // A pair through the whole of it: the matrix, the non-linear stage inside
  // the oversampling, then the chorus and the delay. The answer is `x`, `y`.
  void step(Pair pair, const PlaneTone& t, double x, double y) {
    if (linearOn_) {
      const double sheared = x + t.planeShear * y;
      x = t.planeScaleX * sheared; y = t.planeScaleY * y;
    }
    if (nonlinearOn_) {
      if (factor_ == 1) { op(x, y); x = this->x; y = this->y; }
      else { os_[pair].step(*this, x, y); x = os_[pair].outX; y = os_[pair].outY; }
    }
    if (timeOn_) { timeStep(fx_[pair], t, x, y); x = this->x; y = this->y; }
    this->x = x; this->y = y;
  }

  double x = 0, y = 0;

  // What the governor costs it by: the factor, and which stages are on.
  int factor() const { return factor_; }
  bool nonlinearOn() const { return nonlinearOn_; }
  bool timeOn() const { return timeOn_; }

 private:
  // Leaves its answer in `x`, `y`, where the oversampler reads it.
  void op(double x, double y) {
    if (mirror_ & 1) x = std::fabs(x);
    if (mirror_ & 2) y = std::fabs(y);
    if (twist_ != 0) {
      const double a = twist_ * std::sqrt(x * x + y * y), c = std::cos(a), s = std::sin(a);
      const double tx = x * c - y * s;
      y = x * s + y * c; x = tx;
    }
    if (kaleido_ > 1) {
      const double m = std::sqrt(x * x + y * y);
      if (m > 0) {
        const double wedge = kTwoPi / kaleido_;
        double a = std::fmod(std::atan2(y, x), wedge);
        if (a < 0) a += wedge;
        if (a > wedge / 2) a = wedge - a;
        x = m * std::cos(a); y = m * std::sin(a);
      }
    }
    if (limit_ != 0) {
      const double m = std::sqrt(x * x + y * y);
      if (m > 0) {
        double to;
        if (limit_ == 1) to = radius_ * std::tanh(m / radius_);
        else { const double t = std::fmod(m, 2 * radius_); to = t <= radius_ ? t : 2 * radius_ - t; }
        const double k = to / m; x *= k; y *= k;
      }
    }
    if (snap_ > 0) { x = jsRound(x / snap_) * snap_; y = jsRound(y / snap_) * snap_; }
    this->x = x; this->y = y;
  }

  // The page's oversampler: the base-rate history shifted along, the
  // oversampled one a ring.
  struct Oversampler {
    static constexpr int kPer = 32;
    int factor = 2, n = 64, at = 0;
    const std::vector<double>* h = nullptr;
    std::array<double, kPer> inX {}, inY {};
    std::array<double, 128> upX {}, upY {};
    double outX = 0, outY = 0;
    void reset(int f, const std::vector<double>& taps) {
      factor = f; n = 32 * f; at = 0; h = &taps;
      inX.fill(0); inY.fill(0); upX.fill(0); upY.fill(0);
    }
    void step(Plane& plane, double x, double y) {
      const auto& c = *h;
      for (int k = kPer - 1; k > 0; k--) { inX[k] = inX[k - 1]; inY[k] = inY[k - 1]; }
      inX[0] = x; inY[0] = y;
      for (int p = 0; p < factor; p++) {
        double ux = 0, uy = 0;
        for (int k = 0; k < kPer; k++) {
          const double tap = c[static_cast<std::size_t>(p + k * factor)];
          ux += tap * inX[k]; uy += tap * inY[k];
        }
        plane.op(ux * factor, uy * factor);
        upX[at] = plane.x; upY[at] = plane.y;
        at = at + 1 == n ? 0 : at + 1;
      }
      double dx = 0, dy = 0;
      int j = at;
      for (int k = 0; k < n; k++) {
        j = j == 0 ? n - 1 : j - 1;
        dx += c[static_cast<std::size_t>(k)] * upX[j]; dy += c[static_cast<std::size_t>(k)] * upY[j];
      }
      outX = dx; outY = dy;
    }
  };

  struct TimeFx {
    std::vector<float> dl, dr, cl, cr;
    int dw = 0, cw = 0;
    double dNow = -1;
  };

  static double readLine(const std::vector<float>& buf, int w, double d, int size) {
    double at = w - d;
    while (at < 0) at += size;
    const double i = std::floor(at), f = at - i;
    const int k = static_cast<int>(i), j = k + 1 == size ? 0 : k + 1;
    const double a = buf[static_cast<std::size_t>(k)], b = buf[static_cast<std::size_t>(j)];
    return a + (b - a) * f;
  }

  void timeStep(TimeFx& fx, const PlaneTone& t, double x, double y) {
    if (t.chorusMix > 0) {
      const double base = t.chorusMs * rate_ / 1000, depth = t.chorusDepthMs * rate_ / 1000;
      const double lim = chorusMax_ - 3;
      const double wl = readLine(fx.cl, fx.cw, std::fmax(1.0, std::fmin(lim, base + depth * chorusSin_)), chorusMax_);
      const double wr = readLine(fx.cr, fx.cw, std::fmax(1.0, std::fmin(lim, base + depth * chorusCos_)), chorusMax_);
      const double fb = std::fmax(0.0, std::fmin(0.9, t.chorusFeedback));
      fx.cl[static_cast<std::size_t>(fx.cw)] = static_cast<float>(x + fb * wl);
      fx.cr[static_cast<std::size_t>(fx.cw)] = static_cast<float>(y + fb * wr);
      fx.cw = fx.cw + 1 == chorusMax_ ? 0 : fx.cw + 1;
      const double m = t.chorusMix;
      x = x * (1 - m / 2) + wl * m / 2; y = y * (1 - m / 2) + wr * m / 2;
    }
    if (delayOn_) {
      const double want = std::fmax(1.0, std::fmin(static_cast<double>(delayMax_ - 3), echoMs_ * rate_ / 1000));
      fx.dNow = fx.dNow < 0 ? want : fx.dNow + (want - fx.dNow) * delayGlide_;
      const double echoL = readLine(fx.dl, fx.dw, fx.dNow, delayMax_);
      const double echoR = readLine(fx.dr, fx.dw, fx.dNow, delayMax_);
      const double fb = std::fmax(0.0, std::fmin(0.9, t.delayFeedback));
      const auto w = static_cast<std::size_t>(fx.dw);
      if (t.delayPingPong) { fx.dl[w] = static_cast<float>(x + fb * echoR); fx.dr[w] = static_cast<float>(y + fb * echoL); }
      else { fx.dl[w] = static_cast<float>(x + fb * echoL); fx.dr[w] = static_cast<float>(y + fb * echoR); }
      fx.dw = fx.dw + 1 == delayMax_ ? 0 : fx.dw + 1;
      x += echo_ * echoL; y += echo_ * echoR;
    }
    this->x = x; this->y = y;
  }

  double rate_;
  int delayMax_, chorusMax_;
  double delayGlide_;
  std::vector<double> taps2_, taps4_;
  int factor_ = 0;
  std::array<Oversampler, 3> os_;
  std::array<TimeFx, 3> fx_;
  bool linearOn_ = false, nonlinearOn_ = false, timeOn_ = false, delayOn_ = false;
  int mirror_ = 0, limit_ = 0;
  double kaleido_ = 0, snap_ = 0, radius_ = 0, twist_ = 0;
  double chorusPhase_ = 0, chorusSin_ = 0, chorusCos_ = 1, echo_ = 0, echoMs_ = 375;
};

}  // namespace scope
