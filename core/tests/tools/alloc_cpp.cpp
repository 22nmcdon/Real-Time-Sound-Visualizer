// Whether the hearing allocates once it is made: scope::HearingSources made,
// then stepped a frame at a time over a steady tone, as the plugin steps it
// once a block on the audio thread, with every operator new counted. Prints
// what was allocated in the making, what in the steps, and the pitch the
// period estimator reached - so a run where the estimator never ran, and so
// could not allocate, is told apart from one where it ran and did not.
#include <atomic>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <new>
#include <vector>

#include "scope/hearing.h"

namespace {
std::atomic<long> allocations { 0 };
}

void* operator new(std::size_t size) {
  allocations++;
  if (void* p = std::malloc(size ? size : 1)) return p;
  throw std::bad_alloc();
}
void operator delete(void* p) noexcept { std::free(p); }
void operator delete(void* p, std::size_t) noexcept { std::free(p); }

int main(int argc, char** argv) {
  const double hz = argc > 1 ? std::atof(argv[1]) : 440;
  const double rate = 48000;
  std::vector<float> window(scope::kHearN);
  scope::Matrix matrix;
  const long before = allocations.load();
  scope::HearingSources hearing(matrix);
  hearing.hears(true);
  const long made = allocations.load() - before;
  long stepped = 0;
  std::size_t at = 0;
  for (int frame = 0; frame < 120; ++frame) {
    for (auto& v : window) v = static_cast<float>(0.5 * std::sin(2 * M_PI * hz * static_cast<double>(at++) / rate));
    const long start = allocations.load();
    hearing.step(matrix, true, window.data(), window.data(), window.data(), window.size(), rate, 16, std::nullopt, frame * 16.0);
    stepped += allocations.load() - start;
  }
  const auto want = hearing.hearing().pitchWant;
  std::printf("made %ld stepped %ld pitch %.9f\n", made, stepped, want ? *want : -9.0);
  return 0;
}
