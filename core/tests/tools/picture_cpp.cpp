// The core's picture sources through the same runs as picture_js.mjs, one
// result line per command. See that file for the language.
#include <cmath>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#include "scope/noise.h"
#include "scope/picture.h"

namespace {
std::string show(double v) {
  if (std::isinf(v)) return v > 0 ? "Infinity" : "-Infinity";
  char b[40]; std::snprintf(b, sizeof b, "%.17g", v); return b;
}
double num(const std::string& w) { return std::strtod(w.c_str(), nullptr); }
std::vector<std::string> split(const std::string& s, char c) {
  std::vector<std::string> out;
  std::string part;
  std::istringstream in(s);
  while (std::getline(in, part, c)) out.push_back(part);
  return out;
}

void run(const std::vector<std::vector<std::string>>& commands) {
  scope::Phosphor phosphor;
  scope::PictureSources sources;
  scope::Plot plot;
  double persistence = 0.12, limiting = 0, gx = 1, gy = 1, ox = 0, oy = 0, spin = 0, zoom = 1;
  bool spect = false, hasFrame = false;
  std::vector<float> left, right;
  for (const auto& w : commands) {
    const std::string& cmd = w[0];
    const auto arg = [&](std::size_t i) { return i < w.size() ? w[i] : std::string(); };
    std::string extra;
    const auto shape = [&] { return scope::shapeOfPair(left.data(), right.data(), left.size(), gx, gy, ox, oy, spin, zoom); };
    if (cmd == "plot") plot = { num(arg(1)), num(arg(2)), num(arg(3)), num(arg(4)) };
    else if (cmd == "persist") persistence = num(arg(1));
    else if (cmd == "fade") phosphor.fade(persistence, arg(1) == "1");
    else if (cmd == "seg") phosphor.segment(plot, num(arg(1)), num(arg(2)), num(arg(3)), num(arg(4)), num(arg(5)));
    else if (cmd == "poly") {
      std::vector<double> xs, ys;
      for (const auto& p : split(arg(1), ';')) { const auto xy = split(p, ','); xs.push_back(num(xy[0])); ys.push_back(num(xy[1])); }
      std::vector<int> steps;
      if (!arg(2).empty()) for (const auto& s : split(arg(2), ',')) steps.push_back(static_cast<int>(num(s)));
      phosphor.deposit(plot, xs.data(), ys.data(), xs.size(), steps.empty() ? nullptr : steps.data());
    } else if (cmd == "read") extra = " read " + show(phosphor.read(num(arg(1)), num(arg(2))));
    else if (cmd == "photo") {
      if (w.size() > 3) { sources.u = num(arg(2)); sources.v = num(arg(3)); }
      sources.setOn(arg(1) == "1");
    } else if (cmd == "spect") spect = arg(1) == "1";
    else if (cmd == "pair") {
      if (arg(1) == "none") hasFrame = false;
      else {
        hasFrame = true;
        const bool ellipse = arg(1) == "ellipse";
        const std::size_t n = static_cast<std::size_t>(num(arg(ellipse ? 5 : 4)));
        left.assign(n, 0); right.assign(n, 0);
        if (ellipse) {
          const double a = num(arg(2)), b = num(arg(3)), cycles = num(arg(4)), phase = num(arg(6));
          for (std::size_t i = 0; i < n; i++) {
            left[i] = static_cast<float>(a * std::cos(2 * 3.14159265358979323846 * cycles * static_cast<double>(i) / static_cast<double>(n)));
            right[i] = static_cast<float>(b * std::sin(2 * 3.14159265358979323846 * cycles * static_cast<double>(i) / static_cast<double>(n) + phase));
          }
        } else {
          scope::Random random(static_cast<std::uint32_t>(num(arg(2))));
          const double amp = num(arg(3));
          for (std::size_t i = 0; i < n; i++) {
            left[i] = static_cast<float>((random.next() * 2 - 1) * amp);
            right[i] = static_cast<float>((random.next() * 2 - 1) * amp);
          }
        }
      }
    } else if (cmd == "view") { gx = num(arg(1)); gy = num(arg(2)); ox = num(arg(3)); oy = num(arg(4)); spin = num(arg(5)); zoom = num(arg(6)); }
    else if (cmd == "limit") limiting = num(arg(1));
    else if (cmd == "step") {
      const double elapsed = num(arg(1));
      sources.photoStep(phosphor, elapsed, spect);
      const scope::PairShape s = hasFrame ? shape() : scope::PairShape {};
      sources.pictureStep(phosphor, hasFrame ? &s : nullptr, elapsed, spect, limiting);
      const auto& v = sources.values();
      const auto& r = sources.raw();
      const auto& m = sources.meter();
      extra = " photo " + show(sources.photoRaw()) + " " + show(sources.photo())
            + " values " + show(v.round) + " " + show(v.cover) + " " + show(v.change) + " " + show(v.novelty) + " "
            + show(v.signed_) + " " + show(v.edge) + " " + show(v.bored)
            + " raw " + show(r.round) + " " + show(r.cover) + " " + show(r.change) + " " + show(r.novelty) + " "
            + show(r.signed_) + " " + show(r.edge) + " " + show(r.bored)
            + " meter " + show(m.coverage()) + " " + show(m.lit()) + " " + show(m.change()) + " " + show(m.novelty()) + " "
            + std::to_string(m.depth()) + " " + m.verdict()
            + " shape " + show(s.signed_) + " " + show(s.edge);
    } else { std::fprintf(stderr, "unknown command %s\n", cmd.c_str()); std::exit(2); }
    double a1 = 0, a2 = 0;
    const auto& g = phosphor.grid();
    for (std::size_t i = 0; i < g.size(); i++) { a1 += g[i] * static_cast<double>(i + 1); a2 += static_cast<double>(g[i]) * g[i]; }
    std::printf("%s | grid %s %s round %s%s\n", cmd.c_str(), show(a1).c_str(), show(a2).c_str(),
                show(phosphor.moments().roundness()).c_str(), extra.c_str());
  }
}
}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) return 2;
  std::ifstream file(argv[1]);
  std::vector<std::vector<std::string>> commands;
  bool in = false;
  for (std::string line; std::getline(file, line);) {
    std::istringstream words(line);
    std::vector<std::string> w;
    for (std::string x; words >> x;) w.push_back(x);
    if (w.empty()) continue;
    if (!in) { if (w[0] == "run") { in = true; commands.clear(); } continue; }
    if (w[0] == "end") { run(commands); in = false; continue; }
    commands.push_back(w);
  }
  return 0;
}
