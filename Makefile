.PHONY: dev test init dashboard deploy

dev:
	cd backend && uvicorn app.main:app --reload --port 8000

dashboard:
	streamlit run dashboard/app.py

test:
	cd backend && pytest tests/ -v

init:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	@echo "Done. Copy .env.example to .env and fill in your MIMO_API_KEY"

deploy:
	docker-compose up -d --build

logs:
	docker-compose logs -f backend

ai-cost:
	curl -s http://localhost:8000/api/dashboard/stats | python3 -m json.tool
