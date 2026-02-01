from __future__ import annotations

from django.core.management.base import BaseCommand
from analytics.tasks import capture_course_drop_snapshot


class Command(BaseCommand):
    help = "Manually capture course drop snapshot (baseline/final) for a semester."

    def add_arguments(self, parser):
        parser.add_argument("school", type=str)   # e.g. jhu
        parser.add_argument("year", type=str)     # e.g. 2022
        parser.add_argument("term", type=str)     # e.g. Spring
        parser.add_argument("phase", type=str, choices=["baseline", "final"])

        # Optional: allow a subset by course IDs if your capture function supports it
        parser.add_argument(
            "--course-ids",
            nargs="*",
            type=int,
            default=None,
            help="Optional list of course IDs to snapshot (defaults to all courses in semester).",
        )

    def handle(self, *args, **opts):
        school = opts["school"]
        year = opts["year"]
        term = opts["term"]
        phase = opts["phase"]
        course_ids = opts["course_ids"] or None

        # Your function currently takes (school, year, term, phase) OR
        # (school, year, term, phase, course_ids). Use whichever you implemented.
        try:
            if course_ids is None:
                capture_course_drop_snapshot(school, year, term, phase)
            else:
                capture_course_drop_snapshot(school, year, term, phase, course_ids)
        except TypeError:
            # fallback if signature is the 4-arg version
            capture_course_drop_snapshot(school, year, term, phase)

        self.stdout.write(self.style.SUCCESS(f"Captured {phase} snapshot for {school} {term} {year}."))
