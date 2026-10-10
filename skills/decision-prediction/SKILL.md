---
name: decision-prediction
description: Evidence-led educational stock research using the bundled deterministic engine and cloud report workflow.
---
# Decision ≥ Prediction

Use OAI dot as the primary cloud workflow; Muse/Grok mappings are secondary and unverified. Only use capabilities actually exposed by the current host. No native installation or provider integration is implied by this skill file.

## Evidence and inputs

Never invent financial facts or claim account access. Public-company research needs no portfolio. Optional holdings, balances, screenshots or CSVs must be explicitly supplied through an authorized private destination. Preserve source, publication/reference/retrieval times, raw-file hash, units, confidence and limitations. Screenshots are Observed · unconfirmed until actually confirmed. Label every material metric Measured, Calculated, Modeled or Forecasted; assumed Python results remain Modeled.

## Workflow

1. Inspect portable.py doctor and identify unavailable host tools.
2. Preserve supplied evidence and pending assumptions. Source research uses actual host tools only; source/API examples are not implemented integrations.
3. Use portable.py analyze/compare with --fixture or an explicit --data-dir and a contained relative --file. Validate schemas before calculations.
4. Retain calculation inputs, code hashes, formulas, raw outputs, seeds, and provenance. Do not alter assumptions silently.
5. Apply thesis-specific Bayesian sensitivity rules only to genuinely verified evidence. No user verification is manufactured by an imported JSON label.
6. Render the HTML reading edition, complete the anatomy checklist, and preserve immutable versions and current pointer.
7. Keep missing live sources, actual generated PNG and browser review gates open. Deliver through an authorized host route only.

## Bundled engines

| Engine | Doc file | Supply | Key formulas | Output |
|---|---|---|---|---|
| **Formula spec** | `formula-specification.md` | Periodic returns OR supplied vol/drawdown | ROI, CAGR, pop σ, downside σ, drawdown (positive), VaR/ES sorted, Sharpe/Sortino/Calmar annualised by √(periods) | Atoms with input refs + limitations |
| **Kelly** | `kelly-criterion.md` | p,q, g>0, l<0, haircut, fraction, cap | `edge=p·g+q·l`, `full_kelly=−edge/(g·l)`, `confidence_adjusted=full·haircut`, `fractional=adj·fraction`, `capped=min(max(frac,0),cap)` + `Σ p·log(1+ex·payoff)` | Negative edge → 0+warning; bad inputs → unavailable |
| **Convexity** | `convexity-upside.md` | Bear/base/bull/moon prices→payoffs + probs | `up/down = bull/|bear|`, `breakeven=|bear|/(bull+|bear|)`, `weighted_up/down`, `convexity=weighted_up/|weighted_down|` | EV, expected return, skew, max loss; ratio unavailable if downside 0 |
| **Margin** | `margin-safety.md` | MV, borrowed, maintenance | `equity=MV−borrowed`, `margin_ratio=eq/MV`, `LTV=borrowed/MV`, `required=maint·MV`, `call=borrowed/(shares·(1−maint))`, `buffer=price−call` + stress rows | Stressed MV/equity/ratio/threshold — labeled as stress, not brokerage truth |
| **Simulation** | `simulation-method.md` | μ, σ, seed, iters, distribution | Seeded normal Monte Carlo, bounded at −1.0, deterministic given seed | P5/P50/P95, mean terminal, loss prob |

## Cost and cache discipline

Estimate core, expanded and engine-plus-framework input/output budgets before costly calls. Separate immutable policy/specification prefixes, timestamped source documents and dynamic user inputs; hash cache inputs and record provider-reported usage when actually available. Image bytes/dimensions are measured locally, not inferred token counts. Do not copy historical provider discounts, TTLs, model IDs or token-price estimates as current facts. Mark usage unavailable when the host does not report it. No metering integration is implemented here.

## Report and frameworks

Use references/monocle-report-anatomy.md, references/DESIGN-Monocle.md, design/ and docs/reports/REPORT-STANDARD-v5.md. Include all eight original frameworks with distinct question, assessment, dissent, missing evidence and limits; Page is a separate robustness note, not an extra vote. Original cards are preserved but never authorize transactions. Common-name masthead, nine-block BMC, all seven Powers and an actual final generated sketchnote are required for full acceptance. Preserve source/audit navigation before strategy and final image.

Use the explicit private report store, not a default home folder. Never overwrite prior revisions. No preset refresh schedule exists; any schedule requires actual host support and authorized scope.
