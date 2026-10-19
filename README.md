# AI Stock Market Analysis, Forecasting & Risk Assessment Platform

A full-stack application for exploring stock-market data, technical indicators, machine-learning analysis, portfolio performance, and investment scenarios.

## Features

- **Market Dashboard:** Stock overview, historical prices, and interactive charts.
- **Technical Analysis:** Price charts and technical indicators for market analysis.
- **Machine Learning:** Forecasting pipelines, model selection, uncertainty analysis, and explainability tools.
- **Backtesting:** Strategy evaluation, performance analysis, sensitivity analysis, and walk-forward validation.
- **Stock Screener:** Screen stocks using supported market metrics and criteria.
- **News Sentiment:** Stock-news ingestion and sentiment analysis.
- **Portfolio Management:** Manage holdings and review portfolio analytics.
- **Alerts:** Configure and evaluate stock-market alert rules.
- **Investment Simulator:** Explore investment scenarios and potential outcomes.

## Technology Stack

| Component | Technologies |
|---|---|
| Frontend | Vue 3, Vite, JavaScript |
| Charts | Plotly Finance |
| Backend | Python, Django, Django REST Framework |
| Database | PostgreSQL |
| Market Data | yfinance |
| Machine Learning | scikit-learn, XGBoost, PyTorch, Transformers, SHAP |
| Testing | Django tests and frontend build checks |

## Project Structure

```text
ai-stock-market-platform/
├── backend/
│   ├── config/                 # Django configuration and URL routing
│   ├── stocks/                 # Stock-related functionality
│   ├── market_data/            # Market data, screening, news, and ML APIs
│   ├── portfolios/             # Portfolio models and APIs
│   ├── alerts/                 # Alert rules and evaluation
│   ├── ml_engine.py            # Machine-learning functionality
│   ├── ml_models.py            # ML model implementations
│   ├── ml_pipeline.py          # ML pipeline
│   ├── backtesting.py          # Backtesting functionality
│   ├── requirements.txt        # Python dependencies
│   └── manage.py               # Django management commands
├── frontend/
│   ├── public/                 # Public assets
│   ├── src/
│   │   ├── components/         # Reusable UI and chart components
│   │   ├── services/           # API client
│   │   ├── views/              # Application pages
│   │   ├── App.vue
│   │   └── router.js
│   ├── package.json
│   └── README.md               # Frontend-specific instructions
├── data/                       # Project data, where applicable
├── docs/                       # Project documentation
├── .env.example                # Environment configuration template
├── .gitignore
└── README.md
