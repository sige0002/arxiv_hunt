.PHONY: install search convert ui test clean

install:
	uv sync

search:
	uv run python scripts/paperhunt_arxiv.py --query '$(QUERY)' --days $(or $(DAYS),7) --max $(or $(MAX),10)

convert:
	uv run python scripts/csv_to_excel_translate.py

ui:
	uv sync --extra ui
	uv run python run_ui.py

test:
	uv run pytest tests/ -v

clean:
	rm -f data/csv/*.csv data/excel/*.xlsx
