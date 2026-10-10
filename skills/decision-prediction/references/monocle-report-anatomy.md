# Monocle Report — Output Artifact Anatomy

Historical structural reference for the current cloud reading edition; current report policy takes precedence. The analytical shape of a `Decision > Prediction` single-stock output artifact. Design tokens live in
`references/DESIGN-Monocle.md` (colors, Plantin/Helvetica type, spacing).
Working HTML template: `templates/stock-report/Stock-Report-Web-Template.html`.

No external deps. Inline SVG only. Single self-contained HTML file.

## Skeleton (top → bottom)

1. **Utility bar** (sticky, `.utility`): left `DECISION > PREDICTION` + `EVIDENCE · SIZING · SURVIVABILITY`,
   right `SHARE` button (yellow `#ffc500` bg, black text, charcoal 1px border).
2. **Masthead** (`.masthead`): `.co` (company common name, 52px Plantin 700, -0.02em), `.tick` (ticker metadata,
   22px, caption gray), `.sub` (uppercase tracked 12px: "Evidence dossier · Decision > Prediction · No. N · Month Year").
3. **Nav** (`.nav`): section links, uppercase Plantin 12px, `border-right` separators, overflow-x auto.
4. **Quote/cover** (`.quote`): `.kicker` ("Cover — Company · Exchange: TICKER"), `h1` two-line compound headline,
   `.deck` (personalized: shares/cost/return/%), `.meta` (byline: "By the research agent · Personalized for <name> · N screenshots
   · N Polymarket pages · N call expiries · time range"), `.price-block` (`.price` 64px + `.cents` 36px, `.chg`, `.asof`).
5. **grid3** (`.grid3`): `1.5fr | 1fr | 300px`, collapses to 1fr under 1000px. Left = `.lead` (sections), right = `.sidebar`.
6. **Footer** (`.footer`): `TICKER · Company · Decision > Prediction · date` | token-cost file names.

## The 13 analytical areas (cloud reading edition may map their order)

| # | id | Kicker label | Content |
|---|---|---|---|
| 1 | `position` | Folio — Optional supplied context | cream card; `shares × price → $` h2; position table; 1Y price line SVG (MA overlay + cost-basis ref dashed yellow); evidence-label callout |
| 2 | `frameworks` | Porter · Helmer · Canvas | Porter 5-forces table + Helmer 7-powers table (`.cols2`), BMC card |
| 3 | `bayes` | Bayesian Update | Polymarket board table (odds/fair-odds/what-it-says) + prior/likelihood/posterior cards |
| 4 | `sharpe` | Risk — Sharpe · Kelly · Survivability | return/risk/risk-adjusted atoms table (formula + result) + Kelly table (edge→full→adj→frac→cap) + Kelly bars SVG |
| 5 | `engines` | Engines — Capital Decision Lab v1 | formula spec (`--what engines calculate`) + "Did we run these?" provenance list |
| 6 | `convexity` | Convexity — Upside Asymmetry | 4-scenario payoff table (Bear/Base/Bull/Moonshot) + ratios + scenario bars SVG |
| 7 | `simulation` | Simulation — Seeded Monte Carlo | seeded-normal params table + P5/P50/P95/mean terminal bars SVG |
| 8 | `margin` | Margin — Hypothetical stress | supplied balances table + stress bars SVG (−10/−20/−30% vs maintenance) + educational limitations callout |
| 9 | `options` | Options — chain pricing | near-dated + ~6wk chains (strike/breakeven/to-BE/ask) + hypothetical barbell comparison |
| 10 | `barbell` | Barbell — Compounders \| Convexity | left compounders table + right convexity table + hypothetical alternatives card |
| 11 | `dlc` | DLC — Simulated commentary | 8 lenses, each: third-person simulated framework summary + `.note` rule; no attributed invented quotation; disclaimed "not advice" |
| 12 | `metrology` | Metrology — measured cost | token/cost tables + cost bars SVG (log scale) |
| 13 | `verdict` | Verdict — Decision Receipt | badge `Research status: X`, confidence, risk tags; research implication headline; trigger-to-change table; evidence stack; TL;DR |

## Sidebar (`.sidebar`, 300px)

1. **Timestamped evidence feed** (`.card.gray`): black header strip ("Evidence feed"), timed entries (HH:MM — event).
2. **Evidence Stack — at a glance**: table of sources with `✓ measured` vs `○ estimated`.
3. **Portfolio donut** (SVG): center derived only from authorized confirmed inputs, or `unavailable`; no preset percentage; legend below.
4. **Discipline** card: `border-left` charcoal; compounding-over-excitement note.

## Inline SVG chart functions (no external libs)

- `line(id, data, {ref, ma})` — polyline + dashed gridlines + optional MA polyline (desk-blue) + cost-basis ref (yellow dashed).
- `bars(id, rows)` — zero-baseline bar chart; `r.c`: `0`=gray `#d9d9d9`, `1`=black, `2`=desk-blue `#64d5ff`.
- `donut(id, segments)` — donut with center label.

## Conventions

- **Evidence labels inline**: `measured` / `calculated` / `modeled` / `forecast` / `narrative` / `unknown` via
  `.callout` blocks and `.tag`. Never let narrative masquerade as measured.
- **Ratios are decimals** (0.56 = 56%). Formulas in `.mono`.
- **Tables**: uppercase `caption`; first column left-aligned, rest right; `.you` row = yellow `inset 3px 0 0` left border.
- **`unavailable`** with reason is correct behavior — never invent a number for an invalid domain.
- **Callout for risk**: "If the downside breaks the portfolio, the upside is irrelevant."


Current full-acceptance additions: all nine BMC blocks, all seven Powers, separate Page robustness note, common-name masthead, source/audit navigation before strategy and actual generated PNG sketchnote through one named simulated lens with Dan Roam 6×5. Preserve PNG hash, dimensions, alt text, full text and host inspection receipt. Browser review is a separate gate.
