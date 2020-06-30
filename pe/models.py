# standard libaries
import logging
from datetime import datetime
from typing import Dict, Union

# third-party libraries
from django.db import models


LOGGER = logging.getLogger(__name__)


class Report(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name='Report ID')
    name = models.CharField(max_length=255, verbose_name='Report Name', unique=True)
    contact = models.CharField(max_length=255, verbose_name='Report Contact Email')

    def __str__(self):
        return (f'(id={self.id}, name={self.name}, contact={self.contact})')


class Exam(models.Model):
    id = models.AutoField(primary_key=True, verbose_name='Exam ID')
    sa_code = models.CharField(max_length=5, verbose_name='Exam SA Code', unique=True)
    name = models.CharField(max_length=255, verbose_name='Exam Name', unique=True)
    report = models.ForeignKey(to='Report', related_name='exams', null=True, on_delete=models.SET_NULL)
    course_id = models.IntegerField(verbose_name='Canvas Course ID for Exam')
    assignment_id = models.IntegerField(verbose_name='Canvas Assignment ID for Exam', unique=True)
    default_time_filter = models.DateTimeField(verbose_name='Earliest Date & Time for Submission Search')

    def __str__(self):
        return (
            f'(id={self.id}, sa_code={self.sa_code}, name={self.name}, report={self.report}, ' +
            f'course_id={self.course_id}, assignment_id={self.assignment_id}, ' +
            f'default_time_filter={self.default_time_filter})'
        )

    def get_last_sub_graded_datetime(self) -> Union[datetime, None]:
        """
        Return latest graded_timestamp value for an exam's submissions, or None.

        :return: Either a datetime object or null.
        :rtype: datetime.datetime or None
        """
        last_graded_dt = None
        sub_ordered_queryset = self.submissions.order_by('-graded_timestamp')
        if sub_ordered_queryset.exists():
            last_graded_dt = sub_ordered_queryset.first().graded_timestamp
        LOGGER.debug(last_graded_dt)
        return last_graded_dt


class Submission(models.Model):
    id = models.AutoField(primary_key=True, verbose_name='Submission ID')
    submission_id = models.IntegerField(verbose_name='Canvas Submission ID', unique=True)
    exam = models.ForeignKey(to='Exam', related_name='submissions', on_delete=models.CASCADE)
    student_uniqname = models.CharField(max_length=255, verbose_name='Student Uniqname')
    submitted_timestamp = models.DateTimeField(verbose_name='Submitted At Date & Time')
    graded_timestamp = models.DateTimeField(verbose_name='Graded At Date & Time')
    score = models.FloatField(verbose_name='Submission Score')
    transmitted = models.BooleanField(verbose_name='Transmitted')
    transmitted_timestamp = models.DateTimeField(verbose_name='Transmitted At Date & Time', null=True, default=None)

    def __str__(self):
        return (
            f'(id={self.id}, submission_id={self.submission_id}, exam={self.exam}, ' +
            f'student_uniqname={self.student_uniqname}, submitted_timestamp={self.submitted_timestamp}, ' +
            f'graded_timestamp={self.graded_timestamp}, score={self.score}, transmitted={self.transmitted}, ' +
            f'transmitted_timestamp={self.transmitted_timestamp})'
        )

    def prepare_score(self) -> Dict[str, str]:
        """
        Return condensed version of the submission needed by M-Pathways.

        :return: Dictionary with strings for keys and values.
        :rtype: dictionary
        """
        score_dict: Dict[str, str] = {
            'ID': self.student_uniqname,
            'Form': self.exam.sa_code,
            'GradePoints': str(self.score)
        }
        return score_dict
