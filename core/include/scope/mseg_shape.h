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
// Room for the longest shape's text and its terminator.
constexpr std::size_t kMsegTextRoom = 640;
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

/* A shape's text read as it is written: each stretch's inner points and its
   closing bend, the loop and the sustain point (-2 where it always is, -1
   none), with what does not stand checked out - the page's msegParse, rule
   for rule. What the morph walks (msegBlend) and writes back (msegWrite);
   MsegShape is made from it. Fixed in size, so neither allocates. */
struct MsegDraft {
  struct Inner { double u = 0, level = 0; MsegBend bend; };
  std::array<std::array<Inner, kMsegMaxInner>, kMsegStretches> pts {};
  std::array<int, kMsegStretches> n {};
  std::array<MsegBend, kMsegStretches> close {};
  int loop = -1, sustain = -2;
  int total() const { int t = 0; for (const int k : n) t += k; return t; }
  int decayEnd() const { return n[0] + n[1] + n[2] + n[3] + 4; }
};
namespace mseg_detail {
inline bool number(std::string_view t, double& out) {
  if (t.empty() || t.size() > 24) return false;
  for (const char c : t)
    if (!((c >= '0' && c <= '9') || c == '.' || c == '-' || c == 'e' || c == 'E' || c == '+')) return false;
  out = readDouble(t);
  return std::isfinite(out);
}
inline bool bendOf(std::string_view t, MsegBend& out) {
  if (t == "l") { out = { 'l', 0 }; return true; }
  if (t.size() < 2 || (t[0] != 'm' && t[0] != 'p' && t[0] != 'a')) return false;
  double v = 0;
  if (!number(t.substr(1), v)) return false;
  if (t[0] == 'm') v = std::fmax(0.1, std::fmin(0.9, v));
  else v = std::fmax(1e-4, std::fmin(100.0, v));
  out = { t[0], v };
  return true;
}
inline int letter(char c) {
  return c == 'W' ? kMsegDelay : c == 'A' ? kMsegAttack : c == 'H' ? kMsegHold : c == 'D' ? kMsegDecay : c == 'R' ? kMsegRelease : -1;
}
}  // namespace mseg_detail

// The text into a draft; false for one that does not read (the old envelope's, to whatever reads it).
inline bool msegRead(std::string_view text, MsegDraft& d) {
  using namespace mseg_detail;
  d = MsegDraft();
  if (text.empty()) return false;
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
    if (!bendOf(block.substr(gt + 1), d.close[static_cast<std::size_t>(s)])) return false;
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
      MsegDraft::Inner p {};
      if (!number(f[0], p.u) || !number(f[1], p.level) || !bendOf(f[2], p.bend)) return false;
      if (total >= kMsegMaxInner) return false;
      p.u = std::fmax(prevU, std::fmin(1.0, p.u));
      p.level = std::fmax(0.0, std::fmin(1.0, p.level));
      prevU = p.u;
      d.pts[static_cast<std::size_t>(s)][static_cast<std::size_t>(d.n[static_cast<std::size_t>(s)]++)] = p;
      total++;
    }
    if (k != 0) return false;
  }
  const int last = total + 5;  // the end point: nothing can hold there
  d.sustain = sustain == -1 ? -1 : sustain >= 1 && sustain < last ? sustain : -2;
  const int susPt = d.sustain == -1 ? -1 : d.sustain == -2 ? d.decayEnd() : d.sustain;
  d.loop = loop >= 0 && susPt > 0 && loop < susPt ? loop : -1;
  return true;
}

/* A draft as its text, the page's msegText character for character: a block
   for each stretch with points or a bend, its numbers to fixed places with
   no trailing noughts or leading nought. Into `out`, which needs room for the
   longest a shape is (640); the length written. */
inline std::size_t msegWrite(const MsegDraft& d, char* out, std::size_t room) {
  std::size_t n = 0;
  const auto put = [&](char c) { if (n + 1 < room) out[n++] = c; };
  const auto num = [&](double x, int places) {
    const double scale = std::pow(10.0, places);
    double r = std::floor(x * scale + 0.5);  // JavaScript's Math.round
    r /= scale;
    char buf[48];
    std::size_t m = writeDouble(buf, sizeof buf, r, std::chars_format::fixed, places);
    if (std::string_view(buf, m).find('.') != std::string_view::npos) {
      while (m > 0 && buf[m - 1] == '0') m--;
      if (m > 0 && buf[m - 1] == '.') m--;
    }
    std::size_t i = 0;
    if (m == 2 && buf[0] == '-' && buf[1] == '0') { put('0'); return; }
    if (buf[0] == '-') { put('-'); i = 1; }
    if (m - i >= 2 && buf[i] == '0' && buf[i + 1] == '.') i++;
    for (; i < m; i++) put(buf[i]);
  };
  const auto bend = [&](const MsegBend& b) {
    put(b.law);
    if (b.law != 'l') num(b.v, b.law == 'm' ? 3 : 4);
  };
  put('1');
  for (int s = 0; s < kMsegStretches; s++) {
    const std::size_t si = static_cast<std::size_t>(s);
    if (d.n[si] == 0 && d.close[si].law == 'l') continue;
    put(';'); put("WAHDR"[s]);
    for (int k = 0; k < d.n[si]; k++) {
      const MsegDraft::Inner& p = d.pts[si][static_cast<std::size_t>(k)];
      if (k) put(',');
      num(p.u, 4); put(','); num(p.level, 5); put(','); bend(p.bend);
    }
    put('>'); bend(d.close[si]);
  }
  const auto whole = [&](int v) { char buf[16]; const std::size_t m = writeDouble(buf, sizeof buf, v, std::chars_format::fixed, 0); for (std::size_t i = 0; i < m; i++) put(buf[i]); };
  if (d.loop >= 0) { put(';'); put('L'); whole(d.loop); }
  if (d.sustain == -1) { put(';'); put('S'); put('-'); }
  else if (d.sustain >= 0) { put(';'); put('S'); whole(d.sustain); }
  out[n] = '\0';
  return n;
}

/* The morph between two shapes at a share t (18 Nov, the owner's rule): with
   as many points in each stretch, each point's share and level walk, and a
   bend of the same kind walks its number; a bend of another kind, the loop
   and the sustain point change at half-way, as the whole shape does when the
   points differ. The page's msegBlend. The text into `out`; its length. */
inline std::size_t msegBlend(std::string_view a, std::string_view b, double t, char* out, std::size_t room) {
  MsegDraft da, db;
  const bool ra = msegRead(a, da), rb = msegRead(b, db);
  const std::string_view half = t < 0.5 ? a : b;
  bool same = ra && rb;
  for (int s = 0; same && s < kMsegStretches; s++) same = da.n[static_cast<std::size_t>(s)] == db.n[static_cast<std::size_t>(s)];
  if (!same) {
    const std::size_t m = half.size() < room ? half.size() : room - 1;
    for (std::size_t i = 0; i < m; i++) out[i] = half[i];
    out[m] = '\0';
    return m;
  }
  const auto walk = [t](double x, double y) { return x + (y - x) * t; };
  const auto bend = [&](const MsegBend& x, const MsegBend& y) { return x.law == y.law ? MsegBend { x.law, walk(x.v, y.v) } : t < 0.5 ? x : y; };
  MsegDraft o = t < 0.5 ? da : db;
  for (int s = 0; s < kMsegStretches; s++) {
    const std::size_t si = static_cast<std::size_t>(s);
    o.close[si] = bend(da.close[si], db.close[si]);
    for (int k = 0; k < da.n[si]; k++) {
      const std::size_t ki = static_cast<std::size_t>(k);
      o.pts[si][ki] = { walk(da.pts[si][ki].u, db.pts[si][ki].u), walk(da.pts[si][ki].level, db.pts[si][ki].level), bend(da.pts[si][ki].bend, db.pts[si][ki].bend) };
    }
  }
  return msegWrite(o, out, room);
}

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
  bool parse(std::string_view text) {
    MsegDraft d;
    if (!msegRead(text, d)) return false;
    const auto& pts = d.pts;
    const auto& n = d.n;
    // Into segments, stretch by stretch: the inner points, then the anchor.
    count = 0;
    for (int s = 0; s < kMsegStretches; s++) {
      const std::size_t si = static_cast<std::size_t>(s);
      inner[si] = n[si];
      double u0 = 0;
      for (int k = 0; k < n[si]; k++) {
        const MsegDraft::Inner& p = pts[si][static_cast<std::size_t>(k)];
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
      g.bend = d.close[si];
      if (s == kMsegDecay) decayEndPt = count;
    }
    sustainPt = d.sustain == -2 ? decayEndPt : d.sustain;
    loopPt = d.loop;
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
