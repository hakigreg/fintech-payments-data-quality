from __future__ import annotations

from pathlib import Path

from .domain import RunConfig
from .paths import RunPaths
from .pipeline import prepare_run, publish_trusted_data
from .quality import QualityResult, format_console_summary, verify_contracts


def execute(config: RunConfig, project_root: Path) -> tuple[RunPaths, QualityResult, bool]:
    paths = RunPaths.for_scenario(project_root, config.scenario.value)
    prepare_run(config, paths)
    result = verify_contracts(config, paths)
    if result.passed:
        publish_trusted_data(paths)
    expected = result.passed == config.scenario.expects_quality_pass
    print(format_console_summary(config, paths, result))
    return paths, result, expected
