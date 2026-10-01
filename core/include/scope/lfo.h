// The page's two LFOs, ported from `lfoStep` in web/scope.html: a phase run
// at `rate` hertz and read through `waveAt`, or, for the random shape, a
// level drawn once a cycle and held. Advanced once a sample whether or not
// anything is patched from it, so its phase does not jump when something is.

#pragma once

#include <string_view>

#include "scope/noise.h"
#include "scope/wave.h"

namespace scope {

struct Lfo {
  Shape shape = Shape::Sine;
  bool random = false;  // the page's "random": sample and hold, once a cycle
  double rate = 0.2, depth = 0.5, phase = 0, held = 0, value = 0;
  int epoch = 0;

  void setShape(std::string_view name) {
    random = name == "random";
    shape = shapeNamed(name);
  }
};

inline double lfoStep(Lfo& lfo, double rate, Random& random) {
  lfo.phase += kTwoPi * lfo.rate / rate;
  if (lfo.phase >= kTwoPi) {
    lfo.phase -= kTwoPi;
    lfo.held = random.next() * 2 - 1;
  }
  lfo.value = lfo.random ? lfo.held : waveAt(lfo.shape, lfo.phase);
  return lfo.value;
}

}  // namespace scope
