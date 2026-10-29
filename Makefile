.PHONY: install run lint format
install:
	poetry install && poetry run pre-commit install
run:
	poetry run python -m ppu_bot
lint:
	poetry run ruff check . && poetry run ruff format --check .
