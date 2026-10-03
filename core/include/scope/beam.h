// The beam's walk, ported from web/scope.html (stage 4c): what the renderer
// lays into the phosphor grid each frame. The X-Y figure or figures - the
// pair or pairs, turned when the capture has not turned them, placed by full
// scale and offset, magnified - and each Y-T lane, as peak-detect bars when
// there are more samples than pixels and as the polyline otherwise; and the
// beam's shading on both, which makes a fast stroke deposit less than a slow
// one: `beamAnchor`, `beamStep` and the step loop of `strokeBeam`, and the
// walks in `drawMain` and `drawXY` that feed `phosphorDeposit`.
//
// What differs from the page, and why, so nobody goes looking:
//
// - Nothing is drawn. The page strokes the same points it deposits; here only
//   the deposits are made, because what the core owes the plugin is the grid
//   the photocell and the picture meter read, with the window closed. The
//   colours a step would be drawn in are the page's business.
// - The canvas is handed in: its size in CSS pixels, whether it was resized
//   (or wiped, which the page folds into the same flag), and how wide the
//   widest lane name measures, which sets the Y-T gutter when stacked. The
//   page measures text; nothing here can.
// - The page's scratch arrays are Float32Arrays, so every point and squared
//   length is rounded to a float as it is stored. These are rounded the same
//   way, since the steps are read off the lengths.
// - The spectrogram deposits nothing and clears the grid, as the page's does.
//
// One thing in the page that is not what its comment says, ported as it is so
// the two stay together: `strokeBeam`'s hysteresis compares the centre of the
// new step against the old step's edges widened by a fifth of a step, and the
// nearest a neighbouring step's centre can be is half a step out, so it never
// holds a step. See plugin/PLAN.md, stage 4c.

#pragma once

#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <map>
#include <string>
#include <vector>

#include "scope/capture.h"
#include "scope/picture.h"
#include "scope/wave.h"  // jsRound

namespace scope {

constexpr std::size_t kBeamMax = 6000;  // BEAM_MAX: the points a figure is walked in, at most
constexpr double kBeamEps2 = 1e-6;      // BEAM_EPS2: the floor that makes the log safe
constexpr double kBeamTau = 0.5;        // BEAM_TAU, seconds: the anchor's smoothing
constexpr double kBeamAnchorQ = 0.30;   // BEAM_ANCHOR_Q: the speed that still reaches full ink
constexpr double kBeamHistLo = -20, kBeamHistHi = 30;
constexpr int kBeamHistBins = 64;
constexpr double kPadLeft = 44, kPadRight = 14, kPadTop = 16, kPadBottom = 28;  // PAD

// BEAM_LEVELS' ratio - the contrast - for a level, or nought for off and for a
// level the page has no ramp for, which the page also draws unshaded.
inline double beamRatio(const std::string& level) {
  if (level == "subtle") return 3.0;
  if (level == "moderate") return 2.1;
  if (level == "high") return 1.6;
  return 0;
}

// beamStep: a squared length to a step, against the anchor's log2.
inline int beamStep(double len2, double logRef2, double ratio) {
  const double d = (std::log2(len2 > kBeamEps2 ? len2 : kBeamEps2) - logRef2) / 2;
  const double u = 1 - d / std::log2(ratio);
  return u <= 0 ? 0 : u >= 1 ? kBeamK - 1 : static_cast<int>(std::floor(u * kBeamK));
}

// The renderer's scratch and the beam's smoothed anchors, one per display.
class Beam {
 public:
  // beamAnchor: the thirtieth percentile of the squared lengths' log2, from a
  // histogram, smoothed in the log domain per key.
  double anchor(const std::string& key, std::size_t count, double elapsed) {
    std::array<int, kBeamHistBins> hist {};
    const double span = kBeamHistHi - kBeamHistLo;
    for (std::size_t i = 0; i < count; i++) {
      const double l2 = l2_[i] > kBeamEps2 ? l2_[i] : kBeamEps2;
      double bin = std::floor((std::log2(l2) - kBeamHistLo) / span * kBeamHistBins);
      if (bin < 0) bin = 0; else if (bin >= kBeamHistBins) bin = kBeamHistBins - 1;
      hist[static_cast<std::size_t>(bin)]++;
    }
    double seen = 0;
    int bin = 0;
    const double want = static_cast<double>(count) * kBeamAnchorQ;
    for (; bin < kBeamHistBins - 1; bin++) {
      seen += hist[static_cast<std::size_t>(bin)];
      if (seen >= want) break;
    }
    const double median = kBeamHistLo + (bin + 0.5) / kBeamHistBins * span;
    const auto previous = refs_.find(key);
    if (previous == refs_.end() || !std::isfinite(previous->second)) {
      refs_[key] = median;
      return median;
    }
    const double a = 1 - std::exp(-std::fmax(1.0, elapsed) / 1000 / kBeamTau);
    const double next = previous->second + (median - previous->second) * a;
    previous->second = next;
    return next;
  }

  // strokeBeam's steps: one per segment of the `count` points walked.
  void shade(const std::string& key, std::size_t count, double elapsed, double ratio) {
    if (count < 2) return;
    const double logRef2 = anchor(key, count - 1, elapsed);
    const double margin = 0.2 / kBeamK;
    int previous = -1;
    for (std::size_t i = 0; i + 1 < count; i++) {
      int step = beamStep(l2_[i], logRef2, ratio);
      if (previous >= 0 && step != previous) {
        const double u = (step + 0.5) / kBeamK;
        const double lo = static_cast<double>(previous) / kBeamK, hi = (previous + 1.0) / kBeamK;
        if (u > lo - margin && u < hi + margin) step = previous;
      }
      steps_[i] = step;
      previous = step;
    }
  }

  // A point, rounded to a float as the page's scratch stores it, and the
  // squared length of the segment it ends.
  void put(std::size_t n, double x, double y) {
    x_[n] = static_cast<float>(x);
    y_[n] = static_cast<float>(y);
    if (n > 0) {
      const double dx = x_[n] - x_[n - 1], dy = y_[n] - y_[n - 1];
      l2_[n - 1] = static_cast<float>(dx * dx + dy * dy);
    }
  }

  void deposit(Phosphor& phosphor, const Plot& plot, std::size_t count, bool shaded) const {
    phosphor.deposit(plot, x_.data(), y_.data(), count, shaded ? steps_.data() : nullptr);
  }

  // beamRefs.clear(): a setup that changes the figure starts its anchors afresh.
  void clear() { refs_.clear(); }
  const std::map<std::string, double>& refs() const { return refs_; }
  const int* steps() const { return steps_.data(); }

 private:
  std::array<double, kBeamMax> x_ {}, y_ {}, l2_ {};
  std::array<int, kBeamMax> steps_ {};
  std::map<std::string, double> refs_;
};

// What the renderer reads that the capture does not.
struct Figure { int x = 0, y = 1; };
struct Screen {
  std::string display = "yt";   // yt | xy | spect
  double persistence = 0;
  double zoom = 1;
  bool stack = true;
  Figure xyPair;
  std::vector<Figure> figures;  // what the source asks for, or none
  std::string beam = "moderate";
  bool beamXY = true, beamYT = false;
};
struct Canvas { double w = 0, h = 0; bool resized = false; double widestName = 0; };

// The X-Y graticule: square, centred.
inline Plot xyPlot(double w, double h) {
  const double size = std::fmax(40.0, std::fmin(w - 2 * kPadRight, h - 2 * kPadTop));
  const double cx = w / 2, cy = h / 2, radius = size / 2;
  return { cx - radius, cy - radius, size, size };
}

// The Y-T graticule, with the gutter the lane names need when stacked.
inline Plot ytPlot(double w, double h, bool stacked, double widestName) {
  double gutter = kPadLeft;
  if (stacked) gutter = std::fmin(std::fmax(kPadLeft, std::ceil(widestName) + 16), jsRound(w * 0.22));
  return { gutter, kPadTop, std::fmax(1.0, w - gutter - kPadRight), std::fmax(1.0, h - kPadTop - kPadBottom) };
}

// drawXY's walk: one figure, or one per layer while the source asks and the
// lag has not taken the lanes.
inline void walkXY(Beam& beam, Phosphor& phosphor, const View& v, const Screen& s, const Frame& f,
                   double w, double h, bool lagging, double elapsed) {
  if (f.channels.empty()) return;
  const double size = std::fmax(40.0, std::fmin(w - 2 * kPadRight, h - 2 * kPadTop));
  const double cx = w / 2, cy = h / 2, radius = size / 2;
  const Plot plot { cx - radius, cy - radius, size, size };

  const auto exists = [&](int ch) { return ch >= 0 && static_cast<std::size_t>(ch) < v.channels.size(); };
  std::vector<Figure> figures { s.xyPair };
  if (!lagging && !s.figures.empty()) {
    bool all = true;
    for (const auto& fig : s.figures) all = all && exists(fig.x) && exists(fig.y);
    if (all) figures = s.figures;
  }

  const double ratio = s.beamXY ? beamRatio(s.beam) : 0;
  for (std::size_t figure = 0; figure < figures.size(); figure++) {
    const int fx = figures[figure].x, fy = figures[figure].y;
    const auto lane = [&](int ch) -> const Lane* {
      return ch >= 0 && static_cast<std::size_t>(ch) < f.channels.size() ? &f.channels[static_cast<std::size_t>(ch)] : nullptr;
    };
    const Lane& left = lane(fx) ? *lane(fx) : f.channels[0];
    const Lane& right = lane(fy) ? *lane(fy) : f.channels.size() > 1 ? f.channels[1] : left;
    const double gainX = gainOf(v, fx), gainY = gainOf(v, fy);
    const double offX = exists(fx) ? v.channels[static_cast<std::size_t>(fx)].offset : 0;
    const double offY = exists(fy) ? v.channels[static_cast<std::size_t>(fy)].offset : 0;

    const std::size_t points = std::min(left.size(), right.size());
    const std::size_t stride = std::max<std::size_t>(1, static_cast<std::size_t>(std::ceil(static_cast<double>(points) / kBeamMax)));
    const double scale = radius * s.zoom;

    // Turned only when the capture has not already, and only on the shaped side.
    const double spin = f.turned || !v.shaping ? 0 : v.rotate + v.rotateMod;
    const double angle = spin * 2 * 3.14159265358979323846;
    const double rc = std::cos(angle), rs = std::sin(angle);
    const bool turning = spin != 0;

    std::size_t n = 0;
    for (std::size_t i = 0; i < points && n < kBeamMax; i += stride, n++) {
      const double l = left[i], r = right[i];
      const double rx = turning ? l * rc - r * rs : l;
      const double ry = turning ? l * rs + r * rc : r;
      beam.put(n, cx + (rx * gainX + offX) * scale, cy - (ry * gainY + offY) * scale);
    }

    if (ratio > 0) {
      beam.shade(figure == 0 ? "xy" : "xy" + std::to_string(figure), n, elapsed, ratio);
      beam.deposit(phosphor, plot, n, true);
    } else {
      beam.deposit(phosphor, plot, n, false);
    }
  }
}

// drawMain's Y-T walk: each lane on, in its band when stacked.
inline void walkYT(Beam& beam, Phosphor& phosphor, const View& v, const Screen& s, const Frame& f,
                   const Plot& plot, int lanes, double elapsed) {
  const bool isStack = s.stack && lanes > 2;
  const double bandH = isStack ? plot.h / lanes : plot.h;
  const auto bandY = [&](std::size_t index) { return plot.y + (isStack ? static_cast<double>(index) * bandH : 0); };
  const auto yAt = [&](std::size_t index, double value) { return bandY(index) + (1 - (value + 1) / 2) * bandH; };

  // The magnifier: a slice of the record about the trigger point.
  const double visible = std::fmax(16.0, jsRound(f.length / s.zoom));
  const double from = std::fmax(0.0, std::fmin(f.length - visible, jsRound(f.pre - visible / 2)));
  const double ratio = s.beamYT && f.triggered ? beamRatio(s.beam) : 0;

  for (std::size_t index = 0; index < f.channels.size(); index++) {
    if (static_cast<int>(index) >= lanes || index >= v.channels.size() || !v.channels[index].on) continue;
    const Lane& samples = f.channels[index];
    // Past the end reads as the page's `undefined`: no bar, and a point that is not a number.
    const auto at = [&](double i) {
      return i >= 0 && i < static_cast<double>(samples.size()) ? static_cast<double>(samples[static_cast<std::size_t>(i)]) : NAN;
    };
    const double gain = gainOf(v, static_cast<int>(index));
    const double offset = v.channels[index].offset;
    const double n = visible;
    const double perPixel = n / plot.w;

    if (perPixel > 2) {
      // Peak detect: each column's own range, one bar, at full ink.
      for (double px = 0; px < plot.w; px++) {
        const double start = from + std::floor(px * perPixel);
        const double stop = from + std::fmin(n, std::floor((px + 1) * perPixel));
        double lo = HUGE_VAL, hi = -HUGE_VAL;
        for (double i = start; i < stop; i++) {
          const double value = at(i);
          if (value < lo) lo = value;
          if (value > hi) hi = value;
        }
        if (lo == HUGE_VAL) continue;
        const double x = plot.x + px;
        phosphor.segment(plot, x, yAt(index, hi * gain + offset), x, yAt(index, lo * gain + offset), 1);
      }
      continue;
    }
    const double across = n - 1 != 0 ? n - 1 : 1;
    if (ratio > 0 && n <= static_cast<double>(kBeamMax)) {
      const std::size_t count = static_cast<std::size_t>(n);
      for (std::size_t i = 0; i < count; i++) {
        beam.put(i, plot.x + (static_cast<double>(i) / across) * plot.w, yAt(index, at(from + static_cast<double>(i)) * gain + offset));
      }
      // One anchor per lane: lanes sit at different levels.
      beam.shade("yt" + std::to_string(index), count, elapsed, ratio);
      beam.deposit(phosphor, plot, count, true);
      continue;
    }
    double lastX = 0, lastY = 0;
    for (double i = 0; i < n; i++) {
      const double x = plot.x + (i / across) * plot.w;
      const double y = yAt(index, at(from + i) * gain + offset);
      if (i > 0) phosphor.segment(plot, lastX, lastY, x, y, 1);
      lastX = x; lastY = y;
    }
  }
}

// A frame's deposits, as `drawMain` makes them: the fade first, with the
// canvas, then the walk for the display. Returns the graticule the grid lies
// over, which is where a reticle's u and v are measured from.
inline Plot drawPicture(Beam& beam, Phosphor& phosphor, const View& v, const Screen& s, const CaptureSource& source,
                        const Frame& f, const Canvas& canvas, double elapsed) {
  if (s.display == "spect") {
    phosphor.blank();
    return {};
  }
  const bool lagging = lagSeconds(v, source) > 0;
  if (s.display == "xy") {
    phosphor.fade(s.persistence, canvas.resized);
    walkXY(beam, phosphor, v, s, f, canvas.w, canvas.h, lagging, elapsed);
    return xyPlot(canvas.w, canvas.h);
  }
  const int lanes = laneCount(v, source);
  const Plot plot = ytPlot(canvas.w, canvas.h, s.stack && lanes > 2, canvas.widestName);
  phosphor.fade(s.persistence, canvas.resized);
  walkYT(beam, phosphor, v, s, f, plot, lanes, elapsed);
  return plot;
}

}  // namespace scope
