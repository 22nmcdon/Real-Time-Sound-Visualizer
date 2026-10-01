// A setup loaded into the instrument: the page's `restore`, ported for what
// it does to the sound - both layers of the generator, the keyboard, the
// LFOs, the routings, the key, the quantiser and the tempo, the crossings,
// the plane and the echo - and for the settings it keeps for pieces still to
// come (the score, the arpeggiator, the threshold, the macros, the morph, the
// photocell). It is held to the page's own `restore`, run in a browser, by
// core/tests/parity.py.
//
// The page's `restore` writes each value into a control and fires the
// control's handler, so what a setup means is two things at once: what the
// browser makes of a value written into a slider or a menu, and what the
// handler then does with it. Both are here. `Controls` is the browser's part -
// a slider clamps what it is given to its range and snaps it to its step,
// half-way up, and takes its middle for anything that is not a number; a menu
// given a value it has not got has nothing chosen, and reads "" - for the
// sliders and menus the page has (scope/panel_controls.h). `restoreSetup` is
// the handlers' part, in the order `restore` fires them, each with its law:
// hundredths, tenths, degrees, the cutoff's steps, a resonance as a Q.
//
// What differs from the page, and why, so nobody goes looking:
//
// - The view's half of a setup (the display, the trigger, the channels, the
//   filter, the beam, the panes) is the page's to apply. The core keeps the
//   setup it was given, and in the plugin the page reads it from there.
// - The drawn cycles and the figures made of strokes (text, a path, a
//   drawing) are a later piece of the port. Their fields are kept and not yet
//   applied.
// - The page's tempo has a MIDI clock that can override it; here the tempo in
//   force is the setup's, which is what the page's is with no clock running.
// - Three fields the page passes on raw are taken by their truth or their
//   name: `gen` (a mode the page has not got leaves the generator as it was
//   told, and the core plays a waveform), `just` (anything truthy is just),
//   and an LFO's shape (any shape the page does not know plays a sine). The
//   page keeps the raw value as well, which only its panel reads.
// - A legacy LFO destination naming something on Object.prototype ("toString")
//   is not followed; the page would take the function for a destination.

#pragma once

#include <array>
#include <cmath>
#include <map>
#include <optional>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include "scope/generator.h"
#include "scope/json.h"
#include "scope/keyboard.h"
#include "scope/lfo.h"
#include "scope/matrix.h"
#include "scope/panel_controls.h"
#include "scope/setup.h"

namespace scope {

// --- the browser's part: what a control makes of a value written into it ------

inline const RangeSpec* rangeSpec(std::string_view id) {
  for (const auto& r : kRanges) if (id == r.id) return &r;
  return nullptr;
}
inline const SelectSpec* selectSpec(std::string_view id) {
  for (const auto& s : kSelects) if (id == s.id) return &s;
  return nullptr;
}
inline bool selectHas(const SelectSpec& s, std::string_view value) {
  if (!s.options) return false;
  std::string_view all = s.options;
  for (;;) {
    const std::size_t sep = all.find('\x1f');
    if (all.substr(0, sep) == value) return true;
    if (sep == std::string_view::npos) return false;
    all.remove_prefix(sep + 1);
  }
}

// HTML's "valid floating-point number": a minus perhaps, digits and a point
// in either order but not alone, an exponent perhaps. No plus, no space, no
// "Infinity" - all of which JavaScript's Number would take.
inline bool htmlValidFloat(std::string_view s) {
  std::size_t i = 0;
  if (i < s.size() && s[i] == '-') i++;
  std::size_t whole = 0, frac = 0;
  while (i < s.size() && s[i] >= '0' && s[i] <= '9') { i++; whole++; }
  if (i < s.size() && s[i] == '.') {
    i++;
    while (i < s.size() && s[i] >= '0' && s[i] <= '9') { i++; frac++; }
    if (frac == 0) return false;
  }
  if (whole == 0 && frac == 0) return false;
  if (i < s.size() && (s[i] == 'e' || s[i] == 'E')) {
    i++;
    if (i < s.size() && (s[i] == '+' || s[i] == '-')) i++;
    std::size_t exp = 0;
    while (i < s.size() && s[i] >= '0' && s[i] <= '9') { i++; exp++; }
    if (exp == 0) return false;
  }
  return i == s.size();
}

// A slider's value sanitised as the browser sanitises it: a valid number,
// else the slider's middle; clamped to its range; snapped to its step from
// its minimum, a tie going up. Every slider the page has steps in whole
// numbers from a whole minimum, so what comes out is a whole number.
inline double rangeSanitise(const RangeSpec& r, std::string_view written) {
  double v = NAN;
  if (htmlValidFloat(written)) v = std::strtod(std::string(written).c_str(), nullptr);
  if (!std::isfinite(v)) v = r.max < r.min ? r.min : r.min + (r.max - r.min) / 2;
  v = std::fmax(r.min, std::fmin(r.max, v));
  double snapped = r.min + std::floor((v - r.min) / r.step + 0.5) * r.step;
  if (snapped > r.max) snapped -= r.step;
  return snapped == 0 ? 0 : snapped;  // no minus nought: the browser writes "0"
}

// The controls: every slider and menu the page has, holding what the page's
// control would hold - a slider's number, a menu's chosen value or "".
class Controls {
 public:
  Controls() {
    for (const auto& r : kRanges) ranges_[r.id] = r.value;
    for (const auto& s : kSelects) selects_[s.id] = s.value;
  }
  void setRange(const std::string& id, std::u16string written) {
    const RangeSpec* r = rangeSpec(id);
    std::string ascii;
    for (const char16_t c : written) ascii += c < 0x80 ? static_cast<char>(c) : '\x7f';
    ranges_[id] = rangeSanitise(*r, ascii);
  }
  void setSelect(const std::string& id, const std::u16string& written) {
    const SelectSpec* s = selectSpec(id);
    const std::string value = utf16To8(written);
    selects_[id] = selectHas(*s, value) ? value : "";
  }
  double range(const std::string& id) const { return ranges_.at(id); }
  const std::string& select(const std::string& id) const { return selects_.at(id); }
  // Number() of a menu's value, as a handler reads it.
  double selectNumber(const std::string& id) const { return jsStringToNumber(utf8To16(select(id))); }

 private:
  std::map<std::string, double> ranges_;
  std::map<std::string, std::string> selects_;
};

// --- the brain's state that a setup sets beyond the generator ----------------------

struct Brain {
  Controls panel;
  std::string inputFrom = "live";  // genInput.from
  double inputMode = 0;            // genInput.mode
  struct LfoSetting { Json shape = Json::string(std::string_view("sine")); double free = 0.2; std::string sync; };
  std::array<LfoSetting, 2> lfo { { { Json::string(std::string_view("sine")), 0.2, "" },
                                    { Json::string(std::string_view("sine")), 0.5, "" } } };
  double keyRoot = 0;
  std::string keyScale = "chromatic";
  bool quantise = false;
  double quantiseGlide = 0;
  double tempo = 120;  // transport.set, and the tempo in force
  struct Cross { bool on = false; double x = 0, y = 0, noteX = 60, noteY = 67, decayMs = 180, level = 0.4; } cross;
  struct Score { bool on = false; std::string step = "1/16"; double voices = 2, low = 48, octaves = 3; } score;
  struct Arp { std::string mode = "off", rate = "1/8", octaves = "1"; } arp;  // the menus' values
  std::u16string threshWatch = u"env.live";
  double threshLevel = 0.5, pluckNote = 60;
  struct Macro { std::u16string name; double value = 0; };
  std::array<Macro, 4> macros { { { u"Macro 1", 0 }, { u"Macro 2", 0 }, { u"Macro 3", 0 }, { u"Macro 4", 0 } } };
  using MorphEnd = std::vector<std::pair<std::string, double>>;  // every slider the morph walks, in order
  std::optional<MorphEnd> morphA, morphB;
  double morphPos = 0;
  struct Photo { bool on = false; double u = 0.75, v = 0.5; } photo;
  struct PlaneState {
    double mirror = 0, limit = 0, radius = 0.4, os = 2, twist = 0, kaleido = 0, snap = 0, scaleX = 1, scaleY = 1, shear = 0;
  } plane;
  struct EchoState {
    double mix = 0, ms = 375;
    std::string sync;
    double feedback = 0.35;
    bool pingPong = false;
    double chorus = 0, rate = 0.6, depthMs = 3, centreMs = 12, chorusFeedback = 0;
  } echo;
};

// --- the tables restore reads -----------------------------------------------------------

struct ScaleSpec { const char* id; std::vector<int> degrees; };
inline const std::vector<ScaleSpec>& scales() {  // SCALES
  static const std::vector<ScaleSpec> list {
    { "chromatic", { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 } }, { "major", { 0, 2, 4, 5, 7, 9, 11 } },
    { "minor", { 0, 2, 3, 5, 7, 8, 10 } }, { "dorian", { 0, 2, 3, 5, 7, 9, 10 } },
    { "phrygian", { 0, 1, 3, 5, 7, 8, 10 } }, { "lydian", { 0, 2, 4, 6, 7, 9, 11 } },
    { "mixolydian", { 0, 2, 4, 5, 7, 9, 10 } }, { "locrian", { 0, 1, 3, 5, 6, 8, 10 } },
    { "harmonic", { 0, 2, 3, 5, 7, 8, 11 } }, { "pentatonic", { 0, 2, 4, 7, 9 } }, { "minorpent", { 0, 3, 5, 7, 10 } },
    { "blues", { 0, 3, 5, 6, 7, 10 } }, { "whole", { 0, 2, 4, 6, 8, 10 } },
  };
  return list;
}
inline int keyMask(double root, const std::string& scale) {
  const ScaleSpec* found = &scales()[0];
  for (const auto& s : scales()) if (scale == s.id) found = &s;
  int mask = 0;
  for (const int degree : found->degrees) mask |= 1 << static_cast<int>(std::fmod(root + degree, 12));
  return mask;
}
inline double syncBeats(const std::string& sync) {  // LFO_SYNC
  static const std::pair<const char*, double> table[] = {
    { "4", 16 }, { "2", 8 }, { "1", 4 }, { "1/2", 2 }, { "1/4", 1 }, { "1/8", 0.5 }, { "1/16", 0.25 },
    { "1/4t", 2.0 / 3 }, { "1/8t", 1.0 / 3 },
  };
  for (const auto& [id, beats] : table) if (sync == id) return beats;
  return 0;
}
inline double delayBeats(const std::string& sync) {  // DELAY_SYNC
  static const std::pair<const char*, double> table[] = {
    { "1/2", 2 }, { "1/4", 1 }, { "1/8d", 0.75 }, { "1/8", 0.5 }, { "1/4t", 2.0 / 3 }, { "1/8t", 1.0 / 3 }, { "1/16", 0.25 },
  };
  for (const auto& [id, beats] : table) if (sync == id) return beats;
  return 0;
}
inline bool delaySyncKnown(const std::u16string& s) {
  return s.empty() || s == u"1/2" || s == u"1/4" || s == u"1/8d" || s == u"1/8" || s == u"1/4t" || s == u"1/8t" || s == u"1/16";
}
inline double cutoffHz(double step) { return 20 * std::pow(1000.0, step / 1000); }  // CUTOFF_STEPS a thousand
inline double resonanceQ(double v) { return std::sqrt(0.5) * std::pow(20 / std::sqrt(0.5), v / 100); }

// MORPH_IDS: the sliders the morph walks, in the page's order, less those that
// are not part of a sound.
inline const std::vector<std::string>& morphIds() {
  static const std::vector<std::string> ids = [] {
    std::vector<std::string> out;
    for (const auto& r : kRanges) {
      const std::string id = r.id;
      if (id == "morphPos" || id == "macro1" || id == "macro2" || id == "macro3" || id == "macro4"
          || id == "fileSeek" || id == "keysVelocity" || id == "align") continue;
      out.push_back(id);
    }
    return out;
  }();
  return ids;
}
inline double morphHome(const std::string& id) { return rangeSpec(id)->value; }

// decodeMorphEnd: "=" and then id:value pairs; nothing for anything else.
template <class Ref>
std::optional<Brain::MorphEnd> decodeMorphEnd(const Json* text, Ref ref) {
  if (!text || text->type != Json::Type::String || text->s.empty() || text->s[0] != u'=') return std::nullopt;
  std::map<std::string, double> given;
  const std::u16string body = text->s.substr(1);
  std::size_t at = 0;
  while (at <= body.size()) {
    const std::size_t end = std::min(body.find(u',', at), body.size());
    const std::u16string part = body.substr(at, end - at);
    const std::size_t colon = part.find(u':');
    const std::string id = utf16To8(part.substr(0, colon));
    if (colon != std::u16string::npos) {
      const std::size_t next = part.find(u':', colon + 1);
      const double value = jsStringToNumber(part.substr(colon + 1, next == std::u16string::npos ? std::u16string::npos : next - colon - 1));
      bool known = false;
      for (const auto& m : morphIds()) if (m == id) known = true;
      if (known && std::isfinite(value)) given[id] = value;
    }
    if (end >= body.size()) break;
    at = end + 1;
  }
  Brain::MorphEnd out;
  for (const auto& id : morphIds()) {
    const auto found = given.find(id);
    out.emplace_back(id, found != given.end() ? found->second : ref(id));
  }
  return out;
}
// encodeMorphEnd: what differs from the reference, after the "=".
template <class Ref>
std::string encodeMorphEnd(const std::optional<Brain::MorphEnd>& end, Ref ref) {
  if (!end) return "";
  std::string out = "=";
  bool first = true;
  for (const auto& [id, value] : *end) {
    if (value == ref(id)) continue;
    out += (first ? "" : ",") + id + ":" + jsNumberToString(value);
    first = false;
  }
  return out;
}

// parseRegistration: nine digits among whatever else, each no more than eight.
inline std::optional<std::array<double, 9>> parseRegistrationText(const std::u16string& text) {
  std::array<double, 9> out {};
  std::size_t n = 0;
  for (const char16_t c : text) {
    if (c < u'0' || c > u'9') continue;
    if (n == 9) return std::nullopt;
    out[n++] = std::fmin(8.0, static_cast<double>(c - u'0'));
  }
  if (n != 9) return std::nullopt;
  return out;
}

// One row of LAYER_CONTROLS: the control, the generator's field, and its law.
struct LayerControl { const char* id; const char* field; enum Kind { Range, Menu, Text } kind; double (*law)(double); };
inline const std::vector<LayerControl>& layerControls() {
  static const std::vector<LayerControl> rows {
    { "amp", "amp", LayerControl::Range, [](double v) { return v / 100; } },
    { "shape", "shape", LayerControl::Text, nullptr },
    { "envAttack", "attackMs", LayerControl::Range, [](double v) { return v; } },
    { "envDecay", "decayMs", LayerControl::Range, [](double v) { return v; } },
    { "envSustain", "sustain", LayerControl::Range, [](double v) { return v / 100; } },
    { "envRelease", "releaseMs", LayerControl::Range, [](double v) { return v; } },
    { "bars", "bars", LayerControl::Text, nullptr },
    { "morph", "morph", LayerControl::Range, [](double v) { return v / 100; } },
    { "width", "width", LayerControl::Range, [](double v) { return v / 100; } },
    { "table", "table", LayerControl::Range, [](double v) { return v / 100; } },
    { "oscRatio", "modRatio", LayerControl::Menu, [](double v) { return v; } },
    { "oscFm", "fmIndex", LayerControl::Range, [](double v) { return v / 10; } },
    { "oscRing", "ringMix", LayerControl::Range, [](double v) { return v / 100; } },
    { "oscSync", "syncRatio", LayerControl::Range, [](double v) { return v / 100; } },
    { "oscSub", "subLevel", LayerControl::Range, [](double v) { return v / 100; } },
    { "oscSubOct", "subOctave", LayerControl::Menu, [](double v) { return v; } },
    { "oscSubShape", "subShape", LayerControl::Text, nullptr },
    { "oscUnison", "unison", LayerControl::Menu, [](double v) { return v; } },
    { "oscSpread", "unisonCents", LayerControl::Range, [](double v) { return v; } },
    { "shpDrive", "drive", LayerControl::Range, [](double v) { return v / 100; } },
    { "shpFold", "fold", LayerControl::Range, [](double v) { return v / 100; } },
    { "shpBits", "crushBits", LayerControl::Menu, [](double v) { return v; } },
    { "shpRate", "crushHz", LayerControl::Menu, [](double v) { return v; } },
    { "vcfType", "vcfType", LayerControl::Menu, [](double v) { return v; } },
    { "vcfCut", "vcfCutoff", LayerControl::Range, [](double v) { return cutoffHz(v); } },
    { "vcfRes", "vcfQ", LayerControl::Range, [](double v) { return resonanceQ(v); } },
    { "vcfTrack", "vcfTrack", LayerControl::Range, [](double v) { return v / 100; } },
    { "vcfEnvAmt", "vcfEnv", LayerControl::Range, [](double v) { return v / 10; } },
    { "vcfAtk", "fAttackMs", LayerControl::Range, [](double v) { return v; } },
    { "vcfDec", "fDecayMs", LayerControl::Range, [](double v) { return v; } },
    { "vcfSus", "fSustain", LayerControl::Range, [](double v) { return v / 100; } },
    { "vcfRel", "fReleaseMs", LayerControl::Range, [](double v) { return v; } },
  };
  return rows;
}
inline bool isVoiceControl(std::string_view id) {
  return id.substr(0, 3) == "osc" || id.substr(0, 3) == "shp" || id.substr(0, 3) == "vcf";
}

// The voice's controls from the panel into one layer, each through its law,
// as `restore` sends layer A's after writing them.
inline void applyVoiceLaws(Generator& gen, const Controls& panel, int layer) {
  for (const auto& row : layerControls()) {
    if (!isVoiceControl(row.id)) continue;
    if (row.kind == LayerControl::Text) { gen.set(row.field, panel.select(row.id), layer); continue; }
    const double v = row.kind == LayerControl::Range ? panel.range(row.id) : panel.selectNumber(row.id);
    gen.set(row.field, row.law(v), layer);
  }
}

// Layer B's sound: B's own field where the setup gives one, else what the
// setup gives layer A - a number held to its slider's range, a registration
// that does not read falling back to A's sliders - and nothing at all for a
// value that cannot be used.
template <class Field>
void applyLayerB(const Json& partial, Field s, Generator& gen, const Controls& panel) {
  static const std::pair<const char*, const char*> keys[] = {
    { "amp", "bAmp" }, { "shape", "bShape" }, { "envAttack", "bAtk" }, { "envDecay", "bDec" }, { "envSustain", "bSus" },
    { "envRelease", "bRel" }, { "bars", "bBars" }, { "morph", "bMorph" }, { "width", "bWidth" }, { "table", "bTable" },
    { "oscRatio", "bRatio" }, { "oscFm", "bFm" }, { "oscRing", "bRing" }, { "oscSync", "bSync" }, { "oscSub", "bSub" },
    { "oscSubOct", "bSubOct" }, { "oscSubShape", "bSubShape" }, { "oscUnison", "bUnison" }, { "oscSpread", "bSpread" },
    { "shpDrive", "bDrive" }, { "shpFold", "bFold" }, { "shpBits", "bBits" }, { "shpRate", "bRate" }, { "vcfType", "bVcf" },
    { "vcfCut", "bVcfCut" }, { "vcfRes", "bVcfRes" }, { "vcfTrack", "bVcfTrack" }, { "vcfEnvAmt", "bVcfEnv" },
    { "vcfAtk", "bVcfAtk" }, { "vcfDec", "bVcfDec" }, { "vcfSus", "bVcfSus" }, { "vcfRel", "bVcfRel" },
  };
  static const std::pair<const char*, const char*> fallback[] = {
    { "amp", "amp" }, { "shape", "shape" }, { "envAttack", "atk" }, { "envDecay", "dec" }, { "envSustain", "sus" },
    { "envRelease", "rel" }, { "morph", "morph" },
  };
  for (const auto& row : layerControls()) {
    std::string key, from = row.id;
    for (const auto& [id, k] : keys) if (std::string_view(row.id) == id) key = k;
    for (const auto& [id, f] : fallback) if (std::string_view(row.id) == id) from = f;
    const Json* own = partial.type == Json::Type::Object ? partial.get(key) : nullptr;
    Json raw = own ? *own : (s(from) ? *s(from) : Json());
    const bool missing = !own && !s(from);
    const bool bars = std::string_view(row.id) == "bars";
    if (bars && !parseRegistrationText(missing ? u"" : jsToString(raw))) {
      std::u16string sliders;
      for (int k = 0; k < 9; k++) sliders += toU16(jsNumberToString(panel.range("bar" + std::to_string(k))));
      raw = Json::string(sliders);
    }
    // A number held to its slider's range, as A's is by the slider itself.
    if (row.kind == LayerControl::Range && !missing && raw.type != Json::Type::Null
        && !(raw.type == Json::Type::String && raw.s.empty()) && std::isfinite(jsToNumber(&raw))) {
      const RangeSpec* r = rangeSpec(row.id);
      raw = Json::number(std::fmax(r->min, std::fmin(r->max, jsToNumber(&raw))));
    }
    if (row.kind == LayerControl::Text) {
      if (bars) {
        const auto levels = parseRegistrationText(jsToString(raw));
        if (levels) gen.setBars(std::vector<double>(levels->begin(), levels->end()), 1);
      } else if (!missing && raw.type == Json::Type::String) {
        gen.set(row.field, std::string_view(utf16To8(raw.s)), 1);
      }
      continue;
    }
    const double v = missing ? NAN : jsToNumber(&raw);
    if (std::isfinite(v)) gen.set(row.field, row.law(v), 1);
  }
}

// --- the handlers' part, in restore's order -------------------------------------------------

inline void restoreSetup(const Json& partial, Brain& brain, Generator& gen, Keyboard& keys, Matrix& matrix,
                         std::vector<Lfo>& lfos) {
  const Json& defaults = setupDefaults();
  const bool given = partial.type == Json::Type::Object;
  // s = Object.assign({}, DEFAULTS, partial): the setup's own field, else the default.
  const auto s = [&](std::string_view key) -> const Json* {
    if (given) if (const Json* v = partial.get(key)) return v;
    return defaults.get(key);
  };
  const auto num = [&](std::string_view key) { return jsToNumber(s(key)); };
  const auto str = [&](std::string_view key) -> std::u16string { const Json* v = s(key); return v ? jsToString(*v) : u"undefined"; };
  const auto isTrue = [&](std::string_view key) { const Json* v = s(key); return v && v->type == Json::Type::Bool && v->b; };
  const auto isString = [&](std::string_view key, std::u16string_view want) { const Json* v = s(key); return v && v->type == Json::Type::String && v->s == want; };
  // within(): a finite number held to a range, else the default.
  const auto within = [&](std::string_view key, double lo, double hi, double dflt) {
    const double v = num(key);
    return std::isfinite(v) ? std::fmax(lo, std::fmin(hi, v)) : dflt;
  };
  // [..].includes(s.x): a number, and one of these.
  const auto among = [&](std::string_view key, std::initializer_list<double> list, double dflt) {
    const Json* v = s(key);
    if (v && v->type == Json::Type::Number) for (const double x : list) if (v->n == x) return v->n;
    return dflt;
  };
  Controls& panel = brain.panel;
  const auto u16 = [](std::string_view a) { return toU16(a); };
  const auto setA = [&](std::string_view field, double v) { gen.set(field, v, 0); };

  // The panel's own values first, each as its control takes it.
  panel.setSelect("shape", str("shape"));
  {
    const std::u16string bars = str("bars");
    const auto levels = parseRegistrationText(bars);
    const std::u16string use = levels ? bars : jsToString(*defaults.get("bars"));
    const auto set = *parseRegistrationText(use);
    for (int k = 0; k < 9; k++) panel.setRange("bar" + std::to_string(k), toU16(jsNumberToString(set[static_cast<std::size_t>(k)])));
  }
  panel.setRange("morph", std::isfinite(num("morph")) ? str("morph") : u"150");
  panel.setRange("width", std::isfinite(num("width")) ? toU16(jsNumberToString(std::fmax(5, std::fmin(95, num("width"))))) : u"25");
  panel.setRange("table", std::isfinite(num("table")) ? toU16(jsNumberToString(std::fmax(0, std::fmin(300, num("table"))))) : u"150");
  panel.setRange("freq", str("freq"));
  panel.setRange("amp", str("amp"));
  panel.setSelect("interval", str("interval"));
  panel.setRange("phase", str("phase"));
  panel.setSelect("figure", str("figure"));
  panel.setRange("detail", str("detail"));
  panel.setRange("figureRate", str("figureRate"));
  panel.setRange("swingRate", str("swingRate"));
  panel.setRange("decay", str("decay"));
  panel.setRange("swingDrive", str("swingDrive"));
  panel.setSelect("inputMode", toU16(jsNumberToString(among("inputMode", { 0, 1, 2, 3 }, 0))));
  panel.setRange("inputDepth", str("inputDepth"));
  brain.inputFrom = isString("inputFrom", u"gen2") ? "gen2" : "live";
  {
    const Json* f = s("gen2Figure");
    static const char16_t* figures[] = { u"Circle", u"Square", u"Polygon", u"Star", u"Rose", u"Heart", u"Infinity",
                                         u"Spiral", u"Spirograph", u"Butterfly" };
    bool ok = false;
    if (f && f->type == Json::Type::String) for (const char16_t* x : figures) if (f->s == x) ok = true;
    panel.setSelect("gen2Figure", ok ? f->s : u"Circle");
    const double rate = num("gen2Rate");
    panel.setRange("gen2Rate", toU16(jsNumberToString(jsMathRound(std::fmax(1, std::fmin(1000, rate == 0 || std::isnan(rate) ? 110 : rate))))));
  }
  gen.set("gen2Figure", panel.select("gen2Figure"), 0);
  setA("gen2Rate", panel.range("gen2Rate"));
  gen.set("inputFrom", brain.inputFrom, 0);  // syncGen2
  {
    const double mode = panel.selectNumber("inputMode");
    brain.inputMode = mode == 0 || std::isnan(mode) ? 0 : mode;
    setA("inputMode", brain.inputMode);
  }
  panel.setRange("detune", str("detune"));
  panel.setRange("envAttack", str("atk"));
  panel.setRange("envDecay", str("dec"));
  panel.setRange("envSustain", str("sus"));
  panel.setRange("envRelease", str("rel"));
  panel.setRange("glide", str("glide"));
  panel.setSelect("model", str("model"));
  for (const char* axis : { "spinX", "spinY", "spinZ" }) panel.setRange(axis, str(axis));
  panel.setRange("spinRate", str("spinRate"));
  panel.setRange("depth", str("depth"));
  panel.setSelect("genMode", str("gen"));

  // The sliders' handlers, as `restore` fires them.
  setA("freq", panel.range("freq"));
  setA("amp", panel.range("amp") / 100);
  setA("phase", panel.range("phase") * kPi / 180);
  setA("detail", panel.range("detail"));
  setA("figureRate", panel.range("figureRate"));
  setA("swingRate", panel.range("swingRate") / 10);
  setA("decay", panel.range("decay") / 100);
  setA("swingDrive", panel.range("swingDrive") / 100);
  setA("inputDepth", panel.range("inputDepth") / 100);
  setA("detune", panel.range("detune") / 10000);
  gen.setSpin({ panel.range("spinX") / 100, panel.range("spinY") / 100, panel.range("spinZ") / 100 });
  setA("spinRate", panel.range("spinRate") / 100);
  setA("depth", panel.range("depth") / 100);
  setA("attackMs", panel.range("envAttack"));
  setA("decayMs", panel.range("envDecay"));
  setA("sustain", panel.range("envSustain") / 100);
  setA("releaseMs", panel.range("envRelease"));
  setA("glideMs", panel.range("glide"));
  setA("morph", panel.range("morph") / 100);
  setA("width", panel.range("width") / 100);
  setA("table", panel.range("table") / 100);
  gen.set("shape", panel.select("shape"), 0);
  {
    std::vector<double> bars;
    for (int k = 0; k < 9; k++) bars.push_back(std::fmin(8.0, panel.range("bar" + std::to_string(k))));
    gen.setBars(bars, 0);
  }

  // The voice's oscillator, shaping and filter: sliders held to their range,
  // menus to their options, then each through its law.
  static const std::pair<const char*, std::pair<double, double>> oscRanges[] = {
    { "oscFm", { 0, 100 } }, { "oscRing", { 0, 100 } }, { "oscSync", { 100, 800 } }, { "oscSub", { 0, 100 } },
    { "oscSpread", { 0, 50 } }, { "shpDrive", { 0, 100 } }, { "shpFold", { 0, 100 } }, { "vcfCut", { 0, 1000 } },
    { "vcfRes", { 0, 100 } }, { "vcfTrack", { 0, 100 } }, { "vcfEnvAmt", { -40, 40 } }, { "vcfAtk", { 0, 1000 } },
    { "vcfDec", { 1, 2000 } }, { "vcfSus", { 0, 100 } }, { "vcfRel", { 1, 2000 } },
  };
  for (const auto& [id, lohi] : oscRanges) {
    const double v = num(id);
    panel.setRange(id, std::isfinite(v) ? toU16(jsNumberToString(std::fmax(lohi.first, std::fmin(lohi.second, v))))
                                        : jsToString(*defaults.get(id)));
  }
  {
    const Json* os = s("shpOS");
    panel.setSelect("shpOS", os && os->type == Json::Type::Number && os->n == 4 ? u"4" : u"2");
    setA("shapeOS", panel.selectNumber("shpOS"));
  }
  for (const char* id : { "oscRatio", "oscSubOct", "oscSubShape", "oscUnison", "shpBits", "shpRate", "vcfType" }) {
    const std::u16string want = str(id);
    const SelectSpec* spec = selectSpec(id);
    panel.setSelect(id, selectHas(*spec, utf16To8(want)) ? want : jsToString(*defaults.get(id)));
  }
  applyVoiceLaws(gen, panel, 0);

  gen.set("figure", panel.select("figure"), 0);
  gen.set("model", panel.select("model"), 0);
  setA("interval", panel.selectNumber("interval"));

  // The kind, a reswing, and the tuning, as the page passes them.
  {
    const Json* g = s("gen");
    gen.set("mode", g && g->type == Json::Type::String ? std::string_view(utf16To8(g->s)) : std::string_view("wave"), 0);
  }
  gen.reswing();
  {
    const Json* j = s("just");
    const bool truthy = j && !(j->type == Json::Type::Null || (j->type == Json::Type::Bool && !j->b)
                               || (j->type == Json::Type::Number && (j->n == 0 || std::isnan(j->n)))
                               || (j->type == Json::Type::String && j->s.empty()));
    setA("just", truthy ? 1 : 0);
  }

  // The keyboard.
  Keyboard::Settings k = keys.settings();
  k.mode = isString("midiMode", u"mono") ? NoteMode::Mono : isString("midiMode", u"poly") ? NoteMode::Poly : NoteMode::Dyad;
  const auto rule = [&](std::string_view key) {
    const Json* v = s(key);
    if (v && v->type == Json::Type::String) {
      if (v->s == u"lowest") return DrawWhich::Lowest;
      if (v->s == u"highest") return DrawWhich::Highest;
      if (v->s == u"recent") return DrawWhich::Recent;
    }
    return DrawWhich::Outer;
  };
  const auto count = [&](std::string_view key) {
    const double v = num(key);
    return std::fmax(2, std::fmin(kPolyVoices, v == 0 || std::isnan(v) ? 2 : v));
  };
  k.draws[0] = { count("midiDrawCount"), rule("midiDrawWhich") };
  k.draws[1] = { count("midiDrawCountB"), rule("midiDrawWhichB") };
  k.layers = isString("layers", u"split") ? LayerMode::Split : isString("layers", u"layer") ? LayerMode::Layer : LayerMode::Off;
  {
    const Json* at = s("splitAt");
    k.point = at && at->type == Json::Type::Number && std::isfinite(at->n) && at->n == std::floor(at->n)
            ? static_cast<int>(std::fmax(0, std::fmin(127, at->n))) : 60;
  }
  k.against = isString("layerPair", u"against");

  // Layer B: its own field where the setup gives one, else layer A's.
  applyLayerB(partial, s, gen, panel);

  k.polyJust = isTrue("midiPolyJust");
  // Math.min and Math.max carry a NaN through, where fmin and fmax drop it.
  brain.photo.u = jsMax(0, jsMin(1, num("photoU")));
  brain.photo.v = jsMax(0, jsMin(1, num("photoV")));
  if (!std::isfinite(brain.photo.u)) brain.photo.u = 0.75;
  if (!std::isfinite(brain.photo.v)) brain.photo.v = 0.5;
  brain.photo.on = isTrue("photoOn");
  k.hold = isTrue("midiHold");
  {
    const Json* t = s("midiTruth");
    k.truth = !(t && t->type == Json::Type::Bool && !t->b);
  }
  k.follow = isTrue("midiFollow");
  const auto kinds = [&](std::string_view key) {
    const std::u16string list = str(key);
    std::array<bool, 4> out { false, false, false, false };
    static const char16_t* names[] = { u"wave", u"harmonograph", u"figure", u"wireframe" };
    std::size_t at = 0;
    while (at <= list.size()) {
      const std::size_t end = std::min(list.find(u',', at), list.size());
      for (std::size_t i = 0; i < 4; i++) if (list.substr(at, end - at) == names[i]) out[i] = true;
      if (end >= list.size()) break;
      at = end + 1;
    }
    return out;
  };
  k.drive = kinds("midiDrive");
  k.play = kinds("midiPlay");
  {
    const double ring = num("ring");
    panel.setRange("ringTime", toU16(jsNumberToString(std::fmax(20, std::fmin(4000, ring == 0 || std::isnan(ring) ? 600 : ring)))));
    setA("ringMs", panel.range("ringTime"));
  }
  keys.setSettings(k);
  keys.decodeCC(str("cc"));
  keys.panel() = { panel.range("freq"), static_cast<int>(panel.selectNumber("interval")), panel.range("figureRate"),
                   panel.range("detail") };
  keys.apply();

  // The LFOs, the key, the quantiser and the tempo.
  for (int i = 0; i < 2; i++) {
    const std::string key = "l" + std::to_string(i);
    Brain::LfoSetting& l = brain.lfo[static_cast<std::size_t>(i)];
    const Json* shape = s(key + "s");
    l.shape = shape ? *shape : Json();
    l.free = jsToNumber(s(key + "r")) / 100;
    const std::u16string sync = str(key + "y");
    l.sync = syncBeats(utf16To8(sync)) > 0 ? utf16To8(sync) : "";
    Lfo& lfo = lfos[static_cast<std::size_t>(i)];
    lfo.setShape(shape && shape->type == Json::Type::String ? utf16To8(shape->s) : "sine");
    lfo.rate = l.free;
    lfo.depth = jsToNumber(s(key + "a")) / 100;
  }
  {
    const Json* root = s("keyRoot");
    brain.keyRoot = root && root->type == Json::Type::Number && std::isfinite(root->n) && root->n == std::floor(root->n)
                  ? std::fmod(std::fmod(root->n, 12) + 12, 12) : 0;
    const std::string scale = utf16To8(str("keyScale"));
    brain.keyScale = "chromatic";
    for (const auto& sc : scales()) if (scale == sc.id && s("keyScale")->type == Json::Type::String) brain.keyScale = sc.id;
    brain.quantise = isTrue("quant");
    const double glide = num("qGlide");
    brain.quantiseGlide = std::fmax(0, std::fmin(300, glide == 0 || std::isnan(glide) ? 0 : glide));
    const double bpm = num("bpm");
    brain.tempo = std::fmax(30, std::fmin(300, jsMathRound(bpm == 0 || std::isnan(bpm) ? 120 : bpm)));
  }
  for (int i = 0; i < 2; i++) {  // clockStep: an LFO locked to the tempo runs at it
    const double beats = syncBeats(brain.lfo[static_cast<std::size_t>(i)].sync);
    if (beats > 0) lfos[static_cast<std::size_t>(i)].rate = brain.tempo / 60 / beats;
  }
  setA("qMask", brain.quantise ? keyMask(brain.keyRoot, brain.keyScale) : 0);
  setA("qGlideMs", brain.quantiseGlide);

  // The crossings.
  brain.cross.on = isTrue("crossOn");
  brain.cross.x = within("crossX", -100, 100, 0) / 100;
  brain.cross.y = within("crossY", -100, 100, 0) / 100;
  brain.cross.noteX = jsMathRound(within("crossNoteX", 36, 84, 60));
  brain.cross.noteY = jsMathRound(within("crossNoteY", 36, 84, 67));
  brain.cross.decayMs = jsMathRound(within("crossDecay", 20, 1000, 180));
  brain.cross.level = within("crossLevel", 0, 100, 40) / 100;
  setA("crossOn", brain.cross.on ? 1 : 0);
  setA("crossX", brain.cross.x);
  setA("crossY", brain.cross.y);
  setA("crossHzX", midiHz(brain.cross.noteX));
  setA("crossHzY", midiHz(brain.cross.noteY));
  setA("crossDecayMs", brain.cross.decayMs);
  setA("crossLevel", brain.cross.level);

  // The score, the arpeggiator, the threshold and the pluck: kept for their pieces.
  brain.score.on = isTrue("scoreOn");
  brain.score.step = isString("scoreStep", u"1/8") ? "1/8" : isString("scoreStep", u"1/4") ? "1/4" : "1/16";
  brain.score.voices = jsMathRound(within("scoreVoices", 1, 4, 2));
  brain.score.low = among("scoreLow", { 36, 48, 60 }, 48);
  brain.score.octaves = jsMathRound(within("scoreOctaves", 1, 4, 3));
  {
    const Json* m = s("arpMode");
    static const char16_t* modes[] = { u"off", u"up", u"down", u"updown", u"played", u"random" };
    brain.arp.mode = "off";
    if (m && m->type == Json::Type::String) for (const char16_t* x : modes) if (m->s == x) brain.arp.mode = utf16To8(m->s);
    const Json* r = s("arpRate");
    static const char16_t* rates[] = { u"1/4", u"1/8", u"1/16", u"1/8t", u"1/16t" };
    brain.arp.rate = "1/8";
    if (r && r->type == Json::Type::String) for (const char16_t* x : rates) if (r->s == x) brain.arp.rate = utf16To8(r->s);
    brain.arp.octaves = jsNumberToString(jsMathRound(within("arpOctaves", 1, 3, 1)));
  }
  keys.apply();  // arpSet, which ends in midiApplyNotes
  {
    const Json* w = s("threshWatch");
    brain.threshWatch = w && w->type == Json::Type::String && !w->s.empty() ? w->s : u"env.live";
    brain.threshLevel = within("threshLevel", 5, 95, 50) / 100;
    brain.pluckNote = jsMathRound(within("pluckNote", 36, 84, 60));
  }

  // The macros and the morph.
  {
    const Json* names = s("macroNames");
    std::vector<std::u16string> list;
    if (names && names->type == Json::Type::String) {
      std::size_t at = 0;
      for (;;) {
        const std::size_t end = names->s.find(u'|', at);
        list.push_back(names->s.substr(at, end == std::u16string::npos ? std::u16string::npos : end - at));
        if (end == std::u16string::npos) break;
        at = end + 1;
      }
    }
    for (int i = 0; i < 4; i++) {
      Brain::Macro& m = brain.macros[static_cast<std::size_t>(i)];
      m.value = std::fmax(0, std::fmin(1, within("mac" + std::to_string(i + 1), 0, 100, 0) / 100));
      std::u16string name = static_cast<std::size_t>(i) < list.size() ? list[static_cast<std::size_t>(i)] : u"";
      std::u16string clean;
      for (const char16_t c : name) if (c != u'|') clean += c;
      clean = jsTrim(clean).substr(0, 16);
      m.name = clean.empty() ? u"Macro " + u16(std::to_string(i + 1)) : clean;
    }
    brain.morphA = decodeMorphEnd(s("morphA"), morphHome);
    const auto refB = [&](const std::string& id) {
      if (brain.morphA) for (const auto& [mid, v] : *brain.morphA) if (mid == id) return v;
      return morphHome(id);
    };
    brain.morphB = decodeMorphEnd(s("morphB"), refB);
    brain.morphPos = within("morphPos", 0, 100, 0) / 100;
  }

  // The plane and the echo.
  {
    Brain::PlaneState& p = brain.plane;
    p.mirror = among("planeMirror", { 0, 1, 2, 3 }, 0);
    p.limit = among("planeLimit", { 0, 1, 2 }, 0);
    p.radius = within("planeRadius", 2, 100, 40) / 100;
    p.os = among("planeOS", { 1, 2, 4 }, 2);
    p.twist = within("planeTwist", -100, 100, 0) / 100;
    p.kaleido = among("planeKaleido", { 0, 2, 3, 4, 5, 6, 8 }, 0);
    p.snap = among("planeSnap", { 0, 1, 2, 3, 4, 5, 6 }, 0);
    p.scaleX = within("planeScaleX", 0, 200, 100) / 100;
    p.scaleY = within("planeScaleY", 0, 200, 100) / 100;
    p.shear = within("planeShear", -100, 100, 0) / 100;
    setA("planeMirror", p.mirror); setA("planeLimit", p.limit); setA("planeRadius", p.radius); setA("planeOS", p.os);
    setA("planeTwist", p.twist * kTwoPi); setA("planeKaleido", p.kaleido); setA("planeSnap", p.snap);
    setA("planeScaleX", p.scaleX); setA("planeScaleY", p.scaleY); setA("planeShear", p.shear);
  }
  {
    Brain::EchoState& e = brain.echo;
    e.mix = within("delayMix", 0, 100, 0) / 100;
    e.ms = jsMathRound(within("delayMs", 10, 2000, 375));
    const Json* sync = s("delaySync");
    e.sync = sync && sync->type == Json::Type::String && delaySyncKnown(sync->s) ? utf16To8(sync->s) : "";
    e.feedback = within("delayFeedback", 0, 90, 35) / 100;
    e.pingPong = isTrue("delayPingPong");
    e.chorus = within("chorusMix", 0, 100, 0) / 100;
    e.rate = within("chorusRate", 5, 500, 60) / 100;
    e.depthMs = within("chorusDepth", 0, 100, 30) / 10;
    e.centreMs = within("chorusTime", 10, 300, 120) / 10;
    e.chorusFeedback = within("chorusFeedback", 0, 90, 0) / 100;
    const double beats = delayBeats(e.sync);
    setA("delayMix", e.mix);
    setA("delayMs", beats > 0 ? std::fmin(2000, beats * 60000 / brain.tempo) : e.ms);
    setA("delayFeedback", e.feedback);
    setA("delayPingPong", e.pingPong ? 1 : 0);
    setA("chorusMix", e.chorus); setA("chorusRate", e.rate); setA("chorusDepthMs", e.depthMs);
    setA("chorusMs", e.centreMs); setA("chorusFeedback", e.chorusFeedback);
  }

  // The routings: the setup's list, or the old enum when it has none.
  {
    const Json* mod = given ? partial.get("mod") : nullptr;
    std::vector<Routing> list;
    if (mod) {
      const bool falsy = mod->type == Json::Type::Null || (mod->type == Json::Type::Bool && !mod->b)
                      || (mod->type == Json::Type::Number && (mod->n == 0 || std::isnan(mod->n)))
                      || (mod->type == Json::Type::String && mod->s.empty());
      if (!falsy) list = Matrix::decode(utf16To8(jsToString(*mod)));
    } else {
      for (int i = 0; i < 2; i++) {
        const std::u16string name = str("l" + std::to_string(i) + "d");
        static const std::pair<const char16_t*, const char*> legacy[] = {
          { u"phase", "gen.phase" }, { u"ratio", "gen.ratio" }, { u"detail", "gen.detail" }, { u"tumble", "gen.tumble" },
          { u"depth", "gen.depth" }, { u"freq", "gen.freq" }, { u"amp", "gen.amp" },
        };
        for (const auto& [word, dest] : legacy) {
          if (name == word) list.push_back({ "lfo" + std::to_string(i + 1), dest, jsToNumber(s("l" + std::to_string(i) + "a")) / 100, 0 });
        }
      }
    }
    matrix.load(list);
  }
}

}  // namespace scope
