# standard libraries
import logging, os
from smtplib import SMTPException
from typing import Any, Dict, List, Tuple

# third-party libraries
from django.core.mail import send_mail
from django.db.models import QuerySet
from django.forms.models import model_to_dict
from django.template.loader import render_to_string

# local libraries
from pe.models import Report


LOGGER = logging.getLogger(__name__)


class Reporter:
    """
    """

    def __init__(self, report):
        """
        """
        self.report: Report = report
        self.exams_metadata: Dict[Dict[str, Any]] = dict()
        self.context: Dict[str, Any] = dict()
        self.total_successes: int = 0
        self.total_failures: int = 0
        self.total_new: int = 0

    def prepare_context(self) -> None:
        """
        """
        exam_dicts: List[Dict[str, Any]] = []
        for exam in self.report.exams.all():
            exam_dict: Dict[str, Any] = model_to_dict(exam)
            
            success_sub_qs: QuerySet = exam.submissions.filter(
                transmitted=True, transmitted_timestamp__gte=self.exams_metadata[exam.id]['start_time']
            )
            num_successes: int = len(success_sub_qs)

            # ScoresOrchestration tries to send everything that is un-transmitted, so anything left un-transmitted
            # after a run is a failure.
            failure_sub_qs: QuerySet = exam.submissions.filter(transmitted=False)
            num_failures: int = len(failure_sub_qs)

            new_sub_qs: QuerySet = exam.submissions.filter(
                graded_timestamp__gte=self.exams_metadata[exam.id]['datetime_filter']
            )
            num_new: int = len(new_sub_qs)

            exam_dict['summary'] = {
                'success_count': num_successes,
                'failure_count': num_failures,
                'new_count': num_new
            }
            exam_dict['time'] = self.exams_metadata[exam.id]

            sub_values: Tuple[str, ...] = ('submission_id', 'student_uniqname', 'score', 'submitted_timestamp')
            exam_dict['successes'] = list(success_sub_qs.values(*sub_values))
            exam_dict['failures'] = list(failure_sub_qs.values(*sub_values))
            exam_dicts.append(exam_dict)

            self.total_successes += num_successes
            self.total_failures += num_failures
            self.total_new += num_new

        report_dict: Dict[str, Any] = model_to_dict(self.report)
        report_dict['summary'] = {
            'success_count': self.total_successes,
            'failure_count': self.total_failures,
            'new_count': self.total_new
        }

        self.context = {'report': report_dict, 'exams': exam_dicts}
        LOGGER.debug(self.context)
        return None

    def get_subject(self) -> str:
        """
        """
        subject: str = (
            f'Placement Exams - {self.report.name} - ' +
            f'New: {self.total_new}, Success: {self.total_successes}, Failure: {self.total_failures} - ' +
            ', '.join([exam.name for exam in self.report.exams.all()])
        )
        LOGGER.debug(subject)
        return subject

    def send_email(self) -> None:
        """
        """
        plain_text_email: str = render_to_string('email.txt', self.context)
        html_email: str = render_to_string('email.html', self.context)

        try:
            result = send_mail(
                subject=self.get_subject(),
                message=plain_text_email,
                from_email=os.getenv('SMTP_FROM', ''),
                recipient_list=[self.report.contact],
                html_message=html_email
            )
            LOGGER.debug(result)
            LOGGER.info('Successfully sent email')
        except SMTPException as e:
            LOGGER.info(f'Error: unable to send email due to {e}')
