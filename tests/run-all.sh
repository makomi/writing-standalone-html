#!/usr/bin/env bash
# Run every suite in one command, in the one order that is correct.
#
# Two ordering constraints, neither of them obvious from the file names:
#
#   test_upstream.sh deletes .upstream/ as a side effect, so it runs
#   before test_conversion_rules.py, which needs a clone, and before
#   test_update.sh, which asserts detection works without one.
#
#   test_conversion_rules.py is the only suite needing the clone, so it
#   is bracketed by fetch and clean and the clone never outlives it.
#
# Exits 0 only when every suite passed. A failure is reported and the
# run continues, so one command shows every problem rather than the
# first.
set -uo pipefail
cd "$(dirname "$0")/.."

failed=()
started=$(date +%s)

run() {
  local label="$1"; shift
  echo
  echo "=== $label"
  if "$@"; then
    echo "--- $label: pass"
  else
    echo "--- $label: FAIL"
    failed+=("$label")
  fi
}

run "checker fixtures"        ./tests/test_verify.sh
run "token roles and contrast" python3 tests/test_tokens.py
run "inline script syntax"    python3 tests/test_js_syntax.py
run "upstream borrow"         ./tests/test_upstream.sh

echo
echo "=== conversion rules (needs the clone)"
if ./scripts/upstream.sh fetch >/dev/null; then
  python3 tests/test_conversion_rules.py
  rc=$?
  ./scripts/upstream.sh clean >/dev/null
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
if [ -d .upstream ]; then
  echo "FAIL: .upstream survived the run"
  failed+=(".upstream cleanup")
fi

elapsed=$(( $(date +%s) - started ))
if [ ${#failed[@]} -eq 0 ]; then
  echo "run-all: every suite passed in ${elapsed}s"
  exit 0
fi
echo "run-all: ${#failed[@]} suite(s) failed in ${elapsed}s"
printf '  %s\n' "${failed[@]}"
exit 1
