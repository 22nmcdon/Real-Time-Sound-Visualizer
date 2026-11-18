// The drawn envelope (MSEG, 18 Nov): a shape of points between the knobs,
// played by the one-pole the old envelope is made of.
//
// web/docs/mseg-design.md is the design and says why; this is the engine it
// describes. The old `Envelope` (envelope.h) stays as the tests' reference:
// the shape the version-13 decode pass writes for every old setup,
// "1;A>p.2;D>p.2;R>a.2", plays here sample for sample what that class plays,
// to the bit (core/tests/pieces/mseg.py holds it with its nulls). That is why
// this is a recursion and not the analytic curve the drawing uses: the old
// envelope ends a stage on the first sample at or past its end, which after
// rounding is sometimes a sample after the drawn time, and a note let go
// then carries the difference into its release.
//
// The shape is RELATIVE TO THE KNOBS. Five stretches - the delay (W, a
// wait), the attack, the hold, the decay and the release - are each as long
// as their knob says, and the points drawn inside one are kept as a share of
// its time, a level and a bend, so a knob turned stretches its points with
// it. The anchors are not stored: silence at the start and at the end of the
// delay and the release, full scale at the end of the attack and the hold,
// and the Sustain knob's level at the end of the decay. A point is reached by
// a setup, a preset and undo only; a host, a routing and the morph's walk
// reach the knobs.
//
// The text (the setup's `envShape`, `vcfShape`, `menvShape` and the upper
// hand's twins), version first:
//
//   1;A>p.2;D>p.2;R>a.2                           the old envelope
//   1;A>m.62;D.4,.18,m.72>m.3;R.35,.35,m.65>a.2;L3   points, a loop
//
// then a block per stretch that is not plain - its letter, its inner points
// as `u,level,bend` triples, `>` and the bend of its last segment - and
// `L<n>` a loop back to point n while held, `S<n>` the point the shape holds
// at while the key is down (the decay's end when absent), or `S-` none, a
// one-shot that plays through whatever the key does. A block left out is a
// straight segment with no points. Points are numbered over the whole shape:
// 0 the start, then each stretch's inner points and its end, in order, the
// zero-length delay's and hold's included, so a number does not move when a
// knob turns.
//
// Bends: `m<mid>` a drawn midpoint, the level reached half-way as a share of
// the fall (0.1 to 0.9; 0.5 straight), `p<rho>` an aim past the end as a
// share of the drawn fall (the old attack's and decay's), `a<r>` an aim past
// the end in full scale (the old release's), `l` straight. A midpoint is an
// aim by k = 2 ln(m / (1 - m)), rho = 1 / (e^k - 1): the old curves are a
// midpoint of 0.710.

#pragma once

#include <algorithm>
#include <cmath>
#include <cstdint>

#include "scope/envelope.h"
#include "scope/mseg_shape.h"

namespace scope {

// The times the shape's five stretches read, per sample (envelope.h's EnvelopeTone, with the two new ones).
inline double msegStretchMs(const EnvelopeTone& t, int s) {
  return s == kMsegDelay ? t.delayMs : s == kMsegAttack ? t.attackMs : s == kMsegHold ? t.holdMs
       : s == kMsegDecay ? t.decayMs : t.releaseMs;
}

class Mseg {
 public:
  using Stage = Envelope::Stage;

  // The tone (its times and its shape) is read per sample, as the old
  // envelope's is, so a knob moved mid-note takes effect mid-note.
  Mseg(double rate, const EnvelopeTone& tone) : rate_(rate), tone_(&tone), serial_(tone.shape.serial) {}

  double step() {
    if (tone_->shape.serial != serial_) resync();
    if (idle_ || holding_) return value_ * velocity_;
    const MsegShape& sh = tone_->shape;
    const MsegSegment& g = sh.seg[static_cast<std::size_t>(seg_)];
    const double ms = msegStretchMs(*tone_, g.stretch) * g.share;
    const double samples = std::fmax(1.0, ms * rate_ / 1000.0);
    x_ += 1 / samples;
    if (line_) {
      value_ = from_ + (end_ - from_) * std::fmin(1.0, x_);
      if (x_ >= 1 - 1e-12) { value_ = end_; arrive(seg_ + 1); }
    } else {
      value_ += (target_ - value_) * (1.0 - std::exp(-span_ / samples));
      if (rising_ ? value_ >= end_ : value_ <= end_) { value_ = end_; arrive(seg_ + 1); }
    }
    return value_ * velocity_;
  }

  /* The legato rule, as the old envelope's: a note arriving while the
     envelope is open changes nothing, and keeps the velocity of the note that
     opened it. A key let go before the sustain point goes on from the segment
     after it, from where the level is; a one-shot pays the key no mind once
     it has started, and starts again only for a key struck afresh. */
  void gate(bool open, double vel) {
    const MsegShape& sh = tone_->shape;
    if (!open) {
      held_ = false;
      if (idle_ || sh.oneShot()) return;
      if (holding_ || seg_ < sh.sustainPt) { holding_ = false; enter(sh.sustainPt); }
      return;
    }
    const bool was = held_;
    held_ = true;
    if (idle_ || releasing() || (sh.oneShot() && !was)) {
      velocity_ = vel > 0 ? vel : 1;
      idle_ = false; holding_ = false;
      enter(0);
    }
  }

  void reset(double to) { idle_ = true; holding_ = false; held_ = false; value_ = to; velocity_ = 1; seg_ = 0; x_ = 0; }

  double level() const { return value_ * velocity_; }
  double velocity() const { return velocity_; }
  // The old envelope's five stages, for what reads them (a voice let go and
  // silent, the Envelope card's dot): before the sustain point the delay and
  // attack are the attack and the rest the decay, after it the release.
  Stage stage() const {
    if (idle_) return Stage::Idle;
    if (holding_) return Stage::Sustain;
    const MsegShape& sh = tone_->shape;
    if (releasing()) return Stage::Release;
    const int s = sh.seg[static_cast<std::size_t>(seg_)].stretch;
    if (sh.oneShot() && s == kMsegRelease) return Stage::Release;
    return s <= kMsegAttack ? Stage::Attack : Stage::Decay;
  }
  // Where on the shape it is, for the face's dot: the segment and how far
  // through its time, or the point it holds at; -1 idle.
  int segment() const { return idle_ ? -1 : seg_; }
  double progress() const { return holding_ ? 0 : std::fmin(1.0, x_); }
  bool holding() const { return holding_; }

 private:
  bool releasing() const {
    const MsegShape& sh = tone_->shape;
    return !idle_ && !holding_ && !sh.oneShot() && seg_ >= sh.sustainPt;
  }

  // Arrived at point pt: hold there, loop back, end, or go on.
  void arrive(int pt) {
    const MsegShape& sh = tone_->shape;
    if (pt == sh.sustainPt && held_) {
      if (sh.loopPt >= 0) { enter(sh.loopPt); return; }
      holding_ = true; seg_ = pt; x_ = 0;
      return;
    }
    enter(pt);
  }

  /* Segment i entered from where the level is, keeping its time and its aim
     (the old enterStage, generalised): a stretch entered from anywhere else
     - a release while the attack still rises, a loop's return, a retrigger -
     travels from there and arrives on time. A segment already at or past its
     end jumps to it, as the old one did; one entered from behind its aim,
     which the law cannot carry to its end, goes straight from where it is.
     A zero-length delay or hold costs a skipped segment; every other segment
     takes at least a sample, as the old attack of nought did. */
  void enter(int i) {
    const MsegShape& sh = tone_->shape;
    for (int guard = 0; guard <= 2 * kMsegMaxSegments; guard++) {
      if (i >= sh.count) { idle_ = true; holding_ = false; seg_ = sh.count > 0 ? sh.count - 1 : 0; x_ = 1; return; }
      seg_ = i; x_ = 0; holding_ = false;
      const MsegSegment& g = sh.seg[static_cast<std::size_t>(i)];
      bool jump = (g.stretch == kMsegDelay || g.stretch == kMsegHold) && !(msegStretchMs(*tone_, g.stretch) > 0);
      if (!jump) {
        const double sus = tone_->sustain;
        const double a = msegPointLevel(sh, i, sus), b = msegPointLevel(sh, i + 1, sus);
        end_ = b;
        double aim = 0;
        if (!msegAim(a, b, g.bend, aim)) { line_ = true; from_ = value_; return; }
        line_ = false;
        target_ = aim;
        const double from = std::fabs(value_ - aim), to = std::fabs(b - aim);
        if (g.bend.law == 'm' && msegRho(g.bend.v) < 0) {
          // Slow to start: the aim lies behind the start, and the level moves away from it.
          const double r = (b - aim) / (value_ - aim);
          if (!(r > 0)) { line_ = true; from_ = value_; return; }
          jump = from >= to;
        } else {
          jump = to <= 1e-9 || from <= to;
        }
        if (jump) value_ = b;
        else {
          span_ = std::log(from / to);
          rising_ = b > value_;
          return;
        }
      }
      // At its end already: the next point, held at or looped from as arriving there in time would be.
      const int pt = i + 1;
      if (pt == sh.sustainPt && held_) {
        if (sh.loopPt < 0) { holding_ = true; seg_ = pt; x_ = 0; return; }
        i = sh.loopPt;
        continue;
      }
      i = pt;
    }
    holding_ = true;  // a loop of nothing but jumps: held where it is
  }

  /* The shape changed under a sounding note (a setup, the editor): go on
     from where the level is, in the segment it was in if it still has one. */
  void resync() {
    serial_ = tone_->shape.serial;
    if (idle_) return;
    const MsegShape& sh = tone_->shape;
    if (holding_) {
      if (held_ && sh.sustainPt >= 0) { seg_ = sh.sustainPt; return; }
      holding_ = false;
      enter(sh.oneShot() ? std::min(seg_, sh.count - 1) : sh.sustainPt);
      return;
    }
    enter(std::min(seg_, sh.count - 1));
  }

  double rate_;
  const EnvelopeTone* tone_;
  std::uint32_t serial_;
  bool idle_ = true, holding_ = false, held_ = false, line_ = false, rising_ = false;
  int seg_ = 0;
  double value_ = 1;
  double velocity_ = 1;
  double target_ = 0, end_ = 0, span_ = 1, from_ = 0, x_ = 0;
};

}  // namespace scope
