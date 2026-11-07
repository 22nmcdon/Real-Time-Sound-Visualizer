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
// - The level (`env.live`), the note envelope (`env.note`) and the drawings'
//   six - Swing, Pendulum, Tilt, Turn, Roll and Facing - read from the
//   generator, as the page reads them from its core.
// - Swing again and Kick, the two things a hit can strike. Pluck, a third,
//   went in P5 with the threshold.
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

// What the harmonograph and a solid are doing (drawingNow): nought from a
// drawing that is not the one playing, as the generator reports it.
class DrawingSource : public ModSource {
 public:
  enum class Kind { Swing, Pendulum, TurnX, TurnY, TurnZ, Facing };
  DrawingSource(Kind kind, const Generator& gen) : ModSource(idFor(kind)), kind_(kind), gen_(gen) {}
  double value() const override {
    const auto d = gen_.drawing();
    switch (kind_) {
      case Kind::Swing: return d.swing;
      case Kind::Pendulum: return d.pendulum;
      case Kind::TurnX: return d.turn[0];
      case Kind::TurnY: return d.turn[1];
      case Kind::TurnZ: return d.turn[2];
      case Kind::Facing: return d.facing;
    }
    return 0;
  }
  static const char* idFor(Kind k) {
    switch (k) {
      case Kind::Swing: return "draw.swing";
      case Kind::Pendulum: return "draw.pendulum";
      case Kind::TurnX: return "draw.turnX";
      case Kind::TurnY: return "draw.turnY";
      case Kind::TurnZ: return "draw.turnZ";
      case Kind::Facing: return "draw.facing";
    }
    return "";
  }

 private:
  Kind kind_;
  const Generator& gen_;
};

// The ported sources, made and registered together, and the generator's
// struck destinations registered beside them.
class CoreSources {
 public:
  CoreSources(Matrix& matrix, Generator& gen, const std::vector<Lfo>& lfos, const Keyboard& keys) : envelope_(gen) {
    for (int i = 0; i < static_cast<int>(lfos.size()); i++) lfo_.emplace_back(i, lfos);
    using K = KeyboardSource::Kind;
    for (const K k : { K::Key }) keys_.emplace_back(k, keys);
    using D = DrawingSource::Kind;
    for (const D k : { D::Swing, D::Pendulum, D::TurnX, D::TurnY, D::TurnZ, D::Facing }) drawing_.emplace_back(k, gen);
    for (auto& s : lfo_) matrix.registerSource(&s);
    for (auto& s : keys_) matrix.registerSource(&s);
    for (auto& s : drawing_) matrix.registerSource(&s);
    matrix.registerSource(&envelope_);
    const auto struck = [&](const char* id, std::function<void(double)> fire) {
      ModDest d;
      d.id = id; d.kind = DestKind::Event; d.fire = std::move(fire);
      matrix.registerDest(std::move(d));
    };
    Generator* g = &gen;
    struck("gen.reswing", [g](double) { g->reswing(); });
    struck("gen.kick", [g](double amount) { g->kick(amount); });
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
  std::vector<DrawingSource> drawing_;
  Level level_;
  EnvelopeSource envelope_;
};

}  // namespace scope
