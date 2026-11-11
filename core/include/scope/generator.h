// The generator, ported from `makeGeneratorCore` in web/scope.html: the
// per-sample loop that makes the waveform's pair - the dyad, or the chord on
// one layer or two - through the routings, the governor, the plane and the
// score's voices, and the calls the worklet makes of it. (The drawings - the
// pendulums, the figures, the solids and the second generator - went in G2,
// 9 Nov: the owner did not miss them.) It is held to the page's own `makeGeneratorCore` whole,
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
//   or one of the structured fields (the bars, the chord, a drawn cycle),
//   each with its own call. A field the page would take but
//   never reads is ignored rather than kept.
// - The routings' accumulator is a Float32Array in the page, so it is `float`
//   here and every sum into it is rounded as the page rounds it. It is made at
//   least as long as the slots the loop reads, so a core asked for fewer
//   slots than that reads nought from the ones it lacks, which is what the
//   page's `|| 0` gives for most of them; the page reads `undefined` from the
//   seven it does not guard, and no caller makes a core that small.
// - The outputs are float, as an AudioWorklet's are, and the loop reads its
//   own picture back from them as the page does - the heard pair sees the
//   picture as rounded, not as computed.

#pragma once

#include <array>
#include <cmath>
#include <memory>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include "scope/envelope.h"
#include "scope/lfo.h"
#include "scope/noise.h"
#include "scope/osc.h"
#include "scope/plane.h"
#include "scope/scan.h"
#include "scope/voice.h"
#include "scope/voices.h"
#include "scope/wave.h"

namespace scope {

// Where each destination sits in the routings' accumulator: GEN_DESTS's slots.
// The drawings' went in G2 and their slots are left empty rather than the
// rest renumbered: the page's GEN_DESTS and this share the numbers, and an
// off-by-one between them would be silent. Nothing writes or reads 4, 5, 6
// (the figure's detail, the solid's spin rate and perspective), 26 (the
// pendulums' energy) or 29 to 31 (the solid's three spins).
namespace slot {
constexpr int Freq = 0, Amp = 1, Phase = 2, Ratio = 3;
constexpr int Drawbar = 7, Morph = Drawbar + 9, Radius = Morph + 1, Twist = Radius + 1, Fm = Twist + 1, Sync = Fm + 1;
constexpr int Drive = Sync + 1, Fold = Drive + 1, Vcf = Fold + 1, Echo = Vcf + 1, EchoTime = Echo + 1;
constexpr int Width = EchoTime + 2, Table = Width + 1;
constexpr int Turn = Table + 4;  // layer B's turn, after the solid's three spins that were
constexpr int Bend = Turn + 1, BendAt = Bend + 1;  // the voice's bend and where it centres
constexpr int Phaser = BendAt + 1;  // the phaser's amount (P8e)
constexpr int DelayTone = Phaser + 1;  // the delay's tone (8 Nov)
constexpr int Reverb = DelayTone + 1, ReverbSize = Reverb + 1, ReverbTone = ReverbSize + 1;  // P9
constexpr int Used = ReverbTone + 1;  // the slots the loop reads
// Held where they were before G2 emptied the drawings' slots between them.
static_assert(Drawbar == 7 && EchoTime == 25 && Width == 27 && Table == 28 && Turn == 32 && Used == 40,
              "a slot moved: the page's GEN_DESTS numbers them too");
}  // namespace slot

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

// Layer B's: the voice, and a plane of its own in force only while
// `planeOwn` is on, `planeTurn` its turn in radians, B's alone; and a phaser,
// chorus, delay and reverb of its own, each in force while its bit is set in
// `timeOwn` (G6, the page's TIME_OWN: 1, 2, 4, 8) - one switch with the
// plane's until each module had its own link.
struct LayerBSettings : LayerSettings, PlaneLayerTone {
  bool planeOwn = false;
  double planeTurn = 0;
  int timeOwn = 0;
};

// Layer A's tone, which is also the page's: everything but the voice.
struct Tone : LayerSettings, PlaneTone {
  double freq = 220;
  int interval = 0;
  double octaves = 0;
  bool just = true;
  double phase = kPi / 2;
  bool polyRound = false;  // poly's quarter turn (P8g): see the page's ROUND_RING
  double pitchBend = 0, vibrato = 0;  // the keyboard's, in semitones (6 Nov): see the page's tone
  // The Envelope card's own (8 Nov), whether env.note reads it, and its four times.
  bool menvOwn = false;
  bool menvEvery = false;  // once a phrase, or again on every note, as the page's
  EnvelopeTone menv { 10, 300, 0.5, 400 };
  double inputMode = 0, inputDepth = 0.5;
  std::shared_ptr<const CycleTables> cycle;
  std::shared_ptr<const std::vector<CycleTables>> wavetable;
  double shapeOS = 2, glideMs = 0;
  int qMask = 0;
  double qGlideMs = 0;
  double scoreDecayMs = 400, scoreLevel = 0.4;
  // The master Output (G7), as a gain on what is heard alone: the page's tone says why.
  double output = 1;
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
  // Every key a pedal can hold, and the tails let ring past them: more is made room for as it comes.
  static constexpr std::size_t kVoicesKept = 128 + kPolyTails;

  Generator(double rate, int slots, std::vector<Lfo>& lfos, std::uint32_t seed = 1)
      : rate_(rate), slots_(slots), lfos_(lfos), random_(seed),
        genMod_(static_cast<std::size_t>(std::max(slots, slot::Used)), 0.0f), genModB_(genMod_),
        env_(rate, a_.env), fenv_(rate, a_.fenv), menv_(rate, a_.menv), plane_(rate), ctx_(rate),
        scoreAttack_(1 / std::max(1.0, jsRound(0.002 * rate))),
        shapeL_(2, ctx_.taps2), shapeR_(2, ctx_.taps2),
        noiseL_(random_), noiseR_(random_) {
    ctx_.random = &random_;
    // Room for a held chord and its tails in each layer, so a note born does not move the list (G8).
    voices_.reserve(kVoicesKept);
    voicesB_.reserve(kVoicesKept);
    fenv_.reset(0);
    menv_.reset(0);
    barsA_.at.fill(-1); barsB_.at.fill(-1);
  }
  Generator(const Generator&) = delete;
  Generator& operator=(const Generator&) = delete;

  Tone& tone() { return a_; }
  const Tone& tone() const { return a_; }
  LayerBSettings& toneB() { return b_; }
  const LayerBSettings& toneB() const { return b_; }

  // --- the page's `set`, by kind of value -----------------------------------

  void set(std::string_view field, double value, int layer = 0) {
    LayerSettings& t = layer == 1 ? static_cast<LayerSettings&>(b_) : a_;
    if (setLayerNumber(t, field, value)) return;
    if (layer == 1) {
      if (setPlaneShape(b_, field, value) || setPlaneTime(b_, field, value)) return;
      if (field == "planeOwn") b_.planeOwn = value != 0;
      else if (field == "planeTurn") b_.planeTurn = value;
      // The page's `timeOwn | 0`: a mask, and anything that is not a number is none.
      else if (field == "timeOwn") b_.timeOwn = std::isfinite(value) ? static_cast<int>(value) : 0;
      return;
    }
    Tone& a = a_;
    if (setPlaneShape(a, field, value) || setPlaneTime(a, field, value)) return;
    if (field == "freq") a.freq = value;
    else if (field == "interval") a.interval = static_cast<int>(value);
    else if (field == "octaves") a.octaves = value;
    else if (field == "just") a.just = value != 0;
    else if (field == "polyRound") a.polyRound = value != 0;
    else if (field == "pitchBend") a.pitchBend = value;
    else if (field == "vibrato") a.vibrato = value;
    else if (field == "phase") a.phase = value;
    else if (field == "inputMode") a.inputMode = value;
    else if (field == "inputDepth") a.inputDepth = value;
    else if (field == "shapeOS") a.shapeOS = value;
    else if (field == "glideMs") a.glideMs = value;
    else if (field == "qMask") a.qMask = static_cast<int>(value);
    else if (field == "qGlideMs") a.qGlideMs = value;
    else if (field == "menvOwn") a.menvOwn = value != 0;
    else if (field == "menvEvery") a.menvEvery = value != 0;
    else if (field == "menvAttackMs") a.menv.attackMs = value;
    else if (field == "menvDecayMs") a.menv.decayMs = value;
    else if (field == "menvSustain") a.menv.sustain = value;
    else if (field == "menvReleaseMs") a.menv.releaseMs = value;
    else if (field == "scoreDecayMs") a.scoreDecayMs = value;
    else if (field == "scoreLevel") a.scoreLevel = value;
    else if (field == "output") a.output = value;
    else if (field == "planeOS") a.planeOS = value;
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
  }

  // Copied and clamped; the page ignores a registration that is not nine.
  void setBars(const std::vector<double>& value, int layer = 0) { setBars(value.data(), value.size(), layer); }
  void setBars(const double* value, std::size_t n, int layer = 0) {
    if (n != 9) return;
    LayerSettings& t = layer == 1 ? static_cast<LayerSettings&>(b_) : a_;
    for (std::size_t k = 0; k < 9; k++) {
      const double v = std::isnan(value[k]) ? 0 : value[k];
      t.bars[k] = std::fmax(0.0, std::fmin(8.0, v));
    }
  }
  void setCycle(std::shared_ptr<const CycleTables> c) { a_.cycle = std::move(c); }
  void setWavetable(std::shared_ptr<const std::vector<CycleTables>> w) { a_.wavetable = std::move(w); }
  /* Scan's latest table for a layer, taken at the next tick (the page's
     `scanTable`). Not owned: the caller keeps it alive while it is this, or
     the one the layer is fading from or to (`scanPrev`, `scanNext`), which is
     what ScanTables is for. */
  void setScanTable(const CycleTables* table, int layer = 0) { (layer == 1 ? b_.scanTable : a_.scanTable) = table; }
  const CycleTables* scanTable(int layer) const { return layer == 1 ? b_.scanTable : a_.scanTable; }
  const CycleTables* scanPrev(int layer) const { return layer == 1 ? vxB_.scanPrev : vxA_.scanPrev; }
  const CycleTables* scanNext(int layer) const { return layer == 1 ? vxB_.scanNext : vxA_.scanNext; }

  // The chord: a list of notes, or none for no chord on that layer.
  void setVoices(const std::vector<NoteWant>* list, int layer = 0) {
    LayerSettings& t = layer == 1 ? static_cast<LayerSettings&>(b_) : a_;
    if (list == nullptr) t.voices.reset(); else t.voices = *list;
    reconcileVoices(layer == 1 ? voicesB_ : voices_, t.voices ? &*t.voices : nullptr, t, glideFrom_[layer == 1 ? 1 : 0], ctx_);
    bool held = false;
    for (const auto& v : voices_) held = held || v.held;
    for (const auto& v : voicesB_) held = held || v.held;
    menvGate(held);
  }

  void setRoutes(const std::vector<Route>& list) { routes_ = list; }

  // --- the rest of the worklet's calls --------------------------------------

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

  /* The page's genReswing, which restore still calls: the pair's phases
     back to nought and the voice's copies with them. Named for the
     pendulums it struck until G2; what is left of it is the waveform's. */
  void reswing() {
    phaseL_ = 0; phaseR_ = 0;
    oscL_.n = 0; oscR_.n = 0;
  }

  void gate(bool open, double velocity) { env_.gate(open, velocity); fenv_.gate(open, velocity); menvGate(open); }
  // A key gone down: the Envelope's own, on Every note, starts its attack again from where it is.
  void noteDown() {
    if (!a_.menvEvery || !menvHeld_) return;
    menv_.reset(menv_.level());
    menv_.gate(true, 1);
  }

  void setGated(bool on) {
    if (on == gated_) return;
    gated_ = on;
    env_.reset(on ? 0 : 1);
    fenv_.reset(0);
    menv_.reset(0);
    menvHeld_ = false;
  }

  // In poly the loudest voice; otherwise the envelope, or one ungated.
  double envelope() const {
    if (a_.menvOwn) return gated_ ? menv_.level() : 0;  // the Envelope card's own, as the page's
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
  const std::vector<Voice>& voices() const { return voices_; }
  const std::vector<Voice>& voicesB() const { return voicesB_; }
  const Budget& budget() const { return budget_; }
  // Where layer `l`'s voice was in its cycle at the last tick, 0 to 1, or -1 (scanHeadOf).
  double scanHead(int l) const { return scanHead_[l == 1 ? 1 : 0]; }
  static bool cutting(const Voice& v) { return v.gone || v.fade > 0; }

  /* The loop overlay's read-head (P8f): where a layer's voice was in its
     cycle at the moment its table last changed, as a fraction of a turn - the
     place round Scan's circle that sample was read from, since a table's
     index i is the reading's angle 2 pi i / n. The lowest held note's, the
     one the X lane leans onto, or the plain tone's own phase when no note
     sounds (`fallback`, NaN for B, which has none); -1 for nothing. One per
     tick, so drawn at sixty a second it is a stroboscope: it stands still
     on a note at a multiple of 60 Hz and turns at the difference otherwise,
     the voice's real phase sampled where the tables change. The page's
     `scanHeadOf`. */
  static double scanHeadOf(const std::vector<Voice>& pool, double fallback) {
    const Voice* low = nullptr;
    for (const auto& v : pool) if (!cutting(v) && v.freq > 0 && (!low || v.freq < low->freq)) low = &v;
    const double phase = low ? low->phase : fallback;
    if (std::isnan(phase)) return -1;
    const double turns = phase / kTwoPi;
    return turns - std::floor(turns);
  }

  // --- S1: a live input through the plane -----------------------------------

  void effect(const float* inL, const float* inR, float* outL, float* outR, int n) {
    const double dt = 1 / rate_;
    bool twistRouted = false, echoRouted = false, phaserRouted = false, reverbRouted = false;
    for (const auto& r : routes_) {
      if (r.slot == slot::Twist) twistRouted = true;
      if (r.slot == slot::Echo) echoRouted = true;
      if (r.slot == slot::Phaser) phaserRouted = true;
      if (r.slot == slot::Reverb) reverbRouted = true;
    }
    const bool planeOn = plane_.setup(a_, twistRouted, echoRouted, nullptr, 0, false, phaserRouted, reverbRouted);
    for (int i = 0; i < n; i++) {
      lfoStep(lfos_[0], rate_, random_);
      lfoStep(lfos_[1], rate_, random_);
      sumRoutes();
      if (planeOn) {
        planeTick(dt);
        plane_.step(Plane::A, inL[i], inR[i]);
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
    bool turnRouted = false, phaserRouted = false, bendRouted = false, reverbRouted = false;
    for (const auto& r : routes_) {
      if (r.slot == slot::Reverb) reverbRouted = true;
      if (r.slot == slot::Twist) twistRouted = true;
      if (r.slot == slot::Echo) echoRouted = true;
      if (r.slot == slot::Phaser) phaserRouted = true;
      if (r.slot == slot::Turn) turnRouted = true;
      // The bend is phase modulation as FM is, and switches the oscillator on alike.
      if (r.slot == slot::Fm || r.slot == slot::Bend || r.slot == slot::BendAt) fmRouted = true;
      if (r.slot == slot::Bend) bendRouted = true;
      if (r.slot == slot::Sync) syncRouted = true;
      if (r.slot == slot::Drive || r.slot == slot::Fold) shapeRouted = true;
    }
    const int timeOwn = b_.timeOwn & 15;
    const bool planeOn = plane_.setup(a_, twistRouted, echoRouted, layered && (b_.planeOwn || timeOwn != 0) ? &b_ : nullptr,
                                      b_.planeTurn, turnRouted, phaserRouted, reverbRouted, b_.planeOwn, timeOwn);
    govern(fmRouted, syncRouted, shapeRouted, planeOn);
    voiceFxFor(a_, vxA_, fmRouted, syncRouted, shapeRouted);
    const int wantShape = a_.shapeOS == 4 && govFactor_ == 4 ? 4 : 2;
    if (wantShape != ctx_.shapeFactor) {
      ctx_.shapeFactor = wantShape;
      shapeL_ = Shaper(wantShape, wantShape == 4 ? ctx_.taps4 : ctx_.taps2);
      shapeR_ = Shaper(wantShape, wantShape == 4 ? ctx_.taps4 : ctx_.taps2);
    }
    voiceFxFor(b_, vxB_, fmRouted, syncRouted, shapeRouted);
    // The bend's offset blocker, and the oscillator held on a second after a bend (the page says why).
    vxA_.dcK = vxB_.dcK = poleFor(1000 / (kTwoPi * kBendDcHz), rate_);
    vxA_.dcHold = a_.warp != 0 || bendRouted ? rate_ : std::fmax(0.0, vxA_.dcHold - n);
    vxB_.dcHold = b_.warp != 0 || bendRouted ? rate_ : std::fmax(0.0, vxB_.dcHold - n);
    if (vxA_.dcHold > 0) vxA_.on = true;
    if (vxB_.dcHold > 0) vxB_.on = true;
    // How much of each layer's voice is Scan this block: the depth, under the running-away hold.
    vxA_.scanW = scanWeight(a_);
    vxB_.scanW = scanWeight(b_);
    ctx_.qMask = a_.qMask;
    ctx_.qGlide = a_.qGlideMs > 0 ? poleFor(a_.qGlideMs, rate_) : 1;
    scoreFade_ = std::exp(-1 / std::fmax(1.0, a_.scoreDecayMs * rate_ / 1000));

    const double octave = std::pow(2.0, a_.octaves);
    const double glide = a_.glideMs > 0 ? poleFor(a_.glideMs, rate_) : 1;
    const double bendGlide = poleFor(kBendGlideMs, rate_);
    const double outGlide = poleFor(kOutputGlideMs, rate_);
    const double levelGlide = poleFor(kLevelGlideMs, rate_);
    if (!freqStarted_) { freqNow_ = a_.freq; freqStarted_ = true; }
    const int inMode = inBuf_ != nullptr && inLen_ >= n ? toInt32(a_.inputMode) : 0;
    const double inDepth = a_.inputDepth;

    for (int i = 0; i < n; i++) {
      lfoStep(lfos_[0], rate_, random_);
      lfoStep(lfos_[1], rate_, random_);
      scanAdvance();
      sumRoutes();
      if (gated_) menv_.step();  // the Envelope card's own, as the page's
      // Each hand's level and cutoff, B's whether or not it is sounding (the page's block says why).
      levelsStep(vxA_, a_, levelGlide);
      levelsStep(vxB_, b_, levelGlide);

      freqNow_ += (a_.freq - freqNow_) * glide;
      // Pitch bend and the wheel's vibrato, in octaves, glided (the page says why).
      bendNow_ += (a_.pitchBend - bendNow_) * bendGlide;
      vibNow_ += (a_.vibrato - vibNow_) * bendGlide;
      vibPhase_ += kTwoPi * kVibratoHz * dt;
      if (vibPhase_ >= kTwoPi) vibPhase_ -= kTwoPi;
      const double pitchOct = (bendNow_ + (vibNow_ != 0 ? vibNow_ * std::sin(vibPhase_) : 0)) / 12;
      const double level = gated_ ? env_.step() : 1;
      const double freq = freqNow_ * std::pow(2.0, mod(slot::Freq) + pitchOct);
      const double amp = vxA_.level * (1 - mod(slot::Amp)) * level;
      const double phase = a_.phase + mod(slot::Phase) * kPi;
      const double ratio = intervalRatio(a_.interval, a_.just) * octave + mod(slot::Ratio) * 0.5;
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
      vxA_.warpA = std::fmax(-0.9, std::fmin(0.9, a_.warp + modOr0(slot::Bend) * 0.9));
      vxB_.warpA = std::fmax(-0.9, std::fmin(0.9, b_.warp + modBOr0(slot::Bend) * 0.9));
      const double bendAtA = a_.warpAt + modOr0(slot::BendAt) * 0.5;
      const double bendAtB = b_.warpAt + modBOr0(slot::BendAt) * 0.5;
      vxA_.warpC = bendAtA - std::floor(bendAtA);
      vxB_.warpC = bendAtB - std::floor(bendAtB);
      vxA_.warpDc = vxA_.warpA != 0 ? besselJ1(vxA_.warpA) * std::sin(kTwoPi * vxA_.warpC) : 0;
      vxB_.warpDc = vxB_.warpA != 0 ? besselJ1(vxB_.warpA) * std::sin(kTwoPi * vxB_.warpC) : 0;
      const double drivePush = modOr0(slot::Drive) * 0.5, foldPush = modOr0(slot::Fold) * 0.5;
      vxA_.vcfPush = modOr0(slot::Vcf) * 3;
      vxB_.vcfPush = modBOr0(slot::Vcf) * 3;
      if (vxA_.shaping) setShaping(ctx_.shaping, a_, drivePush, foldPush);

      double xin = 0, fmIn = 1, clockHz = 0;
      bool clockReset = false;
      if (inMode != 0) {
        xin = inBuf_[i];
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

      if (poly) {
        sound(voices_, a_, bars, amount, std::pow(2.0, mod(slot::Freq) + pitchOct), 1 - mod(slot::Amp), dt, roleGlide, vxA_, ctx_,
              a_.polyRound, glide);
        l = ctx_.mix[0]; r = ctx_.mix[1];
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
          if (vxA_.scanW > 0) {
            wl = scanMix(wl, vxA_.scanPrev, vxA_.scanNext, phaseL_, stepL, vxA_.scanX, vxA_.scanW);
            wr = scanMix(wr, vxA_.scanPrev, vxA_.scanNext, phaseR_ + phase, stepR, vxA_.scanX, vxA_.scanW);
          }
        }
        if (vxA_.shaping) { wl = shapeL_.step(wl, ctx_.shaping); wr = shapeR_.step(wr, ctx_.shaping); }
        if (vxA_.crushing) { wl = crushStep(crushL_, wl, a_, vxA_, rate_); wr = crushStep(crushR_, wr, a_, vxA_, rate_); }
        if (vxA_.filtering) {
          const double fl = gated_ ? fenv_.step() : 0;
          wl = svfStep(vcfL_, wl, vcfCoef(vcfL_, a_, hz, fl, vxA_.vcfPush, vxA_.cut, rate_), vxA_.vcfK, a_.vcfType);
          wr = svfStep(vcfR_, wr, vcfCoef(vcfR_, a_, hz * ratio, fl, vxA_.vcfPush, vxA_.cut, rate_), vxA_.vcfK, a_.vcfType);
        }
        l = amp * wl;
        r = amp * wr;
      }

      if (inMode == 2) {
        const double g = 1 + inDepth * 2 * xin;
        l *= g; r *= g;
      }

      if (planeOn) {
        planeTick(dt);
        plane_.step(Plane::A, l, r); l = plane_.x; r = plane_.y;
      }
      // Nothing clamped: the page's block says why.
      outL[i] = static_cast<float>(l);
      outR[i] = static_cast<float>(r);

      // Layer B through its plane whether or not its lanes were asked for,
      // since it is heard either way.
      double bx = 0, by = 0;
      if (layered) {
        const WaveTables barsOfB = tablesFor(b_, barsB_, genModB_);
        const double amountOfB = shapeAmount(b_, modBOr0(slot::Morph) * 1.5, modBOr0(slot::Width) * 0.45,
                                             modBOr0(slot::Table) * 1.5);
        if (vxB_.shaping) setShaping(ctx_.shaping, b_, modBOr0(slot::Drive) * 0.5, modBOr0(slot::Fold) * 0.5);
        sound(voicesB_, b_, barsOfB, amountOfB, std::pow(2.0, modB(slot::Freq) + pitchOct), 1 - modB(slot::Amp), dt, roleGlide,
              vxB_, ctx_, a_.polyRound, glide);
        bx = ctx_.mix[0]; by = ctx_.mix[1];
        if (planeOn) { plane_.step(Plane::B, bx, by, true); bx = plane_.x; by = plane_.y; }
      }
      if (outBL) { outBL[i] = static_cast<float>(bx); outBR[i] = static_cast<float>(by); }

      // The score's voice, heard and not drawn; the page's block says why.
      double scored = 0;
      if (scoreStruck_ > 0) {
        double sum = 0;
        int live = 0;
        for (auto& v : score_) {
          sum += scoreVoice(v);
          if (v.env > 0) live++;
        }
        scored = a_.scoreLevel * sum / 2;
        if (live == 0) scoreStruck_ = 0;
      }

      // What is heard: the lanes, summed, and the score's voice, at the Output (G7).
      if (heardL) {
        outputStep(outGlide);
        heardL[i] = static_cast<float>((outL[i] + bx + scored) * outNow_);
        heardR[i] = static_cast<float>((outR[i] + by + scored) * outNow_);
      }
    }

    for (auto* pool : { &voices_, &voicesB_ }) {
      for (std::size_t v = pool->size(); v-- > 0;) {
        const Voice& voice = (*pool)[v];
        if (!voice.held && (voice.env.stage() == Envelope::Stage::Idle || voice.gone)) {
          retireVoice((*pool)[v], ctx_);
          pool->erase(pool->begin() + static_cast<long>(v));
        }
      }
    }
  }

  /* The Output on a pair that is heard and was never the generator's: the
     instrument's input, drawn whole or in bands, whose heard pair is the
     picture (Instrument::render). The same stage as the block's, glide and
     all, so going from the generator to the input and back is one gain that
     never jumps. Not the page's: its live input is not heard. */
  void hear(float* left, float* right, int n) {
    const double glide = poleFor(kOutputGlideMs, rate_);
    for (int i = 0; i < n; i++) {
      outputStep(glide);
      left[i] = static_cast<float>(left[i] * outNow_);
      if (right) right[i] = static_cast<float>(right[i] * outNow_);
    }
  }
  // Where the Output's gain has got to, for a harness; and a hand's level and cutoff (layer 1 is B's).
  double outputNow() const { return outNow_; }
  double levelNow(int layer) const { return (layer == 1 ? vxB_ : vxA_).level; }
  double cutNow(int layer) const { return (layer == 1 ? vxB_ : vxA_).cut; }
  /* The Output's gain put where it is asked, with no glide: for an
     instrument opening on a project that was turned down, whose first
     samples - an input heard at once, a note held from the start - would
     otherwise come out at unity for the glide's first tenth of a second. */
  void settleOutput() { outNow_ = a_.output; }

 private:
  static constexpr double kBendGlideMs = 5, kVibratoHz = 5.5;  // BEND_GLIDE_MS, VIBRATO_HZ
  // OUTPUT_GLIDE_MS and OUTPUT_SNAP, the page's block's: why there.
  static constexpr double kOutputGlideMs = 20, kOutputSnap = 1e-6;
  void outputStep(double glide) {
    outNow_ += (a_.output - outNow_) * glide;
    if (std::fabs(a_.output - outNow_) < kOutputSnap) outNow_ = a_.output;
  }
  // LEVEL_GLIDE_MS, LEVEL_SNAP and CUT_SNAP, and the page's levelsStep, where the page says why.
  static constexpr double kLevelGlideMs = 20, kLevelSnap = 1e-6, kCutSnap = 1e-6;
  static void levelsStep(VoiceFx& vx, const LayerTone& t, double k) {
    if (std::isnan(vx.level)) vx.level = t.amp;
    vx.level += (t.amp - vx.level) * k;
    if (std::fabs(t.amp - vx.level) < kLevelSnap) vx.level = t.amp;
    if (vx.cut == t.vcfCutoff) return;
    if (!(t.vcfCutoff > 0) || !(vx.cut > 0)) {
      vx.cut = vx.cutTo = t.vcfCutoff;
      vx.cutLn = vx.cutToLn = std::log(t.vcfCutoff);
      return;
    }
    if (t.vcfCutoff != vx.cutTo) { vx.cutTo = t.vcfCutoff; vx.cutToLn = std::log(t.vcfCutoff); }
    vx.cutLn += (vx.cutToLn - vx.cutLn) * k;
    if (std::fabs(vx.cutToLn - vx.cutLn) < kCutSnap) { vx.cutLn = vx.cutToLn; vx.cut = t.vcfCutoff; }
    else vx.cut = std::exp(vx.cutLn);
  }
  double outNow_ = 1;  // the Output's gain as it glides, a sample at a time
  static constexpr double kClockHyst = 0.01;

  // JavaScript's `| 0`: towards nought, and a value past 32 bits wrapped.
  static int toInt32(double v) {
    if (!std::isfinite(v)) return 0;
    const double t = std::trunc(v);
    const double m = std::fmod(t, 4294967296.0);
    const double u = m < 0 ? m + 4294967296.0 : m;
    return static_cast<int>(static_cast<std::uint32_t>(u));
  }

  // The plane's echo and chorus, which layer A has in its tone and layer B
  // of its own.
  static bool setPlaneTime(PlaneTimeTone& p, std::string_view field, double v) {
    if (field == "delayMix") p.delayMix = v;
    else if (field == "delayMs") p.delayMs = v;
    else if (field == "delayFeedback") p.delayFeedback = v;
    else if (field == "delayPingPong") p.delayPingPong = v != 0;
    else if (field == "delayTone") p.delayTone = v;
    else if (field == "delayLowCut") p.delayLowCut = v;
    else if (field == "delayWidth") p.delayWidth = v;
    else if (field == "delayWow") p.delayWow = v;
    else if (field == "chorusMix") p.chorusMix = v;
    else if (field == "chorusRate") p.chorusRate = v;
    else if (field == "chorusDepthMs") p.chorusDepthMs = v;
    else if (field == "chorusMs") p.chorusMs = v;
    else if (field == "chorusFeedback") p.chorusFeedback = v;
    else if (field == "phaserMix") p.phaserMix = v;
    else if (field == "phaserRate") p.phaserRate = v;
    else if (field == "phaserDepth") p.phaserDepth = v;
    else if (field == "phaserFeedback") p.phaserFeedback = v;
    else if (field == "fxOrder") p.fxOrder = static_cast<int>(v);
    else if (field == "reverbMix") p.reverbMix = v;
    else if (field == "reverbSize") p.reverbSize = v;
    else if (field == "reverbTone") p.reverbTone = v;
    else if (field == "reverbPreMs") p.reverbPreMs = v;
    else if (field == "reverbSpread") p.reverbSpread = v;
    else return false;
    return true;
  }

  // The plane's shape, which layer A has in its tone and layer B of its own.
  static bool setPlaneShape(PlaneShapeTone& p, std::string_view field, double v) {
    if (field == "planeMirror") p.planeMirror = static_cast<int>(v);
    else if (field == "planeRadius") p.planeRadius = v;
    else if (field == "planeLimit") p.planeLimit = static_cast<int>(v);
    else if (field == "planeScaleX") p.planeScaleX = v;
    else if (field == "planeScaleY") p.planeScaleY = v;
    else if (field == "planeShear") p.planeShear = v;
    else if (field == "planeTwist") p.planeTwist = v;
    else if (field == "planeSnap") p.planeSnap = v;
    else return false;
    return true;
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
    else if (field == "warp") t.warp = v;
    else if (field == "warpAt") t.warpAt = v;
    else if (field == "scan") t.scan = v;
    else if (field == "scanHold") t.scanHold = v;
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

  /* The page's `Math.max(0, Math.min(1, tone.scan || 0)) * Math.max(0,
     Math.min(1, tone.scanHold)) * SCAN_MOST`: a NaN depth is nought, a NaN
     hold carries through and is not more than nought, so plays no Scan. */
  static double scanWeight(const LayerSettings& t) {
    const double depth = std::isnan(t.scan) ? 0 : t.scan;
    return jsMax(0.0, jsMin(1.0, depth)) * jsMax(0.0, jsMin(1.0, t.scanHold)) * kScanMost;
  }

  /* Scan's tick: kScanRate a second of this core's samples, a sixtieth apart
     however the blocks fall. At each a layer goes from the table it was
     fading to, to the latest it has been given; `scanX` is how far through the
     tick this sample is. The page's `scanAdvance`. */
  void scanAdvance() {
    scanClock_ += 1;
    if (scanClock_ >= scanPer_) {
      scanClock_ -= scanPer_;
      vxA_.scanPrev = vxA_.scanNext; vxA_.scanNext = a_.scanTable;
      vxB_.scanPrev = vxB_.scanNext; vxB_.scanNext = b_.scanTable;
      scanHead_[0] = scanHeadOf(voices_, phaseL_);
      scanHead_[1] = scanHeadOf(voicesB_, NAN);
    }
    vxA_.scanX = vxB_.scanX = scanClock_ / scanPer_;
  }

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
    const PlanePushes a { modOr0(slot::Radius), modOr0(slot::Twist), modOr0(slot::Echo), modOr0(slot::EchoTime), 0,
                          modOr0(slot::Phaser), modOr0(slot::DelayTone), modOr0(slot::Reverb),
                          modOr0(slot::ReverbSize), modOr0(slot::ReverbTone) };
    const PlanePushes b { modBOr0(slot::Radius), modBOr0(slot::Twist), modBOr0(slot::Echo), modBOr0(slot::EchoTime),
                          modBOr0(slot::Turn), modBOr0(slot::Phaser), modBOr0(slot::DelayTone), modBOr0(slot::Reverb),
                          modBOr0(slot::ReverbSize), modBOr0(slot::ReverbTone) };
    plane_.tick(a_, a, dt, &b_, b);
  }

  // --- S10: the governor ------------------------------------------------------

  double voiceCost(const LayerSettings& t, int n, int factor, bool fmRouted, bool syncRouted, bool shapeRouted) const {
    double c = 2.5;
    if (t.noise) c += 3;
    else {
      const bool fm = t.fmIndex > 0 || t.warp != 0 || fmRouted, sync = t.syncRatio != 1 || syncRouted;
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

  // Releasing before held, inner voices before the outline, and the oldest of a rank.
  /* The pools a block governs: one or both layers' voices. A fixed pair and a
     count rather than a list made each step, which allocated on the audio
     thread twice a step with two hands (G8). */
  struct Pools {
    std::array<std::vector<Voice>*, 2> at {};
    std::size_t n = 0;
    std::vector<Voice>* const* begin() const { return at.data(); }
    std::vector<Voice>* const* end() const { return at.data() + n; }
  };
  Voice* victim(const Pools& pools) {
    Voice* best = nullptr;
    double bestRank = INFINITY;
    for (auto* pool : pools) {
      for (auto& voice : *pool) {
        if (cutting(voice)) continue;
        const double rank = (!voice.held ? 0 : voice.inner ? 1 : 2) * 1e9 + voice.born;
        if (rank < bestRank) { bestRank = rank; best = &voice; }
      }
    }
    return best;
  }

  void govern(bool fmRouted, bool syncRouted, bool shapeRouted, bool planeOn) {
    const bool poly = a_.voices.has_value(), layered = b_.voices.has_value();
    Pools pools;
    if (poly) pools.at[pools.n++] = &voices_;
    if (layered) pools.at[pools.n++] = &voicesB_;
    int countA = poly ? liveIn(voices_) : 2;
    int countB = layered ? liveIn(voicesB_) : 0;
    const int askedA = unisonAsked(a_), askedB = unisonAsked(b_), askedF = a_.shapeOS == 4 ? 4 : 2;
    // A pass through the plane for each layer's pair; the heard pair's own
    // passes went with it in P4 (the page's govern).
    const int passes = 1 + (layered ? 1 : 0);
    const double planeCost = plane_.factor() == 1 ? 3.3 : plane_.factor() == 2 ? 30 : plane_.factor() == 4 ? 60 : 0;
    const double fixed = !planeOn ? 0
      : passes * ((plane_.nonlinearOn() ? planeCost : 0) + (plane_.timeOn() ? 5.3 : 0));
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

  // --- the score's voices -----------------------------------------------------

  struct ScoreVoice { double hz = 0, vel = 0, env = 0, phase = 0; bool attacking = false; long age = 0; };

  double scoreVoice(ScoreVoice& v) const {
    if (v.attacking) {
      v.env += scoreAttack_;
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
  LayerBSettings b_;
  std::vector<float> genMod_, genModB_;
  std::vector<Route> routes_;
  Registration barsA_, barsB_;

  double phaseL_ = 0, phaseR_ = 0;
  const float* inBuf_ = nullptr;
  int inLen_ = 0;
  struct { bool low = true; long since = 0, period = 0; } clock_;
  bool gated_ = false;
  Envelope env_, fenv_;
  Envelope menv_;          // the Envelope card's own, one for the generator
  bool menvHeld_ = false;  // and whether it is open, so a gate is sent only on a change
  void menvGate(bool open) {
    if (open == menvHeld_) return;
    menvHeld_ = open;
    menv_.gate(open, 1);
  }
  bool freqStarted_ = false;
  double freqNow_ = 0;
  std::array<double, 2> glideFrom_ {};  // each layer's last note's pitch, for Poly's glide out of silence
  double bendNow_ = 0, vibNow_ = 0, vibPhase_ = 0;  // the bend and the vibrato as they glide, and its cycle
  VcfState vcfL_, vcfR_;
  std::vector<Voice> voices_, voicesB_;
  Plane plane_;
  VoiceContext ctx_;
  Quantiser qA_;
  double lastHz_ = 0;
  double scoreAttack_;
  std::array<ScoreVoice, 4> score_;
  double scoreFade_ = 0;
  int scoreStruck_ = 0;
  VoiceFx vxA_, vxB_;
  double scanPer_ = rate_ / kScanRate, scanClock_ = 0;
  std::array<double, 2> scanHead_ { { -1, -1 } };
  double askedCostA_ = -1, askedCostB_ = -1, askedFixed_ = -1;
  int govFactor_ = 4;
  Budget budget_;
  Shaper shapeL_, shapeR_;
  Crush crushL_, crushR_;
  Osc oscL_, oscR_;
  NoiseState noiseL_, noiseR_;
};

}  // namespace scope
