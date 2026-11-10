// The sources the core has ported so far, as the matrix reads them, and the
// generator's struck destinations. Each is the page's `registerSource` or
// `registerDest` entry for it, with the value read from where the core keeps
// it rather than from the page's globals.
//
// - The LFOs, `lfo1` and `lfo2`: read for themselves by the per-sample loop
//   (their `index`), so the matrix only carries the depth.
// - The keyboard's six - Key, Sustain, Notes, Spread, Melody, Inner - which
//   move only when a note does, and so are `stepped`: the fades ease them.
// - The learned controllers, `cc.N`, each registered the first frame after
//   the keyboard learns it - and the routes compiled again then, since a
//   routing from a controller that had not moved yet was skipped.
// - The note envelope (`env.note`), read from the generator, as the page
//   reads it from its core. The drawings' six - Swing, Pendulum, Tilt, Turn,
//   Roll and Facing - and the two things a hit could strike, Swing again and
//   Kick, went with the drawings in G2 (Pluck, a third, in P5 with the
//   threshold); the level in F4b.
//
// The morph's fader is the Brain's (restore.h), and the hearing's
// sources are its own (hearing.h); the picture's sources arrive with stage 4.

#pragma once

#include <string>
#include <vector>

#include "scope/generator.h"
#include "scope/keyboard.h"
#include "scope/level.h"
#include "scope/lfo.h"
#include "scope/matrix.h"

namespace scope {

class LfoSource : public ModSource {
 public:
  LfoSource(int i, const std::vector<Lfo>& lfos) : ModSource("lfo" + std::to_string(i + 1)), lfos_(lfos) { index = i; }
  double value() const override { return lfos_[static_cast<std::size_t>(index)].value; }

 private:
  const std::vector<Lfo>& lfos_;
};

class KeyboardSource : public ModSource {
 public:
  // Key alone since F4b (7 Nov): the pedal, pressure as a source and the four
  // readings of the notes held were cut with the matrix's other sources.
  enum class Kind { Key };
  KeyboardSource(Kind kind, const Keyboard& keys) : ModSource(idFor(kind)), kind_(kind), keys_(keys) { stepped = true; }
  double value() const override {
    switch (kind_) {
      case Kind::Key: return keys_.key();
    }
    return 0;
  }
  static const char* idFor(Kind k) {
    switch (k) {
      case Kind::Key: return "midi.key";
    }
    return "";
  }

 private:
  Kind kind_;
  const Keyboard& keys_;
};

// The note envelope: where the generator's ADSR has got to, and nought while
// no keyboard gates it.
class EnvelopeSource : public ModSource {
 public:
  explicit EnvelopeSource(const Generator& gen) : ModSource("env.note"), gen_(gen) {}
  double value() const override { return gen_.gated() ? gen_.envelope() : 0; }

 private:
  const Generator& gen_;
};

// The ported sources, made and registered together.
class CoreSources {
 public:
  CoreSources(Matrix& matrix, const Generator& gen, const std::vector<Lfo>& lfos, const Keyboard& keys) : envelope_(gen) {
    for (int i = 0; i < static_cast<int>(lfos.size()); i++) lfo_.emplace_back(i, lfos);
    using K = KeyboardSource::Kind;
    for (const K k : { K::Key }) keys_.emplace_back(k, keys);
    for (auto& s : lfo_) matrix.registerSource(&s);
    for (auto& s : keys_) matrix.registerSource(&s);
    matrix.registerSource(&envelope_);
  }
  CoreSources(const CoreSources&) = delete;
  CoreSources& operator=(const CoreSources&) = delete;

  // The level, which its owner feeds once a frame with the signal on the screen.
  Level& level() { return level_; }
  const Level& level() const { return level_; }

 private:
  // Kept where they were made: the matrix holds pointers to them.
  std::vector<LfoSource> lfo_;
  std::vector<KeyboardSource> keys_;
  Level level_;
  EnvelopeSource envelope_;
};

}  // namespace scope
