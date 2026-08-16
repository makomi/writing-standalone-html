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
