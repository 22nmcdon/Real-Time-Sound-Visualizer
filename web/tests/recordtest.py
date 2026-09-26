"""Stage L's Record: a clip of the screen and what it sounds like.

Against the way it would fail:

- a clip of the wrong thing: the picture has the trace's own size and IS the
  trace, told apart from its mirror image, which a blank or a different canvas
  would not be;
- a clip whose sound is not the sound: a heard tone comes back at its pitch,
  and a pitch changed halfway comes back changed halfway, so the track is live
  rather than a copy of the first moment;
- a recorder living in one source's context: a clip that runs across a change
  of source carries the second source's sound too;
- the rule about what is heard, both ways: a live input nobody hears is in
  the clip, one that is monitored is in it once and not twice, and a silent
  generator makes a silent clip that says why;
- a clip no player can seek: the file carries its length, which the browser's
  own recording does not;
- a recorder that holds on: when it stops, its taps and its context are let
  go, and at the longest clip it stops by itself and says so.
"""
import os
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

fails = []
def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (("   " + detail) if detail else ""))
    if not ok: fails.append(name)

STUB = """
  window.__wait = (ms) => new Promise((r) => setTimeout(r, ms));
  window.__set = (id, v, kind) => { el[id].value = String(v); el[id].dispatchEvent(new Event(kind)); };
  // Record for a while, with something done part way through, and hand back
  // the finished clip.
  window.__record = async (ms, during, at) => {
    el.recordButton.click();
    await __wait(at || ms / 2);
    if (during) await during();
    await __wait(ms - (at || ms / 2));
    el.recordButton.click();
    for (let k = 0; k < 100 && (rec.recorder || !rec.clip); k++) await __wait(50);
    return rec.clip;
  };
  /* The sound in a clip, decoded, and its pitch between two times: upward
     crossings with a little hysteresis, so the silence before the first
     sample and the codec's noise floor do not count as cycles. */
  window.__sound = async (blob) => {
    const ctx = new AudioContext();
    const audio = await ctx.decodeAudioData(await blob.arrayBuffer());
    ctx.close();
    const data = audio.getChannelData(0), rate = audio.sampleRate;
    const pitch = (a, b) => {
      let ups = 0, low = false;
      const from = Math.floor(a * rate), to = Math.min(data.length, Math.floor(b * rate));
      for (let i = from; i < to; i++) {
        if (data[i] < -0.05) low = true;
        else if (low && data[i] > 0.05) { ups++; low = false; }
      }
      return ups / ((to - from) / rate);
    };
    const peakIn = (a, b) => {
      let most = 0;
      for (let i = Math.floor(a * rate); i < Math.min(data.length, Math.floor(b * rate)); i++) most = Math.max(most, Math.abs(data[i]));
      return most;
    };
    return { duration: audio.duration, peak: peakIn(0.2, audio.duration), peakIn, pitch };
  };
  // A stereo microphone of one sine, the page handed it as its input.
  window.__mic = async (hz) => {
    const ctx = new AudioContext();
    const dest = ctx.createMediaStreamDestination(), a = ctx.createOscillator(), g = ctx.createGain();
    a.frequency.value = hz; g.gain.value = 0.5; a.connect(g); g.connect(dest); a.start();
    navigator.mediaDevices.getUserMedia = () => Promise.resolve(dest.stream);
    if (state.source && state.source.kind === 'mic') { el.srcTone.click(); await __wait(300); }
    el.srcMic.click(); await __wait(1200);
  };
  // A file of one sine, two seconds, looped.
  window.__wav = (hz) => {
    const rate = 44100, n = rate * 2, bytes = 44 + n * 2;
    const b = new ArrayBuffer(bytes), v = new DataView(b);
    const str = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
    str(0, 'RIFF'); v.setUint32(4, bytes - 8, true); str(8, 'WAVE'); str(12, 'fmt ');
    v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
    v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true);
    v.setUint16(34, 16, true); str(36, 'data'); v.setUint32(40, n * 2, true);
    for (let i = 0; i < n; i++) v.setInt16(44 + i * 2, Math.round(0.4 * 32767 * Math.sin(2 * Math.PI * hz * i / rate)), true);
    return new File([b], 'sine.wav', { type: 'audio/wav' });
  };
"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--autoplay-policy=no-user-gesture-required"])
    p = b.new_page(viewport={"width": 1400, "height": 900})
    bad = []
    p.on("pageerror", lambda e: bad.append("pageerror: " + str(e)))
    p.on("console", lambda m: bad.append("console: " + m.text)
         if m.type == "error" and "ERR_CERT" not in m.text else None)
    p.add_init_script(STUB)
    p.goto(f"file://{ART}/scope.html"); p.wait_for_timeout(700)
    if p.locator("#helpClose").is_visible(): p.locator("#helpClose").click()

    print("\n--- the generator, heard ---")
    tone = p.evaluate("""async () => {
      __set('shape', 'saw', 'change'); __set('freq', 220, 'input');
      state.genSound = true; await applyGeneratorSound(); await __wait(600);
      // The file as the browser wrote it, kept aside to be held against the
      // one this page hands over.
      let raw = null;
      const patch = webmWithDuration;
      window.webmWithDuration = (bytes, ms) => { raw = bytes.slice(); return patch(bytes, ms); };
      const during = { label: null, pressed: null };
      const clip = await __record(2400, async () => {
        during.label = el.recordLabel.textContent;
        during.pressed = el.recordButton.getAttribute('aria-pressed');
        during.taps = rec.taps.size;
        __set('freq', 330, 'input');
      }, 1200);
      window.webmWithDuration = patch;
      const sound = await __sound(clip);
      const out = { type: clip.type, size: clip.size, during, note: el.recordNote.textContent,
                    open: !el.recordPanel.hidden, clipShown: !el.recordClip.hidden,
                    save: el.recordSave.getAttribute('download'), href: el.recordSave.href === rec.url,
                    first: sound.pitch(0.4, 1.1), second: sound.pitch(1.5, 2.2), peak: sound.peak,
                    after: { taps: rec.taps.size, ctx: rec.ctx.state, recording: rec.recorder !== null,
                             label: el.recordLabel.textContent,
                             pressed: el.recordButton.getAttribute('aria-pressed') } };

      // The length: the one handed over, and the browser's own.
      const length = async (blob) => {
        const v = document.createElement('video');
        v.src = URL.createObjectURL(blob);
        await new Promise((r) => { v.onloadedmetadata = r; v.onerror = r; });
        return v.duration;
      };
      out.duration = await length(clip);
      out.rawDuration = await length(new Blob([raw], { type: clip.type }));
      out.patchedTwice = patch(new Uint8Array(await clip.arrayBuffer()), 5000).length === clip.size;
      const mp4 = new Uint8Array([0, 0, 0, 24, 102, 116, 121, 112]);
      out.notWebm = patch(mp4, 1000) === mp4;

      // The picture: the video's last frames against the trace, and against
      // the trace mirrored left to right. A saw is not its own mirror image.
      const v = el.recordVideo;
      if (v.readyState < 1) await new Promise((r) => { v.onloadedmetadata = r; });
      out.video = [v.videoWidth, v.videoHeight];
      out.canvas = [el.trace.width, el.trace.height];
      return out;
    }""")
    print("    %s" % tone)
    check("a clip is made: a webm, offered under the Clip button with a Save link named for the time",
          tone["type"] == "video/webm" and tone["size"] > 10000 and tone["open"] and tone["clipShown"]
          and tone["href"] and tone["save"].startswith("scope-") and tone["save"].endswith(".webm"),
          "%s, %d bytes, %s" % (tone["type"], tone["size"], tone["save"]))
    check("while it records the button says Stop and the time, and the speakers are tapped",
          tone["during"]["label"] == "Stop 0:01" and tone["during"]["pressed"] == "true" and tone["during"]["taps"] == 1,
          str(tone["during"]))
    check("its sound is the generator's: 220 Hz, then 330 Hz after the pitch was changed halfway",
          abs(tone["first"] - 220) < 6 and abs(tone["second"] - 330) < 8 and tone["peak"] > 0.1,
          "%.1f Hz then %.1f Hz, peak %.2f" % (tone["first"], tone["second"], tone["peak"]))
    check("and the note says the sound is what the speakers played",
          "the sound is what the speakers played." in tone["note"] and tone["note"].startswith("0:02"), tone["note"])
    check("stopped, it lets go: no taps, its context closed, the button back to Record",
          tone["after"] == {"taps": 0, "ctx": "closed", "recording": False, "label": "Record", "pressed": "false"},
          str(tone["after"]))
    check("the file carries its length, which the browser's own recording does not",
          abs(tone["duration"] - 2.4) < 0.25 and tone["rawDuration"] in (None, float("inf")),
          "%.3f s; as recorded, %s" % (tone["duration"], tone["rawDuration"]))
    check("and the length is written once: a file that has one, or is not webm, comes back untouched",
          tone["patchedTwice"] and tone["notWebm"], "%s, %s" % (tone["patchedTwice"], tone["notWebm"]))
    check("the picture is the trace at its own size", tone["video"] == tone["canvas"],
          "%s against %s" % (tone["video"], tone["canvas"]))

    frame = p.evaluate("""async () => {
      /* A stopped scope, so that the screen now is the screen in the clip's
         last frame. Running, the trace moves between the two, and the check
         read 78 per cent for a clip that was plainly the screen. */
      setRunning(false); await __wait(200);
      await __record(900);
      const v = el.recordVideo;
      if (v.readyState < 1) await new Promise((r) => { v.onloadedmetadata = r; });
      v.currentTime = Math.max(0, v.duration - 0.15);
      await new Promise((r) => { v.onseeked = r; });
      const w = el.trace.width, h = el.trace.height;
      const grab = (src, flip) => {
        const c = document.createElement('canvas'); c.width = w; c.height = h;
        const g = c.getContext('2d');
        if (flip) { g.translate(w, 0); g.scale(-1, 1); }
        g.drawImage(src, 0, 0, w, h);
        const d = g.getImageData(0, 0, w, h).data, out = new Float32Array(w * h);
        for (let i = 0; i < w * h; i++) out[i] = (d[i * 4] + d[i * 4 + 1] + d[i * 4 + 2]) / 3;
        return out;
      };
      const seen = grab(v, false), screen = grab(el.trace, false), mirror = grab(el.trace, true);
      /* Judged only where the screen and its mirror image disagree. The
         graticule is its own mirror image and so is most of the paper, and a
         mean over every pixel was carried by them: 4.3 against 6.8, a margin
         the codec's own blur could close. Where the two differ, the video is
         nearer one or the other, and a clip of the screen is nearer the
         screen nearly everywhere. */
      let judged = 0, nearer = 0;
      for (let i = 0; i < seen.length; i++) {
        if (Math.abs(screen[i] - mirror[i]) < 60) continue;
        judged++;
        if (Math.abs(seen[i] - screen[i]) < Math.abs(seen[i] - mirror[i])) nearer++;
      }
      setRunning(true);
      return { judged, nearer: nearer / Math.max(1, judged) };
    }""")
    print("    %d pixels where the screen and its mirror differ; the video is nearer the screen at %.1f%% of them"
          % (frame["judged"], 100 * frame["nearer"]))
    check("and what it shows is the screen, not its mirror image or anything else",
          frame["judged"] > 500 and frame["nearer"] > 0.85, str(frame))

    print("\n--- across a change of source ---")
    across = p.evaluate("""async () => {
      __set('freq', 220, 'input');
      const clip = await __record(2600, async () => { await toFile(__wav(550)); }, 1000);
      const sound = await __sound(clip);
      const out = { first: sound.pitch(0.3, 0.9), second: sound.pitch(1.8, 2.4), note: rec.note };
      el.srcTone.click(); await __wait(300);
      return out;
    }""")
    check("a clip that runs across a change of source hears the second one too: 220 Hz, then the file's 550",
          abs(across["first"] - 220) < 6 and abs(across["second"] - 550) < 12,
          "%.1f Hz then %.1f Hz" % (across["first"], across["second"]))

    print("\n--- what is heard ---")
    heard = p.evaluate("""async () => {
      const out = {};
      state.genSound = false; await applyGeneratorSound(); await __wait(300);
      const quiet = await __sound(await __record(1200));
      out.silent = { peak: quiet.peak, note: rec.note };
      await __mic(440);
      const unheard = await __sound(await __record(1500));
      out.unheard = { pitch: unheard.pitch(0.4, 1.3), peak: unheard.peak, note: rec.note };
      // The same input split into bands, and as a rack's live lane: two more
      // sources that draw a live input and send it nowhere.
      el.micBands.click(); await __wait(1500);
      const bands = await __sound(await __record(1500));
      out.bands = { bands: !!state.source.bands, pitch: bands.pitch(0.4, 1.3), note: rec.note };
      el.micWhole.click(); await __wait(1200);
      rackFiles = null; el.rackLive.checked = true; await setRackLive(true); await __wait(800);
      const lane = await __sound(await __record(1500));
      out.lane = { kind: state.source.kind, pitch: lane.pitch(0.4, 1.3), note: rec.note };
      el.rackLive.checked = false; await setRackLive(false);
      await __mic(440);
      // Declared a line input and monitored: the speakers carry it now.
      el.kindLine.click(); await __wait(100);
      el.monitorLive.checked = true; el.monitorLive.dispatchEvent(new Event('change')); await __wait(300);
      const monitored = state.source.monitored;
      const both = await __sound(await __record(1500));
      out.monitored = { on: monitored, pitch: both.pitch(0.4, 1.3), peak: both.peak, note: rec.note };
      el.monitorLive.checked = false; el.monitorLive.dispatchEvent(new Event('change')); await __wait(300);
      /* Monitoring switched on in the middle of a clip. The input stops being
         unheard, and its tap has to go as the speakers' arrives; kept, the
         second half would carry it twice. The one case where a tap left
         behind still sounds, and the mutation pass found no check for it. */
      const switched = await __sound(await __record(2400, async () => {
        el.monitorLive.checked = true; el.monitorLive.dispatchEvent(new Event('change'));
      }, 1000));
      out.switched = { before: switched.peakIn(0.3, 0.9), after: switched.peakIn(1.6, 2.3), note: rec.note };
      el.monitorLive.checked = false; el.monitorLive.dispatchEvent(new Event('change'));
      el.kindMic.click();
      el.srcTone.click(); await __wait(300);
      return out;
    }""")
    print("    %s" % heard)
    check("a silent generator makes a silent clip, and the note says why and what puts the sound in",
          heard["silent"]["peak"] < 0.01 and "silent: nothing was heard" in heard["silent"]["note"]
          and "Hear the generator" in heard["silent"]["note"], str(heard["silent"]))
    check("a live input nobody hears is in the clip, and the note says it is your input",
          abs(heard["unheard"]["pitch"] - 440) < 10 and 0.35 < heard["unheard"]["peak"] < 0.65
          and "the sound is your input." in heard["unheard"]["note"], str(heard["unheard"]))
    # The speakers are a touch louder than the input: the limiter is a
    # DynamicsCompressor, and Chrome gives it make-up gain. Taken twice it
    # would be over one; once, it is 0.63.
    check("and so is one split into bands, and a rack's live lane",
          heard["bands"]["bands"] and abs(heard["bands"]["pitch"] - 440) < 10 and "your input" in heard["bands"]["note"]
          and heard["lane"]["kind"] == "rack" and abs(heard["lane"]["pitch"] - 440) < 10
          and "your input" in heard["lane"]["note"], "%s / %s" % (heard["bands"], heard["lane"]))
    check("monitored, it is in the clip once, through the speakers, not twice",
          heard["monitored"]["on"] is True and abs(heard["monitored"]["pitch"] - 440) < 10
          and 0.35 < heard["monitored"]["peak"] < 0.8
          and "the sound is what the speakers played." in heard["monitored"]["note"], str(heard["monitored"]))

    check("and monitoring switched on mid-clip hands the input from its own tap to the speakers', once",
          0.35 < heard["switched"]["before"] < 0.65 and 0.35 < heard["switched"]["after"] < 0.8
          and "what the speakers played, and your input" in heard["switched"]["note"], str(heard["switched"]))

    print("\n--- the longest clip, and discarding ---")
    end = p.evaluate("""async () => {
      rec.maxS = 1;
      el.recordButton.click();
      for (let k = 0; k < 60 && (rec.recorder || !rec.clip); k++) await __wait(50);
      const out = { stopped: rec.recorder === null, ms: rec.ms, note: rec.note };
      rec.maxS = RECORD_MAX_S;
      const first = rec.url, revoke = URL.revokeObjectURL, gone = [];
      URL.revokeObjectURL = (u) => { gone.push(u); revoke.call(URL, u); };
      const short = await __record(600);
      URL.revokeObjectURL = revoke;
      out.manual = rec.note;
      out.replaced = gone.includes(first) && rec.url !== first;
      // Watched at the call: a page on file:// cannot fetch a blob address
      // to find out whether it still answers.
      const url = rec.url;
      gone.length = 0;
      URL.revokeObjectURL = (u) => { gone.push(u); revoke.call(URL, u); };
      el.recordDiscard.click();
      URL.revokeObjectURL = revoke;
      out.discarded = { clip: rec.clip, url: rec.url, shown: !el.recordClip.hidden, open: !el.recordPanel.hidden,
                        revoked: gone.length === 1 && gone[0] === url };
      return out;
    }""")
    print("    %s" % end)
    check("at the longest clip it stops by itself and says so; stopped by hand, it does not claim to have",
          end["stopped"] and 950 < end["ms"] < 1400 and "It stopped at 0:01, the longest clip." in end["note"]
          and "longest" not in end["manual"], "%s / %s" % (end["note"], end["manual"]))
    check("a new recording lets the last clip go", end["replaced"], str(end["replaced"]))
    check("Discard lets the clip go: its address is revoked and the Clip button is gone",
          end["discarded"] == {"clip": None, "url": None, "shown": False, "open": False, "revoked": True},
          str(end["discarded"]))

    check("no page errors", not bad, "; ".join(bad[:3]))
    b.close()

print("\n%d failed" % len(fails) if fails else "\nall passed")
raise SystemExit(1 if fails else 0)
