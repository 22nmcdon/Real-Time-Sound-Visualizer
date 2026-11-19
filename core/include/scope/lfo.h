// The page's two LFOs, ported from `lfoStep` in web/scope.html: a phase run
// at `rate` hertz and read through `waveAt`, or, for the random shape, a
// level drawn once a cycle and held. Advanced once a sample whether or not
// anything is patched from it, so its phase does not jump when something is.
//
// Since 19 Nov (web/docs/lfo-drawn.md) a shape can also be drawn: points
// round one cycle (lfo_shape.h), read at the same phase. The path today's
// five shapes take is the code it always was, untouched while `drawn` is
// false: that is the whole of the claim that an old setup plays as it did.

#pragma once

#include <array>
#include <cmath>
#include <string_view>

#include "scope/lfo_shape.h"
#include "scope/noise.h"
#include "scope/wave.h"

namespace scope {

struct Lfo {
  Shape shape = Shape::Sine;
  bool random = false;  // the page's "random": sample and hold, once a cycle
  double rate = 0.2, depth = 0.5, phase = 0, held = 0, value = 0;
  int epoch = 0;

  /* The drawn shape (l<i>s "drawn", its text l<i>m). `wantsDrawn` is what
     the shape menu says; `drawn` is whether a shape is playing it, so a
     "drawn" with no text that reads plays the sine rather than nothing. */
  bool wantsDrawn = false, drawn = false;
  LfoShape pts;
  // Where in the cycle the shape is read from (l<i>p, as a share), and when it starts again (l<i>t).
  double phase0 = 0;
  char starts = 0;  // 0 free, 'n' each note, 'p' each phrase
  // The drawn engine's state: each point's level this pass, and the line it is on and where that began.
  std::array<double, kLfoMaxPoints> lv {};
  int segI = 0;
  double segA = 0;

  void setShape(std::string_view name);
  void setDrawn(std::string_view text);
  void setPhase0(double share);
};

// Where the shape is read: the core's cycleOf, moved on by Phase. Not
// fmod(t + p, 1) + 1 and so on, which adds 1 and loses a small t's low bits:
// the saw's twin was 2.2e-16 off lfo.h that way in the mockup.
inline double lfoReadU(const Lfo& l) {
  const double u = cycleOf(l.phase) + l.phase0;
  return u >= 1 ? u - 1 : u;
}

/* The level at u along the line from point i, which began at a. */
inline double lfoLevelOf(const Lfo& l, double u, double a, int i) {
  const LfoShape& s = l.pts;
  const int j = (i + 1) % s.n;
  const double len = lfoSegLen(s, i);
  if (len <= 0) return l.lv[static_cast<std::size_t>(j)];
  double du = u - s.p[static_cast<std::size_t>(i)].x;
  if (du < 0) du += 1;
  return lfoLaw(s.p[static_cast<std::size_t>(i)], a, l.lv[static_cast<std::size_t>(j)], du / len);
}

// Each point at its drawn level, a random one at nought until its first level is drawn, as today's held is.
inline void lfoDrawnInit(Lfo& l) {
  for (int k = 0; k < l.pts.n; ++k) {
    const LfoPoint& p = l.pts.p[static_cast<std::size_t>(k)];
    l.lv[static_cast<std::size_t>(k)] = p.r ? 0 : p.y;
  }
  l.segI = lfoSegAt(l.pts, lfoReadU(l));
  l.segA = l.lv[static_cast<std::size_t>(l.segI)];
}

inline void Lfo::setShape(std::string_view name) {
  const bool was = drawn, wasRandom = random;
  wantsDrawn = name == "drawn";
  random = name == "random";
  // A drawn shape's fallback is the sine, should its text not read.
  shape = wantsDrawn ? Shape::Sine : shapeNamed(name);
  drawn = wantsDrawn && pts.n > 0;
  if (drawn && !was) {
    /* Adopted (the first edit of one of today's shapes, or a setup that
       plays a drawn one): from the drawn levels where the phase is now, and
       today's Random's held level kept on the point it is on, so the twin
       takes over where today's left off rather than at nought. */
    lfoDrawnInit(*this);
    const LfoPoint& on = pts.p[static_cast<std::size_t>(segI)];
    if (wasRandom && on.r) { lv[static_cast<std::size_t>(segI)] = held; segA = held; }
  }
}

/* A new text: the shape it reads. While it plays, each point not random takes
   its new level and a random one keeps the level it has this pass, within its
   new reach - an edit moves the line, and does not roll the dice again. */
inline void Lfo::setDrawn(std::string_view text) {
  LfoShape next;
  lfoShapeRead(text, next);
  const bool same = next.n == pts.n;
  pts = next;
  const bool was = drawn;
  drawn = wantsDrawn && pts.n > 0;
  if (!drawn) return;
  if (!was || !same) { lfoDrawnInit(*this); return; }
  for (int k = 0; k < pts.n; ++k) {
    const LfoPoint& p = pts.p[static_cast<std::size_t>(k)];
    double& v = lv[static_cast<std::size_t>(k)];
    v = p.r ? std::fmax(-std::fabs(p.y), std::fmin(std::fabs(p.y), v)) : p.y;
  }
  segI = lfoSegAt(pts, lfoReadU(*this));
  segA = lv[static_cast<std::size_t>(segI)];
}

inline void Lfo::setPhase0(double share) {
  phase0 = share >= 0 && share < 1 ? share : 0;
  if (drawn) { segI = lfoSegAt(pts, lfoReadU(*this)); segA = lv[static_cast<std::size_t>(segI)]; }
}

/* A random point's new level, within its reach. The draw is lfoStep's
   (random() * 2 - 1) and the reach multiplies it after, so a reach of 1 is
   today's Random to the bit (times one is exact). */
inline double lfoLanding(const LfoPoint& p, Random& random) { return (random.next() * 2 - 1) * std::fabs(p.y); }

/* Point k passed. A random point after a hold or a jump takes its new level
   now; the line from it starts at its level; and if the next point is random
   and the line to it moves, the next point takes its level now, so the line
   aims at where it will land. One random point, held, so draws at the same
   sample as lfoStep draws `held`: that is why the drawn Random steps is
   today's to the bit, and rolling a line early (the null) is not. */
inline void lfoCross(Lfo& l, int k, Random& random) {
  const LfoShape& s = l.pts;
  const int n = s.n, before = (k - 1 + n) % n, j = (k + 1) % n;
  const LfoPoint& p = s.p[static_cast<std::size_t>(k)];
  if (p.r && (s.p[static_cast<std::size_t>(before)].law == 'h' || lfoSegLen(s, before) <= 0))
    l.lv[static_cast<std::size_t>(k)] = lfoLanding(p, random);
  l.segI = k;
  l.segA = l.lv[static_cast<std::size_t>(k)];
  if (s.p[static_cast<std::size_t>(j)].r && p.law != 'h' && lfoSegLen(s, k) > 0)
    l.lv[static_cast<std::size_t>(j)] = lfoLanding(s.p[static_cast<std::size_t>(j)], random);
}

/* The drawn engine, a sample: the phase runs exactly as lfoStep's (the same
   increment and the same wrap), and the points passed since the last sample
   are crossed in the order they were passed - across the wrap, those after
   where it was and then those up to where it is. */
inline double lfoDrawnStep(Lfo& lfo, double rate, Random& random) {
  const double u0 = lfoReadU(lfo);
  lfo.phase += kTwoPi * lfo.rate / rate;
  if (lfo.phase >= kTwoPi) lfo.phase -= kTwoPi;
  const double u1 = lfoReadU(lfo);
  const LfoShape& s = lfo.pts;
  if (u1 >= u0) {
    for (int k = 0; k < s.n; ++k) { const double x = s.p[static_cast<std::size_t>(k)].x; if (x > u0 && x <= u1) lfoCross(lfo, k, random); }
  } else {
    for (int k = 0; k < s.n; ++k) if (s.p[static_cast<std::size_t>(k)].x > u0) lfoCross(lfo, k, random);
    for (int k = 0; k < s.n; ++k) if (s.p[static_cast<std::size_t>(k)].x <= u1) lfoCross(lfo, k, random);
  }
  lfo.value = lfoLevelOf(lfo, u1, lfo.segA, lfo.segI);
  return lfo.value;
}

inline double lfoStep(Lfo& lfo, double rate, Random& random) {
  if (lfo.drawn) return lfoDrawnStep(lfo, rate, random);
  lfo.phase += kTwoPi * lfo.rate / rate;
  if (lfo.phase >= kTwoPi) {
    lfo.phase -= kTwoPi;
    lfo.held = random.next() * 2 - 1;
  }
  lfo.value = lfo.random ? lfo.held : waveAt(lfo.shape, lfo.phase);
  // Phase (19 Nov) moves where today's shapes are read; at nought, the line above is the whole of it.
  if (lfo.phase0 != 0 && !lfo.random) lfo.value = waveAt(lfo.shape, lfo.phase + kTwoPi * lfo.phase0);
  return lfo.value;
}

/* Back to the top of the cycle: Phase is where that reads, and a drawn shape
   starts again from its drawn levels there. A lock to the tempo, a note on
   Each note, the first of a phrase on Each phrase. */
inline void lfoRestart(Lfo& lfo) {
  lfo.phase = 0;
  if (lfo.drawn) lfoDrawnInit(lfo);
}

}  // namespace scope
