// Physical paint for the painting study: a bristle brush on a canvas, paint
// kept as pigment amounts per pixel (so its thickness is a height map), mixed
// by Kubelka-Munk, wet until it dries, and lit by a raking light.
//
// Input, text, a line each, in time order (paint.py's `physical` writes it):
//
//   canvas W H                       the canvas, in pixels
//   ground r g b                     the ground's linear reflectance
//   ink i r g b                      pigment i's linear masstone reflectance (0 to 5 the
//                                    inks, 6 the white)
//   dry tau thick                    wet paint's wetness falls to 1/e in tau * (1 + thick * a)
//                                    seconds, a its thickness: thin paint dries first
//   load s t role amount [white]     brush s loaded at time t with pigment `role`, that
//                                    share of the dip being white instead
//   step s t x y dx dy w p [stiff splay dry]
//                                    brush s at x,y moving along dx,dy, width w, pressure 0-1;
//                                    and, each nought to one, how stiff its bristles are (stiff
//                                    ones streak and blend less), how far they splay (wider,
//                                    with gaps between groups) and how dry it drags (catching
//                                    only on high points whatever its load)
//   frame t                          render now, to the output
//
// Out, binary: for each frame, W*H*3 bytes of sRGB, then W*H float32 of paint
// coverage (what Scan would read: it depends on the amounts of paint, never on
// their colours). On stderr at the end, how long the brushwork and the
// rendering took, per frame.
//
// The model, and what it leaves out:
//  - The brush is 32 bins across its width, each a bristle group with its own
//    load of paint and its own mixture. Loading gives each bin a slightly
//    different share (seeded per brush), so some run dry before others:
//    the streaks. A bin deposits in proportion to its load and the pressure,
//    and spends its load doing so, so a stroke is dense at the start and
//    broken at the end.
//  - Where it passes over paint that is still wet, the brush picks some of it
//    up into the bin's mixture (and carries that colour on) and pushes some
//    of it out to the stroke's edges (the ridges). Over dry paint it does
//    neither: what it lays covers what is under it by its own opacity, and a
//    nearly empty brush catches only on the high points - the weave and the
//    dried ridges - which is dry brush and broken colour.
//  - Colour is Kubelka-Munk with one constant per channel: each ink's K/S
//    from its masstone, mixed by concentration, so blue and yellow make a
//    green, not a grey. Thin paint lets the ground through by Beer's law on
//    its thickness. Not modelled: tinting strength differing between
//    pigments, the paint's flow and levelling, the brush's angle.
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

namespace {

// Six inks, a hand's three each, and a white: the brush mapping (cycle 2)
// lightens a bright sound's paint by mixing white into the dip.
constexpr int kInks = 7;
constexpr int kBins = 32;

// Paint per unit of deposit, and the thickness at which paint hides the ground to 1/e.
constexpr float kDeposit = 0.6f;
constexpr float kHide = 0.15f;
// Fractions of wet paint under the brush's core taken up into it, and pushed to its edges, per step.
constexpr float kPick = 0.05f;
constexpr float kPush = 0.018f;
// How far, in brush widths, a stroke goes before a bin's load falls to 1/e:
// a dipped brush lays solid paint for several widths and is dry brush by about
// ten, about a loaded hog-hair brush's reach on primed canvas.
constexpr float kReach = 7.0f;

struct Brush {
  std::array<float, kBins> load {};
  std::array<std::array<float, kInks>, kBins> mix {};
  std::array<float, kBins> share {};
  bool seeded = false;
  float lastX = -1e9f, lastY = -1e9f;
  float span = 0;   // the brush's own half-width: the widest it has pressed, which places its bristles
};

float hash(std::uint32_t x) {
  x ^= x >> 16; x *= 0x7feb352dU; x ^= x >> 15; x *= 0x846ca68bU; x ^= x >> 16;
  return (x & 0xffffff) / float(0xffffff);
}

float srgb(float c) {
  c = std::clamp(c, 0.0f, 1.0f);
  return c <= 0.0031308f ? 12.92f * c : 1.055f * std::pow(c, 1 / 2.4f) - 0.055f;
}

}  // namespace

int main() {
  int W = 0, H = 0;
  float ground[3] = { 1, 1, 1 };
  float ks[kInks][3] = {};
  float tau = 1.5f, thick = 0.0f;
  std::vector<float> P, last, weave;      // pigment amounts (ink-major), last wet time, canvas relief
  std::vector<int> owner;                 // which brush laid each pixel's paint last
  std::map<int, Brush> brushes;
  double brushSeconds = 0, renderSeconds = 0;
  long frames = 0, steps = 0;
  // Where paint landed, by amount: into wet paint (merging), onto dry paint
  // (layering), on bare canvas - so whether the timing decided it can be read.
  double intoWet = 0, ontoDry = 0, ontoBare = 0;
  std::vector<std::uint8_t> rgb;
  std::vector<float> cover;
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream in(line);
    std::string cmd;
    in >> cmd;
    if (cmd == "canvas") {
      in >> W >> H;
      P.assign(static_cast<std::size_t>(kInks) * W * H, 0.0f);
      last.assign(static_cast<std::size_t>(W) * H, -1e9f);
      owner.assign(static_cast<std::size_t>(W) * H, -1);
      weave.assign(static_cast<std::size_t>(W) * H, 0.0f);
      // A plain-weave canvas: threads about four pixels apart, over and
      // under in a checker, each a rounded ridge. Real threads wander and
      // vary in thickness; a perfectly periodic weave made dry brush catch in
      // a ruled grid, so each thread's line is bent by a slow noise and its
      // height varies thread to thread, with a slub here and there.
      const auto smoothNoise = [](float x, std::uint32_t seed) {
        const int i = int(std::floor(x)); const float f = x - i, g = f * f * (3 - 2 * f);
        return hash(static_cast<std::uint32_t>(i) * 2654435761u + seed) * (1 - g) + hash(static_cast<std::uint32_t>(i + 1) * 2654435761u + seed) * g;
      };
      for (int y = 0; y < H; y++)
        for (int x = 0; x < W; x++) {
          const float xw = x + 1.6f * smoothNoise(y / 23.0f, 11) + 0.7f * smoothNoise(y / 5.0f, 12);
          const float yw = y + 1.6f * smoothNoise(x / 23.0f, 13) + 0.7f * smoothNoise(x / 5.0f, 14);
          const int tx = int(std::floor(xw / 4)), ty = int(std::floor(yw / 4));
          const bool warp = (tx + ty) % 2 == 0;
          const float thick = 0.6f + 0.4f * hash(static_cast<std::uint32_t>(warp ? tx * 7 + 1 : ty * 13 + 2));
          const float a = std::fabs(std::sin(3.14159265f * (warp ? xw : yw) / 4.0f)) * thick;
          const float b = 0.3f * std::fabs(std::sin(3.14159265f * (warp ? yw : xw) / 4.0f));
          weave[static_cast<std::size_t>(y) * W + x] = 0.6f * a + 0.2f * b + 0.25f * hash(static_cast<std::uint32_t>(y * 7919 + x * 104729));
        }
      rgb.assign(static_cast<std::size_t>(W) * H * 3, 0);
      cover.assign(static_cast<std::size_t>(W) * H, 0.0f);
    } else if (cmd == "ground") {
      in >> ground[0] >> ground[1] >> ground[2];
    } else if (cmd == "ink") {
      int i; float r[3];
      in >> i >> r[0] >> r[1] >> r[2];
      for (int c = 0; c < 3; c++) {
        const float R = std::clamp(r[c], 0.004f, 0.995f);
        ks[i][c] = (1 - R) * (1 - R) / (2 * R);
      }
    } else if (cmd == "dry") {
      in >> tau;
      if (!(in >> thick)) thick = 0;
    } else if (cmd == "load") {
      int s, role; float t, amount, white = 0;
      in >> s >> t >> role >> amount;
      if (!(in >> white)) white = 0;
      Brush& b = brushes[s];
      if (!b.seeded) {
        for (int k = 0; k < kBins; k++) b.share[k] = 0.45f + 0.55f * hash(static_cast<std::uint32_t>(s * 977 + k * 31 + 7));
        b.seeded = true;
      }
      // Dipping a brush that still holds paint keeps some of what it held.
      for (int k = 0; k < kBins; k++) {
        const float add = amount * b.share[k];
        const float total = b.load[k] + add;
        for (int i = 0; i < kInks; i++)
          b.mix[k][i] = (b.mix[k][i] * b.load[k] + (i == role ? add * (1 - white) : i == kInks - 1 ? add * white : 0.0f)) / std::max(total, 1e-6f);
        b.load[k] = std::min(total, 2.5f);
      }
    } else if (cmd == "step") {
      const auto t0 = std::chrono::steady_clock::now();
      int s; float t, x, y, dx, dy, w, p;
      in >> s >> t >> x >> y >> dx >> dy >> w >> p;
      float stiff = 0.5f, splay = 0.0f, dryness = 0.0f;
      if (in >> stiff) { in >> splay >> dryness; } else stiff = 0.5f;
      Brush& b = brushes[s];
      const float len = std::hypot(dx, dy);
      if (len < 1e-6f) { dx = 1; dy = 0; } else { dx /= len; dy /= len; }
      const float nx = -dy, ny = dx;                 // across the stroke
      // Paint laid per step in proportion to how far the brush moved since
      // its last, so the deposit per unit length does not depend on how the
      // path was sampled (a brush held still lays a little more, not a pile).
      const float moved = b.lastX < -1e8f ? 1.0f : std::hypot(x - b.lastX, y - b.lastY);
      b.lastX = x; b.lastY = y;
      // Splayed bristles fan out: the contact is wider, with gaps.
      const float hw = std::max(0.8f, w * 0.5f * (0.4f + 0.6f * std::min(p, 1.0f)) * (1 + 0.4f * splay));
      b.span = std::max(b.span, hw);
      const float hl = std::max(1.2f, 0.12f * w);    // the bristles' tips, along it
      // A brush barely moving lays very little more (a floor of a fiftieth):
      // a higher floor piled a held note's paint into lumps where its brush lingered.
      const float per = std::clamp(moved / (1.4f * hl), 0.02f, 1.0f);
      const int x0 = std::max(0, int(std::floor(x - hw - hl - 1))), x1 = std::min(W - 1, int(std::ceil(x + hw + hl + 1)));
      const int y0 = std::max(0, int(std::floor(y - hw - hl - 1))), y1 = std::min(H - 1, int(std::ceil(y + hw + hl + 1)));
      std::array<std::array<float, kInks>, kBins> picked {};
      std::array<float, kBins> spent {};
      // The mean height of what is firm under the brush - the weave and
      // dried paint, not wet paint, which gives under it - so a near-dry bin
      // can tell a ridge from a hollow.
      const auto firm = [&](std::size_t q) {
        float a = 0; for (int i = 0; i < kInks; i++) a += P[i * W * H + q];
        const float wet = a > 1e-5f ? std::exp(-(t - last[q]) / (tau * (1 + thick * a))) : 0.0f;
        return weave[q] * 0.15f + a * (1 - wet);
      };
      double hsum = 0; int hn = 0;
      for (int yy = y0; yy <= y1; yy++)
        for (int xx = x0; xx <= x1; xx++) { hsum += firm(static_cast<std::size_t>(yy) * W + xx); hn++; }
      const float hmean = hn ? float(hsum / hn) : 0.0f;
      for (int yy = y0; yy <= y1; yy++)
        for (int xx = x0; xx <= x1; xx++) {
          const float rx = xx + 0.5f - x, ry = yy + 0.5f - y;
          const float u = rx * nx + ry * ny, v = rx * dx + ry * dy;
          // The brush's footprint is rounded at its tip, not square.
          if (std::fabs(u) > hw || (u * u) / (hw * hw) + (v * v) / (hl * hl) > 1.6f) continue;
          const std::size_t q = static_cast<std::size_t>(yy) * W + xx;
          // A bristle group's place is fixed on the brush, not stretched to
          // the contact: as a brush lifts, fewer bristles touch, at the
          // middle, where before every streak was squeezed towards the
          // centre line and they ran out past the stroke's end as thin hard
          // lines (the owner's report, 12 Nov).
          const int k = std::clamp(int((u / b.span + 1) * 0.5f * kBins), 0, kBins - 1);
          // The brush's flank thins, raggedly: the outer bristles are of
          // uneven length, so the stroke's edge is broken, not ruled.
          const float rag = 0.72f + 0.28f * hash(static_cast<std::uint32_t>(s * 131 + k * 17));
          // Stiff bristles hold a hard edge; soft ones round it off.
          const float edge = std::max(0.0f, 1 - std::pow(std::fabs(u) / (hw * rag + (1 - rag) * hw * 0.6f), 2.0f + 6.0f * stiff));
          // Fading to nothing at the footprint's rounded boundary: a tip
          // that stopped at half strength printed every step as a rung.
          const float tip = std::max(0.0f, 1 - (v * v) / (hl * hl * 1.6f));
          float amount = 0;
          for (int i = 0; i < kInks; i++) amount += P[i * W * H + q];
          const float wet = amount > 1e-5f ? std::exp(-(t - last[q]) / (tau * (1 + thick * amount))) : 0.0f;
          // Wet paint under the core: some into the brush, some shoved to the flank it is nearer.
          // Paint this brush laid a moment ago is the stroke itself, not
          // something it drags through: it is not picked up or shoved
          // aside. (Picking up its own trail kept a brush full for ever, and
          // it never went to dry brush.) Another brush's paint is, however
          // new: two notes of a chord laid side by side at once merge.
          // Within a second and a half: a slow brush (a held note) still has
          // its own paint from a moment ago under it, and at 0.15 s it
          // ploughed that into bow waves. A brush looping back later does
          // drag its earlier stroke.
          const bool own = owner[q] == s && t - last[q] <= 1.5f;
          if (wet > 0.01f && !own) {
            const float core = edge * tip;
            // Stiff bristles plough more and blend less; soft ones lift and mix.
            const float take = kPick * wet * core * per * (1.3f - 0.8f * stiff), push = kPush * wet * core * p * per * (0.6f + 0.8f * stiff);
            // Shoved out past the flank by a varying amount, so the ridge
            // is a bank of paint, not a line.
            // Ploughed by the brush's leading half only, and banked across a
            // spread past the flank (three places, by a third each), not
            // dropped on one pixel: pushing from the whole footprint to one
            // spot every step made boxy patches and a ribbed surface.
            const float lead = v > 0 ? 1.0f : 0.0f;
            const float spill = hw * (0.05f + 0.15f * (0.5f + 0.5f * std::sin(t * 5.3f + s * 1.7f + k * 0.4f)));
            const float side = u >= 0 ? 1.0f : -1.0f;
            std::array<std::size_t, 3> to {};
            int nto = 0;
            for (const float f : { 0.85f, 1.0f, 1.18f }) {
              const float off = side * (hw * f + spill);
              const int ex = int(std::floor(x + nx * off + dx * v)), ey = int(std::floor(y + ny * off + dy * v));
              if (ex >= 0 && ey >= 0 && ex < W && ey < H) to[nto++] = static_cast<std::size_t>(ey) * W + ex;
            }
            for (int i = 0; i < kInks; i++) {
              float& cell = P[i * W * H + q];
              const float tk = cell * take, ps = nto ? cell * push * lead : 0.0f;
              picked[k][i] += tk;
              cell -= tk + ps;
              for (int m = 0; m < nto; m++) P[i * W * H + to[m]] += ps / nto;
            }
            for (int m = 0; m < nto; m++) last[to[m]] = std::max(last[to[m]], last[q]);
          }
          // The deposit: the bin's load and the pressure; a nearly empty bin
          // catches only where the surface stands above the brush's mean.
          float d = kDeposit * p * b.load[k] * edge * tip * per;
          // A lifting brush feathers: under half pressure only some bristle
          // tips still touch, scattered rather than in rows, and each lays
          // less - so the stroke's end breaks up instead of drawing lines.
          if (p < 0.5f) {
            const float touch = hash(static_cast<std::uint32_t>((xx / 2) * 73856093u) ^ static_cast<std::uint32_t>((yy / 2) * 19349663u) ^ static_cast<std::uint32_t>(k * 83492791u));
            d *= std::clamp((p * 2.2f - touch) / 0.25f, 0.0f, 1.0f) * (p * 2);
          }
          // Stiff bristles streak: the groups loaded least starve first.
          d *= 1 - 0.75f * stiff * (1 - b.share[k]);
          // Splayed bristles leave gaps between groups.
          if (hash(static_cast<std::uint32_t>(s * 7 + k * 101)) < 0.35f * splay) d *= 0.12f;
          // A dry drag (noise in the sound) catches only on high points, as
          // an emptying brush does, whatever its load.
          const float effLoad = b.load[k] * (1 - 0.8f * dryness);
          if (effLoad < 0.5f) {
            // The emptier the bin, the higher the surface must stand to take paint from it.
            const float relief = firm(q) - hmean;
            const float need = 0.1f * (1 - effLoad / 0.5f) - 0.03f;
            d *= std::clamp((relief - need) / 0.03f, 0.0f, 1.0f);
          }
          if (d <= 1e-6f) continue;
          // Own paint from this stroke's last moments is neither: it is the stroke.
          if (amount < 1e-4f || own) ontoBare += d;
          else if (wet > 0.3f) intoWet += d;
          else ontoDry += d;
          // Over dry paint the new coat hides what is under it by its own
          // opacity (it is buried, not mixed); over wet paint they mix.
          const float hide = (1 - std::exp(-d / kHide)) * (1 - wet);
          for (int i = 0; i < kInks; i++) {
            float& cell = P[i * W * H + q];
            cell = cell * (1 - hide) + d * b.mix[k][i];
          }
          spent[k] += d;
          // Fresh paint into wet paint makes the mixture as much younger as
          // it is a share of it; onto dry paint or bare canvas it starts its own clock.
          const float frac = d / (amount + d);
          last[q] = wet > 0.01f ? last[q] * (1 - frac) + t * frac : t;
          owner[q] = s;
        }
      for (int k = 0; k < kBins; k++) {
        float got = 0; for (int i = 0; i < kInks; i++) got += picked[k][i];
        if (spent[k] > 0) b.load[k] *= std::exp(-moved / (kReach * w) * p);
        if (got > 0) {
          const float g = got * 0.8f;                     // what the bristles hold, against their load
          const float total = b.load[k] + g;
          for (int i = 0; i < kInks; i++) b.mix[k][i] = (b.mix[k][i] * b.load[k] + picked[k][i] / got * g) / std::max(total, 1e-6f);
          b.load[k] = std::min(total, 2.5f);
        }
      }
      steps++;
      brushSeconds += std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    } else if (cmd == "frame") {
      const auto t0 = std::chrono::steady_clock::now();
      float t; in >> t;
      // Height: the weave, and the paint on it, in pixels of relief.
      const float L[3] = { -0.55f, -0.62f, 0.56f };   // a raking light from the top left
      const std::size_t N = static_cast<std::size_t>(W) * H;
      std::vector<float> h(N);
      for (std::size_t q = 0; q < N; q++) {
        float a = 0; for (int i = 0; i < kInks; i++) a += P[i * N + q];
        h[q] = weave[q] * 0.6f / (1 + a * 6) + a * 3.0f;   // thick paint buries the weave
        cover[q] = 1 - std::exp(-a / kHide);
      }
      for (int y = 0; y < H; y++)
        for (int x = 0; x < W; x++) {
          const std::size_t q = static_cast<std::size_t>(y) * W + x;
          float a = 0; for (int i = 0; i < kInks; i++) a += P[i * N + q];
          float col[3] = { ground[0], ground[1], ground[2] };
          if (a > 1e-6f) {
            for (int c = 0; c < 3; c++) {
              float k = 0; for (int i = 0; i < kInks; i++) k += P[i * N + q] / a * ks[i][c];
              const float R = 1 + k - std::sqrt(k * k + 2 * k);
              col[c] = R * cover[q] + ground[c] * (1 - cover[q]);
            }
          }
          const float hx = h[q + (x < W - 1 ? 1 : 0)] - h[q - (x > 0 ? 1 : 0)];
          const float hy = h[q + (y < H - 1 ? W : 0)] - h[q - (y > 0 ? W : 0)];
          float n[3] = { -hx * 0.5f, -hy * 0.5f, 1 };
          const float nl = std::sqrt(n[0] * n[0] + n[1] * n[1] + 1);
          for (auto& c : n) c /= nl;
          const float dot = n[0] * L[0] + n[1] * L[1] + n[2] * L[2];
          const float shade = std::clamp(0.25f + 0.75f * dot / L[2], 0.35f, 1.6f);
          // Oil glistens while wet: a highlight off the ridges that goes as it dries.
          const float wet = a > 1e-5f ? std::exp(-(t - last[q]) / (tau * (1 + thick * a))) : 0.0f;
          const float hv[3] = { L[0], L[1], L[2] + 1 };
          const float hn2 = std::sqrt(hv[0] * hv[0] + hv[1] * hv[1] + hv[2] * hv[2]);
          const float spec = std::pow(std::max(0.0f, (n[0] * hv[0] + n[1] * hv[1] + n[2] * hv[2]) / hn2), 40.0f) * (0.05f + 0.3f * wet) * cover[q];
          for (int c = 0; c < 3; c++) rgb[q * 3 + c] = static_cast<std::uint8_t>(std::lround(srgb(col[c] * shade + spec) * 255));
        }
      std::fwrite(rgb.data(), 1, rgb.size(), stdout);
      std::fwrite(cover.data(), sizeof(float), cover.size(), stdout);
      std::fflush(stdout);
      frames++;
      renderSeconds += std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    }
  }
  std::fprintf(stderr, "cost steps %ld brush_s %.3f frames %ld render_s %.3f canvas %d %d landed wet %.1f dry %.1f bare %.1f\n", steps,
               brushSeconds, frames, renderSeconds, W, H, intoWet, ontoDry, ontoBare);
  return 0;
}
