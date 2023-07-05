all: black isort mypy flake8 pyright pylint test

black:
	poetry run black .

isort:
	poetry run isort .

mypy:
	poetry run mypy .

flake8:
	poetry run flake8

pyright:
	poetry run pyright

pylint:
	poetry run pylint bolt11

test:
	poetry run pytest tests
