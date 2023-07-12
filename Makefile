all: black isort mypy flake8 test
format: black isort
lint: flake8 mypy
check: checkblack checkisort

black:
	poetry run black .

isort:
	poetry run isort .

checkblack:
	poetry run black --check .

checkisort:
	poetry run isort --check-only .

mypy:
	poetry run mypy .

flake8:
	poetry run flake8

test:
	poetry run pytest tests --cov=lnurl --cov-report=xml
