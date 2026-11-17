// Numbers to characters and back, the same in every locale.
//
// strtod, atof and printf's %f, %e and %g follow LC_NUMERIC, and a host is
// free to set it: under de_DE a JSON parser built on strtod read 0.75 as 0
// (it stopped at the point, which there is not the decimal separator) and a
// preset's persistence loaded as nought (the outside review, 17 Nov). The
// page has no locale - JavaScript's numbers are written one way - so the core
// must not have one either. Every number the core reads from text or writes
// as text goes through here; `localetest` (`core/tests/tools/locale_cpp.cpp`)
// runs the codecs under a comma-decimal locale to hold it.
//
// Writing uses std::to_chars with a precision, which the standard defines as
// printf's in the C locale, so the characters are the same as the snprintf
// they replace and no recording moves. Reading uses strtod in the C locale
// rather than std::from_chars, which is the other way it could have gone:
// from_chars for doubles is not in the libc++ the page's core is built with
// (18) nor in older Apple ones, and it reports a range error where strtod
// answers infinity or nought, so it would have meant a second rounding of the
// edges to keep the recordings still. strtod_l with a C locale is the same
// function, rounding and range behaviour as before, just told which locale.

#pragma once

#include <charconv>
#include <cstddef>
#include <cstdlib>
#include <string>
#include <string_view>

#if defined(_WIN32)
#include <locale.h>
#elif defined(__wasi__) || defined(__EMSCRIPTEN__)
// The WASI libc (musl) has only the C locale's numbers: strtod is already proof.
#else
#include <locale.h>
#if defined(__APPLE__)
#include <xlocale.h>
#endif
#endif

namespace scope {

/* strtod of the whole text in the C locale: as far as it reads, 0 when
   nothing does. The text is copied to a terminated buffer on the stack, so
   the audio thread can call it; a longer one (no number the core reads is)
   is read from its first 255 characters. */
inline double readDouble(std::string_view text) {
  char buf[256];
  const std::size_t n = text.size() < sizeof buf - 1 ? text.size() : sizeof buf - 1;
  for (std::size_t i = 0; i < n; ++i) buf[i] = text[i];
  buf[n] = '\0';
#if defined(_WIN32)
  static const _locale_t c = _create_locale(LC_NUMERIC, "C");
  return _strtod_l(buf, nullptr, c);
#elif defined(__wasi__) || defined(__EMSCRIPTEN__)
  return std::strtod(buf, nullptr);
#else
  // Made once, on the first number read; the codecs read one long before
  // any block is played.
  static const locale_t c = newlocale(LC_NUMERIC_MASK, "C", static_cast<locale_t>(0));
  return strtod_l(buf, nullptr, c);
#endif
}

/* snprintf's "%.{precision}{g|f|e}" into `out`, terminated, in the C locale:
   the length is returned, as snprintf's would be when it fits. `room` is the
   caller's to make large enough (a %.200f of a number under 1e21 is 222). */
inline std::size_t writeDouble(char* out, std::size_t room, double x, std::chars_format format, int precision) {
  const auto r = std::to_chars(out, out + room - 1, x, format, precision);
  if (r.ec != std::errc()) { out[0] = '\0'; return 0; }
  *r.ptr = '\0';
  return static_cast<std::size_t>(r.ptr - out);
}

}  // namespace scope
