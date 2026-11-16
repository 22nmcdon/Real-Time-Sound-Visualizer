"""The options, as switches in a scratch copy of core/include (never the real one)."""
import sys
INC = sys.argv[1]
def sub(path, old, new):
    p = INC + "/scope/" + path
    s = open(p).read()
    assert s.count(old) == 1, (path, old[:60], s.count(old))
    open(p, "w").write(s.replace(old, new))
    print("ok", path, old[:50].replace("\n", " "))
V = "voices.h"; G = "generator.h"
sub(V, "#pragma once\n", """#pragma once
#ifndef OPT_POLY_TURN_OUTER
#define OPT_POLY_TURN_OUTER 0
#endif
#ifndef OPT_POLY_NOLEAN
#define OPT_POLY_NOLEAN 0
#endif
#ifndef OPT_ROLE_MS
#define OPT_ROLE_MS 4
#endif
#ifndef OPT_DYAD_INSTEP
#define OPT_DYAD_INSTEP 0
#endif
#ifndef OPT_XF_MS
#define OPT_XF_MS 0
#endif
#ifndef OPT_DYAD_LEAN
#define OPT_DYAD_LEAN 0
#endif
""")
sub(V, """  const double inner = std::sqrt((1 + kPolyLean * kPolyLean) / 2);  // POLY_INNER
""", """  const double inner = std::sqrt((1 + kPolyLean * kPolyLean) / 2);  // POLY_INNER
  if (OPT_POLY_NOLEAN && role != "xonly" && role != "yonly") return { 1, 1 };
""")
sub(V, """inline bool roundsRole(const std::string& role) { return role == "xy" || role == "u" || innerRole(role); }""",
       """inline bool roundsRole(const std::string& role) { return OPT_POLY_TURN_OUTER || OPT_POLY_NOLEAN ? (role != "xonly" && role != "yonly") : (role == "xy" || role == "u" || innerRole(role)); }""")
sub(G, "const double roleGlide = poleFor(4, rate_);", "const double roleGlide = poleFor(OPT_ROLE_MS, rate_);")
# Dyad: the right channel's change of note crossfaded, put back in step, and leaned.
sub(G, """        if (clockReset) { phaseL_ = 0; phaseR_ = 0; }
        phaseL_ += kTwoPi * hz * dt;""", """        if (clockReset) { phaseL_ = 0; phaseR_ = 0; }
        const double optBase = intervalRatio(a_.interval, a_.just) * octave;
        if (optRatio_ == 0) optRatio_ = optBase;
        if (optBase != optRatio_ && (OPT_XF_MS > 0 || OPT_DYAD_INSTEP)) {
          optOldRatio_ = optRatio_; optOldPhase_ = phaseR_; optOldOsc_ = oscR_; optX_ = 0;
          if (OPT_DYAD_INSTEP) phaseR_ = std::fmod(phaseL_ * optBase, kPhaseWrap);
        }
        optRatio_ = optBase;
        const double optPairTo = optBase != 1 ? 1 : 0;
        if (OPT_XF_MS > 0) optPair_ += (optPairTo - optPair_) * std::fmin(1.0, 1000 * dt / OPT_XF_MS);
        else optPair_ = optPairTo;
        phaseL_ += kTwoPi * hz * dt;""")
sub(G, """          wl = waveAt(a_.shape, phaseL_, stepL, bars, amount);
          wr = waveAt(a_.shape, phaseR_ + phase, stepR, bars, amount);
          if (vxA_.scanW > 0) {
            wl = scanMix(wl, vxA_.scanPrev, vxA_.scanNext, phaseL_, stepL, vxA_.scanX, vxA_.scanW);
            wr = scanMix(wr, vxA_.scanPrev, vxA_.scanNext, phaseR_ + phase, stepR, vxA_.scanX, vxA_.scanW);
          }
""", """          wl = waveAt(a_.shape, phaseL_, stepL, bars, amount);
          wr = waveAt(a_.shape, phaseR_ + phase, stepR, bars, amount);
          if (vxA_.scanW > 0) {
            wl = scanMix(wl, vxA_.scanPrev, vxA_.scanNext, phaseL_, stepL, vxA_.scanX, vxA_.scanW);
            wr = scanMix(wr, vxA_.scanPrev, vxA_.scanNext, phaseR_ + phase, stepR, vxA_.scanX, vxA_.scanW);
          }
          auto optWave = [&](double ph, double st) {
            double w = waveAt(a_.shape, ph, st, bars, amount);
            return vxA_.scanW > 0 ? scanMix(w, vxA_.scanPrev, vxA_.scanNext, ph, st, vxA_.scanX, vxA_.scanW) : w;
          };
          if (OPT_XF_MS > 0 && optX_ < 1) {
            optOldPhase_ += kTwoPi * hz * optOldRatio_ * dt;
            if (optOldPhase_ >= kPhaseWrap) optOldPhase_ -= kPhaseWrap;
            const double old = optWave(optOldPhase_ + phase, std::fabs(hz * optOldRatio_) / rate_);
            optX_ = std::fmin(1.0, optX_ + 1000 * dt / OPT_XF_MS);
            wr = std::sin(kPi / 2 * optX_) * wr + std::cos(kPi / 2 * optX_) * old;
          }
          if (OPT_DYAD_LEAN > 0) {
            // The bass's own quarter turn kept in the right, and the upper note's own left, at the lean.
            const double k = OPT_DYAD_LEAN * optPair_;
            const double wq = optWave(phaseL_ + phase, stepL), wu = optWave(phaseR_, stepR);
            wl += k * wu; wr += k * wq;
          }
""")
sub(G, "  double phaseL_ = 0, phaseR_ = 0;\n", "  double phaseL_ = 0, phaseR_ = 0;\n  double optRatio_ = 0, optOldRatio_ = 1, optOldPhase_ = 0, optX_ = 1, optPair_ = 0;\n  Osc optOldOsc_;\n")
