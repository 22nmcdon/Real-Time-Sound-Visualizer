// The core's level and threshold, through the same runs as signal_js.mjs, one
// result line per command. See that file for the language.
#include <cmath>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#include "scope/restore.h"
#include "scope/sources.h"

namespace {
std::string show(double v) {
  if (std::isinf(v)) return v > 0 ? "Infinity" : "-Infinity";
  char b[40]; std::snprintf(b, sizeof b, "%.17g", v); return b;
}
double num(const std::string& w) { return std::strtod(w.c_str(), nullptr); }

// The run's stand-ins: a value it sets, an event source, and the same value
// marked as the picture's.
struct Stand : scope::ModSource {
  Stand(const char* id, const double& v) : ModSource(id), v_(v) {}
  double value() const override { return v_; }
  const double& v_;
};

void run(const std::vector<std::vector<std::string>>& commands) {
  double testValue = 0;
  scope::Matrix matrix;
  scope::Brain brain;
  std::vector<scope::Lfo> lfos(2);
  scope::Generator gen(48000, scope::slot::Used, lfos);
  scope::GeneratorNotes notes(gen);
  scope::Keyboard keys(notes);
  scope::Level level;
  scope::LevelSource live(level);
  Stand v("test.v", testValue), e("test.e", testValue), pic("test.p", testValue);
  e.event = true;
  pic.fromPicture = true;
  for (scope::ModSource* s : { static_cast<scope::ModSource*>(&live), static_cast<scope::ModSource*>(&v),
                               static_cast<scope::ModSource*>(&e), static_cast<scope::ModSource*>(&pic) })
    matrix.registerSource(s);
  scope::BrainSources sources(matrix, brain);
  const scope::ModSource* th = matrix.source("threshold");
  std::vector<float> lane;
  double now = 0;
  for (const auto& words : commands) {
    const std::string& cmd = words[0];
    const auto arg = [&](std::size_t i) { return i < words.size() ? words[i] : std::string(); };
    if (cmd == "at") { now = num(arg(1)); brain.clock.setNow(now); }
    else if (cmd == "sine") {
      const double amp = num(arg(1)), cycles = num(arg(2));
      const auto n = static_cast<std::size_t>(num(arg(3)));
      lane.assign(n, 0.0f);
      for (std::size_t i = 0; i < n; i++)
        lane[i] = static_cast<float>(amp * std::sin(2 * M_PI * cycles * static_cast<double>(i) / static_cast<double>(n)));
    } else if (cmd == "noise") {
      scope::Random next(static_cast<std::uint32_t>(num(arg(1))));
      const double amp = num(arg(2));
      const auto n = static_cast<std::size_t>(num(arg(3)));
      lane.assign(n, 0.0f);
      for (std::size_t i = 0; i < n; i++) lane[i] = static_cast<float>((next.next() * 2 - 1) * amp);
    } else if (cmd == "frame") level.update(lane.data(), lane.size(), num(arg(1)));
    else if (cmd == "v") testValue = num(arg(1));
    else if (cmd == "watch") scope::setThresholdWatch(brain, scope::toU16(arg(1)));
    else if (cmd == "level") brain.threshLevel = num(arg(1));
    else if (cmd == "thresh") sources.frame(brain, matrix, now);
    else if (cmd == "drop") matrix.unregisterSource("test.v");
    else if (cmd == "add") matrix.registerSource(&v);
    else if (cmd == "restore") {
      scope::Json setup = scope::Json::object();
      setup.set("threshWatch", scope::Json::string(std::string_view(arg(1))));
      setup.set("threshLevel", scope::Json::number(num(arg(2))));
      scope::restoreSetup(setup, brain, gen, keys, matrix, lfos);
    }
    else { std::fprintf(stderr, "unknown command %s\n", cmd.c_str()); std::exit(2); }
    std::printf("%s | env %s level %s count %d armed %d last %s flash %s value %s loop %d\n", cmd.c_str(), show(level.env()).c_str(),
                show(live.value()).c_str(), th->count(), brain.thresh.armed ? 1 : 0, show(brain.thresh.last).c_str(),
                show(brain.thresh.flash).c_str(), show(th->value()).c_str(), th->picture() ? 1 : 0);
  }
}
}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) { std::fprintf(stderr, "usage: signal_cpp <runs>\n"); return 2; }
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
