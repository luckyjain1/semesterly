from django.core.management.base import BaseCommand
from analytics.dropstats_scheduler import run_drop_snapshot_scheduler


class Command(BaseCommand):
    help = "Run drop-rate snapshot scheduler (baseline=+7 days, final=+21 days from start)."

    def add_arguments(self, parser):
        parser.add_argument("--baseline-days", type=int, default=7)
        parser.add_argument("--final-days", type=int, default=21)

    def handle(self, *args, **options):
        run_drop_snapshot_scheduler(
            baseline_offset_days=options["baseline_days"],
            final_offset_days=options["final_days"],
        )
        self.stdout.write(self.style.SUCCESS("Drop snapshot scheduler ran."))
