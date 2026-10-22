from __future__ import annotations

from pathlib import Path

import pytest

from fintech_payments_dq.paths import RunPaths


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def run_paths(tmp_path: Path, project_root: Path) -> RunPaths:
    run_root = tmp_path / "run"
    lake_root = run_root / "data-lake"
    paths = RunPaths(
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
    paths.create()
    return paths
