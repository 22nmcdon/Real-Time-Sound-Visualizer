// The core's level, through the same runs as signal_js.mjs, one result line
// per command. See that file for the language.
#include <cmath>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#include "scope/sources.h"

namespace {
std::string show(double v) {
  if (std::isinf(v)) return v > 0 ? "Infinity" : "-Infinity";
  char b[40]; std::snprintf(b, sizeof b, "%.17g", v); return b;
}
double num(const std::string& w) { return std::strtod(w.c_str(), nullptr); }

void run(const std::vector<std::vector<std::string>>& commands) {
  scope::Level level;
  scope::LevelSource live(level);
  std::vector<float> lane;
  for (const auto& words : commands) {
    const std::string& cmd = words[0];
    const auto arg = [&](std::size_t i) { return i < words.size() ? words[i] : std::string(); };
    if (cmd == "at") {}  // the clock: the level does not read it
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
    else { std::fprintf(stderr, "unknown command %s\n", cmd.c_str()); std::exit(2); }
    std::printf("%s | env %s level %s\n", cmd.c_str(), show(level.env()).c_str(), show(live.value()).c_str());
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
