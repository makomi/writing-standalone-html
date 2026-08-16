#!/usr/bin/env bash
# update.sh must be read-only and must classify drift correctly.
set -uo pipefail
cd "$(dirname "$0")/.."
fail=0

backup=$(mktemp)
trap 'rm -f "$backup"' EXIT

# 1. A clean tree must stay clean after a run.
before=$(git status --porcelain | sort)
./scripts/update.sh >/dev/null 2>&1
after=$(git status --porcelain | sort)
if [ "$before" == "$after" ]; then
  echo "ok: update.sh does not write to the working tree"
else
  echo "ASSERT FAIL: update.sh modified the working tree"
  diff <(echo "$before") <(echo "$after")
  fail=1
fi

# 2. Against the pinned commit, everything must read as unchanged.
if ./scripts/update.sh 2>&1 | grep -q "unchanged: 20"; then
  echo "ok: all 20 files unchanged at the pinned commit"
else
  echo "ASSERT FAIL: expected 20 unchanged files"
  fail=1
fi

# 3. A tampered manifest SHA must be reported as changed, exit 1.
cp templates/MANIFEST.json "$backup"
python3 - <<'PY'
import json
m = json.load(open("templates/MANIFEST.json"))
m["files"][0]["upstream_blob_sha"] = "0" * 40
json.dump(m, open("templates/MANIFEST.json", "w"), indent=2)
PY
./scripts/update.sh >/dev/null 2>&1
if [ $? -eq 1 ]; then
  echo "ok: pending work exits non-zero"
else
  echo "ASSERT FAIL: tampered manifest did not exit 1"
  fail=1
fi
cp "$backup" templates/MANIFEST.json

# 4. A broken API endpoint must exit 2, not 1. Exit 1 means "drift
#    found"; a wrapper must never read an outage as pending work.
if GITHUB_API_BASE="https://api.github.com/repos/anthropics/does-not-exist-$$" \
     ./scripts/update.sh >/dev/null 2>&1; then
  echo "ASSERT FAIL: unreachable endpoint should not exit 0"
  fail=1
elif [ $? -eq 2 ]; then
  echo "ok: a broken check exits 2, distinct from drift"
else
  echo "ASSERT FAIL: unreachable endpoint did not exit 2"
  fail=1
fi

# 5. Detection must not need a clone. Exit 0 or 1 means the check ran;
#    2 means it could not, and anything else means it never started.
./scripts/upstream.sh clean >/dev/null 2>&1
./scripts/update.sh >/dev/null 2>&1
rc=$?
if [ $rc -eq 0 ] || [ $rc -eq 1 ]; then
  echo "ok: detection runs with no local clone"
else
  echo "ASSERT FAIL: update.sh needs a clone it should not need (exit $rc)"
  fail=1
fi

exit $fail
