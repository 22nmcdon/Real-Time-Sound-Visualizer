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
#include <cstdlib>
#include <optional>
#include <string>
#include <string_view>

#include "scope/json.h"
#include "scope/schema.h"

namespace scope {

constexpr int kSetupVersion = 10;  // SETUP_VERSION
constexpr double kFullScaleDb[9] = { 0, -3, -6, -12, -18, -24, -30, -40, -50 };  // FULL_SCALE_DB

// The table (schema.h, SETUP_FIELDS on the page), parsed once.
inline const Json& setupFields() {
  static const Json fields = [] {
    std::string text;
    for (const char* piece : kSetupFieldsPieces) text += piece;
    return *jsonParse(utf8To16(text));
  }();
  return fields;
}

// DEFAULTS: every field the table gives a default, in its order.
inline const Json& setupDefaults() {
  static const Json defaults = [] {
    Json d = Json::object();
    for (const auto& [key, row] : setupFields().o)
      if (row.a[0].type != Json::Type::Null) d.set(key, row.a[0]);
    return d;
  }();
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

// ToBoolean: false, nought, NaN, the empty string and null are false, and
// everything else - an array, an object, the string "false" - is true.
inline bool jsTruthy(const Json& v) {
  switch (v.type) {
    case Json::Type::Null: return false;
    case Json::Type::Bool: return v.b;
    case Json::Type::Number: return v.n != 0 && !std::isnan(v.n);
    case Json::Type::String: return !v.s.empty();
    default: return true;
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
// --- reading a field by its rule (the page's setupField and setupOwn) ------------

// The rule a field is read by; a twin's is its A field's.
inline const Json& setupRule(std::string_view key) {
  const Json& rule = setupFields().get(key)->a[1];
  if (rule.a[0].s == u"twin") return setupFields().get(rule.a[1].s)->a[1];
  return rule;
}

// Whether a rule takes a value: Array.includes for a menu (a number or a
// string, the same and equal), Number.isFinite(Number(v)) for a range, a
// boolean for a switch. A rule with no reading here is the caller's own.
inline bool setupTakes(const Json& rule, const Json* v) {
  const std::u16string& kind = rule.a[0].s;
  if (kind == u"menu") {
    if (!v) return false;
    for (const Json& x : rule.a[1].a)
      if (x.type == v->type && ((x.type == Json::Type::Number && x.n == v->n) || (x.type == Json::Type::String && x.s == v->s)))
        return true;
    return false;
  }
  if (kind == u"within") return std::isfinite(jsToNumber(v));
  if (kind == u"flag") return v && v->type == Json::Type::Bool;
  std::abort();
}

inline Json setupHeld(const Json& rule, const Json* v) {
  if (rule.a[0].s == u"within") return Json::number(std::fmax(rule.a[1].n, std::fmin(rule.a[2].n, jsToNumber(v))));
  return *v;
}

// The merged setup's value v for key, by its rule, or the default where the
// rule will not take it. A switch is on only for true, or off only for false
// where its default is on.
inline Json setupField(const Json* v, std::string_view key) {
  const Json& dflt = setupFields().get(key)->a[0];
  const Json& rule = setupRule(key);
  if (rule.a[0].s == u"flag") {
    const bool given = v && v->type == Json::Type::Bool;
    return Json::boolean(dflt.b ? !(given && !v->b) : (given && v->b));
  }
  return setupTakes(rule, v) ? setupHeld(rule, v) : dflt;
}

// Layer B's own, or nothing where it is missing or unusable: the caller then
// has A's value as it stands.
inline std::optional<Json> setupOwn(const Json* v, std::string_view key) {
  const Json& rule = setupRule(key);
  if (!setupTakes(rule, v)) return std::nullopt;
  return setupHeld(rule, v);
}

inline double jsMathRound(double x) {
  if (!std::isfinite(x)) return x;
  const double r = std::floor(x);
  return x - r >= 0.5 ? r + 1 : r;
}

// --- the code -----------------------------------------------------------------------

// encodeSetup: what differs from the defaults - and the Picture amount
// always, since a restore leaves an amount a setup does not name where it was,
// and a code saved at the default would otherwise not say it (the page's
// encodeSetupHere has why) - stamped with the version, as base64 without its
// padding. Nothing for a setup with a unit past 0xFF in it, where the
// browser's `btoa` throws.
inline std::optional<std::string> encodeSetup(const Json& snap) {
  const Json& defaults = setupDefaults();
  Json diff = Json::object();
  diff.set("v", Json::number(kSetupVersion));
  for (const auto& [key, value] : snap.o) {
    const Json* d = defaults.get(key);
    if (!d || !strictEquals(value, *d) || key == u"pictureAmount") diff.set(key, value);
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
  // 4 -> 5: crossings, the threshold and the pluck cut (P5) - their fields, and
  // any routing from the threshold or to the pluck, each other one as written.
  if (!(v >= 5) && setup.type == Json::Type::Object) {
    for (const char* key : { "crossOn", "crossX", "crossY", "crossNoteX", "crossNoteY", "crossDecay", "crossLevel",
                             "threshWatch", "threshLevel", "pluckNote" }) setup.erase(key);
    const Json* mod = field("mod");
    if (mod && mod->type == Json::Type::String && !mod->s.empty()) {
      const std::u16string& text = mod->s;
      std::u16string kept;
      bool first = true;
      std::size_t at = 0;
      while (true) {
        const std::size_t end = text.find(u';', at);
        const std::u16string part = text.substr(at, end == std::u16string::npos ? std::u16string::npos : end - at);
        const std::u16string p = jsTrim(part);
        const bool fromThreshold = p.rfind(u"threshold>", 0) == 0;
        const bool toPluck = p.find(u">gen.pluck@") != std::u16string::npos;
        if (!fromThreshold && !toPluck) { if (!first) kept += u';'; kept += part; first = false; }
        if (end == std::u16string::npos) break;
        at = end + 1;
      }
      setup.set("mod", Json::string(kept));
    }
  }
  // 5 -> 6: the macros cut (P8d) - their values and names, and every routing
  // from one; nothing moved a macro, so none to one. The rest as written.
  if (!(v >= 6) && setup.type == Json::Type::Object) {
    for (const char* key : { "mac1", "mac2", "mac3", "mac4", "macroNames" }) setup.erase(key);
    const Json* mod = field("mod");
    if (mod && mod->type == Json::Type::String && !mod->s.empty()) {
      const std::u16string& text = mod->s;
      std::u16string kept;
      bool first = true;
      std::size_t at = 0;
      while (true) {
        const std::size_t end = text.find(u';', at);
        const std::u16string part = text.substr(at, end == std::u16string::npos ? std::u16string::npos : end - at);
        const std::u16string p = jsTrim(part);
        const bool fromMacro = p.size() >= 8 && p.compare(0, 6, u"macro.") == 0 && p[6] >= u'1' && p[6] <= u'4' && p[7] == u'>';
        if (!fromMacro) { if (!first) kept += u';'; kept += part; first = false; }
        if (end == std::u16string::npos) break;
        at = end + 1;
      }
      setup.set("mod", Json::string(kept));
    }
  }
  // 6 -> 7: the latch cut (P8h), a day after it was built - the sustain
  // pedal is told what an automatic latch had to guess. Its field goes.
  if (!(v >= 7) && setup.type == Json::Type::Object) setup.erase("midiLatch");
  // 7 -> 8: the kaleidoscope cut, and Snap below five bits (7 Nov): its
  // fields go, and a snap of one to four bits is five, the coarsest kept.
  if (!(v >= 8) && setup.type == Json::Type::Object) {
    setup.erase("planeKaleido");
    setup.erase("bKaleido");
    for (const char* key : { "planeSnap", "bSnap" }) {
      const Json* s = setup.get(key);
      if (s && s->type == Json::Type::Number && s->n >= 1 && s->n <= 4) setup.set(key, Json::number(5));
    }
  }
  // 8 -> 9: the matrix's sources cut to the modulation cards' and the parked
  // ones (F4b, 7 Nov): learned controllers, with the names a code kept for
  // them, and the keyboard's pedal, pressure and four readings of the notes,
  // and the level. Their routings go (the page's CUT_SOURCE); Key stays.
  if (!(v >= 9) && setup.type == Json::Type::Object) {
    setup.erase("cc");
    const Json* mod = field("mod");
    if (mod && mod->type == Json::Type::String && !mod->s.empty()) {
      const std::u16string& text = mod->s;
      std::u16string kept;
      bool first = true;
      std::size_t at = 0;
      const auto from = [](const std::u16string& p, const char16_t* id) {
        const std::u16string head = std::u16string(id) + u">";
        return p.compare(0, head.size(), head) == 0;
      };
      while (true) {
        const std::size_t end = text.find(u';', at);
        const std::u16string part = text.substr(at, end == std::u16string::npos ? std::u16string::npos : end - at);
        const std::u16string p = jsTrim(part);
        // cc. and one or more digits, then the arrow: /^cc\.\d+>/.
        std::size_t d = 3;
        while (d < p.size() && p[d] >= u'0' && p[d] <= u'9') d++;
        const bool fromController = p.size() > 4 && p.compare(0, 3, u"cc.") == 0 && d > 3 && d < p.size() && p[d] == u'>';
        const bool cutSource = fromController || from(p, u"midi.pedal") || from(p, u"midi.pressure")
          || from(p, u"notes.count") || from(p, u"notes.spread") || from(p, u"notes.top") || from(p, u"notes.inner")
          || from(p, u"env.live");
        if (!cutSource) { if (!first) kept += u';'; kept += part; first = false; }
        if (end == std::u16string::npos) break;
        at = end + 1;
      }
      setup.set("mod", Json::string(kept));
    }
  }
  // 9 -> 10: the drawings cut (G2, 9 Nov) - the harmonograph, the figures,
  // the solids and the second generator. A code that named one as its kind
  // loads as the waveform, their fields go, and so does every routing from
  // one of their sources or to one of their destinations (the page's pattern
  // beside CUT_SOURCE). Read as that pattern reads a routing: the source is
  // what comes before the first arrow, the destination what follows it up
  // to the next "@" - so a destination that only begins with one of these,
  // or a source that ends with one, is another and stays.
  if (!(v >= 10) && setup.type == Json::Type::Object) {
    // Anything but "wave", missing included, is the waveform: `setup.gen !== "wave"` on the page.
    const Json* gen = setup.get("gen");
    if (!(gen && gen->type == Json::Type::String && gen->s == u"wave")) setup.set("gen", Json::string(std::string_view("wave")));
    for (const char* key : { "figure", "detail", "figureRate", "figText", "figPath", "figDrawn", "swingRate", "decay",
                             "detune", "swingDrive", "inputFrom", "gen2Figure", "gen2Rate", "model", "spinX", "spinY",
                             "spinZ", "spinRate", "depth", "midiDrive", "midiPlay", "ring" }) setup.erase(key);
    const Json* mod = field("mod");
    if (mod && mod->type == Json::Type::String && !mod->s.empty()) {
      const std::u16string& text = mod->s;
      std::u16string kept;
      bool first = true;
      std::size_t at = 0;
      static const char16_t* const sources[] = { u"draw.swing", u"draw.pendulum", u"draw.turnX", u"draw.turnY",
                                                 u"draw.turnZ", u"draw.facing" };
      static const char16_t* const dests[] = { u"gen.detail", u"gen.tumble", u"gen.depth", u"gen.swing", u"gen.spinX",
                                               u"gen.spinY", u"gen.spinZ", u"gen.reswing", u"gen.kick" };
      while (true) {
        const std::size_t end = text.find(u';', at);
        const std::u16string part = text.substr(at, end == std::u16string::npos ? std::u16string::npos : end - at);
        const std::u16string p = jsTrim(part);
        const std::size_t arrow = p.find(u'>');
        bool cut = false;
        if (arrow != std::u16string::npos) {
          for (const char16_t* id : sources) cut = cut || p.compare(0, arrow, id) == 0;
          for (const char16_t* id : dests) {
            const std::u16string head = std::u16string(id) + u"@";
            cut = cut || p.compare(arrow + 1, head.size(), head) == 0;
          }
        }
        if (!cut) { if (!first) kept += u';'; kept += part; first = false; }
        if (end == std::u16string::npos) break;
        at = end + 1;
      }
      setup.set("mod", Json::string(kept));
    }
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
// The code as the page's string holds it, UTF-16 (stage 5e: the page hands
// its codes over as they are). A code is base64, so anything past Latin-1 in
// it makes it unreadable however it crosses; this saves the round trip.
inline DecodedSetup decodeSetup(const std::u16string& code) {
  DecodedSetup out;
  const auto text = atob(jsTrim(code));
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
inline DecodedSetup decodeSetup(std::string_view code) { return decodeSetup(utf8To16(code)); }

}  // namespace scope
