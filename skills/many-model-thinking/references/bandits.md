# Bernoulli Multi-Armed Bandit Simulation Reference

Grounding: Scott Page (Many-Model Thinking Ch. 14 / Model Thinking Ch. 18).

## Simulation Specifications

- **Arms:** $K \in [2, 64]$ Bernoulli arms with true payout probabilities $p_i \in [0.0, 1.0]$.
- **Horizon:** $T \in [1, 100000]$.
- **Tie-Breaking:** Lowest index arm wins ties.
- **Pseudo-Regret:** $\text{Regret}(T) = T \cdot \max_i(p_i) - \sum_{t=1}^T r_t$.

## Supported Policies

1. **Greedy:** After $k_0$ initial pulls per arm, always pull $\arg\max_i \hat{\mu}_i$.
2. **Sample-Then-Greedy:** Pull each arm $k_0$ times in round-robin, then exploit the best empirical arm for all remaining $T - k_0 K$ rounds.
3. **Adaptive $\epsilon$-Greedy:** After initial pulls, in each round $t \ge k_0 K$, $\epsilon_t = \max(\epsilon_{\min}, \epsilon_0 / \sqrt{t+1})$. Explore with probability $\epsilon_t$, exploit best empirical arm with probability $1 - \epsilon_t$.

## RNG Draw Sequence & Isolation

For round $t$:
1. Explore test: $u_1 \sim \text{Uniform}(0, 1) < \epsilon_t \implies$ explore.
2. If exploring: select arm $a_t \sim \text{randrange}(K)$.
3. Reward test: $u_2 \sim \text{Uniform}(0, 1) < p_{a_t} \implies r_t = 1$, else $0$.

Local `random.Random(seed)` instances are strictly isolated to guarantee deterministic replay.
