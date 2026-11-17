// The core's numbers in a locale of the host's (the outside review, 17 Nov):
// a plugin lives in a process whose LC_NUMERIC the host may have set, and
// strtod and printf follow it. Under de_DE the JSON parser read 0.75 as 0,
// and a preset's persistence loaded as nought.
//
//   locale_cpp LOCALE
//
// sets LC_NUMERIC to LOCALE before anything else - before the bank is parsed
// - and prints, a line each, what the core reads and writes as text: numbers
// through each of its readers and writers, every bank preset's setup encoded
// and decoded and loaded into an instrument whose sliders and state code are
// printed, and the fade's gains as the page reads them. Run once with "C" and
// once with a comma-decimal locale; core_tests.py requires the two to be the
// same line for line. The first line says what the locale's decimal point is,
// so a locale that did not take, or one with a point, is seen and the
// comparison refused rather than passed for want of a comma.
#include <clocale>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "scope/instrument.h"
#include "scope/presets.h"
#include "scope/text.h"

namespace {
// Printed in a way no locale reaches: the exact bits, and the text as written.
void num(const char* what, double x) {
  unsigned long long bits;
  static_assert(sizeof bits == sizeof x, "");
  std::memcpy(&bits, &x, sizeof x);
  std::printf("%s %016llx\n", what, bits);
}
void text(const char* what, const std::string& s) { std::printf("%s %s\n", what, s.c_str()); }
}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) { std::fprintf(stderr, "usage: locale_cpp LOCALE\n"); return 2; }
  const char* set = std::setlocale(LC_NUMERIC, argv[1]);
  std::printf("locale %s point %s\n", set ? set : "(refused)", std::localeconv()->decimal_point);
  if (!set) return 3;

  // The readers, on the text each is handed.
  for (const char* s : { "0.75", "-12.5e-3", "1e999", "4.9e-324", "0.1", "123456.789", "5.", ".5", "+0.25" }) {
    const std::string at = std::string("[") + s + "]";
    const auto j = scope::jsonParse(scope::utf8To16(at));
    num(("json " + at).c_str(), j && !j->a.empty() ? j->a[0].n : NAN);
    num((std::string("jsNumber ") + s).c_str(), scope::jsNumber(s));
    num((std::string("jsStringToNumber ") + s).c_str(), scope::jsStringToNumber(scope::utf8To16(s)));
    const scope::RangeSpec* r = scope::rangeSpec("scanMemory");
    num((std::string("rangeSanitise ") + s).c_str(), scope::rangeSanitise(*r, s));
  }
  // The writers.
  for (const double x : { 0.0625, 0.75, -2.5, 1e22, 123.456, 1.0 / 3, 6.02e23, 1e-7 }) {
    unsigned long long bits;
    std::memcpy(&bits, &x, sizeof x);
    char label[32];
    std::snprintf(label, sizeof label, "%016llx", bits);
    text((std::string("toFixed3 ") + label).c_str(), scope::jsToFixed(x, 3));
    text((std::string("toString ") + label).c_str(), scope::jsNumberToString(x));
    num((std::string("toPrecision4 ") + label).c_str(), scope::jsToPrecision4(x));
  }

  // The bank, through the codec and into an instrument.
  std::vector<float> l(512), rr(512);
  for (const auto& p : scope::presets()) {
    const auto code = scope::encodeSetup(p.setup);
    text(("code " + p.name).c_str(), code ? *code : "(none)");
    const auto back = code ? scope::decodeSetup(*code) : scope::DecodedSetup {};
    text(("decoded " + p.name).c_str(), back.kind == scope::DecodedSetup::Kind::Read
                                            ? scope::utf16To8(scope::jsonStringify(back.setup)) : "(unread)");
    scope::Instrument ins;
    ins.prepare(48000, 512, p.setup);
    for (const char* id : { "scanMemory", "pictureAmount", "vcfCut", "delayMix", "reverbMix", "amp", "oscScan" })
      num(("slider " + p.name + " " + id).c_str(), ins.slider(id));
    // A slider moved as the page writes it, and the routing's depth to the last digit.
    ins.apply(*scope::Instrument::slider("vcfCut", u"1234.5"));
    ins.apply(scope::Instrument::routings("lfo1>vcf.cut@0.375"));
    const auto fade = scope::Instrument::fade("{\"mode\":\"in\",\"envs\":{}}");
    if (fade) ins.apply(*fade);
    for (int k = 0; k < 4; ++k) ins.block(l.data(), rr.data(), 512, nullptr, 0, nullptr, nullptr, 0);
    text(("state " + p.name).c_str(), ins.stateCode());
    char served[4096];
    const std::size_t n = ins.fadeServed(served, sizeof served);
    std::string fades(served, n);
    for (auto& c : fades) if (c == '\n' || c == '\t') c = ' ';
    text(("fade " + p.name).c_str(), fades);
  }
  return 0;
}
