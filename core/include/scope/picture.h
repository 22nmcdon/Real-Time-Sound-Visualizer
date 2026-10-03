// The picture's own sources, ported from web/scope.html (stage 4): the
// phosphor grid the photocell reads, the beam's moments for roundness, the
// picture meter (coverage, change, novelty and the verdict), the drawn pair's
// direction and edge contact, the photocell's slewed reading, and boredom.
// `phosphor`, `makeMoments`, `makePictureMeter`, `shapeOfPair`, `photoStep`
// and `pictureStep`.
//
// What differs from the page, and why, so nobody goes looking:
//
// - What feeds the grid. The page deposits the renderer's own segment walks -
//   the X-Y figure, each Y-T polyline, the peak bars - in canvas pixels, and
//   the grid is mapped through the graticule's rectangle (`plot`). Here the
//   rectangle is handed in with each segment's owner, and what is walked is
//   whoever's business owns the picture; this piece is the arithmetic, held
//   to the page's with segments both are given.
// - The page's grids are Float32Arrays, so every cell is rounded to a float
//   each time it is written. So are these, written the same way, since a
//   difference in the last bit of a cell is a difference in coverage.
// - The time is handed in. The page's deposit times itself to report its
//   cost; nothing here reads a clock.

#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <string>
#include <vector>

#include "scope/wireframe.h"  // jsHypot, as V8 computes it

namespace scope {

constexpr int kPhosphorN = 64;  // PHOSPHOR_N
constexpr int kBeamK = 8;       // BEAM_K: the beam's steps, which a shaded segment's level is out of

// makeMoments: the beam's path as running second moments, for roundness.
class Moments {
 public:
  // The exact integrals along a straight segment, weighted by its length and
  // by how brightly it was drawn.
  void add(double x0, double y0, double x1, double y1, double level) {
    const double len = jsHypot({ x1 - x0, y1 - y0 }) * level;
    if (!(len > 0)) return;
    w_ += len;
    sx_ += len * (x0 + x1) / 2;
    sy_ += len * (y0 + y1) / 2;
    sxx_ += len * (x0 * x0 + x0 * x1 + x1 * x1) / 3;
    syy_ += len * (y0 * y0 + y0 * y1 + y1 * y1) / 3;
    sxy_ += len * (2 * x0 * y0 + x0 * y1 + x1 * y0 + 2 * x1 * y1) / 6;
  }
  void scale(double k) { w_ *= k; sx_ *= k; sy_ *= k; sxx_ *= k; syy_ *= k; sxy_ *= k; }
  void clear() { w_ = sx_ = sy_ = sxx_ = syy_ = sxy_ = 0; }
  // sqrt(smallest / largest) of the spread, a floor under the largest so
  // that a figure shrinking to nothing is a slope and not a cliff.
  double roundness() const {
    if (!(w_ > 1e-9)) return 0;
    const double mx = sx_ / w_, my = sy_ / w_;
    const double vxx = sxx_ / w_ - mx * mx, vyy = syy_ / w_ - my * my, vxy = sxy_ / w_ - mx * my;
    const double middle = (vxx + vyy) / 2;
    const double split = std::sqrt(std::pow((vxx - vyy) / 2, 2) + vxy * vxy);
    // Math.max's, which keeps a NaN where std::fmax would drop it: a path of
    // samples far past full scale has spreads too large to subtract.
    const auto atLeast0 = [](double v) { return std::isnan(v) ? v : v > 0 ? v : 0; };
    return std::sqrt(atLeast0(middle - split) / (atLeast0(middle + split) + 0.002));
  }

 private:
  double w_ = 0, sx_ = 0, sy_ = 0, sxx_ = 0, syy_ = 0, sxy_ = 0;
};

// The graticule's rectangle in canvas pixels, which the grid lies over.
struct Plot { double x = 0, y = 0, w = 1, h = 1; };

// phosphor: what the phosphor would hold, 64 by 64 over the graticule.
class Phosphor {
 public:
  using Grid = std::array<float, kPhosphorN * kPhosphorN>;
  Phosphor() { grid_.fill(0); }

  // phosphorFade: once a frame, as the canvas fades. Off or a resize clears
  // it; infinite (a negative persistence) leaves it alone.
  void fade(double persistence, bool resized) {
    frames_++;
    hasMoments_ = true;  // the page makes its moments at the first fade
    if (persistence == 0 || resized) {
      grid_.fill(0);
      moments_.clear();
      return;
    }
    if (persistence < 0) return;
    const double keep = 1 - persistence;
    moments_.scale(keep);
    for (auto& c : grid_) c = static_cast<float>(c * keep);
  }

  // phosphorSegment: a segment in canvas pixels, laid into the cells it
  // crosses, each keeping the brighter of what it held and what is laid on.
  void segment(const Plot& plot, double x0, double y0, double x1, double y1, double level) {
    constexpr int N = kPhosphorN;
    double ax = (x0 - plot.x) / plot.w * N, ay = (y0 - plot.y) / plot.h * N;
    double bx = (x1 - plot.x) / plot.w * N, by = (y1 - plot.y) / plot.h * N;
    // The path, in half-widths of the screen, for roundness.
    if (hasMoments_) moments_.add(ax / N * 2 - 1, 1 - ay / N * 2, bx / N * 2 - 1, 1 - by / N * 2, level);
    // A point that is not a number, or is off at infinity, lays nothing. The
    // page's `Math.max` carries a NaN through to the count and stops there,
    // where `std::fmax` would drop it - and two ends at the same infinity are
    // a NaN only in their difference, so it is the differences that are
    // asked. An infinite count would never finish.
    const double across = std::fabs(bx - ax), down = std::fabs(by - ay);
    if (std::isnan(across) || std::isnan(down)) return;
    double steps = std::fmax(1.0, std::ceil(std::fmax(across, down) * 2));
    if (!(steps < HUGE_VAL)) return;
    // A long one walked only where it crosses the grid, as the page walks it:
    // cut to the grid's square (Liang and Barsky), then the samples it always
    // took that fall in the cut part, two either side for rounding - so the
    // cells are the whole walk's, and one sample a million times full scale
    // is not a hundred million steps in a host that cannot stop. Past 2^40
    // steps, where a step cannot be counted in a double, the cut part afresh.
    double first = 0, last = steps;
    if (steps > 4 * N) {
      double t0 = 0, t1 = 1;
      const double dx = bx - ax, dy = by - ay;
      const auto keep = [&](double p, double q) {
        if (p == 0) return q >= 0;
        const double r = q / p;
        if (p < 0) { if (r > t1) return false; if (r > t0) t0 = r; }
        else { if (r < t0) return false; if (r < t1) t1 = r; }
        return true;
      };
      if (!keep(-dx, ax) || !keep(dx, N - ax) || !keep(-dy, ay) || !keep(dy, N - ay)) return;
      if (steps <= 1099511627776.0) {  // 2^40
        first = std::fmax(0.0, std::floor(t0 * steps) - 2);
        last = std::fmin(steps, std::ceil(t1 * steps) + 2);
      } else {
        const double cx0 = ax + dx * t0, cy0 = ay + dy * t0;
        bx = ax + dx * t1; by = ay + dy * t1; ax = cx0; ay = cy0;
        steps = std::fmax(1.0, std::ceil(std::fmax(std::fabs(bx - ax), std::fabs(by - ay)) * 2));
        last = steps;
      }
    }
    for (double s = first; s <= last; s++) {
      const double t = s / steps;
      const double cx = std::floor(ax + (bx - ax) * t), cy = std::floor(ay + (by - ay) * t);
      if (cx < 0 || cy < 0 || cx >= N || cy >= N) continue;
      float& cell = grid_[static_cast<std::size_t>(cy * N + cx)];
      if (cell < level) cell = static_cast<float>(level);
    }
  }

  // phosphorDeposit: a polyline; `steps`, when given, is the beam's step for
  // each segment, and a segment deposits what it was drawn at.
  void deposit(const Plot& plot, const double* xs, const double* ys, std::size_t count, const int* steps = nullptr) {
    for (std::size_t i = 0; i + 1 < count; i++) {
      const double level = steps ? (steps[i] + 1.0) / kBeamK : 1;
      segment(plot, xs[i], ys[i], xs[i + 1], ys[i + 1], level);
    }
  }

  // drawSpectrogram's: no beam draws a spectrogram, so the grid holds nothing.
  void blank() {
    grid_.fill(0);
    if (hasMoments_) moments_.clear();
  }

  // phosphorRead: brightness at a point of the graticule, five bilinear
  // reads - the centre and a cross three quarters of a cell out - so it
  // moves smoothly as the reticle does.
  double read(double u, double v) const {
    constexpr int N = kPhosphorN;
    const auto at = [&](double x, double y) {
      const double fx = x * N - 0.5, fy = y * N - 0.5;
      const double x0 = std::floor(fx), y0 = std::floor(fy);
      const double tx = fx - x0, ty = fy - y0;
      const auto cell = [&](double cx, double cy) -> double {
        return (cx < 0 || cy < 0 || cx >= N || cy >= N) ? 0 : grid_[static_cast<std::size_t>(cy * N + cx)];
      };
      return cell(x0, y0) * (1 - tx) * (1 - ty) + cell(x0 + 1, y0) * tx * (1 - ty)
           + cell(x0, y0 + 1) * (1 - tx) * ty + cell(x0 + 1, y0 + 1) * tx * ty;
    };
    const double d = 0.75 / N;
    return (at(u, v) + at(u - d, v) + at(u + d, v) + at(u, v - d) + at(u, v + d)) / 5;
  }

  const Grid& grid() const { return grid_; }
  const Moments& moments() const { return moments_; }
  int frames() const { return frames_; }

 private:
  Grid grid_;
  Moments moments_;
  bool hasMoments_ = false;
  int frames_ = 0;
};

// The verdict's floors and the meter's history, as the page sets them.
constexpr int kMeterCoarse = 16;                         // METER_COARSE
constexpr double kMeterEvery = 0.25;                     // METER_EVERY, seconds
constexpr std::size_t kMeterDepth = 60, kMeterRecent = 8;  // METER_DEPTH, METER_RECENT
constexpr double kMeterWindow = 4;                       // METER_WINDOW, seconds
constexpr double kChangeFloor = 0.02, kNoveltyFloor = 0.2, kSaturated = 0.35, kStrained = -6;

// makePictureMeter: what the picture says - how much is lit, how much it
// moved, how new it is - and the verdict on the loop.
class PictureMeter {
 public:
  using Coarse = std::array<float, kMeterCoarse * kMeterCoarse>;

  double coverage() const { return coverage_; }
  double lit() const { return lit_; }
  double change() const { return change_; }
  double novelty() const { return novelty_; }
  std::size_t depth() const { return history_.size(); }

  // `limiting` is how hard the monitor chains' limiters work, in dB, nought or less.
  void update(const Phosphor::Grid& grid, double dt, double limiting) {
    clock_ += dt;
    limiting_ = limiting;
    // A soft sum, every cell capped at one; a quarter of the screen lit reads one.
    double soft = 0;
    for (const float c : grid) soft += c < 1 ? c : 1;
    lit_ = soft / static_cast<double>(grid.size());
    coverage_ = std::fmin(1.0, lit_ * 4);
    change_ = hasLast_ ? distance(grid.data(), last_.data(), grid.size()) : 0;
    last_ = grid;
    hasLast_ = true;
    // Novelty: how far from the nearest picture of the last fifteen seconds,
    // leaving out the last two.
    since_ += dt;
    if (since_ >= kMeterEvery) {
      since_ = 0;
      const Coarse c = coarse(grid);
      double nearest = 1;
      for (std::size_t k = 0; k + kMeterRecent < history_.size(); k++) {
        nearest = std::fmin(nearest, distance(c.data(), history_[k].data(), c.size()));
      }
      novelty_ = nearest;
      history_.push_back(c);
      if (history_.size() > kMeterDepth) history_.erase(history_.begin());
    }
    recent_.push_back({ clock_, change_, novelty_, lit_, limiting_ });
    while (!recent_.empty() && clock_ - recent_.front().t > kMeterWindow) recent_.erase(recent_.begin());
  }

  // Medians over the window; nothing said until "been here before" can mean anything.
  std::string verdict() const {
    if (clock_ < kMeterWindow || history_.size() <= kMeterRecent + 4) return "listening";
    if (median(&Row::lit) > kSaturated || median(&Row::limiting) < kStrained) return "running away";
    if (median(&Row::change) < kChangeFloor) return "settled";
    return median(&Row::novelty) < kNoveltyFloor ? "cycling" : "wandering";
  }

  void reset() {
    hasLast_ = false; history_.clear(); recent_.clear();
    clock_ = 0; since_ = kMeterEvery;
    coverage_ = 0; lit_ = 0; change_ = 0; novelty_ = 1;
  }

 private:
  struct Row { double t, change, novelty, lit, limiting; };
  static Coarse coarse(const Phosphor::Grid& grid) {
    constexpr int N = kPhosphorN, C = kMeterCoarse, B = N / C;
    Coarse c;
    c.fill(0);
    for (int y = 0; y < N; y++) {
      const int row = (y / B) * C;
      for (int x = 0; x < N; x++) {
        float& cell = c[static_cast<std::size_t>(row + x / B)];
        cell = static_cast<float>(static_cast<double>(cell) + grid[static_cast<std::size_t>(y * N + x)]);
      }
    }
    return c;
  }
  // L1 distance over the two pictures' summed energy; nought when both are dark.
  static double distance(const float* a, const float* b, std::size_t n) {
    double d = 0, s = 0;
    for (std::size_t i = 0; i < n; i++) { d += std::fabs(static_cast<double>(a[i]) - b[i]); s += static_cast<double>(a[i]) + b[i]; }
    return s > 1e-9 ? d / s : 0;
  }
  double median(double Row::*key) const {
    std::vector<double> values;
    for (const auto& r : recent_) values.push_back(r.*key);
    std::sort(values.begin(), values.end());
    return values[values.size() >> 1];
  }

  Phosphor::Grid last_ {};
  bool hasLast_ = false;
  std::vector<Coarse> history_;
  std::vector<Row> recent_;
  double clock_ = 0, since_ = kMeterEvery;
  double coverage_ = 0, lit_ = 0, change_ = 0, novelty_ = 1, limiting_ = 0;
};

// shapeOfPair: the drawn pair, turned and scaled as it is drawn, for which
// way round the beam goes (signed) and how much the screen's edge clips
// (edge). Strided to 2048 points, which the page keeps as floats.
struct PairShape { double signed_ = 0, edge = 0; };
inline PairShape shapeOfPair(const float* left, const float* right, std::size_t n, double gx, double gy,
                             double ox, double oy, double spinTurns, double zoom) {
  static constexpr std::size_t kShape = 2048;
  std::array<float, kShape> sx {}, sy {};
  const double angle = spinTurns * 2 * 3.14159265358979323846;
  const double rc = std::cos(angle), rs = std::sin(angle);
  const std::size_t stride = std::max<std::size_t>(1, (n + kShape - 1) / kShape);
  std::size_t m = 0;
  double mx = 0, my = 0, edge = 0;
  for (std::size_t i = 0; i < n && m < kShape; i += stride, m++) {
    const double l = left[i], r = right[i];
    const double x = (spinTurns != 0 ? l * rc - r * rs : l) * gx + ox;
    const double y = (spinTurns != 0 ? l * rs + r * rc : r) * gy + oy;
    sx[m] = static_cast<float>(x); sy[m] = static_cast<float>(y); mx += x; my += y;
    const double reach = std::fmax(std::fabs(x), std::fabs(y)) * zoom;
    edge += std::fmax(0.0, std::fmin(1.0, (reach - 0.9) / 0.1));
  }
  if (m < 3) return {};
  mx /= static_cast<double>(m); my /= static_cast<double>(m);
  double swept = 0, path = 0;
  for (std::size_t i = 0; i + 1 < m; i++) {
    const double x = sx[i] - mx, y = sy[i] - my;
    const double dx = static_cast<double>(sx[i + 1]) - sx[i], dy = static_cast<double>(sy[i + 1]) - sy[i];
    swept += x * dy - y * dx;
    path += jsHypot({ x, y }) * jsHypot({ dx, dy });
  }
  return { path > 1e-9 ? std::fmax(-1.0, std::fmin(1.0, swept / (path + 1e-6))) : 0, edge / static_cast<double>(m) };
}

// The photocell and the picture's sources, with their defences: half the
// reach any other source may have, a start that is enough to see, and a
// slew of two whole swings a second on every one of them.
constexpr double kPhotoReach = 0.5, kPhotoStart = 0.2, kPhotoSlew = 2;
constexpr double kBoredReach = 0.3, kBoredRise = 0.25, kBoredLeak = 0.2;

struct PictureValues { double round = 0, cover = 0, change = 0, novelty = 0, signed_ = 0, edge = 0, bored = 0; };

// photo and picture, stepped once a frame: photoStep, then pictureStep.
class PictureSources {
 public:
  bool on = false;
  double u = 0.75, v = 0.5;

  // photoStep: the reading under the reticle, slewed. Nothing on the spectrogram.
  void photoStep(const Phosphor& phosphor, double elapsedMs, bool spectrogram) {
    if (!on || spectrogram) { photoRaw_ = 0; photo_ = 0; return; }
    photoRaw_ = phosphor.read(u, v);
    const double most = kPhotoSlew * std::fmax(0.0, elapsedMs) / 1000;
    photo_ += std::fmax(-most, std::fmin(most, photoRaw_ - photo_));
  }

  // pictureStep: the meter fed, boredom risen or drained, each value slewed.
  // `shape` is the drawn pair's, or nothing when there is no frame.
  void pictureStep(const Phosphor& phosphor, const PairShape* shape, double elapsedMs, bool spectrogram, double limiting) {
    if (!on || spectrogram || !shape) { values_ = {}; raw_ = {}; bored_ = 0; return; }
    const double dt = std::fmax(0.0, elapsedMs) / 1000;
    meter_.update(phosphor.grid(), dt, limiting);
    const double stuck = std::fmax(0.0, std::fmin(1.0, 1 - std::fmax(meter_.change() / (2 * kChangeFloor),
                                                                     meter_.novelty() / (2 * kNoveltyFloor))));
    bored_ += dt * (kBoredRise * stuck - kBoredLeak * bored_);
    bored_ = std::fmax(0.0, std::fmin(1.0, bored_));
    raw_.round = phosphor.moments().roundness();
    raw_.signed_ = shape->signed_;
    raw_.edge = shape->edge;
    raw_.cover = meter_.coverage();
    raw_.change = meter_.change();
    raw_.novelty = meter_.novelty();
    raw_.bored = bored_;
    const double most = kPhotoSlew * std::fmax(0.0, elapsedMs) / 1000;
    const auto slew = [&](double& value, double target) { value += std::fmax(-most, std::fmin(most, target - value)); };
    slew(values_.round, raw_.round); slew(values_.cover, raw_.cover); slew(values_.change, raw_.change);
    slew(values_.novelty, raw_.novelty); slew(values_.signed_, raw_.signed_); slew(values_.edge, raw_.edge);
    slew(values_.bored, raw_.bored);
  }

  // setPhoto: on, the meter starts afresh; off, the photocell reads nothing.
  void setOn(bool want) {
    on = want;
    if (on) meter_.reset();
    else { photo_ = 0; photoRaw_ = 0; }
  }

  double photo() const { return photo_; }
  double photoRaw() const { return photoRaw_; }
  const PictureValues& values() const { return values_; }
  const PictureValues& raw() const { return raw_; }
  double bored() const { return bored_; }
  const PictureMeter& meter() const { return meter_; }

 private:
  double photo_ = 0, photoRaw_ = 0, bored_ = 0;
  PictureValues values_, raw_;
  PictureMeter meter_;
};

}  // namespace scope
