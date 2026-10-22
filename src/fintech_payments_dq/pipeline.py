from __future__ import annotations

import shutil
from pathlib import Path

import duckdb

from .domain import RunConfig, Scenario
from .generator import generate_raw_data
from .paths import RunPaths


def prepare_run(config: RunConfig, paths: RunPaths) -> None:
    if paths.run_root.exists():
        shutil.rmtree(paths.run_root)
    paths.create()
    generate_raw_data(config, paths)
    _build_database(config, paths)
    _export_pre_quality_layers(paths)
    _write_data_source_config(paths)


def publish_trusted_data(paths: RunPaths) -> None:
    connection = duckdb.connect(str(paths.database), read_only=True)
    try:
        ledger_path = _sql_path(paths.trusted_root / "ledger_entries")
        settlement_path = _sql_path(paths.trusted_root / "merchant_settlements")
        connection.execute(
            f"""
            COPY trusted.ledger_entries TO '{ledger_path}' (
                FORMAT PARQUET,
                PARTITION_BY (accounting_date),
                OVERWRITE_OR_IGNORE TRUE
            )
            """
        )
        connection.execute(
            f"""
            COPY trusted.merchant_settlements TO '{settlement_path}' (
                FORMAT PARQUET,
                PARTITION_BY (settlement_date),
                OVERWRITE_OR_IGNORE TRUE
            )
            """
        )
    finally:
        connection.close()


def _build_database(config: RunConfig, paths: RunPaths) -> None:
    connection = duckdb.connect(str(paths.database))
    try:
        connection.execute("CREATE SCHEMA raw")
        connection.execute("CREATE SCHEMA conformed")
        connection.execute("CREATE SCHEMA trusted")
        connection.execute("CREATE SCHEMA quality")

        merchants_path = _sql_path(paths.raw_root / "merchants.parquet")
        events_glob = _sql_path(paths.raw_root / "payment_events" / "**" / "*.parquet")
        connection.execute(
            f"CREATE TABLE raw.merchants AS SELECT * FROM read_parquet('{merchants_path}')"
        )
        connection.execute(
            f"""
            CREATE TABLE raw.payment_events AS
            SELECT *
            FROM read_parquet('{events_glob}', hive_partitioning = true)
            """
        )

        connection.execute(
            """
            CREATE TABLE conformed.payment_transactions AS
            WITH event_rollup AS (
                SELECT
                    payment_id,
                    arg_min(merchant_id, event_timestamp) AS merchant_id,
                    arg_min(currency, event_timestamp) AS currency,
                    min(event_timestamp) AS initiated_at,
                    min(event_timestamp) FILTER (WHERE event_type = 'authorized') AS authorized_at,
                    min(event_timestamp) FILTER (WHERE event_type = 'captured') AS captured_at,
                    min(event_timestamp) FILTER (WHERE event_type = 'declined') AS declined_at,
                    max(event_timestamp) FILTER (WHERE event_type = 'refunded') AS last_refund_at,
                    max(amount) FILTER (WHERE event_type = 'captured') AS captured_amount,
                    coalesce(sum(amount) FILTER (WHERE event_type = 'refunded'), 0)::DECIMAL(18, 2)
                        AS refunded_amount,
                    count(*) FILTER (WHERE event_type = 'initiated') AS initiated_count,
                    count(*) FILTER (WHERE event_type = 'authorized') AS authorization_count,
                    count(*) FILTER (WHERE event_type = 'captured') AS capture_count,
                    count(*) FILTER (WHERE event_type = 'declined') AS decline_count,
                    count(*) FILTER (WHERE event_type = 'refunded') AS refund_count
                FROM raw.payment_events
                GROUP BY payment_id
            )
            SELECT
                e.payment_id,
                e.merchant_id,
                e.currency,
                CASE
                    WHEN e.refund_count > 0
                        AND e.refunded_amount >= e.captured_amount THEN 'refunded'
                    WHEN e.refund_count > 0 THEN 'partially_refunded'
                    WHEN e.capture_count > 0 THEN 'captured'
                    WHEN e.decline_count > 0 THEN 'declined'
                    WHEN e.authorization_count > 0 THEN 'authorized'
                    ELSE 'initiated'
                END::VARCHAR AS payment_status,
                e.initiated_at,
                e.authorized_at,
                e.captured_at,
                e.declined_at,
                e.last_refund_at,
                e.captured_amount::DECIMAL(18, 2) AS captured_amount,
                e.refunded_amount::DECIMAL(18, 2) AS refunded_amount,
                round(e.captured_amount * m.fee_rate, 2)::DECIMAL(18, 2) AS fee_amount,
                e.initiated_count,
                e.authorization_count,
                e.capture_count,
                e.decline_count,
                e.refund_count,
                coalesce(e.captured_at, e.declined_at, e.initiated_at)::DATE AS processing_date
            FROM event_rollup e
            LEFT JOIN raw.merchants m USING (merchant_id)
            """
        )

        connection.execute(
            """
            CREATE TABLE trusted.ledger_entries AS
            WITH captured AS (
                SELECT *
                FROM conformed.payment_transactions
                WHERE capture_count > 0
            ), entries AS (
                SELECT
                    payment_id || ':capture:clearing' AS ledger_entry_id,
                    payment_id,
                    merchant_id,
                    'processor_clearing'::VARCHAR AS account_code,
                    'debit'::VARCHAR AS entry_type,
                    captured_amount::DECIMAL(18, 2) AS amount,
                    currency,
                    processing_date AS accounting_date
                FROM captured
                UNION ALL
                SELECT
                    payment_id || ':capture:payable', payment_id, merchant_id,
                    'merchant_payable', 'credit', captured_amount, currency, processing_date
                FROM captured
                UNION ALL
                SELECT
                    payment_id || ':fee:payable', payment_id, merchant_id,
                    'merchant_payable', 'debit', fee_amount, currency, processing_date
                FROM captured
                UNION ALL
                SELECT
                    payment_id || ':fee:revenue', payment_id, merchant_id,
                    'fee_revenue', 'credit', fee_amount, currency, processing_date
                FROM captured
                UNION ALL
                SELECT
                    payment_id || ':refund:payable', payment_id, merchant_id,
                    'merchant_payable', 'debit', refunded_amount, currency, processing_date
                FROM captured
                WHERE refunded_amount > 0
                UNION ALL
                SELECT
                    payment_id || ':refund:clearing', payment_id, merchant_id,
                    'processor_clearing', 'credit', refunded_amount, currency, processing_date
                FROM captured
                WHERE refunded_amount > 0
            )
            SELECT * FROM entries
            """
        )

        if config.scenario is Scenario.UNBALANCED_LEDGER:
            connection.execute(
                """
                UPDATE trusted.ledger_entries
                SET amount = amount + 1.00
                WHERE ledger_entry_id = (
                    SELECT min(ledger_entry_id)
                    FROM trusted.ledger_entries
                    WHERE entry_type = 'debit'
                )
                """
            )

        connection.execute(
            """
            CREATE TABLE trusted.merchant_settlements AS
            SELECT
                'stl_' || strftime(processing_date, '%Y%m%d') || '_'
                    || merchant_id || '_' || currency
                    AS settlement_id,
                merchant_id,
                currency,
                processing_date AS settlement_date,
                sum(captured_amount)::DECIMAL(18, 2) AS gross_captured_amount,
                sum(refunded_amount)::DECIMAL(18, 2) AS refunded_amount,
                sum(fee_amount)::DECIMAL(18, 2) AS fee_amount,
                sum(captured_amount - refunded_amount - fee_amount)::DECIMAL(18, 2)
                    AS net_settlement_amount,
                count(*)::BIGINT AS payment_count,
                'pending_quality_approval'::VARCHAR AS settlement_status
            FROM conformed.payment_transactions
            WHERE capture_count > 0
            GROUP BY merchant_id, currency, processing_date
            """
        )

        if config.scenario is Scenario.SETTLEMENT_MISMATCH:
            connection.execute(
                """
                UPDATE trusted.merchant_settlements
                SET net_settlement_amount = net_settlement_amount + 10.00
                WHERE settlement_id = (SELECT min(settlement_id) FROM trusted.merchant_settlements)
                """
            )

        connection.execute(
            """
            CREATE TABLE quality.quarantined_payment_events AS
            SELECT
                e.*,
                CASE
                    WHEN m.merchant_id IS NULL THEN 'UNKNOWN_MERCHANT'
                    WHEN e.amount <= 0 THEN 'NON_POSITIVE_AMOUNT'
                    WHEN e.currency NOT IN ('USD', 'EUR', 'ARS') THEN 'INVALID_CURRENCY'
                    WHEN e.event_type NOT IN (
                        'initiated', 'authorized', 'captured', 'declined', 'refunded'
                    )
                        THEN 'INVALID_EVENT_TYPE'
                    ELSE NULL
                END::VARCHAR AS rejection_reason
            FROM raw.payment_events e
            LEFT JOIN raw.merchants m USING (merchant_id)
            WHERE
                m.merchant_id IS NULL
                OR e.amount <= 0
                OR e.currency NOT IN ('USD', 'EUR', 'ARS')
                OR e.event_type NOT IN (
                    'initiated', 'authorized', 'captured', 'declined', 'refunded'
                )
            """
        )
    finally:
        connection.close()


def _export_pre_quality_layers(paths: RunPaths) -> None:
    connection = duckdb.connect(str(paths.database), read_only=True)
    try:
        transactions_path = _sql_path(paths.conformed_root / "payment_transactions")
        quarantine_path = _sql_path(paths.quarantine_root / "payment_events")
        connection.execute(
            f"""
            COPY conformed.payment_transactions TO '{transactions_path}' (
                FORMAT PARQUET,
                PARTITION_BY (processing_date),
                OVERWRITE_OR_IGNORE TRUE
            )
            """
        )
        quarantined_count = connection.execute(
            "SELECT count(*) FROM quality.quarantined_payment_events"
        ).fetchone()[0]
        if quarantined_count:
            connection.execute(
                f"""
                COPY quality.quarantined_payment_events TO '{quarantine_path}' (
                    FORMAT PARQUET,
                    PARTITION_BY (ingestion_date),
                    OVERWRITE_OR_IGNORE TRUE
                )
                """
            )
    finally:
        connection.close()


def _write_data_source_config(paths: RunPaths) -> None:
    database_path = str(paths.database.resolve()).replace("\\", "/")
    paths.data_source_config.write_text(
        "\n".join(
            [
                "type: duckdb",
                "name: duckdb",
                "connection:",
                f'  database: "{database_path}"',
                "",
            ]
        ),
        encoding="utf-8",
    )


def _sql_path(path: Path) -> str:
    return str(path.resolve()).replace("'", "''")
