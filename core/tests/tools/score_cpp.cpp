// The core's score, MIDI out and notes out, as the Brain holds them and on
// its clock, linked as linkClock links them, through the same runs as
// score_js.mjs, one result line per command. See that file for the language.
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#include "scope/restore.h"

namespace {
std::string show(double v) { char b[40]; std::snprintf(b, sizeof b, "%.17g", v); return b; }
double num(const std::string& w) { return std::strtod(w.c_str(), nullptr); }

void run(const std::vector<std::vector<std::string>>& commands) {
  std::vector<std::string> log;
  scope::MidiOut out([&log](const std::uint8_t* b, int n) {
    std::string line = "send ";
    for (int i = 0; i < n; i++) line += (i ? "," : "") + std::to_string(b[i]);
    log.push_back(line);
  });
  std::vector<scope::Lfo> lfos(2);
  scope::Brain brain;
  brain.out = &out;
  scope::linkClock(brain, lfos);
  scope::Clock& clock = brain.clock;
  scope::ScoreState& score = brain.score;
  scope::NotesOut& notes = brain.notesOut;
  std::vector<float> grid(64 * 64, 0.0f);
  bool running = true, crossOn = false;
  double keyRoot = 0;
  std::string keyScale = "chromatic";
  int noteX = 60, noteY = 67, pluckNote = 60;
  std::array<int, 2> counts { 0, 0 };
  const scope::Strike strike = [&log](double hz, double v) { log.push_back("strike " + show(hz) + " " + show(v)); };
  double now = 0;
  for (const auto& words : commands) {
    const std::string& cmd = words[0];
    const auto arg = [&](std::size_t i) { return i < words.size() ? words[i] : std::string(); };
    log.clear();
    if (cmd == "at") { now = num(arg(1)); clock.setNow(now); }
    else if (cmd == "tempo") clock.setTempo(num(arg(1)), now);
    else if (cmd == "start") clock.start(now);
    else if (cmd == "stop") clock.stop(now);
    else if (cmd == "tick") clock.tick(now);
    else if (cmd == "midistart") clock.start(now, true);
    else if (cmd == "frame") {
      scope::crossStep(notes, now, crossOn, counts, noteX, noteY, &out);
      scope::scoreTick(score, now, running, clock, grid.data(), scope::keyMask(keyRoot, keyScale), strike, &out);
      scope::endDue(notes.pluckOffs, now, &out);
    } else if (cmd == "running") running = arg(1) == "1";
    else if (cmd == "key") { keyRoot = num(arg(1)); keyScale = arg(2); }
    else if (cmd == "score") {
      const auto orElse = [](double v, double d) { return v == 0 || std::isnan(v) ? d : v; };
      score.step = arg(2);
      score.voices = orElse(num(arg(3)), 1);
      score.low = orElse(num(arg(4)), 48);
      score.octaves = orElse(num(arg(5)), 3);
      score.on = arg(1) == "on";
      if (!score.on) scope::scoreStop(score, &out);
    } else if (cmd == "grid") {
      scope::Random next(static_cast<std::uint32_t>(num(arg(1))));
      const double fill = num(arg(2));
      for (auto& g : grid) g = next.next() < fill ? static_cast<float>(next.next()) : 0.0f;
    } else if (cmd == "cell") grid[static_cast<std::size_t>(num(arg(1)) * 64 + num(arg(2)))] = static_cast<float>(num(arg(3)));
    else if (cmd == "port") out.choose(arg(1) == "1", static_cast<int>(num(arg(2))));
    else if (cmd == "panic") out.panic();
    else if (cmd == "pluck") scope::pluckFire(notes, pluckNote, num(arg(1)), now, strike, &out);
    else if (cmd == "pluckNote") pluckNote = static_cast<int>(num(arg(1)));
    else if (cmd == "cross") { crossOn = arg(1) == "1"; noteX = static_cast<int>(num(arg(2))); noteY = static_cast<int>(num(arg(3))); }
    else if (cmd == "counts") counts = { static_cast<int>(num(arg(1))), static_cast<int>(num(arg(2))) };
    else { std::fprintf(stderr, "unknown command %s\n", cmd.c_str()); std::exit(2); }

    std::string line = cmd;
    for (const auto& l : log) line += " :: " + l;
    std::string ns, sounding, coffs, poffs;
    for (const auto& [n, v] : score.notes) ns += (ns.empty() ? "" : "+") + std::to_string(n) + "/" + show(v);
    for (const auto& [n, t] : out.sounding()) sounding += (sounding.empty() ? "" : "+") + std::to_string(n);
    for (const auto& [n, t] : notes.crossOffs) coffs += (coffs.empty() ? "" : "+") + std::to_string(n) + "/" + show(t);
    for (const auto& [n, t] : notes.pluckOffs) poffs += (poffs.empty() ? "" : "+") + std::to_string(n) + "/" + show(t);
    line += " | col " + std::to_string(score.col) + " last " + show(score.last) + " steps " + show(score.steps)
          + " notes " + (ns.empty() ? "-" : ns) + " sounding " + (sounding.empty() ? "-" : sounding)
          + " recent " + std::to_string(out.recent()) + " dropped " + std::to_string(out.dropped())
          + " seen " + std::to_string(notes.seenX) + " " + std::to_string(notes.seenY)
          + " crossoffs " + (coffs.empty() ? "-" : coffs) + " pluckoffs " + (poffs.empty() ? "-" : poffs)
          + " beat " + show(clock.beat(now));
    std::printf("%s\n", line.c_str());
  }
}
}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) { std::fprintf(stderr, "usage: score_cpp <runs>\n"); return 2; }
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
