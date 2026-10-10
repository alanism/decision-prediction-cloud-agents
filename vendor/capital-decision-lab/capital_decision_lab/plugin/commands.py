"""Capital Decision Lab CLI boundary."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from capital_decision_lab.contracts.validation import validate_contract
from capital_decision_lab.contracts.canonical import contract_payload_hash
from capital_decision_lab.evidence.bayesian import build_belief_update
from capital_decision_lab.evidence.event_market import analyze_event_market
from capital_decision_lab.evidence.proposals import apply_approved_proposal, create_assumption_proposal
from capital_decision_lab.evidence.social import analyze_social
from capital_decision_lab.evidence.sensitivity import match_sensitivity
from capital_decision_lab.evidence.synthesis import synthesize_evidence
from capital_decision_lab.evidence.validation import validate_local_evidence
from capital_decision_lab.connectors.registry import ConnectorRegistry, RetrievalRequest
from capital_decision_lab.connectors.manual_input_connector import manual_capability
from capital_decision_lab.connectors.local_file_connector import file_import_capability
from capital_decision_lab.connectors.web_connector import retrieve_public_url
from capital_decision_lab.recommendation.engine import build_recommendation
from capital_decision_lab.recommendation.health import evaluate_model_health
from capital_decision_lab.recommendation.records import record_recommendation
from capital_decision_lab.research.loop import evaluate_research_readiness
from capital_decision_lab.research.portfolio import import_portfolio_file, validate_portfolio_snapshot
from capital_decision_lab.host.bridge import CAPABILITIES, analysis_eligibility, extract_source, ingest_capability_response
from capital_decision_lab.host.confirmation import apply_confirmation
from capital_decision_lab.host.confirmation_queue import build_confirmation_queue, pair_confirmation_responses
from capital_decision_lab.orchestration.analyze import analyze_case
from capital_decision_lab.orchestration.compare import compare_case
from capital_decision_lab.orchestration.record import record_from_files
from capital_decision_lab.orchestration.research_run import _load_confirmation_responses, _load_host_inputs, run_analyze_position
from capital_decision_lab.methods.runner import available_method_packs, run_committee, run_method_pack
from capital_decision_lab.privacy.containment import validate_contained_path


PROFILE_ROOT = Path(__file__).resolve().parents[4]
SYNTHETIC_CONTRACT_ROOT = PROFILE_ROOT / "fixtures" / "valid" / "contracts"


def doctor() -> tuple[int, dict]:
    """Engine-only compatibility diagnostic; no host discovery or registration."""
    return 0, {"command": "capital doctor", "status": "ok",
               "distribution_id": "decision-prediction-cloud-agents",
               "scope": "Vendored engine only; use portable.py doctor for cloud capabilities",
               "native_integration": False, "issues": [],
               "network_attempts": 0, "model_calls": 0}


def setup_cli(parser: argparse.ArgumentParser) -> None:
    """Build the internal compatibility command tree for regression tests."""
    subcommands = parser.add_subparsers(dest="capital_action", required=True)
    subcommands.add_parser("doctor")
    validate = subcommands.add_parser("validate")
    validate.add_argument("--synthetic", action="store_true", required=True)
    analyze = subcommands.add_parser("analyze")
    analyze.add_argument("--case", required=True)
    analyze.add_argument("--assumption-update")
    compare = subcommands.add_parser("compare")
    compare.add_argument("--case", required=True)
    record = subcommands.add_parser("record")
    record.add_argument("--analysis", required=True)
    record.add_argument("--authorization", required=True)
    evidence = subcommands.add_parser("evidence")
    evidence_actions = evidence.add_subparsers(dest="evidence_action", required=True)
    evidence_validate = evidence_actions.add_parser("validate")
    evidence_validate.add_argument("--file", required=True)
    for name in ("analyze-event-market", "analyze-polymarket"):
        event = evidence_actions.add_parser(name)
        event.add_argument("--snapshot", required=True)
    social = evidence_actions.add_parser("analyze-social")
    social.add_argument("--batch", required=True)
    synthesize = evidence_actions.add_parser("synthesize")
    synthesize.add_argument("--inputs", required=True)
    gather = evidence_actions.add_parser("gather")
    gather.add_argument("--case", required=True)
    gather.add_argument("--source", required=True)
    gather.add_argument("--query", required=True)
    inbox = evidence_actions.add_parser("inbox")
    inbox.add_argument("--case", required=True)
    inbox.add_argument("--folder", required=True)
    verify = evidence_actions.add_parser("verify")
    verify.add_argument("--item", required=True)
    belief = subcommands.add_parser("belief")
    belief_actions = belief.add_subparsers(dest="belief_action", required=True)
    update = belief_actions.add_parser("update")
    update.add_argument("--case", required=True)
    evidence_input = update.add_mutually_exclusive_group(required=True)
    evidence_input.add_argument("--synthesis")
    evidence_input.add_argument("--evidence")
    update.add_argument("--sensitivity", required=True)
    assumption = subcommands.add_parser("assumption")
    assumption_actions = assumption.add_subparsers(dest="assumption_action", required=True)
    propose = assumption_actions.add_parser("propose")
    propose.add_argument("--belief-update", required=True)
    portfolio = subcommands.add_parser("portfolio")
    portfolio_actions = portfolio.add_subparsers(dest="portfolio_action", required=True)
    for name in ("import", "validate"):
        command = portfolio_actions.add_parser(name)
        command.add_argument("--file", required=True)
    thesis = subcommands.add_parser("thesis")
    thesis_actions = thesis.add_subparsers(dest="thesis_action", required=True)
    thesis_start = thesis_actions.add_parser("start"); thesis_start.add_argument("--portfolio", required=True)
    thesis_refine = thesis_actions.add_parser("refine"); thesis_refine.add_argument("--case", required=True)
    research = subcommands.add_parser("research")
    research_actions = research.add_subparsers(dest="research_action", required=True)
    research_loop = research_actions.add_parser("loop"); research_loop.add_argument("--case", required=True)
    research_run = research_actions.add_parser("run"); research_run.add_argument("--case", required=True); research_run.add_argument("--host-inputs", required=True)
    analyze_position = subcommands.add_parser("analyze-position")
    analyze_position.add_argument("--case", required=True)
    analyze_position.add_argument("--host-inputs", required=True)
    analyze_position.add_argument("--method", default="core")
    method = subcommands.add_parser("method")
    method_actions = method.add_subparsers(dest="method_action", required=True)
    method_actions.add_parser("list")
    method_run = method_actions.add_parser("run"); method_run.add_argument("--pack", required=True); method_run.add_argument("--case", required=True)
    method_committee = method_actions.add_parser("committee"); method_committee.add_argument("--packs", required=True, nargs="+"); method_committee.add_argument("--case", required=True)
    confirmation = subcommands.add_parser("confirmation")
    confirmation_actions = confirmation.add_subparsers(dest="confirmation_action", required=True)
    confirmation_queue = confirmation_actions.add_parser("queue"); confirmation_queue.add_argument("--case", required=True); confirmation_queue.add_argument("--host-inputs", required=True)
    confirmation_apply = confirmation_actions.add_parser("apply"); confirmation_apply.add_argument("--queue", required=True); confirmation_apply.add_argument("--responses", required=True)
    confirmation_status = confirmation_actions.add_parser("status"); confirmation_status.add_argument("--case", required=True)
    model_health = subcommands.add_parser("model-health")
    health_actions = model_health.add_subparsers(dest="model_health_action", required=True)
    health_check = health_actions.add_parser("check"); health_check.add_argument("--case", required=True); health_check.add_argument("--evidence", required=True)
    recommend = subcommands.add_parser("recommend"); recommend.add_argument("--case", required=True)
    decision = subcommands.add_parser("decision")
    decision_actions = decision.add_subparsers(dest="decision_action", required=True)
    decision_record = decision_actions.add_parser("record"); decision_record.add_argument("--recommendation", required=True); decision_record.add_argument("--authorization", required=True)
    host = subcommands.add_parser("host")
    host_actions = host.add_subparsers(dest="host_action", required=True)
    host_actions.add_parser("capabilities")
    host_ingest = host_actions.add_parser("ingest"); host_ingest.add_argument("--capability-response", required=True)
    host_extract = host_actions.add_parser("extract"); host_extract.add_argument("--source", required=True, choices=["polymarket", "x_twitter", "reddit", "portfolio", "broker_margin", "manual_note"]); host_extract.add_argument("--input", required=True)
    host_confirm = host_actions.add_parser("confirm"); host_confirm.add_argument("--extraction", required=True); host_confirm.add_argument("--confirmation", required=True)


def _base(command: str) -> dict:
    return {"command": command, "network_attempts": 0, "model_calls": 0}


def _load_local_json(path: str, local_root: Path) -> tuple[dict | None, str | None]:
    check = validate_contained_path(local_root, Path(path))
    if not check["allowed"]:
        return None, check["issues"][0]["code"]
    try:
        value = json.loads(Path(check["resolved_path"]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, "LOCAL_DOCUMENT_INVALID"
    if not isinstance(value, dict):
        return None, "LOCAL_DOCUMENT_INVALID"
    return value, None


def _dispatch(args: argparse.Namespace, *, local_root: Path | None = None) -> tuple[int, dict]:
    action = args.capital_action
    if action == "doctor":
        return doctor()
    read_only_fixture_action = action == "validate" or (action == "method" and args.method_action == "list")
    if local_root is None and not read_only_fixture_action:
        return 2, {**_base("capital " + action), "status": "blocked",
                   "issues": [{"code": "EXPLICIT_DATA_ROOT_REQUIRED"}]}
    root = Path(local_root) if local_root is not None else PROFILE_ROOT
    if action == "method":
        command = f"capital method {args.method_action}"
        if args.method_action == "list":
            return 0, {**_base(command), "status": "ok", "issues": [], "method_packs": available_method_packs()}
        case, error = _load_local_json(args.case, root)
        if error:
            return 2, {**_base(command), "status": "failed", "issues": [{"code": error}]}
        try:
            if args.method_action == "run":
                result = run_method_pack(args.pack, case)
                return 0, {**_base(command), "status": "ok", "issues": [], "method_result": result}
            packs = [pack.strip() for item in args.packs for pack in item.split(",") if pack.strip()]
            result = run_committee(packs, case)
            return 0, {**_base(command), "status": "ok", "issues": [], "committee_result": result}
        except ValueError as exc:
            return 2, {**_base(command), "status": "failed", "issues": [{"code": str(exc)}]}
    if action == "confirmation":
        command = f"capital confirmation {args.confirmation_action}"
        if args.confirmation_action == "queue":
            case, error = _load_local_json(args.case, root)
            folder_check = validate_contained_path(root, Path(args.host_inputs))
            if error or not folder_check["allowed"]:
                return 2, {**_base(command), "status": "failed", "issues": [{"code": error}] if error else folder_check["issues"]}
            bundles, _, issues = _load_host_inputs(Path(folder_check["resolved_path"]))
            case_id = case.get("decision_case", case).get("case_id")
            if not case_id:
                return 2, {**_base(command), "status": "failed", "issues": [{"code": "CASE_ID_REQUIRED"}]}
            queue = build_confirmation_queue(case_id, bundles)
            return 0, {**_base(command), "status": "ok", "issues": issues, "confirmation_queue": queue}
        if args.confirmation_action == "apply":
            queue, error = _load_local_json(args.queue, root)
            folder_check = validate_contained_path(root, Path(args.responses))
            if error or not folder_check["allowed"]:
                return 2, {**_base(command), "status": "failed", "issues": [{"code": error}] if error else folder_check["issues"]}
            try:
                pairing = pair_confirmation_responses(queue, _load_confirmation_responses(Path(folder_check["resolved_path"])))
            except ValueError as exc:
                return 2, {**_base(command), "status": "failed", "issues": [{"code": str(exc)}]}
            return 0, {**_base(command), "status": "ok", "issues": [], "confirmation_pairing": pairing}
        case, error = _load_local_json(args.case, root)
        if error:
            return 2, {**_base(command), "status": "failed", "issues": [{"code": error}]}
        queue = case.get("confirmation_queue")
        if queue is None and case.get("confirmation_queue_path"):
            queue, error = _load_local_json(case["confirmation_queue_path"], root)
        if error:
            return 2, {**_base(command), "status": "failed", "issues": [{"code": error}]}
        pending = queue.get("pending_count", 0) if isinstance(queue, dict) else 0
        return 0, {**_base(command), "status": "pending" if pending else "resolved", "issues": [], "pending_count": pending, "confirmation_queue": queue}
    if action == "analyze-position":
        if args.method not in available_method_packs() or args.method == "committee":
            return 2, {**_base("capital analyze-position"), "status": "failed", "issues": [{"code": "METHOD_PACK_UNKNOWN"}]}
        document, error = _load_local_json(args.case, root)
        if error:
            return 2, {**_base("capital analyze-position"), "status": "failed", "issues": [{"code": error}]}
        folder_check = validate_contained_path(root, Path(args.host_inputs))
        if not folder_check["allowed"]:
            return 2, {**_base("capital analyze-position"), "status": "failed", "issues": folder_check["issues"]}
        folder = Path(folder_check["resolved_path"])
        if not folder.is_dir():
            return 2, {**_base("capital analyze-position"), "status": "failed", "issues": [{"code": "HOST_INPUT_FOLDER_INVALID"}]}
        result = run_analyze_position(document, folder)
        if result["status"] == "ok":
            try:
                result["method_result"] = run_method_pack(args.method, document, base_result=result)
            except ValueError as exc:
                return 2, {**_base("capital analyze-position"), "status": "failed", "issues": [{"code": str(exc)}]}
        return (0 if result["status"] == "ok" else 3), {**_base("capital analyze-position"), **result}
    if action == "host":
        if args.host_action == "capabilities":
            return 0, {**_base("capital host capabilities"), "status": "ok", "issues": [], "capabilities": list(CAPABILITIES)}
        if args.host_action == "ingest":
            document, error = _load_local_json(args.capability_response, root)
            if error:
                return 2, {**_base("capital host ingest"), "status": "failed", "issues": [{"code": error}]}
            try:
                ingested = ingest_capability_response(document)
            except ValueError as exc:
                return 2, {**_base("capital host ingest"), "status": "failed", "issues": [{"code": str(exc)}]}
            return 0, {**_base("capital host ingest"), "status": "ok", "issues": [], "host_response": ingested}
        if args.host_action == "extract":
            document, error = _load_local_json(args.input, root)
            if error:
                return 2, {**_base("capital host extract"), "status": "failed", "issues": [{"code": error}]}
            result = extract_source(args.source, document)
            code = 0 if result["status"] == "ok" else 3
            return code, {**_base("capital host extract"), **result}
        bundle, bundle_error = _load_local_json(args.extraction, root)
        confirmation, confirmation_error = _load_local_json(args.confirmation, root)
        error = bundle_error or confirmation_error
        if error:
            return 2, {**_base("capital host confirm"), "status": "failed", "issues": [{"code": error}]}
        try:
            confirmed = apply_confirmation(bundle, confirmation)
        except ValueError as exc:
            return 2, {**_base("capital host confirm"), "status": "failed", "issues": [{"code": str(exc)}]}
        return 0, {**_base("capital host confirm"), "status": "ok", "issues": [], "extraction_bundle": confirmed}
    if action == "portfolio":
        command = f"capital portfolio {args.portfolio_action}"
        if args.portfolio_action == "import":
            check = validate_contained_path(root, Path(args.file))
            if not check["allowed"]:
                return 2, {**_base(command), "status": "failed", "issues": check["issues"]}
            imported = import_portfolio_file(Path(check["resolved_path"]))
            code = 0 if imported["status"] == "ok" else 3
            return code, {**_base(command), **imported}
        document, error = _load_local_json(args.file, root)
        issues = [{"code": error}] if error else validate_portfolio_snapshot(document, root)
        return (0 if not issues else 2), {**_base(command), "status": "ok" if not issues else "failed", "issues": issues, "portfolio": document if not issues else None}
    if action == "thesis":
        path = args.portfolio if args.thesis_action == "start" else args.case
        document, error = _load_local_json(path, root)
        if error:
            return 2, {**_base(f"capital thesis {args.thesis_action}"), "status": "failed", "issues": [{"code": error}]}
        result = evaluate_research_readiness(document)
        return 3, {**_base(f"capital thesis {args.thesis_action}"), "status": "blocked_missing_user_input", "issues": [], "research_loop": result, "prompt": "Provide or refine the thesis, scenarios, probabilities, payoffs, catalysts, and kill conditions."}
    if action == "research":
        document, error = _load_local_json(args.case, root)
        if error:
            return 2, {**_base("capital research loop"), "status": "failed", "issues": [{"code": error}]}
        if args.research_action == "run":
            folder_check = validate_contained_path(root, Path(args.host_inputs))
            if not folder_check["allowed"]:
                return 2, {**_base("capital research run"), "status": "failed", "issues": folder_check["issues"]}
            folder = Path(folder_check["resolved_path"])
            if "decision_case" in document or "portfolio" in document or "thesis" in document:
                result = run_analyze_position(document, folder)
                return (0 if result["status"] == "ok" else 3), {**_base("capital research run"), **result}
            bundles = []
            try:
                bundles = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(folder.glob("*.json"))]
            except (OSError, json.JSONDecodeError):
                return 2, {**_base("capital research run"), "status": "failed", "issues": [{"code": "HOST_INPUT_INVALID"}]}
            if not bundles:
                return 3, {**_base("capital research run"), "status": "blocked_missing_user_input", "issues": [{"code": "HOST_INPUTS_REQUIRED"}]}
            eligibility = [analysis_eligibility(bundle.get("extraction", {})) for bundle in bundles]
            if any(not item["eligible"] for item in eligibility):
                return 3, {**_base("capital research run"), "status": "blocked_low_confidence", "issues": [issue for item in eligibility for issue in item["issues"]]}
        result = evaluate_research_readiness(document)
        code = 0 if result["status"] == "analysis_ready" else 3
        command = f"capital research {args.research_action}"
        return code, {**_base(command), "status": result["status"], "issues": [], "research_loop": result}
    if action == "model-health":
        case, case_error = _load_local_json(args.case, root)
        evidence, evidence_error = _load_local_json(args.evidence, root)
        error = case_error or evidence_error
        if error:
            return 2, {**_base("capital model-health check"), "status": "failed", "issues": [{"code": error}]}
        try:
            health = evaluate_model_health(**evidence)
        except (TypeError, ValueError):
            return 2, {**_base("capital model-health check"), "status": "failed", "issues": [{"code": "MODEL_HEALTH_INPUT_INVALID"}]}
        return 0, {**_base("capital model-health check"), "status": "ok", "issues": [], "model_health": health}
    if action == "recommend":
        case, error = _load_local_json(args.case, root)
        if error:
            return 2, {**_base("capital recommend"), "status": "failed", "issues": [{"code": error}]}
        try:
            recommendation = build_recommendation(case)
        except (KeyError, TypeError, ValueError):
            return 2, {**_base("capital recommend"), "status": "failed", "issues": [{"code": "RECOMMENDATION_INPUT_INVALID"}]}
        return 0, {**_base("capital recommend"), "status": "ok", "issues": [], "recommendation": recommendation}
    if action == "decision":
        recommendation, recommendation_error = _load_local_json(args.recommendation, root)
        authorization, authorization_error = _load_local_json(args.authorization, root)
        error = recommendation_error or authorization_error
        if error:
            return 2, {**_base("capital decision record"), "status": "failed", "issues": [{"code": error}]}
        result = record_recommendation(root / "ledger" / "recommendation-ledger.json", recommendation, authorization, local_root=root)
        return (0 if result["success"] else 2), {**_base("capital decision record"), "status": "ok" if result["success"] else "failed", **result}
    if action == "evidence":
        evidence_action = args.evidence_action
        if evidence_action == "gather":
            case, error = _load_local_json(args.case, root)
            if error:
                return 2, {**_base("capital evidence gather"), "status": "failed", "issues": [{"code": error}]}
            is_url = args.query.startswith(("http://", "https://"))
            is_file = args.source in {"local_file", "portfolio_file"} and not is_url
            request = RetrievalRequest(args.source, source_url=args.query if is_url else None, query=args.query, artifact_path=args.query if is_file else None, content=args.query)
            capabilities = {"manual": manual_capability} if args.source == "manual_note" else ({"scrape": retrieve_public_url} if request.source_url else {})
            if is_file:
                capabilities["file_import"] = file_import_capability(root)
            if request.source_url and args.source in {"polymarket", "reddit"} and ("api." in request.source_url or request.source_url.endswith(".json")):
                capabilities["api"] = retrieve_public_url
            try:
                gathered = ConnectorRegistry(capabilities).gather(request)
            except ValueError as exc:
                return 2, {**_base("capital evidence gather"), "status": "failed", "issues": [{"code": str(exc)}]}
            success = gathered["status"] == "ok"
            network_attempts = sum(attempt["method"] in {"api", "browser", "scrape"} for attempt in gathered["attempts"])
            return (0 if success else 3), {**_base("capital evidence gather"), "status": "ok" if success else gathered["status"], "issues": [], "evidence": gathered, "network_attempts": network_attempts}
        if evidence_action == "verify":
            document, error = _load_local_json(args.item, root)
            if error:
                return 2, {**_base("capital evidence verify"), "status": "failed", "issues": [{"code": error}]}
            verified = copy.deepcopy(document); verified["verification_status"] = "user_verified"
            return 0, {**_base("capital evidence verify"), "status": "ok", "issues": [], "verified_item": verified}
        if evidence_action == "inbox":
            _case, case_error = _load_local_json(args.case, root)
            if case_error:
                return 2, {**_base("capital evidence inbox"), "status": "failed", "issues": [{"code": case_error}]}
            folder_check = validate_contained_path(root, Path(args.folder))
            if not folder_check["allowed"]:
                return 2, {**_base("capital evidence inbox"), "status": "failed", "issues": folder_check["issues"]}
            folder = Path(folder_check["resolved_path"])
            files = [str(path) for path in sorted(folder.glob("*.json"))] if folder.is_dir() else []
            return 0, {**_base("capital evidence inbox"), "status": "ok", "issues": [], "files": files}
        option = "file" if evidence_action == "validate" else "snapshot" if evidence_action in {"analyze-event-market", "analyze-polymarket"} else "batch" if evidence_action == "analyze-social" else "inputs"
        document, error = _load_local_json(getattr(args, option), root)
        command = f"capital evidence {evidence_action}"
        if error:
            return 2, {**_base(command), "status": "failed", "issues": [{"code": error}]}
        try:
            if evidence_action == "validate":
                issues = validate_local_evidence(document, root)
                result = {"document_valid": not issues}
            elif evidence_action in {"analyze-event-market", "analyze-polymarket"}:
                issues = validate_local_evidence(document, root)
                result = {"signal": analyze_event_market(document)} if not issues else {}
            elif evidence_action == "analyze-social":
                issues = validate_local_evidence(document, root)
                result = {"signal": analyze_social(document)} if not issues else {}
            else:
                signals = document.get("signals")
                issues = [] if isinstance(signals, list) and signals else [{"code": "EVIDENCE_SIGNALS_REQUIRED", "path": "$.signals"}]
                result = {"synthesis": synthesize_evidence(signals)} if not issues else {}
        except (KeyError, TypeError, ValueError, OverflowError):
            issues = [{"code": "EVIDENCE_ANALYSIS_INPUT_INVALID", "path": "$"}]
            result = {}
        payload = {**_base(command), "status": "ok" if not issues else "failed", "issues": issues, **result}
        return (0 if not issues else 2), payload
    if action == "belief":
        belief, belief_error = _load_local_json(args.case, root)
        synthesis, synthesis_error = _load_local_json(args.synthesis or args.evidence, root)
        sensitivity, sensitivity_error = _load_local_json(args.sensitivity, root)
        error = belief_error or synthesis_error or sensitivity_error
        if error:
            return 2, {**_base("capital belief update"), "status": "failed", "issues": [{"code": error}]}
        try:
            if belief.get("contract_version") == "nhi.decision_case.v1":
                matched = match_sensitivity(synthesis, sensitivity)
                assumption_name = matched.get("affected_assumption")
                assumption_atom = belief.get("inputs", {}).get(assumption_name, {})
                prior = assumption_atom.get("value") if isinstance(assumption_atom, dict) else None
                if not isinstance(prior, (int, float)):
                    raise ValueError("BELIEF_PRIOR_UNAVAILABLE")
                case_hash = contract_payload_hash(belief)
                belief = {
                    "contract_version": "nhi.belief_state.v1",
                    "belief_id": f"belief_{belief['case_id']}_{assumption_name}",
                    "case_ref": belief["case_id"], "assumption": assumption_name,
                    "prior_probability": prior, "canonical_hash": case_hash,
                }
            update = build_belief_update(belief, synthesis, sensitivity)
        except (KeyError, TypeError, ValueError, OverflowError):
            return 2, {**_base("capital belief update"), "status": "failed", "issues": [{"code": "BELIEF_UPDATE_INPUT_INVALID"}]}
        return 0, {**_base("capital belief update"), "status": "ok", "issues": [], "belief_update": update}
    if action == "assumption":
        update, error = _load_local_json(args.belief_update, root)
        if error:
            return 2, {**_base("capital assumption propose"), "status": "failed", "issues": [{"code": error}]}
        try:
            proposal = create_assumption_proposal(update)
        except (KeyError, TypeError, ValueError):
            return 2, {**_base("capital assumption propose"), "status": "failed", "issues": [{"code": "ASSUMPTION_PROPOSAL_INPUT_INVALID"}]}
        return 0, {**_base("capital assumption propose"), "status": "ok", "issues": [], "proposal": proposal}
    if action == "validate":
        failures: dict[str, list] = {}
        fixtures = sorted(SYNTHETIC_CONTRACT_ROOT.glob("*.json"))
        for path in fixtures:
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
                issues = validate_contract(document)
            except (OSError, json.JSONDecodeError):
                issues = [{"code": "SYNTHETIC_FIXTURE_INVALID", "path": "$"}]
            if issues:
                failures[path.name] = issues
        payload = {
            **_base("capital validate"),
            "status": "ok" if not failures and fixtures else "failed",
            "validated_contracts": len(fixtures) - len(failures),
            "failures": failures,
            "issues": [] if not failures and fixtures else [{"code": "SYNTHETIC_VALIDATION_FAILED"}],
        }
        return (0 if payload["status"] == "ok" else 2), payload
    if action in {"analyze", "compare"}:
        case, error = _load_local_json(args.case, root)
        if error:
            return 2, {**_base(f"capital {action}"), "status": "failed", "issues": [{"code": error}]}
        contract_issues = validate_contract(case)
        if contract_issues:
            return 2, {**_base(f"capital {action}"), "status": "failed", "issues": contract_issues}
        if action == "analyze" and args.assumption_update:
            proposal, proposal_error = _load_local_json(args.assumption_update, root)
            if proposal_error:
                return 2, {**_base("capital analyze"), "status": "failed", "issues": [{"code": proposal_error}]}
            proposal_issues = validate_contract(proposal)
            if proposal_issues:
                return 2, {**_base("capital analyze"), "status": "failed", "issues": proposal_issues}
            case = apply_approved_proposal(case, proposal)
        try:
            result = analyze_case(case) if action == "analyze" else compare_case(case)
        except (TypeError, ValueError, OverflowError):
            return 2, {**_base(f"capital {action}"), "status": "failed", "issues": [{"code": "ORCHESTRATION_INPUT_INVALID"}]}
        key = "analysis" if action == "analyze" else "comparison"
        payload = {**_base(f"capital {action}"), "status": "ok", "issues": []}
        if action == "analyze":
            payload[key] = result
        else:
            payload.update(result)
        return 0, payload
    result = record_from_files(
        Path(args.analysis), Path(args.authorization), local_root=root
    )
    return (
        0 if result["success"] else 2,
        {
            **_base("capital record"),
            "status": "ok" if result["success"] else "failed",
            **result,
        },
    )


def run_cli(argv: list[str], *, local_root: Path | None = None) -> tuple[int, dict]:
    parser = argparse.ArgumentParser(prog="capital")
    setup_cli(parser)
    args = parser.parse_args(argv)
    return _dispatch(args, local_root=local_root)



def main(argv: list[str] | None = None) -> int:
    import sys

    exit_code, result = run_cli(list(sys.argv[1:] if argv is None else argv))
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
