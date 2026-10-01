// The modulation matrix, ported from web/scope.html: sources and destinations
// registered by id, routings between them with a depth each, the reach a
// picture source may move a destination and the one total the loop may push
// into it, the fades that ease a routing in when it arrives and out when it
// leaves and ease the stepped sources through their envelopes, the events
// fired once a frame, the picture's destinations summed once a frame, and the
// routes compiled for the generator, read and faded once a block.
//
// It is held to the page's own functions by core/tests/parity.py, which drives
// both through the same routings, values and times and compares the routes,
// the events and the picture's offsets each frame.
//
// What differs from the page, and why, so nobody goes looking:
//
// - The page reads `performance.now()` wherever it needs the time. Here the
//   time is handed in - to `frame` and `routes` - so a block knows when it is
//   and two runs of the same thing agree.
// - The page keeps a routing's fades and its events by the routing OBJECT: a
//   preset's load makes new objects, and an edit keeps the old one. Here each
//   routing carries a serial number, given when it is made and kept through an
//   edit, which is the same thing said with a number.
// - The page asks `layersOn()` of the keyboard and `midi.strikesBy` for the
//   notes struck per layer; here the brain hands both over (`setLayered`,
//   `setStrikes`).
// - What only the page's panel reads - the fade's last ramp, for the dot on
//   the drawing - is not kept.

#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <functional>
#include <limits>
#include <map>
#include <optional>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include "scope/generator.h"
#include "scope/text.h"

namespace scope {

// A source as the matrix sees it. The flags are the page's: an event source
// counts hits rather than holding a level, a picture source closes the loop,
// a stepped source moves only when a note does, `reach` is the most of a
// destination's span a source may move it (nought for no limit), and `index`
// is an LFO the per-sample loop reads for itself.
class ModSource {
 public:
  explicit ModSource(std::string sourceId) : id(std::move(sourceId)) {}
  virtual ~ModSource() = default;
  virtual double value() const = 0;
  virtual int count() const { return 0; }
  std::string id;
  bool event = false, fromPicture = false, stepped = false, reachVaries = false;
  double reach = 0;
  int index = -1;
};

enum class DestKind { Audio, Visual, Event };

// A destination: one of the generator's slots, a property of the picture
// written as an offset once a frame, or something struck.
struct ModDest {
  std::string id;
  DestKind kind = DestKind::Audio;
  int slot = 0;
  bool unipolar = false;
  double span = 0, min = 0, max = 0;
  std::function<double()> base;
  std::function<void(double)> set;
  std::function<void(double)> fire;
};

// GEN_DESTS: the generator's destinations, each on its slot of the routings'
// accumulator. Amplitude only ever ducks.
inline std::vector<ModDest> genDests() {
  std::vector<ModDest> out;
  const auto add = [&](std::string id, int at, bool unipolar = false) {
    ModDest d;
    d.id = std::move(id); d.slot = at; d.unipolar = unipolar;
    out.push_back(std::move(d));
  };
  add("gen.freq", slot::Freq); add("gen.amp", slot::Amp, true); add("gen.phase", slot::Phase);
  add("gen.ratio", slot::Ratio); add("gen.detail", slot::Detail); add("gen.tumble", slot::Tumble);
  add("gen.depth", slot::Depth);
  for (int k = 0; k < 9; k++) add("gen.bar" + std::to_string(k), slot::Drawbar + k);
  add("gen.morph", slot::Morph); add("gen.radius", slot::Radius); add("gen.twist", slot::Twist);
  add("gen.fm", slot::Fm); add("gen.sync", slot::Sync); add("gen.drive", slot::Drive); add("gen.fold", slot::Fold);
  add("gen.vcf", slot::Vcf); add("gen.echo", slot::Echo); add("gen.echoTime", slot::EchoTime);
  add("gen.swing", slot::Swing); add("gen.width", slot::Width); add("gen.table", slot::Table);
  add("gen.spinX", slot::Spin); add("gen.spinY", slot::Spin + 1); add("gen.spinZ", slot::Spin + 2);
  return out;
}

// A routing: a source, a destination and a depth. The serial is the page's
// object identity - new for a new routing or a preset's, kept through an edit.
struct Routing {
  std::string sourceId, destId;
  double amount = 0;
  long serial = 0;
  std::string key() const { return sourceId + ">" + destId; }  // routeKey
};

enum class FadeMode { Off, In, Out, Both };

// One layer's envelope, as the page's `fade.envs` holds it.
struct FadeEnvelope {
  double delay = 0, attack = 2, attackMid = 0.5, decay = 0.5, decayMid = 0.5, sustain = 1;
  double release = 2, releaseMid = 0.5;
  bool restart = false, loop = false;
};

// What `setFadeEnvelope` is handed: any of the envelope's numbers, and the
// names a fade stored before the envelope had (seconds for both, in and out).
struct FadePart {
  std::optional<double> delay, attack, attackMid, decay, decayMid, sustain, release, releaseMid;
  std::optional<double> seconds, inSeconds, outSeconds, inMid, outMid;
  std::optional<bool> restart, loop;
};

constexpr double kLoopTotal = 0.5;  // LOOP_TOTAL
inline double clampLoop(double v) { return std::fmax(-kLoopTotal, std::fmin(kLoopTotal, v)); }

// routingAllowed: an event reaches only an event, and never from the picture.
inline bool routingAllowed(const ModSource* source, const ModDest* dest) {
  if (!source || !dest) return false;
  if (source->event != (dest->kind == DestKind::Event)) return false;
  if (source->event && source->fromPicture) return false;
  return true;
}

// routingAmount: a picture source's depth, held within its reach.
inline double routingAmount(const ModSource* source, double amount) {
  if (!source || !(source->reach > 0)) return amount;
  return std::fmax(-source->reach, std::fmin(source->reach, amount));
}

// fadeTravel: how far along its stretch a fade is, a power of the share of
// its time chosen so half the time gives the stored midpoint.
inline double fadeTravel(double t, double mid) {
  if (t >= 1) return 1;
  if (t <= 0) return 0;
  return std::pow(t, std::log(mid) / std::log(0.5));
}

class Matrix {
 public:
  Matrix() {
    for (auto& d : genDests()) registerDest(std::move(d));
    routes_.reserve(64);
  }

  // --- what there is ----------------------------------------------------------

  void registerSource(ModSource* source) {
    sources_[source->id] = source;
  }
  void unregisterSource(const std::string& id) { sources_.erase(id); }
  void registerDest(ModDest dest) {
    const auto at = destIndex_.find(dest.id);
    if (at != destIndex_.end()) { dests_[at->second] = std::move(dest); return; }
    destIndex_[dest.id] = dests_.size();
    dests_.push_back(std::move(dest));
  }
  const std::vector<ModDest>& dests() const { return dests_; }

  // --- the routings -------------------------------------------------------------

  const std::vector<Routing>& routings() const { return routings_; }
  void add(std::string sourceId, std::string destId, double amount) {
    routings_.push_back({ std::move(sourceId), std::move(destId), amount, ++serial_ });
    touch();
  }
  void remove(std::string_view sourceId, std::string_view destId) {
    routings_.erase(std::remove_if(routings_.begin(), routings_.end(), [&](const Routing& r) {
      return r.sourceId == sourceId && r.destId == destId;
    }), routings_.end());
    touch();
  }
  // An edit keeps the routing, as the page's object is kept.
  void setAmount(std::string_view sourceId, std::string_view destId, double amount) {
    for (auto& r : routings_) {
      if (r.sourceId == sourceId && r.destId == destId) { r.amount = amount; break; }
    }
    touch();
  }
  // A preset's routings: every one new.
  void load(const std::vector<Routing>& list) {
    routings_.clear();
    for (const auto& r : list) routings_.push_back({ r.sourceId, r.destId, r.amount, ++serial_ });
    touch();
  }

  // touchRoutings: stored within reach, except for a source whose reach
  // depends on what is playing, which keeps what was asked.
  void touch() {
    dirty_ = true;
    for (auto& r : routings_) {
      const ModSource* s = source(r.sourceId);
      if (s && s->reach > 0 && !s->reachVaries) r.amount = routingAmount(s, r.amount);
    }
  }

  // encodeRoutings: "src>dest@0.400;..." with three places.
  static std::string encode(const std::vector<Routing>& list) {
    std::string out;
    for (const auto& r : list) {
      if (!out.empty()) out += ";";
      out += r.sourceId + ">" + r.destId + "@" + jsToFixed(r.amount, 3);
    }
    return out;
  }
  // decodeRoutings: each part `src>dest@amount`, anything else skipped.
  static std::vector<Routing> decode(std::string_view text) {
    std::vector<Routing> out;
    std::size_t at = 0;
    while (at <= text.size()) {
      const std::size_t end = std::min(text.find(';', at), text.size());
      std::string_view part = text.substr(at, end - at);
      while (!part.empty() && isSpace(part.front())) part.remove_prefix(1);
      while (!part.empty() && isSpace(part.back())) part.remove_suffix(1);
      const std::size_t gt = part.find('>');
      const std::size_t atSign = gt == std::string_view::npos ? gt : part.find('@', gt + 1);
      if (gt != std::string_view::npos && gt > 0 && atSign != std::string_view::npos && atSign > gt + 1
          && part.substr(0, gt).find('>') == std::string_view::npos
          && part.substr(gt + 1, atSign - gt - 1).find('@') == std::string_view::npos
          && isAmount(part.substr(atSign + 1))) {
        out.push_back({ std::string(part.substr(0, gt)), std::string(part.substr(gt + 1, atSign - gt - 1)),
                        jsNumber(part.substr(atSign + 1)), 0 });
      }
      if (end >= text.size()) break;
      at = end + 1;
    }
    return out;
  }

  // --- the fades ----------------------------------------------------------------

  // setFade: a new mode starts from where things are - every routing fully
  // on, nothing left fading. A time is both the attack and the release.
  void setFade(FadeMode mode, std::optional<double> seconds = std::nullopt) {
    if (seconds) {
      FadePart p;
      p.seconds = seconds;
      setFadeEnvelope(p, 0);
      setFadeEnvelope(p, 1);
    }
    if (mode != mode_) {
      mode_ = mode;
      gains_.clear();
      stepFade_.clear();
      // Keyed as the page's Map is: a pair twice over is one entry, where the
      // first of them stood, holding the last of them.
      for (const auto& r : routings_) {
        const std::string key = r.key();
        Gain* entry = nullptr;
        for (auto& g : gains_) if (g.key == key) { entry = &g; break; }
        if (entry) *entry = { key, { still(1, 0), still(1, 1) }, r };
        else gains_.push_back({ key, { still(1, 0), still(1, 1) }, r });
      }
      dirty_ = true;
    }
  }
  FadeMode fadeMode() const { return mode_; }

  // setFadeEnvelope: each number clamped, the old names taken as the new.
  void setFadeEnvelope(const FadePart& part, int layer = 0) {
    FadeEnvelope& env = envs_[layer == 1 ? 1 : 0];
    FadePart p = part;
    if (p.seconds) {
      if (!p.attack) p.attack = p.seconds;
      if (!p.release) p.release = p.seconds;
    }
    if (p.inSeconds && !p.attack) p.attack = p.inSeconds;
    if (p.outSeconds && !p.release) p.release = p.outSeconds;
    if (p.inMid && !p.attackMid) p.attackMid = p.inMid;
    if (p.outMid && !p.releaseMid) p.releaseMid = p.outMid;
    const auto within = [](const std::optional<double>& v, double lo, double hi, double dflt) {
      return v && std::isfinite(*v) ? std::fmax(lo, std::fmin(hi, *v)) : dflt;
    };
    env.delay = within(p.delay, 0, kDelayMax, env.delay);
    env.attack = within(p.attack, kFadeMin, kFadeMax, env.attack);
    env.decay = within(p.decay, kFadeMin, kFadeMax, env.decay);
    env.release = within(p.release, kFadeMin, kFadeMax, env.release);
    env.sustain = within(p.sustain, 0, 1, env.sustain);
    env.attackMid = within(p.attackMid, kBendMin, kBendMax, env.attackMid);
    env.decayMid = within(p.decayMid, kBendMin, kBendMax, env.decayMid);
    env.releaseMid = within(p.releaseMid, kBendMin, kBendMax, env.releaseMid);
    if (p.restart) env.restart = *p.restart;
    if (p.loop) env.loop = *p.loop;
  }
  const FadeEnvelope& fadeEnvelope(int layer) const { return envs_[layer == 1 ? 1 : 0]; }

  // The time, for what is asked between frames: the page reads its clock
  // wherever it is asked, and how much is heard depends on it.
  void setTime(double now) { now_ = now; }
  void setLayered(bool on) { layered_ = on; }
  void setStrikes(std::array<int, 2> strikes) { strikes_ = strikes; }

  // fadeGain: how much of a routing is on, for one layer.
  double fadeGain(const std::string& key, int layer = 0) const {
    if (mode_ == FadeMode::Off) return 1;
    const Gain* entry = gain(key);
    if (!entry) return fadesIn() ? 0 : 1;
    return rampAt(entry->ramps[static_cast<std::size_t>(layer)], now_);
  }

  // routingsHeard: the routings in the setup, and those fading out.
  const std::vector<Routing>& heard() const {
    if (!fadesOut() || gains_.empty()) return routings_;
    heard_ = routings_;
    for (const auto& g : gains_) {
      if (inSetup(g.key)) continue;
      bool sounding = false;
      for (const auto& ramp : g.ramps) if (ramp.to > 0 || !rampDone(ramp, now_)) sounding = true;
      if (sounding) heard_.push_back(g.routing);
    }
    return heard_;
  }
  std::size_t fading() const { return gains_.size(); }
  bool dirty() const { return dirty_; }

  // --- once a frame ---------------------------------------------------------------

  // fadeStep, fireEvents and the picture's destinations, in the page's order.
  void frame(double now) {
    now_ = now;
    fadeStep();
    fireEvents();
    applyVisual();
  }

  // --- once a block ---------------------------------------------------------------

  // workletRoutes: compiled if anything changed, each held source read, each
  // depth at its fade - the routes as the generator takes them.
  const std::vector<Route>& routes(double now) {
    now_ = now;
    if (dirty_) compile();
    const bool layered = mode_ != FadeMode::Off && layered_;
    routes_.clear();
    for (auto& c : compiled_) {
      Route r;
      r.index = c.index;
      if (c.index < 0) {
        c.held = c.parts.empty() ? sourceNow(*c.source, 0) : loopValue(c);
        c.heldB = layered ? (c.parts.empty() ? sourceNow(*c.source, 1) : loopValue(c)) : c.held;
      }
      c.amount = c.loop ? c.full : c.full * fadeGain(c.key, 0);
      c.amountB = c.loop || !layered ? c.amount : c.full * fadeGain(c.key, 1);
      r.held = c.index < 0 ? c.held : 0;
      r.heldB = c.index < 0 ? c.heldB : 0;
      r.slot = c.slot;
      r.amount = c.amount;
      r.amountB = c.amountB;
      r.unipolar = c.unipolar;
      routes_.push_back(r);
    }
    return routes_;
  }

  // sourceNow: a stepped source as one layer hears it - the value it last had
  // while notes were down, times where that layer's envelope has got to. Any
  // other source is its value.
  double sourceNow(const ModSource& source, int layer = 0) {
    const double target = source.value();
    if (mode_ == FadeMode::Off || !source.stepped) return target;
    auto found = stepFade_.find(source.id);
    if (found == stepFade_.end()) {
      Stepped st;
      st.last = target;
      st.strikes = strikes_;
      for (int l = 0; l < 2; l++) {
        st.values[static_cast<std::size_t>(l)] = still(target, l);
        st.gates[static_cast<std::size_t>(l)] = { target != 0, -kInf, 0, l };
      }
      found = stepFade_.emplace(source.id, st).first;
    }
    Stepped& st = found->second;
    if (target != st.last) {
      const bool opens = st.last == 0, closes = target == 0;
      for (int l = 0; l < 2; l++) {
        Ramp& value = st.values[static_cast<std::size_t>(l)];
        if (opens) { value = still(target, l); gateSet(st.gates[static_cast<std::size_t>(l)], true); }
        else if (closes) { value = still(rampAt(value, now_), l); gateSet(st.gates[static_cast<std::size_t>(l)], false); }
        else {
          const bool arriving = std::fabs(target) > std::fabs(rampAt(value, now_));
          if (arriving ? fadesIn() : fadesOut()) rampTo(value, target, arriving);
          else value = still(target, l);
        }
      }
      st.last = target;
    }
    for (int l = 0; l < 2; l++) {
      const auto k = static_cast<std::size_t>(l);
      if (strikes_[k] == st.strikes[k]) continue;
      st.strikes[k] = strikes_[k];
      if (envs_[k].restart && target != 0) gateSet(st.gates[k], true);
    }
    const auto k = static_cast<std::size_t>(layer);
    return rampAt(st.values[k], now_) * gatePhase(st.gates[k]).level;
  }

 private:
  static constexpr double kInf = std::numeric_limits<double>::infinity();
  // FADE_LIMITS
  static constexpr double kFadeMin = 0.05, kFadeMax = 10, kDelayMax = 5, kBendMin = 0.1, kBendMax = 0.9;

  struct Ramp { double from = 0, to = 0, at = -kInf; bool arriving = true; int layer = 0; };
  struct Gate { bool on = false; double at = -kInf, from = 0; int layer = 0; };
  struct Phase { double level; };
  struct Gain { std::string key; std::array<Ramp, 2> ramps; Routing routing; };
  struct Stepped {
    double last = 0;
    std::array<int, 2> strikes { 0, 0 };
    std::array<Ramp, 2> values;
    std::array<Gate, 2> gates;
  };
  struct LoopPart { const ModSource* source; std::string key; double amount; bool unipolar; };
  struct Compiled {
    int index = -1;
    const ModSource* source = nullptr;
    std::vector<LoopPart> parts;  // the loop's routes into one slot, as one
    bool loop = false;
    double held = 0, heldB = 0;
    int slot = 0;
    std::string key;
    double full = 0, amount = 0, amountB = 0;
    bool unipolar = false;
  };

  static bool isSpace(char c) { return c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == '\f' || c == '\v'; }
  // The page's /-?[\d.]+/ for the depth.
  static bool isAmount(std::string_view s) {
    if (!s.empty() && s.front() == '-') s.remove_prefix(1);
    if (s.empty()) return false;
    for (const char c : s) if (!(c == '.' || (c >= '0' && c <= '9'))) return false;
    return true;
  }

  const ModSource* source(const std::string& id) const {
    const auto at = sources_.find(id);
    return at == sources_.end() ? nullptr : at->second;
  }
  const ModDest* dest(const std::string& id) const {
    const auto at = destIndex_.find(id);
    return at == destIndex_.end() ? nullptr : &dests_[at->second];
  }
  bool fadesIn() const { return mode_ == FadeMode::In || mode_ == FadeMode::Both; }
  bool fadesOut() const { return mode_ == FadeMode::Out || mode_ == FadeMode::Both; }
  bool inSetup(const std::string& key) const {
    for (const auto& r : routings_) if (r.key() == key) return true;
    return false;
  }
  const Gain* gain(const std::string& key) const {
    for (const auto& g : gains_) if (g.key == key) return &g;
    return nullptr;
  }

  // The ramps and gates of the page's fades, with the time handed in.
  static Ramp still(double value, int layer) { return { value, value, -kInf, true, layer }; }
  double rampMs(const Ramp& ramp) const {
    const FadeEnvelope& env = envs_[static_cast<std::size_t>(ramp.layer)];
    return (ramp.arriving ? env.attack : env.release) * 1000;
  }
  double rampAt(const Ramp& ramp, double now) const {
    const FadeEnvelope& env = envs_[static_cast<std::size_t>(ramp.layer)];
    const double t = (now - ramp.at) / rampMs(ramp);
    return ramp.from + (ramp.to - ramp.from) * fadeTravel(t, ramp.arriving ? env.attackMid : env.releaseMid);
  }
  bool rampDone(const Ramp& ramp, double now) const { return now - ramp.at >= rampMs(ramp); }
  void rampTo(Ramp& ramp, double to, bool arriving) {
    ramp.from = rampAt(ramp, now_);
    ramp.to = to; ramp.arriving = arriving; ramp.at = now_;
  }
  Phase gatePhase(const Gate& gate) const {
    const FadeEnvelope& env = envs_[static_cast<std::size_t>(gate.layer)];
    if (!std::isfinite(now_ - gate.at)) return { gate.on ? env.sustain : 0 };
    if (!gate.on) {
      const double t = (now_ - gate.at) / (env.release * 1000);
      if (!fadesOut() || t >= 1) return { 0 };
      return { gate.from * (1 - fadeTravel(t, env.releaseMid)) };
    }
    if (!fadesIn()) return { env.sustain };
    double ms = now_ - gate.at;
    const double wait = env.delay * 1000, rise = env.attack * 1000, fall = env.decay * 1000;
    if (ms < wait) return { gate.from };
    ms -= wait;
    double start = gate.from;
    // Round again from the sustain level, once the first attack and decay are done.
    if (env.loop && ms >= rise + fall) { ms = std::fmod(ms, rise + fall); start = env.sustain; }
    if (ms < rise) return { start + (1 - start) * fadeTravel(ms / rise, env.attackMid) };
    ms -= rise;
    if (ms < fall) return { 1 + (env.sustain - 1) * fadeTravel(ms / fall, env.decayMid) };
    return { env.sustain };
  }
  void gateSet(Gate& gate, bool on) {
    gate.from = gatePhase(gate).level;
    gate.on = on; gate.at = now_;
  }

  // fadeStep: each pair in the setup towards one, each ghost towards nought;
  // a ghost arrived on both layers is forgotten and the routes recompiled.
  void fadeStep() {
    if (mode_ == FadeMode::Off) return;
    for (const auto& r : routings_) {
      const std::string key = r.key();
      Gain* entry = nullptr;
      for (auto& g : gains_) if (g.key == key) { entry = &g; break; }
      if (!entry) { gains_.push_back({ key, { still(0, 0), still(0, 1) }, r }); entry = &gains_.back(); }
      entry->routing = r;
      for (auto& ramp : entry->ramps) {
        if (ramp.to == 1) continue;
        if (fadesIn()) rampTo(ramp, 1, true);
        else ramp = still(1, ramp.layer);
      }
    }
    for (std::size_t i = 0; i < gains_.size();) {
      Gain& g = gains_[i];
      if (inSetup(g.key)) { i++; continue; }
      if (!fadesOut()) { gains_.erase(gains_.begin() + static_cast<std::ptrdiff_t>(i)); dirty_ = true; continue; }
      for (auto& ramp : g.ramps) if (ramp.to != 0) rampTo(ramp, 0, false);
      if (rampDone(g.ramps[0], now_) && rampDone(g.ramps[1], now_)) {
        gains_.erase(gains_.begin() + static_cast<std::ptrdiff_t>(i));
        dirty_ = true;
        continue;
      }
      i++;
    }
  }

  // fireEvents: an event routing fires once for each new count its source
  // reaches, and never for the count it found when it was made.
  void fireEvents() {
    for (const auto& r : routings_) {
      const ModDest* d = dest(r.destId);
      if (!d || d->kind != DestKind::Event) continue;
      const ModSource* s = source(r.sourceId);
      if (!s || !s->event) continue;
      const int now = s->count();
      const auto seen = eventSeen_.find(r.serial);
      const bool fresh = seen == eventSeen_.end();
      const int was = fresh ? 0 : seen->second;
      eventSeen_[r.serial] = now;
      if (fresh || was == now) continue;
      if (r.amount != 0 && routingAllowed(s, d) && d->fire) d->fire(r.amount);
    }
  }

  // The picture's destinations, summed and written as offsets: everything the
  // loop pushes into one bounded as one, and the value kept to its range.
  void applyVisual() {
    const std::vector<Routing>& list = heard();
    for (const auto& d : dests_) {
      if (d.kind != DestKind::Visual) continue;
      double sum = 0, loop = 0;
      for (const auto& r : list) {
        if (r.destId != d.id) continue;
        const ModSource* s = source(r.sourceId);
        if (s && routingAllowed(s, &d)) {
          const double push = sourceNow(*s) * routingAmount(s, r.amount) * fadeGain(r.key());
          if (s->fromPicture) loop += push; else sum += push;
        }
      }
      sum += clampLoop(loop);
      const double base = d.base ? d.base() : 0;
      const double want = std::fmax(d.min, std::fmin(d.max, base + sum * d.span));
      if (d.set) d.set(want - base);
    }
  }

  // compileRoutes: the generator's routes, once per change. A routing whose
  // source or destination is not registered is skipped, not dropped.
  void compile() {
    compiled_.clear();
    std::vector<std::pair<int, std::vector<LoopPart>>> loopBySlot;
    const std::vector<Routing> list = heard();
    for (const auto& r : list) {
      const ModSource* s = source(r.sourceId);
      const ModDest* d = dest(r.destId);
      if (!s || !d) continue;
      if (d->kind != DestKind::Audio) continue;
      if (!routingAllowed(s, d)) continue;
      if (s->fromPicture) {
        auto at = std::find_if(loopBySlot.begin(), loopBySlot.end(), [&](const auto& e) { return e.first == d->slot; });
        if (at == loopBySlot.end()) { loopBySlot.push_back({ d->slot, {} }); at = loopBySlot.end() - 1; }
        at->second.push_back({ s, r.key(), routingAmount(s, r.amount), d->unipolar });
        continue;
      }
      const double amount = routingAmount(s, r.amount);
      Compiled c;
      c.index = s->index; c.source = s; c.slot = d->slot; c.key = r.key();
      c.full = amount; c.amount = amount; c.unipolar = d->unipolar;
      compiled_.push_back(std::move(c));
    }
    // The loop's routes into one slot, combined before they cross into the
    // per-sample loop, so their total is bounded as a picture destination's is.
    for (auto& [at, parts] : loopBySlot) {
      Compiled c;
      c.slot = at; c.full = 1; c.amount = 1; c.loop = true;
      c.parts = std::move(parts);
      compiled_.push_back(std::move(c));
    }
    dirty_ = false;
  }
  double loopValue(const Compiled& c) const {
    double total = 0;
    for (const auto& part : c.parts) {
      const double v = part.source->value(), amount = part.amount * fadeGain(part.key);
      total += part.unipolar ? amount * (1 - v) / 2 : amount * v;
    }
    return clampLoop(total);
  }

  std::map<std::string, ModSource*> sources_;
  std::vector<ModDest> dests_;
  std::map<std::string, std::size_t> destIndex_;
  std::vector<Routing> routings_;
  long serial_ = 0;
  FadeMode mode_ = FadeMode::Off;
  std::array<FadeEnvelope, 2> envs_ {};
  std::vector<Gain> gains_;  // in the order the page's Map has them
  std::map<std::string, Stepped> stepFade_;
  std::map<long, int> eventSeen_;
  std::vector<Compiled> compiled_;
  std::vector<Route> routes_;
  mutable std::vector<Routing> heard_;
  std::array<int, 2> strikes_ { 0, 0 };
  bool layered_ = false;
  bool dirty_ = true;
  double now_ = 0;
};

}  // namespace scope
