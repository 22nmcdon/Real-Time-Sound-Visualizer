// The plane, ported from inside `makeGeneratorCore` in web/scope.html:
// `planeOp` (mirror, twist, kaleidoscope, the clip or fold at a radius, the
// snap), the echo and chorus (`makeTimeFx`, `readLine`, `timeStep`), the
// non-linear stage's oversampler (`makeOversampler`), and the three calls the
// block makes of it - `planeSetup`, `planeTick` and `planeStep`. One plane for
// three pairs: layer A's picture, layer B's, and the heard pair, each with its
// own oversampler and its own delay lines. Layer B can have a shape and a time
// stage of its own (the page's `shapeOfB` and `timeOfB`), and then its share
// of the heard pair goes through a fourth oversampler and fourth lines, and
// is added to A's.
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

// The fields of a layer's tone that bend its pair, which layer B has its own
// of; the page's defaults.
struct PlaneShapeTone {
  int planeMirror = 0;  // a bitmask: 1 folds X onto its positive half, 2 folds Y
  double planeRadius = 0.4;
  int planeLimit = 0;  // 0 nothing, 1 the clip, 2 the fold
  double planeScaleX = 1, planeScaleY = 1, planeShear = 0;
  double planeTwist = 0, planeKaleido = 0, planeSnap = 0;
};

// And its echo and chorus, which layer B has its own of too.
struct PlaneTimeTone {
  double delayMix = 0, delayMs = 375, delayFeedback = 0.35;
  bool delayPingPong = false;
  double chorusMix = 0, chorusRate = 0.6, chorusDepthMs = 3, chorusMs = 12, chorusFeedback = 0;
};

// What a layer has of the plane: layer B's own is this.
struct PlaneLayerTone : PlaneShapeTone, PlaneTimeTone {};

// The fields of layer A's tone the plane reads: its own, and the
// oversampling, which is one for the page.
struct PlaneTone : PlaneLayerTone {
  double planeOS = 2;
};

// A sample's pushes from the routings onto a layer's plane, as the page's
// accumulator holds them.
struct PlanePushes { double radius = 0, twist = 0, echo = 0, echoTime = 0, turn = 0; };

class Plane {
 public:
  enum Pair { A = 0, B = 1, Heard = 2, HeardB = 3 };

  // A layer's shape as `setup` and `tick` work it out: the page's `planeOf`.
  struct Shape {
    bool linear = false, nonlinear = false;
    int mirror = 0, limit = 0;
    double kaleido = 0, snap = 0, radius = 0, twist = 0, sx = 1, sy = 1, shear = 0, turn = 0, tc = 1, ts = 0;
  };
  // And its time stage: the page's `timeOf`.
  struct Time {
    const PlaneTimeTone* t = nullptr;
    bool on = false, delayOn = false;
    double echo = 0, echoMs = 375, phase = 0, sin = 0, cos = 1;
  };

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

  // What the plane does this block; true if it does anything. `b` is layer
  // B's own plane when it has one in force (the page's `withB` and
  // `planeOwn` both), and `turnB` its turn in radians.
  bool setup(const PlaneTone& t, bool twistRouted, bool echoRouted, const PlaneLayerTone* b = nullptr,
             double turnB = 0, bool turnRouted = false) {
    const int want = t.planeOS == 4 ? 4 : t.planeOS == 1 ? 1 : 2;
    if (want != factor_) {
      factor_ = want;
      for (auto& os : os_) os.reset(want, want == 4 ? taps4_ : taps2_);
    }
    shapeSet(shapeA_, t, twistRouted, 0);
    ownB_ = b != nullptr;
    if (ownB_) shapeSet(shapeB_, *b, twistRouted, turnB);
    turnRoutedB_ = turnRouted;  // read only where B has its own
    turnB_ = turnB;
    linearOn_ = shapeA_.linear || (ownB_ && (shapeB_.linear || shapeB_.turn != 0 || turnRoutedB_));
    nonlinearOn_ = shapeA_.nonlinear || (ownB_ && shapeB_.nonlinear);
    timeSet(timeA_, t, echoRouted);
    if (ownB_) timeSet(timeB_, *b, echoRouted);
    timeOn_ = timeA_.on || (ownB_ && timeB_.on);
    return linearOn_ || nonlinearOn_ || timeOn_;
  }

  // This sample's radius, twist and echo from their pushes, and the chorus's
  // sweep; layer B's own from B's pushes, through B's fade.
  void tick(const PlaneTone& t, const PlanePushes& a, double dt, const PlaneLayerTone* b = nullptr,
            const PlanePushes& pb = {}) {
    shapeA_.radius = std::fmax(0.02, std::fmin(1.0, t.planeRadius + a.radius * 0.5));
    shapeA_.twist = std::fmax(-kTwoPi, std::fmin(kTwoPi, t.planeTwist + a.twist * kPi));
    if (ownB_ && b) {
      shapeB_.radius = std::fmax(0.02, std::fmin(1.0, b->planeRadius + pb.radius * 0.5));
      shapeB_.twist = std::fmax(-kTwoPi, std::fmin(kTwoPi, b->planeTwist + pb.twist * kPi));
      // B's turn under a routing, a sample at a time.
      if (turnRoutedB_) {
        const double turn = turnB_ + pb.turn * kPi;
        shapeB_.turn = turn; shapeB_.tc = std::cos(turn); shapeB_.ts = std::sin(turn);
      }
    }
    timeTick(timeA_, a, dt);
    if (ownB_ && b) timeTick(timeB_, pb, dt);
  }

  // A pair through the whole of it: the matrix, the non-linear stage inside
  // the oversampling, layer B's turn, then the chorus and the delay. Through
  // layer B's own when `layerB` and B has its own, A's otherwise. The
  // answer is `x`, `y`.
  void step(Pair pair, double x, double y, bool layerB = false) {
    const bool own = layerB && ownB_;
    const Shape& s = own ? shapeB_ : shapeA_;
    const Time& T = own ? timeB_ : timeA_;
    if (s.linear) {
      const double sheared = x + s.shear * y;
      x = s.sx * sheared; y = s.sy * y;
    }
    if (s.nonlinear) {
      cur_ = &s;
      if (factor_ == 1) { op(x, y); x = this->x; y = this->y; }
      else { os_[pair].step(*this, x, y); x = os_[pair].outX; y = os_[pair].outY; }
    }
    if (s.turn != 0) {
      const double tx = x * s.tc - y * s.ts;
      y = x * s.ts + y * s.tc; x = tx;
    }
    if (T.on) { timeStep(fx_[pair], T, x, y); x = this->x; y = this->y; }
    this->x = x; this->y = y;
  }

  double x = 0, y = 0;

  // Whether layer B's own plane is in force this block.
  bool ownB() const { return ownB_; }
  const Shape& shapeB() const { return shapeB_; }
  const Time& timeB() const { return timeB_; }

  // What the governor costs it by: the factor, and which stages are on.
  int factor() const { return factor_; }
  bool nonlinearOn() const { return nonlinearOn_; }
  bool timeOn() const { return timeOn_; }

 private:
  // A routing on the echo's level keeps the line running at nought.
  static void timeSet(Time& T, const PlaneTimeTone& t, bool echoRouted) {
    T.t = &t;
    T.delayOn = t.delayMix > 0 || echoRouted;
    T.on = T.delayOn || t.chorusMix > 0;
  }
  void timeTick(Time& T, const PlanePushes& p, double dt) {
    const PlaneTimeTone& t = *T.t;
    if (T.delayOn) {
      T.echo = std::fmax(0.0, std::fmin(1.0, t.delayMix + p.echo * 0.5));
      T.echoMs = p.echoTime == 0 ? t.delayMs : t.delayMs * std::pow(2.0, p.echoTime);
    }
    if (t.chorusMix > 0) {
      T.phase += kTwoPi * t.chorusRate * dt;
      if (T.phase >= kTwoPi) T.phase -= kTwoPi;
      T.sin = std::sin(T.phase); T.cos = std::cos(T.phase);
    }
  }

  static void shapeSet(Shape& s, const PlaneShapeTone& t, bool twistRouted, double turn) {
    s.linear = t.planeScaleX != 1 || t.planeScaleY != 1 || t.planeShear != 0;
    s.nonlinear = t.planeMirror != 0 || t.planeLimit != 0 || t.planeTwist != 0 || twistRouted || t.planeKaleido > 1 ||
                  t.planeSnap > 0;
    s.mirror = t.planeMirror;
    s.limit = t.planeLimit;
    s.kaleido = t.planeKaleido;
    s.snap = t.planeSnap > 0 ? 2 / std::pow(2.0, t.planeSnap) : 0;
    s.sx = t.planeScaleX; s.sy = t.planeScaleY; s.shear = t.planeShear;
    s.turn = turn; s.tc = std::cos(turn); s.ts = std::sin(turn);
  }

  // Leaves its answer in `x`, `y`, where the oversampler reads it. Applies
  // `cur_`, the shape `step` was given.
  void op(double x, double y) {
    const int mirror_ = cur_->mirror, limit_ = cur_->limit;
    const double kaleido_ = cur_->kaleido, snap_ = cur_->snap, radius_ = cur_->radius, twist_ = cur_->twist;
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

  void timeStep(TimeFx& fx, const Time& T, double x, double y) {
    const PlaneTimeTone& t = *T.t;
    if (t.chorusMix > 0) {
      const double base = t.chorusMs * rate_ / 1000, depth = t.chorusDepthMs * rate_ / 1000;
      const double lim = chorusMax_ - 3;
      const double wl = readLine(fx.cl, fx.cw, std::fmax(1.0, std::fmin(lim, base + depth * T.sin)), chorusMax_);
      const double wr = readLine(fx.cr, fx.cw, std::fmax(1.0, std::fmin(lim, base + depth * T.cos)), chorusMax_);
      const double fb = std::fmax(0.0, std::fmin(0.9, t.chorusFeedback));
      fx.cl[static_cast<std::size_t>(fx.cw)] = static_cast<float>(x + fb * wl);
      fx.cr[static_cast<std::size_t>(fx.cw)] = static_cast<float>(y + fb * wr);
      fx.cw = fx.cw + 1 == chorusMax_ ? 0 : fx.cw + 1;
      const double m = t.chorusMix;
      x = x * (1 - m / 2) + wl * m / 2; y = y * (1 - m / 2) + wr * m / 2;
    }
    if (T.delayOn) {
      const double want = std::fmax(1.0, std::fmin(static_cast<double>(delayMax_ - 3), T.echoMs * rate_ / 1000));
      fx.dNow = fx.dNow < 0 ? want : fx.dNow + (want - fx.dNow) * delayGlide_;
      const double echoL = readLine(fx.dl, fx.dw, fx.dNow, delayMax_);
      const double echoR = readLine(fx.dr, fx.dw, fx.dNow, delayMax_);
      const double fb = std::fmax(0.0, std::fmin(0.9, t.delayFeedback));
      const auto w = static_cast<std::size_t>(fx.dw);
      if (t.delayPingPong) { fx.dl[w] = static_cast<float>(x + fb * echoR); fx.dr[w] = static_cast<float>(y + fb * echoL); }
      else { fx.dl[w] = static_cast<float>(x + fb * echoL); fx.dr[w] = static_cast<float>(y + fb * echoR); }
      fx.dw = fx.dw + 1 == delayMax_ ? 0 : fx.dw + 1;
      x += T.echo * echoL; y += T.echo * echoR;
    }
    this->x = x; this->y = y;
  }

  double rate_;
  int delayMax_, chorusMax_;
  double delayGlide_;
  std::vector<double> taps2_, taps4_;
  int factor_ = 0;
  std::array<Oversampler, 4> os_;
  std::array<TimeFx, 4> fx_;
  bool linearOn_ = false, nonlinearOn_ = false, timeOn_ = false, ownB_ = false, turnRoutedB_ = false;
  double turnB_ = 0;
  Shape shapeA_, shapeB_;
  const Shape* cur_ = &shapeA_;
  Time timeA_, timeB_;
};

}  // namespace scope
