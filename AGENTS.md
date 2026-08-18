# AGENTS.md

Instructions for agents working **on** this repository. For using the
skill, read `SKILL.md`.

## What this repo is

A Claude Code skill: twenty self-contained HTML templates plus the
tooling that keeps them synchronized with upstream
`anthropics/html-effectiveness`.

Read before changing anything:

1. `docs/specs/2026-08-14-writing-standalone-html-design.md` — the design
2. `docs/decisions/` — eight decision records with the alternatives rejected
3. `docs/plans/2026-08-14-writing-standalone-html.md` — the ten-task build
4. `TASKS.md` — the open backlog, and where the next task comes from

If a change contradicts a decision record, that is a new decision. Write
`docs/decisions/0008 - ....md`, mark the old record superseded, and say
so in the commit body. Do not silently reverse one.

The build plan is finished and `v1.0.0` is tagged, so "the next task"
means the top of `TASKS.md`, not the next unchecked plan step. The plan
keeps its checkboxes as a record of what was built and what was skipped.

## Browsing and the theme check

Two checks need a rendered page, and `scripts/verify.sh` makes neither:
whether a template holds up in dark theme, and whether its retained
interaction still works. Both need a browser.

**What the step needs.** Any headless browser you can drive from a
shell, provided it can do five things: load a `file://` URL, set the
viewport, evaluate JavaScript in the page and hand back the result,
capture a screenshot, and send a key press. Playwright, Puppeteer and a
bare Chrome DevTools Protocol client all qualify.

The concrete invocation is machine-local, so this repo does not carry
one. If `.claude/browsing.md` exists, it holds the commands for this
machine. That path is git-ignored, so a fresh clone has none: write the
equivalent for whatever driver you have before running either check.
Everything below is stated in terms of the five capabilities, not a
command line. Decision 0008 records why.

**Set the theme on a copy, not the template.** Templates ship without
`data-theme` on the root element, so they follow the reader's system
setting and a headless browser gives you light:

```bash
sed 's/<html lang="en">/<html lang="en" data-theme="dark">/' \
  templates/11-status-report.html > "$TMPDIR/dark.html"
```

`data-theme="dark"` and `data-theme="light"` both work, and the token
block supports the attribute directly, so there is no need to rewrite
the media query.

**Read the computed style, not the screenshot.** A 14px swatch and a
downscaled screenshot will both lie to you. Two findings from the
2026-08-16 sweep — inverted delta colours in `09`, light legend chips
in `13` — were false alarms that `getComputedStyle` disproved in one
call. Load the dark copy and ask the page:

```js
getComputedStyle(document.querySelector('.chip')).backgroundColor
```

Two traps around that. A colour under a CSS `transition` reads as the
value it is passing through, so let one settle before believing it
(`19`'s toggle track takes 160ms). And a driver that chains steps into
one call may print nothing at all when a step fails, which loses the
whole run's output to a mistyped selector rather than just that step's —
find out which kind yours is before trusting an empty result.

**A page taller than the viewport needs more than one shot.** Full-page
capture is usually capped and scaled down — 2000px in the driver these
templates were checked with — and the scaling costs exactly the
legibility the check depends on. Scroll in viewport-sized steps instead.
`09-slide-deck.html` is the exception: it is a scroll-snap deck and
`window.scrollTo` does not move it. Drive it with the right-arrow key,
or jump with
`document.querySelectorAll('.slide')[n].scrollIntoView({behavior:'instant'})`
when you want the shot without waiting out the smooth scroll.

**`scripts/audit-contrast.js` does the same reading for every text node**
on the page and reports what fails WCAG AA. It found the `02` defect
that eleven screenshots had not. Set the viewport to 1280x900, load the
page, then evaluate the script's source in it. The result is the
findings as JSON; `[]` is a pass for everything it looks at, which is
not everything on the page. One character counts as text: a diff
marker, a focus-item number and a middot separator are each a single
node, and the first two were real AA failures that an earlier `> 1`
bound hid until 2026-08-18.

It is an audit aid, not a suite member: it needs a browser, and a
browser must not become a dependency of `tests/run-all.sh`. Its rules
are a suite member, though. Everything that is not a DOM read — colour
parsing, contrast, the rect geometry, the node filter, the large-text
threshold and the ground rule — is a pure function the file exports
when node requires it, and `tests/test_audit_contrast.py` pins each
one. Change a rule and change its case.

**`scripts/sweep-contrast.sh` runs that audit over every template in
both themes** in one browser session per theme: about thirteen seconds
a theme, against the eight minutes forty separate launches cost. Run it
after any template edit — the two one-character failures found on
2026-08-18 survived two earlier sweeps because a sweep that costs eight
minutes gets run selectively. Batched and per-page results were
compared on eighteen pages carrying eight known findings on 2026-08-18
and agreed exactly. It exits 0 clean, 1 on findings, 2 when it could
not run.

The browser invocation stays machine-local (decision 0008): the script
takes `--driver <command>` and otherwise reads the `sweep-driver:` line
of `.claude/browsing.md`. The command is called with the audit's path
and a list of urls and must print one JSON object mapping each url to
that page's findings, which keeps the batching in the repo and the
driver grammar out of it.

The ground is the nearest ancestor that paints **and** contains the
text box. Ancestry alone is not enough: the beat labels in
`07-prototype-animation.html` are absolutely positioned clear of the
12px dot they are nested in and paint on the panel behind it, which is
why the walk skips both the dot and the 2px track above it. A finding
carrying `"straddles": true` means the text crosses that ground's edge
instead of sitting on it, so the ratio holds for part of the run —
look at the page rather than trusting the number.

## What this environment cannot do

- **No writing to `~/.claude/skills/`.** The skill cannot install
  itself; decision 0005 records why. Print the command and let a person
  run it.
- **No writing to `/tmp`.** Refused outright. Use `$TMPDIR`, which the
  recipes above assume.
- **No launching a browser binary yourself.** A bare
  `chromium --headless` is denied `socket()` and dumps core before it
  renders anything. Whatever drives the page has to be something the
  sandbox already permits.
- **No `git config` writes.** `.git/config` and `~/.gitconfig` are both
  read-only mounts, and `.git/config.lock` is masked as a character
  device, so every `git config` call fails with "could not lock config
  file". `git gc` and `git branch` print the same warning while
  otherwise succeeding — it is their own bookkeeping write failing, not
  the operation. An identity change has to be made outside the sandbox.
  Rewriting history still works, because `git filter-branch` takes the
  identity from environment variables.
- **No `git add -A`.** The sandbox masks `.bashrc`, `.env`, `.mcp.json`
  and a dozen more dotfiles into the repo root as character devices.
  They show up as untracked, and git refuses the whole staging run with
  "can only add regular files". Stage explicit pathspecs instead. The
  files are not repo content and must never be committed.
- **Only 60 unauthenticated GitHub API calls an hour.** A budget rather
  than a wall. See "Running the checks" for what that costs and how to
  raise it.

## Invariants

Breaking any of these breaks the point of the project.

1. **Templates have zero external references.** No CDN, no external
   font, no remote image. Embed images as data URIs or draw inline SVG.
   This is the property the whole project exists to preserve.
2. **The token block is embedded verbatim, never linked.** It sits
   between `/* TOKENS:BEGIN */` and `/* TOKENS:END */`. Linking
   `references/design-system.css` would satisfy DRY and destroy
   invariant 1. Edit the source of truth and run `./scripts/stamp.sh`
   to push it into every template. Never edit a copy in place.
   `scripts/verify.sh` compares every embedded copy against the source
   of truth and fails on a mismatch.
3. **No raw colour outside the token block.** Every color resolves
   through `var()` — hex, `rgb()`, `hsl()` and named colours alike.
   `scripts/verify.sh` enforces this, in a `<style>` block, in a
   colour-bearing attribute, and in a string a script writes into CSS
   through `style`, `cssText`, `setProperty` or `setAttribute`. A colour
   set from JavaScript pins itself to whichever theme was current, and
   it fails only after a reader interacts. Put the colour in a class and
   let the script toggle the class.
4. **Tier 1 light values are upstream's palette.** Never retune them.
   Contrast problems get fixed in the variants this project added —
   `--clay-deep`, `--olive-deep` for light, `--ink`, `--ink-raised`,
   `--clay-light`, `--olive-light`, `--rust-light` for dark — never by
   editing `--clay` or `--ivory` themselves.
5. **`scripts/update.sh` is read-only.** It never edits a template and never
   writes `MANIFEST.json`, including `checked_at`. A cron run that
   dirties the git tree produces spurious diffs forever after.
6. **Interaction logic is kept, not rewritten.** Keyboard navigation,
   drag-and-drop, tab switching and live re-render come from upstream
   working. Do not refactor or simplify them.
7. **Nothing references a path outside this directory.** Drift
   detection reads the GitHub API. Anything needing upstream file
   contents runs `./scripts/upstream.sh fetch`, works in `.upstream/`, and runs
   `./scripts/upstream.sh clean`. Never hardcode a clone living elsewhere on
   the machine, and never leave `.upstream/` behind.

## Running the checks

No install step. Python 3 standard library only.

```bash
./tests/run-all.sh    # every suite, in the one order that is correct
```

Any suite can also be run on its own, in any order. `test_upstream.sh`
moves aside a clone it finds and puts it back, so running the suite
mid-task no longer destroys the clone that task was converting from.
Only `test_conversion_rules.py` needs upstream file contents, and
`run-all.sh` brackets the fetch and clean around it.

The individual pieces:

```bash
./scripts/verify.sh                      # all templates
./scripts/verify.sh templates/09-*.html  # one file
./scripts/stamp.sh                       # re-embed the token block
./tests/test_verify.sh              # the checker's own tests
./tests/test_upstream.sh            # borrow and return the clone
python3 tests/test_tokens.py        # token roles and WCAG contrast
python3 tests/test_js_syntax.py     # every inline script parses
python3 tests/test_audit_contrast.py  # the contrast audit's own rules
./tests/test_update.sh              # drift classification and exit codes

# This one reads upstream sources, so bracket it:
./scripts/upstream.sh fetch && python3 tests/test_conversion_rules.py; \
  rc=$?; ./scripts/upstream.sh clean; exit $rc
```

Three suites skip rather than fail when they cannot run, and the runner
reports a skip as a skip rather than a pass. `test_js_syntax.py` and
`test_audit_contrast.py` skip when `node` is absent — node is not a
dependency and must not become one. `test_update.sh` skips when the GitHub API is unreachable, because
an outage reported as a code failure is the exact confusion `update.sh`
has a distinct exit 2 to prevent.

Watch the API budget: `test_update.sh` spends about ten calls, and
unauthenticated GitHub allows 60 an hour. Six full runs exhaust it. Set
`GITHUB_TOKEN` when iterating.

Do not add a dependency, a package manager, or a virtualenv. The repo
must stay installable by copying a directory. This overrides the
default preference for `uv`: there is no Python project here, only
stdlib helper scripts.

## Converting a template

Never freehand it. Follow `references/conversion-rules.md` step by step.
The rules exist so the twentieth conversion matches the first, and they
are the only thing making agent-driven conversion reproducible.

Two rules people get wrong:

- **Map colors by job, not by value.** The same `#3D3D3A` is body text
  in one place and a border in another. Matching on the hex produces a
  file that looks converted and is wrong.
- **Collapse to one instance, except when one cannot show the
  pattern.** A comparison page needs two cards. A slide deck needs two
  slides for the keyboard navigation to have a destination. A
  dependency warning needs a prerequisite to point at. Use judgment and
  record it in the template's header notes.

After converting, run `./scripts/verify.sh <file>`, then
`./scripts/sweep-contrast.sh <file>`, which renders it in both themes
and audits each. See "Browsing and the theme check" for what that
needs. The audit catches a
colour mapped to a role that inverts; the eye catches the rest, which is
why both still happen.

## Traps

Each of these cost time at least once. They are settled; do not reopen
them.

- **Never edit a token block inside a template.** Edit
  `references/design-system.css` and run `./scripts/stamp.sh`. The
  checker fails the file if you forget.
- **`./scripts/upstream.sh clean` after anything that fetches.** The
  clone is git-ignored, so a stale one is invisible in `git status`.
- **The colour check scans `<style>` blocks and colour attributes only,
  and skips HTML comments.** Both exclusions are deliberate: `#4871` in
  `11-status-report.html` is a pull-request number, and the provenance
  headers quote the colours they replaced. Commit `349531c` removed a
  regression that widened the scan.
- **The script-colour check triggers on the sink, not the string.** A
  colour fails when it reaches CSS through `style`, `cssText`,
  `setProperty` or `setAttribute("style", ...)`. A colour in a data
  attribute or a label is not a defect. When it fires, put the colour in
  a CSS class and toggle the class — never a `var()` inside the string.
  `03` and `06` are the worked examples.
- **`data-theme` and `--warn` are settled.** `--warn` resolves to the
  same clay as `--accent` on purpose. Do not add an amber to separate
  them.
- **A three-step severity scale has two hues, not three.** `03` is the
  worked example: safe takes `--ok`, the middle step takes the neutral
  band, flagged takes `--accent`.
- **Text on the code panel takes a light variant.** `--code-bg` is the
  same near-black in both themes, so the tier that reads on it is the
  light one — `--rust-light`, `--olive-light`. Upstream's own diff
  colours are light hues, `--rust` reaches only 3.4:1 there against
  5.4:1 for `--rust-light`, and the deep variants are tuned for ivory
  and go muddy. `03` and `12` are the worked examples.
- **A solid Tier 1 fill behind white needs a deep variant.** White on
  `--clay` is 3.1:1 and on `--olive` 3.7:1; `--clay-deep` and
  `--olive-deep` reach 5.4:1 and stay Tier 1, so the element stays
  theme-invariant. The light variants are for text on a dark ground and
  make a fill worse. `16` and `17` are the worked examples.
- **There is no target line count.** A template is as long as its genre
  CSS and interaction logic make it. Spec section 4.4 records the
  measurement and withdraws the old projection.

## Commits

Conventional Commits, with the metadata footer:

```
<type>(<scope>): <short imperative summary>

One paragraph: what changed and why.

[Constraint]    The binding requirement that shaped the solution.
[Rejected]      Alternatives considered, and why.
[Confidence]    low | medium | high
[Scope-risk]    narrow | broad
[Reversibility] clean | messy
[Directive]     Guidance for the work that follows.
[Tested]        What was verified before committing.
[Not-tested]    Known gaps in verification.
```

Wrap body and footer at 72 characters. One commit per logical change.
Skip the footer for typos and formatting.

## Changelog

`CHANGELOG.md` records **what changes for someone who has installed the
skill**. It is not a log of the work.

Update it in the same commit as the change it describes. Never backfill
it later from a run of commits: a changelog assembled after the fact
looks compliant without doing the job, which is telling a reader what
they are getting.

**The test:** would somebody who installed this skill, and who will
never read this repository, notice? If no, it does not go in.

| Goes in | Stays in the commit body |
|---|---|
| A template added, removed or renamed | Test suites and fixtures |
| A change to what the skill triggers on | Refactors, file moves |
| A change to how a generated page looks | Tooling bugs fixed before release |
| A command someone runs: `verify`, `update`, `upstream` | Corrections to our own measurements |
| A change to the tokens a template embeds | Documentation syncs |
| A breaking change to `MANIFEST.json` | Anything in `docs/` |

Two rules that follow from this:

- **An empty release section is a legitimate outcome.** If a milestone
  changed nothing a user can see, say exactly that. Padding the section
  with internal work to make it look substantial is the failure this
  rule exists to prevent.
- **A bug fixed before it ever shipped is not a fix.** It never reached
  a user, so there is nothing to tell them. Record it in the commit
  body, where the reasoning is useful to whoever hits it next.

## Writing

- Short sentences, plain words, active voice. Cut words, never
  information.
- Name the file, the command, the number. Avoid "some", "various",
  "should probably".
- Never use gendered or gender-split language. Use the plain generic
  noun, or rewrite so the noun disappears.
- `README.md` and `SKILL.md` are read by people who have never seen a
  previous version. Never write "now also", "as corrected above", or
  any sentence that only parses for someone who saw the last edition.
  Internal records — decision files, commit bodies, this file — do keep
  their history.

## Installing after a change

The sandbox cannot write to `~/.claude/skills/` (decision 0005). Print
the command and let a human run it:

```bash
echo "mv $(pwd) ~/.claude/skills/"
```
