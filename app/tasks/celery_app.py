"""
Celery設定
"""

from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "accounting_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.scheduled_reports",
        "app.tasks.reminders",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Tokyo",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    worker_prefetch_multiplier=1,
)

# 定期タスクスケジュール
celery_app.conf.beat_schedule = {
    # 月中レポート（毎月15日 9:00）
    "mid-month-report": {
        "task": "app.tasks.scheduled_reports.send_mid_month_reports",
        "schedule": crontab(day_of_month="15", hour=9, minute=0),
    },
    # 月末レポート（毎月末日 18:00）
    "month-end-report": {
        "task": "app.tasks.scheduled_reports.send_month_end_reports",
        "schedule": crontab(day_of_month="28-31", hour=18, minute=0),
    },
    # 四半期レポート（3,6,9,12月末）
    "quarterly-report": {
        "task": "app.tasks.scheduled_reports.send_quarterly_reports",
        "schedule": crontab(month_of_year="3,6,9,12", day_of_month="28-31", hour=19, minute=0),
    },
    # 確定申告リマインダー（1-3月の毎週月曜 9:00）
    "tax-filing-reminder": {
        "task": "app.tasks.reminders.send_tax_filing_reminders",
        "schedule": crontab(month_of_year="1,2,3", day_of_week="1", hour=9, minute=0),
    },
    # 消費税納付リマインダー（3月上旬）
    "consumption-tax-reminder": {
        "task": "app.tasks.reminders.send_consumption_tax_reminders",
        "schedule": crontab(month_of_year="3", day_of_month="1-10", hour=9, minute=0),
    },
    # 入金催促（毎月5日、15日、25日）
    "payment-reminder": {
        "task": "app.tasks.reminders.send_payment_reminders",
        "schedule": crontab(day_of_month="5,15,25", hour=10, minute=0),
    },
}
