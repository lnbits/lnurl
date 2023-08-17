all: black ruff mypy test
format: black ruff isort
lint: ruff mypy
check: checkblack checkruff

black:
	poetry run black .

ruff:
	poetry run ruff check . --fix

checkruff:
	poetry run ruff check .

checkblack:
	poetry run black --check .

mypy:
	poetry run mypy .

test:
	poetry run pytest tests --cov=lnurl --cov-report=xml
