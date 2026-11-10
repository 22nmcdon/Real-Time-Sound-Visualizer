// scope::ScanReader through the same runs as scan_js.mjs, one result line per
// frame. See that file for the language. The generator is a stand-in that
// writes down what it is sent, as the page's genSet is in scan_js.
//
// `scan_cpp --alloc` instead counts what the reader allocates once made: the
// instrument runs it on the audio thread. A figure moves under it for two
// seconds of frames, both layers reading, the hold moving; it prints what
// was allocated in the making, in the frames, and how many tables were sent,
// so a run that sent none, and so could not allocate, is told apart.
#include <array>
#include <atomic>
#include <cmath>
#include <new>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

#include "scope/scan.h"

// Replaced with malloc and free, which GCC sees inlined into the tables'
// vectors and takes for a mismatch: they are this file's new and delete.
#pragma GCC diagnostic ignored "-Wmismatched-new-delete"
namespace {
std::atomic<long> allocations { 0 };
}
void* operator new(std::size_t size) {
  allocations++;
  if (void* p = std::malloc(size ? size : 1)) return p;
  throw std::bad_alloc();
}
void operator delete(void* p) noexcept { std::free(p); }
void operator delete(void* p, std::size_t) noexcept { std::free(p); }

namespace {
std::vector<std::string> splitOn(const std::string& text, char sep) {
  std::vector<std::string> out;
  std::string part;
  std::istringstream in(text);
  while (std::getline(in, part, sep)) out.push_back(part);
  return out;
}
double num(const std::string& w) { return std::strtod(w.c_str(), nullptr); }

// What the reader asks of a generator, and what it sends written down.
struct StandIn {
  std::array<const scope::CycleTables*, 2> latest { { nullptr, nullptr } };
  std::vector<double> row;
  void set(const char* field, double value, int layer) {
    if (std::string(field) == "scanHold") { row.push_back(1); row.push_back(layer); row.push_back(value); }
  }
  void setScanTable(const scope::CycleTables* t, int layer) {
    latest[static_cast<std::size_t>(layer)] = t;
    row.push_back(2); row.push_back(layer); row.push_back(t->most); row.push_back(static_cast<double>(t->levels.size()));
    for (const auto& level : t->levels) {
      row.push_back(static_cast<double>(level.size()));
      row.insert(row.end(), level.begin(), level.end());
    }
  }
  const scope::CycleTables* scanTable(int layer) const { return latest[static_cast<std::size_t>(layer)]; }
  const scope::CycleTables* scanPrev(int) const { return nullptr; }
  const scope::CycleTables* scanNext(int) const { return nullptr; }
};
// The same asks with nothing written down, for the count - and a generator's
// tick between frames, so the latest table becomes the one faded to and that
// the one faded from, as the real one's does; a table sent that is one of
// the three is a clash, a table rewritten under the generator's feet.
struct Quiet {
  std::array<const scope::CycleTables*, 2> latest { { nullptr, nullptr } }, prev { { nullptr, nullptr } },
      next { { nullptr, nullptr } };
  long sent = 0, clashes = 0;
  void set(const char*, double, int) {}
  void setScanTable(const scope::CycleTables* t, int layer) {
    const std::size_t l = static_cast<std::size_t>(layer);
    if (t == prev[l] || t == next[l] || t == latest[l]) clashes++;
    latest[l] = t; sent++;
  }
  void tick() { for (std::size_t l = 0; l < 2; l++) { prev[l] = next[l]; next[l] = latest[l]; } }
  const scope::CycleTables* scanTable(int layer) const { return latest[static_cast<std::size_t>(layer)]; }
  const scope::CycleTables* scanPrev(int layer) const { return prev[static_cast<std::size_t>(layer)]; }
  const scope::CycleTables* scanNext(int layer) const { return next[static_cast<std::size_t>(layer)]; }
};

int countAllocations() {
  std::vector<float> a(64 * 64), b(64 * 64);
  const long before = allocations.load();
  scope::ScanReader reader;
  Quiet gen;
  const long made = allocations.load() - before;
  long framed = 0;
  for (int f = 0; f < 120; f++) {
    std::fill(a.begin(), a.end(), 0.0f); std::fill(b.begin(), b.end(), 0.0f);
    for (int k = 0; k < 600; k++) {
      const double t = 2 * M_PI * k / 600;
      const int x = static_cast<int>(32 + 14 * std::cos(t) + 3 * std::sin(f * 0.1)), y = static_cast<int>(30 + 7 * std::sin(t + 0.4));
      a[static_cast<std::size_t>(y * 64 + x)] = 1;
      b[static_cast<std::size_t>((63 - y) * 64 + x)] = 0.5f;
    }
    // Both layers reading both pictures (P7b): two readings and an average each frame.
    scope::ScanInput<float> in;
    in.live = true;
    in.depth = { { 1, 0.5 } };
    in.reads = { { f % 40 < 20 ? "both" : "B", "both" } };
    in.pictures[0] = { f % 30 < 15 ? 1.0 : 0.25, a.data(), a.size() };
    in.pictures[1] = { 1, b.data(), b.size() };
    const long start = allocations.load();
    reader.frame(gen, false, 2, in, 16.67, 3, f * 16.67 + 300);
    framed += allocations.load() - start;
    if (f % 3 != 2) gen.tick();  // ticks and frames not in step, as in the instrument
  }
  std::printf("made %ld framed %ld sent %ld clashes %ld\n", made, framed, gen.sent, gen.clashes);
  return 0;
}
}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) { std::fprintf(stderr, "usage: scan_cpp <runs> | --alloc\n"); return 2; }
  if (std::string(argv[1]) == "--alloc") return countAllocations();
  std::ifstream file(argv[1]);
  std::map<std::string, std::vector<float>> grids;
  std::unique_ptr<scope::ScanReader> reader;
  std::unique_ptr<StandIn> gen;
  double soft = 3;
  for (std::string line; std::getline(file, line);) {
    std::istringstream in(line);
    std::vector<std::string> w;
    for (std::string word; in >> word;) w.push_back(word);
    if (w.empty()) continue;
    if (w[0] == "grid") {
      std::vector<float> g;
      for (const auto& v : splitOn(w[2], ',')) g.push_back(static_cast<float>(num(v)));
      grids[w[1]] = g;
      continue;
    }
    std::map<std::string, std::string> o;
    for (std::size_t i = 1; i < w.size(); i++) {
      const auto eq = w[i].find('=');
      o[w[i].substr(0, eq)] = w[i].substr(eq + 1);
    }
    if (w[0] == "run") { reader = std::make_unique<scope::ScanReader>(); gen = std::make_unique<StandIn>(); soft = num(o["soft"]); continue; }
    if (w[0] == "end") continue;
    if (w[0] == "freeze") { reader->freeze(num(o["now"])); continue; }
    // Through scanInput, as the instrument picks each picture's grid and hold
    // and takes each layer's Reads as restoreSetup does.
    const bool live = o["live"] == "1";
    static const std::vector<float> none(64 * 64, 0.0f);
    const auto grid = [&](const std::string& key) { return o.count(key) ? &grids[o[key]] : &none; };
    const std::array<std::string, 2> reads { { scope::scanReadsOf(o.count("r0") ? o["r0"] : "A", "A"),
                                               scope::scanReadsOf(o.count("r1") ? o["r1"] : "B", "B") } };
    const auto input = scope::scanInput<float>(live, { num(o["d0"]), num(o["d1"]) }, reads, o.count("hs") ? num(o["hs"]) : 1,
                                            { o.count("h0") ? num(o["h0"]) : 1, o.count("h1") ? num(o["h1"]) : 1 },
                                            grid("gs")->data(), { grid("g0")->data(), grid("g1")->data() }, 64 * 64);
    if (w[0] == "strike") {
      // The keyboard's layersOf, from the line's split and point.
      const int note = static_cast<int>(num(o["note"]));
      const int layers = num(o["count"]) < 2 ? 1 : o["split"] == "1" ? (note >= num(o["point"]) ? 2 : 1) : 3;
      const auto box = splitOn(o["plot"], ',');
      const scope::Plot plot { num(box[0]), num(box[1]), num(box[2]), num(box[3]) };
      std::vector<double> row;
      // Each hand's Strike (G6): B's its own where the line gives one.
      reader->strike(note, num(o["vel"]), layers, num(o["amount"]), o["spect"] == "1", input, plot,
                     [&](int p, double x0, double y0, double x1, double y1, double level) {
                       row.insert(row.end(), { 5.0, static_cast<double>(p), x0, y0, x1, y1, level });
                     }, num(o.count("amountB") ? o["amountB"] : o["amount"]));
      if (row.empty()) row.push_back(6);
      for (std::size_t i = 0; i < row.size(); i++) std::printf(i ? " %.17g" : "%.17g", row[i]);
      std::printf("\n");
      continue;
    }
    reader->frame(*gen, o["spect"] == "1", static_cast<int>(num(o["count"])), input, num(o["elapsed"]), soft, num(o["now"]));
    for (std::size_t l = 0; l < 2; l++) {
      if (reader->paths[l]) {
        gen->row.insert(gen->row.end(), { 3.0, static_cast<double>(l), reader->paths[l]->cx, reader->paths[l]->cy, reader->paths[l]->r });
      } else {
        gen->row.insert(gen->row.end(), { 4.0, static_cast<double>(l) });
      }
    }
    for (std::size_t i = 0; i < gen->row.size(); i++) std::printf(i ? " %.17g" : "%.17g", gen->row[i]);
    std::printf("\n");
    gen->row.clear();
  }
  return 0;
}
