// scope::Clock, as the Brain holds it, through the same runs as clock_js.mjs,
// one result line per command. See that file for the language.
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#include "scope/restore.h"

namespace {
std::string show(double v) { char b[40]; std::snprintf(b, sizeof b, "%.17g", v); return b; }

void run(const std::vector<std::vector<std::string>>& commands) {
  std::vector<scope::Lfo> lfos(2);
  lfos[0].rate = 0.2; lfos[1].rate = 0.5;
  scope::Generator gen(48000, scope::slot::Used, lfos);
  scope::Brain brain;
  scope::linkClock(brain, lfos);
  std::vector<std::string> log;
  brain.clock.onAnchor = [&log] { log.push_back("anchor"); };
  brain.clock.onStop = [&log] { log.push_back("stop"); };
  scope::Clock& c = brain.clock;
  double now = 0;
  for (const auto& words : commands) {
    const std::string& cmd = words[0];
    const auto arg = [&](std::size_t i) { return i < words.size() ? words[i] : std::string(); };
    const auto num = [&](std::size_t i) { return std::stod(arg(i)); };
    log.clear();
    if (cmd == "at") { now = num(1); c.setNow(now); }
    else if (cmd == "tick") c.realtime(0xF8, now);
    else if (cmd == "rt") c.realtime(static_cast<int>(num(1)), now);
    else if (cmd == "start") c.start(now);
    else if (cmd == "stop") c.stop(now);
    else if (cmd == "tap") scope::tapTempo(brain, now);
    else if (cmd == "tempo") scope::setTempo(brain, num(1), now);
    else if (cmd == "step") {
      if (scope::clockFrame(brain, gen, now)) log.push_back("delayMs " + scope::jsNumberToString(*brain.echo.sent));
    }
    else if (cmd == "sync") brain.lfo[static_cast<std::size_t>(num(1))].sync = arg(2) == "-" ? "" : arg(2);
    else if (cmd == "echo") { brain.echo.sync = arg(1) == "-" ? "" : arg(1); brain.echo.ms = num(2); }
    else if (cmd == "phase") lfos[static_cast<std::size_t>(num(1))].phase = num(2);
    else { std::fprintf(stderr, "unknown command %s\n", cmd.c_str()); std::exit(2); }

    std::string line = cmd;
    for (const auto& l : log) line += " :: " + l;
    line += " | bpm " + show(c.bpm) + " set " + show(c.set) + " from " + (c.from == scope::Clock::From::Midi ? "midi" : "internal")
          + " running " + (c.running ? "1" : "0") + " base " + show(c.base) + " at " + show(c.baseAt)
          + " ticking " + (c.onTicks ? "1" : "0") + " ticks " + std::to_string(c.ticks.size()) + " taps "
          + std::to_string(c.taps.size()) + " beat " + show(c.beat(now)) + " said " + c.said(now);
    for (int i = 0; i < 2; i++) {
      const auto& l = lfos[static_cast<std::size_t>(i)];
      line += " lfo" + std::to_string(i) + " " + show(l.rate) + " " + show(l.phase) + " " + std::to_string(l.epoch);
    }
    line += " sent " + (brain.echo.sent ? show(*brain.echo.sent) : std::string("u"));
    std::printf("%s\n", line.c_str());
  }
}
}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) { std::fprintf(stderr, "usage: clock_cpp <runs>\n"); return 2; }
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
