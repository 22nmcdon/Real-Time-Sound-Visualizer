// Painting, step 1's renders: the instrument's own core playing a phrase
// offline, on the trace as it ships or painting (core/include/scope/paint.h),
// and writing what the listening page needs. A script in the format
// core/tests/tools/instrument_cpp.cpp reads ("make", "midi" and "block" are
// all it uses), then:
//
//   render <script> <out prefix> trace
//   render <script> <out prefix> paint <dryThin> <dryThick> [<layout>]
//
// <layout> is "round" (the default) or "turned" (round turned a quarter, for
// the check that a layout moves only where paint lands). Out, beside the
// prefix:
//
//   .f32     the heard pair, float32 stereo interleaved
//   .reads   a line a picture frame: t glow motion memory hold, then on paint
//            the map's cover moved repaint covered intoWet ontoDry ontoBare
//   .tables  a record a picture frame and reading, float32: the frame, the
//            voice's note (or -1 - layer for the trace's layer table), its
//            level, and the richest level of its table, 512 samples
//   .maps    on paint, every sixth frame: the time, then the thickness and
//            the wetness, 128 by 128 each, float32
//   .cost    the seconds spent in the instrument, and the samples rendered
//
// It reads nothing the instrument does not hold and changes nothing in it
// but the internal switch, so what it writes is what the core would play.
#include <chrono>
#include <cstdio>
#include <fstream>
#include <string>
#include <vector>

#include "scope/instrument.h"

namespace {
std::string text(const scope::Json& v) { return v.type == scope::Json::Type::String ? scope::utf16To8(v.s) : std::string(); }

// Round, turned a quarter: the same strokes landing elsewhere, and each note reading its ring there.
class TurnedLayout : public scope::PaintLayout {
 public:
  explicit TurnedLayout(const scope::PaintParams& p) : round_(p), turn_(p.turn) {}
  scope::PaintPoint at(double seconds, double hz) const override { return round_.at(seconds + turn_ / 4, hz); }
  scope::PaintRing ring(double hz) const override { return round_.ring(hz); }

 private:
  scope::RoundLayout round_;
  double turn_;
};
}  // namespace

int main(int argc, char** argv) {
  if (argc < 4) { std::fprintf(stderr, "usage: render <script> <prefix> trace | paint <thin> <thick> [round|turned]\n"); return 2; }
  const std::string prefix = argv[2], mode = argv[3];
  const bool paint = mode == "paint";
  scope::PaintParams params;
  if (paint) {
    if (argc < 6) { std::fprintf(stderr, "paint needs <thin> <thick>\n"); return 2; }
    params.dryThin = std::atof(argv[4]);
    params.dryThick = std::atof(argv[5]);
  }
  const std::string layout = argc > 6 ? argv[6] : "round";
  std::ifstream file(argv[1]);
  std::FILE* audio = std::fopen((prefix + ".f32").c_str(), "wb");
  std::FILE* reads = std::fopen((prefix + ".reads").c_str(), "w");
  std::FILE* tables = std::fopen((prefix + ".tables").c_str(), "wb");
  std::FILE* maps = paint ? std::fopen((prefix + ".maps").c_str(), "wb") : nullptr;
  scope::Instrument instrument;
  std::vector<std::uint8_t> midi;
  std::vector<std::size_t> lengths;
  double rate = 48000, spent = 0;
  long long frames = 0;
  int seen = -1, frame = 0;
  for (std::string line; std::getline(file, line);) {
    if (line.empty()) continue;
    const auto parsed = scope::jsonParse(scope::utf8To16(line));
    if (!parsed || parsed->type != scope::Json::Type::Array || parsed->a.empty()) { std::fprintf(stderr, "bad line\n"); return 2; }
    const auto& a = parsed->a;
    const std::string cmd = text(a[0]);
    if (cmd == "make") {
      rate = a[1].n;
      const auto setup = scope::Instrument::setup(text(a[3]));
      if (!setup) { std::fprintf(stderr, "setup refused\n"); return 2; }
      instrument.prepare(rate, static_cast<int>(a[2].n), *setup->setup);
      if (paint) {
        instrument.setPainting(true, params);
        if (layout == "turned") instrument.painter()->setLayout(std::make_unique<TurnedLayout>(params));
      }
    } else if (cmd == "midi") {
      for (std::size_t i = 1; i < a.size() && i < 4; ++i) midi.push_back(static_cast<std::uint8_t>(a[i].n));
      lengths.push_back(std::min<std::size_t>(a.size() - 1, 3));
    } else if (cmd == "block") {
      const std::size_t n = static_cast<std::size_t>(a[1].n);
      std::vector<float> l(n), r(n), inter(2 * n);
      std::vector<scope::Instrument::Event> events;
      std::size_t at = 0;
      for (const std::size_t length : lengths) { events.push_back({ 0, midi.data() + at, length }); at += length; }
      const auto t0 = std::chrono::steady_clock::now();
      instrument.block(l.data(), r.data(), static_cast<int>(n), events.data(), events.size(), nullptr, nullptr, 0, nullptr);
      spent += std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
      midi.clear(); lengths.clear();
      for (std::size_t k = 0; k < n; ++k) { inter[2 * k] = l[k]; inter[2 * k + 1] = r[k]; }
      std::fwrite(inter.data(), sizeof(float), inter.size(), audio);
      frames += static_cast<long long>(n);
      // A picture frame has gone by when the phosphor has faded again.
      const int now = instrument.picture().phosphor().frames();
      if (now == seen) continue;
      seen = now;
      const double t = static_cast<double>(frames) / rate;
      const auto& st = instrument.picture().stage();
      std::fprintf(reads, "%.6f %.6f %.6f %.6f %.6f", t, st.glow(), st.motion(), st.memory(), st.hold());
      const auto& g = instrument.generator();
      std::vector<float> rec(3 + scope::kScanTable);
      const auto table = [&](float who, float level, const scope::CycleTables* tab) {
        if (!tab || tab->levels.empty()) return;
        rec[0] = static_cast<float>(frame); rec[1] = who; rec[2] = level;
        for (std::size_t i = 0; i < scope::kScanTable; i++) rec[3 + i] = static_cast<float>(tab->levels[0][i]);
        std::fwrite(rec.data(), sizeof(float), rec.size(), tables);
      };
      if (paint) {
        const auto& p = instrument.painter()->reads();
        std::fprintf(reads, " %.6f %.6f %.6f %.6f %.6g %.6g %.6g", p.cover, p.moved, p.repaint, p.covered, p.intoWet, p.ontoDry, p.ontoBare);
        for (int layer = 0; layer < 2; layer++)
          for (const auto& v : layer ? g.voicesB() : g.voices())
            if (!v.gone && v.painted) table(static_cast<float>(v.note), static_cast<float>(v.env.level()), v.paintTable);
        if (frame % 6 == 0) {
          const auto& m = instrument.painter()->map();
          const float tt = static_cast<float>(t);
          std::fwrite(&tt, sizeof(float), 1, maps);
          std::fwrite(m.thick.data(), sizeof(float), m.thick.size(), maps);
          std::fwrite(m.wet.data(), sizeof(float), m.wet.size(), maps);
        }
      } else {
        for (int layer = 0; layer < 2; layer++) table(static_cast<float>(-1 - layer), 1, g.scanTable(layer));
      }
      std::fprintf(reads, "\n");
      frame++;
    } else { std::fprintf(stderr, "unknown command %s\n", cmd.c_str()); return 2; }
  }
  std::fclose(audio); std::fclose(reads); std::fclose(tables);
  if (maps) std::fclose(maps);
  std::FILE* cost = std::fopen((prefix + ".cost").c_str(), "w");
  std::fprintf(cost, "%.6f %lld\n", spent, frames);
  std::fclose(cost);
  return 0;
}
