#include "PluginProcessor.h"

#include <algorithm>
#include <cmath>
#include <cstdlib>

#include "PluginEditor.h"

ScopeProcessor::ScopeProcessor()
    : AudioProcessor(BusesProperties().withOutput("Output", juce::AudioChannelSet::stereo(), true)) {
  for (std::size_t i = 0; i < kKnobs.size(); ++i) {
    const auto* spec = scope::rangeSpec(kKnobs[i].slider);
    knobs_[i] = new juce::AudioParameterFloat(juce::ParameterID { kKnobs[i].id, 1 }, kKnobs[i].name,
                                              juce::NormalisableRange<float>(static_cast<float>(spec->min), static_cast<float>(spec->max),
                                                                             static_cast<float>(spec->step)),
                                              static_cast<float>(spec->value));
    addParameter(knobs_[i]);
  }
}

void ScopeProcessor::load(const scope::Json& setup) {
  setup_ = setup;
  scope::restoreSetup(setup_, *brain_, *core_, *keyboard_, *matrix_, lfos_);
  for (std::size_t i = 0; i < kKnobs.size(); ++i) {
    const auto v = static_cast<float>(brain_->panel.range(kKnobs[i].slider));
    knobs_[i]->setValueNotifyingHost(knobs_[i]->convertTo0to1(v));
    applied_[i] = knobs_[i]->get();
  }
}

void ScopeProcessor::applyKnobs() {
  /* As a hand on the slider: the value written as the browser would hold it,
     the slider's handler run. Which allocates, as the morph's walk does, and
     moves with it to the message thread (PLAN.md, stage 2). */
  for (std::size_t i = 0; i < kKnobs.size(); ++i) {
    const float v = knobs_[i]->get();
    if (v == applied_[i]) continue;
    applied_[i] = v;
    scope::moveSlider(kKnobs[i].slider, scope::jsToString(scope::Json::number(v)), *brain_, *core_, *keyboard_, lfos_);
  }
}

void ScopeProcessor::getStateInformation(juce::MemoryBlock& out) {
  const juce::SpinLock::ScopedLockType lock(stateLock_);
  if (!brain_) return;
  /* The setup as loaded, and over it what has moved: each parameter's slider
     as the page's snapshot writes it, and the controllers learned. */
  scope::Json setup = setup_.type == scope::Json::Type::Object ? setup_ : scope::Json::object();
  for (const auto& k : kKnobs) setup.set(k.key, scope::Json::number(brain_->panel.range(k.slider)));
  setup.set("cc", scope::Json::string(std::string_view(keyboard_->encodeCC())));
  if (const auto code = scope::encodeSetup(setup)) out.append(code->data(), code->size());
}

void ScopeProcessor::setStateInformation(const void* data, int size) {
  const auto decoded = scope::decodeSetup(std::string_view(static_cast<const char*>(data), static_cast<std::size_t>(size)));
  if (decoded.kind != scope::DecodedSetup::Kind::Read) return;
  const juce::SpinLock::ScopedLockType lock(stateLock_);
  pending_ = decoded.setup;
}

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
  /* What it hears is the picture, which is always the generator's: every
     hearing source is a loop here, with the picture's reach, and the onset
     is refused anything it could strike. */
  hearing_ = std::make_unique<scope::HearingSources>(*matrix_);
  hearing_->hears(true);
  nowMs_ = 0;
  lastBlockMs_ = 0;
  scope::linkClock(*brain_, lfos_);
  /* The page's MIDI out, a port chosen once and for good: the host's MIDI out
     is always there, and whether anything listens to it is the host's
     routing. Channel 1, the page's default; the page's menu for it is not the
     plugin's yet. */
  midiOut_ = std::make_unique<scope::MidiOut>([this](const std::uint8_t* bytes, int length) {
    outgoing_.addEvent(bytes, length, outAt_);
  });
  midiOut_->choose(true, 0);
  outgoing_.clear();
  outgoing_.ensureSize(2048);
  brain_->out = midiOut_.get();
  keyboard_->setOut(midiOut_.get());
  scope::Generator* gen = core_.get();
  strike_ = [gen](double hz, double velocity) { gen->strike(hz, velocity); };
  brainSources_ = std::make_unique<scope::BrainSources>(*matrix_, *brain_, core_.get());
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
  {
    // A state the host handed over before there was a core to give it to wins.
    const juce::SpinLock::ScopedLockType lock(stateLock_);
    if (pending_) { load(*pending_); pending_.reset(); }
    else if (preset) load(preset->setup);
  }
  keyboard_->frame(0);
  levelLane_.assign(kLevelFrames, 0.0f);
  hearL_.assign(scope::kHearN, 0.0f);
  hearR_.assign(scope::kHearN, 0.0f);
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
  /* A state being loaded from the message thread: this block is silence
     rather than a wait; one waiting for this thread is loaded here, which
     allocates, as a preset's load does. */
  const juce::SpinLock::ScopedTryLockType lock(stateLock_);
  if (!lock.isLocked()) { buffer.clear(); midi.clear(); return; }
  if (pending_) { load(*pending_); pending_.reset(); }
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
  applyKnobs();
  /* The level over the last of the picture, the page's screen, as the frame
     before this one left it. The page's window is its fetch, which follows
     the timebase; this is 2048 frames, about 43 ms at 48 kHz. */
  window(levelLane_, nullptr);
  sources_->level().update(levelLane_.data(), levelLane_.size(), lastBlockMs_);
  /* And the hearing, from the last 4096 frames, its held key the lowest the
     hands hold. Once a block where the page's is once a frame; its period
     estimator allocates as it goes, which is not yet fit for an audio
     thread and is to move with the morph's walk (PLAN.md, stage 2). */
  window(hearL_, &hearR_);
  std::optional<double> heldHz;
  if (!keyboard_->notes().empty()) {
    int low = keyboard_->notes().front().note;
    for (const auto& held : keyboard_->notes()) low = std::min(low, held.note);
    heldHz = scope::midiHz(low);
  }
  hearing_->setNow(nowMs_);
  hearing_->step(*matrix_, true, hearL_.data(), hearL_.data(), hearR_.data(), hearL_.size(), rate_.load(), lastBlockMs_, heldHz, nowMs_);
  keyboard_->setNow(nowMs_);
  keyboard_->setTempo(brain_->clock.bpm);
  keyboard_->frame(lastBlockMs_);
  outAt_ = 0;  // what is sent before the block's events is sent at its top
  /* The crossings' notes from the counts the generator reached by the end of
     the last block, the score's step, the arpeggio's, the threshold, the
     events, and the pluck's note-offs due, in the page's frame's order: once
     a block, as the page does them once a frame, so a note-off due inside a
     block goes at the next block's top - 11 ms late at most at 512 samples,
     where the page's frames are 17 ms apart. The picture is the page's until
     stage 4, so the score has no grid to read and plays nothing, though its
     playhead runs on the bar. */
  scope::crossStep(brain_->notesOut, nowMs_, brain_->cross.on, core_->crossings(), static_cast<int>(brain_->cross.noteX),
                   static_cast<int>(brain_->cross.noteY), midiOut_.get());
  scope::scoreTick(brain_->score, nowMs_, true, brain_->clock, nullptr, scope::keyMask(brain_->keyRoot, brain_->keyScale),
                   strike_, midiOut_.get());
  keyboard_->arpTick(nowMs_);  // the step due this frame, if one is
  // A controller the keyboard learned last block is a source now, and its routings are heard.
  sources_->learn(*matrix_, *keyboard_);
  brainSources_->frame(*brain_, *matrix_, nowMs_);
  matrix_->setLayered(keyboard_->layersOn());
  matrix_->setStrikes(keyboard_->strikes());
  matrix_->frame(nowMs_);
  scope::endDue(brain_->notesOut.pluckOffs, nowMs_, midiOut_.get());
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
  // is run up to it, told, and run on. The arpeggiator's first step, which
  // the page strikes on a timer once the chord has gathered, is struck the
  // same way at the sample its time falls on.
  int done = 0;
  const double rate = rate_.load();
  const double endMs = blockMs + 1000.0 * frames / rate;
  const auto wakesUntil = [&](int until) {
    for (auto wake = keyboard_->arpWake(); wake && *wake < endMs; wake = keyboard_->arpWake()) {
      const int at = std::clamp(static_cast<int>(std::ceil((*wake - blockMs) * rate / 1000)), done, frames);
      if (at > until) break;
      render(left, right, done, at);
      done = at;
      outAt_ = std::min(at, frames - 1);  // a wake in the block's last fraction of a sample rounds up past its end
      keyboard_->setNow(*wake);
      keyboard_->wakeArp();
    }
  };
  for (const auto event : midi) {
    const int at = std::clamp(event.samplePosition, done, frames);
    wakesUntil(at);
    render(left, right, done, at);
    done = at;
    outAt_ = at;
    keyboard_->setNow(blockMs + 1000.0 * at / rate);
    /* The bytes, not JUCE's reading of them: the keyboard is the page's
       `midiBytes` ported, so a note-on at velocity nought, a controller, the
       pedal and a panic all mean here what they mean on the page. A chord
       handed to the generator is copied there, which can allocate on a note
       - once per layer, and a known cost until the brain's state is fixed in
       size (PLAN.md). */
    clockIn_->at(blockMs + 1000.0 * at / rate);  // a clock byte at its own time
    keyboard_->bytes(event.data, static_cast<std::size_t>(event.numBytes));
  }
  wakesUntil(frames);
  render(left, right, done, frames);
  // The host's notes are spent; what goes back is what the out sent.
  midi.swapWith(outgoing_);
  outgoing_.clear();
}

void ScopeProcessor::window(std::vector<float>& left, std::vector<float>* right) const {
  // Oldest first, from the ring this thread writes.
  const std::size_t at = pictureAt_.load(std::memory_order_relaxed), n = left.size();
  for (std::size_t k = 0; k < n; ++k) {
    const std::size_t from = ((at + kPictureFrames - n + k) % kPictureFrames) * 2;
    left[k] = picture_[from];
    if (right) (*right)[k] = picture_[from + 1];
  }
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
