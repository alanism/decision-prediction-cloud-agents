> Cloud adaptation: current educational report policy controls outputs. Source CLI and D3/Three.js snippets are research references, not installed integrations. Use the supported portable shell entrypoint. No D3/Three.js runtime is bundled.

---
name: many-models-reddit
description: Apply Scott E Page many-model thinking to authorized Reddit data through selection, inputs, calculations, visualization and auditable reporting.
---

# Many-Models Thinking × Reddit/Redditor Analysis — MECE User's Guide

Evidence-grounded in 27 sequential NotebookLM queries to shared notebook `083ca6cf-8d45-4a1b-a7b8-c80f82f9faf9` **Scott E Page** (34 sources, 2026-09-02). R1 9/9, R2 7/9 (Q11 Markov 11yr + Q13 bandits timeout → retried simplified in R3), R3 9/9 = **25/27 cited answers**. All claims below trace to Page + Clauset-Shalizi-Newman where noted.

## When to use
Public synthetic or explicitly authorized corpora only; no personal corpus is bundled.
- Need to pick the right complexity model (not just run one), find inputs, calculate, visualize, report into auditable HTML or 5-min talk
- Need to combine Reddit signal with finance Decision > Prediction evidence hierarchy without heterogeneous averaging

## The 6-stage MECE pipeline

```
1 SELECT  → 2 INPUTS → 3 CALCULATE → 4 DISPLAY → 5 REPORT → 6 PRESENT
  (REDCAPE purpose + granularity)  (measure)      (visual)   (receipt)  (talk)
```

Each stage has entry/exit checks. Skip a stage and you create false precision — Page's central warning: "all models are wrong, many models reveal blind spots."

### 1) SELECT — Picking the right model (R1)

**Page's 5 taxonomies (R1-Q1):**
1. **Ontological:** Simplification (embodiment — keep essential structure, lump rest) vs Mathematical analogy (isomorphism across domains) vs Exploratory artificial construct (Game of Life — purposely detached)
2. **Structural 7-family palette:** Distributional (normal/power-law), Strategic (games), Dynamics (Markov, systems dynamics, contagion SIR/Bass, path dependence Polya, Lyapunov), Aggregation (threshold Granovetter, NK rugged landscape), Emergence (ABM, CA), plus categorization and human-actor frameworks
3. **Eightfold Path (ABM design):** View/Intention/Speech/Action/Livelihood/Effort/Mindfulness/Concentration
4. **Computation matrix:** Simple vs complicated × agent-based vs abstraction-based
5. **REDCAPE functional:** Reason, Explain, Design, Communicate, Act, Predict, Explore

**Selection rules for Reddit (R1-Q2..Q9):**

| If you see... | Use... | Not... | Why (Page) |
|---|---|---|---|
| Karma/mentions heavy right tail, "rich get richer" early upvotes → visibility | **Power-law** (preferential attachment or SOC) | Normal | CLT requires `N≥20` independent finite-variance additive events. Reddit violates independence → preferential attachment. Test via log-log straight line (Page) or Clauset MLE. |
| Topic/Engine state today predicts tomorrow, fixed rules, history washes out | **Markov stationary `πT=π`** | Path-dependent Polya | Markov iff finite states + fixed row-stochastic `T` + ergodicity (BFS reachability every node) + aperiodicity (`g=1`). Then intervention must change `T`, not one-off state. |
| Adoption driven by external broadcast + internal word-of-mouth | **Bass** `ΔN=(p+qN/M)(M-N)` | Pure SIR (peer only) or broadcast r-shape (external only) vs threshold (sensitive to tails) | Bass captures interplay. `p=0.01-0.05` innovators, `q` imitators, `M` TAM. Threshold models collapse if tail thresholds wrong. |
| Sequential choices with unknown reward distributions, can update | **Bandits** | One-shot optimization (no learning) or classic rigid A/B (pay cost of over-exploring inferior) | Bandits when downside of exploring inferior is costly (Page: pharma trial). Greedy myopic traps → pseudo-regret. |
Public synthetic or explicitly authorized corpora only; no personal corpus is bundled.

**Diversity & heterogeneity (R1-Q8):** `Collective Error = Avg Individual Error - Diversity`. Averaging many diverse subreddit lenses cancels bias. **Never average heterogeneous populations** — `r/parenting` ≠ `r/wsb` ≠ `r/travel`. Keep separate `M`, separate ensembles, merge via claim compiler not raw mean.

**Not-to-model criteria (R1-Q7):** Veto if (a) no modular structure (sand vs stone — every detail matters → cascade), (b) cognitive/intangible space unmeasurable (organizational change train wreck), (c) static math on dynamic heterogeneous adaptive system, (d) violated mixing assumptions (random mixing on networked Reddit).

Public synthetic or explicitly authorized corpora only; no personal corpus is bundled.

### 2) INPUTS — Knowing/finding what to use (R2 pivoted)

Public synthetic or explicitly authorized corpora only; no personal corpus is bundled.

Public synthetic or explicitly authorized corpora only; no personal corpus is bundled.

**Bass (R2-Q12):** Need `p∈[0,1]`, `q≥0`, `M∈(0,1e9]`, `N0∈[0,M]`, `T∈[1,10000]`. Calibrate: `M` from Cosmos (parenting 8,056,434; lifestyle N=100 per sub; travel separate). `p` 0.01-0.05 from Page innovators; `q` from `responses.jsonl` or `aggregates.json` imitation rate. `N0` from pilot believers. Conservation: `N≤M`, `ΔN≥0`, clamp `N(t+1)=min(M, N+ΔN)`. Stagnation veto: `p=0 & N0=0 → ΔN=0` forever → reject `STAGNANT`. Find `t*` where `ΔN` maximal.

**Bandits (R2-Q13):** `K∈[2,64]` arms, `T∈[1,100000]` horizon, `p_i∈[0,1]` true Bernoulli, `k0` initial pulls per arm, `ε0`, `ε_min`. For Reddit book angles `K=5` per category, `T=10k` impressions, `k0=20`. Need `personas.jsonl` win rates as `p_i`. Crucial: isolated `random.Random(seed)` per Page — canonical `seed = hash(params)`, never touch global `random`. Rewards: `r_t=1 if U(0,1)<p_{a_t} else 0`.

Public synthetic or explicitly authorized corpora only; no personal corpus is bundled.

Public synthetic or explicitly authorized corpora only; no personal corpus is bundled.

### 3) CALCULATE — Measuring/modeling/forecasting

**Power-law:** MLE `α̂ = 1 + n / Σ ln(x_i / xmin)`. Compute KS `D = max|S(x)-F(x)|`, bootstrap 250 synthetic datasets via `x = xmin*(1-U)^(-1/(α̂-1))` with canonical seed, `p = fraction(D_synth > D_obs)`. Keep power-law if `p≥0.10`. Moment gates: `α>2` mean defined else `HEAVY_TAIL_UNDEFINED_MEAN` veto Kelly/size; `α>3` variance defined else `HEAVY_TAIL_INFINITE_VARIANCE_ALLOWED` (binary Kelly only, flagged). Never estimate without reporting `n`, `xmin`, `α̂`, `D`, `p`.

**Markov:** Initialize `π0 = [1/n …]`, iterate `π_{k+1}=π_k T` until `‖π_{k+1}-π_k‖1 ≤1e-12`. Output `π`. Deterministic replay required. If not irreducible/aperiodic, do not iterate — report reducible components instead.

**Bass:** Iterate `N(0)=N0`, `ΔN` formula, clamp. Report `N(T)`, `t*`, final penetration `N(T)/M`. If stagnant, report `STAGNANT_DIFFUSION_PARAMETERS` not zero.

**Bandits:** For each policy: `greedy` (after `k0` per arm, pull `argmax μ̂`), `sample_then_greedy` (round-robin `k0` then exploit), `adaptive_ε` (`ε_t = max(ε_min, ε0/√(t+1))`, explore if `U<ε_t`). Compute pseudo-regret `T·max(p_i) - Σ r_t`. Isolate RNG, lowest-index tie break.

**No heterogeneous averaging (R2-Q17):** Convert each family's raw prediction to structured `claim_id` record (`claim_id`, family, direction, strength, `evidence` labels) before compilation. Compile with deterministic compiler. Supermajority `threshold = max(2, ceil(2A/3))` where `A` = independent families. `robust_positive` needs ≥2 families; single-family sweep = `conditional`.

### 4) DISPLAY — Visualization

**Power-law (R3-Q20):** Log-log CCDF `P(X≥x)` vs `x`, straight line = power-law with slope `- (α-1)`, vertical `xmin` line, downward curve = lognormal. Annotate `α̂`, `D`, `bootstrap p`. Tail-only zoom.

**Markov (R3-Q21):** Heatmap `T` (row-stochastic, color 0→1), bar chart `π` (sum=1), plus ergodicity badge: green `g=1` irreducible else red trapped components.

**Bass (R3-Q22):** S-curve cumulative `N(t)/M` (0%→100%) + bar `ΔN(t)` with `t*` peak marker, conservation line `M`, stagnation annotation if `p=0 & N0=0`.

**Bandits (R3-Q23):** Two panels: (a) cumulative pseudo-regret vs `t` for `greedy` vs `adaptive_ε`, (b) `ε_t` decay. Lower regret = better.

### 5) REPORT — HTML Decision Receipt

**Structure (R3-Q24):** Monocle/Notion warm paper `#fdfcf3`/`#f6f5f4`, hairlines, Plantin headlines, no shadows. Required sections: Header (question, date, `A` families, threshold), Inputs (table of `x/xmin/n`, `T`, `p/q/M/N0`, `K/T/k0`), Diagnostics (power-law `α/D/p`, Markov `g`/BFS, Bass `t*`, bandit regret), Evidence Stack per claim (Measured/Calculated/Modeled/Forecast/Narrative + `source.url` + `timestamp` + `formula`), Claim Compiler output (`robust_positive` if ≥threshold families else `conditional`), Veto banner if `α≤2`, Appendix with SVG visuals.

**Evidence hierarchy:** Measured > Calculated > Modeled > Forecast > Narrative > Unknown. Reddit sentiment is Modeling/Narrative — caps weight, needs `user_verified` to update Bayesian posterior `PosteriorMid ±6`.

### 6) PRESENT — Talking script (R3-Q26)

**5-min arc (Page REDCAPE Communicate):**
0:00 Diversity — "One model has blind spots, many lenses cancel errors (Collective Error = Avg Error - Diversity)." 
0:45 Evidence — "We measured X via…"
1:30 Diagnostics — "Power-law α=2.4 (p=0.34) keeps mean, Bass t*=8mo, Markov g=1, bandit regret 12% lower with adaptive ε."
2:30 Veto — "If α≤2 we veto sizing — heavy tail infinite mean — otherwise we proceed."
3:15 Ensemble — "3 families support claim X with threshold 2 → robust_positive; Y only one family → conditional."
4:30 Action — "These scenarios differ because …"

**Framing (R3-Q25):** Show assumptions and boundary conditions, never false precision. Present alternative frames, not majority vote. Name parts formally (`α`, `π`, `p/q`) to create lingua franca.

**Pitfalls (R3-Q27):** Cherry-picking models, overfitting tail, p-hacking `xmin`, narrative fallacy, averaging heterogeneous `r/*` (Simpson's), ignoring `HEAVY_TAIL` veto, presenting conditional as robust.

## Reddit-specific recipes

| Folder | N / schema | Lead ensemble | Key inputs | Horizon |
|---|---|---|---|---|
Public synthetic or explicitly authorized corpora only; no personal corpus is bundled.
| `reddit-intel-lifestyle` `r-malefashionadvice/outfits/travel` | 3×100, V4.4 DEMO, outfits 15 vs 30, 77/h churn | Power+Markov+Bandits (outfits), Bass+Bandits (travel) | Separate `M` per sub, state = aesthetic cluster | days/weeks |
| `reddit-intel-stocks` `r-stocks N=20, r-wsb N=70` | Pilots underpowered | Finance5+Page4=9 families, threshold 6 | Power-law veto first (`α≤2` → no supported model-size conclusion), then Kelly | immediate, re-estimate fast |
Public synthetic or explicitly authorized corpora only; no personal corpus is bundled.

## CLI (capital method pack `page`)

```bash
capital method run --pack page --case reddit-case.json
capital analyze-position --case case.json --method page
capital method committee --packs core page thorp --case case.json
```

`case.json` must contain per-family blocks with `xmin`, `T`, `p/q/M/N0`, `K/T/k0`, seeds, and `claim_id` mapping. Deterministic replay via local RNG, canonical param-hash seeds.

## Limitations & provenance

- Corpus is Reddit comments; identities not independently verifiable.
Public synthetic or explicitly authorized corpora only; no personal corpus is bundled.
- 2/27 NotebookLM queries timed out (Q11 Markov 11yr, Q13 bandits) → retried simplified in R3; answers for those two are condensed.
- Finance engines and Page models are simplifications; use as crutches, not oracles.
```


## Verify and update the source

Use the exact notebook identifier above with an available NotebookLM interface. See `../../docs/sources/NOTEBOOKLM-SOURCES.md` for the source register and careful update workflow. Preserve notebook/source citations when updating the framework; a notebook answer is not a substitute for checking its underlying talk, text or paper.
