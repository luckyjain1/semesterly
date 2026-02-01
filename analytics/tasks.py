# analytics/tasks.py
from celery import shared_task
from django.db import models
from django.utils import timezone
from timetable.models import Course, Section, Semester
from analytics.dropstats_models import CourseDropStats
from analytics.models import CourseDropRateAggregate

def _sum_enrolment_for(course, semester):
    return (Section.objects
            .filter(course=course, semester=semester)
            .aggregate(total=models.Sum("enrolment"))["total"] or 0)

@shared_task
def capture_course_drop_snapshot(school, year, term, phase, course_ids=None):

    """
    Capture a snapshot ('baseline' or 'final') for ALL courses in (school, term, year).
    Idempotent: won't overwrite unless you later add a force flag.
    """
    sem = Semester.objects.get(name=term, year=year)
    now = timezone.now()

    qs = (Course.objects
      .filter(school=school, section__semester=sem)
      .distinct())

    if course_ids:
        qs = qs.filter(id__in=course_ids)


    for c in qs:
        stats, _ = CourseDropStats.objects.get_or_create(course=c, semester=sem)
        if phase == "baseline":
            if stats.baseline_captured_at:
                continue
            stats.baseline_total_enrolment = _sum_enrolment_for(c, sem)
            stats.baseline_captured_at = now
        elif phase == "final":
            if stats.final_captured_at:
                continue

            stats.final_total_enrolment = _sum_enrolment_for(c, sem)

            b = stats.baseline_total_enrolment or 0
            f = stats.final_total_enrolment or 0
            current = ((b - f) / b) if b else None

            stats.drop_rate = current
            stats.final_captured_at = now
            stats.save()

            # ---- Update aggregate (current weighted more than past) ----
            # Choose how much to weight the new semester vs historical.
            # Example: alpha=0.70 means this semester counts 70%, historical counts 30%.
            alpha = 0.70

            if current is not None:
                agg, _ = CourseDropRateAggregate.objects.get_or_create(course=c)

                if agg.historical_drop_rate is None or agg.semesters_count == 0:
                    # past empty -> initialize to current
                    agg.historical_drop_rate = float(current)
                    agg.semesters_count = 1
                else:
                    # exponential smoothing / weighted update
                    agg.historical_drop_rate = (alpha * float(current)) + ((1 - alpha) * float(agg.historical_drop_rate))
                    agg.semesters_count = agg.semesters_count + 1

                agg.save()

            continue  # because we already saved stats above

        else:
            raise ValueError("phase must be 'baseline' or 'final'")
        stats.save()
