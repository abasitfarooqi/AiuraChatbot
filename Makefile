.PHONY: help install start stop restart test clean

help:
	@echo "AiuraChatbot - Available commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make start     - Start the application"
	@echo "  make stop      - Stop the application"
	@echo "  make restart   - Restart the application"
	@echo "  make test      - Run tests"
	@echo "  make clean     - Clean temporary files"

install:
	python3 -m venv venv
	. venv/bin/activate && pip install -r requirements.txt
	mkdir -p data logs
	@if [ ! -f .env ]; then cp .env.example .env; fi

start:
	./scripts/start.sh

stop:
	./scripts/stop.sh

restart:
	./scripts/restart.sh

test:
	. venv/bin/activate && pytest

clean:
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

