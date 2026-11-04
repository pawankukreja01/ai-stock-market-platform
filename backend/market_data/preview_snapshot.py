"""Whitelisted, offline snapshot of historical market data for isolated preview.

Only market-data models are serialized. There are no users, portfolios, sessions,
tokens, alerts, personal settings or external provider requests.
"""
import gzip
import json
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import CommandError
from django.db import connection, transaction

from market_data.models import HistoricalPrice, Fundamental, NewsArticle
from stocks.models import Stock

SOURCE_DB = "marketpulse_restored_test"
DESTINATION_DB = "marketpulse_preview"
SCHEMA = "marketpulse-market-snapshot-v1"
PRICE_FIELDS = (
    "date", "open_price", "high_price", "low_price", "close_price",
    "adjusted_close", "volume", "provider_currency", "storage_currency",
    "is_ohlc_valid", "is_volume_valid", "quality_flags",
)
STOCK_FIELDS = ("symbol", "company_name", "exchange", "currency",
                "sector", "industry", "is_active")
FUNDAMENTAL_FIELDS = (
    "period_end", "period_type", "revenue", "gross_profit", "operating_income",
    "net_income", "eps", "free_cash_flow", "roe", "roa", "gross_margin",
    "operating_margin", "profit_margin", "debt_to_equity", "current_ratio",
    "pe_ratio", "forward_pe", "peg_ratio", "price_to_sales", "price_to_book",
    "dividend_per_share", "dividend_yield",
)
NEWS_FIELDS = (
    "source_name", "source_id", "title", "summary", "url", "publisher",
    "published_at", "thumbnail_url", "sentiment_label", "sentiment_score",
    "sentiment_positive_prob", "sentiment_neutral_prob", "sentiment_negative_prob",
    "sentiment_model", "sentiment_analyzed_at",
)
FIELDS = {"stock": STOCK_FIELDS, "price": PRICE_FIELDS,
          "fundamental": FUNDAMENTAL_FIELDS, "news": NEWS_FIELDS}
MAX_ITEMS = {"stock": 10000, "price": 1500000,
             "fundamental": 200000, "news": 100000}


def assert_database(name):
    from os import environ
    configured = connection.settings_dict.get("NAME")
    if environ.get("DB_NAME") != name or configured != name:
        raise CommandError(
            f"Refusing market-data operation. Both DB_NAME and the Django "
            f"connection must explicitly select {name}; currently "
            f"DB_NAME={environ.get('DB_NAME')!r}, connection={configured!r}."
        )


def json_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def write_record(stream, kind, obj, *, symbol):
    fields = {name: json_value(getattr(obj, name)) for name in FIELDS[kind]}
    stream.write(json.dumps({"type": kind, "symbol": symbol, "fields": fields},
                            allow_nan=False, separators=(",", ":")) + "\n")


def export_snapshot(destination):
    assert_database(SOURCE_DB)
    path = Path(destination).expanduser().resolve()
    if path.exists():
        raise CommandError("Refusing to overwrite an existing snapshot.")
    path.parent.mkdir(parents=True, exist_ok=True)
    counts = {key: 0 for key in FIELDS}
    with gzip.open(path, "xt", encoding="utf-8", newline="\n") as output:
        output.write(json.dumps({
            "schema": SCHEMA, "source": SOURCE_DB,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "note": "Stored historical observations, not real-time quotes.",
        }) + "\n")
        for stock in Stock.objects.order_by("symbol").iterator(chunk_size=1000):
            write_record(output, "stock", stock, symbol=stock.symbol)
            counts["stock"] += 1
        for kind, model in (
            ("price", HistoricalPrice),
            ("fundamental", Fundamental),
            ("news", NewsArticle),
        ):
            for obj in model.objects.select_related("stock").order_by("pk").iterator(chunk_size=1000):
                write_record(output, kind, obj, symbol=obj.stock.symbol)
                counts[kind] += 1
    return path, counts


def _valid_record(item):
    if not isinstance(item, dict):
        raise ValueError("Snapshot record must be an object.")
    kind, symbol, fields = item.get("type"), item.get("symbol"), item.get("fields")
    if kind not in FIELDS:
        raise ValueError("Disallowed record type (only whitelisted market data is accepted).")
    if not isinstance(symbol, str) or not 1 <= len(symbol) <= 20 or symbol != symbol.strip().upper():
        raise ValueError("Invalid stock symbol.")
    if not isinstance(fields, dict) or set(fields) != set(FIELDS[kind]):
        raise ValueError("Unexpected or missing market-data fields.")
    if kind == "stock" and fields["symbol"] != symbol:
        raise ValueError("Stock identity mismatch.")
    if kind == "price":
        parsed = date.fromisoformat(fields["date"])
        if parsed > date.today():
            raise ValueError("Future stock price date in snapshot.")
        try:
            if Decimal(str(fields["close_price"])) <= 0:
                raise ValueError("Invalid stored closing price.")
        except InvalidOperation as exc:
            raise ValueError("Invalid stored closing price.") from exc
        if not isinstance(fields["quality_flags"], list):
            raise ValueError("Invalid price-quality flags.")
    if kind == "fundamental":
        if fields["period_end"]:
            date.fromisoformat(fields["period_end"])
        if fields["period_type"] not in ("annual", "quarterly"):
            raise ValueError("Invalid fundamental period.")
    if kind == "news":
        if not isinstance(fields["url"], str) or not fields["url"].startswith(("https://", "http://")):
            raise ValueError("News URL is missing or invalid.")
    return kind, symbol, fields


def iter_snapshot(path):
    with gzip.open(path, "rt", encoding="utf-8") as reader:
        header_line = reader.readline()
        if not header_line:
            raise ValueError("Empty market snapshot.")
        header = json.loads(header_line)
        if not isinstance(header, dict) or header.get("schema") != SCHEMA or header.get("source") != SOURCE_DB:
            raise ValueError("Unexpected snapshot origin/schema; refusing import.")
        yield "header", "", header
        for line_number, line in enumerate(reader, start=2):
            if len(line) > 1024 * 1024:
                raise ValueError(f"Oversized snapshot row at line {line_number}.")
            try:
                yield _valid_record(json.loads(line))
            except (TypeError, KeyError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError(f"Invalid snapshot row {line_number}: {exc}") from exc


def preflight_snapshot(path):
    counts = {key: 0 for key in FIELDS}
    stock_symbols = set()
    for kind, symbol, fields in iter_snapshot(path):
        if kind == "header":
            continue
        counts[kind] += 1
        if counts[kind] > MAX_ITEMS[kind]:
            raise ValueError(f"Snapshot limit exceeded for {kind}.")
        if kind == "stock":
            if symbol in stock_symbols:
                raise ValueError("Duplicate stock in source snapshot.")
            stock_symbols.add(symbol)
        elif symbol not in stock_symbols:
            raise ValueError(f"Unknown stock {symbol}; market rows must follow stock records.")
    if not stock_symbols or counts["price"] == 0:
        raise ValueError("Snapshot has no stock catalogue or price observations.")
    return counts


def import_snapshot(path, *, dry_run=False):
    assert_database(DESTINATION_DB)
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise CommandError("Market snapshot file does not exist.")
    try:
        counts = preflight_snapshot(path)
    except (ValueError, OSError, EOFError) as exc:
        raise CommandError(f"Snapshot validation failed: {exc}") from exc
    if dry_run:
        return counts, None
    created = {key: 0 for key in FIELDS}
    with transaction.atomic():
        # Never delete existing preview data, or overwrite a newer observation.
        symbols = {}
        buffer = []
        current_kind = None

        def flush():
            nonlocal buffer, current_kind
            if not buffer:
                return
            model = {"price": HistoricalPrice,
                     "fundamental": Fundamental, "news": NewsArticle}[current_kind]
            before = model.objects.count()
            model.objects.bulk_create(buffer, batch_size=500, ignore_conflicts=True)
            created[current_kind] += model.objects.count() - before
            buffer = []

        for kind, symbol, fields in iter_snapshot(path):
            if kind == "header":
                continue
            if kind == "stock":
                obj, made = Stock.objects.get_or_create(symbol=symbol, defaults=fields)
                symbols[symbol] = obj.pk
                created["stock"] += int(made)
                continue
            if current_kind != kind:
                flush()
                current_kind = kind
            data = dict(fields, stock_id=symbols[symbol])
            buffer.append({"price": HistoricalPrice,
                           "fundamental": Fundamental, "news": NewsArticle}[kind](**data))
            if len(buffer) >= 1000:
                flush()
        flush()
    return counts, created
