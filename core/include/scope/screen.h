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
// - The automatic lag's lock. The page listens for a lag to lock to and the
//   core has not got that analysis yet; the lag is the slider's until it has.
// - The canvas. The page's is the window it is drawn in; this one is a size
//   the owner chooses (Canvas), and with it the graticule the grid lies over.
//   A reticle's u and v are fractions of the graticule, so they read the same
//   picture whatever the size, give or take where a stroke meets a cell edge.
// - Normal and Single. The trigger's mode is kept, and the capture here is
//   always Auto's: what the page holds for a frame Normal could not trigger
//   is the page's screen, and the grid follows the signal.

#pragma once

#include <array>
#include <memory>
#include <string>
#include <vector>

#include "scope/beam.h"
#include "scope/capture.h"
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

class PictureRun {
 public:
  PictureRun(Matrix& matrix, Brain& brain) : brain_(brain) {
    // PICTURE_SOURCES, with SIXTH ("signed") the one of the drawn pair's two that is offered.
    for (const char* key : { "round", "cover", "change", "novelty", "signed", "bored" })
      sources_.push_back(std::make_unique<PictureSource>(key, pics_));
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
      if (registered_) {
        matrix.registerSource(&photo_);
        for (auto& s : sources_) matrix.registerSource(s.get());
      } else {
        matrix.unregisterSource(photo_.id);
        for (auto& s : sources_) matrix.unregisterSource(s->id);
      }
      matrix.touch();
    }
    pics_.u = brain_.photo.u;
    pics_.v = brain_.photo.v;
    const View& view = captureView(brain_);
    frame_ = capture(view, source);
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

  const Phosphor& phosphor() const { return phosphor_; }
  const PictureSources& pictures() const { return pics_; }
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
  Frame frame_;
  Plot plot_;
  bool registered_ = false;
  int restored_ = -1;
  double last_ = -1, next_ = 0, elapsed_ = 16;
};

}  // namespace scope
