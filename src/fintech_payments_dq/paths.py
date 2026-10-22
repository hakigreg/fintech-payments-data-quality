from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunPaths:
    project_root: Path
    run_root: Path
    lake_root: Path
    raw_root: Path
    conformed_root: Path
    trusted_root: Path
    quarantine_root: Path
    evidence_root: Path
    database: Path
    data_source_config: Path

    @classmethod
    def for_scenario(cls, project_root: Path, scenario: str) -> RunPaths:
        run_root = project_root / "build" / "runs" / scenario
        lake_root = run_root / "data-lake"
        return cls(
            project_root=project_root,
            run_root=run_root,
            lake_root=lake_root,
            raw_root=lake_root / "raw",
            conformed_root=lake_root / "conformed",
            trusted_root=lake_root / "trusted",
            quarantine_root=lake_root / "quarantine",
            evidence_root=run_root / "evidence",
            database=run_root / "fintech.duckdb",
            data_source_config=run_root / "duckdb.yml",
        )

    def create(self) -> None:
        for path in (
            self.raw_root,
            self.conformed_root,
            self.trusted_root,
            self.quarantine_root,
            self.evidence_root,
        ):
            path.mkdir(parents=True, exist_ok=True)


def find_project_root() -> Path:
    return Path(__file__).resolve().parents[2]
