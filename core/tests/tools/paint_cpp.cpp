// Painting, step 1 (scope/paint.h), for core/tests/pieces/painting.py: each
// piece driven on its own and its numbers printed, so the piece's checks -
// and each one's null - read the core's own output. A command a run:
//
//   radius                 a note held in the instrument painting; the thickness-weighted
//                          radius of the map against where the layout puts the note and an
//                          octave above it, in cells
//   dry THIN THICK         a thin dab and a thick one, each's wetness after 2 and 6 s
//   rings                  three dabs round one note's ring and five round another's; the
//                          strongest harmonic each note's read has, and a mid ring's
//   wet READ               two dabs alike, one dried; field over thickness, wet over dry
//   reads                  the three reads' inputs: wet coverage fresh and dried, all
//                          paint's coverage dried, paint laid while laying and after,
//                          repainting onto bare canvas, another brush's paint and its own
//   pickup WAIT            a loaded stroke, then an empty brush across it WAIT seconds later:
//                          the paint it laid past the crossing, which it can only have carried
//   tables [off]           two notes held in the instrument painting (or not, `off`): how many
//                          voices have a table of their own, whether the two are one, how far
//                          apart their harmonics are, and whether the generator is painting
//   layout                 a phrase painted on round and on round turned a quarter: the
//                          difference between the maps (summed, over the paint) turned back,
//                          turned back the wrong way, and not turned, and the wetness's; and between the stage's reads and the
//                          notes' tables' harmonics
//   same                   a phrase painted twice, and once with another drying: whether the
//                          maps are the same to the bit
//   stage                  the picture stage on the paint's inputs, Level and Change
//   switch                 the stored switch and Persistence (step 2): a setup drawing Paint at a
//                          Persistence of 30 s, its knob moved, then Trace pressed and the knob
//                          moved again, and the state reopened in a second instrument: whether
//                          each paints, both Persistences at each step, and the knob's place
//   line MODE              A3 held in Mono, or A3 and E4 in Dyad, painting: the paint's radius
//                          and how much lies within a cell of each note's ring, and whether
//                          the layer plays a painted table
//   chain [JOIN [WIDTH]]   a run of eleven short notes struck alone on Tine piano's envelope, painting, a note
//                          joining the last one's stroke while it sounds (PaintParams::join; 0 each its own): how much of the
//                          run's arc has paint, the longest stretch without (degrees), the arc's degrees, and
//                          its thinnest tenth over its median (how deep it dips between notes), and how many strokes
//   join SOUND GAP [FLOOR [PEDAL]]  six notes struck alone GAP s apart on a pluck, a pad or Tine piano's
//                          envelope, at a join floor, the pedal down if PEDAL: how many strokes, and the
//                          quietest the last note was over its peak at a strike
//   width WIDTH            A3 held at a base width: the map's spread across its ring and the core's own contact
//                          half-width at the last stamp, both in cells, and the ring's radius
//   served                 the strokes the face is served: the count, the last frame's stamps
//                          against the ring's newest, and a read from the count itself
//   cost SECONDS [WIDTH]   a chord of sixteen held, trace and painting (at a base width), the best of three
//                          runs: the instrument's seconds per second of audio
//
// Step 3, the player's controllers on the brush; HEARS is PaintParams::hears (15 all, a bit off a null's):
//   pedal HEARS            a pluck's slow melody, six notes a second apart, under the sustain pedal, then the pedal
//                          let go: how much of its arc has paint and the longest stretch without (degrees), the paint's
//                          mean wetness as the pedal goes up, two seconds later, and the stamps the last frame laid
//   wheel WHEEL HEARS      A3 held, the mod wheel at WHEEL (below nought: never moved): the map's spread across the
//                          ring and the last stamp's half-width (cells), the paint laid in all, the mean bristle load
//                          at the last stamp, and the map's thickness summed to nine figures
//   bend HEARS             A3 held, the bend wheel swept to the top over a second: the brush's radius before and at the
//                          end, where the layout puts A3 two semitones up, the largest step from frame to frame, and
//                          how many frames it went back
//   spatter VEL [AT]       a note struck at VEL (or every strike spattered at impact AT): the paint more than five cells
//                          off its ring (past the widest stroke), and the farthest any lies off it (cells)
//   lean PRESSURE HEARS    A3 held and leaned on at PRESSURE: the map's spread and the last stamp's half-width, as width's
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

#include "scope/instrument.h"

namespace {
using namespace scope;

constexpr double kRate = 48000;
constexpr int kBlock = 128;

std::string code(const char* json) { return *encodeSetup(*jsonParse(utf8To16(json))); }
const char* const kSine = R"({"shape":"sine","midiMode":"poly","oscScan":60,"pictureAmount":50,"atk":2,"dec":300,"sus":80,"rel":400})";

struct Player {
  Instrument in;
  std::vector<float> l = std::vector<float>(kBlock), r = std::vector<float>(kBlock);
  explicit Player(const char* json, bool paint, const PaintParams& p = {}) {
    in.prepare(kRate, kBlock, *Instrument::setup(code(json))->setup);
    if (paint) in.setPainting(true, p);
  }
  void blocks(double seconds, std::vector<std::vector<std::uint8_t>> midi = {}) {
    const int n = static_cast<int>(std::round(seconds * kRate / kBlock));
    for (int b = 0; b < n; b++) {
      std::vector<Instrument::Event> ev;
      if (b == 0) for (auto& m : midi) ev.push_back({ 0, m.data(), m.size() });
      in.block(l.data(), r.data(), kBlock, ev.data(), ev.size(), nullptr, nullptr, 0, nullptr);
    }
  }
};

double hzOf(int note) { return 440 * std::pow(2.0, (note - 69) / 12.0); }

std::vector<double> harmonics(const std::vector<double>& t) {
  const std::size_t n = t.size();
  std::vector<double> p(65, 0);
  for (std::size_t k = 1; k <= 64; k++) {
    double a = 0, b = 0;
    for (std::size_t i = 0; i < n; i++) {
      const double th = 2 * kPi * static_cast<double>(k * i) / static_cast<double>(n);
      a += t[i] * std::cos(th); b += t[i] * std::sin(th);
    }
    p[k] = a * a + b * b;
  }
  double s = 0;
  for (double v : p) s += v;
  for (double& v : p) v /= s > 0 ? s : 1;
  return p;
}
int strongest(const std::vector<double>& p) { return static_cast<int>(std::max_element(p.begin() + 1, p.end()) - p.begin()); }
std::vector<double> asVector(const std::array<double, kScanPoints>& a) { return std::vector<double>(a.begin(), a.end()); }

// Dabs round a ring at `count` angles, from a brush of its own each.
void dabs(Painter& p, const PaintRing& ring, int count, double load, double t, int own) {
  for (int k = 0; k < count; k++) {
    const double th = 2 * kPi * k / count;
    p.lay(ring.cx + ring.r * std::sin(th), ring.cy - ring.r * std::cos(th), 3, 1, load, t, own + k);
  }
}

double radiusOfMap(const PaintMap& m) {
  double s = 0, sr = 0;
  for (int y = 0; y < kPaintN; y++)
    for (int x = 0; x < kPaintN; x++) {
      const double a = m.thick[static_cast<std::size_t>(y * kPaintN + x)];
      s += a; sr += a * std::hypot(x + 0.5 - kPaintN / 2.0, y + 0.5 - kPaintN / 2.0);
    }
  return s > 0 ? sr / s : 0;
}

// The map turned a quarter clockwise about its centre, as the turned layout turns where paint lands.
std::vector<float> turned(const std::vector<float>& g, int quarters) {
  std::vector<float> out(g.size());
  for (int y = 0; y < kPaintN; y++)
    for (int x = 0; x < kPaintN; x++) {
      int sx = x, sy = y;
      for (int q = 0; q < ((quarters % 4) + 4) % 4; q++) { const int nx = kPaintN - 1 - sy, ny = sx; sx = nx; sy = ny; }
      out[static_cast<std::size_t>(sy * kPaintN + sx)] = g[static_cast<std::size_t>(y * kPaintN + x)];
    }
  return out;
}
// The summed difference over the summed paint: nought the same, two none in common.
double l1(const std::vector<float>& a, const std::vector<float>& b) {
  double d = 0, t = 0;
  for (std::size_t i = 0; i < a.size(); i++) { d += std::fabs(a[i] - b[i]); t += a[i]; }
  return t > 0 ? d / t : 0;
}
double maxDiff(const std::vector<float>& a, const std::vector<float>& b) {
  double d = 0;
  for (std::size_t i = 0; i < a.size(); i++) d = std::max(d, static_cast<double>(std::fabs(a[i] - b[i])));
  return d;
}

class TurnedLayout : public PaintLayout {
 public:
  explicit TurnedLayout(const PaintParams& p) : round_(p), turn_(p.turn) {}
  PaintPoint at(double seconds, double hz) const override { return round_.at(seconds + turn_ / 4, hz); }
  PaintRing ring(double hz) const override { return round_.ring(hz); }

 private:
  RoundLayout round_;
  double turn_;
};

// A short phrase: a chord, a line over it, the chord let go.
struct Phrase {
  std::vector<double> glow, motion, memory;
  std::vector<std::vector<double>> tables;  // each frame's notes' harmonics, in voice order
  std::vector<float> thick, wet;
};
Phrase phrase(bool turnedLayout, const PaintParams& params = {}) {
  Player p(kSine, true, params);
  if (turnedLayout) p.in.painter()->setLayout(std::make_unique<TurnedLayout>(params));
  Phrase out;
  const std::vector<std::pair<double, std::vector<std::uint8_t>>> events = {
    { 0.1, { 0x90, 48, 90 } }, { 0.1, { 0x90, 55, 90 } }, { 0.5, { 0x90, 72, 100 } }, { 0.8, { 0x80, 72, 0 } },
    { 0.8, { 0x90, 74, 70 } }, { 1.1, { 0x80, 74, 0 } }, { 1.1, { 0x90, 76, 110 } }, { 1.6, { 0x80, 76, 0 } },
    { 2.2, { 0x80, 48, 0 } }, { 2.2, { 0x80, 55, 0 } } };
  std::size_t k = 0;
  int seen = -1;
  const int blocks = static_cast<int>(3.0 * kRate / kBlock);
  for (int b = 0; b < blocks; b++) {
    const double top = (b + 1) * static_cast<double>(kBlock) / kRate;
    std::vector<Instrument::Event> ev;
    while (k < events.size() && events[k].first < top) { ev.push_back({ 0, events[k].second.data(), events[k].second.size() }); k++; }
    p.in.block(p.l.data(), p.r.data(), kBlock, ev.data(), ev.size(), nullptr, nullptr, 0, nullptr);
    const int now = p.in.picture().phosphor().frames();
    if (now == seen) continue;
    seen = now;
    const auto& st = p.in.picture().stage();
    out.glow.push_back(st.glow()); out.motion.push_back(st.motion()); out.memory.push_back(st.memory());
    std::vector<double> row;
    for (const auto& v : p.in.generator().voices())
      if (!v.gone && v.paintTable) { const auto h = harmonics(v.paintTable->levels[0]); row.insert(row.end(), h.begin() + 1, h.begin() + 9); }
    out.tables.push_back(row);
  }
  out.thick = p.in.painter()->map().thick;
  out.wet = p.in.painter()->map().wet;
  return out;
}

double seriesDiff(const std::vector<double>& a, const std::vector<double>& b) {
  if (a.size() != b.size()) return 1e9;
  double d = 0;
  for (std::size_t i = 0; i < a.size(); i++) d = std::max(d, std::fabs(a[i] - b[i]));
  return d;
}
double tablesDiff(const std::vector<std::vector<double>>& a, const std::vector<std::vector<double>>& b) {
  if (a.size() != b.size()) return 1e9;
  double d = 0;
  for (std::size_t i = 0; i < a.size(); i++) {
    if (a[i].size() != b[i].size()) return 1e9;
    for (std::size_t j = 0; j < a[i].size(); j++) d = std::max(d, std::fabs(a[i][j] - b[i][j]));
  }
  return d;
}

double costOf(bool paint, double seconds, double width = 1) {
  double best = 1e9;
  PaintParams params;
  params.width = width;
  for (int run = 0; run < 3; run++) {
    Player p(R"({"shape":"sine","midiMode":"poly","oscScan":60,"pictureAmount":50,"atk":2,"sus":80,"rel":400})", paint, params);
    std::vector<std::vector<std::uint8_t>> chord;
    for (int k = 0; k < 16; k++) chord.push_back({ 0x90, static_cast<std::uint8_t>(36 + 3 * k), 90 });
    p.blocks(0.5, chord);
    const auto t0 = std::chrono::steady_clock::now();
    p.blocks(seconds);
    best = std::min(best, std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count() / seconds);
  }
  return best;
}
// The map's spread across the radius about its thickness-weighted mean, and that mean, in cells.
std::pair<double, double> spreadOf(const PaintMap& m) {
  double s = 0, sr = 0, srr = 0;
  for (int y = 0; y < kPaintN; y++)
    for (int x = 0; x < kPaintN; x++) {
      const double a = m.thick[static_cast<std::size_t>(y * kPaintN + x)];
      const double r = std::hypot(x + 0.5 - kPaintN / 2.0, y + 0.5 - kPaintN / 2.0);
      s += a; sr += a * r; srr += a * r * r;
    }
  const double mean = s > 0 ? sr / s : 0;
  return { s > 0 ? std::sqrt(std::max(0.0, srr / s - mean * mean)) : 0, mean };
}
// The core's contact half-width at a stamp, in cells (paint.h's stamp).
double halfWidthOf(const PaintStamp& st) { return std::max(0.5, st.w * kPaintN * 0.5 * (0.4 + 0.6 * st.p)); }
// Along an arc of the turn from t0 to t1 s, a degree at a time: the share of degrees whose most paint across the radius
// is over a fifth of the median's, and the longest run of degrees that is not.
std::pair<double, int> arcCover(const PaintMap& m, double turn, double t0, double t1) {
  const int a0 = static_cast<int>(std::ceil(360 * t0 / turn)), a1 = static_cast<int>(std::floor(360 * t1 / turn));
  std::vector<double> most(static_cast<std::size_t>(std::max(1, a1 - a0 + 1)), 0.0);
  for (int y = 0; y < kPaintN; y++)
    for (int x = 0; x < kPaintN; x++) {
      double deg = std::atan2(x + 0.5 - kPaintN / 2.0, -(y + 0.5 - kPaintN / 2.0)) * 180 / kPi;
      if (deg < 0) deg += 360;
      const int bin = static_cast<int>(std::floor(deg));
      if (bin < a0 || bin > a1) continue;
      double& v = most[static_cast<std::size_t>(bin - a0)];
      v = std::max(v, static_cast<double>(m.thick[static_cast<std::size_t>(y * kPaintN + x)]));
    }
  std::vector<double> sorted = most;
  std::sort(sorted.begin(), sorted.end());
  const double median = sorted[sorted.size() / 2];
  int covered = 0, gap = 0, longest = 0;
  for (const double v : most) { if (v > 0.2 * median && v > 1e-4) { covered++; gap = 0; } else longest = std::max(longest, ++gap); }
  return { static_cast<double>(covered) / static_cast<double>(most.size()), longest };
}
double meanWet(const PaintMap& m) {
  double s = 0, w = 0;
  for (std::size_t q = 0; q < PaintMap::kCells; q++) { s += m.thick[q]; w += m.thick[q] * m.wet[q]; }
  return s > 0 ? w / s : 0;
}
using Midi = std::vector<std::vector<std::uint8_t>>;
}  // namespace
int main(int argc, char** argv) {
  if (argc < 2) { std::fprintf(stderr, "usage: paint_cpp COMMAND ...\n"); return 2; }
  const std::string cmd = argv[1];
  const auto arg = [&](int i, double d) { return argc > i ? std::atof(argv[i]) : d; };
  if (cmd == "radius") {
    Player p(kSine, true);
    p.blocks(2.0, { { 0x90, 57, 100 } });
    const RoundLayout round;
    std::printf("%.4f %.4f %.4f\n", radiusOfMap(p.in.painter()->map()), round.radius(hzOf(57)) * kPaintN, round.radius(hzOf(69)) * kPaintN);
  } else if (cmd == "dry") {
    PaintParams params;
    params.dryThin = arg(2, 2); params.dryThick = arg(3, 6);
    Painter p(params);
    p.lay(0.25, 0.5, 3, 1, 0.55, 0, 1);
    p.lay(0.75, 0.5, 3, 1, 2.5, 0, 2);
    const auto cell = [](double x) { return static_cast<std::size_t>(64 * kPaintN + static_cast<int>(x * kPaintN)); };
    const double thinA = p.map().thick[cell(0.25)], thickA = p.map().thick[cell(0.75)];
    for (int k = 0; k < 120; k++) p.ageBy(1.0 / 60);
    const double thin2 = p.map().wet[cell(0.25)], thick2 = p.map().wet[cell(0.75)];
    for (int k = 0; k < 240; k++) p.ageBy(1.0 / 60);
    std::printf("%.4f %.4f %.4f %.4f %.4f %.4f\n", thinA, thickA, thin2, thick2, p.map().wet[cell(0.25)], p.map().wet[cell(0.75)]);
  } else if (cmd == "rings") {
    Painter p;
    const RoundLayout round;
    const double low = hzOf(40), high = hzOf(88);
    dabs(p, round.ring(low), 3, 1, 0, 10);
    dabs(p, round.ring(high), 5, 1, 0, 20);
    p.field();
    std::array<double, kScanPoints> pts {};
    p.readRing(round.ring(low), 3, pts);
    const int a = strongest(harmonics(asVector(pts)));
    p.readRing(round.ring(high), 3, pts);
    const int b = strongest(harmonics(asVector(pts)));
    p.readRing(round.ring(std::sqrt(low * high)), 3, pts);
    const auto mid = harmonics(asVector(pts));
    std::printf("%d %d %d %.4f %.4f\n", a, b, strongest(mid), mid[3], mid[5]);
  } else if (cmd == "wet") {
    PaintParams params;
    params.wetRead = arg(2, 0.4);
    Painter p(params);
    p.lay(0.3, 0.5, 3, 1, 1, 0, 1);
    for (int k = 0; k < 600; k++) p.ageBy(1.0 / 60);
    p.lay(0.7, 0.5, 3, 1, 1, 10, 2);
    p.field();
    const auto q = [](double x) { return static_cast<std::size_t>(64 * kPaintN + static_cast<int>(x * kPaintN)); };
    const auto& f = p.fieldCells();
    const auto& m = p.map();
    std::printf("%.5f %.5f %.5f %.5f\n", (f[q(0.7)] / m.thick[q(0.7)]) / (f[q(0.3)] / m.thick[q(0.3)]), m.wet[q(0.7)], m.wet[q(0.3)],
                f[q(0.7)] / f[q(0.3)]);
  } else if (cmd == "reads") {
    Painter p;
    for (int k = 0; k < 20; k++) p.lay(0.3 + 0.01 * k, 0.5, 4, 1, 1.5, 0, 1);
    p.measureNow(1.0 / 60);
    const double fresh = p.reads().cover, laying = p.reads().moved;
    const double bare = p.reads().repaint;
    for (int k = 0; k < 1800; k++) p.ageBy(1.0 / 60);
    p.measureNow(1.0 / 60);
    const double dried = p.reads().cover, covered = p.reads().covered, idle = p.reads().moved;
    // Over that, now dry, by another brush; and a fresh stroke of its own laid twice.
    for (int k = 0; k < 20; k++) p.lay(0.3 + 0.01 * k, 0.5, 4, 1, 1.5, 30, 2);
    p.measureNow(1.0 / 60);
    const double over = p.reads().repaint;
    for (int k = 0; k < 20; k++) p.lay(0.3 + 0.01 * k, 0.7, 4, 1, 1.5, 30, 3);
    p.measureNow(1.0 / 60);
    for (int k = 0; k < 20; k++) p.lay(0.3 + 0.01 * k, 0.7, 4, 1, 1.5, 30.2, 3);
    p.measureNow(1.0 / 60);
    const double own = p.reads().repaint;
    std::printf("%.5f %.5f %.5f %.5f %.5f %.5f %.5f %.5f\n", fresh, dried, covered, laying, idle, bare, over, own);
  } else if (cmd == "pickup") {
    const double wait = arg(2, 0.2);
    Painter p;
    p.drag(0.5, 0.2, 0.5, 0.8, 4, 1, 2.5, 0, 1);  // down the canvas, loaded
    const int steps = std::max(0, static_cast<int>(std::round(wait * 60)));
    for (int k = 0; k < steps; k++) p.ageBy(1.0 / 60);
    // An empty brush across it, left to right, one brush throughout.
    double past = 0;
    std::vector<float> before = p.map().thick;
    p.drag(0.3, 0.5, 0.75, 0.5, 4, 1, 0, wait, 2);
    // What it laid past the crossing (the stroke's right flank is 0.5 + its half-width), right of 0.56.
    for (int y = 0; y < kPaintN; y++)
      for (int x = static_cast<int>(0.56 * kPaintN); x < kPaintN; x++) {
        const std::size_t q = static_cast<std::size_t>(y * kPaintN + x);
        past += std::max(0.0f, p.map().thick[q] - before[q]);
      }
    std::printf("%.6f\n", past);
  } else if (cmd == "tables") {
    Player p(kSine, std::string(argc > 2 ? argv[2] : "") != "off");
    p.blocks(0.6, { { 0x90, 40, 100 } });
    p.blocks(0.9, { { 0x90, 88, 100 } });
    std::vector<std::vector<double>> h;
    std::vector<const CycleTables*> ptr;
    for (const auto& v : p.in.generator().voices())
      if (!v.gone && v.paintTable) { h.push_back(harmonics(v.paintTable->levels[0])); ptr.push_back(v.paintTable); }
    double diff = 0;
    if (h.size() == 2) for (std::size_t k = 1; k < h[0].size(); k++) diff += std::fabs(h[0][k] - h[1][k]);
    /* Each voice's table against its own ring read afresh (the map stands still
       between frames) and against the other voice's ring. */
    double ownErr = -1, otherErr = -1;
    if (h.size() == 2 && p.in.painter()) {
      Painter& painter = *p.in.painter();
      painter.field();
      std::array<double, kScanPoints> pts {};
      auto table = scanTableSet();
      std::vector<double> hzs;
      for (const auto& v : p.in.generator().voices()) if (!v.gone && v.paintTable) hzs.push_back(v.hz > 0 ? v.hz : v.freq);
      ownErr = otherErr = 0;
      for (std::size_t k = 0; k < 2; k++)
        for (int which = 0; which < 2; which++) {
          painter.readRing(painter.layout().ring(hzs[which ? 1 - k : k]), kScanSoftDefault, pts);  // the setup leaves the Softness at its start
          scanTables(pts, table);
          double err = 0;
          for (std::size_t i = 0; i < kScanTable; i++) err = std::max(err, std::fabs(table.levels[0][i] - ptr[k]->levels[0][i]));
          (which ? otherErr : ownErr) = std::max(which ? otherErr : ownErr, err);
        }
    }
    std::printf("%zu %d %.5f %d %.3g %.3g\n", h.size(), h.size() == 2 && ptr[0] == ptr[1] ? 1 : 0, diff / 2,
                p.in.generator().painting() ? 1 : 0, ownErr, otherErr);
  } else if (cmd == "own") {
    // A stroke, then a dry brush dragged back over it a moment later: as itself (`own`) or as another.
    const bool same = std::string(argc > 2 ? argv[2] : "") == "own";
    Painter p;
    p.drag(0.3, 0.5, 0.7, 0.5, 4, 1, 2.5, 0, 1);
    double before = 0, after = 0;
    for (float v : p.map().thick) before += v;
    p.drag(0.7, 0.5, 0.3, 0.5, 4, 1, 0, 0.2, same ? 1 : 2);
    for (float v : p.map().thick) after += v;
    std::printf("%.6f %.6f\n", before, after);
  } else if (cmd == "fade") {
    PaintParams params;
    params.fade = arg(2, 16);
    Painter p(params);
    p.lay(0.5, 0.5, 3, 1, 2.5, 0, 1);
    double before = 0, after = 0;
    for (float v : p.map().thick) before += v;
    for (int k = 0; k < 960; k++) p.ageBy(1.0 / 60);
    for (float v : p.map().thick) after += v;
    std::printf("%.6f\n", after / before);
  } else if (cmd == "heard") {
    // What a painted voice plays: Scan at 60 against Scan at nought, and nought twice, the Picture amount off.
    const auto play = [](const char* json) {
      Player p(json, true);
      std::vector<float> out;
      p.blocks(0.01, { { 0x90, 57, 100 } });
      for (int b = 0; b < static_cast<int>(1.5 * kRate / kBlock); b++) {
        p.blocks(1.0 / (kRate / kBlock));
        out.insert(out.end(), p.l.begin(), p.l.end());
      }
      return out;
    };
    const char* on = R"({"shape":"sine","midiMode":"poly","oscScan":60,"pictureAmount":0,"atk":2,"sus":80})";
    const char* off = R"({"shape":"sine","midiMode":"poly","oscScan":0,"pictureAmount":0,"atk":2,"sus":80})";
    const auto a = play(on), b = play(off), c = play(off);
    double ab = 0, bc = 0, e = 0;
    for (std::size_t i = 0; i < a.size(); i++) { ab += (a[i] - b[i]) * (a[i] - b[i]); bc += (b[i] - c[i]) * (b[i] - c[i]); e += b[i] * b[i]; }
    std::printf("%.6f %.6g\n", std::sqrt(ab / e), std::sqrt(bc / e));
  } else if (cmd == "switch") {
    Player p(R"({"shape":"sine","midiMode":"poly","oscScan":60,"persistence":"0.3","screenDraws":"paint","paintPersistence":30})", false);
    p.blocks(0.1, { { 0x90, 60, 100 } });
    const int a = p.in.painting() ? 1 : 0;
    const double a1 = p.in.paintPersistence(), t1 = p.in.tracePersistence(), k1 = p.in.slider("scanMemory");
    p.in.apply(*Instrument::slider("scanMemory", u"40"));
    p.blocks(0.05);
    const double a2 = p.in.paintPersistence(), t2 = p.in.tracePersistence();
    p.in.apply(Instrument::click("drawTrace"));
    p.blocks(0.05);
    const int b = p.in.painting() ? 1 : 0;
    const double k3 = p.in.slider("scanMemory");
    p.in.apply(*Instrument::slider("scanMemory", u"80"));
    p.blocks(0.05);
    const double a4 = p.in.paintPersistence(), t4 = p.in.tracePersistence();
    p.in.apply(Instrument::click("drawPaint"));
    p.blocks(0.05);
    // Reopened from its state, as a host's project is.
    Instrument again;
    again.prepare(kRate, kBlock, *Instrument::setup(p.in.stateCode())->setup);
    std::vector<float> l(kBlock), r(kBlock);
    for (int k = 0; k < 20; k++) again.block(l.data(), r.data(), kBlock, nullptr, 0, nullptr, nullptr, 0, nullptr);
    std::printf("%d %.4f %.4f %.1f %.4f %.4f %d %.1f %.4f %.4f %d %.4f %.4f %.1f\n", a, a1, t1, k1, a2, t2, b, k3, a4, t4,
                again.painting() ? 1 : 0, again.paintPersistence(), again.tracePersistence(), again.slider("scanMemory"));
  } else if (cmd == "line") {
    const std::string mode = argc > 2 ? argv[2] : "mono";
    const std::string json = R"({"shape":"sine","oscScan":60,"atk":2,"sus":80,"screenDraws":"paint","midiMode":")" + mode + R"("})";
    Player p(json.c_str(), false);
    // At today's narrow brush (width one), where A3's and E4's rings, seven semitones apart, are three cells apart
    // and a brush lays within a cell and a half of its own: what is held is where the line paints, not how wide.
    p.in.setPaintWidth(1);
    // A fifth held in Dyad, its two keys; the lower alone in Mono.
    if (mode == "dyad") p.blocks(1.5, { { 0x90, 57, 100 }, { 0x90, 64, 100 } });
    else p.blocks(1.5, { { 0x90, 57, 100 } });
    const RoundLayout round;
    const auto near = [&](double hz) {
      const double want = round.radius(hz) * kPaintN;
      double in = 0, all = 0;
      const auto& m = p.in.painter()->map();
      for (int y = 0; y < kPaintN; y++)
        for (int x = 0; x < kPaintN; x++) {
          const double a = m.thick[static_cast<std::size_t>(y * kPaintN + x)];
          all += a;
          if (std::fabs(std::hypot(x + 0.5 - kPaintN / 2.0, y + 0.5 - kPaintN / 2.0) - want) < 1.5) in += a;
        }
      return all > 0 ? in / all : 0;
    };
    const double hz = hzOf(57), fifth = hzOf(64);
    std::printf("%d %.4f %.4f %.4f %d\n", p.in.painting() ? 1 : 0, radiusOfMap(p.in.painter()->map()), near(hz), near(fifth),
                p.in.generator().scanTable(0) ? 1 : 0);
  } else if (cmd == "chain") {
    // A run of short notes in Poly, each struck alone a ninth of a second after the last, painting; joined (1) or not (0).
    PaintParams params;
    params.join = argc > 2 ? std::atof(argv[2]) != 0 : params.join;
    params.width = argc > 3 ? std::atof(argv[3]) : 1;
    // Tine piano's envelope: each note still sounding at the next strike, its own stroke ending well after its key.
    Player p(R"({"shape":"sine","midiMode":"poly","oscScan":60,"pictureAmount":50,"atk":1,"dec":1000,"sus":25,"rel":500})", true, params);
    const int scale[] = { 60, 62, 64, 65, 67, 69, 71, 72, 71, 69, 67 };
    const double t0 = 0;
    std::vector<std::int32_t> strokes;
    const auto look = [&]() {
      for (const auto& b : p.in.painter()->brushes())
        if (b.serial && std::find(strokes.begin(), strokes.end(), b.serial) == strokes.end()) strokes.push_back(b.serial);
    };
    for (const int n : scale) {
      p.blocks(0.06, { { 0x90, static_cast<std::uint8_t>(n), 100 } });
      look();
      p.blocks(1.0 / 9 - 0.06, { { 0x80, static_cast<std::uint8_t>(n), 0 } });
      look();
    }
    p.blocks(0.05, { { 0x80, 67, 0 } });
    const double t1 = 11.0 / 9;
    // Along the run's turn, a bin of a degree at a time: the most paint across the canvas's radius in it.
    const auto& m = p.in.painter()->map();
    const double turn = p.in.painter()->params().turn;
    const int a0 = static_cast<int>(std::ceil(360 * (t0 + 0.05) / turn)), a1 = static_cast<int>(std::floor(360 * (t1 - 0.05) / turn));
    std::vector<double> most(static_cast<std::size_t>(a1 - a0 + 1), 0.0);
    for (int y = 0; y < kPaintN; y++)
      for (int x = 0; x < kPaintN; x++) {
        const double dx = x + 0.5 - kPaintN / 2.0, dy = y + 0.5 - kPaintN / 2.0;
        double deg = std::atan2(dx, -dy) * 180 / kPi;
        if (deg < 0) deg += 360;
        const int bin = static_cast<int>(std::floor(deg));
        if (bin < a0 || bin > a1) continue;
        double& v = most[static_cast<std::size_t>(bin - a0)];
        v = std::max(v, static_cast<double>(m.thick[static_cast<std::size_t>(y * kPaintN + x)]));
      }
    std::vector<double> sorted = most;
    std::sort(sorted.begin(), sorted.end());
    const double median = sorted[sorted.size() / 2];
    // How much of the run's arc has paint at a fifth of the median's, and the longest stretch without.
    int covered = 0, gap = 0, longest = 0;
    for (const double v : most) {
      if (v > 0.2 * median) { covered++; gap = 0; } else longest = std::max(longest, ++gap);
    }
    // And how deep the stroke dips between notes: its thinnest tenth over its median.
    std::printf("%.4f %d %d %.4f %zu\n", static_cast<double>(covered) / static_cast<double>(most.size()), longest, static_cast<int>(most.size()),
                median > 0 ? sorted[sorted.size() / 10] / median : 0, strokes.size());
  } else if (cmd == "join") {
    /* Six notes struck alone, GAP seconds apart and each held nine tenths of
       that, on SOUND - "pluck" (gone in a quarter second), "pad" (a long
       release) or "tine" (Tine piano's) - at a join floor FLOOR (of the
       peak), with the sustain pedal down throughout if PEDAL is 1: how many
       strokes the phrase is, and the quietest the hand's last note was, over
       its peak, at a strike. */
    const std::string sound = argc > 2 ? argv[2] : "pluck";
    const double gap = arg(3, 1), floor = arg(4, PaintParams {}.joinFloor);
    const bool pedal = arg(5, 0) != 0;
    PaintParams params;
    params.joinFloor = floor;
    const char* json = sound == "pad" ? R"({"shape":"ramp","midiMode":"poly","oscScan":60,"atk":200,"dec":800,"sus":80,"rel":1500})"
                     : sound == "tine" ? R"({"shape":"sine","midiMode":"poly","oscScan":60,"atk":1,"dec":1000,"sus":25,"rel":500})"
                                       : R"({"shape":"sine","midiMode":"poly","oscScan":60,"atk":1,"dec":250,"sus":0,"rel":150})";
    Player p(json, true, params);
    std::vector<std::int32_t> strokes;
    double quietest = 1e9;
    const auto look = [&]() {
      for (const auto& b : p.in.painter()->brushes())
        if (b.serial && std::find(strokes.begin(), strokes.end(), b.serial) == strokes.end()) strokes.push_back(b.serial);
    };
    if (pedal) p.blocks(0.05, { { 0xB0, 64, 127 } });
    const int melody[] = { 60, 64, 67, 72, 67, 64 };
    for (int k = 0; k < 6; k++) {
      if (k > 0) {
        // The hand's last note, just before this strike: its level over its peak.
        const PaintBrush* last = nullptr;
        for (const auto& b : p.in.painter()->brushes()) if (b.serial && !b.handed && (!last || b.bornAt > last->bornAt)) last = &b;
        quietest = std::min(quietest, last && last->peak > 0 ? last->level / last->peak : 0.0);
      }
      const int steps = std::max(1, static_cast<int>(std::round(gap * 0.9 / 0.05)));
      for (int s = 0; s < steps; s++) { p.blocks(0.05, s == 0 ? std::vector<std::vector<std::uint8_t>> { { 0x90, static_cast<std::uint8_t>(melody[k]), 100 } } : std::vector<std::vector<std::uint8_t>> {}); look(); }
      const int rest = std::max(1, static_cast<int>(std::round(gap * 0.1 / 0.01)));
      for (int s = 0; s < rest; s++) { p.blocks(0.01, s == 0 ? std::vector<std::vector<std::uint8_t>> { { 0x80, static_cast<std::uint8_t>(melody[k]), 0 } } : std::vector<std::vector<std::uint8_t>> {}); look(); }
    }
    std::printf("%zu %.5f\n", strokes.size(), quietest > 1e8 ? 0.0 : quietest);
  } else if (cmd == "width") {
    // A3 held, painting at a base width: the map's spread across its ring (the thickness-weighted RMS of the
    // radius about its mean, in cells), and the core's own contact half-width at the last stamp, in cells.
    PaintParams params;
    params.width = argc > 2 ? std::atof(argv[2]) : 1;
    params.spatterAt = 0;  // the stroke's width alone: its strike's spatter (step 3) lies off the ring
    Player p(kSine, true, params);
    p.blocks(1.5, { { 0x90, 57, 100 } });
    const auto& m = p.in.painter()->map();
    double s = 0, sr = 0, srr = 0;
    for (int y = 0; y < kPaintN; y++)
      for (int x = 0; x < kPaintN; x++) {
        const double a = m.thick[static_cast<std::size_t>(y * kPaintN + x)];
        const double r = std::hypot(x + 0.5 - kPaintN / 2.0, y + 0.5 - kPaintN / 2.0);
        s += a; sr += a * r; srr += a * r * r;
      }
    const double mean = s > 0 ? sr / s : 0, spread = s > 0 ? std::sqrt(std::max(0.0, srr / s - mean * mean)) : 0;
    const auto& st = p.in.painter()->stamps();
    const double w = st.empty() ? 0 : st.back().w * kPaintN, pr = st.empty() ? 0 : st.back().p;
    const double hw = std::max(0.5, w * 0.5 * (0.4 + 0.6 * pr));
    std::printf("%.4f %.4f %.4f\n", spread, hw, mean);
  } else if (cmd == "served") {
    Player p(kSine, true);
    p.blocks(0.5, { { 0x90, 60, 100 }, { 0x90, 64, 100 } });
    const std::uint64_t count = p.in.paintCount();
    const auto& last = p.in.painter()->stamps();
    std::vector<float> out(Instrument::kPaintServed * Instrument::kStampFloats);
    std::uint64_t from = 0;
    const std::size_t n = p.in.paintServed(count - last.size(), out.data(), Instrument::kPaintServed, from);
    double err = 0;
    for (std::size_t k = 0; k < n && k < last.size(); k++) {
      const float* row = &out[k * Instrument::kStampFloats];
      err = std::max({ err, std::fabs(static_cast<double>(row[0] - last[k].x)), std::fabs(static_cast<double>(row[4] - last[k].w)),
                       std::fabs(static_cast<double>(row[16] - static_cast<float>(last[k].serial))) });
    }
    std::uint64_t at = 0;
    const std::size_t none = p.in.paintServed(count, out.data(), Instrument::kPaintServed, at);
    std::printf("%llu %zu %zu %.3g %zu\n", static_cast<unsigned long long>(count), last.size(), n, err, none);
  } else if (cmd == "layout") {
    const Phrase a = phrase(false), b = phrase(true);
    std::printf("%.6g %.6g %.6g %.6g %.6g %.6g %.6g %.6g\n", l1(turned(b.thick, -1), a.thick), l1(turned(b.thick, 1), a.thick),
                l1(b.thick, a.thick), l1(turned(b.wet, -1), a.wet), seriesDiff(a.glow, b.glow),
                std::max(seriesDiff(a.motion, b.motion), seriesDiff(a.memory, b.memory)), tablesDiff(a.tables, b.tables),
                static_cast<double>(a.tables.size()));
  } else if (cmd == "same") {
    PaintParams slow;
    slow.dryThin = 6; slow.dryThick = 18;
    const Phrase a = phrase(false), b = phrase(false), c = phrase(false, slow);
    std::printf("%d %d %.6g\n", a.thick == b.thick && a.wet == b.wet ? 1 : 0, a.wet == c.wet ? 1 : 0, maxDiff(a.wet, c.wet));
  } else if (cmd == "stage") {
    PictureStage level, change;
    StageResponse lr, cr;
    lr.respondsTo = 1; cr.respondsTo = 0;
    for (int k = 0; k < 600; k++) {
      level.stepPaint(0.3, 0.4, 0.5, 1000.0 / 60, false, lr);
      change.stepPaint(0.3, 0.4, 0.5, 1000.0 / 60, false, cr);
    }
    std::printf("%.5f %.5f %.5f %.5f %.5f\n", level.glow(), stageLevel(0.3), change.glow(), level.motion(), level.memory());
  } else if (cmd == "cost") {
    const double seconds = arg(2, 2);
    const double width = arg(3, 1);
    std::printf("%.5f %.5f\n", costOf(false, seconds), costOf(true, seconds, width));
  } else if (cmd == "pedal") {
    PaintParams params;
    params.hears = static_cast<unsigned>(arg(2, 15));
    Player p(R"({"shape":"sine","midiMode":"poly","oscScan":60,"atk":1,"dec":250,"sus":0,"rel":150})", true, params);
    p.blocks(0.05, { { 0xB0, 64, 127 } });
    const int melody[] = { 60, 64, 67, 72, 67, 64 };
    for (const int n : melody) {
      p.blocks(0.9, { { 0x90, static_cast<std::uint8_t>(n), 100 } });
      p.blocks(0.1, { { 0x80, static_cast<std::uint8_t>(n), 0 } });
    }
    const auto [covered, longest] = arcCover(p.in.painter()->map(), p.in.painter()->params().turn, 0.1, 6.0);
    const double wetDown = meanWet(p.in.painter()->map());
    p.blocks(2.0, { { 0xB0, 64, 0 } });
    std::printf("%.4f %d %.4f %.4f %zu\n", covered, longest, wetDown, meanWet(p.in.painter()->map()), p.in.painter()->stamps().size());
  } else if (cmd == "wheel") {
    const double wheel = arg(2, -1);
    PaintParams params;
    params.hears = static_cast<unsigned>(arg(3, 15));
    params.spatterAt = 0;  // the stroke alone
    Player p(kSine, true, params);
    if (wheel >= 0) p.blocks(0.05, { { 0xB0, 1, static_cast<std::uint8_t>(std::lround(wheel * 127)) } });
    p.blocks(1.5, { { 0x90, 57, 100 } });
    const auto& m = p.in.painter()->map();
    const auto& st = p.in.painter()->stamps();
    double laid = 0, load = 0;
    for (std::size_t q = 0; q < PaintMap::kCells; q++) laid += m.thick[q];
    if (!st.empty()) for (const float v : st.back().load) load += v / kPaintBins;
    std::printf("%.4f %.4f %.5f %.4f %.9g\n", spreadOf(m).first, st.empty() ? 0.0 : halfWidthOf(st.back()), laid, load, laid);
  } else if (cmd == "bend") {
    PaintParams params;
    params.hears = static_cast<unsigned>(arg(2, 15));
    params.spatterAt = 0;
    Player p(kSine, true, params);
    p.blocks(0.5, { { 0x90, 57, 100 } });
    const auto radiusNow = [&]() {
      for (const auto& b : p.in.painter()->brushes())
        if (b.serial && b.placed) return std::hypot(b.x - kPaintN / 2.0, b.y - kPaintN / 2.0);
      return 0.0;
    };
    const double before = radiusNow();
    double last = before, step = 0;
    int back = 0;
    // Up to the top over a second, a message every 20 ms, as a wheel sends them.
    for (int k = 1; k <= 50; k++) {
      const int v = 8192 + static_cast<int>(std::lround(8191.0 * k / 50));
      p.blocks(0.02, { { 0xE0, static_cast<std::uint8_t>(v & 127), static_cast<std::uint8_t>(v >> 7) } });
      const double r = radiusNow();
      step = std::max(step, std::fabs(r - last));
      if (r < last - 1e-9) back++;
      last = r;
    }
    for (int k = 0; k < 25; k++) {
      p.blocks(0.02);
      const double r = radiusNow();
      step = std::max(step, std::fabs(r - last));
      if (r < last - 1e-9) back++;
      last = r;
    }
    const RoundLayout round;
    std::printf("%.4f %.4f %.4f %.4f %d\n", before, last, round.radius(hzOf(59)) * kPaintN, step, back);
  } else if (cmd == "spatter") {
    const int vel = static_cast<int>(arg(2, 100));
    PaintParams params;
    params.spatterAt = arg(3, -1);
    Player p(R"({"shape":"sine","midiMode":"poly","oscScan":60,"scanStrike":100,"atk":2,"dec":300,"sus":80,"rel":400})", true, params);
    p.blocks(0.3, { { 0x90, 57, static_cast<std::uint8_t>(vel) } });
    const double ring = RoundLayout().radius(hzOf(57)) * kPaintN;
    const auto& m = p.in.painter()->map();
    double off = 0, far = 0;
    for (int y = 0; y < kPaintN; y++)
      for (int x = 0; x < kPaintN; x++) {
        const double a = m.thick[static_cast<std::size_t>(y * kPaintN + x)];
        const double d = std::fabs(std::hypot(x + 0.5 - kPaintN / 2.0, y + 0.5 - kPaintN / 2.0) - ring);
        if (d > 5) off += a;
        if (a > 1e-3) far = std::max(far, d);
      }
    std::printf("%.5f %.3f\n", off, far);
  } else if (cmd == "lean") {
    const double lean = arg(2, 1);
    PaintParams params;
    params.hears = static_cast<unsigned>(arg(3, 15));
    params.spatterAt = 0;
    Player p(kSine, true, params);
    p.blocks(0.05, { { 0xD0, static_cast<std::uint8_t>(std::lround(lean * 127)) } });
    p.blocks(1.5, { { 0x90, 57, 100 } });
    const auto& st = p.in.painter()->stamps();
    std::printf("%.4f %.4f\n", spreadOf(p.in.painter()->map()).first, st.empty() ? 0.0 : halfWidthOf(st.back()));
  } else { std::fprintf(stderr, "unknown command %s\n", cmd.c_str()); return 2; }
  return 0;
}
