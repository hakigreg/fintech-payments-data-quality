# Data quality strategy

## Principles

1. Express business risk, not only technical symptoms.
2. Place controls at the boundary where a defect can still be contained.
3. Treat financial integrity failures as release blockers.
4. Make negative scenarios executable and continuously tested.
5. Retain enough evidence to explain every release decision.
6. Keep generated data synthetic and deterministic.

## Quality dimensions

- **Completeness:** required identifiers, timestamps, amounts, and lineage fields exist.
- **Validity:** codes, monetary values, currencies, and states belong to accepted domains.
- **Uniqueness:** events, payments, ledger entries, and settlements are not duplicated.
- **Consistency:** payment states and their timestamps form a valid lifecycle.
- **Timeliness:** events arrive within the declared ingestion SLA.
- **Referential integrity:** financial activity belongs to a known merchant and payment.
- **Financial integrity:** money is conserved across ledger and settlement calculations.

## Gate policy

All implemented controls are blocking because they protect financial boundaries. Warning-level trend and volume controls can be introduced when historical baselines are available, but they must remain distinct from hard business invariants.

## Row quarantine versus partition blocking

Malformed source records can be retained in quarantine with a reason. A partition is still blocked when accepting the remaining rows would produce an incomplete or financially misleading result. Ledger and settlement failures always block the complete publication unit.

## Evidence

Every run records:

- scenario and execution date;
- overall gate decision;
- contract-level outcomes and process exit codes;
- Soda output;
- whether the observed result matched the scenario expectation.

JSON supports automation, while Markdown supports human review.
