// The instrument's core played offline for the painting study: a script in
// instrument_cpp.cpp's format (only "make", "midi" and "block" are needed
// here), and out, instead of text, the heard pair as raw float32 stereo and a
// log of what the core knows of its voices, one line per block:
//
//   t  coverA coverB  |  layer note hz level held ; ...
//
// so the painting reads what the instrument itself holds - which note each
// voice is, where its glide has got to, how loud its envelope is, whether the
// key is still down - rather than guessing it back from the audio. A copy of
// instrument_cpp's loop rather than a change to it: the study changes nothing.
#include <cstdio>
#include <fstream>
#include <string>
#include <vector>

#include "scope/instrument.h"

namespace {
std::string text(const scope::Json& v) { return v.type == scope::Json::Type::String ? scope::utf16To8(v.s) : std::string(); }
}

int main(int argc, char** argv) {
  if (argc < 4) { std::fprintf(stderr, "usage: render <script> <audio.f32> <voices.txt>\n"); return 2; }
  std::ifstream file(argv[1]);
  std::FILE* audio = std::fopen(argv[2], "wb");
  std::FILE* log = std::fopen(argv[3], "w");
  scope::Instrument instrument;
  std::vector<std::uint8_t> midi;
  std::vector<std::size_t> lengths;
  double rate = 48000;
  long long frames = 0;
  for (std::string line; std::getline(file, line);) {
    if (line.empty()) continue;
    const auto parsed = scope::jsonParse(scope::utf8To16(line));
    if (!parsed || parsed->type != scope::Json::Type::Array || parsed->a.empty()) { std::fprintf(stderr, "bad line\n"); return 2; }
    const auto& a = parsed->a;
    const std::string cmd = text(a[0]);
    if (cmd == "make") {
      rate = a[1].n;
      const auto setup = scope::Instrument::setup(text(a[3]));
      if (!setup) { std::fprintf(stderr, "setup refused\n"); return 2; }
      instrument.prepare(rate, static_cast<int>(a[2].n), *setup->setup);
    } else if (cmd == "midi") {
      for (std::size_t i = 1; i < a.size() && i < 4; ++i) midi.push_back(static_cast<std::uint8_t>(a[i].n));
      lengths.push_back(std::min<std::size_t>(a.size() - 1, 3));
    } else if (cmd == "block") {
      const std::size_t n = static_cast<std::size_t>(a[1].n);
      std::vector<float> l(n), r(n), inter(2 * n);
      std::vector<scope::Instrument::Event> events;
      std::size_t at = 0;
      for (const std::size_t length : lengths) { events.push_back({ 0, midi.data() + at, length }); at += length; }
      instrument.block(l.data(), r.data(), static_cast<int>(n), events.data(), events.size(), nullptr, nullptr, 0, nullptr);
      midi.clear(); lengths.clear();
      for (std::size_t k = 0; k < n; ++k) { inter[2 * k] = l[k]; inter[2 * k + 1] = r[k]; }
      std::fwrite(inter.data(), sizeof(float), inter.size(), audio);
      frames += static_cast<long long>(n);
      const auto& layers = instrument.layerPictures();
      std::fprintf(log, "%.6f %.6g %.6g |", frames / rate, layers.pictures(0).raw().cover, layers.pictures(1).raw().cover);
      const auto& g = instrument.generator();
      for (int layer = 0; layer < 2; ++layer)
        for (const auto& v : layer ? g.voicesB() : g.voices())
          if (!v.gone) std::fprintf(log, " %d %d %.4f %.5f %d ;", layer, v.note, v.hz > 0 ? v.hz : v.freq, v.env.level(), v.held ? 1 : 0);
      std::fprintf(log, "\n");
    } else { std::fprintf(stderr, "unknown command %s\n", cmd.c_str()); return 2; }
  }
  std::fclose(audio); std::fclose(log);
  return 0;
}
