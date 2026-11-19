// An LFO's drawn shape (19 Nov, web/docs/lfo-drawn.md): one cycle as points,
// its text, and the laws its lines are played by. lfo.h is the engine that
// plays it; this half is apart, as mseg_shape.h is from mseg.h, so the text
// can be read and written without the engine.
//
// The text is the envelope string's grammar in a form of its own for one
// repeating cycle:
//
//   1;x,level,law[,r];x,level,law[,r];...
//
// the version, then each point sorted by x (0 to 1, a share of the cycle):
// its level (-1 to 1; for a random point its reach, 0 to 1), the law of the
// line to the next point - l straight, s an S (half a cosine), h held, or
// m<mid> a curve by its midpoint, the envelopes' one-pole law clamped 0.1 to
// 0.9 - and r if the point takes a new level each pass. The last point's line
// runs on to the first point of the next pass; two points at one x are a
// jump. At most 32 points.

#pragma once

#include <array>
#include <cmath>
#include <cstddef>
#include <string_view>

#include "scope/chars.h"
#include "scope/mseg_shape.h"
#include "scope/wave.h"

namespace scope {

constexpr int kLfoMaxPoints = 32;

struct LfoPoint {
  double x = 0, y = 0;  // for a random point, y's size is its reach
  double m = 0.5;   // a curve's midpoint, read only while law is 'm'
  char law = 'l';   // 'l' straight, 's' an S, 'h' held, 'm' a curve
  bool r = false;   // a new level each pass, within the reach y
};

struct LfoShape {
  std::array<LfoPoint, kLfoMaxPoints> p {};
  int n = 0;
};

/* The text into a shape; false, and the shape empty, for one that does not
   read. A point's x is held between its neighbour before and 1, as the
   editor holds it, and a level to its range, so a hand-written text cannot
   make the engine read out of order. */
inline bool lfoShapeRead(std::string_view text, LfoShape& out) {
  using mseg_detail::number;
  out = LfoShape();
  std::size_t at = text.find(';');
  if (at == std::string_view::npos || text.substr(0, at) != "1") return false;
  double prevX = 0;
  while (at != std::string_view::npos) {
    const std::size_t next = text.find(';', at + 1);
    const std::string_view block = text.substr(at + 1, next == std::string_view::npos ? std::string_view::npos : next - at - 1);
    at = next;
    if (block.empty()) { out.n = 0; return false; }
    std::string_view f[5];
    int k = 0;
    std::string_view rest = block;
    while (k < 5) {
      const std::size_t comma = rest.find(',');
      f[k++] = rest.substr(0, comma);
      if (comma == std::string_view::npos) break;
      rest = rest.substr(comma + 1);
    }
    if (k < 3 || k > 4 || out.n >= kLfoMaxPoints) { out.n = 0; return false; }
    LfoPoint p;
    if (!number(f[0], p.x) || !number(f[1], p.y)) { out.n = 0; return false; }
    const std::string_view law = f[2];
    if (law == "l" || law == "s" || law == "h") p.law = law[0];
    else if (law.size() >= 2 && law[0] == 'm' && number(law.substr(1), p.m)) { p.law = 'm'; p.m = std::fmax(0.1, std::fmin(0.9, p.m)); }
    else { out.n = 0; return false; }
    if (k == 4) {
      if (f[3] != "r") { out.n = 0; return false; }
      p.r = true;
    }
    p.x = std::fmax(prevX, std::fmin(1.0, p.x));
    // A random point's reach is its height either way of nought; the sign is kept, so the text reads back as written.
    p.y = std::fmax(-1.0, std::fmin(1.0, p.y));
    prevX = p.x;
    out.p[static_cast<std::size_t>(out.n++)] = p;
  }
  return out.n > 0;
}

namespace lfo_detail {
// A number as the page's shape text writes it: to five places, no trailing
// noughts, and no nought before the point ("-.6", ".25", "1").
inline std::size_t put(double v, char* out, std::size_t room) {
  const double r = jsRound(v * 1e5) / 1e5;
  long long whole = static_cast<long long>(std::llround(std::fabs(r) * 1e5));
  std::size_t n = 0;
  auto push = [&](char c) { if (n + 1 < room) out[n] = c; n++; };
  if (whole == 0) { push('0'); return n; }
  if (r < 0) push('-');
  const long long ip = whole / 100000, fp = whole % 100000;
  if (ip > 0) {
    char tmp[24]; int t = 0;
    for (long long q = ip; q > 0; q /= 10) tmp[t++] = static_cast<char>('0' + q % 10);
    while (t > 0) push(tmp[--t]);
  }
  if (fp > 0) {
    char d[5];
    long long q = fp;
    for (int i = 4; i >= 0; --i) { d[i] = static_cast<char>('0' + q % 10); q /= 10; }
    int last = 4;
    while (last > 0 && d[last] == '0') --last;
    push('.');
    for (int i = 0; i <= last; ++i) push(d[i]);
  }
  return n;
}
}  // namespace lfo_detail

/* A shape as its text, the page's lfoShapeText character for character. Into
   `out`, which needs room for the longest (32 points, under 640); the length
   written, without its terminator. */
inline std::size_t lfoShapeWrite(const LfoShape& s, char* out, std::size_t room) {
  std::size_t n = 0;
  auto push = [&](char c) { if (n + 1 < room) out[n] = c; n++; };
  push('1');
  for (int k = 0; k < s.n; ++k) {
    const LfoPoint& p = s.p[static_cast<std::size_t>(k)];
    push(';');
    n += lfo_detail::put(p.x, out + std::min(n, room), n < room ? room - n : 0);
    push(',');
    n += lfo_detail::put(p.y, out + std::min(n, room), n < room ? room - n : 0);
    push(',');
    push(p.law);
    if (p.law == 'm') n += lfo_detail::put(p.m, out + std::min(n, room), n < room ? room - n : 0);
    if (p.r) { push(','); push('r'); }
  }
  if (room > 0) out[std::min(n, room - 1)] = 0;
  return n;
}

/* The line from a to b at share f of its time, by the law of the point it
   starts from. The S is half a cosine, a law of its own (the owner's call, 19
   Nov): no one-pole curve makes a sine. The curve is the envelopes' travel
   towards an aim past the end, its aim found from the midpoint as msegRho
   finds it, so a drawn midpoint means here what it means on an envelope. */
inline double lfoLaw(const LfoPoint& p, double a, double b, double f) {
  if (f <= 0) return a;
  if (p.law == 'h') return f >= 1 ? b : a;
  if (f >= 1) return b;
  if (p.law == 's') return a + (b - a) * (1 - std::cos(kPi * f)) / 2;
  if (p.law == 'm') {
    if (a == b) return b;
    const double rho = msegRho(std::fmax(0.1, std::fmin(0.9, p.m)));
    if (!std::isfinite(rho)) return a + (b - a) * f;
    const double aim = b + rho * (b - a);
    const double r = (b - aim) / (a - aim);
    if (!(r > 0)) return a + (b - a) * f;
    return aim + (a - aim) * std::pow(r, f);
  }
  return a + (b - a) * f;
}

// The point whose line u is on: the last at or before u, or the last of all, from the pass before.
inline int lfoSegAt(const LfoShape& s, double u) {
  int i = -1;
  for (int k = 0; k < s.n; ++k) if (s.p[static_cast<std::size_t>(k)].x <= u) i = k;
  return i < 0 ? s.n - 1 : i;
}
// How long the line from point i lasts, as a share of the cycle: to the next point, or round to the first.
inline double lfoSegLen(const LfoShape& s, int i) {
  const auto& p = s.p;
  return i + 1 < s.n ? p[static_cast<std::size_t>(i + 1)].x - p[static_cast<std::size_t>(i)].x
                     : p[0].x + 1 - p[static_cast<std::size_t>(i)].x;
}

}  // namespace scope
