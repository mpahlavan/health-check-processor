.PHONY: install test lint type check run docker

install:
	uv sync --frozen

test:
	uv run pytest --cov=uptime --cov-report=term-missing

lint:
	uv run ruff check src tests
	uv run ruff format --check src tests

type:
	uv run mypy src

check: lint type test

run:
	uv run uptime --input data/scilifelab-data-centre-coding-test-input.csv --output data/out.csv --report

docker:
	docker build -t uptime .
