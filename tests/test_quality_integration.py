from datetime import date

import pytest

from fintech_payments_dq.domain import RunConfig, Scenario
from fintech_payments_dq.pipeline import prepare_run
from fintech_payments_dq.quality import verify_contracts


@pytest.mark.parametrize(
    ("scenario", "expected_pass", "expected_failed_contract"),
    [
        (Scenario.GREEN, True, None),
        (Scenario.DUPLICATE_CAPTURE, False, "raw_payment_events.yml"),
        (Scenario.INVALID_STATE_TRANSITION, False, "payment_transactions.yml"),
        (Scenario.MISSING_MERCHANT, False, "raw_payment_events.yml"),
        (Scenario.REFUND_OVER_CAPTURE, False, "payment_transactions.yml"),
        (Scenario.LATE_EVENT, False, "raw_payment_events.yml"),
        (Scenario.UNBALANCED_LEDGER, False, "ledger_entries.yml"),
        (Scenario.SETTLEMENT_MISMATCH, False, "merchant_settlements.yml"),
        (Scenario.SCHEMA_DRIFT, False, "raw_payment_events.yml"),
    ],
)
def test_soda_quality_gate(run_paths, scenario, expected_pass, expected_failed_contract):
    config = RunConfig(scenario=scenario, as_of=date(2026, 10, 21), seed=42)
    prepare_run(config, run_paths)

    result = verify_contracts(config, run_paths)

    assert result.passed is expected_pass
    if expected_failed_contract:
        failed_contracts = {
            contract.contract for contract in result.contracts if not contract.passed
        }
        assert expected_failed_contract in failed_contracts
