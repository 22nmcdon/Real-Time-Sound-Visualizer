// The page's output limiter and clamp (stage 5, step 5a): the last two
// things in its monitor chain (`makeMonitorChain`), a DynamicsCompressorNode
// at -3 dB, no knee, 20:1, 3 ms and 100 ms, and a WaveShaperNode on the
// clamp's curve with no oversampling - ported here so the instrument limits
// its own output, the plugin's as the site's, and its picture meter hears
// how hard the limiter works (the page's `monitorLimiting`), which until now
// it never did.
//
// The page's limiter is the browser's node, not JavaScript, so this is a port
// of Chromium's DynamicsCompressor (third_party/blink/renderer/platform/audio/
// dynamics_compressor.cc, the release Playwright's Chromium 153 runs) and of
// its WaveShaper's interpolation (modules/webaudio/wave_shaper_handler.cc),
// in single precision as they are, operation for operation. Parity renders
// the page's own chain in an OfflineAudioContext and holds this to it.
//
// Two decisions, each with its cost:
//
// - The float functions the compressor calls per sample - log10f and powf,
//   which Chromium takes from the system's C library - are glibc 2.39's,
//   ported below, rather than the C library's own. Measured, WebAssembly's
//   C library (wasi-libc) gives another log10f for 3 per cent of floats and
//   another powf for a few in ten thousand; the core compiled for the page
//   and the core native are held to equality (parity's 5f section), and the
//   page's node, through Chromium's libm on Linux, is glibc. The port agrees
//   with this machine's glibc on 11.7 million inputs, including through its
//   FMA variants, and is the same code in both builds. The cost: on a host
//   whose browser takes another libm (a Mac's, Windows'), the page's own
//   limiter and this one may differ in the last bit now and then, which is
//   inaudible and which only parity would see.
// - The double functions (sin per sample, exp, asin and pow per block of
//   32) are the C library's, since each is rounded to a float at once and a
//   last-bit difference in a double survives that about once in half a
//   billion; measured, (float)sin agrees between the two builds on all 24
//   million floats in [0, 1].
//
// The compressor delays everything by its lookahead, 6 ms (288 frames at
// 48 kHz, 264 at 44.1), which the page's chain always did; the plugin
// reports it to its host (`latency`).

#pragma once

#include <algorithm>
#include <array>
#include <cfloat>
#include <cmath>
#include <cstdint>
#include <cstring>

namespace scope {

namespace glibcf {

inline std::uint32_t bits(float f) { std::uint32_t u; std::memcpy(&u, &f, 4); return u; }
inline float fromBits(std::uint32_t u) { float f; std::memcpy(&f, &u, 4); return f; }
inline std::uint64_t bits64(double f) { std::uint64_t u; std::memcpy(&u, &f, 8); return u; }
inline double fromBits64(std::uint64_t u) { double f; std::memcpy(&f, &u, 8); return f; }

struct InvLog { double invc, logc; };

// sysdeps/ieee754/flt-32/e_logf.c and e_logf_data.c
inline float logf(float x) {
  static constexpr InvLog T[16] = {
    { 0x1.661ec79f8f3bep+0, -0x1.57bf7808caadep-2 }, { 0x1.571ed4aaf883dp+0, -0x1.2bef0a7c06ddbp-2 },
    { 0x1.49539f0f010bp+0, -0x1.01eae7f513a67p-2 }, { 0x1.3c995b0b80385p+0, -0x1.b31d8a68224e9p-3 },
    { 0x1.30d190c8864a5p+0, -0x1.6574f0ac07758p-3 }, { 0x1.25e227b0b8eap+0, -0x1.1aa2bc79c81p-3 },
    { 0x1.1bb4a4a1a343fp+0, -0x1.a4e76ce8c0e5ep-4 }, { 0x1.12358f08ae5bap+0, -0x1.1973c5a611cccp-4 },
    { 0x1.0953f419900a7p+0, -0x1.252f438e10c1ep-5 }, { 0x1p+0, 0x0p+0 },
    { 0x1.e608cfd9a47acp-1, 0x1.aa5aa5df25984p-5 }, { 0x1.ca4b31f026aap-1, 0x1.c5e53aa362eb4p-4 },
    { 0x1.b2036576afce6p-1, 0x1.526e57720db08p-3 }, { 0x1.9c2d163a1aa2dp-1, 0x1.bc2860d22477p-3 },
    { 0x1.886e6037841edp-1, 0x1.1058bc8a07ee1p-2 }, { 0x1.767dcf5534862p-1, 0x1.4043057b6ee09p-2 },
  };
  static constexpr double A[3] = { -0x1.00ea348b88334p-2, 0x1.5575b0be00b6ap-2, -0x1.ffffef20a4123p-2 };
  static constexpr double Ln2 = 0x1.62e42fefa39efp-1;
  std::uint32_t ix = bits(x);
  if (ix == 0x3f800000) return 0;
  if (ix - 0x00800000 >= 0x7f800000 - 0x00800000) {
    if (ix * 2 == 0) return -HUGE_VALF;
    if (ix == 0x7f800000) return x;
    if ((ix & 0x80000000) || ix * 2 >= 0xff000000) return NAN;
    ix = bits(x * 0x1p23f);
    ix -= 23u << 23;
  }
  const std::uint32_t tmp = ix - 0x3f330000;
  const int i = static_cast<int>((tmp >> (23 - 4)) % 16);
  const int k = static_cast<std::int32_t>(tmp) >> 23;
  const std::uint32_t iz = ix - (tmp & 0x1ffu << 23);
  const double z = static_cast<double>(fromBits(iz));
  const double r = z * T[i].invc - 1;
  const double y0 = T[i].logc + static_cast<double>(k) * Ln2;
  const double r2 = r * r;
  double y = A[1] * r + A[2];
  y = A[0] * r2 + y;
  y = y * r2 + (y0 + r);
  return static_cast<float>(y);
}

// sysdeps/ieee754/flt-32/e_log10f.c
inline float log10f(float x) {
  constexpr float two25 = 3.3554432000e+07f, ivln10 = 4.3429449201e-01f;
  constexpr float log10_2hi = 3.0102920532e-01f, log10_2lo = 7.9034151668e-07f;
  std::int32_t hx = static_cast<std::int32_t>(bits(x));
  std::int32_t k = 0;
  if (hx < 0x00800000) {
    if ((hx & 0x7fffffff) == 0) return -two25 / std::fabs(x);
    if (hx < 0) return NAN;
    k -= 25; x *= two25;
    hx = static_cast<std::int32_t>(bits(x));
  }
  if (hx >= 0x7f800000) return x + x;
  k += (hx >> 23) - 127;
  const std::int32_t i = static_cast<std::int32_t>((static_cast<std::uint32_t>(k) & 0x80000000u) >> 31);
  hx = (hx & 0x007fffff) | ((0x7f - i) << 23);
  const float y = static_cast<float>(k + i);
  x = fromBits(static_cast<std::uint32_t>(hx));
  const float z = y * log10_2lo + ivln10 * logf(x);
  return z + y * log10_2hi;
}

// sysdeps/ieee754/flt-32/e_powf.c, e_powf_log2_data.c and e_exp2f_data.c,
// for what the compressor asks: a base that is a positive normal number.
// Anything else (never asked) goes to the C library.
inline float powf(float x, float y) {
  static constexpr InvLog T[16] = {
    { 0x1.661ec79f8f3bep+0, -0x1.efec65b963019p-2 }, { 0x1.571ed4aaf883dp+0, -0x1.b0b6832d4fca4p-2 },
    { 0x1.49539f0f010bp+0, -0x1.7418b0a1fb77bp-2 }, { 0x1.3c995b0b80385p+0, -0x1.39de91a6dcf7bp-2 },
    { 0x1.30d190c8864a5p+0, -0x1.01d9bf3f2b631p-2 }, { 0x1.25e227b0b8eap+0, -0x1.97c1d1b3b7afp-3 },
    { 0x1.1bb4a4a1a343fp+0, -0x1.2f9e393af3c9fp-3 }, { 0x1.12358f08ae5bap+0, -0x1.960cbbf788d5cp-4 },
    { 0x1.0953f419900a7p+0, -0x1.a6f9db6475fcep-5 }, { 0x1p+0, 0x0p+0 },
    { 0x1.e608cfd9a47acp-1, 0x1.338ca9f24f53dp-4 }, { 0x1.ca4b31f026aap-1, 0x1.476a9543891bap-3 },
    { 0x1.b2036576afce6p-1, 0x1.e840b4ac4e4d2p-3 }, { 0x1.9c2d163a1aa2dp-1, 0x1.40645f0c6651cp-2 },
    { 0x1.886e6037841edp-1, 0x1.88e9c2c1b9ff8p-2 }, { 0x1.767dcf5534862p-1, 0x1.ce0a44eb17bccp-2 },
  };
  static constexpr double P[5] = { 0x1.27616c9496e0bp-2, -0x1.71969a075c67ap-2, 0x1.ec70a6ca7baddp-2,
                                   -0x1.7154748bef6c8p-1, 0x1.71547652ab82bp0 };
  static constexpr std::uint64_t E[32] = {
    0x3ff0000000000000, 0x3fefd9b0d3158574, 0x3fefb5586cf9890f, 0x3fef9301d0125b51, 0x3fef72b83c7d517b,
    0x3fef54873168b9aa, 0x3fef387a6e756238, 0x3fef1e9df51fdee1, 0x3fef06fe0a31b715, 0x3feef1a7373aa9cb,
    0x3feedea64c123422, 0x3feece086061892d, 0x3feebfdad5362a27, 0x3feeb42b569d4f82, 0x3feeab07dd485429,
    0x3feea47eb03a5585, 0x3feea09e667f3bcd, 0x3fee9f75e8ec5f74, 0x3feea11473eb0187, 0x3feea589994cce13,
    0x3feeace5422aa0db, 0x3feeb737b0cdc5e5, 0x3feec49182a3f090, 0x3feed503b23e255d, 0x3feee89f995ad3ad,
    0x3feeff76f2fb5e47, 0x3fef199bdd85529c, 0x3fef3720dcef9069, 0x3fef5818dcfba487, 0x3fef7c97337b9b5f,
    0x3fefa4afa2a490da, 0x3fefd0765b6e4540,
  };
  static constexpr double C[3] = { 0x1.c6af84b912394p-5, 0x1.ebfce50fac4f3p-3, 0x1.62e42ff0c52d6p-1 };
  const std::uint32_t ix = bits(x), iy = bits(y);
  if (ix - 0x00800000 >= 0x7f800000 - 0x00800000 || 2 * iy - 1 >= 2u * 0x7f800000 - 1) return std::pow(x, y);
  // log2_inline
  const std::uint32_t tmp = ix - 0x3f330000;
  const int i = static_cast<int>((tmp >> (23 - 4)) % 16);
  const std::uint32_t top = tmp & 0xff800000;
  const std::uint32_t iz = ix - top;
  const int k = static_cast<std::int32_t>(top) >> 23;
  const double z = static_cast<double>(fromBits(iz));
  const double r = z * T[i].invc - 1;
  const double y0 = T[i].logc + static_cast<double>(k);
  const double r2 = r * r;
  double yy = P[0] * r + P[1];
  const double p = P[2] * r + P[3];
  const double r4 = r2 * r2;
  double q = P[4] * r + y0;
  q = p * r2 + q;
  yy = yy * r4 + q;
  const double ylogx = static_cast<double>(y) * yy;
  if (((bits64(ylogx) >> 47) & 0xffff) >= (bits64(126.0) >> 47)) {
    if (ylogx > 0x1.fffffffd1d571p+6) return HUGE_VALF;
    if (ylogx <= -150.0) return 0.0f;
  }
  // exp2_inline
  constexpr double shift = 0x1.8p+52 / 32;
  double kd = ylogx + shift;
  const std::uint64_t ki = bits64(kd);
  kd -= shift;
  const double rr = ylogx - kd;
  std::uint64_t t = E[ki % 32];
  t += ki << (52 - 5);
  const double s = fromBits64(t);
  const double zz = C[0] * rr + C[1];
  const double rr2 = rr * rr;
  double e = C[2] * rr + 1;
  e = zz * rr2 + e;
  return static_cast<float>(e * s);
}

}  // namespace glibcf

/* The clamp's curve, the page's clampCurve(2048): linear below the knee and
   asymptotic to the ceiling above it, so the output cannot exceed the largest
   value in the table. The page's own words on it are in makeMonitorChain. */
constexpr double kClampKnee = 0.85, kClampCeiling = 0.99;  // CLAMP_KNEE, CLAMP_CEILING
constexpr std::size_t kClampPoints = 2048;
inline std::array<float, kClampPoints> clampCurve(double knee = kClampKnee, double ceiling = kClampCeiling) {
  std::array<float, kClampPoints> curve {};
  const double room = ceiling - knee;
  for (std::size_t i = 0; i < kClampPoints; i++) {
    const double x = (static_cast<double>(i) / (kClampPoints - 1)) * 2 - 1;
    const double size = std::fabs(x);
    const double shaped = size <= knee ? size : knee + room * std::tanh((size - knee) / room);
    curve[i] = static_cast<float>(x < 0 ? -shaped : shaped);
  }
  return curve;
}

/* One sample through a WaveShaperNode's curve with no oversampling, as
   Chromium's WaveShaperCurveValues does it in floats: the input put on the
   table's index, clipped to its ends, and the two points either side
   interpolated. */
inline float shapeBy(const std::array<float, kClampPoints>& curve, float x) {
  constexpr float scale = static_cast<float>(0.5 * (kClampPoints - 1));
  float v = (x + 1.0f) * scale;
  v = std::min(std::max(v, 0.0f), static_cast<float>(kClampPoints - 1));
  const int i1 = static_cast<int>(v);
  const int i2 = std::min(i1 + 1, static_cast<int>(kClampPoints - 1));
  const float f = v - static_cast<float>(i1);
  const float v1 = curve[static_cast<std::size_t>(std::clamp(i1, 0, static_cast<int>(kClampPoints - 1)))];
  const float v2 = curve[static_cast<std::size_t>(i2)];
  return f * (v2 - v1) + v1;
}

/* Chromium's DynamicsCompressor, two channels, at the page's settings. Its
   per-block work happens every 32 frames of its life, as the node's
   divisions fall within each 128-frame quantum, however the caller cuts its
   blocks. */
class Limiter {
 public:
  // The page's: limiter.threshold, knee, ratio, attack, release.
  static constexpr float kThreshold = -3, kKnee = 0, kRatio = 20, kAttack = 0.003f, kRelease = 0.1f;

  void prepare(double sampleRate) {
    rate_ = static_cast<float>(sampleRate);
    detector_ = 0; gain_ = 1; metering_ = 1; maxAttack_ = -1; division_ = 0;
    meteringK_ = static_cast<float>(1 - std::exp(-1 / (static_cast<double>(rate_) * static_cast<double>(kMeteringRelease))));
    unsigned frames = static_cast<unsigned>(kPreDelay * rate_);
    if (frames > kMaxPreDelay - 1) frames = kMaxPreDelay - 1;
    delay_ = static_cast<int>(frames);
    for (auto& b : buffers_) b.fill(0.0f);
    readAt_ = 0; writeAt_ = delay_;
    curve();
    postGain_ = static_cast<float>(std::pow(static_cast<double>(1 / saturate(1, k_)), static_cast<double>(0.6f)));
    attackFrames_ = std::max(0.001f, kAttack) * rate_;
    const float releaseFrames = rate_ * kRelease;
    satReleaseFrames_ = kSatRelease * rate_;
    a_ = releaseFrames * kA; b_ = releaseFrames * kB; c_ = releaseFrames * kC; d_ = releaseFrames * kD; e_ = releaseFrames * kE;
    clamp_ = clampCurve();
  }

  // How late it puts the sound: the lookahead, in frames.
  int latency() const { return delay_; }
  /* How hard it works, in dB: the node's `reduction`, nought or below once
     it has settled (it opens at one, as the node's metering does, and
     releases from there). */
  float reduction() const { return metering_; }

  /* n frames of the pair, limited and clamped in place: the node's output,
     then the shaper's, as the page's chain has them in that order. */
  void process(float* left, float* right, int n) {
    for (int k = 0; k < n; k++) {
      if (division_ == 0) divisionStart();
      float in = 0;
      float* ch[2] = { left, right };
      for (int j = 0; j < 2; j++) {
        const float x = ch[j][k];
        buffers_[static_cast<std::size_t>(j)][static_cast<std::size_t>(writeAt_)] = x;
        const float a = x > 0 ? x : -x;
        if (in < a) in = a;
      }
      const float absIn = in > 0 ? in : -in;
      const float shaped = saturate(absIn, k_);
      const float attenuation = absIn <= 0.0001f ? 1 : shaped / absIn;
      const float dbAttenuation = std::max(2.0f, -db(attenuation));
      const float dbPerFrame = dbAttenuation / satReleaseFrames_;
      const float satRate = linear(dbPerFrame) - 1;
      const float rate = attenuation > detector_ ? satRate : 1;
      detector_ += (attenuation - detector_) * rate;
      detector_ = std::min(1.0f, detector_);
      detector_ = finite(detector_, 1);
      if (envelopeRate_ < 1) {
        gain_ += (scaledDesired_ - gain_) * envelopeRate_;
      } else {
        gain_ *= envelopeRate_;
        gain_ = std::min(1.0f, gain_);
      }
      const float warped = static_cast<float>(std::sin(static_cast<double>(kPiOverTwo * gain_)));
      const float total = postGain_ * warped;
      const float dbReal = db(warped);
      if (dbReal < metering_) metering_ = dbReal;
      else metering_ += (dbReal - metering_) * meteringK_;
      for (int j = 0; j < 2; j++)
        ch[j][k] = shapeBy(clamp_, buffers_[static_cast<std::size_t>(j)][static_cast<std::size_t>(readAt_)] * total);
      readAt_ = (readAt_ + 1) & (kMaxPreDelay - 1);
      writeAt_ = (writeAt_ + 1) & (kMaxPreDelay - 1);
      if (++division_ == kDivision) {
        division_ = 0;
        detector_ = std::fabs(detector_) < FLT_MIN ? 0.0f : detector_;
        gain_ = std::fabs(gain_) < FLT_MIN ? 0.0f : gain_;
      }
    }
  }

 private:
  static constexpr float kMeteringRelease = 0.325f, kPreDelay = 0.006f, kSatRelease = 0.0025f;
  static constexpr int kMaxPreDelay = 1024, kDivision = 32;
  static constexpr float kPiOverTwo = static_cast<float>(1.57079632679489661923);
  static constexpr float kZ1 = 0.09f, kZ2 = 0.16f, kZ3 = 0.42f, kZ4 = 0.98f;
  static constexpr float kA = 0.9999999999999998f * kZ1 + 1.8432219684323923e-16f * kZ2 - 1.9373394351676423e-16f * kZ3
                              + 8.824516011816245e-18f * kZ4;
  static constexpr float kB = -1.5788320352845888f * kZ1 + 2.3305837032074286f * kZ2 - 0.9141194204840429f * kZ3
                              + 0.1623677525612032f * kZ4;
  static constexpr float kC = 0.5334142869106424f * kZ1 - 1.272736789213631f * kZ2 + 0.9258856042207512f * kZ3
                              - 0.18656310191776226f * kZ4;
  static constexpr float kD = 0.08783463138207234f * kZ1 - 0.1694162967925622f * kZ2 + 0.08588057951595272f * kZ3
                              - 0.00429891410546283f * kZ4;
  static constexpr float kE = -0.042416883008123074f * kZ1 + 0.1115693827987602f * kZ2 - 0.09764676325265872f * kZ3
                              + 0.028494263462021576f * kZ4;

  static float db(float linear) { return 20 * glibcf::log10f(linear); }
  static float linear(float decibels) { return glibcf::powf(10, 0.05f * decibels); }
  static float finite(float x, float otherwise) { return std::isfinite(x) ? x : otherwise; }

  // The node's per-division work: the gain it wants, and how fast to go there.
  void divisionStart() {
    detector_ = finite(detector_, 1);
    const float desired = detector_;
    scaledDesired_ = static_cast<float>(std::asin(static_cast<double>(desired))) / kPiOverTwo;
    const bool releasing = scaledDesired_ > gain_;
    float diff;
    if (scaledDesired_ == 0) diff = releasing ? -1 : 1;
    else diff = db(gain_ / scaledDesired_);
    if (releasing) {
      maxAttack_ = -1;
      diff = finite(diff, -1);
      float x = std::clamp(diff, -12.0f, 0.0f);
      x = 0.25f * (x + 12);
      const float x2 = x * x, x3 = x2 * x, x4 = x2 * x2;
      const float frames = a_ + b_ * x + c_ * x2 + d_ * x3 + e_ * x4;
      constexpr float kDbSpacing = 5;
      envelopeRate_ = linear(kDbSpacing / frames);
    } else {
      diff = finite(diff, 1);
      if (maxAttack_ == -1 || maxAttack_ < diff) maxAttack_ = diff;
      const float eff = std::max(0.5f, maxAttack_);
      const float x = 0.25f / eff;
      envelopeRate_ = 1 - static_cast<float>(std::pow(static_cast<double>(x), static_cast<double>(1 / attackFrames_)));
    }
  }

  float knee(float x, float k) const {
    if (x < linearThreshold_) return x;
    return linearThreshold_ + (1 - static_cast<float>(std::exp(static_cast<double>(-k * (x - linearThreshold_))))) / k;
  }
  float saturate(float x, float k) const {
    if (x < kneeThreshold_) return knee(x, k);
    const float dbX = db(x);
    const float dbY = dbYKnee_ + slope_ * (dbX - dbKneeThreshold_);
    return linear(dbY);
  }
  float kAtSlope(float desired) const {
    const float dbX = dbThreshold_ + dbKnee_;
    const float x = linear(dbX);
    float x2 = 1, dbX2 = 0;
    if (!(x < linearThreshold_)) {
      x2 = static_cast<float>(x * 1.001);
      dbX2 = db(x2);
    }
    float lo = 0.1f, hi = 10000, k = 5, slope = 1;
    for (int i = 0; i < 15; ++i) {
      if (!(x < linearThreshold_)) {
        const float dbY = db(knee(x, k)), dbY2 = db(knee(x2, k));
        slope = (dbY2 - dbY) / (dbX2 - dbX);
      }
      if (slope < desired) hi = k; else lo = k;
      k = std::sqrt(lo * hi);
    }
    return k;
  }
  void curve() {
    dbThreshold_ = kThreshold;
    linearThreshold_ = linear(kThreshold);
    dbKnee_ = kKnee;
    slope_ = 1 / kRatio;
    const float k = kAtSlope(1 / kRatio);
    dbKneeThreshold_ = kThreshold + kKnee;
    kneeThreshold_ = linear(dbKneeThreshold_);
    dbYKnee_ = db(knee(kneeThreshold_, k));
    k_ = k;
  }

  float rate_ = 48000;
  float detector_ = 0, gain_ = 1, metering_ = 1, maxAttack_ = -1, meteringK_ = 0;
  float scaledDesired_ = 0, envelopeRate_ = 1;
  float postGain_ = 1, attackFrames_ = 1, satReleaseFrames_ = 1, a_ = 0, b_ = 0, c_ = 0, d_ = 0, e_ = 0;
  float dbThreshold_ = 0, linearThreshold_ = 0, dbKnee_ = 0, slope_ = 0, dbKneeThreshold_ = 0, kneeThreshold_ = 0;
  float dbYKnee_ = 0, k_ = 0;
  int division_ = 0, delay_ = 0, readAt_ = 0, writeAt_ = 0;
  std::array<std::array<float, kMaxPreDelay>, 2> buffers_ {};
  std::array<float, kClampPoints> clamp_ {};
};

}  // namespace scope
