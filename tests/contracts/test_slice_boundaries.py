from __future__ import annotations

from capital_decision_lab.contracts import authorization, ledger
from capital_decision_lab.orchestration import analyze, compare, record


def test_excluded_creation_and_execution_surfaces_do_not_exist() -> None:
    for module in (authorization, ledger, analyze, compare, record):
        assert not hasattr(module, "create_proposal")
        assert not hasattr(module, "create_authorization")
        assert not hasattr(module, "execute_trade")
        assert not hasattr(module, "fetch_live_data")
