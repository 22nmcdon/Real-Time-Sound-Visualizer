// What a harness can read off the instrument (scope/instrument.h) as it
// plays, each as one line of text: instrument_cpp's native-only readings,
// kept here so render_cpp, which grew from response_cpp and instrument_cpp
// (stage 5, step 3, batch 5), prints them by the same code and not a copy.
// Each was written for a piece of core/tests/pieces/, and its comment says
// which; instrument_cpp's own header lists them as script commands.
//
// None allocates on the instrument's side or moves it, but for `hold`, which
// puts a layer's hold in as the page's tests write `pictureStage`, and
// `resetMeter`, the page's `pictureMeter.reset()`.
#pragma once

#include <cmath>
#include <cstdio>
#include <string>

#include "scope/instrument.h"

namespace reads {

// The two sums a grid is printed by: weighted by place, so where a figure lies
// shows, and squared.
template <class Grid>
inline void sums(const Grid& g, double& a1, double& a2) {
  a1 = 0; a2 = 0;
  for (std::size_t i = 0; i < g.size(); ++i) { a1 += g[i] * static_cast<double>(i + 1); a2 += static_cast<double>(g[i]) * g[i]; }
}

/* ["grid"]: the grid the instrument draws for itself, by two sums. Native
   only - the compiled instrument does not hand its grid out - so a script
   with this in it is not one the two are compared on. */
inline void grid(const scope::Instrument& instrument) {
  double a1, a2;
  sums(instrument.picture().phosphor().grid(), a1, a2);
  std::printf("grid %.17g %.17g\n", a1, a2);
}

// ["lgrid"]: each layer's own grid by the same two sums (P7b: where a note's
// strike lands in a split), A's then B's.
inline void lgrid(const scope::Instrument& instrument) {
  std::printf("lgrid");
  for (int l = 0; l < 2; l++) {
    double a1, a2;
    sums(instrument.layerPictures().layerGrid(l).grid(), a1, a2);
    std::printf(" %.17g %.17g", a1, a2);
  }
  std::printf("\n");
}

// ["hearing"]: how many windows the hearing has analysed, and its brightness.
inline void hearing(const scope::Instrument& instrument) {
  std::printf("hearing %ld %.17g\n", instrument.hearing().runs, instrument.hearing().bright);
}

/* ["hold", layer, value]: a layer's picture stage's hold put in, as the
   page's tests write pictureStage - so a layer's hold can differ from the
   other's and from the shared stage's, which a harness reading what each
   layer is handed needs. Its reads are kept. */
inline void hold(const scope::Instrument& instrument, int layer, double value) {
  auto& stage = const_cast<scope::LayerPictures&>(instrument.layerPictures()).stage(layer);
  stage.put(stage.glow(), stage.motion(), stage.memory(), value);
}

/* ["scan"]: Scan's reading (P7a): when the freeze after a setup ends, in
   milliseconds of audio, the hold each layer last sent, and whether each has
   a path; then what the last frame handed each layer against what is each
   layer's - its depth and the layer's, its hold, the shared stage's and its
   own picture's, and which grid (0 the screen, 1 and 2 A's and B's own) - and
   whether the layers draw a picture each. */
inline void scan(const scope::Instrument& instrument) {
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
}

/* ["reads"]: which pictures each layer's Scan read at the last frame (A as
   1, B as 2, nought for a layer not reading), each layer's depth, and whether
   the layers draw one each. core/tests/pieces/strike.py's (stage 5, step 3,
   batch 3), for a preset whose left hand reads the right hand's picture. */
inline void scanReads(const scope::Instrument& instrument) {
  const auto& scan = instrument.scan();
  std::printf("reads %d %d %.17g %.17g %d\n", scan.reads[0], scan.reads[1], instrument.generator().tone().scan,
              instrument.generator().toneB().scan, instrument.layerPictures().live() ? 1 : 0);
}

/* ["tone"]: what the generator holds of the hands' tone - frequency,
   interval, octaves, just, vibrato and bend - then the keyboard's held notes,
   the voices each layer is sounding (note numbers, gone ones left out), the
   note envelope, and the automatic lag's lock (- for none). The pieces'
   (batch 4), so the keyboard's rows read the instrument the site plays rather
   than the page's mirror of it. */
inline void tone(const scope::Instrument& instrument) {
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
}

/* ["routed"]: each routing the instrument's matrix holds, as `source>dest`,
   whether that source is registered (1 or 0), its value, and how many of the
   routes handed to the generator are on that destination's slot (- for a
   destination that is not the generator's). The pieces' (batch 4), for
   performtest's "every routing reaches the generator, is still at rest, and
   moves when played". */
inline void routed(scope::Instrument& instrument) {
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
}

/* ["meter"]: the instrument's own picture meter - how much the last frame
   changed, its verdict, how much is lit and how new it is. The pieces'
   (batch 4): the page's `pictureMeter` on the default site is the face's
   second grid, not this one. */
inline void meter(const scope::Instrument& instrument) {
  const auto& m = instrument.picture().pictures().meter();
  std::printf("meter %.17g %s %.17g %.17g\n", m.change(), m.verdict().c_str(), m.lit(), m.novelty());
}

// The page's `pictureMeter.reset()`: the shared meter afresh, as a suite does at a run's start.
inline void resetMeter(const scope::Instrument& instrument) {
  const_cast<scope::PictureSources&>(instrument.picture().pictures()).resetMeter();
}

/* ["layers"]: each layer's picture (P6): whether live, the figures laid out,
   each layer's raw coverage, stage reads, hold and raw signed area, and the
   loop's routes as slot:held:heldB. */
inline void layers(const scope::Instrument& instrument) {
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
}

}  // namespace reads
