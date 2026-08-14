# writing-standalone-html Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code skill that supplies house-styled, self-contained HTML templates for 20 known document genres, derived from `anthropics/html-effectiveness` and re-tokenized for light and dark themes.

**Architecture:** A two-tier CSS token file is the single source of truth for color; every template embeds it verbatim between sentinel comments. Twenty templates are converted from upstream by stripping repeated content to one worked instance and rewriting every color to a semantic token. A read-only `update.sh` detects upstream drift by blob SHA; conversion itself stays agent work under written rules.

**Tech Stack:** Bash, Python 3 standard library only, HTML, CSS. No package manager, no dependencies, no build step. Do not introduce `uv`, npm, or a virtualenv — there is nothing to install.

**Spec:** `docs/specs/2026-08-14-writing-standalone-html-design.md`

**Decisions:** `docs/decisions/0001` through `0005`

## Global Constraints

- Templates must contain **zero external references**. No CDN, no external CSS/JS/fonts/images. This is the property the whole project exists to preserve.
- Templates embed the token block verbatim between `/* TOKENS:BEGIN */` and `/* TOKENS:END */`. They never link `references/design-system.css`.
- Outside that sentinel block, a template contains **zero raw hex literals**. Every color resolves through `var()`.
- Templates reference Tier 2 semantic tokens for anything theme-dependent. Tier 1 raw names are for deliberately theme-invariant decoration only.
- Genre-specific CSS and JavaScript are kept intact and unabridged.
- Repeated sibling content collapses to exactly one instance, marked with an HTML comment naming the repetition.
- Upstream pin: `anthropics/html-effectiveness` at `58c305be97f47b26b678f2c07dec01d4242268ec`.
- **The skill depends on no path outside its own directory.** Drift detection reads blob SHAs from the GitHub API. Anything needing file contents runs `./upstream.sh fetch` to borrow a `--depth 1` clone at `.upstream/`, and `./upstream.sh clean` to delete it. `.upstream/` is git-ignored and must not survive a task. Never hardcode a path to a clone elsewhere on the machine (decision 0006).
- All upstream sample data is fictional and branded "Acme". No Acme string may survive into a template.
- Commit messages follow Conventional Commits with the metadata footer from the user's global CLAUDE.md. Body and footer wrap at 72 characters.
- Never use gendered or gender-split language in any file.

---

### Task 1: Scaffolding, the verification harness, and the upstream borrow script

`verify.sh` is the test suite for every later task, so it is built first and proven against known-good and known-bad input. `upstream.sh` lands here too, because Task 1's own final check needs a real upstream file to run against and nothing else may reach outside the skill folder to find one.

**Files:**
- Create: `verify.sh`
- Create: `upstream.sh`
- Create: `lib/checks.py`
- Create: `tests/fixtures/good.html`
- Create: `tests/fixtures/bad-external-ref.html`
- Create: `tests/fixtures/bad-raw-hex.html`
- Create: `tests/test_verify.sh`
- Create: `tests/test_upstream.sh`
- Create: `.gitignore`

**Interfaces:**
- Consumes: nothing.
- Produces: `verify.sh [path...]` — exits 0 when all checked files pass, 1 otherwise, printing one line per failure as `FAIL <file>: <check>: <detail>`. Defaults to `templates/*.html` when given no arguments. `lib/checks.py` exposes `check_parses(text) -> list[str]`, `check_no_external_refs(text) -> list[str]`, `check_no_raw_hex_outside_tokens(text) -> list[str]`, each returning a list of human-readable problem strings, empty when the file passes. `upstream.sh fetch` clones upstream `--depth 1` into `.upstream/` and prints the commit SHA; `upstream.sh clean` removes it; both are idempotent.

- [ ] **Step 1: Write the failing test**

Create `tests/fixtures/good.html`:

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Fixture</title>
<style>
/* TOKENS:BEGIN */
:root { --ivory: #FAF9F5; --slate: #141413; --bg: var(--ivory); --text: var(--slate); }
/* TOKENS:END */
body { background: var(--bg); color: var(--text); }
</style>
</head>
<body><p>Fixture body.</p></body>
</html>
```

Create `tests/fixtures/bad-external-ref.html` — identical to `good.html` but with this line added inside `<head>`:

```html
<link rel="stylesheet" href="https://cdn.example.com/reset.css">
```

Create `tests/fixtures/bad-raw-hex.html` — identical to `good.html` but with the `body` rule replaced by:

```css
body { background: var(--bg); color: #3D3D3A; }
```

Create `tests/test_verify.sh`:

```bash
#!/usr/bin/env bash
# Test harness for verify.sh. No framework: a failing assertion exits 1.
set -uo pipefail
cd "$(dirname "$0")/.."
fail=0

assert_exit() {
  local want="$1" file="$2" label="$3"
  ./verify.sh "$file" >/dev/null 2>&1
  local got=$?
  if [ "$got" != "$want" ]; then
    echo "ASSERT FAIL: $label — wanted exit $want, got $got"
    fail=1
  else
    echo "ok: $label"
  fi
}

assert_output_contains() {
  local needle="$1" file="$2" label="$3"
  if ./verify.sh "$file" 2>&1 | grep -q "$needle"; then
    echo "ok: $label"
  else
    echo "ASSERT FAIL: $label — output missing '$needle'"
    fail=1
  fi
}

assert_exit 0 tests/fixtures/good.html "clean file passes"
assert_exit 1 tests/fixtures/bad-external-ref.html "external ref fails"
assert_exit 1 tests/fixtures/bad-raw-hex.html "raw hex outside tokens fails"
assert_output_contains "external" tests/fixtures/bad-external-ref.html "names the external-ref check"
assert_output_contains "raw hex" tests/fixtures/bad-raw-hex.html "names the raw-hex check"

exit $fail
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
chmod +x tests/test_verify.sh
./tests/test_verify.sh
```

Expected: fails on every assertion, because `verify.sh` does not exist yet.

- [ ] **Step 3: Write `lib/checks.py`**

```python
"""Mechanical checks for standalone HTML templates.

Every function takes the file text and returns a list of problem
strings. An empty list means the check passed.
"""

import re
from html.parser import HTMLParser

TOKEN_BLOCK = re.compile(
    r"/\*\s*TOKENS:BEGIN\s*\*/.*?/\*\s*TOKENS:END\s*\*/", re.S
)
HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
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


def check_no_raw_hex_outside_tokens(text):
    """Blank the sentinel token block, then scan what remains.

    Blanking preserves line numbers so reported positions stay true to
    the original file.
    """
    stripped = TOKEN_BLOCK.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)
    out = []
    for m in HEX.finditer(stripped):
        line = stripped.count("\n", 0, m.start()) + 1
        out.append(f"raw hex {m.group(0)} at line {line}")
    return out


CHECKS = [
    ("parses", check_parses),
    ("external refs", check_no_external_refs),
    ("raw hex", check_no_raw_hex_outside_tokens),
]


def run(path):
    text = open(path, encoding="utf-8").read()
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
```

- [ ] **Step 4: Write `verify.sh`**

```bash
#!/usr/bin/env bash
# Mechanical verification for standalone HTML templates.
# Usage: ./verify.sh [file...]   (defaults to templates/*.html)
set -uo pipefail
cd "$(dirname "$0")"

files=("$@")
if [ ${#files[@]} -eq 0 ]; then
  shopt -s nullglob
  files=(templates/*.html)
  if [ ${#files[@]} -eq 0 ]; then
    echo "verify: no templates found in templates/" >&2
    exit 1
  fi
fi

echo "verify: checking ${#files[@]} file(s)"
python3 lib/checks.py "${files[@]}"
status=$?
if [ $status -eq 0 ]; then
  echo "verify: all ${#files[@]} file(s) passed"
fi
exit $status
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
chmod +x verify.sh
./tests/test_verify.sh
```

Expected: five `ok:` lines, exit 0.

- [ ] **Step 6: Write `upstream.sh`**

```bash
#!/usr/bin/env bash
# Borrow an ephemeral clone of upstream, then give it back.
#
#   ./upstream.sh fetch   clone --depth 1 into .upstream/, print commit
#   ./upstream.sh clean   delete .upstream/
#
# The skill keeps no permanent copy of upstream (decision 0006).
# .upstream/ is git-ignored and must not survive an ingest run.
set -euo pipefail
cd "$(dirname "$0")"

REPO="https://github.com/anthropics/html-effectiveness.git"
DIR=".upstream"

case "${1:-}" in
  fetch)
    if [ -d "$DIR/.git" ]; then
      echo "upstream: reusing existing clone at $DIR"
    else
      rm -rf "$DIR"
      echo "upstream: cloning $REPO (depth 1)"
      git clone --quiet --depth 1 "$REPO" "$DIR"
    fi
    commit=$(git -C "$DIR" rev-parse HEAD)
    count=$(find "$DIR" -maxdepth 1 -name '[0-9][0-9]-*.html' | wc -l)
    echo "upstream: $DIR at $commit"
    echo "upstream: $count numbered files"
    ;;
  clean)
    if [ -d "$DIR" ]; then
      rm -rf "$DIR"
      echo "upstream: removed $DIR"
    else
      echo "upstream: nothing to remove"
    fi
    ;;
  *)
    echo "usage: ./upstream.sh {fetch|clean}" >&2
    exit 2
    ;;
esac
```

- [ ] **Step 7: Write `tests/test_upstream.sh`**

```bash
#!/usr/bin/env bash
# upstream.sh must be idempotent, and .upstream/ must never be tracked.
set -uo pipefail
cd "$(dirname "$0")/.."
fail=0

./upstream.sh clean >/dev/null 2>&1

./upstream.sh fetch >/dev/null 2>&1
if [ -d .upstream/.git ]; then echo "ok: fetch creates the clone"
else echo "ASSERT FAIL: fetch did not create .upstream"; fail=1; fi

# Fetching twice must not fail or re-clone.
if ./upstream.sh fetch 2>&1 | grep -q "reusing"; then
  echo "ok: fetch is idempotent"
else
  echo "ASSERT FAIL: second fetch did not reuse the clone"; fail=1
fi

# The clone must be invisible to git.
if [ -z "$(git status --porcelain --ignored=no | grep '\.upstream')" ]; then
  echo "ok: .upstream is git-ignored"
else
  echo "ASSERT FAIL: .upstream shows up in git status"; fail=1
fi

./upstream.sh clean >/dev/null 2>&1
if [ ! -d .upstream ]; then echo "ok: clean removes the clone"
else echo "ASSERT FAIL: clean left .upstream behind"; fail=1; fi

# Cleaning twice must not fail.
./upstream.sh clean >/dev/null 2>&1
if [ $? -eq 0 ]; then echo "ok: clean is idempotent"
else echo "ASSERT FAIL: second clean exited non-zero"; fail=1; fi

exit $fail
```

- [ ] **Step 8: Write `.gitignore`**

```
.upstream/
*.tmp
.DS_Store
```

- [ ] **Step 9: Prove the harness catches real upstream input**

Fixtures prove the checks work on material written to fail them. This step proves they work on the real thing:

```bash
./upstream.sh fetch
python3 lib/checks.py .upstream/11-status-report.html
./upstream.sh clean
```

Expected: numerous `raw hex` failures. Record the count — the spec predicts 37 outside `:root`, and this check counts hex inside `:root` too, since upstream carries no sentinel markers.

- [ ] **Step 10: Run every test**

```bash
chmod +x upstream.sh tests/test_upstream.sh
./tests/test_verify.sh && ./tests/test_upstream.sh
```

Expected: all assertions `ok`, and no `.upstream/` directory left behind.

- [ ] **Step 11: Commit**

```bash
git add verify.sh upstream.sh lib tests .gitignore
git commit -m "feat(verify): add template checks and the upstream borrow

Add verify.sh and lib/checks.py covering the three automatable
template properties, plus upstream.sh, which borrows a depth-1 clone
into a git-ignored .upstream/ and deletes it again.

The three checks are: the file parses, it holds no external reference,
and it carries no raw hex outside the sentinel token block. Fixtures
cover one passing and two failing shapes.

Borrowing rather than depending on a clone elsewhere keeps the skill
free of any path outside its own directory (decision 0006).

[Constraint]    Python 3 standard library only; the repo has no
                dependencies and must stay installable by copy.
[Rejected]      An HTML validator dependency, which would break the
                zero-install property for one check.
[Confidence]    high
[Scope-risk]    narrow
[Reversibility] clean
[Directive]     Every later task ends by running ./verify.sh, and
                every task that fetches also cleans.
[Tested]        tests/test_verify.sh and tests/test_upstream.sh pass;
                the raw-hex check fails a real upstream file as
                expected; .upstream stays out of git status.
[Not-tested]    Theme legibility, which stays a manual check."
```

---

### Task 2: The two-tier token file

**Files:**
- Create: `references/design-system.css`
- Create: `tests/test_tokens.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `references/design-system.css`, whose entire content sits between `/* TOKENS:BEGIN */` and `/* TOKENS:END */` and is embedded verbatim into every template. Tier 2 role names, fixed for all later tasks: `--bg`, `--surface`, `--surface-sunken`, `--text`, `--text-muted`, `--border`, `--accent`, `--ok`, `--warn`, `--danger`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_tokens.py`:

```python
"""Token file contract: every role defined in both themes, and every
text pairing legible in both.

Contrast follows WCAG 2.1 relative luminance. Body text needs 4.5:1;
borders and large UI shapes need 3.0:1.
"""

import re
import sys

CSS = open("references/design-system.css", encoding="utf-8").read()

ROLES = [
    "--bg", "--surface", "--surface-sunken", "--text", "--text-muted",
    "--border", "--accent", "--ok", "--warn", "--danger",
]

# Pairings that must stay legible: (foreground role, background role, min ratio)
PAIRS = [
    ("--text", "--bg", 4.5),
    ("--text", "--surface", 4.5),
    ("--text-muted", "--bg", 4.5),
    ("--text-muted", "--surface", 4.5),
    ("--accent", "--bg", 3.0),
    ("--ok", "--bg", 3.0),
    ("--warn", "--bg", 3.0),
    ("--danger", "--bg", 3.0),
    ("--border", "--bg", 3.0),
]


def blocks(css):
    """Return (light_decls, dark_decls) as name -> value strings."""
    dark_match = re.search(
        r"@media\s*\(prefers-color-scheme:\s*dark\)\s*\{(.*)\}\s*$", css, re.S
    )
    if not dark_match:
        raise SystemExit("no prefers-color-scheme: dark block found")
    dark_src = dark_match.group(1)
    light_src = css[: dark_match.start()]
    decl = re.compile(r"(--[a-z0-9-]+)\s*:\s*([^;]+);")
    light = {m.group(1): m.group(2).strip() for m in decl.finditer(light_src)}
    dark = dict(light)
    dark.update({m.group(1): m.group(2).strip() for m in decl.finditer(dark_src)})
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
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in parts]
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
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
python3 tests/test_tokens.py
```

Expected: `FileNotFoundError` for `references/design-system.css`.

- [ ] **Step 3: Write `references/design-system.css`**

The Tier 1 light values are upstream's palette, unchanged. The dark-side raws (`--ink`, `--ink-raised`, `--olive-light`, `--rust-light`) are new: upstream's olive and rust do not reach 3:1 against a dark ground, so dark mode needs lightened variants.

```css
/* TOKENS:BEGIN
   Source of truth: references/design-system.css in writing-standalone-html.
   Embedded verbatim in every template. Do not edit a copy in place —
   edit this file and re-stamp. Tier 1 is the fixed palette; Tier 2 is
   the semantic layer and the only tier that changes with theme. */
:root {
  /* Tier 1 — raw palette, from anthropics/html-effectiveness */
  --ivory:      #faf9f5;
  --slate:      #141413;
  --clay:       #d97757;
  --oat:        #e3dacc;
  --olive:      #788c5d;
  --rust:       #b04a3f;
  --gray-100:   #f0eee6;
  --gray-300:   #d1cfc5;
  --gray-500:   #87867f;
  --gray-700:   #3d3d3a;
  --white:      #ffffff;

  /* Tier 1 — dark-side raws, added by this project */
  --ink:         #1a1a18;
  --ink-raised:  #232320;
  --olive-light: #9bb07a;
  --rust-light:  #d9695c;

  /* Tier 2 — semantic roles, light theme */
  --bg:             var(--ivory);
  --surface:        var(--white);
  --surface-sunken: var(--gray-100);
  --text:           var(--slate);
  --text-muted:     var(--gray-700);
  --border:         var(--gray-300);
  --accent:         var(--clay);
  --ok:             var(--olive);
  --warn:           var(--clay);
  --danger:         var(--rust);

  /* Type and shape, normalized from upstream's drifting spellings */
  --serif: ui-serif, Georgia, "Times New Roman", serif;
  --sans:  system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --mono:  ui-monospace, "SF Mono", Menlo, Consolas, monospace;

  --radius-panel: 12px;
  --radius-row:   8px;
  --border-width: 1.5px;
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg:             var(--ink);
    --surface:        var(--ink-raised);
    --surface-sunken: var(--slate);
    --text:           var(--ivory);
    --text-muted:     var(--gray-300);
    --border:         var(--gray-700);
    --accent:         var(--clay);
    --ok:             var(--olive-light);
    --warn:           var(--clay);
    --danger:         var(--rust-light);
  }
}
/* TOKENS:END */
```

`--warn` intentionally resolves to the same clay as `--accent`. Upstream's palette carries three hues (clay, olive, rust) and no fourth for warnings. If a template genuinely needs accent and warning to differ visually, that is an escalation recorded in `references/conversion-rules.md`, not a silent new color.

- [ ] **Step 4: Run the test to verify it passes**

```bash
python3 tests/test_tokens.py
```

Expected: `PASS: 0 problem(s)`.

If any pairing fails, adjust the dark-side raw values only — never a Tier 1 light value, which is upstream's palette and fixed.

- [ ] **Step 5: Commit**

```bash
git add references/design-system.css tests/test_tokens.py
git commit -m "feat(tokens): add the two-tier design system

Normalize upstream's drifting token names into one Tier 1 palette and
add a Tier 2 semantic layer that is the only tier redefined for dark.
Add four dark-side raws, because upstream's olive and rust do not
reach 3:1 against a dark ground.

[Constraint]    Color-named tokens cannot flip between themes, so a
                semantic tier is required for dark mode (see 0003).
[Rejected]      Parallel --ivory-dark tokens, which would push a theme
                branch to every use site.
[Confidence]    high
[Scope-risk]    narrow
[Reversibility] clean
[Directive]     Tier 1 light values are upstream's; never retune them.
[Tested]        tests/test_tokens.py checks every role is defined in
                both themes and that nine pairings meet WCAG 4.5:1 or
                3.0:1 as appropriate.
[Not-tested]    Perceptual quality of the dark palette; contrast math
                is a floor, not a design review."
```

---

### Task 3: The conversion rules

Conversion is agent work (decision 0004), which makes this file load-bearing: it is the only thing keeping the twentieth conversion consistent with the first.

**Files:**
- Create: `references/conversion-rules.md`
- Create: `tests/test_conversion_rules.py`

**Interfaces:**
- Consumes: Tier 2 role names from Task 2.
- Produces: the written procedure every conversion task follows, including a hex-to-role mapping table covering all 12 distinct hex values found upstream.

- [ ] **Step 1: Write the failing test**

The rules file must map every distinct hex that appears upstream, or a conversion will hit an unmapped color and improvise. Create `tests/test_conversion_rules.py`:

```python
"""The mapping table must cover every distinct hex used upstream."""

import pathlib
import re
import sys

UPSTREAM = pathlib.Path(".upstream")
RULES = pathlib.Path("references/conversion-rules.md")
HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")


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
            "run ./upstream.sh fetch first, and ./upstream.sh clean after"
        )

    upstream_hexes = set()
    for path in sources:
        for m in HEX.finditer(path.read_text(encoding="utf-8")):
            upstream_hexes.add(expand(m.group(0)))

    rules = RULES.read_text(encoding="utf-8").lower()
    missing = sorted(h for h in upstream_hexes if h not in rules)

    for h in missing:
        print(f"FAIL unmapped upstream color: {h}")
    print(f"{'FAIL' if missing else 'PASS'}: "
          f"{len(upstream_hexes) - len(missing)}/{len(upstream_hexes)} mapped")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Borrow the clone and run the test to verify it fails**

```bash
./upstream.sh fetch
python3 tests/test_conversion_rules.py
```

Expected: `FileNotFoundError` for `references/conversion-rules.md`.

Keep `.upstream/` for the next two steps. Step 6 gives it back.

- [ ] **Step 3: Enumerate the real upstream colors before writing the table**

Do not write the mapping from memory. Generate the ground truth:

```bash
grep -ohiE '#[0-9a-f]{3,8}\b' .upstream/[0-9]*.html \
  | tr 'A-F' 'a-f' | sort | uniq -c | sort -rn
```

Copy every distinct value into the table in Step 4. If a color appears that this plan does not list, add a row for it — the plan's list was measured on commit `58c305b` and upstream may have moved.

- [ ] **Step 4: Write `references/conversion-rules.md`**

```markdown
# Conversion rules

How an upstream file becomes a template. Follow these in order. Every
step is mechanical except where it says "judgment", and every judgment
call gets recorded in the file's provenance header.

## 1. Stamp the provenance header

First line of the file, before `<!doctype html>`:

<!--
  Template derived from anthropics/html-effectiveness
  upstream: https://github.com/anthropics/html-effectiveness
  commit:   <full 40-char SHA>
  source:   <NN-name.html>
  blob:     <40-char blob SHA of the source file at that commit>
  converted: <YYYY-MM-DD>
  notes:    <judgment calls made, or "none">
-->

Get the blob SHA with:

    git -C .upstream rev-parse HEAD:<NN-name.html>

## 2. Replace the token block

Delete the file's `:root { ... }` declaration entirely. Paste
`references/design-system.css` verbatim in its place, sentinels
included. Do not merge upstream's token names into it — they are being
replaced, not extended.

## 3. Re-tokenize every color

Work through the file and replace each color with its Tier 2 role.
Two sources to cover: `var(--upstream-name)` references and raw hex
literals, including SVG `fill`, `stroke` and `stop-color` attributes.

Map by the job the color does, never by its value. The same hex is
body text in one place and a border in another.

| Upstream color | Role in context | Token |
|---|---|---|
| `#faf9f5` ivory | page background | `var(--bg)` |
| `#ffffff` / `#fff` white | raised panel, card, sheet | `var(--surface)` |
| `#f0eee6` gray-100/150/50 | sunken well, code block, table stripe | `var(--surface-sunken)` |
| `#141413` slate | body text, headings | `var(--text)` |
| `#3d3d3a` gray-700/800 | secondary text, captions, labels | `var(--text-muted)` |
| `#87867f` gray-500 | tertiary text, placeholder, axis label | `var(--text-muted)` |
| `#d1cfc5` gray-300/200 | rules, borders, dividers | `var(--border)` |
| `#e3dacc` oat | tinted band, highlight fill, tag background | `var(--surface-sunken)` |
| `#d97757` clay | links, active state, primary emphasis | `var(--accent)` |
| `#788c5d` olive | success, passing, shipped, "ok" | `var(--ok)` |
| `#b04a3f` rust | error, failure, blocker, "danger" | `var(--danger)` |
| `#b04a4a` stray | see judgment call below | `var(--danger)` |

Two values share `var(--text-muted)`: upstream uses `#3d3d3a` and
`#87867f` for the same job at different weights. Collapsing them is
intentional. If a file genuinely needs two muted levels in one view,
that is an escalation — record it in the header notes.

`#e3dacc` maps to `var(--surface-sunken)` rather than a tint token,
because no Tier 2 tint role exists. If a template's oat band must stay
visually distinct from its code blocks, use Tier 1 `var(--oat)`
directly and note that the element is theme-invariant by choice.

### Judgment call: `#b04a4a`

Three occurrences upstream, one hex digit from rust `#b04a3f`. Treat as
a typo and map to `var(--danger)`. Record in the header notes as
"collapsed #b04a4a into --danger". Revisit only if a file shows the two
side by side, which would make it deliberate.

## 4. Collapse repeated content

Find every set of repeated sibling elements — ticket rows, timeline
entries, flag toggles, slides, swatches, table rows. Keep exactly one.
Delete the rest. Mark the survivor:

    <!-- repeat per ticket -->

Judgment: pick the instance that exercises the most structure. A ticket
row carrying a label, an assignee and a due date teaches more than a
bare one. If states differ meaningfully — a passing row and a failing
row look different — keep one of each and mark both.

## 5. Strip the fiction

No "Acme" string survives. Replace remaining sample text with short
neutral placeholders that describe their slot: "Section title",
"One-line summary", "2026-01-01". Keep them short — a template is read
for structure, not for prose.

Numbers in charts stay, because a chart with no data has no shape.
Round them to obviously-fake values (10, 25, 40) so they are never
mistaken for real figures.

## 6. Keep the machinery

Genre CSS and JavaScript are kept whole. Do not simplify, refactor or
"clean up" interaction logic. Keyboard navigation, drag-and-drop, tab
switching and live re-render are the expensive parts and the reason the
template exists.

The only permitted JS edit is shrinking an inline data array to match
the single retained instance from step 4.

## 7. Verify

    ./verify.sh templates/<NN-name>.html

All three checks must pass. Then open the file in a browser and confirm
it reads correctly in both light and dark — the fourth check, which no
script can make.
```

- [ ] **Step 5: Run the test to verify it passes**

```bash
python3 tests/test_conversion_rules.py
```

Expected: `PASS: N/N mapped`. If a color is reported unmapped, add a row for it — do not delete the assertion.

- [ ] **Step 6: Give the clone back**

```bash
./upstream.sh clean
git status --porcelain
```

Expected: no `.upstream` entry, because it is git-ignored, and no stray files.

- [ ] **Step 7: Commit**

```bash
git add references/conversion-rules.md tests/test_conversion_rules.py
git commit -m "docs(rules): add the conversion procedure

Write the seven-step procedure turning an upstream file into a
template, with a mapping table from every distinct upstream hex to a
Tier 2 role. A test asserts the table covers every color actually
present upstream, so a conversion cannot hit an unmapped value and
improvise.

[Constraint]    Conversion is agent work (0004), so consistency across
                20 files depends entirely on this file being precise.
[Rejected]      Mapping colors by hex value alone; the same value does
                different jobs in different places.
[Confidence]    medium
[Scope-risk]    narrow
[Reversibility] clean
[Directive]     Any judgment call goes in the provenance header notes.
[Tested]        Mapping table covers every distinct hex found across
                the 20 upstream files at 58c305b.
[Not-tested]    Whether the rules produce consistent output in
                practice; Task 4 is the first real exercise."
```

---

### Task 4: Pilot conversion — `01-exploration-code-approaches.html`

One file, end to end, before committing to the other nineteen. This is the cheapest place to discover that the rules are wrong.

**Files:**
- Create: `templates/01-exploration-code-approaches.html`
- Modify: `references/conversion-rules.md` (only if the pilot exposes a gap)

**Interfaces:**
- Consumes: `references/design-system.css`, `references/conversion-rules.md`, `verify.sh`.
- Produces: the first template, and a validated conversion procedure.

- [ ] **Step 1: Borrow the clone and read the source in full**

```bash
./upstream.sh fetch
cat .upstream/01-exploration-code-approaches.html
```

453 lines, zero raw hex outside `:root`. It was chosen as the pilot precisely because the color work is a straight token swap, isolating the content-collapse rules for their first test.

- [ ] **Step 2: Capture the blob SHA for the provenance header**

```bash
git -C .upstream \
  rev-parse 58c305be97f47b26b678f2c07dec01d4242268ec:01-exploration-code-approaches.html
```

- [ ] **Step 3: Convert, following all seven rules in order**

Apply `references/conversion-rules.md` steps 1 through 6. For this file specifically: the three approach columns are repeated siblings under rule 4. Keep one column, mark it `<!-- repeat per approach -->`. The trade-off list inside the retained column is itself a repeated set — keep two items, since a single list item does not show that the list is a list.

- [ ] **Step 4: Run verification**

```bash
./verify.sh templates/01-exploration-code-approaches.html
```

Expected: `verify: all 1 file(s) passed`.

- [ ] **Step 5: Check both themes by eye**

Open the file in a browser. Confirm in light mode, then switch the OS or browser to dark and confirm again. Look for: text that vanishes into its background, borders that disappear, and any element still showing an upstream color because its hex was missed inside an attribute.

- [ ] **Step 6: Fix the rules if the pilot exposed a gap**

If any judgment during Step 3 was not covered by `conversion-rules.md`, add it now, before nineteen more files inherit the ambiguity. Re-run `python3 tests/test_conversion_rules.py`.

- [ ] **Step 7: Give the clone back**

```bash
./upstream.sh clean
```

- [ ] **Step 8: Commit**

```bash
git add templates/01-exploration-code-approaches.html references/conversion-rules.md
git commit -m "feat(templates): convert 01-exploration-code-approaches

First template through the full procedure. Chosen as pilot because it
carries zero raw hex outside :root, isolating the content-collapse
rules for their first real test. Three approach columns collapse to
one marked instance.

[Constraint]    Rules must survive contact with a real file before
                nineteen more inherit them.
[Rejected]      Starting with a heavy file; a rules bug found on
                10-svg-illustrations would cost 105 redone mappings.
[Confidence]    medium
[Scope-risk]    narrow
[Reversibility] clean
[Directive]     Any rule gap found here is fixed before Task 5.
[Tested]        ./verify.sh passes; both themes checked in a browser.
[Not-tested]    Whether the procedure generalizes to files carrying
                SVG fills, which Task 7 settles."
```

---

### Task 5: The five remaining zero-hex files

**Files:**
- Create: `templates/02-exploration-visual-designs.html`
- Create: `templates/06-component-variants.html`
- Create: `templates/08-prototype-interaction.html`
- Create: `templates/16-implementation-plan.html`
- Create: `templates/20-editor-prompt-tuner.html`

**Interfaces:**
- Consumes: the procedure validated in Task 4.
- Produces: six templates total in `templates/`.

These five carry zero raw hex outside `:root`, so the color work stays a straight token swap and the effort is concentrated in content collapse.

- [ ] **Step 1: Borrow the clone, then convert each file**

```bash
./upstream.sh fetch
```

For each of the five, apply `references/conversion-rules.md` steps 1 through 6 exactly as in Task 4. Capture each blob SHA with:

```bash
git -C .upstream \
  rev-parse 58c305be97f47b26b678f2c07dec01d4242268ec:<NN-name.html>
```

File-specific notes for rule 4:

- `02-exploration-visual-designs.html` — the design option cards repeat. Keep two, not one: the file's whole purpose is side-by-side comparison, and one card cannot show a comparison.
- `06-component-variants.html` — the variant grid repeats along two axes, size and state. Keep one row and one column that intersect, so both axes stay visible.
- `08-prototype-interaction.html` — four linked screens. Keep two, because a flow needs a source and a destination for the link wiring to make sense.
- `16-implementation-plan.html` — milestones, risk-table rows and mockup blocks each repeat independently. Collapse each set separately; do not collapse the whole plan to one section.
- `20-editor-prompt-tuner.html` — three sample inputs repeat, but the live re-render JS iterates them. Keep one sample and shrink the JS data array to match, which rule 6 permits.

- [ ] **Step 2: Verify all six templates together**

```bash
./verify.sh
```

Expected: `verify: all 6 file(s) passed`.

- [ ] **Step 3: Check each in both themes**

Open all five new files in a browser, light then dark. `20-editor-prompt-tuner.html` additionally needs its live re-render exercised: type into the template field and confirm the sample output still updates.

- [ ] **Step 4: Give the clone back**

```bash
./upstream.sh clean
```

- [ ] **Step 5: Commit**

```bash
git add templates/
git commit -m "feat(templates): convert the five remaining zero-hex files

Convert 02, 06, 08, 16 and 20. All carry zero raw hex outside :root,
so the work is content collapse rather than re-tokenization. Two files
keep two instances rather than one: a comparison needs two cards, and
a flow needs two screens.

[Constraint]    Collapsing to exactly one instance loses the pattern
                where the pattern IS the comparison.
[Rejected]      A blanket one-instance rule, which would have made
                02 and 08 meaningless.
[Confidence]    high
[Scope-risk]    narrow
[Reversibility] clean
[Directive]     Heavier files follow in Tasks 6 and 7.
[Tested]        ./verify.sh passes on all six; both themes checked by
                eye; the prompt tuner's re-render exercised.
[Not-tested]    SVG attribute re-tokenization, which starts in Task 6."
```

---

### Task 6: The eleven low-hex files

**Files:**
- Create: `templates/03-code-review-pr.html` (14 raw hex)
- Create: `templates/04-code-understanding.html` (7)
- Create: `templates/07-prototype-animation.html` (4)
- Create: `templates/09-slide-deck.html` (10)
- Create: `templates/12-incident-report.html` (3)
- Create: `templates/13-flowchart-diagram.html` (10)
- Create: `templates/14-research-feature-explainer.html` (4)
- Create: `templates/15-research-concept-explainer.html` (12)
- Create: `templates/17-pr-writeup.html` (1)
- Create: `templates/18-editor-triage-board.html` (10)
- Create: `templates/19-editor-feature-flags.html` (7)

**Interfaces:**
- Consumes: the procedure and mapping table.
- Produces: 17 templates total in `templates/`.

Counts are raw hex outside `:root`, measured at `58c305b`. `04`, `13` and `09` carry theirs inside SVG attributes, which is the first exercise of that part of rule 3.

- [ ] **Step 1: Borrow the clone, then convert in ascending order of hex count**

```bash
./upstream.sh fetch
```

Order: `17`, `12`, `07`, `14`, `04`, `19`, `09`, `13`, `18`, `15`, `03`. Ascending order means any weakness in the SVG mapping rule surfaces on a 4-hex file rather than a 14-hex one.

Apply `references/conversion-rules.md` steps 1 through 6 to each.

File-specific notes for rule 4:

- `03-code-review-pr.html` — diff hunks and margin notes repeat. Keep one hunk with one attached note, plus one severity tag of each level present, since the severity colors are the point.
- `04-code-understanding.html` — module boxes repeat inside an SVG. Keep two boxes and the arrow between them; a module map with one box shows no relationship.
- `07-prototype-animation.html` — the slider row repeats per parameter. Keep one slider, wired.
- `09-slide-deck.html` — slides repeat. Keep two, so the keyboard navigation has somewhere to navigate to.
- `12-incident-report.html` — timeline entries, log lines and checklist rows repeat independently. Collapse each set separately.
- `13-flowchart-diagram.html` — pipeline steps repeat inside an SVG, each with a click handler. Keep two steps and the connector, and shrink the step-detail data object to match.
- `14-research-feature-explainer.html` — collapsible steps, FAQ entries and config tabs each repeat. Keep one of each, but keep two tabs, because one tab cannot demonstrate tab switching.
- `15-research-concept-explainer.html` — the live demo's nodes repeat. Keep the demo functional with two nodes and shrink its data array.
- `17-pr-writeup.html` — the file-by-file tour repeats. Keep one file entry.
- `18-editor-triage-board.html` — thirty tickets across four columns. Keep one ticket, and keep all four columns: the columns are the taxonomy, not repeated content.
- `19-editor-feature-flags.html` — flag rows repeat within groups, and groups repeat. Keep one group with two flags, because the dependency warning needs a prerequisite flag to point at.

- [ ] **Step 2: Verify all seventeen templates together**

```bash
./verify.sh
```

Expected: `verify: all 17 file(s) passed`.

- [ ] **Step 3: Exercise the interactive files**

Static checks cannot catch broken JS. In a browser, confirm:

- `09` — left and right arrow keys move between the two retained slides.
- `13` — clicking a step opens its detail panel.
- `14` — tabs switch.
- `15` — the demo responds to adding and removing a node.
- `18` — a ticket drags between columns, and "copy as markdown" produces output.
- `19` — toggling the prerequisite flag off raises the dependency warning.
- `07` — moving a slider changes the animation.

- [ ] **Step 4: Check each in both themes**

Pay particular attention to `03`'s severity tags and `12`'s timeline: both encode meaning in color, so a token mapped to the wrong role destroys information rather than just looking wrong.

- [ ] **Step 5: Give the clone back**

```bash
./upstream.sh clean
```

- [ ] **Step 6: Commit**

```bash
git add templates/
git commit -m "feat(templates): convert the eleven low-hex files

Convert 03, 04, 07, 09, 12, 13, 14, 15, 17, 18 and 19, in ascending
order of raw-hex count so the SVG attribute mapping is first exercised
on a 4-hex file rather than a 14-hex one. Several files retain two
instances where one cannot show the pattern: two slides for keyboard
navigation, two tabs for tab switching, two flags for the dependency
warning.

[Constraint]    Files encoding meaning in color (03 severity tags, 12
                timeline) break silently if a token maps to the wrong
                role, so both were checked by eye in both themes.
[Rejected]      Converting in file-number order, which would have hit
                the 14-hex file before the mapping rule was exercised.
[Confidence]    medium
[Scope-risk]    narrow
[Reversibility] clean
[Directive]     Only the three heavy files remain.
[Tested]        ./verify.sh passes on all 17; seven interactive files
                exercised in a browser; both themes checked.
[Not-tested]    Long-run rendering on browsers other than the one
                used for the eye check."
```

---

### Task 7: The three heavy files

**Files:**
- Create: `templates/05-design-system.html` (30 raw hex)
- Create: `templates/11-status-report.html` (37)
- Create: `templates/10-svg-illustrations.html` (105)

**Interfaces:**
- Consumes: the procedure, now exercised on 17 files.
- Produces: all 20 templates.

- [ ] **Step 1: Borrow the clone, then convert `05-design-system.html`**

```bash
./upstream.sh fetch
```

This file is a special case worth stating plainly: it is a page *about* a design system, so its swatches display colors as content. A swatch showing `#d97757` is not a themed surface — it is a sample of clay, and it must keep showing clay in both themes.

Use Tier 1 tokens directly for swatch fills (`var(--clay)`, `var(--olive)`), and Tier 2 for the page chrome around them. Record in the header notes: "swatch fills use Tier 1 deliberately; they are content, not chrome."

The swatch grid repeats. Keep one swatch per Tier 1 color, since the palette is the content.

- [ ] **Step 2: Convert `11-status-report.html`**

37 raw hex, mostly in the inline chart. Chart series colors are semantic — shipped is `var(--ok)`, slipped is `var(--danger)` — so they map cleanly. Keep the chart's data array at three or four rounded, obviously-fake values per rule 5.

The shipped and slipped lists repeat. Keep two entries in each, since a status report with one item in each column does not show the contrast it exists to show.

- [ ] **Step 3: Convert `10-svg-illustrations.html`**

The hard file: 105 hex literals in SVG `fill`, `stroke` and `stop-color` attributes, outside the CSS cascade.

Do not rewrite 105 attributes one at a time. Lift them into CSS classes instead:

```html
<!-- before -->
<rect fill="#F0EEE6" stroke="#D1CFC5" />

<!-- after -->
<rect class="fig-well" />
```

```css
.fig-well { fill: var(--surface-sunken); stroke: var(--border); }
```

`fill` and `stroke` are presentation attributes, so a CSS rule overrides them and accepts `var()` where the attribute does not. This converts 105 scattered decisions into roughly eight named classes, and it is the only way the file stays maintainable when a token changes.

Gradients need care: `stop-color` also accepts `var()` via CSS, but each `<stop>` needs a class or a scoped selector.

The figure sheet holds several independent illustrations. Keep two, not one: the file's purpose is a sheet of figures, and one figure is not a sheet.

- [ ] **Step 4: Verify all twenty templates**

```bash
./verify.sh
```

Expected: `verify: all 20 file(s) passed`.

- [ ] **Step 5: Measure the result against the estimate**

```bash
wc -l templates/*.html | tail -1
```

The spec projects 4,000–5,000 lines from 11,611 upstream. Record the real number. If it lands far outside that band, say so rather than quietly accepting it: far below suggests content was over-stripped, far above suggests repeated content survived.

- [ ] **Step 6: Check all three in both themes**

`10` needs the closest look, since a missed `fill` attribute shows as an upstream color sitting unchanged on a dark background.

- [ ] **Step 7: Give the clone back**

```bash
./upstream.sh clean
```

- [ ] **Step 8: Commit**

```bash
git add templates/
git commit -m "feat(templates): convert the three heavy files

Convert 05, 11 and 10, completing all twenty. In 10, the 105 SVG
presentation attributes are lifted into roughly eight CSS classes
rather than rewritten individually — fill and stroke accept var()
through CSS but not as attributes, and named classes keep the file
maintainable when a token changes.

05 is a deliberate exception: its swatches display colors as content,
so swatch fills use Tier 1 tokens and stay theme-invariant while the
page chrome around them uses Tier 2.

[Constraint]    SVG presentation attributes cannot take var()
                directly, so re-tokenizing them requires moving them
                into the cascade.
[Rejected]      Rewriting 105 attributes in place, which would leave
                the file unmaintainable on the next token change.
[Confidence]    medium
[Scope-risk]    narrow
[Reversibility] messy
[Directive]     All 20 templates exist; wiring comes next.
[Tested]        ./verify.sh passes on all 20; all three checked in
                both themes, with 10 checked attribute by attribute.
[Not-tested]    Gradient rendering in browsers that treat stop-color
                var() inheritance differently."
```

---

### Task 8: The manifest and the update checker

**Files:**
- Create: `templates/MANIFEST.json`
- Create: `update.sh`
- Create: `lib/manifest.py`
- Create: `lib/github.py`
- Create: `tests/test_update.sh`

**Interfaces:**
- Consumes: the 20 templates and their provenance headers; `upstream.sh` from Task 1.
- Produces: `update.sh` — read-only, needs no clone, exits 0 when everything is current, 1 when work is pending, 2 when the check itself could not run. `lib/manifest.py` exposes `load(path) -> dict`, `stamp(path, manifest) -> None`, and `compare(manifest, upstream_shas) -> dict` returning keys `unchanged`, `changed`, `new`, `removed`, each a sorted list of filenames. `lib/github.py` exposes `head_commit(repo) -> str` and `tree_blobs(repo, commit) -> dict[str, str]`.

Detection reads blob SHAs from the GitHub API rather than a clone (decision 0006). This was verified before the design was settled: `11-status-report.html` returns `764665143d3731ccb5e8978898bf7d7a5e46cc5f` from both the API and `git rev-parse`, so the comparison is unchanged.

- [ ] **Step 1: Write the failing test**

Create `tests/test_update.sh`:

```bash
#!/usr/bin/env bash
# update.sh must be read-only and must classify drift correctly.
set -uo pipefail
cd "$(dirname "$0")/.."
fail=0

# 1. A clean tree must stay clean after a run.
before=$(git status --porcelain | sort)
./update.sh >/dev/null 2>&1
after=$(git status --porcelain | sort)
if [ "$before" == "$after" ]; then
  echo "ok: update.sh does not write to the working tree"
else
  echo "ASSERT FAIL: update.sh modified the working tree"
  diff <(echo "$before") <(echo "$after")
  fail=1
fi

# 2. Against the pinned commit, everything must read as unchanged.
if ./update.sh 2>&1 | grep -q "unchanged: 20"; then
  echo "ok: all 20 files unchanged at the pinned commit"
else
  echo "ASSERT FAIL: expected 20 unchanged files"
  fail=1
fi

# 3. A tampered manifest SHA must be reported as changed, exit 1.
cp templates/MANIFEST.json "$TMPDIR/manifest.bak"
python3 - <<'PY'
import json
m = json.load(open("templates/MANIFEST.json"))
m["files"][0]["upstream_blob_sha"] = "0" * 40
json.dump(m, open("templates/MANIFEST.json", "w"), indent=2)
PY
./update.sh >/dev/null 2>&1
if [ $? -eq 1 ]; then
  echo "ok: pending work exits non-zero"
else
  echo "ASSERT FAIL: tampered manifest did not exit 1"
  fail=1
fi
cp "$TMPDIR/manifest.bak" templates/MANIFEST.json

# 4. A broken API endpoint must exit 2, not 1. Exit 1 means "drift
#    found"; a wrapper must never read an outage as pending work.
if GITHUB_API_BASE="https://api.github.com/repos/anthropics/does-not-exist-$$" \
     ./update.sh >/dev/null 2>&1; then
  echo "ASSERT FAIL: unreachable endpoint should not exit 0"
  fail=1
elif [ $? -eq 2 ]; then
  echo "ok: a broken check exits 2, distinct from drift"
else
  echo "ASSERT FAIL: unreachable endpoint did not exit 2"
  fail=1
fi

# 5. Detection must not need a clone.
./upstream.sh clean >/dev/null 2>&1
if ./update.sh >/dev/null 2>&1; [ $? -ne 2 ]; then
  echo "ok: detection runs with no local clone"
else
  echo "ASSERT FAIL: update.sh needs a clone it should not need"
  fail=1
fi

exit $fail
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
chmod +x tests/test_update.sh
./tests/test_update.sh
```

Expected: fails, `update.sh` does not exist.

- [ ] **Step 3: Write `lib/manifest.py`**

```python
"""Read, compare and stamp templates/MANIFEST.json."""

import json


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def stamp(path, manifest):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def compare(manifest, upstream_shas):
    """Classify every file into exactly one of four buckets.

    upstream_shas maps upstream filename -> current blob SHA.
    Enumerating upstream (not the manifest) is what makes a newly
    added upstream file visible.
    """
    recorded = {e["upstream_source"]: e["upstream_blob_sha"]
                for e in manifest["files"]}
    unchanged, changed, new = [], [], []
    for name, sha in upstream_shas.items():
        if name not in recorded:
            new.append(name)
        elif recorded[name] == sha:
            unchanged.append(name)
        else:
            changed.append(name)
    removed = [n for n in recorded if n not in upstream_shas]
    return {
        "unchanged": sorted(unchanged),
        "changed": sorted(changed),
        "new": sorted(new),
        "removed": sorted(removed),
    }
```

- [ ] **Step 4: Write `lib/github.py`**

Detection talks to the API, not to git. Standard library only — `urllib`, no `requests`.

```python
"""Read upstream blob SHAs from the GitHub API.

GitHub returns real git blob SHAs, so the values compare directly
against a manifest recorded from a clone. Verified:
11-status-report.html reads 764665143d3731ccb5e8978898bf7d7a5e46cc5f
from both this API and `git rev-parse`.
"""

import json
import os
import urllib.error
import urllib.request

BASE = os.environ.get("GITHUB_API_BASE",
                      "https://api.github.com/repos/anthropics/html-effectiveness")


class UpstreamUnavailable(Exception):
    """The check could not run. Distinct from 'upstream drifted'."""


def _get(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "writing-standalone-html-update",
    })
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        if exc.code == 403 and "rate limit" in exc.read().decode(errors="replace").lower():
            raise UpstreamUnavailable(
                "GitHub rate limit reached; set GITHUB_TOKEN or wait"
            ) from exc
        raise UpstreamUnavailable(f"HTTP {exc.code} from {url}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise UpstreamUnavailable(f"cannot reach {url}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise UpstreamUnavailable(f"malformed JSON from {url}") from exc


def head_commit():
    """Full 40-character SHA of the current upstream HEAD."""
    data = _get(f"{BASE}/commits?per_page=1")
    if not data:
        raise UpstreamUnavailable("no commits returned")
    return data[0]["sha"]


def tree_blobs(commit):
    """Map upstream filename -> blob SHA for every NN-*.html at commit."""
    data = _get(f"{BASE}/git/trees/{commit}")
    if data.get("truncated"):
        raise UpstreamUnavailable(
            "tree response truncated; upstream has outgrown a single page"
        )
    return {
        e["path"]: e["sha"]
        for e in data["tree"]
        if e["type"] == "blob"
        and e["path"].endswith(".html")
        and e["path"][:2].isdigit()
    }
```

The `truncated` guard matters: the API pages large trees, and a silently truncated response would read as "these files were removed upstream". Upstream currently returns 20 files untruncated.

- [ ] **Step 5: Generate `templates/MANIFEST.json`**

The manifest is written once here, from the clone that is already present after Task 7. Afterwards only ingest mode writes it.

```bash
./upstream.sh fetch
python3 - <<'PY'
import json, subprocess, datetime, pathlib, re

CLONE = ".upstream"
HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
commit = subprocess.run(["git", "-C", CLONE, "rev-parse", "HEAD"],
                        capture_output=True, text=True, check=True).stdout.strip()

entries = []
for tpl in sorted(pathlib.Path("templates").glob("[0-9][0-9]-*.html")):
    src = tpl.name
    blob = subprocess.run(["git", "-C", CLONE, "rev-parse", f"{commit}:{src}"],
                          capture_output=True, text=True, check=True).stdout.strip()
    upstream_text = (pathlib.Path(CLONE) / src).read_text(encoding="utf-8")
    entries.append({
        "template": tpl.name,
        "upstream_source": src,
        "upstream_blob_sha": blob,
        "converted_at": datetime.date.today().isoformat(),
        "raw_hex_count_at_conversion": len(HEX.findall(upstream_text)),
    })

manifest = {
    "upstream_repo": "anthropics/html-effectiveness",
    "upstream_commit": commit,
    "checked_at": datetime.datetime.now(datetime.timezone.utc)
                    .isoformat(timespec="seconds").replace("+00:00", "Z"),
    "files": entries,
}
with open("templates/MANIFEST.json", "w", encoding="utf-8") as fh:
    json.dump(manifest, fh, indent=2)
    fh.write("\n")
print(f"wrote {len(entries)} entries at {commit[:7]}")
PY
./upstream.sh clean
```

Expected: `wrote 20 entries at 58c305b`.

- [ ] **Step 6: Write `update.sh`**

```bash
#!/usr/bin/env bash
# Read-only upstream drift check over the GitHub API.
#
# Needs no clone and touches no path outside this directory.
# Never edits a template and never writes MANIFEST.json.
#
# Exit codes, which must stay distinct:
#   0  everything current
#   1  upstream drifted, ingest mode has work
#   2  the check itself could not run
set -uo pipefail
cd "$(dirname "$0")"

python3 - <<'PY'
import sys
sys.path.insert(0, "lib")
import github as G
import manifest as M

try:
    commit = G.head_commit()
    upstream = G.tree_blobs(commit)
except G.UpstreamUnavailable as exc:
    print(f"update: cannot check upstream: {exc}", file=sys.stderr)
    sys.exit(2)

if not upstream:
    print("update: upstream returned no numbered files; refusing to "
          "report 20 removals", file=sys.stderr)
    sys.exit(2)

print(f"update: upstream HEAD is {commit[:7]} ({len(upstream)} files)")

result = M.compare(M.load("templates/MANIFEST.json"), upstream)

for bucket in ("unchanged", "changed", "new", "removed"):
    names = result[bucket]
    print(f"{bucket}: {len(names)}")
    if bucket != "unchanged":
        for n in names:
            print(f"  {n}")

pending = sum(len(result[b]) for b in ("changed", "new", "removed"))
if pending:
    print(f"\nupdate: {pending} file(s) need ingest mode")
    print("update: run ./upstream.sh fetch, convert per "
          "references/conversion-rules.md, then ./upstream.sh clean")
    sys.exit(1)
print("\nupdate: everything current")
PY
```

The empty-response guard is deliberate. An API change that returns a tree without the numbered files would otherwise classify all 20 as "removed upstream" — a confident, catastrophic, wrong answer. Refusing to report is the correct response to an implausible result.

- [ ] **Step 7: Run the tests to verify they pass**

```bash
chmod +x update.sh
./tests/test_update.sh
```

Expected: five `ok:` lines, exit 0, and no `.upstream/` left behind.

- [ ] **Step 8: Commit**

```bash
git add update.sh lib/manifest.py lib/github.py templates/MANIFEST.json tests/test_update.sh
git commit -m "feat(update): add read-only upstream drift detection

Add update.sh, which fetches upstream, enumerates every NN-*.html at
HEAD over the GitHub API and diffs blob SHAs against
templates/MANIFEST.json, printing four buckets. Detection needs no
clone, so the skill depends on no path outside its own directory.

Enumerating upstream rather than the manifest is what makes a newly
added upstream file visible; the reverse would have made it invisible
by construction.

Two guards protect against a confident wrong answer: an empty tree
response refuses to report 20 removals, and a truncated one refuses to
report at all.

[Constraint]    A cron-run checker must not dirty the git tree, so
                checked_at is stamped by ingest mode, not by update.sh.
[Rejected]      Iterating the manifest's 20 known files, which cannot
                see a 21st file appearing upstream. Also rejected: a
                long-lived local clone, which made the skill depend on
                a directory whose lifetime nobody manages (0006).
[Confidence]    high
[Scope-risk]    narrow
[Reversibility] clean
[Directive]     Ingest mode is the only writer of MANIFEST.json.
[Tested]        tests/test_update.sh asserts the tree stays clean, all
                20 read as unchanged at the pin, a tampered SHA exits
                1, an unreachable endpoint exits 2, and detection runs
                with no clone present. API blob SHAs verified equal to
                git blob SHAs for 11-status-report.html.
[Not-tested]    Behavior against an upstream commit that actually
                renames or deletes a file; rate-limit handling under a
                real 403."
```

---

### Task 9: SKILL.md

The entry point. Everything before this task is inert until Claude Code can find and select a template.

**Files:**
- Create: `SKILL.md`

**Interfaces:**
- Consumes: all 20 templates, `references/design-system.css`, `references/conversion-rules.md`.
- Produces: the skill's trigger surface and selection table.

- [ ] **Step 1: Write `SKILL.md`**

The description is the trigger. Decision 0001 requires it to name genres, not the phrase "HTML file".

```markdown
---
name: writing-standalone-html
description: Use when producing a self-contained HTML page for one of these document genres — weekly status report, incident post-mortem, implementation plan, PR write-up or annotated code review, module map, feature or concept explainer, flowchart, slide deck, design system sheet, component variant sheet, animation or interaction prototype, SVG figure sheet, code-approach comparison, or a small single-purpose editing UI such as a triage board, feature-flag panel or prompt tuner. Supplies a house template with a shared light and dark token system. Not for app UI, marketing pages, or general web development — those stay with frontend-design.
---

# Writing standalone HTML

## What this gives you

Twenty templates, one per document genre, each a self-contained page:
no build step, no dependency, no external reference. All share one
two-tier token system that works in light and dark.

Templates are **inputs to generation, not finished pages**. Each keeps
one worked instance of every repeating pattern, marked with a comment.
Replace the instance; do not ship it.

## Selecting a template

| You are producing | Template |
|---|---|
| Comparison of two or more ways to solve a problem | `01-exploration-code-approaches.html` |
| Several layout or palette directions, rendered live | `02-exploration-visual-designs.html` |
| An annotated diff or code review | `03-code-review-pr.html` |
| A map of an unfamiliar module or package | `04-code-understanding.html` |
| A design system: colors, type scale, spacing | `05-design-system.html` |
| Every size and state of one component | `06-component-variants.html` |
| An animation tuned in isolation | `07-prototype-animation.html` |
| A clickable multi-screen flow | `08-prototype-interaction.html` |
| A slide deck | `09-slide-deck.html` |
| A sheet of inline SVG figures | `10-svg-illustrations.html` |
| A weekly or sprint status report | `11-status-report.html` |
| An incident post-mortem | `12-incident-report.html` |
| A pipeline or process flowchart | `13-flowchart-diagram.html` |
| How a feature works in this repo | `14-research-feature-explainer.html` |
| A concept taught with a live demo | `15-research-concept-explainer.html` |
| An implementation plan with milestones and risks | `16-implementation-plan.html` |
| A PR write-up for reviewers | `17-pr-writeup.html` |
| A ticket triage board | `18-editor-triage-board.html` |
| A feature-flag editor | `19-editor-feature-flags.html` |
| A prompt tuner with live preview | `20-editor-prompt-tuner.html` |

If nothing matches, this skill does not apply. Say so and write the
page without a template rather than forcing a bad fit.

## Rules

1. **Copy the token block verbatim.** It sits between
   `/* TOKENS:BEGIN */` and `/* TOKENS:END */`. Never edit it inside a
   generated page, and never link it as an external stylesheet.
2. **Never invent a color.** Every color comes from a Tier 2 semantic
   token: `--bg`, `--surface`, `--surface-sunken`, `--text`,
   `--text-muted`, `--border`, `--accent`, `--ok`, `--warn`,
   `--danger`. Tier 1 raw names are only for something deliberately
   theme-invariant, such as a swatch that displays a color as content.
3. **Stay self-contained.** No CDN, no external font, no remote image.
   Embed images as data URIs or draw them as inline SVG.
4. **Replace every worked instance.** The retained sample is a shape to
   follow, not content to ship. No placeholder text survives.
5. **Keep the machinery.** Interaction logic in the template works.
   Do not rewrite it.
6. **Verify before handing it over.** Run `./verify.sh <file>` from the
   skill directory.

## Updating the templates

`./update.sh` reports upstream drift by reading blob SHAs from the
GitHub API. It needs no local copy of upstream, is read-only, and is
safe to run unattended. Exit 1 means work is pending; exit 2 means the
check itself could not run.

When it reports work:

    ./upstream.sh fetch     # borrow a depth-1 clone at .upstream/
    # convert per references/conversion-rules.md, stamp MANIFEST.json
    ./upstream.sh clean     # give it back

`.upstream/` is git-ignored and must not survive the run.

## Provenance

Templates derive from `anthropics/html-effectiveness` (MIT), pinned per
file in `templates/MANIFEST.json`. All upstream sample data was
fictional and has been removed.
```

- [ ] **Step 2: Confirm the front matter parses**

```bash
python3 -c "
import re
text = open('SKILL.md', encoding='utf-8').read()
m = re.match(r'---\n(.*?)\n---\n', text, re.S)
assert m, 'no front matter block'
body = m.group(1)
assert body.startswith('name: writing-standalone-html'), 'name field wrong'
assert 'description:' in body, 'description field missing'
desc = body.split('description:', 1)[1].strip()
assert len(desc) > 200, f'description too thin at {len(desc)} chars'
assert 'HTML file' not in desc, 'description triggers on format, not genre'
print(f'front matter ok, description {len(desc)} chars')
"
```

- [ ] **Step 3: Confirm every template named in the table exists**

```bash
python3 -c "
import re, pathlib
text = open('SKILL.md', encoding='utf-8').read()
named = set(re.findall(r'\`(\d\d-[a-z0-9-]+\.html)\`', text))
present = {p.name for p in pathlib.Path('templates').glob('*.html')}
missing = named - present
extra = present - named
assert not missing, f'named but absent: {sorted(missing)}'
assert not extra, f'present but unnamed: {sorted(extra)}'
print(f'all {len(named)} templates named and present')
"
```

Expected: `all 20 templates named and present`.

- [ ] **Step 4: Commit**

```bash
git add SKILL.md
git commit -m "feat(skill): add SKILL.md with the genre selection table

Add the entry point. The description enumerates the 20 genres rather
than the phrase 'HTML file', so matching happens on use case and the
skill does not collide with frontend-design or artifact-design.

[Constraint]    Decision 0001 requires a genre-shaped trigger; a
                format-shaped one would fire on every HTML request.
[Rejected]      A short description naming only 'standalone HTML',
                which is exactly the collision 0001 rules out.
[Confidence]    medium
[Scope-risk]    narrow
[Reversibility] clean
[Directive]     Trigger precision can only be judged in real use;
                revisit after the first week.
[Tested]        Front matter parses; every template named in the
                selection table exists and none is unnamed.
[Not-tested]    Whether the trigger actually fires at the right
                moments, which needs live sessions to judge."
```

---

### Task 10: Changelog and first release

**Files:**
- Create: `CHANGELOG.md`

**Interfaces:**
- Consumes: everything.
- Produces: a tagged `v1.0.0`.

- [ ] **Step 1: Run the whole test suite**

`tests/test_conversion_rules.py` reads upstream sources, so it is
bracketed by fetch and clean. Everything else runs without a clone.

```bash
./tests/test_verify.sh && \
./tests/test_upstream.sh && \
python3 tests/test_tokens.py && \
./upstream.sh fetch && python3 tests/test_conversion_rules.py; rc=$?; \
./upstream.sh clean && [ $rc -eq 0 ] && \
./tests/test_update.sh && ./verify.sh
```

Expected: every suite passes and `verify: all 20 file(s) passed`. Do not proceed past a failure — fix it and re-run.

- [ ] **Step 1b: Confirm the tree is clean and no clone survived**

```bash
git status --porcelain
[ -d .upstream ] && echo "FAIL: .upstream survived" || echo "ok: no clone left"
```

Expected: no output from `git status`, and `ok: no clone left`.

- [ ] **Step 2: Write `CHANGELOG.md`**

```markdown
# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-08-14

### Added

- Twenty self-contained HTML templates, one per document genre, derived
  from `anthropics/html-effectiveness` at
  `58c305be97f47b26b678f2c07dec01d4242268ec`.
- Two-tier token system in `references/design-system.css`: a fixed Tier 1
  palette and a Tier 2 semantic layer carrying light and dark themes.
- `references/conversion-rules.md`, the seven-step procedure for turning
  an upstream file into a template.
- `update.sh`, a read-only upstream drift checker that reads blob SHAs
  from the GitHub API and needs no local copy of upstream.
- `upstream.sh`, borrowing an ephemeral `--depth 1` clone into a
  git-ignored `.upstream/` for the duration of an ingest run.
- `verify.sh`, checking that every template parses, holds no external
  reference, and carries no raw hex outside the token block.
- `SKILL.md` with a genre-to-template selection table.
```

- [ ] **Step 3: Commit and tag**

```bash
git add CHANGELOG.md
git commit -m "docs(changelog): add changelog for v1.0.0

[Constraint]    Keep a Changelog format, semver per the user's global
                conventions.
[Confidence]    high
[Scope-risk]    narrow
[Reversibility] clean
[Tested]        Full suite green before tagging."
git tag -a v1.0.0 -m "v1.0.0 — twenty templates, two-tier tokens, drift detection"
```

- [ ] **Step 4: Report the install command**

The skill cannot install itself (decision 0005). Print the command for the user to run:

```bash
echo "mv $(pwd) ~/.claude/skills/"
```

---

## Self-review

**Spec coverage.** Section 1 purpose and scope → Task 9. Section 2 source and licensing → Tasks 4–8 provenance headers, Task 9 provenance section. Section 3 token architecture → Task 2. Section 4.0 genres → Task 9 selection table. Sections 4.1–4.3 conversion → Tasks 3–7. Section 4.4 size estimate → Task 7 Step 5. Section 5 repo layout → all tasks; `README.md` and `AGENTS.md` are written outside this plan. Section 6 update flow → Task 8. Section 7 verification → Task 1, with the manual theme check appearing in every conversion task. Section 8 constraints → Task 10 Step 4 for D5; the restructuring risk and dark-layer cost are ongoing, not implementable. Section 9 decisions → `docs/decisions/`.

**Placeholder scan.** No TBDs. Every code step carries real code. The one deliberately open item is the `#b04a4a` judgment, which Task 3 resolves with a stated default rather than deferring it.

**Type consistency.** `lib/checks.py` exposes `check_parses`, `check_no_external_refs`, `check_no_raw_hex_outside_tokens`, used under those names by `verify.sh` via `CHECKS`. `lib/manifest.py` exposes `load`, `stamp`, `compare`; `update.sh` calls `M.load` and `M.compare`, and `stamp` is reserved for ingest mode, which is agent work rather than a scripted task. `lib/github.py` exposes `head_commit`, `tree_blobs` and `UpstreamUnavailable`, all three used by `update.sh`. Tier 2 role names are identical in Task 2's CSS, Task 3's mapping table, and Task 9's rule 2. The sentinel spelling `/* TOKENS:BEGIN */` matches across `lib/checks.py`, `design-system.css` and `conversion-rules.md`. `.upstream/` is spelled identically in `upstream.sh`, `.gitignore`, every conversion task and `tests/test_upstream.sh`.

**Path independence.** Re-checked after decision 0006: no task references a path outside the skill directory. The only absolute path left in the plan is the install target `~/.claude/skills/` in Task 10.
