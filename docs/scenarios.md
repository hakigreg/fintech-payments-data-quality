# Scenario guide

Controlled failure injection proves that a check can reject the defect it claims to control.

## Green path

```bash
uv run fintech-dq scenario green --as-of 2026-10-21
```

Expected result: all contracts pass and trusted ledger and settlement Parquet files are published.

## Duplicate capture

```bash
uv run fintech-dq scenario duplicate-capture --as-of 2026-10-21
```

The generator adds a second capture for one authorized payment. `FIN-PAY-001` blocks publication.

## Invalid state transition

```bash
uv run fintech-dq scenario invalid-state-transition --as-of 2026-10-21
```

A payment is declined and subsequently captured. `FIN-TXN-001` blocks publication.

## Missing merchant

```bash
uv run fintech-dq scenario missing-merchant --as-of 2026-10-21
```

One payment references an unknown merchant. `FIN-PAY-002` fails and affected events are retained in quarantine.

## Refund above capture

```bash
uv run fintech-dq scenario refund-over-capture --as-of 2026-10-21
```

A refund exceeds its captured amount. `FIN-TXN-002` blocks publication.

## Late event

```bash
uv run fintech-dq scenario late-event --as-of 2026-10-21
```

An event arrives 30 hours after it occurred, exceeding the 24-hour SLA.

## Unbalanced ledger

```bash
uv run fintech-dq scenario unbalanced-ledger --as-of 2026-10-21
```

One debit is increased without a matching credit. `FIN-LEDGER-001` blocks the ledger.

## Settlement mismatch

```bash
uv run fintech-dq scenario settlement-mismatch --as-of 2026-10-21
```

One net settlement is changed after calculation. `FIN-SETTLE-001` blocks payout publication.

## Schema drift

```bash
uv run fintech-dq scenario schema-drift --as-of 2026-10-21
```

An unexpected upstream column is added. The strict intake schema contract rejects the change.

## Expected failures

The underlying Soda contract returns a failure for a negative scenario. The scenario command itself exits successfully only when that rejection was expected. This makes controlled failures suitable for CI without disguising the quality-gate decision.
