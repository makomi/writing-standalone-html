# TASKS

Open work only. A task is deleted when it ships — what was done lives in
`CHANGELOG.md` and the git history, and a second copy here goes stale.

The ten-task build plan is finished and `v1.0.0` is tagged, so the next
task comes from here rather than from
`docs/plans/2026-08-14-writing-standalone-html.md`.

## Prioritized

### High

**Keep `browse-once` out of the repo before it is published.** The tool
is local to this machine: `~/.claude/bin/browse-once/browse-once`, with
gstack behind it. `AGENTS.md` names it eight times and gstack four
more — the whole "Browsing and the theme check" section is written
around it — and `scripts/audit-contrast.js` line 3 points a reader at
that section for the invocation. Published as it stands, the repo
would instruct anyone working on it to run a binary they do not have,
and it would do so in the one section that documents the two checks
`verify.sh` cannot make.

The trigger is publication, not the calendar. Nothing is wrong while
the repo is private, and the priority is High because the leak is
silent at exactly the moment it matters: the push.

Keeping the instructions in is the fallback, not the goal. If they
stay, they have to work for somebody with no gstack and no
`browse-once` — which means naming what the step needs (a headless
browser, a computed style, a full-page capture) and treating the local
binary as one way to get it.

Three shapes were raised, and the choice is open:

- Move the browsing section into `.claude/`, which `.gitignore`
  already excludes, so it stays local by construction.
- Move it into the global `CLAUDE.md`, where it is machine-wide and
  never in any repo.
- Keep a tool-neutral section in `AGENTS.md` and let the local file
  supply the concrete command.

Each trades away something: the first two take the instructions out of
the repo that needs them, and the third leaves a public reader with a
step they must still solve themselves. Recommendation to follow when
the task is taken on.

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
than a substitution, which is what holds this at Medium: a fill that is
Tier 1 on Tier 1 cannot be repaired by darkening a variant the way
`--accent` and `--ok` were.

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

**Say why `15` can report that nothing moved.** "remove a node" deletes
a node at random, so the ring sometimes reads "0 (0%) moved on last
change" — the opposite of the point the demo exists to make, which is
that a ring moves few keys rather than none. The logic is upstream's and
invariant 6 keeps it, so the fix is a sentence in the template's header
notes saying the pick is random and the readout is honest about that
draw. Trivial effort. Rewriting the pick to prefer a node that owns keys
would be a code change to retained interaction, which needs a decision
record first.

**Open `06` and `07` with a judgment-call count.** The other eighteen
templates start their header notes with "N judgment calls" and then
number them; `06` lists six and `07` lists five with no opening line.
Nothing breaks and no reader is misled, but a convention kept in
eighteen places and dropped in two stops being a convention. Trivial
effort: one line each, counted from what is already there.

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
`[Unreleased]` section with four user-facing entries:
`scripts/verify.sh` gained a sixth check,
`02-exploration-visual-designs.html` no longer
hides its preview headings in dark theme, `--accent` and `--ok` are
legible on a sunken panel in light theme, and `audit-contrast.js` stops
reporting a positioned label against a fill it never touches. That is a
`v1.1.0` by semver — the added capability outranks the three fixes.
Blocked on whether the skill has been installed anywhere yet. If nobody
has `v1.0.0`, folding all four into a re-cut `v1.0.0` is cleaner than
shipping two tags nobody used; if somebody does have it, the token fix
argues for tagging soon, because it is a defect a reader meets on a
first read.
