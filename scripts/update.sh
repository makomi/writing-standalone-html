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
cd "$(dirname "$0")/.."

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
    print(f"update: {G.budget_note()}", file=sys.stderr)
    sys.exit(2)

if not upstream:
    print("update: upstream returned no numbered files; refusing to "
          "report 20 removals", file=sys.stderr)
    sys.exit(2)

print(f"update: upstream HEAD is {commit[:7]} ({len(upstream)} files)")
print(f"update: {G.budget_note()}")

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
    print("update: run ./scripts/upstream.sh fetch, convert per "
          "references/conversion-rules.md, then ./scripts/upstream.sh clean")
    sys.exit(1)
print("\nupdate: everything current")
PY
