# MarketPulse — AI Stock Market Platform

MarketPulse is a full-stack stock-market research and portfolio analytics application. It combines a Django REST API with a Vue 3 frontend and provides tools for exploring US and UK equities, reviewing market data, studying technical and fundamental indicators, monitoring news sentiment, and analysing investment portfolios.

> **Project status:** Development / research project. Market data and model outputs depend on external providers, data availability, and the quality of the stored history. Forecasts, recommendations, simulations, and backtests are experimental research tools. They are not financial advice, do not guarantee returns, and should not be used as the sole basis for investment decisions. The application does not place live trades.

---

## Contents

1. [Main capabilities](#main-capabilities)
2. [Technology stack](#technology-stack)
3. [Repository structure](#repository-structure)
4. [Prerequisites](#prerequisites)
5. [Clone the repository](#1-clone-the-repository)
6. [Set up PostgreSQL](#2-set-up-postgresql)
7. [Configure environment variables](#3-configure-environment-variables)
8. [Set up the Django backend](#4-set-up-the-django-backend)
9. [Set up the Vue frontend](#5-set-up-the-vue-frontend)
10. [Run the application](#6-run-the-application)
11. [Create an admin account](#7-create-an-admin-account)
12. [Populate stock and market data](#8-populate-stock-and-market-data)
13. [Run tests and build checks](#9-run-tests-and-build-checks)
14. [Useful development commands](#useful-development-commands)
15. [Troubleshooting](#troubleshooting)
16. [Security and production notes](#security-and-production-notes)
17. [Financial-data limitations](#financial-data-limitations)

---

## Main capabilities

The current application includes the following areas:

- **Dashboard:** market overview, benchmark performance, latest available stock quotes, tracked stocks, saved investment preferences, and news-sentiment summaries.
- **Stock discovery:** searchable stock catalogue for supported US and UK markets.
- **Stock screener:** filter and explore stocks using available company and market attributes.
- **Stock research workspace:** individual stock research pages with historical price charts, technical indicators, company/market context, risk information, explainability outputs, and news sentiment where data is available.
- **Portfolio intelligence:** create portfolios, record holdings, review valuations, and inspect portfolio risk metrics. Values are kept in their relevant currencies; do not add GBP and USD values together unless a valid FX conversion is applied.
- **Investment simulator:** explore hypothetical investment scenarios using historical data.
- **Recommendations and ML research:** inspect experimental quantitative features and model-generated research signals.
- **Alerts and notifications:** configure and review supported price/news-related alert events.
- **User accounts:** register, log in, manage profile information, and use authenticated application pages.

Some screens can be empty until the stock catalogue, historical prices, news, and analysis records have been populated.

## Technology stack

### Backend

| Component | Technology |
|---|---|
| Language | Python 3.13.x |
| Web framework | Django 6.1.1 |
| API | Django REST Framework 3.18.1 |
| Database | PostgreSQL |
| PostgreSQL driver | psycopg 3.3.6 (binary extra) |
| Data analysis | NumPy 2.5.3, pandas 3.0.6, SciPy 1.17.0 |
| Machine learning | scikit-learn 1.9.1, XGBoost 3.4.1, SHAP 0.54.1, joblib 1.6.0 |
| Market data / HTTP | yfinance 1.7.0, requests 2.34.2 |
| NLP / model runtime | PyTorch 2.14.1, Transformers 5.20.1 |
| Environment configuration | python-dotenv 1.2.3 |

The pinned backend dependencies are listed in [`backend/requirements.txt`](backend/requirements.txt). Use that file as the source of truth when installing Python packages.

### Frontend

| Component | Technology |
|---|---|
| Framework | Vue 3.5 |
| Build tool / dev server | Vite 8.3 |
| Routing | Vue Router 5 |
| State management | Pinia 4 |
| HTTP client | Axios 1.20 |
| Charts | Plotly Finance distribution |
| Image cropping | CropperJS |
| Language | JavaScript (ES modules) |

Frontend scripts are defined in [`frontend/package.json`](frontend/package.json): `npm run dev`, `npm run build`, and `npm run preview`.

---

## Repository structure

```text
ai-stock-market-platform/
├── backend/
│   ├── config/                 # Django settings, root URLs, ASGI/WSGI
│   ├── accounts/               # Authentication and user profile APIs
│   ├── stocks/                 # Stock catalogue and stock management commands
│   ├── market_data/             # Prices, benchmarks, indicators, ML, news and simulation APIs
│   ├── portfolios/              # Portfolio and holding APIs / analysis
│   ├── alerts/                  # Alert rules and notification events
│   ├── data/                    # Local data and generated research artefacts
│   ├── media/                   # User-uploaded media in local development
│   ├── manage.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/          # Shared UI, charts and layout components
│   │   ├── services/            # API client and service functions
│   │   ├── views/               # Dashboard, research, portfolio and other pages
│   │   ├── router.js
│   │   └── main.js
│   ├── package.json
│   └── vite.config.js
├── .env                         # Local secrets and database configuration (create locally)
└── README.md
```

The `.env` file belongs in the **repository root**, beside the `backend/` and `frontend/` folders. Django loads it from that location.

---

## Prerequisites

Install the following before setting up the project:

| Requirement | Recommended version / notes |
|---|---|
| macOS, Linux, or Windows with WSL | Development instructions below use macOS Terminal |
| Git | Required to clone and update the repository |
| Python | Python 3.13.x; the project has been developed with Python 3.13.2 |
| pip | Included with Python; used to install backend requirements |
| Node.js | Node.js 24.x recommended for the current Vite setup |
| npm | Included with Node.js; npm 11.x is suitable |
| PostgreSQL | A running local PostgreSQL server and a database/user for the project |
| Internet access | Needed for repository/package installation and external market/news data; NLP models may also need to be downloaded on first use |

Check your installed tools:

```bash
python3.13 --version
node --version
npm --version
git --version
psql --version
```

If `python3.13` is not found, install Python 3.13 and make sure it is available on your shell `PATH`. If PostgreSQL is already installed, you do not need to install it again.

### macOS installation hints

Using Homebrew, if the tools are not already installed:

```bash
brew install python@3.13
brew install node
brew install postgresql@16
brew services start postgresql@16
```

Homebrew service names and executable paths can differ by PostgreSQL version and machine. If you use Postgres.app or another PostgreSQL installation, start that service instead.

---

## 1. Clone the repository

Open Terminal and run:

```bash
git clone https://github.com/pawankukreja01/ai-stock-market-platform.git
cd ai-stock-market-platform
```

If you already have the repository locally, open its root directory instead:

```bash
cd ~/Desktop/ai-stock-market-platform
```

Confirm that the main folders exist:

```bash
ls
```

You should see at least `backend/` and `frontend/`.

---

## 2. Set up PostgreSQL

The Django settings use PostgreSQL. SQLite is not the configured application database.

### 2.1 Start PostgreSQL

For a Homebrew installation:

```bash
brew services start postgresql@16
```

If PostgreSQL is already running, continue to the next step.

### 2.2 Create a database and application user

Open a PostgreSQL shell:

```bash
psql postgres
```

Run the following SQL. Replace the example password with a strong local password:

```sql
CREATE ROLE marketpulse_user WITH LOGIN PASSWORD 'replace-with-a-strong-password';
CREATE DATABASE ai_stock_market OWNER marketpulse_user;
ALTER ROLE marketpulse_user CREATEDB;
\q
```

`CREATEDB` allows Django's test runner to create its temporary test database. If the role or database already exists, do not run the corresponding `CREATE` statement again; inspect the existing configuration and update it as appropriate.

You can test the database connection with:

```bash
psql -h 127.0.0.1 -U marketpulse_user -d ai_stock_market
```

Enter the password when prompted, then exit with `\q`.

---

## 3. Configure environment variables

Create a `.env` file in the repository root:

```bash
cd ~/Desktop/ai-stock-market-platform
nano .env
```

Paste the following and replace the database password. Generate a new Django secret key rather than using the example value:

```dotenv
# Django
DJANGO_SECRET_KEY=replace-with-a-generated-secret-key
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,[::1]

# PostgreSQL
DB_NAME=ai_stock_market
DB_USER=marketpulse_user
DB_PASSWORD=replace-with-your-database-password
DB_HOST=127.0.0.1
DB_PORT=5432
```

Generate a Django secret key after installing the backend dependencies (Step 4):

```bash
cd ~/Desktop/ai-stock-market-platform
source .venv/bin/activate
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy the generated value into `DJANGO_SECRET_KEY` in `.env`.

Save the file in `nano` with **Control + O**, press **Enter**, then **Control + X**.

**Important:** Do not commit `.env` or share its contents. The development settings can fall back to a local-only insecure secret when `DJANGO_DEBUG=true`, but you should still use a generated secret. For any non-local environment, set a real secret, set `DJANGO_DEBUG=false`, and configure `DJANGO_ALLOWED_HOSTS` correctly.

---

## 4. Set up the Django backend

The virtual environment is created in the repository root so both backend commands and local tooling can use the same environment.

### 4.1 Create and activate the virtual environment

From the repository root:

```bash
cd ~/Desktop/ai-stock-market-platform
python3.13 -m venv .venv
source .venv/bin/activate
```

When activated, your terminal prompt should show `(.venv)` or the environment name.

If `.venv` already exists and is working, do not recreate it; simply activate it:

```bash
source .venv/bin/activate
```

### 4.2 Upgrade pip and install backend dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

The ML/NLP packages, especially PyTorch and Transformers, are large and may take longer to install than the basic Django packages. Allow enough disk space. The first use of a pretrained NLP model may also require an internet connection to download model files.

### 4.3 Run Django checks and database migrations

```bash
cd backend
python manage.py check
python manage.py migrate
```

The `migrate` command creates or updates the application tables in the PostgreSQL database.

### 4.4 Verify migration state (optional)

```bash
python manage.py showmigrations
python manage.py makemigrations --check --dry-run
```

The second command should report that no model changes are missing from migrations. Do not generate migrations unless you have intentionally changed Django models.

---

## 5. Set up the Vue frontend

Open a **second Terminal window**. Keep the backend virtual environment active in the first window; the frontend has its own Node dependencies.

```bash
cd ~/Desktop/ai-stock-market-platform/frontend
npm install
```

`npm install` installs the packages declared in `frontend/package.json` and updates/uses the npm lock file as appropriate.

### Frontend API connection

The Axios client uses the relative API base path `/api` and sends browser credentials for Django session authentication. During local development, the Vite development server must proxy `/api` requests to Django at `http://127.0.0.1:8000` (and `/media` requests to the backend if local profile images need to be served).

The Vite configuration should contain equivalent proxy settings. Merge these into the existing `defineConfig` object if they are missing; do not replace other project configuration:

```javascript
server: {
  proxy: {
    "/api": {
      target: "http://127.0.0.1:8000",
      changeOrigin: true,
    },
    "/media": {
      target: "http://127.0.0.1:8000",
      changeOrigin: true,
    },
  },
},
```

If API requests fail even though both servers are running, inspect `frontend/vite.config.js` and confirm that its development-server proxy points to the backend port shown above. Do not change the API client base path to a hard-coded external URL for ordinary local development.

---

## 6. Run the application

Run the backend and frontend in **two separate Terminal windows**.

### Terminal 1 — Django backend

```bash
cd ~/Desktop/ai-stock-market-platform
source .venv/bin/activate
cd backend
python manage.py runserver 127.0.0.1:8000
```

Expected local backend address:

- Django server: `http://127.0.0.1:8000/`
- Django admin: `http://127.0.0.1:8000/admin/`
- API base path: `http://127.0.0.1:8000/api/`

Leave this terminal running.

### Terminal 2 — Vue / Vite frontend

```bash
cd ~/Desktop/ai-stock-market-platform/frontend
npm run dev
```

Vite prints the local URL in the terminal. Usually it is:

- Frontend: `http://localhost:5173/`

Open the exact URL printed by Vite. If port `5173` is already occupied, Vite may automatically choose `5174` or another port. When that happens, make sure the Django CSRF trusted-origin configuration and Vite proxy configuration allow the actual frontend port.

### First login

1. Open the frontend URL printed by Vite.
2. Select **Create an account** / **Register**.
3. Register using your name, email address, and a strong password.
4. Log in with the new account if the registration flow returns you to the login screen.
5. Open the Dashboard and then explore Discover Stocks, Stock Screener, Stock Research, Portfolio, Investment Simulator, Recommendations, and Alerts.

The application uses Django session authentication and CSRF protection. Keep the browser and both servers on the configured local origins so session cookies and CSRF checks work correctly.

---

## 7. Create an admin account

A Django superuser is optional for normal frontend registration, but useful for inspecting database records through Django Admin.

In the backend terminal:

```bash
cd ~/Desktop/ai-stock-market-platform/backend
source ../.venv/bin/activate
python manage.py createsuperuser
```

Follow the prompts. Then open:

`http://127.0.0.1:8000/admin/`

---

## 8. Populate stock and market data

A newly created database may contain no stock records or historical observations. Some dashboard cards and research panels will remain empty until data has been loaded.

### 8.1 Discover available data-management commands

From `backend/` with the virtual environment active:

```bash
python manage.py help
python manage.py help seed_stock_universe
python manage.py help backfill_stock_history
python manage.py help ingest_stock_history
```

The repository includes stock-universe and historical-price management commands. Read each command's help output before running it, because options can change as the data pipeline evolves.

### 8.2 Seed the stock catalogue

Use the options shown by:

```bash
python manage.py help seed_stock_universe
```

Then run the stock-universe seed command with the desired market/universe options. Avoid seeding duplicate catalogue entries if the database is already populated.

### 8.3 Ingest historical prices

The historical ingestion command accepts a stock symbol and a period. For example, to ingest one year of history for Apple:

```bash
python manage.py ingest_stock_history AAPL --period 1y
```

Use the command's `--help` output for other supported periods, symbols, and options. External data providers can return incomplete data or apply rate limits; ingestion may need to be retried later.

### 8.4 Backfill and benchmark data

For the stock-history backfill and benchmark-related commands, inspect their options first:

```bash
python manage.py help backfill_stock_history
```

Benchmark data may be cached locally under the backend data directory. That cache is generated data and should not be treated as source code.

### 8.5 News sentiment and model outputs

News sentiment and ML explanations require the relevant underlying news, price history, and model dependencies. Empty sentiment or explainability panels do not necessarily mean the frontend is broken; first verify that the relevant stock and source data exist and that the backend logs do not show provider/model errors.

---

## 9. Run tests and build checks

Run checks before committing changes.

### Backend system check

From `backend/`:

```bash
source ../.venv/bin/activate
python manage.py check
```

### Backend test suite

```bash
python manage.py test
```

Run an individual Django app's tests when debugging a focused area:

```bash
python manage.py test portfolios
python manage.py test market_data
python manage.py test stocks
python manage.py test alerts
python manage.py test accounts
```

Django creates a temporary test database. The PostgreSQL user must have permission to create databases (the setup above grants `CREATEDB`).

### Frontend production build

Open another terminal or stop the frontend dev server with **Control + C**, then run:

```bash
cd ~/Desktop/ai-stock-market-platform/frontend
npm run build
```

Vite writes the production bundle to `frontend/dist/`. A successful build can still display a warning about a large Plotly bundle; a warning is not the same as a failed build.

### Preview the production build locally (optional)

```bash
npm run preview
```

Use the URL printed by Vite.

---

## Useful development commands

Run these from the relevant directory and with the backend virtual environment activated where required.

| Task | Command |
|---|---|
| Check Django configuration | `python manage.py check` |
| Apply migrations | `python manage.py migrate` |
| Show migrations | `python manage.py showmigrations` |
| Check for missing migrations | `python manage.py makemigrations --check --dry-run` |
| Create admin user | `python manage.py createsuperuser` |
| Run all backend tests | `python manage.py test` |
| Run portfolio tests | `python manage.py test portfolios` |
| List management commands | `python manage.py help` |
| See ingestion options | `python manage.py help ingest_stock_history` |
| Install frontend packages | `npm install` |
| Start frontend | `npm run dev` |
| Build frontend | `npm run build` |
| Preview frontend build | `npm run preview` |

Stop a running server with **Control + C** in its terminal.

---

## Troubleshooting

### 1. `Error: That port is already in use`

Another process may already be running Django on port `8000` or Vite on port `5173`. Check which process is listening:

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
lsof -nP -iTCP:5173 -sTCP:LISTEN
```

If it is an old development server that you started, stop it from its original terminal with **Control + C**. Do not terminate an unfamiliar process. If Vite selects a different port, use the URL it prints and make sure the CSRF trusted origins and API proxy configuration include that port.

### 2. Django reports a PostgreSQL connection error

Check that PostgreSQL is running and that the values in the root `.env` match the database you created:

- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`

Test the connection directly with `psql -h 127.0.0.1 -U marketpulse_user -d ai_stock_market`.

### 3. `ModuleNotFoundError` when running Django

Activate the project virtual environment and install the pinned dependencies again:

```bash
cd ~/Desktop/ai-stock-market-platform
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
```

### 4. Login, registration, or API calls fail in the browser

1. Confirm the Django server is running on `127.0.0.1:8000`.
2. Confirm the frontend is using the Vite proxy for `/api`.
3. Check the browser developer console and the Django terminal for the actual HTTP status and error.
4. Confirm the frontend's actual port is included in Django's CSRF trusted origins.
5. Do not mix `localhost` and `127.0.0.1` casually; use the origins consistently during a session.

### 5. Dashboard loads, but no prices or benchmark observations appear

This is commonly a data-ingestion or provider-availability issue rather than a frontend startup issue. Check that:

- the stock exists in the stock catalogue;
- historical observations exist for the requested symbol and date range;
- the benchmark data cache has been populated or refreshed;
- external data-provider requests are not failing or rate-limited.

Review the backend terminal output and run the relevant management command's `--help` before re-running ingestion.

### 6. News sentiment or ML explanations are unavailable

Confirm that required historical/news data exists and that the Python environment includes the pinned ML/NLP requirements. The first model invocation may need internet access to download model files. Check the Django terminal for the full exception instead of assuming the model has returned a neutral or negative signal.

### 7. Frontend build fails after a dependency change

From `frontend/`:

```bash
npm install
npm run build
```

If the error remains, capture the complete terminal output and the Node/npm versions (`node --version`, `npm --version`) before changing package versions.

---

## Security and production notes

The commands in this README are for **local development**. Django's `runserver` and Vite's development server are not production deployment servers.

Before deploying to a public environment, at minimum:

- Set `DJANGO_DEBUG=false`.
- Generate and store a unique `DJANGO_SECRET_KEY` outside source control.
- Set `DJANGO_ALLOWED_HOSTS` to the exact production hostnames.
- Configure HTTPS, secure session/CSRF cookies, and trusted origins for the real frontend domain.
- Configure a real production email backend if email verification or password-reset delivery is required; do not rely on console email output.
- Use a managed or properly secured PostgreSQL database with backups and least-privilege credentials.
- Serve user-uploaded media from suitable persistent storage; do not rely on the local development `backend/media/` directory.
- Build and serve the frontend production bundle through an appropriate web server or hosting platform.
- Review logging, rate limits, secrets, CORS/CSRF policy, static assets, migrations, and database backup/restore procedures.

Never commit `.env`, database passwords, API credentials, private user media, generated datasets, or local virtual environments.

## Financial-data limitations

- Market data is retrieved from external providers and may be delayed, incomplete, adjusted, unavailable, or rate-limited.
- US and UK securities can be quoted in different currencies. Portfolio values and returns must be compared within the same currency unless a documented FX conversion is used.
- Historical backtests are sensitive to survivorship bias, look-ahead bias, data leakage, missing observations, corporate actions, liquidity, spread, and transaction-cost assumptions.
- Model results are experimental. A model should not be described as predictive or profitable merely because it produces a forecast or recommendation.
- News sentiment describes the text analysed; it is not a direct forecast of future stock returns.
- Simulations and portfolio risk calculations depend on the data window and assumptions shown by the application. They may not reflect real execution, slippage, taxes, fees, or changing holdings unless those effects are explicitly modelled.

---

## Contributing / making changes

1. Create a branch for your change.
2. Keep secrets, local databases, uploads, generated data, temporary patch scripts, and diagnostic bundles out of commits.
3. Add or update backend tests for API, calculation, and data-quality changes.
4. Run `python manage.py check` and the relevant Django tests.
5. Run `npm run build` for frontend changes.
6. Review `git status --short` and `git diff --check` before committing.

For bugs, include the relevant command, full error output, and the affected feature. Never include passwords, tokens, or private user data in an issue or log excerpt.

---

## Forecast evidence and launch gates

The ML prediction API at `GET /api/ml-prediction/?symbol=AAPL&horizon=5&model=random_forest`
returns a *research forecast* of the return after hypothetical execution at the
**next session close**. It does not know that future entry price, so the API
does not assert a current-to-future target share price. It returns training,
calibration and test diagnostics and, on the development branch, an `evidence`
object with the following fields:

- `model_mae`: mean absolute forecast error on the chronologically held-out test block.
- `baselines.zero_return` and `baselines.training_mean_return`: the same error metric
  calculated on that *same* test block. The mean-return baseline is fitted only on
  the training block.
- `mae_skill_vs_best_baseline`: relative error reduction versus the stronger
  of those baselines. Negative values mean the ML model performs worse.
- `holdout_interval_coverage`: empirical test coverage of the range calibrated
  on a separate historical block, not a guarantee of future coverage.
- `price_age_days`, `approx_non_overlapping_holdout_windows`, and `warnings`:
  basic validity checks. Multi-day overlapping labels can greatly overstate
  the effective number of test observations.
- `ready_for_live_trading`: **always false**. One holdout comparison cannot
  establish a production trading edge.

The evidence status `promising_holdout_only` means a *single historical holdout*
met basic diagnostic thresholds, **not** that the stock is likely to rise or that
a strategy is profitable. `limited_evidence` marks cases needing particular caution.
No model-selection or recommendation scoring logic should consume the evidence
status as a trading signal without a separate rigorous study.

### Read-only stored data audit

Run against the **restored development database**, never the original user database:

```bash
cd backend
DB_NAME=marketpulse_restored_test python manage.py audit_market_readiness
```

This lists the proportion of active stocks with at least 300 positive stored
closes and a price date within seven calendar days, plus stocks without any
fundamental or news records. It **does not download data**, update the database,
assess financial-data licensing, or certify model accuracy.

For one-symbol ingestion where a provider permits the intended use, see
`python manage.py refresh_market_data --symbol AAPL --period 5y`.
Back up the working database before running any ingestion, and review provider
rate limits, exchange entitlements, timestamps, and adjustment policies.

### Repeatable multi-stock forecasting study

Use the restored database to compare one ML model against three simple
baselines across multiple symbols and expanding walk-forward folds. The
command reads stored prices only, without downloading new quotes or changing
any tables:

```bash
cd backend
DB_NAME=marketpulse_restored_test python manage.py validate_stock_forecasts \\
  --symbols AAPL MSFT GOOGL AMZN NVDA \\
  --model random_forest --horizon 5 --min-train 500 --test-size 100 \\
  --output ~/Desktop/marketpulse_walk_forward_5d.json
```

The output file is optional; existing report files are **not overwritten**.
Run this separately for the competing models and horizons; record exceptions,
failed baselines, fold-to-fold variation and excluded stocks. The command
does **not** include dynamically retrieved benchmark features, cross-sectional
portfolio allocation, survivorship correction, or realistic trading costs.
Never select the best-performing model and cite those same test dates as an
unbiased final validation; reserve new forward dates for confirmation.

### Requirements before a real public market launch

1. Run a multi-market, multi-stock **purged walk-forward study** of all candidate
   models versus trivial baselines. Use corporate-action-adjusted price histories
   where appropriate, realistic costs, delisting/survivorship checks and frozen
   evaluation periods. Report per-horizon and per-regime failures, not just averages.
2. Validate data-provider commercial redistribution rights, exchange market-data
   agreements, and the availability of delayed/realtime quotes for the proposed
   audience. A development-only Yahoo Finance feed should not be assumed to
   authorize a paid production product.
3. Implement and validate production ingestion scheduling, retries, idempotent
   upserts, source provenance, failure alerting, stale-data gating, and model
   re-training/monitoring. A forecast based on old data must never masquerade
   as an up-to-date signal.
4. Deploy on an HTTPS environment with real secrets management, persistent
   PostgreSQL backups and recovery drills, user account protections, rate
   limiting, dependency scanning, CI/CD rollback, observability and audit trails.
   Validate session cookies and CSRF in the *real* frontend/backend origin setup.
5. Perform cross-user authorization tests, browser/mobile QA, accessibility,
   billing/privacy reviews if applicable, and jurisdiction-specific legal review
   before offering personalized investment recommendations. Financial research
   must not be marketed as guaranteed stock-price prediction.
6. Require a live staged smoke test on a **copy** of user market data. CI passing
   on synthetic test data is not proof that external APIs, models and deploys work.

The development branch is **not** a production release until those gates are
demonstrably passed. The original `ai_stock_market` PostgreSQL database and
its backup should remain untouched during branch testing.
