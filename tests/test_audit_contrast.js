/* The rules inside scripts/audit-contrast.js, pinned without a browser.
 *
 * That script is the one tool the theme review depends on, and its
 * ground rule has been wrong twice: once reporting a positioned label
 * against a fill it never touches (fixed 2026-08-17), once hiding a
 * one-character node from the walk entirely (fixed 2026-08-18). Both
 * were found by eye against scratch pages that no longer exist. These
 * cases are those pages, written down.
 *
 * Requiring the script gives back its pure half; everything that reads
 * a DOM stays behind that export and is not exercised here. Run through
 * tests/test_audit_contrast.py, which skips when node is absent.
 */
const A = require("../scripts/audit-contrast.js");

const failures = [];
let checked = 0;

function check(name, got, want) {
  checked++;
  const ok = typeof want === "number" && typeof got === "number"
    ? Math.abs(got - want) < 0.01
    : JSON.stringify(got) === JSON.stringify(want);
  if (!ok) {
    failures.push(`${name}: got ${JSON.stringify(got)}, want ${JSON.stringify(want)}`);
  }
}

const rgb = (r, g, b) => ({ r: r, g: g, b: b, a: 1 });
const rect = (left, top, right, bottom) =>
  ({ left: left, top: top, right: right, bottom: bottom });

const WHITE = rgb(255, 255, 255);
const BLACK = rgb(0, 0, 0);
const IVORY = rgb(250, 249, 245);      // --bg, light theme
const HAIRLINE = rgb(209, 207, 197);   // --border, light theme

/* Colour parsing. The audit reads computed styles, and a browser hands
   back rgb(), rgba() and the space-separated form. */
check("parse rgb", A.parse("rgb(209, 207, 197)"), { r: 209, g: 207, b: 197, a: 1 });
check("parse rgba", A.parse("rgba(0, 0, 0, 0.4)"), { r: 0, g: 0, b: 0, a: 0.4 });
check("parse slash alpha", A.parse("rgb(1 2 3 / 0.5)"), { r: 1, g: 2, b: 3, a: 0.5 });
check("parse keyword", A.parse("none"), null);

/* Contrast. The middot pair is the ratio a browser reported at 1.48 on
   2026-08-18, so this case ties the arithmetic to a real measurement. */
check("white on black", A.contrast(WHITE, BLACK), 21);
check("a colour on itself", A.contrast(IVORY, IVORY), 1);
check("WCAG's 4.5 boundary", A.contrast(rgb(118, 118, 118), WHITE), 4.54);
check("hairline on ivory", A.contrast(HAIRLINE, IVORY), 1.48);

/* Geometry. The half-pixel slack exists so a child that fills its
   parent exactly is not read as overflowing it. */
check("the slack is half a pixel", A.EPS, 0.5);
check("exact fill is contained", A.contains(rect(0, 0, 100, 50), rect(0, 0, 100, 50)), true);
check("subpixel overflow right is contained", A.contains(rect(0, 0, 100, 50), rect(0, 0, 100.3, 50)), true);
check("subpixel overflow bottom is contained", A.contains(rect(0, 0, 100, 50), rect(0, 0, 100, 50.3)), true);
check("subpixel overflow left is contained", A.contains(rect(0, 0, 100, 50), rect(-0.3, 0, 100, 50)), true);
check("subpixel overflow top is contained", A.contains(rect(0, 0, 100, 50), rect(0, -0.3, 100, 50)), true);
check("a pixel of overflow right is not", A.contains(rect(0, 0, 100, 50), rect(0, 0, 101, 50)), false);
check("a pixel of overflow left is not", A.contains(rect(0, 0, 100, 50), rect(-1, 0, 100, 50)), false);
check("a pixel of overflow top is not", A.contains(rect(0, 0, 100, 50), rect(0, -1, 100, 50)), false);
check("a pixel of overflow bottom is not", A.contains(rect(0, 0, 100, 50), rect(0, 0, 100, 51)), false);
check("overlap intersects", A.intersects(rect(0, 0, 100, 50), rect(90, 10, 200, 40)), true);
check("touching edges do not", A.intersects(rect(0, 0, 100, 50), rect(100, 0, 200, 50)), false);
check("clear of each other", A.intersects(rect(0, 0, 100, 50), rect(0, 60, 100, 90)), false);

/* The node filter. One character is text: the diff marker in 03 and the
   focus-item number in 17 were both single nodes and both real AA
   failures. Whitespace is not, and a child's text belongs to the
   child. */
const textNode = (s) => ({ nodeType: 3, textContent: s });
check("a one-character node is text", A.hasOwnText({ childNodes: [textNode("·")] }), true);
check("whitespace is not", A.hasOwnText({ childNodes: [textNode("  \n  ")] }), false);
check("a child element is not own text", A.hasOwnText({ childNodes: [{ nodeType: 1 }] }), false);
check("no children at all", A.hasOwnText({ childNodes: [] }), false);

/* WCAG's large-text threshold, which decides 3:1 against 4.5:1. */
check("24px is large", A.needsRatio(24, false), 3);
check("just under 24px is not", A.needsRatio(23.9, false), 4.5);
check("18.66px bold is large", A.needsRatio(18.66, true), 3);
check("18.66px normal is not", A.needsRatio(18.66, false), 4.5);
check("just under, bold, is not", A.needsRatio(18.65, true), 4.5);

/* The ground rule. `box` is the text; `painted` is the painted
   ancestors from nearest outward, which is the order the DOM walk
   collects them in. */
const box = rect(10, 10, 50, 30);
const painted = (color, r) => ({ color: color, rect: r });

const contained = A.assess(BLACK, box, [painted(HAIRLINE, rect(0, 0, 100, 100))], WHITE);
check("a containing ancestor is the ground", contained.ground, HAIRLINE);
check("and does not straddle", contained.straddles, false);

const bare = A.assess(BLACK, box, [], IVORY);
check("no painted ancestor falls back to the page", bare.ground, IVORY);

/* 07-prototype-animation.html: a beat label positioned clear of the dot
   it is nested in paints on the panel behind it. An ancestor that
   neither contains nor touches the text box is not a ground, and
   reading it produced six phantom failures before 2026-08-17. */
const clear = A.assess(BLACK, box, [painted(HAIRLINE, rect(0, 60, 100, 100))], IVORY);
check("an ancestor clear of the text is not a ground", clear.ground, IVORY);
check("and nothing straddles", clear.straddles, false);

/* Text half on a chip and half off it: the worse of the two grounds is
   the one reported, and it is marked. */
const straddling = A.assess(WHITE, box, [painted(WHITE, rect(30, 0, 200, 100))], BLACK);
check("a worse partial ground wins", straddling.ground, WHITE);
check("and is marked as a straddle", straddling.straddles, true);
check("with the worse ratio", straddling.ratio, 1);

/* A partial ground only wins by being worse. White text crossing onto
   black reads better there, so the page it mostly sits on stays the
   finding. */
const kinder = A.assess(WHITE, box, [painted(BLACK, rect(30, 0, 200, 100))], rgb(128, 128, 128));
check("a kinder partial ground does not win", kinder.ground, rgb(128, 128, 128));
check("and is not called a straddle", kinder.straddles, false);
check("keeping the whole ground's ratio", kinder.ratio, 3.95);

/* Both at once: the text straddles a chip and then sits inside a panel.
   The panel ends the walk, and the chip it crossed on the way still
   counts. */
const both = A.assess(WHITE, box, [
  painted(WHITE, rect(30, 0, 200, 100)),
  painted(BLACK, rect(0, 0, 300, 300))
], IVORY);
check("a straddled chip outranks the containing panel", both.ground, WHITE);
check("straddling either way", both.straddles, true);

for (const problem of failures) console.log(`FAIL ${problem}`);
console.log(`${failures.length ? "FAIL" : "PASS"}: ` +
  `${checked - failures.length}/${checked} rules hold in scripts/audit-contrast.js`);
process.exit(failures.length ? 1 : 0);
