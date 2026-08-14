# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing is released yet. `v1.0.0` requires all twenty templates plus
`SKILL.md`; see `docs/plans/2026-08-14-writing-standalone-html.md`.

### Added

- `references/design-system.css` — two-tier token system. Tier 1 is
  upstream's fixed palette plus the variants this project adds; Tier 2
  is the semantic layer and the only tier redefined for dark mode.
  Theme-invariant code-block roles cover the dark syntax palette
  several upstream files use.
- `references/conversion-rules.md` — the seven-step procedure for
  turning an upstream file into a template, with a mapping table for
  the 14 systematic colors and an ordered fallback for the 35 one-offs.
- `scripts/verify.sh` and `lib/checks.py` — three mechanical checks:
  the file parses, holds no external reference, and carries no raw hex
  outside the sentinel token block.
- `scripts/upstream.sh` — borrows a `--depth 1` clone into a
  git-ignored `.upstream/` and deletes it again, so the skill depends
  on no path outside its own directory.
- Four test suites: `tests/test_verify.sh`, `tests/test_upstream.sh`,
  `tests/test_tokens.py` (22 contrast pairings across both themes),
  `tests/test_conversion_rules.py`.
- Design record: spec, six decision records, ten-task implementation
  plan.

### Fixed

- The raw-hex check scanned whole files, counting anything hex-shaped
  in element text. `11-status-report.html` renders pull-request numbers
  as link text (`<a>#4871</a>`), so the check would have failed that
  template permanently. It now scans `<style>` blocks and
  color-bearing attributes only.

### Changed

- Per-file color counts corrected throughout the spec, decision `0003`
  and the plan. The originals came from a bare regex whose `:root`
  stripping swallowed most of the stylesheet in
  `16-implementation-plan.html`, reporting 0 colors where there are 36.
  Three files are color-free, not six; the total is 253, not ~270.
