# analytics/dropstats_scheduler.py

from __future__ import annotations

from datetime import timedelta
from django.utils import timezone

from timetable.models import Semester, Offering
from timetable.school_mappers import SCHOOLS_MAP
from parsing.schools.active import ACTIVE_PARSING_SCHOOLS as ACTIVE_SCHOOLS
from analytics.tasks import capture_course_drop_snapshot


def _course_ids_with_start_date(school: str, sem: Semester, start_day) -> list[int]:
    """
    Return course IDs whose Offering.date_start == start_day formatted as %m-%d-%Y.
    Assumes Offering.date_start strings always match %m-%d-%Y.
    """
    target = start_day.strftime("%m-%d-%Y")
    return list(
        Offering.objects.filter(
            section__semester=sem,
            section__course__school__iexact=school,
            date_start=target,
        )
        .values_list("section__course_id", flat=True)
        .distinct()
    )


def run_drop_snapshot_scheduler(
    baseline_offset_days: int = 7,
    final_offset_days: int = 21,
) -> None:
    """
    Idempotent daily scheduler logic:
      - baseline snapshot for courses with start_date == today - baseline_offset_days
      - final snapshot for courses with start_date == today - final_offset_days

    This function is intentionally NOT a celery task.
    It's pure logic you can call from:
      - celerybeat (recommended if you already run it)
      - a cron job
      - a manual management command
    """
    today = timezone.localdate()
    baseline_start = today - timedelta(days=baseline_offset_days)
    final_start = today - timedelta(days=final_offset_days)

    for school in set(SCHOOLS_MAP) & set(ACTIVE_SCHOOLS):
        active = SCHOOLS_MAP[school].active_semesters  # {year: [terms]}
        for year, terms in active.items():
            for term in terms:
                sem = Semester.objects.filter(name=term, year=year).first()
                if not sem:
                    continue

                baseline_ids = _course_ids_with_start_date(school, sem, baseline_start)
                if baseline_ids:
                    capture_course_drop_snapshot.delay(
                        school, year, term, "baseline", baseline_ids
                    )

                final_ids = _course_ids_with_start_date(school, sem, final_start)
                if final_ids:
                    capture_course_drop_snapshot.delay(
                        school, year, term, "final", final_ids
                    )
