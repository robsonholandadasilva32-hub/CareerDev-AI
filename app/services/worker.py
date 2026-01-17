import time
import threading
import traceback
import asyncio
import logging
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models.job import BackgroundJob
from app.services.notifications import send_email, send_telegram, send_email_template, send_telegram_template, send_raw_email

logger = logging.getLogger(__name__)

# Worker function to process jobs
def process_jobs():
    db = SessionLocal()
    try:
        jobs = db.query(BackgroundJob).filter(BackgroundJob.status == "pending").all()

        for job in jobs:
            try:
                # Dispatch tasks
                if job.task_type == "send_email":
                    asyncio.run(send_email(job.payload['code'], job.payload['email']))

                elif job.task_type == "send_telegram":
                    asyncio.run(send_telegram(job.payload['code'], job.payload['chat_id']))

                elif job.task_type == "send_email_template":
                    asyncio.run(send_email_template(
                        to_email=job.payload['email'],
                        template_name=job.payload['template'],
                        context=job.payload['context'],
                        lang=job.payload.get('lang', 'pt')
                    ))

                elif job.task_type == "send_raw_email":
                    asyncio.run(send_raw_email(
                        to_email=job.payload['to_email'],
                        subject=job.payload['subject'],
                        body=job.payload['body']
                    ))

                elif job.task_type == "send_telegram_template":
                    asyncio.run(send_telegram_template(
                        chat_id=job.payload['chat_id'],
                        template_key=job.payload['template_key'],
                        context=job.payload['context'],
                        lang=job.payload.get('lang', 'pt')
                    ))

                job.status = "completed"

            except Exception as e:
                job.status = "failed"
                job.error_log = str(e)
                job.attempts += 1
                logger.error(f"JOB FAILED ID {job.id}: {e}")

            finally:
                db.commit()

    except Exception as e:
        logger.error(f"WORKER ERROR: {e}")
    finally:
        db.close()

class JobWorker(threading.Thread):
    def __init__(self, interval=10):
        super().__init__()
        self.interval = interval
        self._stop_event = threading.Event()

    def run(self):
        logger.info("Background Job Worker Started")
        while not self._stop_event.is_set():
            process_jobs()
            time.sleep(self.interval)

    def stop(self):
        self._stop_event.set()

job_worker = JobWorker()
