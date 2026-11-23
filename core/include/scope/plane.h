// The plane, ported from inside `makeGeneratorCore` in web/scope.html:
// `planeOp` (mirror, twist, the clip or fold at a radius, the
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

#include <algorithm>
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
  double planeTwist = 0, planeSnap = 0;
};

// And its echo and chorus, which layer B has its own of too.
struct PlaneTimeTone {
  double delayMix = 0, delayMs = 375, delayFeedback = 0.35;
  bool delayPingPong = false;
  // F5c: the repeats' tone (1 open), low cut (0 off), width (1 as it was) and wow (0 still).
  double delayTone = 1, delayLowCut = 0, delayWidth = 1, delayWow = 0;
  double chorusMix = 0, chorusRate = 0.6, chorusDepthMs = 3, chorusMs = 12, chorusFeedback = 0;
  // P8e, the phaser: amount, sweep in hertz, range (0 to 1 of its octaves), resonance.
  double phaserMix = 0, phaserRate = 0.3, phaserDepth = 0.7, phaserFeedback = 0.3;
  // F5b: which order the three run in after the plane, an index into kFxOrders.
  int fxOrder = 0;
  // P9, the reverb: its mix, size (0 to 1 of a log law of decay times), tone
  // (one open), pre-delay in milliseconds and spread (nought keeps the figure).
  double reverbMix = 0, reverbSize = 0.4, reverbTone = 0.6, reverbPreMs = 10, reverbSpread = 0;
  // The EQ (17 Nov): each band's gain in dB, nought for none, and where it
  // acts in hertz; the mid's width in octaves.
  double eqLow = 0, eqLowHz = 160, eqMid = 0, eqMidHz = 1000, eqMidWidth = 1, eqHigh = 0, eqHighHz = 4000;
  /* Its two cuts (23 Nov, the owner's five points): a low cut, Web Audio's
     highpass, and a high cut, its lowpass, each 12 dB an octave, where it
     acts in hertz and its resonance as a plain Q (the node takes it in
     decibels, 20 log10 of this). A cut at its end of the range - the low at
     20 Hz, the high at 20 kHz, where the knobs start - is out, as a gain of
     nought is, so an EQ with its cuts at their ends is the three bands to
     the bit. */
  double eqCutLowHz = 20, eqCutLowQ = 0.71, eqCutHighHz = 20000, eqCutHighQ = 0.71;
  /* Whether the EQ is in at all (17 Nov, the owner's): its switch is a field,
     the one rack module whose is, so an EQ switched off keeps its curve and a
     flat one switched on is ready to shape. Off, no band runs, whatever the
     gains: the same to the bit as no EQ. */
  bool eqOn = false;
};

/* The orders the phaser (p), the chorus (c) and the delay (d) can run in, as
   the page's FX_ORDER_STAGES: the first is the order they always had. A setup
   names its order by these letters (fxOrder) and the engine is given the
   index, which is never stored, so this table can grow without a saved code
   changing what it means. The plane is always first: its turn is the screen's
   rotation, which the trigger and the lanes see before anything copies it. */
inline constexpr const char* kFxOrders[] = { "pcd", "pdc", "cpd", "cdp", "dpc", "dcp" };
inline constexpr int kFxOrderCount = 6;

// What a layer has of the plane: layer B's own is this.
struct PlaneLayerTone : PlaneShapeTone, PlaneTimeTone {};

// The fields of layer A's tone the plane reads: its own, and the
// oversampling, which is one for the page.
struct PlaneTone : PlaneLayerTone {
  double planeOS = 2;
};

// A sample's pushes from the routings onto a layer's plane, as the page's
// accumulator holds them.
struct PlanePushes {
  double radius = 0, twist = 0, echo = 0, echoTime = 0, turn = 0, phaser = 0, delayTone = 0;
  double reverb = 0, reverbSize = 0, reverbTone = 0;  // P9
};

class Plane {
 public:
  // A pair a layer: since P4 the heard pair is the layers' pictures summed,
  // and no longer goes through the plane apart from them.
  enum Pair { A = 0, B = 1 };

  // A layer's shape as `setup` and `tick` work it out: the page's `planeOf`.
  struct Shape {
    bool linear = false, nonlinear = false;
    int mirror = 0, limit = 0;
    double snap = 0, radius = 0, twist = 0, sx = 1, sy = 1, shear = 0, turn = 0, tc = 1, ts = 0;
  };
  // And its time stage: the page's `timeOf`.
  struct Time {
    const PlaneTimeTone* t = nullptr;
    bool on = false, delayOn = false, phOn = false;
    double echo = 0, echoMs = 375, phase = 0, sin = 0, cos = 1;
    double ph = 0, phPhase = 0, aL = 0, aR = 0;  // the phaser's amount, sweep, and each channel's coefficient
    double toneA = 0, cutA = 0;                     // F5c: the repeats' one-poles, nought skipped
    double toneAt = NAN;                            // the tone the coefficient was last worked out for
    // P9, the reverb: on, its mix this sample, the size and tone last worked
    // out, each line's gain, the input's scale, the tone's one-pole, the
    // pre-delay in samples and Y's taps turned by the spread.
    bool revOn = false;
    double rev = 0, revSizeAt = NAN, revToneAt = NAN;
    std::array<double, 8> revG {};
    double revIn = 0, revDampA = 0, revC = 1, revS = 0;
    int revPre = 0;
    /* The EQ (17 Nov): which bands are in (1 the low shelf, 2 the mid, 4 the
       high shelf, and since 23 Nov 8 the low cut and 16 the high cut; a band
       at nought dB, or a cut at its end, is left out, so it is exact), and
       each band's coefficients, b0 b1 b2 a1 a2 over a0, worked out only when
       what they are made from moves. */
    int eqBands = 0;
    std::array<std::array<double, 5>, 5> eqC {};
    std::array<std::array<double, 2>, 5> eqAt { { { NAN, NAN }, { NAN, NAN }, { NAN, NAN }, { NAN, NAN }, { NAN, NAN } } };
    double eqWidthAt = NAN;
  };

  explicit Plane(double rate)
      : rate_(rate), reverbPreMax_(static_cast<int>(std::ceil(0.1 * rate)) + 4),
        delayMax_(static_cast<int>(std::ceil(2 * rate)) + 4),
        chorusMax_(static_cast<int>(std::ceil(0.05 * rate)) + 4),
        delayGlide_(1 - std::exp(-1 / std::fmax(1.0, 50 * rate / 1000))), phaserTop_(0.45 * rate),
        taps2_(lowpassTaps(2)), taps4_(lowpassTaps(4)) {
    for (auto& fx : fx_) {
      fx.dl.assign(static_cast<std::size_t>(delayMax_), 0.0f);
      fx.dr.assign(static_cast<std::size_t>(delayMax_), 0.0f);
      fx.cl.assign(static_cast<std::size_t>(chorusMax_), 0.0f);
      fx.cr.assign(static_cast<std::size_t>(chorusMax_), 0.0f);
    }
    // The reverb's lines, each layer's two channels, made here and not on the audio thread.
    for (int i = 0; i < kReverbLines; i++) reverbLen_[i] = std::max(1, static_cast<int>(jsRound(kReverbLineMs[i] * rate / 1000)));
    for (int k = 0; k < kReverbDiffusers; k++)
      reverbDiffuseLen_[k] = std::max(1, static_cast<int>(jsRound(kReverbDiffuseMs[k] * rate / 1000)));
    for (auto& fx : fx_) {
      for (auto* c : { &fx.rvx, &fx.rvy }) {
        c->pre.assign(static_cast<std::size_t>(reverbPreMax_), 0.0);
        for (int k = 0; k < kReverbDiffusers; k++) c->ap[k].assign(static_cast<std::size_t>(reverbDiffuseLen_[k]), 0.0);
        for (int i = 0; i < kReverbLines; i++) c->lines[i].assign(static_cast<std::size_t>(reverbLen_[i]), 0.0);
      }
    }
  }

  // What the plane does this block; true if it does anything. `b` is layer
  // B's tone when it has anything of its own in force (the page's `withB`),
  // `shapeOwn` whether that is its plane (`planeOwn`), with `turnB` its turn
  // in radians, and `timeOwn` which of its time modules (G6: 1 the phaser, 2
  // the chorus, 4 the delay, 8 the reverb; 16 the EQ since 17 Nov). A `b`
  // alone is all of them, as it was while B's own effects were one switch.
  bool setup(const PlaneTone& t, bool twistRouted, bool echoRouted, const PlaneLayerTone* b = nullptr,
             double turnB = 0, bool turnRouted = false, bool phaserRouted = false, bool reverbRouted = false,
             bool shapeOwn = true, int timeOwn = 31) {
    phaserRouted_ = phaserRouted;
    reverbRouted_ = reverbRouted;
    const int want = t.planeOS == 4 ? 4 : t.planeOS == 1 ? 1 : 2;
    if (want != factor_) {
      factor_ = want;
      for (auto& os : os_) os.reset(want, want == 4 ? taps4_ : taps2_);
    }
    shapeSet(shapeA_, t, twistRouted, 0);
    shapeOwnB_ = b != nullptr && shapeOwn;
    timeOwnB_ = b != nullptr ? timeOwn & 31 : 0;
    ownB_ = shapeOwnB_ || timeOwnB_ != 0;
    if (shapeOwnB_) shapeSet(shapeB_, *b, twistRouted, turnB);
    turnRoutedB_ = turnRouted;  // read only where B has its own
    turnB_ = turnB;
    linearOn_ = shapeA_.linear || (shapeOwnB_ && (shapeB_.linear || shapeB_.turn != 0 || turnRoutedB_));
    // Or a pair's stage still fading out, which has to be stepped to get there.
    nonlinearOn_ = shapeA_.nonlinear || (shapeOwnB_ && shapeB_.nonlinear) || nlIn_[0] > 0 || nlIn_[1] > 0;
    timeSet(timeA_, t, echoRouted);
    if (timeOwnB_ != 0) timeSet(timeB_, *b, echoRouted);
    timeOn_ = timeA_.on || (timeOwnB_ != 0 && timeB_.on);
    // A new block for the pairs' modules, as the page's planeSetup: asked of each pair as it is stepped.
    for (auto& fx : fx_) { fx.was = fx.ran; fx.ran = 0; }
    return linearOn_ || nonlinearOn_ || timeOn_;
  }

  // This sample's radius, twist and echo from their pushes, and the chorus's
  // sweep; layer B's own from B's pushes, through B's fade.
  void tick(const PlaneTone& t, const PlanePushes& a, double dt, const PlaneLayerTone* b = nullptr,
            const PlanePushes& pb = {}) {
    shapeA_.radius = std::fmax(0.02, std::fmin(1.0, t.planeRadius + a.radius * 0.5));
    shapeA_.twist = std::fmax(-kTwoPi, std::fmin(kTwoPi, t.planeTwist + a.twist * kPi));
    if (shapeOwnB_ && b) {
      shapeB_.radius = std::fmax(0.02, std::fmin(1.0, b->planeRadius + pb.radius * 0.5));
      shapeB_.twist = std::fmax(-kTwoPi, std::fmin(kTwoPi, b->planeTwist + pb.twist * kPi));
      // B's turn under a routing, a sample at a time.
      if (turnRoutedB_) {
        const double turn = turnB_ + pb.turn * kPi;
        shapeB_.turn = turn; shapeB_.tc = std::cos(turn); shapeB_.ts = std::sin(turn);
      }
    }
    timeTick(timeA_, a, dt);
    if (timeOwnB_ != 0 && b) { timeTick(timeB_, pb, dt); timeShare(timeB_, timeA_, timeOwnB_); }
  }

  // A pair through the whole of it: the matrix, the non-linear stage inside
  // the oversampling, layer B's turn, then the chorus and the delay. Through
  // layer B's own when `layerB` and B has its own, A's otherwise. The
  // answer is `x`, `y`.
  void step(Pair pair, double x, double y, bool layerB = false) {
    const Shape& s = layerB && shapeOwnB_ ? shapeB_ : shapeA_;
    const Time& T = layerB && timeOwnB_ != 0 ? timeB_ : timeA_;
    if (s.linear) {
      const double sheared = x + s.shear * y;
      x = s.sx * sheared; y = s.sy * y;
    }
    /* Crossfaded in and out over the switch time, a pair at a time, as
       the voice's shaper is: the oversampler is a delay of its own, so a
       stage switched straight in or out - a routing on the twist arriving,
       the Picture amount crossing nought - was a step (the page's
       planeStep says why). Its history is emptied as it comes in. */
    double& in = nlIn_[pair];
    int& wait = nlWait_[pair];
    if (!s.nonlinear) wait = 0;
    if (s.nonlinear || in > 0) {
      // Emptied as it comes in, then run unheard while it fills (kSwitchPrime), then crossfaded.
      bool priming = false;
      if (s.nonlinear && in == 0) {
        if (wait == 0) { wait = switchPrime_ + 1; if (factor_ != 1) os_[pair].clear(); }
        priming = --wait > 0;
      }
      if (!priming) in = s.nonlinear ? std::fmin(1.0, in + switchStep_) : std::fmax(0.0, in - switchStep_);
      if (priming || in > 0) {
        cur_ = &s;
        double nx, ny;
        if (factor_ == 1) { op(x, y); nx = this->x; ny = this->y; }
        else { os_[pair].step(*this, x, y); nx = os_[pair].outX; ny = os_[pair].outY; }
        x = switchBlend(x, nx, in);
        y = switchBlend(y, ny, in);
      }
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
  /* How late the non-linear stage puts the pair, in base samples, as the
     settings ask for it rather than where its crossfade has got to: an
     oversampler of 32 taps a step delays by (32f - f) / f, 31 at either
     factor (planetest.py measured 31.00 at both), and nothing at 1x or off. */
  int nonlinearDelay() const {
    const bool wanted = shapeA_.nonlinear || (shapeOwnB_ && shapeB_.nonlinear);
    return wanted && factor_ > 1 ? (32 * factor_ - factor_) / factor_ : 0;
  }
  // A sample's walk of the non-linear stage's crossfade, set each block.
  void setSwitchStep(double step, int prime) { switchStep_ = step; switchPrime_ = prime; }
  // Each pair's share where `setup` asks it, with no crossfade: the generator's first block.
  void settleSwitch() {
    nlIn_[0] = shapeA_.nonlinear ? 1 : 0;
    nlIn_[1] = (shapeOwnB_ ? shapeB_ : shapeA_).nonlinear ? 1 : 0;
    nlWait_ = { 0, 0 };
  }
  bool timeOn() const { return timeOn_; }
  // The reverb's decay to 60 dB down at a size, in seconds, as timeTick sets its gains: the tail a host is told.
  static double reverbT60(double size) { return kReverbT60Low * std::pow(kReverbT60Span, size); }

 private:
  // A routing on the echo's level keeps the line running at nought.
  void timeSet(Time& T, const PlaneTimeTone& t, bool echoRouted) const {
    T.t = &t;
    T.delayOn = t.delayMix > 0 || echoRouted;
    // F5c: the page's laws - 500 Hz to 20 kHz for the tone, 20 Hz to 1 kHz for the cut.
    T.cutA = t.delayLowCut > 0 ? 1 - std::exp(-kTwoPi * 20 * std::pow(50.0, std::fmin(1.0, t.delayLowCut)) / rate_) : 0;
    T.phOn = t.phaserMix > 0 || phaserRouted_;
    // The reverb, on its mix or a routing on it, as the echo is.
    T.revOn = t.reverbMix > 0 || reverbRouted_;
    T.revPre = static_cast<int>(std::fmax(0.0, std::fmin(static_cast<double>(reverbPreMax_ - 1),
                                                         jsRound(std::fmax(0.0, t.reverbPreMs) * rate_ / 1000))));
    const double spread = std::fmax(0.0, std::fmin(1.0, t.reverbSpread)) * kPi / 2;
    T.revC = std::cos(spread); T.revS = std::sin(spread);
    eqSet(T, t);
    T.on = T.delayOn || t.chorusMix > 0 || T.phOn || T.revOn || T.eqBands != 0;
  }
  /* The EQ's three bands as Web Audio's BiquadFilterNode makes them (the
     Audio EQ Cookbook, with the shelves' slope at one, as the node has
     them), so the node's getFrequencyResponse is the reference the core's
     response is held to (core/tests/pieces/eq.py). Each frequency is held
     under 0.45 of the rate, where the phaser's sweep is, so a high shelf
     set at 16 kHz on a 22 kHz render is a shelf and not a fold. The mid's
     width is in octaves, turned into the node's Q by the analog relation.
     Bands 3 and 4 (23 Nov) are the cuts, the node's highpass and lowpass,
     whose Q is the plain one here (`widthOct` carries it) and 20 log10 of
     it on the node; `db` is not read for them. */
  static std::array<double, 5> eqCoefficients(int band, double db, double hz, double widthOct, double rate) {
    const double f = std::fmin(hz, 0.45 * rate);
    const double w0 = kTwoPi * f / rate, c = std::cos(w0), sn = std::sin(w0);
    const double A = std::pow(10.0, db / 40);
    double b0, b1, b2, a0, a1, a2;
    if (band >= 3) {
      const double alpha = sn / (2 * std::fmax(0.1, widthOct));
      if (band == 3) { b0 = (1 + c) / 2; b1 = -(1 + c); b2 = (1 + c) / 2; }
      else { b0 = (1 - c) / 2; b1 = 1 - c; b2 = (1 - c) / 2; }
      a0 = 1 + alpha; a1 = -2 * c; a2 = 1 - alpha;
    } else if (band == 1) {
      const double q = eqWidthQ(widthOct), alpha = sn / (2 * q);
      b0 = 1 + alpha * A; b1 = -2 * c; b2 = 1 - alpha * A;
      a0 = 1 + alpha / A; a1 = -2 * c; a2 = 1 - alpha / A;
    } else {
      const double alpha = sn / 2 * std::sqrt(2.0), k = 2 * std::sqrt(A) * alpha;
      if (band == 0) {
        b0 = A * ((A + 1) - (A - 1) * c + k); b1 = 2 * A * ((A - 1) - (A + 1) * c); b2 = A * ((A + 1) - (A - 1) * c - k);
        a0 = (A + 1) + (A - 1) * c + k; a1 = -2 * ((A - 1) + (A + 1) * c); a2 = (A + 1) + (A - 1) * c - k;
      } else {
        b0 = A * ((A + 1) + (A - 1) * c + k); b1 = -2 * A * ((A - 1) + (A + 1) * c); b2 = A * ((A + 1) + (A - 1) * c - k);
        a0 = (A + 1) - (A - 1) * c + k; a1 = 2 * ((A - 1) - (A + 1) * c); a2 = (A + 1) - (A - 1) * c - k;
      }
    }
    return { b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0 };
  }
 public:
  // The mid's Q for a width in octaves; public so the tests can ask the node for the same filter.
  static double eqWidthQ(double widthOct) {
    const double w = std::fmax(0.05, widthOct), p = std::pow(2.0, w);
    return std::sqrt(p) / (p - 1);
  }
  // A band's coefficients, b0 b1 b2 a1 a2 (a0 one): the tests' way to the filter itself.
  static std::array<double, 5> eqBand(int band, double db, double hz, double widthOct, double rate) {
    return eqCoefficients(band, db, hz, widthOct, rate);
  }
 private:
  void eqSet(Time& T, const PlaneTimeTone& t) const {
    const double gains[3] = { t.eqLow, t.eqMid, t.eqHigh }, freqs[3] = { t.eqLowHz, t.eqMidHz, t.eqHighHz };
    T.eqBands = 0;
    if (!t.eqOn) return;
    for (int k = 0; k < 3; k++) {
      const double g = std::isfinite(gains[k]) ? std::fmax(-24.0, std::fmin(24.0, gains[k])) : 0;
      if (g == 0) continue;
      T.eqBands |= 1 << k;
      const double f = std::isfinite(freqs[k]) ? std::fmax(10.0, freqs[k]) : 1000;
      auto& at = T.eqAt[static_cast<std::size_t>(k)];
      const bool widthMoved = k == 1 && !(t.eqMidWidth == T.eqWidthAt);
      if (at[0] == g && at[1] == f && !widthMoved) continue;
      at = { g, f };
      if (k == 1) T.eqWidthAt = t.eqMidWidth;
      T.eqC[static_cast<std::size_t>(k)] = eqCoefficients(k, g, f, t.eqMidWidth, rate_);
    }
    // The cuts: in unless at their ends (20 Hz, 20 kHz, the knobs' ends exactly), whatever the gains.
    const double cutHz[2] = { t.eqCutLowHz, t.eqCutHighHz }, cutQ[2] = { t.eqCutLowQ, t.eqCutHighQ };
    for (int j = 0; j < 2; j++) {
      const int k = 3 + j;
      if (!std::isfinite(cutHz[j]) || (j == 0 ? !(cutHz[j] > 20) : !(cutHz[j] < 20000))) continue;
      T.eqBands |= 1 << k;
      const double f = std::fmax(10.0, cutHz[j]), q = std::isfinite(cutQ[j]) ? std::fmax(0.5, std::fmin(4.0, cutQ[j])) : 0.71;
      auto& at = T.eqAt[static_cast<std::size_t>(k)];
      if (at[0] == q && at[1] == f) continue;
      at = { q, f };
      T.eqC[static_cast<std::size_t>(k)] = eqCoefficients(k, 0, f, q, rate_);
    }
  }
  /* A module the hands share while another is B's own (G6) is layer A's to
     the sample, as the page's timeShare: its sweep, its level under A's
     routings and every coefficient worked out from them, so a shared chorus
     moves as one chorus, as it did while B had no effects of its own. */
  static void timeShare(Time& T, const Time& A, int own) {
    if (!(own & 1)) { T.ph = A.ph; T.phPhase = A.phPhase; T.aL = A.aL; T.aR = A.aR; }
    if (!(own & 2)) { T.phase = A.phase; T.sin = A.sin; T.cos = A.cos; }
    if (!(own & 4)) { T.echo = A.echo; T.echoMs = A.echoMs; T.toneA = A.toneA; T.toneAt = A.toneAt; }
    if (!(own & 8)) {
      T.rev = A.rev; T.revIn = A.revIn; T.revDampA = A.revDampA; T.revSizeAt = A.revSizeAt; T.revToneAt = A.revToneAt;
      T.revG = A.revG;
    }
    if (!(own & 16)) { T.eqBands = A.eqBands; T.eqC = A.eqC; T.eqAt = A.eqAt; T.eqWidthAt = A.eqWidthAt; }
  }
  void timeTick(Time& T, const PlanePushes& p, double dt) {
    const PlaneTimeTone& t = *T.t;
    if (T.delayOn) {
      T.echo = std::fmax(0.0, std::fmin(1.0, t.delayMix + p.echo * 0.5));
      T.echoMs = p.echoTime == 0 ? t.delayMs : t.delayMs * std::pow(2.0, p.echoTime);
      // The tone from its knob and its push, worked out again only when it moves, as the page's.
      const double tone = std::fmax(0.0, std::fmin(1.0, t.delayTone + p.delayTone * 0.5));
      if (!(tone == T.toneAt)) {
        T.toneAt = tone;
        T.toneA = tone < 1 ? 1 - std::exp(-kTwoPi * 500 * std::pow(40.0, tone) / rate_) : 0;
      }
    }
    if (t.chorusMix > 0) {
      T.phase += kTwoPi * t.chorusRate * dt;
      if (T.phase >= kTwoPi) T.phase -= kTwoPi;
      T.sin = std::sin(T.phase); T.cos = std::cos(T.phase);
    }
    if (T.phOn) {
      T.ph = std::fmax(0.0, std::fmin(1.0, t.phaserMix + p.phaser * 0.5));
      T.phPhase += kTwoPi * t.phaserRate * dt;
      if (T.phPhase >= kTwoPi) T.phPhase -= kTwoPi;
      const double span = kPhaserOctaves * t.phaserDepth;
      T.aL = allpassCoef(kPhaserCentre * std::pow(2.0, span * std::sin(T.phPhase)));
      T.aR = allpassCoef(kPhaserCentre * std::pow(2.0, span * std::cos(T.phPhase)));
    }
    if (T.revOn) {
      T.rev = std::fmax(0.0, std::fmin(1.0, t.reverbMix + p.reverb * 0.5));
      // The gains and the tone worked out again only when they move, as the page's.
      const double size = std::fmax(0.0, std::fmin(1.0, t.reverbSize + p.reverbSize * 0.5));
      if (!(size == T.revSizeAt)) {
        T.revSizeAt = size;
        const double t60 = kReverbT60Low * std::pow(kReverbT60Span, size);
        double sq = 0;
        for (int i = 0; i < kReverbLines; i++) {
          T.revG[static_cast<std::size_t>(i)] = std::pow(10.0, -3 * reverbLen_[i] / (t60 * rate_));
          sq += T.revG[static_cast<std::size_t>(i)] * T.revG[static_cast<std::size_t>(i)];
        }
        T.revIn = std::sqrt(1 - sq / kReverbLines);
      }
      const double rtone = std::fmax(0.0, std::fmin(1.0, t.reverbTone + p.reverbTone * 0.5));
      if (!(rtone == T.revToneAt)) {
        T.revToneAt = rtone;
        T.revDampA = rtone < 1 ? 1 - std::exp(-kTwoPi * kReverbToneLow * std::pow(kReverbToneSpan, rtone) / rate_) : 0;
      }
    }
  }

  /* P8e, the phaser, as the page's: four first-order all-passes a channel,
     swept together in quadrature, fed back for the resonance and mixed with
     the dry pair at most half and half. The page's comment (makeTimeFx) has
     the reasons: four for two notches, quadrature because a phaser alike on
     both channels leaves a diagonal line a line. States below 1e-30 are
     flushed to nought, on both sides, so a silence never decays into
     denormals - which a native core pays for dearly and V8 does not, so the
     page does it only to stay equal to this. Fixed arrays, so nothing is
     allocated on the audio thread. */
  static constexpr int kPhaserStages = 4;
  static constexpr double kPhaserCentre = 700, kPhaserOctaves = 2.5, kPhaserFeedbackMax = 0.75;
  double allpassCoef(double hz) const {
    const double t = std::tan(kPi * std::fmin(hz, phaserTop_) / rate_);
    return (t - 1) / (t + 1);
  }
  // A channel's four in series: `s` holds each one's last input at o + k and last output at o + 4 + k.
  static double allpassChain(std::array<double, 4 * kPhaserStages>& s, int o, double a, double v) {
    for (int k = 0; k < kPhaserStages; k++) {
      const auto in = static_cast<std::size_t>(o + k), out = static_cast<std::size_t>(o + kPhaserStages + k);
      double y = a * v + s[in] - a * s[out];
      if (std::fabs(y) < 1e-30) y = 0;
      s[in] = v;
      s[out] = y;
      v = y;
    }
    return v;
  }

  static void shapeSet(Shape& s, const PlaneShapeTone& t, bool twistRouted, double turn) {
    s.linear = t.planeScaleX != 1 || t.planeScaleY != 1 || t.planeShear != 0;
    s.nonlinear = t.planeMirror != 0 || t.planeLimit != 0 || t.planeTwist != 0 || twistRouted ||
                  t.planeSnap > 0;
    s.mirror = t.planeMirror;
    s.limit = t.planeLimit;
    s.snap = t.planeSnap > 0 ? 2 / std::pow(2.0, t.planeSnap) : 0;
    s.sx = t.planeScaleX; s.sy = t.planeScaleY; s.shear = t.planeShear;
    s.turn = turn; s.tc = std::cos(turn); s.ts = std::sin(turn);
  }

  // Leaves its answer in `x`, `y`, where the oversampler reads it. Applies
  // `cur_`, the shape `step` was given.
  void op(double x, double y) {
    const int mirror_ = cur_->mirror, limit_ = cur_->limit;
    const double snap_ = cur_->snap, radius_ = cur_->radius, twist_ = cur_->twist;
    if (mirror_ & 1) x = std::fabs(x);
    if (mirror_ & 2) y = std::fabs(y);
    if (twist_ != 0) {
      const double a = twist_ * std::sqrt(x * x + y * y), c = std::cos(a), s = std::sin(a);
      const double tx = x * c - y * s;
      y = x * s + y * c; x = tx;
    }
    // The kaleidoscope was here, cut on 7 Nov (the page's planeOp says why).
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
    // Its histories emptied, its factor kept: a stage coming back in.
    void clear() { at = 0; inX.fill(0); inY.fill(0); upX.fill(0); upY.fill(0); }
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

  /* P9, the reverb, as the page's (reverbStep says why): a channel each, no
     cross-feed, a pre-delay, four all-passes, eight lines through a
     Householder matrix with a one-pole each, Y's taps turned by the spread. */
  static constexpr int kReverbLines = 8, kReverbDiffusers = 4;
  static constexpr double kReverbLineMs[kReverbLines] = { 31.3, 37.9, 41.7, 47.3, 53.1, 59.9, 67.1, 73.7 };
  static constexpr double kReverbDiffuseMs[kReverbDiffusers] = { 4.7, 3.6, 12.7, 9.3 };
  static constexpr double kReverbDiffuseG = 0.6, kReverbT60Low = 0.3, kReverbT60Span = 30;
  static constexpr double kReverbToneLow = 500, kReverbToneSpan = 40;
  static constexpr int kReverbRowA[kReverbLines] = { 1, -1, 1, -1, 1, -1, 1, -1 };
  static constexpr int kReverbRowB[kReverbLines] = { 1, 1, -1, -1, 1, 1, -1, -1 };
  struct ReverbChannel {
    std::vector<double> pre;
    int pw = 0;
    std::array<std::vector<double>, kReverbDiffusers> ap;
    std::array<int, kReverbDiffusers> apw {};
    std::array<std::vector<double>, kReverbLines> lines;
    std::array<int, kReverbLines> lw {};
    std::array<double, kReverbLines> damp {}, outs {}, back {};
  };

  struct TimeFx {
    ReverbChannel rvx, rvy;
    std::vector<float> dl, dr, cl, cr;
    int dw = 0, cw = 0;
    double dNow = -1;
    std::array<double, 4 * kPhaserStages> ps {};  // the phaser's all-pass states, left then right
    double pl = 0, pr = 0;                        // and what each channel's chain last gave, fed back
    double tl = 0, tr = 0, hl = 0, hr = 0, wph = 0;  // F5c: the tone's and cut's memories, the wow's phase
    int ran = 0, was = 0;  // the modules that ran this block and the last, by timeOwn's bits
    // The EQ's: each band's two states a channel (transposed direct form II), and the bands it last ran.
    std::array<std::array<double, 2>, 5> eqL {}, eqR {};
    int eqWas = 0;
  };

  /* A module switched on starts from silence (11 Nov), as the page's
     timeFresh: a module that ran in neither this block nor the last has its
     lines and memories emptied before it runs. The page says why, and what
     was rejected. Filled in place, so nothing is allocated here: the delay's
     two lines are the most of it, about 0.7 MB at 48 kHz, once a switch-on. */
  static void timeFresh(TimeFx& fx, int bit) {
    if (bit == 16) { for (auto& st : fx.eqL) st.fill(0); for (auto& st : fx.eqR) st.fill(0); fx.eqWas = 0; return; }
    if (bit == 1) { fx.ps.fill(0); fx.pl = 0; fx.pr = 0; }
    else if (bit == 2) { std::fill(fx.cl.begin(), fx.cl.end(), 0.0f); std::fill(fx.cr.begin(), fx.cr.end(), 0.0f); }
    else if (bit == 4) {
      std::fill(fx.dl.begin(), fx.dl.end(), 0.0f); std::fill(fx.dr.begin(), fx.dr.end(), 0.0f);
      fx.dNow = -1; fx.tl = 0; fx.tr = 0; fx.hl = 0; fx.hr = 0; fx.wph = 0;
    } else {
      for (auto* c : { &fx.rvx, &fx.rvy }) {
        std::fill(c->pre.begin(), c->pre.end(), 0.0);
        for (auto& buf : c->ap) std::fill(buf.begin(), buf.end(), 0.0);
        for (auto& line : c->lines) std::fill(line.begin(), line.end(), 0.0);
        c->damp.fill(0);
      }
    }
  }
  static void timeRuns(TimeFx& fx, int bit) {
    if (fx.ran & bit) return;
    if (!(fx.was & bit)) timeFresh(fx, bit);
    fx.ran |= bit;
  }

  static double readLine(const std::vector<float>& buf, int w, double d, int size) {
    double at = w - d;
    while (at < 0) at += size;
    const double i = std::floor(at), f = at - i;
    const int k = static_cast<int>(i), j = k + 1 == size ? 0 : k + 1;
    const double a = buf[static_cast<std::size_t>(k)], b = buf[static_cast<std::size_t>(j)];
    return a + (b - a) * f;
  }

  // One channel a sample, as the page's reverbChannel.
  void reverbChannel(ReverbChannel& c, const Time& T, double v) const {
    c.pre[static_cast<std::size_t>(c.pw)] = v;
    int read = c.pw - T.revPre;
    if (read < 0) read += reverbPreMax_;
    double u = c.pre[static_cast<std::size_t>(read)];
    c.pw = c.pw + 1 == reverbPreMax_ ? 0 : c.pw + 1;
    for (int k = 0; k < kReverbDiffusers; k++) {
      auto& buf = c.ap[static_cast<std::size_t>(k)];
      const int w = c.apw[static_cast<std::size_t>(k)];
      const double d = buf[static_cast<std::size_t>(w)];
      double y = -kReverbDiffuseG * u + d;
      if (std::fabs(y) < 1e-30) y = 0;
      buf[static_cast<std::size_t>(w)] = u + kReverbDiffuseG * y;
      c.apw[static_cast<std::size_t>(k)] = w + 1 == static_cast<int>(buf.size()) ? 0 : w + 1;
      u = y;
    }
    double sum = 0;
    for (std::size_t i = 0; i < kReverbLines; i++) {
      double o = c.lines[i][static_cast<std::size_t>(c.lw[i])];
      if (T.revDampA > 0) {
        double d = c.damp[i] + T.revDampA * (o - c.damp[i]);
        if (std::fabs(d) < 1e-30) d = 0;
        c.damp[i] = d; o = d;
      }
      c.outs[i] = o;  // after the tone, as the page's
      o *= T.revG[i];
      c.back[i] = o;
      sum += o;
    }
    const double s = sum * 2 / kReverbLines, inj = u * T.revIn;
    for (std::size_t i = 0; i < kReverbLines; i++) {
      const int w = c.lw[i];
      double next = c.back[i] - s + inj;
      if (std::fabs(next) < 1e-30) next = 0;
      c.lines[i][static_cast<std::size_t>(w)] = next;
      c.lw[i] = w + 1 == static_cast<int>(c.lines[i].size()) ? 0 : w + 1;
    }
  }

  // One band of the EQ, a channel, in transposed direct form II.
  static double eqBiquad(const std::array<double, 5>& c, std::array<double, 2>& z, double v) {
    const double out = c[0] * v + z[0];
    double z0 = c[1] * v - c[3] * out + z[1], z1 = c[2] * v - c[4] * out;
    if (std::fabs(z0) < 1e-30) z0 = 0;
    if (std::fabs(z1) < 1e-30) z1 = 0;
    z[0] = z0; z[1] = z1;
    return out;
  }

  void timeStep(TimeFx& fx, const Time& T, double x, double y) {
    const PlaneTimeTone& t = *T.t;
    /* The EQ (17 Nov) first, straight after the plane and before the three
       the setup orders, so the chorus and the delay repeat the equalised
       pair; its place is fixed, as the Plane's and the Reverb's are. The
       same three bands on both channels, so a line stays a line: an EQ alike
       on X and Y changes the figure's size along its length with frequency
       and never opens it. A band at nought is skipped, so an EQ switched off
       is not in the sum at all; a band coming back in starts from silence,
       as a module switched on does. */
    if (T.eqBands != 0) {
      timeRuns(fx, 16);
      if (const int fresh = T.eqBands & ~fx.eqWas) {
        for (std::size_t k = 0; k < 5; k++)
          if (fresh & (1 << k)) { fx.eqL[k].fill(0); fx.eqR[k].fill(0); }
      }
      fx.eqWas = T.eqBands;
      // The three bands in the order they always ran, then the two cuts (23 Nov), so the three alone are the old sum to the bit.
      for (std::size_t k = 0; k < 5; k++) {
        if (!(T.eqBands & (1 << k))) continue;
        x = eqBiquad(T.eqC[k], fx.eqL[k], x);
        y = eqBiquad(T.eqC[k], fx.eqR[k], y);
      }
    }
    /* In the setup's order (F5b): by default the phaser first, so the chorus and
       the echoes are of the phased pair. Each stage's arithmetic is as it was,
       so the default order is the old sum to the bit. */
    const char* order = kFxOrders[t.fxOrder >= 0 && t.fxOrder < kFxOrderCount ? t.fxOrder : 0];
    for (int k = 0; k < 3; k++) {
      const char stage = order[k];
      if (stage == 'p') {
        if (T.phOn) {
          timeRuns(fx, 1);
          const double fb = std::fmax(0.0, std::fmin(kPhaserFeedbackMax, t.phaserFeedback));
          const double wl = allpassChain(fx.ps, 0, T.aL, x + fb * fx.pl);
          const double wr = allpassChain(fx.ps, 2 * kPhaserStages, T.aR, y + fb * fx.pr);
          fx.pl = wl; fx.pr = wr;
          const double m = T.ph;
          x = x * (1 - m / 2) + wl * m / 2; y = y * (1 - m / 2) + wr * m / 2;
        }
      } else if (stage == 'c') {
        if (t.chorusMix > 0) {
          timeRuns(fx, 2);
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
      } else {
        if (T.delayOn) {
          timeRuns(fx, 4);
          const double want = std::fmax(1.0, std::fmin(static_cast<double>(delayMax_ - 3), T.echoMs * rate_ / 1000));
          fx.dNow = fx.dNow < 0 ? want : fx.dNow + (want - fx.dNow) * delayGlide_;
          // Wow: half a hertz, two milliseconds either side at the most, as the page's.
          double at = fx.dNow;
          if (t.delayWow > 0) {
            fx.wph += kTwoPi * 0.5 / rate_;
            if (fx.wph >= kTwoPi) fx.wph -= kTwoPi;
            at = std::fmax(1.0, std::fmin(static_cast<double>(delayMax_ - 3),
                                          at + std::fmin(1.0, t.delayWow) * (0.002 * rate_) * std::sin(fx.wph)));
          }
          double echoL = readLine(fx.dl, fx.dw, at, delayMax_);
          double echoR = readLine(fx.dr, fx.dw, at, delayMax_);
          // Tone and low cut in the loop, skipped open and off, as the page's.
          if (T.toneA > 0) { fx.tl += T.toneA * (echoL - fx.tl); fx.tr += T.toneA * (echoR - fx.tr); echoL = fx.tl; echoR = fx.tr; }
          if (T.cutA > 0) { fx.hl += T.cutA * (echoL - fx.hl); fx.hr += T.cutA * (echoR - fx.hr); echoL -= fx.hl; echoR -= fx.hr; }
          const double fb = std::fmax(0.0, std::fmin(0.9, t.delayFeedback));
          const auto w = static_cast<std::size_t>(fx.dw);
          if (t.delayPingPong) { fx.dl[w] = static_cast<float>(x + fb * echoR); fx.dr[w] = static_cast<float>(y + fb * echoL); }
          else { fx.dl[w] = static_cast<float>(x + fb * echoL); fx.dr[w] = static_cast<float>(y + fb * echoR); }
          fx.dw = fx.dw + 1 == delayMax_ ? 0 : fx.dw + 1;
          // Width on what is heard and drawn only; one skipped, as the page's.
          const double wide = std::fmax(0.0, std::fmin(2.0, t.delayWidth));
          if (wide != 1) {
            const double mid = (echoL + echoR) / 2, side = (echoL - echoR) / 2 * wide;
            echoL = mid + side; echoR = mid - side;
          }
          x += T.echo * echoL; y += T.echo * echoR;
        }
      }
    }
    // The reverb last, after the three in their order, as the page's.
    if (T.revOn) {
      timeRuns(fx, 8);
      reverbChannel(fx.rvx, T, x);
      reverbChannel(fx.rvy, T, y);
      double wx = 0, wy = 0;
      for (std::size_t i = 0; i < kReverbLines; i++) {
        wx += kReverbRowA[i] * fx.rvx.outs[i];
        wy += (T.revC * kReverbRowA[i] + T.revS * kReverbRowB[i]) * fx.rvy.outs[i];
      }
      const double out = T.rev / std::sqrt(static_cast<double>(kReverbLines));
      x = x + out * wx; y = y + out * wy;
    }
    this->x = x; this->y = y;
  }

  double rate_;
  int reverbPreMax_;
  std::array<int, kReverbLines> reverbLen_ {};
  std::array<int, kReverbDiffusers> reverbDiffuseLen_ {};
  bool reverbRouted_ = false;
  int delayMax_, chorusMax_;
  double delayGlide_, phaserTop_;
  bool phaserRouted_ = false;  // a routing on the phaser's amount runs it at nought, as the echo's does
  std::vector<double> taps2_, taps4_;
  int factor_ = 0;
  std::array<Oversampler, 2> os_;
  std::array<double, 2> nlIn_ {};  // each pair's share of the non-linear stage, the page's fx.nlIn
  std::array<int, 2> nlWait_ {};   // and its samples still to prime, plus one, the page's fx.nlWait
  double switchStep_ = 1;
  int switchPrime_ = 0;
  std::array<TimeFx, 2> fx_;
  bool linearOn_ = false, nonlinearOn_ = false, timeOn_ = false, ownB_ = false, turnRoutedB_ = false;
  bool shapeOwnB_ = false;  // B's own plane in force (planeOwn)
  int timeOwnB_ = 0;        // B's own time modules in force (timeOwn's bits)
  double turnB_ = 0;
  Shape shapeA_, shapeB_;
  const Shape* cur_ = &shapeA_;
  Time timeA_, timeB_;
};

}  // namespace scope
