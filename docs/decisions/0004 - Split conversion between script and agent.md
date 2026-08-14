# 0004 - Split conversion between script and agent

- Status: accepted
- Date: 2026-08-14
- Supersedes: none

## Context

The skill needs to track an upstream repo that will keep changing:
detect updates, re-convert changed files, and pick up newly added ones.
The obvious wish is a single script that does all of it unattended.

Conversion, however, requires judgment at three points: which sibling
instance is representative, where a repeat boundary falls, and which
semantic role a given hex literal plays
(see [0003](0003%20-%20Adopt%20a%20two-tier%20token%20architecture%20and%20maintain%20dark%20mode.md)).
None of these is decidable from the markup alone, and regex-stripping
hand-written HTML mangles it reliably.

## Decision

Split the pipeline where determinism ends.

- **`update.sh` — bookkeeping.** Fetches upstream, enumerates every
  `NN-*.html` at HEAD, diffs blob SHAs against `templates/MANIFEST.json`,
  and prints four lists: unchanged, changed, new, removed. Exits non-zero
  when work is pending.
- **Ingest mode — semantics.** The skill converts the files `update.sh`
  named, following the written procedure in
  `references/conversion-rules.md`, then stamps the manifest.

`update.sh` is strictly read-only. It never edits a template and never
writes `MANIFEST.json`, including the `checked_at` field.

## Consequences

- The detection half is deterministic, needs no model, and is safe to run
  from cron.
- A cron run cannot dirty the git tree, because the read path performs no
  writes. This is why `checked_at` is stamped by ingest mode instead.
- Conversion stays reproducible across sessions only to the extent that
  `conversion-rules.md` is precise. That file is load-bearing, not
  documentation.
- Updates are never fully unattended. Accepted: the alternative is silent
  corruption of templates.
- Files removed upstream are flagged, never auto-deleted.

## Alternatives rejected

**One fully automatic script.** A regex or DOM pass could strip repeated
siblings, but choosing the representative instance and assigning semantic
roles are judgment calls. The failure mode is a template that still looks
plausible while teaching the wrong pattern.

**Fully manual updates.** No script at all. Rejected because detecting
drift across 20 files by eye is exactly the mechanical work worth
automating, and it is the part that gets skipped when done by hand.
