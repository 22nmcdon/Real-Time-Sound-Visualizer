// The C++ ports through the same list of calls as functions_js.mjs, one
// result line per call. See that file for the language.
#include <array>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <functional>
#include <sstream>
#include <string>
#include <vector>

#include <map>

#include "scope/figures.h"
#include "scope/lfo.h"
#include "scope/noise.h"
#include "scope/osc.h"
#include "scope/plane.h"
#include "scope/voice.h"
#include "scope/voices.h"
#include "scope/wave.h"
#include "scope/wireframe.h"

namespace {
std::vector<std::string> splitOn(const std::string& text, char sep) {
  std::vector<std::string> out;
  std::string part;
  std::istringstream in(text);
  while (std::getline(in, part, sep)) out.push_back(part);
  return out;
}
std::vector<double> numbers(const std::string& text) {
  std::vector<double> out;
  for (const auto& w : splitOn(text, ',')) out.push_back(std::strtod(w.c_str(), nullptr));
  return out;
}
scope::CycleTables tables(const std::string& text) {  // "most:t0;t1;..."
  const auto colon = text.find(':');
  scope::CycleTables c;
  c.most = std::strtod(text.substr(0, colon).c_str(), nullptr);
  for (const auto& t : splitOn(text.substr(colon + 1), ';')) {
    std::vector<double> table = numbers(t);
    c.levels.push_back(table);
  }
  return c;
}
double num(const std::string& w) { return std::strtod(w.c_str(), nullptr); }
void show(const std::vector<double>& values) {
  for (std::size_t i = 0; i < values.size(); i++) std::printf(i ? " %.17g" : "%.17g", values[i]);
  std::printf("\n");
}
}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) { std::fprintf(stderr, "usage: functions_cpp <calls>\n"); return 2; }
  std::ifstream file(argv[1]);
  for (std::string line; std::getline(file, line);) {
    std::istringstream in(line);
    std::vector<std::string> w;
    for (std::string word; in >> word;) w.push_back(word);
    if (w.empty()) continue;
    const std::string& name = w[0];
    if (name == "noiseRun") {
      scope::Noise shape = scope::Noise::White;
      scope::noiseNamed(w[1], shape);
      const double hz = num(w[4]), rate = num(w[5]);
      scope::Random random(static_cast<std::uint32_t>(num(w[2])));
      scope::NoiseState z(random);
      std::vector<double> out;
      double phase = 0;
      for (long i = 0; i < static_cast<long>(num(w[3])); i++) {
        phase += scope::kTwoPi * hz / rate;
        if (phase >= scope::kPhaseWrap) phase -= scope::kPhaseWrap;
        out.push_back(scope::noiseStep(z, shape, phase, hz / rate, random));
      }
      show(out);
      continue;
    }
    if (name == "oscRun") {
      std::map<std::string, std::string> p;
      for (std::size_t i = 1; i < w.size(); i++) { const auto eq = w[i].find('='); p[w[i].substr(0, eq)] = w[i].substr(eq + 1); }
      auto d = [&](const char* k) { return num(p[k]); };
      scope::VoiceTone t;
      t.shape = scope::shapeNamed(p["shape"]);
      t.fmIndex = d("fm"); t.modRatio = d("mod"); t.ringMix = d("ring"); t.syncRatio = d("sync");
      t.subLevel = d("sub"); t.subOctave = static_cast<int>(d("suboct")); t.subSine = d("subsine") == 1;
      t.unison = d("n"); t.unisonCents = d("cents");
      std::array<double, 9> weights {};
      scope::WaveTables bars;
      if (p["bars"] != "-") { const auto v = numbers(p["bars"]); for (std::size_t k = 0; k < 9; k++) weights[k] = v[k]; bars.weights = &weights; }
      scope::Osc o;
      scope::VoiceFx x;
      const bool fmr = d("fmr") == 1, syncr = d("syncr") == 1;
      scope::voiceFxFor(t, x, fmr, syncr, false);
      const double rate = d("rate");
      const long samples = static_cast<long>(d("samples")), flip = static_cast<long>(d("flip"));
      std::vector<double> out;
      double base = 0;
      for (long i = 0; i < samples; i++) {
        if (i == flip) { t.unison = d("n2"); scope::voiceFxFor(t, x, fmr, syncr, false); }
        const double hz = d("hz") + (d("hz2") - d("hz")) * static_cast<double>(i) / static_cast<double>(samples);
        x.fmI = d("fm");
        x.syncR = d("sync") + d("sweep") * static_cast<double>(i) / static_cast<double>(samples);
        base += scope::kTwoPi * hz / rate;
        if (base >= scope::kPhaseWrap) base -= scope::kPhaseWrap;
        out.push_back(scope::oscStep(o, base, d("offset"), hz, t, bars, d("amount"), x, rate));
      }
      show(out);
      continue;
    }
    if (name == "voicesRun") {
      std::map<std::string, std::string> p;
      for (std::size_t i = 1; i < w.size(); i++) { const auto eq = w[i].find('='); p[w[i].substr(0, eq)] = w[i].substr(eq + 1); }
      auto d = [&](const char* k) { return num(p[k]); };
      const double rate = d("rate");
      scope::LayerTone t;
      t.noise = scope::noiseNamed(p["shape"], t.noiseShape);
      t.shape = scope::shapeNamed(p["shape"]);
      t.amp = d("amp");
      t.env = { d("a"), d("d"), d("s"), d("r") };
      t.fenv = { d("fa"), d("fd"), d("fs"), d("fr") };
      t.vcfType = static_cast<int>(d("vtype")); t.vcfCutoff = d("vcut"); t.vcfQ = d("vq");
      t.vcfTrack = d("vtrack"); t.vcfEnv = d("venv");
      t.drive = d("drive"); t.fold = d("fold"); t.crushBits = d("cbits"); t.crushHz = d("chz");
      t.unison = d("n"); t.unisonCents = d("cents");
      t.fmIndex = d("fm"); t.modRatio = d("mod"); t.ringMix = d("ring"); t.syncRatio = d("sync");
      t.subLevel = d("sub"); t.subOctave = static_cast<int>(d("suboct")); t.subSine = d("subsine") == 1;
      t.width = d("width"); t.table = d("table"); t.morph = d("morph");
      std::array<double, 9> weights {};
      scope::WaveTables bars;
      if (p["bars"] != "-") { const auto v = numbers(p["bars"]); for (std::size_t k = 0; k < 9; k++) weights[k] = v[k]; bars.weights = &weights; }
      scope::Random random(static_cast<std::uint32_t>(d("seed")));
      scope::VoiceContext c(rate);
      c.random = &random;
      c.qMask = static_cast<int>(d("qmask")); c.qGlide = d("qglide"); c.shapeFactor = static_cast<int>(d("factor"));
      scope::VoiceFx x;
      scope::voiceFxFor(t, x, d("fmr") == 1, d("syncr") == 1, d("shr") == 1);
      x.fmI = t.fmIndex; x.syncR = t.syncRatio; x.vcfPush = d("vpush");
      scope::setShaping(c.shaping, t, d("dp"), d("fp"));
      std::map<long, std::vector<std::string>> events;
      for (const auto& e : splitOn(p["ev"], ';')) {
        const auto colon = e.find(':');
        events[std::strtol(e.substr(0, colon).c_str(), nullptr, 10)].push_back(e.substr(colon + 1));
      }
      std::vector<scope::Voice> voices;
      std::vector<double> out;
      const long samples = static_cast<long>(d("samples"));
      for (long i = 0; i < samples; i++) {
        for (const auto& what : events[i]) {
          if (what == "null") scope::reconcileVoices(voices, nullptr, t, c);
          else if (what.rfind("cut:", 0) == 0) {
            const auto k = static_cast<std::size_t>(num(what.substr(4)));
            if (k < voices.size()) voices[k].fade = c.cutSamples;
          } else if (what.rfind("factor:", 0) == 0) {
            c.shapeFactor = static_cast<int>(num(what.substr(7)));
          } else if (what.rfind("set:", 0) == 0) {
            const auto f = splitOn(what, ':');
            const double v = num(f[2]);
            const std::map<std::string, double*> fields {
              { "attackMs", &t.env.attackMs }, { "decayMs", &t.env.decayMs }, { "sustain", &t.env.sustain },
              { "releaseMs", &t.env.releaseMs }, { "fAttackMs", &t.fenv.attackMs }, { "fDecayMs", &t.fenv.decayMs },
              { "fSustain", &t.fenv.sustain }, { "fReleaseMs", &t.fenv.releaseMs }, { "vcfCutoff", &t.vcfCutoff },
              { "vcfEnv", &t.vcfEnv }, { "vcfTrack", &t.vcfTrack }, { "amp", &t.amp },
            };
            const auto at = fields.find(f[1]);
            if (at == fields.end()) { std::fprintf(stderr, "no field %s\n", f[1].c_str()); return 2; }
            *at->second = v;
          } else {
            std::vector<scope::NoteWant> list;
            if (what != "none") {
              for (const auto& n : splitOn(what, '+')) {
                const auto f = splitOn(n, '/');
                list.push_back({ static_cast<int>(num(f[0])), num(f[1]), num(f[2]), f[3] });
              }
            }
            scope::reconcileVoices(voices, &list, t, c);
          }
        }
        const double bend = d("bend") + (d("bend2") - d("bend")) * static_cast<double>(i) / static_cast<double>(samples);
        scope::sound(voices, t, bars, d("amount"), bend, d("duck"), 1 / rate, d("glide"), x, c);
        out.insert(out.end(), c.mix.begin(), c.mix.end());
      }
      show(out);
      continue;
    }
    if (name == "planeRun") {
      std::map<std::string, std::string> p;
      for (std::size_t i = 1; i < w.size(); i++) { const auto eq = w[i].find('='); p[w[i].substr(0, eq)] = w[i].substr(eq + 1); }
      auto d = [&](const std::string& k) { return num(p[k]); };
      const double rate = d("rate");
      scope::PlaneTone t;
      const std::map<std::string, std::function<void(double)>> fields {
        { "planeMirror", [&](double v) { t.planeMirror = static_cast<int>(v); } },
        { "planeRadius", [&](double v) { t.planeRadius = v; } }, { "planeOS", [&](double v) { t.planeOS = v; } },
        { "planeLimit", [&](double v) { t.planeLimit = static_cast<int>(v); } },
        { "planeScaleX", [&](double v) { t.planeScaleX = v; } }, { "planeScaleY", [&](double v) { t.planeScaleY = v; } },
        { "planeShear", [&](double v) { t.planeShear = v; } }, { "planeTwist", [&](double v) { t.planeTwist = v; } },
        { "planeKaleido", [&](double v) { t.planeKaleido = v; } }, { "planeSnap", [&](double v) { t.planeSnap = v; } },
        { "delayMix", [&](double v) { t.delayMix = v; } }, { "delayMs", [&](double v) { t.delayMs = v; } },
        { "delayFeedback", [&](double v) { t.delayFeedback = v; } },
        { "delayPingPong", [&](double v) { t.delayPingPong = v != 0; } },
        { "chorusMix", [&](double v) { t.chorusMix = v; } }, { "chorusRate", [&](double v) { t.chorusRate = v; } },
        { "chorusDepthMs", [&](double v) { t.chorusDepthMs = v; } }, { "chorusMs", [&](double v) { t.chorusMs = v; } },
        { "chorusFeedback", [&](double v) { t.chorusFeedback = v; } },
      };
      for (const auto& [k, set] : fields) set(d(k));
      std::map<long, std::vector<std::pair<std::string, double>>> events;
      for (const auto& e : splitOn(p["ev"], ';')) {
        if (e.empty()) continue;
        const auto f = splitOn(e, ':');
        events[std::strtol(f[0].c_str(), nullptr, 10)].push_back({ f[1], num(f[2]) });
      }
      scope::Plane plane(rate);
      std::vector<double> out;
      bool on = false;
      const double tw = scope::kTwoPi;
      for (long i = 0; i < static_cast<long>(d("samples")); i++) {
        const auto ev = events.find(i);
        if (ev != events.end()) for (const auto& [field, value] : ev->second) fields.at(field)(value);
        if (i % 128 == 0 || ev != events.end()) on = plane.setup(t, d("twr") == 1, d("ecr") == 1);
        const double di = static_cast<double>(i);
        const double rp = static_cast<float>(d("rpush") * std::sin(di * 0.0031));
        const double tp = static_cast<float>(d("tpush") * std::sin(di * 0.0047 + 1));
        const double ep = static_cast<float>(d("epush") * std::sin(di * 0.0023 + 2));
        const double etp = static_cast<float>(d("etpush") * std::sin(di * 0.0013 + 3));
        double x = 0.7 * std::sin(tw * 220 * di / rate) + 0.25 * std::sin(tw * 661 * di / rate);
        double y = 0.5 * std::sin(tw * 330 * di / rate + 0.4);
        if (d("inp") == 1) { x = -0.375; y = 0.625; }
        if (!on) { out.insert(out.end(), { x, y, y, x, x, y }); continue; }
        plane.tick(t, rp, tp, ep, etp, 1 / rate);
        plane.step(scope::Plane::A, t, x, y); out.insert(out.end(), { plane.x, plane.y });
        plane.step(scope::Plane::B, t, 0.8 * y, 1.1 * x); out.insert(out.end(), { plane.x, plane.y });
        plane.step(scope::Plane::Heard, t, 0.6 * (x + y), 0.6 * (x - y)); out.insert(out.end(), { plane.x, plane.y });
      }
      show(out);
      continue;
    }
    if (name == "figureAt") {
      scope::FigurePath path;
      const bool has = w[4] != "-";
      if (has) {
        const auto parts = splitOn(w[4].substr(2), ';');
        path.xy = numbers(parts[0]); path.at = numbers(parts[1]);
      }
      const auto at = scope::figureAt(scope::figureNamed(w[1]), num(w[2]), num(w[3]), has ? &path : nullptr);
      show({ at[0], at[1] });
      continue;
    }
    if (name == "hypot") {
      show({ w.size() == 3 ? scope::jsHypot({ num(w[1]), num(w[2]) }) : scope::jsHypot({ num(w[1]), num(w[2]), num(w[3]) }) });
      continue;
    }
    if (name == "solidData") {
      for (const auto& s : scope::solids()) {
        if (s.name != w[1]) continue;
        std::vector<double> out(s.route.begin(), s.route.end());
        for (const auto& p : s.v) out.insert(out.end(), p.begin(), p.end());
        show(out);
      }
      continue;
    }
    if (name == "wireRun") {
      std::map<std::string, std::string> p;
      for (std::size_t i = 1; i < w.size(); i++) { const auto eq = w[i].find('='); p[w[i].substr(0, eq)] = w[i].substr(eq + 1); }
      auto d = [&](const char* k) { return num(p[k]); };
      scope::Wireframe wire;
      wire.set(p["model"]);
      std::map<long, std::vector<std::vector<std::string>>> events;
      for (const auto& e : splitOn(p["ev"], ';')) {
        if (e.empty()) continue;
        const auto f = splitOn(e, ':');
        events[std::strtol(f[0].c_str(), nullptr, 10)].push_back({ f.begin() + 1, f.end() });
      }
      double depth = d("depth");
      const double dt = 1 / d("rate");
      std::vector<double> out;
      for (long i = 0; i < static_cast<long>(d("samples")); i++) {
        const auto ev = events.find(i);
        if (ev != events.end()) {
          for (const auto& e : ev->second) {
            if (e[0] == "model") wire.set(e[1]);
            else if (e[0] == "reset") wire.reset();
            else if (e[0] == "depth") depth = num(e[1]);
          }
        }
        const auto at = wire.step(dt, d("laps"), depth,
                                  { d("s0"), d("s1") * (1 + 0.5 * std::sin(static_cast<double>(i) * 0.001)), d("s2") });
        out.insert(out.end(), at.begin(), at.end());
      }
      const auto& ang = wire.angles();
      out.insert(out.end(), ang.begin(), ang.end());
      show(out);
      continue;
    }
    if (name == "lfoRun") {
      scope::Lfo lfo;
      lfo.setShape(w[1]);
      lfo.rate = num(w[2]);
      scope::Random random(static_cast<std::uint32_t>(num(w[3])));
      std::vector<double> out;
      for (long i = 0; i < static_cast<long>(num(w[4])); i++) out.push_back(scope::lfoStep(lfo, num(w[5]), random));
      show(out);
      continue;
    }
    if (name == "lowpassTaps") { show(scope::lowpassTaps(static_cast<int>(num(w[1])))); continue; }
    if (name == "shapeRun") {
      const int factor = static_cast<int>(num(w[1]));
      scope::VoiceTone t; t.drive = num(w[2]); t.fold = num(w[3]);
      scope::Shaping sh; scope::setShaping(sh, t, num(w[4]), num(w[5]));
      scope::Shaper shaper(factor, scope::lowpassTaps(factor));
      std::vector<double> out;
      for (const double x : numbers(w[6])) out.push_back(shaper.step(x, sh));
      show(out);
      continue;
    }
    if (name == "crushRun") {
      scope::VoiceTone t; t.crushHz = num(w[1]); t.crushBits = num(w[2]);
      const double rate = num(w[3]);
      scope::VoiceFx x; scope::voiceFxFor(t, x, false, false, false);
      scope::Crush z;
      std::vector<double> out;
      for (const double v : numbers(w[4])) out.push_back(scope::crushStep(z, v, t, x, rate));
      show(out);
      continue;
    }
    if (name == "vcfRun") {
      scope::VoiceTone t; t.vcfCutoff = num(w[1]); t.vcfEnv = num(w[2]); t.vcfTrack = num(w[3]); t.vcfQ = num(w[4]);
      const int type = static_cast<int>(num(w[5]));
      t.vcfType = type;
      const double note = num(w[6]), rate = num(w[7]), push = num(w[8]), k = 1 / std::fmax(0.1, t.vcfQ);
      const auto xs = numbers(w[9]), envs = numbers(w[10]);
      scope::VcfState st;
      std::vector<double> out;
      const std::string field = w.size() > 11 ? w[11] : "";
      for (std::size_t i = 0; i < xs.size(); i++) {
        if (i == 80) {
          if (field == "cutoff") t.vcfCutoff = num(w[12]);
          else if (field == "env") t.vcfEnv = num(w[12]);
          else if (field == "track") t.vcfTrack = num(w[12]);
        }
        out.push_back(scope::svfStep(st, xs[i], scope::vcfCoef(st, t, note, envs[i], push, rate), k, type));
      }
      show(out);
      continue;
    }
    if (name == "cycleOf") show({ scope::cycleOf(num(w[1])) });
    else if (name == "polyBlep") show({ scope::polyBlep(num(w[1]), num(w[2])) });
    else if (name == "polyBlamp") show({ scope::polyBlamp(num(w[1]), num(w[2])) });
    else if (name == "drawbarGain") show({ scope::drawbarGain(num(w[1])) });
    else if (name == "drawbarWeights") {
      const auto v = numbers(w[1]);
      std::array<double, 9> levels {}, out {};
      for (std::size_t k = 0; k < 9; k++) levels[k] = v[k];
      scope::drawbarWeights(levels, out);
      show({ out.begin(), out.end() });
    } else if (name == "intervalRatio") show({ scope::intervalRatio(static_cast<int>(num(w[1])), num(w[2]) == 1) });
    else if (name == "svfG") show({ scope::svfG(num(w[1]), num(w[2])) });
    else if (name == "svfRun") {
      scope::SvfState s;
      std::vector<double> out;
      for (const double x : numbers(w[4])) out.push_back(scope::svfStep(s, x, num(w[1]), num(w[2]), static_cast<int>(num(w[3]))));
      show(out);
    } else if (name == "cycleRead") {
      const auto c = tables(w[1].substr(2));
      show({ scope::cycleRead(&c, num(w[2]), num(w[3])) });
    } else if (name == "waveAt") {
      scope::WaveTables bars;
      std::array<double, 9> weights {};
      scope::CycleTables cycle;
      std::vector<scope::CycleTables> bank;
      if (w[4].rfind("T:", 0) == 0) { cycle = tables(w[4].substr(2)); bars.cycle = &cycle; }
      else if (w[4].rfind("B:", 0) == 0) {
        for (const auto& c : splitOn(w[4].substr(2), '!')) bank.push_back(tables(c));
        bars.bank = &bank;
      } else if (w[4] != "-") {
        const auto v = numbers(w[4]);
        for (std::size_t k = 0; k < 9; k++) weights[k] = v[k];
        bars.weights = &weights;
      }
      show({ scope::waveAt(scope::shapeNamed(w[1]), num(w[2]), num(w[3]), bars, num(w[5])) });
    } else { std::fprintf(stderr, "unknown call %s\n", name.c_str()); return 2; }
  }
  return 0;
}
