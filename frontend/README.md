# AI Stock Market Analysis, Forecasting & Risk Assessment Platform

A full-stack stock-market analysis application combining historical market data, fundamental and technical indicators, news sentiment analysis, machine-learning explanations, portfolio analytics, and investment simulations.

**Technology stack:** Django REST Framework, PostgreSQL, Vue 3, Vite, and Plotly.

> **Disclaimer:** This is an educational and analytical project, not financial advice. Historical performance, forecasts, sentiment scores, and risk metrics do not guarantee future results. Demo portfolio holdings are illustrative and are not verified brokerage transactions.

## Features

### Stock Screener
- Search and filter active stocks by company, sector, exchange, valuation metrics, and technical indicators.
- Sort and paginate results.
- Inspect fundamental, technical, and sentiment information where data is available.

### Market Data and Charts
- Store historical stock prices and company fundamentals in PostgreSQL.
- Retrieve market data through `yfinance`.
- Visualize stock prices and technical indicators with interactive Plotly charts.
- Refresh data using Django management commands.

### Machine Learning and Explainability
- Machine-learning workflows using scikit-learn and XGBoost.
- Prediction explanation visualizations.
- Transformer-based news sentiment analysis.
- Model evaluation and validation tooling.

### Portfolio Analysis
- Create portfolios and manage holdings.
- Calculate market value, cost basis, unrealized profit/loss, returns, and portfolio weights.
- Review historical volatility, maximum drawdown, and period returns where sufficient data exists.

### Investment Simulator
- Model an initial investment with optional recurring monthly contributions.
- Examine estimated historical investment value over a selected period.
- Display an investment-performance curve and calculated returns.

### Alerts
- Configure price- and sentiment-based alert rules.
- Evaluate rules against stored market data and analyzed news.
- Review triggered events and mark notifications as read.

## Technology

| Layer | Technologies |
|---|---|
| Frontend | Vue 3, Vue Router, Vite, Axios |
| Charts | Plotly finance distribution |
| Backend | Python, Django, Django REST Framework |
| Database | PostgreSQL |
| Market data | yfinance |
| Machine learning | scikit-learn, XGBoost, PyTorch, Transformers, SHAP |
| Testing | Django automated tests and browser smoke tests |

## Project Structure

```text
ai-stock-market-platform/
├── backend/
│   ├── config/                 # Django settings and URL configuration
│   ├── stocks/                 # Stock universe and stock API
│   ├── market_data/            # Prices, fundamentals, news, screening and ML
│   ├── portfolios/             # Portfolio and holdings analytics
│   ├── alerts/                 # Alert rules and event evaluation
│   ├── requirements.txt
│   └── manage.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── services/
│   │   ├── views/
│   │   └── router.js
│   ├── package.json
│   └── vite.config.js
├── docs/
├── data/
├── .env.example
└── README.md