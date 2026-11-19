// Paint width's renders (web/docs/listening/paint-width/): the instrument's
// own core playing a phrase offline, painting at a base brush width
// (PaintParams::width), and writing what the listening page needs - the
// heard pair, the reads, every note's table, the maps, and every stamp the
// painter laid, which the look is painted from. Made from painting-step1's
// render.cpp; a script in the format core/tests/tools/instrument_cpp.cpp
// reads ("make", "midi" and "block"), then:
//
//   render <script> <out prefix> <width> [<join>]
//
// <join> is PaintParams::join: 1 (the default) a note struck alone goes on
// with the last one's stroke while that one sounds or the pedal is down, 0
// every note a stroke of its own. The script's setup is a code, or a JSON
// setup (starting with a brace), which is encoded here.
//
// Out, beside the prefix, as painting-step1's (.f32, .reads, .tables, .maps,
// .cost), and:
//
//   .stamps  a record a picture frame: int32 the frame, int32 how many
//            stamps, then that many stamps of twenty float32, as the face is
//            served them (Instrument::publishPaint's row)
//
// It reads nothing the instrument does not hold and changes nothing in it
// but the internal switch and the width, so what it writes is what the core
// would play.
#include <chrono>
#include <cstdio>
#include <fstream>
#include <string>
#include <vector>

#include "scope/instrument.h"

namespace {
std::string text(const scope::Json& v) { return v.type == scope::Json::Type::String ? scope::utf16To8(v.s) : std::string(); }

}  // namespace

int main(int argc, char** argv) {
  if (argc < 4) { std::fprintf(stderr, "usage: render <script> <prefix> <width>\n"); return 2; }
  const std::string prefix = argv[2];
  const bool paint = true;
  scope::PaintParams params;
  params.width = std::atof(argv[3]);
  if (argc > 4) params.join = std::atof(argv[4]) != 0;
  std::ifstream file(argv[1]);
  std::FILE* audio = std::fopen((prefix + ".f32").c_str(), "wb");
  std::FILE* reads = std::fopen((prefix + ".reads").c_str(), "w");
  std::FILE* tables = std::fopen((prefix + ".tables").c_str(), "wb");
  std::FILE* maps = std::fopen((prefix + ".maps").c_str(), "wb");
  std::FILE* stamps = std::fopen((prefix + ".stamps").c_str(), "wb");
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
      std::string given = text(a[3]);
      if (!given.empty() && given[0] == '{') given = *scope::encodeSetup(*scope::jsonParse(scope::utf8To16(given)));
      const auto setup = scope::Instrument::setup(given);
      if (!setup) { std::fprintf(stderr, "setup refused\n"); return 2; }
      instrument.prepare(rate, static_cast<int>(a[2].n), *setup->setup);
      instrument.setPainting(true, params);
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
      {
        const auto& sts = instrument.painter()->stamps();
        const std::int32_t head[2] = { frame, static_cast<std::int32_t>(sts.size()) };
        std::fwrite(head, sizeof(head), 1, stamps);
        for (const scope::PaintStamp& st : sts) {
          const float row[20] = { st.x, st.y, st.dx, st.dy, st.w, st.p, st.t, st.per,
                                  st.load[0], st.load[1], st.load[2], st.load[3], st.load[4], st.load[5], st.load[6], st.load[7],
                                  static_cast<float>(st.serial), static_cast<float>(st.hand), static_cast<float>(st.ink), static_cast<float>(st.note) };
          std::fwrite(row, sizeof(row), 1, stamps);
        }
      }
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
  std::fclose(maps); std::fclose(stamps);
  std::FILE* cost = std::fopen((prefix + ".cost").c_str(), "w");
  std::fprintf(cost, "%.6f %lld\n", spent, frames);
  std::fclose(cost);
  return 0;
}
