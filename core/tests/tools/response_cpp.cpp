// How the picture responds (11 Nov, web/docs/the-picture-amount.md), heard:
// the instrument (scope/instrument.h) rendering a setup through a sequence of
// MIDI messages at their own moments, a 128-frame step at a time at 48 kHz,
// as the study rendered the owner's sequence. web/tests/responsetest.py runs
// it and judges what it prints.
//
//   response_cpp CODE PATCH EVENTS SECONDS
//
// CODE is a setup code; PATCH a JSON object of fields laid over it (the
// Responds to, the amount, the Picture moves...); EVENTS a file of lines
// `seconds status data1 data2`. Out, one line each:
//
//   level T DB                  the heard pair's level over the quarter second from T
//   band T TOTAL HIGH           a 4096-sample window from T, Hann-windowed: the left
//                               channel's energy, and the part of it above 1 kHz
//   stage T LIVE A... B...      every eighth step: each hand's picture's glow, level,
//                               change, motion and hold, and whether the hands have
//                               pictures of their own
#include <cmath>
#include <complex>
#include <cstdio>
#include <fstream>
#include <string>
#include <vector>

#include "scope/instrument.h"

namespace {

// A radix-2 FFT, in place, for the band split: nothing here needs to be fast.
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

}  // namespace

int main(int argc, char** argv) {
  if (argc < 5) { std::fprintf(stderr, "usage: response_cpp CODE PATCH EVENTS SECONDS\n"); return 2; }
  const auto command = scope::Instrument::setup(argv[1]);
  if (!command) { std::fprintf(stderr, "the code does not read\n"); return 2; }
  scope::Json setup = *command->setup;
  const auto patch = scope::jsonParse(scope::utf8To16(argv[2]));
  if (!patch || patch->type != scope::Json::Type::Object) { std::fprintf(stderr, "the patch is not an object\n"); return 2; }
  for (const auto& kv : patch->o) setup.set(kv.first, kv.second);
  struct Message { double t; std::uint8_t bytes[3]; };
  std::vector<Message> messages;
  {
    std::ifstream file(argv[3]);
    double t;
    int a, b, c;
    while (file >> t >> a >> b >> c)
      messages.push_back({ t, { static_cast<std::uint8_t>(a), static_cast<std::uint8_t>(b), static_cast<std::uint8_t>(c) } });
  }
  constexpr double kRate = 48000;
  constexpr int kStep = 128, kWindow = 4096;
  const long total = static_cast<long>(std::atof(argv[4]) * kRate);
  scope::Instrument instrument;
  instrument.prepare(kRate, kStep, setup);
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
