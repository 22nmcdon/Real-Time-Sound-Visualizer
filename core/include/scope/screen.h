// The picture run without the window (stage 4d): what the page's frame does
// for the photocell and the picture's sources, so the loops through the
// picture go on with the plugin's window closed. A frame captures from the
// source, steps the photocell and the picture's sources from the grid the
// last frame left, and - after the matrix has run, as the page draws after
// `applyModMatrix` - lays this frame's deposits into the grid. The sources
// are registered while the photocell is on and not otherwise, as `setPhoto`
// has it; the view's destinations (rotation, the lag, the filter, the zoom,
// the trigger's position, each lane's full scale) are registered always, as
// the page registers them at load.
//
// What differs from the page, and why, so nobody goes looking:
//
// - How often. The page's frame is the display's, about sixty a second; the
//   owner calls `due` with the audio time and runs a frame when a sixtieth of
//   a second has gone, so the meter's clock, the slews and the beam's anchor
//   see the page's rate rather than the host's block size.
// - The limiter. The page's verdict reads how hard its monitor chains'
//   limiters work - Web Audio nodes on the way to the speakers, which the
//   plugin does not have; the host's output is the host's. The owner passes
//   nought, so a picture cannot read as running away by the limiter here,
//   only by its ink.
// - The automatic lag's lock, which listens every fifth of a second from the
//   first frame, where the page's counts from when it loaded. The held note
//   it locks to is the one the owner says, as the page asks `midiPitchHz`.
// - The canvas. The page's is the window it is drawn in; this one is a size
//   the owner chooses (Canvas), and with it the graticule the grid lies over.
//   A reticle's u and v are fractions of the graticule, so they read the same
//   picture whatever the size, give or take where a stroke meets a cell edge.
// - Single. Normal holds the last triggered frame when nothing triggers, as
//   the page does, so the grid and the photocell read what the screen shows.
//   Single is held the same way and is not stopped by its capture: the page
//   stops itself and is set going again by its Run button, which the core
//   does not hear, and a grid held for good while the page had moved on would
//   leave the photocell reading a picture nobody could see.

#pragma once

#include <array>
#include <memory>
#include <string>
#include <vector>

#include "scope/beam.h"
#include "scope/capture.h"
#include "scope/hearing.h"  // estimatePeriod, for the lag's lock
#include "scope/matrix.h"
#include "scope/picture.h"
#include "scope/restore.h"

namespace scope {

constexpr double kPictureFrameMs = 1000.0 / 60;  // the page's frame, the display's
constexpr double kFsSpanDb = 12;                  // FS_SPAN_DB

// photo.1: how bright the grid is under the reticle.
class PhotoSource : public ModSource {
 public:
  explicit PhotoSource(const PictureSources& p) : ModSource("photo.1"), p_(p) { reach = kPhotoReach; fromPicture = true; }
  double value() const override { return p_.photo(); }

 private:
  const PictureSources& p_;
};

// picture.*: what the picture says. Boredom's reach is its own, lower.
class PictureSource : public ModSource {
 public:
  PictureSource(std::string key, const PictureSources& p) : ModSource("picture." + key), key_(std::move(key)), p_(p) {
    reach = key_ == "bored" ? kBoredReach : kPhotoReach;
    fromPicture = true;
  }
  double value() const override {
    const PictureValues& v = p_.values();
    if (key_ == "round") return v.round;
    if (key_ == "cover") return v.cover;
    if (key_ == "change") return v.change;
    if (key_ == "novelty") return v.novelty;
    if (key_ == "signed") return v.signed_;
    if (key_ == "edge") return v.edge;
    return v.bored;
  }

 private:
  std::string key_;
  const PictureSources& p_;
};

// stage.*: the picture stage's three reads (P3). Memory is boredom, and has
// boredom's lower reach.
class StageSource : public ModSource {
 public:
  StageSource(std::string key, const PictureStage& s) : ModSource("stage." + key), key_(std::move(key)), s_(s) {
    reach = key_ == "memory" ? kBoredReach : kPhotoReach;
    fromPicture = true;
  }
  double value() const override {
    if (key_ == "glow") return s_.glow();
    if (key_ == "motion") return s_.motion();
    return s_.memory();
  }

 private:
  std::string key_;
  const PictureStage& s_;
};

constexpr double kReadoutMs = 200;       // READOUT_MS: words are read, not watched
constexpr double kLagLockSeconds = 1;    // how long the automatic lag takes to follow a new note
constexpr double kLagAperiodicMax = 0.15;
constexpr double kLagProbeSeconds = 4.0 / 20;  // four periods of 20 Hz

/* lagLockUpdate: the automatic lag, a quarter period of what is playing.
   A held note is not an estimate, and sets it at once; otherwise the period
   heard in its own fifth of a second, trusted only when it is periodic and
   between 20 Hz and 5 kHz, approached slowly in the log domain so vibrato
   precesses the figure rather than holding it at a circle. `playedHz` is
   the held note's pitch when the hands' note is the measurements' truth. */
inline void lagLockUpdate(View& v, const CaptureSource& s, std::optional<double> playedHz, PitchScratch& scratch) {
  if (!v.lagOn || !v.lagAuto) return;
  if (playedHz) { v.lagLock = 0.25 / *playedHz; return; }
  const double want = jsMathRound(kLagProbeSeconds * s.rate);
  // `source.capacity || want`: a capacity of nought, or none, is no limit.
  const double room = s.capacity == 0 || std::isnan(s.capacity) ? want : s.capacity;
  const auto probe = static_cast<std::size_t>(std::fmin(want, room));
  if (!s.latest) return;
  const auto lanes = s.latest(probe);
  if (lanes.empty()) return;
  const auto found = estimatePeriod(lanes[0].data(), lanes[0].size(), s.rate, scratch);
  if (!found || found->aperiodicity > kLagAperiodicMax) return;
  if (found->hz < 20 || found->hz > 5000) return;
  const double target = 0.25 / found->hz;
  if (!v.lagLock) { v.lagLock = target; return; }
  const double a = 1 - std::exp(-(kReadoutMs / 1000) / kLagLockSeconds);
  v.lagLock = std::pow(2, std::log2(*v.lagLock) + a * (std::log2(target) - std::log2(*v.lagLock)));
}

class PictureRun {
 public:
  PictureRun(Matrix& matrix, Brain& brain) : brain_(brain) {
    // PICTURE_SOURCES, with SIXTH ("signed") the one of the drawn pair's two that is offered.
    for (const char* key : { "round", "cover", "change", "novelty", "signed", "bored" })
      sources_.push_back(std::make_unique<PictureSource>(key, pics_));
    for (const char* key : { "glow", "motion", "memory" })
      stageSources_.push_back(std::make_unique<StageSource>(key, stage_));
    // Registered always, since the picture stage: the photocell alone comes
    // and goes with its switch.
    for (auto& s : sources_) matrix.registerSource(s.get());
    for (auto& s : stageSources_) matrix.registerSource(s.get());
    // VISUAL_DESTS, and each lane's full scale (registerLaneDests).
    View& v = brain_.view.capture;
    const auto add = [&](std::string id, double span, double min, double max, std::function<double()> base,
                         std::function<void(double)> set) {
      ModDest d;
      d.id = std::move(id); d.kind = DestKind::Visual; d.span = span; d.min = min; d.max = max;
      d.base = std::move(base); d.set = std::move(set);
      matrix.registerDest(std::move(d));
    };
    add("view.rotate", 1, -2, 2, [&v] { return v.rotate; }, [&v](double o) { v.rotateMod = o; });
    add("view.lag", kLagMaxMs, 0, kLagMaxMs, [&v] { return v.lagMs; }, [&v](double o) { v.lagMod = o; });
    add("filter.cutoff", 400, 0, 1000, [&v] { return v.filter.cutoff; }, [&v](double o) { v.cutoffMod = o; });
    add("filter.res", 50, 0, 100, [&v] { return v.filter.res; }, [&v](double o) { v.resMod = o; });
    Brain::ViewState& w = brain_.view;
    add("view.zoom", 8, 0, 24, [&w] { return w.zoomStep; }, [&w](double o) { w.zoomMod = o; });
    add("trig.position", 0.5, 0, 1, [&v] { return v.position; }, [&v](double o) { v.positionMod = o; });
    for (std::size_t i = 0; i < 2; i++) {
      add("view.scale" + std::to_string(i + 1), kFsSpanDb, kFullScaleBottom, 0,
          [&v, i] { return v.channels.size() > i ? v.channels[i].fsDb : 0; },
          [&v, i](double o) { if (v.channels.size() > i) v.channels[i].fsMod = o; });
    }
  }
  PictureRun(const PictureRun&) = delete;
  PictureRun& operator=(const PictureRun&) = delete;

  // Whether a frame is due by `now` (milliseconds of audio), and how long
  // since the last: the page's elapsed, held to a quarter of a second as the
  // page holds it, and sixteen for the first. Due on a running schedule a
  // sixtieth of a second apart, not a sixtieth after the last frame: blocks
  // of 10.7 ms would otherwise land a frame on every other block, 47 a
  // second. Blocks longer than a frame get one frame each, the schedule
  // starting again from the block rather than catching up in a burst.
  bool due(double now) {
    if (last_ < 0) { elapsed_ = 16; last_ = now; next_ = now + kPictureFrameMs; return true; }
    if (now < next_) return false;
    elapsed_ = std::fmin(250.0, now - last_);
    last_ = now;
    next_ += kPictureFrameMs;
    if (next_ <= now) next_ = now + kPictureFrameMs;
    return true;
  }
  double elapsed() const { return elapsed_; }

  // The frame's first half, before the matrix: the photocell switched as the
  // brain says, the capture, and the photocell and the picture's sources
  // stepped from the grid the last frame left.
  void before(Matrix& matrix, const CaptureSource& source, double limiting) {
    if (brain_.photo.on != registered_) {
      registered_ = brain_.photo.on;
      pics_.setOn(registered_);
      if (registered_) matrix.registerSource(&photo_);
      else matrix.unregisterSource(photo_.id);
      matrix.touch();
    }
    pics_.u = brain_.photo.u;
    pics_.v = brain_.photo.v;
    const View& view = captureView(brain_);
    /* Auto, or an edge found: this frame, and the one held. Normal and Single
       with nothing to show keep the frame held, as the page does rather than
       drawing the untriggered sweep the mode exists to suppress; before
       anything has been held, the sweep. */
    Frame fresh = capture(view, source);
    if (brain_.view.mode == "auto" || fresh.triggered) { frame_ = std::move(fresh); held_ = true; }
    else if (!held_) frame_ = std::move(fresh);
    const bool spect = brain_.view.screen.display == "spect";
    pics_.photoStep(phosphor_, elapsed_, spect);
    const Screen& sc = brain_.view.screen;
    const std::size_t ax = static_cast<std::size_t>(sc.xyPair.x), ay = static_cast<std::size_t>(sc.xyPair.y);
    const Lane* left = ax < frame_.channels.size() ? &frame_.channels[ax] : frame_.channels.empty() ? nullptr : &frame_.channels[0];
    const Lane* right = ay < frame_.channels.size() ? &frame_.channels[ay]
                      : frame_.channels.size() > 1 ? &frame_.channels[1] : left;
    if (left && right) {
      const double spin = frame_.turned || !view.shaping ? 0 : view.rotate + view.rotateMod;
      const auto offset = [&](std::size_t ch) { return ch < view.channels.size() ? view.channels[ch].offset : 0.0; };
      const PairShape shape = shapeOfPair(left->data(), right->data(), std::min(left->size(), right->size()),
                                          gainOf(view, sc.xyPair.x), gainOf(view, sc.xyPair.y), offset(ax), offset(ay), spin, sc.zoom);
      pics_.pictureStep(phosphor_, &shape, elapsed_, spect, limiting);
    } else {
      pics_.pictureStep(phosphor_, nullptr, elapsed_, spect, limiting);
    }
    stage_.step(pics_.values(), elapsed_, spect);
    matrix.setStageAmount(brain_.panel.range("pictureAmount") / 100);
  }

  // The zoom made again from its step and what is pointed at it, after the
  // matrix has written the offset - every block, as the page does every frame.
  void afterMatrix() {
    Brain::ViewState& w = brain_.view;
    w.screen.zoom = std::pow(2, (w.zoomStep + w.zoomMod) / 4);
  }

  // The frame's second half, after the matrix: the deposits, on the canvas,
  // wiped rather than faded when the Clear button asked or the canvas changed.
  void draw(const CaptureSource& source, const Canvas& canvas) {
    Brain::ViewState& w = brain_.view;
    if (w.restored != restored_) { restored_ = w.restored; beam_.clear(); }
    Canvas c = canvas;
    c.resized = canvas.resized || w.wipe;
    w.wipe = false;
    plot_ = drawPicture(beam_, phosphor_, w.capture, w.screen, source, frame_, c, elapsed_);
  }

  /* The readout's work, every fifth of a second of frames, after the draw as
     the page's comes after its frame: the automatic lag's lock. Its
     estimator was made with room for the probe, so after its first pass it
     allocates nothing; the capture it reads does, as the frame's does. */
  void readout(const CaptureSource& source, std::optional<double> playedHz) {
    if (readAt_ < 0) readAt_ = last_;
    if (last_ - readAt_ < kReadoutMs) return;
    readAt_ = last_;
    lagLockUpdate(brain_.view.capture, source, playedHz, lagScratch_);
  }

  const Phosphor& phosphor() const { return phosphor_; }
  const PictureSources& pictures() const { return pics_; }
  const PictureStage& stage() const { return stage_; }
  const Frame& frame() const { return frame_; }
  const Plot& plot() const { return plot_; }

 private:
  Brain& brain_;
  Phosphor phosphor_;
  std::unique_ptr<Beam> beamStore_ = std::make_unique<Beam>();  // two hundred kilobytes of scratch, off the stack
  Beam& beam_ = *beamStore_;
  PictureSources pics_;
  PhotoSource photo_ { pics_ };
  std::vector<std::unique_ptr<PictureSource>> sources_;
  PictureStage stage_;
  std::vector<std::unique_ptr<StageSource>> stageSources_;
  Frame frame_;
  Plot plot_;
  bool registered_ = false, held_ = false;
  int restored_ = -1;
  double last_ = -1, next_ = 0, elapsed_ = 16;
  double readAt_ = -1;
  PitchScratch lagScratch_;
};

}  // namespace scope
