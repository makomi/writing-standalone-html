# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This file records what changes for someone who has installed the skill.
Internal work — tests, refactors, tooling fixes, corrections to our own
measurements — lives in commit bodies. See the changelog rules in
`AGENTS.md`.

## [Unreleased]

### Added

- `LICENSE`. The twenty templates derive from
  `anthropics/html-effectiveness` at
  `58c305be97f47b26b678f2c07dec01d4242268ec`, and MIT requires that
  notice to travel with them. The tooling in this repo is MIT under its
  own copyright. The file carries both, over the upstream licence text
  unchanged.

### Changed

- `scripts/verify.sh` also fails a template whose script writes a raw
  colour into CSS through `style`, `cssText`, `setProperty` or
  `setAttribute`. A colour set that way pins itself to one theme.

### Fixed

- `scripts/audit-contrast.js` measures a text node against the ground
  it is painted on, not against any ancestor that happens to paint one.
  A label positioned clear of its parent was reported against a fill it
  never touches; six such phantom failures came out of
  `07-prototype-animation.html`. Text that crosses a ground's edge is
  still reported, marked `"straddles": true`.
- Accent and success text is legible on a sunken panel in light theme.
  `--accent` and `--ok` reached only 4.09:1 and 4.13:1 on
  `--surface-sunken`, short of the 4.5:1 that text needs; the two
  tokens behind them are darker, and both pairings now clear it. The
  slot chips in `20-editor-prompt-tuner.html` and the addition count in
  `17-pr-writeup.html` are the places a reader sees this.
- The design previews in `02-exploration-visual-designs.html` keep the
  ground the page's own `Background: Light / Dark` control selects. In
  dark theme the light preview had taken the page's dark ground while
  its text stayed dark, which hid both empty-state headings.

## [1.0.0] - 2026-08-16

### Added

- Twenty self-contained HTML templates, one per document genre, derived
  from `anthropics/html-effectiveness` at
  `58c305be97f47b26b678f2c07dec01d4242268ec`.
- `SKILL.md` with a genre-to-template selection table, so the skill
  triggers on the genre being written rather than on the file format.
- Light and dark themes in every template, following the reader's system
  setting. A page pins one theme with `data-theme` on the root element.
- `scripts/verify.sh`, checking that a template parses, holds no
  external reference, embeds the token block unedited, carries no raw
  colour outside it, and keeps no upstream brand name.
- `scripts/update.sh`, a read-only upstream drift checker that needs no
  local copy of upstream.
- `scripts/upstream.sh`, borrowing an ephemeral clone for the duration
  of an ingest run.
