"""Token file contract: every role defined in both themes, and every
text pairing legible in both.

Contrast follows WCAG 2.1 relative luminance. Body text needs 4.5:1;
borders and large UI shapes need 3.0:1.
"""

import os
import re
import sys

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

with open("references/design-system.css", encoding="utf-8") as fh:
    CSS = fh.read()

ROLES = [
    "--bg", "--surface", "--surface-sunken", "--text", "--text-muted",
    "--border", "--border-strong", "--accent", "--ok", "--warn",
    "--danger",
]

# Pairings that must stay legible: (foreground role, background role, min ratio)
#
# The accent and status roles are held to 4.5:1, not 3:1. In these
# genres they are used as text — a "shipped" label, a severity tag, a
# link — and text is what WCAG 1.4.3 measures. Holding them to the
# graphical-object floor would pass colors nobody can read at 14px.
#
# --accent and --ok are checked against --surface-sunken as well as the
# other two grounds. Sunken is the darkest light ground, so it is the
# pairing that binds: an accent that clears 4.5:1 there clears it on
# --bg and --surface too. Templates put accent text on a sunken panel —
# the slot chips in 20, the addition count in 17 — so the pairing is
# real, not hypothetical.
#
# --border is deliberately absent. It is a decorative hairline, not a
# UI component boundary, so WCAG 1.4.11 does not apply to it and
# demanding 3:1 would force a near-black rule between every table row.
# --border-strong is the role that carries that requirement.
PAIRS = [
    ("--text", "--bg", 4.5),
    ("--text", "--surface", 4.5),
    ("--text", "--surface-sunken", 4.5),
    ("--text-muted", "--bg", 4.5),
    ("--text-muted", "--surface", 4.5),
    ("--accent", "--bg", 4.5),
    ("--accent", "--surface", 4.5),
    ("--accent", "--surface-sunken", 4.5),
    ("--ok", "--bg", 4.5),
    ("--ok", "--surface-sunken", 4.5),
    ("--warn", "--bg", 4.5),
    ("--danger", "--bg", 4.5),
    ("--border-strong", "--bg", 3.0),
]


DECL = re.compile(r"(--[a-z0-9-]+)\s*:\s*([^;]+);")


def declarations(src):
    return {m.group(1): m.group(2).strip() for m in DECL.finditer(src)}


def rules(css, prefix=""):
    """Return [(selector, body)] for every rule, media queries flattened.

    The selector of a rule inside a media query is prefixed with the
    query, so a caller can tell the two dark blocks apart.
    """
    out = []
    i = 0
    while True:
        brace = css.find("{", i)
        if brace == -1:
            return out
        selector = re.sub(r"/\*.*?\*/", " ", css[i:brace], flags=re.S)
        selector = " ".join(selector.split())
        depth, j = 1, brace + 1
        while depth:
            if j >= len(css):
                raise SystemExit(f"unbalanced braces after {selector!r}")
            depth += {"{": 1, "}": -1}.get(css[j], 0)
            j += 1
        body = css[brace + 1:j - 1]
        if selector.startswith("@"):
            out.extend(rules(body, prefix=f"{prefix}{selector} "))
        else:
            out.append((prefix + selector, body))
        i = j


def blocks(css):
    """Return (light_decls, dark_decls) as name -> value strings.

    Dark is declared twice — once under prefers-color-scheme for the
    system setting, once under [data-theme="dark"] for an explicit
    choice. Both must say the same thing, or a page would render one
    way when the reader asks and another way when the page asks.
    """
    by_selector = {}
    for selector, body in rules(css):
        by_selector.setdefault(selector, []).append(body)

    media = "@media (prefers-color-scheme: dark) :root:not([data-theme=\"light\"])"
    attribute = ":root[data-theme=\"dark\"]"
    for name, selector in (("system", media), ("explicit", attribute)):
        if selector not in by_selector:
            raise SystemExit(f"no {name} dark block; expected {selector}")

    media_decls = declarations("".join(by_selector[media]))
    attribute_decls = declarations("".join(by_selector[attribute]))
    if media_decls != attribute_decls:
        drift = sorted(set(media_decls) ^ set(attribute_decls)) or [
            k for k in media_decls if media_decls[k] != attribute_decls.get(k)
        ]
        raise SystemExit(
            "the two dark blocks disagree on: " + ", ".join(drift)
        )

    light = declarations("".join(by_selector.get(":root", [])))
    dark = dict(light)
    dark.update(media_decls)
    return light, dark


def resolve(name, decls, seen=None):
    """Resolve a token to a #rrggbb literal, following var() chains."""
    seen = seen or set()
    if name in seen:
        raise SystemExit(f"circular var() chain at {name}")
    seen.add(name)
    if name not in decls:
        raise SystemExit(f"token {name} is not defined")
    value = decls[name]
    ref = re.fullmatch(r"var\((--[a-z0-9-]+)\)", value)
    if ref:
        return resolve(ref.group(1), decls, seen)
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        raise SystemExit(f"token {name} is not a 6-digit hex: {value}")
    return value.lower()


def luminance(hex_color):
    parts = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
           for c in parts]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def main():
    light, dark = blocks(CSS)
    failures = []

    for theme, decls in (("light", light), ("dark", dark)):
        for role in ROLES:
            if role not in decls:
                failures.append(f"{theme}: role {role} is undefined")

    for theme, decls in (("light", light), ("dark", dark)):
        for fg, bg, want in PAIRS:
            if fg not in decls or bg not in decls:
                continue
            got = contrast(resolve(fg, decls), resolve(bg, decls))
            status = "ok " if got >= want else "FAIL"
            print(f"  {status} {theme:5s} {fg:16s} on {bg:16s} "
                  f"{got:5.2f}:1 (needs {want})")
            if got < want:
                failures.append(
                    f"{theme}: {fg} on {bg} is {got:.2f}:1, needs {want}:1"
                )

    for problem in failures:
        print(f"FAIL {problem}")
    print(f"{'FAIL' if failures else 'PASS'}: {len(failures)} problem(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
