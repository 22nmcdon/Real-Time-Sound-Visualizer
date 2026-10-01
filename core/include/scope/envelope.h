// The generator's envelope, ported from `makeEnvelope` in web/scope.html.
//
// Plain C++17 with no JUCE in it, because this core is built twice: natively
// for the plugin and to WebAssembly for the website, and the page is the UI
// for both. Anything here that reached for a framework would be one more
// thing the browser build could not have.
//
// It is a port, not a redesign: the same stages, the same pole aimed a fifth
// past the end of each stage, the same legato rule, in the same order of
// operations, so that `core/tests/parity.py` can hold it to the JavaScript
// sample for sample. Where the JavaScript explains why, the explanation is
// there and is not repeated here; where a C++ decision differs, it is said.

#pragma once

#include <cmath>

namespace scope {

// The four numbers of the tone the envelope reads, per sample, so a slider
// moved mid-note takes effect mid-note - as `tone.attackMs` does in the page.
struct EnvelopeTone {
  double attackMs = 5;
  double decayMs = 200;
  double sustain = 1;
  double releaseMs = 200;
};

class Envelope {
 public:
  enum class Stage { Idle, Attack, Decay, Sustain, Release };

  // The tone is read per sample, as the page reads `tone.attackMs`, so it is
  // held by pointer: a voice's envelope has to be movable with the voice.
  Envelope(double rate, const EnvelopeTone& tone) : rate_(rate), tone_(&tone) {}

  double step() {
    switch (stage_) {
      case Stage::Attack:
        value_ += (target_ - value_) * poleFor(tone_->attackMs);
        if (value_ >= end_) { value_ = end_; enterStage(Stage::Decay); }
        break;
      case Stage::Decay:
        value_ += (target_ - value_) * poleFor(tone_->decayMs);
        if (value_ <= end_) { value_ = end_; stage_ = Stage::Sustain; }
        break;
      case Stage::Release:
        value_ += (target_ - value_) * poleFor(tone_->releaseMs);
        if (value_ <= end_) { value_ = end_; stage_ = Stage::Idle; }
        break;
      case Stage::Sustain:
      case Stage::Idle:
        break;  // sustain and idle hold
    }
    return value_ * velocity_;
  }

  // The legato rule: a note arriving while the envelope is open changes
  // nothing, and keeps the velocity of the note that opened it.
  void gate(bool open, double vel) {
    if (!open) {
      if (stage_ != Stage::Idle) enterStage(Stage::Release);
      return;
    }
    if (stage_ == Stage::Idle || stage_ == Stage::Release) {
      velocity_ = vel > 0 ? vel : 1;
      enterStage(Stage::Attack);
    }
  }

  void reset(double to) { stage_ = Stage::Idle; value_ = to; velocity_ = 1; }

  double level() const { return value_ * velocity_; }
  Stage stage() const { return stage_; }

 private:
  static constexpr double kReach = 0.2;

  double poleFor(double ms) const {
    const double samples = std::fmax(1.0, ms * rate_ / 1000.0);
    return 1.0 - std::exp(-span_ / samples);
  }

  void enterStage(Stage next) {
    stage_ = next;
    if (next == Stage::Attack) { target_ = 1 + kReach; end_ = 1; }
    else if (next == Stage::Decay) {
      target_ = tone_->sustain - kReach * (1 - tone_->sustain);
      end_ = tone_->sustain;
    } else if (next == Stage::Release) { target_ = -kReach; end_ = 0; }
    else return;

    const double from = std::fabs(value_ - target_);
    const double to = std::fabs(end_ - target_);
    if (to <= 1e-9 || from <= to) {
      value_ = end_;
      stage_ = next == Stage::Attack ? Stage::Decay : next == Stage::Decay ? Stage::Sustain : Stage::Idle;
      if (stage_ == Stage::Decay) enterStage(Stage::Decay);
      return;
    }
    span_ = std::log(from / to);
  }

  double rate_;
  const EnvelopeTone* tone_;
  Stage stage_ = Stage::Idle;
  double value_ = 1;
  double velocity_ = 1;
  double target_ = 0;
  double end_ = 0;
  double span_ = 1;
};

}  // namespace scope
