# AGENTS.md

Instructions for agents working **on** this repository. For using the
skill, read `SKILL.md`.

## What this repo is

A Claude Code skill: twenty self-contained HTML templates plus the
tooling that keeps them synchronized with upstream
`anthropics/html-effectiveness`.

Read before changing anything:

1. `docs/specs/2026-08-14-writing-standalone-html-design.md` — the design
2. `docs/decisions/` — six decision records with the alternatives rejected
3. `docs/plans/2026-08-14-writing-standalone-html.md` — the ten-task build

If a change contradicts a decision record, that is a new decision. Write
`docs/decisions/0007 - ....md`, mark the old record superseded, and say
so in the commit body. Do not silently reverse one.

## Invariants

Breaking any of these breaks the point of the project.

1. **Templates have zero external references.** No CDN, no external
   font, no remote image. Embed images as data URIs or draw inline SVG.
   This is the property the whole project exists to preserve.
2. **The token block is embedded verbatim, never linked.** It sits
   between `/* TOKENS:BEGIN */` and `/* TOKENS:END */`. Linking
   `references/design-system.css` would satisfy DRY and destroy
   invariant 1.
3. **No raw hex outside the token block.** Every color resolves through
   `var()`. `scripts/verify.sh` enforces this.
4. **Tier 1 light values are upstream's palette.** Never retune them.
   Dark-mode contrast problems get fixed in the dark-side raws
   (`--ink`, `--ink-raised`, `--olive-light`, `--rust-light`), never by
   editing `--clay` or `--ivory`.
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
./scripts/verify.sh                      # all templates
./scripts/verify.sh templates/09-*.html  # one file
./tests/test_verify.sh           # the checker's own tests
./tests/test_upstream.sh         # borrow and return the clone
python3 tests/test_tokens.py     # token roles and WCAG contrast
./tests/test_update.sh           # drift classification and exit codes

# This one reads upstream sources, so bracket it:
./scripts/upstream.sh fetch && python3 tests/test_conversion_rules.py; \
  rc=$?; ./scripts/upstream.sh clean; exit $rc
```

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
one that catches a color mapped to the wrong role.

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
Update `CHANGELOG.md` (Keep a Changelog format) in the same commit as
the change it describes. Skip the footer for typos and formatting.

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
