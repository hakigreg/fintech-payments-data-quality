.PHONY: setup lint test demo demo-green demo-duplicate-capture demo-invalid-state-transition demo-unbalanced-ledger demo-settlement-mismatch clean

setup:
	uv sync --extra dev --frozen

lint:
	uv run ruff check .
	uv run ruff format --check .

test:
	uv run pytest

demo:
	uv run fintech-dq demo

demo-green:
	uv run fintech-dq scenario green

demo-duplicate-capture:
	uv run fintech-dq scenario duplicate-capture

demo-invalid-state-transition:
	uv run fintech-dq scenario invalid-state-transition

demo-unbalanced-ledger:
	uv run fintech-dq scenario unbalanced-ledger

demo-settlement-mismatch:
	uv run fintech-dq scenario settlement-mismatch

clean:
	uv run fintech-dq clean
