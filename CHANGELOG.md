# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This file records what changes for someone who has installed the skill.
Internal work — tests, refactors, tooling fixes, corrections to our own
measurements — lives in commit bodies. See the changelog rules in
`AGENTS.md`.

## [1.0.0] - 2026-08-19

### Added

- Twenty self-contained HTML templates, one per document genre, derived
  from `anthropics/html-effectiveness` at
  `58c305be97f47b26b678f2c07dec01d4242268ec`.
- `SKILL.md` with a genre-to-template selection table, so the skill
  triggers on the genre being written rather than on the file format.
- Light and dark themes in every template, following the reader's system
  setting. A page pins one theme with `data-theme` on the root element.
  Every text node the contrast audit reports clears WCAG AA in both
  themes.
- `references/design-system.css`, the two-tier token block every
  template embeds, and `references/conversion-rules.md`, the procedure
  that turns an upstream page into a template.
- `scripts/verify.sh`, checking that a template parses, holds no
  external reference, embeds the token block unedited, carries no raw
  colour outside it, keeps no upstream brand name, and runs no script
  that writes a raw colour into CSS. That last check covers `style`,
  `cssText`, `setProperty`, `setAttribute`, `insertRule`, the text of a
  `<style>` element the script builds, and a `style="…"` attribute in
  markup it assembles — a colour set any of those ways pins itself to
  one theme.
- `scripts/audit-contrast.js`, a WCAG audit of a rendered page. It
  measures each text node against the ground it is actually painted on,
  down to text one character long: a diff marker, a numbered badge and
  a separator glyph are each a single node, and each is text a reader
  reads.
- `scripts/sweep-contrast.sh`, which runs that audit over every template
  in both themes in one browser session per theme — about thirteen
  seconds a theme, where one launch per page costs eight minutes. It
  exits 0 when every page is clean, 1 on findings, and 2 when it could
  not run. The browser invocation stays machine-local: pass
  `--driver <command>`, or let it read the `sweep-driver:` line of a
  `.claude/browsing.md` of your own.
- `scripts/update.sh`, a read-only upstream drift checker that needs no
  local copy of upstream. It reports what a run costs and what the hour
  has left — `spent 2 API call(s), 58 of 60 left this hour` — read from
  the response headers at no extra call. Unauthenticated GitHub allows
  60 an hour.
- `scripts/upstream.sh`, borrowing an ephemeral clone for the duration
  of an ingest run, and `scripts/stamp.sh`, re-embedding the token block
  in a template.
- `templates/MANIFEST.json`, twenty records pinned at `58c305b`.
- `LICENSE`. The twenty templates derive from
  `anthropics/html-effectiveness`, and MIT requires that notice to
  travel with them. The tooling in this repo is MIT under its own
  copyright. The file carries both, over the upstream licence text
  unchanged.
