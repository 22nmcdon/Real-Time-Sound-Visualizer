// The drawn cycles, ported from web/scope.html: the four slots' points (the
// drawn cycle's own and the wavetable's three), their defaults, their text in
// a setup code, and `cycleTables`, which turns 256 points into the eight
// band-limited tables the generator reads.

#pragma once

#include <array>
#include <atomic>
#include <cmath>
#include <memory>
#include <optional>
#include <string>
#include <vector>

#include "scope/json.h"
#include "scope/setup.h"
#include "scope/wave.h"

namespace scope {

constexpr std::size_t kCyclePoints = 256;  // CYCLE_POINTS
constexpr std::size_t kCycleTable = 2048;  // CYCLE_TABLE
constexpr std::size_t kCycleSlots = 4;     // CYCLE_SLOTS

using CyclePoints = std::vector<double>;

// cycleTables: band-limited by resynthesis. The drawing's harmonics measured
// once, then every harmonic, half, a quarter and so on to the fundamental
// alone, each table scaled by the richest's peak.
// How many times a cycle's tables have been built, for the shell test to
// see where the work happens.
inline std::atomic<long>& cycleTablesBuilt() { static std::atomic<long> n { 0 }; return n; }

inline CycleTables cycleTables(const CyclePoints& points) {
  cycleTablesBuilt().fetch_add(1, std::memory_order_relaxed);
  const std::size_t n = points.size(), top = n / 2 - 1;  // the Nyquist term has no phase
  std::vector<double> a(top + 1, 0.0), b(top + 1, 0.0);
  for (std::size_t k = 1; k <= top; k++) {
    double sa = 0, sb = 0;
    for (std::size_t i = 0; i < n; i++) {
      const double th = 2 * kPi * static_cast<double>(k) * static_cast<double>(i) / static_cast<double>(n);
      sa += points[i] * std::cos(th);
      sb += points[i] * std::sin(th);
    }
    a[k] = 2 * sa / static_cast<double>(n); b[k] = 2 * sb / static_cast<double>(n);
  }
  CycleTables out;
  out.most = static_cast<double>(n / 2);
  for (std::size_t limit = n / 2; limit >= 1; limit >>= 1) {
    std::vector<double> table(kCycleTable);
    const std::size_t upto = std::min(top, limit);
    for (std::size_t i = 0; i < kCycleTable; i++) {
      double v = 0;
      const double th = 2 * kPi * static_cast<double>(i) / static_cast<double>(kCycleTable);
      for (std::size_t k = 1; k <= upto; k++) {
        v += a[k] * std::cos(static_cast<double>(k) * th) + b[k] * std::sin(static_cast<double>(k) * th);
      }
      table[i] = v;
    }
    out.levels.push_back(std::move(table));
  }
  double peak = 0;
  for (const double v : out.levels[0]) peak = jsMax(peak, std::fabs(v));
  if (peak > 0) for (auto& table : out.levels) for (double& v : table) v /= peak;
  return out;
}

// CYCLE_ORGAN_PEAK: the peak of sin x + sin 2x / 2 + 0.33 sin 3x, so slot two
// is scaled to 0.95 like the others.
inline double cycleOrganPeak() {
  static const double peak = [] {
    double most = 0;
    for (int i = 0; i < 4096; i++) {
      const double th = 2 * kPi * i / 4096;
      most = jsMax(most, std::fabs(std::sin(th) + 0.5 * std::sin(2 * th) + 0.33 * std::sin(3 * th)));
    }
    return most;
  }();
  return peak;
}

// cycleDefault: slot one a sine; then a sine with its octave and twelfth, a
// saw turned to start at nought, and a pulse of a quarter.
inline CyclePoints cycleDefault(int k) {
  CyclePoints out(kCyclePoints);
  for (std::size_t i = 0; i < kCyclePoints; i++) {
    const double t = static_cast<double>(i) / kCyclePoints, th = 2 * kPi * t;
    if (k == 1) out[i] = 0.95 * (std::sin(th) + 0.5 * std::sin(2 * th) + 0.33 * std::sin(3 * th)) / cycleOrganPeak();
    else if (k == 2) out[i] = 0.95 * (t < 0.5 ? 2 * t : 2 * t - 2);
    else if (k == 3) out[i] = t < 0.25 ? 0.95 : -0.95 / 3;
    else out[i] = std::sin(th);
  }
  return out;
}

// encodeCycle: the points a byte each, in base 64.
inline std::string encodeCycle(const CyclePoints& points) {
  std::u16string bytes;
  for (const double v : points) {
    // A Uint8Array takes NaN as nought.
    const double r = std::fmod(jsMathRound(jsMax(-1, jsMin(1, v)) * 127) + 256, 256);
    bytes += static_cast<char16_t>(std::isnan(r) ? 0 : static_cast<int>(r));
  }
  return *btoa(bytes);
}

// decodeCycle: nothing for anything but 256 bytes of base 64.
inline std::optional<CyclePoints> decodeCycle(const Json* text) {
  if (!text || text->type != Json::Type::String || text->s.empty()) return std::nullopt;
  const auto raw = atob(text->s);
  if (!raw || raw->size() != kCyclePoints) return std::nullopt;
  CyclePoints out;
  for (const char16_t ch : *raw) out.push_back((ch > 127 ? static_cast<double>(ch) - 256 : static_cast<double>(ch)) / 127);
  return out;
}

// cycleIsDefault: every point within a byte's step of the default.
inline bool cycleIsDefault(const CyclePoints& points, int k) {
  const CyclePoints want = cycleDefault(k);
  for (std::size_t i = 0; i < want.size(); i++) if (!(std::fabs(points[i] - want[i]) < 1.0 / 254)) return false;
  return true;
}

// The wavetable's three slots in a code: each its own text, or nothing for a
// default, joined by commas - or nothing at all when all three are defaults.
inline std::string encodeCycleSlots(const std::array<CyclePoints, kCycleSlots>& slots) {
  std::string parts[3];
  bool any = false;
  for (int k = 1; k <= 3; k++) {
    if (!cycleIsDefault(slots[static_cast<std::size_t>(k)], k)) { parts[k - 1] = encodeCycle(slots[static_cast<std::size_t>(k)]); any = true; }
  }
  return any ? parts[0] + "," + parts[1] + "," + parts[2] : "";
}
inline void decodeCycleSlots(const Json* text, std::array<CyclePoints, kCycleSlots>& slots) {
  std::vector<std::u16string> parts;
  if (text && text->type == Json::Type::String) {
    std::size_t from = 0;
    while (true) {
      const std::size_t comma = text->s.find(u',', from);
      parts.push_back(text->s.substr(from, comma == std::u16string::npos ? std::u16string::npos : comma - from));
      if (comma == std::u16string::npos) break;
      from = comma + 1;
    }
  }
  for (int k = 1; k <= 3; k++) {
    const std::size_t at = static_cast<std::size_t>(k - 1);
    std::optional<CyclePoints> got;
    if (at < parts.size()) { const Json part = Json::string(parts[at]); got = decodeCycle(&part); }
    slots[static_cast<std::size_t>(k)] = got ? *got : cycleDefault(k);
  }
}

/* Tables already built, by the points they were built from. A drawn cycle's
   tables are a transform and eight resyntheses, half a million sines and
   cosines - 7 to 8 ms, most of a 512-frame block at 48 kHz - and a preset
   with a drawn cycle, a drawing made by hand, and any preset after one that
   puts the defaults back, all built them on the audio thread as the setup
   landed (6 Nov). The arithmetic stays the page's, which parity holds to the
   sample, so the work is moved rather than made faster: a thread that may
   wait builds them here first (`warm`: the plugin's message thread, as a
   setup or a drawing is handed over, and `prepare`), and the audio thread
   only looks (`take`), without waiting - busy, or not built, and it builds
   them itself as it always did. A few dozen kept, the oldest let go. */
class CycleCache {
 public:
  static CycleCache& shared() { static CycleCache cache; return cache; }

  void warm(const CyclePoints& points) {
    {
      const Held held(busy_);
      if (find(points)) return;
    }
    auto built = std::make_shared<const CycleTables>(cycleTables(points));
    const Held held(busy_);
    if (find(points)) return;
    entries_.push_back({ points, std::move(built) });
    if (entries_.size() > kMost) entries_.erase(entries_.begin());
  }

  std::shared_ptr<const CycleTables> take(const CyclePoints& points) {
    if (busy_.exchange(true, std::memory_order_acquire)) return nullptr;
    const Entry* e = find(points);
    auto out = e ? e->tables : nullptr;
    busy_.store(false, std::memory_order_release);
    return out;
  }

 private:
  static constexpr std::size_t kMost = 32;
  struct Entry { CyclePoints points; std::shared_ptr<const CycleTables> tables; };
  const Entry* find(const CyclePoints& points) const {
    for (const auto& e : entries_) if (e.points == points) return &e;
    return nullptr;
  }
  /* A spin lock rather than std::mutex, which the page's WebAssembly build
     has no threads for. Held only to look and to add; the audio thread only
     ever tries it, once, and a thread that may wait spins. */
  struct Held {
    std::atomic<bool>& busy;
    explicit Held(std::atomic<bool>& b) : busy(b) { while (busy.exchange(true, std::memory_order_acquire)) {} }
    ~Held() { busy.store(false, std::memory_order_release); }
  };
  std::atomic<bool> busy_ { false };
  std::vector<Entry> entries_;
};

// Every slot a setup's cycles name, the defaults for the rest, built ahead.
inline void warmCycles(const Json& setup) {
  if (setup.type != Json::Type::Object) return;
  CycleCache& cache = CycleCache::shared();
  const auto one = decodeCycle(setup.get("cycle"));
  cache.warm(one ? *one : cycleDefault(0));
  std::array<CyclePoints, kCycleSlots> slots;
  decodeCycleSlots(setup.get("cycles"), slots);
  for (std::size_t k = 1; k < kCycleSlots; k++) cache.warm(slots[k]);
}

}  // namespace scope
