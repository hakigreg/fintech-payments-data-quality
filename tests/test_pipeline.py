from datetime import date

import duckdb

from fintech_payments_dq.domain import RunConfig, Scenario
from fintech_payments_dq.pipeline import prepare_run, publish_trusted_data


def _config(scenario: Scenario) -> RunConfig:
    return RunConfig(scenario=scenario, as_of=date(2026, 10, 21), seed=42)


def test_green_pipeline_builds_balanced_ledger(run_paths):
    prepare_run(_config(Scenario.GREEN), run_paths)
    connection = duckdb.connect(str(run_paths.database), read_only=True)

    unbalanced = connection.execute(
        """
        SELECT count(*)
        FROM (
            SELECT payment_id
            FROM trusted.ledger_entries
            GROUP BY payment_id
            HAVING abs(sum(CASE WHEN entry_type = 'debit' THEN amount ELSE -amount END)) > 0.001
        )
        """
    ).fetchone()[0]
    transaction_count = connection.execute(
        "SELECT count(*) FROM conformed.payment_transactions"
    ).fetchone()[0]
    connection.close()

    assert transaction_count == 120
    assert unbalanced == 0


def test_unbalanced_ledger_scenario_creates_one_failure(run_paths):
    prepare_run(_config(Scenario.UNBALANCED_LEDGER), run_paths)
    connection = duckdb.connect(str(run_paths.database), read_only=True)
    unbalanced = connection.execute(
        """
        SELECT count(*)
        FROM (
            SELECT payment_id
            FROM trusted.ledger_entries
            GROUP BY payment_id
            HAVING abs(sum(CASE WHEN entry_type = 'debit' THEN amount ELSE -amount END)) > 0.001
        )
        """
    ).fetchone()[0]
    connection.close()

    assert unbalanced == 1


def test_trusted_parquet_is_published_only_after_explicit_approval(run_paths):
    prepare_run(_config(Scenario.GREEN), run_paths)
    assert not (run_paths.trusted_root / "ledger_entries").exists()

    publish_trusted_data(run_paths)

    assert list((run_paths.trusted_root / "ledger_entries").rglob("*.parquet"))
    assert list((run_paths.trusted_root / "merchant_settlements").rglob("*.parquet"))
