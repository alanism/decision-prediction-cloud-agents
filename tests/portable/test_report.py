"""Portable reading edition: fail closed on missing analysis and false completion."""
from __future__ import annotations

import base64
import copy
from html.parser import HTMLParser
import json
import re
import shutil
import subprocess
from pathlib import Path
import struct
import zlib

import unittest

from decision_cloud.report import (
    ReportValidationError, build_engine_audit, render_report, validate_report,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures/portable/synthetic-report.json"


def payload():
    return json.loads(FIXTURE.read_text())


class Inventory(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.links = []
        self.images = []
        self.tags = []
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        self.tags.append(tag)
        if "id" in data:
            self.ids.append(data["id"])
        if tag == "a":
            self.links.append(data)
        if tag == "img":
            self.images.append(data)
        if tag == "script":
            self.scripts.append(data)


def test_synthetic_fixture_is_comprehensive_but_incomplete():
    doc = payload()
    validate_report(doc)
    rendered = render_report(doc)
    tree = Inventory()
    tree.feed(rendered)
    assert '<h1 class="masthead">Workshop Cloud</h1>' in rendered
    assert rendered.count('class="lens-card"') == 8
    assert rendered.count('class="power-card"') == 7
    assert rendered.count('class="canvas-card"') == 9
    assert 'id="page-note"' in rendered
    assert "Edition incomplete" in rendered
    assert "Image generation pending" in rendered
    assert not tree.images
    assert "Simulated analytical perspectives inspired by repository playbooks" in rendered
    assert "not eight independent forecasts" in rendered
    assert "formal Bayesian update was not run" in rendered
    assert "No live company or market data" in rendered
    assert "Scenario outputs are not executable" in rendered
    for label in ("Measured", "Calculated", "Modeled", "Forecasted"):
        assert label in rendered


def test_order_and_underlying_thirteen_sections_and_sidebar_are_mapped():
    html = render_report(payload())
    tree = Inventory()
    tree.feed(html)
    assert len(tree.ids) == len(set(tree.ids))
    for target in ("position", "frameworks", "bayes", "sharpe", "engines", "convexity",
                   "simulation", "margin", "options", "barbell", "dlc", "metrology", "verdict"):
        assert target in tree.ids
    assert tree.ids.index("audit") < tree.ids.index("strategy") < tree.ids.index("sketchnote")
    for target in ("sidebar-snapshot", "sidebar-evidence", "sidebar-exposure", "sidebar-discipline"):
        assert target in tree.ids
    for link in tree.links:
        if link.get("href", "").startswith("#"):
            assert link["href"][1:] in tree.ids
    assert html.index('href="#audit"') < html.index('href="#strategy"') < html.index('href="#sketchnote"')


MUTATIONS = [
    lambda p: p["lenses"].pop(),
    lambda p: p["lenses"].append(copy.deepcopy(p["lenses"][0])),
    lambda p: p["lenses"][0].update(analysis=""),
    lambda p: p["lenses"][0].update(evidence_ids=["missing"]),
    lambda p: p["lenses"][0].update(rule="A generic rule."),
    lambda p: p["lenses"][1].update(question=p["lenses"][0]["question"]),
    lambda p: p["canvas"]["blocks"].pop(),
    lambda p: p["powers"].pop(),
    lambda p: p["powers"][0].pop("barrier"),
    lambda p: p["powers"][0].pop("weakening_signal"),
    lambda p: p["powers"][0].update(evidence_date="yesterday"),
    lambda p: p["coverage"].pop(),
    lambda p: p["coverage"][0].update(reason=""),
    lambda p: p.update(synthetic=False),
    lambda p: p["takeaway"].update(conclusion="Buy shares now."),
    lambda p: p.update(recommendation="hold"),
    lambda p: p["sources"][0].update(url="javascript:alert(1)"),
    lambda p: p["sources"][0].update(url="https://user:secret@example.com/data"),
    lambda p: p["sources"][0].update(url="//example.com/pixel"),
    lambda p: p["evidence"][0].update(label="Measured"),
    lambda p: p["sketchnote"].update(status="complete"),
    lambda p: p["sketchnote"].pop("rotation"),
]

def _reject_invalid_mutation(mutation):
    doc = payload()
    mutation(doc)
    with unittest.TestCase().assertRaises(ReportValidationError):
        render_report(doc)


def test_renderer_escapes_text_and_has_no_active_assets_or_network():
    doc = payload()
    doc["company"]["common_name"] = '<img src=x onerror="alert(1)">'
    html = render_report(doc)
    tree = Inventory()
    tree.feed(html)
    assert "&lt;img src=x onerror=&quot;" in html
    assert not tree.images
    assert tree.scripts == [{"type": "application/json", "id": "scenario-data"}, {"id": "scenario-controls-script"}]
    assert "iframe" not in tree.tags
    assert "form" not in tree.tags
    assert "object" not in tree.tags
    assert "http-equiv=\"Content-Security-Policy\"" in html
    assert "default-src 'none'" in html
    assert "connect-src 'none'" in html
    assert 'rel="noopener noreferrer"' in html


def test_audit_runs_original_engines_preserves_bytes_hashes_and_inputs():
    from capital_decision_lab.calculations.convexity import analyze_convexity
    from capital_decision_lab.calculations.simulation import monte_carlo
    from capital_decision_lab.contracts.canonical import canonical_sha256
    doc = payload()
    before = copy.deepcopy(doc)
    audit = build_engine_audit(doc)
    assert doc == before
    assert audit == build_engine_audit(doc)
    by_id = {r["id"]: r for r in audit["runs"]}
    assert by_id["convexity"]["raw_output"] == analyze_convexity(doc["engine_inputs"]["convexity"])
    assert by_id["simulation"]["raw_output"] == monte_carlo(**doc["engine_inputs"]["simulation"])
    assert by_id["cash-flow"]["raw_output"]["value"] == 20
    assert by_id["cash-flow-after-sbc"]["raw_output"]["value"] == 8
    for run in audit["runs"]:
        assert run["input_sha256"] == canonical_sha256(run["inputs"])
        assert run["output_sha256"] == canonical_sha256(run["raw_output"])
        assert len(run["source_sha256"]) == 64
        assert run["evidence_label"] == "Modeled · calculated in Python"
        assert run["call"]
    html = render_report(doc)
    tree = Inventory()
    tree.feed(html)
    download = next(x for x in tree.links if x.get("download", "").endswith("-audit.json"))
    decoded = base64.b64decode(download["href"].split(",", 1)[1])
    assert json.loads(decoded)["engine_audit"] == audit
    assert json.loads(decoded)["report_payload"] == doc
    assert canonical_sha256(doc) in html


def test_invalid_engine_domain_remains_explicit_not_fabricated():
    doc = payload()
    doc["engine_inputs"]["convexity"]["scenarios"][0]["probability"] = 0.99
    html = render_report(doc)
    assert "probabilities must sum to one" in html
    assert "unavailable" in html.lower()
    assert 'id="scenario-explorer"' not in html
    assert "Scenario exploration unavailable" in html


def test_work_is_bounded_and_does_not_accept_nonfinite_or_huge_simulation():
    for key, value in (("iteration_count", 100_001), ("periods", 1001), ("mean_return", float("nan"))):
        doc = payload()
        doc["engine_inputs"]["simulation"][key] = value
        with unittest.TestCase().assertRaises(ReportValidationError):
            render_report(doc)


def _png():
    # Structural test asset, explicitly not an AI-generated or inspected sketchnote.
    def chunk(name, data):
        return struct.pack("!I", len(data)) + name + data + struct.pack("!I", zlib.crc32(name + data))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack("!IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\0\0\0\0")) + chunk(b"IEND", b""))


def test_embedded_png_requires_external_generation_and_actual_inspection_attestation():
    doc = payload()
    doc["sketchnote"].update(status="provided", png_base64=base64.b64encode(_png()).decode())
    with unittest.TestCase().assertRaisesRegex(ReportValidationError, "generation"):
        render_report(doc)
    doc["sketchnote"]["generation"] = {
        "provider": "Unit-test placeholder", "model": "Not a real model", "generated_at": "2026-10-10T00:00:00Z",
        "artifact_id": "structural-test-only", "synthetic_test_asset": True,
    }
    with unittest.TestCase().assertRaisesRegex(ReportValidationError, "synthetic test asset"):
        render_report(doc)


def test_malformed_png_and_false_inspection_are_rejected():
    doc = payload()
    doc["sketchnote"].update(status="provided", png_base64=base64.b64encode(b"not png").decode(),
        generation={"provider": "external", "model": "external", "generated_at": "2026-10-10T00:00:00Z", "artifact_id": "external-id", "synthetic_test_asset": False},
        inspection={"attested": False, "inspector": "external reviewer", "inspected_at": "2026-10-10T00:01:00Z", "legibility": True, "labels": True, "numbers": True, "scale": True, "causality": True, "text_equivalence": True})
    with unittest.TestCase().assertRaises(ReportValidationError):
        render_report(doc)


def test_incomplete_or_unsafe_contract_rejected():
    for mutation in MUTATIONS:
        _reject_invalid_mutation(mutation)


def test_malformed_collection_entries_raise_report_validation_error():
    for field in ("sources", "evidence", "lenses", "powers", "porter", "coverage"):
        for bad in (None, 7, [], {}, {"id": []}):
            doc = payload()
            doc[field][0] = bad
            with unittest.TestCase().assertRaises(ReportValidationError):
                render_report(doc)
    doc = payload()
    doc["engine_inputs"]["convexity"]["scenarios"][0]["name"] = []
    with unittest.TestCase().assertRaises(ReportValidationError):
        render_report(doc)


def test_ordinary_business_wording_is_not_an_action_label():
    doc = payload()
    doc["takeaway"]["conclusion"] = "The synthetic business may hold durable pricing power, but evidence remains unproven."
    doc["takeaway"]["changes"] = "Independent customer checks could add value to the research; important inputs are still missing."
    assert "hold durable pricing power" in render_report(doc)


def test_structural_png_validation_does_not_claim_generation():
    from decision_cloud.report import _validate_png
    def chunk(name, data):
        return struct.pack("!I", len(data)) + name + data + struct.pack("!I", zlib.crc32(name + data))
    raw = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack("!IIBBBBB", 64, 64, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress((b"\0" + b"\0" * 192) * 64)) + chunk(b"IEND", b""))
    assert _validate_png(base64.b64encode(raw).decode()) == raw
    with unittest.TestCase().assertRaises(ReportValidationError):
        _validate_png(base64.b64encode(raw[:-1] + b"x").decode())
    # Parser acceptance only. This handcrafted asset is never reported as generated.
    doc = payload()
    doc["sketchnote"].update(status="provided", png_base64=base64.b64encode(raw).decode(),
        generation={"provider":"unit test", "model":"none", "artifact_id":"parser-only", "generated_at":"2026-10-10T00:00:00Z", "synthetic_test_asset":True})
    with unittest.TestCase().assertRaisesRegex(ReportValidationError, "synthetic test asset"):
        render_report(doc)


def test_frozen_scenario_controls_have_static_fallback_and_exact_csp_script():
    from decision_cloud.report import SCENARIO_SCRIPT
    import hashlib
    html = render_report(payload())
    assert '<svg class="scenario-chart"' in html
    assert 'aria-labelledby="scenario-chart-title scenario-chart-description"' in html
    assert 'Zero is the shared baseline' in html
    assert html.count('data-scenario="') == 8  # four controls plus four existing chart marks
    assert html.count('aria-pressed="false"') == 4
    assert 'id="scenario-readout" role="status" aria-live="polite" aria-atomic="true"' in html
    assert 'id="scenario-reset" type="button" disabled' in html
    assert '<noscript>' in html
    assert "Four scenario inputs" in html  # full table remains with JS unavailable
    digest = base64.b64encode(hashlib.sha256(SCENARIO_SCRIPT.encode()).digest()).decode()
    assert f"script-src 'sha256-{digest}'" in html
    script = re.search(r'<script id="scenario-controls-script">(.*?)</script>', html, re.S).group(1)
    assert script == SCENARIO_SCRIPT
    for forbidden in ("fetch(", "XMLHttpRequest", "localStorage", "sessionStorage", "innerHTML", "eval(", "document.cookie", "WebSocket", "Math."):
        assert forbidden not in script
    data = json.loads(re.search(r'<script type="application/json" id="scenario-data">(.*?)</script>', html, re.S).group(1))
    assert [item["id"] for item in data] == ["bear", "base", "bull", "moonshot"]
    assert all(set(item) == {"id", "text"} and isinstance(item["text"], str) for item in data)


def test_frozen_scenario_json_cannot_break_out_of_inert_script():
    doc = payload()
    doc["engine_inputs"]["convexity"]["scenarios"][0]["assumptions"] = ['</script><img src=x onerror="alert(1)">']
    html = render_report(doc)
    tree = Inventory()
    tree.feed(html)
    assert not tree.images
    assert len(tree.scripts) == 2
    data_text = re.search(r'<script type="application/json" id="scenario-data">(.*?)</script>', html, re.S).group(1)
    assert "</script>" not in data_text and "<img" not in data_text
    assert '</script><img' in json.loads(data_text)[0]["text"]


def test_scenario_javascript_keyboard_uses_focus_and_reset_is_deterministic():
    from decision_cloud.report import SCENARIO_SCRIPT
    node = shutil.which("node")
    if not node:
        raise unittest.SkipTest("Node unavailable; actual JavaScript contract test not run")
    html = render_report(payload())
    records = json.loads(re.search(r'<script type="application/json" id="scenario-data">(.*?)</script>', html, re.S).group(1))
    harness = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
const {script, records} = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
let focused = null;
class Element {
  constructor(id) { this.attributes = {'data-scenario': id, 'aria-pressed':'false'}; this.disabled = true; this.events = {}; this.textContent = ''; }
  setAttribute(k,v) { this.attributes[k] = v; }
  getAttribute(k) { return this.attributes[k]; }
  addEventListener(k,fn) { this.events[k] = fn; }
  focus() { focused = this; }
  click() { this.events.click({currentTarget:this}); }
  key(key) { let prevented = false; this.events.keydown({key,currentTarget:this,preventDefault(){prevented=true;}}); return prevented; }
}
const buttons = records.map(x=>new Element(x.id));
const marks = records.map(x=>new Element(x.id));
const reset = new Element('reset');
const output = new Element('output'); output.textContent = 'All four stipulated cases remain visible.';
const initial = output.textContent;
const data = {textContent:JSON.stringify(records)};
const root = {querySelectorAll(selector){return selector === 'button[data-scenario]' ? buttons : marks;}};
const document = {getElementById(id){ return {'scenario-explorer':root,'scenario-data':data,'scenario-readout':output,'scenario-reset':reset}[id] || null; }};
const original = JSON.stringify(records);
vm.runInNewContext(script, {document});
assert(buttons.every(x=>x.disabled === false)); assert.equal(reset.disabled,false);
buttons[0].click(); assert.equal(output.textContent,records[0].text); assert.equal(buttons[0].attributes['aria-pressed'],'true');
// Selected index is zero; focus index is two. ArrowRight must move to three.
buttons[2].focus(); assert.equal(buttons[2].key('ArrowRight'),true);
assert.equal(focused,buttons[3]); assert.equal(output.textContent,records[3].text);
assert.deepEqual(buttons.map(x=>x.attributes['aria-pressed']), ['false','false','false','true']);
assert.equal(marks[3].attributes['data-selected'],'true');
buttons[3].key('ArrowRight'); assert.equal(focused,buttons[0]);
buttons[0].key('ArrowLeft'); assert.equal(focused,buttons[3]);
buttons[0].key('ArrowDown'); assert.equal(focused,buttons[1]);
buttons[1].key('ArrowUp'); assert.equal(focused,buttons[0]);
buttons[2].key('Home'); assert.equal(focused,buttons[0]);
buttons[0].key('End'); assert.equal(focused,buttons[3]);
assert.equal(buttons[0].key('Tab'),false);
reset.click(); assert.equal(output.textContent,initial); assert(buttons.every(x=>x.attributes['aria-pressed']==='false'));
assert(marks.every(x=>x.attributes['data-selected']==='false'));
reset.click(); assert.equal(output.textContent,initial);
// Altering the inert source after initialization cannot change the frozen snapshot.
data.textContent = '[]'; buttons[1].click(); assert.equal(output.textContent,records[1].text);
assert.equal(JSON.stringify(records),original);
console.log('Frozen scenario controls: click, focus-based arrows, wrap, Home/End, Reset, immutable snapshot passed.');
"""
    result = subprocess.run([node, "-e", harness], input=json.dumps({"script":SCENARIO_SCRIPT,"records":records}), text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    assert "immutable snapshot passed" in result.stdout


def test_cost_provenance_does_not_infer_whole_workflow_provider_usage():
    message = build_engine_audit(payload())["measured_api_cost"]
    assert "renderer/engine" in message
    assert "host image" in message
    assert "generation metadata" in message
    assert "no provider usage receipt or API call" not in message


class PortableReportTests(unittest.TestCase):
    pass


for name, function in list(globals().items()):
    if name.startswith("test_") and callable(function):
        setattr(PortableReportTests, name, staticmethod(function))

del name, function

if __name__ == "__main__":
    unittest.main()
