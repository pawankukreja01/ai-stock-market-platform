from datetime import datetime, timezone as dt_timezone
from urllib.parse import urlsplit

import yfinance as yf

from django.core.management.base import (
    BaseCommand,
    CommandError,
)
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from stocks.models import Stock
from market_data.models import NewsArticle


# ============================================================
# NORMALISE PROVIDER RESPONSES
# ============================================================

def normalise_news_response(response):
    """
    Convert supported Yahoo Finance response structures
    into a list of article dictionaries.
    """
    if isinstance(response, dict):
        if isinstance(response.get("news"), list):
            response = response["news"]
        elif isinstance(response.get("results"), list):
            response = response["results"]
        else:
            response = [response]

    if not isinstance(response, list):
        return []

    return [
        item
        for item in response
        if isinstance(item, dict)
    ]


def get_article_content(item):
    """
    Newer responses may put article fields inside 'content'.
    Older responses may return the fields at the top level.
    """
    content = item.get("content")

    if isinstance(content, dict):
        return content

    return item


# ============================================================
# FETCH NEWS WITH FALLBACKS
# ============================================================

def fetch_news(symbol, limit):
    """
    Try Yahoo Finance Search first, then Ticker.get_news(),
    then the legacy Ticker.news property.

    Returns:
        articles: list of article dictionaries
        diagnostics: list of method results/errors
    """
    diagnostics = []

    # Method 1: Yahoo Finance Search
    try:
        search = yf.Search(
            symbol,
            max_results=5,
            news_count=limit,
            raise_errors=True,
        )

        articles = normalise_news_response(
            search.news
        )

        diagnostics.append(
            f"yf.Search returned {len(articles)} article(s)."
        )

        if articles:
            return articles[:limit], diagnostics

    except Exception as exc:
        diagnostics.append(
            f"yf.Search failed: {type(exc).__name__}: {exc}"
        )

    # Create the ticker once for the fallback methods.
    ticker = yf.Ticker(symbol)

    # Method 2: Ticker.get_news()
    get_news = getattr(
        ticker,
        "get_news",
        None,
    )

    if callable(get_news):
        try:
            response = get_news(
                count=limit,
                tab="news",
            )

            articles = normalise_news_response(
                response
            )

            diagnostics.append(
                "Ticker.get_news returned "
                f"{len(articles)} article(s)."
            )

            if articles:
                return articles[:limit], diagnostics

        except Exception as exc:
            diagnostics.append(
                "Ticker.get_news failed: "
                f"{type(exc).__name__}: {exc}"
            )
    else:
        diagnostics.append(
            "Ticker.get_news is unavailable in this "
            "installed yfinance version."
        )

    # Method 3: Legacy ticker.news property
    try:
        response = ticker.news

        articles = normalise_news_response(
            response
        )

        diagnostics.append(
            "Ticker.news returned "
            f"{len(articles)} article(s)."
        )

        if articles:
            return articles[:limit], diagnostics

    except Exception as exc:
        diagnostics.append(
            "Ticker.news failed: "
            f"{type(exc).__name__}: {exc}"
        )

    return [], diagnostics


# ============================================================
# ARTICLE FIELD EXTRACTORS
# ============================================================

def get_article_url(item, content):
    """
    Extract the article URL from Yahoo Finance metadata.
    """
    for key in (
        "canonicalUrl",
        "clickThroughUrl",
    ):
        value = (
            content.get(key)
            or item.get(key)
        )

        if isinstance(value, dict):
            url = value.get("url")

            if url:
                return str(url).strip()

        elif isinstance(value, str) and value.strip():
            return value.strip()

    for key in (
        "link",
        "url",
        "previewUrl",
    ):
        value = (
            content.get(key)
            or item.get(key)
        )

        if isinstance(value, str) and value.strip():
            return value.strip()

    return ""


def is_valid_article_url(url):
    """
    Accept only HTTP/HTTPS article URLs.
    """
    if not url or len(url) > 2048:
        return False

    try:
        parsed = urlsplit(url)

        return (
            parsed.scheme in ("http", "https")
            and bool(parsed.netloc)
        )

    except ValueError:
        return False


def get_publication_date(item, content):
    """
    Parse ISO datetime strings and Unix timestamps.
    Return a timezone-aware datetime or None.
    """
    raw_date = (
        content.get("pubDate")
        or content.get("publishedAt")
        or content.get("providerPublishTime")
        or item.get("providerPublishTime")
        or item.get("pubDate")
    )

    if raw_date is None:
        return None

    if isinstance(raw_date, (int, float)):
        try:
            return datetime.fromtimestamp(
                raw_date,
                tz=dt_timezone.utc,
            )

        except (
            ValueError,
            OverflowError,
            OSError,
        ):
            return None

    if isinstance(raw_date, str):
        parsed = parse_datetime(
            raw_date
        )

        if parsed is None:
            return None

        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(
                parsed,
                timezone.get_current_timezone(),
            )

        return parsed

    return None


def get_publisher(item, content):
    """
    Extract the publisher from nested or flat metadata.
    """
    provider = (
        content.get("provider")
        or item.get("provider")
        or {}
    )

    if isinstance(provider, dict):
        publisher = (
            provider.get("displayName")
            or provider.get("name")
            or content.get("publisher")
            or item.get("publisher")
            or ""
        )
    else:
        publisher = provider

    return str(publisher).strip()[:255]


def get_thumbnail(item, content):
    """
    Extract a thumbnail URL when one is available.
    """
    thumbnail = (
        content.get("thumbnail")
        or item.get("thumbnail")
        or {}
    )

    if not isinstance(thumbnail, dict):
        return ""

    url = (
        thumbnail.get("originalUrl")
        or thumbnail.get("url")
    )

    if url and is_valid_article_url(str(url)):
        return str(url).strip()[:2048]

    resolutions = thumbnail.get(
        "resolutions",
        [],
    )

    if isinstance(resolutions, list):
        for resolution in resolutions:
            if not isinstance(resolution, dict):
                continue

            url = (
                resolution.get("url")
                or resolution.get("originalUrl")
            )

            if url and is_valid_article_url(str(url)):
                return str(url).strip()[:2048]

    return ""


def get_article_title(item, content):
    title = (
        content.get("title")
        or item.get("title")
        or ""
    )

    return str(title).strip()[:500]


def get_article_summary(item, content):
    summary = (
        content.get("summary")
        or content.get("description")
        or content.get("shortSummary")
        or item.get("summary")
        or item.get("description")
        or ""
    )

    if not isinstance(summary, str):
        return ""

    return summary.strip()


def get_source_id(item, content):
    source_id = (
        item.get("id")
        or content.get("id")
        or item.get("uuid")
        or content.get("uuid")
        or ""
    )

    return str(source_id).strip()[:255]


# ============================================================
# DJANGO MANAGEMENT COMMAND
# ============================================================

class Command(BaseCommand):
    help = (
        "Fetch recent Yahoo Finance news and store "
        "articles for a stock."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--symbol",
            type=str,
            required=True,
            help="Stock symbol, e.g. AAPL",
        )

        parser.add_argument(
            "--limit",
            type=int,
            default=50,
            help="Maximum number of articles to process.",
        )

    def handle(self, *args, **options):
        symbol = (
            options["symbol"]
            .strip()
            .upper()
        )

        limit = options["limit"]

        if not symbol:
            raise CommandError(
                "A stock symbol is required."
            )

        if not 1 <= limit <= 200:
            raise CommandError(
                "--limit must be between 1 and 200."
            )

        try:
            stock = Stock.objects.get(
                symbol=symbol,
                is_active=True,
            )

        except Stock.DoesNotExist as exc:
            raise CommandError(
                f"Active stock '{symbol}' was not found "
                "in the Stock table. Add the stock first."
            ) from exc

        self.stdout.write(
            f"Fetching news for {symbol}..."
        )

        articles, diagnostics = fetch_news(
            symbol,
            limit,
        )

        self.stdout.write(
            "Provider diagnostics:"
        )

        for diagnostic in diagnostics:
            self.stdout.write(
                f"  - {diagnostic}"
            )

        if not articles:
            self.stdout.write(
                self.style.WARNING(
                    f"No news articles were returned for "
                    f"{symbol}. This does not prove that "
                    "no relevant news exists."
                )
            )

            self.stdout.write(
                "Check the diagnostics above. If all "
                "provider methods return zero results or "
                "fail, the data provider may be unavailable "
                "or restricting the request."
            )

            return

        created_count = 0
        updated_count = 0
        skipped_count = 0

        seen_urls = set()

        # ----------------------------------------------------
        # Process each article
        # ----------------------------------------------------

        for item in articles[:limit]:
            content = get_article_content(
                item
            )

            title = get_article_title(
                item,
                content,
            )

            url = get_article_url(
                item,
                content,
            )

            if not title or not is_valid_article_url(url):
                skipped_count += 1

                self.stdout.write(
                    self.style.WARNING(
                        "Skipped an article without a valid "
                        "title or HTTP/HTTPS URL."
                    )
                )

                continue

            # Prevent the same URL being processed twice
            # when duplicate articles appear in one response.
            if url in seen_urls:
                skipped_count += 1
                continue

            seen_urls.add(url)

            summary = get_article_summary(
                item,
                content,
            )

            source_id = get_source_id(
                item,
                content,
            )

            publisher = get_publisher(
                item,
                content,
            )

            published_at = get_publication_date(
                item,
                content,
            )

            thumbnail_url = get_thumbnail(
                item,
                content,
            )

            defaults = {
                "source_name": "Yahoo Finance",
                "source_id": source_id,
                "title": title,
                "summary": summary,
                "publisher": publisher,
                "published_at": published_at,
                "thumbnail_url": thumbnail_url,
            }

            # -----------------------------------------------
            # Upsert by stock + URL
            # -----------------------------------------------

            try:
                _, created = (
                    NewsArticle.objects.update_or_create(
                        stock=stock,
                        url=url,
                        defaults=defaults,
                    )
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            except Exception as exc:
                skipped_count += 1

                self.stderr.write(
                    self.style.WARNING(
                        f"Could not store article "
                        f"'{title[:80]}': "
                        f"{type(exc).__name__}: {exc}"
                    )
                )

        # ----------------------------------------------------
        # Summary
        # ----------------------------------------------------

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                f"News ingestion finished for {symbol}."
            )
        )

        self.stdout.write(
            f"Created: {created_count}"
        )

        self.stdout.write(
            f"Updated: {updated_count}"
        )

        self.stdout.write(
            f"Skipped: {skipped_count}"
        )

        total_saved = NewsArticle.objects.filter(
            stock=stock
        ).count()

        self.stdout.write(
            f"Total stored articles for {symbol}: "
            f"{total_saved}"
        )