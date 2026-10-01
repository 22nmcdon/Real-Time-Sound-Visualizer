// JSON and base64 as a browser has them, for setup codes: a code is
// `btoa(JSON.stringify(diff))`, and the core has to write the same characters
// for the same setup and read the same setup out of the same characters, or a
// code shared from the site plays something else in the plugin.
//
// What that takes, each the way V8 does it:
//
// - Strings are UTF-16, as JavaScript's are, so a lone surrogate or a
//   character past the first plane is handled unit by unit as the page does.
// - A number is printed as `Number.prototype.toString` prints it: the
//   shortest digits that read back to the same double, then placed by the
//   specification's rules (plain up to 1e21, an exponent past it, "0.000001"
//   but "1e-7"), and minus nought as "0". Not `%g`, not `%.17g`.
// - An object keeps its keys in the order they arrived, except that keys
//   which are array indices ("0", "7", not "07") come first, in ascending
//   order, as V8 orders them. A key given twice keeps its first place and its
//   last value.
// - `JSON.parse` is strict JSON; `JSON.stringify` escapes what the
//   well-formed specification escapes (quote, backslash, the C0 controls,
//   lone surrogates) and nothing else.
// - `btoa` takes only units up to 0xFF and fails otherwise, as the browser
//   throws; `atob` is the forgiving decode - ASCII whitespace dropped, padding
//   optional, a length of one past a multiple of four refused. Its output is a
//   string of units 0 to 255, which JSON reads as Latin-1, not UTF-8.
//
// One thing is not followed: a key "__proto__" given to `encodeSetup` as an
// object would set the page's prototype rather than a key. Nothing the page
// writes has one.

#pragma once

#include <charconv>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <optional>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace scope {

// --- Number.prototype.toString ------------------------------------------------

inline std::string jsNumberToString(double x) {
  if (std::isnan(x)) return "NaN";
  if (std::isinf(x)) return x < 0 ? "-Infinity" : "Infinity";
  if (x == 0) return "0";
  std::string sign = x < 0 ? "-" : "";
  char buf[64];
  const auto res = std::to_chars(buf, buf + sizeof buf, std::fabs(x), std::chars_format::scientific);
  const std::string sci(buf, res.ptr);  // d.ddde+NN, the shortest that reads back
  const std::size_t e = sci.find('e');
  std::string digits = sci.substr(0, 1) + (e > 2 ? sci.substr(2, e - 2) : "");
  const int exp10 = std::atoi(sci.c_str() + e + 1);
  const int k = static_cast<int>(digits.size()), n = exp10 + 1;  // value = 0.digits x 10^n
  std::string out;
  if (k <= n && n <= 21) out = digits + std::string(static_cast<std::size_t>(n - k), '0');
  else if (0 < n && n <= 21) out = digits.substr(0, static_cast<std::size_t>(n)) + "." + digits.substr(static_cast<std::size_t>(n));
  else if (-6 < n && n <= 0) out = "0." + std::string(static_cast<std::size_t>(-n), '0') + digits;
  else {
    const int shown = n - 1;
    out = digits.substr(0, 1) + (k > 1 ? "." + digits.substr(1) : "") + "e" + (shown < 0 ? "-" : "+")
        + std::to_string(shown < 0 ? -shown : shown);
  }
  return sign + out;
}

// --- strings ---------------------------------------------------------------------

inline std::u16string toU16(std::string_view s) { return std::u16string(s.begin(), s.end()); }  // ASCII only
inline std::string toAscii(const std::u16string& s) {
  std::string out;
  for (const char16_t c : s) out += static_cast<char>(c);
  return out;
}
// UTF-8 to UTF-16; a malformed byte is taken as its own unit, as Latin-1.
inline std::u16string utf8To16(std::string_view s) {
  std::u16string out;
  for (std::size_t i = 0; i < s.size();) {
    const auto c = static_cast<unsigned char>(s[i]);
    std::uint32_t cp = c;
    std::size_t len = 1;
    if (c >= 0xF0 && i + 3 < s.size()) {
      cp = ((c & 0x07u) << 18) | ((static_cast<unsigned char>(s[i + 1]) & 0x3Fu) << 12)
         | ((static_cast<unsigned char>(s[i + 2]) & 0x3Fu) << 6) | (static_cast<unsigned char>(s[i + 3]) & 0x3Fu);
      len = 4;
    } else if (c >= 0xE0 && i + 2 < s.size()) {
      cp = ((c & 0x0Fu) << 12) | ((static_cast<unsigned char>(s[i + 1]) & 0x3Fu) << 6) | (static_cast<unsigned char>(s[i + 2]) & 0x3Fu);
      len = 3;
    } else if (c >= 0xC0 && i + 1 < s.size()) {
      cp = ((c & 0x1Fu) << 6) | (static_cast<unsigned char>(s[i + 1]) & 0x3Fu);
      len = 2;
    }
    if (cp >= 0x10000) {
      cp -= 0x10000;
      out += static_cast<char16_t>(0xD800 + (cp >> 10));
      out += static_cast<char16_t>(0xDC00 + (cp & 0x3FF));
    } else out += static_cast<char16_t>(cp);
    i += len;
  }
  return out;
}
// UTF-16 to UTF-8, a lone surrogate written as its own three bytes (WTF-8).
inline std::string utf16To8(const std::u16string& s) {
  std::string out;
  for (std::size_t i = 0; i < s.size(); i++) {
    std::uint32_t cp = s[i];
    if (cp >= 0xD800 && cp < 0xDC00 && i + 1 < s.size() && s[i + 1] >= 0xDC00 && s[i + 1] < 0xE000) {
      cp = 0x10000 + ((cp - 0xD800) << 10) + (s[i + 1] - 0xDC00u);
      i++;
    }
    if (cp < 0x80) out += static_cast<char>(cp);
    else if (cp < 0x800) { out += static_cast<char>(0xC0 | (cp >> 6)); out += static_cast<char>(0x80 | (cp & 0x3F)); }
    else if (cp < 0x10000) {
      out += static_cast<char>(0xE0 | (cp >> 12)); out += static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
      out += static_cast<char>(0x80 | (cp & 0x3F));
    } else {
      out += static_cast<char>(0xF0 | (cp >> 18)); out += static_cast<char>(0x80 | ((cp >> 12) & 0x3F));
      out += static_cast<char>(0x80 | ((cp >> 6) & 0x3F)); out += static_cast<char>(0x80 | (cp & 0x3F));
    }
  }
  return out;
}

// String.prototype.trim: JavaScript's white space and line terminators.
inline bool jsSpace(char16_t c) {
  return c == 0x09 || c == 0x0A || c == 0x0B || c == 0x0C || c == 0x0D || c == 0x20 || c == 0xA0 || c == 0x1680
      || (c >= 0x2000 && c <= 0x200A) || c == 0x2028 || c == 0x2029 || c == 0x202F || c == 0x205F || c == 0x3000
      || c == 0xFEFF;
}
inline std::u16string jsTrim(const std::u16string& s) {
  std::size_t a = 0, b = s.size();
  while (a < b && jsSpace(s[a])) a++;
  while (b > a && jsSpace(s[b - 1])) b--;
  return s.substr(a, b - a);
}

// --- the value ----------------------------------------------------------------------

struct Json {
  enum class Type { Null, Bool, Number, String, Array, Object };
  Type type = Type::Null;
  bool b = false;
  double n = 0;
  std::u16string s;
  std::vector<Json> a;
  std::vector<std::pair<std::u16string, Json>> o;

  static Json null() { return {}; }
  static Json boolean(bool v) { Json j; j.type = Type::Bool; j.b = v; return j; }
  static Json number(double v) { Json j; j.type = Type::Number; j.n = v; return j; }
  static Json string(std::u16string v) { Json j; j.type = Type::String; j.s = std::move(v); return j; }
  static Json string(std::string_view utf8) { return string(utf8To16(utf8)); }
  static Json object() { Json j; j.type = Type::Object; return j; }
  static Json array() { Json j; j.type = Type::Array; return j; }

  bool isObject() const { return type == Type::Object; }

  // An array index, as V8 orders keys: a canonical integer below 2^32 - 1.
  static bool isIndex(const std::u16string& k) {
    if (k.empty() || k.size() > 10) return false;
    if (k.size() > 1 && k[0] == u'0') return false;
    std::uint64_t v = 0;
    for (const char16_t c : k) {
      if (c < u'0' || c > u'9') return false;
      v = v * 10 + static_cast<std::uint64_t>(c - u'0');
    }
    return v < 4294967295ull;
  }
  static std::uint64_t indexOf(const std::u16string& k) {
    std::uint64_t v = 0;
    for (const char16_t c : k) v = v * 10 + static_cast<std::uint64_t>(c - u'0');
    return v;
  }

  const Json* get(const std::u16string& key) const {
    for (const auto& kv : o) if (kv.first == key) return &kv.second;
    return nullptr;
  }
  const Json* get(std::string_view key) const { return get(toU16(key)); }
  void set(const std::u16string& key, Json value) {
    for (auto& kv : o) if (kv.first == key) { kv.second = std::move(value); return; }
    if (isIndex(key)) {
      const std::uint64_t at = indexOf(key);
      std::size_t i = 0;
      while (i < o.size() && isIndex(o[i].first) && indexOf(o[i].first) < at) i++;
      o.insert(o.begin() + static_cast<std::ptrdiff_t>(i), { key, std::move(value) });
      return;
    }
    o.emplace_back(key, std::move(value));
  }
  void set(std::string_view key, Json value) { set(toU16(key), std::move(value)); }
  void erase(const std::u16string& key) {
    for (auto it = o.begin(); it != o.end(); ++it) if (it->first == key) { o.erase(it); return; }
  }
  void erase(std::string_view key) { erase(toU16(key)); }
};

// JavaScript's strict equality, for the scalar values a setup holds.
inline bool strictEquals(const Json& x, const Json& y) {
  if (x.type != y.type) return false;
  switch (x.type) {
    case Json::Type::Null: return true;
    case Json::Type::Bool: return x.b == y.b;
    case Json::Type::Number: return x.n == y.n;  // NaN is not itself; -0 is 0
    case Json::Type::String: return x.s == y.s;
    default: return false;  // two objects are never the same object here
  }
}

// --- JSON.stringify -------------------------------------------------------------------

inline void stringifyString(const std::u16string& s, std::u16string& out) {
  static const char* hex = "0123456789abcdef";
  out += u'"';
  for (std::size_t i = 0; i < s.size(); i++) {
    const char16_t c = s[i];
    if (c == u'"') out += u"\\\"";
    else if (c == u'\\') out += u"\\\\";
    else if (c == 0x08) out += u"\\b";
    else if (c == 0x0C) out += u"\\f";
    else if (c == 0x0A) out += u"\\n";
    else if (c == 0x0D) out += u"\\r";
    else if (c == 0x09) out += u"\\t";
    else {
      bool lone = false;
      if (c >= 0xD800 && c < 0xDC00) lone = !(i + 1 < s.size() && s[i + 1] >= 0xDC00 && s[i + 1] < 0xE000);
      else if (c >= 0xDC00 && c < 0xE000) lone = !(i > 0 && s[i - 1] >= 0xD800 && s[i - 1] < 0xDC00);
      if (c < 0x20 || lone) {
        out += u"\\u";
        for (int sh = 12; sh >= 0; sh -= 4) out += static_cast<char16_t>(hex[(c >> sh) & 0xF]);
      } else out += c;
    }
  }
  out += u'"';
}

inline void stringifyInto(const Json& v, std::u16string& out) {
  switch (v.type) {
    case Json::Type::Null: out += u"null"; break;
    case Json::Type::Bool: out += v.b ? u"true" : u"false"; break;
    case Json::Type::Number: out += std::isfinite(v.n) ? toU16(jsNumberToString(v.n)) : u"null"; break;
    case Json::Type::String: stringifyString(v.s, out); break;
    case Json::Type::Array:
      out += u'[';
      for (std::size_t i = 0; i < v.a.size(); i++) { if (i) out += u','; stringifyInto(v.a[i], out); }
      out += u']';
      break;
    case Json::Type::Object:
      out += u'{';
      for (std::size_t i = 0; i < v.o.size(); i++) {
        if (i) out += u',';
        stringifyString(v.o[i].first, out);
        out += u':';
        stringifyInto(v.o[i].second, out);
      }
      out += u'}';
      break;
  }
}
inline std::u16string jsonStringify(const Json& v) { std::u16string out; stringifyInto(v, out); return out; }

// --- JSON.parse --------------------------------------------------------------------------

class JsonParser {
 public:
  explicit JsonParser(const std::u16string& text) : t_(text) {}
  std::optional<Json> parse() {
    Json v;
    space();
    if (!value(v, 0)) return std::nullopt;
    space();
    if (i_ != t_.size()) return std::nullopt;
    return v;
  }

 private:
  void space() { while (i_ < t_.size() && (t_[i_] == u' ' || t_[i_] == u'\t' || t_[i_] == u'\n' || t_[i_] == u'\r')) i_++; }
  bool literal(const char16_t* word) {
    std::size_t j = 0;
    while (word[j]) { if (i_ + j >= t_.size() || t_[i_ + j] != word[j]) return false; j++; }
    i_ += j;
    return true;
  }
  static int hexDigit(char16_t c) {
    if (c >= u'0' && c <= u'9') return c - u'0';
    if (c >= u'a' && c <= u'f') return c - u'a' + 10;
    if (c >= u'A' && c <= u'F') return c - u'A' + 10;
    return -1;
  }
  bool string(std::u16string& out) {
    if (i_ >= t_.size() || t_[i_] != u'"') return false;
    i_++;
    while (i_ < t_.size()) {
      const char16_t c = t_[i_++];
      if (c == u'"') return true;
      if (c < 0x20) return false;
      if (c != u'\\') { out += c; continue; }
      if (i_ >= t_.size()) return false;
      const char16_t e = t_[i_++];
      if (e == u'"' || e == u'\\' || e == u'/') out += e;
      else if (e == u'b') out += 0x08;
      else if (e == u'f') out += 0x0C;
      else if (e == u'n') out += 0x0A;
      else if (e == u'r') out += 0x0D;
      else if (e == u't') out += 0x09;
      else if (e == u'u') {
        if (i_ + 4 > t_.size()) return false;
        int v = 0;
        for (int k = 0; k < 4; k++) { const int d = hexDigit(t_[i_ + static_cast<std::size_t>(k)]); if (d < 0) return false; v = v * 16 + d; }
        i_ += 4;
        out += static_cast<char16_t>(v);
      } else return false;
    }
    return false;
  }
  bool number(Json& v) {
    const std::size_t start = i_;
    if (i_ < t_.size() && t_[i_] == u'-') i_++;
    if (i_ >= t_.size()) return false;
    if (t_[i_] == u'0') i_++;
    else if (t_[i_] >= u'1' && t_[i_] <= u'9') { while (i_ < t_.size() && t_[i_] >= u'0' && t_[i_] <= u'9') i_++; }
    else return false;
    if (i_ < t_.size() && t_[i_] == u'.') {
      i_++;
      if (i_ >= t_.size() || t_[i_] < u'0' || t_[i_] > u'9') return false;
      while (i_ < t_.size() && t_[i_] >= u'0' && t_[i_] <= u'9') i_++;
    }
    if (i_ < t_.size() && (t_[i_] == u'e' || t_[i_] == u'E')) {
      i_++;
      if (i_ < t_.size() && (t_[i_] == u'+' || t_[i_] == u'-')) i_++;
      if (i_ >= t_.size() || t_[i_] < u'0' || t_[i_] > u'9') return false;
      while (i_ < t_.size() && t_[i_] >= u'0' && t_[i_] <= u'9') i_++;
    }
    const std::string text = toAscii(t_.substr(start, i_ - start));
    v = Json::number(std::strtod(text.c_str(), nullptr));
    return true;
  }
  bool value(Json& v, int depth) {
    if (depth > 512 || i_ >= t_.size()) return false;
    const char16_t c = t_[i_];
    if (c == u'n') { if (!literal(u"null")) return false; v = Json::null(); return true; }
    if (c == u't') { if (!literal(u"true")) return false; v = Json::boolean(true); return true; }
    if (c == u'f') { if (!literal(u"false")) return false; v = Json::boolean(false); return true; }
    if (c == u'"') { std::u16string s; if (!string(s)) return false; v = Json::string(std::move(s)); return true; }
    if (c == u'[') {
      i_++;
      v = Json::array();
      space();
      if (i_ < t_.size() && t_[i_] == u']') { i_++; return true; }
      for (;;) {
        Json item;
        space();
        if (!value(item, depth + 1)) return false;
        v.a.push_back(std::move(item));
        space();
        if (i_ < t_.size() && t_[i_] == u',') { i_++; continue; }
        if (i_ < t_.size() && t_[i_] == u']') { i_++; return true; }
        return false;
      }
    }
    if (c == u'{') {
      i_++;
      v = Json::object();
      space();
      if (i_ < t_.size() && t_[i_] == u'}') { i_++; return true; }
      for (;;) {
        std::u16string key;
        space();
        if (!string(key)) return false;
        space();
        if (i_ >= t_.size() || t_[i_] != u':') return false;
        i_++;
        space();
        Json item;
        if (!value(item, depth + 1)) return false;
        v.set(key, std::move(item));
        space();
        if (i_ < t_.size() && t_[i_] == u',') { i_++; continue; }
        if (i_ < t_.size() && t_[i_] == u'}') { i_++; return true; }
        return false;
      }
    }
    return number(v);
  }

  const std::u16string& t_;
  std::size_t i_ = 0;
};
inline std::optional<Json> jsonParse(const std::u16string& text) { return JsonParser(text).parse(); }

// --- btoa and atob ------------------------------------------------------------------------

inline std::optional<std::string> btoa(const std::u16string& s) {
  static const char* alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  std::string out;
  for (const char16_t c : s) if (c > 0xFF) return std::nullopt;  // the browser throws
  for (std::size_t i = 0; i < s.size(); i += 3) {
    const std::uint32_t b0 = s[i], b1 = i + 1 < s.size() ? s[i + 1] : 0, b2 = i + 2 < s.size() ? s[i + 2] : 0;
    const std::uint32_t v = (b0 << 16) | (b1 << 8) | b2;
    out += alphabet[(v >> 18) & 63];
    out += alphabet[(v >> 12) & 63];
    out += i + 1 < s.size() ? alphabet[(v >> 6) & 63] : '=';
    out += i + 2 < s.size() ? alphabet[v & 63] : '=';
  }
  return out;
}

// The forgiving decode: units 0 to 255 out, or nothing for what atob refuses.
inline std::optional<std::u16string> atob(const std::u16string& in) {
  std::u16string s;
  for (const char16_t c : in) if (!(c == 0x09 || c == 0x0A || c == 0x0C || c == 0x0D || c == 0x20)) s += c;
  if (s.size() % 4 == 0 && !s.empty()) {
    if (s.back() == u'=') s.pop_back();
    if (!s.empty() && s.back() == u'=') s.pop_back();
  }
  if (s.size() % 4 == 1) return std::nullopt;
  const auto decode = [](char16_t c) -> int {
    if (c >= u'A' && c <= u'Z') return c - u'A';
    if (c >= u'a' && c <= u'z') return c - u'a' + 26;
    if (c >= u'0' && c <= u'9') return c - u'0' + 52;
    if (c == u'+') return 62;
    if (c == u'/') return 63;
    return -1;
  };
  std::u16string out;
  std::uint32_t buffer = 0;
  int bits = 0;
  for (const char16_t c : s) {
    const int d = decode(c);
    if (d < 0) return std::nullopt;
    buffer = (buffer << 6) | static_cast<std::uint32_t>(d);
    bits += 6;
    if (bits >= 8) {
      bits -= 8;
      out += static_cast<char16_t>((buffer >> bits) & 0xFF);
    }
  }
  return out;
}

}  // namespace scope
