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
// its role in the picture - x, y, both alone, or an inner voice (u).
struct NoteWant {
  int note = 60;
  double freq = 261.63, velocity = 1;
  std::string role = "u";
};

// Left and right, which is picture X and picture Y: a voice is drawn where P4
// put it, and since 16 Nov heard apart from where it is drawn (`sound`'s
// heard pair, `c.heard`). The outer notes lean to their sides, full on their own and
// half on the other; an inner voice is on both at an outer note's power. The
// page's ROLES says why leaning and not splitting.
constexpr double kPolyLean = 0.5;
inline std::array<double, 2> roleGains(const std::string& role) {
  const double inner = std::sqrt((1 + kPolyLean * kPolyLean) / 2);  // POLY_INNER
  if (role == "x") return { 1, kPolyLean };
  if (role == "y") return { kPolyLean, 1 };
  if (role == "xy") return { 1, 1 };
  // A against B: hard, so the one figure the two layers make is not sheared.
  if (role == "xonly") return { 1, 0 };
  if (role == "yonly") return { 0, 1 };
  return { inner, inner };
}
inline bool innerRole(const std::string& role) {
  return role != "x" && role != "y" && role != "xy" && role != "xonly" && role != "yonly";
}

constexpr int kPolyTails = 8;
// The quarter turn (polyRound, P8g): a voice on both channels alike - alone,
// or inner - heard on the left a quarter of its period late, from a ring of
// its own output, so the right leads as a dyad's does (15 Nov; `sound` says
// why). A delay rather than a second phase per voice, which would compute
// every voice twice; what it costs is a quarter period's lag on the left.
constexpr int kRoundRing = 4096;
inline bool roundsRole(const std::string& role) { return role == "xy" || role == "u" || innerRole(role); }

struct Voice {
  int note = 0;
  // `span` is the phase unwrapped, since the voice was born: what a note
  // joining a held chord scales to start in step with it (the page says why).
  // `hz` is where its glide has got to on the way to `freq` (Glide in Poly).
  double phase = 0, span = 0, freq = 0, hz = 0;
  bool held = true, wanted = false, gone = false, inner = false, rounds = false;
  int born = 0, fade = 0;
  /* The quarter its left is heard at once it has fallen silent, let go
     (16 Nov): held where it was, so a voice's last quarter-period heard from
     the pool and from the tails it moves to at a block's end is one value. */
  double stillQuarter = -1;
  Envelope env, fenv;
  std::array<double, 2> gains {}, targets {};
  std::vector<double> ring;  // the quarter turn's, made the first time it turns
  int at = 0;
  double turn = 0;
  Quantiser q;
  std::optional<NoiseState> nz;
  Osc osc;
  std::optional<Shaper> shp;
  Crush cr;
  VcfState vcf;
  /* Painting (paint.h): the voice's own Scan tables, read off the ring at its
     own pitch - the latest, and the two it fades between, moved on at
     Scan's tick as the layer's are. `painted` once the painter has a brush
     for it; until then, and always on the trace, it plays the layer's. */
  bool painted = false;
  const CycleTables* paintTable = nullptr;
  const CycleTables* paintPrev = nullptr;
  const CycleTables* paintNext = nullptr;
  Voice(double rate, const LayerTone& tone) : env(rate, tone.env), fenv(rate, tone.fenv) {}
};

/* A voice's ring let go with it (16 Nov), still to be heard on the left:
   what is heard of a voice is its left up to a quarter of its period late, so
   a voice dropped - its release over, or the governor's fade done - took that
   much of its sound from the left ear in one sample, and on a low note cut by
   the governor most of its level. And the moment a released voice is dropped
   is the end of the block it fell silent in, so where a host's blocks fell
   decided where its left ear stopped. Its ring is heard out here instead, the
   last of it, apart from the voices: the pools, the governor and the picture
   are as they were (the drawn left reads the same ring, and drops it as it
   always did). One list a layer, room made with the generator, kept in the
   order the voices were born: `sound` sums the tails among the voices in that
   order, so a voice adds the same value at the same place in the sum whether
   it is still in the pool or a tail - otherwise the sum's rounding moved with
   where the host's blocks fell, a bit at a time, and the reverb carried it. */
struct RingTail {
  std::vector<double> ring;
  int at = 0, born = 0, left = 0;
  double quarter = 0, now = 0;
};
struct RingTails {
  std::vector<RingTail> list;
  RingTails() { list.reserve(64); }
};

// The ring read `back` samples behind `at`, between samples: the quarter turn's read.
inline double ringLate(const std::vector<double>& ring, int at, double back) {
  back = std::fmin(kRoundRing - 2, back);
  const int whole = static_cast<int>(std::floor(back));
  const double part = back - whole;
  const int i0 = (at - whole + kRoundRing) % kRoundRing, i1 = (i0 - 1 + kRoundRing) % kRoundRing;
  return ring[static_cast<std::size_t>(i0)] + (ring[static_cast<std::size_t>(i1)] - ring[static_cast<std::size_t>(i0)]) * part;
}

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
  std::array<double, 2> mix {};  // left and right, as drawn
  // What is heard (16 Nov): every voice in both ears at the Width, whatever
  // else is held. `sound` says how; filled only when it is asked a width.
  std::array<double, 2> heard {};
  /* What retired voices leave: a quarter turn's ring and a shaper each, for
     the next voices born to take rather than make. A voice made both the
     first time it turned or was shaped, 33 kilobytes, so every note struck -
     and every step of an arpeggio - allocated on the audio thread (G8). Room
     for as many as are kept is made here, with the generator; one retired
     past that is let go. */
  static constexpr std::size_t kSpares = 64;
  std::vector<std::vector<double>> spareRings;
  std::vector<Shaper> spareShapers;

  explicit VoiceContext(double r)
      : rate(r), qHold(std::max(1, static_cast<int>(jsRound(0.025 * r)))),
        cutSamples(std::max(1, static_cast<int>(jsRound(r * 0.01)))) {
    spareRings.reserve(kSpares);
    spareShapers.reserve(kSpares);
  }
};

/* A voice's ring handed to the tails, where it is heard out on the left:
   as long as the Width puts its left behind, and two samples. Where there is
   no room, or no ring, it goes as it did. */
inline std::size_t tailRing(Voice& v, RingTails* tails, double quarter) {
  if (tails == nullptr || v.ring.empty() || tails->list.size() >= tails->list.capacity()) return std::numeric_limits<std::size_t>::max();
  RingTail t;
  t.ring = std::move(v.ring);
  v.ring.clear();
  t.at = v.at;
  t.born = v.born;
  t.quarter = quarter;
  // Long enough for its left at any Width, a quarter at most.
  t.left = 2 + static_cast<int>(std::ceil(std::fmin(kRoundRing - 2, quarter)));
  auto& list = tails->list;
  std::size_t at = 0;
  while (at < list.size() && list[at].born < t.born) at++;
  list.insert(list.begin() + static_cast<long>(at), std::move(t));
  return at;
}
// The quarter a voice let go is heard at: held once it fell silent, or its own now.
inline double quarterOf(const Voice& v, double rate) {
  if (v.stillQuarter >= 0) return v.stillQuarter;
  const double hz = std::fabs(v.hz);
  return hz > 0 ? rate / (4 * hz) : 0;
}

// A voice let go: what it made is kept for the next voice born.
inline void retireVoice(Voice& v, VoiceContext& c) {
  if (v.ring.capacity() > 0 && c.spareRings.size() < c.spareRings.capacity()) c.spareRings.push_back(std::move(v.ring));
  if (v.shp && c.spareShapers.size() < c.spareShapers.capacity()) {
    c.spareShapers.push_back(std::move(*v.shp));
    v.shp.reset();
  }
}

// The voices against what the keyboard now asks of this layer: notes kept
// where they are held, new ones born at nought - or, joining notes already
// held, in step with them (P6, harmony as geometry) - released ones let go into
// their tails, and the oldest tails cut past `kPolyTails`. No list at all is
// the layer switched off, and empties it.
inline void reconcileVoices(std::vector<Voice>& voices, const std::vector<NoteWant>* list, const LayerTone& tone,
                            double& glideFrom,
                            VoiceContext& c) {
  c.chordMoved = true;
  if (list == nullptr) { voices.clear(); return; }
  // Copied before any birth: a voice born below may move the vector. The
  // lowest held voice is the reference only where held voices are out of step
  // (a key retuned under it); in step, any would do. See the page's comment.
  double refSpan = 0, refFreq = 0;
  for (const auto& v : voices) {
    if (v.held && !v.gone && v.freq > 0 && (refFreq == 0 || v.freq < refFreq)) { refFreq = v.freq; refSpan = v.span; }
  }
  for (auto& v : voices) v.wanted = false;
  for (const auto& want : *list) {
    const auto gains = roleGains(want.role);
    Voice* voice = nullptr;
    for (auto& v : voices) if (v.held && v.note == want.note) { voice = &v; break; }
    if (voice == nullptr) {
      // Glide in Poly: the newest voice, held or in its tail, is where the
      // last note had got to, and a new one slides from there (the page says
      // why). Read before the birth, which may move the vector.
      double from = 0;
      int newest = -1;
      for (const auto& v : voices) if (v.born > newest) { newest = v.born; from = v.hz; }
      // With none left - each is dropped once its release is over - the
      // layer's last note's pitch, as Dyad's and Mono's glide remembers it.
      if (newest < 0) from = glideFrom;
      glideFrom = want.freq;
      voices.emplace_back(c.rate, tone);
      voice = &voices.back();
      voice->note = want.note;
      voice->span = refFreq > 0 ? refSpan * (want.freq / refFreq) : 0;
      voice->phase = voice->span - kPhaseWrap * std::floor(voice->span / kPhaseWrap);
      voice->gains = gains; voice->targets = gains;
      voice->born = ++c.births;
      voice->hz = from > 0 ? from : want.freq;
      voice->env.reset(0);
      voice->env.gate(true, want.velocity);
      voice->fenv.reset(0);
      voice->fenv.gate(true, want.velocity);
    }
    voice->wanted = true;
    voice->freq = want.freq;
    voice->inner = innerRole(want.role);  // the budget cuts an inner voice first
    voice->targets = gains;
    voice->rounds = roundsRole(want.role);
  }
  for (auto& v : voices) {
    if (v.held && !v.wanted) { v.held = false; v.env.gate(false, 0); v.fenv.gate(false, 0); }
  }
  int tails = 0;
  for (const auto& v : voices) if (!v.held) tails++;
  for (std::size_t v = 0; v < voices.size() && tails > kPolyTails; v++) {
    if (!voices[v].held) { retireVoice(voices[v], c); voices.erase(voices.begin() + static_cast<long>(v)); v--; tails--; }
  }
}

// One sample of a layer: every voice summed into the picture's pair, `c.mix`,
// and, given a `width` of nought to one, into the heard pair, `c.heard`.
//
// The heard pair (16 Nov, the owner's, after web/docs/both-ears.md): each
// voice in both ears at full, its left `width` of a quarter of its own period
// behind its right, read from the same ring the quarter turn reads. So at
// nought a voice is the same in both ears, at one it is the quarter turn - a
// lone note as it was drawn and heard before - and between, a turn of the
// note's own cycle rather than a fixed delay, which would leave a low note
// nearly mono and comb-filter a high one. None of it depends on what else is
// held: the roles' lean (P4) and the turn's glide are the picture's, and a
// note no longer moves between the ears as others join it. The picture is
// `c.mix` as it was, to the bit (core/tests/pieces/ears.py).
//
// `round` is the quarter turn (polyRound until 16 Nov): the generator always
// asks it now, and it stays a switch here for the functions' recordings.
inline void sound(std::vector<Voice>& voices, const LayerTone& tone, const WaveTables& bars, double amount,
                  double bend, double duck, double dt, double roleGlide, const VoiceFx& vx, VoiceContext& c,
                  bool round = false, double glide = 1, double width = -1, RingTails* tails = nullptr) {
  c.mix = { 0, 0 };
  c.heard = { 0, 0 };
  const bool hearing = width >= 0;
  // The rings of voices let go, heard out on the left (RingTail says why),
  // summed among the voices in the order they were born.
  const bool tailing = hearing && tails != nullptr;
  std::size_t nextTail = 0;
  if (tailing) {
    for (auto& t : tails->list) {
      t.ring[static_cast<std::size_t>(t.at)] = 0;
      t.now = ringLate(t.ring, t.at, width * t.quarter);
      t.at = (t.at + 1) % kRoundRing;
      t.left--;
    }
  }
  const auto tailsBefore = [&](int born) {
    if (!tailing) return;
    while (nextTail < tails->list.size() && tails->list[nextTail].born < born) c.heard[0] += tails->list[nextTail++].now;
  };
  for (auto& voice : voices) {
    if (voice.gone) continue;
    if (glide >= 1) voice.hz = voice.freq;
    else voice.hz += (voice.freq - voice.hz) * glide;
    const double f = c.qMask ? quantise(voice.q, voice.hz * bend, c.qMask, c.qHold, c.qGlide) : voice.hz * bend;
    voice.phase += kTwoPi * f * dt;
    voice.span += kTwoPi * f * dt;
    if (voice.phase >= kPhaseWrap) voice.phase -= kPhaseWrap;
    if (voice.phase < 0) voice.phase += kPhaseWrap;
    double wave;
    if (tone.noise) {
      if (!voice.nz) voice.nz.emplace(*c.random);
      wave = noiseStep(*voice.nz, tone.noiseShape, voice.phase, std::fabs(f) / c.rate, *c.random);
    } else if (vx.on && voice.painted && vx.scanW > 0) {
      // The oscillator mixes Scan in itself, so a painted voice hands it a copy with its own tables.
      VoiceFx own = vx;
      own.scanPrev = voice.paintPrev; own.scanNext = voice.paintNext;
      wave = oscStep(voice.osc, voice.phase, 0, f, tone, bars, amount, own, c.rate);
    } else if (vx.on) {
      wave = oscStep(voice.osc, voice.phase, 0, f, tone, bars, amount, vx, c.rate);
    } else {
      wave = waveAt(tone.shape, voice.phase, std::fabs(f) / c.rate, bars, amount);
    }
    double w = wave;
    // Scan, where the oscillator is off: under it, `oscStep` has mixed it in.
    // A painted voice reads its own ring's tables in place of the layer's.
    if (vx.scanW > 0 && !vx.on && !tone.noise) {
      w = voice.painted ? scanMix(w, voice.paintPrev, voice.paintNext, voice.phase, std::fabs(f) / c.rate, vx.scanX, vx.scanW)
                        : scanMix(w, vx.scanPrev, vx.scanNext, voice.phase, std::fabs(f) / c.rate, vx.scanX, vx.scanW);
    }
    if (vx.shapeRun) {
      if (!voice.shp || voice.shp->factor() != c.shapeFactor) {
        const auto& taps = c.shapeFactor == 4 ? c.taps4 : c.taps2;
        if (!voice.shp && !c.spareShapers.empty()) { voice.shp.emplace(std::move(c.spareShapers.back())); c.spareShapers.pop_back(); }
        if (voice.shp) voice.shp->reset(c.shapeFactor, taps);
        else voice.shp.emplace(c.shapeFactor, taps);
      } else if (vx.shapeFresh) {
        voice.shp->clear();
      }
      w = switchBlend(w, voice.shp->step(w, c.shaping), vx.shapeW);
    }
    if (vx.crushing) w = crushStep(voice.cr, w, tone, vx, c.rate);
    if (vx.filtering) w = svfStep(voice.vcf, w, vcfCoef(voice.vcf, tone, f, voice.fenv.step(), vx.vcfPush, vx.cut, c.rate), vx.vcfK, tone.vcfType);
    double a = vx.level * duck * voice.env.step() * w;
    bool cut = false;
    if (voice.fade > 0) {
      a *= 0.5 - 0.5 * std::cos(kPi * voice.fade / c.cutSamples);
      if (--voice.fade == 0) { voice.gone = true; cut = true; }
    }
    auto& g = voice.gains;
    const auto& t = voice.targets;
    g[0] += (t[0] - g[0]) * roleGlide;
    g[1] += (t[1] - g[1]) * roleGlide;
    const double turnTo = round && voice.rounds ? 1 : 0;
    voice.turn += (turnTo - voice.turn) * roleGlide;
    /* The quarter turn delays the LEFT channel, so the right leads by a
       quarter of the period, as a dyad's lone note's right channel leads at
       its default Phase of a quarter turn. Until 15 Nov it delayed the right,
       which put the right a quarter LATE: the same circle traced the other way
       round, so a note alone in Poly drew the mirror of the one in Dyad or
       Mono, and Scan and the picture, reading the figure, made a different
       sound of it (the owner heard it: after-stage-5.md, Owner's list). A
       right channel three quarters late would lead by a quarter on a sine,
       but the drawbars' 16' runs the phase over two cycles, so it would have
       to be seven quarters late, and that is a silent right ear for a low
       note's first fifteen milliseconds; a quarter's lag on the left is the
       dyad exactly, whatever the wave, the whole voice a quarter of its
       period later on the left. Written whenever the switch is on, and glided
       over the mix's length (the page says why). */
    double left = a;
    if (round || hearing || voice.turn > 1e-9) {
      if (voice.ring.empty()) {
        if (!c.spareRings.empty()) { voice.ring = std::move(c.spareRings.back()); c.spareRings.pop_back(); }
        voice.ring.assign(kRoundRing, 0.0);
        voice.at = 0;
      }
      voice.ring[static_cast<std::size_t>(voice.at)] = a;
      const auto lateBy = [&](double back) { return ringLate(voice.ring, voice.at, back); };
      const double quarter = f > 0 ? c.rate / (4 * std::fabs(f)) : 0;
      const double late = lateBy(quarter);
      // At one, with the pitch its own, the drawn quarter's read: a lone note heard as it was, to the bit.
      if (hearing) {
        if (!voice.held && voice.env.stage() == Envelope::Stage::Idle && voice.stillQuarter < 0) voice.stillQuarter = quarter;
        const double heardQuarter = voice.stillQuarter >= 0 ? voice.stillQuarter : quarter;
        tailsBefore(voice.born);
        c.heard[0] += lateBy(width * heardQuarter);
        c.heard[1] += a;
      }
      voice.at = (voice.at + 1) % kRoundRing;
      const double t = voice.turn, u = 1 - t;
      if (t > 0) left = (u * a + t * late) / std::sqrt(u * u + t * t);
    } else if (voice.turn != 0) {
      voice.turn = 0;
    }
    c.mix[0] += left * g[0]; c.mix[1] += a * g[1];
    // The governor's fade done: the ring heard out from the next sample, and not in this one's sum again.
    if (cut && tailing) {
      const std::size_t at = tailRing(voice, tails, f > 0 ? c.rate / (4 * std::fabs(f)) : 0);
      if (at != std::numeric_limits<std::size_t>::max() && at <= nextTail) nextTail++;
    }
  }
  tailsBefore(std::numeric_limits<int>::max());
  // Tails heard out: their rings back to the spares, the rest kept in order.
  if (tailing) {
    auto& list = tails->list;
    std::size_t keep = 0;
    for (std::size_t k = 0; k < list.size(); k++) {
      if (list[k].left > 0) { if (keep != k) list[keep] = std::move(list[k]); keep++; continue; }
      if (c.spareRings.size() < c.spareRings.capacity()) c.spareRings.push_back(std::move(list[k].ring));
    }
    while (list.size() > keep) list.pop_back();
  }
}

}  // namespace scope
