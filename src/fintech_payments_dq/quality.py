from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from .domain import RunConfig
from .paths import RunPaths

CONTRACTS = (
    "raw_payment_events.yml",
    "payment_transactions.yml",
    "ledger_entries.yml",
    "merchant_settlements.yml",
)


@dataclass(frozen=True)
class ContractResult:
    contract: str
    passed: bool
    return_code: int
    output: str


@dataclass(frozen=True)
class QualityResult:
    passed: bool
    contracts: tuple[ContractResult, ...]


def verify_contracts(config: RunConfig, paths: RunPaths) -> QualityResult:
    soda_executable = shutil.which("soda")
    if soda_executable is None:
        raise RuntimeError("Soda CLI was not found. Run `uv sync --extra dev` first.")

    results: list[ContractResult] = []
    for contract_name in CONTRACTS:
        contract_path = paths.project_root / "contracts" / contract_name
        process = subprocess.run(
            [
                soda_executable,
                "contract",
                "verify",
                "--data-source",
                str(paths.data_source_config),
                "--contract",
                str(contract_path),
            ],
            cwd=paths.project_root,
            text=True,
            capture_output=True,
            check=False,
            env={**os.environ, "SODA_CORE_TELEMETRY_ENABLED": "false"},
        )
        output = "\n".join(part for part in (process.stdout, process.stderr) if part).strip()
        results.append(
            ContractResult(
                contract=contract_name,
                passed=process.returncode == 0,
                return_code=process.returncode,
                output=output,
            )
        )

    quality_result = QualityResult(
        passed=all(result.passed for result in results),
        contracts=tuple(results),
    )
    write_evidence(config, paths, quality_result)
    return quality_result


def write_evidence(config: RunConfig, paths: RunPaths, result: QualityResult) -> None:
    generated_at = datetime.now(UTC).isoformat()
    payload = {
        "scenario": config.scenario.value,
        "as_of": config.as_of.isoformat(),
        "seed": config.seed,
        "generated_at": generated_at,
        "quality_gate": "PASSED" if result.passed else "BLOCKED",
        "expected_quality_pass": config.scenario.expects_quality_pass,
        "scenario_behaved_as_expected": result.passed == config.scenario.expects_quality_pass,
        "contracts": [asdict(contract) for contract in result.contracts],
    }
    (paths.evidence_root / "result.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )

    lines = [
        f"# Quality evidence: {config.scenario.value}",
        "",
        f"- Execution date: `{config.as_of.isoformat()}`",
        f"- Seed: `{config.seed}`",
        f"- Quality gate: **{payload['quality_gate']}**",
        f"- Expected behavior confirmed: **{payload['scenario_behaved_as_expected']}**",
        "",
        "## Contract results",
        "",
        "| Contract | Result | Exit code |",
        "|---|---:|---:|",
    ]
    for contract in result.contracts:
        status = "PASS" if contract.passed else "FAIL"
        lines.append(f"| `{contract.contract}` | {status} | {contract.return_code} |")
    lines.extend(["", "## Soda output", ""])
    for contract in result.contracts:
        lines.extend(
            [
                f"### {contract.contract}",
                "",
                "```text",
                contract.output or "No output captured.",
                "```",
                "",
            ]
        )
    (paths.evidence_root / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def format_console_summary(config: RunConfig, paths: RunPaths, result: QualityResult) -> str:
    expected = result.passed == config.scenario.expects_quality_pass
    lines = [
        "",
        "Fintech Payments Data Quality",
        "=" * 31,
        f"Scenario:      {config.scenario.value}",
        f"Execution date: {config.as_of.isoformat()}",
        f"Quality gate:   {'PASSED' if result.passed else 'BLOCKED'}",
        f"Expected result confirmed: {'YES' if expected else 'NO'}",
        "",
    ]
    for contract in result.contracts:
        lines.append(f"  [{'PASS' if contract.passed else 'FAIL'}] {contract.contract}")
    lines.extend(
        [
            "",
            f"Evidence: {paths.evidence_root / 'summary.md'}",
            f"Published: {'trusted/' if result.passed else 'nothing (quality gate blocked)'}",
        ]
    )
    return "\n".join(lines)


def latest_failed_output(result: QualityResult) -> str:
    return "\n\n".join(contract.output for contract in result.contracts if not contract.passed)
