.PHONY: install install-dev format lint test clean run run-api pipeline help

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

# Code quality
format:
	black src/ tests/ main.py run_api.py
	isort src/ tests/ main.py run_api.py

lint:
	flake8 src/ tests/ main.py run_api.py
	mypy src/

test:
	pytest tests/ -v

test-integration:
	python tests/test_config.py
	python tests/test_gmail_connection.py

# Development
run:
	python main.py

run-api:
	python run_api.py

pipeline:
	python main.py -v pipeline

status:
	python main.py status

summaries:
	python main.py summaries

# Cleanup
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/

# Help
help:
	@echo "Available commands:"
	@echo "  install          Install the package"
	@echo "  install-dev      Install with development dependencies"
	@echo "  format           Format code with black and isort"
	@echo "  lint             Run linting with flake8 and mypy"
	@echo "  test             Run pytest tests"
	@echo "  test-integration Run integration tests"
	@echo "  run              Start the CLI interface"
	@echo "  run-api          Start the FastAPI server"
	@echo "  pipeline         Run the newsletter processing pipeline"
	@echo "  status           Show system status"
	@echo "  summaries        Show recent summaries"
	@echo "  clean            Clean up build artifacts"
	@echo "  help             Show this help message"