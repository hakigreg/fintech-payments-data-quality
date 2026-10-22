# Evidence snapshot

This page presents representative evidence from two deterministic executions so the publication
gate can be reviewed without installing the project. The snapshots use Soda Core `4.28.0`,
execution date `2026-10-21`, and seed `42`.

Absolute local paths and repetitive passing column checks have been omitted. Every local or CI run
still writes the complete Soda output and machine-readable result under
`build/runs/<scenario>/evidence/`.

## Decision summary

| Scenario | Candidate rows: events / transactions / ledger / settlements | Gate | Published trusted datasets |
|---|---:|---:|---|
| `green` | 359 / 120 / 458 / 6 | PASS | Ledger entries and merchant settlements |
| `unbalanced-ledger` | 359 / 120 / 458 / 6 | BLOCK | None |

Both executions use the same valid baseline. The blocked scenario changes one debit entry by
`1.00`, producing exactly one unbalanced payment ledger.

## Passing execution

Command:

```bash
uv run fintech-dq scenario green --as-of 2026-10-21 --seed 42
```

### Contract results

| Contract | Result | Exit code |
|---|---:|---:|
| `raw_payment_events.yml` | PASS | 0 |
| `payment_transactions.yml` | PASS | 0 |
| `ledger_entries.yml` | PASS | 0 |
| `merchant_settlements.yml` | PASS | 0 |

Selected governed controls reported by Soda:

| Control | Check | Outcome |
|---|---|---:|
| `FIN-SCHEMA-001` | Payment event schema must remain compatible | PASS |
| `FIN-PAY-001` | A payment must not be captured more than once | PASS |
| `FIN-PAY-002` | Every payment event must reference a known merchant | PASS |
| `FIN-PAY-SLA` | Payment events must arrive within the 24-hour SLA | PASS |
| `FIN-TXN-001` | Payment state transitions must be valid | PASS |
| `FIN-TXN-002` | Total refunds must not exceed the captured amount | PASS |
| `FIN-LEDGER-001` | Every payment ledger must balance debits and credits | PASS |
| `FIN-SETTLE-001` | Net settlement must equal captures minus refunds and fees | PASS |

Machine-readable evidence excerpt:

```json
{
  "scenario": "green",
  "as_of": "2026-10-21",
  "seed": 42,
  "quality_gate": "PASSED",
  "expected_quality_pass": true,
  "scenario_behaved_as_expected": true,
  "contracts": [
    {"contract": "raw_payment_events.yml", "passed": true, "return_code": 0},
    {"contract": "payment_transactions.yml", "passed": true, "return_code": 0},
    {"contract": "ledger_entries.yml", "passed": true, "return_code": 0},
    {"contract": "merchant_settlements.yml", "passed": true, "return_code": 0}
  ]
}
```

Publication evidence:

```text
data-lake/trusted/
├── ledger_entries/accounting_date=2026-10-21/data_0.parquet
└── merchant_settlements/settlement_date=2026-10-21/data_0.parquet
```

## Blocked execution

Command:

```bash
uv run fintech-dq scenario unbalanced-ledger --as-of 2026-10-21 --seed 42
```

### Contract results

| Contract | Result | Exit code |
|---|---:|---:|
| `raw_payment_events.yml` | PASS | 0 |
| `payment_transactions.yml` | PASS | 0 |
| `ledger_entries.yml` | **FAIL** | 1 |
| `merchant_settlements.yml` | PASS | 0 |

Selected Soda output:

```text
### Contract results for duckdb/fintech/trusted/ledger_entries
| Column          | Check                                                | Threshold   | Outcome   | Diagnostics              |
| [dataset-level] | Every payment ledger must balance debits and credits | must be: 0 | ❌ FAILED | dataset_rows_tested: 458 |
```

The failed check is the governed control
[`FIN-LEDGER-001`](../contracts/ledger_entries.yml), which protects double-entry conservation by
payment and currency.

Machine-readable evidence excerpt:

```json
{
  "scenario": "unbalanced-ledger",
  "as_of": "2026-10-21",
  "seed": 42,
  "quality_gate": "BLOCKED",
  "expected_quality_pass": false,
  "scenario_behaved_as_expected": true,
  "contracts": [
    {"contract": "raw_payment_events.yml", "passed": true, "return_code": 0},
    {"contract": "payment_transactions.yml", "passed": true, "return_code": 0},
    {"contract": "ledger_entries.yml", "passed": false, "return_code": 1},
    {"contract": "merchant_settlements.yml", "passed": true, "return_code": 0}
  ]
}
```

Publication evidence:

```text
data-lake/trusted/
└── empty
```

The candidate tables remain available inside the isolated DuckDB run database for diagnosis, but
the publication gate writes no trusted Parquet products.

## Reproduce the complete evidence

The committed snapshot is intentionally concise. To generate the full Soda output, JSON evidence,
Markdown summary, DuckDB database, Parquet layers, and quarantine data, follow the
[scenario guide](scenarios.md).
