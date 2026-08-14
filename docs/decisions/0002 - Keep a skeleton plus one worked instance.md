# 0002 - Keep a skeleton plus one worked instance

- Status: accepted
- Date: 2026-08-14
- Supersedes: none

## Context

Upstream files are finished pages carrying fictional "Acme" data — 11,611
lines across 21 files, with individual files running to 722 lines. Read
whole, they burn context and invite the fictional data to leak into real
output. Emptied completely, they lose the thing that makes them worth
keeping.

`18-editor-triage-board.html` is the clearest case: thirty fictional
tickets, all instances of one row pattern.

## Decision

Strip content down to a skeleton, but keep one worked instance of every
repeating pattern, marked with a comment such as `<!-- repeat per
ticket -->`. The triage board keeps one ticket and drops twenty-nine.

Genre-specific CSS and JavaScript stay intact and unabridged.

## Consequences

- The pattern survives at roughly a tenth of the content volume. One
  retained row costs about ten lines and removes all guesswork about
  structure.
- Interactive logic keeps working as written. Slide-deck keyboard
  navigation, triage drag-and-drop, tab switching and the prompt tuner's
  live re-render are expensive to re-derive and easy to get subtly wrong
  from a description.
- Templates are not directly usable as finished pages. They are inputs to
  generation, and the retained instance must be replaced, not shipped.
- Every conversion needs a judgment call about which instance is
  representative. See [0004](0004%20-%20Split%20conversion%20between%20script%20and%20agent.md).

## Alternatives rejected

**Fully blank shell.** Smallest output, but the row structure would then
be reconstructed by guesswork on every use — re-deriving exactly what the
template was supposed to record.

**Keep the examples whole.** Zero conversion work and zero drift from
upstream, but every use pays for ~11,600 lines of fictional data, and the
Acme content sits one copy-paste away from real output.
