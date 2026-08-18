#!/usr/bin/env bash
# run-all.sh's own suite: the verdict it gives each suite it runs.
#
# The runner is the line a person reads instead of the output. When it
# called test_update.sh "skipped" -- a suite that runs eleven stub
# assertions and can only skip its final live call -- the summary
# understated coverage, and understating it is how a gap goes unnoticed.
# classify() holds that whole decision, so this suite sources run-all.sh
# for the definitions and calls it directly. The last assertion drives
# the real drift suite into its gap, so the trailer and the verdict are
# checked against each other rather than in isolation.
set -uo pipefail
cd "$(dirname "$0")/.."
fail=0

RUN_ALL_DEFINE_ONLY=yes . ./tests/run-all.sh

expect() {
  local label="$1" want="$2" got="$3"
  if [ "$got" == "$want" ]; then
    echo "ok: $label"
  else
    echo "ASSERT FAIL: $label (wanted '$want', got '$got')"
    fail=1
  fi
}

# 1. The ordinary outcomes.
expect "a clean run is a pass" \
  pass "$(classify 0 'ok: one
ok: two')"
expect "a non-zero exit is a failure" \
  fail "$(classify 1 'ASSERT FAIL: one')"

# 2. A suite that could not run at all is not a pass.
expect "a suite that could not start is a skip" \
  skip "$(classify 0 'SKIP: node not found; inline scripts were not parsed')"

# 3. The distinction this suite exists for. A named gap means the suite
#    ran, and the verdict must not read as if it had not.
expect "a named gap is a gap, not a skip" \
  gap "$(classify 0 'ok: one
ok: two
PARTIAL: the live GitHub check did not run')"

# 4. A suite skips per block, so a partly-skipped suite emits a SKIP
#    line too. The gap wins, or the fix is undone.
expect "a gap outranks a block that skipped" \
  gap "$(classify 0 'SKIP: one block could not run
ok: two
PARTIAL: and the suite says so')"

# 5. Exit status outranks both trailers. A suite that failed has not
#    passed, whatever else it reported on the way.
expect "a failing suite is a failure whatever it printed" \
  fail "$(classify 1 'PARTIAL: a gap
SKIP: and a skip')"

# 6. Both trailers are read at the start of a line, so a suite naming
#    them in prose is still a pass.
expect "SKIP mid-line is not a verdict" \
  pass "$(classify 0 'ok: reports SKIP when node is absent')"
expect "PARTIAL mid-line is not a verdict" \
  pass "$(classify 0 'ok: a PARTIAL run names its gap')"

# 7. End to end. Point the drift suite at a port that refuses, so its
#    live check cannot run and every stub assertion still can. The stub
#    sets GITHUB_API_BASE for each child it launches, so this reaches
#    only the one block that goes to the network.
echo
out=$(GITHUB_API_BASE="http://127.0.0.1:1/repos/nobody/nothing" \
  ./tests/test_update.sh 2>&1)
rc=$?
if printf '%s' "$out" | grep -q "^PARTIAL"; then
  echo "ok: the drift suite names its gap when the network is gone"
else
  echo "ASSERT FAIL: the drift suite did not print a PARTIAL trailer"
  printf '%s\n' "$out" | sed 's/^/      /'
  fail=1
fi
expect "and run-all.sh reads that as a gap, not a skip" \
  gap "$(classify $rc "$out")"

exit $fail
