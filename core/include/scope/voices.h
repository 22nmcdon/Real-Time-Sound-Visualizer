// The chord's voices, ported from inside `makeGeneratorCore` in
// web/scope.html: the quantiser (`nearestAllowed`, `quantise`), the voices
// and their release tails (`reconcileVoices`), and the sum of them a sample
// at a time (`sound`), each voice through its oscillator or noise, its
// shaping, crush and filter, its envelope, the governor's cut, and its gains
// gliding between the picture's roles.
//
// The page builds a voice's noise, oscillator, shaper, crush, filter and
// quantiser the first time each is used. Most of that is only economy and
// they are built with the voice here; the noise is built when first used, as
// there, because building it draws from the random sequence, and drawing at
// the note's birth instead would move every later draw. The shaper too, as
// there, since it is rebuilt when the oversampling factor has changed.

#pragma once

#include <array>
#include <cmath>
#include <limits>
#include <memory>
#include <optional>
#include <string>
#include <vector>

#include "scope/envelope.h"
#include "scope/noise.h"
#include "scope/osc.h"
#include "scope/voice.h"
#include "scope/wave.h"

namespace scope {

// The core's own one-pole: 63 per cent of the way in `ms`. Not the
// envelope's, which is divided into the time constants its stage needs.
inline double poleFor(double ms, double rate) {
  const double samples = std::fmax(1.0, ms * rate / 1000);
  return 1 - std::exp(-1 / samples);
}

// The quantiser: in MIDI note numbers, a step taken only past a tenth of a
// semitone beyond half-way and never sooner than `hold` samples after the
// last, gliding by `glide` towards the note it has chosen.
constexpr double kQHysteresis = 0.2;
constexpr int kNoNote = std::numeric_limits<int>::min();

struct Quantiser {
  int note = kNoNote;
  double at = 0;
  int held = 0;
};

inline int nearestAllowed(double m, int mask) {
  int best = kNoNote;
  double gap = std::numeric_limits<double>::infinity();
  const int from = static_cast<int>(std::floor(m)) - 6;
  for (int n = from; n <= from + 13; n++) {
    if (!(mask & (1 << (((n % 12) + 12) % 12)))) continue;
    const double d = std::fabs(m - n);
    if (d < gap - 1e-9) { gap = d; best = n; }
  }
  return best;
}

inline double quantise(Quantiser& q, double hz, int mask, int hold, double glide) {
  if (!(hz > 0)) return hz;
  const double m = 69 + 12 * std::log2(hz / 440);
  const int want = nearestAllowed(m, mask);
  if (want == kNoNote) return hz;
  if (q.note == kNoNote) { q.note = want; q.at = want; q.held = 0; }
  else if (want != q.note && q.held >= hold && std::fabs(m - want) + kQHysteresis < std::fabs(m - q.note)) {
    q.note = want; q.held = 0;
  }
  q.held++;
  q.at += (q.note - q.at) * glide;
  return 440 * std::pow(2.0, (q.at - 69) / 12);
}

// A layer's tone as its voices read it: the oscillator and the voice chain,
// the level, the two envelopes' times, and the quantiser's key.
struct LayerTone : VoiceTone {
  bool noise = false;
  Noise noiseShape = Noise::White;
  double amp = 0.5;
  EnvelopeTone env;
  EnvelopeTone fenv { 5, 200, 1, 200 };
};

// What the keyboard asks a layer for: a note, its pitch and strength, and
// its role in the picture - x, y, both, or heard only.
struct NoteWant {
  int note = 60;
  double freq = 261.63, velocity = 1;
  std::string role = "u";
};

// Picture X, picture Y, heard left, heard right.
inline std::array<double, 4> roleGains(const std::string& role) {
  if (role == "x") return { 1, 0, 1, 1 };
  if (role == "y") return { 0, 1, 1, 1 };
  if (role == "xy") return { 1, 1, 1, 1 };
  return { 0, 0, 1, 1 };
}

constexpr int kPolyTails = 8;

struct Voice {
  int note = 0;
  double phase = 0, freq = 0;
  bool held = true, wanted = false, gone = false;
  int born = 0, fade = 0;
  Envelope env, fenv;
  std::array<double, 4> gains {}, targets {};
  Quantiser q;
  std::optional<NoiseState> nz;
  Osc osc;
  std::optional<Shaper> shp;
  Crush cr;
  VcfState vcf;
  Voice(double rate, const LayerTone& tone) : env(rate, tone.env), fenv(rate, tone.fenv) {}
};

// What `reconcileVoices` and `sound` share with the rest of the core.
struct VoiceContext {
  double rate = 48000;
  int births = 0;
  bool chordMoved = true;
  int qMask = 0;            // the key, as a mask of pitch classes; nought is off
  int qHold = 1;
  double qGlide = 1;
  int cutSamples = 1;
  Shaping shaping;
  int shapeFactor = 2;
  std::vector<double> taps2 = lowpassTaps(2), taps4 = lowpassTaps(4);
  Random* random = nullptr;
  std::array<double, 4> mix {};

  explicit VoiceContext(double r)
      : rate(r), qHold(std::max(1, static_cast<int>(jsRound(0.025 * r)))),
        cutSamples(std::max(1, static_cast<int>(jsRound(r * 0.01)))) {}
};

// The voices against what the keyboard now asks of this layer: notes kept
// where they are held, new ones born at nought, released ones let go into
// their tails, and the oldest tails cut past `kPolyTails`. No list at all is
// the layer switched off, and empties it.
inline void reconcileVoices(std::vector<Voice>& voices, const std::vector<NoteWant>* list, const LayerTone& tone,
                            VoiceContext& c) {
  c.chordMoved = true;
  if (list == nullptr) { voices.clear(); return; }
  for (auto& v : voices) v.wanted = false;
  for (const auto& want : *list) {
    const auto gains = roleGains(want.role);
    Voice* voice = nullptr;
    for (auto& v : voices) if (v.held && v.note == want.note) { voice = &v; break; }
    if (voice == nullptr) {
      voices.emplace_back(c.rate, tone);
      voice = &voices.back();
      voice->note = want.note;
      voice->gains = gains; voice->targets = gains;
      voice->born = ++c.births;
      voice->env.reset(0);
      voice->env.gate(true, want.velocity);
      voice->fenv.reset(0);
      voice->fenv.gate(true, want.velocity);
    }
    voice->wanted = true;
    voice->freq = want.freq;
    voice->targets = gains;
  }
  for (auto& v : voices) {
    if (v.held && !v.wanted) { v.held = false; v.env.gate(false, 0); v.fenv.gate(false, 0); }
  }
  int tails = 0;
  for (const auto& v : voices) if (!v.held) tails++;
  for (std::size_t v = 0; v < voices.size() && tails > kPolyTails; v++) {
    if (!voices[v].held) { voices.erase(voices.begin() + static_cast<long>(v)); v--; tails--; }
  }
}

// One sample of a layer: every voice summed into the picture's pair and the
// heard pair, `c.mix`.
inline void sound(std::vector<Voice>& voices, const LayerTone& tone, const WaveTables& bars, double amount,
                  double bend, double duck, double dt, double roleGlide, const VoiceFx& vx, VoiceContext& c) {
  c.mix = { 0, 0, 0, 0 };
  for (auto& voice : voices) {
    if (voice.gone) continue;
    const double f = c.qMask ? quantise(voice.q, voice.freq * bend, c.qMask, c.qHold, c.qGlide) : voice.freq * bend;
    voice.phase += kTwoPi * f * dt;
    if (voice.phase >= kPhaseWrap) voice.phase -= kPhaseWrap;
    if (voice.phase < 0) voice.phase += kPhaseWrap;
    double wave;
    if (tone.noise) {
      if (!voice.nz) voice.nz.emplace(*c.random);
      wave = noiseStep(*voice.nz, tone.noiseShape, voice.phase, std::fabs(f) / c.rate, *c.random);
    } else if (vx.on) {
      wave = oscStep(voice.osc, voice.phase, 0, f, tone, bars, amount, vx, c.rate);
    } else {
      wave = waveAt(tone.shape, voice.phase, std::fabs(f) / c.rate, bars, amount);
    }
    double w = wave;
    if (vx.shaping) {
      if (!voice.shp || voice.shp->factor() != c.shapeFactor) voice.shp.emplace(c.shapeFactor, c.shapeFactor == 4 ? c.taps4 : c.taps2);
      w = voice.shp->step(w, c.shaping);
    }
    if (vx.crushing) w = crushStep(voice.cr, w, tone, vx, c.rate);
    if (vx.filtering) w = svfStep(voice.vcf, w, vcfCoef(voice.vcf, tone, f, voice.fenv.step(), vx.vcfPush, c.rate), vx.vcfK, tone.vcfType);
    double a = tone.amp * duck * voice.env.step() * w;
    if (voice.fade > 0) {
      a *= 0.5 - 0.5 * std::cos(kPi * voice.fade / c.cutSamples);
      if (--voice.fade == 0) voice.gone = true;
    }
    auto& g = voice.gains;
    const auto& t = voice.targets;
    g[0] += (t[0] - g[0]) * roleGlide;
    g[1] += (t[1] - g[1]) * roleGlide;
    g[2] += (t[2] - g[2]) * roleGlide;
    g[3] += (t[3] - g[3]) * roleGlide;
    c.mix[0] += a * g[0]; c.mix[1] += a * g[1]; c.mix[2] += a * g[2]; c.mix[3] += a * g[3];
  }
}

}  // namespace scope
