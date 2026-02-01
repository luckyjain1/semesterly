from __future__ import annotations

from django.core.management.base import BaseCommand
from analytics.tasks import capture_course_drop_snapshot
from timetable.models import Semester
from analytics.models import CourseDropStats

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

        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing snapshot rows for this semester/phase (and course subset if provided) before capturing.",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="With --reset: show how many snapshot rows would be deleted, without deleting.",
        )

    def handle(self, *args, **opts):
        school = opts["school"]
        year = opts["year"]
        term = opts["term"]
        phase = opts["phase"]
        course_ids = opts["course_ids"] or None
        reset = opts["reset"]
        dry_run = opts["dry_run"]

        sem = Semester.objects.get(year=year, name=term)

        if reset:
            qs = CourseDropStats.objects.filter(
                semester=sem,
                course__school__iexact=school,
            )
            if course_ids is not None:
                qs = qs.filter(course_id__in=course_ids)

            count = qs.count()

            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f"[DRY RUN] Would reset {count} CourseDropStats rows for {school} {term} {year} ({phase})."
                    )
                )
                return
            
            if phase == "baseline":
                # Clear only baseline fields
                qs.update(
                    baseline_total_enrolment=None,
                    baseline_captured_at=None,
                )
            else:
                # Clear final fields and cached drop_rate
                qs.update(
                    final_total_enrolment=None,
                    final_captured_at=None,
                    drop_rate=None,
                )

            self.stdout.write(
                self.style.WARNING(
                    f"Reset {count} rows for {school} {term} {year} ({phase})."
                )
            )
            return

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
