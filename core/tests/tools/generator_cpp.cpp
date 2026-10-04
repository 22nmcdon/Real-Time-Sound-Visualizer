// scope::Generator through the same runs as generator_js.mjs, one result line
// per run. See that file for the language.
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

#include "scope/generator.h"
#include "scope/sources.h"

namespace {
std::vector<std::string> splitOn(const std::string& text, char sep) {
  std::vector<std::string> out;
  std::string part;
  std::istringstream in(text);
  while (std::getline(in, part, sep)) out.push_back(part);
  return out;
}
double num(const std::string& w) { return std::strtod(w.c_str(), nullptr); }
std::vector<double> numbers(const std::string& text) {
  std::vector<double> out;
  for (const auto& w : splitOn(text, ',')) out.push_back(num(w));
  return out;
}
scope::CycleTables tables(const std::string& text) {  // "most:t0;t1;..."
  const auto colon = text.find(':');
  scope::CycleTables c;
  c.most = num(text.substr(0, colon));
  for (const auto& t : splitOn(text.substr(colon + 1), ';')) {
    std::vector<double> table = numbers(t);
    c.levels.push_back(table);
  }
  return c;
}
bool isNumber(const std::string& w) {
  char* end = nullptr;
  std::strtod(w.c_str(), &end);
  return end != w.c_str() && *end == '\0';
}

using Events = std::map<long, std::vector<std::vector<std::string>>>;

void run(const std::vector<std::string>& head, const Events& events) {
  std::map<std::string, std::string> p;
  for (const auto& kv : head) { const auto eq = kv.find('='); p[kv.substr(0, eq)] = kv.substr(eq + 1); }
  const double rate = num(p["rate"]);
  const long samples = std::strtol(p["samples"].c_str(), nullptr, 10);
  constexpr int N = 128;
  std::vector<scope::Lfo> lfos(2);
  for (int i = 0; i < 2; i++) {
    const std::string key = "lfo" + std::to_string(i);
    const auto parts = splitOn(p.count(key) ? p[key] : "sine,0.2", ',');
    lfos[static_cast<std::size_t>(i)].setShape(parts[0]);
    lfos[static_cast<std::size_t>(i)].rate = num(parts[1]);
  }
  scope::Generator core(rate, static_cast<int>(num(p["slots"])), lfos, static_cast<std::uint32_t>(num(p["seed"])));
  std::vector<double> out;
  std::vector<std::vector<float>> bufs(6, std::vector<float>(N, 0.0f));
  std::vector<float> input(N);
  double inHz = 0, inAmp = 0, inDc = 0;
  bool fx = false;
  for (long at = 0; at < samples; at += N) {
    const auto ev = events.find(at);
    if (ev != events.end()) {
      for (const auto& words : ev->second) {
        const std::string& cmd = words[0];
        const auto arg = [&](std::size_t k) { return k < words.size() ? words[k] : std::string(); };
        if (cmd == "set") {
          const int layer = arg(3).empty() ? 0 : static_cast<int>(num(arg(3)));
          const std::string v = arg(2);
          if (v == "true" || v == "false") core.set(arg(1), v == "true" ? 1.0 : 0.0, layer);
          else if (isNumber(v)) core.set(arg(1), num(v), layer);
          else core.set(arg(1), std::string_view(v), layer);
        } else if (cmd == "bars") core.setBars(numbers(arg(2)), static_cast<int>(num(arg(1))));
        else if (cmd == "spin") { const auto s = numbers(arg(1)); core.setSpin({ s[0], s[1], s[2] }); }
        else if (cmd == "voices") {
          const int layer = static_cast<int>(num(arg(1)));
          if (arg(2) == "null") core.setVoices(nullptr, layer);
          else {
            std::vector<scope::NoteWant> list;
            if (arg(2) != "none") {
              for (const auto& n : splitOn(arg(2), '+')) {
                const auto f = splitOn(n, '/');
                list.push_back({ static_cast<int>(num(f[0])), num(f[1]), num(f[2]), f[3] });
              }
            }
            core.setVoices(&list, layer);
          }
        } else if (cmd == "routes") {
          std::vector<scope::Route> list;
          if (arg(1) != "none") {
            for (const auto& r : splitOn(arg(1), '+')) {
              const auto g = splitOn(r, '/');
              scope::Route route;
              route.index = static_cast<int>(num(g[0]));
              route.held = num(g[1]); route.heldB = num(g[2]); route.slot = static_cast<int>(num(g[3]));
              route.amount = num(g[4]); route.amountB = num(g[5]); route.unipolar = num(g[6]) == 1;
              list.push_back(route);
            }
          }
          core.setRoutes(list);
        } else if (cmd == "gate") core.gate(arg(1) == "1", num(arg(2)));
        else if (cmd == "gated") core.setGated(arg(1) == "1");
        else if (cmd == "kick") core.kick(num(arg(1)));
        else if (cmd == "strike") core.strike(num(arg(1)), num(arg(2)));
        else if (cmd == "reswing") core.reswing();
        else if (cmd == "cycle" && arg(1) == "none") core.setCycle(nullptr);
        else if (cmd == "wavetable" && arg(1) == "none") core.setWavetable(nullptr);
        else if (cmd == "figPath" && arg(1) == "none") core.setFigPath(nullptr);
        else if (cmd == "cycle") core.setCycle(std::make_shared<scope::CycleTables>(tables(arg(1).substr(2))));
        else if (cmd == "wavetable") {
          auto bank = std::make_shared<std::vector<scope::CycleTables>>();
          for (const auto& c : splitOn(arg(1).substr(2), '!')) bank->push_back(tables(c));
          core.setWavetable(bank);
        } else if (cmd == "figPath") {
          const auto parts = splitOn(arg(1).substr(2), ';');
          auto path = std::make_shared<scope::FigurePath>();
          path->xy = numbers(parts[0]); path->at = numbers(parts[1]);
          core.setFigPath(path);
        } else if (cmd == "lfo") {
          auto& lfo = lfos[static_cast<std::size_t>(num(arg(1)))];
          lfo.setShape(arg(2)); lfo.rate = num(arg(3));
        } else if (cmd == "restart") {
          lfos[static_cast<std::size_t>(num(arg(1)))].phase = 0;
        } else if (cmd == "input") { inHz = num(arg(1)); inAmp = num(arg(2)); inDc = arg(3).empty() ? 0 : num(arg(3)); }
        else if (cmd == "fx") fx = arg(1) == "1";
        else { std::fprintf(stderr, "unknown command %s\n", cmd.c_str()); std::exit(2); }
      }
    }
    if (inHz > 0) {
      for (int k = 0; k < N; k++) input[static_cast<std::size_t>(k)] =
          static_cast<float>(inDc + inAmp * std::sin(2 * scope::kPi * inHz * static_cast<double>(at + k) / rate));
    }
    auto& l = bufs[0]; auto& r = bufs[1]; auto& hl = bufs[2]; auto& hr = bufs[3]; auto& bl = bufs[4]; auto& br = bufs[5];
    if (fx) {
      std::vector<float> silent(N, 0.0f), inR(N);
      const std::vector<float>& inL = inHz > 0 ? input : silent;
      for (int k = 0; k < N; k++) inR[static_cast<std::size_t>(k)] = static_cast<float>(0.5 * inL[static_cast<std::size_t>((k + 7) % N)]);
      core.effect(inL.data(), inR.data(), l.data(), r.data(), N);
      for (int k = 0; k < N; k++) out.insert(out.end(), { l[static_cast<std::size_t>(k)], r[static_cast<std::size_t>(k)], 0, 0, 0, 0 });
      continue;
    }
    core.setInput(inHz > 0 ? input.data() : nullptr, N);
    core.block(l.data(), r.data(), N, hl.data(), hr.data(), bl.data(), br.data());
    for (std::size_t k = 0; k < N; k++) out.insert(out.end(), { l[k], r[k], hl[k], hr[k], bl[k], br[k] });
  }
  const auto& b = core.budget();
  const auto d = core.drawing();
  const auto c = core.crossings();
  out.insert(out.end(), { core.envelope(), core.pitch(), static_cast<double>(c[0]), static_cast<double>(c[1]),
                          core.spinKick(), core.swingLevel(), b.units, static_cast<double>(b.asked[0]),
                          static_cast<double>(b.asked[1]), static_cast<double>(b.unison[0]),
                          static_cast<double>(b.unison[1]), static_cast<double>(b.askedFactor),
                          static_cast<double>(b.factor), static_cast<double>(b.silenced), d.swing, d.pendulum,
                          d.turn[0], d.turn[1], d.turn[2], d.facing, static_cast<double>(core.voices().size()),
                          static_cast<double>(core.voicesB().size()) });
  // The sources that read it, as the matrix would.
  out.push_back(scope::EnvelopeSource(core).value());
  using D = scope::DrawingSource::Kind;
  for (const D k : { D::Swing, D::Pendulum, D::TurnX, D::TurnY, D::TurnZ, D::Facing }) out.push_back(scope::DrawingSource(k, core).value());
  for (std::size_t i = 0; i < out.size(); i++) std::printf(i ? " %.17g" : "%.17g", out[i]);
  std::printf("\n");
}
}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) { std::fprintf(stderr, "usage: generator_cpp <runs>\n"); return 2; }
  std::ifstream file(argv[1]);
  std::vector<std::string> lines;
  for (std::string line; std::getline(file, line);) lines.push_back(line);
  for (std::size_t i = 0; i < lines.size(); i++) {
    std::istringstream in(lines[i]);
    std::vector<std::string> words;
    for (std::string w; in >> w;) words.push_back(w);
    if (words.empty() || words[0] != "run") continue;
    Events events;
    for (i++; i < lines.size(); i++) {
      std::istringstream ev(lines[i]);
      std::vector<std::string> w;
      for (std::string x; ev >> x;) w.push_back(x);
      if (!w.empty() && w[0] == "end") break;
      if (w.size() < 3 || w[0] != "at") continue;
      events[std::strtol(w[1].c_str(), nullptr, 10)].push_back({ w.begin() + 2, w.end() });
    }
    run({ words.begin() + 1, words.end() }, events);
  }
  return 0;
}
