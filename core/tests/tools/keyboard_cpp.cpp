// scope::Keyboard through the same runs as keyboard_js.mjs, one result line
// per command. See that file for the language. The keyboard plays a real
// scope::Generator here, through a target that writes down each call first,
// so what it reads back is what the generator really holds.
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#include "scope/keyboard.h"

namespace {
std::vector<std::string> splitOn(const std::string& text, char sep) {
  std::vector<std::string> out;
  std::string part;
  std::istringstream in(text);
  while (std::getline(in, part, sep)) out.push_back(part);
  return out;
}
double num(const std::string& w) { return std::strtod(w.c_str(), nullptr); }
std::string show(double v) { char b[40]; std::snprintf(b, sizeof b, "%.17g", v); return b; }

class Logged : public scope::GeneratorNotes {
 public:
  Logged(scope::Generator& g, std::vector<std::string>& log) : GeneratorNotes(g), log_(log) {}
  void set(std::string_view field, double value) override {
    log_.push_back("set " + std::string(field) + " " + show(value) + " 0");
    GeneratorNotes::set(field, value);
  }
  void setVoices(const std::vector<scope::NoteWant>* list, int layer) override {
    std::string text = "null";
    if (list) {
      text.clear();
      for (const auto& v : *list) {
        text += (text.empty() ? "" : "+") + std::to_string(v.note) + "/" + show(v.freq) + "/" + show(v.velocity) + "/" + v.role;
      }
      if (text.empty()) text = "none";
    }
    log_.push_back("set voices " + text + " " + std::to_string(layer));
    GeneratorNotes::setVoices(list, layer);
  }
  void reswing() override { log_.push_back("reswing"); GeneratorNotes::reswing(); }
  void gate(bool open, double velocity) override {
    log_.push_back(std::string("gate ") + (open ? "1" : "0") + " " + show(velocity));
    GeneratorNotes::gate(open, velocity);
  }
  void setGated(bool on) override { log_.push_back(std::string("setGated ") + (on ? "1" : "0")); GeneratorNotes::setGated(on); }
  void setLayout(scope::Layout next) override {
    log_.push_back(std::string("layout ") + scope::layoutName(next));
    GeneratorNotes::setLayout(next);
  }

 private:
  std::vector<std::string>& log_;
};

class Realtime : public scope::RealtimeIn {
 public:
  explicit Realtime(std::vector<std::string>& log) : log_(log) {}
  void realtime(int status) override { log_.push_back("realtime " + std::to_string(status)); }

 private:
  std::vector<std::string>& log_;
};

void run(const std::vector<std::string>& head, const std::vector<std::vector<std::string>>& commands) {
  bool present = true;
  for (const auto& kv : head) if (kv == "present=0") present = false;
  std::vector<scope::Lfo> lfos(2);
  scope::Generator gen(48000, scope::slot::Used, lfos);
  std::vector<std::string> log;
  Logged target(gen, log);
  Realtime clock(log);
  scope::Keyboard k(target, &clock);
  k.setPresent(present);
  std::vector<std::string> lines;
  for (const auto& words : commands) {
    const std::string& cmd = words[0];
    const auto arg = [&](std::size_t i) { return i < words.size() ? words[i] : std::string(); };
    log.clear();
    if (cmd == "on") k.noteOn(static_cast<int>(num(arg(1))), num(arg(2)));
    else if (cmd == "off") k.noteOff(static_cast<int>(num(arg(1))));
    else if (cmd == "pedal") k.setPedal(num(arg(1)));
    else if (cmd == "panic") k.panic();
    else if (cmd == "name") {
      std::string name = arg(2);
      for (auto& ch : name) if (ch == '_') ch = ' ';
      k.learn(static_cast<int>(num(arg(1))), name);
    }
    else if (cmd == "cc") k.control(static_cast<int>(num(arg(1))), static_cast<int>(num(arg(2))));
    else if (cmd == "bytes") {
      std::vector<std::uint8_t> data;
      for (const auto& b : splitOn(arg(1), ',')) data.push_back(static_cast<std::uint8_t>(std::strtol(b.c_str(), nullptr, 0)));
      k.bytes(data.data(), data.size());
    } else if (cmd == "mode") k.setMode(arg(1) == "mono" ? scope::NoteMode::Mono : arg(1) == "poly" ? scope::NoteMode::Poly : scope::NoteMode::Dyad);
    else if (cmd == "draw") k.setDraw(static_cast<int>(num(arg(1))), static_cast<int>(num(arg(2))), scope::drawWhichNamed(arg(3)));
    else if (cmd == "just") k.setPolyJust(arg(1) == "1");
    else if (cmd == "layers") k.setLayers(arg(1) == "split" ? scope::LayerMode::Split : arg(1) == "layer" ? scope::LayerMode::Layer : scope::LayerMode::Off);
    else if (cmd == "learn") k.learnSplit();
    else if (cmd == "pair") k.setPair(arg(1) == "against");
    else if (cmd == "hold") k.setHold(arg(1) == "1");
    else if (cmd == "drive") k.setDrive(arg(1) == "1");
    else if (cmd == "play") k.setPlay(arg(1) == "1");
    else if (cmd == "gen") {
      const std::string v = arg(2);
      if (v == "true" || v == "false") gen.set(arg(1), v == "true" ? 1.0 : 0.0);
      else if (arg(1) == "mode" || arg(1) == "figure" || arg(1) == "inputFrom") gen.set(arg(1), std::string_view(v));
      else gen.set(arg(1), num(v));
    } else if (cmd == "panel") {
      auto& p = k.panel();
      if (arg(1) == "freq") p.freq = num(arg(2));
      else if (arg(1) == "interval") p.interval = static_cast<int>(num(arg(2)));
      else if (arg(1) == "figureRate") p.figureRate = num(arg(2));
      else if (arg(1) == "detail") p.detail = num(arg(2));
    } else if (cmd == "frame") k.frame(num(arg(1)));
    else if (cmd == "undrive") k.undrive();
    else if (cmd == "present") k.setPresent(arg(1) == "1");
    else { std::fprintf(stderr, "unknown command %s\n", cmd.c_str()); std::exit(2); }

    std::string line = cmd;
    for (const auto& l : log) line += " :: " + l;
    const auto poly = k.polyCount();
    const auto strikes = k.strikes();
    const auto iv = k.interval();
    std::string notes, sustained, cc;
    for (const auto& h : k.notes()) notes += (notes.empty() ? "" : "+") + std::to_string(h.note) + "/" + show(h.velocity);
    for (const int n : k.sustained()) sustained += (sustained.empty() ? "" : "+") + std::to_string(n);
    for (const auto& c : k.controllers()) {
      std::string name = c.name;
      for (auto& ch : name) if (ch == ' ') ch = '_';
      cc += (cc.empty() ? "" : "+") + std::to_string(c.number) + "/" + name + "/" + std::to_string(c.raw) + "/" + show(c.value) + "/" + show(c.value);
    }
    line += " | key " + show(k.key()) + " pedal " + show(k.pedal()) + " count " + show(k.notesCount())
          + " spread " + show(k.notesSpread()) + " top " + show(k.notesTop()) + " inner " + show(k.notesInner())
          + " poly " + std::to_string(poly.sounding) + " " + std::to_string(poly.drawn) + " " + std::to_string(poly.held)
          + " split " + std::to_string(k.splitPoint()) + " " + (k.learning() ? "1" : "0")
          + " sustain " + (k.sustain() ? "1" : "0")
          + " strikes " + std::to_string(strikes[0]) + " " + std::to_string(strikes[1])
          + " interval " + std::to_string(iv[0]) + " " + std::to_string(iv[1])
          + " panel " + std::to_string(k.panel().interval) + " " + show(k.panel().freq)
          + " layout " + scope::layoutName(target.layout()) + " gated " + (target.gated() ? "1" : "0")
          + " layers " + (k.layersOn() ? "1" : "0")
          + " notes " + (notes.empty() ? "-" : notes) + " sustained " + (sustained.empty() ? "-" : sustained)
          + " cc " + (cc.empty() ? "-" : cc);
    lines.push_back(line);
  }
  for (const auto& l : lines) std::printf("%s\n", l.c_str());
}
}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) { std::fprintf(stderr, "usage: keyboard_cpp <runs>\n"); return 2; }
  std::ifstream file(argv[1]);
  std::vector<std::string> text;
  for (std::string line; std::getline(file, line);) text.push_back(line);
  for (std::size_t i = 0; i < text.size(); i++) {
    std::istringstream in(text[i]);
    std::vector<std::string> words;
    for (std::string w; in >> w;) words.push_back(w);
    if (words.empty() || words[0] != "run") continue;
    std::vector<std::vector<std::string>> commands;
    for (i++; i < text.size(); i++) {
      std::istringstream c(text[i]);
      std::vector<std::string> w;
      for (std::string x; c >> x;) w.push_back(x);
      if (!w.empty() && w[0] == "end") break;
      if (!w.empty()) commands.push_back(w);
    }
    run({ words.begin() + 1, words.end() }, commands);
  }
  return 0;
}
