# Conversion rules

How an upstream file becomes a template. Follow these in order. Every
step is mechanical except where it says **judgment**, and every judgment
call gets recorded in the file's provenance header.

Borrow the sources first, and give them back when done:

    ./scripts/upstream.sh fetch
    # ... convert ...
    ./scripts/upstream.sh clean

## 1. Stamp the provenance header

First lines of the file, before `<!doctype html>`:

    <!--
      Template derived from anthropics/html-effectiveness
      upstream:  https://github.com/anthropics/html-effectiveness
      commit:    <full 40-char SHA>
      source:    <NN-name.html>
      blob:      <40-char blob SHA of the source file at that commit>
      converted: <YYYY-MM-DD>
      notes:     <judgment calls made, or "none">
    -->

Get the blob SHA with:

    git -C .upstream rev-parse HEAD:<NN-name.html>

## 2. Replace the token block

Delete the file's `:root { ... }` declaration entirely. Paste
`references/design-system.css` verbatim in its place, sentinels
included. Do not merge upstream's token names into it — they are being
replaced, not extended.

## 3. Re-tokenize every color

Replace each color with its Tier 2 role. Two sources to cover:
`var(--upstream-name)` references and raw hex literals, including SVG
`fill`, `stroke` and `stop-color` attributes.

**Map by the job the color does, never by its value.** The same hex is
body text in one place and a border in another.

### The palette

These eleven values account for most of the work. Counts are total
occurrences across all 20 upstream files at `58c305b`.

| Upstream color | Count | Role in context | Token |
|---|---|---|---|
| `#faf9f5` ivory | 34 | page background | `var(--bg)` |
| `#ffffff` white | 44 | raised panel, card, sheet | `var(--surface)` |
| `#f0eee6` gray-100/150/50 | 36 | sunken well, table stripe | `var(--surface-sunken)` |
| `#141413` slate | 35 | body text, headings | `var(--text)` |
| `#3d3d3a` gray-700/800 | 44 | secondary text, captions | `var(--text-muted)` |
| `#87867f` gray-500 | 81 | tertiary text, axis label | `var(--text-muted)` |
| `#d1cfc5` gray-300/200 | 34 | rules, borders, dividers | `var(--border)` |
| `#e3dacc` oat | 33 | tinted band, tag background | `var(--surface-sunken)` |
| `#d97757` clay | 43 | links, active state, emphasis | `var(--accent)` |
| `#788c5d` olive | 31 | success, passing, shipped | `var(--ok)` |
| `#b04a3f` rust | 10 | error, failure, blocker | `var(--danger)` |

Two values share `var(--text-muted)`: upstream uses `#3d3d3a` and
`#87867f` for the same job at different weights. Collapsing them is
intentional. If one view genuinely needs two muted levels, that is an
escalation — record it in the header notes.

`#e3dacc` maps to `var(--surface-sunken)` because no tint role exists.
If an oat band must stay visually distinct from a code block in the
same view, use Tier 1 `var(--oat)` and note that the element is
theme-invariant by choice.

**`--accent` and `--ok` are not upstream's clay and olive.** They
resolve to `--clay-deep` and `--olive-deep`, because upstream's values
reach only 2.96:1 and 3.49:1 on ivory and these roles are used as text.
Upstream reached the same conclusion independently: three files define
their own `--clay-d: #b85c3e` for exactly this. Map to the role, not to
the raw name, and contrast is handled for you.

Both variants are measured against `--surface-sunken`, the darkest of
the three light grounds. That is the pairing that binds: a role which
clears 4.5:1 there clears it on `--bg` and `--surface` too. When a new
text colour has to be judged, judge it on the sunken panel, not on the
page background.

### Code blocks

Code blocks are theme-invariant: they stay dark in both themes, the way
an editor does, which is what upstream already does. Use the code roles
and do not convert these to Tier 2:

| Upstream color | Role | Token |
|---|---|---|
| `#141413` as a code ground | code block background | `var(--code-bg)` |
| `#e8e6de` | code foreground | `var(--code-text)` |
| `#b8b6ac` | context line, dimmed code | `var(--code-muted)` |
| `#c9b98a` | keyword, identifier | `var(--code-kw)` |
| `#a8bc8c` | string literal | `var(--code-str)` |

Some files colour more syntax classes than there are code roles.
`01-exploration-code-approaches.html` paints keywords and identifiers
apart, and the roles carry one colour for both. When that happens, take
the extra colour from Tier 1 — `var(--clay)`, `var(--olive)` — and not
from Tier 2. The panel is theme-invariant by design, so a Tier 2 role
would flip out from under a ground that never moves. Record it in the
header notes.

Never reach for `var(--accent)` or `var(--ok)` inside a code panel.
They resolve to the deep variants tuned for ivory, and on a near-black
ground they go muddy.

### Everything else

Upstream carries roughly 50 further one-off values: gradient stops,
tag tints such as `#f5e2d8`, chart series colors, and near-duplicates
of palette members. There is no table for these, because a table of
one-offs is a list, not a rule. Apply this order:

1. **Is it a near-duplicate of a palette member?** Collapse it. The
   clearest case is `#b04a4a` (3 occurrences), one digit from rust
   `#b04a3f` — map to `var(--danger)` and note the collapse. Same for
   `#b85c3e`, which is upstream's own deep clay: map to `var(--accent)`.
2. **Is it a tint of a palette hue used as a background?** Use
   `var(--surface-sunken)`, or the role at reduced opacity via
   `color-mix(in srgb, var(--accent) 12%, var(--surface))`. Prefer
   `color-mix` when the tint must track the accent.
3. **Is it a chart or diagram series color?** These carry data meaning.
   Use `var(--accent)`, `var(--ok)`, `var(--danger)` in that order for
   up to three series. Beyond three, stop and escalate rather than
   inventing a fourth hue.
4. **Anything left** is a judgment call. Pick the nearest role by job,
   and record the decision in the header notes.

### Names upstream also uses

Upstream files define their own tokens, and some of the names collide
with ours while meaning something else. `11-status-report.html`
declares `--border: 1.5px solid var(--gray-300)` — a whole shorthand,
where ours is a colour. Every `border: var(--border)` in that file had
to become `border: var(--border-width) solid var(--border)`.

Before re-tokenizing, read the file's own `:root` and compare its names
against ours. A name that means something different is worse than a
name that is missing, because the file keeps working and renders wrong.

### Colours the checker cannot see

`scripts/verify.sh` reads `<style>` blocks and colour-bearing
attributes, and inside them it catches hex, `rgb()`, `hsl()` and the
named colours. Two kinds of colour still slip past it, and both get
re-tokenized:

1. A colour inside a `<script>` string. `06-component-variants.html`
   sets `--card-shadow` from JavaScript, and the literal it wrote left
   the shadow pinned to the light theme the moment a reader touched the
   control. **Rule 6 protects interaction logic, not colour.** A string
   holding a colour is colour work, and rewriting it is not a refactor.

2. A colour in an inline `style` attribute that the regex reaches but
   the eye skips. Check the swatches and chips.

A translucent overlay converts with `color-mix`, which keeps the
mixture tied to a token and passes the checker:

    border-top: 1px solid color-mix(in srgb, var(--text) 8%, transparent);

### Shape tokens

The token block carries three shape values, and they match upstream's
own numbers exactly. Use them wherever the number already matches, so a
later change to the house radius reaches every template:

| Upstream value | Token |
|---|---|
| `12px` radius on a panel, card or code block | `var(--radius-panel)` |
| `8px` radius on a row, chip, badge or table | `var(--radius-row)` |
| `1.5px` border width | `var(--border-width)` |

Leave any other number alone. A `4px` radius on inline code has no
token, and inventing one to cover a single use is how a token system
turns into a second stylesheet.

## 4. Collapse repeated content

Find every set of repeated sibling elements — ticket rows, timeline
entries, flag toggles, slides, swatches, table rows. Keep exactly one.
Delete the rest. Mark the survivor with a comment on the line above the
element it describes, naming the unit of repetition:

    <!-- repeat per ticket -->

**Leave the layout CSS alone.** A three-column grid keeps
`repeat(3, minmax(0, 1fr))` after two of its three children are
deleted. The retained instance is meant to sit in the real layout, and
the page that gets generated from the template fills the other slots.
Rewriting the grid to match the sample would hand every generated page
the wrong layout.

**Judgment:** pick the instance that exercises the most structure. A
ticket row carrying a label, an assignee and a due date teaches more
than a bare one. If states differ meaningfully — a passing row and a
failing row look different — keep one of each and mark both.

**Keep two when one cannot show the pattern.** A comparison needs two
cards. A slide deck needs two slides for the keyboard navigation to
have a destination. A dependency warning needs a prerequisite to point
at. A module map needs two boxes and the arrow between them.

## 5. Strip the fiction

No "Acme" string survives. Replace remaining sample text with short
neutral placeholders that name their slot: "Section title", "One-line
summary", "2026-01-01". Keep them short — a template is read for
structure, not for prose.

Numbers in charts stay, because a chart with no data has no shape.
Round them to obviously-fake values (10, 25, 40) so they are never
mistaken for real figures.

## 6. Keep the machinery

Genre CSS and JavaScript are kept whole. Do not simplify, refactor or
"clean up" interaction logic. Keyboard navigation, drag-and-drop, tab
switching and live re-render are the expensive parts and the reason the
template exists.

The only permitted JS edit is shrinking an inline data array to match
the single retained instance from step 4.

## 7. Verify

    ./scripts/verify.sh templates/<NN-name>.html

Six checks must pass: the file parses, it holds no external reference,
its token block matches `references/design-system.css` exactly, no raw
colour survives outside that block, no script writes a raw colour into
CSS, and no upstream brand name survives anywhere.

Two checks are left, and both need the file rendered. Run
`scripts/audit-contrast.js` against it in each theme — an empty array is
the only pass — and then look at it in each theme yourself. The audit
catches a colour mapped to a role that inverts; the look catches what a
ratio cannot say.

Note what the colour check does and does not scan: it looks inside
`<style>` blocks and color-bearing attributes only, and it skips HTML
comments. Element text is excluded on purpose, because `#4871` in
`11-status-report.html` is a pull-request number, not a color, and
comments are excluded because the provenance header quotes the colours
it replaced.

The script check is narrower still. It triggers on the sink, not on the
string: a colour only fails when it reaches CSS through `style`,
`cssText`, `setProperty` or `setAttribute("style", ...)`. A colour in a
data attribute, a label or a chart legend is not a defect. When the
check fires, do not reach for a token inside the string — put the colour
in a CSS class and let the script toggle the class. `03` and `06` are
the worked examples.

A token-block failure is repaired by `./scripts/stamp.sh <file>`, never
by editing the block in the template.
