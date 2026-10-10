# Markov Stationary Distribution Diagnostic Reference

Grounding: Scott Page (Many-Model Thinking / Model Thinking Ch. 12).

## Mathematical Invariants

- **Matrix Orientation:** Row-stochastic transition matrix $T \in \mathbb{R}^{n \times n}$ where $T_{ij} = P(S_{t+1} = j \mid S_t = i)$, $\sum_{j=1}^n T_{ij} = 1.0 \pm 10^{-12}$.
- **Stationary Vector:** Row vector $\pi \in \mathbb{R}^n$ satisfying $\pi T = \pi$ and $\sum_{i=1}^n \pi_i = 1.0$.

## Ergodicity Verification (Standard Library Graph Algorithms)

1. **Irreducibility:** Run BFS reachability from every state $i \in \{0, \dots, n-1\}$. All $n$ nodes must be reachable from each node (strongly connected graph).
2. **Aperiodicity:** In a strongly connected graph, compute BFS spanning tree levels $L(u)$. For every directed edge $(u, v)$, the cycle difference is $|L(u) - L(v) + 1|$. The chain period $g = \gcd_{(u, v)} |L(u) - L(v) + 1|$. The chain is aperiodic if $g = 1$.

## Power Iteration

- Initialize $\pi_0 = [1/n, \dots, 1/n]$.
- Iterate $\pi_{k+1} = \pi_k T$.
- Terminate when $\|\pi_{k+1} - \pi_k\|_1 \le 10^{-12}$.
