// What a held note does to the sound, read as web/tests/honestytest.py reads
// it: the instrument (scope/instrument.h) loaded with a setup code, left
// alone for PRE seconds as the page leaves a preset before the key, the
// notes struck at velocity 100 and held HOLD seconds, then let go and
// listened to for AFTER seconds, a 128-frame step at a time with each note at
// its own sample. Every quarter second of the instrument's own samples from
// the key, the picture's left lane (a split's two hands' summed) is read as
// the suite's RUN reads the page's ring: the movement between a window and
// the one a quarter second before it, and the newer window's RMS.
//
//   honesty_cpp CODE RATE NOTES PRE HOLD AFTER     NOTES as 48,67
//
// Out, a line a reading: `read T PHASE MOVE RMS`, T in seconds from the key,
// PHASE held or after, MOVE nought on the first reading, which has no last.
//
// Why offline (13 Nov): on the page the same sound read 0.0100 to 0.019 late
// from run to run, because the loop through the picture is fed back, and on
// the page the key, each frame's messages and the timer's reads all land
// wherever the browser's timing puts them, in a sound that magnifies small
// differences. Here every one of them is at a stated sample, so a run is the
// same to the bit every time, and parity holds the page's instrument to this
// one sample for sample.
#include <cmath>
#include <complex>
#include <cstdio>
#include <cstdlib>
#include <sstream>
#include <string>
#include <vector>

#include "scope/instrument.h"

namespace {

// The suite's spectrum to the letter: a Hann window over n - 1, a radix-2
// FFT, forty-eight bands a fifth of an octave wide from 40 Hz, each band's
// share of the whole as an amplitude. The band edges count bins at 44.1 kHz
// whatever the rate, as the page's copy always has; the thresholds were set
// on readings made that way, so this keeps them.
std::vector<double> spectrum(const float* x, int n) {
  std::vector<std::complex<double>> a(static_cast<std::size_t>(n));
  for (int i = 0; i < n; i++)
    a[static_cast<std::size_t>(i)] = x[i] * (0.5 - 0.5 * std::cos(2 * M_PI * i / (n - 1)));
  for (int i = 1, j = 0; i < n; i++) {
    int bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) std::swap(a[static_cast<std::size_t>(i)], a[static_cast<std::size_t>(j)]);
  }
  for (int len = 2; len <= n; len <<= 1) {
    const double ang = -2 * M_PI / len;
    for (int i = 0; i < n; i += len)
      for (int k = 0; k < len / 2; k++) {
        const std::complex<double> w(std::cos(ang * k), std::sin(ang * k));
        const auto u = a[static_cast<std::size_t>(i + k)], v = a[static_cast<std::size_t>(i + k + len / 2)] * w;
        a[static_cast<std::size_t>(i + k)] = u + v;
        a[static_cast<std::size_t>(i + k + len / 2)] = u - v;
      }
  }
  std::vector<double> bands(48, 0.0);
  for (int k = 1; k < n / 2; k++) {
    const double f = k * 44100.0 / n;
    if (f < 40) continue;
    bands[static_cast<std::size_t>(std::min(47, static_cast<int>(std::floor(std::log2(f / 40) * 5))))] += std::norm(a[static_cast<std::size_t>(k)]);
  }
  double total = 0;
  for (double v : bands) total += v;
  for (double& v : bands) v = total > 0 ? std::sqrt(v / total) : 0;
  return bands;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc < 7) { std::fprintf(stderr, "usage: honesty_cpp CODE RATE NOTES PRE HOLD AFTER\n"); return 2; }
  const auto command = scope::Instrument::setup(argv[1]);
  if (!command) { std::fprintf(stderr, "the code does not read\n"); return 2; }
  const double rate = std::atof(argv[2]);
  std::vector<int> notes;
  {
    std::stringstream list(argv[3]);
    for (std::string n; std::getline(list, n, ',');) notes.push_back(std::atoi(n.c_str()));
  }
  const double pre = std::atof(argv[4]), hold = std::atof(argv[5]), after = std::atof(argv[6]);
  constexpr int kStep = 128, kWindow = 4096;
  const int gap = static_cast<int>(std::lround(rate / 4));
  const int reach = kWindow + gap;

  scope::Instrument instrument;
  instrument.prepare(rate, kStep, *command->setup);
  std::vector<float> left(kStep), right(kStep), a0(kStep), a2(kStep);
  /* The picture's left lane over the whole run, kept here: the instrument's
     ring is 8192 frames, shorter than a reading's two windows a quarter
     second apart, which the page's ring holds. */
  std::vector<float> lane;

  const long keyAt = static_cast<long>(std::lround(pre * rate));
  const long upAt = keyAt + static_cast<long>(std::lround(hold * rate));
  const long end = upAt + static_cast<long>(std::lround(after * rate));
  const long quarter = gap;
  std::vector<std::uint8_t> bytes;
  bool first = true;
  long nextRead = keyAt + quarter;
  for (long at = 0; at < end; at += kStep) {
    // Each message on its own sample inside the step that holds it.
    bytes.clear();
    std::vector<scope::Instrument::Event> events;
    const auto put = [&](long when, std::uint8_t status, std::uint8_t velocity) {
      if (when < at || when >= at + kStep) return;
      for (int n : notes) { bytes.push_back(status); bytes.push_back(static_cast<std::uint8_t>(n)); bytes.push_back(velocity); }
    };
    put(keyAt, 0x90, 100);
    const std::size_t downs = bytes.size();
    put(upAt, 0x80, 0);
    for (std::size_t i = 0; i < bytes.size(); i += 3)
      events.push_back({ static_cast<int>((i < downs ? keyAt : upAt) - at), bytes.data() + i, 3 });
    instrument.block(left.data(), right.data(), kStep, events.data(), events.size(), nullptr, nullptr, 0, nullptr);
    const long done = at + kStep;
    /* A read falls on a whole quarter second from the key, and is taken at
       the end of the step that holds that sample, as the page's ring can
       only be read between blocks: at most 127 samples late, and by the
       same amount every run. */
    // A split hands back a pair a layer; heard, they are summed.
    instrument.latestLane(0, a0.data(), kStep);
    const bool split = instrument.pictureLanes() >= 4;
    if (split) instrument.latestLane(2, a2.data(), kStep);
    for (int k = 0; k < kStep; k++) lane.push_back(a0[static_cast<std::size_t>(k)] + (split ? a2[static_cast<std::size_t>(k)] : 0.0f));
    while (nextRead <= done && nextRead <= end) {
      const float* w = lane.data() + lane.size() - static_cast<std::size_t>(reach);
      double e = 0;
      for (int k = gap; k < reach; k++) e += static_cast<double>(w[k]) * w[k];
      double move = 0;
      if (!first) {
        const auto a = spectrum(w, kWindow), b = spectrum(w + gap, kWindow);
        for (std::size_t k = 0; k < a.size(); k++) move += (b[k] - a[k]) * (b[k] - a[k]);
        move = std::sqrt(move);
      }
      first = false;
      const double t = static_cast<double>(nextRead - keyAt) / rate;
      std::printf("read %.6f %s %.9f %.9f\n", t, nextRead <= upAt ? "held" : "after", move, std::sqrt(e / kWindow));
      nextRead += quarter;
    }
  }
  return 0;
}
