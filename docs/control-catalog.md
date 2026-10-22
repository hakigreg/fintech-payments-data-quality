# Data quality control catalog

| ID | Dataset | Rule | Dimension | Owner | Response |
|---|---|---|---|---|---|
| `FIN-PAY-001` | Raw payment events | A payment has at most one capture | Uniqueness | Payment Operations | Block partition and investigate idempotency |
| `FIN-PAY-002` | Raw payment events | Every event references a known merchant | Referential integrity | Payment Operations | Quarantine records and block settlement |
| `FIN-PAY-SLA` | Raw payment events | Events arrive within 24 hours | Timeliness | Data Operations | Block incomplete processing date |
| `FIN-TXN-001` | Payment transactions | Lifecycle transitions are valid | Consistency | Payment Operations | Block transaction publication |
| `FIN-TXN-002` | Payment transactions | Refund total does not exceed capture | Financial integrity | Payment Operations | Block and investigate refund processing |
| `FIN-TXN-003` | Payment transactions | Captured payments have a fee | Completeness | Finance Operations | Block settlement calculation |
| `FIN-LEDGER-001` | Ledger entries | Debits equal credits for every payment and currency | Financial integrity | Finance Operations | Block ledger publication |
| `FIN-SETTLE-001` | Merchant settlements | Net equals captures minus refunds and fees | Financial integrity | Finance Operations | Block merchant payout |
| `FIN-SETTLE-002` | Merchant settlements | Net settlement is non-negative | Validity | Finance Operations | Block merchant payout |

The executable source of truth lives in [`contracts/`](../contracts/). This catalog explains intent and operating response; it does not duplicate contract syntax.
