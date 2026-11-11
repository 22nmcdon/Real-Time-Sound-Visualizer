#include "PluginEditor.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "BinaryData.h"

namespace {
/* WebView2 on Windows, and the platform's own web view elsewhere. WebView2
   was asked for on every platform until G5b. The component never minded -
   macOS and Linux build their own whatever is asked - but areOptionsSupported
   does: on both it says yes only to the default, so from the day the editor
   began asking it (6439001, the "no web view" message) every Mac and Linux
   face was that message instead of the page. Found when the shell test first
   opened the face under a virtual display, to right-click a knob in it. */
constexpr auto kBackend =
#if JUCE_WINDOWS
    juce::WebBrowserComponent::Options::Backend::webview2;
#else
    juce::WebBrowserComponent::Options::Backend::defaultBackend;
#endif

juce::WebBrowserComponent::Options browserOptions(std::function<std::optional<juce::WebBrowserComponent::Resource>(const juce::String&)> provider,
                                                  ScopeProcessor& owner) {
  return juce::WebBrowserComponent::Options{}
      .withBackend(kBackend)
      .withWinWebView2Options(juce::WebBrowserComponent::Options::WinWebView2{}
                                  .withUserDataFolder(juce::File::getSpecialLocation(juce::File::tempDirectory)))
      .withNativeIntegrationEnabled()
      // What the page will ask first once it knows it is hosted: where it is.
      .withNativeFunction("scopeHost", [&owner](const juce::Array<juce::var>&, auto complete) {
        auto* info = new juce::DynamicObject();
        info->setProperty("host", "plugin");
        info->setProperty("rate", owner.sampleRateNow());
        info->setProperty("pictureFrames", static_cast<int>(ScopeProcessor::kPictureFrames));
        // Named here rather than assumed by the page: JUCE's resource root is
        // a different scheme on each platform.
        info->setProperty("pictureUrl", juce::WebBrowserComponent::getResourceProviderRoot() + "picture.bin");
        info->setProperty("lfosUrl", juce::WebBrowserComponent::getResourceProviderRoot() + "lfos.bin");
        complete(juce::var(info));
      })
      /* The page as the plugin's face: a slider moved, a setup loaded, a
         menu, a switch, a button, the routings, and the plugin's state for
         the page to show. */
      .withNativeFunction("scopeSlider", [&owner](const juce::Array<juce::var>& args, auto complete) {
        if (args.size() >= 2)
          owner.pageSlider(args[0].toString().toStdString(), scope::toU16(args[1].toString().toStdString()));
        complete(juce::var());
      })
      // The code, and the page's preset menu as it landed, for the program's number (G8).
      .withNativeFunction("scopeSetup", [&owner](const juce::Array<juce::var>& args, auto complete) {
        const auto code = args.isEmpty() ? std::string() : args[0].toString().toStdString();
        const auto chosen = args.size() > 1 ? args[1].toString().toStdString() : std::string();
        complete(juce::var(owner.pageSetup(code, chosen)));
      })
      // A menu's value or a text box's as text, a switch's as true or false.
      .withNativeFunction("scopeControl", [&owner](const juce::Array<juce::var>& args, auto complete) {
        if (args.size() >= 2) {
          const auto id = args[0].toString().toStdString();
          if (args[1].isBool()) owner.pageControl(id, scope::Json::boolean(static_cast<bool>(args[1])));
          else owner.pageControl(id, scope::Json::string(scope::utf8To16(args[1].toString().toStdString())));
        }
        complete(juce::var());
      })
      .withNativeFunction("scopeClick", [&owner](const juce::Array<juce::var>& args, auto complete) {
        if (!args.isEmpty()) owner.pageClick(args[0].toString().toStdString());
        complete(juce::var());
      })
      .withNativeFunction("scopeFade", [&owner](const juce::Array<juce::var>& args, auto complete) {
        owner.pageFade(args.isEmpty() ? std::string() : args[0].toString().toStdString());
        complete(juce::var());
      })
      .withNativeFunction("scopeRoutings", [&owner](const juce::Array<juce::var>& args, auto complete) {
        owner.pageRoutings(args.isEmpty() ? std::string() : args[0].toString().toStdString());
        complete(juce::var());
      })
      .withNativeFunction("scopeState", [&owner](const juce::Array<juce::var>&, auto complete) {
        const auto state = owner.pageState();
        auto* out = new juce::DynamicObject();
        out->setProperty("version", state.version);
        out->setProperty("loads", state.loads);
        out->setProperty("moved", juce::String(state.moved));
        out->setProperty("code", juce::String(state.code));
        complete(juce::var(out));
      })
      .withNativeFunction("scopeReport", [&owner](const juce::Array<juce::var>& args, auto complete) {
        const auto json = args.isEmpty() ? juce::String() : juce::JSON::toString(args[0], true);
        owner.setPictureReport(json);
        if (std::getenv("SCOPE_REPORT") != nullptr) std::fprintf(stderr, "scope report %s\n", json.toRawUTF8());
        complete(juce::var());
      })
      .withResourceProvider(std::move(provider));
}

const std::string& servedPage() {
  static const std::string page = asciiPage(BinaryData::scope_html, static_cast<std::size_t>(BinaryData::scope_htmlSize));
  return page;
}

juce::WebBrowserComponent::Resource bytes(const void* data, std::size_t size, const char* mime) {
  juce::WebBrowserComponent::Resource out;
  out.data.resize(size);
  std::memcpy(out.data.data(), data, size);
  out.mimeType = mime;
  return out;
}
}  // namespace

ScopeEditor::ScopeEditor(ScopeProcessor& owner)
    : AudioProcessorEditor(owner),
      processor_(owner),
      browser_(browserOptions([this](const juce::String& path) { return scopeResource(path, processor_); }, owner)) {
  /* Without a web view there is no face: Windows without the WebView2
     runtime, a Linux without WebKitGTK. It used to be a blank window; it says
     so now, and that the sound and the host's parameters go on working. */
  const bool supported = juce::WebBrowserComponent::areOptionsSupported(
      browserOptions([](const juce::String&) { return std::optional<juce::WebBrowserComponent::Resource> {}; }, owner));
  face_ = supported;
  if (supported) {
    addAndMakeVisible(browser_);
  } else {
    missing_.setText("The plugin's face is a web page, and this computer has no web view for it to open in"
                     " (on Windows, Microsoft's WebView2 runtime). The instrument still plays, and the host's"
                     " parameters and presets still work.", juce::dontSendNotification);
    missing_.setJustificationType(juce::Justification::centred);
    addAndMakeVisible(missing_);
  }
  /* Where it was left, or a size inside a 1366x768 laptop's screen with a
     host's frame round it - read before anything can resize the editor.
     It used to be read after setResizeLimits, which in JUCE ends with
     setBoundsConstrained(getBounds()): the editor, still 0x0, was clamped up
     to the 960x600 minimum, resized() stored that over the remembered size,
     and the face opened at 960x600 every time, whatever it had been left at
     and whatever the default said. */
  const auto [w, h] = owner.windowSize();
  setSize(w, h);
  setResizable(true, true);
  setResizeLimits(960, 600, 2560, 1600);
  if (supported) browser_.goToURL(juce::WebBrowserComponent::getResourceProviderRoot());
}

void ScopeEditor::resized() {
  browser_.setBounds(getLocalBounds());
  missing_.setBounds(getLocalBounds().reduced(40));
  processor_.setWindowSize(getWidth(), getHeight());
}

std::optional<juce::WebBrowserComponent::Resource> scopeResource(const juce::String& path, const ScopeProcessor& processor) {
  if (path == "/" || path == "/index.html" || path == "/scope.html") {
    /* As ASCII, and with the charset said in the type as well. Served
       through WebKitGTK's custom scheme the page was read as Latin-1 whatever
       its meta or the Content-Type said - the markup survived, being ASCII
       with entities, and the forty-odd characters in the script's strings
       came out as two or three characters of rubbish each: a middle dot as
       "A-circumflex, middle dot". A page with nothing past ASCII in it cannot
       be decoded wrongly by anyone. */
    const auto& page = servedPage();
    return bytes(page.data(), page.size(), "text/html; charset=utf-8");
  }
  // The picture: the last frames played, as little-endian float32, its lanes
  // interleaved - left and right, or the band split's four - fetched by the
  // page each frame it draws, which reads the lane count off the length.
  if (path == "/picture.bin") {
    const auto frames = processor.pictureServed();
    return bytes(frames.data(), frames.size() * sizeof(float), "application/octet-stream");
  }
  /* The two oscillators as they stood at the picture's newest frame, as six
     little-endian float64s - each one's phase, held value and value - which
     the page fetches after the picture and makes its own, so the picture's
     destinations move with the oscillators that move the sound. Apart from
     the picture so that its length goes on saying how many lanes it has. */
  if (path == "/lfos.bin") {
    const auto lfos = processor.lfosServed();
    return bytes(lfos.data(), lfos.size() * sizeof(double), "application/octet-stream");
  }
  return std::nullopt;
}

std::string asciiPage(const char* utf8, std::size_t size) {
  std::string out;
  out.reserve(size + size / 16);
  bool inScript = false;
  char escape[16];
  for (std::size_t i = 0; i < size;) {
    const auto c = static_cast<unsigned char>(utf8[i]);
    if (c < 0x80) {
      // Where a script starts and stops, so each character is escaped in the
      // language it is written in.
      if (c == '<') {
        if (!inScript && size - i >= 7 && std::strncmp(utf8 + i, "<script", 7) == 0) inScript = true;
        else if (inScript && size - i >= 9 && std::strncmp(utf8 + i, "</script", 8) == 0) inScript = false;
      }
      out.push_back(static_cast<char>(c));
      ++i;
      continue;
    }
    // One UTF-8 sequence, decoded to its code point.
    const int extra = c >= 0xF0 ? 3 : c >= 0xE0 ? 2 : 1;
    unsigned long point = c & (extra == 3 ? 0x07u : extra == 2 ? 0x0Fu : 0x1Fu);
    for (int k = 1; k <= extra && i + static_cast<std::size_t>(k) < size; ++k)
      point = (point << 6) | (static_cast<unsigned char>(utf8[i + static_cast<std::size_t>(k)]) & 0x3Fu);
    i += static_cast<std::size_t>(extra) + 1;
    if (!inScript) {
      std::snprintf(escape, sizeof escape, "&#x%lX;", point);
      out += escape;
    } else if (point > 0xFFFF) {
      // Past the first plane, JavaScript's escape is a surrogate pair.
      const unsigned long v = point - 0x10000;
      std::snprintf(escape, sizeof escape, "\\u%04lX\\u%04lX", 0xD800 + (v >> 10), 0xDC00 + (v & 0x3FF));
      out += escape;
    } else {
      std::snprintf(escape, sizeof escape, "\\u%04lX", point);
      out += escape;
    }
  }
  return out;
}
