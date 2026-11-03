// Scan (P7a), ported from web/scope.html: the phosphor read back as the
// voice's wave. `scanGeometry`, `scanFollow`, `scanBlur`, `scanBilinear`,
// `scanRead`, `scanCosine`, `scanTables` and `scanMix` are the page's, held
// to it by core/tests/parity.py; `ScanReader` is the page's `scanStep` and its
// `scan` object, which the instrument runs at its picture frame.
//
// Where the core is exact and the page is not. The page reads its phosphor
// once a SCREEN frame and the generator takes whichever table is latest at its
// own tick, sixty a second of audio time, so on the page which picture a tick
// plays depends on the screen, and the phosphor's per-frame fade assumes a
// screen at sixty. Here the picture frame is itself sixty a second of audio
// time (`PictureRun::due`), the phosphor fades once a picture frame, and the
// generator's tick is the same sixtieth counted in samples: the table a tick
// plays is the one read at the last picture frame before it, the same on
// every machine and in every render. The frame lands on a block boundary and
// the tick on a sample, so the two are not in lockstep - a table read at a
// frame is played from the next tick after it, up to a sixtieth later - but
// neither depends on anything but the audio.
//
// Nothing here allocates once made: the instrument runs it on the audio
// thread, so the blur's scratch and the tables are made up front, and each
// layer has four tables so the one being written is never one the generator
// is reading (`ScanTables`).

#pragma once

#include <array>
#include <cmath>
#include <cstddef>
#include <optional>
#include <vector>

#include "scope/setup.h"
#include "scope/wave.h"

namespace scope {

// SCAN_RATE, SCAN_POINTS, SCAN_HARMONICS, SCAN_TABLE, SCAN_MOST,
// SCAN_SOFT_DEFAULT, SCAN_DARK, SCAN_FOLLOW, SCAN_LEAST and SCAN_FREEZE_MS:
// the page's comment over them says what each is.
constexpr double kScanRate = 60;
constexpr std::size_t kScanPoints = 256;
constexpr std::size_t kScanHarmonics = 64;
constexpr std::size_t kScanTable = 512;
constexpr double kScanMost = 0.8;
constexpr double kScanSoftDefault = 3;
constexpr double kScanDark = 1e-4;
constexpr double kScanFollow = 1;
constexpr double kScanLeast = 2;
constexpr double kScanFreezeMs = 250;
// How many levels a table has: every harmonic, then half, to the fundamental alone.
constexpr std::size_t kScanLevels = 7;

// The figure's centre of brightness and its RMS radius about it, in
// fractions of the grid; nothing when nothing is lit.
struct ScanPath { double cx = 0, cy = 0, r = 0; };

template <typename Cell>
std::optional<ScanPath> scanGeometry(const Cell* grid, std::size_t length) {
  const int n = static_cast<int>(jsRound(std::sqrt(static_cast<double>(length))));
  double s = 0, sx = 0, sy = 0;
  for (int y = 0; y < n; y++) {
    for (int x = 0; x < n; x++) {
      const double w = grid[y * n + x];
      if (w > 0) { s += w; sx += w * (x + 0.5); sy += w * (y + 0.5); }
    }
  }
  if (!(s > 1e-9)) return std::nullopt;
  const double cx = sx / s, cy = sy / s;
  double rr = 0;
  for (int y = 0; y < n; y++) {
    for (int x = 0; x < n; x++) {
      const double w = grid[y * n + x];
      if (w > 0) rr += w * ((x + 0.5 - cx) * (x + 0.5 - cx) + (y + 0.5 - cy) * (y + 0.5 - cy));
    }
  }
  return ScanPath { cx / n, cy / n, std::sqrt(rr / s) / n };
}

// The path's geometry moved towards the grid's over `dt` seconds: taken at
// once the first time, held while nothing is lit.
template <typename Cell>
std::optional<ScanPath> scanFollow(const std::optional<ScanPath>& path, const Cell* grid, std::size_t length, double dt) {
  const auto g = scanGeometry(grid, length);
  if (!g) return path;
  if (!path) return g;
  const double k = 1 - std::exp(-jsMax(0.0, dt) / kScanFollow);
  return ScanPath { path->cx + (g->cx - path->cx) * k, path->cy + (g->cy - path->cy) * k, path->r + (g->r - path->r) * k };
}

/* The grid blurred by `sigma` cells into `out`, a Gaussian along the rows
   into `rows` and then down the columns, out to three sigma, nought beyond
   the edge. `rows` and `out` hold n * n. The kernel is held to the widest the
   Softness slider reaches and then some (six cells reach 18); a sigma past
   that is not one any control can give. */
constexpr int kScanReachMost = 64;
template <typename Cell>
void scanBlur(const Cell* grid, int n, double sigma, double* rows, double* out) {
  if (!(sigma > 0)) { for (int i = 0; i < n * n; i++) out[i] = grid[i]; return; }
  const int reach = std::min(kScanReachMost, static_cast<int>(std::ceil(3 * sigma)));
  std::array<double, 2 * kScanReachMost + 1> kernel {};
  const int width = 2 * reach + 1;
  double sum = 0;
  for (int j = -reach; j <= reach; j++) {
    const double d = j;
    kernel[static_cast<std::size_t>(j + reach)] = std::exp(-d * d / (2 * sigma * sigma));
    sum += kernel[static_cast<std::size_t>(j + reach)];
  }
  for (int j = 0; j < width; j++) kernel[static_cast<std::size_t>(j)] /= sum;
  for (int y = 0; y < n; y++) {
    for (int x = 0; x < n; x++) {
      double v = 0;
      for (int j = -reach; j <= reach; j++) {
        const int xx = x + j;
        if (xx >= 0 && xx < n) v += kernel[static_cast<std::size_t>(j + reach)] * grid[y * n + xx];
      }
      rows[y * n + x] = v;
    }
  }
  for (int y = 0; y < n; y++) {
    for (int x = 0; x < n; x++) {
      double v = 0;
      for (int j = -reach; j <= reach; j++) {
        const int yy = y + j;
        if (yy >= 0 && yy < n) v += kernel[static_cast<std::size_t>(j + reach)] * rows[yy * n + x];
      }
      out[y * n + x] = v;
    }
  }
}

// Brightness at u, v of a grid, bilinear between cell centres, nought outside.
inline double scanBilinear(const double* g, int n, double u, double v) {
  const double fx = u * n - 0.5, fy = v * n - 0.5;
  const double x0 = std::floor(fx), y0 = std::floor(fy);
  const double tx = fx - x0, ty = fy - y0;
  const auto cell = [&](double cx, double cy) {
    return cx < 0 || cy < 0 || cx >= n || cy >= n ? 0.0 : g[static_cast<int>(cy) * n + static_cast<int>(cx)];
  };
  return cell(x0, y0) * (1 - tx) * (1 - ty) + cell(x0 + 1, y0) * tx * (1 - ty)
       + cell(x0, y0 + 1) * (1 - tx) * ty + cell(x0 + 1, y0 + 1) * tx * ty;
}

// The path read: kScanPoints brightnesses round the off-centre circle, from
// `blurred`, the grid already blurred by the softness.
inline void scanRead(const double* blurred, int n, const ScanPath& path, std::array<double, kScanPoints>& points) {
  const double r = jsMax(path.r, kScanLeast / n);
  const double cx = path.cx + 0.35 * r, cy = path.cy + 0.2 * r, across = 0.8 * r;
  for (std::size_t i = 0; i < kScanPoints; i++) {
    const double th = 2 * kPi * static_cast<double>(i) / static_cast<double>(kScanPoints);
    points[i] = scanBilinear(blurred, n, cx + across * std::cos(th), cy + across * std::sin(th));
  }
}

// A cosine over N points, kept, as the page keeps one for each length.
template <std::size_t N>
const std::array<double, N>& scanCosine() {
  static const std::array<double, N> c = [] {
    std::array<double, N> out {};
    for (std::size_t i = 0; i < N; i++) out[i] = std::cos(2 * kPi * static_cast<double>(i) / static_cast<double>(N));
    return out;
  }();
  return c;
}

// A table set made at its full size, so filling it allocates nothing.
inline CycleTables scanTableSet() {
  CycleTables t;
  t.most = static_cast<double>(kScanHarmonics);
  t.levels.assign(kScanLevels, std::vector<double>(kScanTable, 0.0));
  return t;
}

/* scanTables: a reading as `cycleRead`'s tables, written into `out` (made by
   scanTableSet): its harmonics, a level with all of them and each level after
   with half, one peak for every level - the richest's - and no DC. False for
   darkness, so the last table is held. */
inline bool scanTables(const std::array<double, kScanPoints>& points, CycleTables& out) {
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
    // sin(x) is cos(x - a quarter turn), three quarters on.
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
      for (std::size_t k = 1; k <= upto; k++) {
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

// `scanMix`, which the voice calls, is in osc.h beside it.

/* A layer's tables: four, so the one written next is never the generator's
   latest, the one it is fading from or the one it is fading to. */
class ScanTables {
 public:
  ScanTables() { for (auto& t : tables_) t = scanTableSet(); }
  // One the three in use are not.
  CycleTables* fresh(const CycleTables* a, const CycleTables* b, const CycleTables* c) {
    for (auto& t : tables_) if (&t != a && &t != b && &t != c) return &t;
    return nullptr;  // four tables and three in use: never
  }

 private:
  std::array<CycleTables, 4> tables_;
};

/* What a frame's reading needs of one layer: its depth, the hold its
   picture stage has on it, and the grid it reads - its own picture's while
   the layers draw one each, the one screen otherwise. */
template <typename Cell>
struct ScanLayer {
  double depth = 0, hold = 1;
  const Cell* grid = nullptr;
  std::size_t length = 0;
};

/* What each layer reads, as the page's scanStep picks it: its own picture's
   grid and hold while the layers draw a picture each (`live`), the one
   screen's grid and the shared stage's hold otherwise. */
template <typename Cell>
std::array<ScanLayer<Cell>, 2> scanLayers(bool live, const std::array<double, 2>& depth, double sharedHold,
                                          const std::array<double, 2>& ownHold, const Cell* shared,
                                          const std::array<const Cell*, 2>& own, std::size_t length) {
  std::array<ScanLayer<Cell>, 2> in;
  for (std::size_t l = 0; l < 2; l++)
    in[l] = { depth[l], live ? ownHold[l] : sharedHold, live ? own[l] : shared, length };
  return in;
}

/* The page's `scan` and `scanStep`: what is kept from frame to frame - each
   layer's path, the hold it last sent, when a setup's quarter of a second
   ends - and the frame itself. The generator is a template, so this need not
   know it: anything with the page's `genSet` for the hold, a way in for the
   table, and the three tables in use, which a harness can stand in for. */
class ScanReader {
 public:
  std::array<std::optional<ScanPath>, 2> paths;
  std::array<double, 2> held { { 1, 1 } };
  double frozenUntil = 0;
  /* What the last frame was handed for each layer - its depth, its hold and
     which grid - kept so a harness can see that the instrument hands each
     layer its own, which no sound it makes could show apart. */
  struct Seen { double depth = 0, hold = 1; const void* grid = nullptr; };
  std::array<Seen, 2> seen {};

  // scanFreeze: nothing read for a quarter of a second while a setup lands.
  void freeze(double nowMs) { frozenUntil = nowMs + kScanFreezeMs; }

  /* scanStep, for `count` layers (two while the keyboard is split or
     layered): a layer at no depth forgets its path; at any depth it sends
     its hold when that has moved by more than 0.005, or come back to one,
     follows the figure over `elapsedMs`, and - unless frozen or the path
     reads darkness - sends a new table, written into one of its four the
     generator is not reading. Nothing on the spectrogram, which draws no
     figure to read. */
  template <class Gen, typename Cell>
  void frame(Gen& core, bool spect, int count, const std::array<ScanLayer<Cell>, 2>& in, double elapsedMs, double soft,
             double nowMs) {
    for (std::size_t k = 0; k < 2; k++) seen[k] = { in[k].depth, in[k].hold, in[k].grid };
    if (spect) return;
    for (int l = 0; l < count && l < 2; l++) {
      const std::size_t k = static_cast<std::size_t>(l);
      const ScanLayer<Cell>& layer = in[k];
      if (!(layer.depth > 0)) { paths[k].reset(); continue; }
      if (std::fabs(layer.hold - held[k]) > 0.005 || (layer.hold == 1 && held[k] != 1)) {
        held[k] = layer.hold;
        core.set("scanHold", layer.hold, l);
      }
      paths[k] = scanFollow(paths[k], layer.grid, layer.length, elapsedMs / 1000);
      if (!paths[k] || nowMs < frozenUntil) continue;
      CycleTables* into = tables_[k].fresh(core.scanTable(l), core.scanPrev(l), core.scanNext(l));
      if (into && read(layer.grid, layer.length, *paths[k], soft, *into)) core.setScanTable(into, l);
    }
  }

  // The grid blurred by `soft` and read round `path` into `into`: false for darkness.
  template <typename Cell>
  bool read(const Cell* grid, std::size_t length, const ScanPath& path, double soft, CycleTables& into) {
    const int n = static_cast<int>(jsRound(std::sqrt(static_cast<double>(length))));
    if (static_cast<std::size_t>(n) * static_cast<std::size_t>(n) > blurred_.size()) return false;
    scanBlur(grid, n, soft, rows_.data(), blurred_.data());
    scanRead(blurred_.data(), n, path, points_);
    return scanTables(points_, into);
  }

 private:
  std::array<ScanTables, 2> tables_;
  std::vector<double> rows_ = std::vector<double>(64 * 64), blurred_ = std::vector<double>(64 * 64);
  std::array<double, kScanPoints> points_ {};
};

}  // namespace scope
