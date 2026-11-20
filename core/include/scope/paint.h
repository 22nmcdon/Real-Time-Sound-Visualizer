// Painting, step 1 (web/docs/painting-design.md): the core paints. From the
// sound it decides the brushwork - where each stroke goes, how wide, how wet,
// which hand - and keeps a map of how much paint is where. Scan and the
// Picture amount read that map, when painting is chosen, in place of the
// trace's phosphor.
//
// Four pieces, each swappable without touching the next:
//
//   layout  ->  strokes  ->  paint map  ->  reads
//
// - The layout (`PaintLayout`) says where a brush sounding a pitch is at a
//   time, in the canvas's unit square, and which closed path a note at a
//   pitch reads. It is the only piece that knows the canvas is round. A new
//   layout is a class with those two answers; nothing else changes (the
//   brushwork asks it where, the reads ask it which ring), and
//   core/tests/pieces/painting.py holds that a second layout moves only
//   where paint lands.
// - The brushwork (`PaintBrush`, in `Painter::frame`) turns each sounding
//   voice into a brush: dipped when the note is struck, harder struck deeper;
//   fed while the key is down by the voice's level; spent as it lays; and
//   picking wet paint up off the canvas and carrying it on (the study's
//   pick-up, which its graphics-card test cut). Its width and pressure are
//   the voice's level. Its strokes are the frame's stamps (`stamps()`), which
//   the page will paint the look from in step 2.
// - The map (`PaintMap`) is thickness and wetness per cell, 128 square. Paint
//   dries smoothly, thin paint faster than thick (`dryThin`, `dryThick`: the
//   time to fall to a tenth wet), and fades by its own half-life (`fade`, in
//   seconds: what step 2 shows as Persistence while Paint is chosen). New
//   paint over wet paint mixes into it; over dry paint it covers by its own
//   opacity, as the study's physical paint does.
// - The reads. Each note reads the ring the layout gives its pitch (the round
//   layout: its own radius), the map's thickness there, wet paint a little
//   stronger than dry (`wetRead`), never colour, since the map has none. The
//   Picture amount's three reads come from the map: Glow from wet coverage,
//   Motion from paint being laid, Memory from new paint landing on old.
//   They go through the picture stage as the trace's do, so Responds to,
//   Rise and Fall and Swell work as now (`PictureStage::stepPaint`).
//
// One canvas, a shared map: which hand laid a stroke is kept on the stroke
// for the look and never reaches the map or the reads.
//
// Step 1's parameters are an internal struct with defaults (`PaintParams`),
// not setup fields: the Trace / Paint switch and the setup come in step 2.
// Nothing here allocates once made, and nothing reads a clock: the same
// performance paints the same map, to the bit, on every machine.

#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <vector>

#include "scope/scan.h"   // scanTables, ScanTables, scanBilinear, kScanPoints, kScanReachMost
#include "scope/voices.h"  // Voice

namespace scope {

constexpr int kPaintN = 128;   // the map's cells across: twice the phosphor's, so a semitone is half a cell
constexpr int kPaintBins = 8;  // bristle groups across a brush
constexpr std::size_t kPaintBrushes = 32;  // brushes, and table slots, at once
constexpr std::size_t kPaintStampsMost = 1024;  // a frame's stamps kept for the look

// Step 1's settings, with the owner's starting values (18 Nov).
struct PaintParams {
  double turn = 8;          // the round layout: seconds for one turn, clockwise from the top
  double hole = 1.0 / 3;    // the lowest note's radius over the outermost's: the record's hole
  double outer = 0.47;      // the outermost radius, of the canvas's width
  double dryThin = 2;       // seconds for thin paint to fall to a tenth wet
  double dryThick = 6;      // and a thick stroke's
  double thick = 1;         // the thickness that dries as thick (a loud, loaded stroke lays about this)
  double fade = 16;         // the paint's half-life, seconds: two turns
  double wetRead = 0.4;     // how much stronger fully wet paint reads than dry
  /* How fast paint laid is a full Motion: thickness per cell of the canvas
     per second, for a brush of width one; it is out of this times the width
     (the paint a stroke lays per length grows with its width), so Motion
     reads the playing alike at any width rather than pinning at full on a
     wide brush (19 Nov; the listening page measures it). */
  double motionFull = 0.012;
  /* The brush's base width, over today's (paint-width, 18 Nov): one is the
     width step 2 shipped, a brush one to four cells across by its pressure.
     Internal, for the owner to choose between by ear and eye
     (web/docs/listening/paint-width/); the look draws whatever the stamps
     say, so a wider brush is wider for the sound and the picture alike. */
  double width = 2;
  /* When a note goes on with the last one's stroke (the owner, 19 Nov: "only
     if their tail ends meaningfully interact, or if the sustain is held").
     A hand's next note struck alone takes up the brush of the note it struck
     last - the same stroke, dipped again, gliding to the new pitch - when
     that note still sounds at the strike, its own amp envelope as the
     instrument plays it above `joinFloor` of the peak it reached (key down
     or in its release alike), or while the sustain pedal is down. So a run
     is one line, a long pad's slow melody is one line, and a pluck's is a
     stroke a note, by the sound rather than by the clock. It replaced a
     fixed 0.45 s from strike to strike (18 Nov), which split a pad's slow
     melody and would have joined a quick pluck's. A chord's notes, struck
     together, are strokes of their own either way. `join` false: every note
     a stroke of its own, as step 2 painted (for the renders' comparison). */
  bool join = true;
  double joinFloor = 0.063;  // -24 dB: web/docs/listening/paint-width/ says how it was chosen
  /* Which of the player's controllers the brush hears (step 3), a bit each
     (kPaintHears...): all of them, always, in the instrument. A bit off is
     a null for core/tests/pieces/painting.py - the same performance with
     the brush deaf to that one controller - and nothing else sets it. */
  unsigned hears = 0xf;
  // A null too: every strike marks as one at this impact, whatever its velocity (below nought: by the strike's own).
  double spatterAt = -1;
  /* The hardest strikes (over 0.8 of a full impact) flick a few flecks off the mark's fingers' tips: a variant for the
     owner to choose by eye (20 Nov), off until they do. */
  bool flecks = false;
  // How far the bend's pull reaches, over its default (kPullReach): internal, for the owner to choose between by eye.
  double pullReach = 1;
};

/* The player's controllers on the brush (step 3, the owner's table of 16 Nov,
   revised after listening on 20 Nov): the pedal joins a hand's notes into one
   stroke and does nothing else, the wheel loads the brush from its bottom, the
   bend moves its radius with the pitch and pulls the wet paint the way the
   pitch goes, and aftertouch presses it in. A strike's velocity is its
   spatter, drops thrown off the brush, through the impact `strike` is handed. */
constexpr unsigned kPaintHearsPedal = 1, kPaintHearsWheel = 2, kPaintHearsBend = 4, kPaintHearsPressure = 8;
struct PaintControls {
  bool pedal = false;
  /* The mod wheel, nought to one, or below nought while it has not moved
     since the instrument was made. It rests at the bottom, as a wheel does
     (the owner, 20 Nov): at nought, or never moved, the brush is step 2's to
     the bit, and up from there it only adds - more paint on it, laid
     heavier, pressed harder and wider, spent more slowly - so at the top it
     is plainly a loaded brush against a dry one. Read from its middle, as
     first built, a wheel let fall back to rest painted dry. */
  double wheel = -1;
  double pressure = 0;  // channel pressure, nought to one: the stroke widens and presses in while a key is leaned on
  double bend = 1;      // the pitch bend as a ratio of frequency, as the generator has glided it: Poly's voices' pitches do not carry it
};

// ---- The layout -------------------------------------------------------------

struct PaintPoint { double x = 0.5, y = 0.5; };
// A closed path a note reads: a circle, in the canvas's unit square.
struct PaintRing { double cx = 0.5, cy = 0.5, r = 0.25; };

/* Where strokes land and which ring a note reads. The two answers are all a
   layout gives, so a layout that is not round (the owner expects to revisit
   it, 18 Nov) is a new class here and nothing else: the brushwork, the map,
   the drying and the reads ask only these. A layout whose notes should read
   something other than a circle would widen PaintRing into a path, which the
   reads take point by point already. */
class PaintLayout {
 public:
  virtual ~PaintLayout() = default;
  virtual PaintPoint at(double seconds, double hz) const = 0;
  virtual PaintRing ring(double hz) const = 0;
};

// The piano's range, A0 to C8, as the radius's ends.
constexpr double kPaintLowHz = 27.5, kPaintHighHz = 4186.009044809578;

/* Layered round (the owner, 16 and 18 Nov): time goes clockwise from the top,
   one turn in `turn` seconds, and pitch goes outward on a log scale, A0 a
   third of the way out (the hole, like a record's, so every register's ring
   is long enough to carry a timbre) and C8 at the edge. A held note is an
   arc at its own radius, a chord concentric arcs, a run a line in and out. */
class RoundLayout : public PaintLayout {
 public:
  explicit RoundLayout(const PaintParams& p = {}) : p_(p) {}
  double radius(double hz) const {
    const double h = std::isfinite(hz) && hz > 0 ? hz : kPaintLowHz;
    const double u = std::clamp(std::log2(h / kPaintLowHz) / std::log2(kPaintHighHz / kPaintLowHz), 0.0, 1.0);
    return p_.outer * (p_.hole + (1 - p_.hole) * u);
  }
  PaintPoint at(double seconds, double hz) const override {
    const double th = 2 * kPi * seconds / p_.turn, r = radius(hz);
    return { 0.5 + r * std::sin(th), 0.5 - r * std::cos(th) };
  }
  PaintRing ring(double hz) const override { return { 0.5, 0.5, radius(hz) }; }

 private:
  PaintParams p_;
};

// ---- The map ----------------------------------------------------------------

inline float paintHash(std::uint32_t x) {
  x ^= x >> 16; x *= 0x7feb352dU; x ^= x >> 15; x *= 0x846ca68bU; x ^= x >> 16;
  return static_cast<float>((x & 0xffffff) / double(0xffffff));
}

// The thickness at which paint hides the ground to 1/e: what coverage is out of.
constexpr double kPaintHide = 0.15;

/* Thickness and wetness per cell. Who laid a cell last, and when, is kept so
   a brush does not drag its own stroke (the study's rule: its own paint from
   the last second and a half is the stroke, not something it passes over). */
struct PaintMap {
  static constexpr std::size_t kCells = static_cast<std::size_t>(kPaintN) * kPaintN;
  std::vector<float> thick = std::vector<float>(kCells, 0.0f);
  std::vector<float> wet = std::vector<float>(kCells, 0.0f);
  std::vector<std::int32_t> owner = std::vector<std::int32_t>(kCells, -1);
  std::vector<float> laidAt = std::vector<float>(kCells, -1e9f);
  void clear() {
    std::fill(thick.begin(), thick.end(), 0.0f); std::fill(wet.begin(), wet.end(), 0.0f);
    std::fill(owner.begin(), owner.end(), -1); std::fill(laidAt.begin(), laidAt.end(), -1e9f);
  }
};

// How much of the ground a thickness hides, 1 - exp(-a / hide), from a table
// (a quarter of a hide a step, to eight hides, where it is one to 1/3000).
class PaintCover {
 public:
  PaintCover() { for (int i = 0; i <= kSteps; i++) table_[static_cast<std::size_t>(i)] = 1 - std::exp(-static_cast<double>(i) / kPerHide); }
  double operator()(double a) const {
    if (!(a > 0)) return 0;
    const double x = a / kPaintHide * kPerHide;
    if (x >= kSteps) return 1;
    const int i = static_cast<int>(x);
    const double f = x - i;
    return table_[static_cast<std::size_t>(i)] * (1 - f) + table_[static_cast<std::size_t>(i + 1)] * f;
  }

 private:
  static constexpr int kPerHide = 4, kSteps = 8 * kPerHide;
  std::array<double, kSteps + 1> table_ {};
};

// ---- The brush --------------------------------------------------------------

/* What sounds, as the painter is handed it a frame: a Poly voice, or Mono's
   line or Dyad's pair (step 2), each with its layer (the hand), an id that is
   its own while it sounds - a voice's birth, or the instrument's count of the
   line's notes - its key, its pitch where its glide has got to, its level,
   and whether its key is down. */
struct PaintNote {
  int layer = 0, id = 0, note = 0;
  double hz = 0, level = 0;
  bool held = false;
};
constexpr std::size_t kPaintNotesMost = 64;

struct PaintBrush {
  bool live = false;
  int layer = 0, born = 0, note = 0;
  // Its ink's role in the harmony, look only: 0 the hand's own, 1 related, 2 a clash (the study's mapping).
  int ink = 0;
  std::int32_t serial = 0;           // whose paint a cell is: unique to this brush's life
  double x = 0, y = 0;               // where it is, in cells
  bool placed = false;
  double bornAt = 0, impact = 0;     // when its note was struck, and how hard (velocity times Strike)
  std::array<double, kPaintBins> load {}, share {};
  // Wet paint picked up off the canvas, on the bristles' tips, laid on further along whatever the brush's own load.
  std::array<double, kPaintBins> carry {};
  std::size_t slot = 0;              // its table slot
  // Its stroke taken up by a later note (PaintParams::join): it lays no more, and goes on reading its ring.
  bool handed = false;
  int from = -1;                     // the brush whose stroke it took up, while that one sounds
  double level = 0, peak = 0;        // its voice's level at its last frame, and the most it has reached
  double hz = 0;                     // the pitch it is at: a stroke taken up glides to its new note's
  bool spattered = false;            // its strike's mark laid (step 3), once, the frame it is placed
  // The strike's flare (paintFlareAt): how far it opened, the length of stroke it closes over (cells), how far the brush
  // has gone since it landed, its seed and its clumps; and where it is now.
  double splay = 0, regather = 1, splayNow = 0, travelled = 0;
  std::uint32_t splaySeed = 0;
  unsigned clumps = 0x7f;
};

// What the map says this frame, for the picture stage.
struct PaintReads {
  double cover = 0;      // wet coverage, as the stage's cover: a quarter of the canvas wet and covered is one
  double moved = 0;      // paint being laid, nought to one
  double repaint = 0;    // of the paint laid, the share landing on paint already there (not its own stroke)
  double covered = 0;    // all paint's coverage, a fraction of the canvas: running away past kSaturated
  double laid = 0;       // thickness laid this frame, summed
  double intoWet = 0, ontoDry = 0, ontoBare = 0;  // where it landed, as the study counted
};

/* One stamp of a brush, for the look: the page paints the graphics card's
   picture from these (step 2), so a stamp carries what the study's stroke
   stream carried - where, which way, how wide (in the canvas's widths) and
   how hard, when, how far it moved over its own reach (`per`), its bristle
   groups' loads, and whose it is: the brush (for its own paint, and the
   colour it picks up), the hand, the note and its ink's role. */
struct PaintStamp {
  float x = 0, y = 0, dx = 1, dy = 0, w = 0, p = 0, t = 0, per = 0;
  std::array<float, kPaintBins> load {};
  std::int32_t serial = 0;
  std::uint8_t hand = 0, ink = 0, note = 0;
  /* What it is (step 3): a brush's (kPaintStampBrush), a drop of spatter
     (kPaintStampDrop: `w` its diameter, `dx, dy` the way it flew, `a` its
     length over its width, `b` the seed of its edge, `load` its thickness),
     or the bend's pull (kPaintStampPull: `w, p` the brush's, `dx, dy` the
     way the pitch went, `a` how far the wet paint is drawn in the canvas's
     widths, `b` how much of it). The look draws each kind by the same
     arithmetic the map lays it with. */
  std::uint8_t kind = 0;
  float a = 0, b = 0;
};
constexpr std::uint8_t kPaintStampBrush = 0, kPaintStampDrop = 1, kPaintStampPull = 2, kPaintStampFinger = 3;

/* A drop's shape, in units of its radius: how much of a pixel of side `px`
   (in those units) centred at (`u`, `v`) it covers, nought to one - `v`
   along the way it flew, `u` across. A round head with a smooth, uneven edge
   (four low harmonics, their phases from the seed: surface tension keeps a
   drop's edge rounded, and the higher ones drew it as a cog), and, longer
   than one, a teardrop's tail tapering away from where it was thrown from,
   as a drop that lands at a slant draws one. The edge is a ramp a pixel
   wide, so the look draws it smooth at its own resolution rather than in
   steps (the owner, 20 Nov: a hard inside-or-out test drew every drop as a
   cluster of square pixels). The look's shader (scope.html's paintView,
   dropCover) is this, line for line, and the map lays it sampled at the
   look's pixel centres in each cell, at the look's pixel size, so the two
   lay the same paint. */
inline double paintDropCover(double u, double v, double longer, std::uint32_t seed, double rough, double px) {
  const double r = std::sqrt(u * u + v * v), th = std::atan2(u, v);
  const double p1 = 2 * kPi * paintHash(seed * 7u + 1u), p2 = 2 * kPi * paintHash(seed * 7u + 2u), p3 = 2 * kPi * paintHash(seed * 7u + 3u);
  const double p4 = 2 * kPi * paintHash(seed * 7u + 4u);
  const double edge = 1 + rough * (0.10 * std::cos(2 * th + p1) + 0.07 * std::cos(3 * th + p2) + 0.05 * std::cos(4 * th + p3) +
                                   0.04 * std::cos(5 * th + p4));
  double c = std::clamp(0.5 - (r - edge) / px, 0.0, 1.0);
  if (longer > 1.05 && v > 0) {
    const double tail = 2.5 * (longer - 1) + 0.8;
    if (v < tail) c = std::max(c, std::clamp(0.5 - (std::fabs(u) - 0.75 * std::pow(1 - v / tail, 1.3)) / px, 0.0, 1.0));
  }
  return c;
}

/* A hard strike flares the brush (the owner, 20 Nov, after the splay as a
   fan and separate tracks: "When you press into it and then drag the
   stroke, the bristles all follow their lines and then line up again; the
   paint all joins up together and is seamless ... the splays aren't as
   uniform ... the centre of the splay should cascade outward and thin out").
   Flared by `a` (nought: the brush as it always was), the eight bristle
   groups widen from the centre outward - each wider the further out it
   sits, a little irregularly from the seed - and stay side by side, so the
   paint is one mark; inside each group its four bristles take a share of
   their lanes that falls outward (`phi`), so the centre is solid and the
   edges break into separate bristle lines that carry less; and on each side
   one stray bristle reaches past the rest, coming in more slowly (by the
   square root of `a`). Where across the brush `uh` (its half-widths) falls:
   which group, which of its bristles, and how much paint it lays there,
   with a ramp `px` wide at every bristle's edge so the look draws it smooth.
   The look's shader (flareAt) is this, line for line, and the map samples
   it at points in each cell, so both lay the same flare. */
struct PaintFlare {
  int k = -1, bristle = 0;
  double weight = 0, extent = 1;
};
inline PaintFlare paintFlareAt(double uh, double a, std::uint32_t seed, double px) {
  PaintFlare out;
  const bool right = uh >= 0;
  const double x = std::fabs(uh);
  double at = 0, outerS = 0;
  for (int i = 0; i < 4; i++) {
    const int k = right ? 4 + i : 3 - i;
    const double x0 = (2.0 * i + 1) / 8;
    const double s = 2.6 * std::pow(x0, 1.6) * (1 + 0.35 * (paintHash(seed * 29u + static_cast<std::uint32_t>(k) + 1u) * 2 - 1));
    const double h = 0.125 * (1 + a * s);
    if (out.k < 0 && x < at + 2 * h) {
      const double l = (x - at) / h - 1;  // -1 to 1 across the group, outward
      const double lane = (l + 1) / 2 * 4;
      const int j = std::clamp(static_cast<int>(std::floor(lane)), 0, 3);
      const double phi = 1 / (1 + 1.2 * a * s), pl = px / (h / 4);
      // Each bristle its own: thicker or thinner, and off the middle of its lane, as far as its lane's room allows.
      const auto bj = static_cast<std::uint32_t>(k * 4 + j);
      const double pj = std::min(1.0, phi * (0.6 + 0.8 * paintHash(seed * 53u + bj + 7u)));
      const double off = (paintHash(seed * 59u + bj + 13u) - 0.5) * (1 - pj);
      const double cover = std::clamp(0.5 - (std::fabs((lane - j) * 2 - 1 - off) - pj) / pl, 0.0, 1.0);
      out.k = k; out.bristle = right ? j : 3 - j; out.weight = cover / std::sqrt(phi);
    }
    at += 2 * h;
    outerS = s;
  }
  out.extent = at;
  if (out.k < 0 && a > 0) {
    // The stray: past the edge by the square root of the flare, one bristle wide.
    const auto side = static_cast<std::uint32_t>(right ? 1 : 0);
    const double r = paintHash(seed * 43u + side + 3u);
    const double centre = at + std::sqrt(a) * 0.35 * (0.4 + 0.6 * r) * (0.5 + 0.5 * outerS);
    const double half = 0.025 * (1 + a);
    const double cover = r < 0.75 ? std::clamp(0.5 - (std::fabs(x - centre) - half) / px, 0.0, 1.0) : 0.0;
    if (cover > 0) { out.k = right ? 7 : 0; out.bristle = right ? 3 : 0; out.weight = 0.7 * cover; }
    out.extent = centre + half;
  }
  return out;
}

/* A finger of the strike's fan, how much of a pixel of side `px` it covers
   and how much paint it lays there, nought to one: `v` along it from its
   root, `u` across, both in units of its half-width at the root, `len` its
   length in the same. A clump of bristles squeezed out from under the brush:
   square at the root, tapering, five strands each loaded a little differently
   and broken off at its own length (the ragged, dry tip), and drier towards
   the tip. The look's shader (fingerCover) is this, line for line. */
inline double paintFingerCover(double u, double v, double len, std::uint32_t seed, double px) {
  if (v < -0.3 || v > len + px) return 0;
  // Its root is the brush's edge pressed down: square across, a short soft start rather than a disc its width.
  if (v < 0) return std::clamp(0.5 - (std::fabs(u) - 1) / px, 0.0, 1.0) * (1 + v / 0.3);
  const double x = std::min(1.0, v / len), h = 1 - 0.6 * std::pow(x, 1.2);
  const int strand = std::clamp(static_cast<int>(std::floor((u / h + 1) / 2 * 5)), 0, 4);
  const auto si = static_cast<std::uint32_t>(strand);
  const double reach = len * (0.65 + 0.35 * paintHash(seed * 7u + si + 11u));
  const double side = std::clamp(0.5 - (std::fabs(u) - h) / px, 0.0, 1.0), tip = std::clamp(0.5 - (v - reach) / px, 0.0, 1.0);
  return side * tip * (1 - 0.55 * x) * (0.7 + 0.6 * paintHash(seed * 13u + si + 17u));
}

/* One bristle group's smear of the bend's pull: how much paint it lays at a
   pixel of side `px`, nought to one - `s` along the way the pitch went from
   the group's place on the brush, `l` across, both in the group's
   half-widths, `len` the smear's length in the same. The owner, 20 Nov, of
   the pull drawn as fine radial lines: "more of a smear ... a little less
   angular". So it is one band of paint with body, not a haze of lines: its
   density falls smoothly along it, its sides are soft and curve back the way
   the brush came as `bend` says (the brush moves along the ring while it
   pulls, so the smear sweeps), and its far edge feathers out raggedly, each
   of its four bristles' lanes reaching its own length; the bristles are a
   texture inside it, a little more or less paint each. `sharp` from nought
   (a slow bend: wider, softer) to one (a flick: narrower, longer). The look's
   shader (streakCover) is this, line for line. */
inline double paintStreakCover(double l, double s, double len, double bend, double sharp, std::uint32_t seed, double px) {
  if (s < -1 || s > len + 1) return 0;
  const double x = std::clamp(s / len, 0.0, 1.0), lat = l - bend * x * x * len;
  const int j = std::clamp(static_cast<int>(std::floor((lat + 1) / 2 * 4)), 0, 3);
  const auto ji = static_cast<std::uint32_t>(j);
  const double reach = len * (0.6 + 0.4 * paintHash(seed * 7u + ji + 5u)), y = s / reach;
  // The band's half-width: the group's, a little wider for a slow bend, narrowing as the smear thins.
  const double half = (1.05 + 0.25 * (1 - sharp)) * (1 - 0.45 * std::clamp(y, 0.0, 1.0));
  const double edge = std::max(half * 0.35, px);
  const double side = std::clamp((half - std::fabs(lat)) / edge, 0.0, 1.0);
  const double start = std::clamp(0.5 + s / std::max(px, 0.3), 0.0, 1.0);
  const double fade = y >= 1 ? 0.0 : std::pow(1 - y, 2.2);
  const double texture = 0.75 + 0.5 * paintHash(seed * 11u + ji + 9u);
  return side * side * (3 - 2 * side) * start * fade * texture;
}

/* The painter: a layout, the brushes, the map and the reads, stepped once a
   picture frame. Made off the audio thread (its map and its tables are a few
   megabytes), then nothing allocates. */
class Painter {
 public:
  explicit Painter(const PaintParams& p = {}) : p_(p), layout_(std::make_unique<RoundLayout>(p)) {
    for (auto& s : slots_) s.tables = std::make_unique<ScanTables>();
    stamps_.reserve(kPaintStampsMost);
  }
  void setLayout(std::unique_ptr<PaintLayout> layout) { layout_ = std::move(layout); }
  const PaintLayout& layout() const { return *layout_; }
  const PaintParams& params() const { return p_; }
  const PaintMap& map() const { return map_; }
  const PaintReads& reads() const { return reads_; }
  const std::vector<PaintStamp>& stamps() const { return stamps_; }
  std::size_t stampsDropped() const { return dropped_; }
  const std::array<PaintBrush, kPaintBrushes>& brushes() const { return brushes_; }

  /* A note struck, as the keyboard's strike hands it to Scan: its brush, born
     at the next frame, is dipped deeper and presses wider for its first
     moments by `impact` (velocity times the hand's Strike). Kept by note
     until a voice of that note is born or a second has gone. */
  void strike(int note, double impact, int layers, double nowMs) {
    for (auto& s : struck_) {
      if (s.at < 0 || nowMs - s.at > 1000) { s = { note, layers, std::clamp(impact, 0.0, 1.0), nowMs }; return; }
    }
  }

  /* The frame: the map dried and faded over `elapsedMs`, then each sounding
     voice's brush moved from where it was to where the layout puts its pitch
     now, laying paint along the way. `voices[layer]` are the generator's
     pools. */
  void frame(const PaintNote* notes, std::size_t count, double nowMs, double elapsedMs) {
    const double t = nowMs / 1000, dt = std::max(0.0, elapsedMs) / 1000;
    stamps_.clear();
    dropped_ = 0;
    /* The paint dries by the performance's clock, pedal or not (20 Nov): as
       first built the pedal stopped it, and the brush laid on through a
       pluck's silences, which the owner heard as untrue to the sound - the
       paint has to say what was heard, and under the pedal a pluck still
       dies away. The pedal joins its notes into one stroke (brushOf), and
       that is all it does. */
    age(dt, dt);
    // How far the bend has moved since the last frame, in octaves: its pull on the wet paint (stroke).
    bendStep_ = std::log2(controls_.bend / lastBend_);
    lastBend_ = controls_.bend;
    // The lowest note sounding, either hand, which the inks' harmony is judged against (look only).
    int low = 1000;
    for (std::size_t i = 0; i < count; i++) if (notes[i].level > 0) low = std::min(low, notes[i].note);
    for (auto& b : brushes_) b.live = false;  // marked again below for every note still sounding
    // A layer striking more than one note this frame strikes a chord: its notes are strokes of their own.
    std::array<int, 2> fresh {};
    for (std::size_t i = 0; i < count; i++)
      if (notes[i].layer >= 0 && notes[i].layer < 2 && !find(notes[i].layer, notes[i].id)) fresh[static_cast<std::size_t>(notes[i].layer)]++;
    for (std::size_t i = 0; i < count; i++) {
      PaintBrush* b = brushOf(notes[i], t, low, fresh[static_cast<std::size_t>(std::clamp(notes[i].layer, 0, 1))] == 1);
      if (!b) continue;
      b->live = true;
      stroke(*b, notes[i], t, dt);
    }
    // Brushes whose voices are gone let go of their slots.
    for (auto& b : brushes_) {
      if (b.live || !b.serial) continue;
      // The hand's latest stroke, kept as it lifts, so a note struck under the pedal takes it up (PaintParams::join).
      if (!b.handed && b.layer >= 0 && b.layer < 2) {
        PaintBrush& kept = lifted_[static_cast<std::size_t>(b.layer)];
        if (!kept.serial || b.bornAt >= kept.bornAt) { kept = b; kept.from = -1; }
      }
      slots_[b.slot].owner = 0; b.serial = 0;
    }
    measure(dt);
  }

  /* Poly's voices as the painter is handed them: every voice not gone, into
     `out`, which holds kPaintNotesMost; how many. */
  static std::size_t notesOf(std::vector<Voice>* const voices[2], PaintNote* out, std::size_t room, std::size_t at = 0,
                             double bend = 1) {
    for (int layer = 0; layer < 2; layer++) {
      if (!voices[layer]) continue;
      for (const auto& v : *voices[layer]) {
        if (v.gone || at >= room) continue;
        // At the pitch it sounds: a voice's own is its note's, and the bend is the generator's on all of them (step 3).
        out[at++] = { layer, v.born, v.note, (v.hz > 0 ? v.hz : v.freq) * bend, std::clamp(v.env.level(), 0.0, 1.0), v.held };
      }
    }
    return at;
  }

  /* Mono's or Dyad's ring (step 2): the generator plays one table for the
     line or the pair, so it is read off the ring of the lower note's pitch -
     the one its phase runs at - into the brush's slot, avoiding the three
     the layer is playing. Null for none, and while a setup lands. */
  CycleTables* readLine(int layer, int id, double hz, double soft, const CycleTables* a, const CycleTables* b,
                        const CycleTables* c) {
    const PaintBrush* brush = find(layer, id);
    if (!brush) return nullptr;
    field();
    if (!readRing(layout_->ring(hz), soft, points_)) return nullptr;
    CycleTables* into = slots_[brush->slot].tables->fresh(a, b, c);
    return into && scanTables(points_, *into) ? into : nullptr;
  }

  // Clear (step 2): the canvas wiped, as the trace's Clear wipes its grid; the brushes go on.
  void clear() { map_.clear(); lifted_ = {}; }

  // The base width (PaintParams::width), internal: the owner's three to choose between.
  void setWidth(double width) { if (std::isfinite(width) && width > 0) p_.width = width; }

  // The sustain pedal, down or up, as the keyboard has it this frame: a note struck under it goes on with the last one's stroke.
  void setPedal(bool down) { pedal_ = down; }
  /* The player's controllers as the keyboard has them this frame (step 3):
     each one the brush is not to hear (PaintParams::hears, a null's) is
     left at rest. */
  void setControls(const PaintControls& c) {
    controls_ = {};
    if (p_.hears & kPaintHearsPedal) controls_.pedal = c.pedal;
    if (p_.hears & kPaintHearsWheel) controls_.wheel = c.wheel;
    if (p_.hears & kPaintHearsPressure) controls_.pressure = std::clamp(c.pressure, 0.0, 1.0);
    if ((p_.hears & kPaintHearsBend) && std::isfinite(c.bend) && c.bend > 0) controls_.bend = c.bend;
    pedal_ = controls_.pedal;
  }
  const PaintControls& controls() const { return controls_; }

  // The fade, a half-life in seconds, as the setup's paintPersistence sets it (step 2).
  void setFade(double seconds) { if (std::isfinite(seconds) && seconds > 0) p_.fade = seconds; }

  /* Each voice's ring read into a table of its own, through its slot, at the
     layer's Scan: nothing for a layer at no depth or while a setup lands. The
     generator plays each voice's table as it played the layer's. */
  void readRings(std::vector<Voice>* const voices[2], const std::array<double, 2>& depth, double soft, bool frozen) {
    field();
    for (int layer = 0; layer < 2; layer++) {
      if (!voices[layer] || !(depth[static_cast<std::size_t>(layer)] > 0)) continue;
      for (auto& v : *voices[layer]) {
        if (v.gone) continue;
        const PaintBrush* b = find(layer, v.born);
        if (!b) continue;
        v.painted = true;
        if (frozen) continue;
        // The ring at the pitch it sounds, bent with the rest (step 3): the bend moves the brush and what it reads alike.
        const double hz = (v.hz > 0 ? v.hz : v.freq) * controls_.bend;
        if (!readRing(layout_->ring(hz), soft, points_)) continue;
        CycleTables* into = slots_[b->slot].tables->fresh(v.paintTable, v.paintPrev, v.paintNext);
        if (into && scanTables(points_, *into)) v.paintTable = into;
      }
    }
  }

  /* A ring's 256 points (kScanPoints), clockwise from the top: the field (the
     thickness, wet paint stronger) a little across the ring, a quarter, a
     half and a quarter at three radii three quarters of a cell apart, and
     then smoothed along the ring by the Softness - Scan's own, in the
     phosphor's cells, so a Softness reads as round on the paint as on the
     trace. Along rather than across, since across the ring is the next
     register: the trace's blur, applied here, would read a note's
     neighbours a fifth away. False when the ring is off the canvas. */
  bool readRing(const PaintRing& ring, double soft, std::array<double, kScanPoints>& points) const {
    constexpr int N = kPaintN;
    const double r = ring.r * N;
    if (!(r > 0.5)) return false;
    const double across = 0.75;
    for (std::size_t i = 0; i < kScanPoints; i++) {
      const double th = 2 * kPi * static_cast<double>(i) / static_cast<double>(kScanPoints);
      const double s = std::sin(th), c = -std::cos(th);
      double v = 0;
      const double radii[3] = { r - across, r, r + across }, weight[3] = { 0.25, 0.5, 0.25 };
      for (int k = 0; k < 3; k++) {
        v += weight[k] * scanBilinear(field_.data(), N, ring.cx + radii[k] * s / N, ring.cy + radii[k] * c / N);
      }
      raw_[i] = v;
    }
    // The Softness is in the phosphor's cells, half the map's: sigma in points along this ring.
    const double sigma = soft * (static_cast<double>(N) / kPhosphorN) * kScanPoints / (2 * kPi * r);
    if (!(sigma > 1e-3)) { points = raw_; return true; }
    const int reach = std::min(static_cast<int>(kScanPoints / 2), static_cast<int>(std::ceil(3 * sigma)));
    double sum = 0;
    for (int j = -reach; j <= reach; j++) {
      kernel_[static_cast<std::size_t>(j + reach)] = std::exp(-static_cast<double>(j) * j / (2 * sigma * sigma));
      sum += kernel_[static_cast<std::size_t>(j + reach)];
    }
    constexpr int P = static_cast<int>(kScanPoints);
    for (int i = 0; i < P; i++) {
      double v = 0;
      for (int j = -reach; j <= reach; j++) v += kernel_[static_cast<std::size_t>(j + reach)] * raw_[static_cast<std::size_t>(((i + j) % P + P) % P)];
      points[static_cast<std::size_t>(i)] = v / sum;
    }
    return true;
  }

  // The field the rings read: thickness, wet paint stronger by `wetRead`.
  void field() {
    for (std::size_t q = 0; q < PaintMap::kCells; q++) field_[q] = map_.thick[q] * (1 + p_.wetRead * map_.wet[q]);
  }
  const std::vector<double>& fieldCells() const { return field_; }

  // How long a thickness takes to fall to a tenth wet: thin to thick, smoothly.
  double dryTime(double a) const {
    const double x = std::clamp(a / p_.thick, 0.0, 1.0);
    return p_.dryThin + (p_.dryThick - p_.dryThin) * x * x * (3 - 2 * x);
  }

  /* For a harness: paint laid by hand, as a brush would lay it, at a point
     in the unit square - `own` the brush it is as. */
  void lay(double x, double y, double w, double pressure, double load, double t, std::int32_t own = 1 << 30) {
    PaintBrush b;
    b.serial = own; b.live = true;
    b.x = x * kPaintN; b.y = y * kPaintN; b.placed = true;
    b.load.fill(load); b.share.fill(1);
    stamp(b, b.x, b.y, 1, 0, w, pressure, t, 1);
  }
  /* And a brush drawn from one point to another, one brush throughout, so
     what it picks up it carries on: `load` its dip, every bristle group alike. */
  void drag(double x0, double y0, double x1, double y1, double w, double pressure, double load, double t, std::int32_t own) {
    PaintBrush b;
    b.serial = own; b.live = true; b.placed = true;
    b.load.fill(load); b.share.fill(1);
    const double ax = x0 * kPaintN, ay = y0 * kPaintN, dx = (x1 - x0) * kPaintN, dy = (y1 - y0) * kPaintN;
    const double len = std::hypot(dx, dy);
    const int steps = std::max(1, static_cast<int>(std::ceil(len / kSpacing)));
    for (int s = 0; s <= steps; s++) {
      const double f = static_cast<double>(s) / steps;
      stamp(b, ax + dx * f, ay + dy * f, len > 0 ? dx / len : 1, len > 0 ? dy / len : 0, w, pressure, t, len / steps);
    }
  }
  // And the map aged by hand.
  void ageBy(double seconds) { age(seconds, seconds); }
  void measureNow(double seconds) { measure(seconds); }

 private:
  struct Struck { int note = 0, layers = 0; double impact = 0, at = -1; };
  struct Slot { std::int32_t owner = 0; std::unique_ptr<ScanTables> tables; };

  PaintBrush* find(int layer, int born) {
    for (auto& b : brushes_) if (b.serial && b.layer == layer && b.born == born) return &b;
    return nullptr;
  }

  // The voice's brush, made and dipped the first frame it sounds.
  PaintBrush* brushOf(const PaintNote& v, double t, int low, bool alone) {
    const int layer = v.layer;
    if (PaintBrush* b = find(layer, v.id)) return b;
    PaintBrush* b = nullptr;
    for (auto& c : brushes_) if (!c.serial) { b = &c; break; }
    if (!b) return nullptr;  // more voices than brushes: the rest sound their ink
    std::size_t slot = kPaintBrushes;
    for (std::size_t s = 0; s < kPaintBrushes; s++) if (!slots_[s].owner) { slot = s; break; }
    if (slot == kPaintBrushes) return nullptr;
    /* The hand's last strike, if this note is struck alone and that note still
       sounds - or the pedal is down, when its brush may have lifted already
       (a pluck's under the pedal), which is kept for the purpose
       (PaintParams::join). */
    PaintBrush* live = nullptr;
    const PaintBrush* from = nullptr;
    if (alone && p_.join && layer >= 0 && layer < 2) {
      for (auto& c : brushes_)
        if (c.serial && &c != b && c.layer == layer && !c.handed && c.placed && (!live || c.bornAt > live->bornAt)) live = &c;
      const PaintBrush& lifted = lifted_[static_cast<std::size_t>(layer)];
      from = live;
      if (lifted.serial && (!from || lifted.bornAt > from->bornAt)) { from = &lifted; live = nullptr; }
      const bool sounding = live && live->peak > 0 && live->level > p_.joinFloor * live->peak;
      if (from && !(t - from->bornAt >= kChordSeconds && (sounding || pedal_))) from = live = nullptr;
    }
    PaintBrush was = from ? *from : PaintBrush {};
    // A lifted stroke stopped where its note did: it goes on from its pitch where the turn is now.
    if (from && !live) { const PaintPoint at = layout_->at(t, was.hz); was.x = at.x * kPaintN; was.y = at.y * kPaintN; }
    *b = {};
    b->serial = ++serials_;
    if (from) {
      // The same stroke: its serial (its own paint is not dragged, and the look carries its colour on), where it is,
      // what it holds and carries; the old note's brush, if it still sounds, lays no more.
      b->serial = was.serial;
      b->x = was.x; b->y = was.y; b->placed = true;
      b->load = was.load; b->carry = was.carry; b->hz = was.hz;
      if (live) { live->handed = true; b->from = static_cast<int>(live - brushes_.data()); }
      lifted_[static_cast<std::size_t>(layer)].serial = 0;
    }
    b->layer = layer; b->born = v.id; b->note = v.note; b->slot = slot; b->bornAt = t;
    // Its ink against the lowest note sounding, round the circle of fifths: a unison, fifth or fourth
    // the hand's own, a second, third, sixth or minor seventh related, a semitone or tritone a clash.
    const int fifths = ((v.note - (low > 999 ? v.note : low)) * 7 % 12 + 12) % 12, steps = std::min(fifths, 12 - fifths);
    b->ink = steps <= 1 ? 0 : steps <= 4 ? 1 : 2;
    slots_[slot].owner = b->serial;
    // The strike that made it, if the keyboard handed one.
    for (auto& s : struck_) {
      if (s.at >= 0 && s.note == v.note && (s.layers & (1 << layer))) { b->impact = s.impact; s.at = -1; break; }
    }
    // A note going on with a stroke dips less than a stroke's first (the study's 0.4 of a first dip, before the strike's);
    // the wheel loads it heavier or lighter (step 3).
    const double dip = (kDipBase * (from ? 0.4 : 1.0) + kDipStrike * b->impact) * wheelLoad();
    for (int k = 0; k < kPaintBins; k++) {
      const auto ki = static_cast<std::size_t>(k);
      b->share[ki] = 0.45 + 0.55 * paintHash(static_cast<std::uint32_t>(b->serial) * 977u + static_cast<std::uint32_t>(k) * 31u + 7u);
      // Dipped again, a stroke going on keeps what it held (the study's: dipping does not wipe the brush).
      b->load[ki] = std::min(loadMost(), (from ? b->load[ki] : 0) + dip * b->share[ki]);
    }
    return b;
  }

  /* One frame of a brush: fed while its key is down, moved to where its pitch
     is now, stamping every 0.35 of a cell. Its pressure is the voice's level
     to the 0.7, as the study's width was, so a note tapers as it fades - on
     a stroke taken up from another note, the louder of the two, as the
     study's path took it, so the line does not pinch where one note gives
     way to the next; a hard strike presses it, rising over 15 ms and falling
     over 60, and widens it a little (the study's: a sudden jump in width,
     as step 2 had, read as a notch cut in the stroke, and a run as beads). */
  void stroke(PaintBrush& b, const PaintNote& v, double t, double dt) {
    b.level = std::clamp(v.level, 0.0, 1.0);
    b.peak = std::max(b.peak, b.level);
    double level = b.level;
    if (b.from >= 0) {
      const PaintBrush& f = brushes_[static_cast<std::size_t>(b.from)];
      if (f.serial == b.serial && f.handed) level = std::max(level, f.level); else b.from = -1;
    }
    double p = std::pow(level, 0.7);
    const double heavy = wheelLoad();
    if (v.held) {
      const double k = 1 - std::exp(-dt / kFeedTime);
      for (int i = 0; i < kPaintBins; i++) {
        const auto ii = static_cast<std::size_t>(i);
        const double want = kFeed * p * b.share[ii] * heavy;
        if (b.load[ii] < want) b.load[ii] += (want - b.load[ii]) * k;
      }
    }
    /* Where it goes: its note's pitch, but a stroke taken up from another
       note glides there over about 40 ms rather than jumping in a frame,
       which drew a run as a staircase (the study smoothed its path over
       25 ms, knowing the next note; here only the last is known). */
    if (!(b.hz > 0) || !(v.hz > 0)) b.hz = v.hz;
    else b.hz *= std::pow(v.hz / b.hz, 1 - std::exp(-dt / kGlideSeconds));
    const PaintPoint at = layout_->at(t, b.hz);
    const double x = at.x * kPaintN, y = at.y * kPaintN;
    if (!b.placed) { b.x = x; b.y = y; b.placed = true; }
    const double dx = x - b.x, dy = y - b.y, len = std::hypot(dx, dy);
    // Its strike's mark, once, from where it lands (step 3): the splayed brush's fan.
    if (!b.spattered) { b.spattered = true; if (!b.handed) strikeMark(b, x, y, t); }
    const double since = std::max(0.0, t - b.bornAt);
    (void)since;
    const double bump = (1 - std::exp(-since / kImpactRise)) * std::exp(-since / kImpactFall) * b.impact * 1.6;
    const double bulge = 1 + kImpactPress * bump;
    /* The player's hands on it (step 3). The wheel, up from its rest at the
       bottom, presses it harder and wider as it loads it (wheelLoad, and the
       spend in stamp); pressure on a held key presses it in, wider and
       harder, which shoves more wet paint aside (the smear: kPush is by the
       pressure). All of it reaches the stamp's width and pressure, so the
       look draws what the map holds. At rest every factor is one. */
    const double s = wheelUp(), lean = v.held ? controls_.pressure : 0.0;
    p = std::min(1.0, p * (1 + kWheelPress * s) * (1 + kLeanPress * lean));
    // The strike's own widening is the splay now (stamp), which replaced a 6 per cent swell of the whole brush.
    const double w = (kWidthLeast + kWidthPress * p) * p_.width * (1 + kWheelWiden * s) * (1 + kLeanWiden * lean);
    if (!(p > 0.02) || b.handed) { b.x = x; b.y = y; return; }
    /* The bend's pull (20 Nov): a brush pressed into wet paint and moved
       across the radius by the pitch drags the paint with it, the way the
       pitch went. Where the stroke sits stays the pitch's - the look is the
       map, and pitch is the radius - but two semitones move it under a cell,
       which nobody can see under a stroke five wide; the paint it drags is
       drawn a brush's half-width on (kPullShift), as much of it as the
       brush moved over its own half-width, times kPullGain, so a quick flick
       smears hard in a short stretch and a slow bend pulls gently along a
       long one, and the same bend moves the same paint either way. */
    if (bendStep_ != 0 && b.placed && dt > 0) {
      const PaintPoint was = layout_->at(t, b.hz * std::exp2(-bendStep_)), on = layout_->at(t + 0.05, b.hz);
      const double mx = x - was.x * kPaintN, my = y - was.y * kPaintN, moved = std::hypot(mx, my);
      const double hw = std::max(0.5, w * 0.5 * (0.4 + 0.6 * p));
      double fx = on.x * kPaintN - x, fy = on.y * kPaintN - y;
      const double fl = std::hypot(fx, fy);
      fx = fl > 1e-9 ? fx / fl : 1; fy = fl > 1e-9 ? fy / fl : 0;
      if (moved > 1e-9) pull(b, b.x, b.y, mx / moved, my / moved, fx, fy, hw, moved, moved / dt, t);
    }
    const int steps = std::max(1, static_cast<int>(std::ceil(len / kSpacing)));
    const double ux = len > 1e-9 ? dx / len : 1, uy = len > 1e-9 ? dy / len : 0;
    for (int s = 1; s <= steps; s++) {
      const double f = static_cast<double>(s) / steps;
      /* The flare closes over the stroke's length, not its time: the bristles follow their paths back in over
         `regather` cells of travel, smoothly, and then it is the ordinary stroke. */
      const double gone = b.travelled + len * f;
      if (b.splay > 0 && gone < b.regather) {
        const double c = gone / b.regather;
        b.splayNow = b.splay * (1 - c * c * (3 - 2 * c));
      } else { b.splayNow = 0; b.splay = 0; }
      if (b.splayNow < 0.005) b.splayNow = 0;
      stamp(b, b.x + dx * f, b.y + dy * f, ux, uy, w, std::min(1.0, p * bulge), t, len / steps);
    }
    b.travelled += len;
    b.x = x; b.y = y;
  }

  // The wheel up from its rest at the bottom, nought to one; nought while it has not moved (PaintControls::wheel).
  double wheelUp() const { return std::clamp(controls_.wheel, 0.0, 1.0); }
  // What it does to the brush's load: the dip and the feed, and the most a brush holds, heavier up to kWheelLoad times at the top.
  double wheelLoad() const { return 1 + (kWheelLoad - 1) * wheelUp(); }
  double loadMost() const { return kLoadMost * wheelLoad(); }

  /* A strike's mark (step 3). The owner, 20 Nov, of the drops: "It doesn't
     look like a hard pressed paint brush"; and of the splay drawn next, as
     a fan of fingers and separate tracks: "It splays at the start, but then
     it continues into a more normal stroke". A brush slammed onto the canvas
     flares: its bristles spread as it lands, densely in the middle and
     further apart outward (paintFlareAt), and as it drags on each follows
     its own path back in, over 1.5 to 3 of its widths of travel by the
     impact, until it is the ordinary stroke - one seamless mark, the
     bristles' lines texture inside it. Where it lands, a small rounded heel
     of the paint the press squeezes out, just behind; the squeeze leaves the
     brush a little leaner. All of it grows with the impact to the 1.5 from
     nothing, so a soft strike barely flares and Strike at nought never does.
     Seeded from the stroke, so every strike is like the others and none the
     same. Tried and gone: drops of spatter, then a fan of straight fingers
     with the stroke after as separate tracks over bare canvas. */
  void strikeMark(PaintBrush& b, double x, double y, double t) {
    const double impact = std::clamp(p_.spatterAt >= 0 ? p_.spatterAt : b.impact, 0.0, 1.0);
    const double k = std::pow(impact, 1.5);
    if (!(k > 0.002)) return;
    const auto seed = (static_cast<std::uint32_t>(b.serial) * 7919u + static_cast<std::uint32_t>(b.born) * 131u +
                       static_cast<std::uint32_t>(std::lround(t * 1000)) * 31u) & 0xffffu;
    const double hw = kMarkHalfWidth * p_.width / 2;
    b.splay = kFlareMost * k; b.regather = (kCloseLeast + kCloseHard * k) * 2 * hw; b.splaySeed = seed; b.travelled = 0;
    // The heel: rounded, a little behind where it lands (the layout's way, a moment back at the same pitch).
    const PaintPoint back = layout_->at(t - 0.05, b.hz);
    double bx = back.x * kPaintN - x, by = back.y * kPaintN - y;
    const double bl = std::hypot(bx, by);
    bx = bl > 1e-9 ? bx / bl : -1; by = bl > 1e-9 ? by / bl : 0;
    const double r = kHeel * hw * std::sqrt(k);
    drop(b, x + bx * 0.4 * r, y + by * 0.4 * r, -bx, -by, r, 1, seed * 3u + 1u, 0.5, kHeelThick, t);
    for (int g = 0; g < kPaintBins; g++)
      b.load[static_cast<std::size_t>(g)] *= 1 - kSqueeze * k * (0.6 + 0.4 * std::fabs((2.0 * g - 7) / 7));
  }

  /* One finger of the mark, in cells: its root, its way, its half-width at
     the root, its length, its seed and its thickness at the root. Laid as a
     drop is, each cell the mean over the look's pixels in it. */
  void finger(const PaintBrush& b, double x, double y, double dx, double dy, double base, double len, std::uint32_t seed,
              double thick, double t) {
    constexpr int N = kPaintN, S = kDropSamples;
    if (!(base > 0) || !(len > 0)) return;
    seed &= 0xffffffu;
    if (stamps_.size() < kPaintStampsMost) {
      PaintStamp st;
      st.x = static_cast<float>(x / N); st.y = static_cast<float>(y / N); st.dx = static_cast<float>(dx); st.dy = static_cast<float>(dy);
      st.w = static_cast<float>(2 * base / N); st.p = 1; st.t = static_cast<float>(t); st.per = 1;
      st.load.fill(static_cast<float>(thick));
      st.serial = b.serial; st.hand = static_cast<std::uint8_t>(b.layer); st.ink = static_cast<std::uint8_t>(b.ink);
      st.note = static_cast<std::uint8_t>(std::clamp(b.note, 0, 127));
      st.kind = kPaintStampFinger; st.a = static_cast<float>(len / base); st.b = static_cast<float>(seed);
      stamps_.push_back(st);
    } else { dropped_++; }
    const double reach = len + base * 1.5 + 1;
    const int x0 = std::max(0, static_cast<int>(std::floor(std::min(x, x + dx * len) - base * 1.5 - 1)));
    const int x1 = std::min(N - 1, static_cast<int>(std::ceil(std::max(x, x + dx * len) + base * 1.5 + 1)));
    const int y0 = std::max(0, static_cast<int>(std::floor(std::min(y, y + dy * len) - base * 1.5 - 1)));
    const int y1 = std::min(N - 1, static_cast<int>(std::ceil(std::max(y, y + dy * len) + base * 1.5 + 1)));
    (void)reach;
    const double nx = -dy, ny = dx, L = len / base, px = 1.0 / (S * base);
    for (int yy = y0; yy <= y1; yy++)
      for (int xx = x0; xx <= x1; xx++) {
        double in = 0;
        for (int j = 0; j < S; j++)
          for (int i = 0; i < S; i++) {
            const double rx = xx + (i + 0.5) / S - x, ry = yy + (j + 0.5) / S - y;
            in += paintFingerCover((rx * nx + ry * ny) / base, (rx * dx + ry * dy) / base, L, seed, px);
          }
        if (!(in > 0)) continue;
        layCell(b, static_cast<std::size_t>(yy) * N + static_cast<std::size_t>(xx), thick * in / (S * S), t);
      }
  }

  // A deposit `d` into cell `q`, as a drop or a finger lands it: mixed into wet paint, covering dry by its opacity.
  void layCell(const PaintBrush& b, std::size_t q, double d, double t) {
    const double before = map_.thick[q], wetBefore = map_.wet[q];
    if (before < 1e-4) acc_.ontoBare += d; else if (wetBefore > 0.3) acc_.intoWet += d; else acc_.ontoDry += d;
    acc_.laid += d;
    const double hide = (1 - std::exp(-d / kPaintHide)) * (1 - wetBefore);
    const double kept = before * (1 - hide), after = kept + d;
    map_.wet[q] = static_cast<float>(after > 0 ? (wetBefore * kept + d) / after : 0);
    map_.thick[q] = static_cast<float>(after);
    map_.owner[q] = b.serial;
    map_.laidAt[q] = static_cast<float>(t);
  }

  /* One drop, in cells: where, the way it flew, its radius, its length over
     its width, its edge's seed and raggedness, and its thickness. It lays as
     a stamp does over what is there (mixing into wet paint, covering dry by
     its opacity), but neither picks up nor ploughs: it lands from the air.
     Each cell takes the mean of what the shape covers of the look's six by
     six pixels in it (paintDropCover), so the map holds what the look draws. */
  void drop(const PaintBrush& b, double x, double y, double dx, double dy, double r, double longer, std::uint32_t seed,
            double rough, double thick, double t) {
    constexpr int N = kPaintN, S = kDropSamples;
    if (!(r > 0)) return;
    if (stamps_.size() < kPaintStampsMost) {
      PaintStamp st;
      st.x = static_cast<float>(x / N); st.y = static_cast<float>(y / N); st.dx = static_cast<float>(dx); st.dy = static_cast<float>(dy);
      st.w = static_cast<float>(2 * r / N); st.p = static_cast<float>(rough); st.t = static_cast<float>(t); st.per = 1;
      st.load.fill(static_cast<float>(thick));
      st.serial = b.serial; st.hand = static_cast<std::uint8_t>(b.layer); st.ink = static_cast<std::uint8_t>(b.ink);
      st.note = static_cast<std::uint8_t>(std::clamp(b.note, 0, 127));
      st.kind = kPaintStampDrop; st.a = static_cast<float>(longer); st.b = static_cast<float>(seed & 0xffffffu);
      stamps_.push_back(st);
    } else { dropped_++; }
    seed &= 0xffffffu;
    const double reach = r * std::max(1 + 0.26 * rough, longer > 1.05 ? 2.5 * (longer - 1) + 0.8 : 0.0) + 1;  // the edge's harmonics add to about a quarter
    const int x0 = std::max(0, static_cast<int>(std::floor(x - reach))), x1 = std::min(N - 1, static_cast<int>(std::ceil(x + reach)));
    const int y0 = std::max(0, static_cast<int>(std::floor(y - reach))), y1 = std::min(N - 1, static_cast<int>(std::ceil(y + reach)));
    const double nx = -dy, ny = dx;
    for (int yy = y0; yy <= y1; yy++)
      for (int xx = x0; xx <= x1; xx++) {
        double in = 0;
        for (int j = 0; j < S; j++)
          for (int i = 0; i < S; i++) {
            const double rx = xx + (i + 0.5) / S - x, ry = yy + (j + 0.5) / S - y;
            in += paintDropCover((rx * nx + ry * ny) / r, (rx * dx + ry * dy) / r, longer, seed, rough, 1.0 / (S * r));
          }
        if (!(in > 0)) continue;
        layCell(b, static_cast<std::size_t>(yy) * N + static_cast<std::size_t>(xx), thick * in / (S * S), t);
      }
  }

  /* The bend's pull (20 Nov, redesigned after the owner: "it still has
     minimal effect, and the effect it does have is smearing a small blocky
     spot ... The pitch bend should pull a lot more"). A brush pressed into
     wet paint and moved across the radius by the pitch drags the paint with
     it, as a loaded brush or a palette knife does: each of its eight bristle
     groups takes a share of the wet paint under it and draws it out into a
     streak of four bristle lines the way the pitch went, several stroke
     widths long (`kPullReach` half-widths of the brush at a flick, by
     PaintParams::pullReach), thinning and tapering to their ends and curving
     back the way the brush came. The share is by how far the brush moved
     over a group's width (`kPullGain`), so a bend moves the same paint
     whatever its speed; its speed shapes the streaks - a flick (over
     kPullFlick cells a second) fine, long and sharp, a slow bend broad, soft
     and shorter - and how far the bend has gone (in semitones, a whole
     tone the most) how long they are. What a group takes, it lays along its
     streak (conserved), and the streak's stamp carries the thickness, so the
     look lays the same lines from the same shape (paintStreakCover). Where
     the stroke sits stays the pitch's. */
  void pull(const PaintBrush& b, double x, double y, double ux, double uy, double fx, double fy, double hw, double moved,
            double speed, double t) {
    constexpr int N = kPaintN, S = kDropSamples;
    const double sharp = std::clamp(speed / kPullFlick, 0.0, 1.0);
    const double semis = std::min(2.0, std::fabs(12 * std::log2(controls_.bend)));
    const double gw = hw / 8 * (1.3 + 1.2 * (1 - sharp));  // a group's half-width, broader for a slow bend
    const double len = kPullReach * p_.pullReach * hw * (0.45 + 0.55 * sharp) * (0.35 + 0.65 * semis / 2) / gw;  // in gw
    const double f = std::min(0.8, kPullGain * moved / gw);
    const double vx = -uy, vy = ux;  // across the streak
    // The paint trails the brush: the streak curves back against the way it travels.
    const double bend = -(fx * vx + fy * vy) * 0.6;
    for (int g = 0; g < kPaintBins; g++) {
      const double across = (2.0 * g - 7) / 8 * hw;
      const double rx0 = x - fy * across, ry0 = y + fx * across;  // the group's place on the brush (across its travel)
      // What it takes: wet paint within kPullTake of its own half-width of where it is, by how near.
      double took = 0;
      const double tr = kPullTake * gw;
      const int x0 = std::max(0, static_cast<int>(std::floor(rx0 - tr - 1))), x1 = std::min(N - 1, static_cast<int>(std::ceil(rx0 + tr + 1)));
      const int y0 = std::max(0, static_cast<int>(std::floor(ry0 - tr - 1))), y1 = std::min(N - 1, static_cast<int>(std::ceil(ry0 + tr + 1)));
      for (int yy = y0; yy <= y1; yy++)
        for (int xx = x0; xx <= x1; xx++) {
          const double r = std::hypot(xx + 0.5 - rx0, yy + 0.5 - ry0) / std::max(kPullTake * gw, 0.5);
          if (r >= 1) continue;
          const std::size_t q = static_cast<std::size_t>(yy) * N + static_cast<std::size_t>(xx);
          const double tk = map_.thick[q] * f * map_.wet[q] * (1 - r * r);
          map_.thick[q] = static_cast<float>(map_.thick[q] - tk);
          took += tk;
        }
      if (!(took > 1e-7)) continue;
      const auto seed = (static_cast<std::uint32_t>(b.serial) * 131u + static_cast<std::uint32_t>(g) * 977u +
                         static_cast<std::uint32_t>(std::lround(t * 60)) * 7919u) & 0xffffffu;
      // Where it lays it: the streak's shape over the cells, then scaled so it lays what was taken.
      const double ext = len * gw;
      const int sx0 = std::max(0, static_cast<int>(std::floor(std::min(rx0, rx0 + ux * ext) - gw * (2 + std::fabs(bend) * len) - 1)));
      const int sx1 = std::min(N - 1, static_cast<int>(std::ceil(std::max(rx0, rx0 + ux * ext) + gw * (2 + std::fabs(bend) * len) + 1)));
      const int sy0 = std::max(0, static_cast<int>(std::floor(std::min(ry0, ry0 + uy * ext) - gw * (2 + std::fabs(bend) * len) - 1)));
      const int sy1 = std::min(N - 1, static_cast<int>(std::ceil(std::max(ry0, ry0 + uy * ext) + gw * (2 + std::fabs(bend) * len) + 1)));
      const int bw = sx1 - sx0 + 1, bh = sy1 - sy0 + 1;
      if (bw <= 0 || bh <= 0 || bw * bh > kStreakCells) continue;
      double sum = 0;
      for (int yy = sy0; yy <= sy1; yy++)
        for (int xx = sx0; xx <= sx1; xx++) {
          double in = 0;
          for (int j = 0; j < S; j++)
            for (int i = 0; i < S; i++) {
              const double rx = xx + (i + 0.5) / S - rx0, ry = yy + (j + 0.5) / S - ry0;
              in += paintStreakCover((rx * vx + ry * vy) / gw, (rx * ux + ry * uy) / gw, len, bend, sharp, seed, 1.0 / (S * gw));
            }
          streak_[static_cast<std::size_t>((yy - sy0) * bw + (xx - sx0))] = in / (S * S);
          sum += in / (S * S);
        }
      if (!(sum > 1e-9)) continue;
      const double thick = took / sum;
      if (stamps_.size() < kPaintStampsMost) {
        PaintStamp st;
        st.x = static_cast<float>(rx0 / N); st.y = static_cast<float>(ry0 / N); st.dx = static_cast<float>(ux); st.dy = static_cast<float>(uy);
        st.w = static_cast<float>(2 * gw / N); st.p = static_cast<float>(f); st.load[2] = static_cast<float>(kPullTake); st.t = static_cast<float>(t); st.per = static_cast<float>(bend);
        st.load[0] = static_cast<float>(thick); st.load[1] = static_cast<float>(sharp);
        st.serial = b.serial; st.hand = static_cast<std::uint8_t>(b.layer); st.ink = static_cast<std::uint8_t>(b.ink);
        st.note = static_cast<std::uint8_t>(std::clamp(b.note, 0, 127));
        st.kind = kPaintStampPull; st.a = static_cast<float>(len); st.b = static_cast<float>(seed);
        stamps_.push_back(st);
      } else { dropped_++; }
      for (int yy = sy0; yy <= sy1; yy++)
        for (int xx = sx0; xx <= sx1; xx++) {
          const double c = streak_[static_cast<std::size_t>((yy - sy0) * bw + (xx - sx0))];
          if (c > 0) layCell(b, static_cast<std::size_t>(yy) * N + static_cast<std::size_t>(xx), thick * c, t);
        }
    }
  }

  /* One stamp, the study's oil paint (painting-study/tools/oilpaint.cpp) kept
     to what the map holds - thickness and wetness, no colour: the brush's
     bristle groups across its width each lay by their load and the
     pressure; wet paint under it that is not its own stroke is partly
     picked up into the brush (and carried on, to be laid further along) and
     partly shoved to its flanks; over dry paint the new coat covers by its
     opacity, and a nearly empty bristle group catches only where the paint
     stands above the brush's mean. `moved` is how far it went since its
     last stamp, so the paint laid per length does not depend on the
     sampling. */
  void stamp(PaintBrush& b, double x, double y, double dx, double dy, double w, double p, double t, double moved) {
    constexpr int N = kPaintN;
    const double nx = -dy, ny = dx;
    const double hw = std::max(0.5, w * 0.5 * (0.4 + 0.6 * p));
    const double hl = std::max(0.75, 0.15 * w);
    const double per = std::clamp(moved / (1.4 * hl), 0.02, 1.0);
    if (stamps_.size() < kPaintStampsMost) {
      PaintStamp st;
      st.x = static_cast<float>(x / N); st.y = static_cast<float>(y / N); st.dx = static_cast<float>(dx); st.dy = static_cast<float>(dy);
      st.w = static_cast<float>(w / N); st.p = static_cast<float>(p); st.t = static_cast<float>(t); st.per = static_cast<float>(per);
      for (std::size_t k = 0; k < static_cast<std::size_t>(kPaintBins); k++) st.load[k] = static_cast<float>(b.load[k] + b.carry[k]);
      st.serial = b.serial; st.hand = static_cast<std::uint8_t>(b.layer); st.ink = static_cast<std::uint8_t>(b.ink);
      st.note = static_cast<std::uint8_t>(std::clamp(b.note, 0, 127));
      // Splayed (the strike's), how far, and its seed and clumps: the look lays its bristles along the same tracks.
      if (b.splayNow > 0) { st.a = static_cast<float>(b.splayNow); st.b = static_cast<float>(b.splaySeed & 0xffffu); }
      stamps_.push_back(st);
    } else dropped_++;
    if (b.splayNow > 0) { stampSplayed(b, x, y, dx, dy, w, p, t, moved, hw, hl, per); return; }
    const int x0 = std::max(0, static_cast<int>(std::floor(x - hw - hl - 1))), x1 = std::min(N - 1, static_cast<int>(std::ceil(x + hw + hl + 1)));
    const int y0 = std::max(0, static_cast<int>(std::floor(y - hw - hl - 1))), y1 = std::min(N - 1, static_cast<int>(std::ceil(y + hw + hl + 1)));
    if (x0 > x1 || y0 > y1) return;
    // The mean of what is firm under the brush - dried paint, not wet, which gives under it.
    double firmSum = 0;
    int firmN = 0;
    for (int yy = y0; yy <= y1; yy++)
      for (int xx = x0; xx <= x1; xx++) {
        const std::size_t q = static_cast<std::size_t>(yy) * N + static_cast<std::size_t>(xx);
        firmSum += map_.thick[q] * (1 - map_.wet[q]);
        firmN++;
      }
    const double firmMean = firmN ? firmSum / firmN : 0;
    std::array<double, kPaintBins> picked {}, spent {}, smeared {};
    for (int yy = y0; yy <= y1; yy++)
      for (int xx = x0; xx <= x1; xx++) {
        const double rx = xx + 0.5 - x, ry = yy + 0.5 - y;
        const double u = rx * nx + ry * ny, v = rx * dx + ry * dy;
        if (std::fabs(u) > hw || (u * u) / (hw * hw) + (v * v) / (hl * hl) > 1.6) continue;
        const std::size_t q = static_cast<std::size_t>(yy) * N + static_cast<std::size_t>(xx);
        const int k = std::clamp(static_cast<int>((u / hw + 1) * 0.5 * kPaintBins), 0, kPaintBins - 1);
        const auto kk = static_cast<std::size_t>(k);
        const double edge = std::max(0.0, 1 - std::pow(std::fabs(u) / hw, 4.0));
        const double tip = std::max(0.0, 1 - (v * v) / (hl * hl * 1.6));
        const double a = map_.thick[q], wet = map_.wet[q];
        const bool own = map_.owner[q] == b.serial && t - map_.laidAt[q] <= kOwnSeconds;
        // Wet paint under the brush's core: some into it, some to the flank it is nearer.
        if (wet > 0.01 && a > 0 && !own) {
          const double core = edge * tip;
          const double take = std::min(0.5, kPick * wet * core * per);
          const double push = v > 0 ? std::min(0.5, kPush * wet * core * p * per) : 0.0;
          const double tk = a * take, ps = a * push;
          picked[kk] += tk;
          map_.thick[q] = static_cast<float>(a - tk - ps);
          if (ps > 0) {
            const double off = (u >= 0 ? 1 : -1) * hw * 1.05;
            const int ex = static_cast<int>(std::floor(x + nx * off + dx * v)), ey = static_cast<int>(std::floor(y + ny * off + dy * v));
            if (ex >= 0 && ey >= 0 && ex < N && ey < N) {
              const std::size_t e = static_cast<std::size_t>(ey) * N + static_cast<std::size_t>(ex);
              const double ea = map_.thick[e];
              map_.wet[e] = static_cast<float>(ea + ps > 0 ? (map_.wet[e] * ea + wet * ps) / (ea + ps) : 0);
              map_.thick[e] = static_cast<float>(ea + ps);
            }
          }
        }
        double d = kDeposit * p * b.load[kk] * edge * tip * per;
        double c = kDeposit * p * b.carry[kk] * edge * tip * per;
        // A lifting brush feathers: under half pressure only some bristle tips touch, scattered.
        if (p < 0.5) {
          const float touch = paintHash(static_cast<std::uint32_t>(xx) * 73856093u ^ static_cast<std::uint32_t>(yy) * 19349663u ^ static_cast<std::uint32_t>(k) * 83492791u);
          const double feather = std::clamp((p * 2.2 - touch) / 0.25, 0.0, 1.0) * (p * 2);
          d *= feather; c *= feather;
        }
        // A nearly empty bristle group catches only on high, firm points: dry brush. Not what
        // it carries: wet paint on the tips smears on wherever they touch.
        if (b.load[kk] < 0.5) {
          const double relief = map_.thick[q] * (1 - map_.wet[q]) - firmMean;
          const double need = 0.1 * (1 - b.load[kk] / 0.5) - 0.03;
          d *= std::clamp((relief - need) / 0.03, 0.0, 1.0);
        }
        if (d > 0) spent[kk] += d;
        if (c > 0) smeared[kk] += c;
        d += c;
        if (d <= 1e-7) continue;
        const double before = map_.thick[q], wetBefore = map_.wet[q];
        const bool ownNow = map_.owner[q] == b.serial && t - map_.laidAt[q] <= kOwnSeconds;
        if (before < 1e-4 || ownNow) acc_.ontoBare += d;
        else if (wetBefore > 0.3) acc_.intoWet += d;
        else acc_.ontoDry += d;
        acc_.laid += d;
        // Over wet paint they mix; over dry the new coat covers what is under it by its opacity.
        const double hide = (1 - std::exp(-d / kPaintHide)) * (1 - wetBefore);
        const double kept = before * (1 - hide);
        const double after = kept + d;
        map_.wet[q] = static_cast<float>(after > 0 ? (wetBefore * kept + d) / after : 0);
        map_.thick[q] = static_cast<float>(after);
        map_.owner[q] = b.serial;
        map_.laidAt[q] = static_cast<float>(t);
      }
    for (std::size_t k = 0; k < static_cast<std::size_t>(kPaintBins); k++) {
      // A loaded brush spends its paint more slowly (the wheel, step 3): it lays further on what it holds.
      if (spent[k] > 0) b.load[k] *= std::exp(-moved / (kReach * (1 + (kWheelReach - 1) * wheelUp()) * w) * p);
      if (smeared[k] > 0) b.carry[k] *= std::exp(-moved / (kCarryReach * w) * p);
      // What was picked up goes onto the tips, to be laid further on: the pick-up.
      if (picked[k] > 0) b.carry[k] = std::min(kLoadMost, b.carry[k] + kCarry * picked[k]);
    }
  }

  /* A stamp of a flared brush (the strike's, closing as it travels): the
     eight groups each lay in their own widened place side by side, their
     bristles by their share of their lanes (paintFlareAt), and the flare's
     whole width falls off at its edge as the plain stamp's does. Each cell
     takes the mean over three by three points in it, since a bristle line
     is narrower than a cell, so the map holds the paint the look's pixels
     lay. The pick-up, the push past the flare's flank, the feathering and
     the dry brush are the plain stamp's. */
  void stampSplayed(PaintBrush& b, double x, double y, double dx, double dy, double w, double p, double t, double moved, double hw, double hl,
                    double per) {
    constexpr int N = kPaintN, S = 3;
    const double a = b.splayNow, nx = -dy, ny = dx;
    const auto seed = b.splaySeed & 0xffffu;
    const double extent = paintFlareAt(0, a, seed, 0).extent;
    const double hwE = hw * (extent + 0.6 * std::sqrt(a) + 0.1);
    const int x0 = std::max(0, static_cast<int>(std::floor(x - hwE - hl - 1))), x1 = std::min(N - 1, static_cast<int>(std::ceil(x + hwE + hl + 1)));
    const int y0 = std::max(0, static_cast<int>(std::floor(y - hwE - hl - 1))), y1 = std::min(N - 1, static_cast<int>(std::ceil(y + hwE + hl + 1)));
    if (x0 > x1 || y0 > y1) return;
    double firmSum = 0;
    int firmN = 0;
    for (int yy = y0; yy <= y1; yy++)
      for (int xx = x0; xx <= x1; xx++) {
        const std::size_t q = static_cast<std::size_t>(yy) * N + static_cast<std::size_t>(xx);
        firmSum += map_.thick[q] * (1 - map_.wet[q]);
        firmN++;
      }
    const double firmMean = firmN ? firmSum / firmN : 0;
    const double px = 1.0 / (S * hw);
    // Which group, and how much paint, across the brush (its half-widths): the flare's, under its whole width's edge.
    const auto at = [&](double uh, int& k) {
      const PaintFlare f = paintFlareAt(uh, a, seed, px);
      k = f.k;
      if (k < 0) return 0.0;
      return f.weight * std::max(0.0, 1 - std::pow(std::fabs(uh) / extent, 4.0) * 0.6);
    };
    std::array<double, kPaintBins> picked {}, spent {}, smeared {}, wk {};
    for (int yy = y0; yy <= y1; yy++)
      for (int xx = x0; xx <= x1; xx++) {
        wk.fill(0);
        double core = 0;
        for (int j = 0; j < S; j++)
          for (int i = 0; i < S; i++) {
            const double rx = xx + (i + 0.5) / S - x, ry = yy + (j + 0.5) / S - y;
            const double u = rx * nx + ry * ny, v = rx * dx + ry * dy;
            const double tip = std::max(0.0, 1 - (v * v) / (hl * hl * 1.6));
            if (tip <= 0) continue;
            int k = -1;
            const double edge = at(u / hw, k);
            if (k < 0 || edge <= 0) continue;
            const double e = edge * tip / (S * S);
            wk[static_cast<std::size_t>(k)] += e;
            core += e;
          }
        if (core <= 0) continue;
        const std::size_t q = static_cast<std::size_t>(yy) * N + static_cast<std::size_t>(xx);
        const double rx = xx + 0.5 - x, ry = yy + 0.5 - y, u = rx * nx + ry * ny, v = rx * dx + ry * dy;
        const double a0 = map_.thick[q], wet = map_.wet[q];
        const bool own = map_.owner[q] == b.serial && t - map_.laidAt[q] <= kOwnSeconds;
        if (wet > 0.01 && a0 > 0 && !own) {
          const double take = std::min(0.5, kPick * wet * core * per);
          // Pushed to the flank of the clump the cell's middle is in, or nearest.
          int k = -1;
          at(u / hw, k);
          const double push = v > 0 && k >= 0 ? std::min(0.5, kPush * wet * core * p * per) : 0.0;
          const double tk = a0 * take, ps = a0 * push;
          for (int g = 0; g < kPaintBins; g++) picked[static_cast<std::size_t>(g)] += tk * wk[static_cast<std::size_t>(g)] / core;
          map_.thick[q] = static_cast<float>(a0 - tk - ps);
          if (ps > 0) {
            // Past the flare's flank on the cell's side, as the plain stamp pushes past the brush's.
            const double off = (u >= 0 ? 1 : -1) * (extent * hw * 1.05 + 0.5);
            const int ex = static_cast<int>(std::floor(x + nx * off + dx * v)), ey = static_cast<int>(std::floor(y + ny * off + dy * v));
            if (ex >= 0 && ey >= 0 && ex < N && ey < N) {
              const std::size_t e = static_cast<std::size_t>(ey) * N + static_cast<std::size_t>(ex);
              const double ea = map_.thick[e];
              map_.wet[e] = static_cast<float>(ea + ps > 0 ? (map_.wet[e] * ea + wet * ps) / (ea + ps) : 0);
              map_.thick[e] = static_cast<float>(ea + ps);
            }
          }
        }
        double total = 0;
        for (int g = 0; g < kPaintBins; g++) {
          const auto gi = static_cast<std::size_t>(g);
          if (wk[gi] <= 0) continue;
          double d = kDeposit * p * b.load[gi] * wk[gi] * per;
          double c = kDeposit * p * b.carry[gi] * wk[gi] * per;
          if (p < 0.5) {
            const float touch = paintHash(static_cast<std::uint32_t>(xx) * 73856093u ^ static_cast<std::uint32_t>(yy) * 19349663u ^ static_cast<std::uint32_t>(g) * 83492791u);
            const double feather = std::clamp((p * 2.2 - touch) / 0.25, 0.0, 1.0) * (p * 2);
            d *= feather; c *= feather;
          }
          if (b.load[gi] < 0.5) {
            const double relief = map_.thick[q] * (1 - map_.wet[q]) - firmMean;
            const double need = 0.1 * (1 - b.load[gi] / 0.5) - 0.03;
            d *= std::clamp((relief - need) / 0.03, 0.0, 1.0);
          }
          if (d > 0) spent[gi] += d;
          if (c > 0) smeared[gi] += c;
          total += d + c;
        }
        if (total <= 1e-7) continue;
        const double before = map_.thick[q], wetBefore = map_.wet[q];
        const bool ownNow = map_.owner[q] == b.serial && t - map_.laidAt[q] <= kOwnSeconds;
        if (before < 1e-4 || ownNow) acc_.ontoBare += total;
        else if (wetBefore > 0.3) acc_.intoWet += total;
        else acc_.ontoDry += total;
        acc_.laid += total;
        const double hide = (1 - std::exp(-total / kPaintHide)) * (1 - wetBefore);
        const double kept = before * (1 - hide), after = kept + total;
        map_.wet[q] = static_cast<float>(after > 0 ? (wetBefore * kept + total) / after : 0);
        map_.thick[q] = static_cast<float>(after);
        map_.owner[q] = b.serial;
        map_.laidAt[q] = static_cast<float>(t);
      }
    for (std::size_t k = 0; k < static_cast<std::size_t>(kPaintBins); k++) {
      if (spent[k] > 0) b.load[k] *= std::exp(-moved / (kReach * (1 + (kWheelReach - 1) * wheelUp()) * w) * p);
      if (smeared[k] > 0) b.carry[k] *= std::exp(-moved / (kCarryReach * w) * p);
      if (picked[k] > 0) b.carry[k] = std::min(kLoadMost, b.carry[k] + kCarry * picked[k]);
    }
  }

  // The map over `dt`: each cell's wetness falls by its thickness's drying time over `dryDt` (nought under the pedal), and its paint by the fade.
  void age(double dt, double dryDt) {
    if (!(dt > 0)) return;
    const double keep = std::exp2(-dt / p_.fade);
    std::array<double, kDrySteps + 1> dry {};
    for (int i = 0; i <= kDrySteps; i++) dry[static_cast<std::size_t>(i)] = std::pow(10.0, -dryDt / dryTime(p_.thick * i / kDrySteps));
    for (std::size_t q = 0; q < PaintMap::kCells; q++) {
      float& a = map_.thick[q];
      if (a == 0) continue;
      float& w = map_.wet[q];
      if (w > 0) {
        const double x = std::min(1.0, a / p_.thick) * kDrySteps;
        const int i = std::min(kDrySteps - 1, static_cast<int>(x));
        const double f = x - i;
        w = static_cast<float>(w * (dry[static_cast<std::size_t>(i)] * (1 - f) + dry[static_cast<std::size_t>(i + 1)] * f));
        if (w < 1e-4f) w = 0;
      }
      a = static_cast<float>(a * keep);
      if (a < 1e-5f) { a = 0; w = 0; }
    }
  }

  // The frame's reads off the map and what was laid on it.
  void measure(double dt) {
    reads_ = acc_;
    acc_ = {};
    double wetCover = 0, covered = 0;
    for (std::size_t q = 0; q < PaintMap::kCells; q++) {
      const double a = map_.thick[q];
      if (a == 0) continue;
      const double c = cover_(a);
      covered += c;
      wetCover += c * map_.wet[q];
    }
    const double cells = static_cast<double>(PaintMap::kCells);
    reads_.cover = std::min(1.0, 4 * wetCover / cells);
    reads_.covered = covered / cells;
    const double rate = dt > 0 ? reads_.laid / cells / dt : 0;
    reads_.moved = std::clamp(rate / (p_.motionFull * p_.width), 0.0, 1.0);
    reads_.repaint = reads_.laid > 1e-9 ? (reads_.intoWet + reads_.ontoDry) / reads_.laid : 0;
  }

  // The brush's constants, at 128 cells across (the study's were in pixels of 512).
  static constexpr double kDeposit = 0.6, kPick = 0.05, kPush = 0.018, kCarry = 0.8, kReach = 7, kCarryReach = 3;
  static constexpr double kDipBase = 0.8, kDipStrike = 1.2, kLoadMost = 2.5;
  static constexpr double kFeed = 1.6, kFeedTime = 0.25;
  static constexpr double kWidthLeast = 1.0, kWidthPress = 3.0, kSpacing = 0.35;
  static constexpr double kChordSeconds = 0.04, kGlideSeconds = 0.04;  // strikes closer than this are one chord (the study's)
  static constexpr double kImpactRise = 0.015, kImpactFall = 0.06, kImpactPress = 0.6, kImpactWiden = 0.06, kOwnSeconds = 1.5;
  static constexpr int kDrySteps = 32;
  // The controllers' (step 3). The wheel at its top: the load (the dip, the feed and the most a brush holds) times
  // kWheelLoad, its spend kWheelReach times as slow, pressed kWheelPress harder and kWheelWiden wider - chosen by
  // measuring against the mark set for them on 20 Nov, at the top 1.8 times as wide and 2.5 times the paint as at rest
  // (got 2.09 and 5.3; core/tests/pieces/painting.py, web/docs/listening/paint-controllers/). A key leaned on's press
  // and widening.
  static constexpr double kWheelLoad = 2.0, kWheelReach = 1.5, kWheelPress = 0.3, kWheelWiden = 0.5, kLeanPress = 0.5, kLeanWiden = 0.5;
  // The bend's pull: how far the wet paint is drawn, over the brush's half-width, and how much, over what the brush moved.
  static constexpr double kPullReach = 19.2, kPullGain = 10.0, kPullFlick = 6, kPullTake = 3.0;
  static constexpr int kStreakCells = 8192;
  /* The spatter: nothing under kSpatterFrom of a full impact; at a full one kSpatterMost drops, thrown as far as
     kSpatterSeconds along the time and kSpatterOctaves in pitch at width two (the round layout's A3: about nine cells
     along and eight across), the least drop kDropLeast cells across its radius, the blot's edge kSpatterBlot as
     ragged as a drop's, and a drop's thickness about kDropThick (a heavy stroke's). */
  /* The strike's flare: the brush's half-width it is drawn for (cells at width two), how far it flares at a full impact
     (the outermost groups widen by about that times 2.6 of their own width), over how many of its widths of travel it
     closes (from a touch to a full impact, by the impact to the 1.5), the heel's radius over the half-width, and the
     share of the load the squeeze takes. Chosen by looking (web/docs/listening/paint-controllers/strike/). */
  static constexpr double kMarkHalfWidth = 3.0, kFlareMost = 1.5, kCloseLeast = 1.5, kCloseHard = 1.5, kHeel = 0.28, kHeelThick = 0.3;
  static constexpr double kSqueeze = 0.25, kFingerThick = 0.3;
  static constexpr double kSpatterFrom = 0.35, kSpatterMost = 70, kSpatterSeconds = 0.6, kSpatterOctaves = 2.5;
  static constexpr double kDropLeast = 0.18, kSpatterBlot = 1.5, kSpatterBlotMost = 4.2, kDropThick = 0.5;
  static constexpr int kDropSamples = 6;  // the look's pixels across a cell: PAINT_SIZE / PAINT_CELLS

  PaintParams p_;
  std::unique_ptr<PaintLayout> layout_;
  PaintMap map_;
  PaintCover cover_;
  PaintReads reads_, acc_;  // the last frame's reads, and what is being laid towards the next
  std::array<PaintBrush, kPaintBrushes> brushes_ {};
  std::array<PaintBrush, 2> lifted_ {};  // each hand's last stroke as it lifted
  bool pedal_ = false;
  PaintControls controls_ {};
  double lastBend_ = 1, bendStep_ = 0;  // the bend at the last frame, and how far it has moved since, in octaves
  std::array<double, kStreakCells> streak_ {};  // a streak's cover over its box (pull)
  std::array<Slot, kPaintBrushes> slots_ {};
  std::array<Struck, 16> struck_ {};
  std::int32_t serials_ = 0;
  std::vector<PaintStamp> stamps_;
  std::size_t dropped_ = 0;
  std::vector<double> field_ = std::vector<double>(PaintMap::kCells, 0.0);
  mutable std::array<double, kScanPoints> raw_ {};
  mutable std::array<double, kScanPoints + 1> kernel_ {};
  std::array<double, kScanPoints> points_ {};
};

}  // namespace scope
