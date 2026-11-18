// The drawn envelope's shape (MSEG, 18 Nov): its text, parsed once into
// segments, and the curve law its segments are played by. mseg.h is the
// engine that plays it and says what it is; this half is apart only because
// the envelope's tone (envelope.h) carries a shape, and the engine reads the tone.

#pragma once

#include <array>
#include <cmath>
#include <cstdint>
#include <string_view>

#include "scope/chars.h"

namespace scope {

// The five stretches, in the order they play, each its knob.
enum MsegStretch : std::uint8_t { kMsegDelay, kMsegAttack, kMsegHold, kMsegDecay, kMsegRelease, kMsegStretches };
// At most this many points drawn inside an envelope's stretches: the design's
// worst case, a string under 600 characters.
constexpr int kMsegMaxInner = 32;
constexpr int kMsegMaxSegments = kMsegMaxInner + kMsegStretches;
constexpr double kMsegReach = 0.2;  // the old envelope's kReach: its aim a fifth past each end

struct MsegBend {
  char law = 'l';  // 'm' midpoint, 'p' aim past the end by the fall, 'a' by full scale, 'l' straight
  double v = 0;
};
/* The aim's distance past the end, as a share of the drawn fall, for a
   midpoint: positive the aim beyond the end (quick to start), negative behind
   the start (slow to start), and none (infinite) for straight. */
inline double msegRho(double m) {
  const double k = 2 * std::log(m / (1 - m));
  if (std::fabs(k) < 1e-9) return HUGE_VAL;
  return 1 / (std::exp(k) - 1);
}

// One segment of a shape: the stretch it is in, its share of that stretch's
// time, where it ends (silence, the peak, the Sustain knob's level, or its
// own drawn level) and its bend.
struct MsegSegment {
  enum End : std::uint8_t { Zero, Peak, Sustain, Drawn };
  std::uint8_t stretch = kMsegAttack;
  End end = Zero;
  double share = 1;
  double level = 0;
  MsegBend bend;
};

/* A shape parsed once into its segments, shared by every voice of a hand.
   Fixed in size, so a setup arriving on the audio thread (a host's program
   change, the plugin's state) parses into it without allocating. */
struct MsegShape {
  std::array<MsegSegment, kMsegMaxSegments> seg {};
  int count = 0;
  int sustainPt = -1;   // the point it holds at; -1 none, a one-shot
  int loopPt = -1;      // the point a loop goes back to while held, or none
  int decayEndPt = 0;   // the decay's end, where the sustain is unless moved
  std::uint32_t serial = 0;  // bumped on every parse, so a voice playing it sees it change
  // Each stretch's inner points, as given, for the face and the morph.
  std::array<int, kMsegStretches> inner {};

  MsegShape() { legacy(); }

  // The old envelope's: straight delay and hold, the attack and decay aimed a
  // fifth of their fall past their ends, the release 0.2 of full scale under silence.
  void legacy() {
    count = 0;
    inner.fill(0);
    for (int s = 0; s < kMsegStretches; s++) {
      MsegSegment& g = seg[static_cast<std::size_t>(count++)];
      g = MsegSegment();
      g.stretch = static_cast<std::uint8_t>(s);
      g.end = anchorEnd(s);
      g.bend = s == kMsegAttack || s == kMsegDecay ? MsegBend { 'p', kMsegReach }
             : s == kMsegRelease ? MsegBend { 'a', kMsegReach } : MsegBend { 'l', 0 };
    }
    decayEndPt = 4;
    sustainPt = 4;
    loopPt = -1;
  }

  static MsegSegment::End anchorEnd(int s) {
    return s == kMsegAttack || s == kMsegHold ? MsegSegment::Peak : s == kMsegDecay ? MsegSegment::Sustain : MsegSegment::Zero;
  }

  /* The text into this shape; false, and the old envelope's shape, where it
     does not read. Empty is the old envelope's too: the design keeps an empty
     shape's meaning free (the decode pass writes every old setup's out in
     full), so a new sound's default bends can be chosen by ear later. */
  bool assign(std::string_view text) {
    const std::uint32_t was = serial;
    const bool ok = parse(text);
    if (!ok) legacy();
    serial = was + 1;
    return ok;
  }

  int points() const { return count + 1; }
  bool oneShot() const { return sustainPt < 0; }

 private:
  static bool number(std::string_view t, double& out) {
    if (t.empty() || t.size() > 24) return false;
    for (const char c : t)
      if (!((c >= '0' && c <= '9') || c == '.' || c == '-' || c == 'e' || c == 'E' || c == '+')) return false;
    out = readDouble(t);
    return std::isfinite(out);
  }
  static bool bendOf(std::string_view t, MsegBend& out) {
    if (t == "l") { out = { 'l', 0 }; return true; }
    if (t.size() < 2 || (t[0] != 'm' && t[0] != 'p' && t[0] != 'a')) return false;
    double v = 0;
    if (!number(t.substr(1), v)) return false;
    if (t[0] == 'm') v = std::fmax(0.1, std::fmin(0.9, v));
    else v = std::fmax(1e-4, std::fmin(100.0, v));
    out = { t[0], v };
    return true;
  }
  static int letter(char c) {
    return c == 'W' ? kMsegDelay : c == 'A' ? kMsegAttack : c == 'H' ? kMsegHold : c == 'D' ? kMsegDecay : c == 'R' ? kMsegRelease : -1;
  }

  bool parse(std::string_view text) {
    if (text.empty()) return false;
    struct Inner { double u, level; MsegBend bend; };
    std::array<std::array<Inner, kMsegMaxInner>, kMsegStretches> pts {};
    std::array<int, kMsegStretches> n {};
    std::array<MsegBend, kMsegStretches> close {};
    std::array<bool, kMsegStretches> seen {};
    int total = 0, loop = -1, sustain = -2;  // -2: where it always is
    std::size_t at = text.find(';');
    if (text.substr(0, at) != "1") return false;
    while (at != std::string_view::npos) {
      const std::size_t next = text.find(';', at + 1);
      const std::string_view block = text.substr(at + 1, next == std::string_view::npos ? std::string_view::npos : next - at - 1);
      at = next;
      if (block.empty()) return false;
      if (block[0] == 'L' || block[0] == 'S') {
        if (block == "S-") { sustain = -1; continue; }
        double v = 0;
        if (!number(block.substr(1), v) || v < 0 || v != std::floor(v) || v > kMsegMaxSegments) return false;
        (block[0] == 'L' ? loop : sustain) = static_cast<int>(v);
        continue;
      }
      const int s = letter(block[0]);
      if (s < 0 || seen[static_cast<std::size_t>(s)]) return false;
      seen[static_cast<std::size_t>(s)] = true;
      const std::size_t gt = block.find('>');
      if (gt == std::string_view::npos) return false;
      if (!bendOf(block.substr(gt + 1), close[static_cast<std::size_t>(s)])) return false;
      std::string_view list = block.substr(1, gt - 1);
      // The inner points, three numbers a point.
      double prevU = 0;
      std::string_view f[3];
      int k = 0;
      while (!list.empty()) {
        const std::size_t comma = list.find(',');
        f[k++] = list.substr(0, comma);
        list = comma == std::string_view::npos ? std::string_view() : list.substr(comma + 1);
        if (comma != std::string_view::npos && list.empty()) return false;  // a trailing comma
        if (k < 3) continue;
        k = 0;
        Inner p {};
        if (!number(f[0], p.u) || !number(f[1], p.level) || !bendOf(f[2], p.bend)) return false;
        if (total >= kMsegMaxInner) return false;
        p.u = std::fmax(prevU, std::fmin(1.0, p.u));
        p.level = std::fmax(0.0, std::fmin(1.0, p.level));
        prevU = p.u;
        pts[static_cast<std::size_t>(s)][static_cast<std::size_t>(n[static_cast<std::size_t>(s)]++)] = p;
        total++;
      }
      if (k != 0) return false;
    }
    // Into segments, stretch by stretch: the inner points, then the anchor.
    count = 0;
    for (int s = 0; s < kMsegStretches; s++) {
      const std::size_t si = static_cast<std::size_t>(s);
      inner[si] = n[si];
      double u0 = 0;
      for (int k = 0; k < n[si]; k++) {
        const Inner& p = pts[si][static_cast<std::size_t>(k)];
        MsegSegment& g = seg[static_cast<std::size_t>(count++)];
        g.stretch = static_cast<std::uint8_t>(s); g.end = MsegSegment::Drawn; g.level = p.level;
        g.share = p.u - u0; g.bend = p.bend;
        u0 = p.u;
      }
      MsegSegment& g = seg[static_cast<std::size_t>(count++)];
      g.stretch = static_cast<std::uint8_t>(s); g.end = anchorEnd(s); g.level = 0;
      // The last segment's share: exactly one with no points inside, so the
      // old envelope's arithmetic is the same to the bit.
      g.share = n[si] == 0 ? 1.0 : 1.0 - u0;
      g.bend = seen[si] ? close[si] : MsegBend { 'l', 0 };
      if (s == kMsegDecay) decayEndPt = count;
    }
    const int last = count;  // the end point: nothing can hold there
    sustainPt = sustain == -2 ? decayEndPt : sustain == -1 ? -1 : (sustain >= 1 && sustain < last ? sustain : decayEndPt);
    loopPt = loop >= 0 && sustainPt > 0 && loop < sustainPt ? loop : -1;
    return true;
  }
};

/* The level a shape's point is drawn at: the start, an anchor or a drawn one. */
inline double msegPointLevel(const MsegShape& shape, int pt, double sustain) {
  if (pt <= 0) return 0;
  const MsegSegment& g = shape.seg[static_cast<std::size_t>(pt - 1)];
  return g.end == MsegSegment::Peak ? 1 : g.end == MsegSegment::Sustain ? sustain : g.end == MsegSegment::Drawn ? g.level : 0;
}

/* The aim of a segment drawn from a to b, by its bend; false for straight.
   The old release's aim is in full scale, so it holds even for a stretch
   drawn flat at silence (a sustain of nought), which the old envelope still
   travels down from wherever the key let it go. Written so the old
   envelope's three aims come out of the same operations its own did:
   1 + 0.2, sus - 0.2 * (1 - sus) and -0.2. */
inline bool msegAim(double a, double b, const MsegBend& bend, double& aim) {
  if (bend.law == 'l') return false;
  if (bend.law == 'a') { aim = b > a ? b + bend.v : b - bend.v; return true; }
  if (bend.law == 'p') { aim = b - bend.v * (a - b); return true; }
  if (a == b) return false;  // a drawn midpoint on a flat stretch is a flat stretch
  const double rho = msegRho(bend.v);
  if (!std::isfinite(rho)) return false;
  aim = b - rho * (a - b);
  return true;
}

}  // namespace scope
