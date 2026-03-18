PYTHON ?= python

.PHONY: setup run test lint build deploy security-check clean

setup:
	$(PYTHON) scripts/validate_env_example.py
	@echo "Setup concluido. Copie .env.example para .env e ajuste os valores."

run:
	docker compose up -d --build

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m flake8 data_pipeline/src models api_service/app security/tests tests scripts dashboard

build:
	docker compose build

deploy:
	$(PYTHON) scripts/mock_deploy.py

security-check:
	$(PYTHON) scripts/check_secrets.py
	$(PYTHON) -m bandit -q -r data_pipeline/src models api_service/app security/tests scripts

clean:
	docker compose down -v --remove-orphans
