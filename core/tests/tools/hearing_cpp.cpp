// The core's hearing, through the same runs as hearing_js.mjs, one result line
// per command. See that file for the language.
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#include "scope/hearing.h"
#include "scope/keyboard.h"
#include "scope/noise.h"

namespace {
std::string show(double v) {
  if (std::isinf(v)) return v > 0 ? "Infinity" : "-Infinity";
  char b[40]; std::snprintf(b, sizeof b, "%.17g", v); return b;
}
double num(const std::string& w) { return std::strtod(w.c_str(), nullptr); }

struct Part { bool tone; int lane; double hz, amp, phase; std::uint32_t seed; };

void run(const std::vector<std::vector<std::string>>& commands) {
  scope::Matrix matrix;
  scope::HearingSources hearing(matrix);
  double rate = 48000, now = 0;
  long len = 4096, t0 = 0;
  int lanes = 2, trig = 0, xy0 = 0, xy1 = 1;
  bool running = true, gen = true;
  std::string gap = "none";
  std::vector<Part> parts;
  std::vector<int> held;
  std::vector<std::vector<float>> window;
  int touched = 0;
  (void)touched;
  for (const auto& words : commands) {
    const std::string& cmd = words[0];
    const auto arg = [&](std::size_t i) { return i < words.size() ? words[i] : std::string(); };
    if (cmd == "at") { now = num(arg(1)); hearing.setNow(now); }
    else if (cmd == "rate") rate = num(arg(1));
    else if (cmd == "len") len = static_cast<long>(num(arg(1)));
    else if (cmd == "lanes") lanes = static_cast<int>(num(arg(1)));
    else if (cmd == "tone") parts.push_back({ true, static_cast<int>(num(arg(1))), num(arg(2)), num(arg(3)), num(arg(4)), 0 });
    else if (cmd == "noise") parts.push_back({ false, static_cast<int>(num(arg(1))), 0, num(arg(3)), 0, static_cast<std::uint32_t>(num(arg(2))) });
    else if (cmd == "clear") parts.clear();
    else if (cmd == "gap") gap = arg(1);
    else if (cmd == "frame") {
      const double elapsed = num(arg(1));
      t0 += static_cast<long>(scope::jsMathRound(elapsed * rate / 1000));
      window.assign(static_cast<std::size_t>(lanes), std::vector<float>(static_cast<std::size_t>(len), 0.0f));
      for (int l = 0; l < lanes; l++) {
        for (long i = 0; i < len; i++) {
          const long at = t0 - len + i;
          double v = 0;
          for (const auto& p : parts) {
            if (p.lane != l) continue;
            if (p.tone) v += p.amp * std::sin(2 * M_PI * p.hz * static_cast<double>(at) / rate + p.phase);
            else v += p.amp * (scope::Random(static_cast<std::uint32_t>(static_cast<std::int64_t>(p.seed) * 100003 + at)).next() * 2 - 1);
          }
          if ((gap == "first" && i < len / 2) || (gap == "second" && i >= len / 2) || (gap == "early" && i < 3 * len / 8)) v = 0;
          window[static_cast<std::size_t>(l)][static_cast<std::size_t>(i)] = static_cast<float>(v);
        }
      }
      // lanes[trigSource] || lanes[0], and the X-Y pair where there is one.
      const auto lane = [&](int i) -> const float* {
        return i >= 0 && i < lanes ? window[static_cast<std::size_t>(i)].data() : nullptr;
      };
      const float* x = lane(trig) ? lane(trig) : lane(0);
      std::optional<double> heldHz;
      if (!held.empty()) {
        int low = held[0];
        for (const int n : held) low = std::min(low, n);
        heldHz = scope::midiHz(low);
      }
      // The source as the page's frame finds it, then its step.
      hearing.hears(gen);
      hearing.step(matrix, running, x, lane(xy0), lane(xy1), static_cast<std::size_t>(len), rate, elapsed, heldHz, now);
    } else if (cmd == "held") {
      held.clear();
      if (arg(1) != "-") for (std::size_t i = 1; i < words.size(); i++) held.push_back(static_cast<int>(num(words[i])));
    } else if (cmd == "running") running = arg(1) == "1";
    else if (cmd == "gen") gen = arg(1) == "1";
    else if (cmd == "trig") trig = static_cast<int>(num(arg(1)));
    else if (cmd == "xy") { xy0 = static_cast<int>(num(arg(1))); xy1 = static_cast<int>(num(arg(2))); }
    else { std::fprintf(stderr, "unknown command %s\n", cmd.c_str()); std::exit(2); }
    const auto& h = hearing.hearing();
    std::string line = cmd + " | pitch " + show(h.pitch) + " bright " + show(h.bright) + " bands";
    for (const double b : h.bands) line += " " + show(b);
    line += " width " + show(h.width) + " flux " + show(h.flux) + " raw " + show(h.fluxRaw) + " frame " + std::to_string(h.frame)
          + " want " + (h.pitchWant ? show(*h.pitchWant) : std::string("null")) + " onset " + std::to_string(h.onset.count) + " "
          + show(h.onset.last) + " " + (h.onset.armed ? "1" : "0") + " " + show(matrix.source("hear.onset")->value()) + " touched " + std::to_string(matrix.touches()) + " sources";
    for (const char* id : { "hear.pitch", "hear.bright", "hear.band1", "hear.band2", "hear.band3", "hear.band4", "hear.width",
                            "hear.flux", "hear.onset" }) {
      const scope::ModSource* s = matrix.source(id);
      line += std::string(" ") + (s->picture() ? "1" : "0") + "/" + show(s->reach);
    }
    std::printf("%s\n", line.c_str());
  }
}
}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) { std::fprintf(stderr, "usage: hearing_cpp <runs>\n"); return 2; }
  std::ifstream file(argv[1]);
  std::vector<std::string> text;
  for (std::string line; std::getline(file, line);) text.push_back(line);
  for (std::size_t i = 0; i < text.size(); i++) {
    std::istringstream in(text[i]);
    std::string first;
    in >> first;
    if (first != "run") continue;
    std::vector<std::vector<std::string>> commands;
    for (i++; i < text.size(); i++) {
      std::istringstream c(text[i]);
      std::vector<std::string> w;
      for (std::string x; c >> x;) w.push_back(x);
      if (!w.empty() && w[0] == "end") break;
      if (!w.empty()) commands.push_back(w);
    }
    run(commands);
  }
  return 0;
}
