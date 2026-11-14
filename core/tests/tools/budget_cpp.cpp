// The voices' budget, on the core (stage 5, step 3, batch 6): scope::Generator's
// governor (generator.h, govern and voiceCost) driven as budgettest.py drove
// the page's makeGeneratorCore on ?brain=js - a block of any length at once,
// the voices laid on directly, and what the governor did read back voice by
// voice - and timed natively. core/tests/pieces/budget.py reads it.
//
// A script of lines, done in order:
//
//   gen RATE                   a fresh generator with two still oscillators, as the page's
//                              budgettest made one (`make`)
//   setup JSON                 a fresh generator with the setup (an object) migrated as the
//                              page's loadCorpus migrates the old library (v:7 laid in) and
//                              restored into it by the core's restoreSetup, as a load does
//   preset INDEX               the same with the bank's preset at INDEX (presets.h), as is
//   routes                     the setup's routings, from the core's own matrix, on the generator
//   set FIELD VALUE [LAYER]    a number, true or false, or a word
//   voices LAYER none|null|NOTE/HZ/VEL/ROLE+...
//   run N                      one block of N samples (the governor asks once a block)
//   heard N                    the same, printing the heard pair's left lane: `heard v v ...`
//   budget                     `budget units askedA askedB unisonA unisonB askedFactor factor silenced voicesA voicesB`
//   pool                       `pool` then a word a voice, A's then B's: LAYER:NOTE:HELD:CUT, the
//                              last two 0 or 1 (cut is the core's `cutting`: gone or fading); a
//                              voice's role, and so whether it is inner, is the caller's to know
//   shape                      `shape NAME` - layer A's shape, for the scan's count of shapes
//   layered                    `layered 1` when the setup restored splits or layers the keyboard
//   time [TRIES]               `time MS`: the best of TRIES (three if not given) one-second
//                              blocks, in milliseconds
//   --bank                     (as the only argument) the bank's preset count
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

#include "scope/instrument.h"
#include "scope/presets.h"

namespace {

std::vector<std::string> splitOn(const std::string& text, char sep) {
  std::vector<std::string> out;
  std::string part;
  std::istringstream in(text);
  while (std::getline(in, part, sep)) out.push_back(part);
  return out;
}
double num(const std::string& w) { return std::strtod(w.c_str(), nullptr); }
bool isNumber(const std::string& w) {
  char* end = nullptr;
  std::strtod(w.c_str(), &end);
  return end != w.c_str() && *end == '\0';
}

// A generator and what a setup is restored through, made together and kept together.
struct Rig {
  std::vector<scope::Lfo> lfos;
  std::unique_ptr<scope::Generator> gen;
  std::unique_ptr<scope::GeneratorNotes> notes;
  std::unique_ptr<scope::Keyboard> keys;
  std::unique_ptr<scope::Brain> brain;
  std::unique_ptr<scope::Matrix> matrix;
  std::unique_ptr<scope::CoreSources> sources;
  double rate = 44100;

  void make(double r) {
    sources.reset(); matrix.reset(); keys.reset(); notes.reset(); brain.reset(); gen.reset();
    rate = r;
    // The page's `still()`: a sine at 0.2 Hz with no depth, so no oscillator moves anything.
    lfos.assign(2, scope::Lfo {});
    for (auto& l : lfos) { l.rate = 0.2; l.depth = 0; }
    gen = std::make_unique<scope::Generator>(rate, scope::slot::Used, lfos);
    notes = std::make_unique<scope::GeneratorNotes>(*gen);
    keys = std::make_unique<scope::Keyboard>(*notes);
    brain = std::make_unique<scope::Brain>();
    matrix = std::make_unique<scope::Matrix>();
    sources = std::make_unique<scope::CoreSources>(*matrix, *gen, lfos, *keys);
  }
  void restore(const scope::Json& setup) {
    make(rate);
    scope::restoreSetup(setup, *brain, *gen, *keys, *matrix, lfos);
  }
};

int script(const char* path) {
  std::ifstream file(path);
  Rig rig;
  rig.make(44100);
  std::vector<std::vector<float>> bufs(6);
  const auto block = [&](long n) {
    for (auto& b : bufs) b.assign(static_cast<std::size_t>(n), 0.0f);
    rig.gen->block(bufs[0].data(), bufs[1].data(), static_cast<int>(n), bufs[2].data(), bufs[3].data(), bufs[4].data(), bufs[5].data());
  };
  for (std::string line; std::getline(file, line);) {
    std::istringstream in(line);
    std::vector<std::string> w;
    for (std::string x; in >> x;) w.push_back(x);
    if (w.empty()) continue;
    const auto arg = [&](std::size_t k) { return k < w.size() ? w[k] : std::string(); };
    const std::string& cmd = w[0];
    if (cmd == "gen") rig.make(num(arg(1)));
    else if (cmd == "setup") {
      const auto parsed = scope::jsonParse(scope::utf8To16(line.substr(line.find('{'))));
      if (!parsed) { std::fprintf(stderr, "the setup does not read\n"); return 2; }
      scope::Json setup = *parsed;
      setup.set("v", scope::Json::number(7));
      if (!scope::migrateSetup(setup)) { std::printf("refused\n"); continue; }
      rig.restore(setup);
    } else if (cmd == "preset") {
      const auto& list = scope::presets();
      const auto k = static_cast<std::size_t>(num(arg(1)));
      if (k >= list.size()) { std::fprintf(stderr, "no preset %zu\n", k); return 2; }
      rig.restore(list[k].setup);
    } else if (cmd == "routes") rig.gen->setRoutes(rig.matrix->routes(0));
    else if (cmd == "set") {
      const int layer = arg(3).empty() ? 0 : static_cast<int>(num(arg(3)));
      const std::string v = arg(2);
      if (v == "true" || v == "false") rig.gen->set(arg(1), v == "true" ? 1.0 : 0.0, layer);
      else if (isNumber(v)) rig.gen->set(arg(1), num(v), layer);
      else rig.gen->set(arg(1), std::string_view(v), layer);
    } else if (cmd == "voices") {
      const int layer = static_cast<int>(num(arg(1)));
      if (arg(2) == "null") rig.gen->setVoices(nullptr, layer);
      else {
        std::vector<scope::NoteWant> list;
        if (arg(2) != "none") {
          for (const auto& n : splitOn(arg(2), '+')) {
            const auto f = splitOn(n, '/');
            list.push_back({ static_cast<int>(num(f[0])), num(f[1]), num(f[2]), f[3] });
          }
        }
        rig.gen->setVoices(&list, layer);
      }
    } else if (cmd == "run") block(std::strtol(arg(1).c_str(), nullptr, 10));
    else if (cmd == "heard") {
      block(std::strtol(arg(1).c_str(), nullptr, 10));
      std::printf("heard");
      for (const float v : bufs[2]) std::printf(" %.9g", static_cast<double>(v));
      std::printf("\n");
    } else if (cmd == "budget") {
      const auto& b = rig.gen->budget();
      std::printf("budget %.17g %d %d %d %d %d %d %d %zu %zu\n", b.units, b.asked[0], b.asked[1], b.unison[0], b.unison[1],
                  b.askedFactor, b.factor, b.silenced, rig.gen->voices().size(), rig.gen->voicesB().size());
    } else if (cmd == "pool") {
      std::printf("pool");
      for (int l = 0; l < 2; l++)
        for (const auto& v : l ? rig.gen->voicesB() : rig.gen->voices())
          std::printf(" %d:%d:%d:%d", l, v.note, v.held ? 1 : 0, scope::Generator::cutting(v) ? 1 : 0);
      std::printf("\n");
    } else if (cmd == "shape") std::printf("shape %s\n", rig.gen->tone().shapeName.c_str());
    else if (cmd == "layered") std::printf("layered %d\n", rig.keys->settings().layers != scope::LayerMode::Off ? 1 : 0);
    else if (cmd == "time") {
      // The best of several: what the code costs, not what else the machine did during one of them.
      const long n = static_cast<long>(rig.rate);
      const int tries = arg(1).empty() ? 3 : std::max(1, static_cast<int>(num(arg(1))));
      double best = 1e300;
      for (int r = 0; r < tries; r++) {
        for (auto& b : bufs) b.assign(static_cast<std::size_t>(n), 0.0f);
        const auto t0 = std::chrono::steady_clock::now();
        rig.gen->block(bufs[0].data(), bufs[1].data(), static_cast<int>(n), bufs[2].data(), bufs[3].data(), bufs[4].data(), bufs[5].data());
        const double ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
        if (ms < best) best = ms;
      }
      std::printf("time %.4f\n", best);
    } else { std::fprintf(stderr, "unknown command %s\n", cmd.c_str()); return 2; }
  }
  return 0;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) { std::fprintf(stderr, "usage: budget_cpp SCRIPT | --bank\n"); return 2; }
  if (std::string(argv[1]) == "--bank") { std::printf("%zu\n", scope::presets().size()); return 0; }
  return script(argv[1]);
}
