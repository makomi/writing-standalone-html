# TASKS

Open work only. A task is deleted when it ships — what was done lives in
`CHANGELOG.md` and the git history, and a second copy here goes stale.

The ten-task build plan is finished and `v1.0.0` is tagged, so the next
task comes from here rather than from
`docs/plans/2026-08-14-writing-standalone-html.md`.

## Prioritized

### Medium

**Put `scripts/audit-contrast.js` under test.** Nothing in
`tests/` exercises it. Its ground rule changed on 2026-08-17 — an
ancestor counts only if it contains the text box, and a straddling
ground is reported with `"straddles": true` — and that logic was
verified by hand against scratch pages that no longer exist. The next
edit can reintroduce the false positive silently, in the one tool the
theme review depends on. Medium effort: lift the pure helpers
(`contrast`, `luminance`, `contains`, `intersects`) into a form node
can import, and add a suite that skips when node is absent, the way
`test_js_syntax.py` does. No browser, so `run-all.sh` keeps its rule
that a browser is never a dependency. The cases worth pinning are the
three the ground fix turned on — contained, straddling, and no painted
ancestor at all — and the node filter, which counts a one-character
node as text since 2026-08-18.

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
suite. That happened on 2026-08-16. Running out mid-suite is worse
again: on 2026-08-18 a run exhausted the budget partway and `run-all.sh`
reported the suite as failed, where the next run — with the whole budget
already gone — reported the same state as a skip. Small to medium
effort: fetch the tree once per run and reuse it, or point four of the
five assertions at a stub and keep one live call as the integration
check.

**Confirm or withdraw the symlink install route.** `README.md` and
decision `0005` both offer
`ln -s <repo> ~/.claude/skills/writing-standalone-html` and both label
it unverified. A documented route in an unknown state is worse than no
route. Trivial for a person — create the symlink, start a session, see
whether the skill is listed — and impossible for an agent, because
writes to `~/.claude/skills/` are denied.

### Low

**Stop the fixture re-stamp destroying the drift it tests.** Editing
`references/design-system.css` means running `stamp.sh` twice: once for
`templates/`, which it defaults to, and once for `tests/fixtures/`,
which it does not. The second run overwrites the deliberate
`--bg: var(--white)` edit in `bad-token-drift.html` — the whole point
of that fixture — and the only record of what the drift was is git
history. `test_verify.sh` goes red, so nothing ships broken; the cost
is the archaeology. Small effort: have the fixture derive its drift
from the source at test time, or teach `stamp.sh` to cover fixtures and
re-apply the known edit. Hit on 2026-08-17 during the token retune.

**Ignore the dotfiles the sandbox masks into the repo root.** About a
dozen — `.bashrc`, `.env`, `.mcp.json`, `.vscode` and more — appear as
character devices owned by `nobody`. They are not repo content, they
sit in `git status` as untracked forever, and they make `git add -A`
fail outright with "can only add regular files". `AGENTS.md` records
the workaround, which is to stage explicit pathspecs. Trivial effort:
list them in `.gitignore` and confirm `git add -A` then succeeds. Left
at Low because the workaround costs nothing once known.

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
`[Unreleased]` section with six user-facing entries: the repo carries
the upstream MIT notice, `scripts/verify.sh` gained a sixth check,
text on a solid fill clears WCAG AA in five templates,
`02-exploration-visual-designs.html` no longer
hides its preview headings in dark theme, `--accent` and `--ok` are
legible on a sunken panel in light theme, and `audit-contrast.js` stops
reporting a positioned label against a fill it never touches. That is a
`v1.1.0` by semver — a licence file and a new check outrank the four
fixes.
Blocked on whether the skill has been installed anywhere yet. If nobody
has `v1.0.0`, folding all six into a re-cut `v1.0.0` is cleaner than
shipping two tags nobody used; if somebody does have it, the token fix
argues for tagging soon, because it is a defect a reader meets on a
first read.
