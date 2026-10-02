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
// - Swing again, Kick and Pluck, the three things a hit can strike. Pluck
//   strikes the score's voice at the page's pitch for it (C4); the Brain's
//   sources replace it with the setup's pitch, sent out as MIDI.
//
// The macros and the threshold are the Brain's (restore.h), and the hearing's
// are its own (hearing.h); the picture's sources arrive with stage 4.

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
  enum class Kind { Key, Pedal, Count, Spread, Top, Inner };
  KeyboardSource(Kind kind, const Keyboard& keys) : ModSource(idFor(kind)), kind_(kind), keys_(keys) { stepped = true; }
  double value() const override {
    switch (kind_) {
      case Kind::Key: return keys_.key();
      case Kind::Pedal: return keys_.pedal();
      case Kind::Count: return keys_.notesCount();
      case Kind::Spread: return keys_.notesSpread();
      case Kind::Top: return keys_.notesTop();
      case Kind::Inner: return keys_.notesInner();
    }
    return 0;
  }
  static const char* idFor(Kind k) {
    switch (k) {
      case Kind::Key: return "midi.key";
      case Kind::Pedal: return "midi.pedal";
      case Kind::Count: return "notes.count";
      case Kind::Spread: return "notes.spread";
      case Kind::Top: return "notes.top";
      case Kind::Inner: return "notes.inner";
    }
    return "";
  }

 private:
  Kind kind_;
  const Keyboard& keys_;
};

// A learned controller, read by its number: the keyboard's list is the truth,
// and a rename or a value reaches the matrix without either knowing.
class ControllerSource : public ModSource {
 public:
  ControllerSource(int number, const Keyboard& keys) : ModSource("cc." + std::to_string(number)), number_(number), keys_(keys) {}
  double value() const override {
    for (const auto& c : keys_.controllers()) if (c.number == number_) return c.value;
    return 0;
  }
  int number() const { return number_; }

 private:
  int number_;
  const Keyboard& keys_;
};

// The level, how loud the signal on the screen is.
class LevelSource : public ModSource {
 public:
  explicit LevelSource(const Level& level) : ModSource("env.live"), level_(level) {}
  double value() const override { return level_.value(); }

 private:
  const Level& level_;
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
    for (const K k : { K::Key, K::Pedal, K::Count, K::Spread, K::Top, K::Inner }) keys_.emplace_back(k, keys);
    using D = DrawingSource::Kind;
    for (const D k : { D::Swing, D::Pendulum, D::TurnX, D::TurnY, D::TurnZ, D::Facing }) drawing_.emplace_back(k, gen);
    for (auto& s : lfo_) matrix.registerSource(&s);
    for (auto& s : keys_) matrix.registerSource(&s);
    for (auto& s : drawing_) matrix.registerSource(&s);
    matrix.registerSource(&levelSource_);
    matrix.registerSource(&envelope_);
    // Room for every controller there is, so the matrix's pointers stay put.
    controllers_.reserve(128);
    const auto struck = [&](const char* id, std::function<void(double)> fire) {
      ModDest d;
      d.id = id; d.kind = DestKind::Event; d.fire = std::move(fire);
      matrix.registerDest(std::move(d));
    };
    Generator* g = &gen;
    struck("gen.reswing", [g](double) { g->reswing(); });
    struck("gen.kick", [g](double amount) { g->kick(amount); });
    struck("gen.pluck", [g](double amount) { g->strike(midiHz(kPluckNote), std::fmax(0.0, std::fmin(1.0, std::fabs(amount)))); });
  }
  CoreSources(const CoreSources&) = delete;
  CoreSources& operator=(const CoreSources&) = delete;

  static constexpr int kPluckNote = 60;  // pluck.note

  // midiLearn's registration, once a frame: a controller the keyboard has
  // learned since the last becomes a source, and the routes are compiled
  // again so a routing that was skipped without it is heard. The page did
  // not compile them again until it was fixed for this port.
  void learn(Matrix& matrix, const Keyboard& keys) {
    bool added = false;
    for (const auto& c : keys.controllers()) {
      bool known = false;
      for (const auto& s : controllers_) known = known || s.number() == c.number;
      if (known || controllers_.size() == controllers_.capacity()) continue;
      controllers_.emplace_back(c.number, keys);
      matrix.registerSource(&controllers_.back());
      added = true;
    }
    if (added) matrix.touch();
  }

  // The level, which its owner feeds once a frame with the signal on the screen.
  Level& level() { return level_; }
  const Level& level() const { return level_; }

 private:
  // Kept where they were made: the matrix holds pointers to them.
  std::vector<LfoSource> lfo_;
  std::vector<KeyboardSource> keys_;
  std::vector<DrawingSource> drawing_;
  std::vector<ControllerSource> controllers_;
  Level level_;
  LevelSource levelSource_ { level_ };
  EnvelopeSource envelope_;
};

}  // namespace scope
