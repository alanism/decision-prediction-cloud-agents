> Current educational report policy governs. Source style/brand names identify references only; never reproduce their branding in rendered report titles, metadata or visible mastheads.

# Stock Report Design Standard

Generic optional print guidance only. No historical scores or acceptance transfer to this template; inspect each exact artifact independently.

## Purpose and release status

A reusable private stock-review publication for an individual investor. Make the research question, business evidence, valuation assumptions and limits easy to inspect without hiding substantive disagreements. HTML remains primary. Optional print may begin with the eight-section scaffold but has no fixed page ceiling; retain complete BMC/Powers, audit navigation and final actual generated sketchnote without shrinking essential text. Deep reproducibility material lives in a separately delivered companion, linked by exact filename and with an embedded audit download in HTML.

Generic optional print guidance only. No historical scores or acceptance transfer to this template; inspect each exact artifact independently.

## Editorial and visual principles

Use the supplied Andy Allen hero as a design lens: truth before ornament; a publication worth spending time with; a cockpit that invites examination rather than demands passive trust. In this static report, those ideas mean inspectable inputs, clearly reversible navigation, carefully paced pages and explicit routes into detailed calculations. They do not mean animation, fabricated interactivity, physics effects, sound, novelty controls or unsupported claims of user testing.

Preserve a warm editorial character: cream paper, black ink, generous serif headings, restrained sans-serif utility labels, square surfaces and hairline rules. One yellow signal draws attention to a decision or reference, never to imply investment safety. No gradients, shadows, decorative rainbow scorecards or generic finance-dashboard chrome. Do not reproduce source-publication names, wordmarks, slogans or attribution branding inside report titles, filenames, metadata or visible text.

The attached layout rubric is a heuristic, not scientific evidence. Claims about neuroscience, mathematical trust or psychological universals in a design reference are not adopted as factual assertions. Judge whether the report communicates clearly and honestly.

## Tokens

| Role | Token |
|---|---|
| Paper | `#fdfcf3` |
| Ink | `#151515` |
| Signal | `#ffc500` |
| Secondary text | `#4b4b45` |
| Hairline | `#cecdc3` |
| Surfaces | Cream or white; no shadows |
| Editorial type | Georgia / Times New Roman / serif fallback; PDF uses an available readable serif |
| Utility type | Arial / Helvetica / sans-serif fallback |
| Main body | 11pt target, 1.3–1.35 leading |
| Dense lens body | 10.5pt minimum target |
| Caption/source | 9pt target; never substitute tiny text for editorial cuts |
| Page headline | 29pt target, compact serif leading |
| Main decision hero | 29–43pt depending on real fit |
| Grid | Six conceptual columns, composed into two or three reading regions |
| Gutters | 16–25px equivalent; repeated within each component |
| A4 canvas | 210 × 297mm, 13–14mm internal content margins |

Avoid clipping techniques: no text overflow hidden, no fixed-height text cards, no ellipses on substantive findings. Actual page height is fixed only for the print canvas and must be verified with overflow checks. If content does not fit, edit or move it to the companion with an explicit summary and link; never reduce essential body copy below the approved reading size to chase page count.

## Optional print structure (expand as needed)

1. **Research overview.** Company, exact evidence cutoff, business thesis and uncertainty. Up to three high-signal metrics and one qualitative decision map. Screenshot status and market timestamp visible.
2. **Optional authorized context.** Supplied asset/debt/equity reconciliation, concentration and explicitly hypothetical maintenance/financing stresses; unavailable without sufficient inputs. Directly labeled scenario line or stress bars, never invented history.
3. **Business.** Operating demand, capital intensity, normalized interpretation and cash conversion. A conserved cash Sankey when appropriate. Guidance marked Forecasted with issue date and horizon.
4. **Valuation.** Scenario horizon, reference price, explicit input table, formula and price-only limits. Bar/range chart with units and direct labels; no invented scenario probabilities.
5. **Risk models.** Hypothetical distributions, Sharpe definition, payoff asymmetry and generalized/binary Kelly distinctions. State why this model is not the actual leveraged portfolio. Preserve raw versus capped and fractional sizing semantics.
6. **Investor lenses one.** Four complete, individually distinct frameworks, each with its question, evidence assessment, missing inputs/abstention and decision consequence. Summarize a genuine disagreement.
7. **Investor lenses two.** Four remaining complete frameworks plus a separate Scott Page robustness note. Named lenses are simulated applications of authored frameworks, not quotes, endorsements, current opinions or independent votes.
8. **Evidence and uncertainty.** What changes the decision, missing user inputs, known dated checkpoints, four evidence definitions, sources, exact audit links, computation boundaries and suitability limits.

Required eight lenses: Scott Galloway; Brad Gerstner; Chris Camillo; Philippe and Thomas Laffont; Michael Mauboussin; Warren Buffett and Charlie Munger; Martin Shkreli; Ed Thorp. Scott Page stays separately identified. Compress repetition rather than remove dissent or card-specific abstention.

## Evidence grammar

- **Measured:** source-reported observation with source, reference period and timestamp where applicable. Brokerage screenshot observations use a separate status label, “Observed · unconfirmed,” until actual user confirmation. Do not label them Measured and rely on a footnote to undo that claim. Calculated derivatives retain an explicit unconfirmed-input caveat.
- **Calculated:** deterministic arithmetic with formula and input lineage. It inherits any uncertainty in its inputs.
- **Modeled:** chosen assumptions or distributions, including calculations performed in Python. Neither deterministic code nor graphical precision upgrades assumptions into measured evidence.
- **Forecasted:** future expectation or guidance with originating source, horizon and uncertainty.

The current report provides educational research implications, not personal transaction recommendations. A qualitative diagram is expressly a judgment aid, not a fifth data label.

Keep original market cutoffs and account as-of uncertainty. A design update does not refresh facts. Preserve source numbers and formulas. If a prior presentation contains inconsistent rounding, disclose the correction and retain original evidence separately. Do not silently edit embedded numeric audit records.

## Chart selection and accessibility

Every visual must answer a decision-relevant question and include an accessible title, units, a caption with period/source and a nearby caveat if modeled. Direct labels outrank distant legends. Do not use hue as the sole encoding.

- **Sankey:** only conserved flow quantities in comparable units. Widths must be proportional to the same unit scale. Clarify a small remainder rather than exaggerating it.
- **2×2:** categorical or explicitly qualitative axes; do not imply that unmeasured locations are scores. Highlight a current decision category rather than a fictitious coordinate.
- **Three-circle Venn:** suitable for conceptual requirements such as evidence, price and account capacity. Mark “qualitative”; areas and overlaps must not imply observed set sizes. Omit it if it duplicates the 2×2 or adds no information.
- **Bar:** magnitude comparison with zero baseline, consistent units and readable direct labels. Negative values need an explicit zero axis.
- **Line:** dated observations only when real historical series exist. A sensitivity line must say “scenario” and label its x-axis as shocks or assumptions, not time. Never interpolate a fictional price history.
- **Radial:** part-to-whole only when a real denominator exists, or measured comparable dimensions with defensible normalization. Do not create “quality,” “moat,” confidence or investor-vote scores to fill a radar chart. A radial chart is optional when a simpler chart communicates better.

Use this generic scaffold only with the current report’s own verified inputs. No private report examples are bundled.

## Full audit companion

Preserve the original source report byte-for-byte outside the new presentation set. The new companion may remove source branding while retaining detailed prose, all original numerical tables and links. Extract embedded audit JSON without parsing/re-serialization if byte preservation is promised. Store SHA-256 checksums and compare the audit URI payload in the main report and companion. Main HTML contains an offline download of the exact JSON. Deliver companion and JSON alongside report so relative links have a clear destination; package them together when the client cannot resolve sibling attachments.

## Reuse and handoff

Use this generic scaffold only with the current report’s own verified inputs. No private report examples are bundled.

For each future stock, keep its own source numbers, timestamps, assumptions and dissent. Never transfer another report’s scenarios, private values or conclusions into a different report. If evidence does not support a slot, state the missing input and choose an appropriate visual instead.

## Review rubric and acceptance

Scores are design-review judgments, not objective measurements or user-test results. Rate each criterion 0–10 using actual rendered evidence. Target at least 95/100 in each half after iteration. If a reviewer cannot support that score, record the lower result and specific fixes; never manufacture a pass.

### Architectural layers

1. **Canvas:** usable A4 area, stable axes and safe folio placement.
2. **Grid:** coherent two/three-region layouts derived from the shared six-column logic.
3. **Repeated spacing:** consistent margins, gutters and within-component intervals.
4. **Negative space:** enough calm to separate ideas without displacing necessary evidence.
5. **Type ramp:** clear, readable hierarchy with no miniature factual content.
6. **Font/weight roles:** editorial serif and functional utility labels with distinct roles.
7. **Focal primacy:** one dominant decision or analytic claim on each page.
8. **Reading path:** clear entry → evidence → consequence sequence.
9. **Intentional emphasis:** restrained signal accent; no accidental visual noise.
10. **Scale robustness:** inspect full-size print pages, thumbnails and relevant screens independently. A 64px preview tests silhouette only, not body reading.

### Performance criteria

1. **Ten-second intention:** first-view reviewer can identify the page's purpose; call this a reviewer observation, not a user study.
2. **Cognitive relief:** dense analysis alternates with adequately spaced structure.
3. **Active whitespace:** spacing groups related evidence and separates distinct claims.
4. **Temporal rhythm:** report moves from research question to evidence to disagreement to next observation.
5. **Contrast/isolation:** focus survives grayscale and does not depend on yellow alone.
6. **Spacing harmonics:** repeated components feel related and aligned.
7. **Type proportionality:** relative scale and leading support comprehension, without numerology claims.
8. **Format fluency:** actual PDF print fit; separate responsive/browser tests for HTML.
9. **Shape semantics:** charts and rules communicate quantities or relationships honestly; no psychological claim needed.
10. **Controlled variation:** varied meaningful visual forms prevent monotony without breaking navigation.

### Gating failures

Any unreadable essential type, clipping/overlap, missing page, mis-scaled chart, unsupported invented data, stale/cutoff ambiguity, evidence-label error, missing lens, false endorsement or broken/missing audit delivery blocks adoption regardless of points. Check exact page count and output metadata. No pass based on source inspection alone.

### Verification record

Record artifact hash, page count, renderer, fonts used, inspected page images, reviewer observations, scores, fixes and open limitations. Re-render after material changes and reassess affected pages. Keep PDF and HTML statuses separate. Retain unrendered HTML as candidate when permitted browser rendering is unavailable.


Current full acceptance also requires the complete nine-block Business Model Canvas, all seven Powers, source/audit navigation before strategy, and an actual final generated PNG with text and inspection receipts. Expand page count rather than omit required analysis.
