// The score (Stage K3) and MIDI out (K4), ported from web/scope.html: the
// phosphor grid read as a graphical score, a playhead crossing its 64 columns
// on the clock's bar, the brightest few pitches of the key in a column struck
// in the generator's score voice and sent out; and the out they share with the
// crossings, the pluck and the arpeggiator - one port and one channel, a rate
// limit on note-ons and never on note-offs, and a panic. `scorePitches`,
// `scoreColumn`, `scoreTick`, `scoreStop`, `midiOutNote`, `midiOutOff`,
// `midiOutPanic`, `crossStepPanel`'s notes and `pluckFire`.
//
// What differs from the page, and why, so nobody goes looking:
//
// - The grid is the page's until the picture's sources move into the core
//   (PLAN.md, stage 4). The score reads whatever grid it is handed, and in the
//   plugin it is handed none yet, so it plays nothing.
// - What the out sends is bytes handed to a sink: in the page a Web MIDI port,
//   in the plugin the host's MIDI out.
// - The readouts - the count beside the crossings' switch, the out's status,
//   the playhead over the picture - are the page's.

#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <functional>
#include <string>
#include <utility>
#include <vector>

#include "scope/clock.h"
#include "scope/keyboard.h"
#include "scope/loop.h"  // kPhosphorN
#include "scope/setup.h"

namespace scope {

constexpr double kScoreFloor = 0.15;  // SCORE_FLOOR: brightness a note needs, of one
constexpr std::size_t kMidiOutRate = 40;  // MIDI_OUT_RATE: note-ons a second, at most

// The MIDI out: one port and one channel. A note-on past forty a second is
// dropped and counted; a note-off never is, since a dropped note-off is a note
// that sounds until someone finds the panic button.
class MidiOut : public NoteOut {
 public:
  using Sink = std::function<void(const std::uint8_t* bytes, int length)>;
  explicit MidiOut(Sink sink = {}) : sink_(std::move(sink)) {}

  // midiOutChoose: all notes off on the old port and channel, then the new.
  void choose(bool port, int channel) {
    panic();
    port_ = port;
    channel_ = channel;
  }
  bool noteOut(int note, double velocity, double now) override {
    if (!port_) return false;
    times_.erase(std::remove_if(times_.begin(), times_.end(), [now](double t) { return !(now - t < 1000); }), times_.end());
    if (times_.size() >= kMidiOutRate) { dropped_++; return false; }
    times_.push_back(now);
    // A note already sounding is ended first, so the synth hears a new strike.
    const auto at = find(note);
    if (at != sounding_.end()) send(0x80 | channel_, note, 0);
    send(0x90 | channel_, note, static_cast<int>(jsMax(1, jsMin(127, jsMathRound(velocity * 127)))));
    if (at != sounding_.end()) at->second = now; else sounding_.push_back({ note, now });
    last_ = now;
    return true;
  }
  void noteOutOff(int note) override {
    const auto at = find(note);
    if (at == sounding_.end()) return;
    send(0x80 | channel_, note, 0);
    sounding_.erase(at);
  }
  // midiOutPanic: every note this has sent, then All Notes Off.
  void panic() {
    for (const auto& [note, when] : sounding_) send(0x80 | channel_, note, 0);
    sounding_.clear();
    send(0xB0 | channel_, 123, 0);
  }

  bool port() const { return port_; }
  int dropped() const { return dropped_; }
  double last() const { return last_; }
  std::size_t recent() const { return times_.size(); }
  const std::vector<std::pair<int, double>>& sounding() const { return sounding_; }

 private:
  std::vector<std::pair<int, double>>::iterator find(int note) {
    return std::find_if(sounding_.begin(), sounding_.end(), [note](const auto& s) { return s.first == note; });
  }
  void send(int a, int b, int c) {
    if (!port_ || !sink_) return;
    const std::uint8_t bytes[3] = { static_cast<std::uint8_t>(a), static_cast<std::uint8_t>(b), static_cast<std::uint8_t>(c) };
    sink_(bytes, 3);
  }

  Sink sink_;
  bool port_ = false;
  int channel_ = 0, dropped_ = 0;
  std::vector<double> times_;
  std::vector<std::pair<int, double>> sounding_;  // by when each was first sent, as a Map keeps them
  double last_ = -HUGE_VAL;
};

// A strike in the generator's score voice: a pitch in hertz and how hard.
using Strike = std::function<void(double hz, double velocity)>;

// SCORE_STEPS: the playhead's step, in beats.
inline double scoreStepBeats(const std::string& step) {
  if (step == "1/8") return 0.5;
  if (step == "1/4") return 1;
  return 0.25;
}

// scorePitches: the pitches the rows can play, the key from `low`, `octaves` up.
inline std::vector<int> scorePitches(double low, double octaves, int mask) {
  std::vector<int> out;
  for (double m = low; m < low + 12 * octaves; m++) {
    if (mask & (1 << static_cast<int>(std::fmod(m, 12)))) out.push_back(static_cast<int>(m));
  }
  return out;
}

// scoreColumn: each pitch owns a band of rows, bottom up, as bright as its
// brightest row; the `voices` brightest over the floor are the chord, loudest
// first. Brightness is kept in single precision, as the page's Float32Array.
inline std::vector<std::pair<int, double>> scoreColumn(const float* grid, int n, int col, const std::vector<int>& pitches,
                                                       double voices) {
  std::vector<std::pair<int, double>> picked;
  if (pitches.empty()) return picked;
  const int len = static_cast<int>(pitches.size());
  std::vector<float> bright(pitches.size(), 0.0f);
  for (int row = 0; row < n; row++) {
    const float g = grid[row * n + col];
    if (!(g > 0)) continue;
    const int band = std::min(len - 1, static_cast<int>(std::floor(static_cast<double>(n - 1 - row) * len / n)));
    if (g > bright[static_cast<std::size_t>(band)]) bright[static_cast<std::size_t>(band)] = g;
  }
  for (int k = 0; k < len; k++) {
    if (bright[static_cast<std::size_t>(k)] >= kScoreFloor) picked.push_back({ pitches[static_cast<std::size_t>(k)], bright[static_cast<std::size_t>(k)] });
  }
  std::stable_sort(picked.begin(), picked.end(), [](const auto& a, const auto& b) {
    return a.second != b.second ? a.second > b.second : a.first < b.first;
  });
  // slice(0, voices): whole, by truncation, a negative end counted from the
  // end, and nothing for one that is not a number.
  const double size = static_cast<double>(picked.size());
  double keep = std::isnan(voices) ? 0 : std::trunc(voices);
  if (keep < 0) keep = std::fmax(0, size + keep);
  if (keep < size) picked.resize(static_cast<std::size_t>(keep));
  return picked;
}

// The score: what a setup sets, and where the playhead is.
struct ScoreState {
  bool on = false;
  std::string step = "1/16";
  double voices = 2, low = 48, octaves = 3;
  int col = -1;
  double last = -1, steps = 0;
  std::vector<std::pair<int, double>> notes;
};

inline void scoreStop(ScoreState& score, NoteOut* out) {
  for (const auto& [note, velocity] : score.notes) if (out) out->noteOutOff(note);
  score.notes.clear();
  score.last = -1;
  score.steps = 0;
  score.col = -1;
}

// scoreTick, once a frame: the step the bar is on, if it has moved - only the
// newest, since two notes in one frame would be a flam - the last step's
// notes ended as the next begin. Stopped, or with the scope stopped, nothing.
inline void scoreTick(ScoreState& score, double now, bool scopeRunning, const Clock& clock, const float* grid, int mask,
                      const Strike& strike, NoteOut* out) {
  if (!score.on || !scopeRunning || !clock.running) {
    if (score.last != -1 || !score.notes.empty()) scoreStop(score, out);
    return;
  }
  // A hair over, so a step due on the exact millisecond is not a frame late.
  const double step = std::floor(clock.beat(now) / scoreStepBeats(score.step) + 1e-9);
  // Before the one, nothing: on the page that is only a MIDI Start's tick, a
  // step of minus one, but a host's count-in is bars of it, and a negative
  // column would be read from outside the grid.
  if (step < 0 || step == score.last) return;
  score.last = step;
  score.steps++;
  score.col = static_cast<int>(std::fmod(step, kPhosphorN));
  for (const auto& [note, velocity] : score.notes) if (out) out->noteOutOff(note);
  score.notes = grid ? scoreColumn(grid, kPhosphorN, score.col, scorePitches(score.low, score.octaves, mask), score.voices)
                     : std::vector<std::pair<int, double>> {};
  if (score.notes.empty()) return;
  for (const auto& [note, velocity] : score.notes) if (strike) strike(midiHz(note), velocity);
  for (const auto& [note, velocity] : score.notes) if (out) out->noteOut(note, velocity, now);
}

// The crossings' notes out (crossStepPanel): a count gone up is a crossing, sent
// as a note and ended a tenth of a second later; and the pluck's (pluckFire),
// ended after 150 ms. Their pending note-offs, oldest last.
struct NotesOut {
  int seenX = 0, seenY = 0;
  std::vector<std::pair<int, double>> crossOffs, pluckOffs;
};
inline void endDue(std::vector<std::pair<int, double>>& offs, double now, NoteOut* out) {
  for (std::size_t k = offs.size(); k-- > 0;) {
    if (now >= offs[k].second) {
      if (out) out->noteOutOff(offs[k].first);
      offs.erase(offs.begin() + static_cast<std::ptrdiff_t>(k));
    }
  }
}
inline void crossStep(NotesOut& n, double now, bool crossOn, std::array<int, 2> counts, int noteX, int noteY, NoteOut* out) {
  endDue(n.crossOffs, now, out);
  if (!crossOn) return;
  // Up, not merely changed: a new generator starts its count again from nought.
  if (counts[0] != n.seenX) {
    if (counts[0] > n.seenX && out && out->noteOut(noteX, 0.8, now)) n.crossOffs.push_back({ noteX, now + 100 });
    n.seenX = counts[0];
  }
  if (counts[1] != n.seenY) {
    if (counts[1] > n.seenY && out && out->noteOut(noteY, 0.8, now)) n.crossOffs.push_back({ noteY, now + 100 });
    n.seenY = counts[1];
  }
}
inline void pluckFire(NotesOut& n, int note, double velocity, double now, const Strike& strike, NoteOut* out) {
  if (strike) strike(midiHz(note), velocity);
  if (out && out->noteOut(note, velocity, now)) n.pluckOffs.push_back({ note, now + 150 });
}

}  // namespace scope
