.DEFAULT_GOAL := help

PYTHON ?= python3
VENV ?= .venv
VENV_BIN := $(VENV)/bin
VENV_PYTHON := $(VENV_BIN)/python
VENV_PIP := $(VENV_BIN)/pip
REQUIREMENTS ?= requirements.txt
PACKAGE_NAME ?= grafana-mcp

IMAGE_NAME ?= grafana-ai-data-driven
CONTAINER_NAME ?= grafana-ai-data-driven
APP_PORT ?= 8000
APP_ADDRESS ?= 0.0.0.0:8000
BASE_PATH ?= /
LOG_LEVEL ?= INFO
TRANSPORT ?= stdio
ENV_FILE ?= .env

.PHONY: venv
venv:
	@if [ ! -x "$(VENV_PYTHON)" ]; then \
		$(PYTHON) -m venv $(VENV) && \
		$(VENV_PIP) install --upgrade pip; \
	fi
	@if [ -f "$(REQUIREMENTS)" ]; then \
		$(VENV_PIP) install -r $(REQUIREMENTS); \
	fi

.PHONY: local

local: venv
	@set -a; \
		if [ -f "$(ENV_FILE)" ]; then . "$(ENV_FILE)"; fi; \
		set +a; \
                $(VENV_PYTHON) -m app --address $(APP_ADDRESS) --base-path $(BASE_PATH) --log-level $(LOG_LEVEL) --transport $(TRANSPORT)

.PHONY: package
package: venv
	@$(VENV_PIP) install --upgrade pyinstaller >/dev/null
	@$(VENV_BIN)/pyinstaller --clean --onefile --name $(PACKAGE_NAME) run_app.py

.PHONY: docker
docker:
	@docker build -t $(IMAGE_NAME) -f Dockerfile .
	@ENV_FILE_OPT=""; \
		if [ -f "$(ENV_FILE)" ]; then ENV_FILE_OPT="--env-file $(ENV_FILE)"; fi; \
                docker run --rm -it --name $(CONTAINER_NAME) $$ENV_FILE_OPT -e LOG_LEVEL=$(LOG_LEVEL) -e APP_ADDRESS=$(APP_ADDRESS) -e BASE_PATH=$(BASE_PATH) -e TRANSPORT=$(TRANSPORT) -p $(APP_PORT):$(APP_PORT) $(IMAGE_NAME)

.PHONY: podman
podman:
	@podman build -t $(IMAGE_NAME) -f Dockerfile .
	@ENV_FILE_OPT=""; \
		if [ -f "$(ENV_FILE)" ]; then ENV_FILE_OPT="--env-file $(ENV_FILE)"; fi; \
                podman run --rm -it --name $(CONTAINER_NAME) $$ENV_FILE_OPT -e LOG_LEVEL=$(LOG_LEVEL) -e APP_ADDRESS=$(APP_ADDRESS) -e BASE_PATH=$(BASE_PATH) -e TRANSPORT=$(TRANSPORT) -p $(APP_PORT):$(APP_PORT) $(IMAGE_NAME)

.PHONY: clean
clean:
	@rm -rf $(VENV)
	@find . -type d -name '__pycache__' -prune -exec rm -rf {} +

.PHONY: clean-docker
clean-docker:
	@docker rm -f $(CONTAINER_NAME) 2>/dev/null || true
	@docker rmi -f $(IMAGE_NAME) 2>/dev/null || true

.PHONY: clean-podman
clean-podman:
	@podman rm -f $(CONTAINER_NAME) 2>/dev/null || true
	@podman rmi -f $(IMAGE_NAME) 2>/dev/null || true

.PHONY: help
help:
	@echo "Comandos disponíveis:"
	@echo "  make venv          - Cria/atualiza o ambiente virtual local"
	@echo "  make local         - Cria (se necessário) o venv e executa a aplicação localmente"
	@echo "  make package       - Gera um executável único via PyInstaller em dist/"
	@echo "  make docker        - Faz build e executa a imagem no Docker"
	@echo "  make podman        - Faz build e executa a imagem no Podman"
	@echo "  make clean         - Remove o ambiente virtual e caches Python"
	@echo "  make clean-docker  - Remove container/imagem do Docker"
	@echo "  make clean-podman  - Remove container/imagem do Podman"
	@echo "  make help          - Mostra este help"
