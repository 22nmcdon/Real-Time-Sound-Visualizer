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

// biquadFromLinearQ: the cookbook in the form the Web Audio specification
// writes it, for a Q already linear.
inline Biquad biquadFromLinearQ(const std::string& type, double hz, double linearQ, double rate) {
  const double nyquist = rate / 2;
  const double f0 = std::fmax(1e-4, std::fmin(hz / nyquist, 0.9999));
  const double w0 = 3.14159265358979323846 * f0;
  const double cosw = std::cos(w0), sinw = std::sin(w0);
  const double alpha = sinw / (2 * linearQ);
  double b0, b1, b2, a0, a1, a2;
  if (type == "highpass") { b0 = (1 + cosw) / 2; b1 = -(1 + cosw); b2 = b0; a0 = 1 + alpha; a1 = -2 * cosw; a2 = 1 - alpha; }
  else if (type == "bandpass") { b0 = alpha; b1 = 0; b2 = -alpha; a0 = 1 + alpha; a1 = -2 * cosw; a2 = 1 - alpha; }
  else if (type == "notch") { b0 = 1; b1 = -2 * cosw; b2 = 1; a0 = 1 + alpha; a1 = -2 * cosw; a2 = 1 - alpha; }
  else { b0 = (1 - cosw) / 2; b1 = 1 - cosw; b2 = b0; a0 = 1 + alpha; a1 = -2 * cosw; a2 = 1 - alpha; }
  return { b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0 };
}

// biquadCoefficients: the page's JavaScript biquad's - Q in decibels for the
// lowpass and highpass, linear otherwise, all of it in doubles.
inline Biquad biquadCoefficients(const std::string& type, double hz, double q, double rate) {
  const bool decibels = type == "lowpass" || type == "highpass";
  return biquadFromLinearQ(type, hz, decibels ? std::pow(10, q / 20) : std::fmax(1e-4, q), rate);
}

/* biquadNodeCoefficients: a BiquadFilterNode's own, for a lowpass or a
   highpass, which differ from the page's arithmetic in two roundings: Q is
   an AudioParam, so a float, and the browser works the resonance out of it
   as a float too. Found by trying each rounding against the browser's
   output: with these two the core's band split is Chromium's to the bit,
   and without the second a 120 Hz highpass is two parts in a million away. */
inline Biquad biquadNodeCoefficients(const std::string& type, double hz, double qDb, double rate) {
  const double resonance = static_cast<float>(std::pow(10.0, static_cast<double>(static_cast<float>(qDb)) / 20));
  return biquadFromLinearQ(type, hz, resonance, rate);
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
//
// One pass and no lists (G8): it made four arrays a frame - the crossings,
// those qualified, those usable and a sample-long record of when the signal
// was last armed - on the audio thread, sixty times a second. The page's
// four passes are one here because each list only ever looks back: a
// crossing qualifies by where the signal was last armed before it, which is
// what the pass has seen so far, and is usable by its distance from the last
// one that qualified, and the answer is the last usable one in range. The
// same index comes out, which parity's capture runs hold.
inline std::optional<std::size_t> findTriggerIndex(const float* x, std::size_t n, double level, bool rising, double hysteresis,
                                                   double minIndex, double maxIndex, double holdoff) {
  const double lo = std::fmax(1, minIndex);
  const double hi = std::fmin(maxIndex, static_cast<double>(n) - 1);
  if (hi < lo) return std::nullopt;
  const double arm = rising ? level - hysteresis : level + hysteresis;
  const bool armed = hysteresis > 0;
  long seen = -1, fired = -1;   // the last armed sample before this one, and the last crossing that qualified
  std::optional<std::size_t> previous, found;
  if (n > 0 && (rising ? x[0] < arm : x[0] > arm)) seen = 0;
  for (std::size_t i = 1; i < n; i++) {
    const double p = x[i - 1], c = x[i];
    if (rising ? (p < level && c >= level) : (p > level && c <= level)) {
      bool qualified = true;
      if (armed) {
        qualified = seen > fired;
        if (qualified) fired = static_cast<long>(i);
      }
      if (qualified) {
        const bool usable = !(holdoff > 0) || !previous || static_cast<double>(i - *previous) >= holdoff;
        previous = i;
        if (usable && static_cast<double>(i) >= lo && static_cast<double>(i) <= hi) found = i;
      }
    }
    if (rising ? x[i] < arm : x[i] > arm) seen = static_cast<long>(i);
  }
  return found;
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
  bool lanes = false;           // the band split: lanes of its own
  /* getLatestWindow: the most recent n samples of each channel, written into
     `out` - a lane a channel, each n long - rather than handed back new, so
     a source that keeps `out` from frame to frame, as the capture does,
     allocates nothing once its lanes are as long as it asks (G8). */
  std::function<void(std::size_t n, std::vector<Lane>& out)> latest;
};

// A source written the old way, handing back fresh lanes, as a test harness writes it.
inline std::function<void(std::size_t, std::vector<Lane>&)> latestFrom(std::function<std::vector<Lane>(std::size_t)> make) {
  return [make = std::move(make)](std::size_t n, std::vector<Lane>& out) { out = make(n); };
}

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

// One frame, as `capture` returns it. `signal`, the lanes before the turn,
// is filled only when the frame was turned: otherwise it is `channels`, which
// `signalLanes` answers without a copy of every lane a frame (G8).
struct Frame {
  std::vector<Lane> channels, signal;
  bool turned = false, triggered = false;
  double shapedAc = 0, shapedFilter = 0;
  double levelAt = 0, asked = 0, capacity = 0, rate = 0, length = 0, pre = 0;
  double lagActual = 0, starved = 0;  // what the page leaves in state for the readout
  const std::vector<Lane>& signalLanes() const { return turned ? signal : channels; }
  const std::vector<Lane>& measured(const View& v) const { return v.measurePost ? channels : signalLanes(); }
};

/* What a capture works in, kept from one frame to the next so a steady
   frame allocates nothing (G8): the fetch, coupled and filtered where it
   lies and then cut of its lead, which is the frame's lanes before the turn;
   the lag lane; the turned pair; and the probe's samples before each
   shaping. The page makes every one of these afresh each frame, and so did
   this, on the audio thread - two-thirds of what a block allocated. A source
   that asks for more than the room made grows it, once. */
struct CaptureScratch {
  std::vector<Lane> lanes;
  Lane delayed, turnedX, turnedY;
  std::vector<float> probeRaw, probeBefore;
  // Room for `count` lanes of `samples`, the most a source will ask for.
  void reserve(std::size_t count, std::size_t samples) {
    lanes.resize(count);
    for (auto& lane : lanes) lane.reserve(samples);
    for (Lane* lane : { &delayed, &turnedX, &turnedY }) lane->reserve(samples);
    probeRaw.reserve(samples / kShapeStride + 1);
    probeBefore.reserve(samples / kShapeStride + 1);
  }
};
// The most a capture asks of a source: the longest window, or the source's whole capacity.
inline std::size_t captureMost(double rate, double capacity) {
  const double longest = std::fmax(kMinWindow, std::round(kTimebase.back() * kDivsX * rate / 1000));
  return static_cast<std::size_t>(std::fmax(longest, std::isfinite(capacity) ? capacity : longest) + std::ceil(kLagMaxMs / 1000 * rate));
}
// Room in a frame for `count` lanes of `samples`, both its lists.
inline void reserveFrame(Frame& f, std::size_t count, std::size_t samples) {
  for (auto* list : { &f.channels, &f.signal }) {
    list->resize(count);
    for (auto& lane : *list) lane.reserve(samples);
  }
}

// `list`'s lanes, each cut to [from, from + length), into `out`: the page's
// slices, written over what `out` held.
inline void cutLanes(std::vector<Lane>& out, const std::vector<Lane>& list, std::size_t count, double from, double length) {
  out.resize(count);
  for (std::size_t i = 0; i < count; i++) {
    const Lane& b = list[i];
    const std::size_t a = static_cast<std::size_t>(std::fmin(std::fmax(0.0, from), static_cast<double>(b.size())));
    const std::size_t e = static_cast<std::size_t>(std::fmin(std::fmax(0.0, from + length), static_cast<double>(b.size())));
    out[i].assign(b.begin() + static_cast<std::ptrdiff_t>(a), b.begin() + static_cast<std::ptrdiff_t>(std::max(a, e)));
  }
}

/* One frame into `frame`, working in `scratch`. The page's capture, step for
   step and to the same samples; what differs is only where they are kept.
   The lead is cut from the front of the fetch rather than copied out of it,
   mid and side and the turn work a sample at a time rather than from copies
   of the pair, and the turn writes into its own pair so the fetch is still
   the signal before it. */
inline void captureInto(const View& v, const CaptureSource& source, Frame& frame, CaptureScratch& scratch) {
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
  frame.turned = false;
  frame.triggered = false;
  frame.shapedAc = 0;
  frame.shapedFilter = 0;
  frame.lagActual = tau / rate * 1000;
  frame.starved = std::fmax(0.0, length - capacity);

  std::vector<Lane>& full = scratch.lanes;
  source.latest(static_cast<std::size_t>(length + span + lead), full);
  const std::size_t count = full.size();
  const int onScreen = laneCount(v, source);
  const int probe = v.trigSource < onScreen && static_cast<std::size_t>(v.trigSource) < v.channels.size()
                    && v.channels[static_cast<std::size_t>(v.trigSource)].on ? v.trigSource : 0;
  const std::size_t probeLane = static_cast<std::size_t>(probe);
  const double probeLength = probeLane < count ? static_cast<double>(full[probeLane].size()) : 0;
  const double probeFrom = std::fmax(0.0, probeLength - length);
  const double probeCount = probeLength - probeFrom;
  // The probe's samples as fetched, every eighth, for how far the coupling moved them.
  const auto coupled = [&](std::size_t i) { return v.shaping && i < v.channels.size() && v.channels[i].ac; };
  const auto strided = [&](std::vector<float>& into) {
    into.clear();
    for (double i = probeFrom; i < probeFrom + probeCount; i += kShapeStride) into.push_back(full[probeLane][static_cast<std::size_t>(i)]);
  };
  const bool probeCoupled = probeLane < count && coupled(probeLane);
  if (probeCoupled) strided(scratch.probeRaw);
  // AC coupling, on the shaped side, over the whole fetch.
  const Biquad ac = dcBlockerCoefficients(v.acHz, rate);
  for (std::size_t i = 0; i < count; i++) if (coupled(i)) filterInPlace(full[i], ac);
  if (probeCoupled) {
    std::size_t k = 0;
    for (double i = probeFrom; i < probeFrom + probeCount; i += kShapeStride, k++) {
      const double gap = std::fabs(static_cast<double>(full[probeLane][static_cast<std::size_t>(i)]) - scratch.probeRaw[k]);
      if (gap > frame.shapedAc) frame.shapedAc = gap;
    }
  }

  // The filter, each lane on its own after the coupling, over the whole fetch.
  if (v.filter.on && v.shaping) {
    const FilterNow now = filterNow(v);
    const Biquad coefficients = biquadCoefficients(now.type, now.hz, now.q, rate);
    const bool probing = probeCount > 0 && probeLane < count;
    if (probing) strided(scratch.probeBefore);
    for (std::size_t i = 0; i < count; i++) {
      if (static_cast<int>(i) >= onScreen || i >= v.channels.size() || !v.channels[i].on) continue;
      filterInPlace(full[i], coefficients);
    }
    if (probing) {
      std::size_t k = 0;
      for (double i = probeFrom; i < probeFrom + probeCount; i += kShapeStride, k++) {
        const double gap = std::fabs(static_cast<double>(full[probeLane][static_cast<std::size_t>(i)]) - scratch.probeBefore[k]);
        if (gap > frame.shapedFilter) frame.shapedFilter = gap;
      }
    }
  }

  // Everything downstream in the present; the lag lane reads behind it, so it is made before the lead is cut.
  const std::size_t leadN = static_cast<std::size_t>(lead);
  const bool lagged = tau > 0 && count > 0;
  if (lagged) {
    const Lane& src = full[0];
    const std::size_t n = src.size() - std::min(leadN, src.size());
    const double d = lead - tau;
    Lane& delayed = scratch.delayed;
    delayed.resize(n);
    for (std::size_t i = 0; i < n; i++) {
      const double a = src[i];
      delayed[i] = static_cast<float>(a + d * (static_cast<double>(src[i + 1]) - a));
    }
  }
  for (auto& b : full) b.erase(b.begin(), b.begin() + static_cast<std::ptrdiff_t>(std::min(leadN, b.size())));
  std::vector<Lane>& channels = full;
  if (lagged) {
    if (channels.size() < 2) channels.resize(2);
    channels[1].swap(scratch.delayed);
  }
  const std::size_t lanes = channels.size();
  // Mid and side: the same rotation at 45 degrees, halved, side flipped.
  if (v.midSide && lanes == 2 && source.channels == 2) {
    const double angle = kMidSideTurns * 2 * 3.14159265358979323846;
    const double cos = std::cos(angle), sin = std::sin(angle), gain = 1 / std::sqrt(2.0);
    Lane& left = channels[0];
    Lane& right = channels[1];
    for (std::size_t i = 0; i < left.size(); i++) {
      const double l = left[i], r = right[i];
      left[i] = static_cast<float>((l * cos - r * sin) * gain);
      right[i] = static_cast<float>((l * sin + r * cos) * gain * kMidSideFlip);
    }
  }
  // The turn, before the trigger, so the edge it finds is an edge on the screen; the fetch stays the signal.
  const double spin = v.rotate + v.rotateMod;
  frame.turned = v.shaping && spin != 0 && lanes == 2 && rotatesSignal(v, source);
  if (frame.turned) {
    const double angle = spin * 2 * 3.14159265358979323846;
    const double cos = std::cos(angle), sin = std::sin(angle);
    const Lane& left = channels[0];
    const Lane& right = channels[1];
    const std::size_t n = std::min(left.size(), right.size());
    Lane& x = scratch.turnedX;
    Lane& y = scratch.turnedY;
    x.resize(n); y.resize(n);
    for (std::size_t i = 0; i < n; i++) {
      x[i] = static_cast<float>(static_cast<double>(left[i]) * cos - static_cast<double>(right[i]) * sin);
      y[i] = static_cast<float>(static_cast<double>(left[i]) * sin + static_cast<double>(right[i]) * cos);
    }
  }
  const auto drawn = [&](std::size_t i) -> const Lane& {
    return frame.turned && i < 2 ? (i == 0 ? scratch.turnedX : scratch.turnedY) : channels[i];
  };
  // The level is a fraction of full scale, made a voltage here, per capture.
  const double gain = gainOf(v, v.trigSource);
  frame.levelAt = v.level / gain;
  const double holdoff = std::round(v.holdoffMs * rate / 1000);
  const Lane& watched = v.trigSource >= 0 && static_cast<std::size_t>(v.trigSource) < lanes
                        ? drawn(static_cast<std::size_t>(v.trigSource)) : drawn(0);
  const auto at = findTriggerIndex(watched.data(), watched.size(), frame.levelAt, v.rising, kHysteresis / gain,
                                   pre, pre + span, holdoff);
  const double total = length + span;
  const double from = at ? static_cast<double>(*at) - pre : total - length;
  if (frame.turned) {
    frame.channels.resize(2);
    for (std::size_t i = 0; i < 2; i++) {
      const Lane& b = drawn(i);
      const std::size_t a = static_cast<std::size_t>(std::fmin(std::fmax(0.0, from), static_cast<double>(b.size())));
      const std::size_t e = static_cast<std::size_t>(std::fmin(std::fmax(0.0, from + length), static_cast<double>(b.size())));
      frame.channels[i].assign(b.begin() + static_cast<std::ptrdiff_t>(a), b.begin() + static_cast<std::ptrdiff_t>(std::max(a, e)));
    }
    cutLanes(frame.signal, channels, lanes, from, length);
  } else {
    cutLanes(frame.channels, channels, lanes, from, length);
  }
  frame.triggered = at.has_value();
  frame.asked = length + span + lead;
  frame.capacity = capacity;
  frame.rate = rate;
  frame.length = length;
  frame.pre = pre;
}

// One frame, made afresh: for a caller that keeps nothing between frames.
inline Frame capture(const View& v, const CaptureSource& source) {
  Frame frame;
  CaptureScratch scratch;
  captureInto(v, source, frame, scratch);
  return frame;
}

}  // namespace scope
