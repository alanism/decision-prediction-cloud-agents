# Contract flow

The planned flow is:

```text
decision case + assumption register
    -> analysis
    -> comparison
    -> user-created proposal
    -> separate human authorization
    -> local decision ledger
```

A proposal represents the user-selected action or exposure being considered. It cannot authorize itself. An analysis cannot authorize itself. A future record append requires a separate authorization bound to both proposal and analysis hashes.

Outcome tracking is deferred beyond v1. A future `decision-outcome.v1.schema.json` contract may support calibration review by comparing recorded assumptions and decisions with realized outcomes. No outcome schema or runtime behavior is included now.

