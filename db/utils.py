# standard libraries
import logging
from typing import Any, Dict, List

# third-party libraries
from django.core.exceptions import ObjectDoesNotExist

# local libraries
from db.models import Exam, Report

LOGGER = logging.getLogger(__name__)


def load_fixtures(fixtures: Dict[str, List[Dict[str, Any]]]) -> None:
    '''
    Creates or updates Report and Exam records based on the loaded fixtures
    '''

    for report_dict in fixtures['reports']:
        LOGGER.debug(report_dict)

        report_queryset = Report.objects.filter(id=report_dict['id'])
        if report_queryset.exists():
            report_queryset.update(**report_dict)  # automatically saves
            LOGGER.info(f'Report object with id {report_dict["id"]} was updated: {report_queryset[0]}')
        else:
            report = Report.objects.create(**report_dict)  # automatically saves
            LOGGER.info(f'A new Report object was created: {report}')

    for exam_dict in fixtures['exams']:
        LOGGER.debug(exam_dict)

        try:
            rel_report = Report.objects.get(id=exam_dict['report_id'])
        except ObjectDoesNotExist:
            rel_report = None
            LOGGER.error(
                'Related Report object was not found. ' +
                'Verify Exam fixtures use IDs of preexisting or to-be-created Reports.'
            )

        exam_dict['report'] = rel_report
        exam_dict.pop('report_id')
        LOGGER.debug(exam_dict)

        exam_queryset = Exam.objects.filter(sa_code=exam_dict['sa_code'])
        if exam_queryset.exists():
            exam_queryset.update(**exam_dict)  # automatically saves
            LOGGER.info(f'Exam object with sa_code {exam_dict["sa_code"]} was updated: {exam_queryset[0]}')
        else:
            exam = Exam.objects.create(**exam_dict)  # automatically saves
            LOGGER.info(f'A new Exam object was created: {exam}')

    return None
