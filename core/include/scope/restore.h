// A setup loaded into the instrument: the page's `restore`, ported for what
// it does to the sound - both layers of the generator, the keyboard, the
// LFOs, the routings, the key, the quantiser and the tempo, the crossings,
// the plane, the echo, the arpeggiator, the score, the macros and the morph's
// ends and the threshold - and for the settings it keeps for pieces still to
// come (the photocell). It is held to the page's own `restore`, run in a
// browser, by core/tests/parity.py.
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
//   filter, the beam, the panes) is the page's to apply. Its sliders are
//   written into the panel as the page writes them, so the morph can walk
//   them; what they then do is the page's.
// - The drawn cycles' tables are built again only for a slot whose points
//   have changed. The page builds all four on every restore; the tables are
//   the same either way, and each costs some 25 ms.
// - The cycles and the figures made of strokes are the page's from the first
//   restore on: a Brain starts with none, where the page starts with its
//   defaults, and the plugin restores before it plays.
// - "Now", where restore asks for it (setting the tempo re-bases the bar), is
//   the clock's `now()`, which its owner keeps up to date; the page asks
//   `performance.now()`.
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

#include "scope/clock.h"
#include "scope/cycles.h"
#include "scope/generator.h"
#include "scope/json.h"
#include "scope/keyboard.h"
#include "scope/lfo.h"
#include "scope/matrix.h"
#include "scope/panel_controls.h"
#include "scope/score.h"
#include "scope/setup.h"
#include "scope/strokes.h"

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
  int panelLayer = 0;              // which layer the panel's voice controls write
  std::string inputFrom = "live";  // genInput.from
  double inputMode = 0;            // genInput.mode
  struct LfoSetting { Json shape = Json::string(std::string_view("sine")); double free = 0.2; std::string sync; };
  std::array<LfoSetting, 2> lfo { { { Json::string(std::string_view("sine")), 0.2, "" },
                                    { Json::string(std::string_view("sine")), 0.5, "" } } };
  double keyRoot = 0;
  std::string keyScale = "chromatic";
  bool quantise = false;
  double quantiseGlide = 0;
  Clock clock;  // transport: the tempo, the bar, and the oscillators locked to it
  struct Cross { bool on = false; double x = 0, y = 0, noteX = 60, noteY = 67, decayMs = 180, level = 0.4; } cross;
  ScoreState score;
  NotesOut notesOut;       // the crossings' and the pluck's notes out, and their note-offs due
  NoteOut* out = nullptr;  // the MIDI out, where its owner has given one
  struct Arp { std::string mode = "off", rate = "1/8", octaves = "1"; } arp;  // the menus' values
  std::u16string threshWatch = u"env.live";
  double threshLevel = 0.5, pluckNote = 60;
  // The threshold's own state: how many times it has fired, when it last did,
  // and whether its source has fallen far enough below to fire again.
  struct Thresh { int count = 0; double last = -HUGE_VAL, flash = -HUGE_VAL; bool armed = false; } thresh;
  struct Macro { std::u16string name; double value = 0; };
  std::array<Macro, 4> macros { { { u"Macro 1", 0 }, { u"Macro 2", 0 }, { u"Macro 3", 0 }, { u"Macro 4", 0 } } };
  using MorphEnd = std::vector<std::pair<std::string, double>>;  // every slider the morph walks, in order
  std::optional<MorphEnd> morphA, morphB;
  double morphPos = 0;
  double morphMod = 0;                     // what the matrix pushes into the fader
  std::optional<double> morphApplied;      // where the sliders were last put, or nothing
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
    std::optional<double> sent;  // the synced time last sent, which only the clock writes
  } echo;
  // drawnCycle: the four slots' points, and the tables built from them.
  std::array<CyclePoints, kCycleSlots> cycles;
  std::shared_ptr<const std::vector<CycleTables>> cycleBank;
  std::array<CyclePoints, kCycleSlots> cycleBuiltFrom;  // what the bank's tables were built from
  // figDrawing, and the two text rows: the word and the path's d as their
  // inputs hold them, the d last read, and why the last one was not.
  std::u16string figText, figPathD;
  struct FigDrawing {
    std::shared_ptr<const FigurePath> text, path, drawn;
    std::u16string pathD, fault;
    Strokes strokes;
    bool full = false;
  } fig;
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
inline bool delaySyncKnown(const std::u16string& s) {
  return s.empty() || s == u"1/2" || s == u"1/4" || s == u"1/8d" || s == u"1/8" || s == u"1/4t" || s == u"1/8t" || s == u"1/16";
}
inline double cutoffHz(double step) { return 20 * std::pow(1000.0, step / 1000); }  // CUTOFF_STEPS a thousand
inline double resonanceQ(double v) { return std::sqrt(0.5) * std::pow(20 / std::sqrt(0.5), v / 100); }

// MORPH_IDS: the sliders the morph walks, in the page's order.
inline const std::vector<std::string>& morphIds() {
  static const std::vector<std::string> ids(std::begin(kMorphIds), std::end(kMorphIds));
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

// The panel's refreshers: the sliders written back from the state they show.
inline void syncCrossPanel(Brain& b) {
  b.panel.setRange("crossX", toU16(jsNumberToString(jsMathRound(b.cross.x * 100))));
  b.panel.setRange("crossY", toU16(jsNumberToString(jsMathRound(b.cross.y * 100))));
  b.panel.setRange("crossDecay", toU16(jsNumberToString(b.cross.decayMs)));
  b.panel.setRange("crossLevel", toU16(jsNumberToString(jsMathRound(b.cross.level * 100))));
}
inline void syncPlanePanel(Brain& b) {
  const auto pct = [](double v) { return toU16(jsNumberToString(jsMathRound(v * 100))); };
  b.panel.setRange("planeRadius", pct(b.plane.radius));
  b.panel.setRange("planeTwist", pct(b.plane.twist));
  b.panel.setRange("planeScaleX", pct(b.plane.scaleX));
  b.panel.setRange("planeScaleY", pct(b.plane.scaleY));
  b.panel.setRange("planeShear", pct(b.plane.shear));
}
inline double delayTimeMs(const Brain& b) {
  const double beats = delayBeats(b.echo.sync);
  return beats > 0 ? std::fmin(2000, beats * 60000 / b.clock.bpm) : b.echo.ms;
}
// The time a synced echo shows is the tempo's, and its slider stands still.
inline void syncEchoPanel(Brain& b) {
  const auto n = [](double v) { return toU16(jsNumberToString(v)); };
  const Brain::EchoState& e = b.echo;
  b.panel.setRange("delayMix", n(jsMathRound(e.mix * 100)));
  b.panel.setRange("delayMs", n(!e.sync.empty() ? jsMathRound(delayTimeMs(b)) : e.ms));
  b.panel.setRange("delayFeedback", n(jsMathRound(e.feedback * 100)));
  b.panel.setRange("chorusMix", n(jsMathRound(e.chorus * 100)));
  b.panel.setRange("chorusRate", n(jsMathRound(e.rate * 100)));
  b.panel.setRange("chorusDepth", n(jsMathRound(e.depthMs * 10)));
  b.panel.setRange("chorusTime", n(jsMathRound(e.centreMs * 10)));
  b.panel.setRange("chorusFeedback", n(jsMathRound(e.chorusFeedback * 100)));
}

// syncPlane, syncEcho, syncCrossings, syncQuantiser: the state written to the
// generator whole.
inline void syncPlane(const Brain& b, Generator& gen) {
  const Brain::PlaneState& p = b.plane;
  gen.set("planeMirror", p.mirror); gen.set("planeLimit", p.limit); gen.set("planeRadius", p.radius);
  gen.set("planeOS", p.os); gen.set("planeTwist", p.twist * kTwoPi); gen.set("planeKaleido", p.kaleido);
  gen.set("planeSnap", p.snap); gen.set("planeScaleX", p.scaleX); gen.set("planeScaleY", p.scaleY);
  gen.set("planeShear", p.shear);
}
inline void syncEcho(const Brain& b, Generator& gen) {
  const Brain::EchoState& e = b.echo;
  gen.set("delayMix", e.mix); gen.set("delayMs", delayTimeMs(b)); gen.set("delayFeedback", e.feedback);
  gen.set("delayPingPong", e.pingPong ? 1 : 0); gen.set("chorusMix", e.chorus); gen.set("chorusRate", e.rate);
  gen.set("chorusDepthMs", e.depthMs); gen.set("chorusMs", e.centreMs); gen.set("chorusFeedback", e.chorusFeedback);
}
inline void syncCrossings(const Brain& b, Generator& gen) {
  gen.set("crossOn", b.cross.on ? 1 : 0); gen.set("crossX", b.cross.x); gen.set("crossY", b.cross.y);
  gen.set("crossHzX", midiHz(b.cross.noteX)); gen.set("crossHzY", midiHz(b.cross.noteY));
  gen.set("crossDecayMs", b.cross.decayMs); gen.set("crossLevel", b.cross.level);
}
inline void syncQuantiser(const Brain& b, Generator& gen) {
  gen.set("qMask", b.quantise ? keyMask(b.keyRoot, b.keyScale) : 0);
  gen.set("qGlideMs", b.quantiseGlide);
}

// The two oscillators the clock can lock, each with the note value it is
// locked to. Whoever holds both the Brain and the oscillators says so once;
// restore says it again, which costs nothing.
inline void linkClock(Brain& b, std::vector<Lfo>& lfos) {
  b.clock.locks = { { &lfos[0], &b.lfo[0].sync }, { &lfos[1], &b.lfo[1].sync } };
  // The bar's one puts the score back to its first column; Stop lets its notes go.
  Brain* brain = &b;
  b.clock.onAnchor = [brain] { brain->score.last = -1; brain->score.steps = 0; };
  b.clock.onStop = [brain] { scoreStop(brain->score, brain->out); };
}
// MIDI's real-time bytes as the keyboard hands them on, to the clock, at the
// time of the event that carried them.
class ClockIn : public RealtimeIn {
 public:
  explicit ClockIn(Clock& clock) : clock_(clock) {}
  void at(double ms) { when_ = ms; }
  void realtime(int status) override { clock_.realtime(status, when_); }

 private:
  Clock& clock_;
  double when_ = 0;
};
// clockStep, whole: the clock's own step, then a delay in note values sent
// again when the tempo has moved it - and whether it was.
inline bool clockFrame(Brain& b, Generator& gen, double now) {
  b.clock.step(now);
  if (!b.echo.sync.empty()) {
    const double ms = delayTimeMs(b);
    if (!b.echo.sent || *b.echo.sent != ms) { b.echo.sent = ms; gen.set("delayMs", ms); return true; }
  }
  return false;
}
// setTempo, with the slider it writes.
inline void setTempo(Brain& b, double bpm, double at) {
  b.clock.setTempo(bpm, at);
  b.panel.setRange("tempo", toU16(jsNumberToString(b.clock.set)));
}
// clockTap, with the slider a tap's tempo writes.
inline void tapTempo(Brain& b, double at) {
  b.clock.tap(at);
  b.panel.setRange("tempo", toU16(jsNumberToString(b.clock.set)));
}

// cycleSend(true): every slot's tables, to the generator - the drawn cycle
// for both layers (layer B plays layer A's) and the bank for the wavetable.
inline void cycleSend(Brain& b, Generator& gen) {
  if (!b.cycleBank || b.cycleBuiltFrom != b.cycles) {
    auto bank = std::make_shared<std::vector<CycleTables>>();
    for (std::size_t k = 0; k < kCycleSlots; k++) {
      const bool same = b.cycleBank && b.cycleBuiltFrom[k] == b.cycles[k];
      bank->push_back(same ? (*b.cycleBank)[k] : cycleTables(b.cycles[k]));
    }
    b.cycleBank = bank;
    b.cycleBuiltFrom = b.cycles;
  }
  gen.setCycle(std::shared_ptr<const CycleTables>(b.cycleBank, &(*b.cycleBank)[0]));
  gen.setWavetable(b.cycleBank);
}

// A text input's value as the browser keeps it: its line breaks taken out.
inline std::u16string textInputValue(const std::u16string& v) {
  std::u16string out;
  for (const char16_t c : v) if (c != u'\n' && c != u'\r') out += c;
  return out;
}
// setFigureText: the word as its row holds it, at most twenty-four units.
inline void setFigureText(Brain& b, const std::u16string& text) {
  b.figText = textInputValue(text.substr(0, kTextMost));
  b.fig.text = compilePath(textStrokes(b.figText));
}
// setFigurePathD: a d that cannot be read leaves the drawing as it was and
// says why; one that reads to nothing says that.
inline void setFigurePathD(Brain& b, const std::u16string& d) {
  b.figPathD = textInputValue(d);
  if (jsTrim(d).empty()) { b.fig.path = nullptr; b.fig.pathD.clear(); b.fig.fault.clear(); return; }
  const PathRead read = svgStrokes(d);
  if (!read.strokes) { b.fig.fault = u"That path could not be read: " + utf8To16(read.error) + u"."; return; }
  b.fig.path = compilePath(*read.strokes);
  b.fig.pathD = d;
  b.fig.fault = b.fig.path ? u"" : u"Nothing in that path to draw.";
}
inline std::shared_ptr<const FigurePath> figurePathFor(const Brain& b, std::string_view name) {
  return name == "Text" ? b.fig.text : name == "Path" ? b.fig.path : name == "Drawn" ? b.fig.drawn : nullptr;
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
    const auto first = decodeCycle(s("cycle"));
    brain.cycles[0] = first ? *first : cycleDefault(0);
    decodeCycleSlots(s("cycles"), brain.cycles);
    cycleSend(brain, gen);
  }
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

  {
    const Json* text = s("figText");
    setFigureText(brain, text && text->type == Json::Type::String ? text->s : defaults.get("figText")->s);
    const Json* d = s("figPath");
    setFigurePathD(brain, d && d->type == Json::Type::String ? d->s : u"");
    brain.fig.strokes = decodeDrawn(s("figDrawn"));
    brain.fig.full = false;
    brain.fig.drawn = compilePath(brain.fig.strokes);  // drawnCompile: decodeDrawn keeps no stroke of one point
  }
  gen.set("figure", panel.select("figure"), 0);
  gen.setFigPath(figurePathFor(brain, panel.select("figure")));  // syncFigurePath
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
    linkClock(brain, lfos);
    setTempo(brain, bpm == 0 || std::isnan(bpm) ? 120 : bpm, brain.clock.now());
    clockFrame(brain, gen, brain.clock.now());
  }
  setA("qMask", brain.quantise ? keyMask(brain.keyRoot, brain.keyScale) : 0);
  setA("qGlideMs", brain.quantiseGlide);
  panel.setRange("quantiseGlide", toU16(jsNumberToString(brain.quantiseGlide)));  // syncKeyPanel

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
  syncCrossPanel(brain);

  // The score, the arpeggiator, the threshold and the pluck: kept for their pieces.
  brain.score.on = isTrue("scoreOn");
  brain.score.step = isString("scoreStep", u"1/8") ? "1/8" : isString("scoreStep", u"1/4") ? "1/4" : "1/16";
  brain.score.voices = jsMathRound(within("scoreVoices", 1, 4, 2));
  brain.score.low = among("scoreLow", { 36, 48, 60 }, 48);
  brain.score.octaves = jsMathRound(within("scoreOctaves", 1, 4, 3));
  if (!brain.score.on) scoreStop(brain.score, brain.out);
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
  keys.setArp(brain.arp.mode, brain.arp.rate, jsStringToNumber(toU16(brain.arp.octaves)));  // arpSet
  {
    const Json* w = s("threshWatch");
    brain.threshWatch = w && w->type == Json::Type::String && !w->s.empty() ? w->s : u"env.live";
    brain.threshLevel = within("threshLevel", 5, 95, 50) / 100;
    brain.thresh.armed = false;
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
      panel.setRange("macro" + std::to_string(i + 1), toU16(jsNumberToString(jsMathRound(m.value * 100))));
    }
    brain.morphA = decodeMorphEnd(s("morphA"), morphHome);
    const auto refB = [&](const std::string& id) {
      if (brain.morphA) for (const auto& [mid, v] : *brain.morphA) if (mid == id) return v;
      return morphHome(id);
    };
    brain.morphB = decodeMorphEnd(s("morphB"), refB);
    brain.morphPos = within("morphPos", 0, 100, 0) / 100;
    panel.setRange("morphPos", toU16(jsNumberToString(jsMathRound(brain.morphPos * 100))));
    brain.morphApplied.reset();
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
    syncPlanePanel(brain);
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
    setA("delayMix", e.mix);
    setA("delayMs", delayTimeMs(brain));
    setA("delayFeedback", e.feedback);
    setA("delayPingPong", e.pingPong ? 1 : 0);
    setA("chorusMix", e.chorus); setA("chorusRate", e.rate); setA("chorusDepthMs", e.depthMs);
    setA("chorusMs", e.centreMs); setA("chorusFeedback", e.chorusFeedback);
    syncEchoPanel(brain);
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
  // buildSourceDetail: the chosen source's rate slider, made again from where
  // its LFO is (the first LFO, which is the source the page opens on).
  {
    const Brain::LfoSetting& l = brain.lfo[0];
    panel.setRange("lfoRate0", toU16(jsNumberToString(jsMathRound((l.sync.empty() ? lfos[0].rate : l.free) * 100))));
  }

  // The view's half: its sliders are written, and what they do is the page's.
  panel.setRange("timebase", str("timebase"));
  panel.setRange("level", str("level"));
  panel.setRange("position", str("position"));
  panel.setRange("holdoff", str("holdoff"));
  panel.setRange("ch1Scale", str("c0s"));
  panel.setRange("ch1Offset", str("c0o"));
  panel.setRange("ch2Scale", str("c1s"));
  panel.setRange("ch2Offset", str("c1o"));
  panel.setRange("acCorner", str("acHz"));
  panel.setRange("lagMix", toU16(jsNumberToString(jsMathRound(jsMax(0, jsMin(0.5, num("lagMix") / 100)) * 100))));
  panel.setRange("lag", toU16(jsNumberToString(jsMathRound(num("lagMs") * 10))));
  panel.setRange("rotate", str("rotate"));
  panel.setRange("filterCutoff", str("fCut"));
  panel.setRange("filterRes", str("fRes"));
  panel.setRange("zoom", toU16(jsNumberToString(jsMax(0, jsMin(24, num("zoom"))))));  // setZoom
}

}  // namespace scope

namespace scope {

// setMacro: nought to one, and its knob at the nearest hundredth.
inline void setMacro(Brain& b, int i, double value) {
  Brain::Macro& m = b.macros[static_cast<std::size_t>(i)];
  m.value = jsMax(0, jsMin(1, value));
  b.panel.setRange("macro" + std::to_string(i + 1), toU16(jsNumberToString(jsMathRound(m.value * 100))));
}

// --- a slider moved: its handler ---------------------------------------------------------

// What the page's "input" handler for a slider does with its new value, for
// every slider whose handler reaches the sound or a setting a setup carries -
// a hand on it, or the morph walking it. The view's sliders do the view's
// work, which is the page's; their values are the panel's all the same.
inline void sliderInput(const std::string& id, Brain& b, Generator& gen, Keyboard& keys, std::vector<Lfo>& lfos) {
  const double v = b.panel.range(id);
  const int layer = b.panelLayer;
  const auto layerSet = [&](std::string_view field, double x) { gen.set(field, x, layer); };
  if (id == "freq") { gen.set("freq", v); keys.panel().freq = v; }
  else if (id == "amp") layerSet("amp", v / 100);
  else if (id == "morph" || id == "width" || id == "table") layerSet(id, v / 100);
  else if (id == "phase") gen.set("phase", v * kPi / 180);
  else if (id == "detail") { gen.set("detail", v); keys.panel().detail = v; }
  else if (id == "figureRate") { gen.set("figureRate", v); keys.panel().figureRate = v; }
  else if (id == "spinX" || id == "spinY" || id == "spinZ") {
    std::array<double, 3> spin = gen.tone().spin;
    spin[static_cast<std::size_t>(id[4] - 'X')] = v / 100;
    gen.setSpin(spin);
  }
  else if (id == "spinRate") gen.set("spinRate", v / 100);
  else if (id == "depth") gen.set("depth", v / 100);
  else if (id == "envAttack") layerSet("attackMs", v);
  else if (id == "envDecay") layerSet("decayMs", v);
  else if (id == "envSustain") layerSet("sustain", v / 100);
  else if (id == "envRelease") layerSet("releaseMs", v);
  else if (id == "glide") layerSet("glideMs", v);
  else if (id == "ringTime") gen.set("ringMs", v);
  else if (id == "swingRate") gen.set("swingRate", v / 10);
  else if (id == "decay") gen.set("decay", v / 100);
  else if (id == "detune") gen.set("detune", v / 10000);
  else if (id == "swingDrive") gen.set("swingDrive", v / 100);
  else if (id == "gen2Rate") gen.set("gen2Rate", v);
  else if (id == "inputDepth") gen.set("inputDepth", v / 100);
  else if (id == "lfoRate0") {
    b.lfo[0].free = v / 100;
    if (b.lfo[0].sync.empty()) lfos[0].rate = b.lfo[0].free;
  }
  else if (id == "quantiseGlide") { b.quantiseGlide = v; syncQuantiser(b, gen); }
  else if (id.size() == 6 && id.compare(0, 5, "macro") == 0 && id[5] >= '1' && id[5] <= '4') setMacro(b, id[5] - '1', v / 100);
  else if (id == "morphPos") b.morphPos = v / 100;
  else if (id == "tempo") setTempo(b, v, b.clock.now());
  else if (id == "crossX") { b.cross.x = v / 100; syncCrossings(b, gen); }
  else if (id == "crossY") { b.cross.y = v / 100; syncCrossings(b, gen); }
  else if (id == "crossDecay") { b.cross.decayMs = v; syncCrossings(b, gen); }
  else if (id == "crossLevel") { b.cross.level = v / 100; syncCrossings(b, gen); }
  else if (id.size() == 4 && id.compare(0, 3, "bar") == 0) {
    std::vector<double> bars;
    for (int k = 0; k < 9; k++) bars.push_back(b.panel.range("bar" + std::to_string(k)));
    gen.setBars(bars, layer);
  }
  else if (id == "planeRadius" || id == "planeTwist" || id == "planeScaleX" || id == "planeScaleY" || id == "planeShear") {
    double& field = id == "planeRadius" ? b.plane.radius : id == "planeTwist" ? b.plane.twist
                  : id == "planeScaleX" ? b.plane.scaleX : id == "planeScaleY" ? b.plane.scaleY : b.plane.shear;
    field = v / 100;
    syncPlanePanel(b);
    syncPlane(b, gen);
  }
  else if (id == "delayMix" || id == "delayMs" || id == "delayFeedback" || id == "chorusMix" || id == "chorusRate"
           || id == "chorusDepth" || id == "chorusTime" || id == "chorusFeedback") {
    Brain::EchoState& e = b.echo;
    if (id == "delayMix") e.mix = v / 100;
    else if (id == "delayMs") e.ms = v;
    else if (id == "delayFeedback") e.feedback = v / 100;
    else if (id == "chorusMix") e.chorus = v / 100;
    else if (id == "chorusRate") e.rate = v / 100;
    else if (id == "chorusDepth") e.depthMs = v / 10;
    else if (id == "chorusTime") e.centreMs = v / 10;
    else e.chorusFeedback = v / 100;
    syncEchoPanel(b);
    syncEcho(b, gen);
  }
  else {
    for (const auto& row : layerControls()) {
      if (id == row.id && isVoiceControl(row.id) && row.kind == LayerControl::Range) layerSet(row.field, row.law(v));
    }
  }
}

// A hand on a slider: the value written as the browser takes it, then the
// slider's handler.
inline void moveSlider(const std::string& id, std::u16string written, Brain& b, Generator& gen, Keyboard& keys,
                       std::vector<Lfo>& lfos) {
  b.panel.setRange(id, std::move(written));
  sliderInput(id, b, gen, keys, lfos);
}

// --- macros and the morph ------------------------------------------------------------------

// morphCapture: every slider the morph walks, as it stands.
inline Brain::MorphEnd morphCapture(const Brain& b) {
  Brain::MorphEnd out;
  for (const auto& id : morphIds()) out.emplace_back(id, b.panel.range(id));
  return out;
}

// morphStore: storing an end puts the fader at it, so storing moves nothing.
inline void morphStore(Brain& b, bool endB) {
  (endB ? b.morphB : b.morphA) = morphCapture(b);
  b.morphPos = endB ? 1 : 0;
  b.morphApplied = b.morphPos + b.morphMod;
  b.panel.setRange("morphPos", toU16(jsNumberToString(b.morphPos * 100)));
}

// The fader's own slider moved.
inline void morphFader(Brain& b) { b.morphPos = b.panel.range("morphPos") / 100; }

// morphStep, once a frame after the matrix: only when where the fader stands
// has moved, each slider that differs between the ends walked to its blend
// and its handler fired if the browser's value moved. Frequency is walked in
// ratio, so half-way from 220 to 880 is 440.
inline void morphStep(Brain& b, Generator& gen, Keyboard& keys, std::vector<Lfo>& lfos) {
  if (!b.morphA || !b.morphB) return;
  const double t = jsMax(0, jsMin(1, b.morphPos + b.morphMod));
  if (b.morphApplied && std::fabs(t - *b.morphApplied) < 1e-4) return;
  b.morphApplied = t;
  for (std::size_t k = 0; k < b.morphA->size(); k++) {
    const auto& [id, va] = (*b.morphA)[k];
    const double vb = (*b.morphB)[k].second;
    if (va == vb) continue;
    const double want = id == "freq" && va > 0 && vb > 0 ? va * std::pow(vb / va, t) : va + (vb - va) * t;
    const double before = b.panel.range(id);
    b.panel.setRange(id, toU16(jsNumberToString(want)));
    if (b.panel.range(id) != before) sliderInput(id, b, gen, keys, lfos);
  }
}

// K1's threshold (thresholdStep), once a frame before the events fire: the
// source it watches rising through the level is a hit, and it can fire again
// only once that source has fallen 0.05 below and 80 ms have passed. An event
// source, or none, is nothing to watch.
constexpr double kThreshHyst = 0.05, kThreshGap = 80;
inline void thresholdStep(Brain& b, const Matrix& matrix, double now) {
  const ModSource* watched = matrix.source(utf16To8(b.threshWatch));
  if (!watched || watched->event) { b.thresh.armed = false; return; }
  const double v = watched->value();
  if (v < b.threshLevel - kThreshHyst) b.thresh.armed = true;
  else if (b.thresh.armed && v >= b.threshLevel && now - b.thresh.last >= kThreshGap) {
    b.thresh.armed = false; b.thresh.count++; b.thresh.last = now; b.thresh.flash = now;
  }
}
// The panel's menu of what it watches: another source, and armed afresh.
inline void setThresholdWatch(Brain& b, const std::u16string& id) {
  b.threshWatch = id;
  b.thresh.armed = false;
}
class ThresholdSource : public ModSource {
 public:
  ThresholdSource(const Brain& b, const Matrix& matrix) : ModSource("threshold"), b_(b), matrix_(matrix) { event = true; }
  // A flash that fades over 150 ms, for the chip's meter.
  double value() const override { return jsMax(0, 1 - (b_.clock.now() - b_.thresh.flash) / 150); }
  int count() const override { return b_.thresh.count; }
  // It is a loop when what it watches is one, asked afresh each time. An
  // event source is never watched, so it makes no loop - and asking it would
  // ask this, for ever, were a setup to have it watching itself.
  bool picture() const override {
    const ModSource* watched = matrix_.source(utf16To8(b_.threshWatch));
    return watched && !watched->event && watched->picture();
  }

 private:
  const Brain& b_;
  const Matrix& matrix_;
};

// The macros as sources, and the fader as a destination the matrix moves.
class MacroSource : public ModSource {
 public:
  MacroSource(int i, const Brain& b) : ModSource("macro." + std::to_string(i + 1)), i_(i), b_(b) {}
  double value() const override { return b_.macros[static_cast<std::size_t>(i_)].value; }

 private:
  int i_;
  const Brain& b_;
};
class BrainSources {
 public:
  // With a generator, the pluck too: struck at the setup's pluck note and sent
  // out, where the core's own stand-in strikes middle C and sends nothing.
  BrainSources(Matrix& matrix, Brain& b, Generator* gen = nullptr) : threshold_(b, matrix) {
    if (gen) {
      ModDest pluck;
      pluck.id = "gen.pluck"; pluck.kind = DestKind::Event;
      Brain* brain = &b;
      pluck.fire = [brain, gen](double amount) {
        pluckFire(brain->notesOut, static_cast<int>(brain->pluckNote), jsMax(0, jsMin(1, std::fabs(amount))), brain->clock.now(),
                  [gen](double hz, double velocity) { gen->strike(hz, velocity); }, brain->out);
      };
      matrix.registerDest(std::move(pluck));
    }
    for (int i = 0; i < 4; i++) macros_.emplace_back(i, b);
    for (auto& m : macros_) matrix.registerSource(&m);
    matrix.registerSource(&threshold_);
    ModDest d;
    d.id = "morph.pos"; d.kind = DestKind::Visual; d.span = 1; d.min = 0; d.max = 1;
    Brain* brain = &b;
    d.base = [brain] { return brain->morphPos; };
    d.set = [brain](double offset) { brain->morphMod = offset; };
    matrix.registerDest(std::move(d));
  }
  BrainSources(const BrainSources&) = delete;
  BrainSources& operator=(const BrainSources&) = delete;

  // thresholdStep, once a frame before the matrix fires its events.
  void frame(Brain& b, const Matrix& matrix, double now) { thresholdStep(b, matrix, now); }

 private:
  std::vector<MacroSource> macros_;
  ThresholdSource threshold_;
};

}  // namespace scope
