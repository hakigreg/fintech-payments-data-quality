from datetime import date

import duckdb

from fintech_payments_dq.domain import RunConfig, Scenario
from fintech_payments_dq.generator import generate_raw_data


def test_generation_is_deterministic(run_paths):
    config = RunConfig(scenario=Scenario.GREEN, as_of=date(2026, 10, 21), seed=42)
    generate_raw_data(config, run_paths)

    glob = str(run_paths.raw_root / "payment_events" / "**" / "*.parquet")
    connection = duckdb.connect(":memory:")
    first = connection.execute(
        "SELECT count(*), sum(amount) FROM read_parquet(?, hive_partitioning = true)", [glob]
    ).fetchone()

    second_paths = type(run_paths)(
        **{
            **run_paths.__dict__,
            "run_root": run_paths.run_root.parent / "second",
            "lake_root": run_paths.run_root.parent / "second" / "data-lake",
            "raw_root": run_paths.run_root.parent / "second" / "data-lake" / "raw",
            "conformed_root": run_paths.run_root.parent / "second" / "data-lake" / "conformed",
            "trusted_root": run_paths.run_root.parent / "second" / "data-lake" / "trusted",
            "quarantine_root": run_paths.run_root.parent / "second" / "data-lake" / "quarantine",
            "evidence_root": run_paths.run_root.parent / "second" / "evidence",
            "database": run_paths.run_root.parent / "second" / "fintech.duckdb",
            "data_source_config": run_paths.run_root.parent / "second" / "duckdb.yml",
        }
    )
    second_paths.create()
    generate_raw_data(config, second_paths)
    second_glob = str(second_paths.raw_root / "payment_events" / "**" / "*.parquet")
    second = connection.execute(
        "SELECT count(*), sum(amount) FROM read_parquet(?, hive_partitioning = true)",
        [second_glob],
    ).fetchone()

    assert first == second


def test_duplicate_capture_scenario_injects_financial_duplicate(run_paths):
    config = RunConfig(
        scenario=Scenario.DUPLICATE_CAPTURE,
        as_of=date(2026, 10, 21),
        seed=42,
    )
    generate_raw_data(config, run_paths)
    glob = str(run_paths.raw_root / "payment_events" / "**" / "*.parquet")
    connection = duckdb.connect(":memory:")

    duplicate_count = connection.execute(
        """
        SELECT count(*)
        FROM (
            SELECT payment_id
            FROM read_parquet(?, hive_partitioning = true)
            WHERE event_type = 'captured'
            GROUP BY payment_id
            HAVING count(*) > 1
        )
        """,
        [glob],
    ).fetchone()[0]

    assert duplicate_count == 1
