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
#include <string>
#include <vector>

#include "scope/picture.h"  // pictureMovesOf, whose three choices Scan's Reads share
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

/* One picture a frame can read: its grid and the hold its picture stage
   has on what it moves. */
template <typename Cell>
struct ScanPicture {
  double hold = 1;
  const Cell* grid = nullptr;
  std::size_t length = 0;
};

/* What each layer's Scan reads (P7b, cross-scan), the page's SCAN_READS and
   scanReadsOf: its own picture, the other layer's, or both - the same three
   as the picture menus' (pictureMovesOf), with the layer's own the answer to
   anything else. */
inline std::string scanReadsOf(const std::string& value, const std::string& own) { return pictureMovesOf(value, own); }

/* What a frame's reading is handed, as the page's scanStep picks it: each
   layer's depth and what it reads, and the two pictures - each layer's own
   grid and hold while the layers draw a picture each (`live`); otherwise the
   one screen and the shared stage's hold, as both, and every layer reads it. */
template <typename Cell>
struct ScanInput {
  bool live = false;
  std::array<double, 2> depth { { 0, 0 } };
  std::array<std::string, 2> reads { { "A", "B" } };
  std::array<ScanPicture<Cell>, 2> pictures {};
};

template <typename Cell>
ScanInput<Cell> scanInput(bool live, const std::array<double, 2>& depth, const std::array<std::string, 2>& reads,
                          double sharedHold, const std::array<double, 2>& ownHold, const Cell* shared,
                          const std::array<const Cell*, 2>& own, std::size_t length) {
  ScanInput<Cell> in;
  in.live = live;
  in.depth = depth;
  in.reads = reads;
  for (std::size_t p = 0; p < 2; p++) in.pictures[p] = { live ? ownHold[p] : sharedHold, live ? own[p] : shared, length };
  return in;
}

// scanPicturesOf: the pictures, 0 for A's and 1 for B's, a layer reading `reads` reads.
inline std::size_t scanPicturesOf(const std::string& reads, std::array<std::size_t, 2>& out) {
  if (reads == "both") { out = { { 0, 1 } }; return 2; }
  out = { { reads == "A" ? std::size_t { 0 } : std::size_t { 1 }, 0 } };
  return 1;
}

/* Notes strike the screen (P7b): STRIKE_DEFAULT (the slider's percent to
   start), STRIKE_ARC (a twelfth of the circle) and STRIKE_SEGMENTS. The
   page's comment over scanStrike says why it is laid where Scan reads. */
constexpr double kStrikeDefault = 50;
constexpr double kStrikeArc = 1.0 / 12;
constexpr int kStrikeSegments = 8;

/* One picture's strike: the arc of scanRead's off-centre circle at the
   note's place round it - C at the reading's start, a semitone a twelfth on -
   as `lay(x0, y0, x1, y1)` calls in canvas pixels through `plot`, eight
   segments a twelfth of the lap long. The circle is the picture's path, or
   where its light is when it has none yet, or the middle of a dark one. */
template <typename Cell, class Lay>
void scanStrikeArc(const std::optional<ScanPath>& path, const Cell* grid, std::size_t length, const Plot& plot, int note,
                   Lay&& lay) {
  ScanPath at { 0.5, 0.5, 0.25 };
  if (path) at = *path;
  else if (const auto g = scanGeometry(grid, length)) at = *g;
  const double r = jsMax(at.r, kScanLeast / kPhosphorN);
  const double cx = at.cx + 0.35 * r, cy = at.cy + 0.2 * r, across = 0.8 * r;
  const double start = 2 * kPi * static_cast<double>(((note % 12) + 12) % 12) / 12;
  const auto x = [&](double th) { return plot.x + (cx + across * std::cos(th)) * plot.w; };
  const auto y = [&](double th) { return plot.y + (cy + across * std::sin(th)) * plot.h; };
  for (int k = 0; k < kStrikeSegments; k++) {
    const double th0 = start + 2 * kPi * kStrikeArc * (static_cast<double>(k) / kStrikeSegments - 0.5);
    const double th1 = start + 2 * kPi * kStrikeArc * (static_cast<double>(k + 1) / kStrikeSegments - 0.5);
    lay(x(th0), y(th0), x(th1), y(th1));
  }
}

/* The page's `scan` and `scanStep`: what is kept from frame to frame - each
   picture's path (P7b: per picture, so one two layers read is followed and
   read once), each layer's hold as last sent, when a setup's quarter of a
   second ends - and the frame itself. The generator is a template, so this need not
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
  /* Which pictures each layer read at the last frame, A as 1 and B as 2,
     nought for a layer not reading: for the loop overlay (P8f), which draws
     a layer's ring on the picture it reads. The page's scanPicturesOf. */
  std::array<int, 2> reads { { 0, 0 } };

  // scanFreeze: nothing read for a quarter of a second while a setup lands.
  void freeze(double nowMs) { frozenUntil = nowMs + kScanFreezeMs; }

  /* scanStep, for `count` layers (two while the keyboard is split or
     layered). Each picture some playing layer reads is followed over
     `elapsedMs` and - unless frozen - read once; a picture none reads
     forgets its path. Then each layer at any depth sends its hold when that
     has moved by more than 0.005, or come back to one - a crossed pair (A
     reading B's or both while B reads A's or both) the lower of the two
     pictures' holds, since the two loops feed each other, and otherwise the
     lower of the pictures it reads - and, when every picture it reads gave
     a reading, a new table made from that reading or the two averaged,
     written into one of its four the generator is not reading. Nothing on
     the spectrogram, which draws no figure to read. */
  template <class Gen, typename Cell>
  void frame(Gen& core, bool spect, int count, const ScanInput<Cell>& in, double elapsedMs, double soft, double nowMs) {
    for (std::size_t k = 0; k < 2; k++) seen[k] = { in.depth[k], in.pictures[k].hold, in.pictures[k].grid };
    reads = { { 0, 0 } };
    if (spect) return;
    const std::size_t layers = static_cast<std::size_t>(count < 0 ? 0 : count > 2 ? 2 : count);
    std::array<bool, 2> wants { { false, false } };
    for (std::size_t l = 0; l < layers; l++) wants[l] = in.depth[l] > 0;
    std::array<std::array<std::size_t, 2>, 2> from {};
    std::array<std::size_t, 2> reading { { 1, 1 } };
    for (std::size_t l = 0; l < 2; l++) {
      if (in.live) reading[l] = scanPicturesOf(in.reads[l], from[l]);
      else from[l] = { { 0, 0 } };
    }
    for (std::size_t l = 0; l < layers; l++)
      if (wants[l]) for (std::size_t i = 0; i < reading[l]; i++) reads[l] |= 1 << from[l][i];
    const bool frozen = nowMs < frozenUntil;
    std::array<bool, 2> read_ { { false, false } };
    for (std::size_t p = 0; p < 2; p++) {
      bool used = false;
      for (std::size_t l = 0; l < 2; l++)
        for (std::size_t i = 0; i < reading[l]; i++) used = used || (wants[l] && from[l][i] == p);
      if (!used) { paths[p].reset(); continue; }
      const ScanPicture<Cell>& pic = in.pictures[p];
      paths[p] = scanFollow(paths[p], pic.grid, pic.length, elapsedMs / 1000);
      if (paths[p] && !frozen) read_[p] = read(pic.grid, pic.length, *paths[p], soft, readings_[p]);
    }
    const bool crossed = in.live && in.reads[0] != "A" && in.reads[1] != "B";
    for (std::size_t l = 0; l < layers; l++) {
      if (!wants[l]) continue;
      const int layer = static_cast<int>(l);
      double hold = crossed ? jsMin(in.pictures[0].hold, in.pictures[1].hold) : in.pictures[from[l][0]].hold;
      if (!crossed && reading[l] == 2) hold = jsMin(in.pictures[from[l][0]].hold, in.pictures[from[l][1]].hold);
      if (std::fabs(hold - held[l]) > 0.005 || (hold == 1 && held[l] != 1)) {
        held[l] = hold;
        core.set("scanHold", hold, layer);
      }
      bool all = true;
      for (std::size_t i = 0; i < reading[l]; i++) all = all && read_[from[l][i]];
      if (!all) continue;
      const std::array<double, kScanPoints>* points = &readings_[from[l][0]];
      if (reading[l] == 2) {
        for (std::size_t i = 0; i < kScanPoints; i++) averaged_[i] = (readings_[0][i] + readings_[1][i]) / 2;
        points = &averaged_;
      }
      CycleTables* into = tables_[l].fresh(core.scanTable(layer), core.scanPrev(layer), core.scanNext(layer));
      if (into && scanTables(*points, *into)) core.setScanTable(into, layer);
    }
  }

  /* scanStrike: a note's light, at `velocity` (a fraction) times `amount`
     (Strike), laid in each picture a layer the note is in reads - `layers`
     has A as 1 and B as 2 - where that layer's Scan is on, each picture
     once. `lay(picture, x0, y0, x1, y1, level)` lays one segment: into that
     layer's own picture (0 or 1) while the layers draw one each, and into
     the shown screen (-1) always, in the page's order. Nothing when Strike
     is at nought, the note is silent, or on the spectrogram. */
  template <typename Cell, class Lay>
  void strike(int note, double velocity, int layers, double amount, bool spect, const ScanInput<Cell>& in,
              const Plot& plot, Lay&& lay) const {
    if (!(amount > 0) || spect) return;
    const double level = jsMin(1, jsMax(0, velocity) * amount);
    if (!(level > 0)) return;
    std::array<bool, 2> struck { { false, false } };
    for (std::size_t l = 0; l < 2; l++) {
      if (!(layers & (1 << l)) || !(in.depth[l] > 0)) continue;
      std::array<std::size_t, 2> from { { 0, 0 } };
      const std::size_t count = in.live ? scanPicturesOf(in.reads[l], from) : 1;
      for (std::size_t i = 0; i < count; i++) {
        const std::size_t p = from[i];
        if (struck[p]) continue;
        struck[p] = true;
        const ScanPicture<Cell>& pic = in.pictures[p];
        scanStrikeArc(paths[p], pic.grid, pic.length, plot, note, [&](double x0, double y0, double x1, double y1) {
          if (in.live) lay(static_cast<int>(p), x0, y0, x1, y1, level);
          lay(-1, x0, y0, x1, y1, level);
        });
      }
    }
  }

  /* The grid blurred by `soft` and read round `path` into `points` (the
     page's scanRead): false only when the grid is not one this reader has
     room for. */
  template <typename Cell>
  bool read(const Cell* grid, std::size_t length, const ScanPath& path, double soft, std::array<double, kScanPoints>& points) {
    const int n = static_cast<int>(jsRound(std::sqrt(static_cast<double>(length))));
    if (static_cast<std::size_t>(n) * static_cast<std::size_t>(n) > blurred_.size()) return false;
    scanBlur(grid, n, soft, rows_.data(), blurred_.data());
    scanRead(blurred_.data(), n, path, points);
    return true;
  }

 private:
  std::array<ScanTables, 2> tables_;
  std::vector<double> rows_ = std::vector<double>(64 * 64), blurred_ = std::vector<double>(64 * 64);
  std::array<std::array<double, kScanPoints>, 2> readings_ {};
  std::array<double, kScanPoints> averaged_ {};
};

}  // namespace scope
