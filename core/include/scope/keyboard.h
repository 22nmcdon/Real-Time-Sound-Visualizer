// The keyboard, ported from the `midi` functions in web/scope.html: the held
// stack and its three rules (velocity nought is a release, a note does not
// stack twice, a panic empties it), the sustain pedal, learned controllers,
// the bytes a port sends, and what the stack tells the generator - the dyad's
// interval, a mono line, the chord on one layer or two with each layer's draw
// rule, the gate, and how the figures are laid out. And the keyboard's own
// sources: the key, the pedal, and what the hands are doing.
//
// It is held to the page's own functions by core/tests/parity.py, which drives
// both through the same notes and compares every call each makes of the
// generator, and the sources and the stack after each.
//
// What differs from the page, and why, so nobody goes looking:
//
// - The page reads and writes the panel's sliders (`el.freq`, `el.interval`,
//   `el.figureRate`, `el.detail`): a note moves the frequency slider and the
//   interval menu with it, and handing the controls back reads them. Here they
//   are `Panel`, which the brain will own when the setup is in the core.
// - The page asks `keyboardPresent()` - a port or the screen's keys - and
//   whether the source can lay out two figures. In the plugin the host is
//   always a keyboard and the generator is always on its own, so the first is
//   a flag (`setPresent`) and the second is always yes. On the site the page
//   still knows the answer to the first and says it, through the
//   instrument's `keyboardPresent` control.
// - The page's `genInput.from` is the generator's `inputFrom`; here it is read
//   from the tone, where the two are always the same.
// - The arpeggiator's first step waits 25 ms for the rest of the chord, on a
//   timer in the page. The core has no timers: the keyboard keeps its wakes
//   (`arpWake`), and its owner calls `wakeArp` at each one's time - the
//   plugin at its own sample, the page a frame or so late. "Now", where the
//   page asks `performance.now()`, is what the owner last said (`setNow`),
//   and the tempo the steps count in is the clock's (`setTempo`).
// - The arpeggiator's random walk draws from the core's own generator, seeded,
//   where the page asks `Math.random`; the parity seeds the page's alike.
// - The stack is reserved for every note there is, so a note never makes it
//   grow. The chord handed to the generator is a list, and the generator
//   copies it; that copy can allocate on a note, once per layer.

#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <functional>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include "scope/generator.h"
#include "scope/json.h"

namespace scope {

inline double midiHz(double note) { return 440 * std::pow(2.0, (note - 69) / 12); }

constexpr int kPolyVoices = 8;     // POLY_VOICES: held notes sounding at once, per layer
constexpr double kMidiRoot = 220;  // A3, the pitch a trace rate is measured against
constexpr double kCcSmooth = 0.03; // seconds, one pole over a controller's steps

// NORD_CC: a name for a controller the Electro 6D's panel has, and nothing more.
inline const char* nordCc(int number) {
  switch (number) {
    case 7: return "Volume"; case 11: return "Swell pedal"; case 13: return "Organ level";
    case 34: return "Piano level"; case 43: return "Sample level"; case 64: return "Sustain";
    case 16: return "Drawbar 1"; case 17: return "Drawbar 2"; case 18: return "Drawbar 3";
    case 19: return "Drawbar 4"; case 20: return "Drawbar 5"; case 21: return "Drawbar 6";
    case 22: return "Drawbar 7"; case 23: return "Drawbar 8"; case 24: return "Drawbar 9";
    case 86: return "Effect 1 rate"; case 90: return "Effect 2 rate"; case 93: return "Delay amount";
    case 108: return "Rotary speed"; case 113: return "Reverb amount";
    default: return nullptr;
  }
}

// One pair of figures, two, or layer A against layer B as one.
enum class Layout { One, Each, Against };
inline const char* layoutName(Layout l) { return l == Layout::Each ? "each" : l == Layout::Against ? "against" : "one"; }

// What the keyboard plays: the calls the page's `genSet`, `genReswing` and the
// tone source's gate make, and the few settings the keyboard reads back.
class NoteTarget {
 public:
  virtual ~NoteTarget() = default;
  virtual const Tone& tone() const = 0;
  virtual bool hasVoices(int layer) const = 0;
  virtual void set(std::string_view field, double value) = 0;  // layer A's
  virtual void setVoices(const std::vector<NoteWant>* list, int layer) = 0;
  virtual void reswing() = 0;
  virtual void gate(bool open, double velocity) = 0;
  virtual void setGated(bool on) = 0;
  virtual bool gated() const = 0;
  virtual Layout layout() const = 0;
  virtual void setLayout(Layout next) = 0;
};

// The generator as the keyboard's target, which is all the plugin needs; the
// layout is the tone source's in the page, and is kept here beside it.
class GeneratorNotes : public NoteTarget {
 public:
  explicit GeneratorNotes(Generator& g) : g_(g) {}
  const Tone& tone() const override { return g_.tone(); }
  bool hasVoices(int layer) const override {
    return layer == 1 ? g_.toneB().voices.has_value() : g_.tone().voices.has_value();
  }
  void set(std::string_view field, double value) override { g_.set(field, value, 0); }
  void setVoices(const std::vector<NoteWant>* list, int layer) override { g_.setVoices(list, layer); }
  void reswing() override { g_.reswing(); }
  void gate(bool open, double velocity) override { g_.gate(open, velocity); }
  void setGated(bool on) override { g_.setGated(on); }
  bool gated() const override { return g_.gated(); }
  Layout layout() const override { return layout_; }
  void setLayout(Layout next) override { layout_ = next; }

 private:
  Generator& g_;
  Layout layout_ = Layout::One;
};

// Where notes go out: the MIDI out the score and the arpeggiator send on. A
// note sent says whether it went (no port, or past the rate limit, is no).
class NoteOut {
 public:
  virtual ~NoteOut() = default;
  virtual bool noteOut(int note, double velocity, double now) = 0;
  virtual void noteOutOff(int note) = 0;
};

// MIDI's real-time messages - clock, start, continue, stop - which belong to
// the clock rather than to the keyboard, and are handed on as they arrive.
class RealtimeIn {
 public:
  virtual ~RealtimeIn() = default;
  virtual void realtime(int status) = 0;
};

// The panel's controls the keyboard moves and reads: the page's sliders.
struct Panel {
  double freq = 220;
  int interval = 0;
  double figureRate = 40;
  double detail = 5;
};

struct Held { int note; double velocity; };

// A learned controller: its value walks towards its target, as the page's does.
struct Controller {
  int number = 0;
  std::string name;
  int raw = 0;
  double value = 0, target = 0;
};

enum class NoteMode { Dyad, Mono, Poly };
enum class DrawWhich { Outer, Lowest, Highest, Recent };
enum class LayerMode { Off, Split, Layer };

inline DrawWhich drawWhichNamed(std::string_view w) {
  return w == "lowest" ? DrawWhich::Lowest : w == "highest" ? DrawWhich::Highest
       : w == "recent" ? DrawWhich::Recent : DrawWhich::Outer;
}

// The count is a number, not an integer: a setup can give 2.35, the page
// keeps it, and its `slice` reads it as slice reads anything, by truncation.
struct DrawRule { double count = 2; DrawWhich which = DrawWhich::Outer; };

class Keyboard {
 public:
  explicit Keyboard(NoteTarget& target, RealtimeIn* realtime = nullptr) : t_(target), realtime_(realtime) {
    notes_.reserve(128);
    sustained_.reserve(128);
    cc_.reserve(128);
    for (auto& list : chord_) list.reserve(kPolyVoices);
    inner_.reserve(kPolyVoices);
  }

  // --- the stack ------------------------------------------------------------

  // midiNoteOn
  void noteOn(int note, double velocity) {
    if (velocity == 0) { noteOff(note); return; }
    // Struck again under the pedal: held by a finger now.
    forget(sustained_, note);
    // The split point is learned from a key, and the key still plays.
    if (layers_.learning) { layers_.point = note; layers_.learning = false; }
    const auto at = find(note);
    if (at != notes_.end()) notes_.erase(at);
    notes_.push_back({ note, velocity / 127 });
    // Counted for the layer it is in: split, a bass note restarts only the bass's fade.
    if (layersOn() && layers_.mode == LayerMode::Split) strikes_[note >= layers_.point ? 1 : 0]++;
    else { strikes_[0]++; strikes_[1]++; }
    applyNotes();
    // A key struck on a pitched harmonograph strikes the pendulums.
    const Tone& tone = t_.tone();
    if (tone.mode == Mode::Harmonograph && tone.pitched) t_.reswing();
  }

  // midiNoteOff. Under the pedal the key comes up and the note does not.
  void noteOff(int note) {
    const auto at = find(note);
    if (at == notes_.end()) return;
    if (sustain_) { remember(sustained_, note); return; }
    notes_.erase(at);
    applyNotes();
  }

  // midiSetPedal: half-way and past is down, as MIDI has it for a switch.
  void setPedal(double value) {
    pedalTarget_ = std::fmax(0.0, std::fmin(1.0, value));
    const bool down = pedalTarget_ >= 64.0 / 127;
    if (down != sustain_) {
      sustain_ = down;
      if (!down && !sustained_.empty()) {
        for (std::size_t i = notes_.size(); i-- > 0;) {
          if (holds(sustained_, notes_[i].note)) notes_.erase(notes_.begin() + static_cast<std::ptrdiff_t>(i));
        }
        sustained_.clear();
        applyNotes();
      }
    }
  }

  // midiPanic. What the pedal was holding goes; the pedal stays where it is.
  void panic() {
    sustained_.clear();
    if (notes_.empty()) return;
    notes_.clear();
    applyNotes();
  }

  // midiControl: 120 and 123 are panics, 64 is the pedal, the rest are learned.
  void control(int number, int raw) {
    if (number == 120 || number == 123) { panic(); return; }
    if (number == 64) { setPedal(raw / 127.0); return; }
    Controller& entry = learn(number);
    entry.raw = raw;
    entry.target = raw / 127.0;
  }

  // midiLearn: merged into what is known, never replacing it.
  Controller& learn(int number, std::string_view name = {}) {
    for (auto& c : cc_) {
      if (c.number == number) {
        if (!name.empty()) c.name = std::string(name);
        return c;
      }
    }
    Controller c;
    c.number = number;
    const char* known = nordCc(number);
    c.name = !name.empty() ? std::string(name) : known ? std::string(known) : "CC " + std::to_string(number);
    cc_.push_back(c);
    return cc_.back();
  }

  // midiBytes, with running status, and a real-time byte taken as a message of
  // its own wherever it lands - between a note and its velocity included.
  void bytes(const std::uint8_t* data, std::size_t length) {
    for (std::size_t i = 0; i < length;) {
      int status = data[i];
      if (status >= 0xf8) { tick(status); i++; continue; }
      if (status >= 0x80) {
        i++;
        running_ = status < 0xf0 ? status : 0;
      } else {
        status = running_;
        if (!status) { i++; continue; }
      }
      const int kind = status & 0xf0;
      if (kind < 0x80) { i += 1; continue; }
      const std::size_t need = kind == 0xc0 || kind == 0xd0 ? 1 : 2;
      int got[2] = { 0, 0 };
      std::size_t have = 0;
      while (have < need && i < length) {
        const int d = data[i];
        if (d >= 0xf8) { tick(d); i++; continue; }
        if (d >= 0x80) break;
        got[have++] = d; i++;
      }
      if (have < need) {
        if (i >= length) return;
        continue;
      }
      if (need == 1) continue;
      if (kind == 0x90) noteOn(got[0], got[1]);
      else if (kind == 0x80) noteOff(got[0]);
      else if (kind == 0xb0) control(got[0], got[1]);
    }
  }

  // --- once a frame ---------------------------------------------------------

  // midiSmooth then midiApplyGate, as the page's frame has them: the
  // controllers walk, and the gate and the chord are derived again.
  void frame(double elapsedMs) {
    smooth(elapsedMs);
    applyGate();
  }

  void smooth(double elapsedMs) {
    const double a = 1 - std::exp(-(std::fmax(0.0, elapsedMs) / 1000) / kCcSmooth);
    pedal_ += (pedalTarget_ - pedal_) * a;
    for (auto& c : cc_) c.value += (c.target - c.value) * a;
  }

  // --- the panel's handlers -------------------------------------------------

  void setMode(NoteMode m) { mode_ = m; applyNotes(); }
  void setDraw(int layer, double count, DrawWhich which) {
    DrawRule& d = draws_[layer == 1 ? 1 : 0];
    d.count = std::fmax(2, std::fmin(kPolyVoices, count == 0 || std::isnan(count) ? 2 : count));
    d.which = which;
    applyNotes();
  }
  void setPolyJust(bool on) { polyJust_ = on; applyNotes(); }
  void setLayers(LayerMode m) {
    layers_.mode = m;
    layers_.learning = false;
    syncLayers();
    applyNotes();
  }
  void learnSplit() { layers_.learning = !layers_.learning; }
  void setPair(bool against) { layers_.against = against; syncLayers(); applyNotes(); }
  void setHold(bool on) { hold_ = on; }
  // Whether notes drive the generator in the kind it is now.
  void setDrive(bool on) {
    drive_[kindOf(t_.tone().mode)] = on;
    if (on) applyNotes(); else undrive();
    syncPlay();
  }
  // Whether a note plays a drawing at its own pitch; the waveform has no say.
  void setPlay(bool on) {
    const std::size_t kind = kindOf(t_.tone().mode);
    if (kind == 0) return;
    play_[kind] = on;
    syncPlay();
    if (on) applyNotes(); else undrive();
  }
  void setPresent(bool on) { present_ = on; }
  Panel& panel() { return panel_; }

  // --- the arpeggiator: Stage K5 ---------------------------------------------

  void setNow(double ms) { now_ = ms; }
  void setTempo(double bpm) { bpm_ = bpm; }
  void setOut(NoteOut* out) { out_ = out; }

  // arpSet: the menus' values. Switched with keys down, the generator is given
  // what it should now have.
  void setArp(std::string mode, std::string rate, double octaves) {
    arp_.mode = std::move(mode);
    arp_.rate = std::move(rate);
    arp_.octaves = octaves == 0 || std::isnan(octaves) ? 1 : octaves;
    if (arp_.start) { offSent(); arp_.start.reset(); }
    arp_.index = -1;
    arp_.current.clear();
    applyNotes();
  }
  // The rate and octaves menus' own handlers: the field and nothing else,
  // where the mode's handler (arpSet) starts the arpeggio afresh.
  void setArpRate(std::string rate) { arp_.rate = std::move(rate); }
  void setArpOctaves(double octaves) { arp_.octaves = octaves == 0 || std::isnan(octaves) ? 1 : octaves; }
  bool arpActive() const { return arp_.mode != "off" && drives(); }
  // arpStepMs: the step in milliseconds at the tempo in force.
  double arpStepMs() const {
    static const std::pair<const char*, double> rates[] = {
      { "1/4", 1 }, { "1/8", 0.5 }, { "1/16", 0.25 }, { "1/8t", 1.0 / 3 }, { "1/16t", 1.0 / 6 },
    };
    double beats = 0.5;
    for (const auto& [id, b] : rates) if (arp_.rate == id) { beats = b; break; }
    return beats * 60000 / bpm_;
  }
  // arpTick: the step that is due, if one is; counted from the first key on
  // the clock, so the steps cannot drift.
  void arpTick(double now) {
    if (!arpActive() || !arp_.start) return;
    if (notes_.empty()) { arpStop(); return; }
    if (now < *arp_.start) return;
    const double due = std::floor((now - *arp_.start) / arpStepMs());
    if (due < arp_.steps) return;
    arp_.steps = due + 1;
    arpStep(now);
  }
  // The page's timer: when the first step is due, if one is waiting.
  std::optional<double> arpWake() const {
    if (wakes_.empty()) return std::nullopt;
    return *std::min_element(wakes_.begin(), wakes_.end());
  }
  void wakeArp() {
    const auto at = std::min_element(wakes_.begin(), wakes_.end());
    const double when = *at;
    wakes_.erase(at);
    arpTick(when);
  }
  struct ArpState {
    std::string mode = "off", rate = "1/8";
    double octaves = 1;
    std::vector<Held> current;
    int index = -1;
    std::optional<double> start;
    double steps = 0;
    bool stepping = false;
    std::vector<int> sent;
  };
  const ArpState& arp() const { return arp_; }

  // --- what a setup carries -------------------------------------------------

  // The keyboard's part of a setup, written as `restore` writes the page's
  // `midi` fields: all at once, the split's learning cancelled, and nothing
  // applied until `apply`.
  struct Settings {
    NoteMode mode = NoteMode::Dyad;
    std::array<DrawRule, 2> draws {};
    LayerMode layers = LayerMode::Off;
    int point = 60;
    bool against = false, polyJust = false, hold = false, truth = true, follow = false;
    std::array<bool, 4> drive { true, true, true, false };
    std::array<bool, 4> play { false, false, false, false };
  };
  Settings settings() const {
    return { mode_, draws_, layers_.mode, layers_.point, layers_.against, polyJust_, hold_, truth_, follow_, drive_, play_ };
  }
  void setSettings(const Settings& s) {
    mode_ = s.mode; draws_ = s.draws; layers_.mode = s.layers; layers_.point = s.point; layers_.against = s.against;
    layers_.learning = false; polyJust_ = s.polyJust; hold_ = s.hold; truth_ = s.truth; follow_ = s.follow;
    drive_ = s.drive; play_ = s.play;
  }
  // syncMidi's part that reaches the generator, then midiApplyNotes: what
  // `restore` ends the keyboard with, so what is under the hands outranks
  // what the setup asked for.
  void apply() {
    syncPlay();
    applyNotes();
  }
  // syncPlay alone, as the page's panel calls it when the kind changes.
  void syncPlayed() { syncPlay(); }

  // encodeCC: the learned controllers' names, "16:Drawbar 1;...".
  std::string encodeCC() const {
    std::string out;
    for (const auto& c : cc_) {
      std::string name = c.name;
      for (auto& ch : name) if (ch == ';' || ch == ':') ch = ' ';
      out += (out.empty() ? "" : ";") + std::to_string(c.number) + ":" + name;
    }
    return out;
  }
  // decodeCC: merged into what is learned, never swapped for it.
  void decodeCC(const std::u16string& text) {
    std::size_t at = 0;
    while (at <= text.size()) {
      const std::size_t end = std::min(text.find(u';', at), text.size());
      const std::u16string part = jsTrim(text.substr(at, end - at));
      std::size_t colon = 0;
      while (colon < part.size() && part[colon] >= u'0' && part[colon] <= u'9') colon++;
      // The page's /^(\d+):(.*)$/, whose dot stops at a line terminator.
      bool oneLine = true;
      for (const char16_t c : part) if (c == u'\n' || c == u'\r' || c == 0x2028 || c == 0x2029) oneLine = false;
      if (oneLine && colon > 0 && colon < part.size() && part[colon] == u':') {
        double number = 0;
        for (std::size_t i = 0; i < colon; i++) number = number * 10 + (part[i] - u'0');
        // A number past what an int holds names no controller anyone has.
        if (number < 2147483648.0) learn(static_cast<int>(number), utf16To8(jsTrim(part.substr(colon + 1))));
      }
      if (end >= text.size()) break;
      at = end + 1;
    }
  }

  // midiUndrive: the controls handed back, read from the panel.
  void undrive() {
    t_.set("detail", panel_.detail);
    t_.set("freq", panel_.freq);
    t_.set("figureRate", panel_.figureRate);
    t_.set("interval", panel_.interval);
    t_.set("octaves", 0);
  }

  // --- what it says ---------------------------------------------------------

  const std::vector<Held>& notes() const { return notes_; }
  const std::vector<int>& sustained() const { return sustained_; }
  const std::vector<Controller>& controllers() const { return cc_; }
  bool sustain() const { return sustain_; }
  int splitPoint() const { return layers_.point; }
  bool learning() const { return layers_.learning; }
  std::array<int, 2> strikes() const { return strikes_; }
  std::array<int, 2> interval() const { return { interval_.index, interval_.octaves }; }
  struct PolyCount { int sounding = 0, drawn = 0, held = 0; };
  PolyCount polyCount() const { return poly_; }

  // The keyboard's sources, as the page registers them.
  double key() const { return key_; }
  double pedal() const { return pedal_; }
  double notesCount() const { return std::fmin(1.0, static_cast<double>(notes_.size()) / kPolyVoices); }
  double notesSpread() const {
    if (notes_.size() < 2) return 0;
    const auto [lo, hi] = range();
    return std::fmin(1.0, (hi - lo) / 24.0);
  }
  double notesTop() const {
    if (notes_.empty()) return 0;
    return std::fmax(0.0, std::fmin(1.0, (range().second - 36) / 48.0));
  }
  // How hard the notes the picture is not drawing were played.
  double notesInner() const {
    double sum = 0;
    int n = 0;
    if (mode_ == NoteMode::Poly) {
      for (int layer = 0; layer < 2; layer++) {
        polyVoices(layer, inner_);
        for (const auto& v : inner_) if (v.role == "u") { sum += v.velocity; n++; }
      }
    } else {
      const std::size_t keep = mode_ == NoteMode::Mono ? 1 : 2;
      for (std::size_t i = 0; i + keep < notes_.size(); i++) { sum += notes_[i].velocity; n++; }
    }
    return n == 0 ? 0 : sum / n;
  }

  // layersOn: two layers, in poly on the waveform with the generator alone.
  bool layersOn() const { return layers_.mode != LayerMode::Off && polyWanted(); }
  /* Which layer the panel shows (editLayer): B only while there is one, so
     no control writes into a layer nobody hears. The A and B buttons choose,
     and whoever keeps the panel is told whenever the layers are worked out
     again, as the page's syncLayers shows the layer on the panel first. */
  int editLayer() const { return layersOn() && layers_.edit == 1 ? 1 : 0; }
  void setEdit(int layer) { layers_.edit = layer == 1 ? 1 : 0; if (onLayers_) onLayers_(); }
  void setLayerPanel(std::function<void()> f) { onLayers_ = std::move(f); }

 private:
  struct Interval { int index = 0, octaves = 0; };
  struct Layers { LayerMode mode = LayerMode::Off; int point = 60; bool against = false; bool learning = false; int edit = 0; };

  static std::size_t kindOf(Mode m) {
    return m == Mode::Harmonograph ? 1 : m == Mode::Figure ? 2 : m == Mode::Wireframe ? 3 : 0;
  }
  std::vector<Held>::iterator find(int note) {
    return std::find_if(notes_.begin(), notes_.end(), [note](const Held& h) { return h.note == note; });
  }
  static bool holds(const std::vector<int>& set, int note) { return std::find(set.begin(), set.end(), note) != set.end(); }
  static void remember(std::vector<int>& set, int note) { if (!holds(set, note)) set.push_back(note); }
  static void forget(std::vector<int>& set, int note) {
    const auto at = std::find(set.begin(), set.end(), note);
    if (at != set.end()) set.erase(at);
  }
  std::pair<int, int> range() const {
    int lo = notes_[0].note, hi = notes_[0].note;
    for (const auto& h : notes_) { lo = std::min(lo, h.note); hi = std::max(hi, h.note); }
    return { lo, hi };
  }
  void tick(int status) { if (realtime_) realtime_->realtime(status); }

  bool drives() const { return drive_[kindOf(t_.tone().mode)]; }  // midiDrivesGenerator

  // polyWanted: only the waveform plays chords.
  bool polyWanted() const {
    return mode_ == NoteMode::Poly && t_.tone().mode == Mode::Wave && drives() && present_;
  }

  // polyHz: equal by default; just is every note on a small ratio to the lowest.
  double polyHz(int note, int root) const {
    if (!polyJust_) return midiHz(note);
    const int semitones = note - root;
    return midiHz(root) * intervalRatio(semitones % 12, true) * std::pow(2.0, std::floor(semitones / 12.0));
  }

  // layerNotes then polyVoices: up to eight of the layer's notes, each with its role.
  void polyVoices(int layer, std::vector<NoteWant>& out) const {
    out.clear();
    const int which = layer == 1 ? 1 : 0;
    std::array<Held, kPolyVoices> sounding {};
    std::size_t count = 0;
    {
      const bool on = layersOn();
      std::array<Held, 128> mine {};
      std::size_t n = 0;
      if (!on) { if (which == 0) for (const auto& h : notes_) mine[n++] = h; }
      else if (layers_.mode == LayerMode::Layer) for (const auto& h : notes_) mine[n++] = h;
      else for (const auto& h : notes_) if ((h.note >= layers_.point) == (which == 1)) mine[n++] = h;
      const std::size_t from = n > kPolyVoices ? n - kPolyVoices : 0;
      for (std::size_t i = from; i < n; i++) sounding[count++] = mine[i];
    }
    if (count == 0) return;
    std::array<Held, kPolyVoices> byPitch = sounding;
    // Eight at the most, so an insertion sort; GCC's std::sort on an array this
    // short trips its own bounds warning. The notes are distinct, so any sort
    // gives the page's order.
    for (std::size_t i = 1; i < count; i++) {
      for (std::size_t j = i; j > 0 && byPitch[j - 1].note > byPitch[j].note; j--) std::swap(byPitch[j - 1], byPitch[j]);
    }
    const DrawRule& draw = draws_[static_cast<std::size_t>(which)];
    // n as the page has it, then as slice takes it: whole, by truncation.
    const double nRaw = std::fmin(std::fmax(2.0, draw.count), static_cast<double>(count));
    const std::size_t n = static_cast<std::size_t>(std::trunc(nRaw));
    const std::size_t outerTail = static_cast<std::size_t>(std::trunc(nRaw - 1));

    std::array<int, kPolyVoices> drawn {};
    std::size_t drawnCount = 0;
    if (draw.which == DrawWhich::Lowest) for (std::size_t i = 0; i < n; i++) drawn[drawnCount++] = byPitch[i].note;
    else if (draw.which == DrawWhich::Highest) for (std::size_t i = count - n; i < count; i++) drawn[drawnCount++] = byPitch[i].note;
    else if (draw.which == DrawWhich::Recent) for (std::size_t i = count - n; i < count; i++) drawn[drawnCount++] = sounding[i].note;
    else if (nRaw < 2) drawn[drawnCount++] = byPitch[0].note;
    else {
      drawn[drawnCount++] = byPitch[0].note;
      for (std::size_t i = count - outerTail; i < count; i++) drawn[drawnCount++] = byPitch[i].note;
    }
    const auto isDrawn = [&](int note) {
      for (std::size_t i = 0; i < drawnCount; i++) if (drawn[i] == note) return true;
      return false;
    };
    int bass = drawn[0];
    for (std::size_t i = 0; i < drawnCount; i++) bass = std::min(bass, drawn[i]);
    const int root = byPitch[0].note;
    const bool against = layersOn() && layers_.against;
    for (std::size_t i = 0; i < count; i++) {
      const Held& held = sounding[i];
      NoteWant v;
      v.note = held.note;
      v.velocity = held.velocity;
      v.freq = polyHz(held.note, root);
      v.role = !isDrawn(held.note) ? "u"
             : against ? (which == 1 ? "y" : "x")
             : count == 1 ? "xy"
             : held.note == bass ? "x" : "y";
      out.push_back(std::move(v));
    }
  }

  // midiApplyPoly. An empty list rather than none while the layers are on:
  // layer B exists and is silent, which is not the same as no layer B. With
  // the arpeggiator on, asked for by the chord's own bookkeeping, this is the
  // arpeggio's note rather than the whole of what is held.
  void applyPoly() {
    if (arpActive() && !arp_.stepping) { arpApply(); return; }
    polyVoices(0, chord_[0]);
    t_.setVoices(&chord_[0], 0);
    const bool on = layersOn();
    if (on) polyVoices(1, chord_[1]); else chord_[1].clear();
    if (on) t_.setVoices(&chord_[1], 1);
    int drawn = 0;
    for (const auto& list : chord_) for (const auto& v : list) if (v.role != "u") drawn++;
    poly_ = { static_cast<int>(chord_[0].size() + chord_[1].size()), drawn, static_cast<int>(notes_.size()) };
  }

  // syncPoly: whether there is a chord, asked every time rather than stored.
  void syncPoly() {
    const bool want = polyWanted();
    if (!want && t_.hasVoices(0)) t_.setVoices(nullptr, 0);
    else if (want && !t_.hasVoices(0)) applyPoly();
    syncLayers();
  }

  // syncLayers: the layers, derived as the chord is, and how they are drawn.
  void syncLayers() {
    if (onLayers_) onLayers_();
    const bool on = layersOn();
    if (on != t_.hasVoices(1)) {
      if (!on) t_.setVoices(nullptr, 1);
      if (polyWanted()) applyPoly();
    }
    const Layout want = !on ? (t_.tone().fromGen2 ? Layout::Each : Layout::One)
                      : layers_.against ? Layout::Against : Layout::Each;
    if (t_.layout() != want) t_.setLayout(want);
  }

  // midiApplyGate: only the waveform is gated, and only while notes drive it
  // and there is a keyboard to play them. Only the change opens it here.
  void applyGate() {
    syncPoly();
    const bool on = drives() && present_ && t_.tone().mode == Mode::Wave;
    const bool was = t_.gated();
    t_.setGated(on);
    if (on && !was && !notes_.empty()) t_.gate(true, notes_.back().velocity);
  }

  // midiGateNotes: the note events themselves, immediately.
  void gateNotes() {
    if (!t_.gated()) return;
    const bool held = !notes_.empty();
    t_.gate(held, held ? notes_.back().velocity : 0);
  }

  // midiApplyNotes: with the arpeggiator on, the stack stays the hands' and
  // the generator is shown the arpeggio instead.
  void applyNotes() {
    if (arpActive() && !arp_.stepping) {
      key_ = notes_.empty() ? 0 : notes_.back().velocity;
      arpHeld();
      return;
    }
    applyNotesTo();
  }

  // arpSequence: the notes the arpeggio walks, from what is held.
  void arpSequence(std::vector<Held>& seq) const {
    seq.clear();
    std::vector<Held>& base = arpBase_;
    base = notes_;
    if (arp_.mode != "played") {
      std::stable_sort(base.begin(), base.end(), [](const Held& a, const Held& b) { return a.note < b.note; });
    }
    for (int o = 0; o < arp_.octaves; o++) for (const auto& h : base) seq.push_back({ h.note + 12 * o, h.velocity });
    if (arp_.mode == "down") std::reverse(seq.begin(), seq.end());
    // Up and back without playing either end twice in a row.
    if (arp_.mode == "updown" && seq.size() > 2) {
      for (std::size_t i = seq.size() - 1; i-- > 1;) seq.push_back(seq[i]);
    }
  }
  // arpApply: the generator shown the step, struck - nothing, then the
  // step's notes - and the hands' stack put back.
  void arpApply() {
    arp_.stepping = true;
    std::swap(notes_, arpSaved_);
    notes_.clear();
    applyNotesTo();
    notes_ = arp_.current;
    applyNotesTo();
    std::swap(notes_, arpSaved_);
    arp_.stepping = false;
  }
  void offSent() {
    for (const int note : arp_.sent) if (out_) out_->noteOutOff(note);
    arp_.sent.clear();
  }
  void arpStep(double now) {
    arpSequence(arpSeq_);
    if (arpSeq_.empty()) return;
    const int len = static_cast<int>(arpSeq_.size());
    arp_.index = arp_.mode == "random" ? static_cast<int>(std::floor(random_.next() * len)) : (arp_.index + 1) % len;
    const Held pick = arpSeq_[static_cast<std::size_t>(arp_.index)];
    Held low = notes_[0];
    for (const auto& h : notes_) if (h.note < low.note) low = h;
    arp_.current.clear();
    if (mode_ == NoteMode::Dyad && pick.note != low.note) arp_.current.push_back(low);
    arp_.current.push_back(pick);
    arpApply();
    offSent();
    if (out_ && out_->noteOut(pick.note, pick.velocity, now)) arp_.sent.push_back(pick.note);
  }
  void arpStop() {
    arp_.start.reset();
    arp_.index = -1;
    arp_.current.clear();
    offSent();
    arpApply();
  }
  // arpHeld: the hands changed. Start once the first key has gathered its
  // chord, stop on the last.
  void arpHeld() {
    if (notes_.empty()) { if (arp_.start) arpStop(); else arpApply(); return; }
    if (!arp_.start) {
      arp_.start = now_ + kArpGather;
      arp_.steps = 0;
      arp_.index = -1;
      wakes_.push_back(now_ + kArpGather);
    }
  }

  // midiApplyNotesTo: what the stack - or the arpeggio standing in for it -
  // tells the generator.
  void applyNotesTo() {
    key_ = notes_.empty() ? 0 : notes_.back().velocity;
    applyGate();
    gateNotes();
    if (!drives()) return;
    if (polyWanted()) { applyPoly(); return; }
    if (notes_.empty()) return;

    // midiPair: the two most recent, ordered by pitch.
    int low = notes_.back().note, high = -1;
    if (notes_.size() > 1) {
      const int a = notes_[notes_.size() - 2].note, b = notes_.back().note;
      low = std::min(a, b);
      high = std::max(a, b);
    }
    const Tone& tone = t_.tone();
    const int lead = mode_ == NoteMode::Mono ? notes_.back().note : low;
    const double hz = midiHz(lead);

    if (mode_ == NoteMode::Dyad) {
      // One note is a unison, unless Hold keeps the last interval above it.
      if (high >= 0) {
        const int semis = std::max(0, high - low);  // midiInterval
        interval_ = semis <= 12 ? Interval { semis, 0 } : Interval { semis % 12, semis / 12 };
      } else if (!hold_) interval_ = Interval {};
      t_.set("interval", interval_.index);
      t_.set("octaves", interval_.octaves);
      panel_.interval = interval_.index;
    } else {
      t_.set("interval", panel_.interval);
      t_.set("octaves", 0);
    }

    if (tone.mode == Mode::Wave) {
      // Clamped to the slider's own range, so the control and the signal agree.
      const double set = std::fmax(30.0, std::fmin(4000.0, hz));
      t_.set("freq", set);
      panel_.freq = jsRound(set);
    } else if (tone.mode == Mode::Figure || tone.mode == Mode::Wireframe) {
      const double rate = play_[kindOf(tone.mode)] ? std::fmax(1.0, std::fmin(4000.0, hz))
                        : std::fmax(1.0, std::fmin(200.0, panel_.figureRate * hz / kMidiRoot));
      t_.set("figureRate", rate);
      // A dyad on a rose sets its petals to the dyad's own ratio.
      if (tone.mode == Mode::Figure && tone.figure == Figure::Rose) t_.set("detail", roseDetail());
    } else if (tone.mode == Mode::Harmonograph && play_[1]) {
      const double set = std::fmax(30.0, std::fmin(4000.0, hz));
      t_.set("freq", set);
      panel_.freq = jsRound(set);
    }
  }

  // roseDetail: the dyad's ratio, octaves and all; a unison leaves the slider's.
  double roseDetail() const {
    if (mode_ != NoteMode::Dyad || (interval_.index == 0 && interval_.octaves == 0)) return panel_.detail;
    return intervalRatio(interval_.index, t_.tone().just) * std::pow(2.0, interval_.octaves);
  }

  // syncPlay: a harmonograph is pitched only while notes can strike it.
  void syncPlay() {
    const Tone& tone = t_.tone();
    const bool pitched = tone.mode == Mode::Harmonograph && play_[1] && drive_[1];
    if (tone.pitched != pitched) t_.set("pitched", pitched ? 1 : 0);
  }

  NoteTarget& t_;
  RealtimeIn* realtime_;
  std::vector<Held> notes_;      // the held stack, most recent last
  std::vector<int> sustained_;   // keys up and still sounding, in the order they came up
  std::vector<Controller> cc_;
  std::array<std::vector<NoteWant>, 2> chord_;
  mutable std::vector<NoteWant> inner_;  // the Inner source's scratch
  std::array<int, 2> strikes_ { 0, 0 };
  NoteMode mode_ = NoteMode::Dyad;
  std::array<DrawRule, 2> draws_ {};
  Layers layers_;
  bool polyJust_ = false, hold_ = false, present_ = true;
  bool truth_ = true, follow_ = false;  // the note as the measurements' truth; kept for the setup
  double pedal_ = 0, pedalTarget_ = 0;
  bool sustain_ = false;
  // Per generator kind: wave, harmonograph, figure, wireframe.
  std::array<bool, 4> drive_ { true, true, true, false };
  std::array<bool, 4> play_ { false, false, false, false };
  double key_ = 0;
  Interval interval_;
  PolyCount poly_;
  Panel panel_;
  int running_ = 0;
  // The arpeggiator, and what it needs from outside: the time, the tempo, the
  // out, its random walk, and its timers.
  static constexpr double kArpGather = 25;  // ARP_GATHER: how long the first key waits for the chord
  std::function<void()> onLayers_;  // the panel's syncLayerPanel
  ArpState arp_;
  double now_ = 0, bpm_ = 120;
  NoteOut* out_ = nullptr;
  Random random_ { 1 };
  std::vector<double> wakes_;
  std::vector<Held> arpSaved_, arpSeq_;
  mutable std::vector<Held> arpBase_;
};

}  // namespace scope
