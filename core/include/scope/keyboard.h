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
// - The page reads and writes the panel's controls (`el.freq`, `el.interval`):
//   a note moves the frequency slider and the interval menu with it. Here
//   they are `Panel`, which the brain owns now that the setup is in the core.
// - Until 10 Nov the page asked `keyboardPresent()` - a port or the screen's
//   keys - before it gated the generator, and it asks whether the source can
//   lay out two figures. Here both are flags. The first (`setPresent`) is yes
//   on both hosts now, since the site waits for a note as the plugin does;
//   the instrument's `keyboardPresent` control still sets it, which only
//   parity's fixtures do, for a generator heard with no note, and the page's
//   keyboard has no counterpart to hold it to. The second (`setLayable`) the
//   instrument sets itself: no while it draws its input, whole or split into bands, since
//   layer B's figure has nowhere to go. (And while it drew a rack, until P5
//   cut the rack.)
// - Notes always play the waveform. Until G2 (9 Nov) a switch said whether
//   they played each kind of generator, and another whether a drawing was
//   played at the note's pitch; both went with the drawings, and the
//   waveform's switch had been on in every setup that left it alone.
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
//   copies it into the one it keeps, which grows only for a chord larger
//   than any before it; the voices it makes take what retired voices left
//   (G8), so a note struck on the audio thread allocates nothing.

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

// One pair of figures, two (a layer each), or layer A against layer B as one.
enum class Layout { One, Each, Against };
inline const char* layoutName(Layout l) { return l == Layout::Each ? "each" : l == Layout::Against ? "against" : "one"; }

// What the keyboard plays: the calls the page's `genSet` and the tone
// source's gate make, and the few settings the keyboard reads back. (A key
// reswung a pitched harmonograph, and the keyboard read the tone for which
// kind was playing, until G2 took the drawings.)
class NoteTarget {
 public:
  virtual ~NoteTarget() = default;
  virtual bool hasVoices(int layer) const = 0;
  virtual void set(std::string_view field, double value) = 0;  // layer A's
  virtual void setVoices(const std::vector<NoteWant>* list, int layer) = 0;
  virtual void gate(bool open, double velocity) = 0;
  // A key gone down (8 Nov): the page's midiApplyNotesTo tells the generator.
  virtual void noteDown() = 0;
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
  bool hasVoices(int layer) const override {
    return layer == 1 ? g_.toneB().voices.has_value() : g_.tone().voices.has_value();
  }
  void set(std::string_view field, double value) override { g_.set(field, value, 0); }
  void setVoices(const std::vector<NoteWant>* list, int layer) override { g_.setVoices(list, layer); }
  void gate(bool open, double velocity) override { g_.gate(open, velocity); }
  void noteDown() override { g_.noteDown(); }
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
};

struct Held { int note; double velocity; };

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
    // And on the screen, where Scan reads (P7b): the layers the note is in, A's as 1 and B's as 2.
    if (onStrike_) onStrike_(note, velocity / 127, layersOf(note));
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

  // midiControl: 120 and 123 are panics, 64 is the pedal, 11 the Picture
  // amount and 1 the wheel; nothing is learned since F4b (the page's says why).
  void control(int number, int raw) {
    if (number == 120 || number == 123) { panic(); return; }
    if (number == 64) { setPedal(raw / 127.0); return; }
    // 11, the expression pedal, is also the Picture amount (the page's
    // midiControl says why); whoever keeps the panel is told.
    if (number == 11 && onSwell_) onSwell_(raw / 127.0 * 100);
    // 1, the mod wheel, is what Expression's Wheel menu gives it to (6 Nov).
    if (number == 1) express(wheelTo_, raw / 127.0);
  }

  /* Expression (6 Nov): the page's midiPitchBend, midiPressure and the
     menus that say what the wheel and pressure are given to. */
  enum class Express { Vibrato, Picture, Scan, Off };
  static Express expressNamed(std::u16string_view name, Express fallback) {
    if (name == u"vibrato") return Express::Vibrato;
    if (name == u"picture") return Express::Picture;
    if (name == u"scan") return Express::Scan;
    if (name == u"off") return Express::Off;
    return fallback;
  }
  void pitchBend(int lsb, int msb) {
    const int v = ((msb << 7) | lsb) - 8192;
    bend_ = v / (v < 0 ? 8192.0 : 8191.0);
    t_.set("pitchBend", bend_ * bendRange_);
  }
  void pressure(int raw) { express(pressureTo_, raw / 127.0); }
  /* midiExpress: vibrato is the generator's, set here as the page's genSet
     sets it; the Picture amount and Scan's depth are the panel's sliders,
     which whoever keeps the panel is told, as the expression pedal's is. */
  static constexpr double kVibratoMost = 1.0 / 3;  // VIBRATO_MOST, in semitones at the top
  void express(Express to, double value) {
    if (to == Express::Vibrato) t_.set("vibrato", value * kVibratoMost);
    else if ((to == Express::Picture || to == Express::Scan) && onExpress_) onExpress_(to, value);
  }
  void setExpression(double bendRange, Express wheel, Express pressure) {
    bendRange_ = bendRange; wheelTo_ = wheel; pressureTo_ = pressure;
  }
  double bendRange() const { return bendRange_; }
  double bend() const { return bend_; }
  Express wheelTo() const { return wheelTo_; }
  Express pressureTo() const { return pressureTo_; }
  void setExpress(std::function<void(Express, double)> f) { onExpress_ = std::move(f); }

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
      if (kind == 0xd0) { pressure(got[0]); continue; }
      if (need == 1) continue;
      if (kind == 0x90) noteOn(got[0], got[1]);
      else if (kind == 0x80) noteOff(got[0]);
      else if (kind == 0xb0) control(got[0], got[1]);
      else if (kind == 0xe0) pitchBend(got[0], got[1]);
    }
  }

  // --- once a frame ---------------------------------------------------------

  /* midiApplyGate, as the page's frame has it: the gate and the chord derived
     again. The pedal and pressure walked here first (midiSmooth), for the
     sources F4b cut, and for nothing from then until the second review. */
  void frame() { applyGate(); }

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
  void setPresent(bool on) { present_ = on; }
  // Whether the generator is on its own, to lay out a figure for each layer: not while the input is drawn.
  void setLayable(bool on) { layable_ = on; }
  Panel& panel() { return panel_; }

  // --- the arpeggiator: Stage K5 ---------------------------------------------

  void setNow(double ms) { now_ = ms; }
  void setTempo(double bpm) { bpm_ = bpm; }
  void setOut(NoteOut* out) { out_ = out; }

  // arpSet: the menus' values. Switched with keys down, the generator is given
  // what it should now have. Switched off once a step has played, what is
  // held is struck, as a step is (11 Nov; the page's arpSet says why): a
  // setup loaded over held keys left them on the last step's envelope.
  void setArp(std::string mode, std::string rate, double octaves) {
    const bool stepped = !arp_.current.empty();
    arp_.mode = std::move(mode);
    arp_.rate = std::move(rate);
    arp_.octaves = octaves == 0 || std::isnan(octaves) ? 1 : octaves;
    if (arp_.start) { offSent(); arp_.start.reset(); }
    arp_.index = -1;
    arp_.current.clear();
    if (stepped && !arpActive() && !notes_.empty()) {
      std::swap(notes_, arpSaved_);
      notes_.clear();
      applyNotesTo();
      std::swap(notes_, arpSaved_);
    }
    applyNotes();
  }
  // The rate and octaves menus' own handlers: the field and nothing else,
  // where the mode's handler (arpSet) starts the arpeggio afresh.
  void setArpRate(std::string rate) { arp_.rate = std::move(rate); }
  void setArpOctaves(double octaves) { arp_.octaves = octaves == 0 || std::isnan(octaves) ? 1 : octaves; }
  bool arpActive() const { return arp_.mode != "off"; }
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
  };
  Settings settings() const {
    return { mode_, draws_, layers_.mode, layers_.point, layers_.against, polyJust_, hold_, truth_, follow_ };
  }
  void setSettings(const Settings& s) {
    mode_ = s.mode; draws_ = s.draws; layers_.mode = s.layers; layers_.point = s.point; layers_.against = s.against;
    layers_.learning = false; polyJust_ = s.polyJust; hold_ = s.hold; truth_ = s.truth; follow_ = s.follow;
  }
  // midiApplyNotes: what `restore` ends the keyboard with, so what is under
  // the hands outranks what the setup asked for.
  void apply() { applyNotes(); }

  // --- what it says ---------------------------------------------------------

  const std::vector<Held>& notes() const { return notes_; }
  const std::vector<int>& sustained() const { return sustained_; }
  bool sustain() const { return sustain_; }
  int splitPoint() const { return layers_.point; }
  bool learning() const { return layers_.learning; }
  std::array<int, 2> strikes() const { return strikes_; }
  std::array<int, 2> interval() const { return { interval_.index, interval_.octaves }; }
  struct PolyCount { int sounding = 0, drawn = 0, held = 0; };
  PolyCount polyCount() const { return poly_; }

  // Key, the one keyboard source left since F4b (velocity, Expression's FM).
  double key() const { return key_; }

  // layersOn: two layers, in poly with the generator alone.
  bool layersOn() const { return layers_.mode != LayerMode::Off && layable_ && polyWanted(); }
  /* Which layer the panel shows (editLayer): B only while there is one, so
     no control writes into a layer nobody hears. The A and B buttons choose,
     and whoever keeps the panel is told whenever the layers are worked out
     again, as the page's syncLayers shows the layer on the panel first. */
  int editLayer() const { return layersOn() && layers_.edit == 1 ? 1 : 0; }
  void setEdit(int layer) { layers_.edit = layer == 1 ? 1 : 0; if (onLayers_) onLayers_(); }
  // The hand chosen, whether or not there are two to choose between (G6: a project keeps it).
  int edit() const { return layers_.edit; }
  void setLayerPanel(std::function<void()> f) { onLayers_ = std::move(f); }
  /* Who lays a note's strike on the screen (P7b): the page's midiNoteOn calls
     scanStrike, which is the picture's, so the keyboard only says the note,
     its velocity as a fraction and the layers it is in. */
  void setStrike(std::function<void(int, double, int)> f) { onStrike_ = std::move(f); }
  // The layers a note is in, as scanStrike picks them: A alone without layers, its half in a split, both layered.
  int layersOf(int note) const {
    if (!layersOn()) return 1;
    if (layers_.mode == LayerMode::Split) return note >= layers_.point ? 2 : 1;
    return 3;
  }
  void setSwell(std::function<void(double)> f) { onSwell_ = std::move(f); }

 private:
  struct Interval { int index = 0, octaves = 0; };
  struct Layers { LayerMode mode = LayerMode::Off; int point = 60; bool against = false; bool learning = false; int edit = 0; };

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

  // polyWanted: chords, while there is a keyboard to play them.
  bool polyWanted() const { return mode_ == NoteMode::Poly && present_; }

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
      // While the input is drawn, whole or in bands, the generator's figure is not: every note on both sides (the page's polyVoices).
      v.role = !layable_ ? "xy"
             : !isDrawn(held.note) ? "u"
             : against ? (which == 1 ? "yonly" : "xonly")
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
    const Layout want = !on ? Layout::One : layers_.against ? Layout::Against : Layout::Each;
    if (t_.layout() != want) t_.setLayout(want);
  }

  // midiApplyGate: gated while there is a keyboard to play it. Only the
  // change opens it here.
  void applyGate() {
    syncPoly();
    const bool on = present_;
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
    /* By note, keeping the order notes came in for a note held twice, as the
       page's sort does: an insertion sort, which needs nothing beyond the
       list, where std::stable_sort asks the allocator for a buffer - every
       step of the arpeggio, on the audio thread (G8). A dozen notes at most. */
    if (arp_.mode != "played") {
      for (std::size_t i = 1; i < base.size(); ++i) {
        const Held h = base[i];
        std::size_t j = i;
        for (; j > 0 && h.note < base[j - 1].note; --j) base[j] = base[j - 1];
        base[j] = h;
      }
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
    // A note held now that was not last time is a key gone down, as the page reckons it.
    bool struck = false;
    for (const auto& n : notes_) struck = struck || !holds(notesBefore_, n.note);
    notesBefore_.clear();
    for (const auto& n : notes_) notesBefore_.push_back(n.note);
    if (struck && t_.gated()) t_.noteDown();
    if (polyWanted()) { applyPoly(); return; }
    if (notes_.empty()) return;

    // midiPair: the two most recent, ordered by pitch.
    int low = notes_.back().note, high = -1;
    if (notes_.size() > 1) {
      const int a = notes_[notes_.size() - 2].note, b = notes_.back().note;
      low = std::min(a, b);
      high = std::max(a, b);
    }
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

    // Clamped to the slider's own range, so the control and the signal agree.
    const double set = std::fmax(30.0, std::fmin(4000.0, hz));
    t_.set("freq", set);
    panel_.freq = jsRound(set);
  }

  NoteTarget& t_;
  RealtimeIn* realtime_;
  std::vector<Held> notes_;      // the held stack, most recent last
  std::vector<int> sustained_;   // keys up and still sounding, in the order they came up
  std::array<std::vector<NoteWant>, 2> chord_;
  mutable std::vector<NoteWant> inner_;  // the Inner source's scratch
  std::array<int, 2> strikes_ { 0, 0 };
  std::vector<int> notesBefore_;  // the notes the generator was last given (midiNotesBefore)
  NoteMode mode_ = NoteMode::Dyad;
  std::array<DrawRule, 2> draws_ {};
  Layers layers_;
  bool polyJust_ = false, hold_ = false, present_ = true, layable_ = true;
  bool truth_ = true, follow_ = false;  // the note as the measurements' truth; kept for the setup
  double pedalTarget_ = 0;
  bool sustain_ = false;
  double bendRange_ = 2, bend_ = 0;  // Expression (6 Nov)
  Express wheelTo_ = Express::Vibrato, pressureTo_ = Express::Off;
  double key_ = 0;
  Interval interval_;
  PolyCount poly_;
  Panel panel_;
  int running_ = 0;
  // The arpeggiator, and what it needs from outside: the time, the tempo, the
  // out, its random walk, and its timers.
  static constexpr double kArpGather = 25;  // ARP_GATHER: how long the first key waits for the chord
  std::function<void()> onLayers_;  // the panel's syncLayerPanel
  std::function<void(int, double, int)> onStrike_;  // the instrument's scanStrike (P7b)
  std::function<void(double)> onSwell_;  // the Picture slider, from the expression pedal
  std::function<void(Express, double)> onExpress_;  // the Picture amount or Scan's depth, from the wheel or pressure
  ArpState arp_;
  double now_ = 0, bpm_ = 120;
  NoteOut* out_ = nullptr;
  Random random_ { 1 };
  std::vector<double> wakes_;
  std::vector<Held> arpSaved_, arpSeq_;
  mutable std::vector<Held> arpBase_;
};

}  // namespace scope
