// The core's setup codes through the same commands as setup_js.mjs, one
// result line per command. See that file for the language.
#include <cstdio>
#include <fstream>
#include <string>

#include "scope/setup.h"

namespace {
std::string ascii(const std::u16string& s) {
  std::string out;
  for (const char16_t c : s) {
    if (c < 0x80) { out += static_cast<char>(c); continue; }
    char b[16];
    std::snprintf(b, sizeof b, "{u+%04x}", static_cast<unsigned>(c));
    out += b;
  }
  return out;
}
}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) { std::fprintf(stderr, "usage: setup_cpp <commands>\n"); return 2; }
  std::ifstream file(argv[1]);
  for (std::string line; std::getline(file, line);) {
    if (line.empty()) continue;
    const auto space = line.find(' ');
    const std::string cmd = line.substr(0, space), rest = space == std::string::npos ? "" : line.substr(space + 1);
    if (cmd == "defaults") std::printf("%s\n", ascii(scope::jsonStringify(scope::setupDefaults())).c_str());
    else if (cmd == "encode") {
      const auto snap = scope::jsonParse(scope::utf8To16(rest));
      const auto code = snap ? scope::encodeSetup(*snap) : std::nullopt;
      // JSON.parse throws on what does not parse, and the snapshot then never
      // reaches encodeSetup: both are a throw from the page's side.
      std::printf("%s\n", code ? ("code " + *code).c_str() : "throws");
    } else if (cmd == "decode") {
      const auto d = scope::decodeSetup(rest);
      if (d.kind == scope::DecodedSetup::Kind::Unreadable) std::printf("unreadable\n");
      else if (d.kind == scope::DecodedSetup::Kind::Throws) std::printf("throws\n");
      else std::printf("read %s\n", ascii(scope::jsonStringify(d.setup)).c_str());
    } else { std::fprintf(stderr, "unknown command %s\n", cmd.c_str()); return 2; }
  }
  return 0;
}
