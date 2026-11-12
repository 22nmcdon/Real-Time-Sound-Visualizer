#include "PluginProcessor.h"

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <limits>

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
  for (auto& set : pageSet_) set.store(std::numeric_limits<float>::quiet_NaN());
  // What the out sends goes to the host's MIDI out, at its sample.
  instrument_.hooks.midiOut = [this](const std::uint8_t* bytes, int length, int sample) { outgoing_.addEvent(bytes, length, sample); };
  /* A slider moved on the page has its host parameter follow in pageSlider,
     on the message thread, rather than here (the instrument's sliderMoved,
     on the audio thread), which it did until the gestures: JUCE's VST3
     wrapper takes a gesture only from the message thread and passes a value
     from this thread on through the audio's own changes, so a gesture's end
     could reach the host before its last value. */
  // A setup loaded: the parameters read back from the panel, so the host shows what it set.
  instrument_.hooks.loaded = [this] { readBack(false); };
}

void ScopeProcessor::readBack(bool unmovedOnly) {
  for (std::size_t i = 0; i < kKnobs.size(); ++i) {
    /* One the host has moved since it was last applied keeps the host's
       value, to be applied below. One the page has just set is not the
       host's, and reads back like any other. */
    const float now = knobs_[i]->get();
    if (unmovedOnly && now != applied_[i] && now != pageSet_[i].load()) continue;
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

void ScopeProcessor::pageSlider(const std::string& id, const std::u16string& text) {
  if (!queue(scope::Instrument::slider(id, text))) return;
  /* One of the host's parameters follows now, inside whatever gesture the
     page has opened round the move. The value it will hold is noted first,
     so an audio thread that finds it there before the slider's command has
     reached it knows it for the page's. */
  const double value = scope::jsNumber(scope::utf16To8(text));
  if (!std::isfinite(value)) return;
  for (std::size_t i = 0; i < kKnobs.size(); ++i) {
    if (id != kKnobs[i].slider) continue;
    const float to = knobs_[i]->convertTo0to1(static_cast<float>(value));
    pageSet_[i].store(knobs_[i]->convertFrom0to1(to));
    knobs_[i]->setValueNotifyingHost(to);
  }
}

void ScopeProcessor::pageGesture(const std::string& id, bool begin) {
  for (std::size_t i = 0; i < kKnobs.size(); ++i) {
    if (id != kKnobs[i].slider || gesture_[i] == begin) continue;
    gesture_[i] = begin;
    if (begin) knobs_[i]->beginChangeGesture();
    else knobs_[i]->endChangeGesture();
  }
}

void ScopeProcessor::endGestures() {
  for (std::size_t i = 0; i < kKnobs.size(); ++i) {
    if (!gesture_[i]) continue;
    gesture_[i] = false;
    knobs_[i]->endChangeGesture();
  }
}
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
bool ScopeProcessor::pageSetup(std::string_view code, std::string_view chosen) {
  const auto decoded = scope::decodeSetup(code);
  if (decoded.kind == scope::DecodedSetup::Kind::Read) scope::warmCycles(decoded.setup);
  if (!queue(scope::Instrument::setup(code))) return false;
  /* A bank sound, or the plain sine, chosen on the page is that program for
     the host too, told at once so its list follows. Set before the host is
     told: a host answering with the same program finds it already chosen,
     which is nothing (setCurrentProgram), rather than loading the bank's
     version over a setup the page may have moved on from. */
  const int program = programOf(chosen);
  if (program >= 0 && program != program_.load()) {
    program_.store(program);
    updateHostDisplay(juce::AudioProcessorListener::ChangeDetails().withProgramChanged(true));
  }
  return true;
}

int ScopeProcessor::programOf(std::string_view chosen) {
  // The base's name is the page's BASE_NAME, as getProgramName has it.
  if (chosen == "n:Plain sine") return 0;
  if (chosen.substr(0, 2) != "b:") return -1;
  const auto& bank = scope::presets();
  for (std::size_t i = 0; i < bank.size(); ++i)
    if (bank[i].name == chosen.substr(2)) return 1 + static_cast<int>(i);
  return -1;
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
  for (const auto& command : taken_) {
    instrument_.apply(command);
    // A setup from the page - a preset, a code, an undo step - is a load: the latency is read again after it.
    if (command.kind == scope::Instrument::Command::Setup) latencyIn_ = kLatencyAfter;
  }
  taken_.clear();
}

void ScopeProcessor::reportLatency() {
  const int want = latencyWanted_.load();
  if (want >= 0 && want != getLatencySamples()) setLatencySamples(want);
}

void ScopeProcessor::publish(bool wait) {
  if (!instrument_.changed()) return;
  std::string code = instrument_.stateCode();
  if (wait) {
    const juce::SpinLock::ScopedLockType lock(publishLock_);
    published_ = { instrument_.hostVersion(), instrument_.hostLoads(), instrument_.hostMoved(), std::move(code) };
  } else {
    const juce::SpinLock::ScopedTryLockType lock(publishLock_);
    if (!lock.isLocked()) return;  // the page is reading it; again next block
    published_ = { instrument_.hostVersion(), instrument_.hostLoads(), instrument_.hostMoved(), std::move(code) };
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
      /* And the master Output (G7), always, at unity too: the instrument
         writes it only where it is not unity, and a project saved at unity
         must reopen at unity in an instance that was turned down. Read off
         its parameter, which follows the slider and is safe to read here,
         where the instrument is the audio thread's. A state waiting to load
         that names its own keeps it. */
      if (!decoded.setup.get("pluginOutput"))
        decoded.setup.set("pluginOutput", scope::Json::number(static_cast<double>(knob(std::string_view("output"))->get())));
      // And the program's number (G8), which the instrument never sees, always: a project reopens showing it.
      decoded.setup.set("pluginProgram", scope::Json::number(static_cast<double>(program_.load())));
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
    /* The program it was saved at (G8): shown again, not loaded - the setup
       is what sounds, and is whatever the program became. A state from
       before has none and opens at the plain sine's number, as every project
       did; one that names a program the bank has not got, the same. */
    int program = 0;
    if (const scope::Json* saved = setup.get("pluginProgram"); saved && saved->type == scope::Json::Type::Number
        && saved->n >= 0 && saved->n < getNumPrograms() && saved->n == std::floor(saved->n))
      program = static_cast<int>(saved->n);
    program_.store(program);
    setup.erase("pluginProgram");
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
  /* Room for a block's MIDI, a dense controller sweep's worth, so a block
     that brings the host's notes allocates nothing (G8); more than this in
     one block is made room for as it comes. */
  events_.reserve(1024);
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
  // Prepared is loaded: its latency is read after its first blocks, and told from the timer.
  latencyIn_ = kLatencyAfter;
  startTimerHz(10);
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
  if (arrived) { instrument_.load(*arrived, true); latencyIn_ = kLatencyAfter; }
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
    // The page's own move, set by pageSlider and reaching the slider through the queue: no hand of the host's.
    if (v == pageSet_[i].load()) continue;
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
  /* The host's notes are spent; what goes back is what the out sent. Copied
     into the host's buffer rather than swapped with it, so ours keeps the
     room prepare made: swapped, it was the host's next block, and a host
     handing over a buffer with no room left the arpeggio's next step to
     allocate here (G8). The host's buffer is the host's to size, as JUCE's
     wrappers do. */
  midi.clear();
  if (!outgoing_.isEmpty()) midi.addEvents(outgoing_, 0, -1, 0);
  outgoing_.clear();
  if (instrument_.changed()) tail_.store(tailFor(instrument_.tone(), instrument_.toneB()));
  // Once the matrix has made the stages' routes after a load: how late they put the sound.
  if (latencyIn_ >= 0) {
    latencyIn_ -= frames;
    if (latencyIn_ < 0) latencyWanted_.store(instrument_.stageDelay());
  }
  publish(false);
}

juce::AudioProcessorEditor* ScopeProcessor::createEditor() { return new ScopeEditor(*this); }

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter() { return new ScopeProcessor(); }
