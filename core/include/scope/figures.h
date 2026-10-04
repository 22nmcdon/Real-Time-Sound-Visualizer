// The figures, ported from `figureAt` in web/scope.html: a closed path a
// lap long, x(t) and y(t), for each of the figure menu's shapes, and for a
// compiled path - the text, an imported SVG, or a drawing - read by where the
// beam is along it.

#pragma once

#include <array>
#include <cmath>
#include <string_view>
#include <vector>

#include "scope/wave.h"

namespace scope {

enum class Figure { Circle, Square, Polygon, Star, Rose, Heart, Infinity, Spiral, Spirograph, Butterfly, Text, Path, Drawn };

// By the page's names. Anything else is the page's `default:`, the circle.
inline Figure figureNamed(std::string_view name) {
  if (name == "Square") return Figure::Square;
  if (name == "Polygon") return Figure::Polygon;
  if (name == "Star") return Figure::Star;
  if (name == "Rose") return Figure::Rose;
  if (name == "Heart") return Figure::Heart;
  if (name == "Infinity") return Figure::Infinity;
  if (name == "Spiral") return Figure::Spiral;
  if (name == "Spirograph") return Figure::Spirograph;
  if (name == "Butterfly") return Figure::Butterfly;
  if (name == "Text") return Figure::Text;
  if (name == "Path") return Figure::Path;
  if (name == "Drawn") return Figure::Drawn;
  return Figure::Circle;
}

// What `compilePath` leaves: the points, x then y, and the fraction of the
// lap at which the beam reaches each.
struct FigurePath {
  std::vector<double> xy, at;
};

inline std::array<double, 2> figureAt(Figure name, double t, double detail, const FigurePath* path) {
  const double turn = t * 2 * kPi;
  switch (name) {
    case Figure::Text:
    case Figure::Path:
    case Figure::Drawn: {
      if (path == nullptr || path->at.size() < 2) return { 0, 0 };
      const auto& at = path->at;
      // A point past the end of xy is the page's undefined, which makes NaN
      // of whatever it touches; read as that, rather than past the vector.
      // No path the page builds is short, but one given whole can be.
      const auto xy = [&path](std::size_t i) { return i < path->xy.size() ? path->xy[i] : NAN; };
      const double u = t - std::floor(t);
      std::size_t lo = 0, hi = at.size() - 1;
      while (hi - lo > 1) {
        const std::size_t mid = (lo + hi) >> 1;
        if (at[mid] <= u) lo = mid; else hi = mid;
      }
      const double span = at[hi] - at[lo], f = span > 0 ? (u - at[lo]) / span : 0;
      return { xy(2 * lo) + (xy(2 * hi) - xy(2 * lo)) * f, xy(2 * lo + 1) + (xy(2 * hi + 1) - xy(2 * lo + 1)) * f };
    }
    case Figure::Square: {
      static constexpr double corners[5][2] = { { -1, -1 }, { 1, -1 }, { 1, 1 }, { -1, 1 }, { -1, -1 } };
      const double side = std::fmod(t, 1.0) * 4;
      const double k = std::floor(side), f = side - k;
      const int i = static_cast<int>(k);
      const double* a = corners[i % 4];
      const double* b = corners[(i + 1) % 4];
      return { a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f };
    }
    case Figure::Polygon: {
      const double n = std::fmax(3.0, jsRound(detail));
      const double seg = std::fmod(t, 1.0) * n;
      const double k = std::floor(seg), f = seg - k;
      const double a0 = k * 2 * kPi / n, a1 = (k + 1) * 2 * kPi / n;
      return { std::cos(a0) + (std::cos(a1) - std::cos(a0)) * f, std::sin(a0) + (std::sin(a1) - std::sin(a0)) * f };
    }
    case Figure::Star: {
      const double n = std::fmax(5.0, jsRound(detail));
      const double step = std::fmod(n, 2.0) == 0 ? 3 : std::floor(n / 2);
      const double seg = std::fmod(t, 1.0) * n;
      const double k = std::floor(seg), f = seg - k;
      const double a0 = (k * step) * 2 * kPi / n, a1 = ((k + 1) * step) * 2 * kPi / n;
      return { std::cos(a0) + (std::cos(a1) - std::cos(a0)) * f, std::sin(a0) + (std::sin(a1) - std::sin(a0)) * f };
    }
    case Figure::Rose: {
      const double k = std::fmax(0.5, detail);
      const double r = std::cos(k * turn);
      return { r * std::cos(turn), r * std::sin(turn) };
    }
    case Figure::Heart: {
      const double x = 16 * std::pow(std::sin(turn), 3);
      const double y = 13 * std::cos(turn) - 5 * std::cos(2 * turn) - 2 * std::cos(3 * turn) - std::cos(4 * turn);
      return { x / 17, y / 17 };
    }
    case Figure::Infinity: {
      const double d = 1 + std::sin(turn) * std::sin(turn);
      return { std::cos(turn) / d, std::sin(turn) * std::cos(turn) / d };
    }
    case Figure::Spiral: {
      const double loops = std::fmax(2.0, detail);
      const double r = std::fmod(t, 1.0);
      return { r * std::cos(turn * loops), r * std::sin(turn * loops) };
    }
    case Figure::Spirograph: {
      const double n = std::fmax(2.0, detail);
      const double r = 1 / n;
      return { (1 - r) * std::cos(turn) + r * std::cos((1 - r) / r * turn),
               (1 - r) * std::sin(turn) - r * std::sin((1 - r) / r * turn) };
    }
    case Figure::Butterfly: {
      const double th = turn * 6;
      const double r = std::exp(std::cos(th)) - 2 * std::cos(4 * th) - std::pow(std::sin(th / 12), 5);
      return { std::sin(th) * r / 2.907, (std::cos(th) * r - 0.661) / 2.907 };
    }
    case Figure::Circle:
      break;
  }
  return { std::cos(turn), std::sin(turn) };
}

}  // namespace scope
