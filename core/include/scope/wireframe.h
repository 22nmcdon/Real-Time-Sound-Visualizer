// The solids, ported from web/scope.html: the models (`MODELS`, with
// `eulerRoute` and `nearestEdges` building the routes of the ones not written
// out by hand), each scaled to a unit radius, and `makeWireframe`, which
// turns one, projects it and walks the beam round its route at a constant
// speed on the screen. The page explains why the beam retraces edges rather
// than jumping, and why it is paced by distance; this is the same arithmetic.

#pragma once

#include <array>
#include <cmath>
#include <limits>
#include <string>
#include <string_view>
#include <vector>

#include "scope/wave.h"

namespace scope {

/* JavaScript's Math.hypot as V8 computes it: every value divided by the
   largest, the squares summed with Kahan's compensation, and the root taken
   and scaled back. `std::hypot` is a different algorithm and may differ in
   the last place, and a solid's corners are divided by its longest. */
inline double jsHypot(std::initializer_list<double> values) {
  double most = 0;
  for (const double v : values) {
    if (std::isinf(v)) return std::numeric_limits<double>::infinity();
    if (std::isnan(v)) return std::numeric_limits<double>::quiet_NaN();
    most = std::fmax(most, std::fabs(v));
  }
  if (most == 0) return 0;
  double sum = 0, compensation = 0;
  for (const double v : values) {
    const double n = std::fabs(v) / most;
    const double summand = n * n - compensation;
    const double preliminary = sum + summand;
    compensation = (preliminary - sum) - summand;
    sum = preliminary;
  }
  return std::sqrt(sum) * most;
}

struct Solid {
  std::string name;
  std::vector<std::array<double, 3>> v;
  std::vector<int> route;
};

using Edge = std::array<int, 2>;

// Pairs the odd corners along single edges, depth first in the order of the
// edges, as the page's recursive `pair` does; false if there is no way.
inline bool pairCorners(const std::vector<Edge>& edges, const std::vector<int>& left, std::vector<Edge>& out) {
  if (left.empty()) return true;
  const int a = left[0];
  for (const auto& e : edges) {
    const int b = e[0] == a ? e[1] : e[1] == a ? e[0] : -1;
    if (b < 0) continue;
    bool in = false;
    for (const int v : left) if (v == b) in = true;
    if (!in) continue;
    std::vector<int> rest;
    for (const int v : left) if (v != a && v != b) rest.push_back(v);
    std::vector<Edge> more;
    if (pairCorners(edges, rest, more)) {
      out.push_back({ a, b });
      out.insert(out.end(), more.begin(), more.end());
      return true;
    }
  }
  return false;
}

inline std::vector<int> eulerRoute(int count, const std::vector<Edge>& edges) {
  std::vector<int> degree(static_cast<std::size_t>(count), 0);
  for (const auto& e : edges) { degree[static_cast<std::size_t>(e[0])]++; degree[static_cast<std::size_t>(e[1])]++; }
  std::vector<int> odd;
  for (int v = 0; v < count; v++) if (degree[static_cast<std::size_t>(v)] % 2) odd.push_back(v);
  std::vector<Edge> doubled;
  if (!pairCorners(edges, odd, doubled)) return {};  // the page throws; no solid here gets that far
  std::vector<Edge> all = edges;
  all.insert(all.end(), doubled.begin(), doubled.end());
  std::vector<bool> unused(all.size(), true);
  std::vector<std::vector<std::size_t>> at(static_cast<std::size_t>(count));
  for (std::size_t k = 0; k < all.size(); k++) {
    at[static_cast<std::size_t>(all[k][0])].push_back(k);
    at[static_cast<std::size_t>(all[k][1])].push_back(k);
  }
  std::vector<int> stack { 0 }, route;
  while (!stack.empty()) {
    const int v = stack.back();
    std::size_t k = all.size();
    for (const std::size_t e : at[static_cast<std::size_t>(v)]) if (unused[e]) { k = e; break; }
    if (k == all.size()) { route.push_back(v); stack.pop_back(); continue; }
    unused[k] = false;
    stack.push_back(all[k][0] == v ? all[k][1] : all[k][0]);
  }
  return { route.rbegin(), route.rend() };
}

inline std::vector<Edge> nearestEdges(const std::vector<std::array<double, 3>>& v) {
  double least = std::numeric_limits<double>::infinity();
  const auto gap = [&](std::size_t i, std::size_t j) {
    return jsHypot({ v[i][0] - v[j][0], v[i][1] - v[j][1], v[i][2] - v[j][2] });
  };
  for (std::size_t i = 0; i < v.size(); i++) for (std::size_t j = i + 1; j < v.size(); j++) least = std::fmin(least, gap(i, j));
  std::vector<Edge> edges;
  for (std::size_t i = 0; i < v.size(); i++) {
    for (std::size_t j = i + 1; j < v.size(); j++) {
      if (gap(i, j) < least * 1.001) edges.push_back({ static_cast<int>(i), static_cast<int>(j) });
    }
  }
  return edges;
}

// The page's models, in its order, each scaled to a unit radius. Built once.
inline const std::vector<Solid>& solids() {
  static const std::vector<Solid> all = [] {
    std::vector<Solid> m;
    m.push_back({ "Cube", { { -1, -1, -1 }, { 1, -1, -1 }, { 1, 1, -1 }, { -1, 1, -1 },
                            { -1, -1, 1 }, { 1, -1, 1 }, { 1, 1, 1 }, { -1, 1, 1 } },
                  { 0, 1, 2, 3, 0, 4, 5, 1, 5, 6, 2, 6, 7, 3, 7, 4, 0 } });
    m.push_back({ "Tetrahedron", { { 1, 1, 1 }, { 1, -1, -1 }, { -1, 1, -1 }, { -1, -1, 1 } },
                  { 0, 1, 2, 3, 2, 0, 3, 1, 0 } });
    m.push_back({ "Octahedron", { { 1, 0, 0 }, { -1, 0, 0 }, { 0, 1, 0 }, { 0, -1, 0 }, { 0, 0, 1 }, { 0, 0, -1 } },
                  { 0, 2, 1, 3, 0, 4, 2, 5, 1, 4, 3, 5, 0 } });
    const double g = (1 + std::sqrt(5.0)) / 2, h = 1 / g;
    const double signs[2] = { -1, 1 };
    std::vector<std::array<double, 3>> dodeca, icosa, torus, knot;
    for (const double x : signs) for (const double y : signs) for (const double z : signs) dodeca.push_back({ x, y, z });
    for (const double a : signs) for (const double b : signs) {
      dodeca.push_back({ 0, a * h, b * g }); dodeca.push_back({ a * h, b * g, 0 }); dodeca.push_back({ a * g, 0, b * h });
    }
    for (const double a : signs) for (const double b : signs) {
      icosa.push_back({ 0, a, b * g }); icosa.push_back({ a, b * g, 0 }); icosa.push_back({ a * g, 0, b });
    }
    std::vector<Edge> torusEdges, knotEdges;
    const int M = 12, N = 6;
    for (int i = 0; i < M; i++) for (int j = 0; j < N; j++) {
      const double u = static_cast<double>(i) / M * 2 * kPi, w = static_cast<double>(j) / N * 2 * kPi;
      torus.push_back({ (1 + 0.45 * std::cos(w)) * std::cos(u), (1 + 0.45 * std::cos(w)) * std::sin(u), 0.45 * std::sin(w) });
      torusEdges.push_back({ i * N + j, ((i + 1) % M) * N + j });
      torusEdges.push_back({ i * N + j, i * N + (j + 1) % N });
    }
    const int K = 210;
    for (int i = 0; i < K; i++) {
      const double t = static_cast<double>(i) / K * 2 * kPi;
      knot.push_back({ std::cos(3 * t + 0.7), std::cos(2 * t + 0.2), std::cos(7 * t) });
      knotEdges.push_back({ i, (i + 1) % K });
    }
    m.push_back({ "Dodecahedron", dodeca, eulerRoute(static_cast<int>(dodeca.size()), nearestEdges(dodeca)) });
    m.push_back({ "Icosahedron", icosa, eulerRoute(static_cast<int>(icosa.size()), nearestEdges(icosa)) });
    m.push_back({ "Torus", torus, eulerRoute(static_cast<int>(torus.size()), torusEdges) });
    m.push_back({ "Knot", knot, eulerRoute(static_cast<int>(knot.size()), knotEdges) });
    for (auto& model : m) {
      double longest = 0;
      for (const auto& p : model.v) longest = std::fmax(longest, jsHypot({ p[0], p[1], p[2] }));
      for (auto& p : model.v) p = { p[0] / longest, p[1] / longest, p[2] / longest };
    }
    return m;
  }();
  return all;
}

// How often the solid is projected again: see the page's WIRE_REPROJECT.
constexpr int kWireReproject = 512;

class Wireframe {
 public:
  const std::string& modelName() const { return model_->name; }

  void set(std::string_view name) {
    for (const auto& s : solids()) {
      if (s.name != name) continue;
      if (&s == model_) return;
      model_ = &s;
      leg_ = 0; along_ = 0; since_ = kWireReproject;
      return;
    }
  }

  void reset() { spin_ = { 0, 0, 0 }; leg_ = 0; along_ = 0; since_ = kWireReproject; }

  const std::array<double, 3>& angles() const { return spin_; }

  std::array<double, 2> step(double dt, double rate, double depth, const std::array<double, 3>& spinRates) {
    spin_[0] += spinRates[0] * dt * kTwoPi;
    spin_[1] += spinRates[1] * dt * kTwoPi;
    spin_[2] += spinRates[2] * dt * kTwoPi;
    if (++since_ >= kWireReproject) reproject(depth);
    const auto& route = model_->route;
    const int legs = static_cast<int>(route.size()) - 1;
    if (total_ > 1e-9) {
      double arc = rate * dt * total_;
      int guard = 0;
      while (arc > 0 && guard++ < legs + 2) {
        const double len = segment_[static_cast<std::size_t>(leg_)];
        if (len <= 1e-9) { leg_ = (leg_ + 1) % legs; along_ = 0; continue; }
        const double left = (1 - along_) * len;
        if (arc < left) { along_ += arc / len; arc = 0; }
        else { arc -= left; leg_ = (leg_ + 1) % legs; along_ = 0; }
      }
    } else {
      along_ = 0;
    }
    const auto& a = projected_[static_cast<std::size_t>(route[static_cast<std::size_t>(leg_)])];
    const auto& b = projected_[static_cast<std::size_t>(route[static_cast<std::size_t>(leg_) + 1])];
    return { a[0] + (b[0] - a[0]) * along_, a[1] + (b[1] - a[1]) * along_ };
  }

 private:
  void reproject(double depth) {
    const double cx = std::cos(spin_[0]), sxx = std::sin(spin_[0]);
    const double cy = std::cos(spin_[1]), syy = std::sin(spin_[1]);
    const double cz = std::cos(spin_[2]), szz = std::sin(spin_[2]);
    const double d = 1.5 + 10 * (1 - depth);
    const double reach = d / (d - 1);
    const auto& v = model_->v;
    if (projected_.size() < v.size()) projected_.resize(v.size());
    for (std::size_t i = 0; i < v.size(); i++) {
      double x = v[i][0], y = v[i][1], z = v[i][2], t;
      t = y * cx - z * sxx;  z = y * sxx + z * cx;  y = t;
      t = x * cy + z * syy;  z = -x * syy + z * cy; x = t;
      t = x * cz - y * szz;  y = x * szz + y * cz;  x = t;
      const double k = d / (d - z) / reach;
      projected_[i] = { x * k, y * k };
    }
    const auto& route = model_->route;
    if (segment_.size() < route.size()) segment_.resize(route.size());
    total_ = 0;
    for (std::size_t i = 0; i + 1 < route.size(); i++) {
      const auto& a = projected_[static_cast<std::size_t>(route[i])];
      const auto& b = projected_[static_cast<std::size_t>(route[i + 1])];
      const double len = jsHypot({ b[0] - a[0], b[1] - a[1] });
      segment_[i] = len;
      total_ += len;
    }
    since_ = 0;
  }

  const Solid* model_ = &solids()[0];
  std::array<double, 3> spin_ { 0, 0, 0 };
  std::vector<std::array<double, 2>> projected_;
  std::vector<double> segment_;
  int leg_ = 0;
  double along_ = 0, total_ = 0;
  int since_ = kWireReproject;
};

}  // namespace scope
