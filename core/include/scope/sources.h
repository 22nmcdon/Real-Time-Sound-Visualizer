// The sources the core has ported so far, as the matrix reads them, and the
// generator's struck destinations. Each is the page's `registerSource` or
// `registerDest` entry for it, with the value read from where the core keeps
// it rather than from the page's globals.
//
// - The LFOs, `lfo1` and `lfo2`: read for themselves by the per-sample loop
//   (their `index`), so the matrix only carries the depth.
// - The keyboard's six - Key, Sustain, Notes, Spread, Melody, Inner - which
//   move only when a note does, and so are `stepped`: the fades ease them.
// - Swing again, Kick and Pluck, the three things a hit can strike. Pluck
//   strikes the score's voice at the page's pitch for it (C4); sending it out
//   as MIDI is a later piece.
//
// The rest - the controllers, the macros, the note envelope, the level, the
// hearing and the picture's sources - arrive with the pieces they belong to.

#pragma once

#include <string>
#include <vector>

#include "scope/generator.h"
#include "scope/keyboard.h"
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

// The ported sources, made and registered together, and the generator's
// struck destinations registered beside them.
class CoreSources {
 public:
  CoreSources(Matrix& matrix, Generator& gen, const std::vector<Lfo>& lfos, const Keyboard& keys) {
    for (int i = 0; i < static_cast<int>(lfos.size()); i++) lfo_.emplace_back(i, lfos);
    using K = KeyboardSource::Kind;
    for (const K k : { K::Key, K::Pedal, K::Count, K::Spread, K::Top, K::Inner }) keys_.emplace_back(k, keys);
    for (auto& s : lfo_) matrix.registerSource(&s);
    for (auto& s : keys_) matrix.registerSource(&s);
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

 private:
  // Kept where they were made: the matrix holds pointers to them.
  std::vector<LfoSource> lfo_;
  std::vector<KeyboardSource> keys_;
};

}  // namespace scope
