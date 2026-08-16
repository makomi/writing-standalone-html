---
name: writing-standalone-html
description: Use when producing a self-contained HTML page for one of these document genres — weekly status report, incident post-mortem, implementation plan, PR write-up or annotated code review, module map, feature or concept explainer, flowchart, slide deck, design system sheet, component variant sheet, animation or interaction prototype, SVG figure sheet, code-approach comparison, or a small single-purpose editing UI such as a triage board, feature-flag panel or prompt tuner. Supplies a house template with a shared light and dark token system. Not for app UI, marketing pages, or general web development — those stay with frontend-design.
---

# Writing standalone HTML

## What this gives you

Twenty templates, one per document genre, each a self-contained page:
no build step, no dependency, no external reference. All share one
two-tier token system that works in light and dark.

Templates are **inputs to generation, not finished pages**. Each keeps
one worked instance of every repeating pattern, marked with a comment
such as `<!-- repeat per ticket -->`. Replace the instance; do not ship
it.

## Selecting a template

| You are producing | Template |
|---|---|
| Comparison of two or more ways to solve a problem | `01-exploration-code-approaches.html` |
| Several layout or palette directions, rendered live | `02-exploration-visual-designs.html` |
| An annotated diff or code review | `03-code-review-pr.html` |
| A map of an unfamiliar module or package | `04-code-understanding.html` |
| A design system: colors, type scale, spacing | `05-design-system.html` |
| Every size and state of one component | `06-component-variants.html` |
| An animation tuned in isolation | `07-prototype-animation.html` |
| A clickable multi-screen flow | `08-prototype-interaction.html` |
| A slide deck | `09-slide-deck.html` |
| A sheet of inline SVG figures | `10-svg-illustrations.html` |
| A weekly or sprint status report | `11-status-report.html` |
| An incident post-mortem | `12-incident-report.html` |
| A pipeline or process flowchart | `13-flowchart-diagram.html` |
| How a feature works in this repo | `14-research-feature-explainer.html` |
| A concept taught with a live demo | `15-research-concept-explainer.html` |
| An implementation plan with milestones and risks | `16-implementation-plan.html` |
| A PR write-up for reviewers | `17-pr-writeup.html` |
| A ticket triage board | `18-editor-triage-board.html` |
| A feature-flag editor | `19-editor-feature-flags.html` |
| A prompt tuner with live preview | `20-editor-prompt-tuner.html` |

If nothing matches, this skill does not apply. Say so and write the
page without a template rather than forcing a bad fit.

## Using a template

1. Read the whole file from `templates/`. Start from it — do not write a
   page from scratch and paste the tokens in.
2. Delete the provenance header comment at the top. It records where the
   template came from and means nothing in a finished page.
3. Fill in the structure. Every marked instance becomes real content,
   repeated as many times as the material needs.
4. Delete any section the document does not need. A template offers more
   structure than most pages use.
5. Verify, then hand it over.

## Rules

1. **Copy the token block verbatim.** It sits between
   `/* TOKENS:BEGIN */` and `/* TOKENS:END */`. Never edit it inside a
   generated page, and never link it as an external stylesheet.
2. **Never invent a color.** Every color comes from a token in that
   block. The tables below list all of them.
3. **Stay self-contained.** No CDN, no external font, no remote image.
   Embed images as data URIs or draw them as inline SVG.
4. **Replace every worked instance.** The retained sample is a shape to
   follow, not content to ship. No placeholder text survives.
5. **Keep the machinery.** Interaction logic in the template works.
   Do not rewrite it.
6. **Verify before handing it over.** Run `./scripts/verify.sh <file>`
   from the skill directory.

## The tokens

Tier 2 semantic roles carry every theme-dependent color. These are the
ones to reach for:

| Token | Use |
|---|---|
| `--bg` | The page |
| `--surface` | A raised panel, card or sheet |
| `--surface-sunken` | A well, an inset, a table stripe |
| `--text` | Body text and headings |
| `--text-muted` | Captions, labels, secondary text |
| `--border` | A decorative hairline: a row rule, a panel edge |
| `--border-strong` | An edge that conveys state: an input, a toggle, a focus ring |
| `--accent` | Links, active state, primary emphasis |
| `--ok` | Passing, shipped, healthy |
| `--warn` | Caution |
| `--danger` | Error, failure, blocker |

Reach for `--border-strong` whenever the edge is the affordance;
`--border` has no contrast floor and can disappear against the page.
`--warn` and `--accent` resolve to the same clay on purpose — a warning
that sits next to a link is told apart by its shape, not its hue.

Code blocks stay dark in both themes, the way an editor does. They have
their own roles, which are deliberately theme-invariant:

| Token | Use |
|---|---|
| `--code-bg` | The code block ground |
| `--code-text` | Code |
| `--code-muted` | Comments, line numbers |
| `--code-kw` | Keywords |
| `--code-str` | Strings |

Type and shape come from tokens too: `--serif`, `--sans`, `--mono`,
`--radius-panel`, `--radius-row`, `--border-width`.

Tier 1 raw names — `--ivory`, `--slate`, `--clay`, `--oat`, `--olive`,
`--rust`, the grays — are only for something deliberately
theme-invariant, such as a swatch that displays a color as content.
Everything else uses Tier 2.

## Themes

A page follows the reader's system setting on its own. To pin one theme,
set the attribute on the root element:

```html
<html lang="en" data-theme="dark">
```

`data-theme="light"` pins the light theme even for a reader whose system
asks for dark. Leave the attribute off unless the page has a reason to
override the reader.

## Updating the templates

`./scripts/update.sh` reports upstream drift by reading blob SHAs from
the GitHub API. It needs no local copy of upstream, is read-only, and is
safe to run unattended. Exit 1 means work is pending; exit 2 means the
check itself could not run.

When it reports work:

    ./scripts/upstream.sh fetch     # borrow a depth-1 clone at .upstream/
    # convert per references/conversion-rules.md, stamp MANIFEST.json
    ./scripts/upstream.sh clean     # give it back

`.upstream/` is git-ignored and must not survive the run.

## Provenance

Templates derive from `anthropics/html-effectiveness` (MIT), pinned per
file in `templates/MANIFEST.json`. All upstream sample data was
fictional and has been removed.
