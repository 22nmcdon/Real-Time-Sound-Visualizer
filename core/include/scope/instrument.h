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
#include <cstring>
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
#include "scope/scan.h"
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
  /* A MIDI message at its sample in the block, and how many milliseconds
     before that sample it really came, where its owner knows better than
     the sample says. A host places each message at its own sample, so the
     plugin leaves it at nought; the site's worklet can only hand a message
     over at the top of the next block, which is late by however long the
     browser held it, so the page sends each one's time with it and the
     bridge works this out (10 Nov). Only the clock reads it: a tick timed
     by its block was off by up to a callback's worth, the tempo it was read
     from swung by more than the delay's slack, and a synced delay's read
     head glided back and forth - Sync warbled on the site and not in parity,
     which times its ticks exactly. */
  struct Event { int sample; const std::uint8_t* data; std::size_t size; double earlyMs = 0; };
  // A host parameter moved since the last block: a hand on its slider.
  struct HostSlider { const char* id; double value; };
  /* A block's input: what a host's input bus or a page's microphone hands
     over, its right channel null for a mono input. It also carried a rack's
     lanes until P5 cut the rack: a host plays files, each track its own
     instance. */
  struct Input {
    const float* left;
    const float* right;
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
    scan_ = std::make_unique<ScanReader>();  // its tables made here, off the audio thread
    // The default cycles' tables, and the setup's own, built here rather than
    // by a load on the audio thread later (CycleCache).
    for (int k = 0; k < static_cast<int>(kCycleSlots); k++) CycleCache::shared().warm(cycleDefault(k));
    warmCycles(setup);
    core_ = std::make_unique<Generator>(sampleRate, slot::Used, lfos_);
    notes_ = std::make_unique<GeneratorNotes>(*core_);
    brain_ = std::make_unique<Brain>();
    clockIn_ = std::make_unique<ClockIn>(brain_->clock);
    keyboard_ = std::make_unique<Keyboard>(*notes_, clockIn_.get());
    // The layer the panel shows follows the keyboard, as the page's syncLayers has it.
    keyboard_->setLayerPanel([this] { syncLayerPanel(*brain_, *core_, *keyboard_); });
    // A note strikes the screen where Scan reads (P7b).
    keyboard_->setStrike([this](int note, double velocity, int layers) { scanStrike(note, velocity, layers); });
    // The expression pedal is the Picture amount, held as the slider holds it.
    // A known limitation: the plugin's page is not told, so its slider stays
    // where the hand left it while the sound follows the foot. Telling it as a
    // host parameter is told - a kept hand, hostVersion and hostMoved - would
    // now move just that knob on the page, which restored its whole setup at
    // every count until 7 Nov; what is left is a kept hand at a pedal's
    // message rate, dozens a second, each allocating on the audio thread.
    // On the hand or hands the Picture section's Amount is on (G6), as the page's slider moved by it.
    keyboard_->setSwell([this](double amount) { pictureAmountTo(*brain_, *keyboard_, amount); });
    /* The wheel or pressure given to the Picture amount, as the expression
       pedal sets it, or to Scan's depth, as a hand on its slider (6 Nov);
       the bend and the vibrato the keyboard sets on the generator itself.
       None is a hand on the setup, being where the hands are. */
    keyboard_->setExpress([this](Keyboard::Express to, double v) {
      if (to == Keyboard::Express::Picture) pictureAmountTo(*brain_, *keyboard_, v * 100);
      else if (to == Keyboard::Express::Scan) scope::moveSliderTo("oscScan", v * 100, *brain_, *core_, *keyboard_, lfos_);
    });
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
    stepPos_ = 0;
    stepStartMs_ = 0;
    ramps_ = {};
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
    brainSources_ = std::make_unique<BrainSources>(*matrix_, *brain_);
    // The view's destinations before any setup, so a preset's routings onto them are heard.
    pictureRun_ = std::make_unique<PictureRun>(*matrix_, *brain_);
    pictureSource_.rate = sampleRate;
    /* The capture ring and the bands' filter memory start empty, as a project
       reopened starts. Prepared again - a host's rate or device changing - the
       ring held the picture from before, at the rate from before, and the new
       phosphor drew it: the sound parted from the same state reopened 22 ms in
       (the shell test, 6 Nov). */
    picture_.fill(0.0f);
    pictureAt_.store(0);
    bandMemory_ = {};
    bandFilters();
    pictureSource_.capacity = static_cast<double>(kPictureFrames);
    pictureSource_.channels = 2;
    pictureSource_.lanes = false;
    /* The latest n frames of the ring, oldest first, nought before the start
       of what it holds - which the capacity says it never asks for - into
       lanes the caller keeps. A lane count other than the one they have is
       a change in what is drawn, a hand on the face, and makes its lanes
       then, with room for the most a capture asks; otherwise this only
       writes (G8). */
    captureMost_ = captureMost(sampleRate, static_cast<double>(kPictureFrames));
    pictureSource_.latest = [this](std::size_t n, std::vector<Lane>& out) {
      const auto lanes = static_cast<std::size_t>(pictureSource_.channels);
      if (out.size() != lanes) {
        out.resize(lanes);
        for (auto& lane : out) lane.reserve(captureMost_);
      }
      for (std::size_t c = 0; c < lanes; ++c) {
        out[c].resize(n);
        latestLane(static_cast<int>(c), out[c].data(), n);
      }
    };
    /* A host is always a keyboard, so the generator is gated from the start -
       silent until a note - which is what the page's first frame does. Derived
       by the keyboard, not set here. Until 10 Nov the site's page said when it
       had no keyboard (the `keyboardPresent` control), and the generator then
       played with no note; the site is silent until a note now too, so no
       page sends it, and only parity's fixtures for a generator heard without
       a note do. */
    keyboard_->setPresent(true);
    load(setup, true);
    /* The capture's room, for as many lanes as the setup draws: made here so
       the first frame on the audio thread makes nothing (G8). */
    pictureRun_->reserve(notes_->layout() == Layout::Each || bands_ ? 4 : 2, sampleRate, static_cast<double>(kPictureFrames));
    // Opening at the Output it was saved at, not gliding down to it (G7).
    core_->settleOutput();
    keyboard_->frame();
    changed_ = true;
    hearL_.assign(kHearN, 0.0f);
    hearR_.assign(kHearN, 0.0f);
    const auto size = static_cast<std::size_t>(std::max(64, samplesPerBlock));
    pictureL_.assign(size, 0.0f); pictureR_.assign(size, 0.0f); spare_.assign(size, 0.0f); mono_.assign(size, 0.0f);
    pictureBL_.assign(size, 0.0f); pictureBR_.assign(size, 0.0f);
  }

  // A setup loaded as a preset is: the core restored, the hands on it since put back.
  void load(const Json& setup, bool fromHost) {
    setup_ = setup;
    hands_.clear();
    restoreSetup(setup_, *brain_, *core_, *keyboard_, *matrix_, lfos_);
    /* The hand the face is editing is not the setup's (G6), and a load leaves
       it where it is: kept as the first hand, so the hands after it that
       move a hand's own control go back to that hand when a project opens. */
    if (keyboard_->edit() == 1) {
      Json hand = Json::array();
      hand.a.push_back(Json::string(std::string_view("k"))); hand.a.push_back(Json::string(std::string_view("editHandB")));
      remember("k:hand#" + std::to_string(++presses_), std::move(hand));
    }
    // Nothing read for a quarter of a second while it lands, as the page's restoreInto opens with scanFreeze.
    scan_->freeze(nowMs_);
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
    /* The master Output (G7), which a saved state carries beside the setup,
       as it carries the input: a project reopens at the level it was heard
       at. A preset or a code says nothing, and leaves it where it is - which
       is the point of its being no setup's: loading a sound must not change
       how loud you are listening. Not a hand, so no hand clears it. */
    if (const Json* out = setup_.type == Json::Type::Object ? setup_.get("pluginOutput") : nullptr) {
      if (out->type == Json::Type::Number) scope::moveSliderTo("output", out->n, *brain_, *core_, *keyboard_, lfos_);
      setup_.erase("pluginOutput");
    }
    // A setup restores two lanes' worth of view; the band split has four, and keeps them.
    if (bands_) { brain_->view.capture.channels.resize(static_cast<std::size_t>(kBandCount)); fitView(*brain_); }
    if (hooks.loaded) hooks.loaded();
    changed_ = true;
    // A load, from anywhere, is a fresh start for the knobs the host has moved.
    hostMoved_.clear();
    if (fromHost) { hostVersion_++; hostLoads_++; }
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

  /* One block, in steps of 128 frames whatever the host's block (6 Nov): the
     page's once-a-frame work at the top of each step, then the generator up
     to each MIDI event, the event, and on. The steps fall on every 128th
     frame of the instrument's life and carry across the host's blocks, so a
     block of 100 or 441 frames is as good as one of 2048: the same samples
     come out. They used to be the host's blocks, so the matrix, the LFOs'
     routes, the picture stage and the clock stepped once a host block, and
     at 512 or 2048 the plugin was another instrument than the site, whose
     worklet steps every 128, and an offline render changed with the
     buffer. A host's parameter moved is walked from where it stood to where
     it was put across the steps its block holds, rather than stepped at
     the block's top, and kept as one hand at the end. `right` may be null;
     `transport` is null where the host gives none, and is the block's first
     frame's, carried on to each step's. */
  static constexpr int kStepFrames = 128;  // the site's worklet's block
  void block(float* left, float* right, int frames, const Event* events, std::size_t eventCount, const Transport* transport,
             const HostSlider* sliders, std::size_t sliderCount, const Input* input = nullptr) {
    const int firstStep = stepPos_ == 0 ? 0 : kStepFrames - stepPos_;
    const int steps = firstStep < frames ? (frames - firstStep + kStepFrames - 1) / kStepFrames : 0;
    for (std::size_t i = 0; i < sliderCount; ++i) rampTo(sliders[i].id, sliders[i].value, std::max(1, steps));
    int pos = 0;
    std::size_t e = 0;
    while (pos < frames) {
      if (stepPos_ == 0) {
        if (transport) {
          Transport now = *transport;
          // On to this step's first frame, while it plays; stopped, the host's position stands.
          if (now.ppq && now.playing) *now.ppq += pos / rate_ * now.bpm / 60;
          step(&now, pos);
        } else {
          step(nullptr, pos);
        }
      }
      const int n = std::min(kStepFrames - stepPos_, frames - pos);
      std::size_t upTo = e;
      if (pos + n >= frames) upTo = eventCount;
      else while (upTo < eventCount && events[upTo].sample < pos + n) ++upTo;
      Input shifted { nullptr, nullptr };
      if (input) shifted = Input { input->left + pos, input->right ? input->right + pos : nullptr };
      input_ = input ? &shifted : nullptr;
      play(left + pos, right ? right + pos : nullptr, n, events + e, upTo - e, pos);
      input_ = nullptr;
      e = upTo;
      pos += n;
      stepPos_ = (stepPos_ + n) % kStepFrames;
    }
  }

 private:
  // The once-a-frame work, at the top of a step `at` frames into the host's block.
  void step(const Transport* transport, int at) {
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
    /* The host's parameters, each as a hand on its slider: the slider set by
       the number, as the text of it would set it, and its handler run, all
       without allocating (5v). Keeping the hand for the state still does, as
       the state's publishing at the block's end does (PLAN.md, 5v). */
    stepRamps();
    /* The level was followed here, over the last 2048 frames of the picture,
       for the source F4b cut; nothing read it after, and the second review's
       sweep took it out (the meter is the page's own). The hearing, from the
       last 4096 frames, its held key the lowest the
       hands hold. Once a block where the page's is once a frame. It was made
       with room for this window, so it allocates nothing here (5t). And only
       while a routing heard comes from it: the family is parked, and its
       transform every block was about five points of a core on the plain
       sine for readings nothing read (second review, part 2). Asked at this
       step's time, as the page asks at its frame's. */
    const bool heard = matrix_->routedFrom("hear.", nowMs_);
    std::optional<double> heldHz;
    if (heard) {
      window(hearL_, &hearR_);
      if (!keyboard_->notes().empty()) {
        int low = keyboard_->notes().front().note;
        for (const auto& held : keyboard_->notes()) low = std::min(low, held.note);
        heldHz = midiHz(low);
      }
    }
    hearing_->hears(hearsItself());
    hearing_->setNow(nowMs_);
    hearing_->step(*matrix_, true, heard, hearL_.data(), hearL_.data(), hearR_.data(), hearL_.size(), rate_, lastBlockMs_, heldHz, nowMs_);
    keyboard_->setNow(nowMs_);
    keyboard_->setTempo(brain_->clock.bpm);
    keyboard_->frame();
    outAt_ = at;  // what is sent before the step's events is sent at its top
    /* The score's step, the arpeggio's and the events, in the page's frame's
       order: once a step, as the page does them once a frame, so a note-off
       due inside a step goes at the next step's top - 2.7 ms late at most,
       where the page's frames are 17 ms apart. The score
       reads the grid drawn here, as the last picture frame left it. */
    scoreTick(brain_->score, nowMs_, true, brain_->clock, pictureRun_->phosphor().grid().data(),
              keyMask(brain_->keyRoot, brain_->keyScale), strike_, midiOut_.get());
    keyboard_->arpTick(nowMs_);  // the step due this frame, if one is
    /* The picture's frame, when a sixtieth of a second of audio has gone: the
       capture, and the photocell and the picture's sources stepped from the
       grid the last frame left, before the matrix reads them - with no
       limiter to read, the output being the owner's. Its capture and its
       walk allocated as they went, a known cost on this thread from 5v
       until G8: the capture now writes into frames kept from frame to frame
       and the walk points at its figures rather than copying them, so a
       steady frame allocates nothing (parity's block_alloc_cpp). */
    const bool pictureFrame = pictureRun_->due(nowMs_);
    if (pictureFrame) {
      pictureRun_->before(*matrix_, pictureSource_, 0);
      scanFrame();
    }
    matrix_->setLayered(keyboard_->layersOn());
    matrix_->setStrikes(keyboard_->strikes());
    // Whether each layer's sound is moved by its own picture (P6): as the frame's step left it, for the frame's destinations.
    matrix_->setLayerPictures(pictureRun_->layers().live());
    matrix_->frame(nowMs_);
    /* After the matrix, so a source on the fader is already counted. The walk
       moves sliders by number and fires their handlers, none of which
       allocates (5v). It stays here, on the audio thread, rather than going
       to the message thread: here it moves in step with the audio, live or
       in a host's offline render, where the message thread does not. */
    morphStep(*brain_, *core_, *keyboard_, lfos_);
    // The zoom made again from what the matrix wrote, and the frame's deposits, as the page draws after its matrix.
    pictureRun_->afterMatrix();
    if (pictureFrame) {
      pictureRun_->setLayered(keyboard_->layersOn());
      pictureRun_->draw(pictureSource_, kCanvas);
      // And the readout's: the automatic lag locked to the held note while the note is the truth, else to what is heard.
      std::optional<double> played;
      if (keyboard_->settings().truth && !keyboard_->notes().empty()) {
        int low = keyboard_->notes().front().note;
        for (const auto& held : keyboard_->notes()) low = std::min(low, held.note);
        played = midiHz(low);
      }
      pictureRun_->readout(pictureSource_, played);
    }
    // And as the draw left it, for the routes: the page's routes read it after its frame's draw.
    matrix_->setLayerPictures(pictureRun_->layers().live());
    core_->setRoutes(matrix_->routes(nowMs_));
    stepStartMs_ = nowMs_;
    lastBlockMs_ = 1000.0 * kStepFrames / rate_;
    nowMs_ += lastBlockMs_;
  }

  // A piece of a step, `frames` long, `offset` frames into the host's block,
  // its events' samples counted from the block's top.
  void play(float* left, float* right, int frames, const Event* events, std::size_t eventCount, int offset) {
    // Each event at its own sample, not at the top of the block: the
    // generator is run up to it, told, and run on. The arpeggiator's first
    // step, which the page strikes on a timer once the chord has gathered,
    // is struck the same way at the sample its time falls on.
    int done = 0;
    const double blockMs = stepStartMs_ + 1000.0 * stepPos_ / rate_;  // this piece's first sample
    const double endMs = blockMs + 1000.0 * frames / rate_;
    const auto wakesUntil = [&](int until) {
      for (auto wake = keyboard_->arpWake(); wake && *wake < endMs; wake = keyboard_->arpWake()) {
        const int at = std::clamp(static_cast<int>(std::ceil((*wake - blockMs) * rate_ / 1000)), done, frames);
        if (at > until) break;
        render(left, right, done, at);
        done = at;
        outAt_ = offset + std::min(at, frames - 1);  // a wake in the piece's last fraction of a sample rounds up past its end
        keyboard_->setNow(*wake);
        keyboard_->wakeArp();
      }
    };
    for (std::size_t e = 0; e < eventCount; ++e) {
      const Event& event = events[e];
      const int at = std::clamp(event.sample - offset, done, frames);
      wakesUntil(at);
      render(left, right, done, at);
      done = at;
      outAt_ = offset + at;
      keyboard_->setNow(blockMs + 1000.0 * at / rate_);
      /* The bytes, not anyone's reading of them: the keyboard is the page's
         `midiBytes` ported, so a note-on at velocity nought, a controller,
         the pedal and a panic all mean here what they mean on the page. A
         chord handed to the generator is copied into the list it keeps, and
         its voices take what retired ones left, so a note allocates nothing
         (G8) unless it makes a chord larger than any before it. */
      clockIn_->at(blockMs + 1000.0 * at / rate_ - event.earlyMs);  // a clock byte at its own time
      keyboard_->bytes(event.data, event.size);
    }
    wakesUntil(frames);
    render(left, right, done, frames);
  }

  /* A host parameter's walk: from where its slider stands to the value put,
     over the steps of the block it came in. Moved by number, which
     allocates nothing (5v); kept as a hand once, at its end. A new value for
     one still walking walks on from where it has got to. */
  struct Ramp { const char* id = nullptr; double from = 0, to = 0; int steps = 0, done = 0; };
  void rampTo(const char* id, double to, int steps) {
    /* The level, the cutoff and the Output glide a sample at a time in the
       generator (its levelsStep and outputStep), so a host's move of one is
       put whole at the next step and the glide is all its smoothing. Walked
       across the block's steps as well, it was a walk at a block of 512 and
       none at 128, so what was heard depended on the host's buffer, which
       the steps exist to stop (second review, 1.3). The others still walk:
       a hand on them sets the block's value, with nothing per sample under
       it. */
    if (std::strcmp(id, "amp") == 0 || std::strcmp(id, "vcfCut") == 0 || std::strcmp(id, "output") == 0) steps = 1;
    Ramp* r = nullptr;
    for (auto& x : ramps_) if (x.id && std::strcmp(x.id, id) == 0) { r = &x; break; }
    if (!r) for (auto& x : ramps_) if (!x.id) { r = &x; break; }
    if (!r) { moveToNumber(id, to); return; }  // more at once than there is room for: stepped, as before
    *r = Ramp { id, brain_->panel.range(id), to, steps, 0 };
  }
  void stepRamps() {
    for (auto& r : ramps_) {
      if (!r.id) continue;
      r.done++;
      if (r.done >= r.steps) { moveToNumber(r.id, r.to); r.id = nullptr; continue; }
      scope::moveSliderTo(r.id, r.from + (r.to - r.from) * r.done / r.steps, *brain_, *core_, *keyboard_, lfos_);
    }
  }

 public:

  /* Whether the state the page is shown has changed since it was last
     published - a hand, a load, a controller learned - and, once the owner
     has published it, that it has. Two calls rather than one so an owner
     that could not publish this time (the plugin, when the page is reading)
     is asked again next block. */
  bool changed() {
    return changed_;
  }
  void published() { changed_ = false; }
  // How many changes came from the host rather than the page: a load, a parameter moved.
  int hostVersion() const { return hostVersion_; }
  /* How many of them were loads, and which sliders the host has moved since
     the last load, joined by commas: so the page, its count moved and no new
     load, moves those knobs and restores nothing (hostPull on the page has
     why). */
  int hostLoads() const { return hostLoads_; }
  std::string hostMoved() const {
    std::string out;
    for (const auto& id : hostMoved_) out += (out.empty() ? "" : ",") + id;
    return out;
  }

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
    setup.erase("pluginInput");
    setup.erase("pluginBands");
    if (drawsInput_) setup.set("pluginInput", Json::boolean(true));
    if (bands_) setup.set("pluginBands", Json::boolean(true));
    // The Output beside it, where it is not where it starts; the plugin's own save writes it always.
    setup.erase("pluginOutput");
    if (brain_ && brain_->panel.range("output") != rangeSpec("output")->value)
      setup.set("pluginOutput", Json::number(brain_->panel.range("output")));
    const auto code = encodeSetup(setup);
    return code ? *code : std::string();
  }

  // Scan's reading (P7a), for a harness: the paths, the holds, the freeze.
  const ScanReader& scan() const { return *scan_; }

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
     first, as many lanes as the picture has interleaved - two, four, or the
     band split's - so the page, which knows how many frames the ring is,
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
  // The generator, for what the page reads off it: its envelope, gate and budget.
  const Generator& generator() const { return *core_; }
  // Each layer's picture (P6), for the page's readings and a harness.
  const LayerPictures& layerPictures() const { return pictureRun_->layers(); }
  // The two oscillators, which move the picture's destinations on the page as well as the sound here.
  const std::vector<Lfo>& lfos() const { return lfos_; }
  /* The same, as they stood when the picture's newest frame was written, for
     a reader on another thread: each oscillator's phase, held value and value.
     The plugin's page moves the picture's destinations with these, as the
     site's page does with the ones the worklet posts, so an oscillator routed
     to both moves the picture and the sound in step. */
  std::array<double, 6> lfosServed() const {
    pictureAt_.load(std::memory_order_acquire);
    std::array<double, 6> out {};
    for (std::size_t i = 0; i < out.size(); ++i) out[i] = lfosServed_[i].load(std::memory_order_relaxed);
    return out;
  }
  /* The generator's envelope as it stood at the picture's newest frame -
     its level, whether it is gated (one or nought), its stage (nought to
     four, as Envelope::Stage counts them) and its velocity - for the
     Envelope card's dot on the plugin's page (12 Nov), which until then was
     sent none of it and never moved. The site's page has the same four from
     brain_readings. Published with the oscillators, so as cheaply: four
     relaxed stores a block, nothing allocated and nothing waited on. */
  std::array<double, 4> envelopeServed() const {
    pictureAt_.load(std::memory_order_acquire);
    std::array<double, 4> out {};
    for (std::size_t i = 0; i < out.size(); ++i) out[i] = envServed_[i].load(std::memory_order_relaxed);
    return out;
  }
  // How many lanes the picture has: two, or four for a figure a layer or the band split.
  int pictureLanes() const { return pictureSource_.channels; }

  // What the owners and their tests read.
  const Tone& tone() const { return core_->tone(); }
  const LayerSettings& toneB() const { return core_->toneB(); }
  Keyboard& keyboard() { return *keyboard_; }
  const Keyboard& keyboard() const { return *keyboard_; }
  Matrix& matrix() { return *matrix_; }
  const Hearing& hearing() const { return hearing_->hearing(); }
  const Clock& clock() const { return brain_->clock; }
  const ScoreState& score() const { return brain_->score; }
  const PictureRun& picture() const { return *pictureRun_; }
  // The routes the generator was last given, and the figures the screen lays out, for a harness.
  const std::vector<Route>& routes() const { return matrix_->lastRoutes(); }
  std::size_t figures() const { return brain_->view.screen.figures.size(); }
  const Brain::ViewState& view() const { return brain_->view; }
  bool drawsInput() const { return drawsInput_; }
  // How many lanes the input is drawn as: the band split's four, or none.
  int lanes() const { return bands_ ? kBandCount : 0; }
  bool bands() const { return bands_; }
  double bandGain(int lane) const { return bandGain_[static_cast<std::size_t>(lane)]; }
  double lfoRate(int i) const { return lfos_[static_cast<std::size_t>(i)].rate; }
  double slider(const char* id) const { return brain_->panel.range(id); }
  /* Which layer the panel's voice controls write: the plugin's host
     parameters on those controls read back when it changes, since the same
     slider then shows the other layer's value. */
  int panelLayer() const { return brain_->panelLayer; }
  /* A hand on a slider that is not remembered, and an end of the morph
     stored: the plugin's shell test's way in. */
  void moveSlider(const std::string& id, double value) {
    scope::moveSlider(id, jsToString(Json::number(value)), *brain_, *core_, *keyboard_, lfos_);
  }
  void storeMorph(bool endB) { morphStore(*brain_, endB); }

 private:
  // A slider moved, by the host's parameter or the page, and remembered as
  // moved since the setup was loaded.
  /* A host parameter's move: the slider moved by the number, with no text
     made, which is the same value the text would have left (5v). Then kept
     as a hand, which still allocates - the state's bookkeeping, on this
     thread with the state's publishing (PLAN.md, 5v). */
  void moveToNumber(const std::string& id, double value) {
    scope::moveSliderTo(id, value, *brain_, *core_, *keyboard_, lfos_);
    keepSlider(id, true);
  }
  void moveTo(const std::string& id, const std::u16string& text, bool fromHost) {
    scope::moveSlider(id, text, *brain_, *core_, *keyboard_, lfos_);
    keepSlider(id, fromHost);
  }
  void keepSlider(const std::string& id, bool fromHost) {
    /* The Output is not a hand on the setup (G7): the state carries it as
       `pluginOutput`, beside the setup, so a load - which clears the hands -
       never takes it back to unity. Its host parameter and the page still
       follow it as any other slider's. */
    if (id == "output") {
      changed_ = true;
      if (fromHost) {
        hostVersion_++;
        if (std::find(hostMoved_.begin(), hostMoved_.end(), id) == hostMoved_.end()) hostMoved_.push_back(id);
      } else if (hooks.sliderMoved) {
        hooks.sliderMoved(id, brain_->panel.range(id));
      }
      return;
    }
    Json hand = Json::array();
    hand.a.push_back(Json::string(std::string_view("s"))); hand.a.push_back(Json::string(std::string_view(id)));
    hand.a.push_back(Json::string(std::string_view(jsNumberToString(brain_->panel.range(id)))));
    remember("s:" + id, std::move(hand));
    changed_ = true;
    if (fromHost) {
      hostVersion_++;
      if (std::find(hostMoved_.begin(), hostMoved_.end(), id) == hostMoved_.end()) hostMoved_.push_back(id);
      return;
    }
    // Moved on the page: a host parameter on that slider follows it.
    if (hooks.sliderMoved) hooks.sliderMoved(id, brain_->panel.range(id));
  }

  // The page's other hands: done here, and remembered if they did anything.
  void change(const std::string& id, const Json& value) {
    const std::u16string text = value.type == Json::Type::String ? value.s : u"";
    const bool checked = value.type == Json::Type::Bool && value.b;
    if (id == "srcBands") { drawBands(text == u"1"); return; }
    if (id == "laneMix") { mixFrom(utf16To8(text)); return; }
    /* Whether there is a keyboard to wait for, which the site's page knows
       (a MIDI port or the screen's keys) and the plugin never says, being
       always one. Not a hand on the setup: it is where the instrument is
       playing, not what it plays. The gate follows at the next block. */
    if (id == "keyboardPresent") { keyboard_->setPresent(text != u"0"); return; }
    /* How long a stage switched in or out crossfades (the generator's
       `switchMs`), in milliseconds: parity's handle on the switch as it
       was, at nought, which is the null for its check that the wheel on the
       Picture amount no longer clicks. Nothing on the page sends it. */
    if (id == "switchMs") { core_->set("switchMs", jsNumber(utf16To8(text))); return; }
    if (id == "drawn") { drawnFrom(text); return; }
    if (!controlChange(id, text, checked, *brain_, *core_, *keyboard_, lfos_)) return;
    Json hand = Json::array();
    hand.a.push_back(Json::string(std::string_view("c"))); hand.a.push_back(Json::string(std::string_view(id)));
    hand.a.push_back(value.type == Json::Type::Bool ? value : Json::string(text));
    remember("c:" + id, std::move(hand));
    changed_ = true;
  }

  /* What is drawn by hand - the cycles - as the setup's own fields in one
     JSON object: "cycle", "cycles", either. A drawing is neither a slider
     moved nor a preset loaded, so it reached the instrument by neither: on
     the site and in the plugin, a cycle drawn on the panel was never heard.
     Kept in the setup the state is made from, rather than as a hand, so a
     project reopened draws it again by the same restore that a preset does.
     A figure drawn on the screen ("figDrawn") came this way too until G2
     took the figures; one sent now is not kept. */
  void drawnFrom(const std::u16string& text) {
    const auto part = jsonParse(text);
    if (!part || part->type != Json::Type::Object) return;
    if (setup_.type != Json::Type::Object) setup_ = Json::object();
    for (const char* key : { "cycle", "cycles" })
      if (const Json* v = part->get(key)) setup_.set(key, *v);
    if (part->get("cycle") || part->get("cycles"))
      restoreCycles(setup_.get("cycle"), setup_.get("cycles"), *brain_, *core_);
    changed_ = true;
  }

  void press(const std::string& id) {
    if (id == "srcTone" || id == "srcMic") { if (bands_) { bands_ = false; drawLanes(0); } drawFrom(id == "srcMic"); return; }
    if (!controlClick(id, *brain_, *core_, *keyboard_, matrix_.get())) return;
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
    /* The hands (G6): which hand the face edits, and each section's link.
       Every press is kept, and none is made redundant by a later one, since
       a hand on a control after it went to the hand it chose (remember). */
    if (id.rfind("editHand", 0) == 0 || id.rfind("link", 0) == 0) set = "hand#" + std::to_string(presses_);
    remember("k:" + set, std::move(hand));
    changed_ = true;
  }

  /* The page's routings after an edit: every routing, and since G5b, after a
     bar, the sources Routings has silenced (hostRoutingsText), whose
     routings are kept and not heard. The hand keeps the text whole, so a
     project saved while a source is silent has its routings back when it
     opens. A text with no bar is one from before, every routing heard. */
  void route(const std::string& text) {
    // Since G6, after a second bar, the upper hand's own depths, as `modB` has them.
    const std::size_t bar = text.find('|');
    const std::size_t bar2 = bar == std::string::npos ? bar : text.find('|', bar + 1);
    std::vector<Routing> list = Matrix::decode(std::string_view(text).substr(0, bar));
    if (bar2 != std::string::npos) Matrix::applyB(list, std::string_view(text).substr(bar2 + 1));
    matrix_->keep(list,
                  bar == std::string::npos ? std::vector<std::string>()
                                           : Matrix::silentIds(std::string_view(text).substr(bar + 1, bar2 == std::string::npos ? std::string::npos : bar2 - bar - 1)),
                  false);
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
    keyboard_->setLayable(!bands_ && !drawsInput_);
    changed_ = true;
  }

  /* The page's view of a layout (syncLayers, buildLaneRows, fitChannels,
     sourceFigures, layerTurnsItself), for the grid the instrument draws
     itself: four lanes and a figure each, or two and the one pair the menus
     chose; and layer B's figure left to its own turn while it has a plane
     of its own and is drawn as a figure of its own. Until this the grid was
     given neither, so it walked layer A's pair alone, and the photocell and
     the picture's sources in the plugin never saw layer B (or, until G2,
     the second generator). Worked out every block, and written only when
     it changes: the lanes' vector can grow, which allocates, once, the
     first time two figures are drawn - and the capture makes its two
     lanes more then (G8), a hand on the face rather than a steady block. */
  void layOutPicture(Layout lay) {
    const int lanes = lay == Layout::Each ? 4 : 2;
    Brain::ViewState& w = brain_->view;
    // The lanes' settings too: a setup restores two lanes' worth of them.
    if (w.lanes != lanes || w.capture.channels.size() != static_cast<std::size_t>(lanes)) {
      w.lanes = lanes;
      brain_->panel.setLanes(lanes);
      w.capture.channels.resize(static_cast<std::size_t>(lanes));
      fitView(*brain_);
    }
    const bool each = lay == Layout::Each;
    if (each != !w.screen.figures.empty()) {
      w.screen.figures.clear();
      if (each) w.screen.figures = { { 0, 1 }, { 2, 3 } };
    }
    w.screen.ownTurn = keyboard_->layersOn() && brain_->planeB.own && lay != Layout::Against;
  }

  /* The lanes the input is drawn as: the band split's four, or none - the
     generator, or the input whole. A rack of the page's files, with the
     generator and the live input as lanes of it, was the other way to have
     lanes until P5 cut it. */
  void drawLanes(int lanes) {
    /* A rack replaced the input rather than sitting over it, and the band
       split still does: leaving it is the input whole (drawBands). */
    if (lanes > 0) drawsInput_ = false;
    // The view's lanes, as the page's fitChannels has them: the trigger's lane and the pair held to them.
    brain_->view.lanes = lanes > 0 ? lanes : 2;
    brain_->panel.setLanes(lanes > 0 ? lanes : 2);
    auto& channels = brain_->view.capture.channels;
    channels.resize(static_cast<std::size_t>(std::max(2, lanes)));
    fitView(*brain_);
    pictureSource_.channels = lanes > 0 ? lanes : 2;
    pictureSource_.lanes = lanes > 0;
    // Two layers are two figures, and an input has no layers: a split is kept, not applied (layersOn).
    keyboard_->setLayable(lanes == 0 && !drawsInput_);
    changed_ = true;
  }
  /* The band split: the input, split by the page's four crossovers into a
     set of four lanes, each one signal - the two channels filtered apart
     and halved together, as the page's analysers take a stereo band - and
     what is heard the bands' two channels summed, each band at the gain the
     page's mixer gives it, so a band soloed is the part you are looking at.
     Kept in the state, as the input is: a host's input split is how that
     project is played. Off, it is the input whole again. */
  void drawBands(bool on) {
    if (on == bands_) return;
    if (on) {
      bands_ = true;
      drawLanes(kBandCount);
      bandGain_.fill(1.0);
      for (auto& band : bandMemory_) for (auto& channel : band) for (auto& stage : channel) stage = BiquadMemory {};
    } else {
      bands_ = false;
      drawLanes(0);
      drawFrom(true);
    }
    changed_ = true;
  }
  /* The page's mixer, "g0,g1,...": each lane's gain, mute and solo already in
     it, taken as sent - nothing the page's mixer makes is below nought, and
     a gain that was would only turn its band over. Not a hand: the mixer is
     the page's. */
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
  // Whether what it hears is its own sound: the generator's, and not an input's, whole or split.
  bool hearsItself() const { return !bands_ && !drawsInput_; }

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
       one's reads it - an LFO's rate moved while it is synced is its free
       rate - since the earlier one's effect would then be put back in a
       different place. (The kind menu, the keyboard's drive and play, which
       were for the kind chosen at the time, and the figure and its path went
       with the drawings in G2.) */
    static const std::vector<std::vector<std::string>> reads {
      { "c:lfoSync0", "s:lfoRate0" }, { "c:lfoSync1", "s:lfoRate1" }, { "c:delaySync", "s:delayMs" },
      { "c:arpMode", "c:arpRate", "c:arpOctaves" },
      // The view's: the pair's two menus keep it off one lane twice, mid and side and the lag turn each other off,
      // and a display of X-Y reads the persistence.
      { "c:xyX", "c:xyY" }, { "c:midSide", "c:lagOn" }, { "k:disp", "c:persistence" },
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
      /* Nor across a press that chose a hand or a link (G6): a slider moved
         before it was another hand's, or both hands', and the one after it
         does not say what that one did. */
      if (hands_[i].key.rfind("k:hand#", 0) == 0) break;
      if (hands_[i].key == key) { hands_.erase(hands_.begin() + static_cast<std::ptrdiff_t>(i)); break; }
    }
    hands_.push_back({ std::move(key), std::move(hand) });
  }

  /* Scan's frame (P7a), the page's scanStep: after the picture's step, so
     the hold is this frame's, and from the grid the last frame's draw left -
     each layer's own while the layers draw a picture each, the one screen
     otherwise. A layer at no depth forgets its path; one at any depth sends
     its hold when it has moved by more than the page's 0.005, and a new
     table unless the setup is still landing or the path reads darkness.
     Here, unlike the page, the frame is a sixtieth of a second of audio, so
     what a tick plays does not depend on a screen (scan.h). */
  void scanFrame() {
    scan_->frame(*core_, brain_->view.screen.display == "spect", keyboard_->layersOn() ? 2 : 1, scanIn(),
                 pictureRun_->elapsed(), brain_->scanSoft, nowMs_);
  }

  /* What Scan is handed, a frame's reading and a strike alike: each layer's
     depth and what it reads (P7b), and the two pictures - each layer's own
     grid and hold while the layers draw a picture each, the one screen and
     the shared stage's hold otherwise. */
  ScanInput<float> scanIn() const {
    const PictureRun& run = *pictureRun_;
    const LayerPictures& layers = run.layers();
    return scanInput<float>(layers.live(), { core_->tone().scan, core_->toneB().scan }, brain_->scanReads,
                            run.stage().hold(), { layers.stage(0).hold(), layers.stage(1).hold() },
                            run.phosphor().grid().data(), { layers.layerGrid(0).grid().data(), layers.layerGrid(1).grid().data() },
                            run.phosphor().grid().size());
  }

  /* Notes strike the screen (P7b), the page's scanStrike: the keyboard's
     note-on hands the note, its velocity as a fraction and its layers, and
     the light is laid at once into the grids the next frame fades and reads
     - each layer's own picture while they draw one each, and the shown
     screen - through the last frame's graticule, as the page lays it
     through `plot`. Notes the arpeggiator and the score play do not strike,
     as on the page: they reach the generator without passing noteOn. */
  void scanStrike(int note, double velocity, int layers) {
    if (!pictureRun_ || !scan_) return;
    PictureRun& run = *pictureRun_;
    const Plot plot = run.plot();
    // Each hand at its own Strike (G6).
    scan_->strike(note, velocity, layers, brain_->scanStrike, brain_->view.screen.display == "spect", scanIn(), plot,
                  [&](int picture, double x0, double y0, double x1, double y1, double level) {
                    Phosphor* grid = picture < 0 ? &run.phosphor() : run.layers().grid(static_cast<std::size_t>(picture));
                    if (grid) grid->segment(plot, x0, y0, x1, y1, level);
                  }, brain_->scanStrikeB);
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
  /* The picture's newest frame made known, with the oscillators as they
     stand at it: the oscillators first, so a reader that sees the frame sees
     them too. Each value is whole; the six together may be a block apart,
     which on the page is a frame's worth of nothing. */
  void publish(std::size_t ring) {
    for (std::size_t i = 0; i < 2 && i < lfos_.size(); ++i) {
      lfosServed_[i * 3].store(lfos_[i].phase, std::memory_order_relaxed);
      lfosServed_[i * 3 + 1].store(lfos_[i].held, std::memory_order_relaxed);
      lfosServed_[i * 3 + 2].store(lfos_[i].value, std::memory_order_relaxed);
    }
    envServed_[0].store(core_->envelope(), std::memory_order_relaxed);
    envServed_[1].store(core_->gated() ? 1.0 : 0.0, std::memory_order_relaxed);
    envServed_[2].store(static_cast<double>(core_->envelopeStage()), std::memory_order_relaxed);
    envServed_[3].store(core_->envelopeVelocity(), std::memory_order_relaxed);
    pictureAt_.store(ring, std::memory_order_release);
  }
  void render(float* left, float* right, int from, int to) {
    // In pieces no longer than the buffers made for them: a host may hand
    // over a bigger block than it said it would.
    const int most = static_cast<int>(pictureL_.size());
    for (int at = from; at < to; at += most) {
      const int n = std::min(most, to - at);
      float* heardR = right ? right + at : spare_.data();
      const float* inL = input_ ? input_->left + at : nullptr;
      const float* inR = input_ ? (input_->right ? input_->right + at : inL) : nullptr;
      if (bands_) {
        /* The band split: the input split into four lanes, each one signal,
           and what is heard the bands summed at the page's mixer's gains.
           The generator runs all the same, since it steps the oscillators
           every modulation reads; nothing of it is heard. */
        // Its heard pair is not asked for: what is heard here is the bands', at the Output below.
        core_->block(pictureL_.data(), pictureR_.data(), n);
        std::size_t ring = pictureAt_.load(std::memory_order_relaxed);
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
        publish(ring);
        core_->hear(left + at, heardR, n);  // the Output, on what is heard and never on the bands drawn
        continue;
      }
      if (drawsInput_) {
        if (!inL) { std::fill(spare_.begin(), spare_.begin() + n, 0.0f); inL = inR = spare_.data(); }
        core_->effect(inL, inR, pictureL_.data(), pictureR_.data(), n);
        std::copy(pictureL_.begin(), pictureL_.begin() + n, left + at);
        std::copy(pictureR_.begin(), pictureR_.begin() + n, heardR);
        // The Output (G7), on the copy that is heard: the picture is what came out of the plane.
        core_->hear(left + at, heardR, n);
      } else {
        if (inL) {
          for (int k = 0; k < n; ++k) mono_[static_cast<std::size_t>(k)] = input_->right ? (inL[k] + inR[k]) * 0.5f : inL[k];
          core_->setInput(mono_.data(), n);
        }
        core_->block(pictureL_.data(), pictureR_.data(), n, left + at, heardR, pictureBL_.data(), pictureBR_.data());
        core_->setInput(nullptr, 0);
      }
      /* The figures the generator lays out, as the page's tone source lays
         them out (getLatestWindow): layer A's pair alone; A's and B's as two
         pairs ("each"), four lanes; or one pair with B's added, clamped
         ("against") - where the generator has already put A on X and B on
         Y, and B's own pair is silent, so the sum is the page's and changes
         nothing. The keyboard works the layout out, as the page's
         syncLayers does. Until 5m the pair was A's whatever the layout, so
         in the plugin and on the site layer B (and the second generator,
         until G2) were heard and never drawn. */
      const Layout lay = drawsInput_ ? Layout::One : notes_->layout();
      pictureSource_.channels = lay == Layout::Each ? 4 : 2;
      layOutPicture(lay);
      std::size_t ring = pictureAt_.load(std::memory_order_relaxed);
      for (int k = 0; k < n; ++k) {
        float* row = &picture_[ring * kRingLanes];
        const std::size_t i = static_cast<std::size_t>(k);
        if (lay == Layout::Against) {
          row[0] = std::fmax(-1.0f, std::fmin(1.0f, pictureL_[i] + pictureBL_[i]));
          row[1] = std::fmax(-1.0f, std::fmin(1.0f, pictureR_[i] + pictureBR_[i]));
        } else {
          row[0] = pictureL_[i];
          row[1] = pictureR_[i];
        }
        row[2] = lay == Layout::Each ? pictureBL_[i] : 0.0f;
        row[3] = lay == Layout::Each ? pictureBR_[i] : 0.0f;
        // Lanes past these, nought: nothing stale to read in rows the band split last wrote.
        for (int c = 4; c < kRingLanes; ++c) row[c] = 0.0f;
        ring = (ring + 1) % kPictureFrames;
      }
      publish(ring);
    }
  }

  /* The last of the picture, the page's screen, for the hearing to read: its
     left channel, and its right for the width. The band split's, as the page
     reads lanes: the trigger's lane, and for the width the X-Y pair's other
     lane. */
  void window(std::vector<float>& left, std::vector<float>* right) const {
    const int a = bands_ ? std::clamp(static_cast<int>(brain_->view.trigSource), 0, kBandCount - 1) : 0;
    const int b = bands_ ? std::clamp(static_cast<int>(brain_->view.xy[1]), 0, kBandCount - 1) : 1;
    latestLane(a, left.data(), left.size());
    if (right) latestLane(b, right->data(), right->size());
  }

  double rate_ = 48000;
  std::vector<float> hearL_, hearR_;
  std::unique_ptr<HearingSources> hearing_;  // what it hears of itself, as sources
  std::unique_ptr<PictureRun> pictureRun_;
  // Scan's paths and tables (P7a): the generator reads the tables, which are made in prepare.
  std::unique_ptr<ScanReader> scan_;
  CaptureSource pictureSource_;
  std::size_t captureMost_ = 0;  // the most a capture asks of the ring, which its lanes are made room for

  std::vector<Lfo> lfos_;
  std::unique_ptr<Generator> core_;
  std::unique_ptr<GeneratorNotes> notes_;
  std::unique_ptr<Keyboard> keyboard_;
  std::unique_ptr<Matrix> matrix_;
  std::unique_ptr<CoreSources> sources_;
  std::unique_ptr<Brain> brain_;  // what a setup sets beyond the generator
  std::unique_ptr<ClockIn> clockIn_;  // MIDI's real-time bytes, to the brain's clock
  std::unique_ptr<BrainSources> brainSources_;  // the morph's fader as a destination
  std::unique_ptr<MidiOut> midiOut_;  // to the owner, through `hooks.midiOut`
  Strike strike_;  // the score's notes, struck in the generator's score voice
  int outAt_ = 0;  // the sample in the block that what the out sends now is sent at
  int stepPos_ = 0;          // frames into the current 128-frame step
  double stepStartMs_ = 0;   // where the current step began, in the matrix's time
  std::array<Ramp, 16> ramps_ {};  // host parameters walking across a block's steps
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
  int hostLoads_ = 0;
  std::vector<std::string> hostMoved_;  // the sliders the host has moved since the last load
  bool changed_ = false;
  double nowMs_ = 0, lastBlockMs_ = 0;  // the matrix's clock: audio time, not the wall's
  std::vector<float> pictureL_, pictureR_, spare_, mono_;  // a block's worth, made in prepare
  std::vector<float> pictureBL_, pictureBR_;  // layer B's pair, as the generator draws it
  const Input* input_ = nullptr;  // this block's, while it is rendered
  bool drawsInput_ = false;       // drawing the input rather than the generator
  bool bands_ = false;            // the input split into four bands, drawn as lanes
  // The alignment's delay lines, a frame of every lane at a time, and how far back each lane is read.
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
  std::array<std::atomic<double>, 6> lfosServed_ {};
  std::array<std::atomic<double>, 4> envServed_ {};
};

}  // namespace scope
