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

#include <cstdint>
#include <cstdlib>
#include <memory>
#include <string>
#include <vector>

#include "scope/generator.h"
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

EXPORT(scope_block) void scopeBlock(int n, int hasInput) {
  float* l = lanes.data();
  const std::size_t m = laneLength;
  core->setInput(hasInput ? l + 6 * m : nullptr, n);
  core->block(l, l + m, n, l + 2 * m, l + 3 * m, l + 4 * m, l + 5 * m);
}

// A live input's pair through the plane, the effects worklet's call: the
// input in the first two lanes, the result in the next two.
EXPORT(scope_effect) void scopeEffect(int n) {
  float* l = lanes.data();
  const std::size_t m = laneLength;
  core->effect(l, l + m, l + 2 * m, l + 3 * m, n);
}

// What goes back with the samples: the envelope, the crossings' counts, the
// budget, the drawing's readings, and each oscillator's phase, held value and
// value.
EXPORT(scope_state) double* scopeState() {
  const auto c = core->crossings();
  const auto& b = core->budget();
  const auto d = core->drawing();
  state.assign({ core->envelope(), static_cast<double>(c[0]), static_cast<double>(c[1]), b.units,
                 static_cast<double>(b.asked[0]), static_cast<double>(b.asked[1]), static_cast<double>(b.unison[0]),
                 static_cast<double>(b.unison[1]), static_cast<double>(b.askedFactor), static_cast<double>(b.factor),
                 static_cast<double>(b.silenced), scope::Generator::kVoiceBudget, d.swing, d.pendulum, d.turn[0], d.turn[1],
                 d.turn[2], d.facing });
  for (const auto& l : lfos) state.insert(state.end(), { l.phase, l.held, l.value });
  return state.data();
}
