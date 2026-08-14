"""Mechanical checks for standalone HTML templates.

Every function takes the file text and returns a list of problem
strings. An empty list means the check passed.
"""

import re
from html.parser import HTMLParser

TOKEN_BLOCK = re.compile(
    r"/\*\s*TOKENS:BEGIN.*?TOKENS:END\s*\*/", re.S
)
HEX = re.compile(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b")

# Attributes that can carry a color. SVG presentation attributes are the
# reason this list is not just `style`.
COLOR_ATTR = re.compile(
    r"""\b(?:style|fill|stroke|stop-color|flood-color|lighting-color|
         color|bgcolor)\s*=\s*["'](?P<val>[^"']*)["']""",
    re.I | re.X,
)
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

    So: blank the sentinel token block, then collect the regions where
    a color is possible and scan those. Blanking rather than deleting
    preserves line numbers, so reported positions stay true.
    """
    stripped = TOKEN_BLOCK.sub(
        lambda m: re.sub(r"[^\n]", " ", m.group(0)), text
    )

    regions = []
    for m in re.finditer(r"<style\b[^>]*>(.*?)</style>", stripped, re.S | re.I):
        regions.append((m.start(1), m.group(1)))
    for m in COLOR_ATTR.finditer(stripped):
        regions.append((m.start("val"), m.group("val")))

    out = []
    for offset, chunk in regions:
        for m in HEX.finditer(chunk):
            line = stripped.count("\n", 0, offset + m.start()) + 1
            out.append(f"raw hex {m.group(0)} at line {line}")
    return sorted(set(out))


CHECKS = [
    ("parses", check_parses),
    ("external refs", check_no_external_refs),
    ("raw hex", check_no_raw_hex_outside_tokens),
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
