// The setup as the page keeps it: one flat object of every control in its own
// units, `DEFAULTS` for a page just opened, and the setup code that carries
// what differs from them - `encodeSetup`, `decodeSetup` and the migrations
// that bring an old code up to date (`migrateSetup`). Ported from
// web/scope.html and held to the page's own functions, code for code, by
// core/tests/parity.py.
//
// The setup is a `Json` object rather than a struct, because that is what the
// page's is, and what a code holds: a code can carry a field from a later
// version, a field of the wrong type, or no field at all, and the page keeps
// each as it is given. What a field MEANS is `restore`'s business, which is
// the next piece of the port.
//
// `DEFAULTS` is written out below as the page evaluates it, and the parity
// harness holds it to the page key for key and value for value, so a default
// changed on the page and not here is a failure rather than a drift.
//
// The migrations read old codes with JavaScript's coercions, because an old
// code is whatever an old page wrote and a hand can have edited it since: a
// trigger lane given as "1" or [1] reads as lane one, a full scale given as
// "3" reads as the fourth detent, and a level given as text multiplies as a
// number. The page's script is strict, so a code that decodes to a bare
// number, string or `true` throws when the migration stamps its version on
// it; `decodeSetup` says so rather than inventing a setup. Two corners are
// not followed: a full-scale field naming a method of Array.prototype other
// than `length` (the page would read a function), and the key `__proto__`.

#pragma once

#include <cmath>
#include <optional>
#include <string>
#include <string_view>

#include "scope/json.h"

namespace scope {

constexpr int kSetupVersion = 4;  // SETUP_VERSION
constexpr double kFullScaleDb[9] = { 0, -3, -6, -12, -18, -24, -30, -40, -50 };  // FULL_SCALE_DB

inline const Json& setupDefaults() {
  static const Json defaults = *jsonParse(utf8To16(R"json({
  "gen":"wave","shape":"harmonic","bars":"008740000","morph":150,"width":25,"table":150,"freq":220,
  "amp":55,"interval":0,"just":true,"phase":90,"figure":"Circle","detail":5,"figureRate":40,
  "figText":"HELLO","figPath":"","figDrawn":"","swingRate":21,"decay":12,"detune":40,"swingDrive":0,
  "inputMode":0,"inputDepth":50,"inputFrom":"live","gen2Figure":"Circle","gen2Rate":110,"cycle":"",
  "atk":8,"dec":120,"sus":70,"rel":180,"glide":0,"model":"Cube","spinX":11,"spinY":17,"spinZ":0,
  "spinRate":100,"depth":45,"l0d":"none","l0s":"sine","l0r":20,"l0a":50,"l1d":"none","l1s":"sine",
  "l1r":50,"l1a":30,"l0y":"","l1y":"","keyRoot":0,"keyScale":"chromatic","quant":false,"qGlide":0,
  "bpm":120,"crossOn":false,"crossX":0,"crossY":0,"crossNoteX":60,"crossNoteY":67,"crossDecay":180,
  "crossLevel":40,"scoreOn":false,"scoreStep":"1/16","scoreVoices":2,"scoreLow":48,"scoreOctaves":3,
  "arpMode":"off","arpRate":"1/8","arpOctaves":1,"threshWatch":"env.live","threshLevel":50,
  "pluckNote":60,"mac1":0,"mac2":0,"mac3":0,"mac4":0,"macroNames":"","morphA":"","morphB":"",
  "morphPos":0,"mod":"","display":"yt","persistence":"0","span":"5","zoom":0,"timebase":4,"level":0,
  "edge":"rising","trig":0,"position":10,"holdoff":0,"trigMode":"auto","c0on":true,"c0ac":false,"c0s":0,
  "c0o":0,"c1on":true,"c1ac":false,"c1s":0,"c1o":0,"midSide":false,"acHz":100,"octaves":0,
  "midiMode":"dyad","midiHold":false,"midiTruth":true,"midiFollow":false,"midiDrawCount":2,
  "midiDrawWhich":"outer","midiPolyJust":false,"midiDrawCountB":2,"midiDrawWhichB":"outer",
  "layers":"off","splitAt":60,"layerPair":"each","photoOn":false,"photoU":0.75,"photoV":0.5,
  "midiDrive":"wave,harmonograph,figure","cc":"","midiPlay":"","ring":600,"planeMirror":0,
  "planeLimit":0,"planeRadius":40,"planeOS":2,"planeTwist":0,"planeKaleido":0,"planeSnap":0,
  "planeScaleX":100,"planeScaleY":100,"planeShear":0,"delayMix":0,"delayMs":375,"delaySync":"",
  "delayFeedback":35,"delayPingPong":false,"oscRatio":1,"oscFm":0,"oscRing":0,"oscSync":100,"oscSub":0,
  "oscSubOct":1,"oscSubShape":"square","oscUnison":1,"oscSpread":12,"shpDrive":0,"shpFold":0,
  "shpBits":0,"shpRate":0,"shpOS":2,"vcfType":0,"vcfCut":667,"vcfRes":0,"vcfTrack":0,"vcfEnvAmt":0,
  "vcfAtk":5,"vcfDec":300,"vcfSus":30,"vcfRel":300,"chorusMix":0,"chorusRate":60,"chorusDepth":30,
  "chorusTime":120,"chorusFeedback":0,"lagOn":false,"lagMs":5,"lagAuto":true,"rotate":0,"lagMix":20,
  "fOn":false,"fType":"lowpass","fCut":566,"fRes":0,"fSee":"post","fHear":"pre","mSee":"pre","xy0":0,
  "xy1":1,"pGoni":true,"pSpec":true,"pHarm":false,"pTune":false,"cursors":false,"beam":"moderate",
  "beamXY":true,"beamYT":false,"beamGoni":false
})json"));
  return defaults;
}

// --- JavaScript's coercions, for the migrations ---------------------------------

// StringToNumber: JavaScript's white space trimmed, nothing is nought, the
// infinities by name, hex, octal and binary integers, or a decimal literal.
inline double jsStringToNumber(const std::u16string& raw) {
  const std::u16string s = jsTrim(raw);
  if (s.empty()) return 0;
  if (s == u"Infinity" || s == u"+Infinity") return HUGE_VAL;
  if (s == u"-Infinity") return -HUGE_VAL;
  if (s.size() > 2 && s[0] == u'0') {
    int base = s[1] == u'x' || s[1] == u'X' ? 16 : s[1] == u'o' || s[1] == u'O' ? 8 : s[1] == u'b' || s[1] == u'B' ? 2 : 0;
    if (base) {
      double v = 0;
      for (std::size_t i = 2; i < s.size(); i++) {
        const char16_t c = s[i];
        const int d = c >= u'0' && c <= u'9' ? c - u'0' : c >= u'a' && c <= u'f' ? c - u'a' + 10 : c >= u'A' && c <= u'F' ? c - u'A' + 10 : 99;
        if (d >= base) return NAN;
        v = v * base + d;
      }
      return v;
    }
  }
  std::size_t i = 0;
  if (s[i] == u'+' || s[i] == u'-') i++;
  std::size_t digits = 0;
  while (i < s.size() && s[i] >= u'0' && s[i] <= u'9') { i++; digits++; }
  if (i < s.size() && s[i] == u'.') {
    i++;
    while (i < s.size() && s[i] >= u'0' && s[i] <= u'9') { i++; digits++; }
  }
  if (digits == 0) return NAN;
  if (i < s.size() && (s[i] == u'e' || s[i] == u'E')) {
    i++;
    if (i < s.size() && (s[i] == u'+' || s[i] == u'-')) i++;
    std::size_t exp = 0;
    while (i < s.size() && s[i] >= u'0' && s[i] <= u'9') { i++; exp++; }
    if (exp == 0) return NAN;
  }
  if (i != s.size()) return NAN;
  return std::strtod(toAscii(s).c_str(), nullptr);
}

// ToString, for the values JSON can hold: an array joined with commas (a
// null in it as nothing), any other object "[object Object]".
inline std::u16string jsToString(const Json& v) {
  switch (v.type) {
    case Json::Type::Null: return u"null";
    case Json::Type::Bool: return v.b ? u"true" : u"false";
    case Json::Type::Number: return toU16(jsNumberToString(v.n));
    case Json::Type::String: return v.s;
    case Json::Type::Array: {
      std::u16string out;
      for (std::size_t i = 0; i < v.a.size(); i++) {
        if (i) out += u',';
        if (v.a[i].type != Json::Type::Null) out += jsToString(v.a[i]);
      }
      return out;
    }
    case Json::Type::Object: return u"[object Object]";
  }
  return u"";
}

// ToNumber, through ToPrimitive for an array or an object; nothing at all
// (a missing field) is NaN.
inline double jsToNumber(const Json* v) {
  if (!v) return NAN;
  switch (v->type) {
    case Json::Type::Null: return 0;
    case Json::Type::Bool: return v->b ? 1 : 0;
    case Json::Type::Number: return v->n;
    case Json::Type::String: return jsStringToNumber(v->s);
    default: return jsStringToNumber(jsToString(*v));
  }
}

// FULL_SCALE_DB[key]: a detent by its index as a property key, its length by
// name, and nothing for anything else.
inline std::optional<double> fullScaleAt(const Json* key) {
  if (!key) return std::nullopt;
  const std::u16string k = jsToString(*key);
  if (k == u"length") return 9.0;
  if (k.size() == 1 && k[0] >= u'0' && k[0] <= u'8') return kFullScaleDb[k[0] - u'0'];
  return std::nullopt;
}

inline double jsMax(double a, double b) { return std::isnan(a) || std::isnan(b) ? NAN : (a > b ? a : b); }
inline double jsMin(double a, double b) { return std::isnan(a) || std::isnan(b) ? NAN : (a < b ? a : b); }
inline double jsMathRound(double x) {
  if (!std::isfinite(x)) return x;
  const double r = std::floor(x);
  return x - r >= 0.5 ? r + 1 : r;
}

// --- the code -----------------------------------------------------------------------

// encodeSetup: what differs from the defaults, stamped with the version, as
// base64 without its padding. Nothing for a setup with a unit past 0xFF in
// it, where the browser's `btoa` throws.
inline std::optional<std::string> encodeSetup(const Json& snap) {
  const Json& defaults = setupDefaults();
  Json diff = Json::object();
  diff.set("v", Json::number(kSetupVersion));
  for (const auto& [key, value] : snap.o) {
    const Json* d = defaults.get(key);
    if (!d || !strictEquals(value, *d)) diff.set(key, value);
  }
  auto code = btoa(jsonStringify(diff));
  if (!code) return std::nullopt;
  while (!code->empty() && code->back() == '=') code->pop_back();
  return code;
}

// migrateSetup, in the page's order - each pass reads the field as the
// version before it wrote it. False where the page would throw.
inline bool migrateSetup(Json& setup) {
  const bool falsy = setup.type == Json::Type::Null || (setup.type == Json::Type::Bool && !setup.b)
                  || (setup.type == Json::Type::Number && (setup.n == 0 || std::isnan(setup.n)))
                  || (setup.type == Json::Type::String && setup.s.empty());
  if (falsy) return true;
  const bool object = setup.type == Json::Type::Object || setup.type == Json::Type::Array;
  const Json* none = nullptr;
  const auto field = [&](std::string_view k) { return setup.type == Json::Type::Object ? setup.get(k) : none; };
  const double v = jsToNumber(field("v"));
  if (v >= kSetupVersion) return true;
  if (!object) return false;  // the stamp below, on a primitive, in strict mode

  // 1 -> 2: the trigger level, an amplitude then, a fraction of full scale now.
  if (!(v >= 2)) {
    const Json* given = field("trig");
    const Json lane = given ? *given : *setupDefaults().get("trig");
    const std::u16string key = u"c" + jsToString(lane) + u"s";
    const Json* stored = setup.type == Json::Type::Object ? setup.get(key) : nullptr;
    const Json storedValue = stored ? *stored : Json::number(0);
    const bool onDetent = jsToNumber(&lane) <= 1 && fullScaleAt(&storedValue).has_value();
    const Json index = onDetent ? storedValue : Json::number(0);
    const double gain = std::pow(10.0, -*fullScaleAt(&index) / 20);
    const Json* level = field("level");
    if (level && gain != 1) {
      setup.set("level", Json::number(jsMax(-1000, jsMin(1000, jsMathRound(jsToNumber(level) * gain)))));
    }
  }
  // 2 -> 3: full scale, a position in the table then, decibels now.
  if (!(v >= 3)) {
    for (const char* key : { "c0s", "c1s" }) {
      const Json* stored = field(key);
      if (!stored) continue;
      const auto db = fullScaleAt(stored);
      setup.set(key, Json::number(db ? *db : 0));
    }
  }
  // 3 -> 4: the radial clip's yes or no became the limit's nought, one or two.
  if (!(v >= 4)) {
    const Json* clip = field("planeClip");
    if (clip && clip->type == Json::Type::Bool && clip->b) setup.set("planeLimit", Json::number(1));
    if (setup.type == Json::Type::Object) setup.erase("planeClip");
  }
  if (setup.type == Json::Type::Object) setup.set("v", Json::number(kSetupVersion));
  return true;
}

// decodeSetup: nothing for a code that does not read, `throws` for one the
// page's migration throws on, and otherwise the setup brought up to date.
struct DecodedSetup {
  enum class Kind { Unreadable, Throws, Read } kind = Kind::Unreadable;
  Json setup;
};
inline DecodedSetup decodeSetup(std::string_view code) {
  DecodedSetup out;
  const auto text = atob(jsTrim(utf8To16(code)));
  if (!text) return out;
  auto parsed = jsonParse(*text);
  if (!parsed) return out;
  // A code that reads as null is one the page cannot load: its decode hands
  // back null, which is what it says for a code that does not read at all.
  if (parsed->type == Json::Type::Null) return out;
  out.setup = std::move(*parsed);
  out.kind = migrateSetup(out.setup) ? DecodedSetup::Kind::Read : DecodedSetup::Kind::Throws;
  return out;
}

}  // namespace scope
