// The level, ported from web/scope.html: how loud the signal on the screen is,
// as the source `env.live` - an envelope follower over a lane of samples, fast
// to rise and slow to fall, so it describes a note rather than flickering on
// every cycle. `updateEnvelope` and the source's value.
//
// What differs from the page, and why, so nobody goes looking:
//
// - What it is handed. The page reads the screen's own fetch of the signal
//   lane the trigger watches, so its window follows the timebase; the core
//   reads whatever lane its owner hands it, and the plugin hands it the last
//   2048 frames of the picture's left channel. A steady tone reads the same
//   either way to within the part of a cycle the window cuts off.

#pragma once

#include <cmath>
#include <cstddef>

namespace scope {

constexpr double kEnvAttack = 0.02, kEnvRelease = 0.25;  // seconds
constexpr double kEnvFull = 0.707;                       // RMS of a full-scale sine

class Level {
 public:
  // updateEnvelope: the RMS of the lane, strided to about 512 reads, followed.
  void update(const float* lane, std::size_t length, double elapsedMs) {
    double sum = 0;
    std::size_t n = 0;
    const std::size_t stride = length / 512 > 1 ? length / 512 : 1;
    for (std::size_t i = 0; i < length; i += stride) {
      const double v = lane[i];
      sum += v * v;
      n++;
    }
    const double rms = n > 0 ? std::sqrt(sum / static_cast<double>(n)) : 0;
    const double tau = rms > env_ ? kEnvAttack : kEnvRelease;
    env_ += (rms - env_) * (1 - std::exp(-(elapsedMs / 1000) / tau));
  }
  double env() const { return env_; }
  // The source's value: the level as a share of a full-scale sine's.
  double value() const { return env_ / kEnvFull < 1 ? env_ / kEnvFull : 1; }

 private:
  double env_ = 0;
};

}  // namespace scope
