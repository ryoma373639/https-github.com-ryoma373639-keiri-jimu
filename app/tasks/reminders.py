"""
リマインダータスク
"""

from app.tasks.celery_app import celery_app
from app.models.database import SessionLocal
import logging

logger = logging.getLogger(__name__)


@celery_app.task
def check_and_send_reminders():
    """
    毎日9:00にリマインダーをチェックして送信
    """
    db = SessionLocal()
    try:
        # TODO: リマインダーモデル実装後に有効化
        logger.info("Reminder check task executed")
    finally:
        db.close()
