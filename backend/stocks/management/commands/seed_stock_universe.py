from django.core.management.base import BaseCommand
from django.db import transaction

from stocks.catalog import STOCK_CATALOG
from stocks.models import Stock


class Command(BaseCommand):
    help = (
        "Add the curated US and UK stock starter catalog. "
        "Existing stock records are preserved; this command does not download market data."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview records that would be added without writing to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        created = 0
        existing = 0

        with transaction.atomic():
            for symbol, company_name, exchange, sector, industry in STOCK_CATALOG:
                defaults = {
                    "company_name": company_name,
                    "exchange": exchange,
                    "sector": sector,
                    "industry": industry,
                    "is_active": True,
                }

                if dry_run:
                    if Stock.objects.filter(symbol=symbol).exists():
                        existing += 1
                    else:
                        created += 1
                        self.stdout.write(f"Would add {symbol} — {company_name}")
                    continue

                _, was_created = Stock.objects.get_or_create(
                    symbol=symbol,
                    defaults=defaults,
                )
                if was_created:
                    created += 1
                else:
                    existing += 1

            if dry_run:
                transaction.set_rollback(True)

        action = "would be added" if dry_run else "added"
        self.stdout.write(
            self.style.SUCCESS(
                f"Stock catalog complete: {created} {action}; "
                f"{existing} already existed. "
                f"{'Dry run only; database unchanged.' if dry_run else 'No market data downloaded.'}"
            )
        )
