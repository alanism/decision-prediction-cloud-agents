# Assumption Update Proposals

Evidence never silently overwrites an assumption. A Bayesian update creates a separate proposal containing prior and proposed values, evidence and synthesis references, thesis-map and update hashes, affected metric and scenario, projected impacts, and approval status.

New proposals are always `pending`. Supported states are `pending`, `approved`, `rejected`, and `expired`. Only `approved` proposals can affect `capital analyze`; all other states leave the original case unchanged. Applying a proposal does not authorize a decision or write a ledger entry.
