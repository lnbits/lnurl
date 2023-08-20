all: black ruff pyright mypy test
format: black ruff
lint: pyright mypy checkruff
check: checkblack checkruff

black:
	poetry run black .

ruff:
	poetry run ruff check . --fix

checkruff:
	poetry run ruff check .

checkblack:
	poetry run black --check .

pyright:
	poetry run pyright .

mypy:
	poetry run mypy .

test:
	poetry run pytest tests --cov=lnurl --cov-report=xml
