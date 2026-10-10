# Bass Diffusion Discrete Dynamical Model Reference

Grounding: Frank Bass (1969), Scott Page (Many-Model Thinking Ch. 11).

## Discrete Dynamical Equation

For time steps $t = 0, 1, \dots, T$:
$$\Delta N(t) = \left( p + q \frac{N(t)}{M} \right) (M - N(t))$$
$$N(t+1) = \min(M, N(t) + \Delta N(t))$$

Where:
- $p \ge 0$: Coefficient of innovation (external influence).
- $q \ge 0$: Coefficient of imitation (internal network effect).
- $M \in (0, 10^9]$: Market carrying capacity / total addressable adopters.
- $N_0 \in [0, M]$: Initial adopters at $t=0$.
- $T \in [1, 10000]$: Simulation time horizon.

## Invariants & Conservation

- **Conservation Clamping:** Cumulative adopters $N(t) \le M$ and $\Delta N(t) \ge 0$.
- **Stagnation Gate:** If $p = 0$ and $N_0 = 0$, diffusion cannot ignite ($\Delta N(t) = 0$ for all $t$); rejected with `STAGNANT_DIFFUSION_PARAMETERS`.
- **Peak Adoption Detection:** Identified at time period $t^*$ where $\Delta N(t)$ achieves maximum discrete rate.
