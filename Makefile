.PHONY: test check

test:
	uv run pytest tests/ -v

check:
	pre-commit run --all-files
