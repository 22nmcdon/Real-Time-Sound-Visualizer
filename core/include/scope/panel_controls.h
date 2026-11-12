// The panel's sliders and menus, as the page's DOM has them when it opens:
// each slider's range, step and starting value, in the order the page lays
// them out, and each menu's options and the one it starts on. Written out from the page by
// core/tests/tools/restore_page.py --controls, and held to it control for
// control by core/tests/parity.py, so a slider whose range changes on the page
// and not here is a failure, not a drift.

#pragma once

namespace scope {

struct RangeSpec { const char* id; double min, max, step; double value; };
// A menu's options joined by \x1f, or none at all for a menu the page fills
// only once it has something to list (the devices, the MIDI channels).
struct SelectSpec { const char* id; const char* options; const char* value; };

inline constexpr RangeSpec kRanges[] = {
  { "level", -1000, 1000, 1, 0 },
  { "timebase", 0, 8, 1, 7 },
  { "zoom", 0, 24, 1, 0 },
  // How the picture responds (11 Nov): Custom's Rise and Fall, in milliseconds.
  { "pictureRise", 5, 2000, 5, 80 },
  { "pictureFall", 20, 8000, 10, 800 },
  { "pictureAmount", 0, 100, 1, 60 },
  { "freq", 30, 4000, 1, 220 },
  { "amp", 0, 140, 1, 55 },
  // The master Output (G7): the Picture section's corner, never a setup's.
  { "output", 0, 100, 1, 100 },
  // The master Width (12 Nov): beside the Output, never a setup's either.
  { "stereoWidth", 0, 100, 1, 100 },
  { "morph", 0, 300, 1, 150 },
  { "width", 5, 95, 1, 25 },
  { "table", 0, 300, 1, 150 },
  { "phase", 0, 360, 1, 90 },
  { "envAttack", 0, 200, 1, 8 },
  { "envDecay", 1, 1000, 1, 120 },
  { "envSustain", 0, 100, 1, 70 },
  { "envRelease", 1, 2000, 1, 180 },
  { "glide", 0, 500, 1, 0 },
  { "morphPos", 0, 100, 1, 0 },
  { "lfoRate0", 1, 800, 1, 20 },
  { "quantiseGlide", 0, 300, 1, 0 },
  { "tempo", 30, 300, 1, 120 },
  { "ch1Scale", 0, 8, 1, 0 },
  { "ch1Offset", -100, 100, 1, 0 },
  { "ch2Scale", 0, 8, 1, 0 },
  { "ch2Offset", -100, 100, 1, 0 },
  { "lag", 1, 400, 1, 50 },
  { "lagMix", 0, 50, 1, 20 },
  { "acCorner", 5, 200, 1, 100 },
  { "rotate", -50, 50, 1, 0 },
  { "bar0", 0, 8, 1, 0 },
  { "bar1", 0, 8, 1, 0 },
  { "bar2", 0, 8, 1, 8 },
  { "bar3", 0, 8, 1, 7 },
  { "bar4", 0, 8, 1, 4 },
  { "bar5", 0, 8, 1, 0 },
  { "bar6", 0, 8, 1, 0 },
  { "bar7", 0, 8, 1, 0 },
  { "bar8", 0, 8, 1, 0 },
  { "oscFm", 0, 100, 1, 0 },
  { "oscBend", -100, 100, 1, 0 },
  { "oscBendAt", 0, 100, 1, 25 },
  { "oscRing", 0, 100, 1, 0 },
  { "oscSync", 100, 800, 1, 100 },
  { "oscSub", 0, 100, 1, 0 },
  { "oscSpread", 0, 50, 1, 12 },
  { "shpDrive", 0, 100, 1, 0 },
  { "shpFold", 0, 100, 1, 0 },
  { "vcfCut", 0, 1000, 1, 667 },
  { "vcfRes", 0, 100, 1, 0 },
  { "vcfTrack", 0, 100, 1, 0 },
  { "vcfEnvAmt", -40, 40, 1, 0 },
  { "vcfAtk", 0, 1000, 1, 5 },
  { "vcfDec", 1, 2000, 1, 300 },
  { "vcfSus", 0, 100, 1, 30 },
  { "vcfRel", 1, 2000, 1, 300 },
  { "planeTurn", -50, 50, 1, 0 },
  { "planeTwist", -100, 100, 1, 0 },
  { "planeRadius", 2, 100, 1, 40 },
  { "planeScaleX", 0, 200, 1, 100 },
  { "planeScaleY", 0, 200, 1, 100 },
  { "planeShear", -100, 100, 1, 0 },
  { "delayMix", 0, 100, 1, 0 },
  { "delayMs", 10, 2000, 1, 375 },
  { "delayFeedback", 0, 90, 1, 35 },
  // The Envelope's own (8 Nov).
  { "menvAtk", 0, 2000, 1, 10 },
  { "menvDec", 1, 4000, 1, 300 },
  { "menvSus", 0, 100, 1, 50 },
  { "menvRel", 1, 4000, 1, 400 },
  // F5c: the repeats' tone, low cut, width and wow.
  { "delayTone", 0, 100, 1, 100 },
  { "delayLowCut", 0, 100, 1, 0 },
  { "delayWidth", 0, 200, 1, 100 },
  { "delayWow", 0, 100, 1, 0 },
  { "chorusMix", 0, 100, 1, 0 },
  { "chorusRate", 5, 500, 1, 60 },
  { "chorusDepth", 0, 100, 1, 30 },
  { "chorusTime", 10, 300, 1, 120 },
  { "chorusFeedback", 0, 90, 1, 0 },
  { "phaserMix", 0, 100, 1, 0 },
  { "phaserRate", 5, 500, 1, 30 },
  { "phaserDepth", 0, 100, 1, 70 },
  { "phaserFeedback", 0, 75, 1, 30 },
  { "reverbMix", 0, 100, 1, 0 }, { "reverbSize", 0, 100, 1, 40 }, { "reverbTone", 0, 100, 1, 60 },
  { "reverbPre", 0, 100, 1, 10 }, { "reverbSpread", 0, 100, 1, 0 },
  { "inputDepth", 0, 100, 1, 50 },
  { "oscScan", 0, 100, 1, 0 },
  { "scanStrike", 0, 100, 1, 50 },
  { "scanSoft", 0, 60, 1, 30 },
  { "scanMemory", 0, 100, 1, 0 },
  { "filterCutoff", 0, 1000, 1, 566 },
  { "filterRes", 0, 100, 1, 0 },
  { "position", 0, 100, 1, 10 },
  { "holdoff", 0, 50, 1, 0 },
  { "keysVelocity", 1, 127, 1, 100 },
};

inline constexpr SelectSpec kSelects[] = {
  { "device", nullptr, "" },
  { "midiOut", "", "" },
  { "midiOutCh", nullptr, "" },
  { "beamLevel", "off" "\x1f" "subtle" "\x1f" "moderate" "\x1f" "high", "moderate" },
  // Layer B's ink: only the look, which the core never draws, but every
  // menu on the page is the panel's, so a host's view of it is the page's.
  { "traceWidth", "thin" "\x1f" "normal" "\x1f" "thick", "normal" },
  { "bInk", "lane" "\x1f" "accent" "\x1f" "ch1" "\x1f" "ch2" "\x1f" "ch3" "\x1f" "ch4" "\x1f" "ch5", "lane" },
  { "persistence", "0" "\x1f" "0.3" "\x1f" "0.12" "\x1f" "0.04" "\x1f" "-1" "\x1f" "", "0" },
  { "spectroSpan", "2" "\x1f" "5" "\x1f" "10" "\x1f" "30", "5" },
  { "xyX", "0" "\x1f" "1", "0" },
  { "xyY", "0" "\x1f" "1", "1" },
  { "arpMode", "off" "\x1f" "up" "\x1f" "down" "\x1f" "updown" "\x1f" "played" "\x1f" "random", "off" },
  { "arpRate", "1/4" "\x1f" "1/8" "\x1f" "1/16" "\x1f" "1/8t" "\x1f" "1/16t", "1/8" },
  { "arpOctaves", "1" "\x1f" "2" "\x1f" "3", "1" },
  { "midiLayers", "off" "\x1f" "split" "\x1f" "layer", "off" },
  { "midiLayerPair", "each" "\x1f" "against", "each" },
  { "pictureMovesA", "A" "\x1f" "B" "\x1f" "both", "A" },
  { "pictureMovesB", "B" "\x1f" "A" "\x1f" "both", "B" },
  { "pictureResponds", "change" "\x1f" "level" "\x1f" "both", "change" },
  { "pictureFeel", "snappy" "\x1f" "smooth" "\x1f" "slow" "\x1f" "custom", "smooth" },
  { "scanReadsA", "A" "\x1f" "B" "\x1f" "both", "A" },
  { "scanReadsB", "B" "\x1f" "A" "\x1f" "both", "B" },
  { "midiDrawCount", "2" "\x1f" "3" "\x1f" "4" "\x1f" "5" "\x1f" "6" "\x1f" "7" "\x1f" "8", "2" },
  { "midiDrawWhich", "outer" "\x1f" "lowest" "\x1f" "highest" "\x1f" "recent", "outer" },
  { "midiBendRange", "1" "\x1f" "2" "\x1f" "3" "\x1f" "5" "\x1f" "7" "\x1f" "12" "\x1f" "24", "2" },
  { "midiWheelTo", "vibrato" "\x1f" "picture" "\x1f" "scan" "\x1f" "off", "vibrato" },
  { "midiPressureTo", "vibrato" "\x1f" "picture" "\x1f" "scan" "\x1f" "off", "off" },
  // Expression's Velocity (F4): a view of the Key source's routing onto FM,
  // which reaches the core as that routing; listed because the page has it.
  { "midiVelocityTo", "strike" "\x1f" "fm", "strike" },
  { "shape", "harmonic" "\x1f" "sine" "\x1f" "square" "\x1f" "pulse" "\x1f" "triangle" "\x1f" "ramp" "\x1f" "drawbars" "\x1f" "morph" "\x1f" "drawn" "\x1f" "wavetable" "\x1f" "noise" "\x1f" "pink" "\x1f" "brown" "\x1f" "stepped", "harmonic" },
  { "interval", "0" "\x1f" "1" "\x1f" "2" "\x1f" "3" "\x1f" "4" "\x1f" "5" "\x1f" "6" "\x1f" "7" "\x1f" "8" "\x1f" "9" "\x1f" "10" "\x1f" "11" "\x1f" "12", "0" },
  { "fadeMode", "off" "\x1f" "in" "\x1f" "out" "\x1f" "both", "off" },
  { "lfoShape0", "sine" "\x1f" "triangle" "\x1f" "ramp" "\x1f" "square" "\x1f" "random", "sine" },
  { "lfoSync0", "" "\x1f" "4" "\x1f" "2" "\x1f" "1" "\x1f" "1/2" "\x1f" "1/4" "\x1f" "1/8" "\x1f" "1/16" "\x1f" "1/4t" "\x1f" "1/8t", "" },
  { "srcDetail-add", "" "\x1f" "gen.freq" "\x1f" "gen.amp" "\x1f" "gen.phase" "\x1f" "gen.ratio" "\x1f" "gen.bar0" "\x1f" "gen.bar1" "\x1f" "gen.bar2" "\x1f" "gen.bar3" "\x1f" "gen.bar4" "\x1f" "gen.bar5" "\x1f" "gen.bar6" "\x1f" "gen.bar7" "\x1f" "gen.bar8" "\x1f" "gen.morph" "\x1f" "gen.radius" "\x1f" "gen.twist" "\x1f" "gen.fm" "\x1f" "gen.sync" "\x1f" "gen.drive" "\x1f" "gen.fold" "\x1f" "gen.vcf" "\x1f" "gen.echo" "\x1f" "gen.echoTime" "\x1f" "gen.width" "\x1f" "gen.table" "\x1f" "gen.turn" "\x1f" "gen.bend" "\x1f" "gen.bendAt" "\x1f" "gen.phaser" "\x1f" "gen.delayTone" "\x1f" "gen.reverb" "\x1f" "gen.reverbSize" "\x1f" "gen.reverbTone" "\x1f" "view.rotate" "\x1f" "view.lag" "\x1f" "filter.cutoff" "\x1f" "filter.res" "\x1f" "view.zoom" "\x1f" "trig.position" "\x1f" "morph.pos" "\x1f" "view.scale1" "\x1f" "view.scale2", "" },
  { "keyRoot", "0" "\x1f" "1" "\x1f" "2" "\x1f" "3" "\x1f" "4" "\x1f" "5" "\x1f" "6" "\x1f" "7" "\x1f" "8" "\x1f" "9" "\x1f" "10" "\x1f" "11", "0" },
  { "keyScale", "chromatic" "\x1f" "major" "\x1f" "minor" "\x1f" "dorian" "\x1f" "phrygian" "\x1f" "lydian" "\x1f" "mixolydian" "\x1f" "locrian" "\x1f" "harmonic" "\x1f" "pentatonic" "\x1f" "minorpent" "\x1f" "blues" "\x1f" "whole", "chromatic" },
  { "oscRatio", "0.5" "\x1f" "1" "\x1f" "1.25" "\x1f" "1.3333333333333333" "\x1f" "1.5" "\x1f" "1.6666666666666667" "\x1f" "2" "\x1f" "2.5" "\x1f" "3" "\x1f" "3.5" "\x1f" "4" "\x1f" "5" "\x1f" "7", "1" },
  { "oscUnison", "1" "\x1f" "2" "\x1f" "3" "\x1f" "5" "\x1f" "7", "1" },
  { "oscSubOct", "1" "\x1f" "2", "1" },
  { "oscSubShape", "square" "\x1f" "sine", "square" },
  { "shpBits", "0" "\x1f" "8" "\x1f" "6" "\x1f" "4" "\x1f" "3" "\x1f" "2" "\x1f" "1", "0" },
  { "shpRate", "0" "\x1f" "11025" "\x1f" "8000" "\x1f" "4000" "\x1f" "2000" "\x1f" "1000" "\x1f" "500", "0" },
  { "shpOS", "2" "\x1f" "4", "2" },
  { "vcfType", "0" "\x1f" "1" "\x1f" "2" "\x1f" "3" "\x1f" "4", "0" },
  { "planeMirror", "0" "\x1f" "1" "\x1f" "2" "\x1f" "3", "0" },
  { "planeLimit", "0" "\x1f" "1" "\x1f" "2", "0" },
  { "planeSnap", "0" "\x1f" "6" "\x1f" "5", "0" },
  { "delaySync", "" "\x1f" "1/2" "\x1f" "1/4" "\x1f" "1/8d" "\x1f" "1/8" "\x1f" "1/4t" "\x1f" "1/8t" "\x1f" "1/16", "" },
  { "fxOrder", "pcd" "\x1f" "pdc" "\x1f" "cpd" "\x1f" "cdp" "\x1f" "dpc" "\x1f" "dcp", "pcd" },
  { "inputMode", "0" "\x1f" "1" "\x1f" "2" "\x1f" "3", "0" },
  { "scoreStep", "1/16" "\x1f" "1/8" "\x1f" "1/4", "1/16" },
  { "scoreVoices", "1" "\x1f" "2" "\x1f" "3" "\x1f" "4", "2" },
  { "scoreLow", "36" "\x1f" "48" "\x1f" "60", "48" },
  { "scoreOctaves", "1" "\x1f" "2" "\x1f" "3" "\x1f" "4", "3" },
  { "filterType", "lowpass" "\x1f" "highpass" "\x1f" "bandpass" "\x1f" "notch", "lowpass" },
  // Enlarge's Trail (G4): only the look, never in a setup, kept here because every menu is.
  { "enlargeTrail", "heard" "\x1f" "half" "\x1f" "short", "heard" },
};

// The sliders the morph walks (MORPH_IDS), in the order the page found them
// when its script ran - which is not the DOM's order once the Bench has moved
// its sections, and leaves out the sliders made later (the trace scales, the
// LFO's rate) as well as the ones MORPH_SKIP names. The order is what a setup
// code writes an end in, so it is held to the page like the rest.
// Since G8 (11 Nov) without the scope's view - the trigger's level, position
// and holdoff, the timebase and the zoom - which frame the signal rather than
// change it, so a slide between two sounds leaves the screen where the player
// set it; the tempo stays, since it is heard. The page's MORPH_SKIP says more.
inline constexpr const char* kMorphIds[] = {
  // Level in the Generator since G7, after Glide, where the page lays it out.
  "morph", "width", "table", "glide", "amp", "envAttack", "envDecay", "envSustain", "envRelease", "quantiseGlide", "tempo",
  "lag", "lagMix", "acCorner", "planeTwist", "rotate", "planeTurn", "planeRadius", "planeScaleX", "planeScaleY",
  "planeShear", "phaserMix", "phaserRate", "phaserDepth", "phaserFeedback", "chorusMix", "chorusRate", "chorusDepth",
  "chorusTime", "chorusFeedback", "delayMix", "delayMs", "delayFeedback", "delayTone", "delayLowCut", "delayWidth",
  "delayWow", "reverbMix", "reverbSize", "reverbTone", "reverbPre", "reverbSpread", "bar0", "bar1", "bar2", "bar3",
  "bar4", "bar5", "bar6", "bar7", "bar8", "freq", "phase", "oscFm", "oscBend", "oscBendAt", "oscRing", "oscSync",
  "oscSub", "oscSpread", "shpDrive", "shpFold", "vcfCut", "vcfRes", "vcfTrack", "vcfEnvAmt", "vcfAtk", "vcfDec",
  "vcfSus", "vcfRel", "inputDepth", "filterCutoff", "filterRes",
  "oscScan", "scanStrike", "scanSoft", "menvAtk", "menvDec", "menvSus", "menvRel",
};

}  // namespace scope
