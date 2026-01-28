all: black ruff mypy test
format: black ruff isort
lint: ruff mypy
check: checkblack checkruff

black:
	uv run black .

ruff:
	uv run ruff check . --fix

checkruff:
	uv run ruff check .

checkblack:
	uv run black --check .

mypy:
	uv run mypy .

test:
	uv run pytest tests --cov=lnurl --cov-report=xml
