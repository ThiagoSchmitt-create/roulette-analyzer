.PHONY: install install-dev install-dashboard test demo demo-unbiased demo-biased dev dashboard lint format clean check

# Default target
help:
	@echo "Comandos disponiveis:"
	@echo "  make install       - instala dependencias runtime"
	@echo "  make install-dev   - instala runtime + dev (pytest, ruff)"
	@echo "  make install-dashboard - instala runtime + streamlit"
	@echo "  make test          - roda pytest"
	@echo "  make demo          - roda analise em dados sinteticos com vies"
	@echo "  make demo-unbiased - roda analise em dados sinteticos sem vies"
	@echo "  make dev           - sobe FastAPI com hot reload em :8000"
	@echo "  make dashboard     - sobe o dashboard Streamlit em :8501"
	@echo "  make lint          - ruff check"
	@echo "  make format        - ruff format"
	@echo "  make check         - lint + test + demo (CI local)"
	@echo "  make clean         - remove __pycache__, .pytest_cache, etc."

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

install-dashboard:
	pip install -e ".[dashboard]"

test:
	pytest tests/ -v

demo: demo-biased

demo-biased:
	python analyze.py --demo biased --wheel european

demo-unbiased:
	python analyze.py --demo unbiased --wheel european

dev:
	uvicorn api:app --reload --host 0.0.0.0 --port 8000

dashboard:
	streamlit run dashboard.py

lint:
	ruff check .

format:
	ruff format .

check: lint test demo-biased
	@echo ""
	@echo "OK — lint + test + demo passaram."

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ *.egg-info/ .coverage htmlcov/
