# Fintech Payments: Data Quality Controls with Soda Core

[![CI](https://github.com/hakigreg/fintech-payments-data-quality/actions/workflows/ci.yml/badge.svg)](https://github.com/hakigreg/fintech-payments-data-quality/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-3776AB.svg)](https://www.python.org/)
[![Soda Core](https://img.shields.io/badge/data%20quality-Soda_Core-00AEEF.svg)](https://www.soda.io/)
[![DuckDB](https://img.shields.io/badge/analytics-DuckDB-FFF000.svg)](https://duckdb.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Production-oriented data-quality deployment using Soda Core to protect payment transactions, double-entry ledger entries, and merchant settlements with executable controls.

The repository is fully reproducible. It requires no cloud account, external database, API keys, Docker, or proprietary service. DuckDB provides the analytical execution engine, Parquet provides persistent partitioned storage, and Soda Core v4 enforces quality contracts at each financial boundary.

## Why this project exists

A technically successful payment pipeline can still produce financially incorrect data. Duplicate captures, invalid payment transitions, unbalanced ledger entries, and settlement mismatches can pass unnoticed when pipelines validate only execution status.

This project treats data quality as a release control. It builds an isolated candidate
snapshot, evaluates four business boundaries with Soda Core, and aggregates their outcomes
into one fail-closed publication decision:

```text
Synthetic payment events
          │
          ▼
Isolated candidate snapshot
├── Raw payment events ─────────── Soda intake contract
├── Consolidated transactions ─── Soda transaction contract
├── Double-entry ledger ────────── Soda accounting contract
└── Merchant settlements ───────── Soda settlement contract
          │
          ▼
Aggregated publication gate
├── PASS ──▶ Trusted Parquet data products
└── FAIL ──▶ Publication blocked + evidence
              └── Quarantine when defects are row-addressable
```

## What it implements

- Git-managed Soda contracts with business-readable checks.
- Completeness, validity, uniqueness, consistency, timeliness, and referential integrity.
- Financial controls for duplicate capture, ledger balance, refunds, and settlements.
- Layered Parquet datasets: raw, conformed, trusted, and quarantine.
- Deterministic synthetic data and controlled failure injection.
- Quality gates that prevent invalid financial data from being published.
- Machine-readable JSON evidence and reviewer-friendly Markdown summaries.
- CI tests proving that valid data passes and defective scenarios are blocked at the expected
  contract boundary.

## Suggested review path

For a focused assessment of the project, follow this sequence:

1. **Observe the outcome:** start with the committed [evidence snapshot](docs/evidence.md) to compare
   a successful publication with a blocked financial defect—no local setup required.
2. **Inspect the Soda implementation:** open the [data contracts](contracts/), especially the
   [ledger balance contract](contracts/ledger_entries.yml), to see executable business rules and
   their thresholds.
3. **Follow control traceability:** use the [control catalog](docs/control-catalog.md) to connect each
   governed control to its contract, dataset, quality dimension, owner, response, and test scenario.
4. **Understand the publication gate:** read the [architecture](docs/architecture.md), then inspect
   the [Soda execution and evidence code](src/fintech_payments_dq/quality.py) and the
   [fail-closed runner](src/fintech_payments_dq/runner.py).
5. **Verify automated assurance:** review the [integration tests](tests/test_quality_integration.py)
   and the [CI workflow](.github/workflows/ci.yml), whose current result is shown by the badge above.

## Quickstart

Prerequisites:

- Git
- Python 3.11 or 3.12
- [uv](https://docs.astral.sh/uv/)

```bash
git clone https://github.com/hakigreg/fintech-payments-data-quality.git
cd fintech-payments-data-quality
uv sync --extra dev
uv run fintech-dq demo --as-of 2026-10-21
```

The demo runs one valid path and all eight controlled failure scenarios. Each scenario succeeds only
when the observed quality-gate result matches the expected result.

Run one scenario:

```bash
uv run fintech-dq scenario green --as-of 2026-10-21
uv run fintech-dq scenario duplicate-capture --as-of 2026-10-21
uv run fintech-dq scenario unbalanced-ledger --as-of 2026-10-21
uv run fintech-dq scenario settlement-mismatch --as-of 2026-10-21
```

The Makefile provides equivalent convenience commands:

```bash
make demo
make demo-unbalanced-ledger
make test
make lint
```

## Key quality controls

| Control | Business rule | Quality dimension | Gate |
|---|---|---|---|
| `FIN-PAY-001` | A payment must not be captured more than once | Uniqueness | Block |
| `FIN-PAY-002` | Every payment event must reference a known merchant | Referential integrity | Block |
| `FIN-TXN-001` | Payment state transitions must be valid | Consistency | Block |
| `FIN-TXN-002` | Total refunds must not exceed the captured amount | Financial integrity | Block |
| `FIN-LEDGER-001` | Debits and credits must balance for every payment | Financial integrity | Block |
| `FIN-SETTLE-001` | Net settlement must equal captures minus refunds and fees | Financial integrity | Block |

See the complete [governed control catalog](docs/control-catalog.md), including ownership,
contract mapping, response, and failure-scenario traceability.

## Scenarios

| Scenario | Expected result | Gate behavior |
|---|---:|---|
| `green` | Pass | Trusted ledger and settlement Parquet files are published |
| `duplicate-capture` | Block | A second capture for the same payment is rejected |
| `invalid-state-transition` | Block | A declined payment cannot later be captured |
| `missing-merchant` | Block | Orphan financial events are rejected and quarantined |
| `refund-over-capture` | Block | Refund totals cannot exceed captured value |
| `late-event` | Block | Events outside the ingestion SLA are rejected |
| `unbalanced-ledger` | Block | Debits and credits must conserve money |
| `settlement-mismatch` | Block | Merchant settlement arithmetic must reconcile |
| `schema-drift` | Block | Unreviewed upstream fields are rejected |

## Evidence preview

Representative evidence is committed so reviewers can inspect the gate behavior without running
the project:

| Scenario | Gate | Contract outcome | Publication outcome |
|---|---:|---|---|
| `green` | PASS | All four Soda contracts pass | Trusted ledger and settlement Parquet files published |
| `unbalanced-ledger` | BLOCK | `ledger_entries.yml` fails | No trusted Parquet files published |

See the [evidence snapshot](docs/evidence.md) for contract results, selected Soda output,
machine-readable JSON excerpts, and dataset metrics.

## Generated artifacts

Each run is isolated under `build/runs/<scenario>/`:

```text
build/runs/green/
├── data-lake/
│   ├── raw/
│   ├── conformed/
│   ├── trusted/
│   └── quarantine/
├── evidence/
│   ├── result.json
│   └── summary.md
├── duckdb.yml
└── fintech.duckdb
```

The DuckDB snapshot contains candidate tables for Soda to inspect. Trusted Parquet files are
written only after every contract passes. Failure scenarios retain evidence, produce quarantine
output when invalid source rows can be identified individually, and never publish trusted outputs.

## Repository guide

```text
contracts/                  Soda data contracts
data/scenarios/             Controlled failure catalog
docs/                       Architecture and operating model
src/fintech_payments_dq/    Generator, pipeline, gates, and CLI
tests/                      Unit and Soda integration tests
.github/workflows/          Reproducibility and quality CI
```

Additional documentation:

- [Data quality strategy](docs/data-quality-strategy.md)
- [Scenario guide](docs/scenarios.md)

## Design boundaries

- The project models a batch analytical data platform, not a payment-processing system.
- All organizations, transactions, and identifiers are synthetic.
- Currency conversion is deliberately excluded; settlements are calculated independently by currency.
- Soda Core runs locally. Soda Cloud is not required.
- Cloud infrastructure, streaming, orchestration platforms, and BI tooling are outside the project boundary.

## Disclaimer

This repository implements a data-quality deployment for synthetic payment data using Soda, DuckDB, and Parquet. It does not provide financial, accounting, compliance, or legal advice and is not intended to operate as a production payment-processing system.

## License

[MIT](LICENSE)
