// The whole instrument as the plugin plays it: the core's generator, and over
// it the brain - the keyboard, the matrix and every source, the clock, the
// score, the hearing, the picture the photocell reads - with the page as its
// face. It was the plugin's processor until the site wanted to run the same
// brain (plugin/PLAN.md, stage 5f); everything here is what the processor
// did that is not JUCE's, so the plugin and the site's worklet are two thin
// owners of one instrument and cannot come to disagree about what a hand on
// the page does.
//
// What stays with the owner, because only it knows: the host's parameters
// (it hands over the ones moved since the last block, and is told when a
// slider it follows has moved or a setup has loaded), the host's transport,
// the MIDI that arrives and where what is sent goes, and any locking. The
// instrument is single-threaded; the plugin queues the page's commands under
// a lock and applies them at the top of a block, and the worklet, whose
// messages already arrive between blocks, applies them as they come.

#pragma once

#include <algorithm>
#include <array>
#include <atomic>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <memory>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include "scope/generator.h"
#include "scope/hearing.h"
#include "scope/keyboard.h"
#include "scope/lfo.h"
#include "scope/matrix.h"
#include "scope/restore.h"
#include "scope/screen.h"
#include "scope/sources.h"

namespace scope {

class Instrument {
 public:
  /* The last `kPictureFrames` of what was played, left and right, for the
     page to draw. About 170 ms at 48 kHz: enough for the scope's longer
     timebases and for the readout's analysis, at 64 KB a fetch. 2048 was a
     twentieth of a second, shorter than a 5 ms/div screen. */
  static constexpr std::size_t kPictureFrames = 8192;
  static constexpr std::size_t kLevelFrames = 2048;
  /* The picture, drawn here for the photocell and the picture's sources so
     their loops go on with the window closed (stage 4): captured from the
     picture ring by the view the page set, at the page's sixty frames a
     second of audio time, on a canvas of the size the page's trace usually
     is. The grid depends on that size only through the Y-T walk's peak bars,
     one a pixel; X-Y draws on a square however wide the canvas. */
  static constexpr Canvas kCanvas { 846, 534, false, 0 };

  /* What the instrument tells its owner. `midiOut`: bytes the page would send
     to a MIDI port, at the sample of the block that sent them. `sliderMoved`:
     a slider moved by the page, for a host parameter on it to follow.
     `loaded`: a setup loaded, for the host's parameters to read back. */
  struct Hooks {
    std::function<void(const std::uint8_t* bytes, int length, int sample)> midiOut;
    std::function<void(const std::string& id, double value)> sliderMoved;
    std::function<void()> loaded;
  };
  // The host's transport for a block, where it gives one.
  struct Transport { double bpm = 120; std::optional<double> ppq; bool playing = false; };
  // A MIDI message at its sample in the block.
  struct Event { int sample; const std::uint8_t* data; std::size_t size; };
  // A host parameter moved since the last block: a hand on its slider.
  struct HostSlider { const char* id; double value; };
  /* A block's input: what a host's input bus or a page's microphone hands
     over, its right channel null for a mono input; and for a rack, its lanes,
     one signal each, up to kMaxLanes of them (the first two are left and
     right as well). */
  struct Input {
    const float* left;
    const float* right;
    const float* const* lanes = nullptr;
    int laneCount = 0;
  };
  // The most lanes the ring keeps: the page's MAX_LANES.
  static constexpr int kRingLanes = kMaxLanes;
  /* The band split's four bands, as the page's BANDS has them: a highpass at
     the lower edge, a lowpass at the upper, nought for none. */
  static constexpr int kBandCount = 4;
  static constexpr std::array<std::array<double, 2>, kBandCount> kBandEdges { { { 0, 120 }, { 120, 800 }, { 800, 4000 }, { 4000, 0 } } };

  /* One hand from the page: a slider moved (by id and the value the browser
     holds), a setup loaded (a preset, a code), a menu, a switch or a text box
     changed (its value as text, a switch's as true or false), a button
     pressed, the routings as an edit left them, the fade sent whole. Made by
     the functions below, which refuse what could not be done - a slider the
     panel has not got, a code that does not read, a fade that is not JSON -
     so the owner can say so at once rather than a block later. */
  struct Command {
    enum Kind { Slider, Setup, Control, Click, Routings, Fade } kind;
    std::string id; std::u16string text; Json value; std::optional<Json> setup;
  };
  static std::optional<Command> slider(const std::string& id, const std::u16string& text) {
    if (!rangeSpec(id)) return std::nullopt;
    return Command { Command::Slider, id, text, {}, std::nullopt };
  }
  static std::optional<Command> setup(std::string_view code) {
    auto decoded = decodeSetup(code);
    if (decoded.kind != DecodedSetup::Kind::Read) return std::nullopt;
    return Command { Command::Setup, {}, {}, {}, std::move(decoded.setup) };
  }
  static Command control(const std::string& id, Json value) { return { Command::Control, id, {}, std::move(value), std::nullopt }; }
  static Command click(const std::string& id) { return { Command::Click, id, {}, {}, std::nullopt }; }
  static Command routings(std::string_view text) { return { Command::Routings, {}, utf8To16(text), {}, std::nullopt }; }
  static std::optional<Command> fade(std::string_view json) {
    const auto parsed = jsonParse(utf8To16(json));
    if (!parsed) return std::nullopt;
    return Command { Command::Fade, {}, {}, *parsed, std::nullopt };
  }

  Hooks hooks;

  bool prepared() const { return brain_ != nullptr; }
  double rate() const { return rate_; }

  /* Everything made again for a rate and a block size, and `setup` loaded as
     the host's (a project's state, or the preset it opens on). */
  void prepare(double sampleRate, int samplesPerBlock, const Json& setup) {
    rate_ = sampleRate;
    // The page's two LFOs as it starts them.
    lfos_.assign(2, Lfo {});
    lfos_[0].rate = 0.2; lfos_[0].depth = 0.5;
    lfos_[1].rate = 0.5; lfos_[1].depth = 0.3;
    core_ = std::make_unique<Generator>(sampleRate, slot::Used, lfos_);
    notes_ = std::make_unique<GeneratorNotes>(*core_);
    brain_ = std::make_unique<Brain>();
    clockIn_ = std::make_unique<ClockIn>(brain_->clock);
    keyboard_ = std::make_unique<Keyboard>(*notes_, clockIn_.get());
    // The layer the panel shows follows the keyboard, as the page's syncLayers has it.
    keyboard_->setLayerPanel([this] { syncLayerPanel(*brain_, *core_, *keyboard_); });
    matrix_ = std::make_unique<Matrix>();
    sources_ = std::make_unique<CoreSources>(*matrix_, *core_, lfos_, *keyboard_);
    /* What it hears is the picture, the generator's unless it is drawing its
       input: while it is the generator's, every hearing source is a loop,
       with the picture's reach, and the onset is refused anything it could
       strike. Which source is drawn outlives a prepare, as a host's input
       does. */
    hearing_ = std::make_unique<HearingSources>(*matrix_);
    hearing_->hears(!drawsInput_);
    nowMs_ = 0;
    lastBlockMs_ = 0;
    linkClock(*brain_, lfos_);
    /* The page's MIDI out, a port chosen once and for good: the owner's MIDI
       out is always there, and whether anything listens to it is the owner's
       business. Channel 1, the page's default; the page's menu for it is not
       the instrument's yet. */
    midiOut_ = std::make_unique<MidiOut>([this](const std::uint8_t* bytes, int length) {
      if (hooks.midiOut) hooks.midiOut(bytes, length, outAt_);
    });
    midiOut_->choose(true, 0);
    brain_->out = midiOut_.get();
    keyboard_->setOut(midiOut_.get());
    Generator* gen = core_.get();
    strike_ = [gen](double hz, double velocity) { gen->strike(hz, velocity); };
    brainSources_ = std::make_unique<BrainSources>(*matrix_, *brain_, core_.get());
    // The view's destinations before any setup, so a preset's routings onto them are heard.
    pictureRun_ = std::make_unique<PictureRun>(*matrix_, *brain_);
    pictureSource_.rate = sampleRate;
    bandFilters();
    pictureSource_.capacity = static_cast<double>(kPictureFrames);
    pictureSource_.channels = 2;
    pictureSource_.lanes = false;
    // The latest n frames of the ring, oldest first, nought before the start
    // of what it holds - which the capacity says it never asks for.
    pictureSource_.latest = [this](std::size_t n) {
      std::vector<Lane> out(static_cast<std::size_t>(pictureSource_.channels), Lane(n, 0.0f));
      for (std::size_t c = 0; c < out.size(); ++c) latestLane(static_cast<int>(c), out[c].data(), n);
      return out;
    };
    /* A host is always a keyboard, so the generator is gated from the start -
       silent until a note - which is what the page's first frame does once a
       keyboard is there. Derived by the keyboard, not set here. */
    keyboard_->setPresent(true);
    load(setup, true);
    keyboard_->frame(0);
    learnedSeen_ = keyboard_->controllers().size();
    changed_ = true;
    levelLane_.assign(kLevelFrames, 0.0f);
    hearL_.assign(kHearN, 0.0f);
    hearR_.assign(kHearN, 0.0f);
    const auto size = static_cast<std::size_t>(std::max(64, samplesPerBlock));
    pictureL_.assign(size, 0.0f); pictureR_.assign(size, 0.0f); spare_.assign(size, 0.0f); mono_.assign(size, 0.0f);
    heardL_.assign(size, 0.0f); heardR_.assign(size, 0.0f);
  }

  // A setup loaded as a preset is: the core restored, the hands on it since put back.
  void load(const Json& setup, bool fromHost) {
    setup_ = setup;
    hands_.clear();
    restoreSetup(setup_, *brain_, *core_, *keyboard_, *matrix_, lfos_);
    /* The sliders moved since this setup was first loaded, as a state saved
       before the menus reached the plugin wrote them: "id=value;...", put back
       as hands on them. One saved since has none of these, and its hands
       follow in `pluginHands`. */
    if (const Json* moved = setup_.type == Json::Type::Object ? setup_.get("pluginSliders") : nullptr) {
      if (moved->type == Json::Type::String) {
        const std::string text = utf16To8(moved->s);
        std::size_t at = 0;
        while (at < text.size()) {
          const std::size_t end = std::min(text.find(';', at), text.size());
          const std::string pair = text.substr(at, end - at);
          const std::size_t eq = pair.find('=');
          if (eq != std::string::npos && rangeSpec(pair.substr(0, eq)))
            moveTo(pair.substr(0, eq), toU16(pair.substr(eq + 1)), false);
          at = end + 1;
        }
      }
    }
    if (const Json* hands = setup_.type == Json::Type::Object ? setup_.get("pluginHands") : nullptr) {
      if (hands->type == Json::Type::Array) for (const auto& hand : hands->a) replay(hand);
    }
    // A saved state says which source was drawn; a preset or a code from the page says nothing, and changes nothing.
    if (const Json* drawn = setup_.type == Json::Type::Object ? setup_.get("pluginInput") : nullptr)
      drawFrom(drawn->type == Json::Type::Bool && drawn->b);
    if (const Json* split = setup_.type == Json::Type::Object ? setup_.get("pluginBands") : nullptr)
      drawBands(split->type == Json::Type::Bool && split->b);
    // A setup restores two lanes' worth of view; a rack drawn has more, and keeps them.
    if (rack_ > 0) { brain_->view.capture.channels.resize(static_cast<std::size_t>(std::max(2, rack_))); fitView(*brain_); }
    if (hooks.loaded) hooks.loaded();
    changed_ = true;
    if (fromHost) hostVersion_++;
  }

  // One of the page's hands, done now: the owner calls it at the top of a block.
  void apply(const Command& command) {
    switch (command.kind) {
      case Command::Setup: load(*command.setup, false); break;
      case Command::Slider: moveTo(command.id, command.text, false); break;
      case Command::Control: change(command.id, command.value); break;
      case Command::Click: press(command.id); break;
      case Command::Routings: route(utf16To8(command.text)); break;
      case Command::Fade: fadeTo(command.value); break;
    }
  }

  /* One block: the page's once-a-frame work once and before it, then the
     generator up to each MIDI event, the event, and on. `right` may be null;
     `transport` is null where the host gives none; `sliders` are the host's
     parameters moved since the last block. */
  void block(float* left, float* right, int frames, const Event* events, std::size_t eventCount, const Transport* transport,
             const HostSlider* sliders, std::size_t sliderCount, const Input* input = nullptr) {
    input_ = input;
    /* The page's once-a-frame work, once a block and before it: the
       keyboard's controllers walk and its gate and chord are worked out
       again, the matrix steps its fades, fires its events and compiles its
       routes, the morph walks its sliders, and the generator holds those
       routes across the block, as the worklet does. First of all the clock,
       as in the page's frame: the host's transport where it gives one, then
       the clock's step, which sets the locked oscillators' rates. */
    brain_->clock.setNow(nowMs_);
    if (transport) brain_->clock.host(transport->bpm, transport->ppq, transport->playing, nowMs_);
    clockFrame(*brain_, *core_, nowMs_);
    /* The host's parameters, each as a hand on its slider: the value written
       as the browser would hold it, the slider's handler run. Which
       allocates, as the morph's walk does, and moves with it to the message
       thread (PLAN.md, stage 2). */
    for (std::size_t i = 0; i < sliderCount; ++i) moveTo(sliders[i].id, jsToString(Json::number(sliders[i].value)), true);
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
      heldHz = midiHz(low);
    }
    hearing_->hears(hearsItself());
    hearing_->setNow(nowMs_);
    hearing_->step(*matrix_, true, hearL_.data(), hearL_.data(), hearR_.data(), hearL_.size(), rate_, lastBlockMs_, heldHz, nowMs_);
    keyboard_->setNow(nowMs_);
    keyboard_->setTempo(brain_->clock.bpm);
    keyboard_->frame(lastBlockMs_);
    outAt_ = 0;  // what is sent before the block's events is sent at its top
    /* The crossings' notes from the counts the generator reached by the end
       of the last block, the score's step, the arpeggio's, the threshold, the
       events, and the pluck's note-offs due, in the page's frame's order:
       once a block, as the page does them once a frame, so a note-off due
       inside a block goes at the next block's top - 11 ms late at most at
       512 samples, where the page's frames are 17 ms apart. The score reads
       the grid drawn here, as the last picture frame left it. */
    crossStep(brain_->notesOut, nowMs_, brain_->cross.on, core_->crossings(), static_cast<int>(brain_->cross.noteX),
              static_cast<int>(brain_->cross.noteY), midiOut_.get());
    scoreTick(brain_->score, nowMs_, true, brain_->clock, pictureRun_->phosphor().grid().data(),
              keyMask(brain_->keyRoot, brain_->keyScale), strike_, midiOut_.get());
    keyboard_->arpTick(nowMs_);  // the step due this frame, if one is
    /* The picture's frame, when a sixtieth of a second of audio has gone: the
       capture, and the photocell and the picture's sources stepped from the
       grid the last frame left, before the matrix reads them - with no
       limiter to read, the output being the owner's. Its capture and its
       walk allocate as they go, a known cost on this thread like the
       hearing's, until the brain's work moves off it (PLAN.md, stage 2). */
    const bool pictureFrame = pictureRun_->due(nowMs_);
    if (pictureFrame) pictureRun_->before(*matrix_, pictureSource_, 0);
    // A controller the keyboard learned last block is a source now, and its routings are heard.
    sources_->learn(*matrix_, *keyboard_);
    brainSources_->frame(*brain_, *matrix_, nowMs_);
    matrix_->setLayered(keyboard_->layersOn());
    matrix_->setStrikes(keyboard_->strikes());
    matrix_->frame(nowMs_);
    endDue(brain_->notesOut.pluckOffs, nowMs_, midiOut_.get());
    /* After the matrix, so a source on the fader is already counted. A walk
       moves sliders and fires their handlers, which allocate (a slider's
       value is the text the browser would hold): not yet fit for an audio
       thread, and the morph's place is the message thread once there is one
       to hand it to (PLAN.md, stage 2). */
    morphStep(*brain_, *core_, *keyboard_, lfos_);
    // The zoom made again from what the matrix wrote, and the frame's deposits, as the page draws after its matrix.
    pictureRun_->afterMatrix();
    if (pictureFrame) pictureRun_->draw(pictureSource_, kCanvas);
    core_->setRoutes(matrix_->routes(nowMs_));
    const double blockMs = nowMs_;
    lastBlockMs_ = 1000.0 * frames / rate_;
    nowMs_ += lastBlockMs_;
    // Each event at its own sample, not at the top of the block: the
    // generator is run up to it, told, and run on. The arpeggiator's first
    // step, which the page strikes on a timer once the chord has gathered,
    // is struck the same way at the sample its time falls on.
    int done = 0;
    const double endMs = blockMs + 1000.0 * frames / rate_;
    const auto wakesUntil = [&](int until) {
      for (auto wake = keyboard_->arpWake(); wake && *wake < endMs; wake = keyboard_->arpWake()) {
        const int at = std::clamp(static_cast<int>(std::ceil((*wake - blockMs) * rate_ / 1000)), done, frames);
        if (at > until) break;
        render(left, right, done, at);
        done = at;
        outAt_ = std::min(at, frames - 1);  // a wake in the block's last fraction of a sample rounds up past its end
        keyboard_->setNow(*wake);
        keyboard_->wakeArp();
      }
    };
    for (std::size_t e = 0; e < eventCount; ++e) {
      const Event& event = events[e];
      const int at = std::clamp(event.sample, done, frames);
      wakesUntil(at);
      render(left, right, done, at);
      done = at;
      outAt_ = at;
      keyboard_->setNow(blockMs + 1000.0 * at / rate_);
      /* The bytes, not anyone's reading of them: the keyboard is the page's
         `midiBytes` ported, so a note-on at velocity nought, a controller,
         the pedal and a panic all mean here what they mean on the page. A
         chord handed to the generator is copied there, which can allocate on
         a note - once per layer, and a known cost until the brain's state is
         fixed in size (PLAN.md). */
      clockIn_->at(blockMs + 1000.0 * at / rate_);  // a clock byte at its own time
      keyboard_->bytes(event.data, event.size);
    }
    wakesUntil(frames);
    render(left, right, done, frames);
  }

  /* Whether the state the page is shown has changed since it was last
     published - a hand, a load, a controller learned - and, once the owner
     has published it, that it has. Two calls rather than one so an owner
     that could not publish this time (the plugin, when the page is reading)
     is asked again next block. */
  bool changed() {
    if (keyboard_->controllers().size() != learnedSeen_) { learnedSeen_ = keyboard_->controllers().size(); changed_ = true; }
    return changed_;
  }
  void published() { changed_ = false; }
  // How many changes came from the host rather than the page: a load, a parameter moved.
  int hostVersion() const { return hostVersion_; }

  /* The setup code of everything that can have changed: the setup loaded,
     the hands on it since, the controllers learned. */
  std::string stateCode() const {
    Json setup = setup_.type == Json::Type::Object ? setup_ : Json::object();
    setup.erase("pluginSliders");
    setup.erase("pluginHands");
    if (!hands_.empty()) {
      Json list = Json::array();
      for (const auto& h : hands_) list.a.push_back(h.hand);
      setup.set("pluginHands", list);
    }
    setup.set("cc", Json::string(std::string_view(keyboard_->encodeCC())));
    setup.erase("pluginInput");
    setup.erase("pluginBands");
    if (drawsInput_) setup.set("pluginInput", Json::boolean(true));
    if (bands_) setup.set("pluginBands", Json::boolean(true));
    const auto code = encodeSetup(setup);
    return code ? *code : std::string();
  }

  /* The picture ring, oldest first, left and right interleaved, so the page
     reads it as a window of time. Written by the audio thread; read by the
     plugin's message thread, and the read can tear across a block boundary,
     which a picture redrawn sixty times a second survives and a measurement
     would not. */
  std::vector<float> pictureSnapshot() const {
    std::vector<float> out(kPictureFrames * 2);
    const std::size_t at = pictureAt_.load(std::memory_order_acquire);
    for (std::size_t k = 0; k < kPictureFrames; ++k) {
      const std::size_t from = ((at + k) % kPictureFrames) * kRingLanes;
      out[k * 2] = picture_[from];
      out[k * 2 + 1] = picture_[from + 1];
    }
    return out;
  }
  /* The picture as the plugin serves it to its page: the whole ring, oldest
     first, as many lanes as the picture has interleaved - two, or a rack's or
     the band split's - so the page, which knows how many frames the ring is,
     reads the lane count off the length. Two lanes are pictureSnapshot's. */
  std::vector<float> pictureServed() const {
    const std::size_t lanes = static_cast<std::size_t>(std::clamp(pictureSource_.channels, 1, kRingLanes));
    std::vector<float> out(kPictureFrames * lanes);
    const std::size_t at = pictureAt_.load(std::memory_order_acquire);
    for (std::size_t k = 0; k < kPictureFrames; ++k) {
      const std::size_t from = ((at + k) % kPictureFrames) * kRingLanes;
      for (std::size_t c = 0; c < lanes; ++c) out[k * lanes + c] = picture_[from + c];
    }
    return out;
  }
  // The last n frames of the picture into two lanes, oldest first.
  void latest(float* left, float* right, std::size_t n) const { latestLane(0, left, n); latestLane(1, right, n); }
  // The last n frames of one lane of the picture, oldest first.
  void latestLane(int lane, float* out, std::size_t n) const {
    const std::size_t at = pictureAt_.load(std::memory_order_relaxed), take = std::min(n, kPictureFrames);
    const std::size_t c = static_cast<std::size_t>(std::clamp(lane, 0, kRingLanes - 1));
    for (std::size_t k = 0; k < n - take; ++k) out[k] = 0.0f;
    for (std::size_t k = 0; k < take; ++k) out[n - take + k] = picture_[((at + kPictureFrames - take + k) % kPictureFrames) * kRingLanes + c];
  }
  // How many lanes the picture has: two, or a rack's.
  int pictureLanes() const { return pictureSource_.channels; }

  // What the owners and their tests read.
  const Tone& tone() const { return core_->tone(); }
  const LayerSettings& toneB() const { return core_->toneB(); }
  Keyboard& keyboard() { return *keyboard_; }
  const Keyboard& keyboard() const { return *keyboard_; }
  Matrix& matrix() { return *matrix_; }
  double level() const { return sources_->level().value(); }
  int thresholdCount() const { return brain_->thresh.count; }
  const Hearing& hearing() const { return hearing_->hearing(); }
  const Clock& clock() const { return brain_->clock; }
  const ScoreState& score() const { return brain_->score; }
  const PictureRun& picture() const { return *pictureRun_; }
  const Brain::ViewState& view() const { return brain_->view; }
  bool drawsInput() const { return drawsInput_; }
  int rack() const { return rack_; }
  int synthLane() const { return synthLane_; }
  bool bands() const { return bands_; }
  double bandGain(int lane) const { return bandGain_[static_cast<std::size_t>(lane)]; }
  double lfoRate(int i) const { return lfos_[static_cast<std::size_t>(i)].rate; }
  double slider(const char* id) const { return brain_->panel.range(id); }
  int learned() const { return static_cast<int>(keyboard_->controllers().size()); }
  /* A hand on a slider that is not remembered, and an end of the morph
     stored: the plugin's shell test's way in. */
  void moveSlider(const std::string& id, double value) {
    scope::moveSlider(id, jsToString(Json::number(value)), *brain_, *core_, *keyboard_, lfos_);
  }
  void storeMorph(bool endB) { morphStore(*brain_, endB); }

 private:
  // A slider moved, by the host's parameter or the page, and remembered as
  // moved since the setup was loaded.
  void moveTo(const std::string& id, const std::u16string& text, bool fromHost) {
    scope::moveSlider(id, text, *brain_, *core_, *keyboard_, lfos_);
    Json hand = Json::array();
    hand.a.push_back(Json::string(std::string_view("s"))); hand.a.push_back(Json::string(std::string_view(id)));
    hand.a.push_back(Json::string(std::string_view(jsNumberToString(brain_->panel.range(id)))));
    remember("s:" + id, std::move(hand));
    changed_ = true;
    if (fromHost) { hostVersion_++; return; }
    // Moved on the page: a host parameter on that slider follows it.
    if (hooks.sliderMoved) hooks.sliderMoved(id, brain_->panel.range(id));
  }

  // The page's other hands: done here, and remembered if they did anything.
  void change(const std::string& id, const Json& value) {
    const std::u16string text = value.type == Json::Type::String ? value.s : u"";
    const bool checked = value.type == Json::Type::Bool && value.b;
    if (id == "srcLanes") { bands_ = false; rackFrom(utf16To8(text)); return; }
    if (id == "srcBands") { drawBands(text == u"1"); return; }
    if (id == "laneMix") { mixFrom(utf16To8(text)); return; }
    if (!controlChange(id, text, checked, *brain_, *core_, *keyboard_, *matrix_, lfos_)) return;
    Json hand = Json::array();
    hand.a.push_back(Json::string(std::string_view("c"))); hand.a.push_back(Json::string(std::string_view(id)));
    hand.a.push_back(value.type == Json::Type::Bool ? value : Json::string(text));
    remember("c:" + id, std::move(hand));
    changed_ = true;
  }

  void press(const std::string& id) {
    if (id == "srcTone" || id == "srcMic") { bands_ = false; drawRack(0, -1); drawFrom(id == "srcMic"); return; }
    if (!controlClick(id, *brain_, *core_, *keyboard_)) return;
    // The Clear button wipes the next frame and leaves nothing to keep.
    if (id == "clearButton") return;
    Json hand = Json::array();
    hand.a.push_back(Json::string(std::string_view("k"))); hand.a.push_back(Json::string(std::string_view(id)));
    /* The buttons come in sets of which one is on: pressing one undoes the
       last of its set. The photocell's is a switch, each press undoing the
       one before, so every press is kept - two taken out would be the
       photocell left as it was, and one taken out the other way round. */
    static const std::pair<const char*, const char*> sets[] {
      { "tune", "tune" }, { "planeOS", "planeOS" }, { "midiEdit", "midiEdit" }, { "midi", "midiMode" }, { "disp", "disp" },
      { "edge", "edge" }, { "mode", "trigMode" }, { "lag", "lagAuto" }, { "see", "see" }, { "measure", "measure" },
      { "lay", "lay" }, { "trigSource", "trigSource" },
    };
    std::string set = "photoButton#" + std::to_string(++presses_);
    for (const auto& [prefix, name] : sets) if (id.rfind(prefix, 0) == 0) { set = name; break; }
    remember("k:" + set, std::move(hand));
    changed_ = true;
  }

  void route(const std::string& text) {
    matrix_->setRoutings(Matrix::decode(text));
    Json hand = Json::array();
    hand.a.push_back(Json::string(std::string_view("r"))); hand.a.push_back(Json::string(std::string_view("")));
    hand.a.push_back(Json::string(std::string_view(text)));
    remember("r", std::move(hand));
    changed_ = true;
  }

  void fadeTo(const Json& value) {
    fadeFromPage(*matrix_, value);
    Json hand = Json::array();
    hand.a.push_back(Json::string(std::string_view("f"))); hand.a.push_back(Json::string(std::string_view("")));
    hand.a.push_back(value);
    remember("f", std::move(hand));
    changed_ = true;
  }

  /* Which source is drawn: the input, or the generator. Not a hand on the
     setup - a setup has never said which source is playing, and a preset
     lands on whatever is - so a load leaves it where it is, and the state
     carries it beside the setup, as `pluginInput`, for a project reopened. */
  void drawFrom(bool input) {
    if (input == drawsInput_) return;
    drawsInput_ = input;
    // What it hears is its own sound only while that is the generator's: a loop then, and not otherwise.
    hearing_->hears(!input);
    changed_ = true;
  }

  /* A rack: how many lanes, and which of them the generator draws - "4,0" is
     four with the generator first, "3,-1" three of the page's own, "0" none
     and back to the generator alone. The page's rack is the page's - files a
     setup cannot hold, a microphone's lane, the mixer - and what reaches the
     instrument is its lanes, as an input of that many channels. Not kept in
     the state, as a rack's files cannot be. */
  void rackFrom(const std::string& text) {
    const std::size_t comma = text.find(',');
    const double count = jsStringToNumber(toU16(text.substr(0, comma)));
    const double synth = comma == std::string::npos ? -1 : jsStringToNumber(toU16(text.substr(comma + 1)));
    drawRack(std::isfinite(count) ? static_cast<int>(count) : 0, std::isfinite(synth) ? static_cast<int>(synth) : -1);
  }
  void drawRack(int count, int synth) {
    const int lanes = std::clamp(count, 0, kRingLanes);
    if (lanes == rack_ && synth == synthLane_) return;
    rack_ = lanes;
    synthLane_ = lanes > 0 && synth >= 0 && synth < lanes ? synth : -1;
    // A rack replaces the input rather than sitting over it: leaving one is the generator again, and no state says the input.
    if (lanes > 0) drawsInput_ = false;
    // The view's lanes, as the page's fitChannels has them: the trigger's lane and the pair held to them.
    brain_->view.lanes = lanes > 0 ? lanes : 2;
    brain_->panel.setLanes(lanes > 0 ? lanes : 2);
    auto& channels = brain_->view.capture.channels;
    channels.resize(static_cast<std::size_t>(std::max(2, lanes)));
    fitView(*brain_);
    pictureSource_.channels = lanes > 0 ? lanes : 2;
    pictureSource_.lanes = lanes > 0;
    changed_ = true;
  }
  /* The band split: the input, split by the page's four crossovers into a
     rack of four lanes, each one signal - the two channels filtered apart
     and halved together, as the page's analysers take a stereo band - and
     what is heard the bands' two channels summed, each band at the gain the
     page's mixer gives it, so a band soloed is the part you are looking at.
     Kept in the state, as the input is: a host's input split is how that
     project is played. Off, it is the input whole again. */
  void drawBands(bool on) {
    if (on == bands_) return;
    if (on) {
      drawRack(kBandCount, -1);
      bands_ = true;
      bandGain_.fill(1.0);
      for (auto& band : bandMemory_) for (auto& channel : band) for (auto& stage : channel) stage = BiquadMemory {};
    } else {
      bands_ = false;
      drawRack(0, -1);
      drawFrom(true);
    }
    changed_ = true;
  }
  /* The page's mixer, "g0,g1,...": each lane's gain, mute and solo already in
     it, taken as sent - nothing the page's mixer makes is below nought, and
     a gain that was would only turn its band over. Not a hand, as the rack
     is not. */
  void mixFrom(const std::string& text) {
    std::size_t at = 0;
    for (std::size_t lane = 0; lane < bandGain_.size() && at <= text.size(); ++lane) {
      const std::size_t end = std::min(text.find(',', at), text.size());
      const double gain = jsStringToNumber(toU16(text.substr(at, end - at)));
      if (std::isfinite(gain)) bandGain_[lane] = gain;
      at = end + 1;
    }
  }
  /* One band's filters for a rate: the page's Butterworth crossovers as its
     BiquadFilterNodes make them (biquadNodeCoefficients), not as the page's
     own JavaScript biquad would, since the page's band split is the nodes. */
  void bandFilters() {
    for (int b = 0; b < kBandCount; ++b) {
      const auto& edge = kBandEdges[static_cast<std::size_t>(b)];
      bandHp_[static_cast<std::size_t>(b)] = edge[0] > 0 ? biquadNodeCoefficients("highpass", edge[0], kButterworthQDb, rate_) : Biquad {};
      bandLp_[static_cast<std::size_t>(b)] = edge[1] > 0 ? biquadNodeCoefficients("lowpass", edge[1], kButterworthQDb, rate_) : Biquad {};
    }
  }
  /* One sample of one band of one channel: the highpass and then the lowpass,
     each as the browser's BiquadFilterNode runs it - coefficients and memory
     in doubles, every output rounded to a float sample before it is
     remembered or passed on - with a stage the band has not got passing its
     input straight through. */
  float bandStep(int band, int channel, float x) {
    auto& memory = bandMemory_[static_cast<std::size_t>(band)][static_cast<std::size_t>(channel)];
    const auto& edge = kBandEdges[static_cast<std::size_t>(band)];
    if (edge[0] > 0) x = memory[0].step(bandHp_[static_cast<std::size_t>(band)], x);
    if (edge[1] > 0) x = memory[1].step(bandLp_[static_cast<std::size_t>(band)], x);
    return x;
  }
  // Whether what it hears is its own sound: the generator, or a rack's trigger on the generator's lane.
  bool hearsItself() const {
    if (rack_ > 0) return synthLane_ >= 0 && static_cast<int>(brain_->view.trigSource) == synthLane_;
    return !drawsInput_;
  }

  // A hand put back from a saved state, as the page sends it.
  void replay(const Json& hand) {
    if (hand.type != Json::Type::Array || hand.a.size() < 2 || hand.a[0].type != Json::Type::String
        || hand.a[1].type != Json::Type::String) return;
    const std::u16string kind = hand.a[0].s;
    const std::string id = utf16To8(hand.a[1].s);
    const Json* value = hand.a.size() > 2 ? &hand.a[2] : nullptr;
    const std::u16string text = value && value->type == Json::Type::String ? value->s : u"";
    if (kind == u"s" && rangeSpec(id)) moveTo(id, text, false);
    else if (kind == u"c" && value) change(id, *value);
    else if (kind == u"k") press(id);
    else if (kind == u"r") route(utf16To8(text));
    else if (kind == u"f") fadeTo(value ? *value : Json::null());
  }

  // A hand remembered, in place of an earlier one it makes redundant.
  void remember(std::string key, Json hand) {
    /* A hand on a control the list already has makes the earlier one
       redundant: what the control says now is the later. Not when a hand
       between them is on a control whose handler reads this one, or this
       one's reads it - the keyboard's drive and play are for the kind chosen
       at the time, an LFO's rate moved while it is synced is its free rate -
       since the earlier one's effect would then be put back in a different
       place. */
    static const std::vector<std::vector<std::string>> reads {
      { "c:genMode", "c:midiDrive", "c:midiPlay" }, { "c:lfoSync0", "s:lfoRate0" }, { "c:lfoSync1", "s:lfoRate1" }, { "c:delaySync", "s:delayMs" },
      { "c:figure", "c:figPathD" }, { "c:arpMode", "c:arpRate", "c:arpOctaves" },
      // The view's: the pair's two menus keep it off one lane twice, mid and side and the lag turn each other off,
      // and a display of X-Y reads the persistence, which the kind menu's choice of X-Y does too.
      { "c:xyX", "c:xyY" }, { "c:midSide", "c:lagOn" }, { "k:disp", "c:persistence", "c:genMode" },
    };
    const auto related = [&](const std::string& a, const std::string& b) {
      if (a == b) return false;
      for (const auto& set : reads) {
        if (std::find(set.begin(), set.end(), a) != set.end() && std::find(set.begin(), set.end(), b) != set.end()) return true;
      }
      return false;
    };
    for (std::size_t i = hands_.size(); i-- > 0;) {
      if (related(hands_[i].key, key)) break;
      if (hands_[i].key == key) { hands_.erase(hands_.begin() + static_cast<std::ptrdiff_t>(i)); break; }
    }
    hands_.push_back({ std::move(key), std::move(hand) });
  }

  /* Render [from, to) of the block into the output and the picture ring.
     Drawing the input, the input goes through the plane - the page's
     effects worklet, `effect` - and what comes out is both the picture and
     what is heard, as the page's analysers and its monitor chain both hang
     off the insert's output; with no input given, silence goes through, so
     the oscillators the effect steps go on stepping. Drawing the generator,
     the input is the generator's, for its live-input modes, as one channel:
     the two summed and halved, which is how the page's worklet takes a
     stereo input on its one-channel input. */
  void render(float* left, float* right, int from, int to) {
    // In pieces no longer than the buffers made for them: a host may hand
    // over a bigger block than it said it would.
    const int most = static_cast<int>(pictureL_.size());
    for (int at = from; at < to; at += most) {
      const int n = std::min(most, to - at);
      float* heardR = right ? right + at : spare_.data();
      const float* inL = input_ ? input_->left + at : nullptr;
      const float* inR = input_ ? (input_->right ? input_->right + at : inL) : nullptr;
      if (rack_ > 0) {
        /* A rack: each lane its input's, the generator's lane its picture's
           left channel - one signal, as the page's generator lane is - and
           what is heard is that lane alone, on both sides, as the page's goes
           to its lane's gain. The generator runs whether or not it has a lane,
           since it steps the oscillators every modulation reads; with none,
           nothing of it is heard. The rest of what is heard is the page's: it
           mixes the lanes it plays itself. */
        core_->block(pictureL_.data(), pictureR_.data(), n, heardL_.data(), heardR_.data());
        std::size_t ring = pictureAt_.load(std::memory_order_relaxed);
        if (bands_) {
          for (int k = 0; k < n; ++k) {
            float* row = &picture_[ring * kRingLanes];
            const float xl = inL ? inL[k] : 0.0f, xr = inR ? inR[k] : xl;
            double hl = 0, hr = 0;
            for (int c = 0; c < kRingLanes; ++c) {
              if (c >= kBandCount) { row[c] = 0.0f; continue; }
              const float yl = bandStep(c, 0, xl), yr = bandStep(c, 1, xr);
              row[c] = (yl + yr) * 0.5f;
              hl += bandGain_[static_cast<std::size_t>(c)] * yl;
              hr += bandGain_[static_cast<std::size_t>(c)] * yr;
            }
            left[at + k] = static_cast<float>(hl);
            heardR[k] = static_cast<float>(hr);
            ring = (ring + 1) % kPictureFrames;
          }
          pictureAt_.store(ring, std::memory_order_release);
          continue;
        }
        for (int k = 0; k < n; ++k) {
          const float h = synthLane_ >= 0 ? heardL_[static_cast<std::size_t>(k)] : 0.0f;
          left[at + k] = h;
          heardR[k] = h;
        }
        for (int k = 0; k < n; ++k) {
          float* row = &picture_[ring * kRingLanes];
          for (int c = 0; c < kRingLanes; ++c) {
            const float* lane = input_ && c < input_->laneCount && input_->lanes[c] ? input_->lanes[c] + at : nullptr;
            row[c] = c >= rack_ ? 0.0f : c == synthLane_ ? pictureL_[static_cast<std::size_t>(k)] : lane ? lane[k] : 0.0f;
          }
          ring = (ring + 1) % kPictureFrames;
        }
        pictureAt_.store(ring, std::memory_order_release);
        continue;
      }
      if (drawsInput_) {
        if (!inL) { std::fill(spare_.begin(), spare_.begin() + n, 0.0f); inL = inR = spare_.data(); }
        core_->effect(inL, inR, pictureL_.data(), pictureR_.data(), n);
        std::copy(pictureL_.begin(), pictureL_.begin() + n, left + at);
        std::copy(pictureR_.begin(), pictureR_.begin() + n, heardR);
      } else {
        if (inL) {
          for (int k = 0; k < n; ++k) mono_[static_cast<std::size_t>(k)] = input_->right ? (inL[k] + inR[k]) * 0.5f : inL[k];
          core_->setInput(mono_.data(), n);
        }
        core_->block(pictureL_.data(), pictureR_.data(), n, left + at, heardR);
        core_->setInput(nullptr, 0);
      }
      std::size_t ring = pictureAt_.load(std::memory_order_relaxed);
      for (int k = 0; k < n; ++k) {
        float* row = &picture_[ring * kRingLanes];
        row[0] = pictureL_[static_cast<std::size_t>(k)];
        row[1] = pictureR_[static_cast<std::size_t>(k)];
        // A rack's lanes past the pair, gone: nothing stale to read if a rack is drawn again.
        for (int c = 2; c < kRingLanes; ++c) row[c] = 0.0f;
        ring = (ring + 1) % kPictureFrames;
      }
      pictureAt_.store(ring, std::memory_order_release);
    }
  }

  /* The last of the picture, the page's screen, for the level and the hearing
     to read: its left channel for both, and its right for the hearing's
     width. A rack's, as the page reads a rack: the trigger's lane for both,
     and for the width the X-Y pair's other lane. */
  void window(std::vector<float>& left, std::vector<float>* right) const {
    const int a = rack_ > 0 ? std::clamp(static_cast<int>(brain_->view.trigSource), 0, rack_ - 1) : 0;
    const int b = rack_ > 0 ? std::clamp(static_cast<int>(brain_->view.xy[1]), 0, rack_ - 1) : 1;
    latestLane(a, left.data(), left.size());
    if (right) latestLane(b, right->data(), right->size());
  }

  double rate_ = 48000;
  std::vector<float> levelLane_, hearL_, hearR_;
  std::unique_ptr<HearingSources> hearing_;  // what it hears of itself, as sources
  std::unique_ptr<PictureRun> pictureRun_;
  CaptureSource pictureSource_;

  std::vector<Lfo> lfos_;
  std::unique_ptr<Generator> core_;
  std::unique_ptr<GeneratorNotes> notes_;
  std::unique_ptr<Keyboard> keyboard_;
  std::unique_ptr<Matrix> matrix_;
  std::unique_ptr<CoreSources> sources_;
  std::unique_ptr<Brain> brain_;  // what a setup sets beyond the generator
  std::unique_ptr<ClockIn> clockIn_;  // MIDI's real-time bytes, to the brain's clock
  std::unique_ptr<BrainSources> brainSources_;  // the macros, the morph's fader and the pluck as destinations
  std::unique_ptr<MidiOut> midiOut_;  // to the owner, through `hooks.midiOut`
  Strike strike_;  // the score's notes, struck in the generator's score voice
  int outAt_ = 0;  // the sample in the block that what the out sends now is sent at
  Json setup_;     // the setup loaded
  /* Every hand on the setup since it was loaded, in order: a slider, a menu,
     a switch, a button, the routings. Saved with it as `pluginHands`, each
     [kind, id, value], and put back in order when the state is loaded. A
     hand on a control already in the list takes the earlier one's place at
     the end - unless a hand between them is one whose handler reads it. */
  struct Hand { std::string key; Json hand; };
  std::vector<Hand> hands_;
  int presses_ = 0;  // the photocell's button, each press its own hand
  int hostVersion_ = 0;
  bool changed_ = false;
  std::size_t learnedSeen_ = 0;
  double nowMs_ = 0, lastBlockMs_ = 0;  // the matrix's clock: audio time, not the wall's
  std::vector<float> pictureL_, pictureR_, spare_, mono_, heardL_, heardR_;  // a block's worth, made in prepare
  const Input* input_ = nullptr;  // this block's, while it is rendered
  bool drawsInput_ = false;       // drawing the input rather than the generator
  int rack_ = 0;                  // drawing a rack of this many lanes, or none
  int synthLane_ = -1;            // the rack's lane the generator draws, or none
  bool bands_ = false;            // the rack is the input split into bands
  // A biquad's memory as the browser keeps it: doubles, fed and feeding back float samples.
  struct BiquadMemory {
    double x1 = 0, x2 = 0, y1 = 0, y2 = 0;
    float step(const Biquad& c, float x) {
      const float y = static_cast<float>(c.b0 * x + c.b1 * x1 + c.b2 * x2 - c.a1 * y1 - c.a2 * y2);
      x2 = x1; x1 = x; y2 = y1; y1 = y;
      return y;
    }
  };
  std::array<Biquad, kBandCount> bandHp_ {}, bandLp_ {};
  std::array<std::array<std::array<BiquadMemory, 2>, 2>, kBandCount> bandMemory_ {};  // band, channel, stage
  std::array<double, kBandCount> bandGain_ { 1, 1, 1, 1 };
  std::array<float, kPictureFrames * kRingLanes> picture_ {};
  std::atomic<std::size_t> pictureAt_ { 0 };
};

}  // namespace scope
