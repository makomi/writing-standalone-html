#!/usr/bin/env bash
# update.sh must be read-only and must classify drift correctly.
#
# Every classification assertion runs against tests/stub_github.py, so
# the suite costs one live GitHub call rather than eleven. The old shape
# spent about eleven of the 60 an unauthenticated hour allows, so six
# suite runs emptied the budget and this suite then skipped in full --
# a green run with drift detection never exercised.
#
# The live call stays because a stub cannot tell you that github.com
# still answers in the shape lib/github.py reads. It is the last block,
# and only it skips when the network is gone. That case prints PARTIAL,
# not SKIP: the suite ran, and run-all.sh reports the named gap rather
# than calling eleven assertions skipped.
set -uo pipefail
cd "$(dirname "$0")/.."
fail=0
live_calls=0

# Assertion 5 clears .upstream/ to prove detection needs no clone. A
# session mid-conversion still needs the clone it fetched, so it is
# moved aside and put back however this exits.
STASH=".upstream.testbak"
restore() {
  if [ -d "$STASH" ]; then
    rm -rf .upstream
    mv "$STASH" .upstream
    echo "note: restored the clone this test borrowed"
  fi
}
trap restore EXIT
rm -rf "$STASH"
[ -d .upstream ] && mv .upstream "$STASH"

# stub <mode> -- run update.sh against canned responses, echo its exit.
stub() {
  local mode="$1"
  python3 tests/stub_github.py "$mode" -- ./scripts/update.sh >/dev/null 2>&1
  echo $?
}

expect_exit() {
  local label="$1" want="$2" got="$3"
  if [ "$got" -eq "$want" ]; then
    echo "ok: $label"
  else
    echo "ASSERT FAIL: $label (wanted exit $want, got $got)"
    fail=1
  fi
}

# 1. A clean tree must stay clean after a run.
before=$(git status --porcelain | sort)
python3 tests/stub_github.py current -- ./scripts/update.sh >/dev/null 2>&1
after=$(git status --porcelain | sort)
if [ "$before" == "$after" ]; then
  echo "ok: update.sh does not write to the working tree"
else
  echo "ASSERT FAIL: update.sh modified the working tree"
  diff <(echo "$before") <(echo "$after")
  fail=1
fi

# 2. A tree matching the manifest must read as 20 unchanged, exit 0.
out=$(python3 tests/stub_github.py current -- ./scripts/update.sh 2>&1)
rc=$?
expect_exit "a matching tree exits 0" 0 "$rc"
if printf '%s' "$out" | grep -q "unchanged: 20"; then
  echo "ok: all 20 files unchanged against the manifest"
else
  echo "ASSERT FAIL: expected 20 unchanged files"
  printf '%s\n' "$out"
  fail=1
fi

# 3. A changed blob SHA must be reported as changed, exit 1. The stub
#    moves the SHA upstream, so the real MANIFEST.json is never edited
#    and a killed run cannot leave it corrupt.
out=$(python3 tests/stub_github.py drifted -- ./scripts/update.sh 2>&1)
expect_exit "a changed blob exits 1" 1 $?
if printf '%s' "$out" | grep -q "^changed: 1"; then
  echo "ok: a changed blob lands in the changed bucket"
else
  echo "ASSERT FAIL: a changed blob was not reported as changed"
  fail=1
fi

# 4. A file upstream has and the manifest does not must show as new.
#    This is what enumerating upstream rather than the manifest buys.
out=$(python3 tests/stub_github.py added -- ./scripts/update.sh 2>&1)
expect_exit "an added file exits 1" 1 $?
if printf '%s' "$out" | grep -q "^new: 1"; then
  echo "ok: a file only upstream lands in the new bucket"
else
  echo "ASSERT FAIL: an added upstream file was not reported as new"
  fail=1
fi

# 5. An empty tree must exit 2, not report 20 removals.
expect_exit "an empty tree exits 2" 2 "$(stub empty)"

# 6. A truncated tree must exit 2 rather than invent removals from a
#    partial answer.
expect_exit "a truncated tree exits 2" 2 "$(stub truncated)"

# 7. An unreachable endpoint must exit 2, not 1. Exit 1 means "drift
#    found"; a wrapper must never read an outage as pending work. Port 1
#    on loopback refuses instantly and costs no budget, where the old
#    404-against-github.com probe spent a call to learn the same thing.
GITHUB_API_BASE="http://127.0.0.1:1/repos/nobody/nothing" \
  ./scripts/update.sh >/dev/null 2>&1
expect_exit "an unreachable endpoint exits 2" 2 $?

# 8. Detection must not need a clone. Exit 0 means the check ran.
./scripts/upstream.sh clean >/dev/null 2>&1
expect_exit "detection runs with no local clone" 0 "$(stub current)"

# 9. The live integration check. A stub proves the classification; only
#    github.com proves the response still has the shape lib/github.py
#    reads. One call site, two API calls, and the run says what it spent.
echo
live=$(./scripts/update.sh 2>&1)
rc=$?
if [ $rc -eq 2 ]; then
  echo "PARTIAL: the live GitHub check did not run, so the response"
  echo "         shape was not verified. Every stub assertion above ran"
  echo "         and its result stands. update.sh said:"
  printf '%s\n' "$live" | sed 's/^/         /'
else
  live_calls=2
  if printf '%s' "$live" | grep -q "spent 2 API call(s)"; then
    echo "ok: the live check spends 2 API calls, not one per assertion"
  else
    echo "ASSERT FAIL: the live check did not report a 2-call spend"
    printf '%s\n' "$live"
    fail=1
  fi
  printf '%s\n' "$live" | grep -o "spent .*left this hour" |
    sed 's/^/note: /'
fi

echo "note: this suite spent $live_calls live GitHub API call(s) of the 60 an hour"
exit $fail
