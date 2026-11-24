// Scan's read at a picture frame, the way it is done since 24 Nov against
// the way it was done before (core/tests/pieces/scanread.py reads it).
//
// The frame's read was the whole grid blurred (scanBlur) and then read round
// the path (scanRead), and each table level summed in a pass of its own.
// Since 24 Nov ScanReader blurs only the cells the read touches
// (scanBlurRead) and scanTables writes every level in one pass, each level a
// prefix of the richest's sum. Both are meant to be the same to the bit.
// The old ways are kept here, word for word, as the reference.
//
//   scanread_cpp TRIALS SEED [wrong]   TRIALS grids, paths and softnesses from SEED; prints
//                                      `reads DIFFERING MAXDIFF` and `tables DIFFERING MAXDIFF`
//                                      (values that differ in any bit, and by how much at most),
//                                      then `time OLD NEW`: the thread's own milliseconds for the
//                                      old and new read and tables over every trial, the best of
//                                      three. `wrong` makes the reference's blur a hair wider and
//                                      its tables add the harmonics from the top, the null that
//                                      shows a difference is seen.
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <random>
#include <string>
#include <vector>

#include "scope/scan.h"

namespace {

double cpu() { timespec t; clock_gettime(CLOCK_THREAD_CPUTIME_ID, &t); return t.tv_sec * 1e3 + t.tv_nsec / 1e6; }

// scanTables as it was before 24 Nov: a pass of the harmonics for each level.
bool oldTables(const std::array<double, scope::kScanPoints>& points, scope::CycleTables& out, bool wrong) {
  using namespace scope;
  constexpr std::size_t n = kScanPoints;
  double mean = 0;
  for (std::size_t i = 0; i < n; i++) mean += points[i];
  mean /= n;
  double power = 0;
  for (std::size_t i = 0; i < n; i++) power += (points[i] - mean) * (points[i] - mean);
  if (!(std::sqrt(power / n) > kScanDark)) return false;
  constexpr std::size_t top = kScanHarmonics < n / 2 - 1 ? kScanHarmonics : n / 2 - 1;
  const auto& cn = scanCosine<n>();
  constexpr std::size_t q = 3 * n / 4;
  std::array<double, top + 1> a {}, b {};
  for (std::size_t k = 1; k <= top; k++) {
    double sa = 0, sb = 0;
    for (std::size_t i = 0; i < n; i++) {
      const double p = points[i] - mean;
      const std::size_t m = (k * i) % n;
      sa += p * cn[m];
      sb += p * cn[(m + q) % n];
    }
    a[k] = 2 * sa / n; b[k] = 2 * sb / n;
  }
  constexpr std::size_t T = kScanTable, qt = 3 * T / 4;
  const auto& ct = scanCosine<T>();
  std::size_t level = 0;
  for (std::size_t limit = kScanHarmonics; limit >= 1; limit >>= 1, level++) {
    std::vector<double>& table = out.levels[level];
    const std::size_t upto = std::min(top, limit);
    for (std::size_t i = 0; i < T; i++) {
      double v = 0;
      for (std::size_t j = 1; j <= upto; j++) {
        const std::size_t k = wrong ? upto + 1 - j : j;
        const std::size_t m = (k * i) % T;
        v += a[k] * ct[m] + b[k] * ct[(m + qt) % T];
      }
      table[i] = v;
    }
  }
  double peak = 0;
  for (std::size_t i = 0; i < T; i++) peak = jsMax(peak, std::fabs(out.levels[0][i]));
  if (!(peak > 0)) return false;
  for (auto& table : out.levels) for (std::size_t i = 0; i < T; i++) table[i] /= peak;
  out.most = static_cast<double>(kScanHarmonics);
  return true;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc < 3) { std::fprintf(stderr, "usage: scanread_cpp TRIALS SEED [wrong]\n"); return 2; }
  const int trials = std::atoi(argv[1]);
  const bool wrong = argc > 3 && std::string(argv[3]) == "wrong";
  std::mt19937 rng(static_cast<unsigned>(std::atoi(argv[2])));
  std::uniform_real_distribution<double> unit(0, 1);
  constexpr int n = 64;
  struct Trial { std::vector<float> grid; scope::ScanPath path; double soft; };
  std::vector<Trial> all;
  for (int t = 0; t < trials; t++) {
    Trial tr { std::vector<float>(n * n, 0.0f), {}, 0 };
    // A lit figure - a few rings and noise - so the blur has something to carry.
    const double cx = 0.2 + 0.6 * unit(rng), cy = 0.2 + 0.6 * unit(rng), r = 0.02 + 0.45 * unit(rng);
    for (int s = 0; s < 4000; s++) {
      const double th = 2 * scope::kPi * s / 4000, rr = r * (1 + 0.3 * std::sin(3 * th + 6 * unit(rng) * 0.1));
      const int x = static_cast<int>(std::floor((cx + rr * std::cos(th)) * n)), y = static_cast<int>(std::floor((cy + rr * std::sin(th)) * n));
      if (x >= 0 && x < n && y >= 0 && y < n) tr.grid[static_cast<std::size_t>(y * n + x)] = static_cast<float>(unit(rng));
    }
    tr.path = { cx + 0.1 * (unit(rng) - 0.5), cy + 0.1 * (unit(rng) - 0.5), r * (0.3 + unit(rng)) };
    // Softness from none to past the widest a knob gives, and the edge of the grid now and then.
    const int kind = t % 5;
    tr.soft = kind == 0 ? 0 : kind == 1 ? 0.5 * unit(rng) : kind == 4 ? 20 + 30 * unit(rng) : 6 * unit(rng);
    if (t % 7 == 0) tr.path.cx = unit(rng) < 0.5 ? 0.02 : 0.98;
    all.push_back(tr);
  }
  std::vector<double> rows(n * n), blurredOld(n * n), blurredNew(n * n);
  std::vector<std::uint32_t> rowAt(n * n, 0u), outAt(n * n, 0u);
  std::uint32_t stamp = 0;
  std::array<double, scope::kScanPoints> before {}, after {};
  scope::CycleTables tOld = scope::scanTableSet(), tNew = scope::scanTableSet();
  long readsDiffer = 0, tablesDiffer = 0;
  double readsMost = 0, tablesMost = 0;
  const auto same = [](double a, double b) { return std::memcmp(&a, &b, sizeof a) == 0; };
  for (const auto& tr : all) {
    scope::scanBlur(tr.grid.data(), n, tr.soft + (wrong ? 1e-6 : 0), rows.data(), blurredOld.data());
    scope::scanRead(blurredOld.data(), n, tr.path, before);
    scope::scanBlurRead(tr.grid.data(), n, tr.soft, tr.path, rows.data(), blurredNew.data(), rowAt.data(), outAt.data(), ++stamp);
    scope::scanRead(blurredNew.data(), n, tr.path, after);
    for (std::size_t i = 0; i < before.size(); i++)
      if (!same(before[i], after[i])) { readsDiffer++; readsMost = std::fmax(readsMost, std::fabs(before[i] - after[i])); }
    const bool a = oldTables(before, tOld, wrong), b = scope::scanTables(before, tNew);
    if (a != b) tablesDiffer++;
    else if (a)
      for (std::size_t l = 0; l < tOld.levels.size(); l++)
        for (std::size_t i = 0; i < tOld.levels[l].size(); i++)
          if (!same(tOld.levels[l][i], tNew.levels[l][i])) {
            tablesDiffer++; tablesMost = std::fmax(tablesMost, std::fabs(tOld.levels[l][i] - tNew.levels[l][i]));
          }
  }
  std::printf("reads %ld %.17g\ntables %ld %.17g\n", readsDiffer, readsMost, tablesDiffer, tablesMost);
  // The cost, old and new, of a frame's read and tables over every trial.
  double bestOld = 1e300, bestNew = 1e300, sink = 0;
  for (int r = 0; r < 3; r++) {
    double t0 = cpu();
    for (const auto& tr : all) {
      scope::scanBlur(tr.grid.data(), n, tr.soft, rows.data(), blurredOld.data());
      scope::scanRead(blurredOld.data(), n, tr.path, before);
      oldTables(before, tOld, false);
      sink += tOld.levels[0][7];
    }
    bestOld = std::fmin(bestOld, cpu() - t0);
    t0 = cpu();
    for (const auto& tr : all) {
      scope::scanBlurRead(tr.grid.data(), n, tr.soft, tr.path, rows.data(), blurredNew.data(), rowAt.data(), outAt.data(), ++stamp);
      scope::scanRead(blurredNew.data(), n, tr.path, after);
      scope::scanTables(after, tNew);
      sink += tNew.levels[0][7];
    }
    bestNew = std::fmin(bestNew, cpu() - t0);
  }
  std::printf("time %.4f %.4f %d\n", bestOld, bestNew, sink != 12345.678 ? 1 : 0);
  return 0;
}
