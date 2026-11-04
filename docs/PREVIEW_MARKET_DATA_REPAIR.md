# Repair an empty MarketPulse Docker preview using real stored market data

**Scope:** localhost-only development preview. This is NOT a live-market feed,
investment recommendation, production deployment, or permission to copy credentials.

## Why the UI looked empty

The Docker compose file explicitly connects to `marketpulse_preview` in its
own private PostgreSQL volume. The local restored research DB
`marketpulse_restored_test` has price histories, but the preview did not.
`seed_stock_universe` only adds stock *names*; it does not populate OHLCV
prices, quotes, fundamental statements, or news. The screens therefore showed:
- A selectable AAPL record with no cached quote.
- Empty charts, risk metrics, simulator results and strategy backtests.
- Zero eligible recommendations because no historical observations exist.
- Missing fundamentals and news sentiment where no stored provider rows exist.

The benchmark panel uses a separate provider/cache path. Its success does not
prove the stock OHLCV database contains any data.

## Safe data repair (NO Yahoo or external downloads)

Commands here only transfer whitelisted **stored market data** and explicitly
refuse wrong DB connections. No accounts, credentials, portfolios, personal
settings, alerts, sessions, passwords, or original database files are copied.
Export is read-only on the restored test DB. Import writes only to the separate
`marketpulse_preview` DB and never deletes or overwrites existing observations.
Source historical date, currency provenance, adjusted_close and quality flags
are retained; missing values are not synthesized.

From the original project directory on your Mac **after checking out this fix
branch**, using the existing Python virtual environment:

```bash
cd ~/Desktop/ai-stock-market-platform
mkdir -p marketpulse_model_evaluation
DB_NAME=marketpulse_restored_test \
  .venv/bin/python backend/manage.py export_preview_market_snapshot \
  --output marketpulse_model_evaluation/preview_market_archive.jsonl.gz

docker compose --env-file preview.env -f compose.preview.yml \
  cp marketpulse_model_evaluation/preview_market_archive.jsonl.gz \
  backend:/tmp/preview_market_archive.jsonl.gz

docker compose --env-file preview.env -f compose.preview.yml \
  exec backend python manage.py import_preview_market_snapshot \
  --input /tmp/preview_market_archive.jsonl.gz --dry-run

# After checking the dry-run counts, opt into writing to the isolated preview:
docker compose --env-file preview.env -f compose.preview.yml \
  exec backend python manage.py import_preview_market_snapshot \
  --input /tmp/preview_market_archive.jsonl.gz
```

**Important:** This repair branch changes Django management commands. Rebuild
the backend image before `compose cp` and import:

```bash
docker compose --env-file preview.env -f compose.preview.yml up -d --build
```

This preserves existing preview volumes. **Do not** run `down -v`,
`volume prune`, or restore the original entire database into preview.

Use an output filename that does not already exist (no exports are overwritten).
The importer first reads and validates the entire gzip stream; any malformed
type/field or unknown stock fails before writes. If the validation passes, a
single DB transaction imports only four approved models: Stock,
HistoricalPrice, Fundamental and NewsArticle. It never imports accounts or
ProspectiveForecast. Existing stock/price records are preserved. Re-running
the same import uses database uniqueness constraints to skip previously
imported observations.

After import, verify:

```bash
docker compose --env-file preview.env -f compose.preview.yml exec backend \
  python manage.py shell -c "from market_data.models import HistoricalPrice, Fundamental, NewsArticle; from stocks.models import Stock; print('stocks',Stock.objects.filter(is_active=True).count(),'historical_prices',HistoricalPrice.objects.count(),'fundamentals',Fundamental.objects.count(),'news',NewsArticle.objects.count())"
```

Reload localhost:8088. Expect a populated chart and risk metrics for stocks with
sufficient valid history. The quote card now shows the most recent *stored*
daily close if no cached quote exists, marked **stale/ARCHIVED**, never as live.
Fundamentals and sentiment display only genuinely stored records. The
recommendations page includes coverage reasons instead of an ambiguous blank
result. A stale source archive can still yield zero *current* recommendations
because the application intentionally excludes prices over seven days old.

## Boundaries and remaining work

1. This is an opt-in **local repair**, not proof of a complete product. No
   local preview data has been imported remotely by the developer.
2. Import source's historical prices may be stale or missing for some stocks.
   Some views need hundreds of valid rows; quality filtering remains enforced.
3. Some source archives may contain zero fundamentals or news articles.
   No fake statements, prices, quotes, FinBERT analyses or ranking scores
   are introduced.
4. Quote fallback returns the latest stored price, **not** a current quote.
   Date/source and explicit stale status are shown.
5. The benchmark API may still use Yahoo data and hit HTTP 429. Offline
   import itself never calls Yahoo and does not bypass provider restrictions.
6. Original `ai_stock_market` DB and experimental validation reports remain
   untouched.
