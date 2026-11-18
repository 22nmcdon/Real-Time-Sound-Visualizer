// The old envelope or the drawn one through a scenario, one value per line in
// hexadecimal (%a), so two runs compare to the bit: core/tests/pieces/mseg.py.
// The scenario is envelope_cpp's language, with a shape and the two new times:
//
//   rate 44100              tone attackMs 8         shape 1;A>p.2;D>p.2;R>a.2
//   run 20000               at 4410 gate 0          at 9000 tone decayMs 40
//   reset 0                 at 0 gate 1 0.8         (also delayMs, holdMs)
//
// `mseg_cpp old <file>` plays envelope.h's Envelope, `mseg_cpp new <file>`
// mseg.h's Mseg; `new` with `--where` adds the segment, its progress and the stage.
// `mseg_cpp both <file>` plays the two side by side and prints only `same <n>`,
// or where they first part: `differ <i> <old> <new>` (the levels and stages).
// `mseg_cpp parse <text>` prints what a shape reads as.
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

#include "scope/matrix.h"
#include "scope/mseg.h"

namespace {
struct Timed { long at; std::vector<std::string> words; };

std::vector<std::string> split(const std::string& line) {
  std::istringstream in(line);
  std::vector<std::string> words;
  for (std::string w; in >> w;) words.push_back(w);
  return words;
}
}  // namespace

int main(int argc, char** argv) {
  if (argc < 3) { std::fprintf(stderr, "usage: mseg_cpp old|new|both [--where] <scenario> | parse <text>\n"); return 2; }
  // `mseg_cpp fade <mid>`: the modulation fade's travel (matrix.h) at each hundredth of its time.
  if (std::strcmp(argv[1], "fade") == 0) {
    const double mid = std::stod(argv[2]);
    for (int i = 0; i <= 100; i++) std::printf("%.17g\n", scope::fadeTravel(i / 100.0, mid));
    return 0;
  }
  // `mseg_cpp blend <a> <b> <t>`: the morph's blend of two shapes' texts (mseg_shape.h's msegBlend).
  if (std::strcmp(argv[1], "blend") == 0 && argc > 4) {
    char buf[scope::kMsegTextRoom];
    const std::size_t n = scope::msegBlend(argv[2], argv[3], std::stod(argv[4]), buf, sizeof buf);
    std::printf("%.*s\n", static_cast<int>(n), buf);
    return 0;
  }
  if (std::strcmp(argv[1], "parse") == 0) {
    scope::MsegShape sh;
    const bool ok = sh.assign(argv[2]);
    std::printf("%s count %d sustain %d loop %d decayEnd %d\n", ok ? "ok" : "no", sh.count, sh.sustainPt, sh.loopPt, sh.decayEndPt);
    for (int i = 0; i < sh.count; i++) {
      const scope::MsegSegment& g = sh.seg[static_cast<std::size_t>(i)];
      std::printf("seg %d stretch %d end %d share %.17g level %.17g bend %c %.17g\n", i, g.stretch, static_cast<int>(g.end), g.share,
                  g.level, g.bend.law, g.bend.v);
    }
    return 0;
  }
  const bool both = std::strcmp(argv[1], "both") == 0;
  const bool fresh = both || std::strcmp(argv[1], "new") == 0;
  const bool where = argc > 3 && std::strcmp(argv[2], "--where") == 0;
  std::ifstream file(argv[argc - 1]);
  std::vector<std::vector<std::string>> setup;
  std::vector<Timed> timed;
  long run = 0;
  for (std::string raw; std::getline(file, raw);) {
    const std::string line = raw.substr(0, raw.find('#'));
    auto words = split(line);
    if (words.empty()) continue;
    if (words[0] == "run") run = std::stol(words[1]);
    else if (words[0] == "at") timed.push_back({ std::stol(words[1]), { words.begin() + 2, words.end() } });
    else setup.push_back(words);
  }
  std::stable_sort(timed.begin(), timed.end(), [](const Timed& a, const Timed& b) { return a.at < b.at; });

  double rate = 48000;
  bool haveReset = false;
  double resetTo = 0;
  scope::EnvelopeTone tone;
  std::unique_ptr<scope::Envelope> old;
  std::unique_ptr<scope::Mseg> mseg;
  auto apply = [&](const std::vector<std::string>& w) {
    if (w[0] == "rate") rate = std::stod(w[1]);
    else if (w[0] == "tone") {
      const double v = std::stod(w[2]);
      if (w[1] == "attackMs") tone.attackMs = v;
      else if (w[1] == "decayMs") tone.decayMs = v;
      else if (w[1] == "sustain") tone.sustain = v;
      else if (w[1] == "releaseMs") tone.releaseMs = v;
      else if (w[1] == "delayMs") tone.delayMs = v;
      else if (w[1] == "holdMs") tone.holdMs = v;
      else { std::fprintf(stderr, "unknown tone field %s\n", w[1].c_str()); std::exit(2); }
    } else if (w[0] == "shape") {
      if (!tone.shape.assign(w.size() > 1 ? w[1] : "")) std::fprintf(stderr, "shape did not read: %s\n", w.size() > 1 ? w[1].c_str() : "");
    } else if (w[0] == "reset") {
      const double to = std::stod(w[1]);
      if (old || mseg) { if (old) old->reset(to); if (mseg) mseg->reset(to); } else { haveReset = true; resetTo = to; }
    } else if (w[0] == "gate") {
      const bool open = w[1] == "1";
      const double vel = w.size() > 2 ? std::stod(w[2]) : 1.0;
      if (old) old->gate(open, vel);
      if (mseg) mseg->gate(open, vel);
    } else { std::fprintf(stderr, "unknown command %s\n", w[0].c_str()); std::exit(2); }
  };
  for (const auto& w : setup) apply(w);
  if (fresh) mseg = std::make_unique<scope::Mseg>(rate, tone);
  if (!fresh || both) old = std::make_unique<scope::Envelope>(rate, tone);
  if (haveReset) { if (old) old->reset(resetTo); if (mseg) mseg->reset(resetTo); }
  std::size_t k = 0;
  for (long i = 0; i < run; i++) {
    while (k < timed.size() && timed[k].at == i) apply(timed[k++].words);
    if (both) {
      const double a = old->step(), b = mseg->step();
      const int sa = static_cast<int>(old->stage()), sb = static_cast<int>(mseg->stage());
      if (std::memcmp(&a, &b, sizeof a) != 0 || sa != sb) {
        std::printf("differ %ld %a %a %d %d\n", i, a, b, sa, sb);
        return 0;
      }
      continue;
    }
    // Stepped before its stage is read: a call's arguments are evaluated in no set order.
    if (old) { const double v = old->step(); std::printf("%a %d\n", v, static_cast<int>(old->stage())); }
    else {
      const double v = mseg->step();
      if (where) std::printf("%a %d %d %.6f\n", v, static_cast<int>(mseg->stage()), mseg->segment(), mseg->progress());
      else std::printf("%a %d\n", v, static_cast<int>(mseg->stage()));
    }
  }
  if (both) std::printf("same %ld\n", run);
  return 0;
}
