# TradeSentinel 📈

TradeSentinel is a comprehensive trading platform featuring interactive charting, paper trading, technical analysis, and real-time market data. Built with a modern tech stack, it provides an intuitive interface for both beginner and experienced traders to practice trading strategies, analyze charts, and track their performance without financial risk.

> 📚 **Looking for deep-dive technical documentation?**  
> For end-to-end architecture, API reference, database schema/ERD, 4-indicator confluence engine details, background scanner flows, and deployment guides, check out the comprehensive [TradeSentinel_Complete_Documentation.md](./TradeSentinel_Complete_Documentation.md).

## 🌟 Key Features

*   **🔒 Secure Authentication System**: User registration and login using robust JWT-based authentication.
*   **📊 Interactive Charting**: Advanced charting capabilities using Lightweight Charts, featuring:
    *   Price Charts (Candlesticks/Line)
    *   MACD (Moving Average Convergence Divergence) Panel
    *   RSI (Relative Strength Index) Panel
*   **💸 Paper Trading Simulator**: Practice trading with virtual capital. Execute buy/sell orders and track your portfolio in real-time.
*   **📈 Watchlist Management**: Add, remove, and monitor your favorite stock tickers effortlessly.
*   **💼 Position Tracking**: Monitor your active and closed positions, track P&L (Profit & Loss), and manage risk.
*   **📓 Trading Journal**: Document your thoughts, strategies, and lessons learned for every trade to improve your edge.
*   **🔔 Alerts System**: Set custom price and indicator alerts so you never miss a trading opportunity.
*   **🔍 Technical Analysis & Scanning**: Built-in calculators, confluence scanners, and exit scanners powered by `pandas-ta` to identify optimal entry and exit points.

## 🛠️ Technology Stack

**Frontend:**
*   React 19 (Vite)
*   React Router v7 (Navigation)
*   React Query (@tanstack/react-query for state and data fetching)
*   Lightweight Charts (TradingView charts)
*   Lucide React (Icons)
*   Axios

**Backend:**
*   FastAPI (High-performance asynchronous Python web framework)
*   SQLAlchemy & aiosqlite (Database ORM & SQLite async driver)
*   yfinance (Market data provider)
*   pandas & pandas-ta-classic (Data manipulation and technical indicators)
*   APScheduler (Background task scheduling for scanners and alerts)
*   python-jose & passlib (Authentication and cryptography)

## 🚀 Getting Started

### Prerequisites
*   Node.js (v18+)
*   Python (3.9+)
*   Git

### 1. Clone the repository
```bash
git clone https://github.com/Adit1414/TradeSentinel.git
cd TradeSentinel
```

### 2. Setup the Backend
Navigate to the backend directory and set up a virtual environment:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```
Run the FastAPI server:
```bash
uvicorn app.main:app --reload
```
The backend API will be available at `http://localhost:8000`.

### 3. Setup the Frontend
Open a new terminal and navigate to the frontend directory:
```bash
cd frontend
npm install
npm run dev
```
The frontend application will be available at `http://localhost:5173` (or your Vite default port).

### Alternative: Using the Run Script
You can also start both the frontend and backend simultaneously using the provided bash script or Makefile:
```bash
./run.sh
# OR
make run
```

## 📂 Project Structure

```text
TradeSentinel/
├── backend/                  # FastAPI Backend
│   ├── app/                  # Application Logic
│   │   ├── routers/          # API Endpoints (auth, market_data, paper_trade, etc.)
│   │   ├── services/         # Business logic (indicators, scanners, calculator)
│   │   ├── utils/            # Helper utilities
│   │   ├── models.py         # SQLAlchemy Database Models
│   │   ├── schemas.py        # Pydantic Schemas
│   │   └── main.py           # FastAPI Application Entry
│   └── requirements.txt      # Python Dependencies
│
├── frontend/                 # React Frontend
│   ├── src/
│   │   ├── api/              # Axios API Client
│   │   ├── components/       # Reusable UI Components (Chart, Layout, PaperTrade, Watchlist)
│   │   ├── contexts/         # React Contexts (AuthContext)
│   │   ├── pages/            # Application Pages (Dashboard, Chart, Login, etc.)
│   │   └── App.jsx           # Main App Component
│   └── package.json          # Node Dependencies
│
├── .gitignore
├── Makefile
├── run.sh                    # Helper script to launch the app
└── TradeSentinel_Complete_Documentation.md # End-to-end technical documentation
```

## 📝 License
This project is open-source and available under the MIT License.
