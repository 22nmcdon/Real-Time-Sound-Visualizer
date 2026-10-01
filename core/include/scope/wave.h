// The generator's waveforms and the small functions under them, ported from
// web/scope.html: `cycleOf`, `polyBlep`, `polyBlamp`, `drawbarGain`,
// `drawbarWeights`, `intervalRatio`, `svfG`, `svfStep`, `cycleRead` and
// `waveAt`. The page explains each; this is the same arithmetic in the same
// order, held to it by core/tests/parity.py.
//
// Two things the JavaScript leaves to its types and C++ has to say:
//
// - `%` on a double in JavaScript is `std::fmod`, sign of the dividend and
//   all, which is why `cycleOf` folds a negative remainder back itself.
// - The drawn cycle's tables are Float32Arrays in the page, so they are
//   `float` here: a table of doubles would read back values the page never
//   had, and the parity would be a comparison of two different tables.

#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <string_view>
#include <vector>

namespace scope {

constexpr double kPi = 3.14159265358979323846;
constexpr double kTwoPi = kPi * 2;

/* JavaScript's Math.round: to the nearer whole number, a half upwards. Not
   `std::round`, which takes a half away from nought (-2.5 to -3, where the
   page gets -2), and not `floor(x + 0.5)`, which is one too many for the
   double just under a half - 0.49999999999999994 plus a half rounds to one
   in floating point. `x - floor(x)` is exact, so this is the rule itself. */
inline double jsRound(double x) {
  const double r = std::floor(x);
  return x - r >= 0.5 ? r + 1 : r;
}

inline double cycleOf(double phase) {
  const double t = std::fmod(phase / kTwoPi, 1.0);
  return t < 0 ? t + 1 : t;
}

inline double polyBlep(double t, double dt) {
  if (!(dt > 0)) return 0;
  if (t < dt) { const double x = t / dt; return x + x - x * x - 1; }
  if (t > 1 - dt) { const double x = (t - 1) / dt; return x * x + x + x + 1; }
  return 0;
}

inline double polyBlamp(double t, double dt) {
  if (!(dt > 0)) return 0;
  if (t < dt) { const double x = t / dt - 1; return -x * x * x / 3; }
  if (t > 1 - dt) { const double x = (t - 1) / dt + 1; return x * x * x / 3; }
  return 0;
}

// The nine bars' partials, in the order of the drawbars: 16', 5 1/3', 8' ...
constexpr std::array<double, 9> kDrawbarHarmonics { 0.5, 1.5, 1, 2, 3, 4, 5, 6, 8 };

inline double drawbarGain(double level) {
  if (!(level > 0)) return 0;
  const double at = std::fmin(8.0, level);
  return at >= 1 ? std::pow(10.0, -3 * (8 - at) / 20) : at * std::pow(10.0, -21.0 / 20);
}

inline std::array<double, 9>& drawbarWeights(const std::array<double, 9>& levels, std::array<double, 9>& out) {
  double total = 0;
  for (int k = 0; k < 9; k++) { out[k] = drawbarGain(levels[k]); total += out[k]; }
  const double scale = 1 / std::fmax(1.0, total);
  for (int k = 0; k < 9; k++) out[k] *= scale;
  return out;
}

// The page's INTERVALS: the ratio a just interval is, and how many semitones
// the equal one is.
struct Interval { const char* name; int p; int q; int semitones; };
constexpr std::array<Interval, 13> kIntervals {{
  { "Unison", 1, 1, 0 },       { "Minor 2nd", 16, 15, 1 }, { "Major 2nd", 9, 8, 2 },
  { "Minor 3rd", 6, 5, 3 },    { "Major 3rd", 5, 4, 4 },   { "Perfect 4th", 4, 3, 5 },
  { "Tritone", 45, 32, 6 },    { "Perfect 5th", 3, 2, 7 }, { "Minor 6th", 8, 5, 8 },
  { "Major 6th", 5, 3, 9 },    { "Minor 7th", 16, 9, 10 }, { "Major 7th", 15, 8, 11 },
  { "Octave", 2, 1, 12 },
}};

inline double intervalRatio(int index, bool just) {
  const Interval& i = kIntervals.at(static_cast<std::size_t>(index));
  return just ? static_cast<double>(i.p) / i.q : std::pow(2.0, i.semitones / 12.0);
}

// The state-variable filter's two integrators, and its step. `type` is the
// page's: 1 low-pass, 2 band-pass, 3 notch, anything else high-pass.
struct SvfState { double ic1 = 0; double ic2 = 0; };

inline double svfG(double fc, double rate) {
  return std::tan(kPi * std::fmin(fc, 0.49 * rate) / rate);
}

inline double svfStep(SvfState& s, double x, double g, double k, int type) {
  const double a1 = 1 / (1 + g * (g + k)), a2 = g * a1, a3 = g * a2;
  const double v3 = x - s.ic2;
  const double v1 = a1 * s.ic1 + a2 * v3;
  const double v2 = s.ic2 + a2 * s.ic1 + a3 * v3;
  s.ic1 = 2 * v1 - s.ic1;
  s.ic2 = 2 * v2 - s.ic2;
  return type == 1 ? v2 : type == 2 ? k * v1 : type == 3 ? x - k * v1 - v2 : x - k * v1;
}

// A drawn cycle as the page's `cycleTables` leaves it: each table holding
// half the harmonics of the one before, the first with `most` of them.
struct CycleTables {
  double most = 0;
  std::vector<std::vector<float>> levels;
};

inline double cycleRead(const CycleTables* c, double phase, double step) {
  if (c == nullptr || c->levels.empty()) return std::sin(phase);
  const double t = cycleOf(phase);
  const auto& levels = c->levels;
  const int top = static_cast<int>(levels.size()) - 1;
  int lo = 0;
  double w = 0;
  if (step > 0) {
    const double f = std::log2(c->most * 2 * step);
    lo = static_cast<int>(std::fmax(0.0, std::fmin(static_cast<double>(top), std::ceil(f))));
    w = lo < top ? std::fmax(0.0, std::fmin(1.0, f - lo + 1)) : 0;
  }
  auto read = [t](const std::vector<float>& tab) {
    const double n = static_cast<double>(tab.size());
    const double x = t * n, i = std::floor(x), fr = x - i;
    const std::size_t at = static_cast<std::size_t>(i);
    const double a = tab[at % tab.size()], b2 = tab[(at + 1) % tab.size()];
    return a + (b2 - a) * fr;
  };
  const double a = read(levels[static_cast<std::size_t>(lo)]);
  return w > 0 ? a + (read(levels[static_cast<std::size_t>(lo) + 1]) - a) * w : a;
}

enum class Shape { Harmonic, Sine, Triangle, Square, Ramp, Pulse, Morph, Drawbars, Drawn, Wavetable };

// By the page's names. Anything else is the page's `default:`, the harmonic.
inline Shape shapeNamed(std::string_view name) {
  if (name == "sine") return Shape::Sine;
  if (name == "triangle") return Shape::Triangle;
  if (name == "square") return Shape::Square;
  if (name == "ramp") return Shape::Ramp;
  if (name == "pulse") return Shape::Pulse;
  if (name == "morph") return Shape::Morph;
  if (name == "drawbars") return Shape::Drawbars;
  if (name == "drawn") return Shape::Drawn;
  if (name == "wavetable") return Shape::Wavetable;
  return Shape::Harmonic;
}

// What the page passes as `bars`, which is a different thing for each shape:
// the drawbars' nine weights, the drawn cycle's tables, or the wavetable's
// bank of them. One of these, said by which pointer is set.
struct WaveTables {
  const std::array<double, 9>* weights = nullptr;
  const CycleTables* cycle = nullptr;
  const std::vector<CycleTables>* bank = nullptr;
};

inline double waveAt(Shape shape, double phase, double step = 0, const WaveTables& bars = {}, double amount = 0) {
  const double dt = step > 0 ? std::fmin(0.49, step) : 0;
  switch (shape) {
    case Shape::Drawn:
      return cycleRead(bars.cycle, phase, step);
    case Shape::Wavetable: {
      if (bars.bank == nullptr || bars.bank->empty()) return std::sin(phase);
      const auto& bank = *bars.bank;
      const double top = static_cast<double>(bank.size()) - 1;
      const double at = std::fmax(0.0, std::fmin(top, amount));
      const double low = std::floor(at), w = at - low;
      const std::size_t i = static_cast<std::size_t>(low);
      const double a = cycleRead(&bank[i], phase, step);
      return w == 0 ? a : a + (cycleRead(&bank[i + 1], phase, step) - a) * w;
    }
    case Shape::Sine:
      return std::sin(phase);
    case Shape::Triangle: {
      const double t = cycleOf(phase);
      const double pastUp = std::fmod(t + 0.75, 1.0), pastDown = std::fmod(t + 0.25, 1.0);
      return (2 / kPi) * std::asin(std::sin(phase)) + 4 * dt * (polyBlamp(pastDown, dt) - polyBlamp(pastUp, dt));
    }
    case Shape::Square: {
      const double t = cycleOf(phase);
      return 0.9 * ((t < 0.5 ? 1 : -1) + polyBlep(t, dt) - polyBlep(std::fmod(t + 0.5, 1.0), dt));
    }
    case Shape::Ramp: {
      const double t = cycleOf(phase);
      return t * 2 - 1 - polyBlep(t, dt);
    }
    case Shape::Pulse: {
      const double w = std::fmax(0.05, std::fmin(0.95, amount > 0 ? amount : 0.5));
      const double t = cycleOf(phase), size = 0.9 / std::fmax(w, 1 - w);
      return size * ((t < w ? 1 - w : -w) + (polyBlep(t, dt) - polyBlep(std::fmod(t - w + 1, 1.0), dt)) / 2);
    }
    case Shape::Morph: {
      const double at = std::fmax(0.0, std::fmin(3.0, amount));
      const double low = std::floor(at), w = at - low;
      auto station = [&](int k) {
        return k == 0 ? std::sin(phase)
                      : waveAt(k == 1 ? Shape::Triangle : k == 2 ? Shape::Ramp : Shape::Square,
                               k == 2 ? phase + kPi : phase, step);
      };
      const int i = static_cast<int>(low);
      const double a = station(i);
      return w == 0 ? a : a + (station(i + 1) - a) * w;
    }
    case Shape::Drawbars: {
      double sum = 0;
      for (int k = 0; k < 9; k++) {
        const double w = bars.weights != nullptr ? (*bars.weights)[static_cast<std::size_t>(k)] : (k == 2 ? 1 : 0);
        if (w == 0) continue;
        const double m = kDrawbarHarmonics[static_cast<std::size_t>(k)];
        const double room = step > 0 ? std::fmax(0.0, std::fmin(1.0, (0.5 - m * step) / 0.05)) : 1;
        if (room > 0) sum += w * room * std::sin(m * phase);
      }
      return sum;
    }
    case Shape::Harmonic:
      break;
  }
  const double room = std::fmax(0.0, std::fmin(1.0, (0.5 - 3 * dt) / 0.05));
  return std::sin(phase) + room * 0.33 * std::sin(3 * phase);
}

}  // namespace scope
