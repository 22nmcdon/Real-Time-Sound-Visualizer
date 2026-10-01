// The drawn cycles, ported from web/scope.html: the four slots' points (the
// drawn cycle's own and the wavetable's three), their defaults, their text in
// a setup code, and `cycleTables`, which turns 256 points into the eight
// band-limited tables the generator reads.

#pragma once

#include <array>
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
inline CycleTables cycleTables(const CyclePoints& points) {
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

}  // namespace scope
