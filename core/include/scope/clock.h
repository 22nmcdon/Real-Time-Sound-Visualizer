// The page's clock, ported from web/scope.html: the tempo (the slider's, a
// tap's, or a MIDI clock's), the bar the score reads its columns from, Start,
// Stop and Continue, and the oscillators locked to note values. `transport`,
// `clockTick`, `transportBeat` and their neighbours, `clockTap`, `setTempo`
// and `clockStep`.
//
// The bar is worked out from the time it is asked about rather than stepped:
// `base` beats at `baseAt`, moving at the tempo from there, and re-based
// whenever the tempo changes, so it never jumps. Times are milliseconds, the
// page's `performance.now()`; in the plugin, the audio clock.
//
// What differs from the page, and why, so nobody goes looking:
//
// - What the page does to its panel when the clock changes - the tempo's
//   reading, the bar and beat, the LFOs' rates - is the page's. `said` is
//   here because a test reads it.
// - What the bar's anchor and Stop do to the score are hooks (`onAnchor`,
//   `onStop`), since the score is its own piece.
// - A host's transport, which the page has not got. In the plugin the host's
//   tempo is in force while it gives one, the slider's kept as under a MIDI
//   clock; its play and stop are Start and Stop; and its position, where it
//   gives one, is the bar, read afresh each block. It outranks a MIDI clock
//   arriving at the same time, and when the host stops saying, the tempo goes
//   back to the slider's as it does when a clock stops.

#pragma once

#include <cmath>
#include <functional>
#include <optional>
#include <string>
#include <utility>
#include <vector>

#include "scope/lfo.h"
#include "scope/setup.h"

namespace scope {

// LFO_SYNC: note values an oscillator can lock to, as beats a cycle (a beat
// is a crotchet, four to the bar). Nothing else is free.
inline double syncBeats(const std::string& sync) {
  static const std::pair<const char*, double> table[] = {
    { "4", 16 }, { "2", 8 }, { "1", 4 }, { "1/2", 2 }, { "1/4", 1 }, { "1/8", 0.5 }, { "1/16", 0.25 },
    { "1/4t", 2.0 / 3 }, { "1/8t", 1.0 / 3 },
  };
  for (const auto& [id, beats] : table) if (sync == id) return beats;
  return 0;
}
// DELAY_SYNC: note values a delay can take, a dotted quaver among them.
inline double delayBeats(const std::string& sync) {
  static const std::pair<const char*, double> table[] = {
    { "1/2", 2 }, { "1/4", 1 }, { "1/8d", 0.75 }, { "1/8", 0.5 }, { "1/4t", 2.0 / 3 }, { "1/8t", 1.0 / 3 },
    { "1/16", 0.25 },
  };
  for (const auto& [id, beats] : table) if (sync == id) return beats;
  return 0;
}

constexpr double kClockTimeoutMs = 500;  // CLOCK_TIMEOUT_MS: a MIDI clock this quiet has stopped

class Clock {
 public:
  enum class From { Internal, Midi, Host };

  // An oscillator that can lock to the tempo, and the note value it is
  // locked to ("" for free).
  struct Lock { Lfo* lfo; const std::string* sync; };
  std::vector<Lock> locks;
  std::function<void()> onAnchor, onStop;

  double bpm = 120;   // the tempo in force: the slider's, or the MIDI clock's
  double set = 120;   // the slider's, kept while a MIDI clock is overriding it
  From from = From::Internal;
  std::vector<double> ticks, taps;  // recent MIDI clock ticks and taps, in milliseconds
  bool running = true;
  double base = 0, baseAt = 0;
  bool onTicks = false;  // the base is a MIDI clock tick's, and waits for the next

  // The time "now" means to a caller that does not give one, as the page's
  // `performance.now()`.
  void setNow(double ms) { now_ = ms; }
  double now() const { return now_; }

  // transportBeat: where the bar is, in beats.
  double beat(double now) const {
    if (!running) return base;
    const double since = jsMax(0, now - baseAt) * bpm / 60000;
    return base + (onTicks ? jsMin(since, 1.0 / 24) : since);
  }
  void rebase(double now) { base = beat(now); baseAt = now; onTicks = false; }
  // The one, now: the bar to nought and the score to its first column.
  void anchor(double now) {
    base = 0; baseAt = now; onTicks = false;
    if (onAnchor) onAnchor();
  }

  // clockTick: a tick of MIDI clock, 24 to the crotchet, the tempo the mean
  // of the last two dozen gaps.
  void tick(double at) {
    if (!ticks.empty() && at - ticks.back() > kClockTimeoutMs) ticks.clear();
    ticks.push_back(at);
    if (ticks.size() > 25) ticks.erase(ticks.begin());
    if (running) {
      base = onTicks ? base + 1.0 / 24 : beat(at);
      baseAt = at;
      onTicks = true;
    }
    if (ticks.size() >= 3) {
      const double gap = (ticks.back() - ticks.front()) / static_cast<double>(ticks.size() - 1);
      if (gap > 0) bpm = jsMax(20, jsMin(400, 60000 / (gap * 24)));
      from = From::Midi;
    }
  }
  // Start: from the button, or a MIDI Start, which waits for the clock's
  // next tick to be the one.
  void start(double now, bool onClock = false) {
    anchor(now);
    if (onClock) { base = -1.0 / 24; onTicks = true; }
    running = true;
    restart();
  }
  // Stop: the bar stands where it is and the score lets go of its notes.
  void stop(double now) {
    base = beat(now);
    running = false;
    if (onStop) onStop();
  }
  // Continue, from a MIDI Continue: on from where it stood, at the next tick.
  void resume(double now) {
    if (running) return;
    base -= 1.0 / 24; baseAt = now; onTicks = true;
    running = true;
  }
  // midiRealtime: clock, start, continue, stop.
  void realtime(int status, double at) {
    if (status == 0xF8) tick(at);
    else if (status == 0xFA) start(at, true);
    else if (status == 0xFB) resume(at);
    else if (status == 0xFC) stop(at);
  }
  // transportSaid: "3.2", the bar and the beat, in fours, from one.
  std::string said(double now) const {
    const double b = jsMax(0, beat(now));
    return jsNumberToString(std::floor(b / 4) + 1) + "." + jsNumberToString(std::floor(std::fmod(b, 4)) + 1);
  }

  // clockRestart: every locked oscillator back to the top of its cycle.
  void restart() {
    for (auto& lock : locks) {
      if (lock.sync->empty()) continue;
      lock.lfo->phase = 0;
      lock.lfo->epoch++;
    }
  }
  // clockTap: the mean of the gaps between the last four taps; a pause of two
  // seconds starts again, and a tap while the bar runs is the one.
  void tap(double at) {
    if (!taps.empty() && at - taps.back() > 2000) taps.clear();
    taps.push_back(at);
    if (taps.size() > 4) taps.erase(taps.begin());
    if (taps.size() >= 2) {
      const double gap = (taps.back() - taps.front()) / static_cast<double>(taps.size() - 1);
      setTempo(jsMathRound(60000 / gap), at);
      restart();
      if (running) anchor(at);
    }
  }
  // setTempo: the slider's tempo, and the tempo in force unless a MIDI clock
  // is overriding it - re-based first, so the bar does not jump.
  void setTempo(double value, double at) {
    set = jsMax(30, jsMin(300, jsMathRound(value)));
    if (from == From::Internal && bpm != set) {
      rebase(at);
      bpm = set;
    }
  }
  void setTempo(double value) { setTempo(value, now_); }

  // The host's transport, once a block: its tempo, whether it is playing, and
  // where it is in beats if it says.
  void host(double hostBpm, std::optional<double> ppq, bool playing, double now) {
    const double tempo = jsMax(20, jsMin(400, hostBpm));
    hostAt_ = now;
    from = From::Host;
    ticks.clear();
    onTicks = false;
    if (playing && !running) {
      running = true;
      restart();
      if (onAnchor) onAnchor();
    } else if (!playing && running) {
      base = beat(now);
      running = false;
      if (onStop) onStop();
    }
    if (ppq) { base = *ppq; baseAt = now; }
    else if (tempo != bpm) rebase(now);
    bpm = tempo;
  }

  // clockStep, once a frame: a clock gone quiet let go of, and every locked
  // oscillator's rate from the tempo.
  void step(double now) {
    // From the last tick to where the clock would have had the bar - not
    // re-based from where it stood, which left it behind for good.
    if (onTicks && now - baseAt > kClockTimeoutMs) {
      onTicks = false;
      rebase(now);
    }
    if (from == From::Midi && (ticks.empty() || now - ticks.back() > kClockTimeoutMs)) {
      rebase(now);
      from = From::Internal;
      bpm = set;
      ticks.clear();
    }
    if (from == From::Host && now - hostAt_ > kClockTimeoutMs) {
      rebase(now);
      from = From::Internal;
      bpm = set;
    }
    for (auto& lock : locks) {
      const double beats = syncBeats(*lock.sync);
      if (beats > 0) lock.lfo->rate = bpm / 60 / beats;
    }
  }

 private:
  double now_ = 0;
  double hostAt_ = 0;
};

}  // namespace scope
