#!/usr/bin/env bash
# upstream.sh must be idempotent, and .upstream/ must never be tracked.
#
# The assertions have to run against the real .upstream/ path, because
# one of them is that git ignores exactly that path. So a clone the
# session is already using is moved aside first and put back afterwards,
# however this exits. Without that, running the suite mid-task deletes
# the clone the task was converting from.
set -uo pipefail
cd "$(dirname "$0")/.."
fail=0

STASH=".upstream.testbak"
restore() {
  rm -rf .upstream
  if [ -d "$STASH" ]; then
    mv "$STASH" .upstream
    echo "note: restored the clone this test borrowed"
  fi
}
trap restore EXIT

rm -rf "$STASH"
[ -d .upstream ] && mv .upstream "$STASH"

./scripts/upstream.sh clean >/dev/null 2>&1

./scripts/upstream.sh fetch >/dev/null 2>&1
if [ -d .upstream/.git ]; then echo "ok: fetch creates the clone"
else echo "ASSERT FAIL: fetch did not create .upstream"; fail=1; fi

# Fetching twice must not fail or re-clone.
# Capture rather than pipe: grep -q short-circuits, SIGPIPEs the
# writer, and pipefail would then report the pipeline as failed.
second=$(./scripts/upstream.sh fetch 2>&1)
if printf '%s' "$second" | grep -q "reusing"; then
  echo "ok: fetch is idempotent"
else
  echo "ASSERT FAIL: second fetch did not reuse the clone"; fail=1
fi

# The clone must be invisible to git.
if [ -z "$(git status --porcelain | grep '\.upstream')" ]; then
  echo "ok: .upstream is git-ignored"
else
  echo "ASSERT FAIL: .upstream shows up in git status"; fail=1
fi

./scripts/upstream.sh clean >/dev/null 2>&1
if [ ! -d .upstream ]; then echo "ok: clean removes the clone"
else echo "ASSERT FAIL: clean left .upstream behind"; fail=1; fi

# Cleaning twice must not fail.
if ./scripts/upstream.sh clean >/dev/null 2>&1; then
  echo "ok: clean is idempotent"
else
  echo "ASSERT FAIL: second clean exited non-zero"; fail=1
fi

exit $fail
