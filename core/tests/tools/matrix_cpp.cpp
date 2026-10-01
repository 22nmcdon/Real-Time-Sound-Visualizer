// scope::Matrix through the same runs as matrix_js.mjs, one result line per
// command. See that file for the language.
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

#include "scope/matrix.h"

namespace {
double num(const std::string& w) {
  if (w == "true") return 1;
  if (w == "false") return 0;
  char* end = nullptr;
  const double v = std::strtod(w.c_str(), &end);
  return end != w.c_str() && *end == '\0' ? v : std::numeric_limits<double>::quiet_NaN();
}
std::string show(double v) { char b[40]; std::snprintf(b, sizeof b, "%.17g", v); return b; }

// A source whose value and count the run sets.
class Scripted : public scope::ModSource {
 public:
  Scripted(const std::string& id, const std::map<std::string, double>& values, const std::map<std::string, int>& counts)
      : ModSource(id), values_(values), counts_(counts) {}
  double value() const override { const auto at = values_.find(id); return at == values_.end() ? 0 : at->second; }
  int count() const override { const auto at = counts_.find(id); return at == counts_.end() ? 0 : at->second; }

 private:
  const std::map<std::string, double>& values_;
  const std::map<std::string, int>& counts_;
};

void run(const std::vector<std::vector<std::string>>& commands) {
  scope::Matrix m;
  std::map<std::string, double> values;
  std::map<std::string, int> counts;
  std::vector<std::unique_ptr<Scripted>> sources;
  std::vector<std::string> log;
  std::array<int, 2> strikes { 0, 0 };
  double clock = 0;
  for (const auto& words : commands) {
    const std::string& cmd = words[0];
    const auto arg = [&](std::size_t i) { return i < words.size() ? words[i] : std::string(); };
    log.clear();
    std::string said;
    if (cmd == "source") {
      auto s = std::make_unique<Scripted>(arg(1), values, counts);
      for (std::size_t i = 2; i < words.size(); i++) {
        const std::string& f = words[i];
        if (f == "event") s->event = true;
        else if (f == "picture") s->fromPicture = true;
        else if (f == "stepped") s->stepped = true;
        else if (f == "varies") s->reachVaries = true;
        else if (f.rfind("reach=", 0) == 0) s->reach = num(f.substr(6));
        else if (f.rfind("index=", 0) == 0) s->index = static_cast<int>(num(f.substr(6)));
      }
      m.registerSource(s.get());
      sources.push_back(std::move(s));
      m.touch();
    } else if (cmd == "value") values[arg(1)] = num(arg(2));
    else if (cmd == "count") counts[arg(1)] = static_cast<int>(num(arg(2)));
    else if (cmd == "visual") {
      scope::ModDest d;
      d.id = arg(1); d.kind = scope::DestKind::Visual;
      d.span = num(arg(2)); d.min = num(arg(3)); d.max = num(arg(4));
      const double base = num(arg(5));
      const std::string id = d.id;
      d.base = [base] { return base; };
      d.set = [&log, id](double offset) { log.push_back("visual " + id + " " + show(offset)); };
      m.registerDest(std::move(d));
    } else if (cmd == "event") {
      scope::ModDest d;
      d.id = arg(1); d.kind = scope::DestKind::Event;
      const std::string id = d.id;
      d.fire = [&log, id](double amount) { log.push_back("fire " + id + " " + show(amount)); };
      m.registerDest(std::move(d));
    } else if (cmd == "route") m.add(arg(1), arg(2), num(arg(3)));
    else if (cmd == "unroute") m.remove(arg(1), arg(2));
    else if (cmd == "amount") m.setAmount(arg(1), arg(2), num(arg(3)));
    else if (cmd == "load") m.load(scope::Matrix::decode(arg(1)));
    else if (cmd == "forget") { m.unregisterSource(arg(1)); m.touch(); }
    else if (cmd == "fade") {
      const std::string mode = arg(1);
      const scope::FadeMode f = mode == "in" ? scope::FadeMode::In : mode == "out" ? scope::FadeMode::Out
                              : mode == "both" ? scope::FadeMode::Both : mode == "off" ? scope::FadeMode::Off
                              : m.fadeMode();  // a mode the page does not know changes nothing
      if (arg(2).empty()) m.setFade(f); else m.setFade(f, num(arg(2)));
    } else if (cmd == "env") {
      scope::FadePart p;
      for (std::size_t i = 2; i < words.size(); i++) {
        const auto eq = words[i].find('=');
        const std::string k = words[i].substr(0, eq), v = words[i].substr(eq + 1);
        const double n = num(v);
        if (k == "delay") p.delay = n; else if (k == "attack") p.attack = n; else if (k == "attackMid") p.attackMid = n;
        else if (k == "decay") p.decay = n; else if (k == "decayMid") p.decayMid = n; else if (k == "sustain") p.sustain = n;
        else if (k == "release") p.release = n; else if (k == "releaseMid") p.releaseMid = n;
        else if (k == "seconds") p.seconds = n; else if (k == "inSeconds") p.inSeconds = n;
        else if (k == "outSeconds") p.outSeconds = n; else if (k == "inMid") p.inMid = n; else if (k == "outMid") p.outMid = n;
        else if (k == "restart") p.restart = v == "true"; else if (k == "loop") p.loop = v == "true";
      }
      m.setFadeEnvelope(p, static_cast<int>(num(arg(1))));
    } else if (cmd == "layers") m.setLayered(arg(1) == "1");
    else if (cmd == "strike") { strikes[static_cast<std::size_t>(num(arg(1)))]++; }
    else if (cmd == "at") { clock = num(arg(1)); m.setTime(clock); }
    else if (cmd == "frame" || cmd == "routes") {
      m.setStrikes(strikes);
      if (cmd == "frame") m.frame(clock);
      std::string routes;
      for (const auto& r : m.routes(clock)) {
        routes += (routes.empty() ? "" : "+") + (r.index < 0 ? std::string("u") : show(r.index)) + "/" + show(r.held) + "/"
                + show(r.heldB) + "/" + std::to_string(r.slot) + "/" + show(r.amount) + "/" + show(r.amountB) + "/"
                + (r.unipolar ? "1" : "0");
      }
      said = "routes " + (routes.empty() ? std::string("-") : routes) + " ";
    } else if (cmd == "encode") {
      const std::string code = scope::Matrix::encode(m.routings());
      said = "code " + (code.empty() ? std::string("-") : code) + " ";
    } else if (cmd == "dests") {
      std::string list;
      for (const auto& d : m.dests()) {
        if (d.kind != scope::DestKind::Audio) continue;
        list += (list.empty() ? "" : "+") + d.id + "/" + std::to_string(d.slot) + "/" + (d.unipolar ? "1" : "0");
      }
      said = "dests " + list + " ";
    } else { std::fprintf(stderr, "unknown command %s\n", cmd.c_str()); std::exit(2); }

    std::string line = cmd;
    for (const auto& l : log) line += " :: " + l;
    std::string amounts;
    for (const auto& r : m.routings()) amounts += (amounts.empty() ? "" : "+") + show(r.amount);
    line += " | " + said + "amounts " + (amounts.empty() ? "-" : amounts) + " heard " + std::to_string(m.heard().size())
          + " gains " + std::to_string(m.fading()) + " dirty " + (m.dirty() ? "1" : "0");
    std::printf("%s\n", line.c_str());
  }
}
}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) { std::fprintf(stderr, "usage: matrix_cpp <runs>\n"); return 2; }
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
