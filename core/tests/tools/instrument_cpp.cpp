// The instrument (scope/instrument.h) as the plugin plays it, natively,
// through the same script as instrument_js.mjs, which plays the compiled one
// through the page's wrapper. A line of the script is a JSON array:
//
//   ["make", rate, block, code]      made, and loaded with that setup code
//   ["slider", id, value]            a slider moved on the page
//   ["setup", code]                  a setup loaded on the page
//   ["control", id, value]           a menu or text box (text), a switch (true or false)
//   ["click", id] ["routings", text] ["fade", json]
//   ["midi", b0, b1?, b2?]           a message, for the top of the next block
//   ["feed", periodL?, periodR?]     an input from now on: a saw of periodL samples on the
//                                    left and a triangle of periodR on the right, at half
//                                    scale, by arithmetic alone so both sides make it to the
//                                    bit; one period is a mono input, none is no input
//   ["block", n, stride?]            n frames; every stride-th sample printed (1 when left out)
//   ["grid"]                         the instrument's own grid, by two sums (native only)
//   ["hearing"]                      how many windows the hearing has analysed, and its
//                                    brightness (native only)
//   ["hold", layer, value]           a layer's picture stage's hold put in (native only)
//   ["scan"]                         Scan's reading (P7a): when the freeze after a setup ends, in
//                                    milliseconds of audio, the hold each layer last sent, and
//                                    whether each has a path; then what the last frame handed
//                                    each layer against what is each layer's - its depth and the
//                                    layer's, its hold, the shared stage's and its own picture's,
//                                    and which grid (0 the screen, 1 and 2 A's and B's own) -
//                                    and whether the layers draw a picture each (native only)
//   ["reads"]                        which pictures each layer's Scan read last, the depths, and
//                                    whether the layers draw one each (native only)
//   ["tone"]                         the hands' tone, held notes, voices, envelope and lag lock (native only)
//   ["routed"]                       each routing: source registered, its value, routes on its slot (native only)
//   ["meter"]                        the picture meter's change, verdict, lit and novelty (native only)
//   ["layers"]                       each layer's picture (P6): whether live, the figures laid
//                                    out, each layer's raw coverage, stage reads, hold and raw
//                                    signed area, and
//                                    the loop's routes as slot:held:heldB (native only)
//
// `instrument_cpp --code NAME...` prints each preset's setup code instead, and
// `instrument_cpp --names` every preset's name.
//
// Out, a line each: `no` for a slider, setup or fade refused; for a block,
// `block` and its heard pair then the picture's six lanes, every sample; `out` and
// the MIDI it sent, if any; `state`, the host's count and the code, if the
// state changed.
#include <cmath>
#include <cstdio>
#include <fstream>
#include <string>
#include <vector>

#include "scope/instrument.h"
#include "scope/presets.h"

namespace {
std::string text(const scope::Json& v) { return v.type == scope::Json::Type::String ? scope::utf16To8(v.s) : std::string(); }
}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) { std::fprintf(stderr, "usage: instrument_cpp <script> | --code PRESET...\n"); return 2; }
  // Every preset's name, a line each, the generator's first.
  if (std::string(argv[1]) == "--names") {
    for (const char* kind : { "generator", "display" })
      for (const auto& preset : scope::presets()) if (preset.kind == kind) std::printf("%s\n", preset.name.c_str());
    return 0;
  }
  // The setup code of each preset named, a line each, for a script to load.
  if (std::string(argv[1]) == "--code") {
    for (int i = 2; i < argc; ++i) {
      const scope::Preset* preset = scope::findPreset(argv[i]);
      const auto code = preset ? scope::encodeSetup(preset->setup) : std::nullopt;
      std::printf("%s\n", code ? code->c_str() : "");
    }
    return 0;
  }
  std::ifstream file(argv[1]);
  scope::Instrument instrument;
  std::vector<std::uint8_t> midi;
  std::vector<std::size_t> lengths;
  std::vector<std::vector<int>> sent;
  double feedL = 0, feedR = 0;
  long long fed = 0;
  std::vector<float> inL, inR;
  instrument.hooks.midiOut = [&](const std::uint8_t* bytes, int length, int) { sent.emplace_back(bytes, bytes + length); };
  for (std::string line; std::getline(file, line);) {
    if (line.empty()) continue;
    const auto parsed = scope::jsonParse(scope::utf8To16(line));
    if (!parsed || parsed->type != scope::Json::Type::Array || parsed->a.empty()) { std::fprintf(stderr, "bad line\n"); return 2; }
    const auto& a = parsed->a;
    const std::string cmd = text(a[0]);
    const auto arg = [&](std::size_t i) -> const scope::Json& { static const scope::Json none; return i < a.size() ? a[i] : none; };
    if (cmd == "make") {
      const auto setup = scope::Instrument::setup(text(arg(3)));
      instrument.prepare(arg(1).n, static_cast<int>(arg(2).n), setup ? *setup->setup : scope::Json::object());
      if (!setup) std::printf("no\n");
    } else if (cmd == "slider") {
      const auto c = scope::Instrument::slider(text(arg(1)), arg(2).type == scope::Json::Type::String ? arg(2).s : u"");
      if (c) instrument.apply(*c); else std::printf("no\n");
    } else if (cmd == "setup") {
      const auto c = scope::Instrument::setup(text(arg(1)));
      if (c) instrument.apply(*c); else std::printf("no\n");
    } else if (cmd == "control") {
      instrument.apply(scope::Instrument::control(text(arg(1)), arg(2).type == scope::Json::Type::Bool ? arg(2) : scope::Json::string(arg(2).s)));
    } else if (cmd == "click") instrument.apply(scope::Instrument::click(text(arg(1))));
    else if (cmd == "routings") instrument.apply(scope::Instrument::routings(text(arg(1))));
    else if (cmd == "fade") {
      const auto c = scope::Instrument::fade(text(arg(1)));
      if (c) instrument.apply(*c); else std::printf("no\n");
    } else if (cmd == "midi") {
      for (std::size_t i = 1; i < a.size() && i < 4; ++i) midi.push_back(static_cast<std::uint8_t>(a[i].n));
      lengths.push_back(std::min<std::size_t>(a.size() - 1, 3));
    } else if (cmd == "feed") {
      feedL = a.size() > 1 ? a[1].n : 0;
      feedR = a.size() > 2 ? a[2].n : 0;
    } else if (cmd == "hearing") {
      std::printf("hearing %ld %.17g\n", instrument.hearing().runs, instrument.hearing().bright);
    } else if (cmd == "grid") {
      // The grid the instrument draws for itself, by two sums: weighted by
      // place, so where a figure lies shows, and squared. Native only - the
      // compiled instrument does not hand its grid out - so a script with
      // this in it is not one the two are compared on.
      const auto& g = instrument.picture().phosphor().grid();
      double a1 = 0, a2 = 0;
      for (std::size_t i = 0; i < g.size(); ++i) { a1 += g[i] * static_cast<double>(i + 1); a2 += static_cast<double>(g[i]) * g[i]; }
      std::printf("grid %.17g %.17g\n", a1, a2);
    } else if (cmd == "lgrid") {
      // Each layer's own grid by the same two sums (P7b: where a note's strike
      // lands in a split), A's then B's. Native only, as "grid" is.
      std::printf("lgrid");
      for (int l = 0; l < 2; l++) {
        const auto& g = instrument.layerPictures().layerGrid(l).grid();
        double a1 = 0, a2 = 0;
        for (std::size_t i = 0; i < g.size(); ++i) { a1 += g[i] * static_cast<double>(i + 1); a2 += static_cast<double>(g[i]) * g[i]; }
        std::printf(" %.17g %.17g", a1, a2);
      }
      std::printf("\n");
    } else if (cmd == "hold") {
      // ["hold", layer, value]: a layer's picture stage's hold put in, as the
      // page's tests write pictureStage - so a layer's hold can differ from
      // the other's and from the shared stage's, which a harness reading what
      // each layer is handed needs. Its reads are kept.
      auto& stage = const_cast<scope::LayerPictures&>(instrument.layerPictures()).stage(static_cast<int>(arg(1).n));
      stage.put(stage.glow(), stage.motion(), stage.memory(), arg(2).n);
    } else if (cmd == "scan") {
      const auto& scan = instrument.scan();
      std::printf("scan %.17g %.17g %.17g %d %d", scan.frozenUntil, scan.held[0], scan.held[1], scan.paths[0] ? 1 : 0,
                  scan.paths[1] ? 1 : 0);
      const auto& layers = instrument.layerPictures();
      const auto& pic = instrument.picture();
      for (int l = 0; l < 2; l++) {
        const auto& seen = scan.seen[static_cast<std::size_t>(l)];
        const int grid = seen.grid == pic.phosphor().grid().data() ? 0 : seen.grid == layers.layerGrid(0).grid().data() ? 1
                       : seen.grid == layers.layerGrid(1).grid().data() ? 2 : -1;
        const double depth = l == 1 ? instrument.generator().toneB().scan : instrument.generator().tone().scan;
        std::printf(" L%d %.17g %.17g %.17g %.17g %.17g %d", l, seen.depth, depth, seen.hold, pic.stage().hold(),
                    layers.stage(l).hold(), grid);
      }
      std::printf(" live %d\n", layers.live() ? 1 : 0);
    } else if (cmd == "reads") {
      // ["reads"]: which pictures each layer's Scan read at the last frame (A
      // as 1, B as 2, nought for a layer not reading), each layer's depth, and
      // whether the layers draw a picture each. Native only, and not
      // instrument_js's: core/tests/pieces/strike.py's (stage 5, step 3,
      // batch 3), for a preset whose left hand reads the right hand's picture.
      const auto& scan = instrument.scan();
      std::printf("reads %d %d %.17g %.17g %d\n", scan.reads[0], scan.reads[1], instrument.generator().tone().scan,
                  instrument.generator().toneB().scan, instrument.layerPictures().live() ? 1 : 0);
    } else if (cmd == "tone") {
      // ["tone"]: what the generator holds of the hands' tone - frequency,
      // interval, octaves, just, vibrato and bend - then the keyboard's held
      // notes, the voices each layer is sounding (note numbers, gone ones
      // left out), the note envelope, and the automatic lag's lock (- for
      // none). Native only, and not instrument_js's: the pieces' (stage 5,
      // step 3, batch 4), so the keyboard's rows read the instrument the
      // site plays rather than the page's mirror of it.
      const auto& t = instrument.tone();
      std::printf("tone %.17g %d %.17g %d %.17g %.17g notes", t.freq, t.interval, t.octaves, t.just ? 1 : 0, t.vibrato,
                  t.pitchBend);
      for (const auto& h : instrument.keyboard().notes()) std::printf(" %d", h.note);
      for (int l = 0; l < 2; l++) {
        std::printf(" %s", l ? "B" : "A");
        for (const auto& v : l ? instrument.generator().voicesB() : instrument.generator().voices())
          if (!v.gone) std::printf(" %d", v.note);
      }
      const auto& lock = instrument.view().capture.lagLock;
      std::printf(" env %.17g lag", instrument.generator().envelope());
      if (lock) std::printf(" %.17g\n", *lock); else std::printf(" -\n");
    } else if (cmd == "routed") {
      // ["routed"]: each routing the instrument's matrix holds, as
      // `source>dest`, whether that source is registered (1 or 0), its value,
      // and how many of the routes handed to the generator are on that
      // destination's slot (- for a destination that is not the generator's).
      // Native only: the pieces' (batch 4), for performtest's "every routing
      // reaches the generator, is still at rest, and moves when played".
      auto& m = instrument.matrix();
      std::printf("routed");
      for (const auto& r : m.routings()) {
        const scope::ModSource* s = m.source(r.sourceId);
        const scope::ModDest* d = m.dest(r.destId);
        std::printf(" %s>%s %d %.17g ", r.sourceId.c_str(), r.destId.c_str(), s ? 1 : 0, s ? s->value() : 0.0);
        if (!d || d->kind != scope::DestKind::Audio) { std::printf("-"); continue; }
        int on = 0;
        for (const auto& route : instrument.routes()) if (route.slot == d->slot && (route.amount != 0 || route.amountB != 0)) on++;
        std::printf("%d", on);
      }
      std::printf("\n");
    } else if (cmd == "meter") {
      // ["meter"]: the instrument's own picture meter - how much the last frame
      // changed, its verdict, how much is lit and how new it is. Native only,
      // and the pieces' (batch 4): the page's `pictureMeter` on the default
      // site is the face's second grid, not this one.
      const auto& m = instrument.picture().pictures().meter();
      std::printf("meter %.17g %s %.17g %.17g\n", m.change(), m.verdict().c_str(), m.lit(), m.novelty());
    } else if (cmd == "layers") {
      const auto& layers = instrument.layerPictures();
      std::printf("layers %d figures %zu", layers.live() ? 1 : 0, instrument.figures());
      for (int l = 0; l < 2; l++) {
        const auto& st = layers.stage(l);
        std::printf(" L%d %.17g %.17g %.17g %.17g %.17g %.17g", l, layers.pictures(l).raw().cover, st.glow(), st.motion(), st.memory(),
                    st.hold(), layers.pictures(l).raw().signed_);
      }
      std::printf(" shared %.17g %.17g %.17g %.17g routes", instrument.picture().stage().glow(), instrument.picture().stage().motion(),
                  instrument.picture().stage().memory(), instrument.picture().stage().hold());
      for (const auto& r : instrument.routes())
        if (r.index < 0) std::printf(" %d:%.17g:%.17g", r.slot, r.held, r.heldB);
      std::printf("\n");
    } else if (cmd == "block") {
      const std::size_t n = static_cast<std::size_t>(arg(1).n);
      inL.assign(n, 0.0f); inR.assign(n, 0.0f);
      for (std::size_t k = 0; k < n && feedL > 0; ++k, ++fed) {
        const double t = std::fmod(static_cast<double>(fed), feedL) / feedL;
        inL[k] = static_cast<float>(0.5 * (2 * t - 1));
        if (feedR > 0) {
          const double u = std::fmod(static_cast<double>(fed), feedR) / feedR;
          inR[k] = static_cast<float>(0.5 * (u < 0.5 ? 4 * u - 1 : 3 - 4 * u));
        }
      }
      const scope::Instrument::Input input { inL.data(), feedR > 0 ? inR.data() : nullptr };
      std::vector<float> lanes(8 * n);  // the heard pair, then the picture's six lanes
      std::vector<scope::Instrument::Event> events;
      std::size_t at = 0;
      for (const std::size_t length : lengths) { events.push_back({ 0, midi.data() + at, length }); at += length; }
      sent.clear();
      instrument.block(lanes.data(), lanes.data() + n, static_cast<int>(n), events.data(), events.size(), nullptr, nullptr, 0,
                       feedL > 0 ? &input : nullptr);
      for (int c = 0; c < scope::Instrument::kRingLanes; ++c)
        instrument.latestLane(c, lanes.data() + (2 + static_cast<std::size_t>(c)) * n, n);
      midi.clear(); lengths.clear();
      const std::size_t stride = arg(2).type == scope::Json::Type::Number && arg(2).n >= 1 ? static_cast<std::size_t>(arg(2).n) : 1;
      std::printf("block");
      for (std::size_t k = 0; k < lanes.size(); k += stride) std::printf(" %.9g", static_cast<double>(lanes[k]));
      std::printf("\n");
      if (!sent.empty()) {
        std::printf("out");
        for (const auto& m : sent) { for (const int b : m) std::printf(" %d", b); std::printf(" ;"); }
        std::printf("\n");
      }
      if (instrument.changed()) {
        std::printf("state %d %s\n", instrument.hostVersion(), instrument.stateCode().c_str());
        instrument.published();
      }
    } else { std::fprintf(stderr, "unknown command %s\n", cmd.c_str()); return 2; }
  }
  return 0;
}
