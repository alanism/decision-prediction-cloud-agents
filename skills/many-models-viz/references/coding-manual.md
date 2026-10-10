> Cloud adaptation: current educational report policy controls outputs. Source CLI and D3/Three.js snippets are research references, not installed integrations. Use the supported portable shell entrypoint. No D3/Three.js runtime is bundled.

# Many-Models Viz — Coding Manual (D3.js + Three.js × Reddit)

Public synthetic or explicitly authorized corpora only; no personal corpus is bundled.

## Quick start (copy this header)

```html
<script src="https://d3js.org/d3.v7.min.js"></script>
<script type="importmap">{"imports":{"three":"https://unpkg.com/three@0.160.0/build/three.module.js","three/addons/":"https://unpkg.com/three@0.160.0/examples/jsm/"}}</script>
<style>
  :root{--accent:#ffc500;--line:#e5e7eb}
  .viz{border:1px solid var(--line);border-radius:12px;background:#fcfcfc;padding:8px}
</style>
<div id="chart"></div>
```

## Core pattern — decouple, then draw (D3-Q1)

**Anti-pattern:** calculation inside `attr("cx", d=> expensiveFn(d))` + `.append("g")` in update loop → duplicate axes, lag at 77/h.

**Pattern: marks[]**

```js
// 1) Pure JS prep — flat marks with precomputed pixels/colors
const marks = raw.map(d => ({
  x: +d.score,                // from raw/*.json
  ccdf: null,                 // computed later
  color: luminance(d.segment) // not hue for ordered data
})).filter(d=> d.x>0); // log(0) guard

// 2) Stateless declarative draw — idempotent
d3.select("#chart").selectAll("circle")
  .data(marks, d=>d.id)      // keyed join
  .join("circle")             // enter→append, update, exit→remove (replaces enter/update/merge/exit)
    .attr("cx", d=> xScale(d.x))
    .attr("cy", d=> yScale(d.ccdf));
```

## Power-Law CCDF — D3 (D3-Q3)

```js
// tail only: x >= xmin
const tail = marks.filter(d=> d.x >= xmin);
const n = tail.length;
const sumLog = d3.sum(tail, d=> Math.log(d.x / xmin));
const alphaHat = 1 + n / sumLog; // MLE
// CCDF
tail.sort((a,b)=>a.x-b.x).forEach((d,i)=> d.ccdf = (n-i)/n);

const x = d3.scaleLog().domain([xmin, d3.max(tail,d=>d.x)]).range([left, right]);
const y = d3.scaleLog().domain([d3.min(tail,d=>d.ccdf), 1]).range([bottom, top]);
// defensive: replace 0 with small baseline before scale (log(0)=-Infinity)
const yClamped = d=> y(Math.max(d.ccdf, 0.01));

// conditional ticks: only 10^n labeled
const xAxis = d3.axisBottom(x).ticks(6).tickFormat(d=>{
  const l=Math.log10(d); return Math.abs(l-Math.round(l))<1e-9 ? d3.format(".0s")(d) : "";
});
svg.append("g").attr("transform",`translate(0,${bottom})`).call(xAxis);
svg.append("path").datum(tail).attr("d", d3.line().x(d=>x(d.x)).y(d=>yClamped(d)));

// annotate
svg.append("text").text(`α̂=${alphaHat.toFixed(2)} D=${D.toFixed(3)} p=${p.toFixed(2)}${alphaHat<=2?' VETO':alphaHat<=3?' var∞':''}`);
```

Public synthetic or explicitly authorized corpora only; no personal corpus is bundled.

## Markov Heatmap + π — D3 (D3 notebook: heatmap)

```js
Public synthetic or explicitly authorized corpora only; no personal corpus is bundled.
const T = [[0.60,0.30,0.10],[0.15,0.55,0.30],[0.05,0.20,0.75]]; // 3 states: dreaming|planning|booking
// verify before iterate
const irreducible = bfsEveryNodeReachesAll(T); // R1-Q3
const g = gcdCycles(T); // g=1 → aperiodic
if(!irreducible || g!==1) throw "trapped echo chamber — do not report π";

// π power iteration
let pi=[1/3,1/3,1/3];
for(let k=0;k<200;k++){
  const nxt = pi.map((_,j)=> d3.sum(pi.map((p,i)=> p*T[i][j])));
  if(d3.sum(nxt.map((v,i)=>Math.abs(v-pi[i])))<1e-12) break;
  pi=nxt;
}
// heatmap: luminance for probability (not hue)
const color = d3.scaleSequential(d3.interpolateYlOrBr).domain([0,1]);
svg.selectAll("rect").data(T.flat().map((v,i)=>({v,r:Math.floor(i/3),c:i%3})))
  .join("rect").attr("fill",d=>color(d.v));
// pi bars
xBand.domain(["dreaming","planning","booking"]); yPi.domain([0,0.65]);
svg.selectAll("rect.bar").data(pi).join("rect").attr("x",(d,i)=>xBand(i)).attr("y",d=>yPi(d)).attr("height",d=>120-yPi(d));
```

**Styling:** ≤8 colors max, luminance for ordered (light→dark), grayscale printable (D3-Q2).

## Bass S-curve — D3

```js
function bassSeries(p,q,M,N0,steps=26){
  let N=N0, pts=[{t:0,N,dN:0}], peak=0, tStar=0;
  for(let t=1;t<=steps;t++){
    const dN=(p+q*N/M)*(M-N); // ΔN
    const dNclamp=Math.max(0,Math.min(dN,M-N)); // conservation N≤M, ΔN≥0
    if(dNclamp>peak){peak=dNclamp; tStar=t;}
    N=Math.min(M,N+dNclamp); pts.push({t,N,dN:dNclamp});
  }
  if(p===0 && N0===0) throw "STAGNANT_DIFFUSION_PARAMETERS";
  return {pts,tStar,peak};
}
const {pts,tStar}=bassSeries(0.03,0.38,12000,180);
// S-curve line N/M + bars ΔN, t* marker, M dashed
```

## Bandits — D3 (regret + ε decay)

```js
function runBandit(policy, pTrue, T=5000, k0=20, eps0=0.4, epsMin=0.05){
  const K=pTrue.length, best=Math.max(...pTrue), mu=Array(K).fill(0), n=Array(K).fill(0);
  let reg=0; const curve=[];
  for(let a=0;a<K;a++) for(let i=0;i<k0;i++){ const r=Math.random()<pTrue[a]?1:0; n[a]++; mu[a]=(mu[a]*(n[a]-1)+r)/n[a]; reg+=best-pTrue[a]; curve.push(reg); }
  for(let t=K*k0; t<T; t++){
    const eps=Math.max(epsMin, eps0/Math.sqrt(t+1)); // R2-Q13
    const a = (policy==="greedy"|| Math.random()>=eps) ? mu.indexOf(Math.max(...mu)) : Math.floor(Math.random()*K);
    const r=Math.random()<pTrue[a]?1:0; n[a]++; mu[a]=(mu[a]*(n[a]-1)+r)/n[a]; reg+=best-pTrue[a]; if(t%20===0) curve.push(reg);
  }
  return curve; // pseudo-regret; lower wins
}
// draw
const line=d3.line().x((d,i)=>x(i)).y(d=>y(d));
svg.append("path").datum(greedyCurve).attr("stroke-dasharray","5 3");
svg.append("path").datum(adaptCurve).attr("stroke-width",2);
// ε decay secondary
```

**RNG:** isolated `new Random(seed)` with canonical `seed=hash(params)` — never global `Math.random` for replay unless seeded deterministically.

## Three.js — When D3 isn't enough (source-reference)

**Decision:** Low–medium density + need precise labels → D3 pure. High density (10M) + hunt clusters → Three.js pure. Need both → **Hybrid:** D3 SVG axes/labels over Three.js WebGL canvas, shared `marks[]`. [3JS-Q4]

**1) Geometry & draw calls**
```js
// Blender: Ctrl+J merge + single atlas → 7 materials = 7 calls → 1 call
// Code: InstancedMesh for 120 peaks / 1000s nodes
const inst = new THREE.InstancedMesh(sphereGeo, mat, 120);
const dummy=new THREE.Object3D();
for(let i=0;i<120;i++){ dummy.position.set(x,z,y); dummy.updateMatrix(); inst.setMatrixAt(i,dummy.matrix); }
scene.add(inst);
// delete unseen backfaces, FrontSide only
mat.side = THREE.FrontSide;
```

**2) Bake lighting → cheap**
```js
// In Blender Cycles: bake AO + shadows to texture → export
// In code: no lights needed
const mat = new THREE.MeshBasicMaterial({map: bakedTexture}); // not MeshStandard
```

**3) Make discovery pop**
```js
// force-directed 10M network: InstancedMesh + emissive + bloom
const nodeMat = new THREE.MeshStandardMaterial({color:0xffffff, emissive:0xffc500, emissiveIntensity:0.9});
import {UnrealBloomPass} from 'three/addons/postprocessing/UnrealBloomPass.js';
// rugged terrain: PlaneGeometry + procedural height
const geo=new THREE.PlaneGeometry(4,4,64,64);
for(let i=0;i<geo.attributes.position.count;i++) geo.attributes.position.setZ(i, Math.sin(x*2.2)*0.3 + Math.cos(y*1.7)*0.25);
// lighting choreography
scene.add(new THREE.HemisphereLight(0xffffff, 0x222222, 1.1));
scene.background=new THREE.Color(0x0a0a0a);
```

**Cognitive limits remain in 3D:** 5–10 vars, ≤8 colors, up=higher, red=negative, time left→right (front→back in 3D). Violate → harm credibility. [3JS-Q3]
**Salience = message:** whatever glows most must be takeaway. Avoid AI slop purple gradients. [3JS-Q3]

## Hybrid wiring for Reddit many-models (copy this)

```js
// shared marks from Reddit
const marks = raw.map(d=>({id:d.id, score:+d.score, segment:d.segment, x:0, y:0}));

// compute
const tail = marks.filter(d=>d.score>=xmin);
const {alphaHat} = powerLaw(tail);
const pi = markovStationary(T);
const {tStar} = bassSeries(p,q,M,N0);
const curves = runBandit("adapt", pTrue);

// D3 declarative receipt (2D)
d3.select("#receipt").selectAll("circle").data(marks).join("circle")
  .attr("cx",d=>xScale(d.score)).attr("cy",d=>yScale(d.ccdf))
  .on("mouseenter",(e,d)=> tooltip.show(`score ${d.score}`));

// Three.js discovery (3D rugged landscape for NK with K>5)
const terrain = new THREE.Mesh(new THREE.PlaneGeometry(4,4,64,64), bakedMat);
scene.add(terrain); scene.add(instancedPeaks);
```

## Reddit recipe cards — copy-paste

**r/parenting (385@30, M=8056434):** Bass t* months, Bandits K=5/cat, Power tail from scores. `T` months, threshold 2.

**r/lifestyle 3×100 (outfits 77/h):** Separate M per sub, Power gate per sub (outfits n=15 thin → higher xmin), Markov 3-state aesthetic, Bandits T weeks.

**r/travel (100, seasons):** Bass p high (seasonality), q moderate, `T` weeks, Markov funnel, Bandits K=8 itineraries.

Public synthetic or explicitly authorized corpora only; no personal corpus is bundled.

## Checklist before ship

- [ ] Decoupled marks[]? .join() not .append() loop? [D3-Q1]
- [ ] Log scales with zero guard? Conditional 10^n ticks? [D3-Q3]
- [ ] 8-color limit? Luminance for order? Grayscale printable? [D3-Q2]
- [ ] Interactive legend fading 0.2 + staged i*10 delays? [D3-Q4]
- [ ] Merged geometries? InstancedMesh? Baked BasicMaterial? FrontSide? [3JS-Q1]
- [ ] HemisphereLight + emissive bloom for salience? [3JS-Q3]
- [ ] D3 vs Three.js vs hybrid chosen per density? [3JS-Q4]
- [ ] α/D/p + g + t* + regret + threshold reported? Veto banner if α≤2?

Onward. Skill wiring: `many-models-reddit` (math) → `many-models-viz` (this manual) → HTML Receipt.
