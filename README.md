# Decision ≥ Prediction Cloud Agents

Cloud-first educational research. **OAI dot is the primary workflow; Meta Muse and Grok are secondary, unverified host mappings.** The engine runs offline in a generic Python shell. No native tool registration, live provider, scheduler, trading or account connection is supplied.

This independent repository vendors its engine and assets. It needs no sibling repository or desktop installation. Existing upstream main and open PRs are outside this release's control.

## Start

Python 3.11–3.13, standard library only. No dependency installation is needed for the portable workflow.

```sh
python3 scripts/bootstrap_portable.py --destination /chosen/new/cloud-bundle
python3 -I /chosen/new/cloud-bundle/portable.py doctor
python3 -I /chosen/new/cloud-bundle/portable.py validate
python3 -I /chosen/new/cloud-bundle/portable.py analyze --fixture --file valid/mvp-case.json
```

Choose an existing destination parent and a new directory outside this checkout. Retain the returned manifest SHA-256 independently and pass it in DECISION_MANIFEST_SHA256 when invoking the bundle. An unsigned self-hash inventory provides integrity, not independent authenticity. Relocate the whole bundle and run from any working directory.

For a synthetic report, first choose an existing private directory outside any Git checkout and outside the bundle, then run:

```sh
python3 -I /chosen/new/cloud-bundle/portable.py demo --data-dir /chosen/private-data
```

The synthetic demo is deliberately incomplete: missing live sources, actual generated image and browser review remain visible. It is not real-company acceptance.

## Contents

- Pinned deterministic engine in vendor/capital-decision-lab; original calculations, contracts and schemas
- Separate generic cloud adapter in adapters/cloud/decision_cloud
- Eight complete original investor framework cards, Scott Page separately, and original dlc reference
- All three design families, complete stock HTML template, seven adapted skills and their references
- Cloud-adapted report anatomy, tone and evidence rules; public derivative of the current v5 report standard
- Explicit host capability contract, private versioned storage, hash receipts and inactive schedule-intent example
- Independent extraction board and resume procedure under docs/extraction

Read START_HERE.md, docs/reports/REPORT-STANDARD-v5.md, docs/verification/STATUS.md and UPSTREAM.json. Historical cards are source material: stylized simulated lenses do not represent real people's statements or endorsements. Current educational policy governs all current outputs.

## Verification boundaries

Offline tests and one prior actual host-image handoff are bounded evidence. Native OAI registration, Muse/Grok acceptance, live sources, browser visual/interaction QA and full original upstream pytest regression are separate gates. See the exact current test receipt; no historical test count is inherited as a current pass.

## License

The existing custom Capital Decision Lab Fair Source License v1.0 is retained verbatim in LICENSE. Public source availability does not mean unrestricted commercial or hosted-service permission. See its complete terms and delayed conversion provision.
