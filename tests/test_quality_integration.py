from datetime import date

import pytest

from fintech_payments_dq.domain import RunConfig, Scenario
from fintech_payments_dq.pipeline import prepare_run
from fintech_payments_dq.quality import verify_contracts


@pytest.mark.parametrize(
    ("scenario", "expected_pass"),
    [
        (Scenario.GREEN, True),
        (Scenario.DUPLICATE_CAPTURE, False),
        (Scenario.INVALID_STATE_TRANSITION, False),
        (Scenario.MISSING_MERCHANT, False),
        (Scenario.REFUND_OVER_CAPTURE, False),
        (Scenario.LATE_EVENT, False),
        (Scenario.UNBALANCED_LEDGER, False),
        (Scenario.SETTLEMENT_MISMATCH, False),
        (Scenario.SCHEMA_DRIFT, False),
    ],
)
def test_soda_quality_gate(run_paths, scenario, expected_pass):
    config = RunConfig(scenario=scenario, as_of=date(2026, 10, 21), seed=42)
    prepare_run(config, run_paths)

    result = verify_contracts(config, run_paths)

    assert result.passed is expected_pass
