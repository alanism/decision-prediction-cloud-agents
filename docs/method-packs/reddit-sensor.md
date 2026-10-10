# Method Pack Note — Reddit Sensor (many-models-reddit) + Receipt Rendering (many-models-viz)

Reddit never sizes a position in this repo. It acts as a **bounded Bayesian likelihood** on narratives already under test, gated by the Page tail veto, rendered as auditable receipts. Committee Mode (`--packs core page thorp`) calls it natively.

## Skills

- `skills/many-models-reddit/SKILL.md` — 6-stage MECE pipeline (Select→Inputs→Calculate→Display→Report→Present). Grounded in 25/27 cited NotebookLM answers to the Scott E Page notebook (`083ca6cf-8d45-4a1b-a7b8-c80f82f9faf9`, 34 sources, 2026-09-02). Recipes: single-population cohorts (e.g. r/parenting N=385), heterogeneous multi-sub sets (never pool — separate ensembles, merge via `claim_id`), 2-layer finance+Page for tickers (Reddit Modeled/Narrative only, threshold 6/9), longitudinal single-redditor (Markov+Bandits lead, Bass skipped at n=1).
- `skills/many-models-viz/SKILL.md` (+ `references/coding-manual.md`) — D3 = declarative receipts, Three.js = visual discovery. `raw → marks[] (decoupled pure JS) → calculate → D3 + Three → HTML Evidence Stack`. Grounded in 8 NotebookLM pulls (D3 notebook `211997f5-9eba-448d-b043-5613781c3d8f` ×4, Three notebook `92387234-826b-40a8-aabd-b4dc672d5948` ×4). Rules: `.join()` idempotent, scaleLog×2 zero-guard, conditional 10ⁿ ticks, 8-color max, luminance for order, grayscale-first, fadeOpacity 0.2, i*10 stagger; InstancedMesh, baked MeshBasicMaterial, HemisphereLight, FrontSide only, Ctrl+J atlas.

## Wiring into Committee Mode

1. **Tail veto first.** Power-law on ticker-mention counts per author/post (`α = 1+n/Σln(x/xmin)`, KS D, 250 bootstraps). α≤2.0 → `HEAVY_TAIL_UNDEFINED_MEAN` → watch/hold; Reddit chatter cannot justify exposure increase. Matches `test_page_method_pack` veto behavior.
2. **Regime sensor.** Markov over `{risk-on, risk-off, crab, squeeze}` from pulse themes + price, `created_utc`-ordered; needs BFS irreducibility + GCD g=1, else path-dependence flag.
3. **Narrative timing.** Bass on mention diffusion (M = addressable traders, p = external/seasonal, q = imitation); t* schedules confirm/caution checks, never entries.
4. **Research allocation.** Bandits over theses (K≤64), not tickers — adaptive-ε decides what to research next.
5. **Capped likelihood.** Reddit posterior nudge `(EvidenceStrength−50)/5 → PosteriorMid ±6`, requires `user_verified`; weight capped, never sets Kelly size.
6. **Receipts.** Every claim renders via many-models-viz: CCDF log-log, T heatmap + π bars, S-curve + t*, regret curves, Evidence Stack (Measured > Calculated > Modeled > Forecast > Narrative) + 5-min talk script.

## Fixture

`fixtures/valid/many_model/thesis_run_3_reddit_sensor.json` — synthetic semiconductor-thesis case with a `model_thinking_inputs.reddit_sensor` block (mention-count tail that passes the α gate, capped likelihood weight 0.15, user_verified). Run: `capital method run --pack page --case fixtures/valid/many_model/thesis_run_3_reddit_sensor.json`.

See [the NotebookLM source register](../sources/NOTEBOOKLM-SOURCES.md) for exact source identifiers, the original supplied share URL, and verification/update instructions.
