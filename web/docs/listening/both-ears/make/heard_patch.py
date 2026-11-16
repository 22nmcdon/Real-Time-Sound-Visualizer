"""Way 1 and Way 2 as compile-time switches in a scratch copy of core/include (never the real one).

  OPT_HEARD=1  Way 1: what is drawn is untouched; what is heard is a mix of the same voices, each
               voice in both ears, its left a fraction OPT_K of a quarter of its period behind its
               right (0 the same in both ears, 0.5 an eighth, 1 the quarter turn), through a second
               plane set exactly as the first.
  OPT_W2=1     Way 2: that mix at OPT_K=1 is what is drawn as well (and so heard).
Both off, the copy is the core: checked to the bit by heard_proof.py.
Each replacement is asserted to match once and written at once (CLAUDE.md)."""
import sys
INC = sys.argv[1]
def sub(path, old, new):
    p = INC + "/scope/" + path
    s = open(p).read()
    assert s.count(old) == 1, (path, old[:70], s.count(old))
    open(p, "w").write(s.replace(old, new))
    print("ok", path, old[:50].replace("\n", " "))
V, G = "voices.h", "generator.h"
sub(V, "#pragma once\n", """#pragma once
#ifndef OPT_HEARD
#define OPT_HEARD 0
#endif
#ifndef OPT_W2
#define OPT_W2 0
#endif
#ifndef OPT_K
#define OPT_K 1.0
#endif
#ifndef OPT_UFADE_MS
#define OPT_UFADE_MS 10
#endif
""")
# Poly: each voice's own image, into c.hmix, from a ring of its own.
sub(V, "  std::array<double, 2> mix {};  // left and right, drawn and heard\n",
       "  std::array<double, 2> mix {};  // left and right, drawn and heard\n  std::array<double, 2> hmix {};  // OPT: each voice's own image, summed\n")
sub(V, "  std::vector<double> ring;  // the quarter turn's, made the first time it turns\n",
       "  std::vector<double> ring;  // the quarter turn's, made the first time it turns\n  std::vector<double> hring; int hat = 0;  // OPT\n")
sub(V, "  c.mix = { 0, 0 };\n  for (auto& voice : voices) {", "  c.mix = { 0, 0 };\n  c.hmix = { 0, 0 };\n  for (auto& voice : voices) {")
sub(V, """    auto& g = voice.gains;
    const auto& t = voice.targets;""", """    if (OPT_HEARD || OPT_W2) {
      // OPT: the voice in both ears, its left OPT_K of a quarter period behind, whatever else is held.
      if (voice.hring.empty()) { voice.hring.assign(kRoundRing, 0.0); voice.hat = 0; }
      voice.hring[static_cast<std::size_t>(voice.hat)] = a;
      double lateH = a;
      if (OPT_K > 0) {
        const double back = std::fmin(kRoundRing - 2, f > 0 ? OPT_K * c.rate / (4 * std::fabs(f)) : 0);
        const int whole = static_cast<int>(std::floor(back));
        const double part = back - whole;
        const int i0 = (voice.hat - whole + kRoundRing) % kRoundRing, i1 = (i0 - 1 + kRoundRing) % kRoundRing;
        lateH = voice.hring[static_cast<std::size_t>(i0)]
              + (voice.hring[static_cast<std::size_t>(i1)] - voice.hring[static_cast<std::size_t>(i0)]) * part;
      }
      voice.hat = (voice.hat + 1) % kRoundRing;
      c.hmix[0] += lateH; c.hmix[1] += a;
    }
    auto& g = voice.gains;
    const auto& t = voice.targets;""")
# Generator: the second plane, set and stepped as the first.
sub(G, "plane_(rate), ctx_(rate),", "plane_(rate), planeH_(rate), ctx_(rate),")
sub(G, "  Plane plane_;\n", "  Plane plane_;\n  Plane planeH_;  // OPT: the heard mix's, set as plane_\n"
       "  struct HChain { Shaper shp; Crush cr; VcfState vcf; HChain() : shp(2, lowpassTaps(2)) {} };\n"
       "  std::array<HChain, 4> hch_;\n  double hPhaseU_ = 0, hRatioU_ = 1, hU_ = 0, optFl_ = 0;\n")
sub(G, """    plane_.setSwitchStep(switchStep, switchPrime);
    const bool planeOn = plane_.setup(a_, twistRouted, echoRouted, layered && (b_.planeOwn || timeOwn != 0) ? &b_ : nullptr,""",
"""    planeH_.setSwitchStep(switchStep, switchPrime);
    planeH_.setup(a_, twistRouted, echoRouted, layered && (b_.planeOwn || timeOwn != 0) ? &b_ : nullptr,
                                      b_.planeTurn, turnRouted, phaserRouted, reverbRouted, b_.planeOwn, timeOwn);
    plane_.setSwitchStep(switchStep, switchPrime);
    const bool planeOn = plane_.setup(a_, twistRouted, echoRouted, layered && (b_.planeOwn || timeOwn != 0) ? &b_ : nullptr,""")
sub(G, "      plane_.settleSwitch();\n    }\n    // The bend's", "      plane_.settleSwitch();\n      planeH_.settleSwitch();\n    }\n    // The bend's")
sub(G, "    plane_.tick(a_, a, dt, &b_, b);\n", "    plane_.tick(a_, a, dt, &b_, b);\n    planeH_.tick(a_, a, dt, &b_, b);\n")
sub(G, """      shapeL_ = Shaper(wantShape, wantShape == 4 ? ctx_.taps4 : ctx_.taps2);""",
"""      shapeL_ = Shaper(wantShape, wantShape == 4 ? ctx_.taps4 : ctx_.taps2);
      for (auto& h : hch_) h.shp = Shaper(wantShape, wantShape == 4 ? ctx_.taps4 : ctx_.taps2);""")
sub(G, "      double l, r;\n\n      if (poly) {", "      double l, r, optHL = 0, optHR = 0;\n\n      if (poly) {")
sub(G, "        l = ctx_.mix[0]; r = ctx_.mix[1];\n",
       "        l = ctx_.mix[0]; r = ctx_.mix[1];\n        optHL = ctx_.hmix[0]; optHR = ctx_.hmix[1];\n        if (OPT_W2) { l = optHL; r = optHR; }\n")
sub(G, "          const double fl = gated_ ? fenv_.step() : 0;\n", "          const double fl = gated_ ? fenv_.step() : 0;\n          optFl_ = fl;\n")
sub(G, """        l = amp * wl;
        r = amp * wr;
      }
""", """        l = amp * wl;
        r = amp * wr;
        if ((OPT_HEARD || OPT_W2) && !a_.noise && !vxA_.on) {
          // OPT: the dyad as two voices, the lower on phaseL_, the upper on a phase of its own kept from
          // phaseR_ while the interval is not a unison, each in both ears with its own image; the upper
          // faded in and out over OPT_UFADE_MS, since it no longer turns into the lower note.
          const double base = intervalRatio(a_.interval, a_.just) * octave;
          const bool two = base != 1;
          if (two) { hRatioU_ = ratio; hPhaseU_ = phaseR_; }
          else {
            hPhaseU_ += kTwoPi * hz * hRatioU_ * dt;
            if (hPhaseU_ >= kPhaseWrap) hPhaseU_ -= kPhaseWrap;
            if (hPhaseU_ < 0) hPhaseU_ += kPhaseWrap;
          }
          const double fstep = 1000 * dt / OPT_UFADE_MS;
          hU_ = two ? std::fmin(1.0, hU_ + fstep) : std::fmax(0.0, hU_ - fstep);
          auto hw = [&](double ph, double st) {
            double w = waveAt(a_.shape, ph, st, bars, amount);
            return vxA_.scanW > 0 ? scanMix(w, vxA_.scanPrev, vxA_.scanNext, ph, st, vxA_.scanX, vxA_.scanW) : w;
          };
          auto chain = [&](HChain& c, double w, double f) {
            if (vxA_.shapeRun) {
              if (vxA_.shapeFresh) c.shp.clear();
              w = switchBlend(w, c.shp.step(w, ctx_.shaping), vxA_.shapeW);
            }
            if (vxA_.crushing) w = crushStep(c.cr, w, a_, vxA_, rate_);
            if (vxA_.filtering) w = svfStep(c.vcf, w, vcfCoef(c.vcf, a_, f, optFl_, vxA_.vcfPush, vxA_.cut, rate_), vxA_.vcfK, a_.vcfType);
            return w;
          };
          // The right leads by the Phase (a quarter by default), scaled by OPT_K, as a lone note's does.
          const double dR = (OPT_W2 ? 1.0 : OPT_K) * phase;
          const double stepU = std::fabs(hz * hRatioU_) / rate_;
          const double bL = chain(hch_[0], hw(phaseL_, stepL), hz);
          const double bR = chain(hch_[1], hw(phaseL_ + dR, stepL), hz);
          const double uL = chain(hch_[2], hw(hPhaseU_, stepU), hz * hRatioU_);
          const double uR = chain(hch_[3], hw(hPhaseU_ + dR, stepU), hz * hRatioU_);
          const double gU = 0.5 - 0.5 * std::cos(kPi * hU_);
          optHL = amp * (bL + gU * uL);
          optHR = amp * (bR + gU * uR);
          if (OPT_W2) { l = optHL; r = optHR; }
        } else { optHL = l; optHR = r; }
      }
""")
sub(G, """      if (inMode == 2) {
        const double g = 1 + inDepth * 2 * xin;
        l *= g; r *= g;
      }
""", """      if (inMode == 2) {
        const double g = 1 + inDepth * 2 * xin;
        l *= g; r *= g; optHL *= g; optHR *= g;
      }
""")
sub(G, """        plane_.step(Plane::A, l, r); l = plane_.x; r = plane_.y;
      }""", """        plane_.step(Plane::A, l, r); l = plane_.x; r = plane_.y;
        if (OPT_HEARD) { planeH_.step(Plane::A, optHL, optHR); optHL = planeH_.x; optHR = planeH_.y; }
      }""")
sub(G, "        double hl = outL[i] + bx + scored, hr = outR[i] + by + scored;\n",
       "        double hl = (OPT_HEARD ? optHL : outL[i]) + bx + scored, hr = (OPT_HEARD ? optHR : outR[i]) + by + scored;\n")
