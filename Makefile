.PHONY: dev test init deploy

dev:
	uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest backend/tests/ -v

init:
	pip install -r requirements.txt

deploy:
	docker-compose up -d --build
