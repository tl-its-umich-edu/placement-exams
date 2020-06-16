from django.db import models


class Report(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name='Report ID')
    name = models.CharField(max_length=255, verbose_name='Report Name', unique=True)
    contact = models.CharField(max_length=100, verbose_name='Report Contact Email')

    def __str__(self):
        return (f'(id={self.id}, name={self.name}, contact={self.contact})')


class Exam(models.Model):
    id = models.AutoField(primary_key=True, verbose_name='Exam ID')
    sa_code = models.CharField(max_length=5, verbose_name='Exam SA Code', unique=True)
    name = models.CharField(max_length=255, verbose_name='Exam Name', unique=True)
    report = models.ForeignKey(to='Report', related_name='exams', null=True, on_delete=models.SET_NULL)
    course_id = models.IntegerField(verbose_name='Canvas Course ID for Exam')
    assignment_id = models.IntegerField(verbose_name='Canvas Assignment ID for Exam', unique=True)

    def __str__(self):
        return (
            f'(id={self.id}, sa_code={self.sa_code}, name={self.name}, report={self.report}, ' +
            f'course_id={self.course_id}, assignment_id={self.assignment_id})'
        )


class Submission(models.Model):
    id = models.AutoField(primary_key=True, verbose_name='Submission ID')
    submission_id = models.IntegerField(verbose_name='Canvas Submission ID', unique=True)
    exam = models.ForeignKey(to='Exam', related_name='submissions', on_delete=models.CASCADE)
    student_uniqname = models.CharField(max_length=50, verbose_name='Student Uniqname')
    submitted_timestamp = models.DateTimeField(verbose_name='Submitted At Date & Time')
    score = models.FloatField(verbose_name='Submission Score')
    transmitted = models.BooleanField(verbose_name='Transmitted')
    transmitted_timestamp = models.DateTimeField(verbose_name='Transmitted At Date & Time')

    def __str__(self):
        return (
            f'(id={self.id}, submission_id={self.submission_id}, exam={self.exam}, ' +
            f'student_uniqname={self.student_uniqname}, submitted_timestamp={self.submitted_timestamp}, ' +
            f'score={self.score}, transmitted={self.transmitted}, ' +
            f'transmitted_timestamp={self.transmitted_timestamp})'
        )
