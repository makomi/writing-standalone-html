# TASKS

Open work only. A task is deleted when it ships — what was done lives in
`CHANGELOG.md` and the git history, and a second copy here goes stale.

The ten-task build plan is finished and `v1.0.0` is tagged, so the next
task comes from here rather than from
`docs/plans/2026-08-14-writing-standalone-html.md`.

## Prioritized

### High

**Check every template in both themes, and drive the interactive ones.**
Thirteen templates have never been looked at in dark mode: `02`, `03`,
`04`, `08`, `09`, `12`, `13`, `14`, `15`, `16`, `18`, `19`, `20`. Each
carries judgment calls no mechanical check can see — a class-per-series
ramp in `15`, a theme-invariant slide in `09`, a two-hue severity scale
in `03`, a toggle track moved to `--border-strong` in `19`. The
interaction is unexercised too: `tests/test_js_syntax.py` proves all
fourteen inline scripts parse, which is not the same as working.
Drag-and-drop in `18`, the tab switch in `14`, the flag toggles in `19`,
the ring demo in `15`, the flowchart panel in `13` and the risk-map
flash in `03` have not been driven since conversion.

This is the check that catches a colour mapped to the wrong role, and
`SKILL.md` now hands these templates to readers, so a mistake reaches a
reader rather than sitting in a branch. It needs a person or a session
with browser access — headless chromium is denied `socket()` here. Set
`data-theme="dark"` on the root element to pin the theme.

### Medium

**Confirm or withdraw the symlink install route.** `README.md` and
decision `0005` both offer
`ln -s <repo> ~/.claude/skills/writing-standalone-html` and both label
it unverified. A documented route in an unknown state is worse than no
route. Trivial for a person — create the symlink, start a session, see
whether the skill is listed — and impossible for an agent, because
writes to `~/.claude/skills/` are denied.

### Low

**Harden the HTML balance check against implicit end tags.**
`lib/checks.py` `_Balance` requires explicit closing tags. HTML permits
omitting `</li>`, `</td>`, `</p>` and others, so a valid hand-written
template would be reported as unclosed. Nothing false-positives today,
because all twenty upstream files close their tags. Small effort: add
the standard optional-end-tag set and pop implicitly when a sibling or
parent closes. Deferred until it actually bites — the failure message is
clear enough that a person will find the cause.

## Ideas

Nothing speculative is queued. The build plan is complete and the
backlog above is what remains.

## Open questions

**Should the post-`v1.0.0` work be tagged?** `CHANGELOG.md` carries an
`[Unreleased]` section with one user-facing entry: `scripts/verify.sh`
gained a sixth check. That is a `v1.1.0` by semver, since it adds a
capability rather than fixing a defect. Blocked on whether the skill has
been installed anywhere yet — if nobody has `v1.0.0`, folding the change
into a re-cut `v1.0.0` is cleaner than shipping two tags nobody used.
