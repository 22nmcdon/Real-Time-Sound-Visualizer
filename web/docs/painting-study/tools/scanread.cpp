// Scan's read of a painting, by the core's own functions (scope/scan.h): for
// each 64-by-64 grid of ink density in, the figure's centre and radius
// (scanGeometry), the grid blurred by the Softness (scanBlur), the 256 points
// round the off-centre circle (scanRead) and the wavetable they make
// (scanTables, its richest level, 512 samples, peak one). Nothing is
// reimplemented, so this is what the instrument would make of the grid; what
// it cannot say is how the instrument's grid would come to hold a painting,
// which is the study's assumption (painting-the-sound.md, What the study found).
//
//   scanread <grids.f32> <soft> <out.f32>      out: per grid, ok cx cy r then 512 samples
#include <cstdio>
#include <vector>

#include "scope/scan.h"

int main(int argc, char** argv) {
  if (argc < 4) { std::fprintf(stderr, "usage: scanread <grids.f32> <soft> <out.f32>\n"); return 2; }
  const double soft = std::atof(argv[2]);
  std::FILE* in = std::fopen(argv[1], "rb");
  std::FILE* out = std::fopen(argv[3], "wb");
  constexpr int n = scope::kPhosphorN;
  std::vector<float> grid(n * n);
  std::vector<double> rows(n * n), blurred(n * n);
  std::array<double, scope::kScanPoints> points {};
  auto tables = scope::scanTableSet();
  while (std::fread(grid.data(), sizeof(float), grid.size(), in) == grid.size()) {
    std::vector<float> rec(4 + scope::kScanTable, 0.0f);
    const auto path = scope::scanGeometry(grid.data(), grid.size());
    if (path) {
      scope::scanBlur(grid.data(), n, soft, rows.data(), blurred.data());
      scope::scanRead(blurred.data(), n, *path, points);
      const bool ok = scope::scanTables(points, tables);
      rec[0] = ok ? 1.0f : 0.0f;
      rec[1] = static_cast<float>(path->cx); rec[2] = static_cast<float>(path->cy); rec[3] = static_cast<float>(path->r);
      if (ok) for (std::size_t i = 0; i < scope::kScanTable; i++) rec[4 + i] = static_cast<float>(tables.levels[0][i]);
    }
    std::fwrite(rec.data(), sizeof(float), rec.size(), out);
  }
  std::fclose(in); std::fclose(out);
  return 0;
}
