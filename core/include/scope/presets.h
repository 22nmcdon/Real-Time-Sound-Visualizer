// The preset library as the page ships it: each section's name and what it
// plays on, and each preset's name, setup and the line that says what to
// listen for. Written out from the page's PRESETS (the JSON below, as the page
// evaluates it) and held to it by core/tests/parity.py, preset for preset and
// field for field, so a preset changed on the page and not here is a failure,
// not a drift.
//
// In pieces rather than one literal: the whole is past what MSVC takes in one
// string, and the Windows build is still to come. They are joined and read
// once, the first time the library is asked for.

#pragma once

#include <string>
#include <string_view>
#include <vector>

#include "scope/json.h"

namespace scope {

struct Preset {
  std::string section, kind;  // the section's name, and "generator" or "display"
  std::string name;
  Json setup;
  std::u16string blurb;
};

inline const std::vector<Preset>& presets() {
  static const std::vector<Preset> list = [] {
    static const char* const pieces[] = {
      R"preset([["Settled",[["Tine piano",{"shape":"sine","freq":220,"timebase":3,"midiMode":"poly","oscRatio":1,"oscFm":8,"vcfType":1,"vcfCut":700,"atk":1,"dec":1000,"sus":25,"rel":500,"mod":"env.note>gen.fm@0.400;midi.key>gen.fm@0.300","display":"xy","persistence":"0.3","oscScan":50,"scanStrike":100,"pictureAmount":0,"polyRound":true},"An electric piano after the Rhodes: it barks when struck, harder the harder you play, and mellows as it rings, half its wave read back off its own figure. Each key strikes the figure where Scan reads it, so the tone flares and settles as the light fades, and a held chord goes still."],["Drawbar organ",{"shape":"drawbars","bars":"888000000","freq":220,"timebase":6,"midiMode":"poly","atk":2,"dec":120,"sus":100,"rel":80,"display":"xy","persistence":"0.3","oscScan":14,"scanStrike":100,"pictureAmount":0,"polyRound":true},"The first three drawbars all the way out, the jazz organist's registration, with a little of the wave read off the screen. Every key strikes the figure, so the tone clicks brighter for a moment, as an organ's percussion does, and then holds."],["Bass under the tine piano",{"shape":"sine","freq":110,"timebase":6,"midiMode":"poly","layers":"split","splitAt":55,"layerPair":"each","atk":2,"dec":500,"sus":70,"rel":150,"bShape":"sine","bRatio":1,"bFm":8,"bVcf":1,"bVcfCut":700,"bAtk":1,"bDec":1000,"bSus":25,"bRel":500,"mod":"env.note>gen.fm@0.400;midi.key>gen.fm@0.300","display":"xy","persistence":"0.3","oscScan":20,"bScan":45,"scanStrike":100,"pictureAmount":0,"polyRound":true},"Split at G3: a round sine bass under the left hand, the tine piano over the right, each hand drawing its own figure. Every note flares where it strikes its figure and comes to rest, the bass more gently than the keys."]],"generator"],["Breathing",[["Harmonic tone",{"timebase":3,"pictureAmount":60},"The sound the page opens on: a sine with a little of its third harmonic, the colour of a flute or a soft organ pipe, with the picture stage at its default. How much of the screen is lit folds it and how fast the picture changes echoes it, so a held note keeps moving until you let go."],["Slow pad",{"shape":"ramp","freq":220,"timebase":3,"midiMode":"poly","amp":28,"vcfType":1,"vcfCut":560,"vcfRes":15,"atk":200,"dec":800,"sus":80,"rel":1500,"display":"xy","persistence":"0.12","oscScan":60,"scanStrike":40,"pictureAmount":100,"polyRound":true},"A low-passed saw that swells in slowly, with the picture at full. As a held chord's figure repeats itself, Memory pushes the phaser and the twist, which open the figure out and change what Scan reads off it, so the chord keeps turning over until you let go."],["Turning fifths",{"shape":"sine","freq":220,"timebase":3,"midiMode":"poly","amp":40,"just":false,"atk":30,"dec":600,"sus":80,"rel":800,"display":"xy","persistence":"0.12","oscScan":60,"scanStrike":60,"pictureAmount":30,"polyRound":true},"Sines in equal temperament, whose fifths are a hair narrow of still. Play fifths: the figure turns at the rate they beat, and the wave Scan reads off it turns with it, so a held fifth breathes. Lower down it turns slower."],["Bass under the pad",{"shape":"ramp","freq":110,"timebase":4,"midiMode":"poly","layers":"split","splitAt":55,"layerPair":"each","amp":45,"bAmp":40,"vcfType":1,"vcfCut":450,"vcfRes":30,"vcfEnvAmt":20,"vcfDec":250,"vcfSus":20,"atk":2,"dec":400,"sus":70,"rel":200,"bShape":"ramp","bVcf":1,"bVcfCut":560,"bVcfRes":15,"bAtk":200,"bDec":800,"bSus":80,"bRel":1500,"display":"xy","persistence":"0.12","oscScan":25,"bScan":60,"scanStrike":40,"pictureAmount":80,"polyRound":true},"Split at G3: a filtered saw bass under the left hand, its filter opening on every note, and the slow pad over the right, each drawn as its own figure and each moved by its own picture, so both keep moving while you hold them."],["Crossed hands",{"shape":"sine","freq":110,"timebase":4,"display":"xy","persistence":"0.0255","midiMode":"poly","layers":"split","splitAt":60,"layerPair":"each","oscScan":100,"bScan":100,"scanReadsA":"B","scanReadsB":"A","bShape":"sine","bRatio":1,"pictureAmount":60,"polyRound":true},"Each hand's sound is read from the other hand's picture: the left hand's wave is the right hand's figure and the right's is the left's, so neither can be played without the other answering, and a chord held in each half keeps changing. Hold the pedal and it goes on as long as you like."]],"generator"]])preset",
    };
    std::string text;
    for (const char* piece : pieces) text += piece;
    std::vector<Preset> out;
    const Json library = *jsonParse(utf8To16(text));  // held: a range over a temporary's member dangles
    for (const auto& section : library.a) {
      const std::string name = utf16To8(section.a[0].s);
      const std::string kind = section.a.size() > 2 ? utf16To8(section.a[2].s) : "";
      for (const auto& entry : section.a[1].a) {
        out.push_back({ name, kind, utf16To8(entry.a[0].s), entry.a[1], entry.a.size() > 2 ? entry.a[2].s : u"" });
      }
    }
    return out;
  }();
  return list;
}

// findPreset, for a built-in: by name, or nothing.
inline const Preset* findPreset(std::string_view name) {
  for (const auto& p : presets()) if (p.name == name) return &p;
  return nullptr;
}

// The base (P8h): what the instrument opens on and a new setup starts from -
// the page's BASE_SETUP, written out with the bank and held to it by parity.
inline const Json& baseSetup() {
  static const Json base = *jsonParse(utf8To16(
      R"base({"shape":"sine","midiMode":"poly","polyRound":true,"pictureAmount":0,"display":"xy","persistence":"0.3","timebase":3})base"));
  return base;
}

}  // namespace scope
