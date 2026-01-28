# Colors for help system
BLUE := \033[36m
YELLOW := \033[33m
GREEN := \033[32m
RESET := \033[0m

.DEFAULT_GOAL := help

##@ General
.PHONY: help
help: ## Display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\n$(BLUE)Usage:$(RESET)\n  make $(YELLOW)<target>$(RESET)\n"} \
		/^[a-zA-Z0-9_-]+:.*?##/ { printf "  $(YELLOW)%-20s$(RESET) %s\n", $$1, $$2 } \
		/^##@/ { printf "\n$(GREEN)%s$(RESET)\n", substr($$0, 5) }' $(MAKEFILE_LIST)

##@ Development
.PHONY: install
install: ## Install dependencies via uv
	uv sync

.PHONY: dev
dev: ## Run the Streamlit application
	uv run streamlit run app.py --server.headless true

.PHONY: lint
lint: ## Run linters tests
	uv run pre-commit run --all-files

.PHONY: sum
sum: ## Generate summary of the project
	lsproj > lsproj > sum.txt && lsproj | pysum >> sum.txt

.PHONY: all
all: ## Put whole project code into a file
	lsproj | xargs mdcat -o all.txt

.PHONY: mut
mut: ## Run mutation tests
	rm -rf mutants && uv run mutmut run --paths-to-mutate=services/repository.py

.PHONY: mut-ai
mut-ai: ## Mutate aireview tool
	rm -rf mutants && uv run mutmut run --paths-to-mutate=src/aireview/core.py --tests-dir=tests/test_aireview.py

.PHONY: exp
exp: ## Export mutants to markdown
	uv run mutmut export-diffs --status survived

.PHONY: test-html
test-html: ## Run tests with HTML coverage report
	uv run pytest --cov=services --cov=models --cov=pages --cov-report=html --cov-report=term
	@echo "$(GREEN)Coverage report generated in htmlcov/index.html$(RESET)"

.PHONY: test-cov
test-cov: ## Run tests with coverage (uses defaults from pyproject.toml)
	uv run pytest

.PHONY: test
test: ## Run tests WITHOUT coverage
	uv run pytest --no-cov

.PHONY: watch
watch: ## Run tests in watch mode
	uv run pytest-watcher .

.PHONY: clean
clean: ## Remove cache and virtual environment
	rm -rf .venv
	rm -rf .pytest_cache
	rm -rf __pycache__
	rm -rf htmlcov
	rm -rf .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} +

# uv run mutmut run --paths-to-mutate=services/repository.py --tests-dir=tests/

# uv run mutmut run --paths-to-mutate=services/repository.py --tests-dir=tests/test_repository_tdd.py

# uv run mutmut export-diffs --module services.repository



# /Users/michal/PycharmProjects/task_classifier_rd/.venv/lib/python3.14/site-packages/mutmut/__init__.py
