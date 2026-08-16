# 0007 - Carry session context in the tracked files, not a handoff note

- Status: accepted
- Date: 2026-08-16
- Supersedes: none

## Context

Work on this repo happens in agent sessions that do not share memory. For
the build phase, each session wrote `docs/HANDOFF.md`: a git-ignored note
holding where things stood, what to run, and the traps discovered so far.
It carried a banner telling the next reader to delete it after reading.

The note worked while the ten-task plan was the whole of the project,
because "where things stand" was one number — the next unchecked task.
With the plan finished and `v1.0.0` tagged, it stopped being that. It
grew a copy of the invariants, a copy of the test commands, a copy of the
open backlog, and a status section that duplicated `README.md`.

Every one of those copies could disagree with the tracked file it
duplicated, and one did: the note kept a media-query rewrite as the way
to check dark mode after `data-theme` had made it unnecessary.

## Decision

`docs/HANDOFF.md` is deleted and not recreated. What a new session needs
lives in the file that already owns it:

| What | Where |
|---|---|
| What is built, and what one open check remains | `README.md` |
| Invariants, traps, what this environment cannot do | `AGENTS.md` |
| The open backlog and what to pick up next | `TASKS.md` |
| What was built, and what was skipped | the plan's checkboxes |
| Why something is the way it is | `docs/decisions/` |

`TASKS.md` is tracked in git from this decision on. It was git-ignored as
session-local scratch; with the handoff note gone it is the file that
answers "what is the next task", which is project state, not session
state.

## Consequences

- A new session needs no preamble. "Continue with the next task" resolves
  through `README.md` to `TASKS.md`.
- A fact has one home. Correcting it corrects it everywhere, because
  there is nowhere else it is written down.
- Context that turns out to be durable — a trap, an environment limit —
  has to be written into `AGENTS.md` at the time it is learned. There is
  no scratch file to park it in and no banner promising someone will
  clean up later.
- `TASKS.md` changes now show up in review and in history, which is a
  cost: reprioritizing costs a commit. It buys a backlog that survives
  a fresh clone.

## Alternatives rejected

**Keep the handoff note and discipline the duplication.** The banner
already asked readers to delete it and no session did, over the whole
build. A convention that has never once been followed is not a
convention.

**Keep it, but strip it to a pointer file.** A file whose only content is
"read `README.md` and `TASKS.md`" is a redirect, and a redirect that can
go stale is worse than no file.

**Leave `TASKS.md` git-ignored.** It would make the backlog invisible to
anyone cloning the repo, and with the handoff note gone there would be no
tracked answer to "what is next" at all.
