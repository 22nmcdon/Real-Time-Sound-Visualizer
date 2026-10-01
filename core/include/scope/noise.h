// The generator's four noises, ported from `makeNoise` and `noiseStep` inside
// `makeGeneratorCore` in web/scope.html: white, Kellet's pink, a leaky brown,
// and the stepped sample-and-hold clocked by the note.
//
// The page draws from `Math.random()`, which no port can match value for
// value, so this draws from a `Random` it is handed. The parity harness hands
// the page the same generator in place of `Math.random`, and the two are then
// held to each other exactly; in the plugin and the website the sequences
// differ, and the noise is the same noise. That is the decision, and what it
// costs: a patch with noise in it does not sound the same sample for sample
// in the plugin as on the site, which nobody could hear and no test should
// ask for.

#pragma once

#include <cstdint>
#include <string_view>

#include "scope/wave.h"

namespace scope {

// mulberry32: small, fast, and written the same way in JavaScript, which is
// what lets the harness give the page exactly this sequence.
class Random {
 public:
  explicit Random(std::uint32_t seed = 1) : a_(seed) {}
  double next() {
    a_ += 0x6D2B79F5u;
    std::uint32_t t = (a_ ^ (a_ >> 15)) * (1u | a_);
    t = (t + ((t ^ (t >> 7)) * (61u | t))) ^ t;
    return static_cast<double>(t ^ (t >> 14)) / 4294967296.0;
  }

 private:
  std::uint32_t a_;
};

enum class Noise { White, Pink, Brown, Stepped };

inline bool noiseNamed(std::string_view name, Noise& out) {
  if (name == "noise") { out = Noise::White; return true; }
  if (name == "pink") { out = Noise::Pink; return true; }
  if (name == "brown") { out = Noise::Brown; return true; }
  if (name == "stepped") { out = Noise::Stepped; return true; }
  return false;
}

constexpr double kPinkGain = 0.28 / 1.767;
constexpr double kBrownGain = 0.0307;

struct NoiseState {
  double b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0, brown = 0;
  double prev = 0, cur = 0, next = 0, last = 1;
  // As `makeNoise` does: the stepped noise's next level is drawn at once.
  explicit NoiseState(Random& random) : next(random.next() * 1.8 - 0.9) {}
};

inline double noiseStep(NoiseState& z, Noise shape, double phase, double step, Random& random) {
  const double white = random.next() * 2 - 1;
  if (shape == Noise::Pink) {
    z.b0 = 0.99886 * z.b0 + white * 0.0555179;
    z.b1 = 0.99332 * z.b1 + white * 0.0750759;
    z.b2 = 0.96900 * z.b2 + white * 0.1538520;
    z.b3 = 0.86650 * z.b3 + white * 0.3104856;
    z.b4 = 0.55000 * z.b4 + white * 0.5329522;
    z.b5 = -0.7616 * z.b5 - white * 0.0168980;
    const double pink = z.b0 + z.b1 + z.b2 + z.b3 + z.b4 + z.b5 + z.b6 + white * 0.5362;
    z.b6 = white * 0.115926;
    return pink * kPinkGain;
  }
  if (shape == Noise::Brown) {
    z.brown = 0.998 * z.brown + white * kBrownGain;
    return z.brown;
  }
  if (shape == Noise::Stepped) {
    const double t = cycleOf(phase), dt = step > 0 ? std::fmin(0.49, step) : 0;
    if (t < z.last) { z.prev = z.cur; z.cur = z.next; z.next = random.next() * 1.8 - 0.9; }
    z.last = t;
    const double jump = t < 0.5 ? z.cur - z.prev : z.next - z.cur;
    return z.cur + jump / 2 * polyBlep(t, dt);
  }
  return white;
}

}  // namespace scope
