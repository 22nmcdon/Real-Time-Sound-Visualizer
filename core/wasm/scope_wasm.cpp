// The core in WebAssembly (stage 5): the generator behind a plain C interface
// the page's worklet calls, so the worklet can run the compiled core in place
// of `makeGeneratorCore`. Built by core/wasm/build.py with clang's own wasm32
// target and the WASI libc, with no runtime of anyone else's around it: the
// page instantiates the bare module and supplies the three WASI calls the
// C library's abort path imports.
//
// The interface is the JavaScript core's, spelt for a boundary that passes
// only numbers. A setting goes over as its field's name and its value as JSON
// in a scratch buffer, and is read by the core's own `jsonParse`; JavaScript
// writes a number in its shortest round-trip form, so nothing is lost on the
// way. The routes go over as seven doubles each. The oscillators are the
// worklet's objects, which are the truth on that side: their every number is
// written in before a block and read back out after it, so a restart the
// worklet makes by setting a phase to nought is simply the phase.
//
// Exceptions are off and the C++ library's `operator new` would throw, which
// a module without an exception runtime cannot link; allocation failure here
// is the end of the module, as it is of the worklet.

#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <memory>
#include <string>
#include <vector>

#include "scope/generator.h"
#include "scope/picture.h"
#include "scope/json.h"
#include "scope/text.h"

void* operator new(std::size_t n) {
  void* p = std::malloc(n ? n : 1);
  if (!p) std::abort();
  return p;
}
void* operator new[](std::size_t n) { return operator new(n); }
void operator delete(void* p) noexcept { std::free(p); }
void operator delete[](void* p) noexcept { std::free(p); }
void operator delete(void* p, std::size_t) noexcept { std::free(p); }
void operator delete[](void* p, std::size_t) noexcept { std::free(p); }
// And what the library's string conversions reach for to throw, which here
// can only end the module.
extern "C" void* __cxa_allocate_exception(std::size_t) { std::abort(); }
extern "C" void __cxa_throw(void*, void*, void (*)(void*)) { std::abort(); }

#define EXPORT(name) extern "C" __attribute__((export_name(#name)))

namespace {

std::vector<scope::Lfo> lfos;
std::unique_ptr<scope::Generator> core;
std::vector<char> text;        // a field's name, then its value as JSON
std::vector<double> numbers;   // the routes, seven to one
std::vector<float> lanes;      // seven of a block each: the picture's pair, the heard pair, B's pair, the input
std::size_t laneLength = 0;
std::vector<double> state;     // what the worklet sends back with its samples

// The picture's own sources (stage 5d), for the page's main thread: the
// phosphor grid the renderer's walks deposit into, and the photocell, meter
// and slewed values read from it. Their own, beside any generator.
std::unique_ptr<scope::Phosphor> phosphor;
std::unique_ptr<scope::PictureSources> pictures;
std::vector<float> pairLanes;  // the drawn pair, left then right
scope::PairShape pairShape;
std::vector<double> pictureState;

std::vector<double> numberList(const scope::Json& v) {
  std::vector<double> out;
  if (v.type == scope::Json::Type::Array) for (const auto& x : v.a) out.push_back(x.type == scope::Json::Type::Number ? x.n : 0);
  return out;
}

double numberAt(const scope::Json& v, std::string_view key, double otherwise) {
  const scope::Json* x = v.type == scope::Json::Type::Object ? v.get(key) : nullptr;
  return x && x->type == scope::Json::Type::Number ? x->n : otherwise;
}

scope::CycleTables tablesOf(const scope::Json& v) {
  scope::CycleTables t;
  t.most = numberAt(v, "most", 0);
  if (const scope::Json* levels = v.type == scope::Json::Type::Object ? v.get("levels") : nullptr) {
    if (levels->type == scope::Json::Type::Array) for (const auto& level : levels->a) t.levels.push_back(numberList(level));
  }
  return t;
}

// The tables and the path as numbers rather than JSON: a wavetable bank is a
// megabyte and more as text, and the page sends it with every preset, so the
// text cost a tenth of a second a preset that a copy does not. A table is its
// harmonic ceiling, how many levels, then each level's length and samples; a
// path is the length of xy, xy, the length of at, at.
struct Reader {
  const double* at;
  const double* end;
  double next() { return at < end ? *at++ : 0; }
  std::size_t count() { const double n = next(); return n > 0 ? static_cast<std::size_t>(n) : 0; }
  std::vector<double> list() {
    std::vector<double> out(std::min(count(), static_cast<std::size_t>(end - at)));
    for (auto& v : out) v = next();
    return out;
  }
  scope::CycleTables tables() {
    scope::CycleTables t;
    t.most = next();
    for (std::size_t k = count(); k > 0 && at < end; k--) t.levels.push_back(list());
    return t;
  }
};

}  // namespace

// A scratch buffer for text in, at least `bytes` long; where it lives may move
// when it grows, so the worklet asks for it each time.
EXPORT(scope_text) char* scopeText(int bytes) {
  if (text.size() < static_cast<std::size_t>(bytes)) text.resize(static_cast<std::size_t>(bytes));
  return text.data();
}
EXPORT(scope_numbers) double* scopeNumbers(int count) {
  if (numbers.size() < static_cast<std::size_t>(count)) numbers.resize(static_cast<std::size_t>(count));
  return numbers.data();
}

EXPORT(scope_make) void scopeMake(double rate, int slots, int lfoCount, unsigned seed) {
  lfos.assign(static_cast<std::size_t>(lfoCount), scope::Lfo {});
  core = std::make_unique<scope::Generator>(rate, slots, lfos, seed);
}

// set(field, value, layer): the field's name in the first `fieldBytes` of the
// text, its value as JSON in the `valueBytes` after. Returns 0 when the value
// was not JSON at all.
EXPORT(scope_set) int scopeSet(int fieldBytes, int valueBytes, int layer) {
  const std::string field(text.data(), static_cast<std::size_t>(fieldBytes));
  const auto parsed = scope::jsonParse(scope::utf8To16(std::string_view(text.data() + fieldBytes, static_cast<std::size_t>(valueBytes))));
  if (!parsed) return 0;
  const scope::Json& v = *parsed;
  using T = scope::Json::Type;
  if (field == "voices") {
    if (v.type == T::Null) { core->setVoices(nullptr, layer); return 1; }
    std::vector<scope::NoteWant> list;
    if (v.type == T::Array) {
      for (const auto& n : v.a) {
        scope::NoteWant w;
        w.note = static_cast<int>(numberAt(n, "note", 60));
        w.freq = numberAt(n, "freq", 261.63);
        w.velocity = numberAt(n, "velocity", 1);
        const scope::Json* role = n.type == T::Object ? n.get("role") : nullptr;
        if (role && role->type == T::String) w.role = scope::utf16To8(role->s);
        list.push_back(std::move(w));
      }
    }
    core->setVoices(&list, layer);
    return 1;
  }
  if (field == "bars") { core->setBars(numberList(v), layer); return 1; }
  if (field == "spin") {
    const auto s = numberList(v);
    if (s.size() == 3) core->setSpin({ s[0], s[1], s[2] });
    return 1;
  }
  if (field == "cycle") {
    core->setCycle(v.type == T::Object ? std::make_shared<scope::CycleTables>(tablesOf(v)) : nullptr);
    return 1;
  }
  if (field == "wavetable") {
    if (v.type != T::Array) { core->setWavetable(nullptr); return 1; }
    auto bank = std::make_shared<std::vector<scope::CycleTables>>();
    for (const auto& t : v.a) bank->push_back(tablesOf(t));
    core->setWavetable(bank);
    return 1;
  }
  if (field == "figPath") {
    if (v.type != T::Object) { core->setFigPath(nullptr); return 1; }
    auto path = std::make_shared<scope::FigurePath>();
    if (const scope::Json* xy = v.get("xy")) path->xy = numberList(*xy);
    if (const scope::Json* at = v.get("at")) path->at = numberList(*at);
    core->setFigPath(path);
    return 1;
  }
  if (v.type == T::Number) core->set(field, v.n, layer);
  else if (v.type == T::Bool) core->set(field, v.b ? 1.0 : 0.0, layer);
  else if (v.type == T::String) core->set(field, std::string_view(scope::utf16To8(v.s)), layer);
  return 1;
}

// cycle, wavetable or figPath (`which` 0, 1, 2) from the first `count` of the
// numbers buffer, in the shapes above; a count of nought is none.
EXPORT(scope_tables) void scopeTables(int which, int count) {
  Reader r { numbers.data(), numbers.data() + count };
  if (which == 0) {
    core->setCycle(count ? std::make_shared<scope::CycleTables>(r.tables()) : nullptr);
  } else if (which == 1) {
    if (!count) { core->setWavetable(nullptr); return; }
    auto bank = std::make_shared<std::vector<scope::CycleTables>>();
    for (std::size_t k = r.count(); k > 0 && r.at < r.end; k--) bank->push_back(r.tables());
    core->setWavetable(bank);
  } else {
    if (!count) { core->setFigPath(nullptr); return; }
    auto path = std::make_shared<scope::FigurePath>();
    path->xy = r.list();
    path->at = r.list();
    core->setFigPath(path);
  }
}

// setRoutes: `count` routes, seven numbers each in the numbers buffer - index
// (below nought for a held value), held, held on B, slot, amount, amount on B,
// unipolar.
EXPORT(scope_routes) void scopeRoutes(int count) {
  std::vector<scope::Route> list;
  for (int i = 0; i < count; i++) {
    const double* r = numbers.data() + 7 * i;
    scope::Route route;
    route.index = static_cast<int>(r[0]);
    route.held = r[1]; route.heldB = r[2]; route.slot = static_cast<int>(r[3]);
    route.amount = r[4]; route.amountB = r[5]; route.unipolar = r[6] != 0;
    list.push_back(route);
  }
  core->setRoutes(list);
}

EXPORT(scope_gate) void scopeGate(int open, double velocity) { core->gate(open != 0, velocity); }
EXPORT(scope_gated) void scopeGated(int on) { core->setGated(on != 0); }
EXPORT(scope_kick) void scopeKick(double amount) { core->kick(amount); }
EXPORT(scope_strike) void scopeStrike(double hz, double velocity) { core->strike(hz, velocity); }
EXPORT(scope_reswing) void scopeReswing() { core->reswing(); }

// An oscillator as the worklet holds it, written in before a block; its
// shape by name in the text, when it has changed.
EXPORT(scope_lfo) void scopeLfo(int i, double rate, double depth, double phase, double held, double value) {
  scope::Lfo& l = lfos[static_cast<std::size_t>(i)];
  l.rate = rate; l.depth = depth; l.phase = phase; l.held = held; l.value = value;
}
EXPORT(scope_lfo_shape) void scopeLfoShape(int i, int bytes) {
  lfos[static_cast<std::size_t>(i)].setShape(std::string_view(text.data(), static_cast<std::size_t>(bytes)));
}

// The lanes for a block of `n`: the picture's pair, the heard pair, B's pair,
// and the input, `n` floats each, in that order.
EXPORT(scope_lanes) float* scopeLanes(int n) {
  laneLength = static_cast<std::size_t>(n);
  if (lanes.size() < 7 * laneLength) lanes.resize(7 * laneLength);
  return lanes.data();
}

// `given` says which the caller has: 1 an input, 2 the heard pair, 4 B's
// pair. One it has not got is passed as none, as the JavaScript core is
// passed null - the main thread draws without the heard pair, and the rack's
// lane without B's.
EXPORT(scope_block) void scopeBlock(int n, int given) {
  float* l = lanes.data();
  const std::size_t m = laneLength;
  const bool heard = given & 2, pairB = given & 4;
  core->setInput(given & 1 ? l + 6 * m : nullptr, n);
  core->block(l, l + m, n, heard ? l + 2 * m : nullptr, heard ? l + 3 * m : nullptr,
              pairB ? l + 4 * m : nullptr, pairB ? l + 5 * m : nullptr);
}

// A live input's pair through the plane, the effects worklet's call: the
// input in the first two lanes, the result in the next two.
EXPORT(scope_effect) void scopeEffect(int n) {
  float* l = lanes.data();
  const std::size_t m = laneLength;
  core->effect(l, l + m, l + 2 * m, l + 3 * m, n);
}

// --- the picture's own sources (5d) -----------------------------------------

EXPORT(picture_make) void pictureMake() {
  phosphor = std::make_unique<scope::Phosphor>();
  pictures = std::make_unique<scope::PictureSources>();
}
EXPORT(picture_fade) void pictureFade(double persistence, int wipe) { phosphor->fade(persistence, wipe != 0); }
EXPORT(picture_blank) void pictureBlank() { phosphor->blank(); }
EXPORT(picture_segment) void pictureSegment(double px, double py, double pw, double ph, double x0, double y0, double x1,
                                            double y1, double level) {
  phosphor->segment(scope::Plot { px, py, pw, ph }, x0, y0, x1, y1, level);
}
// A polyline from the numbers buffer: `count` xs, then `count` ys, then, when
// `hasSteps`, the beam's `count` steps.
EXPORT(picture_deposit) void pictureDeposit(double px, double py, double pw, double ph, int count, int hasSteps) {
  const std::size_t n = static_cast<std::size_t>(count);
  std::vector<int> steps;
  if (hasSteps) {
    steps.resize(n);
    for (std::size_t i = 0; i < n; i++) steps[i] = static_cast<int>(numbers[2 * n + i]);
  }
  phosphor->deposit(scope::Plot { px, py, pw, ph }, numbers.data(), numbers.data() + n, n, hasSteps ? steps.data() : nullptr);
}
EXPORT(picture_read) double pictureRead(double u, double v) { return phosphor->read(u, v); }
EXPORT(picture_cells) float* pictureCells() { return phosphor->cells(); }
EXPORT(picture_lanes) float* pictureLanes(int n) {
  if (pairLanes.size() < 2 * static_cast<std::size_t>(n)) pairLanes.resize(2 * static_cast<std::size_t>(n));
  return pairLanes.data();
}
// The drawn pair's shape from the `n` samples a lane in the picture lanes,
// turned, scaled and offset as the page draws them.
EXPORT(picture_shape) void pictureShape(int n, double gx, double gy, double ox, double oy, double spin, double zoom) {
  const std::size_t m = static_cast<std::size_t>(n);
  pairShape = scope::shapeOfPair(pairLanes.data(), pairLanes.data() + m, m, gx, gy, ox, oy, spin, zoom);
}
// photoStep, from the page's photocell as it stands: on, where, and the value
// it last slewed to.
EXPORT(picture_photo) void picturePhoto(int on, double u, double v, double value, double elapsed, int spect) {
  pictures->on = on != 0;
  pictures->u = u; pictures->v = v;
  pictures->carry(value, pictures->values());
  pictures->photoStep(*phosphor, elapsed, spect != 0);
}
// pictureStep, from the page's slewed values as they stand, with the shape
// last made or none.
EXPORT(picture_step) void pictureStep(int on, int hasShape, double elapsed, int spect, double limiting, double round,
                                      double cover, double change, double novelty, double signedArea, double edge,
                                      double bored) {
  pictures->on = on != 0;
  pictures->carry(pictures->photo(), scope::PictureValues { round, cover, change, novelty, signedArea, edge, bored });
  pictures->pictureStep(*phosphor, hasShape ? &pairShape : nullptr, elapsed, spect != 0, limiting);
}
EXPORT(picture_reset_meter) void pictureResetMeter() { pictures->resetMeter(); }
// The photocell's value and reading, the slewed values and their targets,
// boredom's level, the meter's readings, its depth and verdict (nought
// listening, one running away, two settled, three cycling, four wandering),
// the fades so far, the roundness, and the last shape.
EXPORT(picture_state) double* pictureStateOut() {
  const auto& v = pictures->values();
  const auto& r = pictures->raw();
  const auto& m = pictures->meter();
  const std::string said = m.verdict();
  const double verdict = said == "running away" ? 1 : said == "settled" ? 2 : said == "cycling" ? 3 : said == "wandering" ? 4 : 0;
  pictureState.assign({ pictures->photo(), pictures->photoRaw(), v.round, v.cover, v.change, v.novelty, v.signed_, v.edge,
                        v.bored, r.round, r.cover, r.change, r.novelty, r.signed_, r.edge, r.bored, pictures->bored(),
                        m.coverage(), m.lit(), m.change(), m.novelty(), static_cast<double>(m.depth()), verdict,
                        static_cast<double>(phosphor->frames()), phosphor->moments().roundness(), pairShape.signed_,
                        pairShape.edge });
  return pictureState.data();
}

// What goes back with the samples: the envelope, the crossings' counts, the
// budget, the drawing's readings, the pitch layer A last played, the kick on
// the spin and the swing's envelope, and each oscillator's phase, held value
// and value.
EXPORT(scope_state) double* scopeState() {
  const auto c = core->crossings();
  const auto& b = core->budget();
  const auto d = core->drawing();
  state.assign({ core->envelope(), static_cast<double>(c[0]), static_cast<double>(c[1]), b.units,
                 static_cast<double>(b.asked[0]), static_cast<double>(b.asked[1]), static_cast<double>(b.unison[0]),
                 static_cast<double>(b.unison[1]), static_cast<double>(b.askedFactor), static_cast<double>(b.factor),
                 static_cast<double>(b.silenced), scope::Generator::kVoiceBudget, d.swing, d.pendulum, d.turn[0], d.turn[1],
                 d.turn[2], d.facing, core->pitch(), core->spinKick(), core->swingLevel() });
  for (const auto& l : lfos) state.insert(state.end(), { l.phase, l.held, l.value });
  return state.data();
}
