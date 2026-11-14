#pragma once

#include <array>
#include <atomic>
#include <cstddef>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include <juce_audio_processors/juce_audio_processors.h>

#include "scope/instrument.h"
#include "scope/presets.h"

// The processor is the instrument (scope::Instrument) behind JUCE: the core's
// generator, and over it the brain - the keyboard, the matrix and its
// sources, the clock, the score, the hearing, the picture the photocell
// reads - which the site's worklet runs too, compiled, so the two are one
// instrument. What is the processor's own is what only a host has: the
// host's MIDI, handed to the instrument byte for byte at its sample, and its
// MIDI out, which gets what the page would send to a port - the arpeggio's
// steps and the score's notes - each at the
// sample of what sent it; the host's transport; eight parameters, each one
// of the panel's sliders; the page's commands, queued under a lock for the
// top of the next block; and the state, saved as a setup code - the setup it
// was loaded with, the hands on it since, and the controllers it has learned.
class ScopeProcessor final : public juce::AudioProcessor, private juce::Timer {
 public:
  ScopeProcessor();
  ~ScopeProcessor() override { stopTimer(); }

  void prepareToPlay(double sampleRate, int samplesPerBlock) override;
  void releaseResources() override {}
  bool isBusesLayoutSupported(const BusesLayout& layouts) const override;
  void processBlock(juce::AudioBuffer<float>&, juce::MidiBuffer&) override;
  using AudioProcessor::processBlock;

  juce::AudioProcessorEditor* createEditor() override;
  bool hasEditor() const override { return true; }

  const juce::String getName() const override { return JucePlugin_Name; }
  bool acceptsMidi() const override { return true; }
  bool producesMidi() const override { return true; }
  bool isMidiEffect() const override { return false; }
  /* How long it goes on after the last note: the longer release of the two
     layers, and the echo's repeats until they are 60 dB down. It was half a
     second whatever the echo did, so a host that stops processing a silent
     track cut the echoes off. Worked out on the audio thread as the setup
     changes (`tailFor`) and read from wherever the host asks. A known limit:
     layer B's own echo, and a loop that keeps itself going under Scan, are
     not counted; the second has no end to report. */
  double getTailLengthSeconds() const override { return tail_.load(); }

  /* The latency told to the host (12 Nov): how late the oversampled stages
     put the sound - the voice's shaper and the plane's non-linear stage, 31
     samples each, so nought, 31 or 62 (Generator::stageDelay) - read once a
     setup has loaded and never again until the next. A load is the plugin
     prepared, a project's state or a program handed over, or the page's
     preset, code or undo step; a slider is not, so the Picture amount moved
     across nought, which switches both stages in or out under a held note,
     leaves the host's figure where the load put it, up to 62 samples out
     until the next load. That is the choice: a host told of every switch
     would be told mid-phrase, and most redo their delay compensation with a
     gap in the sound (plugin/PLAN.md says what the rest would cost).

     Measured on the audio thread a tenth of a second after the load, when the
     stages' routes have been made, into `latencyWanted_`; told to JUCE on
     the message thread by `reportLatency`, which a timer calls, since
     setLatencySamples tells the host's wrapper under a lock. */
  void reportLatency();
  int latencyMeasured() const { return latencyWanted_.load(); }
  // How late the stages put the sound this block, whatever the host was told: the shell test's way in.
  int stageDelayNow() const { return instrument_.stageDelay(); }
  // The limiter's lookahead (5a), which the host is told on top of the stages'.
  int limiterLatency() const { return instrument_.latency(); }
  static double tailFor(const scope::Tone& a, const scope::LayerSettings& b);

  /* The bank as the host's programs (6 Nov): the plain sine the plugin opens
     on, then the bank in the browser's order. A program chosen is a state
     handed over, as a project's is. The one already chosen chosen again is
     nothing: some hosts set the current program straight after restoring a
     project, which would otherwise put the project back to the plain sine.

     The number is where in the bank the sound came from (G8): chosen from
     the host's list, or a bank sound or the plain sine loaded on the page
     (`pageSetup`, which the page tells which), and nothing else moves it. An
     edit keeps it, as a synthesiser's display keeps the program it edits:
     the host has no way to say "edited", and the number is also what a host
     sends back as a project opens, which must find the same number and leave
     the edits alone. A code pasted, a saved sound or an undo to one keeps it
     too - the host's list has no "none", and the plain sine's number would
     claim a sound that is not playing. The page's header is the place that
     says Custom. Kept with the project as `pluginProgram`, beside the setup
     and never in it, as `pluginOutput` is: a project reopens showing the
     program it was saved at, with no preset loaded over what it saved. */
  int getNumPrograms() override { return 1 + static_cast<int>(scope::presets().size()); }
  int getCurrentProgram() override { return program_.load(); }
  void setCurrentProgram(int index) override;
  const juce::String getProgramName(int index) override;
  void changeProgramName(int, const juce::String&) override {}

  /* The face's window: the size it was last left at, kept with the project
     ("pluginWindow" in the state, which the instrument never sees). */
  static constexpr int kWindowW = 1200, kWindowH = 680;  // inside a 1366x768 laptop with a host's frame
  void setWindowSize(int w, int h) { windowW_.store(w); windowH_.store(h); }
  std::pair<int, int> windowSize() const { return { windowW_.load(), windowH_.load() }; }

  /* The plugin's state is a setup code, the thing the page shares: the
     setup it was loaded with, and over it what has moved since - every
     slider moved, by the host's parameters or the page, every menu, switch
     and button the page has sent and its routings, and the controllers
     learned. */
  void getStateInformation(juce::MemoryBlock&) override;
  void setStateInformation(const void*, int) override;

  /* The last `kPictureFrames` of what was played, left and right interleaved,
     for the page to draw: written by the audio thread, read by the editor's
     resource provider. */
  static constexpr std::size_t kPictureFrames = scope::Instrument::kPictureFrames;
  std::vector<float> pictureSnapshot() const { return instrument_.pictureSnapshot(); }
  std::vector<float> pictureServed() const { return instrument_.pictureServed(); }
  // The oscillators as they stood at the picture's newest frame: phase, held and value, each of two.
  std::array<double, 6> lfosServed() const { return instrument_.lfosServed(); }
  // And the envelope at the same frame - level, gate, stage, velocity - for the Envelope card's dot.
  std::array<double, 4> envelopeServed() const { return instrument_.envelopeServed(); }
  // And (5b) the clock, the limiter and what the face shows of the picture, as the site's page reads them.
  std::array<double, scope::Instrument::kClockServed> clockServed() const { return instrument_.clockServed(); }
  std::array<double, scope::Instrument::kFaceServed> faceServed() const { return instrument_.faceServed(); }
  bool bands() const { return instrument_.bands(); }
  int lanes() const { return instrument_.lanes(); }
  double bandGain(int lane) const { return instrument_.bandGain(lane); }
  double sampleRateNow() const { return rate_.load(); }

  /* What the page last said about how the picture is getting through: frames
     a second and how long its fetches take. Kept for whoever asks, and
     printed when SCOPE_REPORT is set - which is how the spike measures the
     path. Written from the message thread, read from it too. */
  void setPictureReport(const juce::String& json) { pictureReport_ = json; }
  juce::String pictureReport() const { return pictureReport_; }

  // What the shell test reads, from the instrument.
  const scope::Tone& tone() const { return instrument_.tone(); }
  const scope::LayerSettings& toneB() const { return instrument_.toneB(); }
  scope::Keyboard::Settings keys() const { return instrument_.keyboard().settings(); }
  // The routings, for the shell test to set. Not to be touched while the audio thread runs.
  scope::Matrix& matrix() { return instrument_.matrix(); }
  const scope::Hearing& hearing() const { return instrument_.hearing(); }
  const scope::Clock& clock() const { return instrument_.clock(); }
  const scope::ScoreState& score() const { return instrument_.score(); }
  const scope::PictureRun& picture() const { return instrument_.picture(); }
  // The generator, for where its level and cutoff have glided to (levelNow, cutNow).
  const scope::Generator& generator() const { return instrument_.generator(); }
  const scope::Brain::ViewState& view() const { return instrument_.view(); }
  double lfoRate(int i) const { return instrument_.lfoRate(i); }
  bool drawsInput() const { return instrument_.drawsInput(); }
  int pictureLanes() const { return instrument_.pictureLanes(); }
  // A hand on one of the panel's sliders, not remembered, and an end of the morph stored: the shell test's way in.
  void moveSlider(const std::string& id, double value) { instrument_.moveSlider(id, value); }
  void storeMorph(bool endB) { instrument_.storeMorph(endB); }

  /* The host's parameters (P8a): the loop's own controls in the main bank,
     then the morph's fader in a group of its own. Each is one of the panel's
     sliders by id and in its units, so a host moving one is a hand on that
     slider, and a hand on the slider moves the parameter.

     The main bank is the Picture section along the bottom of the face -
     the amount, Scan, strike, softness, persistence and, since G7, the
     master Output in the corner the level had - then the level, now the
     Generator's, the cutoff, the warp, the twist, the delay's and the
     phaser's mix (F7c).
     The phaser's amount takes the eighth place when the phaser is built,
     inserted before the morph. The macros were four of the first eight and
     are not parameters any more: nobody had saved a project, so nothing was
     mapped across (plugin/PLAN.md, P8a).

     Hosts that bind automation by id (VST3 and AU here, JUCE's default ids)
     keep the morph's automation when the phaser is inserted; what moves is
     its index, so a controller mapped by position would find it one along.
     Reserving the place now with an inert parameter was the alternative,
     and was turned down: a knob in a host's list that does nothing is worse
     than an index that moves once, before anyone has saved anything.

     `version` is the plugin version a parameter arrived in, which AU hosts
     use to order and JUCE asks for: the level, cutoff, echo and morph were
     the first plugin's, the four loop controls this one's. A layer's
     controls - Scan's depth, the bend, the cutoff, the level, and since G6
     the Picture amount and Strike, which each hand has its own of - address
     what the slider does for a hand: both hands while the section is linked,
     the hand the panel shows while it is that hand's own (`readBack` when
     the panel turns to the other hand). */
  struct HostKnob { const char* id; const char* name; const char* slider; int version; bool main; };
  static constexpr std::array<HostKnob, 15> kKnobs { {
    // F7c of web/docs/redesigning-the-face.md: the Picture section along the
    // bottom of the face, then the sound controls people automate. Strike,
    // softness and twist arrived in version 3; the rest kept their ids, so
    // automation already written follows them to their new places.
    { "picture", "Picture", "pictureAmount", 2, true }, { "scan", "Scan", "oscScan", 2, true },
    { "strike", "Strike", "scanStrike", 3, true }, { "softness", "Softness", "scanSoft", 3, true },
    { "persistence", "Persistence", "scanMemory", 2, true },
    /* G7: the master Output, new in version 5, in the corner the level
       had; the level keeps its id and its meaning, the generator's, and
       moves one along with everything after it. The Output is both hands'
       and has no layer to read back. Not a hand on the setup: the plugin's
       state keeps it as `pluginOutput`, beside the setup. */
    { "output", "Output", "output", 5, true },
    /* The master Width (12 Nov), new in version 6, after the Output and for
       its reasons: both hands', what is heard alone, kept as `pluginWidth`
       beside the setup. Everything after it moves one along again, which
       hosts that bind by id do not see. */
    { "width", "Width", "stereoWidth", 6, true },
    { "level", "Level", "amp", 1, true },
    { "cutoff", "Cutoff", "vcfCut", 1, true }, { "bend", "Warp", "oscBend", 2, true },
    { "twist", "Twist", "planeTwist", 3, true },
    // Shown as Delay mix since F5, the rack's name for the effect and its
    // amount; the id stays echo, so automation already written follows it.
    { "echo", "Delay mix", "delayMix", 1, true },
    // P8e: the phaser's amount, and the morph last in a group of its own.
    { "phaser", "Phaser mix", "phaserMix", 2, true },
    // P9, the reverb's amount (9 Nov), new in version 4; the morph still last.
    { "reverb", "Reverb mix", "reverbMix", 4, true },
    { "morph", "Morph", "morphPos", 1, false },
  } };
  juce::AudioParameterFloat* knob(std::size_t i) const { return knobs_[i]; }
  // By the parameter's id, which outlives its index: the shell test's way to a knob.
  juce::AudioParameterFloat* knob(std::string_view id) const {
    for (std::size_t i = 0; i < kKnobs.size(); ++i)
      if (id == kKnobs[i].id) return knobs_[i];
    return nullptr;
  }

  /* The page as the plugin's face (stage 3), through the editor's native
     functions, on the message thread. A slider moved on the page is a hand
     on that slider here; a setup loaded on the page - a preset, a code - is
     loaded here as it was there. Both wait in a queue for the top of the
     next block, where the audio thread does what it does with everything
     else. And the state for the page to show: the setup code the plugin
     would save, with how many changes in it came from the host rather than
     the page, so the page applies only those and never echoes its own. */
  void pageSlider(const std::string& id, const std::u16string& text);
  /* A change gesture on one of the host's parameters, by its slider's id,
     begun as the player takes hold of the control on the page and ended as
     they let go (second review, 1.2): what a host's touch and latch
     automation record by. The page says when; here a gesture is never
     begun twice nor ended unbegun, whatever the page sends, and the editor
     ends any left open as it goes. Message thread only, as JUCE's VST3
     wrapper takes a gesture from nowhere else - and so is the value a page's
     move gives its parameter (pageSlider), so that the host sees the begin,
     the values and the end in the order they were made. */
  void pageGesture(const std::string& id, bool begin);
  void endGestures();
  /* `chosen` is the page's preset menu as the setup lands: "b:" and a bank
     sound's name, "n:" and the plain sine's, "s:" a saved sound's, or
     nothing for a code or an edit put back. Only the first two move the
     program's number. */
  bool pageSetup(std::string_view code, std::string_view chosen = {});
  // The program a page's preset menu names: the bank's index, or -1 for anything not in the bank.
  static int programOf(std::string_view chosen);
  /* And a menu, a switch or a text box changed (its value as the browser
     holds it, or a switch's state as true or false), a button pressed, and
     the routings as an edit there left them, every depth to the last digit.
     Each is the
     page's handler, ported (scope::controlChange, controlClick and
     Matrix::setRoutings). */
  void pageControl(const std::string& id, scope::Json value);
  void pageClick(const std::string& id);
  void pageRoutings(std::string_view text);
  // And the fade, which the page keeps in its own storage, sent whole as JSON when it is saved.
  void pageFade(std::string_view json);
  // The state for the page: its host count, how many of those were loads, the
  // sliders the host has moved since the last, and the code (hostPull on the page).
  struct PageState { int version = 0; int loads = 0; std::string moved; std::string code; };
  PageState pageState() const;
  double slider(const char* id) const { return instrument_.slider(id); }

 private:
  // A command from the page, waiting for the next block; or refused, and false.
  bool queue(std::optional<scope::Instrument::Command> command);
  // The page's queue, applied; and the state, published for the page if it changed.
  void takePage();
  void publish(bool wait);

  scope::Instrument instrument_;
  juce::MidiBuffer outgoing_;  // what the out sent this block, handed over at its end
  std::array<juce::AudioParameterFloat*, kKnobs.size()> knobs_ {};
  std::array<float, kKnobs.size()> applied_ {};  // each parameter as last applied
  /* Each parameter as the page last set it, from the message thread
     (pageSlider): what the audio thread finds there is the page's own move
     on its way through the queue, not the host's, and is not sent back to
     the page as automation. NaN until the page has set one. */
  std::array<std::atomic<float>, kKnobs.size()> pageSet_;
  std::array<bool, kKnobs.size()> gesture_ {};  // a change gesture open on each, message thread only
  int panelLayer_ = 0;                          // the layer the panel showed at the last block
  // The parameters not moved by the host, read back from their sliders: a setup loaded, or the panel's layer changed.
  void readBack(bool unmovedOnly);
  std::vector<scope::Instrument::HostSlider> moved_;  // the parameters moved since the last block
  std::vector<scope::Instrument::Event> events_;      // the host's MIDI this block, with room made in prepare
  std::vector<float> inL_, inR_;                      // the host's input this block, copied out of the buffer
  juce::SpinLock stateLock_;                   // guards the hand-over of pending_ only, never the instrument
  std::optional<scope::Json> pending_;         // waiting for the next block, or for prepareToPlay
  juce::SpinLock queueLock_;
  std::vector<scope::Instrument::Command> queue_, taken_;
  mutable juce::SpinLock publishLock_;
  PageState published_;
  std::atomic<double> rate_ { 48000.0 };
  std::atomic<double> tail_ { 0.5 };
  void timerCallback() override { reportLatency(); }
  // A tenth of a second at 48 kHz, whatever the host's block: the matrix has stepped many times by then.
  static constexpr int kLatencyAfter = 4800;
  // Samples until the latency is read after a load, or -1 for none owed; and what it read, -1 before the first.
  int latencyIn_ = -1;
  std::atomic<int> latencyWanted_ { -1 };
  std::atomic<int> program_ { 0 };
  std::atomic<int> windowW_ { kWindowW }, windowH_ { kWindowH };
  juce::String pictureReport_;

  JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(ScopeProcessor)
};
