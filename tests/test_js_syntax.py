"""Every inline script in every template must parse.

The other suites say nothing about JavaScript, so a conversion that
breaks a template's interaction logic passes verification and fails
only when a reader opens the page.

Node is not a dependency of this repo and must not become one. When
`node` is absent the suite skips and says so, the way
test_conversion_rules.py handles a missing clone.
"""

import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

TEMPLATES = pathlib.Path("templates")
SCRIPT = re.compile(r"<script\b([^>]*)>(.*?)</script>", re.S)
TYPE = re.compile(r"""\btype\s*=\s*["']([^"']+)["']""", re.I)
COMMENT = re.compile(r"<!--.*?-->", re.S)

# Anything not executable JavaScript is not ours to parse: a data block,
# an import map, a template held in a script tag.
JS_TYPES = {"", "text/javascript", "application/javascript", "module"}


def is_javascript(attrs):
    m = TYPE.search(attrs)
    return (m.group(1).strip().lower() if m else "") in JS_TYPES


def main(argv):
    node = shutil.which("node")
    if not node:
        print("SKIP: node not found; inline scripts were not parsed")
        return 0

    # An optional directory argument exists so the suite can prove this
    # check fails on a broken script rather than passing vacuously.
    root = pathlib.Path(argv[1]) if len(argv) > 1 else TEMPLATES
    sources = sorted(root.glob("[0-9][0-9]-*.html"))
    if not sources:
        raise SystemExit(f"no templates in {root}/")

    failures = []
    checked = 0
    with tempfile.TemporaryDirectory() as tmp:
        for path in sources:
            # Blank the comments first, as lib/checks.py does: the
            # provenance header in 12-incident-report.html discusses a
            # <script> element the file deliberately does not have.
            # Blanking rather than deleting keeps offsets true.
            text = COMMENT.sub(
                lambda m: re.sub(r"[^\n]", " ", m.group(0)),
                path.read_text(encoding="utf-8"),
            )
            for i, m in enumerate(SCRIPT.finditer(text)):
                attrs, body = m.group(1), m.group(2)
                if not is_javascript(attrs) or not body.strip():
                    continue
                # A module and a classic script differ in what parses.
                module = "module" in (TYPE.search(attrs).group(1).lower()
                                      if TYPE.search(attrs) else "")
                suffix = ".mjs" if module else ".js"
                js = pathlib.Path(tmp) / f"{path.stem}-{i}{suffix}"
                js.write_text(body, encoding="utf-8")
                result = subprocess.run([node, "--check", str(js)],
                                        capture_output=True, text=True)
                checked += 1
                if result.returncode:
                    # node reports against its temp copy, which means
                    # nothing to a reader. Keep the diagnosis, drop the
                    # path, and give the line within the script block.
                    reason = next(
                        (ln.strip() for ln in result.stderr.splitlines()
                         if "Error" in ln),
                        "parse error",
                    )
                    where = next(
                        (ln.rsplit(":", 1)[-1] for ln in result.stderr.splitlines()
                         if ln.startswith(str(js))),
                        "?",
                    )
                    failures.append(
                        f"{path.name} script #{i}, line {where} of the "
                        f"block: {reason}"
                    )

    for problem in failures:
        print(f"FAIL {problem}")
    print(f"{'FAIL' if failures else 'PASS'}: "
          f"{checked - len(failures)}/{checked} inline scripts parse "
          f"across {len(sources)} templates")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
