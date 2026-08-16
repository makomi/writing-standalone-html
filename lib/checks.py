"""Mechanical checks for standalone HTML templates.

Every function takes the file text and returns a list of problem
strings. An empty list means the check passed.
"""

import pathlib
import re
from html.parser import HTMLParser

TOKEN_BLOCK = re.compile(
    r"/\*\s*TOKENS:BEGIN.*?TOKENS:END\s*\*/", re.S
)
TOKEN_SOURCE = (
    pathlib.Path(__file__).resolve().parent.parent
    / "references" / "design-system.css"
)
HEX = re.compile(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b")

# Functional colour notation. `color-mix()` is deliberately absent: it
# mixes tokens and is the sanctioned way to tint one. Matching bare
# `color(` does not match `color-mix(`, because `-` follows the name.
COLOR_FN = re.compile(
    r"\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color|device-cmyk)\s*\(",
    re.I,
)

# A declaration value: everything between `:` and the end of the
# declaration. Selectors and property names are excluded by
# construction, which is what keeps `.tan-band` from reading as the
# named colour `tan`.
DECL_VALUE = re.compile(r":\s*(?P<val>[^;{}]*)")

# Things inside a value that are not colour literals and must not be
# searched for one: quoted strings, url(), and any custom property
# name -- `var(--ivory)` is a token reference, not the colour ivory.
VALUE_NOISE = re.compile(
    r"""("[^"]*"|'[^']*'|url\([^)]*\)|--[A-Za-z0-9_-]+)""", re.I
)

# CSS named colours. `transparent` and `currentcolor` are keywords that
# carry no value of their own and stay legal.
NAMED_COLORS = frozenset("""
aliceblue antiquewhite aqua aquamarine azure beige bisque black
blanchedalmond blue blueviolet brown burlywood cadetblue chartreuse
chocolate coral cornflowerblue cornsilk crimson cyan darkblue darkcyan
darkgoldenrod darkgray darkgreen darkgrey darkkhaki darkmagenta
darkolivegreen darkorange darkorchid darkred darksalmon darkseagreen
darkslateblue darkslategray darkslategrey darkturquoise darkviolet
deeppink deepskyblue dimgray dimgrey dodgerblue firebrick floralwhite
forestgreen fuchsia gainsboro ghostwhite gold goldenrod gray green
greenyellow grey honeydew hotpink indianred indigo ivory khaki lavender
lavenderblush lawngreen lemonchiffon lightblue lightcoral lightcyan
lightgoldenrodyellow lightgray lightgreen lightgrey lightpink
lightsalmon lightseagreen lightskyblue lightslategray lightslategrey
lightsteelblue lightyellow lime limegreen linen magenta maroon
mediumaquamarine mediumblue mediumorchid mediumpurple mediumseagreen
mediumslateblue mediumspringgreen mediumturquoise mediumvioletred
midnightblue mintcream mistyrose moccasin navajowhite navy oldlace
olive olivedrab orange orangered orchid palegoldenrod palegreen
paleturquoise palevioletred papayawhip peachpuff peru pink plum
powderblue purple rebeccapurple red rosybrown royalblue saddlebrown
salmon sandybrown seagreen seashell sienna silver skyblue slateblue
slategray slategrey snow springgreen steelblue tan teal thistle tomato
turquoise violet wheat white whitesmoke yellow yellowgreen
""".split())
WORD = re.compile(r"(?<![-\w#.])[A-Za-z]+(?![-\w])")

# Fiction that must not survive a conversion. Upstream's sample data is
# branded; a brand name in a shipped template is the most visible
# possible defect. This catches names, not fiction in general.
FICTION = re.compile(r"\bacme\b", re.I)

# Attributes that can carry a color. SVG presentation attributes are the
# reason this list is not just `style`.
COLOR_ATTR = re.compile(
    r"""\b(?:style|fill|stroke|stop-color|flood-color|lighting-color|
         color|bgcolor)\s*=\s*["'](?P<val>[^"']*)["']""",
    re.I | re.X,
)
COMMENT = re.compile(r"<!--.*?-->", re.S)

# Script routes that put a string into CSS. A colour literal is only a
# defect when it reaches the cascade, so the check triggers on the sink
# rather than on the string: `el.dataset.tint = "#d97757"` is data, and
# `el.style.color = "#d97757"` pins a colour past the theme switch.
STYLE_SINK = re.compile(
    r"""\.setProperty\s*\(
      | \.setAttribute\s*\(\s*["']style["']
      | \.style\s*\.\s*[A-Za-z0-9_$]+\s*=(?!=)
      | \.style\s*\[[^\]]*\]\s*=(?!=)
      | \.cssText\s*=(?!=)
      | \.style\s*=(?!=)
      | <style\b""",
    re.I | re.X,
)
# How far back from a string literal to look for its sink. Long enough
# to clear `.setProperty("--surface-sunken", ` and its whitespace.
SINK_WINDOW = 160
VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "source", "track", "wbr",
}
EXTERNAL = [
    (re.compile(r"""\b(?:src|href)\s*=\s*["']\s*(?:https?:)?//""", re.I),
     "absolute or protocol-relative src/href"),
    (re.compile(r"@import\s+(?:url\()?\s*[\"']?\s*(?:https?:)?//", re.I),
     "@import from a remote host"),
    (re.compile(r"url\(\s*[\"']?\s*(?:https?:)?//", re.I),
     "CSS url() pointing at a remote host"),
]


class _Balance(HTMLParser):
    """Flags unclosed or mismatched non-void elements."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.problems = []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.problems.append(f"stray closing </{tag}>")
        elif self.stack[-1] == tag:
            self.stack.pop()
        elif tag in self.stack:
            while self.stack and self.stack[-1] != tag:
                self.problems.append(f"unclosed <{self.stack.pop()}>")
            if self.stack:
                self.stack.pop()
        else:
            self.problems.append(f"stray closing </{tag}>")


def check_parses(text):
    p = _Balance()
    p.feed(text)
    p.close()
    return p.problems + [f"unclosed <{t}>" for t in p.stack]


def check_no_external_refs(text):
    out = []
    for pattern, label in EXTERNAL:
        for m in pattern.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            out.append(f"{label} at line {line}")
    return out


def _blank(text, match):
    """Replace a match with spaces, keeping newlines and line numbers."""
    return text[:match.start()] + re.sub(r"[^\n]", " ", match.group(0)) + \
        text[match.end():]


def check_no_raw_hex_outside_tokens(text):
    """Scan only where a color can legally appear.

    A hex color lives in a <style> block or in a color-bearing
    attribute. It never lives in element text -- and element text is
    full of things shaped like hex: "#4871" is a pull-request number in
    11-status-report.html, not a color. Scanning the raw file would
    fail that template forever for quoting a PR number.

    HTML comments come out too. The provenance header quotes the
    colors it converted -- `stroke="white"` became a token, and the
    note saying so is not a colour.

    So: blank the sentinel token block and the comments, then collect
    the regions where a color is possible and scan those. Blanking
    rather than deleting preserves line numbers, so reported positions
    stay true.
    """
    def blank(match):
        return re.sub(r"[^\n]", " ", match.group(0))

    stripped = COMMENT.sub(blank, TOKEN_BLOCK.sub(blank, text))

    regions = []
    for m in re.finditer(r"<style\b[^>]*>(.*?)</style>", stripped, re.S | re.I):
        regions.append((m.start(1), m.group(1)))
    for m in COLOR_ATTR.finditer(stripped):
        regions.append((m.start("val"), m.group("val")))

    def at(pos):
        return stripped.count("\n", 0, pos) + 1

    out = []
    for offset, chunk in regions:
        for m in HEX.finditer(chunk):
            out.append(f"raw hex {m.group(0)} at line {at(offset + m.start())}")
        for m in COLOR_FN.finditer(chunk):
            name = m.group(0).rstrip("( \t")
            out.append(
                f"raw colour {name}(...) at line {at(offset + m.start())}"
            )
        for pos, word in _value_words(chunk):
            if word.lower() in NAMED_COLORS:
                out.append(
                    f"named colour {word} at line {at(offset + pos)}"
                )
    return sorted(set(out))


def _value_words(chunk):
    """Yield (offset, word) for every bare word in a declaration value.

    A colour attribute carries a value and nothing else, so the whole
    chunk counts when it holds no declaration. Quoted strings, url()
    and custom property names are blanked first: `var(--ivory)` names a
    token, and a token name is not a colour literal.
    """
    values = [(m.start("val"), m.group("val"))
              for m in DECL_VALUE.finditer(chunk)]
    if not values and ":" not in chunk:
        values = [(0, chunk)]
    for offset, value in values:
        clean = VALUE_NOISE.sub(lambda m: " " * len(m.group(0)), value)
        for m in WORD.finditer(clean):
            yield offset + m.start(), m.group(0)


def _js_literals(src):
    """Yield (start, body) for every string literal in a script.

    A hand-rolled scan rather than a regex, because comments and
    strings nest the wrong way for one: blanking `//` first would eat
    the tail of `"https://example.com"`, and finding strings first
    would miss a colour commented out.

    A regex literal containing a quote -- `/["']/` -- is read as a
    string here. That costs a possible false positive inside a style
    assignment, which is the safe direction to be wrong in.
    """
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            j = src.find("\n", i)
            i = n if j < 0 else j
        elif c == "/" and i + 1 < n and src[i + 1] == "*":
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
        elif c in "\"'`":
            j = i + 1
            while j < n:
                if src[j] == "\\":
                    j += 2
                    continue
                if src[j] == c:
                    break
                j += 1
            yield i + 1, src[i + 1:j]
            i = j + 1
        else:
            i += 1


def check_no_colour_in_scripts(text):
    """A colour written into CSS from JavaScript is still a raw colour.

    The other colour check reads <style> blocks and colour-bearing
    attributes, which leaves one route open: a string assigned to
    `style`, `cssText` or `setProperty`. That route pins a colour to
    whichever theme was current, and it fails only after a reader
    interacts, which is the worst place for it to fail.

    Only strings reaching a CSS sink are scanned. A colour in a data
    attribute, a label or a chart legend is not a defect and is not
    reported.
    """
    def blank(match):
        return re.sub(r"[^\n]", " ", match.group(0))

    stripped = COMMENT.sub(blank, TOKEN_BLOCK.sub(blank, text))

    def at(pos):
        return stripped.count("\n", 0, pos) + 1

    out = []
    for block in re.finditer(r"<script\b[^>]*>(.*?)</script>",
                             stripped, re.S | re.I):
        base, body = block.start(1), block.group(1)
        for start, literal in _js_literals(body):
            window = body[max(0, start - SINK_WINDOW):start]
            sink = None
            for m in STYLE_SINK.finditer(window):
                sink = m
            # A `;` `{` or `}` after the sink means the statement that
            # used it has already ended, so this string is unrelated.
            if sink is None or re.search(r"[;{}]", window[sink.end():]):
                continue
            where = at(base + start)
            for m in HEX.finditer(literal):
                out.append(f"raw hex {m.group(0)} in a style assignment "
                           f"at line {where}")
            for m in COLOR_FN.finditer(literal):
                name = m.group(0).rstrip("( \t")
                out.append(f"raw colour {name}(...) in a style assignment "
                           f"at line {where}")
            for _, word in _value_words(literal):
                if word.lower() in NAMED_COLORS:
                    out.append(f"named colour {word} in a style assignment "
                               f"at line {where}")
    return sorted(set(out))


def check_token_block(text):
    """The embedded block must match the source of truth exactly.

    This is invariant 2 in AGENTS.md and the one the whole palette
    rests on: a template edited in place still renders, just with a
    stale palette that no theme switch reaches. `scripts/stamp.sh`
    repairs a mismatch.
    """
    match = TOKEN_BLOCK.search(text)
    if match is None:
        return ["no token block between /* TOKENS:BEGIN */ and "
                "/* TOKENS:END */"]
    if TOKEN_BLOCK.search(text, match.end()):
        return ["more than one token block"]

    want = TOKEN_SOURCE.read_text(encoding="utf-8").strip()
    got = match.group(0)
    if got == want:
        return []

    first = text.count("\n", 0, match.start()) + 1
    got_lines, want_lines = got.split("\n"), want.split("\n")
    for i, (a, b) in enumerate(zip(got_lines, want_lines)):
        if a != b:
            return [f"token block differs from {TOKEN_SOURCE.name} at "
                    f"line {first + i}: expected {b.strip()!r}, "
                    f"found {a.strip()!r} -- run ./scripts/stamp.sh"]
    return [f"token block is {len(got_lines)} lines, "
            f"{TOKEN_SOURCE.name} is {len(want_lines)} "
            f"-- run ./scripts/stamp.sh"]


def check_no_upstream_fiction(text):
    out = []
    for m in FICTION.finditer(text):
        line = text.count("\n", 0, m.start()) + 1
        out.append(f"upstream fiction {m.group(0)!r} at line {line}")
    return out


CHECKS = [
    ("parses", check_parses),
    ("external refs", check_no_external_refs),
    ("token block", check_token_block),
    ("colour", check_no_raw_hex_outside_tokens),
    ("script colour", check_no_colour_in_scripts),
    ("fiction", check_no_upstream_fiction),
]


def run(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    problems = []
    for name, fn in CHECKS:
        for detail in fn(text):
            problems.append(f"{name}: {detail}")
    return problems


if __name__ == "__main__":
    import sys

    status = 0
    for path in sys.argv[1:]:
        for problem in run(path):
            print(f"FAIL {path}: {problem}")
            status = 1
    sys.exit(status)
