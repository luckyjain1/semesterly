# Copyright (C) 2017 Semester.ly Technologies, LLC
#
# Semester.ly is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Semester.ly is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

from django.db import models
from django.contrib.auth.models import User
from student.models import Student

class CourseDropStats(models.Model):
    course   = models.ForeignKey("timetable.Course", on_delete=models.CASCADE)
    semester = models.ForeignKey("timetable.Semester", on_delete=models.CASCADE)

    baseline_total_enrolment = models.IntegerField(null=True, blank=True)
    final_total_enrolment    = models.IntegerField(null=True, blank=True)

    baseline_captured_at = models.DateTimeField(null=True, blank=True)
    final_captured_at    = models.DateTimeField(null=True, blank=True)

    drop_rate = models.FloatField(null=True, blank=True)  # cached convenience

