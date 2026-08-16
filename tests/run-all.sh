#!/usr/bin/env bash
# Run every suite in one command.
#
# test_conversion_rules.py is the only suite needing upstream file
# contents, so it is bracketed by fetch and clean here and the clone
# never outlives it. Every other suite runs without one: test_upstream.sh
# borrows and restores whatever it finds, and test_update.sh clears the
# path itself before asserting that detection needs no clone.
#
# Exits 0 only when every suite passed. A failure is reported and the
# run continues, so one command shows every problem rather than the
# first.
set -uo pipefail
cd "$(dirname "$0")/.."

failed=()
skipped=()
started=$(date +%s)

# A suite that could not run reports SKIP and exits 0 -- no node, no
# network. That is not a pass, and saying "pass" would hide the gap, so
# it is counted and named separately.
run() {
  local label="$1"; shift
  echo
  echo "=== $label"
  local out rc
  out=$("$@" 2>&1); rc=$?
  printf '%s\n' "$out"
  if [ $rc -ne 0 ]; then
    echo "--- $label: FAIL"
    failed+=("$label")
  elif printf '%s' "$out" | grep -q "^SKIP"; then
    echo "--- $label: skipped"
    skipped+=("$label")
  else
    echo "--- $label: pass"
  fi
}

run "checker fixtures"        ./tests/test_verify.sh
run "token roles and contrast" python3 tests/test_tokens.py
run "inline script syntax"    python3 tests/test_js_syntax.py
run "upstream borrow"         ./tests/test_upstream.sh

echo
echo "=== conversion rules (needs the clone)"
# Leave the working directory as it was found. A session mid-conversion
# has a clone it still needs; only a clone this run created gets removed.
inherited=no
[ -d .upstream ] && inherited=yes
if ./scripts/upstream.sh fetch >/dev/null; then
  python3 tests/test_conversion_rules.py
  rc=$?
  if [ "$inherited" = no ]; then
    ./scripts/upstream.sh clean >/dev/null
  else
    echo "note: left the clone in place, it was here first"
  fi
  if [ $rc -eq 0 ]; then
    echo "--- conversion rules: pass"
  else
    echo "--- conversion rules: FAIL"
    failed+=("conversion rules")
  fi
else
  echo "--- conversion rules: FAIL (could not fetch the clone)"
  failed+=("conversion rules")
fi

run "drift detection"         ./tests/test_update.sh
run "every template"          ./scripts/verify.sh

echo
if [ -d .upstream ] && [ "$inherited" = no ]; then
  echo "FAIL: .upstream survived the run"
  failed+=(".upstream cleanup")
fi

elapsed=$(( $(date +%s) - started ))
note=""
if [ ${#skipped[@]} -gt 0 ]; then
  note=", ${#skipped[@]} skipped: ${skipped[*]}"
fi
if [ ${#failed[@]} -eq 0 ]; then
  echo "run-all: every suite passed in ${elapsed}s${note}"
  exit 0
fi
echo "run-all: ${#failed[@]} suite(s) failed in ${elapsed}s${note}"
printf '  %s\n' "${failed[@]}"
exit 1
