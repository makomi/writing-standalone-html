# TASKS

Open work only. A task is deleted when it ships — what was done lives in
`CHANGELOG.md` and the git history, and a second copy here goes stale.

The ten-task build plan is finished and `v1.0.0` is tagged, so the next
task comes from here rather than from
`docs/plans/2026-08-14-writing-standalone-html.md`.

## Prioritized

### Medium

**Confirm or withdraw the symlink install route.** `README.md` and
decision `0005` both offer
`ln -s <repo> ~/.claude/skills/writing-standalone-html` and both label
it unverified. A documented route in an unknown state is worse than no
route. Trivial for a person — create the symlink, start a session, see
whether the skill is listed — and impossible for an agent. Three routes
were tried on 2026-08-19 and all three are closed; `AGENTS.md`, under
"Installing after a change", records which and what is already known,
so the next session does not spend itself rediscovering them.

### Low

**Test the rate-limit path that turns an exhausted budget into exit 2.**
`_get`'s 403 branch in `lib/github.py` and the populated path of
`budget_note()` have only ever run against live GitHub. The 403 branch
is the one that keeps an exhausted budget reading as "the check could
not run" rather than as drift, which is the confusion the distinct exit
codes exist to prevent, so a silent regression there costs more than
its size suggests. Low because the branch is six lines and has not
changed since it was written. Small effort now that the stub exists:
add a `ratelimited` mode to `tests/stub_github.py` that serves 403 with
the rate-limit body and `X-RateLimit-*` headers, then assert exit 2,
the message, and the budget line.

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
`run()` helper, so it duplicates the pass and fail logic and never
reaches `classify()` — it can report neither a skip nor a named gap.
Nothing is wrong today, because that suite does neither:
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

**None open.** The tagging question is settled: `v1.0.0` is re-cut over
the whole state on 2026-08-19, because the skill is not installed
anywhere yet and two tags nobody used are worse than one.
