> Cloud adaptation: current educational report policy controls outputs. Source CLI and D3/Three.js snippets are research references, not installed integrations. Use the supported portable shell entrypoint. No D3/Three.js runtime is bundled.

---
name: many-models-viz
description: Use when making Reddit + Many-Models thinking visualizations beautiful, correct, and interactive — choosing D3.js for declarative 2D charts versus Three.js for 3D discovery, styling for technical and non-technical audiences, and wiring them to Power-Law, Markov, Bass, and Bandits outputs from reddit-intel corpora.
---

# Many-Models Viz — D3.js + Three.js for Reddit Complexity Science

Public synthetic or explicitly authorized corpora only; no personal corpus is bundled.

## When to use

Public synthetic or explicitly authorized corpora only; no personal corpus is bundled.
- Need to decide **D3 vs Three.js vs hybrid** for a given density/cognitive goal
- Need to avoid chartjunk while keeping interactivity (progressive disclosure)

## The two epistemologies (Page REDCAPE)

- **D3.js = Declarative explanation** — "make a clear statement." Flat 2D SVG, native DOM labels, precise axes. For low–medium density where you know the message.
- **Three.js = Visual discovery** — "hunt for patterns." 3D WebGL, force-directed networks, rugged terrains. For high-density (10M points) where message emerges from exploration.

> Visual salience is the message. Whatever pops most must be your takeaway — else it's a distraction. [Three.js Q3]

## D3.js — Make it correct, then beautiful (from source-reference notebook)

**1. Data architecture — dumb renderer, smart prep**
- Decouple computation from rendering. Pre-process raw `raw/*.json` into flat `marks[]` with precomputed x/y/color. Pass to stateless declarative draw. Portable to React/Svelte/Canvas. [D3-Q1]
- Idempotent DOM: never `.append()` in update loops — stacks duplicate axes. Use `.join("rect")` (enter→append, update, exit→remove). [D3-Q1]
- This is not optional — non-idempotent re-renders ruin text and lag at 77 comments/h (outfits).

**2. Scale correctness**
- **Power-law CCDF must be `d3.scaleLog()` on both axes.** Linear crushes tail into corner. [D3-Q3]
- Log domain never crosses zero (`log(0)=-∞`). Defensibly replace 0 with small baseline (1 or 0.01). [D3-Q3]
- Log ticks cluster exponentially — **conditional ternary**: if `tick == 10^n` render label else `null`. [D3-Q3]

**3. Color & typography — perception science**
- **Categorical limit 8 colors.** Beyond → consolidate or facet. [D3-Q2]
- `scaleOrdinal` for qualitative (species/country), `scaleSequential` for continuous numeric. [D3-Q2]
- **Grayscale rule:** get it right in black & white first — patterns must survive print. [D3-Q2]
- **Luminance for order:** ordered data (years, classes) → luminance (light→dark), not hue. Hues have no preconscious order — forces legend lookup. [D3-Q2]
- Typography is data-ink: native SVG DOM gives perfect wrapping/scaling vs WebGL text.

**4. Interactivity — progressive disclosure (Overview first, details on demand)**
- **Interactive legend opacity fading:** hover legend category → focal `opacity 1.0`, others `0.2` or `0.05`. Instant isolation without losing context. [D3-Q4]
- **Choreographed staged transitions:** stagger `.delay((d,i)=>i*10)` for cascade, initialize enter-state off-screen to avoid bug. [D3-Q4]
- Never crowd all numbers into one static image — layers on demand.

**Model-specific D3 recipes**

| Model | D3 construct | Style note |
|---|---|---|
| **Power-law** | `scaleLog` ×2, conditional ticks, straight line fit, vertical `xmin` | Annotate α̂, D, bootstrap p on chart |
| **Markov** | Heatmap `T` (color luminance for probability) + bar `π` | Row-stochastic check, BFS/g badge |
| **Bass** | S-curve `N/M` line + `ΔN` bars, `t*` marker, `M` dashed | Conservation line, stagnation flag |
| **Bandits** | Regret curves + `εₜ` decay | Adaptive vs greedy, lower wins |

## Three.js — Make discovery immersive (from source-reference notebook)

**1. Geometry & draw calls — performance is beauty**
- **Merge static geometries in Blender** `Ctrl+J` + single texture atlas — every material = draw call (7 materials → 7 calls). [3JS-Q1]
- **`InstancedMesh` for repeats:** grass/rocks/particles or 1000s of state nodes → 1 draw call, per-instance color/scale. [3JS-Q1, Q2]
- **Delete unseen backfaces**, render `FrontSide` only. [3JS-Q1]

**2. Texture baking — cheap beauty**
- Bake lighting/ambient occlusion/shadows in Cycles → swap to `MeshBasicMaterial` (no real-time lights). [3JS-Q1]
- Then you can drop expensive lights — basic material just shows texture. [3JS-Q1]

**3. Art direction — Good Charts in 3D**
- **Salience = message.** Whatever pops (emissive + bloom) must be takeaway. [3JS-Q3]
- **Cognitive limits remain:** 5–10 variables, ≤8 colors even in 3D. Individual points melt to forest fast. [3JS-Q3]
- **Respect conventions:** time left→right (front→back in 3D), up = higher, red = negative. Violate → harm credibility. [3JS-Q3]
- **Lighting:** soft top-down gradient `HemisphereLight` (sky + dark ground), not flat default. Avoid lazy purple gradients/"AI slop". [3JS-Q3]

**4. When Three.js wins (from notebook)**
- **Force-directed 3D networks:** 10M social connections → dense central spot + striations invisible in spreadsheet. Use `InstancedMesh` + `MeshStandardMaterial` emissive + `bloom()` pass for active regions. [3JS-Q2]
- **Rugged landscapes:** procedural terrains for NK fitness/loss landscapes — continuous c. [3JS-Q2]
- **Topographical density plots:** forest-level aggregate patterns. [3JS-Q2]

## Decision matrix — D3 vs Three.js vs Hybrid

| Goal | Density | Audience | Use | Why |
|---|---|---|---|---|
| **Everyday declarative** — bar/line/scatter with clear takeaway | Low–medium (≤8 cats, 5–10 vars) | Mixed tech/non-tech | **D3 pure** | Precise labels, DOM typography, crisp axes, accessible |
| **Visual discovery** — hunt clusters, terrain, 10M points | High | Analyst / explorer | **Three.js pure** | GPU instancing, force-directed, terrain |
| **Explain then explore** — state a claim, then let user hunt | Medium→High | Executive + analyst | **Hybrid** | D3 SVG overlay for axes/labels + Three.js WebGL canvas for 3D state cloud; sync via shared marks[] |

> If dataset fits cognitive limits → D3. If you need forest-level emergence → Three.js. If you need both → hybrid with D3 labels over Three.js canvas. [3JS-Q4]

## Integration with many-models-reddit

**Flow:**
```
reddit-intel raw → marks[] prep (pure JS) → many-models-reddit calculate (α, π, t*, regret, threshold)
    → D3 declarative (2D receipts) + Three.js discovery (3D landscapes) → HTML Receipt + Evidence Stack
```

**Wiring example (pseudo):**
```js
// 1. Prep: reddit → marks (decoupled, per D3-Q1)
const marks = raw.map(d => ({x: log(d.score), y: log(ccdf(d)), color: luminance(d.year)}))
// 2. Calculate: from many-models-reddit
const {alpha, xmin, D, p} = powerLawMLE(marks)
// 3a. D3: CCDF log-log
d3.select("svg").selectAll("circle").data(marks).join("circle")
  .attr("cx", d => xScale(d.x)).attr("cy", d => yScale(d.y))
// 3b. Three.js: rugged landscape for NK (if K>5)
const terrain = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({map: bakedTexture}))
scene.add(new THREE.InstancedMesh(geometry, material, N))
```

**CP+B voice for both:** Short bursts, blunt labels, pineapple ritual ("say pineapple if hue encodes order"), story→lesson→rule. Same report must work for the quant (needs α, D, p) and the human (needs "tail is heavy, don't size on mean").

## Pitfalls this bridge fixes

- **D3 idempotency bug** (stacked axes) at 77/h churn — fixed by `.join`
- **Log(0)** crash on CCDF tails — guard with baseline
- **8-color forest** — facet or consolidate
- **Hues for order** — use luminance
- **Draw-call explosion** (7 materials) — merge + InstancedMesh + FrontSide
- **Flat lighting** — bake + HemisphereLight + basic material
- **Chartjunk crowding** — progressive disclosure, not one static dump

## References

Public synthetic or explicitly authorized corpora only; no personal corpus is bundled.
Public synthetic or explicitly authorized corpora only; no personal corpus is bundled.
Public synthetic or explicitly authorized corpora only; no personal corpus is bundled.
```

