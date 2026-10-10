"""Offline educational HTML adapter. It does not change any engine contract.

Only explicitly synthetic payloads are accepted by v1. Financial computations use
unchanged deterministic engine functions; synthetic assumptions remain modeled,
even when a legacy atom labels its arithmetic ``calculated``. A hash-authorized
script only selects frozen presentation strings. No network, provider call,
portfolio inference, financial-state mutation or order execution is performed.

An optional externally generated PNG requires provenance and an external pixel-
inspection attestation. Structural validation is not visual inspection or proof
of generation. The bundled fixture intentionally leaves that capability pending.
"""
from __future__ import annotations

import base64
import binascii
from datetime import date, datetime
import hashlib
from html import escape
import math
from pathlib import Path
import re
import struct
from urllib.parse import urlsplit
import zlib

from capital_decision_lab.calculations import convexity, returns, simulation
from capital_decision_lab.contracts.canonical import canonical_json, canonical_sha256

SCHEMA_VERSION = "portable-report.v1"
LENSES = (
    ("galloway", "Scott Galloway", "dlc-Galloway"),
    ("gerstner", "Brad Gerstner", "dlc-Gerstner"),
    ("camillo", "Chris Camillo", "dlc-camillo"),
    ("laffont", "Thomas and Philippe Laffont / Coatue", "dlc-laffont"),
    ("mauboussin", "Michael Mauboussin", "dlc-mauboussin"),
    ("buffett-munger", "Warren Buffett and Charlie Munger", "dlc-munger-buffett"),
    ("shkreli", "Martin Shkreli", "dlc-shkreli"),
    ("thorp", "Ed Thorp", "dlc-thorp"),
)
CANVAS = (
    "key-partnerships", "key-activities", "key-resources", "value-propositions",
    "customer-relationships", "channels", "customer-segments", "cost-structure", "revenue-streams",
)
POWERS = ("scale-economies", "network-economies", "counter-positioning", "switching-costs",
          "branding", "cornered-resource", "process-power")
SECTIONS = (
    ("takeaway", "Research takeaway"), ("portfolio", "Optional portfolio context"),
    ("business", "Business evidence"), ("valuation", "Valuation scenarios"),
    ("risk", "Risk and uncertainty"), ("perspectives-a", "Perspectives I"),
    ("perspectives-b", "Perspectives II and Page"), ("audit", "Sources and audit"),
    ("strategy", "Business model and Powers"), ("sketchnote", "Final sketchnote"),
)
ANATOMY = {
    "position": ("portfolio", "Optional position context"),
    "frameworks": ("strategy", "Porter, Helmer and canvas"),
    "bayes": ("business", "Evidence and Bayesian gate"),
    "sharpe": ("risk", "Sharpe, Kelly and survivability"),
    "engines": ("audit", "Deterministic engine provenance"),
    "convexity": ("valuation", "Conditional payoff asymmetry"),
    "simulation": ("risk", "Seeded modeled range"),
    "margin": ("risk", "Conditional margin stress"),
    "options": ("risk", "Dated option evidence"),
    "barbell": ("portfolio", "Exposure comparison context"),
    "dlc": ("perspectives-a", "Eight simulated analytical lenses"),
    "metrology": ("audit", "Usage and cost evidence"),
    "verdict": ("takeaway", "Research conclusion and change conditions"),
}
DISCLAIMER = (
    "Simulated analytical perspectives inspired by repository playbooks. These are not statements, "
    "advice, endorsements or participation by the named individuals or their firms."
)
LABELS = ("Measured", "Calculated", "Modeled", "Forecasted")
MAX_PNG_BYTES = 8 * 1024 * 1024


class ReportValidationError(ValueError):
    """A report would hide missing work, mislabel evidence or emit unsafe content."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ReportValidationError(message)


def _text(value, field: str, minimum: int = 1) -> str:
    _require(isinstance(value, str) and len(value.strip()) >= minimum, f"{field} requires substantive text")
    _require(len(value) <= 20000 and not any(ord(c) < 32 and c not in "\n\t" for c in value), f"{field} contains invalid text")
    _require(not re.search(r"^\s*(?:buy|sell|hold|add|trim)\s*[.!]?\s*$|\b(?:buy|sell|hold|add|trim)\s+(?:the\s+|your\s+|more\s+)?(?:shares?|stock|position|exposure)\b|\b(?:recommended|personalized|target)\s+(?:allocation|position\s+size)", value, re.I),
             f"{field} contains an action label or allocation instruction outside educational scope")
    _require(not re.search(r"\{\{[^}]+\}\}|\[INSERT\b|TODO\b", value), f"{field} contains unresolved template text")
    return value


def _fields(obj, fields: tuple[str, ...], path: str, minimum: int = 1) -> None:
    _require(isinstance(obj, dict), f"{path} must be an object")
    for field in fields:
        _text(obj.get(field), f"{path}.{field}", minimum)


def _date(value, path: str, optional: bool = False) -> None:
    if optional and value is None:
        return
    try:
        _require(isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is not None, f"{path} requires ISO date")
        date.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise ReportValidationError(f"{path} requires ISO date") from exc


def _timestamp(value, path: str) -> None:
    try:
        _require(isinstance(value, str), f"{path} requires timestamp")
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        _require(parsed.utcoffset() is not None, f"{path} requires timezone")
    except (ValueError, TypeError) as exc:
        raise ReportValidationError(f"{path} requires timestamp with timezone") from exc


def _inventory(items, expected, path: str) -> None:
    _require(isinstance(items, list) and all(isinstance(item, dict) for item in items), f"{path} must be an object list")
    actual = [item.get("id") for item in items]
    _require(len(actual) == len(expected) and all(isinstance(id, str) for id in actual) and set(actual) == set(expected), f"{path} must contain exactly {len(expected)} distinct required entries")


def _refs(obj: dict, ids: set[str], path: str) -> None:
    refs = obj.get("evidence_ids")
    _require(isinstance(refs, list) and refs and all(isinstance(r, str) and r in ids for r in refs), f"{path} requires valid evidence references")


def _url(value: str) -> None:
    _require(isinstance(value, str) and not re.search(r"[\x00-\x20\\]", value), "unsafe source URL")
    try:
        url = urlsplit(value)
        _require(url.scheme == "https" and bool(url.hostname) and not url.username and not url.password, "unsafe source URL")
        _require(url.port in (None, 443), "unexpected source URL port")
    except ValueError as exc:
        raise ReportValidationError("unsafe source URL") from exc


def _validate_png(encoded: str) -> bytes:
    """Accept a bounded, non-interlaced, 8-bit RGB/RGBA PNG with valid chunks."""
    _require(isinstance(encoded, str) and len(encoded) <= (MAX_PNG_BYTES * 4 // 3 + 8), "PNG exceeds size limit")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ReportValidationError("invalid PNG base64") from exc
    _require(len(raw) <= MAX_PNG_BYTES and raw.startswith(b"\x89PNG\r\n\x1a\n"), "invalid PNG signature or size")
    offset, names, packed, dimensions = 8, [], bytearray(), None
    while offset < len(raw):
        _require(offset + 12 <= len(raw), "truncated PNG chunk")
        length = struct.unpack_from("!I", raw, offset)[0]
        kind = raw[offset + 4:offset + 8]
        end = offset + 12 + length
        _require(end <= len(raw), "truncated PNG data")
        data = raw[offset + 8:offset + 8 + length]
        crc = struct.unpack_from("!I", raw, offset + 8 + length)[0]
        _require(zlib.crc32(kind + data) == crc, "invalid PNG CRC")
        names.append(kind)
        if kind == b"IHDR":
            _require(len(names) == 1 and length == 13, "invalid PNG IHDR")
            w, h, depth, colour, compression, filtering, interlace = struct.unpack("!IIBBBBB", data)
            _require(64 <= w <= 8192 and 64 <= h <= 8192 and w * h <= 24_000_000,
                     "PNG dimensions outside sketchnote limits")
            _require(depth == 8 and colour in (2, 6) and (compression, filtering, interlace) == (0, 0, 0),
                     "PNG requires non-interlaced 8-bit RGB/RGBA")
            dimensions = (w, h, 3 if colour == 2 else 4)
        elif kind == b"IDAT":
            packed.extend(data)
        elif kind == b"IEND":
            _require(length == 0 and end == len(raw), "invalid PNG ending")
        elif kind == b"acTL":
            raise ReportValidationError("animated PNG is unsupported")
        elif kind[:1].isupper() and kind != b"PLTE":
            raise ReportValidationError("unsupported critical PNG chunk")
        offset = end
    _require(names and names[0] == b"IHDR" and names[-1] == b"IEND" and names.count(b"IEND") == 1 and dimensions and packed,
             "incomplete PNG")
    indices = [i for i, name in enumerate(names) if name == b"IDAT"]
    _require(indices == list(range(indices[0], indices[-1] + 1)), "noncontiguous PNG image data")
    w, h, channels = dimensions
    expected = h * (w * channels + 1)
    try:
        inflater = zlib.decompressobj()
        pixels = inflater.decompress(bytes(packed), expected + 1)
        _require(inflater.eof and not inflater.unused_data and not inflater.unconsumed_tail and len(pixels) == expected,
                 "invalid PNG pixel data")
        _require(all(pixels[row * (w * channels + 1)] <= 4 for row in range(h)), "invalid PNG row filter")
    except zlib.error as exc:
        raise ReportValidationError("invalid PNG compression") from exc
    return raw


def _validate_sketchnote(doc: dict) -> None:
    image = doc.get("sketchnote")
    _fields(image, ("status", "alt", "caption"), "sketchnote")
    _require(image["status"] in ("pending", "provided"), "sketchnote.status requires pending or provided")
    rotation = image.get("rotation")
    _fields(rotation, ("report_id", "edition_date", "selected_lens", "reason"), "sketchnote.rotation")
    _require(rotation["report_id"] == doc["report_id"] and rotation["edition_date"] == doc["edition_date"], "rotation report identity mismatch")
    ids = [item[0] for item in LENSES]
    _require(rotation["selected_lens"] in ids and rotation.get("previous_lens") in [None, *ids], "rotation lens invalid")
    _require(type(rotation.get("index")) is int and rotation["index"] >= 0, "rotation index invalid")
    _fields(image.get("sqvid"), ("simple_elaborate", "quality_quantity", "vision_execution", "individual_comparison", "change_status_quo"), "sketchnote.sqvid", 20)
    _fields(image.get("text_equivalent"), ("who_what", "how_much", "where", "when", "how", "why"), "sketchnote.text_equivalent", 20)
    if image["status"] == "pending":
        _text(image.get("blocker"), "sketchnote.blocker", 30)
        _require(not image.get("png_base64") and not image.get("generation") and not image.get("inspection"), "pending image cannot claim completed generation or inspection")
        return
    generation = image.get("generation")
    _fields(generation, ("provider", "model", "generated_at", "artifact_id"), "sketchnote.generation")
    _require(generation.get("synthetic_test_asset") is False, "synthetic test asset cannot establish real generation; false means an actual externally generated raster, even when depicting a fictional company")
    _timestamp(generation["generated_at"], "generation.generated_at")
    inspection = image.get("inspection")
    _fields(inspection, ("inspector", "inspected_at"), "sketchnote.inspection")
    _timestamp(inspection["inspected_at"], "inspection.inspected_at")
    for check in ("attested", "legibility", "labels", "numbers", "scale", "causality", "text_equivalence"):
        _require(inspection.get(check) is True, f"external inspection attestation required: {check}")
    png = _validate_png(image.get("png_base64"))
    _require(inspection.get("image_sha256") == hashlib.sha256(png).hexdigest(), "inspection must identify exact PNG bytes")


def validate_report(doc: dict) -> None:
    """Validate the bounded synthetic educational contract; return None or raise."""
    _require(isinstance(doc, dict), "report must be an object")
    _require(doc.get("schema_version") == SCHEMA_VERSION, "unsupported report schema")
    _require(doc.get("synthetic") is True and doc.get("fixture_class") == "synthetic_public_educational", "v1 requires explicitly synthetic input")
    _require(not ({"recommendation", "action", "allocation", "portfolio", "holdings", "trade"} & set(doc)), "personalized/action fields are unsupported")
    try:
        canonical_json(doc)
    except (TypeError, ValueError) as exc:
        raise ReportValidationError("report must contain finite JSON values") from exc
    _fields(doc, ("report_id", "edition_date", "source_revision", "horizon", "information_cutoff", "deck", "scope_note"), "report")
    _require(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", doc["report_id"]) is not None, "report_id must be a safe identifier")
    _require(re.fullmatch(r"[0-9a-f]{40}", doc["source_revision"]) is not None, "source_revision requires full declared git revision")
    _date(doc["edition_date"], "edition_date")
    _date(doc["information_cutoff"], "information_cutoff")
    _fields(doc.get("company"), ("common_name", "ticker", "description"), "company")
    _fields(doc.get("takeaway"), ("conclusion", "uncertainty", "counterargument", "changes"), "takeaway", 30)
    sources = doc.get("sources")
    _require(isinstance(sources, list) and sources and all(isinstance(s, dict) for s in sources), "sources required")
    source_ids = set()
    for source in sources:
        _fields(source, ("id", "title", "kind", "scope"), "source")
        _require(source["id"] not in source_ids, "duplicate source id")
        _require(re.fullmatch(r"[A-Za-z0-9-]+", source["id"]) is not None, "unsafe source id")
        source_ids.add(source["id"])
        _require(source["kind"] in ("synthetic", "repository", "framework_reference"), "unsupported source kind")
        for field in ("publication_date", "as_of", "retrieved_on"):
            _require(field in source, f"source missing {field}")
            _date(source[field], f"source.{field}", optional=source["kind"] != "synthetic")
        if "url" in source:
            _url(source["url"])
    evidence = doc.get("evidence")
    _require(isinstance(evidence, list) and evidence and all(isinstance(e, dict) for e in evidence), "evidence required")
    ids = set()
    source_map = {s["id"]: s for s in sources}
    for item in evidence:
        _fields(item, ("id", "claim", "unit", "label", "source_id", "scope", "limitations"), "evidence")
        _require(re.fullmatch(r"[A-Za-z0-9-]+", item["id"]) is not None and item["id"] not in ids, "invalid/duplicate evidence id")
        ids.add(item["id"])
        _require(item["source_id"] in source_map, "unknown evidence source")
        _require(item["label"] in (*LABELS, "Narrative", "Unknown/unavailable"), "invalid evidence label")
        if source_map[item["source_id"]]["kind"] == "synthetic":
            _require(item["label"] in ("Modeled", "Forecasted", "Narrative", "Unknown/unavailable"), "synthetic financial evidence must not be labeled Measured or Calculated")
        for field in ("source_date", "as_of", "retrieved_on"):
            _date(item.get(field), f"evidence.{field}")
    _inventory(doc.get("lenses"), [item[0] for item in LENSES], "lenses")
    questions = set()
    for item in doc["lenses"]:
        identity = next(x for x in LENSES if x[0] == item["id"])
        _require((item.get("name"), item.get("source_path")) == identity[1:], "lens identity/source mismatch")
        _fields(item, ("rule", "question", "analysis", "dissent", "missing_input", "consequence"), "lens", 35)
        _require(item["question"] not in questions, "lens questions must be distinct")
        questions.add(item["question"])
        _refs(item, ids, "lens")
    _fields(doc.get("page_note"), ("rule", "analysis", "dissent", "consequence", "source_path"), "page_note")
    _require(doc["page_note"]["source_path"] == "dlc-page.md", "Page must be a separate sourced note")
    _refs(doc["page_note"], ids, "page_note")
    canvas = doc.get("canvas")
    _fields(canvas, ("scope",), "canvas", 30)
    _inventory(canvas.get("blocks"), CANVAS, "canvas.blocks")
    for item in canvas["blocks"]:
        _fields(item, ("name", "analysis", "attribution"), "canvas.block")
        _date(item.get("evidence_date"), "canvas.block.evidence_date")
        _refs(item, ids, "canvas.block")
    _inventory(doc.get("powers"), POWERS, "powers")
    for item in doc["powers"]:
        _fields(item, ("name",), "power")
        _fields(item, ("benefit", "barrier", "evidence", "analysis", "uncertainty", "strengthening_signal", "weakening_signal"), "power", 15)
        _date(item.get("evidence_date"), "power.evidence_date")
        _refs(item, ids, "power")
    porter = doc.get("porter")
    _require(isinstance(porter, list) and len(porter) == 5, "five Porter forces required")
    for item in porter:
        _fields(item, ("name", "analysis"), "Porter force")
        _refs(item, ids, "Porter force")
    _require(len({item["name"] for item in porter}) == 5, "Porter forces must be distinct")
    _inventory(doc.get("coverage"), ANATOMY, "coverage")
    for item in doc["coverage"]:
        _fields(item, ("section", "status", "reason", "consequence"), "coverage")
        _require(item["section"] == ANATOMY[item["id"]][0], "anatomy mapping mismatch")
        _require(item["status"] in ("completed", "unavailable", "not_run", "not_applicable"), "invalid coverage status")
    engine = doc.get("engine_inputs")
    _require(isinstance(engine, dict) and set(engine) == {"cash_flow", "convexity", "simulation"}, "three bounded synthetic engine input sets required")
    cash = engine["cash_flow"]
    _require(isinstance(cash, dict), "cash_flow must be an object")
    for key in ("operating_cash_flow", "capital_expenditure", "stock_based_compensation"):
        _require(type(cash.get(key)) in (int, float) and math.isfinite(cash[key]), f"cash_flow.{key} requires finite value")
    _require(cash.get("unit") == "USD million", "cash-flow fixture requires explicit USD million units")
    _require(isinstance(engine["convexity"], dict), "convexity inputs must be an object")
    scenarios = engine["convexity"].get("scenarios")
    _require(isinstance(scenarios, list) and len(scenarios) == 4 and all(isinstance(s, dict) for s in scenarios), "four payoff scenarios required")
    _require(all(isinstance(s.get("name"), str) for s in scenarios) and {s["name"] for s in scenarios} == {"bear", "base", "bull", "moonshot"}, "four named payoff scenarios required")
    for s in scenarios:
        for key in ("probability", "payoff", "return"):
            _require(type(s.get(key)) in (int, float), f"scenario.{key} requires numeric input")
        _require(isinstance(s.get("assumptions"), list) and s["assumptions"], "scenario assumptions required")
        for assumption in s["assumptions"]:
            _text(assumption, "scenario assumption")
    sim = engine["simulation"]
    _require(isinstance(sim, dict) and set(sim) == {"starting_value", "mean_return", "volatility", "periods", "iteration_count", "seed", "distribution_family"}, "simulation inputs mismatch")
    _require(type(sim["iteration_count"]) is int and 0 < sim["iteration_count"] <= 100_000, "simulation iteration bound exceeded")
    _require(type(sim["periods"]) is int and 0 < sim["periods"] <= 100 and sim["periods"] * sim["iteration_count"] <= 100_000, "simulation work bound exceeded")
    for key in ("starting_value", "mean_return", "volatility"):
        _require(type(sim[key]) in (int, float) and math.isfinite(sim[key]) and abs(sim[key]) <= 1e9, "simulation numeric input invalid")
    _require(abs(sim["mean_return"]) <= 1 and abs(sim["volatility"]) <= 2, "simulation illustration requires bounded return/volatility")
    _require(type(sim["seed"]) is int, "simulation seed must be integer")
    _require(sim["distribution_family"] == "normal", "only normal demonstration supported")
    _validate_sketchnote(doc)
    _fields(doc.get("qa"), ("automated", "browser", "assistive_technology", "image", "delivery"), "qa")


def build_engine_audit(payload: dict) -> dict:
    """Execute original engines on bounded synthetic inputs and retain raw atoms."""
    validate_report(payload)
    inputs = payload["engine_inputs"]
    cash = inputs["cash_flow"]
    first = {"starting_value": cash["capital_expenditure"], "ending_value": cash["operating_cash_flow"], "unit": cash["unit"]}
    before = returns.absolute_gain_loss(**first)
    second = {"starting_value": cash["stock_based_compensation"], "ending_value": before["value"], "unit": cash["unit"]}
    calls = [
        ("cash-flow", returns, "absolute_gain_loss", first, before),
        ("cash-flow-after-sbc", returns, "absolute_gain_loss", second, returns.absolute_gain_loss(**second)),
        ("convexity", convexity, "analyze_convexity", inputs["convexity"], convexity.analyze_convexity(inputs["convexity"])),
        ("simulation", simulation, "monte_carlo", inputs["simulation"], simulation.monte_carlo(**inputs["simulation"])),
    ]
    runs = []
    for id, module, function, given, output in calls:
        runs.append({
            "id": id, "call": f"{module.__name__}.{function}",
            "call_convention": "positional inputs dictionary" if id == "convexity" else "keyword arguments",
            "inputs": given, "raw_output": output, "input_sha256": canonical_sha256(given),
            "output_sha256": canonical_sha256(output),
            "source_sha256": hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest(),
            "source_module": module.__name__, "declared_fixture_source_revision": payload["source_revision"],
            "evidence_label": "Modeled · calculated in Python",
            "limitations": ["Invented inputs; no empirical calibration or personal exposure.",
                            "Raw engine atoms are unchanged. Calculated arithmetic inherits modeled input uncertainty.",
                            "Source hash identifies the executed module; a declared repository revision alone does not verify installed bytes."],
        })
    return {"schema_version": "portable-engine-audit.v1", "runs": runs,
            "bayesian_update": "not_run: no verified evidence, sensitivity rule, prior or likelihood",
            "kelly": "unavailable: no calibrated probabilities or user-selected constraints",
            "measured_api_cost": "unavailable: this renderer/engine makes no provider calls; external host image usage/cost receipts are unavailable, and generation metadata alone does not establish usage or cost"}


def _e(value) -> str:
    return escape(str(value), quote=True)


def _p(value: str, cls: str = "") -> str:
    return f'<p{f" class={chr(34)}{cls}{chr(34)}" if cls else ""}>{_e(value)}</p>'


def _definition(items) -> str:
    return '<dl>' + ''.join(f'<dt>{_e(label)}</dt><dd>{_e(value)}</dd>' for label, value in items) + '</dl>'


def _evidence_links(ids: list[str]) -> str:
    return '<p class="references">Evidence: ' + ', '.join(f'<a href="#evidence-{_e(id)}">{_e(id)}</a>' for id in ids) + '</p>'


def _table(caption: str, headers: list[str], rows: list[list]) -> str:
    return (f'<div class="table-region" role="region" aria-label="{_e(caption)}" tabindex="0"><table><caption>{_e(caption)}</caption><thead><tr>'
            + ''.join(f'<th scope="col">{_e(h)}</th>' for h in headers)
            + '</tr></thead><tbody>'
            + ''.join('<tr>' + ''.join((f'<th scope="row">{_e(c)}</th>' if i == 0 else f'<td>{_e(c)}</td>') for i, c in enumerate(row)) + '</tr>' for row in rows)
            + '</tbody></table></div>')


def _atom_value(atom: dict) -> str:
    if atom.get("provenance_class") == "unavailable":
        return "unavailable: " + str(atom.get("reason", "unsupported input domain"))
    value = atom.get("value")
    if isinstance(value, float):
        return format(value, ".10g")
    return str(value)


def _engine_table(title, atoms):
    return _table(title, ["Formula / field", "Result", "Units", "Evidence"], [
        [atom.get("formula_ref", name), _atom_value(atom), atom.get("unit", "unknown"),
         "Unknown/unavailable" if atom.get("provenance_class") == "unavailable" else "Modeled · calculated in Python"]
        for name, atom in atoms.items() if not isinstance(atom.get("value"), (dict, list))
    ])


SCENARIO_SCRIPT = r'''(() => {
  "use strict";
  const root = document.getElementById("scenario-explorer");
  const data = document.getElementById("scenario-data");
  const output = document.getElementById("scenario-readout");
  const reset = document.getElementById("scenario-reset");
  if (!root || !data || !output || !reset) return;
  const buttons = Array.from(root.querySelectorAll("button[data-scenario]"));
  const marks = Array.from(root.querySelectorAll("[data-scenario-mark]"));
  let records;
  try {
    const parsed = JSON.parse(data.textContent);
    if (!Array.isArray(parsed) || parsed.length !== buttons.length || !parsed.length) return;
    if (!parsed.every(item => typeof item.id === "string" && typeof item.text === "string")) return;
    records = Object.freeze(parsed.map(item => Object.freeze({id: item.id, text: item.text})));
  } catch (_) { return; }
  const initialText = output.textContent;
  function show(id) {
    const chosen = records.find(item => item.id === id) || null;
    buttons.forEach(button => button.setAttribute("aria-pressed", String(Boolean(chosen && button.getAttribute("data-scenario") === chosen.id))));
    marks.forEach(mark => mark.setAttribute("data-selected", String(Boolean(chosen && mark.getAttribute("data-scenario") === chosen.id))));
    output.textContent = chosen ? chosen.text : initialText;
  }
  buttons.forEach(button => {
    button.disabled = false;
    button.addEventListener("click", () => show(button.getAttribute("data-scenario")));
    button.addEventListener("keydown", event => {
      const focused = buttons.indexOf(event.currentTarget);
      let destination;
      if (event.key === "ArrowRight" || event.key === "ArrowDown") destination = (focused + 1) % buttons.length;
      else if (event.key === "ArrowLeft" || event.key === "ArrowUp") destination = (focused + buttons.length - 1) % buttons.length;
      else if (event.key === "Home") destination = 0;
      else if (event.key === "End") destination = buttons.length - 1;
      else return;
      event.preventDefault();
      buttons[destination].focus();
      show(buttons[destination].getAttribute("data-scenario"));
    });
  });
  reset.disabled = false;
  reset.addEventListener("click", () => show(null));
})();'''


def _scenario_explorer(scenarios: list[dict]) -> str:
    """Present validated frozen engine inputs; only pixel geometry is scaled here."""
    records = [{"id": item["name"], "text": (
        f'{item["name"].title()}: stipulated probability {item["probability"]} (decimal); '
        f'payoff {item["payoff"]} index units; return {item["return"]} (decimal). '
        f'Assumptions: {"; ".join(item["assumptions"])}. '
        'Synthetic scenario only; not calibrated, executable or a personal decision.'
    )} for item in scenarios]
    encoded = canonical_json(records).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    maximum = max(abs(item["payoff"]) for item in scenarios) or 1
    pixels_per_unit = 220 / maximum
    svg = ('<svg class="scenario-chart" viewBox="0 0 680 270" role="img" aria-labelledby="scenario-chart-title scenario-chart-description">'
           '<title id="scenario-chart-title">Four synthetic payoff scenarios</title>'
           '<desc id="scenario-chart-description">Zero is the shared baseline. Negative payoffs extend left and positive payoffs right on one linear index-unit scale. Bar widths show payoff size, not probability. Exact values and assumptions remain in the adjacent table.</desc>'
           '<line x1="365" x2="365" y1="32" y2="225" stroke="currentColor" stroke-width="1"/>'
           '<line x1="145" x2="585" y1="225" y2="225" stroke="currentColor" stroke-width="1"/>')
    for index, item in enumerate(scenarios):
        width = abs(item["payoff"]) * pixels_per_unit
        x = 365 - width if item["payoff"] < 0 else 365
        y = 45 + index * 44
        label_x = x - 8 if item["payoff"] < 0 else x + width + 8
        anchor = "end" if item["payoff"] < 0 else "start"
        svg += (f'<g data-scenario-mark="" data-scenario="{_e(item["name"])}" data-selected="false">'
                f'<text x="8" y="{y + 16}">{_e(item["name"].title())}</text>'
                f'<rect x="{x:.3f}" y="{y}" width="{width:.3f}" height="22"/>'
                f'<text x="{label_x:.3f}" y="{y + 16}" text-anchor="{anchor}">{_e(item["payoff"])}</text></g>')
    for x, number in ((145, -maximum), (365, 0), (585, maximum)):
        svg += f'<text x="{x}" y="246" text-anchor="middle">{_e(number)}</text>'
    svg += '<text x="365" y="268" text-anchor="middle">Synthetic payoff · index units</text></svg>'
    buttons = ''.join(f'<button type="button" data-scenario="{_e(item["name"])}" aria-controls="scenario-readout" aria-pressed="false" disabled>{_e(item["name"].title())}</button>' for item in scenarios)
    return ('<article id="scenario-explorer" class="card"><h3>Explore the frozen scenario assumptions</h3>'
            + _p("Select a case to highlight its existing bar and read its recorded assumptions. Nothing is recalculated. Use Tab, arrow keys, Home or End; Reset restores the all-cases view.", "muted")
            + svg + '<div class="scenario-controls" role="group" aria-label="Choose a frozen scenario">' + buttons
            + '<button id="scenario-reset" type="button" disabled>Reset</button></div>'
            + '<p id="scenario-readout" role="status" aria-live="polite" aria-atomic="true">All four stipulated cases remain visible. Select a case to read its assumptions; these are synthetic examples, not calibrated forecasts.</p>'
            + '<noscript><p>Interactive highlighting is unavailable without JavaScript. The full static chart, scenario table and assumptions remain readable.</p></noscript>'
            + f'<script type="application/json" id="scenario-data">{encoded}</script></article>')


CSS = """
:root{--paper:#fdfcf3;--ink:#211d1c;--rule:#c9c5b9;--accent:#ffc500}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font:18px/1.6 Georgia,'Times New Roman',serif}a{color:inherit;text-decoration-thickness:1px;text-underline-offset:3px}a:focus-visible,[tabindex]:focus-visible{outline:3px solid #9a6700;outline-offset:4px}.skip{position:absolute;left:-10000px}.skip:focus{position:static}.utility{padding:12px 5%;border-bottom:1px solid var(--ink);font:13px/1.4 Arial,sans-serif;letter-spacing:.1em}.wrap{max-width:1280px;margin:auto;padding:0 32px}.masthead{text-align:center;font-size:clamp(42px,8vw,88px);line-height:1.05;letter-spacing:-.04em;margin:36px 0 12px}.issue{text-align:center;font:13px/1.5 Arial,sans-serif;letter-spacing:.08em}.deck{font-size:clamp(22px,3vw,32px);line-height:1.3;max-width:950px;margin:32px auto}.nav{display:flex;flex-wrap:wrap;gap:0;border-block:1px solid var(--ink);padding:10px 0}.nav a{font:12px/1.5 Arial,sans-serif;text-transform:uppercase;letter-spacing:.05em;padding:8px 12px;border-right:1px solid var(--rule)}.status{padding:16px 20px;background:#fff5c7;border:1px solid var(--ink);margin:28px 0}.layout{display:grid;grid-template-columns:minmax(0,1fr) 280px;gap:40px}main{min-width:0}section{padding:30px 0;border-top:1px solid var(--ink);scroll-margin-top:12px}h2{font-size:32px;line-height:1.2;margin:10px 0 24px}h3{font-size:23px;line-height:1.3}h4{font-size:20px}.kicker,.tag{font:12px/1.4 Arial,sans-serif;letter-spacing:.07em;text-transform:uppercase}.tag{display:inline-block;border:1px solid var(--rule);padding:3px 7px}.muted,.references{font-size:15px;color:#514d43}.card,.lens-card,.power-card,.canvas-card{padding:22px;border:1px solid var(--rule);margin:18px 0;background:#fffef8}.card h3,.lens-card h3,.power-card h3,.canvas-card h3{margin-top:0}.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.cards>.canvas-card{margin:0}.canvas-card p{margin:12px 0}.sidebar{padding-top:30px}.sidebar .card{margin-top:0}.sidebar h2{font-size:22px}.sidebar p{font-size:16px}.sidebar .strip{background:var(--ink);color:var(--paper);padding:8px 12px;margin:-22px -22px 16px;font:13px Arial,sans-serif}dt{font:700 12px/1.5 Arial,sans-serif;text-transform:uppercase;letter-spacing:.06em;margin-top:18px}dd{margin:4px 0 0}table{width:100%;border-collapse:collapse;font-size:15px;line-height:1.5}caption{text-align:left;font:700 12px/1.4 Arial,sans-serif;text-transform:uppercase;letter-spacing:.06em;margin-bottom:12px}th,td{padding:10px;border-bottom:1px solid var(--rule);vertical-align:top;text-align:left}thead th{border-bottom:1px solid var(--ink)}.table-region{overflow-x:auto;margin:24px 0}.hash{overflow-wrap:anywhere;font:12px/1.6 monospace}.provenance{margin-bottom:30px}.download{display:inline-block;border:1px solid var(--ink);padding:10px 16px;font:14px Arial,sans-serif}.scenario-chart{width:100%;height:auto;max-height:340px;font:14px Arial,sans-serif}.scenario-chart rect{fill:var(--ink);stroke:var(--ink)}.scenario-chart [data-selected="true"] rect{fill:var(--accent);stroke-width:3}.scenario-controls{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0}.scenario-controls button{font:14px Arial,sans-serif;background:transparent;color:var(--ink);border:1px solid var(--ink);min-height:44px;padding:10px 16px;cursor:pointer}.scenario-controls button[aria-pressed="true"]{background:var(--accent);font-weight:bold}.scenario-controls button:focus-visible{outline:3px solid #9a6700;outline-offset:3px}.scenario-controls button:disabled{cursor:default;opacity:.55}.final-image{display:block;max-width:100%;height:auto}figure{margin:20px 0}figcaption{font-size:15px}footer{padding:30px 0;border-top:1px solid var(--ink);font:13px/1.6 Arial,sans-serif}li{margin:8px 0}p,dd,td,th{overflow-wrap:anywhere}pre{white-space:pre-wrap;word-break:break-word;font-size:12px}details{margin:18px 0}summary{cursor:pointer;font-size:16px}
@media(max-width:950px){.layout{grid-template-columns:1fr}.sidebar{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.sidebar .card{margin:0}}@media(max-width:600px){.wrap{padding:0 18px}.cards,.sidebar{grid-template-columns:1fr}body{font-size:17px}.nav a{padding:8px}h2{font-size:28px}.card,.lens-card,.power-card,.canvas-card{padding:18px}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}@media print{body{background:white;color:black;font-size:11pt}.wrap{max-width:none;padding:0}.layout{display:block}.sidebar{display:block}.nav,.skip,.download{display:none}section{break-before:auto}.lens-card,.power-card,.canvas-card{break-inside:avoid}a{text-decoration:none}.table-region{overflow:visible}details> *{display:block}.masthead{font-size:40pt}}
"""


def render_report(payload: dict) -> str:
    """Return a static, self-contained HTML reading edition. No state is written."""
    validate_report(payload)
    audit = build_engine_audit(payload)
    runs = {run["id"]: run for run in audit["runs"]}
    coverage = {item["id"]: item for item in payload["coverage"]}
    company = payload["company"]
    chunks = []

    def section(id, title, body):
        number = [key for key, _ in SECTIONS].index(id) + 1
        chunks.append(f'<section id="{id}" aria-labelledby="heading-{id}"><p class="kicker">{number:02d} / Reading edition</p><h2 id="heading-{id}">{_e(title)}</h2>{body}</section>')

    def missing(id):
        item = coverage[id]
        return f'<article id="{id}" class="card"><h3>{_e(ANATOMY[id][1])}</h3><span class="tag">{_e(item["status"].replace("_", " "))}</span>' + _definition([("Reason", item["reason"]), ("Research consequence", item["consequence"])]) + '</article>'

    takeaway = payload["takeaway"]
    section("takeaway", "Research takeaway", '<div id="verdict">' + _definition([
        ("Analytical conclusion", takeaway["conclusion"]), ("Main uncertainty", takeaway["uncertainty"]),
        ("Strongest counterargument", takeaway["counterargument"]), ("What changes the conclusion", takeaway["changes"])
    ]) + '</div>' + _p("General educational research only. Scenario outputs are not executable. No personal allocation or transaction is prescribed.", "status"))
    section("portfolio", "Optional portfolio context", _p("No holdings, account balances, leverage, risk tolerance or liquidity needs were supplied or inferred. Optional context must be separately authorized and verified.") + missing("position") + missing("barbell") + _p("If context is requested later, use a redacted CSV or screenshot with names and account identifiers removed. Missing importer fields must remain unavailable; no zero balances are invented.", "muted"))
    body = _p("No live company or market data were collected. Every company claim below is an invented fixture input; the source dates are synthetic effective dates, not real publication claims.")
    for item in payload["evidence"]:
        body += (f'<article class="card" id="evidence-{_e(item["id"])}"><span class="tag">{_e(item["label"])} · synthetic</span><h3>{_e(item["id"])}: {_e(item["claim"])}</h3>'
                 + _definition([("Units and scope", item["unit"] + "; " + item["scope"]), ("Synthetic source date / as of / recorded", f'{item["source_date"]} / {item["as_of"]} / {item["retrieved_on"]}'), ("Limitation", item["limitations"])])
                 + f'<p class="references"><a href="#source-{_e(item["source_id"])}">Source: {_e(item["source_id"])}</a></p></article>')
    body += missing("bayes") + _p("A formal Bayesian update was not run. Narrative reanalysis is not a computed posterior; no prior, likelihood or verified sensitivity gate has been invented.")
    section("business", "Business evidence and open questions", body)
    con = runs["convexity"]["raw_output"]
    body = '<div id="convexity">' + _p("Four stipulated one-year outcomes illustrate arithmetic on a fictional starting index of 100. Index units are not market prices. Probabilities are assumed, not calibrated. No current enterprise value, share count or discount-rate model is available.")
    body += _table("Four scenario inputs", ["Case", "Probability (decimal)", "Payoff (index units)", "Return (decimal)", "Assumption"], [[s["name"], s["probability"], s["payoff"], s["return"], '; '.join(s["assumptions"])] for s in payload["engine_inputs"]["convexity"]["scenarios"]])
    if con["scenario_table"].get("provenance_class") != "unavailable":
        body += _scenario_explorer(payload["engine_inputs"]["convexity"]["scenarios"])
    else:
        body += _p("Scenario exploration unavailable: the original engine rejected the scenario inputs; the input table and failure reason remain visible.")
    body += _engine_table("Original convexity engine output", con) + _p("The breakeven probability uses only the positive bull and negative bear payoffs; it is not the four-case posterior. Raw engine 'currency' units are mapped here to synthetic index units; no currency price is implied.", "muted") + '</div>'
    section("valuation", "Valuation and conditional payoff scenarios", body)
    sim = runs["simulation"]["raw_output"]
    body = missing("sharpe") + _p("Survivability cannot be assessed for a real person without verified obligations, liquidity, downside capacity and exposure inputs. Neither a modeled range nor a Kelly formula establishes suitability.")
    body += '<article id="simulation"><h3>Seeded Monte Carlo demonstration</h3>' + _table("Simulation parameters", ["Parameter", "Supplied value"], [[k, v] for k, v in payload["engine_inputs"]["simulation"].items()])
    body += _engine_table("Modeled normal range, not a forecast", sim["data"]) + _p("One-period normal draws are bounded at a total loss. Percentiles use the original engine's floor-index rule. Extreme tails, path dependence, regime changes and correlations are not modeled. Terminal 'currency' units are interpreted as normalized index units for this synthetic example.", "muted") + '</article>' + missing("margin") + missing("options")
    section("risk", "Risk, sensitivity and explicit missing inputs", body)
    lens_map = {item["id"]: item for item in payload["lenses"]}
    for part, keys in (("a", LENSES[:4]), ("b", LENSES[4:])):
        body = _p(DISCLAIMER, "muted")
        if part == "a":
            body += '<div id="dlc">' + _p("These are third-person educational interpretations of supplied secondary playbooks, not eight independent forecasts or executable engines. Each uses the same fictional evidence.") + '</div>'
        for key, _, _ in keys:
            item = lens_map[key]
            body += (f'<article class="lens-card" id="lens-{key}"><h3>{_e(item["name"])}</h3>' + _definition([
                ("Playbook rule", item["rule"]), ("Company question", item["question"]), ("Evidence-backed analysis (synthetic)", item["analysis"]),
                ("Dissent / contrary evidence", item["dissent"]), ("Missing input or abstention", item["missing_input"]), ("Research consequence", item["consequence"])
            ]) + _evidence_links(item["evidence_ids"]) + _p("Repository source: " + item["source_path"], "muted") + '</article>')
        if part == "b":
            note = payload["page_note"]
            body += '<article id="page-note" class="card"><h3>Scott Page: separate robustness note</h3>' + _definition([(k.replace('_', ' ').title(), note[k]) for k in ("rule", "analysis", "dissent", "consequence")]) + _evidence_links(note["evidence_ids"]) + _p("Not an additional independent vote. No ensemble probability, Page-engine result or formal diversity benefit is claimed. Repository source: dlc-page.md.", "muted") + '</article>'
        section("perspectives-" + part, "Four original analytical perspectives" if part == "a" else "Four remaining perspectives and Page", body)

    # Audit is deliberately before strategy and the final raster-image section.
    envelope = {"schema_version": "portable-report-audit.v1", "report_payload": payload,
                "report_payload_sha256": canonical_sha256(payload), "engine_audit": audit}
    audit_bytes = canonical_json(envelope).encode("utf-8")
    audit_hash = hashlib.sha256(audit_bytes).hexdigest()
    download = base64.b64encode(audit_bytes).decode("ascii")
    body = _p("This reading edition reorganizes the older thirteen-section anatomy; it does not claim the original fixed order. Every underlying component is mapped below with a reason and research consequence. A completed synthetic demonstration is not complete real-company research.")
    body += _table("Thirteen-component completeness ledger", ["Original component", "Reading destination", "Status", "Reason", "Consequence"], [[ANATOMY[item["id"]][1], item["section"], item["status"].replace('_', ' '), item["reason"], item["consequence"]] for item in payload["coverage"]])
    body += _table("Original sidebar mapping", ["Source component", "Educational reading equivalent", "Availability"], [
        ["Live Ticker", "Dated synthetic snapshot", "No live events or market feed"],
        ["Evidence Stack", "Four evidence labels and linked evidence records", "Synthetic assumptions distinguished from observations"],
        ["Portfolio donut", "Optional exposure context", "Unavailable; no invented holdings or proportions"],
        ["Discipline", "Research discipline", "Narrative research safeguard; no allocation rule"],
    ])
    body += '<article id="engines"><h3>Original deterministic engines: actually run</h3>' + _p("The functions below execute in the calling Python process. Their raw output contracts are retained unchanged in the audit; narrative lenses are not represented as executed engines.")
    for run in audit["runs"]:
        body += '<div class="provenance">' + _definition([("Call", run["call"]), ("Call convention", run["call_convention"]), ("Evidence", run["evidence_label"])])
        if run["id"].startswith("cash-flow"):
            label = "CFO less capex proxy" if run["id"] == "cash-flow" else "Separate SBC-adjusted sensitivity"
            body += _p(f'{label}: {_atom_value(run["raw_output"])} USD million. Formula: {run["raw_output"]["formula_ref"]}.')
        body += ''.join(_p(f'{label}: {run[field]}', "hash") for label, field in (("Input SHA-256", "input_sha256"), ("Output SHA-256", "output_sha256"), ("Executed source-module SHA-256", "source_sha256"))) + '</div>'
    body += _p("The USD 20 million CFO-less-capex proxy and USD 8 million separate SBC-adjusted sensitivity are not GAAP owner earnings. The SBC sensitivity is not another cash payment. Avoid counting dilution twice in any later valuation, and do not repeat a D&A adjustment already present in CFO.") + '</article>'
    body += (f'<a class="download" download="{_e(payload["report_id"])}-audit.json" href="data:application/json;base64,{download}">Download exact inputs and engine audit (JSON)</a>'
             + _p("Audit download SHA-256: " + audit_hash, "hash") + _p("Payload SHA-256: " + canonical_sha256(payload), "hash")
             + '<details><summary>Read audit JSON without downloading</summary><pre>' + _e(audit_bytes.decode("utf-8")) + '</pre></details>')
    body += missing("metrology")
    body += '<h3>Dated sources and scope</h3>'
    for source in payload["sources"]:
        title = _e(source["title"])
        if source.get("url"):
            title = f'<a href="{_e(source["url"])}" rel="noopener noreferrer">{title}</a>'
        body += (f'<article class="card" id="source-{_e(source["id"])}"><h4>{title}</h4>'
                 + _definition([("Kind", source["kind"]), ("Publication / as of / recorded", ' / '.join(source[k] or "unavailable / not consulted" for k in ("publication_date", "as_of", "retrieved_on"))), ("Scope", source["scope"])]) + '</article>')
    body += '<h3>Quality checks and delivery limits</h3>' + _definition([(key.replace('_', ' ').title(), value) for key, value in payload["qa"].items()])
    body += _p("No automatic network requests, external fonts, external scripts, remote images or trackers are included. The sole active script selects frozen scenario text and highlights existing marks; it cannot recalculate finance or persist state. Framework links activate only on reader action. The caller must verify private artifact access and any provider data flows; this renderer does not establish local-only processing by a host.", "muted")
    section("audit", "Sources, calculations and completeness", body)

    body = '<div id="frameworks"><h3>Core Business Model Canvas</h3>' + _p(payload["canvas"]["scope"]) + '<div class="cards">'
    for block in payload["canvas"]["blocks"]:
        body += f'<article class="canvas-card" id="canvas-{block["id"]}"><h3>{_e(block["name"])}</h3>' + _p(block["analysis"]) + _evidence_links(block["evidence_ids"]) + _p(f'{block["attribution"]} Effective date: {block["evidence_date"]}.', "muted") + '</article>'
    body += '</div><h3>Hamilton Helmer’s Seven Powers</h3>' + _p("Qualitative strategic hypotheses. Size, growth and margin alone do not establish durable Power. Missing evidence means unproven, not absent. No numerical moat score is invented.")
    for power in payload["powers"]:
        body += f'<article class="power-card" id="power-{power["id"]}"><h3>{_e(power["name"])}</h3>' + _definition([(label, power[field]) for label, field in (("Economic benefit", "benefit"), ("Imitation barrier", "barrier"), ("Dated evidence", "evidence"), ("Evidence effective date", "evidence_date"), ("Strategic analysis", "analysis"), ("Confidence and uncertainty", "uncertainty"), ("Strengthening signal", "strengthening_signal"), ("Weakening signal", "weakening_signal"))]) + _evidence_links(power["evidence_ids"]) + '</article>'
    body += _table("Porter: five-force evidence questions", ["Force", "Synthetic analysis", "Evidence IDs"], [[item["name"], item["analysis"], ', '.join(item["evidence_ids"])] for item in payload["porter"]]) + '</div>'
    section("strategy", "Business model and competitive durability", body)
    image = payload["sketchnote"]
    body = _p(DISCLAIMER, "muted")
    if image["status"] == "pending":
        body += '<div class="status"><h3>Image generation pending</h3>' + _p(image["blocker"]) + _p("The text equivalent below is useful planning material. It does not fulfill the required generated raster sketchnote.") + '</div>'
    else:
        width, height = struct.unpack_from("!II", base64.b64decode(image["png_base64"]), 16)
        body += f'<figure><img class="final-image" width="{width}" height="{height}" src="data:image/png;base64,{image["png_base64"]}" alt="{_e(image["alt"])}"><figcaption>{_e(image["caption"])}</figcaption></figure>'
        body += _p("External generation and pixel-inspection attestations were supplied for these exact bytes. The renderer validates PNG structure and required metadata; it does not itself generate or visually inspect the image.", "muted") + _definition([(f"Generation {key}", str(value)) for key, value in image["generation"].items()] + [(f"Inspection {key}", str(value)) for key, value in image["inspection"].items()])
    body += '<h3>Recorded visual lens and rotation</h3>' + _definition([(key.replace('_', ' ').title(), "none (first edition)" if value is None else str(value)) for key, value in image["rotation"].items()])
    body += '<h3>Dan Roam 6×5 planning choices</h3>' + _p("Six visual questions are covered by the text equivalent. SQVID selects a treatment; it does not require thirty panels. Conceptual relationships must be labeled conceptual, never represented as measured charts.") + _definition([(key.replace('_', ' / ').title(), value) for key, value in image["sqvid"].items()])
    body += '<h3>Complete accessible text equivalent</h3>' + _definition([(key.replace('_', ' / ').title(), value) for key, value in image["text_equivalent"].items()])
    section("sketchnote", "Final generated sketchnote and text equivalent", body)
    sidebar = '<aside class="sidebar" aria-label="Research context sidebar">'
    for id, title, text in (
        ("snapshot", "Dated snapshot, not live", f'Fixture cutoff: {payload["information_cutoff"]}. Edition: {payload["edition_date"]}. No live ticker, intraday events or invented market history.'),
        ("evidence", "Evidence stack at a glance", "Measured: no company measurements. Calculated: deterministic arithmetic only, inheriting modeled inputs. Modeled: fictional business data and engine outputs. Forecasted: stipulated future cases, not validated predictions."),
        ("exposure", "Optional exposure context", "Unavailable: no personal positions or account size. No portfolio donut, allocation percentage or ownership is inferred."),
        ("discipline", "Research discipline", "If the downside breaks the assumed research case, investigate it before emphasizing the upside. Preserve contrary evidence and abstentions. No personal trade or leverage instructions."),
    ):
        sidebar += f'<article id="sidebar-{id}" class="card"><p class="strip">{_e(title)}</p>' + _p(text) + '</article>'
    sidebar += '</aside>'
    nav = '<nav class="nav" aria-label="Report sections">' + ''.join(f'<a href="#{id}">{_e(title)}</a>' for id, title in SECTIONS) + '</nav>'
    boundary = "Edition incomplete: this is a bounded synthetic demonstration. " + ("The required generated image and pixel inspection are pending. " if image["status"] == "pending" else "External image metadata does not resolve missing real-company evidence or unrun host QA. ") + "Unavailable analysis and unverified browser/delivery checks remain visible below."
    script_hash = base64.b64encode(hashlib.sha256(SCENARIO_SCRIPT.encode("utf-8")).digest()).decode("ascii")
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'sha256-{script_hash}\'; img-src data:; style-src \'unsafe-inline\'; connect-src \'none\'; font-src \'none\'; base-uri \'none\'; form-action \'none\'">'
            f'<title>{_e(company["common_name"])} · Educational synthetic research</title><style>{CSS}</style></head><body>'
            '<a class="skip" href="#main">Skip to report</a><div class="utility">DECISION ≥ PREDICTION · EVIDENCE · SCENARIOS · UNCERTAINTY</div><div class="wrap"><header>'
            f'<h1 class="masthead">{_e(company["common_name"])}</h1>'
            + _p(f'{company["ticker"]} · {company["description"]} · {payload["edition_date"]} · {payload["report_id"]}', "issue")
            + _p(payload["deck"], "deck") + nav + _p(boundary, "status") + _p(payload["scope_note"]) + _p(payload["horizon"], "muted")
            + '</header><div class="layout"><main id="main">' + ''.join(chunks) + '</main>' + sidebar + '</div><footer>'
            + _e(f'{company["common_name"]} · {company["ticker"]} · {payload["edition_date"]} · General educational research. Declared fixture source revision: {payload["source_revision"]}.')
            + '</footer></div>' + f'<script id="scenario-controls-script">{SCENARIO_SCRIPT}</script></body></html>')
