"""One page in WebKit, driven by a list of steps: webkittest.py's browser.

Run by webkittest.py under xvfb-run with the system Python that has the GObject
bindings (python3.12 here, where the suites' 3.13 has none), not on its own:

    xvfb-run -a /usr/bin/python3.12 webkit_page.py URL WIDTH HEIGHT STEPS.json

WebKitGTK is the engine the plugin's web view already is on Linux, installed
by the cloud environment's setup script for the plugin's build, and the same
WebKit and JavaScriptCore as Safari's, without Safari's own shell or the
Mac's audio. Playwright's WebKit would be the usual way in; its download is
refused by this environment's network (web/README.md, 22 Nov).

Each step is ["js", body] - an async function's body, its value returned as
JSON - ["click", [x, y]], a press and release of the first button at that
point of the view, sent through GTK as a mouse's would be, so the page sees
a trusted gesture and the autoplay rule is the real one; ["wait", ms]; or
["shot", path], the window as a PNG (the X screen must be as large: webkittest.py asks xvfb-run for one). Autoplay is refused, as Safari refuses it:
the sound starts only on the click. Every error, unhandled rejection,
console.error and console.warn from the page's first script on is kept in
window.__errs. Prints `RESULT ` and the steps' values as one JSON list.
"""
import json, sys

import gi
gi.require_version("Gtk", "3.0"); gi.require_version("Gdk", "3.0"); gi.require_version("WebKit2", "4.1")
from gi.repository import Gdk, GLib, Gtk, WebKit2  # noqa: E402

url, width, height = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
steps = json.load(open(sys.argv[4]))

CATCH = """window.__errs = [];
addEventListener('error', (e) => __errs.push('error: ' + e.message + ' @' + (e.filename || '') + ':' + e.lineno));
addEventListener('unhandledrejection', (e) => __errs.push('rejection: ' + String(e.reason && (e.reason.stack || e.reason.message) || e.reason)));
for (const k of ['error', 'warn']) { const f = console[k].bind(console); console[k] = (...a) => { __errs.push(k + ': ' + a.map(String).join(' ')); f(...a); }; }"""

content = WebKit2.UserContentManager()
content.add_script(WebKit2.UserScript.new(CATCH, WebKit2.UserContentInjectedFrames.TOP_FRAME,
                                          WebKit2.UserScriptInjectionTime.START, None, None))
view = WebKit2.WebView(user_content_manager=content,
                       website_policies=WebKit2.WebsitePolicies(autoplay=WebKit2.AutoplayPolicy.DENY))
settings = view.get_settings()
settings.set_property("enable-webaudio", True)
settings.set_property("enable-webgl", True)
window = Gtk.Window()
window.set_default_size(width, height)
window.move(0, 0)
window.add(view)
window.show_all()
out, loop = [], GLib.MainLoop()


def step(i):
    if i >= len(steps):
        print("RESULT " + json.dumps(out), flush=True)
        loop.quit()
        return False
    kind, arg = steps[i]
    if kind == "wait":
        GLib.timeout_add(int(arg), lambda: step(i + 1))
    elif kind == "click":
        seat = Gdk.Display.get_default().get_default_seat()
        for t in (Gdk.EventType.BUTTON_PRESS, Gdk.EventType.BUTTON_RELEASE):
            ev = Gdk.Event.new(t)
            ev.button.window = view.get_window()
            ev.button.send_event = True
            ev.button.x, ev.button.y = float(arg[0]), float(arg[1])
            ev.button.button = 1
            ev.button.time = Gtk.get_current_event_time()
            ev.set_device(seat.get_pointer())
            Gtk.main_do_event(ev)
        out.append({"clicked": arg})
        GLib.timeout_add(300, lambda: step(i + 1))
    elif kind == "shot":
        # The X server's own picture of the window, cropped to it (ImageMagick's import): the
        # snapshot API hands back a cairo surface, and this Python has no cairo bindings.
        import subprocess
        done = subprocess.run(["import", "-window", "root", "-crop", "%dx%d+0+0" % (width, height), arg],
                              capture_output=True, text=True)
        out.append({"shot": arg} if done.returncode == 0 else {"shotfail": done.stderr[-300:]})
        GLib.idle_add(lambda: step(i + 1))
    else:
        def done(v, res):
            try:
                value = json.loads(v.call_async_javascript_function_finish(res).to_json(0) or "null")
            except Exception as error:  # noqa: BLE001 - a step that threw is a value the suite reads
                value = {"jsfail": str(error)}
            out.append(value)
            GLib.idle_add(lambda: step(i + 1))
        view.call_async_javascript_function(arg, -1, None, None, None, None, done)
    return False


def loaded(v, event):
    if event == WebKit2.LoadEvent.FINISHED:
        GLib.timeout_add(2500, lambda: step(0))


view.connect("load-changed", loaded)
view.load_uri(url)
GLib.timeout_add(300000, lambda: (print("TIMEOUT", flush=True), loop.quit()))
loop.run()
