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
reader rather than sitting in a branch. Use the `/browse` skill from
gstack and pin the theme with `data-theme="dark"` on the root element;
`AGENTS.md` covers the setup and the stale-daemon recovery.

### Medium

**Close the three colour-in-script routes the check misses.**
`check_no_colour_in_scripts` triggers on four sinks: `style`, `cssText`,
`setProperty` and `setAttribute("style", ...)`. Three more reach CSS and
were confirmed to get through on 2026-08-16 — a colour in
`styleEl.textContent`, in `sheet.insertRule(...)`, and in a `style="…"`
attribute built inside an `innerHTML` string. Each pins a colour to one
theme exactly the way the check exists to prevent, and the `innerHTML`
route is plausible in these templates. Small effort: three patterns
added to `STYLE_SINK`, plus a fixture per route. No template trips them
today, so this is closing the rule rather than repairing a breach.

**Stop the drift suite exhausting the API budget.**
`tests/test_update.sh` invokes `update.sh` five times and each call
spends two GitHub API calls. Unauthenticated GitHub allows 60 an hour,
so six full suite runs exhaust it — and the suite then reports green
with drift detection skipped, which is a green run hiding an unexercised
suite. That happened on 2026-08-16. Small to medium effort: fetch the
tree once per run and reuse it, or point four of the five assertions at
a stub and keep one live call as the integration check.

**Confirm or withdraw the symlink install route.** `README.md` and
decision `0005` both offer
`ln -s <repo> ~/.claude/skills/writing-standalone-html` and both label
it unverified. A documented route in an unknown state is worse than no
route. Trivial for a person — create the symlink, start a session, see
whether the skill is listed — and impossible for an agent, because
writes to `~/.claude/skills/` are denied.

### Low

**Route the conversion-rules suite through `run()` in `run-all.sh`.**
That one block is written out longhand instead of using the runner's
`run()` helper, so it duplicates the pass and fail logic and cannot
report a skip. Nothing is wrong today, because that suite never skips —
`run-all.sh` always fetches the clone for it first. It becomes a real
defect the moment the suite learns to skip, because the runner would
call the skip a pass. Small effort: give `run()` an optional setup and
teardown, or bracket the fetch outside it.

**Read a JavaScript regex literal as a regex in `test_js_syntax.py`.**
The literal scanner treats `/["']/` as the start of a string, so a regex
containing a quote desynchronizes it. The consequence is bounded: it can
only produce a false positive inside a style assignment, never a missed
syntax error, and no template contains such a regex. Small to medium
effort — distinguishing a regex from division needs the preceding token,
which is why it was not done the first time.

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
