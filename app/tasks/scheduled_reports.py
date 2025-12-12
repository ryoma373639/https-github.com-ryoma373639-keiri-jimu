"""
定期レポート配信タスク
"""

from app.tasks.celery_app import celery_app
from app.models.database import SessionLocal
from app.models.user import User
from app.services.line_service import line_service
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@celery_app.task
def send_mid_month_reports():
    """
    毎月15日 9:00 に全ユーザーへ月中レポート送信
    """
    db = SessionLocal()
    try:
        users = db.query(User).all()
        today = datetime.now()

        for user in users:
            try:
                # 簡易レポート生成
                report = f"""【月中レポート {today.strftime('%Y年%m月%d日')}】

■ 売上状況
確定売上: 集計中...

■ 経費状況
今月累計: 集計中...

■ 収支
差引: 集計中...

※月末までの見込みに注意して経営判断を行ってください
"""
                line_service.send_text_message(user.line_user_id, report)
                logger.info(f"Mid-month report sent to {user.line_user_id}")
            except Exception as e:
                logger.error(f"Failed to send report to {user.line_user_id}: {e}")
    finally:
        db.close()


@celery_app.task
def send_month_end_reports():
    """
    毎月末日 18:00 に全ユーザーへ月末レポート送信
    """
    db = SessionLocal()
    try:
        users = db.query(User).all()
        today = datetime.now()
        year_month = today.strftime("%Y-%m")

        for user in users:
            try:
                # 簡易レポート生成
                report = f"""【月次決算レポート {year_month}】

■ 損益サマリー
売上高: 集計中...
経費: 集計中...
営業利益: 集計中...
利益率: 集計中...

━━━━━━━━━━━━━━

詳細な帳簿データが必要な場合は
「帳簿表示」とメッセージしてください。
"""
                line_service.send_text_message(user.line_user_id, report)
                logger.info(f"Month-end report sent to {user.line_user_id}")
            except Exception as e:
                logger.error(f"Failed to send report to {user.line_user_id}: {e}")
    finally:
        db.close()
