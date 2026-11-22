// Apple only, and called only from a Debug build (PluginEditor.cpp says why):
// WKWebView's inspectable switch, which needs Objective-C and the macOS 13.3
// SDK. Kept apart from JUCE so the file is a dozen lines of Cocoa.
#import <WebKit/WebKit.h>

bool scopeMarkWebViewsInspectable(void* nsView);  // declared again in PluginEditor.cpp, which calls it

static bool markInspectable(NSView* view) {
  bool any = false;
  if ([view isKindOfClass:[WKWebView class]]) {
    if (@available(macOS 13.3, *)) {
      ((WKWebView*) view).inspectable = YES;
      any = true;
    }
  }
  for (NSView* child in [view subviews]) any = markInspectable(child) || any;
  return any;
}

bool scopeMarkWebViewsInspectable(void* nsView) {
  return nsView != nullptr && markInspectable((__bridge NSView*) nsView);
}
