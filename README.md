# TradingHelper

Educational NSE stock tracking dashboard with 4-indicator confluence engine, charting, paper trade journal, break-even calculator, and conditional exit alert engine.

## Quick Start (Run Both Backend & Frontend)

Depending on your preferred shell:

- **PowerShell**: `.\run.ps1`
- **Command Prompt (CMD) / Double-click**: `run.bat`
- **Git Bash / Linux / Mac**: `./run.sh`
- **Makefile**: `make dev`

---

## Running Manually

### Backend
```bash
cd backend
conda run -n ai uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- API Docs: http://localhost:8000/docs

### Frontend
```bash
cd frontend
npm run dev
```
- App UI: http://localhost:5173