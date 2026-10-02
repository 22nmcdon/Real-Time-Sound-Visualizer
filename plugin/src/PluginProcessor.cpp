#include "PluginProcessor.h"

#include <algorithm>
#include <cstdlib>

#include "PluginEditor.h"

ScopeProcessor::ScopeProcessor()
    : AudioProcessor(BusesProperties().withOutput("Output", juce::AudioChannelSet::stereo(), true)) {}

bool ScopeProcessor::isBusesLayoutSupported(const BusesLayout& layouts) const {
  return layouts.getMainOutputChannelSet() == juce::AudioChannelSet::stereo();
}

void ScopeProcessor::prepareToPlay(double sampleRate, int samplesPerBlock) {
  rate_.store(sampleRate);
  // The page's two LFOs as it starts them.
  lfos_.assign(2, scope::Lfo {});
  lfos_[0].rate = 0.2; lfos_[0].depth = 0.5;
  lfos_[1].rate = 0.5; lfos_[1].depth = 0.3;
  core_ = std::make_unique<scope::Generator>(sampleRate, scope::slot::Used, lfos_);
  notes_ = std::make_unique<scope::GeneratorNotes>(*core_);
  brain_ = std::make_unique<scope::Brain>();
  clockIn_ = std::make_unique<scope::ClockIn>(brain_->clock);
  keyboard_ = std::make_unique<scope::Keyboard>(*notes_, clockIn_.get());
  matrix_ = std::make_unique<scope::Matrix>();
  sources_ = std::make_unique<scope::CoreSources>(*matrix_, *core_, lfos_, *keyboard_);
  nowMs_ = 0;
  lastBlockMs_ = 0;
  scope::linkClock(*brain_, lfos_);
  brainSources_ = std::make_unique<scope::BrainSources>(*matrix_, *brain_);
  /* A host is always a keyboard, so the generator is gated from the start -
     silent until a note - which is what the page's first frame does once a
     keyboard is there. Derived by the keyboard, not set here. */
  keyboard_->setPresent(true);
  /* And the sound the page opens on: its boot preset, loaded as the page loads
     it. SCOPE_PRESET names another, for looking at one in the standalone;
     read once, here, and never on the audio thread. */
  const char* wanted = std::getenv("SCOPE_PRESET");
  const scope::Preset* preset = wanted ? scope::findPreset(wanted) : nullptr;
  if (!preset) preset = scope::findPreset("Harmonic tone");
  if (preset) scope::restoreSetup(preset->setup, *brain_, *core_, *keyboard_, *matrix_, lfos_);
  keyboard_->frame(0);
  const auto size = static_cast<std::size_t>(std::max(64, samplesPerBlock));
  pictureL_.assign(size, 0.0f); pictureR_.assign(size, 0.0f); spare_.assign(size, 0.0f);
  /* For looking at it without a keyboard: SCOPE_HOLD_NOTE=57 holds A3 from
     the start, and SCOPE_HOLD_NOTE=57,64 a fifth on it, so the standalone has
     something to draw. Read once, here, and never on the audio thread. */
  if (const char* held = std::getenv("SCOPE_HOLD_NOTE")) {
    for (const auto& note : juce::StringArray::fromTokens(held, ",", ""))
      keyboard_->noteOn(note.getIntValue(), 127);
  }
}

void ScopeProcessor::render(float* left, float* right, int from, int to) {
  // In pieces no longer than the buffers made for them: a host may hand over
  // a bigger block than it said it would.
  const int most = static_cast<int>(pictureL_.size());
  for (int at = from; at < to; at += most) {
    const int n = std::min(most, to - at);
    float* heardR = right ? right + at : spare_.data();
    core_->block(pictureL_.data(), pictureR_.data(), n, left + at, heardR);
    std::size_t ring = pictureAt_.load(std::memory_order_relaxed);
    for (int k = 0; k < n; ++k) {
      picture_[ring * 2] = pictureL_[static_cast<std::size_t>(k)];
      picture_[ring * 2 + 1] = pictureR_[static_cast<std::size_t>(k)];
      ring = (ring + 1) % kPictureFrames;
    }
    pictureAt_.store(ring, std::memory_order_release);
  }
}

void ScopeProcessor::moveSlider(const std::string& id, double value) {
  scope::moveSlider(id, scope::jsToString(scope::Json::number(value)), *brain_, *core_, *keyboard_, lfos_);
}
void ScopeProcessor::processBlock(juce::AudioBuffer<float>& buffer, juce::MidiBuffer& midi) {
  juce::ScopedNoDenormals noDenormals;
  const int frames = buffer.getNumSamples();
  auto* left = buffer.getWritePointer(0);
  auto* right = buffer.getNumChannels() > 1 ? buffer.getWritePointer(1) : nullptr;
  /* The page's once-a-frame work, once a block and before it: the keyboard's
     controllers walk and its gate and chord are worked out again, the matrix
     steps its fades, fires its events and compiles its routes, the morph
     walks its sliders, and the generator holds those routes across the
     block, as the worklet does. First of all the clock, as in the page's
     frame: the host's transport where it gives one, then the clock's step,
     which sets the locked oscillators' rates. */
  brain_->clock.setNow(nowMs_);
  if (auto* head = getPlayHead()) {
    if (const auto position = head->getPosition()) {
      if (const auto bpm = position->getBpm()) {
        const auto ppq = position->getPpqPosition();
        brain_->clock.host(*bpm, ppq.hasValue() ? std::optional<double>(*ppq) : std::nullopt, position->getIsPlaying(), nowMs_);
      }
    }
  }
  scope::clockFrame(*brain_, *core_, nowMs_);
  keyboard_->frame(lastBlockMs_);
  matrix_->setLayered(keyboard_->layersOn());
  matrix_->setStrikes(keyboard_->strikes());
  matrix_->frame(nowMs_);
  /* After the matrix, so a source on the fader is already counted. A walk
     moves sliders and fires their handlers, which allocate (a slider's value
     is the text the browser would hold): not yet fit for an audio thread,
     and the morph's place is the message thread once there is one to hand
     it to (PLAN.md, stage 2). */
  scope::morphStep(*brain_, *core_, *keyboard_, lfos_);
  core_->setRoutes(matrix_->routes(nowMs_));
  const double blockMs = nowMs_;
  lastBlockMs_ = 1000.0 * frames / rate_.load();
  nowMs_ += lastBlockMs_;
  // Each event at its own sample, not at the top of the block: the generator
  // is run up to it, told, and run on.
  int done = 0;
  for (const auto event : midi) {
    const int at = std::clamp(event.samplePosition, done, frames);
    render(left, right, done, at);
    done = at;
    /* The bytes, not JUCE's reading of them: the keyboard is the page's
       `midiBytes` ported, so a note-on at velocity nought, a controller, the
       pedal and a panic all mean here what they mean on the page. A chord
       handed to the generator is copied there, which can allocate on a note
       - once per layer, and a known cost until the brain's state is fixed in
       size (PLAN.md). */
    clockIn_->at(blockMs + 1000.0 * at / rate_.load());  // a clock byte at its own time
    keyboard_->bytes(event.data, static_cast<std::size_t>(event.numBytes));
  }
  render(left, right, done, frames);
}

std::vector<float> ScopeProcessor::pictureSnapshot() const {
  // Oldest first, so the page reads it as a window of time.
  std::vector<float> out(kPictureFrames * 2);
  const std::size_t at = pictureAt_.load(std::memory_order_acquire);
  for (std::size_t k = 0; k < kPictureFrames; ++k) {
    const std::size_t from = (at + k) % kPictureFrames;
    out[k * 2] = picture_[from * 2];
    out[k * 2 + 1] = picture_[from * 2 + 1];
  }
  return out;
}

juce::AudioProcessorEditor* ScopeProcessor::createEditor() { return new ScopeEditor(*this); }

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter() { return new ScopeProcessor(); }
