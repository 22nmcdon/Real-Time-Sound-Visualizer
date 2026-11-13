// The core's picture sources through the same runs as picture_js.mjs, one
// result line per command. See that file for the language.
#include <array>
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
// A verdict as one word, as picture_js writes a layer's.
std::string underscored(std::string v) { for (char& c : v) if (c == ' ') c = '_'; return v; }
std::vector<std::string> split(const std::string& s, char c) {
  std::vector<std::string> out;
  std::string part;
  std::istringstream in(s);
  while (std::getline(in, part, c)) out.push_back(part);
  return out;
}

constexpr double kPiM = 3.14159265358979323846;
// A made-up grid from the words from `at` on, as shapetest's HELPERS build
// them: `ellipse a b level turn`, the same with `nudged` after it (each lit
// cell 0.02 brighter), `dot u v` (three cells square) and `full t` (every
// cell 0.8 but one, which moves with t). Each cell rounded to a float as the
// page's Float32Array rounds it.
scope::Phosphor::Grid fixture(const std::vector<std::string>& w, std::size_t at) {
  constexpr int N = scope::kPhosphorN;
  scope::Phosphor::Grid g {};
  const std::string& kind = w[at];
  const auto a = [&](std::size_t k) { return num(w[at + k]); };
  if (kind == "ellipse") {
    const double ra = a(1), rb = a(2), level = a(3), t0 = a(4);
    for (int k = 0; k < 4000; k++) {
      const double t = k / 4000.0 * 2 * kPiM, x = ra * std::cos(t), y = rb * std::sin(t);
      const double u = x * std::cos(t0) - y * std::sin(t0), v = x * std::sin(t0) + y * std::cos(t0);
      const int cx = static_cast<int>(std::floor((u + 1) / 2 * N)), cy = static_cast<int>(std::floor((1 - (v + 1) / 2) * N));
      if (cx >= 0 && cy >= 0 && cx < N && cy < N) g[static_cast<std::size_t>(cy * N + cx)] = static_cast<float>(level);
    }
    if (w.size() > at + 5 && w[at + 5] == "nudged")
      for (auto& c : g) if (c > 0) c = static_cast<float>(static_cast<double>(c) + 0.02);
  } else if (kind == "dot") {
    const int cx = std::max(0, std::min(N - 1, static_cast<int>(std::floor(a(1) * N))));
    const int cy = std::max(0, std::min(N - 1, static_cast<int>(std::floor(a(2) * N))));
    for (int dy = -1; dy <= 1; dy++) for (int dx = -1; dx <= 1; dx++) {
      const int x = cx + dx, y = cy + dy;
      if (x >= 0 && y >= 0 && x < N && y < N) g[static_cast<std::size_t>(y * N + x)] = 1;
    }
  } else if (kind == "full") {
    g.fill(0.8f);
    g[static_cast<std::size_t>(static_cast<long>(std::floor(a(1) * 60)) % (N * N))] = 0;
  } else { std::fprintf(stderr, "unknown fixture %s\n", kind.c_str()); std::exit(2); }
  return g;
}

void run(const std::vector<std::vector<std::string>>& commands) {
  scope::PictureMeter meter;
  scope::Phosphor phosphor;
  scope::PictureSources sources;
  scope::PictureStage stage;
  scope::LayerPictures layers;
  // Whether the page would have made its layers' engines yet: the first fade that wanted them.
  bool layersOn = false, twoFigures = false, layerFramed = false, madeLayers = false;
  std::array<std::vector<float>, 4> layerLanes;
  scope::Plot plot;
  double persistence = 0.12, limiting = 0, gx = 1, gy = 1, ox = 0, oy = 0, spin = 0;
  std::array<scope::StageResponse, 2> responses;  // how each hand's picture responds, the page's pictureHands
  const auto respond = [&] { auto r = responses; for (auto& x : r) x.persistence = persistence; return r; };
  bool spect = false, hasFrame = false;
  std::vector<float> left, right;
  for (const auto& w : commands) {
    const std::string& cmd = w[0];
    const auto arg = [&](std::size_t i) { return i < w.size() ? w[i] : std::string(); };
    std::string extra;
    const auto shape = [&] { return scope::shapeOfPair(left.data(), right.data(), left.size(), gx, gy, ox, oy, spin); };
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
    } else if (cmd == "lframe") {
      // A layer's two lanes, as the `pair` command makes them, from the word after the layer.
      const std::size_t at = 2 * static_cast<std::size_t>(num(arg(1)));
      const bool ellipse = arg(2) == "ellipse";
      const std::size_t n = static_cast<std::size_t>(num(arg(ellipse ? 6 : 5)));
      auto& l = layerLanes[at];
      auto& r = layerLanes[at + 1];
      l.assign(n, 0); r.assign(n, 0);
      if (ellipse) {
        const double a = num(arg(3)), b = num(arg(4)), cycles = num(arg(5)), phase = num(arg(7));
        for (std::size_t i = 0; i < n; i++) {
          l[i] = static_cast<float>(a * std::cos(2 * 3.14159265358979323846 * cycles * static_cast<double>(i) / static_cast<double>(n)));
          r[i] = static_cast<float>(b * std::sin(2 * 3.14159265358979323846 * cycles * static_cast<double>(i) / static_cast<double>(n) + phase));
        }
      } else {
        scope::Random random(static_cast<std::uint32_t>(num(arg(3))));
        const double amp = num(arg(4));
        for (std::size_t i = 0; i < n; i++) {
          l[i] = static_cast<float>((random.next() * 2 - 1) * amp);
          r[i] = static_cast<float>((random.next() * 2 - 1) * amp);
        }
      }
      layerFramed = true;
    } else if (cmd == "lon") { layersOn = arg(1) == "1"; twoFigures = arg(2) == "1"; }
    else if (cmd == "lfade") { madeLayers = madeLayers || layersOn; layers.fade(layersOn, persistence, arg(1) == "1"); }
    else if (cmd == "lpoly") {
      std::vector<double> xs, ys;
      for (const auto& p : split(arg(2), ';')) { const auto xy = split(p, ','); xs.push_back(num(xy[0])); ys.push_back(num(xy[1])); }
      std::vector<int> steps;
      if (!arg(3).empty()) for (const auto& s : split(arg(3), ',')) steps.push_back(static_cast<int>(num(s)));
      if (scope::Phosphor* g = layers.grid(static_cast<std::size_t>(num(arg(1)))))
        g->deposit(plot, xs.data(), ys.data(), xs.size(), steps.empty() ? nullptr : steps.data());
    } else if (cmd == "lstep") {
      // Layer A's lanes through the view's gains and offsets, layer B's at one and nought, as the page's stub has them.
      const scope::PairShape a = scope::shapeOfPair(layerLanes[0].data(), layerLanes[1].data(),
                                                    std::min(layerLanes[0].size(), layerLanes[1].size()), gx, gy, ox, oy, spin);
      const scope::PairShape b = scope::shapeOfPair(layerLanes[2].data(), layerLanes[3].data(),
                                                    std::min(layerLanes[2].size(), layerLanes[3].size()), 1, 1, 0, 0, spin);
      layers.step(twoFigures, layerFramed ? &a : nullptr, layerFramed ? &b : nullptr, num(arg(1)), spect, limiting, respond());
    } else if (cmd == "moves") { layers.moves[0] = scope::pictureMovesOf(arg(1), "A"); layers.moves[1] = scope::pictureMovesOf(arg(2), "B"); }
    else if (cmd == "lput") layers.stage(static_cast<int>(num(arg(1)))).put(num(arg(2)), num(arg(3)), num(arg(4)), num(arg(5)));
    else if (cmd == "sput") stage.put(num(arg(1)), num(arg(2)), num(arg(3)), num(arg(4)));
    else if (cmd == "push") {}
    else if (cmd == "resp") {
      auto& r = responses[num(arg(1)) == 1 ? 1 : 0];
      r.respondsTo = static_cast<int>(num(arg(2))); r.riseMs = num(arg(3)); r.fallMs = num(arg(4)); r.swell = arg(5) == "1";
    }
    else if (cmd == "view") { gx = num(arg(1)); gy = num(arg(2)); ox = num(arg(3)); oy = num(arg(4)); spin = num(arg(5)); }  // the zoom, arg 6, fed only edge contact, cut in P5
    else if (cmd == "limit") limiting = num(arg(1));
    // The meter, the moments and the pair's direction on made-up fixtures
    // (stage 5, step 3, batch 2: shapetest.py's numbers rows, which built
    // these in the page's JavaScript). Read by core/tests/pieces/shape.py
    // only; picture_js.mjs has no twin of them, and parity's runs never
    // name them. The fixtures are shapetest's HELPERS, line for line.
    else if (cmd == "mnew") meter = scope::PictureMeter {};
    else if (cmd == "mupd") {
      meter.update(fixture(w, 2), num(arg(1)), 0);
      extra = " meter " + show(meter.coverage()) + " " + show(meter.lit()) + " " + show(meter.change()) + " "
            + show(meter.novelty()) + " " + show(meter.drift()) + " " + underscored(meter.verdict());
    } else if (cmd == "mring" || cmd == "msegs" || cmd == "mempty") {
      scope::Moments m;
      if (cmd == "mring") {
        const double a = num(arg(1)), b = num(arg(2)), t0 = num(arg(3));
        constexpr int K = 720;
        double px = 0, py = 0;
        for (int k = 0; k <= K; k++) {
          const double t = static_cast<double>(k) / K * 2 * kPiM, x = a * std::cos(t), y = b * std::sin(t);
          const double u = x * std::cos(t0) - y * std::sin(t0), v = x * std::sin(t0) + y * std::cos(t0);
          if (k > 0) m.add(px, py, u, v, 1);
          px = u; py = v;
        }
      } else if (cmd == "msegs") {
        // Each segment `x0,y0,x1,y1` or with a level after it, as the beam's shading gives one.
        for (const auto& s : split(arg(1), ';')) {
          const auto q = split(s, ',');
          m.add(num(q[0]), num(q[1]), num(q[2]), num(q[3]), q.size() > 4 ? num(q[4]) : 1);
        }
      }
      extra = " moments " + show(m.roundness());
    } else if (cmd == "mpair") {
      // shapetest's __pair: four turns of a sine against itself at a phase, as floats, drawn unturned.
      constexpr std::size_t n = 2048;
      std::vector<float> l(n), r(n);
      const double phase = num(arg(1)), amp = num(arg(2));
      for (std::size_t i = 0; i < n; i++) {
        const double t = static_cast<double>(i) / n * 2 * kPiM * 4;
        l[i] = static_cast<float>(amp * std::sin(t)); r[i] = static_cast<float>(amp * std::sin(t + phase));
      }
      extra = " signed " + show(scope::shapeOfPair(l.data(), r.data(), n, 1, 1, num(arg(3)), 0, 0).signed_);
    }
    else if (cmd == "step") {
      const double elapsed = num(arg(1));
      sources.photoStep(phosphor, elapsed, spect);
      const scope::PairShape s = hasFrame ? shape() : scope::PairShape {};
      sources.pictureStep(phosphor, hasFrame ? &s : nullptr, elapsed, spect, limiting);
      stage.step(sources.values(), sources.raw(), elapsed, spect, sources.meter().verdict() == "running away", respond()[0]);
      const auto& v = sources.values();
      const auto& r = sources.raw();
      const auto& m = sources.meter();
      extra = " photo " + show(sources.photoRaw()) + " " + show(sources.photo())
            + " values " + show(v.round) + " " + show(v.cover) + " " + show(v.change) + " " + show(v.novelty) + " "
            + show(v.signed_) + " " + show(v.bored)
            + " raw " + show(r.round) + " " + show(r.cover) + " " + show(r.change) + " " + show(r.novelty) + " "
            + show(r.signed_) + " " + show(r.bored)
            + " meter " + show(m.coverage()) + " " + show(m.lit()) + " " + show(m.change()) + " " + show(m.novelty()) + " "
            + std::to_string(m.depth()) + " " + m.verdict()
            + " shape " + show(s.signed_)
            + " stage " + show(stage.glow()) + " " + show(stage.motion()) + " " + show(stage.memory()) + " " + show(stage.hold())
            + " pushes " + show(stage.pushGlow()) + " " + show(stage.pushMotion()) + " " + show(stage.pushMemory());
    } else { std::fprintf(stderr, "unknown command %s\n", cmd.c_str()); std::exit(2); }
    if (cmd[0] == 'l' || cmd == "moves" || cmd == "sput" || cmd == "push") {
      // Each layer's state, as picture_js prints it. A grid the page has not made yet prints as nothing.
      extra += " layers " + std::string(layers.live() ? "1" : "0") + " moves " + layers.moves[0] + " " + layers.moves[1];
      for (int l = 0; l < 2; l++) {
        const auto& p = layers.pictures(l);
        const auto& v = p.values();
        const auto& r = p.raw();
        const auto& st = layers.stage(l);
        double b1 = 0, b2 = 0;
        const auto& cells = layers.layerGrid(l).grid();
        for (std::size_t i = 0; i < cells.size(); i++) { b1 += cells[i] * static_cast<double>(i + 1); b2 += static_cast<double>(cells[i]) * cells[i]; }
        extra += " L" + std::to_string(l) + " grid " + (madeLayers ? show(b1) + " " + show(b2) : std::string("- -"))
               + " values " + show(v.round) + " " + show(v.cover) + " " + show(v.change) + " " + show(v.novelty) + " "
               + show(v.signed_) + " " + show(v.bored)
               + " raw " + show(r.round) + " " + show(r.cover) + " " + show(r.change) + " " + show(r.novelty) + " "
               + show(r.signed_) + " " + show(r.bored)
               + " verdict " + (madeLayers ? underscored(p.meter().verdict()) : std::string("-"))
               + " stage " + show(st.glow()) + " " + show(st.motion()) + " " + show(st.memory()) + " " + show(st.hold());
      }
      extra += " pushes";
      for (int l = 0; l < 2; l++)
        for (const char* key : { "glow", "motion", "memory" }) extra += " " + show(layers.push(key, l, stage));
    }
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
