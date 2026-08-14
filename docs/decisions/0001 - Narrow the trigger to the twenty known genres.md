# 0001 - Narrow the trigger to the twenty known genres

- Status: accepted
- Date: 2026-08-14
- Supersedes: none

## Context

The skill has to fire on its own, without being named. Two skills already
claim neighbouring ground: `frontend-design` covers app and web UI work,
and `artifact-design` governs anything published as an Artifact. A
trigger phrased around "standalone HTML file" would overlap both, because
that phrase describes a file format rather than a purpose.

## Decision

The skill fires only for the 20 genres it ships templates for: status and
incident reports, implementation plans, PR write-ups, module maps,
feature and concept explainers, flowcharts, slide decks, design systems,
component sheets, animation and interaction prototypes, SVG figure
sheets, code-approach comparisons, and the three mini-editors. The full
table is section 4.0 of the design spec.

`SKILL.md` names those genres explicitly in its description, so matching
happens on use case — "write up this incident", "explain how rate
limiting works here" — and not on the literal words "HTML file". A
request for a standalone HTML page with no genre match does not trigger
the skill.

## Consequences

- No collision with `frontend-design` or `artifact-design`.
- Requests just outside the 20 genres get no template. Accepted: a wrong
  template is worse than none, because it drags the output into a shape
  that does not fit.
- Adding a genre means adding a template. The trigger surface and the
  template set stay the same size by construction.

## Alternatives rejected

**Fire on any standalone HTML request.** Broader reach, but it would
collide with the two existing skills and would apply document-shaped
templates to app UI, where they are wrong.

**Require explicit invocation.** Reliable, but defeats the stated goal:
the templates should appear without being asked for.
