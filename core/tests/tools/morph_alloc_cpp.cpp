// Whether the morph's walk and the host's parameters allocate, once made:
// the brain, the generator and the keyboard as the plugin holds them, every
// operator new counted. For each slider the morph walks, two ends a step of
// its range apart and the walk taken across them; then every slider at once;
// then the host's eight parameters, each moved as the plugin moves it. One
// line each: the slider, the allocations in its walk, and how far the slider
// moved - so a walk that never moved anything, and so could not allocate,
// is told apart from one that moved and did not. The first line is what the
// making allocated: the proof the counter counts. The last says how many of
// every slider's awkward values - out of range, NaN, the infinities, minus
// nought, half a step, 1e21 - the number leaves as its text would.
#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <new>
#include <string>
#include <vector>

#include "scope/restore.h"

// The replacement operator new takes its memory from malloc, so free is the
// matching release; GCC, seeing the standard library's news inlined past it,
// calls the pairing mismatched when it is not.
#pragma GCC diagnostic ignored "-Wmismatched-new-delete"

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

int main() {
  const long before = allocations.load();
  std::vector<scope::Lfo> lfos(2);
  scope::Generator gen(48000, scope::slot::Used, lfos);
  scope::GeneratorNotes notes(gen);
  scope::Keyboard keys(notes);
  scope::Brain brain;
  std::printf("made %ld 0\n", allocations.load() - before);
  // Two ends for a slider: a quarter and three quarters of its range.
  const auto ends = [&](const std::vector<std::string>& ids) {
    scope::Brain::MorphEnd a, b;
    for (const auto& id : scope::morphIds()) {
      const scope::RangeSpec* r = scope::rangeSpec(id);
      const bool walked = std::find(ids.begin(), ids.end(), id) != ids.end();
      const double lo = r->min + (r->max - r->min) * 0.25, hi = r->min + (r->max - r->min) * 0.75;
      a.push_back({ id, walked ? lo : brain.panel.range(id) });
      b.push_back({ id, walked ? hi : brain.panel.range(id) });
    }
    brain.morphA = a; brain.morphB = b; brain.morphApplied.reset();
  };
  const auto walk = [&](const std::vector<std::string>& ids, const char* name) {
    ends(ids);
    brain.morphPos = 0;
    scope::morphStep(brain, gen, keys, lfos);  // the first step, which may make room
    const double from = brain.panel.range(ids.front());
    long counted = 0;
    for (int k = 1; k <= 200; ++k) {
      brain.morphPos = k / 200.0;
      const long start = allocations.load();
      scope::morphStep(brain, gen, keys, lfos);
      counted += allocations.load() - start;
    }
    std::printf("%s %ld %.9g\n", name, counted, brain.panel.range(ids.front()) - from);
  };
  for (const auto& id : scope::morphIds()) walk({ id }, id.c_str());
  walk(scope::morphIds(), "all");
  // The host's parameters, as the instrument applies them: a slider moved by
  // its number, a hundred times each across its range.
  for (const char* id : { "macro1", "macro2", "macro3", "macro4", "morphPos", "amp", "vcfCut", "delayMix" }) {
    const scope::RangeSpec* r = scope::rangeSpec(id);
    const double from = brain.panel.range(id);
    scope::moveSliderTo(id, r->min, brain, gen, keys, lfos);
    long counted = 0;
    for (int k = 1; k <= 100; ++k) {
      const long start = allocations.load();
      scope::moveSliderTo(id, r->min + (r->max - r->min) * k / 100.0, brain, gen, keys, lfos);
      counted += allocations.load() - start;
    }
    std::printf("host:%s %ld %.9g\n", id, counted, brain.panel.range(id) - from);
  }
  // The claim the rest stands on: a number sets a slider as the text of it would.
  scope::Controls byText, byNumber;
  int agree = 0, tried = 0;
  for (const auto& r : scope::kRanges) {
    const std::string id = r.id;
    for (const double v : std::initializer_list<double> { r.min - 50.0, r.max + 50.0, static_cast<double>(NAN), HUGE_VAL, -HUGE_VAL, -0.0, r.min + (r.max - r.min) * 0.37,
                            r.min + r.step * 0.5, r.max - r.step * 0.49, 1e21, -1e-7, r.max + r.step * 0.5 }) {
      byText.setRange(id, scope::toU16(scope::jsNumberToString(v)));
      byNumber.setRangeNumber(id, v);
      tried++;
      const double a = byText.range(id), b = byNumber.range(id);
      if (a == b && std::signbit(a) == std::signbit(b)) agree++;
    }
  }
  std::printf("agree %d %d\n", agree, tried);
  return 0;
}
