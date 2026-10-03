// The generator, ported from `makeGeneratorCore` in web/scope.html: the
// per-sample loop that makes every mode's pair - the dyad, the chord on two
// layers, the figure, the solid, the pendulums - through the routings, the
// governor, the plane, the crossings and the score's voices, and the calls the
// worklet makes of it. It is held to the page's own `makeGeneratorCore` whole,
// driven through the same calls, by core/tests/parity.py.
//
// The pieces it is made of are ported and held to the page one at a time in
// the headers it includes; this file is the order they are called in, which
// is the page's line for line. Where the JavaScript explains why, the
// explanation is there.
//
// What differs from the page, and why, so nobody goes looking:
//
// - The page's tone is a JavaScript object written by name, and holds whatever
//   it is handed. Here it is two structs and `set` is typed: a number, a word,
//   or one of the structured fields (the bars, the spin, the chord, a drawn
//   cycle, a path), each with its own call. A field the page would take but
//   never reads is ignored rather than kept.
// - The routings' accumulator is a Float32Array in the page, so it is `float`
//   here and every sum into it is rounded as the page rounds it. It is made at
//   least as long as the slots the loop reads, so a core asked for fewer
//   slots than that reads nought from the ones it lacks, which is what the
//   page's `|| 0` gives for most of them; the page reads `undefined` from the
//   seven it does not guard, and no caller makes a core that small.
// - The outputs are float, as an AudioWorklet's are, and the loop reads its
//   own picture back from them as the page does - the crossings and the heard
//   pair see the picture as rounded, not as computed.

#pragma once

#include <array>
#include <cmath>
#include <memory>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include "scope/envelope.h"
#include "scope/figures.h"
#include "scope/lfo.h"
#include "scope/noise.h"
#include "scope/osc.h"
#include "scope/plane.h"
#include "scope/voice.h"
#include "scope/voices.h"
#include "scope/wave.h"
#include "scope/wireframe.h"

namespace scope {

// Where each destination sits in the routings' accumulator: GEN_DESTS's slots.
namespace slot {
constexpr int Freq = 0, Amp = 1, Phase = 2, Ratio = 3, Detail = 4, Tumble = 5, Depth = 6;
constexpr int Drawbar = 7, Morph = Drawbar + 9, Radius = Morph + 1, Twist = Radius + 1, Fm = Twist + 1, Sync = Fm + 1;
constexpr int Drive = Sync + 1, Fold = Drive + 1, Vcf = Fold + 1, Echo = Vcf + 1, EchoTime = Echo + 1;
constexpr int Swing = EchoTime + 1, Width = Swing + 1, Table = Width + 1, Spin = Table + 1;
constexpr int Used = Spin + 3;  // the slots the loop reads
}  // namespace slot

enum class Mode { Wave, Harmonograph, Figure, Wireframe };

// A layer's own tone: the voice, its level and two envelopes, its bars and
// its chord. Layer B is one of these and nothing else.
struct LayerSettings : LayerTone {
  std::string shapeName = "harmonic";  // as the page names it, for the tables and the costs
  std::string subShapeName = "square";  // as given: a menu with nothing chosen gives ""
  std::array<double, 9> bars { 0, 0, 8, 7, 4, 0, 0, 0, 0 };
  std::optional<std::vector<NoteWant>> voices;  // none is no chord
  LayerSettings() {
    amp = 0.55; unisonCents = 12; morph = 1.5;
    env = { 8, 120, 0.7, 180 };
    fenv = { 5, 300, 0.3, 300 };
  }
};

// Layer A's tone, which is also the page's: everything but the voice.
struct Tone : LayerSettings, PlaneTone {
  Mode mode = Mode::Wave;
  // The words as the page's tone holds them, whatever they are: a setup can
  // give a menu a value it has not got, and the page keeps the "" that results.
  std::string modeName = "wave", figureName = "Circle", gen2FigureName = "Circle", modelName = "Cube";
  std::string inputFromName = "live";
  double freq = 220;
  int interval = 0;
  double octaves = 0;
  bool just = true;
  double phase = kPi / 2;
  Figure figure = Figure::Circle;
  double detail = 5, figureRate = 40, swingRate = 2.1, decay = 0.12, swingDrive = 0;
  double inputMode = 0, inputDepth = 0.5;
  bool fromGen2 = false;  // the page's inputFrom === "gen2"
  Figure gen2Figure = Figure::Circle;
  double gen2Rate = 110, gen2Amp = 0.5;
  std::shared_ptr<const CycleTables> cycle;
  std::shared_ptr<const std::vector<CycleTables>> wavetable;
  std::shared_ptr<const FigurePath> figPath;
  bool pitched = false;
  double ringMs = 600, detune = 0.004;
  std::array<double, 3> spin { 0.11, 0.17, 0.0 };
  double spinRate = 1, depth = 0.45;
  double shapeOS = 2, glideMs = 0;
  int qMask = 0;
  double qGlideMs = 0;
  bool crossOn = false;
  double crossX = 0, crossY = 0, crossHzX = 261.63, crossHzY = 392, crossDecayMs = 180, crossLevel = 0.4;
  double scoreDecayMs = 400, scoreLevel = 0.4;
};

// A routing, as `setRoutes` copies one: an LFO's index or a held value.
struct Route {
  int index = -1;  // the LFO it reads; -1 is the held value
  double held = 0, heldB = 0;
  int slot = 0;
  double amount = 0, amountB = 0;
  bool unipolar = false;
};

// S10's report of the last block.
struct Budget {
  double units = 0;
  std::array<int, 2> asked { 1, 1 }, unison { 1, 1 };
  int askedFactor = 2, factor = 2, silenced = 0;
};

class Generator {
 public:
  static constexpr double kVoiceBudget = 350;

  Generator(double rate, int slots, std::vector<Lfo>& lfos, std::uint32_t seed = 1)
      : rate_(rate), slots_(slots), lfos_(lfos), random_(seed),
        genMod_(static_cast<std::size_t>(std::max(slots, slot::Used)), 0.0f), genModB_(genMod_),
        reletSamples_(std::max(1, static_cast<int>(jsRound(10 * rate / 1000)))),
        env_(rate, a_.env), fenv_(rate, a_.fenv), plane_(rate), ctx_(rate),
        crossHold_(std::max(1, static_cast<int>(jsRound(0.04 * rate)))),
        crossAttack_(1 / std::max(1.0, jsRound(0.002 * rate))),
        shapeL_(2, ctx_.taps2), shapeR_(2, ctx_.taps2),
        noiseL_(random_), noiseR_(random_) {
    ctx_.random = &random_;
    fenv_.reset(0);
    barsA_.at.fill(-1); barsB_.at.fill(-1);
  }
  Generator(const Generator&) = delete;
  Generator& operator=(const Generator&) = delete;

  Tone& tone() { return a_; }
  LayerSettings& toneB() { return b_; }
  const LayerSettings& toneB() const { return b_; }

  // --- the page's `set`, by kind of value -----------------------------------

  void set(std::string_view field, double value, int layer = 0) {
    LayerSettings& t = layer == 1 ? static_cast<LayerSettings&>(b_) : a_;
    if (setLayerNumber(t, field, value)) return;
    if (layer == 1) return;
    Tone& a = a_;
    if (field == "freq") a.freq = value;
    else if (field == "interval") a.interval = static_cast<int>(value);
    else if (field == "octaves") a.octaves = value;
    else if (field == "just") a.just = value != 0;
    else if (field == "phase") a.phase = value;
    else if (field == "detail") a.detail = value;
    else if (field == "figureRate") a.figureRate = value;
    else if (field == "swingRate") a.swingRate = value;
    else if (field == "decay") { a.decay = value; restartSwing(); }
    else if (field == "swingDrive") a.swingDrive = value;
    else if (field == "inputMode") a.inputMode = value;
    else if (field == "inputDepth") a.inputDepth = value;
    else if (field == "gen2Rate") a.gen2Rate = value;
    else if (field == "gen2Amp") a.gen2Amp = value;
    else if (field == "pitched") a.pitched = value != 0;
    else if (field == "ringMs") a.ringMs = value;
    else if (field == "detune") a.detune = value;
    else if (field == "spinRate") a.spinRate = value;
    else if (field == "depth") a.depth = value;
    else if (field == "shapeOS") a.shapeOS = value;
    else if (field == "glideMs") a.glideMs = value;
    else if (field == "qMask") a.qMask = static_cast<int>(value);
    else if (field == "qGlideMs") a.qGlideMs = value;
    else if (field == "crossOn") a.crossOn = value != 0;
    else if (field == "crossX") a.crossX = value;
    else if (field == "crossY") a.crossY = value;
    else if (field == "crossHzX") a.crossHzX = value;
    else if (field == "crossHzY") a.crossHzY = value;
    else if (field == "crossDecayMs") a.crossDecayMs = value;
    else if (field == "crossLevel") a.crossLevel = value;
    else if (field == "scoreDecayMs") a.scoreDecayMs = value;
    else if (field == "scoreLevel") a.scoreLevel = value;
    else if (field == "planeMirror") a.planeMirror = static_cast<int>(value);
    else if (field == "planeRadius") a.planeRadius = value;
    else if (field == "planeOS") a.planeOS = value;
    else if (field == "planeLimit") a.planeLimit = static_cast<int>(value);
    else if (field == "planeScaleX") a.planeScaleX = value;
    else if (field == "planeScaleY") a.planeScaleY = value;
    else if (field == "planeShear") a.planeShear = value;
    else if (field == "planeTwist") a.planeTwist = value;
    else if (field == "planeKaleido") a.planeKaleido = value;
    else if (field == "planeSnap") a.planeSnap = value;
    else if (field == "delayMix") a.delayMix = value;
    else if (field == "delayMs") a.delayMs = value;
    else if (field == "delayFeedback") a.delayFeedback = value;
    else if (field == "delayPingPong") a.delayPingPong = value != 0;
    else if (field == "chorusMix") a.chorusMix = value;
    else if (field == "chorusRate") a.chorusRate = value;
    else if (field == "chorusDepthMs") a.chorusDepthMs = value;
    else if (field == "chorusMs") a.chorusMs = value;
    else if (field == "chorusFeedback") a.chorusFeedback = value;
  }

  void set(std::string_view field, std::string_view value, int layer = 0) {
    LayerSettings& t = layer == 1 ? static_cast<LayerSettings&>(b_) : a_;
    if (field == "shape") {
      t.noise = noiseNamed(value, t.noiseShape);
      t.shape = shapeNamed(value);
      t.shapeName = std::string(value);
      return;
    }
    if (field == "subShape") { t.subSine = value == "sine"; t.subShapeName = std::string(value); return; }
    if (layer == 1) return;
    if (field == "mode") {
      a_.modeName = std::string(value);
      a_.mode = value == "harmonograph" ? Mode::Harmonograph : value == "figure" ? Mode::Figure
              : value == "wireframe" ? Mode::Wireframe : Mode::Wave;
      restartSwing();
    } else if (field == "figure") { a_.figure = figureNamed(value); a_.figureName = std::string(value); }
    else if (field == "inputFrom") { a_.fromGen2 = value == "gen2"; a_.inputFromName = std::string(value); }
    else if (field == "gen2Figure") { a_.gen2Figure = figureNamed(value); a_.gen2FigureName = std::string(value); }
    else if (field == "model") { wire_.set(value); a_.modelName = std::string(value); }
  }

  // Copied and clamped; the page ignores a registration that is not nine.
  void setBars(const std::vector<double>& value, int layer = 0) {
    if (value.size() != 9) return;
    LayerSettings& t = layer == 1 ? static_cast<LayerSettings&>(b_) : a_;
    for (std::size_t k = 0; k < 9; k++) {
      const double v = std::isnan(value[k]) ? 0 : value[k];
      t.bars[k] = std::fmax(0.0, std::fmin(8.0, v));
    }
  }
  void setSpin(const std::array<double, 3>& spin) { a_.spin = spin; }
  void setCycle(std::shared_ptr<const CycleTables> c) { a_.cycle = std::move(c); }
  void setWavetable(std::shared_ptr<const std::vector<CycleTables>> w) { a_.wavetable = std::move(w); }
  void setFigPath(std::shared_ptr<const FigurePath> p) { a_.figPath = std::move(p); }

  // The chord: a list of notes, or none for no chord on that layer.
  void setVoices(const std::vector<NoteWant>* list, int layer = 0) {
    LayerSettings& t = layer == 1 ? static_cast<LayerSettings&>(b_) : a_;
    if (list == nullptr) t.voices.reset(); else t.voices = *list;
    reconcileVoices(layer == 1 ? voicesB_ : voices_, t.voices ? &*t.voices : nullptr, t, ctx_);
  }

  void setRoutes(const std::vector<Route>& list) { routes_ = list; }

  // --- the rest of the worklet's calls --------------------------------------

  void kick(double amount) { kick_ = std::fmax(-kKickMost, std::fmin(kKickMost, kick_ + amount * kKickSize)); }

  // The next block's input, or none.
  void setInput(const float* samples, int length) { inBuf_ = samples; inLen_ = samples ? length : 0; }

  void strike(double hz, double velocity) {
    ScoreVoice* pick = &score_[0];
    for (auto& v : score_) {
      if (v.env == 0) { pick = &v; break; }
      if (v.age > pick->age) pick = &v;
    }
    pick->hz = hz; pick->vel = std::fmax(0.0, std::fmin(1.0, velocity)); pick->attacking = true; pick->age = 0;
    scoreStruck_ = 1;
  }

  void reswing() {
    if (a_.mode == Mode::Harmonograph && a_.pitched) {
      strikeFrom_ = lastGain_; striking_ = true; swing_ = 0; relet_ = reletSamples_;
      return;
    }
    swing_ = 0; swingEnv_ = 1; phaseL_ = 0; phaseR_ = 0; relet_ = 0; striking_ = false; wire_.reset();
    oscL_.n = 0; oscR_.n = 0;
  }

  void gate(bool open, double velocity) { env_.gate(open, velocity); fenv_.gate(open, velocity); }

  void setGated(bool on) {
    if (on == gated_) return;
    gated_ = on;
    env_.reset(on ? 0 : 1);
    fenv_.reset(0);
  }

  // In poly the loudest voice; otherwise the envelope, or one ungated.
  double envelope() const {
    if (a_.voices) {
      double most = 0;
      for (const auto& v : voices_) most = std::fmax(most, v.env.level());
      for (const auto& v : voicesB_) most = std::fmax(most, v.env.level());
      return most;
    }
    return gated_ ? env_.level() : 1;
  }
  bool gated() const { return gated_; }
  double pitch() const { return lastHz_; }
  std::array<int, 2> crossings() const { return { cross_[0].count, cross_[1].count }; }
  const std::vector<Voice>& voices() const { return voices_; }
  const std::vector<Voice>& voicesB() const { return voicesB_; }
  const Budget& budget() const { return budget_; }
  double spinKick() const { return kick_; }
  double swingLevel() const { return swingEnv_; }
  static bool cutting(const Voice& v) { return v.gone || v.fade > 0; }

  struct Drawing { double swing, pendulum; std::array<double, 3> turn; double facing; };
  Drawing drawing() const {
    const bool swinging = a_.mode == Mode::Harmonograph, solid = a_.mode == Mode::Wireframe;
    const auto& a = wire_.angles();
    return { swinging ? lastGain_ : 0, swinging ? std::sin(phaseL_) : 0,
             solid ? std::array<double, 3> { std::sin(a[0]), std::sin(a[1]), std::sin(a[2]) }
                   : std::array<double, 3> { 0, 0, 0 },
             solid ? std::cos(a[0]) * std::cos(a[1]) : 0 };
  }

  // --- S1: a live input through the plane -----------------------------------

  void effect(const float* inL, const float* inR, float* outL, float* outR, int n) {
    const double dt = 1 / rate_;
    bool twistRouted = false, echoRouted = false;
    for (const auto& r : routes_) {
      if (r.slot == slot::Twist) twistRouted = true;
      if (r.slot == slot::Echo) echoRouted = true;
    }
    const bool planeOn = plane_.setup(a_, twistRouted, echoRouted);
    for (int i = 0; i < n; i++) {
      lfoStep(lfos_[0], rate_, random_);
      lfoStep(lfos_[1], rate_, random_);
      sumRoutes();
      if (planeOn) {
        planeTick(dt);
        plane_.step(Plane::A, a_, inL[i], inR[i]);
        outL[i] = static_cast<float>(plane_.x); outR[i] = static_cast<float>(plane_.y);
      } else {
        outL[i] = inL[i]; outR[i] = inR[i];
      }
    }
  }

  // --- the block -------------------------------------------------------------

  void block(float* outL, float* outR, int n, float* heardL = nullptr, float* heardR = nullptr,
             float* outBL = nullptr, float* outBR = nullptr) {
    const double dt = 1 / rate_;
    const bool poly = a_.voices.has_value();
    const bool layered = b_.voices.has_value();
    const double roleGlide = poleFor(4, rate_);
    bool twistRouted = false, fmRouted = false, syncRouted = false, shapeRouted = false, echoRouted = false;
    for (const auto& r : routes_) {
      if (r.slot == slot::Twist) twistRouted = true;
      if (r.slot == slot::Echo) echoRouted = true;
      if (r.slot == slot::Fm) fmRouted = true;
      if (r.slot == slot::Sync) syncRouted = true;
      if (r.slot == slot::Drive || r.slot == slot::Fold) shapeRouted = true;
    }
    const bool planeOn = plane_.setup(a_, twistRouted, echoRouted);
    govern(fmRouted, syncRouted, shapeRouted, planeOn);
    voiceFxFor(a_, vxA_, fmRouted, syncRouted, shapeRouted);
    const int wantShape = a_.shapeOS == 4 && govFactor_ == 4 ? 4 : 2;
    if (wantShape != ctx_.shapeFactor) {
      ctx_.shapeFactor = wantShape;
      shapeL_ = Shaper(wantShape, wantShape == 4 ? ctx_.taps4 : ctx_.taps2);
      shapeR_ = Shaper(wantShape, wantShape == 4 ? ctx_.taps4 : ctx_.taps2);
    }
    voiceFxFor(b_, vxB_, fmRouted, syncRouted, shapeRouted);
    ctx_.qMask = a_.qMask;
    ctx_.qGlide = a_.qGlideMs > 0 ? poleFor(a_.qGlideMs, rate_) : 1;
    crossFade_ = std::exp(-1 / std::fmax(1.0, a_.crossDecayMs * rate_ / 1000));
    scoreFade_ = std::exp(-1 / std::fmax(1.0, a_.scoreDecayMs * rate_ / 1000));

    const double octave = std::pow(2.0, a_.octaves);
    const double glide = a_.glideMs > 0 ? poleFor(a_.glideMs, rate_) : 1;
    const double kickFriction = std::exp(-dt / kKickTau);
    if (!freqStarted_) { freqNow_ = a_.freq; freqStarted_ = true; }
    const bool fromGen2 = a_.fromGen2;
    const int inMode = fromGen2 || (inBuf_ != nullptr && inLen_ >= n) ? toInt32(a_.inputMode) : 0;
    const double inDepth = a_.inputDepth;

    for (int i = 0; i < n; i++) {
      lfoStep(lfos_[0], rate_, random_);
      lfoStep(lfos_[1], rate_, random_);
      sumRoutes();

      freqNow_ += (a_.freq - freqNow_) * glide;
      const double level = gated_ ? env_.step() : 1;
      const double freq = freqNow_ * std::pow(2.0, mod(slot::Freq));
      const double amp = a_.amp * (1 - mod(slot::Amp)) * level;
      const double phase = a_.phase + mod(slot::Phase) * kPi;
      const double ratio = intervalRatio(a_.interval, a_.just) * octave + mod(slot::Ratio) * 0.5;
      const double detail = a_.detail + mod(slot::Detail) * 4;
      const double tumble = a_.spinRate * std::pow(3.0, mod(slot::Tumble));
      const double depth = std::fmax(0.0, std::fmin(1.0, a_.depth + mod(slot::Depth) * 0.5));
      const WaveTables bars = tablesFor(a_, barsA_, genMod_);
      const double morphPush = modOr0(slot::Morph) * 1.5;
      const double widthPush = modOr0(slot::Width) * 0.45;
      const double tablePush = modOr0(slot::Table) * 1.5;
      const double amount = shapeAmount(a_, morphPush, widthPush, tablePush);
      const double fmPush = modOr0(slot::Fm) * 5, syncPush = modOr0(slot::Sync) * 3.5;
      vxA_.fmI = std::fmax(0.0, std::fmin(20.0, a_.fmIndex + fmPush));
      vxA_.syncR = std::fmax(1.0, std::fmin(8.0, a_.syncRatio + syncPush));
      vxB_.fmI = std::fmax(0.0, std::fmin(20.0, b_.fmIndex + modBOr0(slot::Fm) * 5));
      vxB_.syncR = std::fmax(1.0, std::fmin(8.0, b_.syncRatio + modBOr0(slot::Sync) * 3.5));
      const double drivePush = modOr0(slot::Drive) * 0.5, foldPush = modOr0(slot::Fold) * 0.5;
      vxA_.vcfPush = modOr0(slot::Vcf) * 3;
      vxB_.vcfPush = modBOr0(slot::Vcf) * 3;
      if (vxA_.shaping) setShaping(ctx_.shaping, a_, drivePush, foldPush);

      double xin = 0, fmIn = 1, clockHz = 0;
      bool clockReset = false;
      double g2x = 0, g2y = 0;
      if (fromGen2) {
        gen2Phase_ += a_.gen2Rate * dt;
        if (gen2Phase_ >= 1) gen2Phase_ -= std::floor(gen2Phase_);
        const auto at2 = figureAt(a_.gen2Figure, gen2Phase_, 5, nullptr);
        g2x = a_.gen2Amp * at2[0];
        g2y = a_.gen2Amp * at2[1];
      }
      if (inMode != 0) {
        xin = fromGen2 ? g2x : inBuf_[i];
        if (inMode == 1) fmIn = std::fmax(0.0, 1 + inDepth * 4 * xin);
        else if (inMode == 3) {
          clock_.since++;
          if (clock_.low && xin > kClockHyst) {
            clock_.low = false;
            if (clock_.since >= 2) { clock_.period = clock_.since; clockReset = true; }
            clock_.since = 0;
          } else if (xin < -kClockHyst) clock_.low = true;
          if (clock_.period > 0 && clock_.since <= 2 * clock_.period) clockHz = rate_ / clock_.period;
        }
      }

      double l, r;
      bool heard = false;
      double hl = 0, hr = 0;

      if (a_.mode == Mode::Figure) {
        if (clockHz > 0) figurePhase_ = std::fmod(static_cast<double>(clock_.since) / clock_.period, 1.0);
        else figurePhase_ += a_.figureRate * fmIn * dt;
        if (figurePhase_ >= 1) { figurePhase_ -= 1; figureTurns_ = (figureTurns_ + 1) % kRoseTurns; }
        const auto at = figureAt(a_.figure, a_.figure == Figure::Rose ? figurePhase_ + figureTurns_ : figurePhase_,
                                 detail, a_.figPath.get());
        l = amp * at[0];
        r = amp * at[1];
      } else if (a_.mode == Mode::Wireframe) {
        const double spun = kick_ == 0 ? tumble : tumble * (1 + kick_);
        if (kick_ != 0) { kick_ *= kickFriction; if (std::fabs(kick_) < 1e-4) kick_ = 0; }
        const auto at = wire_.step(dt, a_.figureRate * fmIn, depth, {
          (a_.spin[0] + modOr0(slot::Spin) * 0.6) * spun,
          (a_.spin[1] + modOr0(slot::Spin + 1) * 0.6) * spun,
          (a_.spin[2] + modOr0(slot::Spin + 2) * 0.6) * spun,
        });
        l = amp * at[0];
        r = amp * at[1];
      } else if (a_.mode == Mode::Harmonograph) {
        swing_ += dt;
        const double drive = a_.pitched ? 0 : std::fmax(0.0, std::fmin(1.0, a_.swingDrive + modOr0(slot::Swing) * 0.5));
        double env;
        if (a_.pitched) env = std::exp(-swing_ * 1000 / std::fmax(1.0, a_.ringMs));
        else if (drive > 0) {
          swingEnv_ += (-a_.decay * swingEnv_ + kSwingDriveRate * drive * (1 - swingEnv_)) * dt;
          env = swingEnv_;
          swing_ = -std::log(std::fmax(1e-9, env)) / std::fmax(1e-6, a_.decay);
        } else { env = std::exp(-a_.decay * swing_); swingEnv_ = env; }
        if (env < 0.015 && !a_.pitched) { swing_ = 0; swingEnv_ = 1; phaseL_ = 0; phaseR_ = 0; relet_ = reletSamples_; }
        const double k = 1 + a_.detune;
        const double swingHz = (!a_.pitched ? a_.swingRate
                                : ctx_.qMask ? quantise(qA_, freq, ctx_.qMask, ctx_.qHold, ctx_.qGlide) : freq) * fmIn;
        if (a_.pitched) lastHz_ = swingHz;
        phaseL_ += kTwoPi * swingHz * dt;
        phaseR_ += kTwoPi * swingHz * ratio * dt;
        double gain = env;
        if (relet_ > 0) {
          const double through = 1 - static_cast<double>(relet_) / reletSamples_;
          const double rise = 0.5 - 0.5 * std::cos(kPi * through);
          gain = striking_ ? strikeFrom_ + (env - strikeFrom_) * rise : env * rise;
          relet_--;
          if (relet_ == 0) striking_ = false;
        }
        lastGain_ = gain;
        l = amp * gain * (std::sin(phaseL_) + std::sin(phaseL_ * k + phase)) / 2;
        r = amp * gain * (std::sin(phaseR_ + phase) + std::sin(phaseR_ * k)) / 2;
      } else if (poly) {
        sound(voices_, a_, bars, amount, std::pow(2.0, mod(slot::Freq)), 1 - mod(slot::Amp), dt, roleGlide, vxA_, ctx_);
        l = ctx_.mix[0]; r = ctx_.mix[1]; hl = ctx_.mix[2]; hr = ctx_.mix[3]; heard = true;
      } else {
        const double hz = (clockHz > 0 ? clockHz
                           : ctx_.qMask ? quantise(qA_, freq, ctx_.qMask, ctx_.qHold, ctx_.qGlide) : freq) * fmIn;
        lastHz_ = hz;
        if (clockReset) { phaseL_ = 0; phaseR_ = 0; }
        phaseL_ += kTwoPi * hz * dt;
        phaseR_ += kTwoPi * hz * ratio * dt;
        if (phaseL_ >= kPhaseWrap) phaseL_ -= kPhaseWrap;
        if (phaseR_ >= kPhaseWrap) phaseR_ -= kPhaseWrap;
        if (phaseR_ < 0) phaseR_ += kPhaseWrap;
        const double stepL = std::fabs(hz) / rate_;
        const double stepR = std::fabs(hz * ratio) / rate_;
        double wl, wr;
        if (a_.noise) {
          wl = noiseStep(noiseL_, a_.noiseShape, phaseL_, stepL, random_);
          wr = noiseStep(noiseR_, a_.noiseShape, phaseR_ + phase, stepR, random_);
        } else if (vxA_.on) {
          wl = oscStep(oscL_, phaseL_, 0, hz, a_, bars, amount, vxA_, rate_);
          wr = oscStep(oscR_, phaseR_, phase, hz * ratio, a_, bars, amount, vxA_, rate_);
        } else {
          wl = waveAt(a_.shape, phaseL_, stepL, bars, amount);
          wr = waveAt(a_.shape, phaseR_ + phase, stepR, bars, amount);
        }
        if (vxA_.shaping) { wl = shapeL_.step(wl, ctx_.shaping); wr = shapeR_.step(wr, ctx_.shaping); }
        if (vxA_.crushing) { wl = crushStep(crushL_, wl, a_, vxA_, rate_); wr = crushStep(crushR_, wr, a_, vxA_, rate_); }
        if (vxA_.filtering) {
          const double fl = gated_ ? fenv_.step() : 0;
          wl = svfStep(vcfL_, wl, vcfCoef(vcfL_, a_, hz, fl, vxA_.vcfPush, rate_), vxA_.vcfK, a_.vcfType);
          wr = svfStep(vcfR_, wr, vcfCoef(vcfR_, a_, hz * ratio, fl, vxA_.vcfPush, rate_), vxA_.vcfK, a_.vcfType);
        }
        l = amp * wl;
        r = amp * wr;
      }

      if (inMode == 2) {
        const double g = 1 + inDepth * 2 * xin;
        l *= g; r *= g;
        if (heard) { hl *= g; hr *= g; }
      }

      if (planeOn) {
        planeTick(dt);
        plane_.step(Plane::A, a_, l, r); l = plane_.x; r = plane_.y;
      }
      outL[i] = static_cast<float>(std::fmax(-1.0, std::fmin(1.0, l)));
      outR[i] = static_cast<float>(std::fmax(-1.0, std::fmin(1.0, r)));

      double bhl = 0, bhr = 0;
      if (layered) {
        const WaveTables barsOfB = tablesFor(b_, barsB_, genModB_);
        const double amountOfB = shapeAmount(b_, modBOr0(slot::Morph) * 1.5, modBOr0(slot::Width) * 0.45,
                                             modBOr0(slot::Table) * 1.5);
        if (vxB_.shaping) setShaping(ctx_.shaping, b_, modBOr0(slot::Drive) * 0.5, modBOr0(slot::Fold) * 0.5);
        sound(voicesB_, b_, barsOfB, amountOfB, std::pow(2.0, modB(slot::Freq)), 1 - modB(slot::Amp), dt, roleGlide,
              vxB_, ctx_);
        bhl = ctx_.mix[2]; bhr = ctx_.mix[3];
        if (outBL) {
          double bx = ctx_.mix[0], by = ctx_.mix[1];
          if (planeOn) { plane_.step(Plane::B, a_, bx, by); bx = plane_.x; by = plane_.y; }
          outBL[i] = static_cast<float>(std::fmax(-1.0, std::fmin(1.0, bx)));
          outBR[i] = static_cast<float>(std::fmax(-1.0, std::fmin(1.0, by)));
        }
      } else if (outBL) {
        outBL[i] = fromGen2 ? static_cast<float>(std::fmax(-1.0, std::fmin(1.0, g2x))) : 0.0f;
        outBR[i] = fromGen2 ? static_cast<float>(std::fmax(-1.0, std::fmin(1.0, g2y))) : 0.0f;
      }

      double pluck = 0;
      if (a_.crossOn) {
        crossStep(cross_[0], outL[i], a_.crossX);
        crossStep(cross_[1], outR[i], a_.crossY);
        pluck = a_.crossLevel * (crossVoice(cross_[0], a_.crossHzX) + crossVoice(cross_[1], a_.crossHzY)) / 2;
      }
      if (scoreStruck_ > 0) {
        double sum = 0;
        int live = 0;
        for (auto& v : score_) {
          sum += scoreVoice(v);
          if (v.env > 0) live++;
        }
        pluck += a_.scoreLevel * sum / 2;
        if (live == 0) scoreStruck_ = 0;
      }

      if (heardL) {
        double hx = (heard ? hl : static_cast<double>(outL[i])) + bhl;
        double hy = (heard ? hr : static_cast<double>(outR[i])) + bhr;
        if (planeOn && heard) { plane_.step(Plane::Heard, a_, hx, hy); hx = plane_.x; hy = plane_.y; }
        heardL[i] = static_cast<float>(hx + pluck);
        heardR[i] = static_cast<float>(hy + pluck);
      }
    }

    for (auto* pool : { &voices_, &voicesB_ }) {
      for (std::size_t v = pool->size(); v-- > 0;) {
        const Voice& voice = (*pool)[v];
        if (!voice.held && (voice.env.stage() == Envelope::Stage::Idle || voice.gone)) {
          pool->erase(pool->begin() + static_cast<long>(v));
        }
      }
    }
  }

 private:
  static constexpr double kKickSize = 6, kKickTau = 1.2, kKickMost = 20;
  static constexpr double kSwingDriveRate = 3;
  static constexpr double kClockHyst = 0.01;
  static constexpr int kRoseTurns = 10080;
  static constexpr double kCrossHysteresis = 0.05;

  // JavaScript's `| 0`: towards nought, and a value past 32 bits wrapped.
  static int toInt32(double v) {
    if (!std::isfinite(v)) return 0;
    const double t = std::trunc(v);
    const double m = std::fmod(t, 4294967296.0);
    const double u = m < 0 ? m + 4294967296.0 : m;
    return static_cast<int>(static_cast<std::uint32_t>(u));
  }

  // A layer's numeric fields, which both layers have.
  static bool setLayerNumber(LayerSettings& t, std::string_view field, double v) {
    if (field == "amp") t.amp = v;
    else if (field == "attackMs") t.env.attackMs = v;
    else if (field == "decayMs") t.env.decayMs = v;
    else if (field == "sustain") t.env.sustain = v;
    else if (field == "releaseMs") t.env.releaseMs = v;
    else if (field == "fAttackMs") t.fenv.attackMs = v;
    else if (field == "fDecayMs") t.fenv.decayMs = v;
    else if (field == "fSustain") t.fenv.sustain = v;
    else if (field == "fReleaseMs") t.fenv.releaseMs = v;
    else if (field == "morph") t.morph = v;
    else if (field == "width") t.width = v;
    else if (field == "table") t.table = v;
    else if (field == "modRatio") t.modRatio = v;
    else if (field == "fmIndex") t.fmIndex = v;
    else if (field == "ringMix") t.ringMix = v;
    else if (field == "syncRatio") t.syncRatio = v;
    else if (field == "subLevel") t.subLevel = v;
    else if (field == "subOctave") t.subOctave = static_cast<int>(v);
    else if (field == "unison") t.unison = v;
    else if (field == "unisonCents") t.unisonCents = v;
    else if (field == "drive") t.drive = v;
    else if (field == "fold") t.fold = v;
    else if (field == "crushBits") t.crushBits = v;
    else if (field == "crushHz") t.crushHz = v;
    else if (field == "vcfType") t.vcfType = static_cast<int>(v);
    else if (field == "vcfCutoff") t.vcfCutoff = v;
    else if (field == "vcfQ") t.vcfQ = v;
    else if (field == "vcfTrack") t.vcfTrack = v;
    else if (field == "vcfEnv") t.vcfEnv = v;
    else return false;
    return true;
  }

  void restartSwing() { swing_ = 0; swingEnv_ = 1; relet_ = 0; striking_ = false; }

  // The accumulator read as the page reads it: plainly, or with `|| 0`, which
  // also turns a NaN into nought.
  double mod(int k) const { return genMod_[static_cast<std::size_t>(k)]; }
  double modB(int k) const { return genModB_[static_cast<std::size_t>(k)]; }
  double modOr0(int k) const { const double v = mod(k); return std::isnan(v) ? 0 : v; }
  double modBOr0(int k) const { const double v = modB(k); return std::isnan(v) ? 0 : v; }

  void sumRoutes() {
    std::fill(genMod_.begin(), genMod_.end(), 0.0f);
    std::fill(genModB_.begin(), genModB_.end(), 0.0f);
    for (const auto& route : routes_) {
      if (route.slot < 0 || route.slot >= slots_) continue;  // the page's typed array ignores the write
      const auto s = static_cast<std::size_t>(route.slot);
      const bool osc = route.index >= 0;
      const double o = osc ? lfos_[static_cast<std::size_t>(route.index)].value : 0;
      const double value = osc ? o : route.held, valueB = osc ? o : route.heldB;
      genMod_[s] = static_cast<float>(genMod_[s] + (route.unipolar ? route.amount * (1 - value) / 2 : route.amount * value));
      genModB_[s] = static_cast<float>(genModB_[s] + (route.unipolar ? route.amountB * (1 - valueB) / 2 : route.amountB * valueB));
    }
  }

  struct Registration { std::array<double, 9> at {}, weights {}; };

  // The drawbars' weights from the bars and their pushes, worked out again
  // only when a level moves.
  const std::array<double, 9>& registration(const LayerSettings& t, Registration& into, const std::vector<float>& m) {
    bool moved = false;
    for (std::size_t k = 0; k < 9; k++) {
      const double raw = m[static_cast<std::size_t>(slot::Drawbar) + k], push = std::isnan(raw) ? 0 : raw;
      const double level = std::fmax(0.0, std::fmin(8.0, t.bars[k] + push * 8));
      if (level != into.at[k]) { into.at[k] = level; moved = true; }
    }
    if (moved) drawbarWeights(into.at, into.weights);
    return into.weights;
  }

  // What `bars` is for the layer's shape. One drawn cycle for the page: layer
  // B draws with layer A's.
  WaveTables tablesFor(const LayerSettings& t, Registration& into, const std::vector<float>& m) {
    WaveTables w;
    if (t.shapeName == "drawbars") w.weights = &registration(t, into, m);
    else if (t.shapeName == "drawn") w.cycle = a_.cycle.get();
    else if (t.shapeName == "wavetable") w.bank = a_.wavetable.get();
    return w;
  }

  void planeTick(double dt) {
    const double e = mod(slot::EchoTime);
    plane_.tick(a_, modOr0(slot::Radius), modOr0(slot::Twist), modOr0(slot::Echo), std::isnan(e) ? 0 : e, dt);
  }

  // --- S10: the governor ------------------------------------------------------

  double voiceCost(const LayerSettings& t, int n, int factor, bool fmRouted, bool syncRouted, bool shapeRouted) const {
    double c = 2.5;
    if (t.noise) c += 3;
    else {
      const bool fm = t.fmIndex > 0 || fmRouted, sync = t.syncRatio != 1 || syncRouted;
      const bool ring = t.ringMix > 0, sub = t.subLevel > 0;
      const std::string& s = t.shapeName;
      if (fm || sync || ring || sub || n > 1) {
        const double copy = s == "morph" ? 6.8 : s == "drawbars" ? 5.3 : s == "pulse" ? 2.8 : s == "wavetable" ? 2.2 : 2;
        c += 2.3 + n * (copy + (fm ? 1.9 : 0) + (sync ? 1.6 : 0) + (ring ? 1.3 : 0)) + (sub ? 2.5 : 0);
      } else c += s == "morph" ? 7 : s == "drawbars" ? 5.5 : s == "pulse" ? 2.4 : s == "wavetable" ? 2.5 : 2;
    }
    if (t.drive > 0 || t.fold > 0 || shapeRouted) c += factor == 4 ? 30 : factor == 2 ? 17 : NAN;
    if (t.crushBits > 0 || t.crushHz > 0) c += 2;
    if (t.vcfType > 0) c += 4;
    return c;
  }

  static int liveIn(const std::vector<Voice>& pool) {
    int n = 0;
    for (const auto& v : pool) if (!cutting(v)) n++;
    return n;
  }

  // Releasing before held, undrawn before drawn, and the oldest of a rank.
  Voice* victim(const std::vector<std::vector<Voice>*>& pools) {
    Voice* best = nullptr;
    double bestRank = INFINITY;
    for (auto* pool : pools) {
      for (auto& voice : *pool) {
        if (cutting(voice)) continue;
        const double rank = (!voice.held ? 0 : voice.targets[0] == 0 && voice.targets[1] == 0 ? 1 : 2) * 1e9 + voice.born;
        if (rank < bestRank) { bestRank = rank; best = &voice; }
      }
    }
    return best;
  }

  void govern(bool fmRouted, bool syncRouted, bool shapeRouted, bool planeOn) {
    const bool waving = a_.mode == Mode::Wave;
    const bool poly = a_.voices.has_value(), layered = b_.voices.has_value();
    std::vector<std::vector<Voice>*> pools;
    if (waving && poly) pools.push_back(&voices_);
    if (layered) pools.push_back(&voicesB_);
    int countA = !waving ? 0 : poly ? liveIn(voices_) : 2;
    int countB = layered ? liveIn(voicesB_) : 0;
    const int askedA = unisonAsked(a_), askedB = unisonAsked(b_), askedF = a_.shapeOS == 4 ? 4 : 2;
    const int passes = 1 + (poly ? 1 : 0) + (layered ? 1 : 0);
    const double planeCost = plane_.factor() == 1 ? 3.3 : plane_.factor() == 2 ? 30 : plane_.factor() == 4 ? 60 : 0;
    const double fixed = !planeOn ? 0 : passes * ((plane_.nonlinearOn() ? planeCost : 0) + (plane_.timeOn() ? 5.3 : 0));
    const double costA = voiceCost(a_, askedA, askedF, fmRouted, syncRouted, shapeRouted);
    const double costB = voiceCost(b_, askedB, askedF, fmRouted, syncRouted, shapeRouted);
    const bool free = ctx_.chordMoved || costA != askedCostA_ || costB != askedCostB_ || fixed != askedFixed_;
    ctx_.chordMoved = false; askedCostA_ = costA; askedCostB_ = costB; askedFixed_ = fixed;
    int nA = askedA, nB = askedB, factor = askedF;
    if (!free) { nA = std::min(nA, vxA_.cap); nB = std::min(nB, vxB_.cap); factor = std::min(factor, govFactor_); }
    const auto total = [&] {
      return fixed + countA * voiceCost(a_, nA, factor, fmRouted, syncRouted, shapeRouted)
             + countB * voiceCost(b_, nB, factor, fmRouted, syncRouted, shapeRouted);
    };
    if (factor == 4 && total() > kVoiceBudget) factor = 2;
    while (total() > kVoiceBudget) {
      const bool canA = countA > 0 && nA > 1, canB = countB > 0 && nB > 1;
      if (!canA && !canB) break;
      if (canA && (!canB || nA >= nB)) nA--; else nB--;
    }
    while (total() > kVoiceBudget && countA + countB > 1) {
      Voice* voice = victim(pools);
      if (voice == nullptr) break;
      voice->fade = ctx_.cutSamples;
      const bool inA = voice >= voices_.data() && voice < voices_.data() + voices_.size();
      if (inA) countA--; else countB--;
    }
    vxA_.cap = nA; vxB_.cap = nB; govFactor_ = factor;
    int silenced = 0;
    for (auto* pool : pools) for (const auto& v : *pool) if (v.held && cutting(v)) silenced++;
    budget_.units = total(); budget_.asked = { askedA, askedB }; budget_.unison = { nA, nB };
    budget_.askedFactor = askedF; budget_.factor = factor; budget_.silenced = silenced;
  }

  // --- the crossings and the score's voices ------------------------------------

  struct CrossLine { bool armed = false; int wait = 0, count = 0; double env = 0; bool attacking = false; double phase = 0; };
  struct ScoreVoice { double hz = 0, vel = 0, env = 0, phase = 0; bool attacking = false; long age = 0; };

  void crossStep(CrossLine& line, double beam, double at) const {
    if (line.wait > 0) line.wait--;
    if (beam < at - kCrossHysteresis) line.armed = true;
    else if (line.armed && beam >= at && line.wait == 0) {
      line.armed = false;
      line.wait = crossHold_;
      line.count++;
      line.attacking = true;
    }
  }

  double crossVoice(CrossLine& line, double hz) const {
    if (line.attacking) {
      line.env += crossAttack_;
      if (line.env >= 1) { line.env = 1; line.attacking = false; }
    } else {
      line.env *= crossFade_;
    }
    line.phase += kTwoPi * hz / rate_;
    if (line.phase >= kTwoPi) line.phase -= kTwoPi;
    return line.env * std::sin(line.phase);
  }

  double scoreVoice(ScoreVoice& v) const {
    if (v.attacking) {
      v.env += crossAttack_;
      if (v.env >= 1) { v.env = 1; v.attacking = false; }
    } else if (v.env > 0) {
      v.env *= scoreFade_;
      if (v.env < 1e-5) v.env = 0;
    }
    v.age++;
    if (v.env == 0) return 0;
    v.phase += kTwoPi * v.hz / rate_;
    if (v.phase >= kTwoPi) v.phase -= kTwoPi;
    return v.vel * v.env * std::sin(v.phase);
  }

  double rate_;
  int slots_;
  std::vector<Lfo>& lfos_;
  Random random_;
  Tone a_;
  LayerSettings b_;
  std::vector<float> genMod_, genModB_;
  std::vector<Route> routes_;
  Registration barsA_, barsB_;

  double phaseL_ = 0, phaseR_ = 0, figurePhase_ = 0;
  int figureTurns_ = 0;
  double swing_ = 0, swingEnv_ = 1, kick_ = 0;
  const float* inBuf_ = nullptr;
  int inLen_ = 0;
  double gen2Phase_ = 0;
  struct { bool low = true; long since = 0, period = 0; } clock_;
  int reletSamples_, relet_ = 0;
  bool striking_ = false;
  double strikeFrom_ = 0, lastGain_ = 0;
  bool gated_ = false;
  Envelope env_, fenv_;
  bool freqStarted_ = false;
  double freqNow_ = 0;
  VcfState vcfL_, vcfR_;
  std::vector<Voice> voices_, voicesB_;
  Plane plane_;
  VoiceContext ctx_;
  Quantiser qA_;
  double lastHz_ = 0;
  int crossHold_;
  double crossAttack_;
  std::array<CrossLine, 2> cross_;
  double crossFade_ = 0;
  std::array<ScoreVoice, 4> score_;
  double scoreFade_ = 0;
  int scoreStruck_ = 0;
  Wireframe wire_;
  VoiceFx vxA_, vxB_;
  double askedCostA_ = -1, askedCostB_ = -1, askedFixed_ = -1;
  int govFactor_ = 4;
  Budget budget_;
  Shaper shapeL_, shapeR_;
  Crush crushL_, crushR_;
  Osc oscL_, oscR_;
  NoiseState noiseL_, noiseR_;
};

}  // namespace scope
