// The instrument rendered offline (stage 5, step 3, batch 5): scope/instrument.h
// as the plugin and the site play it, from a setup code, MIDI at its own
// moments, an input fed in as a host's input bus or the page's microphone
// hands it over, and the hands a player has, read at a stated interval of
// audio. Grown from response_cpp, whose run it still makes (`--response`,
// below) and which it replaced, and from instrument_cpp, whose script it
// speaks and whose native readings it prints by the same code
// (instrument_reads.h). No browser and no JavaScript, and no clock but the
// samples: a run is the same to the bit every time (core/tests/pieces/render.py
// proves it), where the same run on the page landed each frame, read and key
// wherever the browser's timing put them, in a loop that magnifies small
// differences.
//
//   render_cpp SCRIPT                               a script of JSON lines, below
//   render_cpp --response CODE PATCH EVENTS SECONDS response_cpp's run, to the byte
//   render_cpp --decode CODE                        the code as read: its Picture amounts
//   render_cpp --slots                              the generator's slot numbers by name
//
// A script is one JSON array a line, done in order. Time moves only by `to`;
// everything else happens at the sample the render has reached.
//
//   ["make", rate, code, patch?]     made at that rate, the setup code loaded with the
//                                    fields of `patch` (an object) laid over it, as the
//                                    host's state; a host block of 128 frames
//   ["slider", id, value] ["setup", code] ["control", id, value] ["click", id]
//   ["routings", text] ["fade", json]
//                                    a hand, as instrument_cpp's: what the page sends
//   ["midi", b0, b1?, b2?]           a message, at the sample the render has reached
//   ["to", seconds]                  render on to that moment (rounded to a sample)
//   ["input", "none"]                no input from now on
//   ["input", "file", path, ch]      from now on, the samples of a file of float32 (little-
//                                    endian), mono or two channels interleaved, read once
//                                    from its start; silence after its end
//   ["input", "sine", hz, amp, hzR?, ampR?]   a sine on the left (and one on the right)
//   ["input", "saw", periodL, periodR?]       instrument_cpp's feed, to the bit
//   ["every", seconds, name...]      from now on, the named readings each `seconds` of
//                                    audio, the first that long from now; ["every", 0] stops
//   ["read", name...]                the named readings now
//   ["reset", "meter"]               the picture meter afresh, the page's pictureMeter.reset()
//   ["hold", layer, value]           a layer's picture stage's hold put in
//   ["record", what, path]           from now on, into a file, float32: "heard" the heard
//                                    pair interleaved, "lanes" the picture's six ring lanes a
//                                    sample (kRingLanes), "grid" the shown grid at each reading that names
//                                    `griddump` (kPhosphorN squared values each), "prelimit"
//                                    the heard pair interleaved as it stood before the
//                                    limiter (5a); ["record", what] stops it
//
// Readings, a line each after `at T` (T in seconds, to the sample):
//
//   heard     PEAK_L PEAK_R RMS NONFINITE N   the heard pair since the last `heard`: its
//             peaks, the RMS of both, how many samples were not finite, how many in all
//   stage     LIVE, then the shared stage's glow motion memory hold level change, then each
//             layer's stage the same (A, B)
//   lmeter    LIVE, then each layer's meter: change verdict lit novelty
//   loop      each route the matrix handed the generator as the loop's, slot:held:heldB,
//             then `visual` and the view's offsets: resonance rotation zoom lag cutoff position
//   table     A and B, a line each: the richest level of the Scan table the layer reads now,
//             whole, or `-` for none
//   sources   the photocell's reading and its slewed value, then the picture's six raw
//             (round cover change novelty signed bored), then the same six slewed
//   gridstat  the shown grid's largest cell, its sum, and how many cells are not finite
//   settings  what the generator holds of the effects: reverb mix size spread, phaser mix
//             depth feedback rate, delay mix, and the Picture amount each hand pushes
//   loopof    each routing as source>dest:registered:picture:kind - whether its source is
//             the picture's now (a hearing source is while it hears the generator), and
//             its destination's kind, a v e or - for none
//   griddump  the shown grid, into the `grid` file
//   eye       the shared meter's change as the eye sees it (5a, kMeterEye): this frame's, and
//             the verdict's rate over its window; then the verdict
//   limiter   the limiter's reduction in dB as the node reports it, then what the meter is
//             handed (nought or below), then the instrument's latency in frames
//   grid lgrid hearing scan reads tone routed meter layers    instrument_reads.h's
#include <cmath>
#include <complex>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <memory>
#include <string>
#include <vector>

#include "scope/instrument.h"
#include "instrument_reads.h"

namespace {

std::string text(const scope::Json& v) { return v.type == scope::Json::Type::String ? scope::utf16To8(v.s) : std::string(); }

// A radix-2 FFT, in place, for --response's band split: nothing here needs to be fast.
void fft(std::vector<std::complex<double>>& a) {
  const std::size_t n = a.size();
  for (std::size_t i = 1, j = 0; i < n; i++) {
    std::size_t bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) std::swap(a[i], a[j]);
  }
  for (std::size_t len = 2; len <= n; len <<= 1) {
    const double ang = -2 * 3.14159265358979323846 / static_cast<double>(len);
    for (std::size_t i = 0; i < n; i += len)
      for (std::size_t k = 0; k < len / 2; k++) {
        const std::complex<double> w = std::polar(1.0, ang * static_cast<double>(k));
        const auto u = a[i + k], v = a[i + k + len / 2] * w;
        a[i + k] = u + v;
        a[i + k + len / 2] = u - v;
      }
  }
}

/* response_cpp's run, which this replaced (batch 5): the instrument loaded
   with CODE and PATCH, a file of `seconds status data1 data2` lines played
   at their own samples, a 128-frame step at a time at 48 kHz. Kept to the
   byte, so web/tests/responsetest.py's judgements read what they always read:
   the two were run on responsetest's sequence, its fresh chord and its held
   one, and on --decode, and gave the same bytes before response_cpp went. */
int response(char** argv) {
  const auto command = scope::Instrument::setup(argv[2]);
  if (!command) { std::fprintf(stderr, "the code does not read\n"); return 2; }
  scope::Json setup = *command->setup;
  const auto patch = scope::jsonParse(scope::utf8To16(argv[3]));
  if (!patch || patch->type != scope::Json::Type::Object) { std::fprintf(stderr, "the patch is not an object\n"); return 2; }
  for (const auto& kv : patch->o) setup.set(kv.first, kv.second);
  struct Message { double t; std::uint8_t bytes[3]; };
  std::vector<Message> messages;
  {
    std::ifstream file(argv[4]);
    double t;
    int a, b, c;
    while (file >> t >> a >> b >> c)
      messages.push_back({ t, { static_cast<std::uint8_t>(a), static_cast<std::uint8_t>(b), static_cast<std::uint8_t>(c) } });
  }
  constexpr double kRate = 48000;
  constexpr int kStep = 128, kWindow = 4096;
  const long total = static_cast<long>(std::atof(argv[5]) * kRate);
  scope::Instrument instrument;
  instrument.prepare(kRate, kStep, setup);
  /* With the instrument's limiter off (5a), as response_cpp played it: the
     judgements are of how the picture moves the sound, in decibels, and were
     measured before the limiter, which would hold the loudest swells down at
     its threshold and make the byte-for-byte run another. */
  instrument.apply(scope::Instrument::control("limiter", scope::Json::string(std::string_view("0"))));
  std::vector<float> left(kStep), right(kStep);
  std::vector<double> heardL;
  heardL.reserve(static_cast<std::size_t>(total) + kStep);
  double quarter = 0;
  long inQuarter = 0, quarterAt = 0;
  std::size_t next = 0;
  for (long at = 0; at < total; at += kStep) {
    std::vector<scope::Instrument::Event> events;
    while (next < messages.size() && messages[next].t * kRate < static_cast<double>(at + kStep)) {
      const int sample = static_cast<int>(std::fmax(0.0, messages[next].t * kRate - static_cast<double>(at)));
      events.push_back({ sample, messages[next].bytes, 3 });
      next++;
    }
    instrument.block(left.data(), right.data(), kStep, events.data(), events.size(), nullptr, nullptr, 0, nullptr);
    for (int k = 0; k < kStep; k++) {
      heardL.push_back(left[static_cast<std::size_t>(k)]);
      quarter += static_cast<double>(left[static_cast<std::size_t>(k)]) * left[static_cast<std::size_t>(k)]
               + static_cast<double>(right[static_cast<std::size_t>(k)]) * right[static_cast<std::size_t>(k)];
      if (++inQuarter == static_cast<long>(kRate / 4)) {
        std::printf("level %.4f %.6f\n", static_cast<double>(quarterAt) / kRate, 10 * std::log10(quarter / (2.0 * inQuarter) + 1e-12));
        quarterAt += inQuarter;
        quarter = 0;
        inQuarter = 0;
      }
    }
    if ((at / kStep) % 8 == 0) {
      const auto& layers = instrument.layerPictures();
      std::printf("stage %.4f %d", static_cast<double>(at) / kRate, layers.live() ? 1 : 0);
      for (int l = 0; l < 2; l++) {
        const auto& st = layers.live() ? layers.stage(l) : instrument.picture().stage();
        std::printf(" %.6f %.6f %.6f %.6f %.6f", st.glow(), st.level(), st.change(), st.motion(), st.hold());
      }
      std::printf("\n");
    }
  }
  std::vector<std::complex<double>> buffer(kWindow);
  for (std::size_t start = 0; start + kWindow <= heardL.size(); start += kWindow / 2) {
    for (int i = 0; i < kWindow; i++) {
      const double hann = 0.5 - 0.5 * std::cos(2 * 3.14159265358979323846 * i / (kWindow - 1));
      buffer[static_cast<std::size_t>(i)] = heardL[start + static_cast<std::size_t>(i)] * hann;
    }
    fft(buffer);
    double all = 0, high = 0;
    for (int k = 1; k < kWindow / 2; k++) {
      const double e = std::norm(buffer[static_cast<std::size_t>(k)]);
      all += e;
      if (k * kRate / kWindow > 1000) high += e;
    }
    std::printf("band %.4f %.6g %.6g\n", static_cast<double>(start) / kRate, all, high);
  }
  return 0;
}

// A file opened for a record, closed when the record stops or the run ends.
struct File {
  std::FILE* f = nullptr;
  void open(const std::string& path) { close(); f = std::fopen(path.c_str(), "wb"); }
  void close() { if (f) std::fclose(f); f = nullptr; }
  void put(const float* x, std::size_t n) { if (f) std::fwrite(x, sizeof(float), n, f); }
  ~File() { close(); }
};

class Render {
 public:
  int run(const char* path) {
    std::ifstream file(path);
    for (std::string line; std::getline(file, line);) {
      if (line.empty()) continue;
      const auto parsed = scope::jsonParse(scope::utf8To16(line));
      if (!parsed || parsed->type != scope::Json::Type::Array || parsed->a.empty()) { std::fprintf(stderr, "bad line\n"); return 2; }
      if (!command(parsed->a)) return 2;
    }
    std::fflush(stdout);
    return 0;
  }

 private:
  static constexpr int kStep = 128;
  scope::Instrument inst_;
  double rate_ = 48000;
  long now_ = 0;  // samples rendered
  std::vector<std::uint8_t> midi_;
  std::vector<std::size_t> lengths_;
  // The input: its kind, what it holds, and how far it has been read.
  std::string inKind_ = "none";
  std::vector<float> fileL_, fileR_;
  bool fileStereo_ = false;
  double inA_ = 0, inB_ = 0, inC_ = 0, inD_ = 0;
  long inAt_ = 0;
  // The readings due at an interval, from where they were asked.
  double every_ = 0;
  long everyFrom_ = 0, everyCount_ = 0;
  std::vector<std::string> everyNames_;
  // The heard pair since the last `heard`.
  double peakL_ = 0, peakR_ = 0, sumSq_ = 0;
  long heardN_ = 0, nonFinite_ = 0;
  File heardFile_, lanesFile_, gridFile_, preFile_;

  const scope::Json& at(const std::vector<scope::Json>& a, std::size_t i) {
    static const scope::Json none;
    return i < a.size() ? a[i] : none;
  }

  long nextRead() const {
    return every_ > 0 ? everyFrom_ + static_cast<long>(std::llround(static_cast<double>(everyCount_ + 1) * every_ * rate_)) : -1;
  }

  bool command(const std::vector<scope::Json>& a) {
    const std::string cmd = text(a[0]);
    if (cmd == "make") {
      rate_ = at(a, 1).n;
      const auto setup = scope::Instrument::setup(text(at(a, 2)));
      if (!setup) { std::fprintf(stderr, "the code does not read\n"); return false; }
      scope::Json s = *setup->setup;
      if (at(a, 3).type == scope::Json::Type::Object) for (const auto& kv : at(a, 3).o) s.set(kv.first, kv.second);
      inst_.prepare(rate_, kStep, s);
      now_ = 0;
      inst_.hooks.beforeLimit = [this](const float* l, const float* r, int n) {
        if (!preFile_.f) return;
        for (int k = 0; k < n; ++k) { const float p[2] = { l[k], r[k] }; preFile_.put(p, 2); }
      };
    } else if (cmd == "slider") {
      const auto c = scope::Instrument::slider(text(at(a, 1)), at(a, 2).type == scope::Json::Type::String ? at(a, 2).s : u"");
      if (c) inst_.apply(*c); else std::printf("no slider %s\n", text(at(a, 1)).c_str());
    } else if (cmd == "setup") {
      const auto c = scope::Instrument::setup(text(at(a, 1)));
      if (c) inst_.apply(*c); else std::printf("no setup\n");
    } else if (cmd == "control") {
      inst_.apply(scope::Instrument::control(text(at(a, 1)), at(a, 2).type == scope::Json::Type::Bool ? at(a, 2) : scope::Json::string(at(a, 2).s)));
    } else if (cmd == "click") inst_.apply(scope::Instrument::click(text(at(a, 1))));
    else if (cmd == "routings") inst_.apply(scope::Instrument::routings(text(at(a, 1))));
    else if (cmd == "fade") {
      const auto c = scope::Instrument::fade(text(at(a, 1)));
      if (c) inst_.apply(*c); else std::printf("no fade\n");
    } else if (cmd == "midi") {
      for (std::size_t i = 1; i < a.size() && i < 4; ++i) midi_.push_back(static_cast<std::uint8_t>(a[i].n));
      lengths_.push_back(std::min<std::size_t>(a.size() - 1, 3));
    } else if (cmd == "to") {
      renderTo(static_cast<long>(std::llround(at(a, 1).n * rate_)));
    } else if (cmd == "input") {
      inKind_ = text(at(a, 1));
      inAt_ = 0;
      if (inKind_ == "file") {
        fileL_.clear(); fileR_.clear();
        fileStereo_ = at(a, 3).n == 2;
        std::FILE* f = std::fopen(text(at(a, 2)).c_str(), "rb");
        if (!f) { std::fprintf(stderr, "no input file\n"); return false; }
        float pair[2];
        const std::size_t width = fileStereo_ ? 2 : 1;
        while (std::fread(pair, sizeof(float), width, f) == width) { fileL_.push_back(pair[0]); if (fileStereo_) fileR_.push_back(pair[1]); }
        std::fclose(f);
      } else {
        inA_ = at(a, 2).n; inB_ = at(a, 3).n; inC_ = at(a, 4).n; inD_ = at(a, 5).n;
      }
    } else if (cmd == "every") {
      every_ = at(a, 1).n;
      everyFrom_ = now_;
      everyCount_ = 0;
      everyNames_.clear();
      for (std::size_t i = 2; i < a.size(); ++i) everyNames_.push_back(text(a[i]));
    } else if (cmd == "read") {
      std::vector<std::string> names;
      for (std::size_t i = 1; i < a.size(); ++i) names.push_back(text(a[i]));
      readings(names);
    } else if (cmd == "reset") {
      if (text(at(a, 1)) == "meter") reads::resetMeter(inst_);
    } else if (cmd == "hold") {
      reads::hold(inst_, static_cast<int>(at(a, 1).n), at(a, 2).n);
    } else if (cmd == "record") {
      const std::string what = text(at(a, 1));
      File& f = what == "heard" ? heardFile_ : what == "lanes" ? lanesFile_ : what == "prelimit" ? preFile_ : gridFile_;
      if (at(a, 2).type == scope::Json::Type::String) f.open(text(at(a, 2))); else f.close();
    } else { std::fprintf(stderr, "unknown command %s\n", cmd.c_str()); return false; }
    return true;
  }

  // The input's next n samples, into l and r; false for no input.
  bool input(std::vector<float>& l, std::vector<float>& r, int n, bool& stereo) {
    stereo = false;
    if (inKind_ == "none" || inKind_.empty()) return false;
    for (int k = 0; k < n; ++k, ++inAt_) {
      const std::size_t i = static_cast<std::size_t>(k);
      if (inKind_ == "file") {
        const std::size_t at = static_cast<std::size_t>(inAt_);
        l[i] = at < fileL_.size() ? fileL_[at] : 0.0f;
        r[i] = fileStereo_ && at < fileR_.size() ? fileR_[at] : 0.0f;
        stereo = fileStereo_;
      } else if (inKind_ == "sine") {
        const double t = static_cast<double>(inAt_) / rate_;
        l[i] = static_cast<float>(inB_ * std::sin(2 * M_PI * inA_ * t));
        stereo = inC_ > 0;
        r[i] = stereo ? static_cast<float>(inD_ * std::sin(2 * M_PI * inC_ * t)) : 0.0f;
      } else if (inKind_ == "saw") {
        // instrument_cpp's feed, by the same arithmetic.
        const double t = std::fmod(static_cast<double>(inAt_), inA_) / inA_;
        l[i] = static_cast<float>(0.5 * (2 * t - 1));
        stereo = inB_ > 0;
        if (stereo) {
          const double u = std::fmod(static_cast<double>(inAt_), inB_) / inB_;
          r[i] = static_cast<float>(0.5 * (u < 0.5 ? 4 * u - 1 : 3 - 4 * u));
        } else r[i] = 0.0f;
      }
    }
    return true;
  }

  void renderTo(long target) {
    std::vector<float> left(kStep), right(kStep), inL(kStep), inR(kStep), lanes(static_cast<std::size_t>(scope::Instrument::kRingLanes) * kStep),
        row(scope::Instrument::kRingLanes);
    while (now_ < target) {
      long end = std::min(target, now_ + kStep);
      const long due = nextRead();
      if (due > now_ && due < end) end = due;
      const int n = static_cast<int>(end - now_);
      std::vector<scope::Instrument::Event> events;
      std::size_t off = 0;
      for (const std::size_t length : lengths_) { events.push_back({ 0, midi_.data() + off, length }); off += length; }
      bool stereo = false;
      const bool fed = input(inL, inR, n, stereo);
      const scope::Instrument::Input in { inL.data(), stereo ? inR.data() : nullptr };
      inst_.block(left.data(), right.data(), n, events.data(), events.size(), nullptr, nullptr, 0, fed ? &in : nullptr);
      midi_.clear(); lengths_.clear();
      for (int k = 0; k < n; ++k) {
        const double l = left[static_cast<std::size_t>(k)], r = right[static_cast<std::size_t>(k)];
        if (!std::isfinite(l) || !std::isfinite(r)) nonFinite_++;
        else {
          peakL_ = std::fmax(peakL_, std::fabs(l)); peakR_ = std::fmax(peakR_, std::fabs(r));
          sumSq_ += l * l + r * r;
        }
        heardN_++;
      }
      if (heardFile_.f) for (int k = 0; k < n; ++k) { const float p[2] = { left[static_cast<std::size_t>(k)], right[static_cast<std::size_t>(k)] }; heardFile_.put(p, 2); }
      if (lanesFile_.f) {
        for (int c = 0; c < scope::Instrument::kRingLanes; ++c)
          inst_.latestLane(c, lanes.data() + static_cast<std::size_t>(c) * static_cast<std::size_t>(n), static_cast<std::size_t>(n));
        for (int k = 0; k < n; ++k) {
          for (int c = 0; c < scope::Instrument::kRingLanes; ++c) row[static_cast<std::size_t>(c)] = lanes[static_cast<std::size_t>(c * n + k)];
          lanesFile_.put(row.data(), row.size());
        }
      }
      now_ = end;
      if (due == now_) { readings(everyNames_); everyCount_++; }
    }
  }

  void readings(const std::vector<std::string>& names) {
    std::printf("at %.6f\n", static_cast<double>(now_) / rate_);
    for (const auto& name : names) reading(name);
  }

  void reading(const std::string& name) {
    const auto& layers = inst_.layerPictures();
    const auto& pic = inst_.picture();
    if (name == "heard") {
      std::printf("heard %.9g %.9g %.9g %ld %ld\n", peakL_, peakR_, heardN_ ? std::sqrt(sumSq_ / (2.0 * static_cast<double>(heardN_))) : 0.0,
                  nonFinite_, heardN_);
      peakL_ = peakR_ = sumSq_ = 0; heardN_ = nonFinite_ = 0;
    } else if (name == "stage") {
      const auto put = [](const scope::PictureStage& s) {
        std::printf(" %.9g %.9g %.9g %.9g %.9g %.9g", s.glow(), s.motion(), s.memory(), s.hold(), s.level(), s.change());
      };
      std::printf("stage %d", layers.live() ? 1 : 0);
      put(pic.stage()); put(layers.stage(0)); put(layers.stage(1));
      std::printf("\n");
    } else if (name == "lmeter") {
      std::printf("lmeter %d", layers.live() ? 1 : 0);
      for (int l = 0; l < 2; l++) {
        const auto& m = layers.pictures(l).meter();
        std::printf(" %.9g %s %.9g %.9g", m.change(), m.verdict().c_str(), m.lit(), m.novelty());
      }
      std::printf("\n");
    } else if (name == "loop") {
      std::printf("loop");
      for (const auto& r : inst_.routes()) if (r.loop) std::printf(" %d:%.17g:%.17g", r.slot, r.held, r.heldB);
      const auto& v = inst_.view();
      std::printf(" visual %.17g %.17g %.17g %.17g %.17g %.17g\n", v.capture.resMod, v.capture.rotateMod, v.zoomMod, v.capture.lagMod,
                  v.capture.cutoffMod, v.capture.positionMod);
    } else if (name == "table") {
      for (int l = 0; l < 2; l++) {
        const scope::CycleTables* t = inst_.generator().scanTable(l);
        std::printf("table %s", l ? "B" : "A");
        if (!t || t->levels.empty()) { std::printf(" -\n"); continue; }
        std::printf(" %zu", t->levels[0].size());
        for (const double x : t->levels[0]) std::printf(" %.9g", x);
        std::printf("\n");
      }
    } else if (name == "sources") {
      const auto& p = pic.pictures();
      const auto six = [](const scope::PictureValues& x) {
        std::printf(" %.17g %.17g %.17g %.17g %.17g %.17g", x.round, x.cover, x.change, x.novelty, x.signed_, x.bored);
      };
      std::printf("sources %.17g %.17g", p.photoRaw(), p.photo());
      six(p.raw()); six(p.values());
      std::printf("\n");
    } else if (name == "gridstat") {
      const auto& g = pic.phosphor().grid();
      double most = 0, sum = 0;
      long bad = 0;
      for (const float x : g) { if (!std::isfinite(x)) { bad++; continue; } most = std::fmax(most, x); sum += x; }
      std::printf("gridstat %.9g %.9g %ld\n", most, sum, bad);
    } else if (name == "settings") {
      const auto& t = inst_.generator().tone();
      std::printf("settings %.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g\n", t.reverbMix, t.reverbSize, t.reverbSpread, t.phaserMix,
                  t.phaserDepth, t.phaserFeedback, t.phaserRate, t.delayMix);
    } else if (name == "loopof") {
      // Each routing: whether its source is registered and whether it is the
      // picture's now (ModSource::picture(), which a hearing source answers by
      // what it hears), and its destination's kind - a(udio), v(isual), e(vent), - none.
      auto& m = inst_.matrix();
      std::printf("loopof");
      for (const auto& r : m.routings()) {
        const scope::ModSource* src = m.source(r.sourceId);
        const scope::ModDest* d = m.dest(r.destId);
        const char kind = !d ? '-' : d->kind == scope::DestKind::Audio ? 'a' : d->kind == scope::DestKind::Visual ? 'v' : 'e';
        std::printf(" %s>%s:%d:%d:%c", r.sourceId.c_str(), r.destId.c_str(), src ? 1 : 0, src && src->picture() ? 1 : 0, kind);
      }
      std::printf("\n");
    } else if (name == "griddump") {
      const auto& g = pic.phosphor().grid();
      gridFile_.put(g.data(), g.size());
    } else if (name == "eye") {
      const auto& m = pic.pictures().meter();
      std::printf("eye %.9g %.9g %s\n", m.seen(), m.seenRate(), m.verdict().c_str());
    } else if (name == "limiter") {
      std::printf("limiter %.9g %.9g %d\n", static_cast<double>(inst_.limiterReduction()), inst_.limiting(), inst_.latency());
    } else if (name == "grid") reads::grid(inst_);
    else if (name == "lgrid") reads::lgrid(inst_);
    else if (name == "hearing") reads::hearing(inst_);
    else if (name == "scan") reads::scan(inst_);
    else if (name == "reads") reads::scanReads(inst_);
    else if (name == "tone") reads::tone(inst_);
    else if (name == "routed") reads::routed(inst_);
    else if (name == "meter") reads::meter(inst_);
    else if (name == "layers") reads::layers(inst_);
    else std::printf("no reading %s\n", name.c_str());
  }
};

}  // namespace

int main(int argc, char** argv) {
  if (argc == 3 && std::string(argv[1]) == "--decode") {
    const auto read = scope::Instrument::setup(argv[2]);
    if (!read) return 2;
    for (const char* key : { "v", "pictureAmount", "bPictureAmount" }) {
      const scope::Json* v = read->setup->get(key);
      std::printf("%s %s\n", key, v && v->type == scope::Json::Type::Number ? std::to_string(v->n).c_str() : "none");
    }
    return 0;
  }
  if (argc == 2 && std::string(argv[1]) == "--slots") {
    namespace s = scope::slot;
    std::printf("freq %d amp %d phase %d twist %d fm %d drive %d fold %d vcf %d echo %d phaser %d reverb %d used %d\n", s::Freq, s::Amp,
                s::Phase, s::Twist, s::Fm, s::Drive, s::Fold, s::Vcf, s::Echo, s::Phaser, s::Reverb, s::Used);
    return 0;
  }
  if (argc == 6 && std::string(argv[1]) == "--response") return response(argv);
  if (argc != 2) {
    std::fprintf(stderr, "usage: render_cpp SCRIPT | --response CODE PATCH EVENTS SECONDS | --decode CODE | --slots\n");
    return 2;
  }
  // The instrument is large; one, made once.
  auto render = std::make_unique<Render>();
  return render->run(argv[1]);
}
