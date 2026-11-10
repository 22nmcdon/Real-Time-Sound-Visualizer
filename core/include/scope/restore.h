// A setup loaded into the instrument: the page's `restore`, ported for what
// it does to the sound - both layers of the generator, the keyboard, the
// LFOs, the routings, the key, the quantiser and the tempo,
// the plane, the echo, the arpeggiator, the score and the morph's
// ends - and for the settings it keeps for pieces still to
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
// - The cycles are the page's from the first restore on: a Brain starts with
//   none, where the page starts with its defaults, and the plugin restores
//   before it plays.
// - "Now", where restore asks for it (setting the tempo re-bases the bar), is
//   the clock's `now()`, which its owner keeps up to date; the page asks
//   `performance.now()`.
// - Two fields the page passes on raw are taken by their truth or their
//   name: `just` (anything truthy is just) and an LFO's shape (any shape the
//   page does not know plays a sine). The page keeps the raw value as well,
//   which only its panel reads. `gen`, the kind of generator, is read by
//   nothing since G2 took the drawings: the waveform is the only kind, and
//   version 10 of the code (setup.h) writes it as that.
// - A legacy LFO destination naming something on Object.prototype ("toString")
//   is not followed; the page would take the function for a destination.

#pragma once

#include <array>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <map>
#include <optional>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include "scope/beam.h"     // Screen, what the walk reads
#include "scope/capture.h"
#include "scope/clock.h"
#include "scope/cycles.h"
#include "scope/generator.h"
#include "scope/json.h"
#include "scope/keyboard.h"
#include "scope/lfo.h"
#include "scope/matrix.h"
#include "scope/panel_controls.h"
#include "scope/scan.h"           // scanReadsOf
#include "scope/score.h"
#include "scope/setup.h"

namespace scope {

// --- the browser's part: what a control makes of a value written into it ------

inline const RangeSpec* rangeSpec(std::string_view id) {
  // LFO 2's rate is made when LFO 2 is chosen, as LFO 1's is, and so is not
  // among the sliders the page opened with; it is LFO 1's slider again.
  if (id == "lfoRate1") id = "lfoRate0";
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
/* The step a slider's value lands on. The browser steps in decimal, exactly,
   and a value a hair under a half-step rounds down there: the morph put layer
   B's Turn at 0.05 of the way from 0 to 30, which is 1.4999999999999998, and
   the page's slider said 1. In doubles (v - min) / step was 51.5 against a
   minimum of -50, and with the half added it rounded up to 2 (parity's slider
   operations, 7 Nov, a draw no earlier run had made). So the half-step below
   the step chosen is checked: exact wherever the minimum and the step are, as
   on every whole-numbered slider, and a value under it is the step below. */
inline double rangeStep(const RangeSpec& r, double v) {
  double k = std::floor((v - r.min) / r.step + 0.5);
  if (v < r.min + (k - 0.5) * r.step) k -= 1;
  double snapped = r.min + k * r.step;
  if (snapped > r.max) snapped -= r.step;
  return snapped;
}

inline double rangeSanitise(const RangeSpec& r, std::string_view written) {
  double v = NAN;
  if (htmlValidFloat(written)) v = std::strtod(std::string(written).c_str(), nullptr);
  if (!std::isfinite(v)) v = r.max < r.min ? r.min : r.min + (r.max - r.min) / 2;
  v = std::fmax(r.min, std::fmin(r.max, v));
  const double snapped = rangeStep(r, v);
  return snapped == 0 ? 0 : snapped;  // no minus nought: the browser writes "0"
}

/* The same for a number, which is what the page's text is made from: a
   finite number written as the browser writes it reads back as itself, and
   anything else - NaN, an infinity - is not a valid float and becomes the
   slider's middle. So no text need be made at all, which on the audio thread
   is an allocation saved for every slider the morph's walk or a host
   parameter moves. */
inline double rangeSanitiseNumber(const RangeSpec& r, double v) {
  if (!std::isfinite(v)) v = r.max < r.min ? r.min : r.min + (r.max - r.min) / 2;
  v = std::fmax(r.min, std::fmin(r.max, v));
  const double snapped = rangeStep(r, v);
  return snapped == 0 ? 0 : snapped;
}

// The controls: every slider and menu the page has, holding what the page's
// control would hold - a slider's number, a menu's chosen value or "".
class Controls {
 public:
  /* Every menu's value is given room for any number up front, and so is a
     sixth option's, so writing one later - the persistence, moved by a host
     on the audio thread (P8a) - makes nothing: the writes below assign into
     that room rather than handing a new string over. */
  Controls() {
    for (const auto& r : kRanges) ranges_[r.id] = r.value;
    for (const auto& s : kSelects) {
      std::string& value = selects_[s.id];
      value.reserve(kJsNumberRoom);
      value.assign(s.value);
      custom_[s.id].reserve(kJsNumberRoom);
    }
  }
  /* A slider or a menu the panel has not got is refused, and nothing is
     written: false. Each used to look its id up and use what it found, and an
     id the page had and the core did not yet - Scan's three sliders, between
     P7a's page stage and its port - was a null read and a crash in the middle
     of a morph's walk, where now it is a slider that does nothing, which
     parity reports as the difference it is. */
  bool setRange(const std::string& id, std::u16string written) {
    const RangeSpec* r = rangeSpec(id);
    if (!r) return false;
    std::string ascii;
    for (const char16_t c : written) ascii += c < 0x80 ? static_cast<char>(c) : '\x7f';
    ranges_[id] = rangeSanitise(*r, ascii);
    return true;
  }
  // A slider given a number rather than the text of one: the same value, and nothing made.
  bool setRangeNumber(const std::string& id, double v) {
    const RangeSpec* r = rangeSpec(id);
    if (!r) return false;
    ranges_[id] = rangeSanitiseNumber(*r, v);
    return true;
  }
  bool setSelect(const std::string& id, const std::u16string& written) {
    const SelectSpec* s = selectSpec(id);
    const std::string value = utf16To8(written);
    if (id == "xyX" || id == "xyY") { keep(selects_[id], laneOption(value) ? std::string_view(value) : std::string_view()); return true; }
    if (!s) return false;
    const auto custom = custom_.find(id);
    keep(selects_[id], selectHas(*s, value) || (custom != custom_.end() && !value.empty() && value == custom->second)
                           ? std::string_view(value) : std::string_view());
    return true;
  }
  /* The persistence menu's sixth option (P7a), for a time between its five:
     the page writes it the value it shows, and keeps that value when the
     menu goes back to one of the five, so a hand choosing it again finds it.
     Chosen here as well, as setPersistence chooses it. */
  void setCustomOption(const std::string& id, std::string_view value) {
    if (!selectSpec(id)) return;
    keep(custom_[id], value);
    keep(selects_[id], value);
  }
  /* The X-Y pair's two menus hold an option a lane, as the page builds them
     again for whatever is drawn (buildLaneRows), where every other menu's
     options are fixed: a pair on a fourth lane is a value only four lanes -
     two figures, or the band split - have. Two lanes, the generator's pair, until told. */
  void setLanes(int n) { lanes_ = std::max(1, n); }
  double range(const std::string& id) const { return ranges_.at(id); }
  const std::string& select(const std::string& id) const { return selects_.at(id); }
  // Number() of a menu's value, as a handler reads it.
  double selectNumber(const std::string& id) const { return jsStringToNumber(utf8To16(select(id))); }

 private:
  std::map<std::string, double> ranges_;
  std::map<std::string, std::string> selects_;
  std::map<std::string, std::string> custom_;  // a menu's option whose value is written as it is shown
  int lanes_ = 2;
  // Written into the room the string has, where an assignment of a new string would have replaced it.
  static void keep(std::string& slot, std::string_view value) { slot.assign(value.data(), value.size()); }
  bool laneOption(const std::string& value) const {
    for (int k = 0; k < lanes_; ++k) if (value == std::to_string(k)) return true;
    return false;
  }
};

// --- the brain's state that a setup sets beyond the generator ----------------------

struct Brain {
  Controls panel;
  int panelLayer = 0;              // which layer the panel's voice controls write
  // What layer A's controls said while B is on the panel, and whether there is any.
  std::vector<std::pair<std::string, std::u16string>> panelKeptA;
  bool keptA = false;
  bool panelHeldOnA = false;  // while a setup is restored, as the page's restore holds it
  double inputMode = 0;            // genInput.mode
  struct LfoSetting { Json shape = Json::string(std::string_view("sine")); double free = 0.2; std::string sync; };
  std::array<LfoSetting, 2> lfo { { { Json::string(std::string_view("sine")), 0.2, "" },
                                    { Json::string(std::string_view("sine")), 0.5, "" } } };
  double keyRoot = 0;
  std::string keyScale = "chromatic";
  bool quantise = false;
  double quantiseGlide = 0;
  Clock clock;  // transport: the tempo, the bar, and the oscillators locked to it
  ScoreState score;
  NoteOut* out = nullptr;  // the MIDI out, where its owner has given one
  struct Arp { std::string mode = "off", rate = "1/8", octaves = "1"; } arp;  // the menus' values
  using MorphEnd = std::vector<std::pair<std::string, double>>;  // every slider the morph walks, in order
  std::optional<MorphEnd> morphA, morphB;
  double morphPos = 0;
  double morphMod = 0;                     // what the matrix pushes into the fader
  std::optional<double> morphApplied;      // where the sliders were last put, or nothing
  struct Photo { bool on = false; double u = 0.75, v = 0.5; } photo;
  // Scan's softness in cells (P7a), the page's `scan.soft`: the slider's tenths.
  double scanSoft = 3;
  /* A note's strike on the screen (P7b), the page's `scan.strike`: the
     slider's percent as a fraction, a full-velocity note's light. */
  double scanStrike = 0.5;
  // What each layer's Scan reads (P7b, cross-scan): the page's `scan.reads`, "A", "B" or "both".
  std::array<std::string, 2> scanReads { { "A", "B" } };
  // Whose sound layer A's picture moves, and B's (P6): "A", "B" or "both" - the page's layerPictures.moves.
  std::array<std::string, 2> pictureMoves { { "A", "B" } };
  /* The view: what the screen is set to draw, as the page's `state` holds it
     - the capture's half and the walk's - with the zoom's step and what is
     pointed at it, the trigger's mode and the spectrogram's span. The
     timebase, the trigger's lane and the X-Y pair are kept as the numbers
     the page keeps, whatever they are, and the capture reads them through
     `captureView`, which holds them to what it can index. `lanes` is the
     source's lane count, the page's `laneCount()`: two, for the generator's
     pair, which is all the plugin draws. `restored` counts setups, which
     start the beam's anchors afresh; `wipe` is the Clear button, for the
     next frame. */
  struct ViewState {
    View capture;
    Screen screen;
    double timebase = 4, trigSource = 0;
    std::array<double, 2> xy { 0, 1 };
    std::string edge = "rising", mode = "auto", analyseAt = "post", measureAt = "pre";
    double zoomStep = 0, zoomMod = 0, spectroSpan = 5;
    int lanes = 2;
    int restored = 0;
    bool wipe = false;
  } view;
  // The plane's shape in the panel's terms, which layer B can have its own of.
  struct PlaneShape {
    double mirror = 0, limit = 0, radius = 0.4, twist = 0, snap = 0, scaleX = 1, scaleY = 1, shear = 0;
  };
  struct PlaneState : PlaneShape { double os = 2; } plane;
  // Layer B's own (the page's `planeB`): kept a copy of A's while it has none,
  // and B's turn in turns.
  struct PlaneBState : PlaneShape { bool own = false; double turn = 0; } planeB;
  std::string planeShown;  // which layer's plane the section last showed
  struct EchoState {
    double mix = 0, ms = 375;
    std::string sync;
    double feedback = 0.35;
    bool pingPong = false;
    double tone = 1, lowCut = 0, width = 1, wow = 0;  // F5c
    double chorus = 0, rate = 0.6, depthMs = 3, centreMs = 12, chorusFeedback = 0;
    double phaser = 0, phRate = 0.3, phDepth = 0.7, phFeedback = 0.3;  // P8e
    double rvMix = 0, rvSize = 0.4, rvTone = 0.6, rvPre = 10, rvSpread = 0;  // P9
    std::optional<double> sent;  // the synced time last sent, which only the clock writes
  } echo;
  // Layer B's own echo and chorus (the page's `echoB`), under the plane's
  // switch: kept a copy of A's while B has none, as its plane is.
  EchoState echoB;
  // F5b: the order the phaser, chorus and delay run in (kFxOrders), one for both layers.
  std::string fxOrder = "pcd";
  std::string echoShown;  // which layer's echo the section last showed
  // drawnCycle: the four slots' points, and the tables built from them.
  std::array<CyclePoints, kCycleSlots> cycles;
  std::shared_ptr<const std::vector<CycleTables>> cycleBank;
  std::array<CyclePoints, kCycleSlots> cycleBuiltFrom;  // what the bank's tables were built from
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
// cutoffHz is the capture's (scope/capture.h): one law for the trace's filter and the voice's.
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

// One row of LAYER_CONTROLS: the control, the generator's field, its law, and
// the law back from the field to the control, for showing layer B on the panel.
struct LayerControl {
  const char* id; const char* field; enum Kind { Range, Menu, Text } kind; double (*law)(double); double (*inverse)(double) = nullptr;
};
inline const std::vector<LayerControl>& layerControls() {
  static const auto same = [](double v) { return v; };
  static const auto hundred = [](double v) { return v / 100; };
  static const auto byHundred = [](double v) { return v * 100; };
  static const auto byHundredRound = [](double v) { return jsMathRound(v * 100); };
  static const std::vector<LayerControl> rows {
    { "amp", "amp", LayerControl::Range, hundred, byHundred },
    { "shape", "shape", LayerControl::Text, nullptr },
    { "envAttack", "attackMs", LayerControl::Range, same, same },
    { "envDecay", "decayMs", LayerControl::Range, same, same },
    { "envSustain", "sustain", LayerControl::Range, hundred, byHundred },
    { "envRelease", "releaseMs", LayerControl::Range, same, same },
    { "bars", "bars", LayerControl::Text, nullptr },
    { "morph", "morph", LayerControl::Range, hundred, byHundredRound },
    { "width", "width", LayerControl::Range, hundred, byHundredRound },
    { "table", "table", LayerControl::Range, hundred, byHundredRound },
    { "oscRatio", "modRatio", LayerControl::Menu, same, same },
    { "oscFm", "fmIndex", LayerControl::Range, [](double v) { return v / 10; }, [](double v) { return jsMathRound(v * 10); } },
    { "oscBend", "warp", LayerControl::Range, [](double v) { return v * 0.009; },
      [](double v) { return jsMathRound(v / 0.009); } },
    { "oscBendAt", "warpAt", LayerControl::Range, hundred, byHundredRound },
    // Scan's depth (P7a), in hundredths of its travel.
    { "oscScan", "scan", LayerControl::Range, hundred, byHundredRound },
    { "oscRing", "ringMix", LayerControl::Range, hundred, byHundredRound },
    { "oscSync", "syncRatio", LayerControl::Range, hundred, byHundredRound },
    { "oscSub", "subLevel", LayerControl::Range, hundred, byHundredRound },
    { "oscSubOct", "subOctave", LayerControl::Menu, same, same },
    { "oscSubShape", "subShape", LayerControl::Text, nullptr },
    { "oscUnison", "unison", LayerControl::Menu, same, same },
    { "oscSpread", "unisonCents", LayerControl::Range, same, same },
    { "shpDrive", "drive", LayerControl::Range, hundred, byHundredRound },
    { "shpFold", "fold", LayerControl::Range, hundred, byHundredRound },
    { "shpBits", "crushBits", LayerControl::Menu, same, same },
    { "shpRate", "crushHz", LayerControl::Menu, same, same },
    { "vcfType", "vcfType", LayerControl::Menu, same, same },
    { "vcfCut", "vcfCutoff", LayerControl::Range, [](double v) { return cutoffHz(v); },
      [](double v) { return jsMathRound(1000 * std::log(v / 20) / std::log(1000.0)); } },
    { "vcfRes", "vcfQ", LayerControl::Range, [](double v) { return resonanceQ(v); },
      [](double v) { return jsMathRound(100 * std::log(v / std::sqrt(0.5)) / std::log(20 / std::sqrt(0.5))); } },
    { "vcfTrack", "vcfTrack", LayerControl::Range, hundred, byHundredRound },
    { "vcfEnvAmt", "vcfEnv", LayerControl::Range, [](double v) { return v / 10; }, [](double v) { return jsMathRound(v * 10); } },
    { "vcfAtk", "fAttackMs", LayerControl::Range, same, same },
    { "vcfDec", "fDecayMs", LayerControl::Range, same, same },
    { "vcfSus", "fSustain", LayerControl::Range, hundred, byHundredRound },
    { "vcfRel", "fReleaseMs", LayerControl::Range, same, same },
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

// A layer's field by the name LAYER_CONTROLS gives it, as the page reads
// `toneB[field]`; the three that are words are not asked for here.
inline double layerFieldValue(const LayerSettings& t, std::string_view f) {
  if (f == "amp") return t.amp;
  if (f == "attackMs") return t.env.attackMs;
  if (f == "decayMs") return t.env.decayMs;
  if (f == "sustain") return t.env.sustain;
  if (f == "releaseMs") return t.env.releaseMs;
  if (f == "morph") return t.morph;
  if (f == "width") return t.width;
  if (f == "table") return t.table;
  if (f == "modRatio") return t.modRatio;
  if (f == "fmIndex") return t.fmIndex;
  if (f == "warp") return t.warp;
  if (f == "warpAt") return t.warpAt;
  if (f == "scan") return t.scan;
  if (f == "ringMix") return t.ringMix;
  if (f == "syncRatio") return t.syncRatio;
  if (f == "subLevel") return t.subLevel;
  if (f == "subOctave") return t.subOctave;
  if (f == "unison") return t.unison;
  if (f == "unisonCents") return t.unisonCents;
  if (f == "drive") return t.drive;
  if (f == "fold") return t.fold;
  if (f == "crushBits") return t.crushBits;
  if (f == "crushHz") return t.crushHz;
  if (f == "vcfType") return t.vcfType;
  if (f == "vcfCutoff") return t.vcfCutoff;
  if (f == "vcfQ") return t.vcfQ;
  if (f == "vcfTrack") return t.vcfTrack;
  if (f == "vcfEnv") return t.vcfEnv;
  if (f == "fAttackMs") return t.fenv.attackMs;
  if (f == "fDecayMs") return t.fenv.decayMs;
  if (f == "fSustain") return t.fenv.sustain;
  if (f == "fReleaseMs") return t.fenv.releaseMs;
  return std::nan("");
}

// A layer control's value on the panel as its text, and written back as the
// browser takes it: the drawbars as one registration of nine sliders.
inline std::u16string layerPanelValue(const Controls& panel, const LayerControl& row) {
  if (std::string_view(row.id) == "bars") {
    std::u16string out;
    for (int k = 0; k < 9; k++) out += toU16(jsNumberToString(panel.range("bar" + std::to_string(k))));
    return out;
  }
  return row.kind == LayerControl::Range ? toU16(jsNumberToString(panel.range(row.id))) : utf8To16(panel.select(row.id));
}
inline void setLayerPanelValue(Controls& panel, const LayerControl& row, const std::u16string& text) {
  if (std::string_view(row.id) == "bars") {
    const auto levels = parseRegistrationText(text);  // el.bars's setter: nine digits or nothing
    if (!levels) return;
    for (int k = 0; k < 9; k++) panel.setRange("bar" + std::to_string(k), toU16(jsNumberToString((*levels)[static_cast<std::size_t>(k)])));
    return;
  }
  if (row.kind == LayerControl::Range) panel.setRange(row.id, text);
  else panel.setSelect(row.id, text);
}

/* showLayerOnPanel: the layer controls are layer A's, moved between the
   layers rather than copied. Showing B keeps what A's said and writes B's
   tone into them through each one's law back; showing A again puts A's back
   rather than reading the generator, as the page does. The panel's labels
   are the page's. */
inline void showLayerOnPanel(Brain& b, const Generator& gen, int layer) {
  if (layer == b.panelLayer) return;
  if (layer == 1) {
    b.panelKeptA.clear();
    for (const auto& row : layerControls()) b.panelKeptA.push_back({ row.id, layerPanelValue(b.panel, row) });
    const LayerSettings& toneB = gen.toneB();
    for (const auto& row : layerControls()) {
      const std::string_view field = row.field;
      std::u16string text;
      if (field == "shape") text = utf8To16(toneB.shapeName);
      else if (field == "subShape") text = utf8To16(toneB.subShapeName);
      else if (field == "bars") for (const double v : toneB.bars) text += toU16(jsNumberToString(jsMathRound(v)));
      else text = toU16(jsNumberToString(row.inverse(layerFieldValue(toneB, field))));
      setLayerPanelValue(b.panel, row, text);
    }
  } else if (b.keptA) {
    for (const auto& row : layerControls()) {
      for (const auto& [id, text] : b.panelKeptA) if (id == row.id) setLayerPanelValue(b.panel, row, text);
    }
  }
  b.keptA = layer == 1;
  b.panelLayer = layer;
}
// The plane section's, defined with the other refreshers below.
inline std::string planeSide(const Brain& b, const Keyboard& keys);
inline void syncPlanePanel(Brain& b, const Keyboard& keys);
inline void syncEchoPanel(Brain& b, const Keyboard& keys);
// syncLayerPanel: the layer the keyboard says is being edited, on the panel.
inline void syncLayerPanel(Brain& b, const Generator& gen, const Keyboard& keys) {
  showLayerOnPanel(b, gen, b.panelHeldOnA ? 0 : keys.editLayer());
  // syncPlaneLayer: the plane section says whose plane it shows the moment that changes.
  if (planeSide(b, keys) != b.planeShown) syncPlanePanel(b, keys);
  if (planeSide(b, keys) != b.echoShown) syncEchoPanel(b, keys);
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
    { "oscRatio", "bRatio" }, { "oscFm", "bFm" }, { "oscBend", "bBend" }, { "oscBendAt", "bBendAt" },
    { "oscScan", "bScan" }, { "oscRing", "bRing" }, { "oscSync", "bSync" }, { "oscSub", "bSub" },
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

/* The panel's refreshers: the sliders written back from the state they show.
   By number rather than by the text of it, which comes to the same value
   (setRangeNumber) and makes nothing, since a slider's handler - the morph's
   walk, a host parameter - calls these on the audio thread. */
/* planeEditsB, planeTarget: which layer's plane the section's controls are -
   B's while B has its own and is the layer on the panel, A's otherwise. */
inline bool planeEditsB(const Brain& b, const Keyboard& keys) {
  return !b.panelHeldOnA && keys.layersOn() && b.planeB.own && keys.editLayer() == 1;
}
inline Brain::PlaneShape& planeTarget(Brain& b, const Keyboard& keys) {
  return planeEditsB(b, keys) ? static_cast<Brain::PlaneShape&>(b.planeB) : b.plane;
}
inline std::string planeSide(const Brain& b, const Keyboard& keys) {
  return !keys.layersOn() ? "one" : !b.planeB.own ? "both" : planeEditsB(b, keys) ? "b" : "a";
}
inline void planeBFollow(Brain& b) { static_cast<Brain::PlaneShape&>(b.planeB) = b.plane; }
inline void syncPlanePanel(Brain& b, const Keyboard& keys) {
  const auto pct = [](double v) { return jsMathRound(v * 100); };
  const auto n = [](double v) { return toU16(jsNumberToString(v)); };
  b.planeShown = planeSide(b, keys);
  const Brain::PlaneShape& p = planeTarget(b, keys);
  b.panel.setRangeNumber("planeTurn", pct(b.planeB.turn));
  b.panel.setSelect("planeMirror", n(p.mirror));
  b.panel.setSelect("planeLimit", n(p.limit));
  b.panel.setRangeNumber("planeRadius", pct(p.radius));
  b.panel.setRangeNumber("planeTwist", pct(p.twist));
  b.panel.setSelect("planeSnap", n(p.snap));
  b.panel.setRangeNumber("planeScaleX", pct(p.scaleX));
  b.panel.setRangeNumber("planeScaleY", pct(p.scaleY));
  b.panel.setRangeNumber("planeShear", pct(p.shear));
}
// A's echo's time in force, or B's own.
inline double delayTimeMs(const Brain& b, const Brain::EchoState& e) {
  const double beats = delayBeats(e.sync);
  return beats > 0 ? std::fmin(2000, beats * 60000 / b.clock.bpm) : e.ms;
}
inline double delayTimeMs(const Brain& b) { return delayTimeMs(b, b.echo); }
// echoBFollow, echoTarget: B's own echo a copy of A's, and which of the two
// the section's controls write - the plane's choice, one switch for both.
inline void echoBFollow(Brain& b) {
  const std::optional<double> sent = b.echoB.sent;
  b.echoB = b.echo;
  b.echoB.sent = sent;
}
inline Brain::EchoState& echoTarget(Brain& b, const Keyboard& keys) {
  return planeEditsB(b, keys) ? b.echoB : b.echo;
}
// The time a synced echo shows is the tempo's, and its slider stands still.
inline void syncEchoPanel(Brain& b, const Keyboard& keys) {
  b.echoShown = planeSide(b, keys);
  const Brain::EchoState& e = echoTarget(b, keys);
  b.panel.setRangeNumber("delayMix", jsMathRound(e.mix * 100));
  b.panel.setRangeNumber("delayMs", !e.sync.empty() ? jsMathRound(delayTimeMs(b, e)) : e.ms);
  b.panel.setRangeNumber("delayFeedback", jsMathRound(e.feedback * 100));
  b.panel.setRangeNumber("delayTone", jsMathRound(e.tone * 100));
  b.panel.setRangeNumber("delayLowCut", jsMathRound(e.lowCut * 100));
  b.panel.setRangeNumber("delayWidth", jsMathRound(e.width * 100));
  b.panel.setRangeNumber("delayWow", jsMathRound(e.wow * 100));
  b.panel.setRangeNumber("chorusMix", jsMathRound(e.chorus * 100));
  b.panel.setRangeNumber("chorusRate", jsMathRound(e.rate * 100));
  b.panel.setRangeNumber("chorusDepth", jsMathRound(e.depthMs * 10));
  b.panel.setRangeNumber("chorusTime", jsMathRound(e.centreMs * 10));
  b.panel.setRangeNumber("chorusFeedback", jsMathRound(e.chorusFeedback * 100));
  b.panel.setRangeNumber("phaserMix", jsMathRound(e.phaser * 100));
  b.panel.setRangeNumber("phaserRate", jsMathRound(e.phRate * 100));
  b.panel.setRangeNumber("phaserDepth", jsMathRound(e.phDepth * 100));
  b.panel.setRangeNumber("phaserFeedback", jsMathRound(e.phFeedback * 100));
  b.panel.setRangeNumber("reverbMix", jsMathRound(e.rvMix * 100));
  b.panel.setRangeNumber("reverbSize", jsMathRound(e.rvSize * 100));
  b.panel.setRangeNumber("reverbTone", jsMathRound(e.rvTone * 100));
  b.panel.setRangeNumber("reverbPre", jsMathRound(e.rvPre));
  b.panel.setRangeNumber("reverbSpread", jsMathRound(e.rvSpread * 100));
}

// syncPlane, syncEcho, syncCrossings, syncQuantiser: the state written to the
// generator whole.
// Layer B's, into layer B; following A's while it has none of its own.
inline void syncPlaneB(Brain& b, Generator& gen) {
  if (!b.planeB.own) planeBFollow(b);
  const Brain::PlaneBState& p = b.planeB;
  gen.set("planeOwn", p.own ? 1 : 0, 1);
  gen.set("planeMirror", p.mirror, 1); gen.set("planeLimit", p.limit, 1); gen.set("planeRadius", p.radius, 1);
  gen.set("planeTwist", p.twist * kTwoPi, 1); gen.set("planeSnap", p.snap, 1);
  gen.set("planeScaleX", p.scaleX, 1); gen.set("planeScaleY", p.scaleY, 1); gen.set("planeShear", p.shear, 1);
  gen.set("planeTurn", p.turn * kTwoPi, 1);
}
inline void syncPlane(Brain& b, Generator& gen) {
  syncPlaneB(b, gen);
  const Brain::PlaneState& p = b.plane;
  gen.set("planeMirror", p.mirror); gen.set("planeLimit", p.limit); gen.set("planeRadius", p.radius);
  gen.set("planeOS", p.os); gen.set("planeTwist", p.twist * kTwoPi);
  gen.set("planeSnap", p.snap); gen.set("planeScaleX", p.scaleX); gen.set("planeScaleY", p.scaleY);
  gen.set("planeShear", p.shear);
}
// The order's index in the engine's table, as the page's fxOrderIndex; one it has not got is the first.
inline int fxOrderIndex(const Brain& b) {
  for (int k = 0; k < kFxOrderCount; k++) if (b.fxOrder == kFxOrders[k]) return k;
  return 0;
}
// Layer B's, into layer B, following A's while it has none of its own.
inline void syncEchoB(Brain& b, Generator& gen) {
  if (!b.planeB.own) echoBFollow(b);
  const Brain::EchoState& e = b.echoB;
  gen.set("delayMix", e.mix, 1); gen.set("delayMs", delayTimeMs(b, e), 1); gen.set("delayFeedback", e.feedback, 1);
  gen.set("delayPingPong", e.pingPong ? 1 : 0, 1); gen.set("chorusMix", e.chorus, 1); gen.set("chorusRate", e.rate, 1);
  gen.set("delayTone", e.tone, 1); gen.set("delayLowCut", e.lowCut, 1); gen.set("delayWidth", e.width, 1); gen.set("delayWow", e.wow, 1);
  gen.set("chorusDepthMs", e.depthMs, 1); gen.set("chorusMs", e.centreMs, 1);
  gen.set("chorusFeedback", e.chorusFeedback, 1);
  gen.set("phaserMix", e.phaser, 1); gen.set("phaserRate", e.phRate, 1); gen.set("phaserDepth", e.phDepth, 1);
  gen.set("phaserFeedback", e.phFeedback, 1);
  gen.set("reverbMix", e.rvMix, 1); gen.set("reverbSize", e.rvSize, 1); gen.set("reverbTone", e.rvTone, 1);
  gen.set("reverbPreMs", e.rvPre, 1); gen.set("reverbSpread", e.rvSpread, 1);
  gen.set("fxOrder", fxOrderIndex(b), 1);
}
inline void syncEcho(Brain& b, Generator& gen) {
  syncEchoB(b, gen);
  const Brain::EchoState& e = b.echo;
  gen.set("delayMix", e.mix); gen.set("delayMs", delayTimeMs(b)); gen.set("delayFeedback", e.feedback);
  gen.set("delayPingPong", e.pingPong ? 1 : 0); gen.set("chorusMix", e.chorus); gen.set("chorusRate", e.rate);
  gen.set("delayTone", e.tone); gen.set("delayLowCut", e.lowCut); gen.set("delayWidth", e.width); gen.set("delayWow", e.wow);
  gen.set("chorusDepthMs", e.depthMs); gen.set("chorusMs", e.centreMs); gen.set("chorusFeedback", e.chorusFeedback);
  gen.set("phaserMix", e.phaser); gen.set("phaserRate", e.phRate); gen.set("phaserDepth", e.phDepth);
  gen.set("phaserFeedback", e.phFeedback);
  gen.set("reverbMix", e.rvMix); gen.set("reverbSize", e.rvSize); gen.set("reverbTone", e.rvTone);
  gen.set("reverbPreMs", e.rvPre); gen.set("reverbSpread", e.rvSpread);
  gen.set("fxOrder", fxOrderIndex(b));
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
// delayFollows: under a MIDI clock, a synced delay's time sent again only once
// the tempo has moved it more than kDelaySyncSlack from the time last sent -
// the clock's estimate moves with every tick's jitter, and each new time
// glided the read head, so the repeats were never still (the page says more).
// And not before the clock has a beat of ticks to take its mean over.
constexpr double kDelaySyncSlack = 0.02;      // DELAY_SYNC_SLACK
constexpr std::size_t kDelaySyncTicks = 25;   // DELAY_SYNC_TICKS, a beat's 24 gaps
inline bool delayFollows(const Clock& clock, double ms, const std::optional<double>& sent) {
  if (!sent) return true;
  if (clock.from != Clock::From::Midi) return ms != *sent;
  return clock.ticks.size() >= kDelaySyncTicks && std::fabs(ms - *sent) > *sent * kDelaySyncSlack;
}
// clockStep, whole: the clock's own step, then a delay in note values sent
// again when the tempo has moved it - and whether it was.
inline bool clockFrame(Brain& b, Generator& gen, double now) {
  b.clock.step(now);
  bool sent = false;
  if (!b.echo.sync.empty()) {
    const double ms = delayTimeMs(b);
    if (delayFollows(b.clock, ms, b.echo.sent)) { b.echo.sent = ms; gen.set("delayMs", ms); sent = true; }
  }
  // And layer B's own, while it has one.
  if (b.planeB.own && !b.echoB.sync.empty()) {
    const double ms = delayTimeMs(b, b.echoB);
    if (delayFollows(b.clock, ms, b.echoB.sent)) { b.echoB.sent = ms; gen.set("delayMs", ms, 1); sent = true; }
  }
  return sent;
}
// setTempo, with the slider it writes.
inline void setTempo(Brain& b, double bpm, double at) {
  b.clock.setTempo(bpm, at);
  b.panel.setRangeNumber("tempo", b.clock.set);
}
// clockTap, with the slider a tap's tempo writes.
inline void tapTempo(Brain& b, double at) {
  b.clock.tap(at);
  b.panel.setRangeNumber("tempo", b.clock.set);
}

// cycleSend(true): every slot's tables, to the generator - the drawn cycle
// for both layers (layer B plays layer A's) and the bank for the wavetable.
inline void cycleSend(Brain& b, Generator& gen) {
  if (!b.cycleBank || b.cycleBuiltFrom != b.cycles) {
    auto bank = std::make_shared<std::vector<CycleTables>>();
    for (std::size_t k = 0; k < kCycleSlots; k++) {
      const bool same = b.cycleBank && b.cycleBuiltFrom[k] == b.cycles[k];
      if (same) { bank->push_back((*b.cycleBank)[k]); continue; }
      // Built ahead where it could be (CycleCache), and only then here.
      const auto ahead = CycleCache::shared().take(b.cycles[k]);
      bank->push_back(ahead ? *ahead : cycleTables(b.cycles[k]));
    }
    b.cycleBank = bank;
    b.cycleBuiltFrom = b.cycles;
  }
  gen.setCycle(std::shared_ptr<const CycleTables>(b.cycleBank, &(*b.cycleBank)[0]));
  gen.setWavetable(b.cycleBank);
}

// --- the handlers' part, in restore's order -------------------------------------------------

// --- the view ---------------------------------------------------------------------------

// setZoom: the step held to the slider's range, and the zoom it and what is
// pointed at it make, in quarter-steps of a doubling.
inline void setZoom(Brain& b, double step) {
  Brain::ViewState& w = b.view;
  w.zoomStep = jsMax(0, jsMin(24, step));
  w.screen.zoom = std::pow(2, (w.zoomStep + w.zoomMod) / 4);
}

// setTrigSource: held to the lanes there are.
inline void setTrigSource(Brain& b, double index) {
  b.view.trigSource = jsMax(0, jsMin(index, b.view.lanes - 1));
}

// fitChannels' hold on the trigger's lane and the pair: neither past the
// lanes there are, and the pair never one lane twice.
inline void fitView(Brain& b) {
  Brain::ViewState& w = b.view;
  const double n = w.lanes;
  if (w.trigSource >= n) w.trigSource = 0;
  w.xy = { jsMin(w.xy[0], n - 1), jsMin(w.xy[1], n - 1) };
  if (w.xy[0] == w.xy[1]) w.xy[1] = std::fmod(w.xy[0] + 1, std::fmax(2.0, n));
}

// relaneForLag: the pair and the trigger held to the lanes, and the lanes'
// rows built again from what they hold - each scale at the detent nearest its
// decibels (fsDetent), each offset in whole hundredths.
inline void relane(Brain& b) {
  fitView(b);
  const View& v = b.view.capture;
  for (std::size_t i = 0; i < 2 && i < v.channels.size(); i++) {
    std::size_t best = 0;
    for (std::size_t k = 1; k < 9; k++) {
      if (std::fabs(kFullScaleDb[k] - v.channels[i].fsDb) < std::fabs(kFullScaleDb[best] - v.channels[i].fsDb)) best = k;
    }
    const std::string lane = "ch" + std::to_string(i + 1);
    b.panel.setRange(lane + "Scale", toU16(jsNumberToString(static_cast<double>(best))));
    b.panel.setRange(lane + "Offset", toU16(jsNumberToString(jsMathRound(v.channels[i].offset * 100))));
  }
}

/* Number(x.toPrecision(4)), as the page rounds Persistence's slider to a
   fraction: four significant figures of the exact value, a tie going to the
   larger, read back as the nearest double. glibc's printf writes the exact
   decimal expansion of a double, so eighty digits of it decide the rounding. */
inline double jsToPrecision4(double x) {
  if (!std::isfinite(x) || x == 0) return x;
  char buf[128];
  std::snprintf(buf, sizeof buf, "%.80e", std::fabs(x));
  const char* e = std::strchr(buf, 'e');
  int exponent = std::atoi(e + 1);
  long n = (buf[0] - '0') * 1000L + (buf[2] - '0') * 100L + (buf[3] - '0') * 10L + (buf[4] - '0');
  if (buf[5] >= '5') n++;
  if (n == 10000) { n = 1000; exponent++; }
  std::snprintf(buf, sizeof buf, "%lde%d", n, exponent - 3);
  const double v = std::strtod(buf, nullptr);
  return x < 0 ? -v : v;
}

/* Persistence as Scan's slider shows it (P7a): how long a stroke takes to
   fade to half at sixty frames a second, on a log scale from 20 ms to ten
   seconds, Off below and Infinite above. The page's memoryHalfLife,
   memoryOfSlider and memorySliderOf. */
constexpr double kMemoryLeast = 0.02, kMemoryMost = 10;
inline double memoryHalfLife(double p) { return -1 / (60 * std::log2(1 - p)); }
inline double memoryOfSlider(double m) {
  if (m <= 0) return 0;
  if (m >= 100) return -1;
  const double h = kMemoryLeast * std::pow(kMemoryMost / kMemoryLeast, (m - 1) / 98);
  return jsToPrecision4(1 - std::pow(2.0, -1 / (60 * h)));
}
inline double memorySliderOf(double p) {
  if (p == 0) return 0;
  if (p < 0) return 100;
  const double h = memoryHalfLife(jsMin(0.999, p));
  return jsMax(1, jsMin(99, jsMathRound(1 + 98 * std::log(h / kMemoryLeast) / std::log(kMemoryMost / kMemoryLeast))));
}

/* setPersistence: the screen's persistence, its menu and Scan's slider, one
   field. The menu shows one of its five when the value is one, and otherwise
   its sixth option, written as the value; the page's comment says why. */
inline void setPersistence(Brain& b, double p) {
  p = std::isfinite(p) ? p : 0;
  b.view.screen.persistence = p;
  /* Nothing made, since a host moves this on the audio thread (P8a). The
     value is written once, as the page would show it, into a buffer; an
     option is the value when it is that text, which is Number(option) ===
     p, since a double's shortest text is its own (and -0 writes "0", as
     0 === -0; the five are written as JS writes them). The sixth option
     takes the text into the room the panel keeps for it. */
  char written[kJsNumberRoom];
  const std::string_view text(written, jsNumberToChars(p, written));
  bool found = false;
  if (const SelectSpec* spec = selectSpec("persistence")) {
    std::string_view options = spec->options;
    while (!found) {
      const std::size_t cut = options.find('\x1f');
      // The sixth option is the one with no value until it is given one.
      if (!options.substr(0, cut).empty() && options.substr(0, cut) == text) found = true;
      if (cut == std::string_view::npos) break;
      options.remove_prefix(cut + 1);
    }
  }
  if (found) b.panel.setSelect("persistence", toU16(text));
  else b.panel.setCustomOption("persistence", text);
  b.panel.setRangeNumber("scanMemory", memorySliderOf(p));
}

// setDisplay: X-Y with no persistence is a thin scribble, so it is nudged once, on the way in.
inline void setDisplay(Brain& b, const std::string& mode) {
  Brain::ViewState& w = b.view;
  w.screen.display = mode;
  if (mode == "xy" && w.screen.persistence == 0) setPersistence(b, 0.12);
}

// The view as the capture and the walk read it: the page's numbers held to
// what they can index - a timebase off the table, or a lane that is not a
// whole number, is the default rather than a read past the end - and the
// pair and the analysis tap carried across.
inline const View& captureView(Brain& b) {
  Brain::ViewState& w = b.view;
  const auto index = [](double x, double top, int otherwise) {
    return std::isfinite(x) && x == std::floor(x) && x >= 0 && x <= top ? static_cast<int>(x) : otherwise;
  };
  w.capture.timebase = index(w.timebase, static_cast<double>(kTimebase.size() - 1), 4);
  w.capture.trigSource = index(w.trigSource, kMaxLanes - 1, 0);
  w.capture.rising = w.edge == "rising";
  w.capture.shaping = w.analyseAt == "post";
  w.capture.measurePost = w.measureAt == "post";
  w.screen.xyPair = { index(w.xy[0], kMaxLanes - 1, 0), index(w.xy[1], kMaxLanes - 1, 1) };
  return w.capture;
}

// The cycles drawn by hand, as a setup carries them: slot one ("cycle") and
// the rest ("cycles"), each its default when it says nothing. A setup's, and
// the instrument's `drawn` control, since a drawing is neither a slider nor
// a preset and reached the plugin by neither.
inline void restoreCycles(const Json* first, const Json* rest, Brain& brain, Generator& gen) {
  const auto one = decodeCycle(first);
  brain.cycles[0] = one ? *one : cycleDefault(0);
  decodeCycleSlots(rest, brain.cycles);
  cycleSend(brain, gen);
}

// The Expression menus' value for each place, as the page's menus hold them.
inline std::u16string expressName(Keyboard::Express e) {
  switch (e) {
    case Keyboard::Express::Vibrato: return u"vibrato";
    case Keyboard::Express::Picture: return u"picture";
    case Keyboard::Express::Scan: return u"scan";
    case Keyboard::Express::Off: return u"off";
  }
  return u"off";
}

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
  // The controls say layer A while a setup is being written into them, held
  // there until it is done, and then whatever the keyboard says.
  struct HeldOnA {
    Brain& b; const Generator& gen; const Keyboard& keys;
    ~HeldOnA() { b.panelHeldOnA = false; syncLayerPanel(b, gen, keys); }
  } held { brain, gen, keys };
  brain.panelHeldOnA = true;
  showLayerOnPanel(brain, gen, 0);
  // Menus and ranges are the table's (field, below), not written here: they
  // were, beside the page's, until 7 Nov (schema.h has why).
  Controls& panel = brain.panel;
  const auto setA = [&](std::string_view field, double v) { gen.set(field, v, 0); };
  // A field by its rule in the table (setupField), and as text for a control.
  const auto field = [&](std::string_view key) { return setupField(s(key), key); };
  const auto fieldNum = [&](std::string_view key) { return field(key).n; };
  const auto fieldText = [&](std::string_view key) { return toU16(jsNumberToString(field(key).n)); };
  const auto fieldStr = [&](std::string_view key) { return field(key).s; };
  const auto fieldFlag = [&](std::string_view key) { return field(key).b; };
  // Layer B's own (setupOwn): only what the setup itself says.
  const auto own = [&](std::string_view key) { return setupOwn(given ? partial.get(key) : nullptr, key); };

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
  panel.setRange("width", fieldText("width"));
  panel.setRange("table", fieldText("table"));
  panel.setRange("freq", str("freq"));
  panel.setRange("amp", str("amp"));
  panel.setSelect("interval", str("interval"));
  panel.setRange("phase", str("phase"));
  panel.setSelect("inputMode", fieldText("inputMode"));
  panel.setRange("inputDepth", str("inputDepth"));
  restoreCycles(s("cycle"), s("cycles"), brain, gen);
  {
    const double mode = panel.selectNumber("inputMode");
    brain.inputMode = mode == 0 || std::isnan(mode) ? 0 : mode;
    setA("inputMode", brain.inputMode);
  }
  panel.setRange("envAttack", str("atk"));
  panel.setRange("envDecay", str("dec"));
  panel.setRange("envSustain", str("sus"));
  panel.setRange("envRelease", str("rel"));
  panel.setRange("glide", str("glide"));

  // The sliders' handlers, as `restore` fires them.
  setA("freq", panel.range("freq"));
  setA("amp", panel.range("amp") / 100);
  setA("phase", panel.range("phase") * kPi / 180);
  setA("inputDepth", panel.range("inputDepth") / 100);
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
  // OSC_RANGES and OSC_MENUS: the voice's fields the table gives a range, or
  // its control's own options.
  for (const auto& [key, row] : setupFields().o) {
    const std::string id = utf16To8(key);
    if (id.rfind("osc", 0) != 0 && id.rfind("shp", 0) != 0 && id.rfind("vcf", 0) != 0) continue;
    if (row.a.size() < 2) continue;
    const std::u16string& kind = row.a[1].a[0].s;
    if (kind == u"within") panel.setRange(id, fieldText(id));
    else if (kind == u"options") {
      const std::u16string want = str(id);
      const SelectSpec* spec = selectSpec(id);
      panel.setSelect(id, selectHas(*spec, utf16To8(want)) ? want : jsToString(*defaults.get(id)));
    }
  }
  panel.setSelect("shpOS", fieldText("shpOS"));
  setA("shapeOS", panel.selectNumber("shpOS"));
  applyVoiceLaws(gen, panel, 0);

  setA("interval", panel.selectNumber("interval"));

  // A reswing - the pair's phases from nought - and the tuning, as the page
  // passes them. The kind went before the reswing until G2; there is one.
  gen.reswing();
  {
    const Json* j = s("just");
    const bool truthy = j && !(j->type == Json::Type::Null || (j->type == Json::Type::Bool && !j->b)
                               || (j->type == Json::Type::Number && (j->n == 0 || std::isnan(j->n)))
                               || (j->type == Json::Type::String && j->s.empty()));
    setA("just", truthy ? 1 : 0);
  }
  {
    // The quarter turn (P8g): only a true one, as the page reads `=== true`.
    setA("polyRound", fieldFlag("polyRound") ? 1 : 0);
  }
  {
    // Expression (6 Nov), as the page's restore reads it: a range on the menu's list, or two.
    const double range = fieldNum("bendRange");
    const auto wheel = Keyboard::expressNamed(fieldStr("wheelTo"), Keyboard::Express::Vibrato);
    const auto press = Keyboard::expressNamed(fieldStr("pressureTo"), Keyboard::Express::Off);
    keys.setExpression(range, wheel, press);
    brain.panel.setSelect("midiBendRange", toU16(jsNumberToString(range)));
    brain.panel.setSelect("midiWheelTo", expressName(wheel));
    brain.panel.setSelect("midiPressureTo", expressName(press));
    setA("pitchBend", keys.bend() * range);
    if (wheel != Keyboard::Express::Vibrato && press != Keyboard::Express::Vibrato) setA("vibrato", 0);
  }

  // The keyboard.
  Keyboard::Settings k = keys.settings();
  {
    const std::u16string mode = fieldStr("midiMode");
    k.mode = mode == u"mono" ? NoteMode::Mono : mode == u"poly" ? NoteMode::Poly : NoteMode::Dyad;
  }
  const auto rule = [&](std::string_view key) {
    const std::u16string which = fieldStr(key);
    if (which == u"lowest") return DrawWhich::Lowest;
    if (which == u"highest") return DrawWhich::Highest;
    if (which == u"recent") return DrawWhich::Recent;
    return DrawWhich::Outer;
  };
  const auto count = [&](std::string_view key) {
    const double v = num(key);
    return std::fmax(2, std::fmin(kPolyVoices, v == 0 || std::isnan(v) ? 2 : v));
  };
  k.draws[0] = { count("midiDrawCount"), rule("midiDrawWhich") };
  k.draws[1] = { count("midiDrawCountB"), rule("midiDrawWhichB") };
  {
    const std::u16string layers = fieldStr("layers");
    k.layers = layers == u"split" ? LayerMode::Split : layers == u"layer" ? LayerMode::Layer : LayerMode::Off;
  }
  {
    const Json* at = s("splitAt");
    k.point = at && at->type == Json::Type::Number && std::isfinite(at->n) && at->n == std::floor(at->n)
            ? static_cast<int>(std::fmax(0, std::fmin(127, at->n))) : 60;
  }
  k.against = fieldStr("layerPair") == u"against";
  // Whose sound each layer's picture moves: a value the menu has not got is the layer's own.
  for (int l = 0; l < 2; l++) {
    const Json* v = s(l == 0 ? "pictureMovesA" : "pictureMovesB");
    const std::string own = l == 0 ? "A" : "B";
    brain.pictureMoves[static_cast<std::size_t>(l)] = pictureMovesOf(v && v->type == Json::Type::String ? utf16To8(v->s) : own, own);
    panel.setSelect(l == 0 ? "pictureMovesA" : "pictureMovesB", toU16(brain.pictureMoves[static_cast<std::size_t>(l)]));
  }

  // Layer B: its own field where the setup gives one, else layer A's.
  applyLayerB(partial, s, gen, panel);

  k.polyJust = fieldFlag("midiPolyJust");
  // Math.min and Math.max carry a NaN through, where fmin and fmax drop it.
  brain.photo.u = jsMax(0, jsMin(1, num("photoU")));
  brain.photo.v = jsMax(0, jsMin(1, num("photoV")));
  if (!std::isfinite(brain.photo.u)) brain.photo.u = 0.75;
  if (!std::isfinite(brain.photo.v)) brain.photo.v = 0.5;
  brain.photo.on = fieldFlag("photoOn");
  // The picture stage's amount, only when the setup names it: it is the
  // player's, and a preset that does not say leaves it where the hand left
  // it (the page's restoreInto). Held as the slider holds it, and the
  // default rather than the range's middle for a value that is not a number.
  if (const Json* named = partial.type == Json::Type::Object ? partial.get("pictureAmount") : nullptr) {
    const double want = jsToNumber(named);
    panel.setRangeNumber("pictureAmount", std::isfinite(want) ? want : 60);
  }
  k.hold = fieldFlag("midiHold");
  k.truth = fieldFlag("midiTruth");
  k.follow = fieldFlag("midiFollow");
  keys.setSettings(k);
  keys.panel() = { panel.range("freq"), static_cast<int>(panel.selectNumber("interval")) };
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
    brain.keyScale = utf16To8(fieldStr("keyScale"));
    brain.quantise = fieldFlag("quant");
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

  // The Envelope's own (8 Nov): its switch and its four sliders, and A's tone
  // given what the sliders hold, as the page's restore and syncMenv do.
  setA("menvOwn", fieldFlag("menvOwn") ? 1 : 0);
  setA("menvEvery", fieldFlag("menvEvery") ? 1 : 0);
  for (const auto& [id, field, scale] : { std::tuple<const char*, const char*, double>{ "menvAtk", "menvAttackMs", 1 },
                                          { "menvDec", "menvDecayMs", 1 }, { "menvSus", "menvSustain", 100 },
                                          { "menvRel", "menvReleaseMs", 1 } }) {
    panel.setRangeNumber(id, fieldNum(id));
    setA(field, panel.range(id) / scale);
  }

  // The score and the arpeggiator: kept for their pieces.
  brain.score.on = fieldFlag("scoreOn");
  brain.score.step = utf16To8(fieldStr("scoreStep"));
  brain.score.voices = jsMathRound(fieldNum("scoreVoices"));
  brain.score.low = fieldNum("scoreLow");
  brain.score.octaves = jsMathRound(fieldNum("scoreOctaves"));
  if (!brain.score.on) scoreStop(brain.score, brain.out);
  {
    brain.arp.mode = utf16To8(fieldStr("arpMode"));
    brain.arp.rate = utf16To8(fieldStr("arpRate"));
    brain.arp.octaves = jsNumberToString(jsMathRound(fieldNum("arpOctaves")));
  }
  keys.setArp(brain.arp.mode, brain.arp.rate, jsStringToNumber(toU16(brain.arp.octaves)));  // arpSet

  // The morph's ends (the macros beside them went in P8d).
  {
    brain.morphA = decodeMorphEnd(s("morphA"), morphHome);
    const auto refB = [&](const std::string& id) {
      if (brain.morphA) for (const auto& [mid, v] : *brain.morphA) if (mid == id) return v;
      return morphHome(id);
    };
    brain.morphB = decodeMorphEnd(s("morphB"), refB);
    brain.morphPos = fieldNum("morphPos") / 100;
    panel.setRange("morphPos", toU16(jsNumberToString(jsMathRound(brain.morphPos * 100))));
    brain.morphApplied.reset();
  }

  // The plane and the echo.
  {
    Brain::PlaneState& p = brain.plane;
    p.mirror = fieldNum("planeMirror");
    p.limit = fieldNum("planeLimit");
    p.radius = fieldNum("planeRadius") / 100;
    p.os = fieldNum("planeOS");
    p.twist = fieldNum("planeTwist") / 100;
    p.snap = fieldNum("planeSnap");
    p.scaleX = fieldNum("planeScaleX") / 100;
    p.scaleY = fieldNum("planeScaleY") / 100;
    p.shear = fieldNum("planeShear") / 100;
    /* Layer B's own plane: not in the defaults, so a field the setup lacks
       is A's; with it off, B follows A. */
    Brain::PlaneBState& q = brain.planeB;
    planeBFollow(brain);
    q.own = fieldFlag("bPlane");
    q.turn = 0;
    if (q.own) {
      // B's own where it has a usable one, by A's rule, else A's as it stands.
      const auto menu = [&](std::string_view key, double a) { const auto v = own(key); return v ? v->n : a; };
      const auto slide = [&](std::string_view key, double a) { const auto v = own(key); return v ? v->n / 100 : a; };
      q.mirror = menu("bMirror", p.mirror);
      q.limit = menu("bLimit", p.limit);
      q.radius = slide("bRadius", p.radius);
      q.twist = slide("bTwist", p.twist);
      q.snap = menu("bSnap", p.snap);
      q.scaleX = slide("bScaleX", p.scaleX);
      q.scaleY = slide("bScaleY", p.scaleY);
      q.shear = slide("bShear", p.shear);
      q.turn = slide("bTurn", 0);
    }
    setA("planeMirror", p.mirror); setA("planeLimit", p.limit); setA("planeRadius", p.radius); setA("planeOS", p.os);
    setA("planeTwist", p.twist * kTwoPi); setA("planeSnap", p.snap);
    setA("planeScaleX", p.scaleX); setA("planeScaleY", p.scaleY); setA("planeShear", p.shear);
    syncPlaneB(brain, gen);
    syncPlanePanel(brain, keys);
  }
  {
    Brain::EchoState& e = brain.echo;
    e.mix = fieldNum("delayMix") / 100;
    e.ms = jsMathRound(fieldNum("delayMs"));
    e.sync = utf16To8(fieldStr("delaySync"));
    e.feedback = fieldNum("delayFeedback") / 100;
    e.pingPong = fieldFlag("delayPingPong");
    e.tone = fieldNum("delayTone") / 100;
    e.lowCut = fieldNum("delayLowCut") / 100;
    e.width = fieldNum("delayWidth") / 100;
    e.wow = fieldNum("delayWow") / 100;
    e.chorus = fieldNum("chorusMix") / 100;
    e.rate = fieldNum("chorusRate") / 100;
    e.depthMs = fieldNum("chorusDepth") / 10;
    e.centreMs = fieldNum("chorusTime") / 10;
    e.chorusFeedback = fieldNum("chorusFeedback") / 100;
    e.phaser = fieldNum("phaserMix") / 100;
    e.phRate = fieldNum("phaserRate") / 100;
    e.phDepth = fieldNum("phaserDepth") / 100;
    e.phFeedback = fieldNum("phaserFeedback") / 100;
    e.rvMix = fieldNum("reverbMix") / 100;
    e.rvSize = fieldNum("reverbSize") / 100;
    e.rvTone = fieldNum("reverbTone") / 100;
    e.rvPre = fieldNum("reverbPre");
    e.rvSpread = fieldNum("reverbSpread") / 100;
    setA("delayMix", e.mix);
    setA("delayMs", delayTimeMs(brain));
    setA("delayFeedback", e.feedback);
    setA("delayPingPong", e.pingPong ? 1 : 0);
    setA("delayTone", e.tone); setA("delayLowCut", e.lowCut); setA("delayWidth", e.width); setA("delayWow", e.wow);
    setA("chorusMix", e.chorus); setA("chorusRate", e.rate); setA("chorusDepthMs", e.depthMs);
    setA("chorusMs", e.centreMs); setA("chorusFeedback", e.chorusFeedback);
    setA("phaserMix", e.phaser); setA("phaserRate", e.phRate); setA("phaserDepth", e.phDepth);
    setA("phaserFeedback", e.phFeedback);
    setA("reverbMix", e.rvMix); setA("reverbSize", e.rvSize); setA("reverbTone", e.rvTone);
    setA("reverbPreMs", e.rvPre); setA("reverbSpread", e.rvSpread);
    /* Layer B's own echo and chorus, with its plane (bPlane): a field the
       setup lacks is A's, as B's plane's are. */
    echoBFollow(brain);
    if (brain.planeB.own) {
      Brain::EchoState& f = brain.echoB;
      // By A's rules, the twins in the table; a sync the menu has not got is
      // A's, as every other field of B's is (it was Free until 7 Nov).
      const auto slide = [&](std::string_view key, double scale, double a) { const auto v = own(key); return v ? v->n / scale : a; };
      f.mix = slide("bDelayMix", 100, e.mix);
      const auto ms = own("bDelayMs");
      f.ms = ms ? jsMathRound(ms->n) : e.ms;
      const auto sync = own("bDelaySync");
      f.sync = sync ? utf16To8(sync->s) : e.sync;
      f.feedback = slide("bDelayFeedback", 100, e.feedback);
      const auto ping = own("bDelayPingPong");
      f.pingPong = ping ? ping->b : e.pingPong;
      f.tone = slide("bDelayTone", 100, e.tone);
      f.lowCut = slide("bDelayLowCut", 100, e.lowCut);
      f.width = slide("bDelayWidth", 100, e.width);
      f.wow = slide("bDelayWow", 100, e.wow);
      f.chorus = slide("bChorusMix", 100, e.chorus);
      f.rate = slide("bChorusRate", 100, e.rate);
      f.depthMs = slide("bChorusDepth", 10, e.depthMs);
      f.centreMs = slide("bChorusTime", 10, e.centreMs);
      f.chorusFeedback = slide("bChorusFeedback", 100, e.chorusFeedback);
      f.phaser = slide("bPhaserMix", 100, e.phaser);
      f.phRate = slide("bPhaserRate", 100, e.phRate);
      f.phDepth = slide("bPhaserDepth", 100, e.phDepth);
      f.phFeedback = slide("bPhaserFeedback", 100, e.phFeedback);
      f.rvMix = slide("bReverbMix", 100, e.rvMix);
      f.rvSize = slide("bReverbSize", 100, e.rvSize);
      f.rvTone = slide("bReverbTone", 100, e.rvTone);
      f.rvPre = slide("bReverbPre", 1, e.rvPre);
      f.rvSpread = slide("bReverbSpread", 100, e.rvSpread);
    }
    syncEchoB(brain, gen);
    syncEchoPanel(brain, keys);
    // F5b: the order, after the echoes so both layers are told.
    brain.fxOrder = utf16To8(fieldStr("fxOrder"));
    panel.setSelect("fxOrder", utf8To16(brain.fxOrder));
    setA("fxOrder", fxOrderIndex(brain));
    gen.set("fxOrder", fxOrderIndex(brain), 1);
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
    // And the sources silenced (G5b), held aside with their routings: the
    // page's silentIds, whose `if (!text)` is the same falsiness as the list's.
    std::vector<std::string> silent;
    if (const Json* ids = s("modSilent")) {
      const bool falsy = ids->type == Json::Type::Null || (ids->type == Json::Type::Bool && !ids->b)
                      || (ids->type == Json::Type::Number && (ids->n == 0 || std::isnan(ids->n)))
                      || (ids->type == Json::Type::String && ids->s.empty());
      if (!falsy) silent = Matrix::silentIds(utf16To8(jsToString(*ids)));
    }
    matrix.keep(list, silent, true);
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

  // And what the page's restore leaves in its state, which is what the screen draws by.
  {
    Brain::ViewState& w = brain.view;
    View& v = w.capture;
    const auto truthy = [&](std::string_view key) { const Json* x = s(key); return x && jsTruthy(*x); };
    const auto text = [&](std::string_view key) { return utf16To8(str(key)); };
    w.timebase = num("timebase");
    v.level = num("level") / 1000;
    v.position = num("position") / 100;
    v.holdoffMs = num("holdoff") / 10;
    w.edge = text("edge");
    setTrigSource(brain, num("trig"));
    w.mode = text("trigMode");
    v.channels.resize(2);
    for (int i = 0; i < 2; i++) {
      const std::string key = "c" + std::to_string(i);
      View::Channel& c = v.channels[static_cast<std::size_t>(i)];
      c.on = truthy(key + "on");
      c.ac = truthy(key + "ac");
      c.fsDb = num(key + "s");
      c.offset = num(key + "o") / 100;
    }
    v.midSide = truthy("midSide");
    v.acHz = panel.range("acCorner") / 10;
    v.lagOn = truthy("lagOn") && !truthy("midSide");
    v.lagMs = num("lagMs");
    v.rotate = num("rotate") / 100;
    v.filter.on = truthy("fOn");
    v.filter.type = text("fType");
    v.filter.cutoff = num("fCut");
    v.filter.res = num("fRes");
    w.analyseAt = text("fSee");
    w.measureAt = text("mSee");
    v.lagLock.reset();
    v.lagAuto = truthy("lagAuto");
    w.xy = { num("xy0"), num("xy1") };
    relane(brain);
    Screen& sc = w.screen;
    sc.beam = text("beam");
    sc.beamXY = truthy("beamXY");
    sc.beamYT = truthy("beamYT");
    w.restored++;  // beamRefs.clear()
    // Persistence after the display, because switching to X-Y nudges it.
    setDisplay(brain, text("display"));
    setPersistence(brain, num("persistence"));
    // Scan's softness, in tenths of a cell, held to its slider.
    {
      panel.setRange("scanSoft", fieldText("scanSoft"));
      brain.scanSoft = panel.range("scanSoft") / 10;
      // The strike, held to its slider, and what each layer's Scan reads (P7b).
      panel.setRange("scanStrike", fieldText("scanStrike"));
      brain.scanStrike = panel.range("scanStrike") / 100;
      for (int l = 0; l < 2; l++) {
        const std::string own = l == 0 ? "A" : "B";
        const Json* v = s(l == 0 ? "scanReadsA" : "scanReadsB");
        brain.scanReads[static_cast<std::size_t>(l)] = scanReadsOf(v && v->type == Json::Type::String ? utf16To8(v->s) : own, own);
        panel.setSelect(l == 0 ? "scanReadsA" : "scanReadsB", toU16(brain.scanReads[static_cast<std::size_t>(l)]));
      }
    }
    w.spectroSpan = num("span");
    setZoom(brain, num("zoom"));
  }
}

}  // namespace scope

namespace scope {

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
  else if (id == "envAttack") layerSet("attackMs", v);
  else if (id == "envDecay") layerSet("decayMs", v);
  else if (id == "envSustain") layerSet("sustain", v / 100);
  else if (id == "envRelease") layerSet("releaseMs", v);
  else if (id == "glide") layerSet("glideMs", v);
  else if (id == "inputDepth") gen.set("inputDepth", v / 100);
  else if (id == "lfoRate0" || id == "lfoRate1") {
    const std::size_t i = id.back() == '1' ? 1 : 0;
    b.lfo[i].free = v / 100;
    if (b.lfo[i].sync.empty()) lfos[i].rate = b.lfo[i].free;
  }
  else if (id == "quantiseGlide") { b.quantiseGlide = v; syncQuantiser(b, gen); }
  // The Envelope's own times, as syncMenv sends them.
  else if (id == "menvAtk") gen.set("menvAttackMs", v);
  else if (id == "menvDec") gen.set("menvDecayMs", v);
  else if (id == "menvSus") gen.set("menvSustain", v / 100);
  else if (id == "menvRel") gen.set("menvReleaseMs", v);
  // Scan's softness in tenths of a cell, and its Persistence, which is the screen's.
  else if (id == "scanSoft") b.scanSoft = v / 10;
  else if (id == "scanStrike") b.scanStrike = v / 100;
  else if (id == "scanMemory") setPersistence(b, memoryOfSlider(v));
  else if (id == "morphPos") b.morphPos = v / 100;
  else if (id == "tempo") setTempo(b, v, b.clock.now());
  else if (id.size() == 4 && id.compare(0, 3, "bar") == 0) {
    // The nine read into an array and handed over as one, nothing made: the morph walks them.
    static constexpr const char* barIds[] { "bar0", "bar1", "bar2", "bar3", "bar4", "bar5", "bar6", "bar7", "bar8" };
    std::array<double, 9> bars {};
    for (std::size_t k = 0; k < 9; k++) bars[k] = b.panel.range(barIds[k]);
    gen.setBars(bars.data(), bars.size(), layer);
  }
  else if (id == "planeRadius" || id == "planeTwist" || id == "planeScaleX" || id == "planeScaleY" || id == "planeShear") {
    Brain::PlaneShape& p = planeTarget(b, keys);
    double& field = id == "planeRadius" ? p.radius : id == "planeTwist" ? p.twist
                  : id == "planeScaleX" ? p.scaleX : id == "planeScaleY" ? p.scaleY : p.shear;
    field = v / 100;
    syncPlanePanel(b, keys);
    syncPlane(b, gen);
  }
  // B's alone, whichever layer is on the panel.
  else if (id == "planeTurn") { b.planeB.turn = v / 100; syncPlanePanel(b, keys); syncPlane(b, gen); }
  else if (id == "delayMix" || id == "delayMs" || id == "delayFeedback" || id == "delayTone" || id == "delayLowCut"
           || id == "delayWidth" || id == "delayWow" || id == "chorusMix" || id == "chorusRate"
           || id == "chorusDepth" || id == "chorusTime" || id == "chorusFeedback" || id == "phaserMix"
           || id == "phaserRate" || id == "phaserDepth" || id == "phaserFeedback" || id == "reverbMix"
           || id == "reverbSize" || id == "reverbTone" || id == "reverbPre" || id == "reverbSpread") {
    Brain::EchoState& e = echoTarget(b, keys);
    if (id == "delayMix") e.mix = v / 100;
    else if (id == "delayMs") e.ms = v;
    else if (id == "delayFeedback") e.feedback = v / 100;
    else if (id == "delayTone") e.tone = v / 100;
    else if (id == "delayLowCut") e.lowCut = v / 100;
    else if (id == "delayWidth") e.width = v / 100;
    else if (id == "delayWow") e.wow = v / 100;
    else if (id == "chorusMix") e.chorus = v / 100;
    else if (id == "chorusRate") e.rate = v / 100;
    else if (id == "chorusDepth") e.depthMs = v / 10;
    else if (id == "chorusTime") e.centreMs = v / 10;
    else if (id == "chorusFeedback") e.chorusFeedback = v / 100;
    else if (id == "phaserMix") e.phaser = v / 100;
    else if (id == "phaserRate") e.phRate = v / 100;
    else if (id == "phaserDepth") e.phDepth = v / 100;
    else if (id == "phaserFeedback") e.phFeedback = v / 100;
    else if (id == "reverbMix") e.rvMix = v / 100;
    else if (id == "reverbSize") e.rvSize = v / 100;
    else if (id == "reverbTone") e.rvTone = v / 100;
    else if (id == "reverbPre") e.rvPre = v;
    else e.rvSpread = v / 100;
    syncEchoPanel(b, keys);
    syncEcho(b, gen);
  }
  // The view's sliders, each as the page's handler reads it.
  else if (id == "timebase") b.view.timebase = v;
  else if (id == "level") b.view.capture.level = v / 1000;
  else if (id == "position") b.view.capture.position = v / 100;
  else if (id == "holdoff") b.view.capture.holdoffMs = v / 10;
  else if (id == "ch1Scale" || id == "ch2Scale" || id == "ch1Offset" || id == "ch2Offset") {
    View::Channel& c = b.view.capture.channels[id[2] == '2' ? 1 : 0];
    // The scale's detent, by its index in the table, as the page's handler has it.
    if (id[3] == 'S') { const Json at = Json::number(v); c.fsDb = fullScaleAt(&at).value_or(NAN); }
    else c.offset = v / 100;
  }
  else if (id == "acCorner") b.view.capture.acHz = v / 10;
  else if (id == "lag") b.view.capture.lagMs = v / 10;
  else if (id == "rotate") b.view.capture.rotate = v / 100;
  else if (id == "filterCutoff") b.view.capture.filter.cutoff = v;
  else if (id == "filterRes") b.view.capture.filter.res = v;
  else if (id == "zoom") setZoom(b, v);
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
  if (b.panel.setRange(id, std::move(written))) sliderInput(id, b, gen, keys, lfos);
}
// And to a number, as a host parameter moves it: the slider's value as the
// text of that number would leave it, with no text made.
inline void moveSliderTo(const std::string& id, double value, Brain& b, Generator& gen, Keyboard& keys,
                         std::vector<Lfo>& lfos) {
  if (b.panel.setRangeNumber(id, value)) sliderInput(id, b, gen, keys, lfos);
}

// --- a menu or a switch changed: its handler ----------------------------------------------

/* What the page's "change" handler for a menu, a checkbox or a text box does,
   for each one that reaches the sound or a setting a setup carries: a hand on
   it, sent from the page in the plugin (stage 3). A menu's value is written as
   the browser would take it - one it has not got reads "" - and a switch is
   its new state. The view's do the view's work, which is the page's.

   What is not here yet, and why: the fade's menus and envelope, which live in
   the page's own storage rather than in a setup; layer B's editing, which
   swaps the panel between the layers (the panel here always writes layer A);
   and the MIDI out's port, which in the plugin is the host's. */
inline bool controlChange(const std::string& id, const std::u16string& written, bool checked, Brain& b, Generator& gen,
                          Keyboard& keys, std::vector<Lfo>& lfos) {
  Controls& panel = b.panel;
  const int layer = b.panelLayer;
  // A menu takes only a value it has; one it has not got reads "". LFO 2's
  // menus are made when it is chosen, from the lists LFO 1's are.
  const bool menu = selectSpec(id) != nullptr;
  const SelectSpec* like = selectSpec(id == "lfoShape1" ? "lfoShape0" : id == "lfoSync1" ? "lfoSync0" : "");
  if (menu) panel.setSelect(id, written);
  const std::u16string value = menu ? utf8To16(panel.select(id))
                             : like ? (selectHas(*like, utf16To8(written)) ? written : u"") : written;
  const std::string text = utf16To8(value);
  const double number = jsStringToNumber(value);
  const auto orElse = [](double v, double d) { return v == 0 || std::isnan(v) ? d : v; };
  Keyboard::Settings k = keys.settings();

  // The generator.
  if (id == "interval") { gen.set("interval", number, 0); keys.panel().interval = static_cast<int>(number); }
  else if (id == "inputMode") { b.inputMode = orElse(number, 0); gen.set("inputMode", b.inputMode, 0); }
  else if (id == "shape") gen.set("shape", text, layer);
  else if (id == "shpOS") gen.set("shapeOS", number, 0);
  else if (isVoiceControl(id) && menu) {
    for (const auto& row : layerControls()) {
      if (row.id != id) continue;
      if (row.kind == LayerControl::Text) gen.set(row.field, text, layer);
      else gen.set(row.field, row.law(number), layer);
    }
  }
  // The plane and the echo.
  else if (id == "planeMirror" || id == "planeLimit" || id == "planeSnap") {
    Brain::PlaneShape& p = planeTarget(b, keys);
    (id == "planeMirror" ? p.mirror : id == "planeLimit" ? p.limit : p.snap) = number;
    syncPlanePanel(b, keys); syncPlane(b, gen);
  }
  else if (id == "delaySync") { echoTarget(b, keys).sync = text; syncEchoPanel(b, keys); syncEcho(b, gen); }
  // F5b: the rack's order, one for both layers whichever is on the panel; a menu
  // value it has not got reads "" and is the first order, as on the page.
  else if (id == "fxOrder") {
    b.fxOrder = text.empty() ? kFxOrders[0] : text;
    panel.setSelect("fxOrder", utf8To16(b.fxOrder));
    syncEcho(b, gen);
  }
  else if (id == "delayPingPong") { echoTarget(b, keys).pingPong = checked; syncEcho(b, gen); }
  // The key and the quantiser.
  else if (id == "keyRoot") { b.keyRoot = number; syncQuantiser(b, gen); }
  else if (id == "keyScale") { b.keyScale = text; syncQuantiser(b, gen); }
  else if (id == "quantise") { b.quantise = checked; syncQuantiser(b, gen); }
  // The keyboard. The layer being edited is A's, as the panel here is.
  else if (id == "midiDrawCount") keys.setDraw(0, jsMax(2, jsMin(kPolyVoices, orElse(number, 2))), k.draws[0].which);
  else if (id == "midiDrawWhich") keys.setDraw(0, k.draws[0].count, drawWhichNamed(text));
  else if (id == "midiPolyJust") keys.setPolyJust(checked);
  else if (id == "midiLayers") keys.setLayers(text == "split" ? LayerMode::Split : text == "layer" ? LayerMode::Layer : LayerMode::Off);
  else if (id == "midiLayerPair") keys.setPair(text == "against");
  else if (id == "pictureMovesA") b.pictureMoves[0] = pictureMovesOf(text, "A");
  else if (id == "pictureMovesB") b.pictureMoves[1] = pictureMovesOf(text, "B");
  else if (id == "scanReadsA") b.scanReads[0] = scanReadsOf(text, "A");
  else if (id == "scanReadsB") b.scanReads[1] = scanReadsOf(text, "B");
  else if (id == "midiHold") keys.setHold(checked);
  else if (id == "polyRound") gen.set("polyRound", checked ? 1 : 0, 0);
  // Expression's menus (6 Nov): a vibrato no longer given to stops, as the page's expressionLetGo has it.
  else if (id == "midiBendRange" || id == "midiWheelTo" || id == "midiPressureTo") {
    double range = keys.bendRange();
    auto wheel = keys.wheelTo(), press = keys.pressureTo();
    if (id == "midiBendRange") { const Json t = Json::string(std::string_view(text)); range = jsToNumber(&t); }
    else if (id == "midiWheelTo") wheel = Keyboard::expressNamed(value, Keyboard::Express::Off);
    else press = Keyboard::expressNamed(value, Keyboard::Express::Off);
    keys.setExpression(range, wheel, press);
    if (id == "midiBendRange") gen.set("pitchBend", keys.bend() * range, 0);
    else if (wheel != Keyboard::Express::Vibrato && press != Keyboard::Express::Vibrato) gen.set("vibrato", 0, 0);
  }
  else if (id == "midiTruth") { k.truth = checked; keys.setSettings(k); }
  else if (id == "midiFollow") { k.follow = checked; keys.setSettings(k); }
  // The arpeggiator and the score.
  else if (id == "arpMode") {
    // arpSet reads all three menus. The other two are the brain's, which a
    // setup restores without writing the panel's copies of them.
    b.arp.mode = text;
    keys.setArp(b.arp.mode, b.arp.rate, jsStringToNumber(toU16(b.arp.octaves)));
  }
  else if (id == "arpRate") { b.arp.rate = text; keys.setArpRate(text); }
  else if (id == "arpOctaves") { b.arp.octaves = text; keys.setArpOctaves(number); }
  else if (id == "scoreOn") { b.score.on = checked; if (!b.score.on) scoreStop(b.score, b.out); }
  else if (id == "menvOwn") gen.set("menvOwn", checked ? 1 : 0);
  else if (id == "scoreStep") b.score.step = text;
  else if (id == "scoreVoices") b.score.voices = orElse(number, 1);
  else if (id == "scoreLow") b.score.low = orElse(number, 48);
  else if (id == "scoreOctaves") b.score.octaves = orElse(number, 3);
  // The oscillators: a shape, and a note value to lock to, which starts it on the beat.
  else if (id == "lfoShape0" || id == "lfoShape1") {
    const std::size_t i = id.back() == '1' ? 1 : 0;
    b.lfo[i].shape = Json::string(value);
    lfos[i].setShape(text);
  }
  else if (id == "lfoSync0" || id == "lfoSync1") {
    const std::size_t i = id.back() == '1' ? 1 : 0;
    Brain::LfoSetting& l = b.lfo[i];
    if (l.sync.empty()) l.free = lfos[i].rate;  // what to go back to
    l.sync = text;
    if (l.sync.empty()) lfos[i].rate = l.free;
    b.clock.step(b.clock.now());
    if (!l.sync.empty()) { lfos[i].phase = 0; lfos[i].epoch++; }
  }
  // The view's switches and menus.
  else if (id == "ch1On" || id == "ch2On" || id == "ch1Ac" || id == "ch2Ac") {
    View::Channel& c = b.view.capture.channels[id[2] == '2' ? 1 : 0];
    (id[3] == 'O' ? c.on : c.ac) = checked;
  }
  // Mid and side and the lag both rewrite lane two: the one just thrown wins.
  else if (id == "midSide") {
    View& v = b.view.capture;
    v.midSide = checked;
    if (v.midSide && v.lagOn) { v.lagOn = false; relane(b); }
  }
  else if (id == "lagOn") {
    View& v = b.view.capture;
    v.lagOn = checked;
    if (v.lagOn && v.midSide) v.midSide = false;
    v.lagLock.reset();  // the old lock belonged to whatever was playing before
    relane(b);
  }
  else if (id == "filterOn") b.view.capture.filter.on = checked;
  else if (id == "filterType") b.view.capture.filter.type = text;
  else if (id == "beamLevel") b.view.screen.beam = text;
  else if (id == "beamXY") b.view.screen.beamXY = checked;
  else if (id == "beamYT") b.view.screen.beamYT = checked;
  else if (id == "persistence") setPersistence(b, jsStringToNumber(value));
  else if (id == "xyX" || id == "xyY") {
    Brain::ViewState& w = b.view;
    const std::size_t which = id == "xyY" ? 1 : 0;
    w.xy[which] = jsStringToNumber(value);
    // Two of the same lane is the diagonal, always, whatever it is doing.
    if (w.xy[0] == w.xy[1]) w.xy[which ? 0 : 1] = std::fmod(w.xy[which] + 1, w.lanes);
  }
  // The reticle, moved: "u,v", each held to the screen, as the page splits
  // it - no comma is a u and a v that is not a number at all.
  else if (id == "photoReticle") {
    const std::size_t comma = value.find(u',');
    b.photo.u = jsMax(0, jsMin(1, jsStringToNumber(value.substr(0, comma))));
    b.photo.v = comma == std::u16string::npos ? NAN : jsMax(0, jsMin(1, jsStringToNumber(value.substr(comma + 1))));
  }
  else return false;
  return true;
}

// What the page's buttons that reach the sound do when pressed. Each answers
// whether it knew the control, so the plugin keeps only what did something.
inline bool controlClick(const std::string& id, Brain& b, Generator& gen, Keyboard& keys) {
  if (id == "tuneJust" || id == "tuneEqual") gen.set("just", id == "tuneJust" ? 1 : 0, 0);
  else if (id == "midiDyad") keys.setMode(NoteMode::Dyad);
  else if (id == "midiMono") keys.setMode(NoteMode::Mono);
  else if (id == "midiPoly") keys.setMode(NoteMode::Poly);
  else if (id == "midiEditA" || id == "midiEditB") keys.setEdit(id == "midiEditB" ? 1 : 0);
  else if (id == "menvPhrase" || id == "menvEvery") gen.set("menvEvery", id == "menvEvery" ? 1 : 0);
  else if (id == "planeOS1" || id == "planeOS2" || id == "planeOS4") {
    b.plane.os = id.back() - '0';
    syncPlanePanel(b, keys); syncPlane(b, gen);
  }
  /* setPlaneLayer: Together lets B's own go; A or B gives B its own - which
     is already a copy of A's, kept one by syncPlaneB and syncEchoB - and
     puts that layer on the panel. The Delay and chorus section's Layers row
     is the same choice. */
  else if (id == "planeLayerBoth" || id == "timeLayerBoth") {
    b.planeB.own = false;
    syncPlanePanel(b, keys); syncPlane(b, gen); syncEchoPanel(b, keys); syncEcho(b, gen);
  }
  else if (id == "planeLayerA" || id == "planeLayerB" || id == "timeLayerA" || id == "timeLayerB") {
    b.planeB.own = true;
    keys.setEdit(id == "planeLayerB" || id == "timeLayerB" ? 1 : 0);
    syncPlanePanel(b, keys); syncPlane(b, gen); syncEchoPanel(b, keys); syncEcho(b, gen);
  }
  // The view's buttons.
  else if (id == "dispYT" || id == "dispXY" || id == "dispSpect") setDisplay(b, id == "dispYT" ? "yt" : id == "dispXY" ? "xy" : "spect");
  else if (id == "edgeRising" || id == "edgeFalling") b.view.edge = id == "edgeRising" ? "rising" : "falling";
  else if (id == "modeAuto" || id == "modeNormal" || id == "modeSingle") b.view.mode = id == "modeAuto" ? "auto" : id == "modeNormal" ? "normal" : "single";
  else if (id == "lagAuto" || id == "lagManual") {
    b.view.capture.lagAuto = id == "lagAuto";
    if (b.view.capture.lagAuto) b.view.capture.lagLock.reset();
  }
  else if (id == "seeDry" || id == "seeWet") b.view.analyseAt = id == "seeDry" ? "pre" : "post";
  else if (id == "measurePre" || id == "measurePost") b.view.measureAt = id == "measurePre" ? "pre" : "post";
  else if (id == "layStack" || id == "layOver") b.view.screen.stack = id == "layStack";
  else if (id.size() == 11 && id.compare(0, 10, "trigSource") == 0 && id[10] >= '0' && id[10] <= '5') setTrigSource(b, id[10] - '0');
  else if (id == "photoButton") b.photo.on = !b.photo.on;
  else if (id == "clearButton") b.view.wipe = true;
  else return false;
  return true;
}

// The fade as the page keeps it, {mode, envs}, which the page in the plugin
// sends whole when it is saved (fadeFromHost): a mode it has not got is off,
// and an envelope not given is the default. Each number as the page's
// Number() takes it, so null is nought; restart and loop only if true.
inline void fadeFromPage(Matrix& matrix, const Json& value) {
  const Json* mode = value.isObject() ? value.get("mode") : nullptr;
  const std::u16string m = mode && mode->type == Json::Type::String ? mode->s : u"off";
  matrix.setFade(m == u"in" ? FadeMode::In : m == u"out" ? FadeMode::Out : m == u"both" ? FadeMode::Both : FadeMode::Off);
  const Json* envs = value.isObject() ? value.get("envs") : nullptr;
  for (int i = 0; i < 2; i++) {
    const Json* env = envs && envs->type == Json::Type::Array && static_cast<std::size_t>(i) < envs->a.size()
                      ? &envs->a[static_cast<std::size_t>(i)] : nullptr;
    FadePart p;
    // An envelope that is not an object is the default; an array is an
    // object to the page's typeof, with nothing in it.
    if (!env || !(env->isObject() || env->type == Json::Type::Array)) {
      const FadeEnvelope d;  // ENV_DEFAULT
      p.delay = d.delay; p.attack = d.attack; p.attackMid = d.attackMid; p.decay = d.decay; p.decayMid = d.decayMid;
      p.sustain = d.sustain; p.release = d.release; p.releaseMid = d.releaseMid; p.restart = d.restart; p.loop = d.loop;
    } else {
      const auto number = [&](std::string_view k, std::optional<double>& into) {
        if (const Json* v = env->isObject() ? env->get(k) : nullptr) into = jsToNumber(v);
      };
      // The page fills a missing attack or release from seconds with ??, to
      // which null is missing too.
      const bool seconds = env->isObject() && env->get("seconds") != nullptr;
      const auto timed = [&](std::string_view k, std::optional<double>& into) {
        const Json* v = env->isObject() ? env->get(k) : nullptr;
        if (v && !(seconds && v->type == Json::Type::Null)) into = jsToNumber(v);
      };
      number("delay", p.delay); timed("attack", p.attack); number("attackMid", p.attackMid); number("decay", p.decay);
      number("decayMid", p.decayMid); number("sustain", p.sustain); timed("release", p.release);
      number("releaseMid", p.releaseMid); number("seconds", p.seconds); number("inSeconds", p.inSeconds);
      number("outSeconds", p.outSeconds); number("inMid", p.inMid); number("outMid", p.outMid);
      if (const Json* v = env->isObject() ? env->get("restart") : nullptr) p.restart = v->type == Json::Type::Bool && v->b;
      if (const Json* v = env->isObject() ? env->get("loop") : nullptr) p.loop = v->type == Json::Type::Bool && v->b;
    }
    matrix.setFadeEnvelope(p, i);
  }
}

// --- the morph ----------------------------------------------------------------------------

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
    // The page writes String(want) into the slider; the number is what that text reads back as.
    b.panel.setRangeNumber(id, want);
    if (b.panel.range(id) != before) sliderInput(id, b, gen, keys, lfos);
  }
}

// The fader as a destination the matrix moves. The macros were sources here
// until P8d, and the threshold and the pluck it struck until P5.
class BrainSources {
 public:
  BrainSources(Matrix& matrix, Brain& b) {
    ModDest d;
    d.id = "morph.pos"; d.kind = DestKind::Visual; d.span = 1; d.min = 0; d.max = 1;
    Brain* brain = &b;
    d.base = [brain] { return brain->morphPos; };
    d.set = [brain](double offset) { brain->morphMod = offset; };
    matrix.registerDest(std::move(d));
  }
  BrainSources(const BrainSources&) = delete;
  BrainSources& operator=(const BrainSources&) = delete;
};

}  // namespace scope
