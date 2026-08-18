# 0008 - Keep machine-local browser commands out of the repo

- Status: accepted
- Date: 2026-08-18
- Supersedes: none

## Context

Two checks cannot be made by `scripts/verify.sh`, because both need a
rendered page: whether a template holds up in dark theme, and whether its
retained interaction still works. `AGENTS.md` documented both.

It documented them in terms of `browse-once`, a binary that exists at
`~/.claude/bin/browse-once/browse-once` on one machine, with gstack
behind it. The section named the binary eight times and gstack four
more, and `scripts/audit-contrast.js` pointed a reader at the section
for the invocation. Every command in it was a command a reader of a
published clone cannot run.

Decision 0007 put traps and environment limits in `AGENTS.md` and
rejected a git-ignored note that duplicated tracked files. That settles
where durable knowledge goes. It does not settle what to do with
knowledge that is true of one machine and false everywhere else, which
is what these commands are.

## Decision

`AGENTS.md` states what the step needs, never how to invoke it. The
section names five capabilities — load a `file://` URL, set the
viewport, evaluate JavaScript and return the result, capture a
screenshot, send a key press — and everything downstream of it is
written against those, not against a command line.

The concrete commands live in `.claude/browsing.md`, which `.gitignore`
already excludes. A machine has one or it does not.

The split is by portability, not by subject:

| Kind of fact | Where it lives |
|---|---|
| True of the page or the repo | `AGENTS.md` |
| True of any driver in this sandbox | `AGENTS.md` |
| True of one driver on one machine | `.claude/browsing.md` |

In order: that `09-slide-deck.html` is a scroll-snap deck `window.scrollTo`
will not move; that `/tmp` is refused and a bare `chromium --headless` is
denied `socket()`; that `browse-once` chains steps with a literal `--`.

That is why the `/tmp` and chromium limits moved up into "What this
environment cannot do" instead of leaving the repo with the tool: they
constrain whatever driver a reader brings.

## Consequences

- The repo can be published without instructing anyone to run a binary
  they do not have.
- A fresh clone can still perform both checks, because it is told what
  the checks require. It has to supply its own driver first, and it is
  told that too.
- `.claude/browsing.md` is not a handoff note and does not reopen what
  0007 closed. It duplicates no tracked file: the commands it holds
  appear nowhere in the repo, by construction.
- The cost is a real one and lands on the public reader. They get a
  step they must still solve themselves — no other shape avoided that
  without also removing the knowledge that the step exists.
- This record names `browse-once` and is tracked, which is deliberate: a
  decision record has to say what it rejected. A grep hit here is
  history, not an instruction to run anything.
- Anything learned about the local driver now has a home that is not
  `AGENTS.md`. Anything learned about a template still belongs in
  `AGENTS.md`, and the table above is the test for which it is.

## Alternatives rejected

**Move the whole browsing section into `.claude/`.** Simplest, and it
makes the leak impossible by construction. It also deletes from the repo
the only record that two checks exist outside `verify.sh`, along with
the ground rule, the `data-theme` recipe and the false alarms in `09`
and `13` that took a sweep to learn. A clone would ship twenty templates
with no way to know how they were checked.

**Move it into the global `CLAUDE.md`.** Same loss, and worse placement:
knowledge about `07`'s absolutely positioned beat labels is not
machine-wide, and putting it in a machine-wide file means it applies to
every repo and belongs to none.

**Keep it as it was and rely on remembering before the push.** The
trigger is publication, which is a single moment nobody is guaranteed to
be watching. A leak that is silent at exactly the moment it matters is
not managed by intending to catch it.
