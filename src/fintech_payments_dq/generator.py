from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import duckdb

from .domain import RunConfig, Scenario
from .paths import RunPaths

MONEY = Decimal("0.01")
EVENT_TYPES = ("initiated", "authorized", "captured", "declined", "refunded")
CURRENCIES = ("USD", "EUR", "ARS")


@dataclass(frozen=True)
class Event:
    event_id: str
    payment_id: str
    merchant_id: str
    event_type: str
    amount: Decimal
    currency: str
    event_timestamp: datetime
    ingestion_timestamp: datetime
    ingestion_date: date
    source_system: str = "payments-api"


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def _event(
    sequence: int,
    payment_id: str,
    merchant_id: str,
    event_type: str,
    amount: Decimal,
    currency: str,
    occurred_at: datetime,
) -> Event:
    ingested_at = occurred_at + timedelta(seconds=5)
    return Event(
        event_id=f"evt_{sequence:07d}",
        payment_id=payment_id,
        merchant_id=merchant_id,
        event_type=event_type,
        amount=amount,
        currency=currency,
        event_timestamp=occurred_at,
        ingestion_timestamp=ingested_at,
        ingestion_date=ingested_at.date(),
    )


def _base_data(config: RunConfig) -> tuple[list[tuple[object, ...]], list[Event]]:
    rng = random.Random(config.seed)
    created_at = datetime.combine(config.as_of - timedelta(days=365), time(), tzinfo=UTC).replace(
        tzinfo=None
    )
    merchants = [
        ("mrc_001", "Andes Market", "AR", "active", Decimal("0.021000"), created_at),
        ("mrc_002", "Northstar Digital", "US", "active", Decimal("0.018500"), created_at),
        ("mrc_003", "Lumen Travel", "ES", "active", Decimal("0.024000"), created_at),
        ("mrc_004", "Río Services", "UY", "active", Decimal("0.020000"), created_at),
        ("mrc_005", "Atlas Commerce", "DE", "active", Decimal("0.019500"), created_at),
        ("mrc_006", "Pampa Mobility", "AR", "active", Decimal("0.022500"), created_at),
    ]

    events: list[Event] = []
    sequence = 1
    start = datetime.combine(config.as_of, time(hour=8), tzinfo=UTC).replace(tzinfo=None)
    for index in range(1, config.payment_count + 1):
        payment_id = f"pay_{index:06d}"
        merchant_id = merchants[(index - 1) % len(merchants)][0]
        currency = CURRENCIES[(index - 1) % len(CURRENCIES)]
        amount = _money(Decimal(rng.randint(500, 75_000)) / 100)
        initiated_at = start + timedelta(minutes=index * 3)

        events.append(
            _event(sequence, payment_id, merchant_id, "initiated", amount, currency, initiated_at)
        )
        sequence += 1

        if index % 11 == 0:
            events.append(
                _event(
                    sequence,
                    payment_id,
                    merchant_id,
                    "declined",
                    amount,
                    currency,
                    initiated_at + timedelta(seconds=20),
                )
            )
            sequence += 1
            continue

        authorized_at = initiated_at + timedelta(seconds=15)
        captured_at = authorized_at + timedelta(seconds=30)
        events.extend(
            [
                _event(
                    sequence,
                    payment_id,
                    merchant_id,
                    "authorized",
                    amount,
                    currency,
                    authorized_at,
                ),
                _event(
                    sequence + 1,
                    payment_id,
                    merchant_id,
                    "captured",
                    amount,
                    currency,
                    captured_at,
                ),
            ]
        )
        sequence += 2

        if index % 13 == 0:
            refund_amount = _money(amount * Decimal("0.30"))
            events.append(
                _event(
                    sequence,
                    payment_id,
                    merchant_id,
                    "refunded",
                    refund_amount,
                    currency,
                    captured_at + timedelta(hours=2),
                )
            )
            sequence += 1

    return merchants, events


def _inject_scenario(events: list[Event], scenario: Scenario) -> list[Event]:
    mutated = list(events)
    next_sequence = len(events) + 100

    if scenario is Scenario.DUPLICATE_CAPTURE:
        captured = next(event for event in mutated if event.event_type == "captured")
        mutated.append(
            _event(
                next_sequence,
                captured.payment_id,
                captured.merchant_id,
                "captured",
                captured.amount,
                captured.currency,
                captured.event_timestamp + timedelta(minutes=1),
            )
        )
    elif scenario is Scenario.INVALID_STATE_TRANSITION:
        declined = next(event for event in mutated if event.event_type == "declined")
        mutated.append(
            _event(
                next_sequence,
                declined.payment_id,
                declined.merchant_id,
                "captured",
                declined.amount,
                declined.currency,
                declined.event_timestamp + timedelta(minutes=1),
            )
        )
    elif scenario is Scenario.MISSING_MERCHANT:
        target_payment = mutated[0].payment_id
        mutated = [
            Event(
                event_id=event.event_id,
                payment_id=event.payment_id,
                merchant_id=(
                    "mrc_missing" if event.payment_id == target_payment else event.merchant_id
                ),
                event_type=event.event_type,
                amount=event.amount,
                currency=event.currency,
                event_timestamp=event.event_timestamp,
                ingestion_timestamp=event.ingestion_timestamp,
                ingestion_date=event.ingestion_date,
                source_system=event.source_system,
            )
            for event in mutated
        ]
    elif scenario is Scenario.REFUND_OVER_CAPTURE:
        captured = next(event for event in mutated if event.event_type == "captured")
        mutated.append(
            _event(
                next_sequence,
                captured.payment_id,
                captured.merchant_id,
                "refunded",
                _money(captured.amount + Decimal("1.00")),
                captured.currency,
                captured.event_timestamp + timedelta(hours=3),
            )
        )
    elif scenario is Scenario.LATE_EVENT:
        target = mutated[0]
        mutated[0] = Event(
            event_id=target.event_id,
            payment_id=target.payment_id,
            merchant_id=target.merchant_id,
            event_type=target.event_type,
            amount=target.amount,
            currency=target.currency,
            event_timestamp=target.event_timestamp,
            ingestion_timestamp=target.event_timestamp + timedelta(hours=30),
            ingestion_date=(target.event_timestamp + timedelta(hours=30)).date(),
            source_system=target.source_system,
        )
    return mutated


def generate_raw_data(config: RunConfig, paths: RunPaths) -> None:
    merchants, events = _base_data(config)
    events = _inject_scenario(events, config.scenario)
    connection = duckdb.connect(":memory:")
    try:
        connection.execute(
            """
            CREATE TABLE merchants (
                merchant_id VARCHAR,
                merchant_name VARCHAR,
                country_code VARCHAR,
                status VARCHAR,
                fee_rate DECIMAL(8, 6),
                created_at TIMESTAMP
            )
            """
        )
        connection.executemany("INSERT INTO merchants VALUES (?, ?, ?, ?, ?, ?)", merchants)

        extra_column = (
            ", unexpected_note VARCHAR" if config.scenario is Scenario.SCHEMA_DRIFT else ""
        )
        connection.execute(
            f"""
            CREATE TABLE payment_events (
                event_id VARCHAR,
                payment_id VARCHAR,
                merchant_id VARCHAR,
                event_type VARCHAR,
                amount DECIMAL(18, 2),
                currency VARCHAR,
                event_timestamp TIMESTAMP,
                ingestion_timestamp TIMESTAMP,
                ingestion_date DATE,
                source_system VARCHAR
                {extra_column}
            )
            """
        )
        column_count = 11 if config.scenario is Scenario.SCHEMA_DRIFT else 10
        placeholders = ", ".join("?" for _ in range(column_count))
        rows = [
            (
                event.event_id,
                event.payment_id,
                event.merchant_id,
                event.event_type,
                event.amount,
                event.currency,
                event.event_timestamp,
                event.ingestion_timestamp,
                event.ingestion_date,
                event.source_system,
            )
            + (("unexpected-upstream-field",) if config.scenario is Scenario.SCHEMA_DRIFT else ())
            for event in events
        ]
        connection.executemany(f"INSERT INTO payment_events VALUES ({placeholders})", rows)

        merchants_path = _sql_path(paths.raw_root / "merchants.parquet")
        events_path = _sql_path(paths.raw_root / "payment_events")
        connection.execute(f"COPY merchants TO '{merchants_path}' (FORMAT PARQUET)")
        connection.execute(
            f"""
            COPY payment_events TO '{events_path}' (
                FORMAT PARQUET,
                PARTITION_BY (ingestion_date),
                OVERWRITE_OR_IGNORE TRUE
            )
            """
        )
    finally:
        connection.close()


def _sql_path(path: Path) -> str:
    return str(path.resolve()).replace("'", "''")
