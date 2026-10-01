// scope::restoreSetup through the same setups as restore_page.py, one JSON
// line per setup in the same shape. The page's sources are registered as
// stand-ins with their reach, so a stored depth is held as the page holds it.
//   restore_cpp <setups> <sources.json>
#include <cstdio>
#include <fstream>
#include <memory>
#include <string>
#include <vector>

#include "scope/presets.h"
#include "scope/restore.h"

namespace {
using scope::Json;
Json num(double v) { return Json::number(v); }
Json str(const std::string& v) { return Json::string(std::string_view(v)); }
Json flag(bool v) { return Json::boolean(v); }

class StandIn : public scope::ModSource {
 public:
  explicit StandIn(std::string id) : ModSource(std::move(id)) {}
  double value() const override { return 0; }
};

Json layerJson(const scope::LayerSettings& t) {
  Json o = Json::object();
  o.set("shape", str(t.shapeName)); o.set("amp", num(t.amp));
  o.set("attackMs", num(t.env.attackMs)); o.set("decayMs", num(t.env.decayMs));
  o.set("sustain", num(t.env.sustain)); o.set("releaseMs", num(t.env.releaseMs));
  Json bars = Json::array();
  for (const double b : t.bars) bars.a.push_back(num(b));
  o.set("bars", bars);
  o.set("morph", num(t.morph)); o.set("width", num(t.width)); o.set("table", num(t.table));
  o.set("modRatio", num(t.modRatio)); o.set("fmIndex", num(t.fmIndex)); o.set("ringMix", num(t.ringMix));
  o.set("syncRatio", num(t.syncRatio)); o.set("subLevel", num(t.subLevel)); o.set("subOctave", num(t.subOctave));
  o.set("subShape", str(t.subShapeName)); o.set("unison", num(t.unison)); o.set("unisonCents", num(t.unisonCents));
  o.set("drive", num(t.drive)); o.set("fold", num(t.fold)); o.set("crushBits", num(t.crushBits)); o.set("crushHz", num(t.crushHz));
  o.set("vcfType", num(t.vcfType)); o.set("vcfCutoff", num(t.vcfCutoff)); o.set("vcfQ", num(t.vcfQ));
  o.set("vcfTrack", num(t.vcfTrack)); o.set("vcfEnv", num(t.vcfEnv));
  o.set("fAttackMs", num(t.fenv.attackMs)); o.set("fDecayMs", num(t.fenv.decayMs));
  o.set("fSustain", num(t.fenv.sustain)); o.set("fReleaseMs", num(t.fenv.releaseMs));
  return o;
}

Json toneJson(const scope::Tone& t) {
  Json o = layerJson(t);
  o.set("mode", str(t.modeName)); o.set("freq", num(t.freq)); o.set("interval", num(t.interval));
  o.set("octaves", num(t.octaves)); o.set("just", flag(t.just)); o.set("phase", num(t.phase));
  o.set("figure", str(t.figureName)); o.set("detail", num(t.detail)); o.set("figureRate", num(t.figureRate));
  o.set("swingRate", num(t.swingRate)); o.set("decay", num(t.decay)); o.set("swingDrive", num(t.swingDrive));
  o.set("inputMode", num(t.inputMode)); o.set("inputDepth", num(t.inputDepth)); o.set("inputFrom", str(t.inputFromName));
  o.set("gen2Figure", str(t.gen2FigureName)); o.set("gen2Rate", num(t.gen2Rate)); o.set("gen2Amp", num(t.gen2Amp));
  o.set("pitched", flag(t.pitched)); o.set("ringMs", num(t.ringMs)); o.set("detune", num(t.detune));
  o.set("model", str(t.modelName));
  Json spin = Json::array();
  for (const double v : t.spin) spin.a.push_back(num(v));
  o.set("spin", spin);
  o.set("spinRate", num(t.spinRate)); o.set("depth", num(t.depth)); o.set("shapeOS", num(t.shapeOS));
  o.set("glideMs", num(t.glideMs)); o.set("qMask", num(t.qMask)); o.set("qGlideMs", num(t.qGlideMs));
  o.set("crossOn", flag(t.crossOn)); o.set("crossX", num(t.crossX)); o.set("crossY", num(t.crossY));
  o.set("crossHzX", num(t.crossHzX)); o.set("crossHzY", num(t.crossHzY)); o.set("crossDecayMs", num(t.crossDecayMs));
  o.set("crossLevel", num(t.crossLevel)); o.set("scoreDecayMs", num(t.scoreDecayMs)); o.set("scoreLevel", num(t.scoreLevel));
  o.set("planeMirror", num(t.planeMirror)); o.set("planeRadius", num(t.planeRadius)); o.set("planeOS", num(t.planeOS));
  o.set("planeLimit", num(t.planeLimit)); o.set("planeScaleX", num(t.planeScaleX)); o.set("planeScaleY", num(t.planeScaleY));
  o.set("planeShear", num(t.planeShear)); o.set("planeTwist", num(t.planeTwist)); o.set("planeKaleido", num(t.planeKaleido));
  o.set("planeSnap", num(t.planeSnap)); o.set("delayMix", num(t.delayMix)); o.set("delayMs", num(t.delayMs));
  o.set("delayFeedback", num(t.delayFeedback)); o.set("delayPingPong", flag(t.delayPingPong));
  o.set("chorusMix", num(t.chorusMix)); o.set("chorusRate", num(t.chorusRate)); o.set("chorusDepthMs", num(t.chorusDepthMs));
  o.set("chorusMs", num(t.chorusMs)); o.set("chorusFeedback", num(t.chorusFeedback));
  return o;
}

const char* modeName(scope::NoteMode m) { return m == scope::NoteMode::Mono ? "mono" : m == scope::NoteMode::Poly ? "poly" : "dyad"; }
const char* whichName(scope::DrawWhich w) {
  return w == scope::DrawWhich::Lowest ? "lowest" : w == scope::DrawWhich::Highest ? "highest" : w == scope::DrawWhich::Recent ? "recent" : "outer";
}
}  // namespace

int main(int argc, char** argv) {
  // The panel's table as the core has it, in restore_page.py --controls's shape.
  if (argc == 2 && std::string(argv[1]) == "--controls") {
    Json ranges = Json::object(), selects = Json::object();
    for (const auto& r : scope::kRanges) {
      Json o = Json::object();
      o.set("min", num(r.min)); o.set("max", num(r.max)); o.set("step", num(r.step)); o.set("value", num(r.value));
      ranges.set(std::string_view(r.id), o);
    }
    for (const auto& sel : scope::kSelects) {
      Json o = Json::object(), options = Json::array();
      std::string_view all = sel.options ? sel.options : "";
      for (; sel.options;) {
        const std::size_t sep = all.find('\x1f');
        options.a.push_back(Json::string(all.substr(0, sep)));
        if (sep == std::string_view::npos) break;
        all.remove_prefix(sep + 1);
      }
      o.set("options", options); o.set("value", Json::string(std::string_view(sel.value)));
      selects.set(std::string_view(sel.id), o);
    }
    Json out = Json::object();
    out.set("ranges", ranges); out.set("selects", selects);
    std::printf("%s\n", scope::utf16To8(scope::jsonStringify(out)).c_str());
    return 0;
  }
  // The library as the core has it, in the page's PRESETS shape.
  if (argc == 2 && std::string(argv[1]) == "--library") {
    Json out = Json::array();
    for (const auto& p : scope::presets()) {
      if (out.a.empty() || scope::utf16To8(out.a.back().a[0].s) != p.section) {
        Json section = Json::array();
        section.a.push_back(str(p.section)); section.a.push_back(Json::array());
        if (!p.kind.empty()) section.a.push_back(str(p.kind));
        out.a.push_back(section);
      }
      Json entry = Json::array();
      entry.a.push_back(str(p.name)); entry.a.push_back(p.setup); entry.a.push_back(Json::string(p.blurb));
      out.a.back().a[1].a.push_back(entry);
    }
    std::printf("%s\n", scope::utf16To8(scope::jsonStringify(out)).c_str());
    return 0;
  }
  if (argc < 3) { std::fprintf(stderr, "usage: restore_cpp <setups> <sources.json>\n"); return 2; }
  std::vector<scope::Lfo> lfos(2);
  lfos[0].rate = 0.2; lfos[0].depth = 0.5; lfos[1].rate = 0.5; lfos[1].depth = 0.3;
  scope::Generator gen(48000, scope::slot::Used, lfos);
  scope::GeneratorNotes notes(gen);
  scope::Keyboard keys(notes);
  keys.setPresent(false);  // the page in the harness has no keyboard plugged in
  scope::Matrix matrix;
  scope::Brain brain;
  std::vector<std::unique_ptr<StandIn>> standIns;
  {
    std::ifstream f(argv[2]);
    std::string text((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
    const auto list = scope::jsonParse(scope::utf8To16(text));
    for (const auto& s : list->a) {
      auto in = std::make_unique<StandIn>(scope::utf16To8(s.get("id")->s));
      in->reach = s.get("reach")->n;
      in->reachVaries = s.get("varies")->b;
      matrix.registerSource(in.get());
      standIns.push_back(std::move(in));
    }
  }
  std::ifstream file(argv[1]);
  for (std::string line; std::getline(file, line);) {
    if (line.empty()) continue;
    const auto setup = scope::jsonParse(scope::utf8To16(line));
    scope::restoreSetup(*setup, brain, gen, keys, matrix, lfos);

    Json out = Json::object();
    out.set("error", Json::null());
    out.set("a", toneJson(gen.tone()));
    out.set("b", layerJson(gen.toneB()));
    const auto k = keys.settings();
    Json midi = Json::object();
    midi.set("mode", str(modeName(k.mode)));
    Json draws = Json::array();
    for (const auto& d : k.draws) { Json o = Json::object(); o.set("count", num(d.count)); o.set("which", str(whichName(d.which))); draws.a.push_back(o); }
    midi.set("draws", draws);
    Json layers = Json::object();
    layers.set("mode", str(k.layers == scope::LayerMode::Split ? "split" : k.layers == scope::LayerMode::Layer ? "layer" : "off"));
    layers.set("point", num(k.point)); layers.set("pair", str(k.against ? "against" : "each"));
    midi.set("layers", layers);
    midi.set("polyJust", flag(k.polyJust)); midi.set("hold", flag(k.hold));
    midi.set("truth", flag(k.truth)); midi.set("follow", flag(k.follow));
    Json drive = Json::object(), play = Json::object();
    const char* kinds[] = { "wave", "harmonograph", "figure", "wireframe" };
    for (int i = 0; i < 4; i++) drive.set(kinds[i], flag(k.drive[static_cast<std::size_t>(i)]));
    for (int i = 1; i < 4; i++) play.set(kinds[i], flag(k.play[static_cast<std::size_t>(i)]));
    midi.set("drive", drive); midi.set("play", play); midi.set("cc", str(keys.encodeCC()));
    out.set("midi", midi);
    Json panel = Json::object();
    panel.set("freq", str(scope::jsNumberToString(keys.panel().freq)));
    panel.set("interval", str(brain.panel.select("interval")));
    panel.set("figureRate", str(scope::jsNumberToString(keys.panel().figureRate)));
    panel.set("detail", str(scope::jsNumberToString(keys.panel().detail)));
    out.set("panel", panel);
    Json lfoList = Json::array();
    for (int i = 0; i < 2; i++) {
      Json o = Json::object();
      o.set("shape", brain.lfo[static_cast<std::size_t>(i)].shape);
      o.set("rate", num(lfos[static_cast<std::size_t>(i)].rate)); o.set("depth", num(lfos[static_cast<std::size_t>(i)].depth));
      o.set("free", num(brain.lfo[static_cast<std::size_t>(i)].free)); o.set("sync", str(brain.lfo[static_cast<std::size_t>(i)].sync));
      lfoList.a.push_back(o);
    }
    out.set("lfos", lfoList);
    out.set("mod", str(scope::Matrix::encode(matrix.routings())));
    Json key = Json::object();
    key.set("root", num(brain.keyRoot)); key.set("scale", str(brain.keyScale)); key.set("quantise", flag(brain.quantise));
    key.set("glide", num(brain.quantiseGlide)); key.set("bpm", num(brain.tempo));
    out.set("key", key);
    Json cross = Json::object();
    cross.set("on", flag(brain.cross.on)); cross.set("x", num(brain.cross.x)); cross.set("y", num(brain.cross.y));
    cross.set("noteX", num(brain.cross.noteX)); cross.set("noteY", num(brain.cross.noteY));
    cross.set("decayMs", num(brain.cross.decayMs)); cross.set("level", num(brain.cross.level));
    out.set("cross", cross);
    Json score = Json::object();
    score.set("on", flag(brain.score.on)); score.set("step", str(brain.score.step)); score.set("voices", num(brain.score.voices));
    score.set("low", num(brain.score.low)); score.set("octaves", num(brain.score.octaves));
    out.set("score", score);
    Json arp = Json::object();
    arp.set("mode", str(brain.arp.mode)); arp.set("rate", str(brain.arp.rate)); arp.set("octaves", str(brain.arp.octaves));
    out.set("arp", arp);
    Json thresh = Json::object();
    thresh.set("watch", Json::string(brain.threshWatch)); thresh.set("level", num(brain.threshLevel));
    out.set("thresh", thresh);
    out.set("pluck", num(brain.pluckNote));
    Json macros = Json::array();
    for (const auto& m : brain.macros) { Json o = Json::object(); o.set("name", Json::string(m.name)); o.set("value", num(m.value)); macros.a.push_back(o); }
    out.set("macros", macros);
    Json morph = Json::object();
    morph.set("a", str(scope::encodeMorphEnd(brain.morphA, scope::morphHome)));
    morph.set("b", str(scope::encodeMorphEnd(brain.morphB, [&](const std::string& id) {
      if (brain.morphA) for (const auto& [mid, v] : *brain.morphA) if (mid == id) return v;
      return scope::morphHome(id);
    })));
    morph.set("pos", num(brain.morphPos));
    out.set("morph", morph);
    Json photo = Json::object();
    photo.set("on", flag(brain.photo.on)); photo.set("u", num(brain.photo.u)); photo.set("v", num(brain.photo.v));
    out.set("photo", photo);
    const auto& p = brain.plane;
    Json plane = Json::object();
    plane.set("mirror", num(p.mirror)); plane.set("limit", num(p.limit)); plane.set("radius", num(p.radius)); plane.set("os", num(p.os));
    plane.set("twist", num(p.twist)); plane.set("kaleido", num(p.kaleido)); plane.set("snap", num(p.snap));
    plane.set("scaleX", num(p.scaleX)); plane.set("scaleY", num(p.scaleY)); plane.set("shear", num(p.shear));
    out.set("plane", plane);
    const auto& e = brain.echo;
    Json echo = Json::object();
    echo.set("mix", num(e.mix)); echo.set("ms", num(e.ms)); echo.set("sync", str(e.sync)); echo.set("feedback", num(e.feedback));
    echo.set("pingPong", flag(e.pingPong)); echo.set("chorus", num(e.chorus)); echo.set("rate", num(e.rate));
    echo.set("depthMs", num(e.depthMs)); echo.set("centreMs", num(e.centreMs)); echo.set("chorusFeedback", num(e.chorusFeedback));
    out.set("echo", echo);
    std::printf("%s\n", scope::utf16To8(scope::jsonStringify(out)).c_str());
  }
  return 0;
}
