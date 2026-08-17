# 0003 - Adopt a two-tier token architecture and maintain dark mode

- Status: accepted
- Date: 2026-08-14
- Supersedes: none

## Context

Upstream is light-mode only: zero of the 21 files contain
`prefers-color-scheme`. We want dark mode.

All 20 files already draw from one palette — ivory `#FAF9F5`, slate
`#141413`, clay `#D97757`, oat `#E3DACC`, olive `#788C5D`, rust
`#B04A3F`, a gray ramp and white. But every file names its custom
properties **by color**, and the names drift between files for identical
values: `#3D3D3A` is `--gray-700` in some files and `--gray-800` in
others; `#F0EEE6` appears as `--gray-150`, `--gray-50` and `--gray-100`.

A color-named token cannot flip meaning between themes. `--ivory` is
`#FAF9F5` — that is what the name promises. A dark-mode background
called `--ivory` reads as a bug.

## Decision

Split the token set in two.

- **Tier 1, raw palette.** Fixed values, color-named, never swapped:
  `--clay: #D97757`, `--ivory: #FAF9F5`, and the rest.
- **Tier 2, semantic roles.** Function-named and theme-swappable:
  `--bg`, `--surface`, `--text`, `--text-muted`, `--border`, `--accent`,
  `--ok`, `--warn`, `--danger`. Only Tier 2 is redefined for dark.

Templates reference Tier 2 for anything that must adapt. Tier 1 stays
available for deliberately theme-invariant decoration.

The canonical definition lives in `references/design-system.css` and is
**embedded verbatim** in each template. Linking it would break
self-containment, which is the property that makes these files worth
having.

## Consequences

- Dark mode costs one edit to the shared token block instead of one edit
  per template.
- Conversion becomes strip-content **and** re-tokenize. This is the bulk
  of the implementation effort, not a side task.
- The 253 hex literals sitting outside `:root` upstream must each be
  mapped to the role they play. This cannot be done by matching on the
  hex value alone: `#3D3D3A` is body text in one place and a border in
  another, and the correct token depends on the job, not the value.
  They draw from 49 distinct values, of which only 14 recur often
  enough to deserve a table row.
- `10-svg-illustrations.html` carries 97 of those literals in SVG `fill`
  attributes, outside the CSS cascade. It is the most expensive file to
  convert, followed by `16-implementation-plan.html` at 36.
- Naming drift is resolved once, on our side, rather than inherited.
- Every future upstream change touching color needs a dark-mode judgment
  call, indefinitely. Upstream will not make it for us.

**Note added 2026-08-14, during implementation.** Upstream's clay
reaches only 2.96:1 on ivory and its olive 3.49:1, short of the 4.5:1
these roles need as text. `--accent` and `--ok` therefore resolve to new
`--clay-deep` and `--olive-deep` variants; Tier 1 keeps upstream's
values untouched. Upstream reached the same conclusion independently,
defining `--clay-d: #b85c3e` in three files.

**Note added 2026-08-17.** That first pass measured the two variants
against `--bg` alone, where they cleared 4.51:1 and 4.55:1, and missed
that `--surface-sunken` is darker still: 4.09:1 and 4.13:1 there, on a
ground two shipped templates put accent text on. The variants were
retuned and `tests/test_tokens.py` gained the sunken pairings. The
architecture is unchanged — this is what invariant 4 anticipates, a
contrast defect repaired in a variant this project owns rather than in
upstream's palette. The rule that follows: measure a light-theme text
role against the darkest light ground, not against the page.

## Alternatives rejected

**Stay faithful to upstream's color-named tokens, no dark mode.** Cheaper
to build and updates stay clean merges, but gives up dark mode
permanently — and a light-only page inherits the host background when
published as an Artifact unless it paints its own.

**Keep color names and add a parallel dark palette.** Would require
tokens like `--ivory-dark`, leaving every template to branch on theme at
each use site. More code, more drift, same outcome.
