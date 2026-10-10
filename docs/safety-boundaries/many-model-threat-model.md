> Historical engine threat model. Its desktop staging references are not shipped capabilities. Cloud extraction containment/inventory tests and the current private-data policy govern this distribution.

# Threat Model and Data Routing Policy — Many-Model Thinking Extension

Status: Authoritative security specification.  
Task: T04  
Primary Hero: `Nicholas Carlini`  
Verifier Hero: `Simon Willison`  

---

## 1. Threat Model & Adversarial Vector Analysis

The Many-Model Thinking extension introduces statistical and simulation diagnostics (Power Law, Markov, Bass diffusion, Bandits) and claim ensembling to stock investment decisions. Because input data originates from external unstructured sources (web scrapes, social feeds, filings, market snapshots), the architecture enforces defense-in-depth against the **lethal trifecta** (untrusted content + agent autonomy + sensitive local data).

### Core Security Invariants
1. **Hostile by Default:** All externally retrieved text (API payloads, web pages, social posts, OCR/broker extracts) is treated as attacker-controlled.
2. **Trust is Separate from Provenance:** An item may have provenance `measured` (retrieved from an API), but its `input_trust_class` remains `untrusted_external` until explicitly verified by the user.
3. **Calculation Layer Containment:** Pure Python standard library calculation modules have zero network egress, zero filesystem writes, and zero subprocess invocation capabilities.
4. **Injection Invariance:** Injected instructions inside data payloads cannot alter calculation outcomes. Injection-present and injection-absent runs with identical numeric inputs produce byte-identical canonical outputs.
5. **Strict Schema Gatekeeping:** Free text is length-bounded and regex-constrained; numeric inputs reject booleans, `NaN`, `+Infinity`, `-Infinity`, and out-of-domain values.

---

## 2. Trust-Class Matrix

Every model input contract (`nhi.model_input.v1`) must declare an explicit `input_trust_class`:

| Trust Class | Source / Origin | Calculation Permitted? | Promotion Requirement |
|---|---|---|---|
| `synthetic_test` | Committed test fixtures under `fixtures/` | Yes (test harnesses only) | Immutable test fixtures |
| `user_verified` | Extracted or manual data explicitly confirmed by user | Yes | User confirmation receipt (`nhi.host_user_confirmation.v1`) |
| `verified_local` | Deterministic outputs computed and stored locally under `local/` | Yes | Local cryptographic signature / hash verification |
| `untrusted_external` | Raw API, web scraper, X/Reddit, PDF/filing extracts | **No** (Rejected with `UNTRUSTED_INPUT_REJECTED`) | Must pass through user confirmation flow |

---

## 3. Model and Data-Clearance Matrix

Routing and intelligence boundaries governing task distribution and external model access:

| Execution Tier / Model | Clearance Level | Permitted Data Scope | Forbidden Data Scope |
|---|---|---|---|
| Local Root Planner (`sol` / local Python) | Full Local Private | Local portfolio, private theses, `.env`, credentials, raw local files | Egress to uncontained external networks |
| DeepSeek V4 Pro (`I4`) | Public & Synthetic Only | Published math formulas, synthetic fixtures, redacted contract shapes | Real portfolio holdings, private financial data, credentials, `.env` |
| Gemini 3.7 Flash (`I3`) | Public & Synthetic Only | Public docs, repository code structure, synthetic fixtures | Real portfolio holdings, private financial data, credentials, `.env` |
| Pure Deterministic Engine | Physical Air-Gap | Pure typed in-memory dictionaries and arrays | Network sockets, HTTP, subprocesses, filesystem scanning |

---

## 4. Threat-to-Test / Risk Mitigation Mapping

Every named threat vector maps directly to an automated verification test or a recorded risk in [`docs/council/risk_review.md`](private-data-policy.md):

| Threat Vector | Failure Mode | Mitigation Mechanism | Verification Test / Gate | Risk ID |
|---|---|---|---|---|
| **Prompt Injection** | Attacker smuggles instructions into market notes or filing text | Narrative text never reaches calculation code; schemas consume typed enums | `test_model_input_contract.py`, `test_injection_invariance.py` | MR-12, MR-16 |
| **Path Escape** | Directory traversal (`../`) to access root files or private data | Strict containment validation against approved root | `test_slice_boundaries.py`, `validate_contained_path` | MR-25 |
| **Hostile Numeric Types** | Boolean (`True`/`False`) passed where numbers expected | `_matches_type` rejects booleans for integer/number schemas | `test_model_input_contract.py` | MR-29 |
| **Nonfinite Values** | `NaN`, `Infinity` passed to corrupt Kelly/power-law math | Strict finite number check in validators and calculation modules | `test_power_law_rejection.py`, `test_markov_rejection.py` | MR-06, MR-29 |
| **Oversized Input / DoS** | Enormous matrices or million-item arrays causing timeouts | Fixed schema bounds (tail obs $\le 10,000$, Markov states $\le 64$, horizon $\le 100,000$) | `test_performance.py`, `test_ensemble_rejection.py` | MR-19, MR-31 |
| **Free-Text Smuggling** | Hostile instructions hidden in `reason` or `limitations` | Bounded strings, enum reason codes, no LLM interpretation of reasons | `test_ensemble_result_contract.py` | MR-17 |
| **Calculation Egress** | New calculation modules phoning home or fetching data | AST / static import scanner rejecting `socket`, `urllib`, `requests`, `subprocess` | `test_stdlib_no_egress.py` | MR-22 |
| **Private Data Leakage** | Staged distribution profile includes `local/` data | Staged profile scanner enforcing private path/sentinel exclusions | `check_staged_private_data.py`, `test_private_data_exclusion.py` | MR-24 |
