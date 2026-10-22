# Data quality control catalog

| ID | Contract | Dataset | Rule | Dimension | Owner | Response | Failure scenario |
|---|---|---|---|---|---|---|---|
| `FIN-SCHEMA-001` | `raw_payment_events.yml` | Raw payment events | Schema matches the approved event contract | Schema | Payment Operations | Block intake | `schema-drift` |
| `FIN-PAY-001` | `raw_payment_events.yml` | Raw payment events | A payment has at most one capture | Uniqueness | Payment Operations | Block partition and investigate idempotency | `duplicate-capture` |
| `FIN-PAY-002` | `raw_payment_events.yml` | Raw payment events | Every event references a known merchant | Referential integrity | Payment Operations | Quarantine records and block settlement | `missing-merchant` |
| `FIN-PAY-SLA` | `raw_payment_events.yml` | Raw payment events | Events arrive within 24 hours | Timeliness | Data Operations | Block incomplete processing date | `late-event` |
| `FIN-SCHEMA-002` | `payment_transactions.yml` | Payment transactions | Schema matches the approved transaction contract | Schema | Payment Operations | Block transaction publication | — |
| `FIN-TXN-001` | `payment_transactions.yml` | Payment transactions | Lifecycle transitions are valid | Consistency | Payment Operations | Block transaction publication | `invalid-state-transition` |
| `FIN-TXN-002` | `payment_transactions.yml` | Payment transactions | Refund total does not exceed capture | Financial integrity | Payment Operations | Block and investigate refund processing | `refund-over-capture` |
| `FIN-TXN-003` | `payment_transactions.yml` | Payment transactions | Captured payments have a fee | Completeness | Finance Operations | Block settlement calculation | — |
| `FIN-SCHEMA-003` | `ledger_entries.yml` | Ledger entries | Schema matches the approved ledger contract | Schema | Finance Operations | Block ledger publication | — |
| `FIN-LEDGER-001` | `ledger_entries.yml` | Ledger entries | Debits equal credits for every payment and currency | Financial integrity | Finance Operations | Block ledger publication | `unbalanced-ledger` |
| `FIN-SCHEMA-004` | `merchant_settlements.yml` | Merchant settlements | Schema matches the approved settlement contract | Schema | Finance Operations | Block merchant payout | — |
| `FIN-SETTLE-001` | `merchant_settlements.yml` | Merchant settlements | Net equals captures minus refunds and fees | Financial integrity | Finance Operations | Block merchant payout | `settlement-mismatch` |
| `FIN-SETTLE-002` | `merchant_settlements.yml` | Merchant settlements | Net settlement is non-negative | Validity | Finance Operations | Block merchant payout | — |

This catalog covers governed controls with stable IDs, ownership, response, and scenario
traceability. Standard Soda checks for row count, missing values, duplicates, and allowed values
remain executable supporting checks inside each contract and do not receive separate control IDs.

The executable source of truth lives in [`contracts/`](../contracts/). This catalog explains intent
and operating response; it does not duplicate contract syntax.
