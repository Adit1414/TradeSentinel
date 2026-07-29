.PHONY: help dev backend frontend

help:
	@echo "TradingHelper Run Commands:"
	@echo "  make dev      - Start backend and frontend together"
	@echo "  make backend  - Start FastAPI backend"
	@echo "  make frontend - Start Vite frontend"

backend:
	cd backend && conda run -n ai uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

dev:
	@bash run.sh
