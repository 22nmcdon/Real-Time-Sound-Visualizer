// The hearing (Stage J1), ported from web/scope.html: the sound as sources
// beyond its level - its pitch, where its energy sits, how loud each of four
// bands is, how alike its two channels are, how fast its spectrum is changing,
// and an onset, a new note or hit as an event. `hearingStep`, `onsetStep`,
// `fft`, `estimatePeriod` and `correlation`, and the sources registered from
// `HEARING_SOURCES` and `hear.onset`.
//
// What differs from the page, and why, so nobody goes looking:
//
// - What it hears. The page reads a window of 4096 samples from whatever is
//   on the screen - the trigger's lane for most of it, the X-Y pair for the
//   width - and its owner says whether that is the generator. The core reads
//   the lanes its owner hands it; the plugin hands it the last 4096 frames of
//   the picture, which is always the generator, so in the plugin every
//   hearing source is the picture's - a loop, with the picture's reach.
// - The pitch's held key is the lowest note the hands hold, worked out by the
//   caller from the keyboard, as the page asks `midiPitchHz`.
// - The cost the page measures for its readout is the page's.
// - A window whose length is not a power of two is not heard at all. The
//   page's windows always are one; on any other length its FFT reads and
//   writes past the end of its arrays, which JavaScript forgives with NaN and
//   C++ would not.

#pragma once

#include <array>
#include <cmath>
#include <cstddef>
#include <optional>
#include <string>
#include <vector>

#include "scope/level.h"
#include "scope/matrix.h"
#include "scope/setup.h"

namespace scope {

constexpr std::size_t kHearN = 4096;
constexpr double kHearSlew = 4;        // the most a value moves in a second, in its own units
constexpr double kHearFloor = 0.001;   // RMS: -60 dBFS
constexpr double kPitchRef = 261.6256; // C4, the pitch source's nought
constexpr std::size_t kPitchMaxWindow = 16384;
constexpr double kPitchDip = 0.1, kPitchTrust = 0.35;
constexpr double kOnsetOn = 0.3, kOnsetOff = 0.12, kOnsetGap = 80;
constexpr double kPhotoReach = 0.5;    // PHOTO_REACH: the most of a span the picture may move a control

// BANDS: the band split's crossovers, a top of nought for no top.
struct HearingBand { double from, to; };
constexpr std::array<HearingBand, 4> kHearingBands { { { 0, 120 }, { 120, 800 }, { 800, 4000 }, { 4000, 0 } } };

// fft: iterative radix-2, in place.
inline void fft(double* re, double* im, std::size_t n) {
  for (std::size_t i = 1, j = 0; i < n; i++) {
    std::size_t bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) { std::swap(re[i], re[j]); std::swap(im[i], im[j]); }
  }
  for (std::size_t len = 2; len <= n; len <<= 1) {
    const double angle = -2 * M_PI / static_cast<double>(len);
    const double wr = std::cos(angle), wi = std::sin(angle);
    const std::size_t half = len >> 1;
    for (std::size_t i = 0; i < n; i += len) {
      double cr = 1, ci = 0;
      for (std::size_t k = 0; k < half; k++) {
        const double ar = re[i + k], ai = im[i + k];
        const double br = re[i + k + half], bi = im[i + k + half];
        const double vr = br * cr - bi * ci, vi = br * ci + bi * cr;
        re[i + k] = ar + vr; im[i + k] = ai + vi;
        re[i + k + half] = ar - vr; im[i + k + half] = ai - vi;
        const double next = cr * wr - ci * wi;
        ci = cr * wi + ci * wr;
        cr = next;
      }
    }
  }
}

struct Period { double hz, aperiodicity; };

// pitchPass: `count` samples, every `step`th from `from`, averaged in steps,
// as a zero-mean block; the period by YIN's normalised difference.
inline std::optional<Period> pitchPass(const float* x, std::size_t from, std::size_t count, std::size_t step, double rate) {
  const std::size_t w = count;
  std::vector<double> y(w);
  double mean = 0;
  for (std::size_t i = 0; i < w; i++) {
    double v = 0;
    for (std::size_t k = 0; k < step; k++) v += x[from + i * step + k];
    y[i] = v / static_cast<double>(step);
    mean += y[i];
  }
  mean /= static_cast<double>(w);
  double energy = 0;
  for (std::size_t i = 0; i < w; i++) { y[i] -= mean; energy += y[i] * y[i]; }
  if (energy / static_cast<double>(w) < 1e-9) return std::nullopt;  // nothing there to measure

  std::size_t size = 1;
  while (size < 2 * w) size <<= 1;
  std::vector<double> re(size, 0.0), im(size, 0.0);
  for (std::size_t i = 0; i < w; i++) re[i] = y[i];
  fft(re.data(), im.data(), size);
  for (std::size_t i = 0; i < size; i++) { re[i] = re[i] * re[i] + im[i] * im[i]; im[i] = 0; }
  fft(re.data(), im.data(), size);  // real and even, so forward is inverse
  const double sz = static_cast<double>(size);

  std::vector<double> cum(w + 1, 0.0);
  for (std::size_t i = 0; i < w; i++) cum[i + 1] = cum[i] + y[i] * y[i];

  const double fs = rate / static_cast<double>(step);
  const long tauMin = static_cast<long>(jsMax(2, std::floor(fs / 8000)));
  const long tauMax = static_cast<long>(std::floor(static_cast<double>(w) / 2));
  if (tauMax <= tauMin + 2) return std::nullopt;
  std::vector<double> dn(static_cast<std::size_t>(tauMax + 2), 0.0);
  double running = 0;
  dn[0] = 1;
  const long wl = static_cast<long>(w);
  for (long t = 1; t <= tauMax + 1; t++) {
    const auto ut = static_cast<std::size_t>(t);
    const double d = (cum[static_cast<std::size_t>(wl - t)] + (cum[w] - cum[ut]) - 2 * re[ut] / sz) / static_cast<double>(wl - t);
    running += d;
    dn[ut] = running > 0 ? d * static_cast<double>(t) / running : 1;
  }
  const auto at = [&](long t) { return dn[static_cast<std::size_t>(t)]; };

  long tau = -1;
  for (long t = tauMin; t <= tauMax; t++) {
    if (at(t) < kPitchDip) {
      while (t + 1 <= tauMax && at(t + 1) < at(t)) t++;
      if (t >= tauMax - 1) return std::nullopt;
      tau = t;
      break;
    }
  }
  if (tau < 0) {
    long best = tauMin;
    for (long t = tauMin; t <= tauMax; t++) if (at(t) < at(best)) best = t;
    if (best >= tauMax - 1) return std::nullopt;
    // The earliest dip nearly as deep as the deepest, rather than the deepest.
    const double enough = at(best) * 1.25 + 0.02;
    for (long t = tauMin + 1; t < best; t++) {
      if (at(t) <= enough && at(t) <= at(t - 1) && at(t) <= at(t + 1)) { best = t; break; }
    }
    tau = best;
  }
  // Between samples, by the parabola through a dip and its neighbours.
  const auto vertex = [&](long t) {
    const double a = at(t - 1), b = at(t), c = at(t + 1);
    const double bend = a - 2 * b + c;
    return static_cast<double>(t) + (bend > 0 ? jsMax(-0.5, jsMin(0.5, 0.5 * (a - c) / bend)) : 0);
  };
  double period = vertex(tau);
  // And further out, at two periods, four, eight, as far as the range goes.
  for (double m = 2; m * period <= static_cast<double>(tauMax - 1); m *= 2) {
    long found = static_cast<long>(jsMathRound(m * period));
    // The bound is asked again each time round with the dip found so far, as
    // the page's loop does: a deeper dip moves the end of the search with it.
    for (long t = std::max(tauMin, found - 2); t <= std::min(tauMax - 1, found + 2); t++) if (at(t) < at(found)) found = t;
    if (found <= 1 || found >= tauMax) break;
    period = vertex(found) / m;
  }
  return Period { fs / period, jsMax(0, at(tau)) };
}

// estimatePeriod: the newest stretch of up to 16384 samples, and if that is
// not trusted and there is more, the whole window decimated to fit.
inline std::optional<Period> estimatePeriod(const float* x, std::size_t n, double rate) {
  if (n < 16) return std::nullopt;
  const std::size_t w = std::min(n, kPitchMaxWindow);
  const auto near = pitchPass(x, n - w, w, 1, rate);
  if (near && near->aperiodicity <= kPitchTrust) return near;
  if (n <= kPitchMaxWindow) return near;
  const std::size_t step = static_cast<std::size_t>(std::ceil(static_cast<double>(n) / kPitchMaxWindow));
  const std::size_t count = n / step;
  const auto far = pitchPass(x, n - count * step, count, step, rate);
  if (!far) return near;
  if (!near) return far;
  return far->aperiodicity < near->aperiodicity ? far : near;
}

// correlation: one for two channels alike, nought for unrelated, minus one for one the other inverted.
inline double correlation(const float* left, const float* right, std::size_t n) {
  double lr = 0, ll = 0, rr = 0;
  for (std::size_t i = 0; i < n; i++) {
    lr += static_cast<double>(left[i]) * right[i];
    ll += static_cast<double>(left[i]) * left[i];
    rr += static_cast<double>(right[i]) * right[i];
  }
  const double denom = std::sqrt(ll * rr);
  return denom > 1e-9 ? lr / denom : 0;
}

// What it hears, and the onset.
class Hearing {
 public:
  double pitch = 0, bright = 0, width = 1, flux = 0, fluxRaw = 0;
  std::array<double, 4> bands { 0, 0, 0, 0 };
  int frame = 0;
  std::optional<double> pitchWant;
  struct Onset { int count = 0; double last = -HUGE_VAL; bool armed = true; } onset;

  // hearingFollow and hearingSlew.
  static double follow(double now, double want, double elapsed) {
    const double tau = want > now ? kEnvAttack : kEnvRelease;
    return now + (want - now) * (1 - std::exp(-(elapsed / 1000) / tau));
  }
  static double slew(double now, double want, double elapsed) {
    const double most = kHearSlew * jsMax(0, elapsed) / 1000;
    return now + jsMax(-most, jsMin(most, want - now));
  }

  // hearingStep, from the window: `x` the lane the trigger watches, `a` and
  // `b` the pair the X-Y view draws (either missing, or the same lane, is
  // mono), all `n` long; `heldHz` the lowest held key's pitch, if any.
  void step(const float* x, const float* a, const float* b, std::size_t n, double rate, double elapsed,
            std::optional<double> heldHz, double now) {
    if (!x || n < 256 || (n & (n - 1)) != 0) return;
    if (re_.size() != n) {
      re_.assign(n, 0.0); im_.assign(n, 0.0); hann_.assign(n, 0.0);
      for (std::size_t i = 0; i < n; i++) hann_[i] = 0.5 - 0.5 * std::cos(2 * M_PI * static_cast<double>(i) / static_cast<double>(n - 1));
      hasPrev_ = false;
    }
    double sum = 0, w2 = 0, early = 0;
    for (std::size_t i = 0; i < n; i++) {
      const double v = x[i];
      re_[i] = v * hann_[i]; im_[i] = 0; sum += v * v; w2 += hann_[i] * hann_[i];
      if (i == (n >> 1) - 1) early = sum;
    }
    const double rms = std::sqrt(sum / static_cast<double>(n));
    // One steady sound, or a note starting or stopping part-way through.
    const double late = sum - early;
    const bool steady = early > 0 && late > 0 && late / early < 2 && early / late < 2;
    fft(re_.data(), im_.data(), n);
    const std::size_t half = n >> 1;
    const double binHz = rate / static_cast<double>(n);
    mags_.resize(half);
    for (std::size_t k = 0; k < half; k++) mags_[k] = std::hypot(re_[k], im_[k]);

    // The bands, by Parseval, a full-scale sine inside one reading one there.
    for (std::size_t bi = 0; bi < kHearingBands.size(); bi++) {
      const auto& band = kHearingBands[bi];
      const auto lo = static_cast<std::size_t>(jsMax(1, std::ceil(band.from / binHz)));
      const auto hi = band.to > 0 ? static_cast<std::size_t>(jsMin(static_cast<double>(half), std::ceil(band.to / binHz))) : half;
      double power = 0;
      for (std::size_t k = lo; k < hi; k++) power += mags_[k] * mags_[k];
      const double bandRms = std::sqrt(2 * power / (static_cast<double>(n) * w2));
      bands[bi] = follow(bands[bi], jsMin(1, bandRms / kEnvFull), elapsed);
    }

    // Flux: rising energy since the last spectrum, as a share of the whole.
    double rise = 0, total = 0;
    if (hasPrev_) {
      for (std::size_t k = 1; k < half; k++) { rise += jsMax(0, mags_[k] - prev_[k]); total += mags_[k]; }
    }
    prev_.swap(mags_);
    hasPrev_ = true;
    fluxRaw = total > 1e-9 ? jsMin(1, rise / total) : 0;
    flux = follow(flux, rms < kHearFloor ? 0 : fluxRaw, elapsed);
    onsetStep(rms, late > early, now);

    if (rms >= kHearFloor) {
      // Brightness: the centroid, on a log scale from 100 Hz to 8 kHz.
      double weighted = 0, mass = 0;
      for (std::size_t k = 1; k < half; k++) { weighted += static_cast<double>(k) * binHz * prev_[k]; mass += prev_[k]; }
      if (mass > 1e-12) {
        const double centroid = weighted / mass;
        const double want = jsMax(0, jsMin(1, std::log2(jsMax(1, centroid) / 100) / std::log2(80.0)));
        bright = slew(bright, want, elapsed);
      }
      // Pitch: a held key, else the estimator past its gate on a steady
      // window; the estimator every other frame, the slew every frame.
      if ((frame++ & 1) == 0) {
        std::optional<double> hz = heldHz;
        if (!hz && steady) {
          const auto found = estimatePeriod(x, n, rate);
          if (found && found->aperiodicity <= kPitchTrust) hz = found->hz;
        }
        if (hz && *hz > 0) pitchWant = jsMax(-1, jsMin(1, std::log2(*hz / kPitchRef) / 2));
      }
      if (pitchWant) pitch = slew(pitch, *pitchWant, elapsed);
      // Width: the correlation of the pair the X-Y view draws; one lane is mono.
      const double want = a && b && a != b ? correlation(a, b, n) : 1;
      width = slew(width, want, elapsed);
    }
  }

 private:
  // onsetStep: the raw flux through 0.3, the energy rising, at most every
  // 80 ms, and armed again once the flux falls under 0.12.
  void onsetStep(double rms, bool rising, double now) {
    if (onset.armed && rising && rms >= kHearFloor && fluxRaw > kOnsetOn && now - onset.last >= kOnsetGap) {
      onset.count++; onset.last = now; onset.armed = false;
    } else if (!onset.armed && fluxRaw < kOnsetOff) {
      onset.armed = true;
    }
  }

  std::vector<double> re_, im_, hann_, mags_, prev_;
  bool hasPrev_ = false;
};

// The hearing's sources: Pitch, Brightness, the four bands, Width, Flux, and
// Onset. While what is heard is the generator they are the picture's - a
// loop, with its reach - which the owner says (`hears`).
class HearingSource : public ModSource {
 public:
  enum class Kind { Pitch, Bright, Band1, Band2, Band3, Band4, Width, Flux };
  HearingSource(Kind kind, const Hearing& h, const bool& hears) : ModSource(idFor(kind)), kind_(kind), h_(h), hears_(hears) {
    reachVaries = true;
  }
  double value() const override {
    switch (kind_) {
      case Kind::Pitch: return h_.pitch;
      case Kind::Bright: return h_.bright;
      case Kind::Band1: return h_.bands[0];
      case Kind::Band2: return h_.bands[1];
      case Kind::Band3: return h_.bands[2];
      case Kind::Band4: return h_.bands[3];
      case Kind::Width: return h_.width;
      case Kind::Flux: return h_.flux;
    }
    return 0;
  }
  bool picture() const override { return hears_; }
  static const char* idFor(Kind k) {
    switch (k) {
      case Kind::Pitch: return "hear.pitch";
      case Kind::Bright: return "hear.bright";
      case Kind::Band1: return "hear.band1";
      case Kind::Band2: return "hear.band2";
      case Kind::Band3: return "hear.band3";
      case Kind::Band4: return "hear.band4";
      case Kind::Width: return "hear.width";
      case Kind::Flux: return "hear.flux";
    }
    return "";
  }

 private:
  Kind kind_;
  const Hearing& h_;
  const bool& hears_;
};
class OnsetSource : public ModSource {
 public:
  OnsetSource(const Hearing& h, const bool& hears, const double& now) : ModSource("hear.onset"), h_(h), hears_(hears), now_(now) {
    event = true;
  }
  // A flash for the eye, 150 ms long; what a destination reads is the count.
  double value() const override { return jsMax(0, 1 - (now_ - h_.onset.last) / 150); }
  int count() const override { return h_.onset.count; }
  bool picture() const override { return hears_; }

 private:
  const Hearing& h_;
  const bool& hears_;
  const double& now_;
};

// The hearing and its sources, registered together, stepped once a frame.
class HearingSources {
 public:
  explicit HearingSources(Matrix& matrix) {
    using K = HearingSource::Kind;
    for (const K k : { K::Pitch, K::Bright, K::Band1, K::Band2, K::Band3, K::Band4, K::Width, K::Flux })
      sources_.emplace_back(k, hearing_, hears_);
    for (auto& s : sources_) matrix.registerSource(&s);
    matrix.registerSource(&onset_);
    reach();
  }
  HearingSources(const HearingSources&) = delete;
  HearingSources& operator=(const HearingSources&) = delete;

  // hearsGenerator: whether what is heard is the generator, which the owner
  // says as soon as it changes. The page's sources ask it live, stopped or
  // not, so their loop flag and reach follow it at once.
  void hears(bool hearsGenerator) { hears_ = hearsGenerator; reach(); }
  // The time the onset's flash is read at, as the page reads `performance.now()`.
  void setNow(double now) { now_ = now; }

  // hearingStep's frame: nothing while the scope is stopped; the routes
  // compiled again when the answer has flipped since the last step, since
  // they carry the decision; then the window.
  void step(Matrix& matrix, bool running, const float* x, const float* a, const float* b, std::size_t n,
            double rate, double elapsed, std::optional<double> heldHz, double now) {
    now_ = now;
    if (!running) return;
    if (!known_ || seen_ != hears_) { known_ = true; seen_ = hears_; matrix.touch(); }
    hearing_.step(x, a, b, n, rate, elapsed, heldHz, now);
  }
  const Hearing& hearing() const { return hearing_; }
  bool hearsGenerator() const { return hears_; }

 private:
  // The picture's reach while it hears the generator, and none otherwise.
  void reach() { for (auto& s : sources_) s.reach = hears_ ? kPhotoReach : 0; }

  Hearing hearing_;
  bool hears_ = false;
  bool seen_ = false, known_ = false;  // `hearing.gen`, which starts as null, so the first step always touches
  double now_ = 0;
  std::vector<HearingSource> sources_;
  OnsetSource onset_ { hearing_, hears_, now_ };
};

}  // namespace scope
