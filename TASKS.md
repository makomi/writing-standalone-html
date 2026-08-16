# TASKS

Open work only. A task is deleted when it ships — what was done lives in
`CHANGELOG.md` and the git history, and a second copy here goes stale.

The ten-task build plan is finished and `v1.0.0` is tagged, so the next
task comes from here rather than from
`docs/plans/2026-08-14-writing-standalone-html.md`.

## Prioritized

### High

**Test the token pair that fails, `--accent` on `--surface-sunken`.**
`tests/test_tokens.py` checks `--accent` against `--bg` and `--surface`
and passes at 4.51:1 and 4.75:1. It never checks `--surface-sunken`,
where the same accent reaches only 4.09:1, and `--ok` only 4.13:1 —
both short of the 4.5:1 small text needs. Two shipped templates land
there: the slot chips in `20-editor-prompt-tuner.html` and the addition
count in `17-pr-writeup.html`. Dark theme passes; this is a light-theme
defect only.

Adding the pair to `PAIRS` turns a silent near-miss into a red suite,
which is the point — but it also decides something. Either the deep
variants get retuned until they clear 4.5:1 on the sunken surface, or
that pairing is ruled out and the two templates move their accent text
to `--surface`. Invariant 4 permits the first: `--clay-deep` and
`--olive-deep` are this project's own, not upstream's palette.

### Medium

**Raise the four fixed fills that fail AA.** Found by
`scripts/audit-contrast.js` on 2026-08-16, each identical in both
themes because each is Tier 1 on Tier 1:

| Where | Pair | Ratio |
|---|---|---|
| `16` Post button | `--white` on `--clay` | 3.12 |
| `12` deleted diff line | `--rust` on `--code-bg` | 3.42 |
| `02` preview body text | `--gray-500` on the fixed ground | 3.47 |
| `16` second avatar | `--white` on `--olive` | 3.68 |

`02` already solved this shape once: header note (6) moved the primary
button to `--clay-deep` for exactly this reason, and recorded that the
artboard stays theme-invariant because `--clay-deep` is Tier 1 too. The
same move fixes the `16` button. The other three need a decision rather
than a substitution, which is why this sits below the token-pair task.

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
`[Unreleased]` section with two user-facing entries: `scripts/verify.sh`
gained a sixth check, and `02-exploration-visual-designs.html` no longer
hides its preview headings in dark theme. That is a `v1.1.0` by semver —
the added capability outranks the fix. Blocked on whether the skill has
been installed anywhere yet. If nobody has `v1.0.0`, folding both into a
re-cut `v1.0.0` is cleaner than shipping two tags nobody used; if
somebody does have it, the fix alone argues for tagging soon, because it
is a defect a reader meets on their first dark-mode page.
