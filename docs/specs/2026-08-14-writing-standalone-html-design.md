# Design spec: writing-standalone-html skill

Status: accepted
Date: 2026-08-14
Implemented: tasks 1-3 of 10 (see docs/plans/)

## 1. Purpose and scope

The skill supplies house-styled templates automatically whenever the user
asks for a standalone HTML file that matches one of 20 known genres —
exploration doc, code review, design system, status report, incident
report, slide deck, and so on (full list in section 4.0). Each template
is self-contained: no build step, no dependency, no external reference.

**Scope boundary (D1).** The skill fires only for the 20 genres it ships
templates for. It does not fire for general web pages or app UI — the
existing `frontend-design` and `artifact-design` skills already cover
those. `SKILL.md`'s description names the genres explicitly, so matching
happens on use case ("I need a PR write-up", "sketch an incident
post-mortem"), not on the literal phrase "HTML file". A request for "a
standalone HTML file" with no genre match does not trigger this skill.

## 2. Source and licensing

Templates are derived from `anthropics/html-effectiveness`
(https://github.com/anthropics/html-effectiveness), MIT licensed,
pinned at commit `58c305be97f47b26b678f2c07dec01d4242268ec`.

The skill keeps no permanent copy of upstream. Drift detection reads
blob SHAs from the GitHub API, and conversion clones into a git-ignored
`.upstream/` inside the skill folder and deletes it afterwards
(section 6, decision 0006).

Upstream ships 20 numbered `.html` files plus an `index.html` gallery,
11,611 lines total. All sample data upstream is fictional; the
placeholder brand is "Acme". The MIT license permits derivative works;
this project keeps a provenance trail back to the exact upstream commit
and blob (section 5) rather than relying on the license alone.

## 3. Token architecture

This is the load-bearing design decision. Everything else in the
pipeline — conversion effort, verification checks, maintenance cost —
follows from it.

### 3.1 The problem

Upstream is light-mode only: zero of the 21 files contain
`prefers-color-scheme`. All 20 files draw from the same fixed palette —
ivory `#FAF9F5`, slate `#141413`, clay `#D97757`, oat `#E3DACC`, olive
`#788C5D`, rust `#B04A3F`, a gray ramp (`#F0EEE6`, `#D1CFC5`, `#87867F`,
`#3D3D3A`), and white `#FFFFFF` — but each file names its CSS custom
properties **by color**, not by role: `--ivory`, `--clay`, `--olive`.
Token names also drift between files for the identical value: `#3D3D3A`
is `--gray-700` in some files and `--gray-800` in others; `#F0EEE6`
appears as `--gray-150`, `--gray-50`, and `--gray-100` depending on the
file.

A color-named token cannot flip meaning between light and dark. `--clay`
is always `#D97757` — that is what the name promises. But "the page
background" must be ivory in light mode and near-slate in dark mode.
Naming the background token `--ivory` makes that swap incoherent: a
dark-mode background literally named `--ivory` reads as a bug.

### 3.2 The two-tier design (D3)

We add and maintain a dark palette upstream never had. The token set
splits into two tiers:

- **Tier 1 — raw palette.** Fixed values that never change with theme.
  Named by color, matching upstream's intent: `--clay: #D97757`,
  `--olive: #788C5D`, `--ivory: #FAF9F5`, `--slate: #141413`, and so on
  through the full palette in section 3.1. These exist so Tier 2 can
  reference them, and so a designer can still reach for "the clay
  accent" by name.

- **Tier 2 — semantic roles.** Named by function, not color: `--bg`,
  `--surface`, `--surface-sunken`, `--text`, `--text-muted`, `--border`,
  `--border-strong`, `--accent`, `--ok`, `--warn`, `--danger`. Only
  Tier 2 is redefined between light and dark.

Illustrative shape (full definitions live in
`references/design-system.css`):

```css
:root {
  /* Tier 1 — raw palette, fixed, straight from upstream */
  --ivory: #faf9f5;  --slate: #141413;  --clay: #d97757;
  --oat:   #e3dacc;  --olive: #788c5d;  --rust: #b04a3f;
  --gray-100: #f0eee6;  --gray-300: #d1cfc5;
  --gray-500: #87867f;  --gray-700: #3d3d3a;  --white: #ffffff;

  /* Tier 1 — variants this project adds, because upstream's accent
     hues do not clear 4.5:1 as text on either ground */
  --clay-deep: #b34a28;  --olive-deep: #60704b;
  --ink: #1a1a18;  --ink-raised: #232320;
  --clay-light: #e89b80;  --olive-light: #9bb07a;  --rust-light: #d9695c;

  /* Tier 2 — semantic roles, light (default) */
  --bg: var(--ivory);          --surface: var(--white);
  --surface-sunken: var(--gray-100);
  --text: var(--slate);        --text-muted: var(--gray-700);
  --border: var(--gray-300);   --border-strong: var(--gray-500);
  --accent: var(--clay-deep);  --ok: var(--olive-deep);
  --warn: var(--clay-deep);    --danger: var(--rust);
}
```

The dark block redefines the same Tier 2 names and nothing else. The
authoritative file is `references/design-system.css`.

Two findings from building it, both recorded because they change how
the palette is used:

**Upstream's accent hues fail as text.** Clay reaches only 2.96:1 on
ivory and olive only 3.49:1, short of the 4.5:1 that a link or a
severity label needs. In these genres those colors are text — "shipped",
"blocker", a jump link — so the roles point at `--clay-deep` and
`--olive-deep` instead. Upstream's `--clay` and `--olive` keep their
exact values in Tier 1 and stay available for decorative fills.

*Retuned 2026-08-17.* The first values, `#c0502b` and `#677850`, were
measured against `--bg` only, where they reached 4.51:1 and 4.55:1.
They fall to 4.09:1 and 4.13:1 on `--surface-sunken`, which is the
darkest light ground and therefore the one that binds — and two
templates put accent text there. The values above clear 4.5:1 on all
three light grounds; `tests/test_tokens.py` checks the sunken pairing
so the near-miss cannot come back.

**Borders split in two.** `--border` is a decorative hairline with no
contrast floor, which is why upstream's soft `#d1cfc5` survives
unchanged. `--border-strong` is for edges that convey state — an input,
a toggle, a focus ring — and clears 3:1 in both themes. Holding every
row rule to 3:1 would have forced a near-black divider and wrecked the
look for no accessibility gain.

Templates reference Tier 2 exclusively for anything that must adapt —
backgrounds, text, borders, surfaces. Tier 1 stays available for
one-off decorative uses that are intentionally theme-invariant.

### 3.3 Consequence for conversion

Because templates must use Tier 2 tokens, converting an upstream file is
not just content-stripping — it is **re-tokenization**. Every
`background: var(--ivory)` becomes `background: var(--bg)`, every
`color: var(--gray-800)` (or whatever that file happened to call slate)
becomes `color: var(--text)`, and so on for the full set of role
mappings. The 253 hardcoded hex literals found outside `:root` blocks
(section 4.2) get the same treatment: each literal is mapped to the
Tier 2 role it plays in context, then replaced with the `var()` call.

This re-tokenization step is the bulk of the implementation effort. It
cannot be done by search-and-replace on the hex value alone, because the
same hex value plays different roles in different places — `#3D3D3A`
might be body text in one spot and a border in another, and the mapping
depends on what the color is doing, not what it equals.

## 4. Template conversion

### 4.0 The 20 genres

One template per upstream file. This table is the authority for D1's
trigger matching and for the selection table in `SKILL.md`.

| Upstream file | Genre |
|---|---|
| 01-exploration-code-approaches.html | Three ways to solve one problem, side by side, trade-offs inline |
| 02-exploration-visual-designs.html | Several layout and palette options rendered live |
| 03-code-review-pr.html | Diff with margin notes, severity tags, jump links |
| 04-code-understanding.html | Module map: boxes and arrows, hot path highlighted, entry points |
| 05-design-system.html | Colors, type scale, spacing tokens as copyable swatches |
| 06-component-variants.html | Every size, state and intent of one component on one sheet |
| 07-prototype-animation.html | One transition in isolation, with duration and easing sliders |
| 08-prototype-interaction.html | Four linked screens, clickable flow |
| 09-slide-deck.html | Arrow-key slide deck in one file |
| 10-svg-illustrations.html | Inline SVG figure sheet for a blog post |
| 11-status-report.html | Weekly status: shipped, slipped, small chart |
| 12-incident-report.html | Post-mortem: timeline, log excerpts, follow-up checklist |
| 13-flowchart-diagram.html | Pipeline flowchart, click a step for detail |
| 14-research-feature-explainer.html | How a feature works: TL;DR, collapsible steps, tabbed snippets, FAQ |
| 15-research-concept-explainer.html | Concept explainer with live demo, comparison table, glossary |
| 16-implementation-plan.html | Milestones, data-flow diagram, inline mockups, risk table |
| 17-pr-writeup.html | Author's PR tour: motivation, before/after, file-by-file |
| 18-editor-triage-board.html | Drag tickets across Now/Next/Later/Cut, copy ordering as markdown |
| 19-editor-feature-flags.html | Grouped toggles, dependency warnings, copy-diff button |
| 20-editor-prompt-tuner.html | Editable template with variable slots, live re-render |

### 4.1 What "conversion" means (D2)

Content is stripped, but not to blank. A fully blank template loses the
pattern it exists to teach. The rule: collapse repeated sibling content
to one representative instance, marked with a comment stating the
repetition, e.g. `<!-- repeat per ticket -->`. Example:
`18-editor-triage-board.html` has thirty fictional tickets in the
upstream file; the template keeps one and drops the other twenty-nine,
with the comment marking where the other twenty-nine belong.

Genre-specific CSS and JS are kept intact, unabridged. Interactive logic
— slide-deck keyboard navigation, triage-board drag-and-drop, tab
switching, the prompt-tuner's live re-render — is expensive to re-derive
correctly and easy to get subtly wrong from a description. Keeping the
working implementation is cheaper and safer than regenerating it.

### 4.2 Effort by file

CSS dominates upstream: 40–75% of each file's lines sit inside
`<style>`. Example: `11-status-report.html` is 528 lines, 296 of them
`<style>`. Conversion effort tracks raw-hex count outside `:root`, since
each literal needs a manual role decision (section 3.3).

Counts below were measured with `lib/checks.py`, which scans `<style>`
blocks and color-bearing attributes only. An earlier pass used a bare
regex over the whole file and was wrong twice over: it counted
pull-request numbers such as `#4871` in `11-status-report.html` as
colors, and its `:root` stripping swallowed most of the stylesheet in
`16-implementation-plan.html`, reporting that file as having no colors
at all when it has 36.

Colors outside `:root`, per file:

| Count | Files |
|---|---|
| 0 | `06`, `08`, `20` |
| 2 | `01`, `07`, `12` |
| 4 | `02`, `14`, `15` |
| 5–6 | `19`, `09`, `17` |
| 7–12 | `04`, `13`, `18`, `03` |
| 17 | `05` |
| 29 | `11` |
| 36 | `16` |
| 97 | `10` |

Total 253 across the 20 files, drawn from 49 distinct values. Fourteen
of those recur three or more times and are mapped explicitly in
`references/conversion-rules.md`; the remaining 35 are one-offs —
gradient stops, tag tints, chart series — handled by an ordered
fallback procedure rather than a table.

- **Highest effort:** `10-svg-illustrations.html`, 97 colors, almost all
  SVG `fill` attributes, which sit outside the CSS cascade entirely and
  must be lifted into CSS classes.
- **Next:** `16-implementation-plan.html` (36) and `11-status-report.html`
  (29), both carrying inline chart and diagram colors.
- **Next highest:** `11-status-report.html` (37), `05-design-system.html`
  (30).

### 4.3 Conversion is agent work (D4)

A script cannot decide which sibling instance is representative, where a
repeat-block boundary falls, or which semantic role a given hex literal
plays. Regex-stripping hand-written HTML mangles it. So the work splits:

- **Deterministic bookkeeping** — diffing upstream, tracking blob SHAs,
  stamping the manifest — is script work (`scripts/update.sh`, section 6).
- **Semantic conversion** — stripping to one instance, re-tokenizing
  colors, writing the provenance header — is skill work, done by the
  agent under the written rules in `references/conversion-rules.md`
  (ingest mode, section 6).

### 4.4 Size

**Superseded 2026-08-16 by measurement.** This section projected
4,000–5,000 lines from 11,611 upstream. The converted set is 12,394
lines, of which 2,300 are the embedded token block (115 × 20) and about
600 are provenance headers, leaving 9,296 against 10,789 upstream.

The projection assumed content collapse would halve a file. It cannot.
Splitting the six longest templates against their sources shows where
the length actually sits:

| Part | Template vs upstream |
|---|---|
| Markup | 85–103% |
| CSS | 95–99% |
| JavaScript | 92–102% |

CSS and JavaScript are kept whole by rule 6 and by the global
constraints, so only markup and sample data can shrink — and in these
files the repetition was never in the markup to begin with. The 24
tickets in `18-editor-triage-board.html` live in a JavaScript data
array, so collapsing them to four moved the JS line count, not the
markup. Where markup did carry the repetition it did shrink:
`09-slide-deck.html` to 85%, `07-prototype-animation.html` to 88%.

A reading pass over the six longest templates on 2026-08-16 confirmed
every repeated unit is collapsed to between one and four instances, each
marked. No repeated content survived.

**There is no target line count.** A converted template is the length
its genre CSS and interaction logic make it. Rule 4 and the marker
comments are the guard against repeated content surviving; a line-count
band never was one, and a number nobody can hit is worse than none.

## 5. Repo layout

```
writing-standalone-html/          own git repo, matching the user's
                                   per-skill convention
  SKILL.md                        frontmatter + genre-to-template
                                   selection table + hard rules
  README.md
  CHANGELOG.md                    keepachangelog.com format
  references/
    design-system.css             two-tier tokens, light and dark
    conversion-rules.md           ingest procedure + hex-to-semantic-
                                   token mapping table
  templates/
    NN-<genre>.html               20 skeletons, each with a provenance
                                   header
    MANIFEST.json                 upstream commit + per-file blob SHA +
                                   conversion date
  scripts/
    update.sh                     drift check over the GitHub API
    upstream.sh                   borrow and return the ephemeral clone
    verify.sh                     mechanical template checks
  lib/                            Python stdlib helpers imported by the
                                   scripts: checks, manifest, github
  tests/
  .upstream/                      ephemeral --depth 1 clone, git-ignored,
                                   present only during an ingest run
```

Executables live in `scripts/`; importable modules live in `lib/`. Every
script resolves the repo root with `cd "$(dirname "$0")/.."`, so all
paths inside them stay relative to the skill directory regardless of
where the script is invoked from.

File purposes:

- `SKILL.md` — the entry point Claude Code reads to decide when this
  skill fires and which template to hand back for a given request.
- `references/design-system.css` — the canonical two-tier token file
  (section 3.2). Templates **embed** a verbatim copy of it inside their
  own `<style>` block. They must not link it: an external stylesheet
  would break the self-containment property in section 1 and fail
  verify check 2. The file is the single source of truth; the embedded
  copies are stamped from it and re-stamped whenever it changes.
- `references/conversion-rules.md` — the written procedure an agent
  follows in ingest mode: how to pick the representative sibling
  instance, how to map a given hex to a Tier 2 role, how to write the
  provenance header.
- `templates/NN-<genre>.html` — the 20 deliverables, one per genre from
  the table in section 4.0.
- `templates/MANIFEST.json` — machine-readable record tying every
  template back to the exact upstream blob it was converted from
  (schema in section 6.2).
- `scripts/update.sh` — deterministic drift checker over the GitHub API
  (section 6.1). Needs no local copy of upstream.
- `scripts/upstream.sh` — `fetch` borrows an ephemeral clone into `.upstream/`,
  `clean` deletes it (section 6.3).
- `scripts/verify.sh` — mechanical template validator (section 7).

**Provenance header.** Every template file opens with an HTML comment
recording: upstream repo URL, upstream commit SHA, source filename
upstream, and that source file's blob SHA at conversion time. This is
what makes `scripts/update.sh`'s drift detection possible — it diffs the
manifest's stored blob SHA against upstream's current blob SHA per file.

## 6. Update and maintenance flow

### 6.1 update.sh contract

Deterministic, no model involved, safe to run from cron. Needs no
local copy of upstream and touches nothing outside the skill folder.

1. Resolve upstream HEAD: `GET /repos/anthropics/html-effectiveness/
   commits?per_page=1` returns the current commit SHA.
2. Enumerate the tree: `GET /repos/anthropics/html-effectiveness/
   git/trees/<commit>` returns every path with its blob SHA. Keep the
   entries matching `NN-*.html`.
3. Enumerate from that response, never from the manifest. Reading the
   manifest's 20 known files instead would make a newly added upstream
   file invisible, which defeats the purpose.
4. Compare each blob SHA against the SHA recorded in
   `templates/MANIFEST.json`, matching on `files[].upstream_source`.
5. Print four lists: unchanged, changed upstream, new upstream (present
   at HEAD, absent from the manifest), removed upstream (present in the
   manifest, absent at HEAD).
6. Exit 1 when any list other than "unchanged" is non-empty. Exit 2
   when the check itself could not run — network failure, rate limit, a
   malformed response. The two codes must stay distinct so a wrapper can
   tell pending work from a broken checker.

The API returns real git blob SHAs, verified against a local clone:
`11-status-report.html` reads `764665143d3731ccb5e8978898bf7d7a5e46cc5f`
from both. So the comparison is identical to the one a local `git
ls-tree` would produce, without the clone.

Unauthenticated calls are limited to 60 per hour and this path spends
two. That suits a scheduled check; it does not suit tight polling.

`scripts/update.sh` never edits a template, and it never writes
`MANIFEST.json` either — including `checked_at`. Writing on a read path
would make a cron run dirty the git tree and produce spurious diffs.
`checked_at` is stamped by ingest mode alongside the rest of the
manifest. The deterministic, cron-safe half of the pipeline stays
strictly read-only; every write belongs to the semantic, agent-driven
half (D4).

### 6.2 MANIFEST.json schema

```json
{
  "upstream_repo": "anthropics/html-effectiveness",
  "upstream_commit": "58c305be97f47b26b678f2c07dec01d4242268ec",
  "checked_at": "2026-08-14T00:00:00Z",
  "files": [
    {
      "template": "11-status-report.html",
      "upstream_source": "11-status-report.html",
      "upstream_blob_sha": "764665143d3731ccb5e8978898bf7d7a5e46cc5f",
      "converted_at": "2026-08-14",
      "raw_hex_count_at_conversion": 29
    }
  ]
}
```

Fields:

- `upstream_repo`, `upstream_commit` — top-level pin used as the
  baseline for the next `scripts/update.sh` run. Full 40-character SHA, not the
  short form, so the pin stays unambiguous as upstream grows.
- `checked_at` — timestamp of the last ingest run. Written by ingest
  mode only; `scripts/update.sh` reads it and never updates it (section 6.1).
- `files[].template` — filename in `templates/`.
- `files[].upstream_source` — corresponding filename upstream (usually
  identical, kept separate in case of a rename).
- `files[].upstream_blob_sha` — the git blob SHA `scripts/update.sh` diffs
  against on every run.
- `files[].converted_at` — date this template was last (re)converted by
  the skill's ingest mode.
- `files[].raw_hex_count_at_conversion` — the upstream colour count
  outside `:root` this conversion had to resolve (29 for
  `11-status-report.html`), counted by `lib/checks.py`,
  recorded so effort is visible when a file is re-converted. It is a
  record of work done, not a health metric; the post-conversion count
  outside the token block must be 0, and verify check 3 is what
  enforces that.

### 6.3 Ingest mode

Runs when `scripts/update.sh` reports non-empty changed/new/removed lists.
Conversion needs file contents, which the API path deliberately does not
fetch, so ingest borrows a clone for the duration and gives it back.

1. `./scripts/upstream.sh fetch` clones upstream `--depth 1` into `.upstream/`
   inside the skill folder, prints the path and commit, and exits.
   `.upstream/` is git-ignored.
2. For each named file, the skill converts it following
   `references/conversion-rules.md`: strip repeated siblings to one
   marked instance (section 4.1), re-tokenize colors to Tier 2 roles
   (section 3.3), write the provenance header (section 5).
3. Removed-upstream files are flagged for a human decision — the
   template is not auto-deleted.
4. `MANIFEST.json` is stamped with the new blob SHAs, `converted_at`
   dates, `raw_hex_count_at_conversion` values, and `checked_at`.
5. `./scripts/upstream.sh clean` deletes `.upstream/`.

The clone is ephemeral by design (decision 0006). Creating it per run
costs about 860 KB and a few seconds, and removes the failure mode where
a stale local clone yields stale blob SHAs with full confidence. The
test suite fails while `.upstream/` exists, so an un-cleaned clone
cannot reach a commit.

## 7. Verification

`scripts/verify.sh` runs three mechanical checks against every template:

1. **Parses as HTML** — no malformed markup.
2. **Zero external references** — no CDN, no external CSS/JS/fonts/
   images, matching the upstream property this project inherits.
3. **Zero raw hex outside the embedded token block** — every color in a
   template's markup, genre CSS and SVG attributes resolves through a
   `var()` reference. Literal hex values are legal only inside the
   embedded copy of `design-system.css`, which is where Tier 1 has to
   define them. The check is therefore scoped: extract the token block,
   scan everything else, expect zero matches.

A fourth check needs the template rendered: it reads legibly in both
light and dark theme. It applies to templates that changed in the
current ingest run, not to the full set on every check.

**Amended 2026-08-16.** This section called the fourth check
unautomatable. Half of it is: `scripts/audit-contrast.js` runs in the
rendering harness the environment turned out to have and reports every
text node below WCAG AA against its own ground. It found a heading at
1.06:1 in `02-exploration-visual-designs.html` that a full-page
screenshot did not show, because near-black on near-black reads as
absent rather than as wrong. What stays unautomatable is the legibility
judgment the ratio cannot make — whether a colour carries the meaning
its role claims.

**Amended 2026-08-17.** The script took the ground from the nearest
ancestor that painted one, which reported a positioned child against a
fill it never touches — six phantom failures in
`07-prototype-animation.html`. The ground is now the nearest ancestor
that paints *and* contains the text box, and text crossing a ground's
edge is reported with `"straddles": true`. The lesson generalizes: an
automated check that over-reports gets read less carefully, so a false
positive costs as much as a miss in a tool a person reads by hand.

## 8. Constraints and open risks

- **Installation constraint (D5).** The agent's sandbox cannot write to
  `/home/mkm/.claude/skills/` — that file system is read-only,
  confirmed by direct attempt. The skill is built at
  `/home/data/home-dir/dev/0_TEMP/writing-standalone-html/` and the user
  installs it by moving or symlinking that directory into
  `~/.claude/skills/`. This is a manual step outside the skill's own
  automation.

- **Detection needs the network and a quota.** `scripts/update.sh` spends two
  unauthenticated API calls against a limit of 60 per hour. A rate
  limit, an outage or a malformed response exits 2, never 1, so a
  wrapper never mistakes a broken checker for a clean result. Anything
  polling more than a few times an hour needs an authenticated token.

- **Upstream restructuring risk.** `scripts/update.sh` detects a changed blob
  SHA but not the *size* of the change. If upstream heavily restructures
  a file — new layout, new interaction model, not just a copy edit —
  re-conversion is effectively a rewrite, not a patch. The manifest
  records this as "changed upstream" either way; the human or agent
  running ingest mode must open the diff to know which case they are in.

- **One-off colors outstrip any table.** Of the 49 distinct values
  outside `:root`, only 14 recur three or more times. The remaining 35
  are gradient stops, tag tints and chart series appearing once or
  twice. Enumerating them would produce a list, not a rule, so
  `references/conversion-rules.md` gives an ordered fallback instead:
  collapse near-duplicates, express tints with `color-mix`, assign
  series colors by role, escalate the rest. The clearest near-duplicate
  is `#b04a4a` (3 uses), one digit from rust `#b04a3f`; upstream's own
  `#b85c3e` is likewise a deep clay it defines as `--clay-d` in three
  files.

- **Dark-layer maintenance cost.** Upstream carries no dark mode and
  will not maintain one. Every future upstream change that touches color
  usage — a new component, a new state color — needs a corresponding
  dark-mode judgment call on this project's side, indefinitely. Upstream
  drift detection (`scripts/update.sh`) does not know whether a change affects
  color usage; every "changed upstream" file must be checked for that
  regardless of what else changed.

## 9. Decisions log

Each decision has its own record under `docs/decisions/`, carrying the
context, consequences and the alternatives rejected. Those records are
authoritative; this list is an index.

| ID | Decision | Record |
|----|----------|--------|
| D1 | Trigger only on the 20 named genres | `0001 - Narrow the trigger to the twenty known genres.md` |
| D2 | Templates keep a skeleton plus one worked instance | `0002 - Keep a skeleton plus one worked instance.md` |
| D3 | Two-tier tokens; we add and maintain dark mode | `0003 - Adopt a two-tier token architecture and maintain dark mode.md` |
| D4 | `scripts/update.sh` does bookkeeping, ingest mode does semantics | `0004 - Split conversion between script and agent.md` |
| D5 | Build outside `~/.claude/skills/`, install by hand | `0005 - Install the skill manually into the skills directory.md` |
| D6 | Detect drift over the GitHub API; clone only during ingest | `0006 - Detect drift over the API and clone only on demand.md` |
