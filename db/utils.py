import logging
from typing import Any, Dict, List

from db.models import Exam, Report

LOGGER = logging.getLogger(__name__)


def load_fixtures(fixtures: Dict[str, List[Dict[str, Any]]]) -> None:
    '''
    Creates or updates Report and Exam records based on the loaded fixtures
    '''

    for report_dict in fixtures['reports']:
        LOGGER.debug(report_dict)
        try:
            report, report_created = Report.objects.update_or_create(**report_dict)
            if report_created:
                LOGGER.info(f'A new Report object was created: {report}')
        except Exception as e:
            LOGGER.error(e)

    for exam_dict in fixtures['exams']:
        LOGGER.debug(exam_dict)
        try:
            exam, exam_created = Exam.objects.update_or_create(
                name=exam_dict['name'],
                report=Report.objects.get(id=exam_dict['report_id']),
                sa_code=exam_dict['sa_code'],
                course_id=exam_dict['course_id'],
                assignment_id=exam_dict['assignment_id']
            )
            if exam_created:
                LOGGER.info(f'A new Exam object was created: {exam}')
        except Exception as e:
            LOGGER.error(e)

    return None
