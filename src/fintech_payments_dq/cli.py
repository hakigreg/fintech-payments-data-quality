from __future__ import annotations

import argparse
import shutil
from datetime import UTC, date, datetime

from .domain import RunConfig, Scenario
from .paths import find_project_root
from .runner import execute


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Expected an ISO date such as 2026-10-21") from error


def _today_utc() -> date:
    return datetime.now(UTC).date()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fintech-dq",
        description="Run reproducible fintech payment data-quality scenarios.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo = subparsers.add_parser("demo", help="Run the complete quality scenario catalog.")
    demo.add_argument("--as-of", type=_parse_date, default=_today_utc())
    demo.add_argument("--seed", type=int, default=42)

    scenario = subparsers.add_parser("scenario", help="Run one named scenario.")
    scenario.add_argument("name", choices=[item.value for item in Scenario])
    scenario.add_argument("--as-of", type=_parse_date, default=_today_utc())
    scenario.add_argument("--seed", type=int, default=42)

    subparsers.add_parser("clean", help="Remove generated build artifacts.")
    return parser


def _run_scenario(scenario: Scenario, as_of: date, seed: int) -> bool:
    config = RunConfig(scenario=scenario, as_of=as_of, seed=seed)
    _, _, expected = execute(config, find_project_root())
    return expected


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "clean":
        build_directory = find_project_root() / "build"
        if build_directory.exists():
            shutil.rmtree(build_directory)
        print(f"Removed generated artifacts from {build_directory}")
        return 0

    if args.command == "scenario":
        return 0 if _run_scenario(Scenario(args.name), args.as_of, args.seed) else 1

    outcomes = [_run_scenario(item, args.as_of, args.seed) for item in Scenario]
    return 0 if all(outcomes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
