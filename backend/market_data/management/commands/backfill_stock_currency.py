import re

import yfinance as yf
from django.core.management.base import BaseCommand
from django.db.models import Q

from stocks.models import Stock


class Command(BaseCommand):
    help = (
        "Backfill missing stock currencies using Yahoo Finance metadata."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report verified currencies without changing the database.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Process at most this many stocks.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        dry_run = options["dry_run"]

        if limit is not None and limit <= 0:
            self.stderr.write(
                self.style.ERROR("--limit must be greater than zero.")
            )
            return

        stocks = Stock.objects.filter(
            Q(currency__isnull=True) | Q(currency="")
        ).order_by("symbol")

        if limit is not None:
            stocks = stocks[:limit]

        stocks = list(stocks)

        if not stocks:
            self.stdout.write(
                self.style.SUCCESS("No stocks with missing currency found.")
            )
            return

        updated = 0
        missing = 0
        errors = 0

        self.stdout.write(
            f"Checking currency metadata for {len(stocks)} stocks"
            + (" (dry run)." if dry_run else ".")
        )

        for stock in stocks:
            try:
                info = yf.Ticker(stock.symbol).info
                raw_currency = (
                    info.get("currency")
                    if isinstance(info, dict)
                    else None
                )

                if not isinstance(raw_currency, str):
                    missing += 1
                    self.stdout.write(
                        f"{stock.symbol}: currency unavailable."
                    )
                    continue

                currency = raw_currency.strip().upper()

                if not re.fullmatch(r"[A-Z]{3}", currency):
                    missing += 1
                    self.stdout.write(
                        f"{stock.symbol}: invalid currency metadata."
                    )
                    continue

                if dry_run:
                    self.stdout.write(
                        f"{stock.symbol}: would set currency to {currency}."
                    )
                else:
                    # Update only if currency is still missing.
                    changed = Stock.objects.filter(
                        pk=stock.pk
                    ).filter(
                        Q(currency__isnull=True) | Q(currency="")
                    ).update(currency=currency)

                    if not changed:
                        self.stdout.write(
                            f"{stock.symbol}: skipped; currency was "
                            "populated by another process."
                        )
                        continue

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"{stock.symbol}: currency set to {currency}."
                        )
                    )

                updated += 1

            except Exception as exc:
                errors += 1
                self.stderr.write(
                    self.style.WARNING(
                        f"{stock.symbol}: metadata lookup failed "
                        f"({type(exc).__name__}: {exc})."
                    )
                )

        action = "would be updated" if dry_run else "updated"
        self.stdout.write(
            f"\nFinished. {updated} {action}; "
            f"{missing} unavailable or invalid; {errors} lookup errors."
        )

        if dry_run:
            self.stdout.write(
                "Dry run only: the database was not changed."
            )
