// Numbers to text and back as JavaScript has them, for what the page writes
// into a setup code and reads out of one. The core and the page have to write
// the same characters for the same number, or a setup saved by one reads
// differently in the other.
//
// - `jsToFixed` is `Number.prototype.toFixed`: the exact value of the double,
//   rounded half away from nought at the place asked for. `printf("%.3f")`
//   rounds an exact tie to even - 0.0625 is "0.062" there and "0.063" in a
//   browser - and says "-0.000" for minus nought, which JavaScript says as
//   "0.000".
// - `jsNumber` is `Number(text)` for the text the page's patterns let through
//   (a sign, digits and points): two points or a point alone is NaN, where
//   `strtod` would read as far as it could.

#pragma once

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <limits>
#include <string>
#include <string_view>

namespace scope {

inline std::string jsToFixed(double x, int digits) {
  if (std::isnan(x)) return "NaN";
  std::string sign = x < 0 ? "-" : "";
  const double a = std::fabs(x);
  if (a >= 1e21) {  // toFixed hands these to ToString; nothing the page writes is this big
    char b[64];
    std::snprintf(b, sizeof b, "%.17g", x);
    return b;
  }
  // The exact decimal expansion, far past any digit a tie can hang on.
  char b[512];
  std::snprintf(b, sizeof b, "%.200f", a);
  std::string s(b);
  const std::size_t point = s.find('.');
  std::string keep = s.substr(0, point) + s.substr(point + 1, static_cast<std::size_t>(digits));
  // Half away from nought: a tie is the larger n, as the specification says.
  if (s[point + 1 + static_cast<std::size_t>(digits)] >= '5') {
    std::size_t i = keep.size();
    while (i > 0) {
      i--;
      if (keep[i] == '9') { keep[i] = '0'; continue; }
      keep[i]++;
      break;
    }
    if (i == 0 && keep[0] == '0') keep.insert(keep.begin(), '1');
  }
  const std::size_t whole = keep.size() - static_cast<std::size_t>(digits);
  std::string out = keep.substr(0, whole);
  if (digits > 0) out += "." + keep.substr(whole);
  return sign + out;
}

inline double jsNumber(std::string_view text) {
  std::string_view s = text;
  if (!s.empty() && (s.front() == '-' || s.front() == '+')) s.remove_prefix(1);
  int points = 0, digits = 0;
  for (const char c : s) {
    if (c == '.') points++;
    else if (c >= '0' && c <= '9') digits++;
    else return std::numeric_limits<double>::quiet_NaN();
  }
  if (points > 1 || digits == 0) return std::numeric_limits<double>::quiet_NaN();
  return std::strtod(std::string(text).c_str(), nullptr);
}

}  // namespace scope
