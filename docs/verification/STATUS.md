# Cloud extraction verification — 10 October 2026

## Passed in this extraction

- 37 portable standard-library tests: fresh installation, relocation, exact inventory tamper detection, private path/input boundaries, bounded simulation, report/image validation, immutable storage and frozen-scenario JavaScript checks.
- Six additional direct engine checks reject Windows drive, UNC and rooted-backslash paths on Linux, preserving the inherited containment repair.
- 9 extraction-specific standard-library tests: all runtime/design/doc assets selected, original cards/license pinned, mathematical and contract bytes preserved, cloud-only distribution, adapter separation, fixed task denominator and declared patch hashes.
- Fresh bundle installed from this separate tree, relocated, then doctor/validate/analyze/compare/demo invoked with Python isolated mode from an unrelated working directory. No source sibling path is imported.
- One actual previously generated and pixel-inspected OAI host PNG for fictional Workshop Cloud replayed through this extracted renderer. Exact embedded bytes match SHA-256 f10814bc30924ca9d792d8eb00e6d36291017e17ca84c99905ffa8e0531b1526. Two image-bearing revisions preserve the initial missing-image demo revision and advance the atomic current pointer to v000003. The rendering is identical to the prior image-bearing report, hash f2dd8ad1d3df2a6623218fb324ff1d40e748d8f30392685ac47d9f7fefbdfae4.
- No dependency installed, network/provider call, credential operation or external publication performed by the extraction worker. Source main and PR2 remain unchanged.

Actual commands:

```sh
PYTHONPATH=vendor/capital-decision-lab:adapters/cloud python3 -B -m unittest discover -s tests/portable -v
PYTHONPATH=vendor/capital-decision-lab:adapters/cloud python3 -B -m unittest discover -s tests/extraction -v
python3 -B scripts/bootstrap_portable.py --destination <new-bundle>
# Relocate the directory; invoke from unrelated cwd:
python3 -I <relocated>/portable.py doctor
python3 -I <relocated>/portable.py validate
python3 -I <relocated>/portable.py analyze --fixture --file valid/mvp-case.json
python3 -I <relocated>/portable.py compare --fixture --file valid/mvp-case.json
python3 -I <relocated>/portable.py demo --data-dir <private>
python3 -I <relocated>/portable.py render --data-dir <private> --file host-image-report.json --report-id workshop-cloud-synthetic
```

The real-image payload and generated reports are not committed. The image inspection receipt is a prior host attestation, not fresh pixel inspection by this extraction or cryptographic identity proof. No new image generation/model usage is claimed. Unit test PNGs remain synthetic test assets.

## Open / not established

- Full original upstream pytest regression: not run; pytest 9.0.2 installation approval is pending. Portable tests are not a substitute. The retained upstream engine pytest tests in this cloud tree also remain unrun. The cloud tree excludes 12 original desktop distribution/governance test files plus their vocabulary fixture; see the exact exclusion list. Those cases are not counted passed. A current full original-suite run requires the original tree and authorized test dependency.
- Browser visual/interaction QA: still open. Prior cloud Chromium socket creation failed before rendering; no bypass attempted. Static/JavaScript mock-DOM checks do not establish browser layout, accessibility, native keyboard, downloads or print.
- OAI native tool registration, Muse/Grok hosts, live financial providers, real-company acceptance, calibrated beliefs, scheduler setup/run and verified delivery/access remain untested or unimplemented.
- Publisher-wide noncollection, cloud retention/durability and platform permission enforcement are not established by offline code tests.
- Independent extraction review passed the bounded offline scope; see INDEPENDENT-REVIEW.md. Exact-commit publication remains a separate gate. Historical PR2 review/publication does not close these new gates.

Target environment: Linux, Python 3.12. No claims for macOS/native Windows runtime are made. Preserve the fixed ten-task board and report remaining gaps even after repository publication.
