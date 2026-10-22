from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class Scenario(StrEnum):
    GREEN = "green"
    DUPLICATE_CAPTURE = "duplicate-capture"
    INVALID_STATE_TRANSITION = "invalid-state-transition"
    MISSING_MERCHANT = "missing-merchant"
    REFUND_OVER_CAPTURE = "refund-over-capture"
    LATE_EVENT = "late-event"
    UNBALANCED_LEDGER = "unbalanced-ledger"
    SETTLEMENT_MISMATCH = "settlement-mismatch"
    SCHEMA_DRIFT = "schema-drift"

    @property
    def expects_quality_pass(self) -> bool:
        return self is Scenario.GREEN


@dataclass(frozen=True)
class RunConfig:
    scenario: Scenario
    as_of: date
    seed: int = 42
    payment_count: int = 120
