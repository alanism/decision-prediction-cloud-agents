# Deterministic Claim Compiler Reference

Grounding: Scott Page (Diversity Prediction Theorem & Ensemble Methodology).

## Claim Intermediate Representation (IR)

Claims submitted to the compiler must be structured JSON dicts containing:
- `claim_id`: Standardized string identifying target thesis claim (e.g. `growth_persistence`).
- `model_family`: Distinct mathematical family (`power_law`, `markov`, `bass`, `bandit`).
- `direction`: Discrete vote (`positive`, `negative`, `neutral`).
- `receipt_hash`: 64-character SHA-256 hex digest of the originating model execution receipt.
- `correlation_group` (optional): Group identifier for correlated model instances.

## Ensemble Aggregation Rules

1. **Same-`claim_id` Grouping:** Only records matching the exact `claim_id` are combined. Cross-target raw averaging is strictly prohibited.
2. **Two-Family Minimum:** A claim requires support from $\ge 2$ independent model families to qualify as `robust_positive`.
3. **Supermajority Rule:**
   $$\text{threshold} = \max\left(2, \left\lceil \frac{2A}{3} \right\rceil\right)$$
   Where $A$ is the number of independent contributing voting entities (families or collapsed correlation groups).
4. **Correlation Group Collapsing:** Models sharing a `correlation_group` collapse to at most 1 independent vote.
5. **Binding Veto Precedence:** Active binding vetoes (e.g. `HEAVY_TAIL_UNDEFINED_MEAN`) suppress `robust_positive` status to `conditional` and enforce risk gates.
