# 0006 - Detect drift over the API and clone only on demand

- Status: accepted
- Date: 2026-08-14
- Refines: [0004](0004%20-%20Split%20conversion%20between%20script%20and%20agent.md)

## Context

The first design of `update.sh` shelled into a long-lived local clone of
`anthropics/html-effectiveness` at a fixed path, using it both as the
transport for `git fetch` and as the object store for blob SHAs. That
made a skill whose whole selling point is self-containment depend on a
directory somewhere else on the machine — one that a cleanup of a temp
folder would remove.

The GitHub REST API returns real git blob SHAs, verified against the
local clone: `11-status-report.html` reads
`764665143d3731ccb5e8978898bf7d7a5e46cc5f` from both. A single
`git/trees` call returns all 20 files untruncated.

## Decision

Split the two needs, because they are not the same need.

**Detection needs SHAs, not content.** `update.sh` calls the GitHub API
and compares the returned blob SHAs against `templates/MANIFEST.json`.
No clone, no working directory, no dependency outside the skill folder.

**Conversion needs content.** When `update.sh` reports work, ingest mode
clones into `.upstream/` inside the skill folder, converts, and deletes
it. `.upstream/` is git-ignored. `./upstream.sh fetch` creates it,
`./upstream.sh clean` removes it, and the test suite fails if it is
still present, so a stale clone cannot be committed.

## Consequences

- The skill depends on no path outside its own directory. It can be
  moved, copied or reinstalled without breaking drift detection.
- Detection costs two API calls per run against an unauthenticated limit
  of 60 per hour. Ample for a daily or hourly check; not for a tight
  polling loop.
- Detection now needs network access, where a local clone could be
  diffed offline. Accepted: the clone had to be fetched over the network
  to be current anyway, so offline detection was only ever reporting
  stale results confidently.
- The clone is created and destroyed per ingest run, so it is always at
  upstream HEAD. The class of bug where a stale local clone silently
  yields stale blob SHAs disappears.
- `--depth 1` keeps the clone at roughly 860 KB and seconds to create.
- Two failure modes replace one: the API can rate-limit or be
  unreachable. Both exit 2, distinct from exit 1 meaning "drift found",
  so a wrapper can tell a broken checker from pending work.

## Alternatives rejected

**Keep the long-lived local clone.** Simple and offline-capable, but
makes the skill depend on a second directory whose lifetime nobody
manages. Discovered when the natural build location turned out to be a
folder named `0_TEMP`.

**Auto-clone the long-lived path when missing.** Fixes the failure but
keeps a permanent second copy of upstream on disk for something used a
few times a year, and leaves the stale-clone bug intact.

**Clone for detection too, every run.** Correct but wasteful: fetching
860 KB to compare 20 hashes, when the hashes are one API call away.
