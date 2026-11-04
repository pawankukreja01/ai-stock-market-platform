"""Read-only export of stored market observations from restored test database."""
from django.core.management.base import BaseCommand, CommandError
from market_data.preview_snapshot import export_snapshot


class Command(BaseCommand):
    help = "Export only stored market-data records to a gzipped offline snapshot; never users or portfolios."

    def add_arguments(self, parser):
        parser.add_argument("--output", required=True, help="New .jsonl.gz file; never overwritten.")

    def handle(self, *args, **options):
        if not options["output"].endswith(".jsonl.gz"):
            raise CommandError("Output filename must end in .jsonl.gz.")
        path, counts = export_snapshot(options["output"])
        self.stdout.write(self.style.SUCCESS(f"Exported market snapshot to {path}"))
        self.stdout.write(f"Counts: {counts}")
        self.stdout.write("Source was read only. No Yahoo requests. Snapshot contains no accounts, sessions, portfolios or secrets.")
