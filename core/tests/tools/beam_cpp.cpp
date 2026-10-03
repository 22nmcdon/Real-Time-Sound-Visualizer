// The core's beam walk through the same runs as beam_js.mjs, one result line
// per command: a frame from scope::capture, laid into the grid by
// scope::drawPicture. See that file for the language.
#include <cmath>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#include "scope/beam.h"
#include "scope/capture.h"
#include "scope/noise.h"

namespace {
std::string show(double v) {
  if (std::isinf(v)) return v > 0 ? "Infinity" : "-Infinity";
  char b[40]; std::snprintf(b, sizeof b, "%.17g", v); return b;
}
double num(const std::string& w) { return std::strtod(w.c_str(), nullptr); }
void run(const std::vector<std::vector<std::string>>& commands) {
  scope::View v;
  v.lagOn = false;
  scope::Screen screen;
  scope::Canvas canvas { 800, 500, false, 0 };
  scope::Beam beam;
  scope::Phosphor phosphor;
  double rate = 48000, capacity = HUGE_VAL;
  int chans = 2;
  bool lanes = false;
  std::size_t length = 0;
  std::vector<scope::Lane> buffers;
  for (const auto& w : commands) {
    const std::string& cmd = w[0];
    const auto arg = [&](std::size_t i) { return i < w.size() ? w[i] : std::string(); };
    const auto ch = [&] {
      const std::size_t c = static_cast<std::size_t>(num(arg(1)));
      if (v.channels.size() <= c) v.channels.resize(c + 1);
      return c;
    };
    std::string extra;
    if (cmd == "rate") rate = num(arg(1));
    else if (cmd == "cap") capacity = arg(1) == "inf" ? HUGE_VAL : num(arg(1));
    else if (cmd == "draw") {
      scope::CaptureSource src;
      src.rate = rate; src.capacity = capacity; src.channels = chans; src.lanes = lanes;
      src.latest = [&](std::size_t n) {
        std::vector<scope::Lane> out;
        for (int c = 0; c < chans; c++) {
          const scope::Lane& b = buffers[static_cast<std::size_t>(c)];
          scope::Lane o(n, 0.0f);
          const std::size_t take = std::min(n, b.size());
          std::copy(b.end() - static_cast<std::ptrdiff_t>(take), b.end(), o.end() - static_cast<std::ptrdiff_t>(take));
          out.push_back(std::move(o));
        }
        return out;
      };
      v.channels.resize(static_cast<std::size_t>(std::max(2, scope::laneCount(v, src))));
      const scope::Frame f = scope::capture(v, src);
      const scope::Plot p = scope::drawPicture(beam, phosphor, v, screen, src, f, canvas, num(arg(1)));
      canvas.resized = false;
      double a1 = 0, a2 = 0;
      const auto& g = phosphor.grid();
      for (std::size_t i = 0; i < g.size(); i++) { a1 += g[i] * static_cast<double>(i + 1); a2 += static_cast<double>(g[i]) * g[i]; }
      extra = " | grid " + show(a1) + " " + show(a2) + " round " + show(phosphor.moments().roundness())
            + " frames " + std::to_string(phosphor.frames()) + " plot " + show(p.x) + " " + show(p.y) + " " + show(p.w)
            + " " + show(p.h) + " refs";
      for (const auto& [k, r] : beam.refs()) extra += " " + k + " " + show(r);
    }
    else if (cmd == "canvas") { canvas.w = num(arg(1)); canvas.h = num(arg(2)); }
    else if (cmd == "resize") canvas.resized = true;
    else if (cmd == "name") canvas.widestName = num(arg(1));
    else if (cmd == "display") screen.display = arg(1);
    else if (cmd == "persist") screen.persistence = num(arg(1));
    else if (cmd == "zoom") screen.zoom = num(arg(1));
    else if (cmd == "stack") screen.stack = arg(1) == "1";
    else if (cmd == "pair") screen.xyPair = { static_cast<int>(num(arg(1))), static_cast<int>(num(arg(2))) };
    else if (cmd == "figures") {
      screen.figures.clear();
      if (arg(1) != "none") {
        std::istringstream list(arg(1));
        for (std::string one; std::getline(list, one, ';');) {
          const auto comma = one.find(',');
          screen.figures.push_back({ static_cast<int>(num(one.substr(0, comma))), static_cast<int>(num(one.substr(comma + 1))) });
        }
      }
    }
    else if (cmd == "beam") screen.beam = arg(1);
    else if (cmd == "beamxy") screen.beamXY = arg(1) == "1";
    else if (cmd == "beamyt") screen.beamYT = arg(1) == "1";
    else if (cmd == "offset") v.channels[ch()].offset = num(arg(2));
    else if (cmd == "forget") beam.clear();
    else if (cmd == "chans") chans = static_cast<int>(num(arg(1)));
    else if (cmd == "lanes") lanes = arg(1) == "1";
    else if (cmd == "signal") { length = static_cast<std::size_t>(num(arg(1))); buffers.assign(6, scope::Lane(length, 0.0f)); }
    else if (cmd == "add") {
      scope::Lane& b = buffers[ch()];
      const std::string kind = arg(2);
      if (kind == "sine" || kind == "square") {
        const double amp = num(arg(3)), hz = num(arg(4)), phase = num(arg(5));
        for (std::size_t i = 0; i < length; i++) {
          const double s = std::sin(2 * 3.14159265358979323846 * hz * static_cast<double>(i) / rate + phase);
          b[i] = static_cast<float>(b[i] + amp * (kind == "sine" ? s : s >= 0 ? 1 : -1));
        }
      } else if (kind == "noise") {
        scope::Random r(static_cast<std::uint32_t>(num(arg(3))));
        const double amp = num(arg(4));
        for (std::size_t i = 0; i < length; i++) b[i] = static_cast<float>(b[i] + (r.next() * 2 - 1) * amp);
      } else for (std::size_t i = 0; i < length; i++) b[i] = static_cast<float>(b[i] + num(arg(3)));
    }
    else if (cmd == "tb") v.timebase = static_cast<int>(num(arg(1)));
    else if (cmd == "pos") v.position = num(arg(1));
    else if (cmd == "posmod") v.positionMod = num(arg(1));
    else if (cmd == "holdoff") v.holdoffMs = num(arg(1));
    else if (cmd == "level") v.level = num(arg(1));
    else if (cmd == "edge") v.rising = arg(1) == "rising";
    else if (cmd == "trig") v.trigSource = static_cast<int>(num(arg(1)));
    else if (cmd == "ac") v.channels[ch()].ac = arg(2) == "1";
    else if (cmd == "achz") v.acHz = num(arg(1));
    else if (cmd == "fs") v.channels[ch()].fsDb = num(arg(2));
    else if (cmd == "fsmod") v.channels[ch()].fsMod = num(arg(2));
    else if (cmd == "on") v.channels[ch()].on = arg(2) == "1";
    else if (cmd == "filter") {
      if (arg(1) == "off") v.filter.on = false;
      else { v.filter.on = true; v.filter.type = arg(1); v.filter.cutoff = num(arg(2)); v.filter.res = num(arg(3)); }
    } else if (cmd == "fmod") { v.cutoffMod = num(arg(1)); v.resMod = num(arg(2)); }
    else if (cmd == "lag") { v.lagOn = true; v.lagMs = num(arg(1)); }
    else if (cmd == "lagoff") v.lagOn = false;
    else if (cmd == "lagmod") v.lagMod = num(arg(1));
    else if (cmd == "lagauto") {
      v.lagAuto = arg(1) != "none";
      v.lagLock = arg(1) == "none" ? std::nullopt : std::optional<double>(num(arg(1)));
    }
    else if (cmd == "ms") v.midSide = arg(1) == "1";
    else if (cmd == "rot") v.rotate = num(arg(1));
    else if (cmd == "rotmod") v.rotateMod = num(arg(1));
    else if (cmd == "shaping") v.shaping = arg(1) == "1";
    else if (cmd == "measure") v.measurePost = arg(1) == "1";
    else { std::fprintf(stderr, "unknown command %s\n", cmd.c_str()); std::exit(2); }
    std::printf("%s%s\n", cmd.c_str(), extra.c_str());
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
