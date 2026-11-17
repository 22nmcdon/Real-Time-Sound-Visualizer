/* The mockup's dealing, by number, against split-by-notes.md: each case
   names the rule it holds and what the other way would answer. Not a suite
   of run.py - the mockup is not the instrument - but the diagram is only worth
   playing if it deals as the instrument does.
   node web/docs/mockups/play/check-dealing.js  (Chromium from Playwright) */
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  p.on('pageerror', e => console.log('PAGEERR', e.message));
  await p.goto('file://' + require('path').join(__dirname, 'index.html')); await p.waitForTimeout(200);
  const r = await p.evaluate(() => {
    const M = window.__playMock, out = {};
    const run = (cfg, steps) => { M.clear(); M.set(Object.assign({ mode: 'poly', hands: 'notes', splitEnd: 'lower', splitCount: 1, windowMs: 10 }, Object.fromEntries(Object.entries(cfg).filter(([k]) => k !== 'noFlush')))); for (const s of steps) s(); if (!cfg.noFlush) M.flush(); return M.hands(); };
    const C3=48,E3=52,G3=55,A2=45,C4=60,E4=64,G4=67;
    out.rank = run({}, [() => M.on(C3, 0), () => M.on(E3, 100), () => M.on(G3, 200), () => M.on(A2, 300)]);
    out.fixed = run({ splitCount: 2 }, [() => M.on(E3, 0), () => M.on(G3, 100), () => M.on(C4, 200), () => M.on(C3, 300)]);
    out.gather = run({}, [() => M.on(G4, 1000), () => M.on(E4, 1002), () => M.on(C3, 1004)]);
    out.gatherNull = run({ windowMs: 0 }, [() => M.on(G4, 1000), () => M.on(E4, 1002), () => M.on(C3, 1004)]);
    out.halfOpen = run({}, [() => M.on(G4, 1000), () => M.on(C3, 1010)]);
    out.inside = run({}, [() => M.on(G4, 1000), () => M.on(C3, 1009.9)]);
    out.fromFirst = run({}, [() => M.on(G4, 1000), () => M.on(E4, 1008), () => M.on(C3, 1012)]);
    // The look-ahead: inside the window nothing is dealt yet (the code before
    // it dealt each note as it landed, which this would see as a hand).
    out.waits = run({ noFlush: true }, [() => M.on(G4, 1000), () => M.on(E4, 1002)]);
    out.pedal = run({}, [() => M.pedal(true), () => M.on(C3, 0), () => M.off(C3, 300), () => M.on(G3, 500)]);
    out.highest = run({ splitEnd: 'upper' }, [() => M.on(C3, 0), () => M.on(E3, 100), () => M.on(G3, 200), () => M.on(C4, 300)]);
    out.key = run({ hands: 'key', splitAt: 60 }, [() => M.on(C3, 0), () => M.on(C4, 100)]);
    M.pedal(false); M.clear();
    return out;
  });
  const want = {
    rank: { C3: 0, E3: 1, G3: 1, A2: 0 },              // fill would put A2 high
    fixed: { E3: 0, G3: 0, C4: 1, C3: 0 },             // re-sorting would move G3 high
    gather: { G4: 1, E4: 1, C3: 0 },                   // arrival order would give G4 E4 low
    gatherNull: { G4: 0, E4: 0, C3: 0 },
    halfOpen: { G4: 0, C3: 0 },                        // 10 ms after: a new gather, G4 kept low
    inside: { G4: 1, C3: 0 },
    pedal: { C3: 0, G3: 1 },
    waits: { G4: 'waiting', E4: 'waiting' },
    // Counted from the top, one note: each note struck above everything held
    // is the top and joins the upper hand, and C3 keeps the upper hand it was
    // dealt alone (fewer held than the count). Mirrored as Lowest, all low.
    highest: { C3: 1, E3: 1, G3: 1, C4: 1 },
    key: { C3: 0, C4: 1 }
  };
  // G4 at 0 and E4 at 8 are one gather (E4 low, G4 high); C3 at 12 is
  // outside the window timed from G4, so it starts its own, and E4 keeps low.
  // A window sliding with each note would gather C3 too and move E4 high.
  want.fromFirst = { G4: 1, E4: 0, C3: 0 };
  let bad = 0;
  for (const k in want) {
    const ok = JSON.stringify(Object.keys(want[k]).sort().map(n => [n, r[k][n]])) === JSON.stringify(Object.keys(want[k]).sort().map(n => [n, want[k][n]]));
    if (!ok) bad++;
    console.log(ok ? 'ok  ' : 'FAIL', k, JSON.stringify(r[k]));
  }
  console.log(bad ? bad + ' failed' : 'all ' + Object.keys(want).length + ' agree');
  await b.close();
})();
