// The capture, ported from web/scope.html (stage 4): one frame of what the
// screen draws, from the most recent samples of the source - the window and
// the trigger's search span behind it, coupled, filtered, the lag lane,
// mid and side, turned, and cut at the edge the trigger finds. `capture`,
// `findTriggerIndex`, `filterInPlace`, `biquadCoefficients`,
// `dcBlockerCoefficients`, `filterNow` and the gates they read.
//
// What differs from the page, and why, so nobody goes looking:
//
// - The view's settings are a struct handed in (`View`), where the page reads
//   them from `state` - the timebase, the trigger, the channels' full scales
//   and offsets, the filter, the lag, the turn - and the source is the
//   samples it is asked for and what it says about itself.
// - The automatic lag's lock is handed in, or nothing, where the page keeps
//   it beside the pitch estimator that sets it: that is another piece.
// - The readout's own numbers that capture leaves in `state` (the lag that
//   was used, how short the buffer was) are returned instead.
// - Every lane is a Float32Array in the page, so every sample here is a
//   float, written back the way the page writes it - a filter's output
//   rounded as it is stored, its history carried at full precision.

#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <functional>
#include <optional>
#include <string>
#include <vector>

namespace scope {

using Lane = std::vector<float>;

constexpr int kDivsX = 10, kDivsY = 8;                // DIVS_X, DIVS_Y
constexpr double kMinWindow = 64;                     // MIN_WINDOW
constexpr double kHysteresis = 0.02;                  // HYSTERESIS, of full scale
constexpr double kSearchSeconds = 0.05, kMaxSearchSeconds = 0.2;
constexpr double kLagMaxMs = 40, kLagMinSpanSeconds = kSearchSeconds / 4;
constexpr std::array<double, 9> kTimebase { 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50 };  // ms a division
constexpr double kFullScaleBottom = -50;  // FULL_SCALE_DB's last, its quietest
constexpr int kMaxLanes = 6;
constexpr double kButterworthQDb = -3.0103;
constexpr double kAcCornerMin = 0.5, kAcCornerMax = 20;
constexpr double kMidSideTurns = -0.125, kMidSideFlip = -1;
constexpr int kShapeStride = 8;                       // SHAPE_STRIDE

inline double cutoffHz(double step) { return 20 * std::pow(1000.0, step / 1000); }  // CUTOFF_STEPS a thousand

// A biquad's coefficients, normalised by a0, and a one-pole DC blocker's.
struct Biquad { double b0 = 1, b1 = 0, b2 = 0, a1 = 0, a2 = 0; };

// biquadCoefficients: the cookbook in the form the Web Audio specification
// writes it; Q in decibels for the lowpass and highpass, linear otherwise.
inline Biquad biquadCoefficients(const std::string& type, double hz, double q, double rate) {
  const double nyquist = rate / 2;
  const double f0 = std::fmax(1e-4, std::fmin(hz / nyquist, 0.9999));
  const double w0 = 3.14159265358979323846 * f0;
  const double cosw = std::cos(w0), sinw = std::sin(w0);
  const bool decibels = type == "lowpass" || type == "highpass";
  const double linearQ = decibels ? std::pow(10, q / 20) : std::fmax(1e-4, q);
  const double alpha = sinw / (2 * linearQ);
  double b0, b1, b2, a0, a1, a2;
  if (type == "highpass") { b0 = (1 + cosw) / 2; b1 = -(1 + cosw); b2 = b0; a0 = 1 + alpha; a1 = -2 * cosw; a2 = 1 - alpha; }
  else if (type == "bandpass") { b0 = alpha; b1 = 0; b2 = -alpha; a0 = 1 + alpha; a1 = -2 * cosw; a2 = 1 - alpha; }
  else if (type == "notch") { b0 = 1; b1 = -2 * cosw; b2 = 1; a0 = 1 + alpha; a1 = -2 * cosw; a2 = 1 - alpha; }
  else { b0 = (1 - cosw) / 2; b1 = 1 - cosw; b2 = b0; a0 = 1 + alpha; a1 = -2 * cosw; a2 = 1 - alpha; }
  return { b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0 };
}

// dcBlockerCoefficients: the pole that puts the -3 dB point at the corner.
inline Biquad dcBlockerCoefficients(double hz, double rate) {
  const double corner = std::fmax(kAcCornerMin, std::fmin(kAcCornerMax, hz));
  const double r = std::exp(-2 * 3.14159265358979323846 * corner / rate);
  return { 1, -1, 0, -r, 0 };
}

// filterInPlace: over the whole buffer, primed to the steady state its
// first sample would reach, so a constant input is already at its answer.
inline void filterInPlace(Lane& buffer, const Biquad& c) {
  const double first = buffer.empty() ? 0 : buffer[0];
  const double dcGain = (c.b0 + c.b1 + c.b2) / (1 + c.a1 + c.a2);
  double x1 = first, x2 = first, y1 = first * dcGain, y2 = y1;
  for (auto& sample : buffer) {
    const double x0 = sample;
    const double y0 = c.b0 * x0 + c.b1 * x1 + c.b2 * x2 - c.a1 * y1 - c.a2 * y2;
    x2 = x1; x1 = x0;
    y2 = y1; y1 = y0;
    sample = static_cast<float>(y0);
  }
}

// findTriggerIndex: the most recent edge in [minIndex, maxIndex] that has
// travelled back past the hysteresis band since the last and has a quiet
// holdoff before it. Nothing, if there is none.
inline std::optional<std::size_t> findTriggerIndex(const float* x, std::size_t n, double level, bool rising, double hysteresis,
                                                   double minIndex, double maxIndex, double holdoff) {
  const double lo = std::fmax(1, minIndex);
  const double hi = std::fmin(maxIndex, static_cast<double>(n) - 1);
  if (hi < lo) return std::nullopt;
  std::vector<std::size_t> crossings;
  for (std::size_t i = 1; i < n; i++) {
    const double p = x[i - 1], c = x[i];
    if (rising ? (p < level && c >= level) : (p > level && c <= level)) crossings.push_back(i);
  }
  if (crossings.empty()) return std::nullopt;
  std::vector<std::size_t> qualified = crossings;
  if (hysteresis > 0) {
    const double arm = rising ? level - hysteresis : level + hysteresis;
    std::vector<long> lastArmed(n);
    long seen = -1;
    for (std::size_t i = 0; i < n; i++) {
      if (rising ? x[i] < arm : x[i] > arm) seen = static_cast<long>(i);
      lastArmed[i] = seen;
    }
    qualified.clear();
    long fired = -1;
    for (const std::size_t at : crossings) {
      if (lastArmed[at - 1] > fired) { fired = static_cast<long>(at); qualified.push_back(at); }
    }
    if (qualified.empty()) return std::nullopt;
  }
  std::vector<std::size_t> usable;
  if (holdoff > 0) {
    for (std::size_t k = 0; k < qualified.size(); k++) {
      if (k == 0 || static_cast<double>(qualified[k] - qualified[k - 1]) >= holdoff) usable.push_back(qualified[k]);
    }
  } else {
    usable = qualified;
  }
  for (std::size_t k = usable.size(); k-- > 0;) {
    if (static_cast<double>(usable[k]) >= lo && static_cast<double>(usable[k]) <= hi) return usable[k];
  }
  return std::nullopt;
}

// The view's settings the capture reads, as the page's `state` holds them.
struct View {
  int timebase = 4;
  double position = 0.1, positionMod = 0, holdoffMs = 0;
  double level = 0;    // the trigger's level, a fraction of full scale
  bool rising = true;  // and its edge
  int trigSource = 0;
  double acHz = 5;
  struct Channel { bool on = true, ac = false; double fsDb = 0, fsMod = 0, offset = 0; };
  std::vector<Channel> channels { Channel {}, Channel {} };
  struct Filter { bool on = false; std::string type = "lowpass"; double cutoff = 1000, res = 0; } filter;
  double cutoffMod = 0, resMod = 0;
  bool lagOn = false, lagAuto = false;
  double lagMs = 0, lagMod = 0;
  std::optional<double> lagLock;  // the automatic lag's, in seconds, when it has one
  bool midSide = false;
  double rotate = 0, rotateMod = 0;
  bool shaping = true;     // analyseAt === "post"
  bool measurePost = false;  // measureAt === "post"
};

// What the source says about itself.
struct CaptureSource {
  double rate = 48000;
  double capacity = HUGE_VAL;  // Infinity, when it has no limit
  int channels = 2;
  bool lanes = false;           // a rack, or a band split: lanes of its own
  // getLatestWindow: the most recent n samples of each channel.
  std::function<std::vector<Lane>(std::size_t)> latest;
};

inline double fullScaleDb(const View& v, int ch) {
  if (ch < 0 || static_cast<std::size_t>(ch) >= v.channels.size()) return 0;
  const auto& lane = v.channels[static_cast<std::size_t>(ch)];
  return std::fmax(kFullScaleBottom, std::fmin(0.0, lane.fsDb + lane.fsMod));
}
inline double gainOf(const View& v, int ch) { return std::pow(10, -fullScaleDb(v, ch) / 20); }
inline double windowMs(const View& v) { return kTimebase[static_cast<std::size_t>(v.timebase)] * kDivsX; }

// lagSeconds: how far back the lag lane reaches; nought with mid and side, or a source of lanes.
inline double lagSeconds(const View& v, const CaptureSource& s) {
  if (!v.lagOn || v.midSide) return 0;
  if (s.lanes) return 0;
  if (!v.lagAuto || !v.lagLock) return std::fmax(0.0, v.lagMs + v.lagMod) / 1000;
  return *v.lagLock;
}
inline int laneCount(const View& v, const CaptureSource& s) {
  return lagSeconds(v, s) > 0 ? 2 : std::max(1, std::min(kMaxLanes, s.channels));
}
inline bool rotatesSignal(const View& v, const CaptureSource& s) {
  return s.channels == 2 && !s.lanes && !(lagSeconds(v, s) > 0) && laneCount(v, s) == 2;
}

// filterNow: the filter as set, after whatever is pointed at it.
struct FilterNow { std::string type; double hz, q; };
inline FilterNow filterNow(const View& v) {
  const double step = std::fmax(0.0, std::fmin(1000.0, v.filter.cutoff + v.cutoffMod));
  const double res = std::fmax(0.0, std::fmin(100.0, v.filter.res + v.resMod));
  const bool decibels = v.filter.type == "lowpass" || v.filter.type == "highpass";
  return { v.filter.type, cutoffHz(step), decibels ? kButterworthQDb + res / 100 * 27 : 0.5 + res / 100 * 19.5 };
}

// One frame, as `capture` returns it.
struct Frame {
  std::vector<Lane> channels, signal;
  bool turned = false, triggered = false;
  double shapedAc = 0, shapedFilter = 0;
  double levelAt = 0, asked = 0, capacity = 0, rate = 0, length = 0, pre = 0;
  double lagActual = 0, starved = 0;  // what the page leaves in state for the readout
  const std::vector<Lane>& measured(const View& v) const { return v.measurePost ? channels : signal; }
};

inline double strayBetween(const Lane& a, const Lane& b, double from, double count, int stride) {
  double worst = 0;
  for (double i = from; i < from + count; i += stride) {
    const double gap = std::fabs(static_cast<double>(a[static_cast<std::size_t>(i)]) - b[static_cast<std::size_t>(i)]);
    if (gap > worst) worst = gap;
  }
  return worst;
}

inline Frame capture(const View& v, const CaptureSource& source) {
  const double rate = source.rate;
  const double capacity = source.capacity;
  const double length = std::fmax(kMinWindow, std::round(windowMs(v) * rate / 1000));
  const double where = std::fmax(0.0, std::fmin(1.0, v.position + v.positionMod));
  const double pre = std::round(where * length);
  double span = std::fmin(std::fmax(length, std::round(kSearchSeconds * rate)), std::round(kMaxSearchSeconds * rate));
  double tau = std::fmin(lagSeconds(v, source), kLagMaxMs / 1000) * rate;
  double lead = std::ceil(tau);
  const double room = capacity - length;
  if (room - lead < std::round(kLagMinSpanSeconds * rate)) { tau = 0; lead = 0; }
  span = std::fmax(0.0, std::fmin(span, room - lead));
  Frame frame;
  frame.lagActual = tau / rate * 1000;
  frame.starved = std::fmax(0.0, length - capacity);

  const std::vector<Lane> raw = source.latest(static_cast<std::size_t>(length + span + lead));
  // AC coupling, on the shaped side, over the whole fetch.
  const Biquad ac = dcBlockerCoefficients(v.acHz, rate);
  std::vector<Lane> full = raw;
  std::vector<bool> copied(raw.size(), false);  // the page's "a new array", against its own handed back
  for (std::size_t i = 0; i < raw.size(); i++) {
    if (!v.shaping || i >= v.channels.size() || !v.channels[i].ac) continue;
    filterInPlace(full[i], ac);
    copied[i] = true;
  }
  const int onScreen = laneCount(v, source);
  const int probe = v.trigSource < onScreen && static_cast<std::size_t>(v.trigSource) < v.channels.size()
                    && v.channels[static_cast<std::size_t>(v.trigSource)].on ? v.trigSource : 0;
  const double probeLength = static_cast<std::size_t>(probe) < raw.size() ? static_cast<double>(raw[static_cast<std::size_t>(probe)].size()) : 0;
  const double probeFrom = std::fmax(0.0, probeLength - length);
  const double probeCount = probeLength - probeFrom;
  frame.shapedAc = static_cast<std::size_t>(probe) < raw.size() && copied[static_cast<std::size_t>(probe)]
                   ? strayBetween(full[static_cast<std::size_t>(probe)], raw[static_cast<std::size_t>(probe)], probeFrom, probeCount, kShapeStride) : 0;

  // The filter, each lane on its own after the coupling, over the whole fetch.
  if (v.filter.on && v.shaping) {
    const FilterNow now = filterNow(v);
    const Biquad coefficients = biquadCoefficients(now.type, now.hz, now.q, rate);
    std::vector<float> before;
    const bool probing = probeCount > 0 && static_cast<std::size_t>(probe) < full.size();
    if (probing) {
      for (double i = probeFrom; i < probeFrom + probeCount; i += kShapeStride) before.push_back(full[static_cast<std::size_t>(probe)][static_cast<std::size_t>(i)]);
    }
    for (std::size_t i = 0; i < full.size(); i++) {
      if (static_cast<int>(i) >= onScreen || i >= v.channels.size() || !v.channels[i].on) continue;
      filterInPlace(full[i], coefficients);
    }
    if (probing) {
      std::size_t k = 0;
      for (double i = probeFrom; i < probeFrom + probeCount; i += kShapeStride, k++) {
        const double gap = std::fabs(static_cast<double>(full[static_cast<std::size_t>(probe)][static_cast<std::size_t>(i)]) - before[k]);
        if (gap > frame.shapedFilter) frame.shapedFilter = gap;
      }
    }
  }

  // Everything downstream in the present; the lag lane reads behind it.
  const std::size_t leadN = static_cast<std::size_t>(lead);
  std::vector<Lane> channels;
  for (const auto& b : full) channels.emplace_back(b.begin() + static_cast<std::ptrdiff_t>(std::min(leadN, b.size())), b.end());
  if (tau > 0 && !full.empty()) {
    const Lane& src = full[0];
    const std::size_t n = channels[0].size();
    const double d = lead - tau;
    Lane delayed(n);
    for (std::size_t i = 0; i < n; i++) {
      const double a = src[i];
      delayed[i] = static_cast<float>(a + d * (static_cast<double>(src[i + 1]) - a));
    }
    if (channels.size() < 2) channels.resize(2);
    channels[1] = std::move(delayed);
  }
  // Mid and side: the same rotation at 45 degrees, halved, side flipped.
  if (v.midSide && channels.size() == 2 && source.channels == 2) {
    const double angle = kMidSideTurns * 2 * 3.14159265358979323846;
    const double cos = std::cos(angle), sin = std::sin(angle), gain = 1 / std::sqrt(2.0);
    const Lane left = channels[0], right = channels[1];
    for (std::size_t i = 0; i < left.size(); i++) {
      channels[0][i] = static_cast<float>((static_cast<double>(left[i]) * cos - static_cast<double>(right[i]) * sin) * gain);
      channels[1][i] = static_cast<float>((static_cast<double>(left[i]) * sin + static_cast<double>(right[i]) * cos) * gain * kMidSideFlip);
    }
  }
  // The turn, before the trigger, so the edge it finds is an edge on the screen.
  const std::vector<Lane> signal = channels;
  const double spin = v.rotate + v.rotateMod;
  frame.turned = v.shaping && spin != 0 && channels.size() == 2 && rotatesSignal(v, source);
  if (frame.turned) {
    const double angle = spin * 2 * 3.14159265358979323846;
    const double cos = std::cos(angle), sin = std::sin(angle);
    const Lane left = channels[0], right = channels[1];
    const std::size_t n = std::min(left.size(), right.size());
    Lane x(n), y(n);
    for (std::size_t i = 0; i < n; i++) {
      x[i] = static_cast<float>(static_cast<double>(left[i]) * cos - static_cast<double>(right[i]) * sin);
      y[i] = static_cast<float>(static_cast<double>(left[i]) * sin + static_cast<double>(right[i]) * cos);
    }
    channels[0] = std::move(x);
    channels[1] = std::move(y);
  }
  // The level is a fraction of full scale, made a voltage here, per capture.
  const double gain = gainOf(v, v.trigSource);
  frame.levelAt = v.level / gain;
  const double holdoff = std::round(v.holdoffMs * rate / 1000);
  const Lane& watched = v.trigSource >= 0 && static_cast<std::size_t>(v.trigSource) < channels.size()
                        ? channels[static_cast<std::size_t>(v.trigSource)] : channels[0];
  const auto at = findTriggerIndex(watched.data(), watched.size(), frame.levelAt, v.rising, kHysteresis / gain,
                                   pre, pre + span, holdoff);
  const double total = length + span;
  const double from = at ? static_cast<double>(*at) - pre : total - length;
  const auto cut = [&](const std::vector<Lane>& list) {
    std::vector<Lane> out;
    for (const auto& b : list) {
      const std::size_t a = static_cast<std::size_t>(std::fmin(std::fmax(0.0, from), static_cast<double>(b.size())));
      const std::size_t e = static_cast<std::size_t>(std::fmin(std::fmax(0.0, from + length), static_cast<double>(b.size())));
      out.emplace_back(b.begin() + static_cast<std::ptrdiff_t>(a), b.begin() + static_cast<std::ptrdiff_t>(std::max(a, e)));
    }
    return out;
  };
  frame.channels = cut(channels);
  frame.signal = frame.turned ? cut(signal) : frame.channels;
  frame.triggered = at.has_value();
  frame.asked = length + span + lead;
  frame.capacity = capacity;
  frame.rate = rate;
  frame.length = length;
  frame.pre = pre;
  return frame;
}

}  // namespace scope
