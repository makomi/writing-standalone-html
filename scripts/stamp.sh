#!/usr/bin/env bash
# Re-stamp the token block into templates from the source of truth.
#
#   ./scripts/stamp.sh              every template
#   ./scripts/stamp.sh <file...>    named templates
#
# The block is embedded verbatim, never linked (invariant 2 in
# AGENTS.md), so editing references/design-system.css means rewriting
# the copy inside every template. Doing that by hand across twenty
# files is how the copies drift.
set -uo pipefail
cd "$(dirname "$0")/.."

files=("$@")
if [ ${#files[@]} -eq 0 ]; then
  shopt -s nullglob
  files=(templates/*.html)
  if [ ${#files[@]} -eq 0 ]; then
    echo "stamp: no templates found in templates/" >&2
    exit 1
  fi
fi

python3 - "${files[@]}" <<'PY'
import pathlib
import re
import sys

BLOCK = re.compile(r"/\* TOKENS:BEGIN.*?/\* TOKENS:END \*/", re.S)

source = pathlib.Path("references/design-system.css").read_text(
    encoding="utf-8").strip()

changed = unchanged = 0
status = 0
for name in sys.argv[1:]:
    path = pathlib.Path(name)
    text = path.read_text(encoding="utf-8")
    if not BLOCK.search(text):
        print(f"FAIL {path}: no token block between the sentinels")
        status = 1
        continue
    stamped = BLOCK.sub(lambda _: source, text, count=1)
    if BLOCK.search(stamped[stamped.index(source) + len(source):]):
        print(f"FAIL {path}: more than one token block")
        status = 1
        continue
    if stamped == text:
        unchanged += 1
        continue
    path.write_text(stamped, encoding="utf-8")
    print(f"stamp: rewrote {path}")
    changed += 1

print(f"stamp: {changed} rewritten, {unchanged} already current")
sys.exit(status)
PY
