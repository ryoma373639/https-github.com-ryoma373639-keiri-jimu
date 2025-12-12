"""
Celery設定
"""

from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "line_accounting",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Tokyo",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5分
    worker_prefetch_multiplier=1,
)

# 定期タスクスケジュール
celery_app.conf.beat_schedule = {
    # 月中レポート（毎月15日 9:00）
    "send-mid-month-reports": {
        "task": "app.tasks.scheduled_reports.send_mid_month_reports",
        "schedule": crontab(hour=9, minute=0, day_of_month=15),
    },
    # 月末レポート（毎月最終日 18:00）
    "send-month-end-reports": {
        "task": "app.tasks.scheduled_reports.send_month_end_reports",
        "schedule": crontab(hour=18, minute=0, day_of_month="28-31"),
    },
    # リマインダーチェック（毎日9:00）
    "check-reminders": {
        "task": "app.tasks.reminders.check_and_send_reminders",
        "schedule": crontab(hour=9, minute=0),
    },
}

# タスクを自動検出
celery_app.autodiscover_tasks(["app.tasks"])
