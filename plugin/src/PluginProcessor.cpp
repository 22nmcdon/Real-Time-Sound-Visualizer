#include "PluginProcessor.h"

#include <algorithm>
#include <cmath>
#include <cstdlib>

#include "PluginEditor.h"

ScopeProcessor::ScopeProcessor()
    /* An input bus, off until a host turns it on: with it, the plugin can be
       an effect - drawing its input through the plane, and hearing it - and
       its generator can take the input for its live-input modes. */
    : AudioProcessor(BusesProperties().withInput("Input", juce::AudioChannelSet::stereo(), false)
                                      .withOutput("Output", juce::AudioChannelSet::stereo(), true)) {
  /* Two groups, so a host that shows them - most do, as folders or
     sections - puts the morph apart from the bank it plays with. */
  auto main = std::make_unique<juce::AudioProcessorParameterGroup>("loop", "Instrument", "|");
  auto setups = std::make_unique<juce::AudioProcessorParameterGroup>("setups", "Setups", "|");
  for (std::size_t i = 0; i < kKnobs.size(); ++i) {
    const auto* spec = scope::rangeSpec(kKnobs[i].slider);
    auto knob = std::make_unique<juce::AudioParameterFloat>(
        juce::ParameterID { kKnobs[i].id, kKnobs[i].version }, kKnobs[i].name,
        juce::NormalisableRange<float>(static_cast<float>(spec->min), static_cast<float>(spec->max), static_cast<float>(spec->step)),
        static_cast<float>(spec->value));
    knobs_[i] = knob.get();
    (kKnobs[i].main ? main : setups)->addChild(std::move(knob));
  }
  addParameterGroup(std::move(main));
  addParameterGroup(std::move(setups));
  moved_.reserve(kKnobs.size());
  // What the out sends goes to the host's MIDI out, at its sample.
  instrument_.hooks.midiOut = [this](const std::uint8_t* bytes, int length, int sample) { outgoing_.addEvent(bytes, length, sample); };
  // A slider moved on the page: the host's parameter for it follows.
  instrument_.hooks.sliderMoved = [this](const std::string& id, double value) {
    for (std::size_t i = 0; i < kKnobs.size(); ++i) {
      if (id != kKnobs[i].slider) continue;
      knobs_[i]->setValueNotifyingHost(knobs_[i]->convertTo0to1(static_cast<float>(value)));
      applied_[i] = knobs_[i]->get();
    }
  };
  // A setup loaded: the parameters read back from the panel, so the host shows what it set.
  instrument_.hooks.loaded = [this] { readBack(false); };
}

void ScopeProcessor::readBack(bool unmovedOnly) {
  for (std::size_t i = 0; i < kKnobs.size(); ++i) {
    // One the host has moved since it was last applied keeps the host's value, to be applied below.
    if (unmovedOnly && knobs_[i]->get() != applied_[i]) continue;
    const auto v = static_cast<float>(instrument_.slider(kKnobs[i].slider));
    knobs_[i]->setValueNotifyingHost(knobs_[i]->convertTo0to1(v));
    applied_[i] = knobs_[i]->get();
  }
  panelLayer_ = instrument_.panelLayer();
}

bool ScopeProcessor::queue(std::optional<scope::Instrument::Command> command) {
  if (!command) return false;
  const juce::SpinLock::ScopedLockType lock(queueLock_);
  queue_.push_back(std::move(*command));
  return true;
}

void ScopeProcessor::pageSlider(const std::string& id, const std::u16string& text) { queue(scope::Instrument::slider(id, text)); }
/* A drawing made by hand arrives a few times a second while it is drawn, and
   a drawn cycle's tables are milliseconds to build: built here, on the
   message thread, so the audio thread finds them made (CycleCache). */
void ScopeProcessor::pageControl(const std::string& id, scope::Json value) {
  if (id == "drawn" && value.type == scope::Json::Type::String)
    if (const auto part = scope::jsonParse(value.s)) scope::warmCycles(*part);
  queue(scope::Instrument::control(id, std::move(value)));
}
void ScopeProcessor::pageClick(const std::string& id) { queue(scope::Instrument::click(id)); }
void ScopeProcessor::pageFade(std::string_view json) { queue(scope::Instrument::fade(json)); }
void ScopeProcessor::pageRoutings(std::string_view text) { queue(scope::Instrument::routings(text)); }
// A preset from the page: its drawn cycles built here first, as a drawing's are.
bool ScopeProcessor::pageSetup(std::string_view code) {
  const auto decoded = scope::decodeSetup(code);
  if (decoded.kind == scope::DecodedSetup::Kind::Read) scope::warmCycles(decoded.setup);
  return queue(scope::Instrument::setup(code));
}

ScopeProcessor::PageState ScopeProcessor::pageState() const {
  const juce::SpinLock::ScopedLockType lock(publishLock_);
  return published_;
}

void ScopeProcessor::takePage() {
  {
    // Not waited for: a page mid-push leaves its commands for the next block.
    const juce::SpinLock::ScopedTryLockType lock(queueLock_);
    if (!lock.isLocked()) return;
    std::swap(queue_, taken_);
  }
  for (const auto& command : taken_) instrument_.apply(command);
  taken_.clear();
}

void ScopeProcessor::publish(bool wait) {
  if (!instrument_.changed()) return;
  std::string code = instrument_.stateCode();
  if (wait) {
    const juce::SpinLock::ScopedLockType lock(publishLock_);
    published_ = { instrument_.hostVersion(), std::move(code) };
  } else {
    const juce::SpinLock::ScopedTryLockType lock(publishLock_);
    if (!lock.isLocked()) return;  // the page is reading it; again next block
    published_ = { instrument_.hostVersion(), std::move(code) };
  }
  instrument_.published();
}

/* Never the audio thread's work, and never its lock for longer than a copy.
   A state handed over and not yet loaded is the state: saved before the first
   block - a frozen or inactive track, a closed device - this used to write
   nothing, and the project reopened on the opening sound. Otherwise the code
   the audio thread last published, which is at most a block behind and is
   what the page reads too. It used to encode the instrument here, holding the
   lock processBlock only tries for, and every block that found it held came
   out silent with its MIDI dropped; hosts save for autosave and undo, and a
   lost note-off stuck the note (6 Nov). */
void ScopeProcessor::getStateInformation(juce::MemoryBlock& out) {
  std::optional<scope::Json> waiting;
  {
    const juce::SpinLock::ScopedLockType lock(stateLock_);
    waiting = pending_;
  }
  std::string code;
  if (waiting) {
    if (const auto encoded = scope::encodeSetup(*waiting)) code = *encoded;
  } else {
    code = pageState().code;
  }
  // The face's window, which is the plugin's and not the setup's.
  if (!code.empty()) {
    auto decoded = scope::decodeSetup(code);
    if (decoded.kind == scope::DecodedSetup::Kind::Read && decoded.setup.type == scope::Json::Type::Object) {
      const auto [w, h] = windowSize();
      decoded.setup.set("pluginWindow", scope::Json::string(std::string_view(std::to_string(w) + "x" + std::to_string(h))));
      if (const auto encoded = scope::encodeSetup(decoded.setup)) code = *encoded;
    }
  }
  out.append(code.data(), code.size());
}

void ScopeProcessor::setCurrentProgram(int index) {
  if (index < 0 || index >= getNumPrograms() || index == program_.load()) return;
  program_.store(index);
  const scope::Json& setup = index == 0 ? scope::baseSetup() : scope::presets()[static_cast<std::size_t>(index - 1)].setup;
  scope::warmCycles(setup);
  const juce::SpinLock::ScopedLockType lock(stateLock_);
  pending_ = setup;
}

const juce::String ScopeProcessor::getProgramName(int index) {
  // The base's name is the page's BASE_NAME; the core keeps the setup and not the name.
  if (index == 0) return "Plain sine";
  if (index < 0 || index >= getNumPrograms()) return {};
  return juce::String(scope::presets()[static_cast<std::size_t>(index - 1)].name);
}

double ScopeProcessor::tailFor(const scope::Tone& a, const scope::LayerSettings& b) {
  double tail = std::fmax(a.env.releaseMs, b.env.releaseMs) / 1000;
  if (a.delayMix > 0) {
    const double fb = std::fmax(0.0, std::fmin(0.9, a.delayFeedback));
    const double repeats = fb > 0 ? std::log(0.001) / std::log(fb) : 1;
    tail += a.delayMs / 1000 * (repeats + 1);
  }
  return std::fmin(60.0, tail);
}

void ScopeProcessor::setStateInformation(const void* data, int size) {
  const auto decoded = scope::decodeSetup(std::string_view(static_cast<const char*>(data), static_cast<std::size_t>(size)));
  if (decoded.kind != scope::DecodedSetup::Kind::Read) return;
  scope::Json setup = decoded.setup;
  if (setup.type == scope::Json::Type::Object) {
    if (const scope::Json* window = setup.get("pluginWindow"); window && window->type == scope::Json::Type::String) {
      const std::string text = scope::utf16To8(window->s);
      const auto x = text.find('x');
      if (x != std::string::npos) {
        const int w = std::atoi(text.substr(0, x).c_str()), h = std::atoi(text.substr(x + 1).c_str());
        if (w >= 960 && h >= 600 && w <= 2560 && h <= 1600) setWindowSize(w, h);
      }
    }
    setup.erase("pluginWindow");
  }
  scope::warmCycles(setup);  // here rather than as the audio thread loads it
  const juce::SpinLock::ScopedLockType lock(stateLock_);
  pending_ = std::move(setup);
}

bool ScopeProcessor::isBusesLayoutSupported(const BusesLayout& layouts) const {
  // A stereo out, and an input of one channel, two, or none.
  const auto in = layouts.getMainInputChannelSet();
  return layouts.getMainOutputChannelSet() == juce::AudioChannelSet::stereo()
      && (in.isDisabled() || in == juce::AudioChannelSet::mono() || in == juce::AudioChannelSet::stereo());
}

void ScopeProcessor::prepareToPlay(double sampleRate, int samplesPerBlock) {
  rate_.store(sampleRate);
  outgoing_.clear();
  outgoing_.ensureSize(2048);
  const auto most = static_cast<std::size_t>(std::max(64, samplesPerBlock));
  inL_.assign(most, 0.0f); inR_.assign(most, 0.0f);
  /* The sound the page opens on: its boot preset, loaded as the page loads
     it. SCOPE_PRESET names another, for looking at one in the standalone, or
     is a setup written out as JSON - which is how the shell test opens on the
     presets P8g cut, from the old library it keeps as a corpus. Read once,
     here, and never on the audio thread. */
  const char* wanted = std::getenv("SCOPE_PRESET");
  std::optional<scope::Json> written;
  if (wanted && wanted[0] == '{') written = scope::jsonParse(scope::utf8To16(wanted));
  const scope::Preset* preset = wanted && !written ? scope::findPreset(wanted) : nullptr;
  {
    /* A state the host handed over and not yet loaded wins. Then, prepared
       again - a host's rate or block size changing, its device restarting,
       the plugin reactivated - the sound it has, read back from its own state
       code as a project reopened reads it: preset, routings, the hands on
       them since, learned controllers. It used to be built again on the
       opening sound every time (6 Nov). With neither, the base the page opens
       on too (P8h). */
    const juce::SpinLock::ScopedLockType lock(stateLock_);
    std::optional<scope::Json> current;
    if (!pending_ && instrument_.prepared()) {
      const auto decoded = scope::decodeSetup(instrument_.stateCode());
      if (decoded.kind == scope::DecodedSetup::Kind::Read) current = decoded.setup;
    }
    instrument_.prepare(sampleRate, samplesPerBlock, pending_ ? *pending_ : current ? *current : written ? *written
                        : preset ? preset->setup : scope::baseSetup());
    pending_.reset();
  }
  tail_.store(tailFor(instrument_.tone(), instrument_.toneB()));
  publish(true);  // for a page that asks before the first block
  /* For looking at it without a keyboard: SCOPE_HOLD_NOTE=57 holds A3 from
     the start, and SCOPE_HOLD_NOTE=57,64 a fifth on it, so the standalone has
     something to draw. Read once, here, and never on the audio thread. */
  if (const char* held = std::getenv("SCOPE_HOLD_NOTE")) {
    for (const auto& note : juce::StringArray::fromTokens(held, ",", ""))
      instrument_.keyboard().noteOn(note.getIntValue(), 127);
  }
}

void ScopeProcessor::processBlock(juce::AudioBuffer<float>& buffer, juce::MidiBuffer& midi) {
  juce::ScopedNoDenormals noDenormals;
  /* A state waiting for this thread is taken here and loaded, which
     allocates, as a preset's load does. The lock guards only the hand-over:
     found held - a state being handed over, or a save copying one - the
     state waits a block and this one plays. It used to guard the whole
     instrument against a save, and a block that found it held was silence
     with its MIDI dropped (6 Nov). */
  std::optional<scope::Json> arrived;
  {
    const juce::SpinLock::ScopedTryLockType lock(stateLock_);
    if (lock.isLocked() && pending_) { arrived = std::move(pending_); pending_.reset(); }
  }
  if (arrived) instrument_.load(*arrived, true);
  takePage();
  // The host's transport, where it gives one.
  std::optional<scope::Instrument::Transport> transport;
  if (auto* head = getPlayHead()) {
    if (const auto position = head->getPosition()) {
      if (const auto bpm = position->getBpm()) {
        const auto ppq = position->getPpqPosition();
        transport = scope::Instrument::Transport { *bpm, ppq.hasValue() ? std::optional<double>(*ppq) : std::nullopt,
                                                   position->getIsPlaying() };
      }
    }
  }
  /* The panel turned to the other layer - by the page's edit switch, or by
     the layers going off: the sliders a layer has now show that layer, so
     their parameters read back, or the host would show A's cutoff while its
     next move wrote B's. */
  if (instrument_.panelLayer() != panelLayer_) readBack(true);
  // Each parameter the host has moved since the last block, to its slider.
  moved_.clear();
  for (std::size_t i = 0; i < kKnobs.size(); ++i) {
    const float v = knobs_[i]->get();
    if (v == applied_[i]) continue;
    applied_[i] = v;
    moved_.push_back({ kKnobs[i].slider, v });
  }
  /* The host's MIDI, as bytes at their samples, not JUCE's reading of them:
     the keyboard is the page's `midiBytes` ported. Collected first, as the
     instrument runs the generator up to each. */
  events_.clear();
  for (const auto event : midi)
    events_.push_back({ event.samplePosition, event.data, static_cast<std::size_t>(event.numBytes) });
  const int frames = buffer.getNumSamples();
  /* The input, copied out before anything is written: a host hands the
     input over in the same buffer the output goes back in. */
  const int inputs = getTotalNumInputChannels();
  std::optional<scope::Instrument::Input> input;
  if (inputs > 0) {
    const auto n = static_cast<std::size_t>(frames);
    if (inL_.size() < n) { inL_.resize(n); inR_.resize(n); }
    std::copy(buffer.getReadPointer(0), buffer.getReadPointer(0) + frames, inL_.begin());
    if (inputs > 1) std::copy(buffer.getReadPointer(1), buffer.getReadPointer(1) + frames, inR_.begin());
    input = scope::Instrument::Input { inL_.data(), inputs > 1 ? inR_.data() : nullptr };
  }
  auto* right = buffer.getNumChannels() > 1 ? buffer.getWritePointer(1) : nullptr;
  instrument_.block(buffer.getWritePointer(0), right, frames, events_.data(), events_.size(), transport ? &*transport : nullptr,
                    moved_.data(), moved_.size(), input ? &*input : nullptr);
  // The host's notes are spent; what goes back is what the out sent.
  midi.swapWith(outgoing_);
  outgoing_.clear();
  if (instrument_.changed()) tail_.store(tailFor(instrument_.tone(), instrument_.toneB()));
  publish(false);
}

juce::AudioProcessorEditor* ScopeProcessor::createEditor() { return new ScopeEditor(*this); }

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter() { return new ScopeProcessor(); }
