/* Reports every text node in the rendered page whose contrast against
   its own ground is below WCAG AA. Run it against a template in each
   theme, by evaluating this source in the loaded page at a 1280x900
   viewport. AGENTS.md, under "Browsing and the theme check", says what
   the browser has to be able to do.

   This is an audit aid, not a test. It needs a browser, and a browser
   must not become a dependency of tests/run-all.sh — that is why it
   lives here and not there. tests/test_tokens.py checks the token pairs
   the design system declares; this checks what a page actually renders,
   including a token pair no one thought to declare.

   Returns a JSON array. An empty array is a pass. */
(function () {
  function parse(c) {
    var m = c.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    var p = m[1].split(/[,\s\/]+/).filter(Boolean).map(Number);
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
  }

  function luminance(c) {
    var f = [c.r, c.g, c.b].map(function (v) {
      v = v / 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2];
  }

  function contrast(a, b) {
    var l1 = luminance(a), l2 = luminance(b);
    return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
  }

  /* Rect geometry. The half-pixel slack absorbs subpixel rounding, so
     a child that fills its parent exactly is not read as overflowing
     it. */
  var EPS = 0.5;

  function contains(outer, inner) {
    return outer.left - EPS <= inner.left
        && outer.right + EPS >= inner.right
        && outer.top - EPS <= inner.top
        && outer.bottom + EPS >= inner.bottom;
  }

  function intersects(a, b) {
    return a.left < b.right && a.right > b.left
        && a.top < b.bottom && a.bottom > b.top;
  }

  /* What the page paints behind a text box. A translucent layer is
     skipped rather than blended: the aim is to name suspects, and a
     blend would invent a colour no token declares.

     Ancestry alone does not make a ground. An absolutely positioned
     child can sit clear of the parent it is nested in — the beat
     labels in 07-prototype-animation.html are offset above and below
     the 12px dot they belong to, and paint on the panel behind it. So
     an ancestor counts only if it contains the text box.

     An ancestor that overlaps without containing is a real ground for
     part of the run: the text straddles an edge, half on a chip and
     half off it. Those are collected and the caller reports whichever
     ground reads worst. */
  function groundsOf(el) {
    var box = el.getBoundingClientRect();
    var partial = [];
    var n = el;
    while (n && n.nodeType === 1) {
      var c = parse(getComputedStyle(n).backgroundColor);
      if (c && c.a > 0.5) {
        var rect = n.getBoundingClientRect();
        if (contains(rect, box)) return { ground: c, partial: partial };
        if (intersects(rect, box)) partial.push(c);
      }
      n = n.parentElement;
    }
    return { ground: pageGround(), partial: partial };
  }

  /* The ground of last resort, for a text box no painted ancestor
     contains. Reading the root rather than assuming white keeps the
     script honest in dark theme. */
  function pageGround() {
    var roots = [document.documentElement, document.body];
    for (var i = 0; i < roots.length; i++) {
      var c = roots[i] && parse(getComputedStyle(roots[i]).backgroundColor);
      if (c && c.a > 0.5) return c;
    }
    return { r: 255, g: 255, b: 255, a: 1 };
  }

  function describe(el) {
    var s = el.tagName.toLowerCase();
    if (el.id) s += "#" + el.id;
    if (el.className && typeof el.className === "string") {
      s += "." + el.className.trim().split(/\s+/).join(".");
    }
    return s;
  }

  var found = [];

  document.querySelectorAll("*").forEach(function (el) {
    var ownText = Array.from(el.childNodes).some(function (n) {
      return n.nodeType === 3 && n.textContent.trim().length > 1;
    });
    if (!ownText) return;

    var cs = getComputedStyle(el);
    if (cs.visibility === "hidden" || cs.display === "none") return;
    if (cs.opacity === "0") return;

    var box = el.getBoundingClientRect();
    if (box.width < 2 || box.height < 2) return;

    var fg = parse(cs.color);
    if (!fg || fg.a < 0.5) return;

    var grounds = groundsOf(el);
    var bg = grounds.ground;
    var ratio = contrast(fg, bg);
    var straddles = false;
    grounds.partial.forEach(function (c) {
      var r = contrast(fg, c);
      if (r < ratio) { ratio = r; bg = c; straddles = true; }
    });

    var size = parseFloat(cs.fontSize);
    var bold = parseInt(cs.fontWeight, 10) >= 700;
    var large = size >= 24 || (size >= 18.66 && bold);
    var needs = large ? 3 : 4.5;

    if (ratio < needs) {
      var finding = {
        selector: describe(el),
        text: el.textContent.trim().slice(0, 40),
        color: cs.color,
        ground: "rgb(" + bg.r + "," + bg.g + "," + bg.b + ")",
        ratio: Math.round(ratio * 100) / 100,
        needs: needs
      };
      /* The text crosses this ground's edge rather than sitting on it,
         so the ratio holds for part of the run. Look at the page. */
      if (straddles) finding.straddles = true;
      found.push(finding);
    }
  });

  return JSON.stringify(found, null, 2);
})()
