// The figures made of strokes, ported from web/scope.html: a word in the
// page's single-stroke font (`textStrokes`), an SVG path's `d` (`svgStrokes`),
// a drawing's text in a setup code (`decodeDrawn`, `encodeDrawn`), and the
// strokes compiled into what `figureAt` reads (`compilePath`).
//
// What differs from the page, and why, so nobody goes looking:
//
// - `textStrokes` upper-cases its text first, and JavaScript's upper case is
//   Unicode's: "ß" is "SS" and draws two letters, "ﬁ" draws F and I, and a
//   Greek letter with its accents can become three characters, each a space.
//   Only the count and the ASCII letters reach the font, so the port carries
//   the characters whose upper case is not one non-ASCII character - 104 of
//   them, written out from V8 - and leaves every other character as itself.
// - `svgStrokes` throws in the page and the panel says why; here it answers
//   the strokes or the same message.

#pragma once

#include <cmath>
#include <map>
#include <memory>
#include <optional>
#include <string>
#include <vector>

#include "scope/figures.h"
#include "scope/json.h"
#include "scope/setup.h"

namespace scope {

using Stroke = std::vector<std::array<double, 2>>;
using Strokes = std::vector<Stroke>;

constexpr double kTravelSpeed = 8;    // TRAVEL_SPEED
constexpr std::size_t kTextMost = 24;  // TEXT_MAX
constexpr std::size_t kPathPointsMost = 6000;
constexpr std::size_t kDrawnMost = 3000;

// STROKE_FONT: each glyph on a grid four wide and six tall, as pairs of digits
// x then y, strokes parted by a bar.
inline const char* strokeGlyph(char32_t c) {
  static const std::map<char32_t, const char*> font = {
    { 'A', "002640|1333" }, { 'B', "00063645443303|3342413000" }, { 'C', "4536160501103041" },
    { 'D', "00062644422000" }, { 'E', "46060040|0333" }, { 'F', "460600|0333" },
    { 'G', "45361605011030414323" }, { 'H', "0006|4640|0343" }, { 'I', "1636|2620|1030" },
    { 'J', "4641301001" }, { 'K', "0006|4602|1340" }, { 'L', "060040" }, { 'M', "0006234640" },
    { 'N', "00064046" }, { 'O', "103041453616050110" }, { 'P', "00063645443303" },
    { 'Q', "103041453616050110|2240" }, { 'R', "00063645443303|2340" },
    { 'S', "453616050413334241301001" }, { 'T', "0646|2620" }, { 'U', "060110304146" }, { 'V', "062046" },
    { 'W', "0610233046" }, { 'X', "0046|0640" }, { 'Y', "062346|2320" }, { 'Z', "06460040" },
    { '0', "103041453616050110|0145" }, { '1', "152620|1030" }, { '2', "05163645440040" },
    { '3', "051636454433|13334241301001" }, { '4', "30360242" }, { '5', "460603334241301001" },
    { '6', "453616050110304142331302" }, { '7', "064610" }, { '8', "13040516364544331302011030414233" },
    { '9', "443313040516364541301001" },
    { '.', "2021" }, { ',', "2110" }, { '!', "2623|2021" }, { '?', "05163645442322|2021" }, { '-', "1333" },
    { '+', "1333|2224" }, { '\'', "2625" }, { ':', "2425|2021" }, { '/', "0046" }, { '=', "0444|0242" }, { ' ', "" },
  };
  const auto at = font.find(c);
  return at == font.end() ? "" : at->second;
}

// The characters JavaScript's toUpperCase turns into ASCII letters, or into
// more than one character: each with what it becomes, a non-ASCII character
// written as 1, since all the font does with one is leave a space.
inline const std::map<char32_t, std::u32string>& upperSpecial() {
  static const std::map<char32_t, std::u32string> table = [] {
    std::map<char32_t, std::u32string> t = {
      { 0xDF, U"SS" }, { 0x131, U"I" }, { 0x149, U"\x01N" }, { 0x17F, U"S" }, { 0x1F0, U"J\x01" },
      { 0x1E96, U"H\x01" }, { 0x1E97, U"T\x01" }, { 0x1E98, U"W\x01" }, { 0x1E99, U"Y\x01" }, { 0x1E9A, U"A\x01" },
      { 0xFB00, U"FF" }, { 0xFB01, U"FI" }, { 0xFB02, U"FL" }, { 0xFB03, U"FFI" }, { 0xFB04, U"FFL" },
      { 0xFB05, U"ST" }, { 0xFB06, U"ST" },
    };
    // Those that become two or three characters none of which is ASCII.
    const std::pair<char32_t, int> longer[] = {
      { 0x390, 3 }, { 0x3B0, 3 }, { 0x587, 2 }, { 0x1F50, 2 }, { 0x1F52, 3 }, { 0x1F54, 3 }, { 0x1F56, 3 },
      { 0x1FB2, 2 }, { 0x1FB3, 2 }, { 0x1FB4, 2 }, { 0x1FB6, 2 }, { 0x1FB7, 3 }, { 0x1FBC, 2 }, { 0x1FC2, 2 },
      { 0x1FC3, 2 }, { 0x1FC4, 2 }, { 0x1FC6, 2 }, { 0x1FC7, 3 }, { 0x1FCC, 2 }, { 0x1FD2, 3 }, { 0x1FD3, 3 },
      { 0x1FD6, 2 }, { 0x1FD7, 3 }, { 0x1FE2, 3 }, { 0x1FE3, 3 }, { 0x1FE4, 2 }, { 0x1FE6, 2 }, { 0x1FE7, 3 },
      { 0x1FF2, 2 }, { 0x1FF3, 2 }, { 0x1FF4, 2 }, { 0x1FF6, 2 }, { 0x1FF7, 3 }, { 0x1FFC, 2 },
      { 0xFB13, 2 }, { 0xFB14, 2 }, { 0xFB15, 2 }, { 0xFB16, 2 }, { 0xFB17, 2 },
    };
    for (const auto& [c, n] : longer) t[c] = std::u32string(static_cast<std::size_t>(n), U'\x01');
    for (char32_t c = 0x1F80; c <= 0x1FAF; c++) t[c] = U"\x01\x01";  // Greek with a iota below: two
    return t;
  }();
  return table;
}

// Array.from(text.toUpperCase()): the code points of the upper case, a lone
// surrogate as itself.
inline std::u32string jsUpperCodePoints(const std::u16string& text) {
  std::u32string out;
  for (std::size_t i = 0; i < text.size(); i++) {
    char32_t c = text[i];
    if (c >= 0xD800 && c <= 0xDBFF && i + 1 < text.size() && text[i + 1] >= 0xDC00 && text[i + 1] <= 0xDFFF) {
      c = 0x10000 + ((c - 0xD800) << 10) + (text[i + 1] - 0xDC00);
      i++;
    }
    if (c >= 'a' && c <= 'z') { out += static_cast<char32_t>(c - 32); continue; }
    const auto& special = upperSpecial();
    const auto at = c >= 0x80 ? special.find(c) : special.end();
    if (at != special.end()) out += at->second;
    else out += c >= 0x80 ? U'\x01' : c;
  }
  return out;
}

// textStrokes: a word laid out on one line and scaled to the screen's width.
inline Strokes textStrokes(const std::u16string& text) {
  Strokes strokes;
  std::u32string chars = jsUpperCodePoints(text);
  if (chars.size() > kTextMost) chars.resize(kTextMost);
  const double width = static_cast<double>(chars.size()) * 6 - 2;
  if (width <= 0) return strokes;
  const double scale = 1.9 / std::fmax(width, 6);
  for (std::size_t k = 0; k < chars.size(); k++) {
    const std::string glyph = strokeGlyph(chars[k]);
    std::size_t from = 0;
    while (from <= glyph.size()) {
      const std::size_t bar = std::min(glyph.find('|', from), glyph.size());
      const std::string part = glyph.substr(from, bar - from);
      from = bar + 1;
      if (part.size() < 4) continue;
      Stroke stroke;
      for (std::size_t i = 0; i + 1 < part.size(); i += 2) {
        stroke.push_back({ (static_cast<double>(k) * 6 + (part[i] - '0') - width / 2) * scale,
                           ((part[i + 1] - '0') - 3) * scale });
      }
      strokes.push_back(stroke);
    }
  }
  return strokes;
}

// What svgStrokes answers: the strokes, or why not.
struct PathRead {
  std::optional<Strokes> strokes;
  std::string error;
};

// svgStrokes: every command in the specification, curves and arcs flattened
// into short lines, each subpath a stroke, fitted to the screen.
inline PathRead svgStrokes(const std::u16string& text) {
  struct Refused { std::string why; };
  const std::size_t n = text.size();
  std::size_t i = 0;
  const auto at = [&](std::size_t k) { return k < n ? text[k] : char16_t(0); };
  const auto digit = [](char16_t c) { return c >= '0' && c <= '9'; };
  const auto letter = [](char16_t c) { return (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z'); };
  const auto skip = [&] { while (i < n && (jsSpace(text[i]) || text[i] == ',')) i++; };
  const auto number = [&]() -> double {
    skip();
    // /^[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?/
    std::size_t k = i;
    if (at(k) == '+' || at(k) == '-') k++;
    std::size_t whole = 0;
    while (digit(at(k))) { k++; whole++; }
    if (whole) {
      if (at(k) == '.') { k++; while (digit(at(k))) k++; }
    } else {
      if (at(k) != '.' || !digit(at(k + 1))) throw Refused { "expected a number at character " + std::to_string(i) };
      k++;
      while (digit(at(k))) k++;
    }
    if (at(k) == 'e' || at(k) == 'E') {
      std::size_t e = k + 1;
      if (at(e) == '+' || at(e) == '-') e++;
      if (digit(at(e))) { while (digit(at(e))) e++; k = e; }
    }
    const double v = jsStringToNumber(text.substr(i, k - i));
    i = k;
    return v;
  };
  const auto flag = [&]() -> bool {
    skip();
    const char16_t c = at(i);
    if (i >= n || (c != '0' && c != '1')) throw Refused { "expected an arc flag at character " + std::to_string(i) };
    i++;
    return c == '1';
  };
  const auto more = [&] { skip(); return i < n && (text[i] == '-' || text[i] == '+' || text[i] == '.' || digit(text[i])); };

  Strokes strokes;
  try {
    bool open = false;  // whether `stroke` is the last of `strokes`
    double x = 0, y = 0, sx = 0, sy = 0;
    char16_t cmd = 0;
    std::optional<std::array<double, 2>> lastC, lastQ;
    const auto to = [&](double nx, double ny) {
      if (!open) { strokes.push_back({ { x, y } }); open = true; }
      strokes.back().push_back({ nx, ny });
      x = nx; y = ny;
    };
    constexpr int kSteps = 16;
    while (true) {
      skip();
      if (i >= n) break;
      if (letter(text[i])) cmd = text[i++];
      else if (!cmd) throw Refused { "a path starts with a command" };
      const bool rel = cmd >= 'a' && cmd <= 'z';
      const char16_t c = rel ? static_cast<char16_t>(cmd - 32) : cmd;
      const double ox = rel ? x : 0, oy = rel ? y : 0;
      if (c == 'Z') {
        if (open) to(sx, sy);
        open = false; lastC.reset(); lastQ.reset();
        if (more()) throw Refused { "unexpected character at " + std::to_string(i) };
        continue;
      }
      if (c == 'M') {
        x = number() + ox; y = number() + oy; sx = x; sy = y;
        strokes.push_back({ { x, y } }); open = true;
        cmd = rel ? u'l' : u'L';
        lastC.reset(); lastQ.reset();
        continue;
      }
      if (c == 'L') { const double nx = number() + ox; const double ny = number() + oy; to(nx, ny); lastC.reset(); lastQ.reset(); }
      else if (c == 'H') { to(number() + ox, y); lastC.reset(); lastQ.reset(); }
      else if (c == 'V') { to(x, number() + (rel ? y : 0)); lastC.reset(); lastQ.reset(); }
      else if (c == 'C' || c == 'S') {
        double x1, y1;
        if (c == 'C') { x1 = number() + ox; y1 = number() + oy; }
        else if (lastC) { x1 = 2 * x - (*lastC)[0]; y1 = 2 * y - (*lastC)[1]; }
        else { x1 = x; y1 = y; }
        const double x2 = number() + ox, y2 = number() + oy, ex = number() + ox, ey = number() + oy;
        const double x0 = x, y0 = y;
        for (int k = 1; k <= kSteps; k++) {
          const double t = static_cast<double>(k) / kSteps, u = 1 - t;
          to(u * u * u * x0 + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t * t * t * ex,
             u * u * u * y0 + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t * t * t * ey);
        }
        lastC = std::array<double, 2> { x2, y2 }; lastQ.reset();
      } else if (c == 'Q' || c == 'T') {
        double x1, y1;
        if (c == 'Q') { x1 = number() + ox; y1 = number() + oy; }
        else if (lastQ) { x1 = 2 * x - (*lastQ)[0]; y1 = 2 * y - (*lastQ)[1]; }
        else { x1 = x; y1 = y; }
        const double ex = number() + ox, ey = number() + oy, x0 = x, y0 = y;
        for (int k = 1; k <= kSteps; k++) {
          const double t = static_cast<double>(k) / kSteps, u = 1 - t;
          to(u * u * x0 + 2 * u * t * x1 + t * t * ex, u * u * y0 + 2 * u * t * y1 + t * t * ey);
        }
        lastQ = std::array<double, 2> { x1, y1 }; lastC.reset();
      } else if (c == 'A') {
        double rx = std::fabs(number()), ry = std::fabs(number());
        const double phi = number() * kPi / 180;
        const bool large = flag(), sweep = flag();
        const double ex = number() + ox, ey = number() + oy, x0 = x, y0 = y;
        if (rx == 0 || ry == 0) to(ex, ey);
        else {
          const double cs = std::cos(phi), sn = std::sin(phi);
          const double dx = (x0 - ex) / 2, dy = (y0 - ey) / 2;
          const double x1 = cs * dx + sn * dy, y1 = -sn * dx + cs * dy;
          const double grow = (x1 * x1) / (rx * rx) + (y1 * y1) / (ry * ry);
          if (grow > 1) { rx *= std::sqrt(grow); ry *= std::sqrt(grow); }
          const double num = rx * rx * ry * ry - rx * rx * y1 * y1 - ry * ry * x1 * x1;
          const double den = rx * rx * y1 * y1 + ry * ry * x1 * x1;
          const double k = (large == sweep ? -1 : 1) * std::sqrt(jsMax(0, num / den));
          const double cx1 = k * rx * y1 / ry, cy1 = -k * ry * x1 / rx;
          const double cx = cs * cx1 - sn * cy1 + (x0 + ex) / 2, cy = sn * cx1 + cs * cy1 + (y0 + ey) / 2;
          const auto angle = [](double ux, double uy, double vx, double vy) { return std::atan2(ux * vy - uy * vx, ux * vx + uy * vy); };
          const double a0 = angle(1, 0, (x1 - cx1) / rx, (y1 - cy1) / ry);
          double da = angle((x1 - cx1) / rx, (y1 - cy1) / ry, (-x1 - cx1) / rx, (-y1 - cy1) / ry);
          if (!sweep && da > 0) da -= 2 * kPi;
          if (sweep && da < 0) da += 2 * kPi;
          const double steps = jsMax(2, std::ceil(std::fabs(da) / (kPi / 16)));
          for (double s = 1; s <= steps; s++) {
            const double a = a0 + da * s / steps, px = rx * std::cos(a), py = ry * std::sin(a);
            to(s == steps ? ex : cs * px - sn * py + cx, s == steps ? ey : sn * px + cs * py + cy);
          }
        }
        lastC.reset(); lastQ.reset();
      } else {
        std::string name;
        name += static_cast<char>(cmd);
        throw Refused { "no such command: " + name };
      }
      if (!more() && i < n && !letter(text[i])) throw Refused { "unexpected character at " + std::to_string(i) };
    }
  } catch (const Refused& r) {
    return { std::nullopt, r.why };
  }
  std::size_t count = 0;
  for (const auto& s : strokes) count += s.size();
  if (count > kPathPointsMost) {
    return { std::nullopt, "too detailed: " + std::to_string(count) + " points, and the most is " + std::to_string(kPathPointsMost) };
  }
  // Fitted to the screen: the box scaled to 1.9 across its longer side and
  // centred, and the right way up, since SVG's y runs down.
  double x0 = HUGE_VAL, x1 = -HUGE_VAL, y0 = HUGE_VAL, y1 = -HUGE_VAL;
  for (const auto& s : strokes) for (const auto& p : s) {
    x0 = jsMin(x0, p[0]); x1 = jsMax(x1, p[0]); y0 = jsMin(y0, p[1]); y1 = jsMax(y1, p[1]);
  }
  const double size = jsMax(x1 - x0, y1 - y0);
  if (!(size > 0)) return { Strokes {}, "" };
  const double scale = 1.9 / size, cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
  Strokes out;
  for (const auto& s : strokes) {
    if (s.size() <= 1) continue;
    Stroke fitted;
    for (const auto& p : s) fitted.push_back({ (p[0] - cx) * scale, (cy - p[1]) * scale });
    out.push_back(fitted);
  }
  return { out, "" };
}

// compilePath: the points in drawing order, and for each the fraction of the
// lap at which the beam arrives - by length along a stroke, and by length
// over the travel speed between strokes and back to the start.
inline std::shared_ptr<const FigurePath> compilePath(const Strokes& strokes) {
  auto path = std::make_shared<FigurePath>();
  auto& xy = path->xy;
  std::vector<double> weight { 0 };
  double total = 0;
  const std::array<double, 2>* prev = nullptr;
  for (const auto& stroke : strokes) {
    for (std::size_t k = 0; k < stroke.size(); k++) {
      const auto& p = stroke[k];
      if (prev) {
        const double len = std::hypot(p[0] - (*prev)[0], p[1] - (*prev)[1]);
        total += k == 0 ? len / kTravelSpeed : len;
        weight.push_back(total);
      }
      xy.push_back(p[0]); xy.push_back(p[1]);
      prev = &p;
    }
  }
  if (xy.size() < 4) return nullptr;
  total += std::hypot(xy[0] - (*prev)[0], xy[1] - (*prev)[1]) / kTravelSpeed;
  weight.push_back(total);
  xy.push_back(xy[0]); xy.push_back(xy[1]);
  if (!(total > 0)) return nullptr;
  for (const double w : weight) path->at.push_back(w / total);
  return path;
}

// decodeDrawn: "x,y x,y;x,y ..." - strokes by semicolons, points by white
// space - each point held to two either way, three thousand at most, and a
// stroke of one point dropped.
inline Strokes decodeDrawn(const Json* text) {
  Strokes out;
  if (!text || text->type != Json::Type::String || text->s.empty()) return out;
  std::size_t count = 0;
  const std::u16string& s = text->s;
  std::size_t from = 0;
  while (from <= s.size()) {
    const std::size_t semi = std::min(s.find(u';', from), s.size());
    const std::u16string part = jsTrim(s.substr(from, semi - from));
    from = semi + 1;
    Stroke stroke;
    // part.split(/\s+/): an empty part is one empty pair.
    std::size_t at = 0;
    while (at <= part.size()) {
      std::size_t end = at;
      while (end < part.size() && !jsSpace(part[end])) end++;
      const std::u16string pair = part.substr(at, end - at);
      at = end;
      while (at < part.size() && jsSpace(part[at])) at++;
      // pair.split(",").map(Number), and the first two of them.
      const std::size_t comma = pair.find(u',');
      const double px = jsStringToNumber(pair.substr(0, comma));
      double py = NAN;
      if (comma != std::u16string::npos) {
        const std::size_t next = pair.find(u',', comma + 1);
        py = jsStringToNumber(pair.substr(comma + 1, next == std::u16string::npos ? std::u16string::npos : next - comma - 1));
      }
      if (std::isfinite(px) && std::isfinite(py) && count < kDrawnMost) {
        stroke.push_back({ jsMax(-2, jsMin(2, px)), jsMax(-2, jsMin(2, py)) });
        count++;
      }
      if (end >= part.size()) break;
    }
    if (stroke.size() > 1) out.push_back(stroke);
  }
  return out;
}

// encodeDrawn: the same text back.
inline std::string encodeDrawn(const Strokes& strokes) {
  std::string out;
  for (std::size_t s = 0; s < strokes.size(); s++) {
    if (s) out += ";";
    for (std::size_t k = 0; k < strokes[s].size(); k++) {
      if (k) out += " ";
      out += jsNumberToString(strokes[s][k][0]) + "," + jsNumberToString(strokes[s][k][1]);
    }
  }
  return out;
}

}  // namespace scope
