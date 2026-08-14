# Design spec: writing-standalone-html skill

Status: draft
Date: 2026-08-14

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
(https://github.com/anthropics/html-effectiveness), MIT licensed, cloned
locally at `/home/data/home-dir/dev/0_TEMP/html-effectiveness`, commit
`58c305be97f47b26b678f2c07dec01d4242268ec`.

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
  `--surface`, `--text`, `--text-muted`, `--border`, `--accent`, `--ok`,
  `--warn`, `--danger`. Only Tier 2 is redefined between light and dark.

Illustrative shape (full definitions live in
`references/design-system.css`):

```css
:root {
  /* Tier 1 — raw palette, fixed */
  --ivory: #FAF9F5;
  --slate: #141413;
  --clay:  #D97757;
  --oat:   #E3DACC;
  --olive: #788C5D;
  --rust:  #B04A3F;
  --gray-100: #F0EEE6;
  --gray-300: #D1CFC5;
  --gray-500: #87867F;
  --gray-700: #3D3D3A;

  /* Tier 2 — semantic roles, light (default) */
  --bg:          var(--ivory);
  --surface:     #FFFFFF;
  --text:        var(--slate);
  --text-muted:  var(--gray-700);
  --border:      var(--gray-300);
  --accent:      var(--clay);
  --ok:          var(--olive);
  --warn:        var(--clay);
  --danger:      var(--rust);
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg:         var(--slate);
    --surface:    #1E1E1C;
    --text:       var(--ivory);
    --text-muted: var(--gray-300);
    --border:     var(--gray-700);
    /* --accent, --ok, --warn, --danger stay legible on dark; retuned
       per-value where contrast requires it, not blanket-inherited */
  }
}
```

Templates reference Tier 2 exclusively for anything that must adapt —
backgrounds, text, borders, surfaces. Tier 1 stays available for
one-off decorative uses that are intentionally theme-invariant.

### 3.3 Consequence for conversion

Because templates must use Tier 2 tokens, converting an upstream file is
not just content-stripping — it is **re-tokenization**. Every
`background: var(--ivory)` becomes `background: var(--bg)`, every
`color: var(--gray-800)` (or whatever that file happened to call slate)
becomes `color: var(--text)`, and so on for the full set of role
mappings. The ~270 hardcoded hex literals found outside `:root` blocks
(section 4.1) get the same treatment: each literal is mapped to the
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
each literal needs a manual role decision (section 3.3):

- **Zero raw hex outside `:root` — the easy files:** `01`, `02`, `06`,
  `08`, `16`, `20`. These already reference `:root` tokens throughout,
  so conversion is close to a straight token rename.
- **Highest effort:** `10-svg-illustrations.html`, 105 raw hex
  occurrences — almost all SVG `fill` attributes, which sit outside the
  CSS cascade entirely and must be re-tokenized attribute by attribute
  or lifted into CSS classes.
- **Next highest:** `11-status-report.html` (37), `05-design-system.html`
  (30).

### 4.3 Conversion is agent work (D4)

A script cannot decide which sibling instance is representative, where a
repeat-block boundary falls, or which semantic role a given hex literal
plays. Regex-stripping hand-written HTML mangles it. So the work splits:

- **Deterministic bookkeeping** — diffing upstream, tracking blob SHAs,
  stamping the manifest — is script work (`update.sh`, section 6).
- **Semantic conversion** — stripping to one instance, re-tokenizing
  colors, writing the provenance header — is skill work, done by the
  agent under the written rules in `references/conversion-rules.md`
  (ingest mode, section 6).

### 4.4 Size estimate

11,611 upstream lines are expected to become roughly 4,000–5,000 across
the 20 templates. This is an estimate derived from the CSS-to-content
ratio (CSS survives conversion near-intact; repeated content does not),
not a measurement — it will be checked against the actual converted
line count once conversion runs.

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
  update.sh
  verify.sh
```

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
- `update.sh` — deterministic drift checker (section 6.1).
- `verify.sh` — mechanical template validator (section 7).

**Provenance header.** Every template file opens with an HTML comment
recording: upstream repo URL, upstream commit SHA, source filename
upstream, and that source file's blob SHA at conversion time. This is
what makes `update.sh`'s drift detection possible — it diffs the
manifest's stored blob SHA against upstream's current blob SHA per file.

## 6. Update and maintenance flow

### 6.1 update.sh contract

Deterministic, no model involved, safe to run from cron.

1. Fetch upstream `anthropics/html-effectiveness` at its current HEAD.
2. Enumerate every `NN-*.html` at that HEAD — not the 20 recorded in
   the manifest. Enumerating the manifest instead would make a newly
   added upstream file invisible, which defeats the purpose.
3. Compare each file's current blob SHA against the SHA recorded in
   `templates/MANIFEST.json`, matching on `files[].upstream_source`.
4. Print four lists: unchanged, changed upstream, new upstream (present
   at HEAD, absent from the manifest), removed upstream (present in the
   manifest, absent at HEAD).
5. Exit non-zero when any list other than "unchanged" is non-empty
   (work is pending).

`update.sh` never edits a template, and it never writes
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
      "raw_hex_count_at_conversion": 37
    }
  ]
}
```

Fields:

- `upstream_repo`, `upstream_commit` — top-level pin used as the
  baseline for the next `update.sh` run. Full 40-character SHA, not the
  short form, so the pin stays unambiguous as upstream grows.
- `checked_at` — timestamp of the last ingest run. Written by ingest
  mode only; `update.sh` reads it and never updates it (section 6.1).
- `files[].template` — filename in `templates/`.
- `files[].upstream_source` — corresponding filename upstream (usually
  identical, kept separate in case of a rename).
- `files[].upstream_blob_sha` — the git blob SHA `update.sh` diffs
  against on every run.
- `files[].converted_at` — date this template was last (re)converted by
  the skill's ingest mode.
- `files[].raw_hex_count_at_conversion` — the upstream raw-hex count
  this conversion had to resolve (37 for `11-status-report.html`),
  recorded so effort is visible when a file is re-converted. It is a
  record of work done, not a health metric; the post-conversion count
  outside the token block must be 0, and verify check 3 is what
  enforces that.

### 6.3 Ingest mode

Runs when `update.sh` reports non-empty changed/new/removed lists.

1. For each named file, the skill converts it following
   `references/conversion-rules.md`: strip repeated siblings to one
   marked instance (section 4.1), re-tokenize colors to Tier 2 roles
   (section 3.3), write the provenance header (section 5).
2. Removed-upstream files are flagged for a human decision — the
   template is not auto-deleted.
3. On completion, `MANIFEST.json` is stamped with the new blob SHAs,
   `converted_at` dates, and `raw_hex_count_at_conversion` values.

## 7. Verification

`verify.sh` runs three mechanical checks against every template:

1. **Parses as HTML** — no malformed markup.
2. **Zero external references** — no CDN, no external CSS/JS/fonts/
   images, matching the upstream property this project inherits.
3. **Zero raw hex outside the embedded token block** — every color in a
   template's markup, genre CSS and SVG attributes resolves through a
   `var()` reference. Literal hex values are legal only inside the
   embedded copy of `design-system.css`, which is where Tier 1 has to
   define them. The check is therefore scoped: extract the token block,
   scan everything else, expect zero matches.

A fourth check is manual: the template renders legibly in both light
and dark theme. This cannot be automated without a rendering harness and
a legibility judgment, so it applies only to templates that changed in
the current ingest run — not to the full set on every check.

## 8. Constraints and open risks

- **Installation constraint (D5).** The agent's sandbox cannot write to
  `/home/mkm/.claude/skills/` — that file system is read-only,
  confirmed by direct attempt. The skill is built at
  `/home/data/home-dir/dev/0_TEMP/writing-standalone-html/` and the user
  installs it by moving or symlinking that directory into
  `~/.claude/skills/`. This is a manual step outside the skill's own
  automation.

- **Upstream restructuring risk.** `update.sh` detects a changed blob
  SHA but not the *size* of the change. If upstream heavily restructures
  a file — new layout, new interaction model, not just a copy edit —
  re-conversion is effectively a rewrite, not a patch. The manifest
  records this as "changed upstream" either way; the human or agent
  running ingest mode must open the diff to know which case they are in.

- **The `#B04A4A` stray.** Of the ~270 raw hex literals outside
  `:root`, 11 of 12 distinct values are already palette members written
  literally. The twelfth, `#B04A4A` (3 occurrences), is a near-duplicate
  of rust `#B04A3F` — one hex digit off. Conversion must decide, file by
  file, whether this is a typo that should collapse into `--rust` or an
  intentional near-rust variant that deserves its own Tier 1 token. This
  is a judgment call, not a mechanical mapping, and conversion-rules.md
  should record the decision made for each occurrence.

- **Dark-layer maintenance cost.** Upstream carries no dark mode and
  will not maintain one. Every future upstream change that touches color
  usage — a new component, a new state color — needs a corresponding
  dark-mode judgment call on this project's side, indefinitely. Upstream
  drift detection (`update.sh`) does not know whether a change affects
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
| D4 | `update.sh` does bookkeeping, ingest mode does semantics | `0004 - Split conversion between script and agent.md` |
| D5 | Build outside `~/.claude/skills/`, install by hand | `0005 - Install the skill manually into the skills directory.md` |
