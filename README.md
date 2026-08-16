# writing-standalone-html

A Claude Code skill that supplies house-styled, self-contained HTML
templates for twenty document genres — status reports, incident
post-mortems, implementation plans, PR write-ups, module maps,
explainers, flowcharts, slide decks, design system sheets, prototypes
and small single-purpose editing UIs.

Every template is one file. No build step, no dependency, no external
reference. Open it in a browser and it works.

## Status

**`v1.0.0`.** All ten tasks of the build plan are done and every test
passes.

| Path | State |
|---|---|
| `references/design-system.css` | Built — two-tier tokens, light and dark, with an explicit theme switch |
| `references/conversion-rules.md` | Built — the seven-step procedure |
| `scripts/verify.sh` | Built — six mechanical checks |
| `scripts/upstream.sh` | Built — borrow and return the clone |
| `scripts/stamp.sh` | Built — re-embed the token block |
| `scripts/update.sh` | Built — read-only drift check over the GitHub API |
| `templates/MANIFEST.json` | Built — 20 records, pinned at `58c305b` |
| `lib/`, `tests/` | Built — 6 test suites, all green via `tests/run-all.sh` |
| `templates/` | 20 of 20 converted |
| `SKILL.md` | Built — the trigger surface and the genre selection table |

One check is open, and no script can make it: thirteen templates are
waiting on a look in both themes, and the interactive files have not
been driven in a browser since conversion. The plan's status section
names them.

## How it works

Templates derive from
[`anthropics/html-effectiveness`](https://github.com/anthropics/html-effectiveness)
(MIT), pinned at commit `58c305be97f47b26b678f2c07dec01d4242268ec`.
Upstream ships twenty finished example pages carrying fictional data.
This project converts each one into a template by doing two things:

**Stripping content to a skeleton plus one worked instance.** A triage
board with thirty fictional tickets keeps one, marked
`<!-- repeat per ticket -->`. The pattern survives; the fiction does
not. Interaction logic — keyboard navigation, drag-and-drop, tab
switching — is kept intact, because it is expensive to re-derive and
easy to get subtly wrong.

**Re-tokenizing every color.** Upstream names its CSS custom properties
by color (`--ivory`, `--clay`) and the names drift between files: the
same `#3D3D3A` is `--gray-700` in one file and `--gray-800` in another.
A color-named token cannot flip between light and dark, so this project
adds a semantic tier — `--bg`, `--surface`, `--text`, `--accent`,
`--ok`, `--danger` and the rest — and templates reference that. Dark
mode then costs one edit to a shared block instead of one edit per
template.

A page follows the reader's system setting by default, and can override
it by setting `data-theme="dark"` or `data-theme="light"` on the root
element.

There are 253 such colors across the twenty files, drawn from 49
distinct values. Fourteen recur often enough to be mapped in a table;
the rest are gradient stops and tag tints handled by an ordered
fallback. `10-svg-illustrations.html` alone holds 97, in SVG
presentation attributes that have to be lifted into CSS classes before
they can take a `var()`.

Two accessibility findings shaped the palette. Upstream's clay reaches
only 2.96:1 on ivory and its olive 3.49:1, short of the 4.5:1 these
colors need when used as text — so `--accent` and `--ok` resolve to
darker variants while Tier 1 keeps upstream's exact values. And
`--border` is deliberately exempt from a contrast floor: a table row
rule is decoration, not a control boundary. `--border-strong` carries
that requirement instead.

## Installing

The skill is a plain directory. Claude Code discovers it in
`~/.claude/skills/`:

```bash
mv writing-standalone-html ~/.claude/skills/
```

To keep the repository where development happens, link it instead:

```bash
ln -s "$PWD/writing-standalone-html" ~/.claude/skills/writing-standalone-html
```

The symlink route is unverified — confirm the skill is discovered before
relying on it.

Installation is manual by design. An agent sandbox cannot write to
`~/.claude/skills/`, because a skill directory is executable surface.
See `docs/decisions/0005`.

## Using it

The skill triggers on its own when the work matches one of its twenty
genres. Ask for a status report or an incident write-up and the template
is applied without being named.

It deliberately does not trigger for app UI, marketing pages or general
web development. Those belong to `frontend-design`. A template forced
onto the wrong genre is worse than no template.

## Keeping up with upstream

```bash
./scripts/update.sh
```

Reads every upstream file's blob SHA from the GitHub API, compares them
against `templates/MANIFEST.json`, and prints four lists: unchanged,
changed, new, removed. It keeps no copy of upstream and touches nothing
outside this directory, so it is safe to run unattended.

Exit codes are distinct on purpose: `1` means upstream drifted and there
is work to do, `2` means the check itself could not run — no network, a
rate limit, a malformed response. A wrapper that conflates them would
read an outage as a clean result.

Conversion stays manual, because it needs judgment a script cannot
supply: which instance is representative, where a repeat boundary falls,
and which semantic role a given color plays. It also needs file
contents, which the API path deliberately does not fetch, so it borrows
a clone for the duration:

```bash
./scripts/upstream.sh fetch     # depth-1 clone into .upstream/
# convert per references/conversion-rules.md, stamp MANIFEST.json
./scripts/upstream.sh clean     # delete it again
```

`.upstream/` is git-ignored and is not meant to survive the run. A clone
is 860 KB and takes seconds, which is cheaper than a permanent second
copy of upstream that can go stale without anyone noticing.

## Verifying

```bash
./scripts/verify.sh
```

Checks every template: it parses, it holds no external reference, its
token block matches `references/design-system.css` exactly, it carries
no raw colour outside that block, no script writes a raw colour into
CSS, and no upstream brand name survives.

One check stays manual — that the page reads correctly in both light
and dark themes. No script can make it.

## License

Templates derive from MIT-licensed upstream material. Every template
carries its source file, its upstream commit and its blob SHA in a
header comment. `templates/MANIFEST.json` collects the same records for
the drift checker.
