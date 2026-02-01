from __future__ import annotations

from django.core.management.base import BaseCommand
from analytics.tasks import capture_course_drop_snapshot
from timetable.models import Semester, Offering
from analytics.models import CourseDropStats

from django.db.models import Value
from django.utils import timezone
from django.db.models import DateField, Func

class ToDate(Func):
    function = "to_date"
    output_field = DateField()

def get_ineligible_course_ids(school: str, sem, phase: str, today):
    if phase != "baseline":
        return []
    cutoff = today

    return list(
        Offering.objects.filter(
            section__semester=sem,
            section__course__school__iexact=school,
        )
        .exclude(date_start__isnull=True)
        .annotate(start_dt=ToDate("date_start", Value("MM-DD-YYYY")))
        .filter(start_dt__gt=cutoff)
        .values_list("section__course_id", flat=True)
        .distinct()
    )

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
            "--clear",
            action="store_true",
            help="Delete existing snapshot rows for this semester/phase (and course subset if provided) before capturing.",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="With --clear: show how many snapshot rows would be deleted, without deleting.",
        )

    def handle(self, *args, **opts):
        school = opts["school"]
        year = opts["year"]
        term = opts["term"]
        phase = opts["phase"]
        clear = opts["clear"]
        dry_run = opts["dry_run"]

        today = timezone.localdate()
        sem = Semester.objects.get(year=year, name=term)

        if clear:
            qs = CourseDropStats.objects.filter(
                semester=sem,
                course__school__iexact=school,
            )
            count = qs.count()

            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f"[DRY RUN] Would clear {count} CourseDropStats rows for {school} {term} {year} ({phase})."
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
                    f"Cleared {count} rows for {school} {term} {year} ({phase})."
                )
            )
            return
        ineligible_ids = get_ineligible_course_ids(school, sem, phase, today)
        capture_course_drop_snapshot(school, year, term, phase, ineligible_ids)

        self.stdout.write(self.style.SUCCESS(f"Captured {phase} snapshot for {school} {term} {year}."))
