from typing import List, Dict
import os
from smtplib import SMTP, SMTPException
from email.mime.text import MIMEText
from autologging import logged, traced
from datetime import datetime

from spe_utils.constants import SMPT_DEBUG, SMPT_FROM, SMPT_TO, SMPT_HOST, SMPT_PORT


@traced
@logged
class SPESummaryReport:
    stored_persisted_date: str = None
    next_stored_persisted_date: str = None
    used_query_date: str = None
    start_time: str = None
    end_time: str = None
    elapsed_time: str = None
    full_score_list: List[Dict[str, str]] = []
    sent_score_list: List[Dict[str, str]] = []
    not_sent_scores_list: List[Dict[str, str]] = []
    course_id: str = None

    def get_subject(self):
        return f"({len(self.sent_score_list)}/{len(self.full_score_list)}) Spanish Placement Exam Processing Summary {datetime.now().replace(microsecond=0)}"


    def email_report(self):
        msg = f"""
        Summary of Spanish Placement Exam processing.  
        This report includes the report runtimes, the cutoff times used for querying for new users, and counts of users added and errors.
        The subject line of the corresponding email summarizes the scores added/received as (n/n).
        
        starting time: {self.start_time}
        end time: {self.end_time}
        elapsed time: {self.elapsed_time}

        storedTestLastTakenTime: {self.stored_persisted_date}
        useTestLastTakenTime: {self.used_query_date}
        updatedTestLastTakenTime: {self.next_stored_persisted_date}
        
        course_id: {self.course_id}
        
        user scores added: {len(self.sent_score_list)} failed scores addition: {len(self.not_sent_scores_list)}
         """
        return msg

    def email_msg(self):
        msg: List[str] = [self.email_report()]
        if self.sent_score_list:
            msg.append("Success users List:")
            for item in self.sent_score_list:
                msg.append(f"user: {item['user']}  score: {item['score']}  finished_at: {item['local_submitted_date']}")
            msg.append("\n")
        if self.not_sent_scores_list:
            msg.append("Failed to send users List below, will try in the next run")
            for item in self.not_sent_scores_list:
                msg.append(f"user: {item['user']}  score: {item['score']}  finished_at: {item['local_submitted_date']}")

        return msg


    def send_email(self):
        port: str = os.getenv(SMPT_PORT)
        host: str = os.getenv(SMPT_HOST)
        to_address: str = os.getenv(SMPT_TO)
        from_address: str = os.getenv(SMPT_FROM)
        email_debug: int = int(os.getenv(SMPT_DEBUG)) if os.getenv(SMPT_DEBUG) else 0
        try:
            smtpObj: SMTP = SMTP(host, port)
            smtpObj.set_debuglevel(email_debug)
            msg = MIMEText('\n'.join(self.email_msg()))
            msg['Subject'] = self.get_subject()
            msg['From'] = from_address
            msg['To'] = to_address
            smtpObj.send_message(msg)
            self.__log.info("Successfully sent email")
        except SMTPException as e:
            self.__log.info(f"Error: unable to send email due to {e}")

