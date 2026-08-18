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
gapped=()
started=$(date +%s)

# classify <rc> <output> -- the verdict for one suite, echoed as
# fail | gap | skip | pass.
#
# A suite reports what it could not do, because only the suite knows.
# Two trailers say it, and they mean different things:
#
#   SKIP     nothing ran. No node, no network. Not a pass -- saying
#            "pass" would hide the whole suite.
#   PARTIAL  the suite ran and names a gap. Its other assertions hold.
#
# PARTIAL is checked first, and that order is the point of the
# distinction. A suite prints SKIP from whichever block could not run,
# so a suite with one skipped block among ten that ran emits a SKIP
# line; reading that as "skipped" understates the coverage a person
# then trusts. A suite that names a gap ran.
classify() {
  local rc="$1" out="$2"
  if [ "$rc" -ne 0 ]; then
    echo fail
  elif printf '%s' "$out" | grep -q "^PARTIAL"; then
    echo gap
  elif printf '%s' "$out" | grep -q "^SKIP"; then
    echo skip
  else
    echo pass
  fi
}

run() {
  local label="$1"; shift
  echo
  echo "=== $label"
  local out rc
  out=$("$@" 2>&1); rc=$?
  printf '%s\n' "$out"
  case "$(classify "$rc" "$out")" in
    fail) echo "--- $label: FAIL";              failed+=("$label") ;;
    gap)  echo "--- $label: pass, with a gap";  gapped+=("$label") ;;
    skip) echo "--- $label: skipped";           skipped+=("$label") ;;
    *)    echo "--- $label: pass" ;;
  esac
}

# tests/test_run_all.sh sources this file to call classify() on its own.
# Everything above is a definition; everything below runs a suite.
[ "${RUN_ALL_DEFINE_ONLY:-no}" = yes ] && return 0

run "checker fixtures"        ./tests/test_verify.sh
run "token roles and contrast" python3 tests/test_tokens.py
run "inline script syntax"    python3 tests/test_js_syntax.py
run "contrast audit rules"    python3 tests/test_audit_contrast.py
run "upstream borrow"         ./tests/test_upstream.sh
run "the runner's verdicts"   ./tests/test_run_all.sh

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
if [ ${#gapped[@]} -gt 0 ]; then
  note=", ${#gapped[@]} with a named gap: ${gapped[*]}"
fi
if [ ${#skipped[@]} -gt 0 ]; then
  note="$note, ${#skipped[@]} skipped: ${skipped[*]}"
fi
if [ ${#failed[@]} -eq 0 ]; then
  echo "run-all: every suite passed in ${elapsed}s${note}"
  exit 0
fi
echo "run-all: ${#failed[@]} suite(s) failed in ${elapsed}s${note}"
printf '  %s\n' "${failed[@]}"
exit 1
