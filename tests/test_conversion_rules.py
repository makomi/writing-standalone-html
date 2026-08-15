"""The mapping table must cover every systematic color upstream uses.

"Systematic" means a value appearing three or more times across the 20
files. Those are palette members and shared sub-systems, and a
conversion that meets one without a rule will improvise.

One-off values are deliberately not required: upstream carries roughly
fifty gradient stops and tag tints, and a table of one-offs is a list,
not a rule. Section "Everything else" of conversion-rules.md gives the
ordered procedure for those instead, and this test asserts that
procedure is present.
"""

import os
import pathlib
import re
import sys

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, "lib")
import checks  # noqa: E402

UPSTREAM = pathlib.Path(".upstream")
RULES = pathlib.Path("references/conversion-rules.md")
SYSTEMATIC_AT = 3


def expand(h):
    """Normalize #abc to #aabbcc, lowercase."""
    h = h.lower()
    if len(h) == 4:
        return "#" + "".join(c * 2 for c in h[1:])
    return h[:7]


def main():
    sources = sorted(UPSTREAM.glob("[0-9][0-9]-*.html"))
    if not sources:
        raise SystemExit(
            f"no upstream sources in {UPSTREAM}/ — "
            "run ./scripts/upstream.sh fetch first, "
            "and ./scripts/upstream.sh clean after"
        )

    counts = {}
    for path in sources:
        text = path.read_text(encoding="utf-8")
        for hit in checks.check_no_raw_hex_outside_tokens(text):
            # The check also reports rgb(), hsl() and named colours.
            # Counting is by hex value, so those hits are not ours.
            if not hit.startswith("raw hex "):
                continue
            value = expand(re.search(r"#[0-9a-fA-F]+", hit).group(0))
            counts[value] = counts.get(value, 0) + 1

    systematic = sorted(h for h, n in counts.items() if n >= SYSTEMATIC_AT)
    rules = RULES.read_text(encoding="utf-8").lower()

    failures = [h for h in systematic if h not in rules]
    for h in failures:
        print(f"FAIL unmapped systematic color: {h} ({counts[h]} uses)")

    # The fallback procedure must exist, or one-offs have no home.
    for marker in ("everything else", "near-duplicate", "color-mix"):
        if marker not in rules:
            print(f"FAIL conversion-rules.md is missing '{marker}'")
            failures.append(marker)

    print(f"{len(systematic) - len([f for f in failures if f.startswith('#')])}"
          f"/{len(systematic)} systematic colors mapped "
          f"({len(counts)} distinct values seen, "
          f"{len(counts) - len(systematic)} one-offs)")
    print("PASS" if not failures else "FAIL")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
