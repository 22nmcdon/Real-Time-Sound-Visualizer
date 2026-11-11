#pragma once

#include <juce_gui_extra/juce_gui_extra.h>

#include "PluginProcessor.h"

// The editor is a web view and nothing else: the page is the UI. It serves
// the page from the binary, and the samples to draw from the processor, both
// through JUCE's resource provider, so nothing the page asks for leaves the
// plugin. The page cannot tell it is in a plugin yet (PLAN.md, stage 1).
// What the page asks for, answered: the page itself, and the picture. A free
// function rather than a member so a test can ask without a web view.
std::optional<juce::WebBrowserComponent::Resource> scopeResource(const juce::String& path, const ScopeProcessor&);

// The page as pure ASCII: every character past it written as the escape that
// means the same thing where it stands - `\uXXXX` inside a script, `&#xXXXX;`
// in the markup. See scopeResource for why the plugin cannot serve it as it is.
std::string asciiPage(const char* utf8, std::size_t size);

class ScopeEditor final : public juce::AudioProcessorEditor {
 public:
  explicit ScopeEditor(ScopeProcessor& owner);
  // A gesture the page left open - the window closed mid-drag - is ended as the face goes.
  ~ScopeEditor() override { processor_.endGestures(); }
  void resized() override;
  /* For the shell test, which opens the face under a virtual display: whether
     there is a web view, and a script run in the page with what it returns. */
  bool hasFace() const { return face_; }
  void evaluate(const juce::String& script, juce::WebBrowserComponent::EvaluationCallback done) {
    browser_.evaluateJavascript(script, std::move(done));
  }

 private:
  ScopeProcessor& processor_;
  bool face_ = false;
  juce::WebBrowserComponent browser_;
  juce::Label missing_;  // said instead of the face where there is no web view

  JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(ScopeEditor)
};
