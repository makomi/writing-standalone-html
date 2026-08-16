# AGENTS.md

Instructions for agents working **on** this repository. For using the
skill, read `SKILL.md`.

## What this repo is

A Claude Code skill: twenty self-contained HTML templates plus the
tooling that keeps them synchronized with upstream
`anthropics/html-effectiveness`.

Read before changing anything:

1. `docs/specs/2026-08-14-writing-standalone-html-design.md` — the design
2. `docs/decisions/` — seven decision records with the alternatives rejected
3. `docs/plans/2026-08-14-writing-standalone-html.md` — the ten-task build
4. `TASKS.md` — the open backlog, and where the next task comes from

If a change contradicts a decision record, that is a new decision. Write
`docs/decisions/0008 - ....md`, mark the old record superseded, and say
so in the commit body. Do not silently reverse one.

The build plan is finished and `v1.0.0` is tagged, so "the next task"
means the top of `TASKS.md`, not the next unchecked plan step. The plan
keeps its checkboxes as a record of what was built and what was skipped.

## What this environment cannot do

Two checks cannot be made from an agent sandbox. Neither is a defect to
fix in code, and both cost real time to rediscover.

- **No browser.** Headless chromium is denied `socket()` and dumps core
  before rendering. The theme and interaction checks need a person or a
  session with real browser access.
- **No writing to `~/.claude/skills/`.** The skill cannot install
  itself; decision 0005 records why. Print the command and let a person
  run it.

A third limit is a budget rather than a wall: the GitHub API allows only
60 unauthenticated calls an hour. See "Running the checks" for what that
costs and how to raise it.

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
./tests/test_update.sh              # drift classification and exit codes

# This one reads upstream sources, so bracket it:
./scripts/upstream.sh fetch && python3 tests/test_conversion_rules.py; \
  rc=$?; ./scripts/upstream.sh clean; exit $rc
```

Two suites skip rather than fail when they cannot run, and the runner
reports a skip as a skip rather than a pass. `test_js_syntax.py` skips
when `node` is absent — node is not a dependency and must not become
one. `test_update.sh` skips when the GitHub API is unreachable, because
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

After converting, run `./scripts/verify.sh <file>` and open the result in a
browser in both themes. The theme check is not automatable and is the
one that catches a color mapped to the wrong role. Set
`data-theme="dark"` or `data-theme="light"` on the root element to pin a
theme — the token block supports it directly, so there is no need to
rewrite the media query.

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
