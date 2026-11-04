"""Safely import an offline research archive only into the isolated Docker preview."""
from django.core.management.base import BaseCommand, CommandError
from market_data.preview_snapshot import import_snapshot


class Command(BaseCommand):
    help = "Import previously captured market records ONLY into marketpulse_preview; never other databases."

    def add_arguments(self, parser):
        parser.add_argument("--input", required=True, help="Offline .jsonl.gz archive in the preview container.")
        parser.add_argument("--dry-run", action="store_true", help="Validate complete snapshot without writing.")

    def handle(self, *args, **options):
        path = options["input"]
        if not path.endswith(".jsonl.gz"):
            raise CommandError("Input filename must end in .jsonl.gz.")
        counts, created = import_snapshot(path, dry_run=options["dry_run"])
        self.stdout.write(f"Validated source rows: {counts}")
        if created is None:
            self.stdout.write(self.style.SUCCESS("Dry run complete; no data changed."))
            return
        self.stdout.write(self.style.SUCCESS(f"Preview import complete. New rows: {created}"))
        self.stdout.write("Historical observations are archived, NOT real-time market quotes.")
