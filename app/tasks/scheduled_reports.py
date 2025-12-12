"""
定期レポート配信タスク
月中・月末・四半期レポートを自動配信
"""

from app.tasks.celery_app import celery_app
from app.models.database import get_db
from app.models.user import User
from app.core.report_generator import report_generator
from app.services.line_service import line_service
from datetime import date, datetime
import calendar
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def send_mid_month_reports(self):
    """
    月中レポート配信（毎月15日）
    全アクティブユーザーに配信
    """
    logger.info("Starting mid-month report distribution")
    
    try:
        db = next(get_db())
        users = db.query(User).filter(User.is_active == True).all()
        
        success_count = 0
        error_count = 0
        
        for user in users:
            try:
                report = report_generator.generate_mid_month_report(
                    db, user.line_user_id
                )
                
                if report and "error" not in report.lower():
                    line_service.send_text_message(user.line_user_id, report)
                    success_count += 1
                    logger.info(f"Mid-month report sent to user {user.id}")
                else:
                    logger.warning(f"No report data for user {user.id}")
                    
            except Exception as e:
                error_count += 1
                logger.error(f"Failed to send report to user {user.id}: {e}")
        
        logger.info(
            f"Mid-month reports completed: {success_count} success, {error_count} errors"
        )
        
        return {
            "status": "completed",
            "success_count": success_count,
            "error_count": error_count,
        }
        
    except Exception as e:
        logger.error(f"Mid-month report task failed: {e}")
        self.retry(countdown=60 * 5)  # 5分後にリトライ


@celery_app.task(bind=True, max_retries=3)
def send_month_end_reports(self):
    """
    月末レポート配信
    """
    today = date.today()
    last_day = calendar.monthrange(today.year, today.month)[1]
    
    # 月末日のみ実行
    if today.day != last_day:
        logger.info(f"Not month end (day {today.day}), skipping")
        return {"status": "skipped", "reason": "not_month_end"}
    
    year_month = today.strftime("%Y-%m")
    logger.info(f"Starting month-end report distribution for {year_month}")
    
    try:
        db = next(get_db())
        users = db.query(User).filter(User.is_active == True).all()
        
        success_count = 0
        error_count = 0
        
        for user in users:
            try:
                report = report_generator.generate_month_end_report(
                    db, user.line_user_id, year_month
                )
                
                if report and "error" not in report.lower():
                    line_service.send_text_message(user.line_user_id, report)
                    success_count += 1
                    logger.info(f"Month-end report sent to user {user.id}")
                else:
                    logger.warning(f"No report data for user {user.id}")
                    
            except Exception as e:
                error_count += 1
                logger.error(f"Failed to send report to user {user.id}: {e}")
        
        logger.info(
            f"Month-end reports completed: {success_count} success, {error_count} errors"
        )
        
        return {
            "status": "completed",
            "year_month": year_month,
            "success_count": success_count,
            "error_count": error_count,
        }
        
    except Exception as e:
        logger.error(f"Month-end report task failed: {e}")
        self.retry(countdown=60 * 5)


@celery_app.task(bind=True, max_retries=3)
def send_quarterly_reports(self):
    """
    四半期レポート配信（3,6,9,12月末）
    """
    today = date.today()
    last_day = calendar.monthrange(today.year, today.month)[1]
    
    # 月末日かつ四半期末月のみ実行
    if today.day != last_day or today.month not in [3, 6, 9, 12]:
        logger.info("Not quarter end, skipping")
        return {"status": "skipped", "reason": "not_quarter_end"}
    
    year = today.year
    quarter = (today.month - 1) // 3 + 1
    
    logger.info(f"Starting quarterly report distribution for {year} Q{quarter}")
    
    try:
        db = next(get_db())
        users = db.query(User).filter(User.is_active == True).all()
        
        success_count = 0
        error_count = 0
        
        for user in users:
            try:
                report = report_generator.generate_quarterly_report(
                    db, user.line_user_id, year, quarter
                )
                
                if report and "error" not in report.lower():
                    line_service.send_text_message(user.line_user_id, report)
                    success_count += 1
                    logger.info(f"Quarterly report sent to user {user.id}")
                else:
                    logger.warning(f"No report data for user {user.id}")
                    
            except Exception as e:
                error_count += 1
                logger.error(f"Failed to send report to user {user.id}: {e}")
        
        logger.info(
            f"Quarterly reports completed: {success_count} success, {error_count} errors"
        )
        
        return {
            "status": "completed",
            "year": year,
            "quarter": quarter,
            "success_count": success_count,
            "error_count": error_count,
        }
        
    except Exception as e:
        logger.error(f"Quarterly report task failed: {e}")
        self.retry(countdown=60 * 5)


@celery_app.task(bind=True, max_retries=3)
def send_annual_reports(self):
    """
    年次レポート配信（12月末または1月初）
    """
    today = date.today()
    year = today.year - 1 if today.month == 1 else today.year
    
    logger.info(f"Starting annual report distribution for {year}")
    
    try:
        db = next(get_db())
        users = db.query(User).filter(User.is_active == True).all()
        
        success_count = 0
        error_count = 0
        
        for user in users:
            try:
                report = report_generator.generate_annual_report(
                    db, user.line_user_id, year
                )
                
                if report and "error" not in report.lower():
                    line_service.send_text_message(user.line_user_id, report)
                    success_count += 1
                    logger.info(f"Annual report sent to user {user.id}")
                else:
                    logger.warning(f"No report data for user {user.id}")
                    
            except Exception as e:
                error_count += 1
                logger.error(f"Failed to send report to user {user.id}: {e}")
        
        logger.info(
            f"Annual reports completed: {success_count} success, {error_count} errors"
        )
        
        return {
            "status": "completed",
            "year": year,
            "success_count": success_count,
            "error_count": error_count,
        }
        
    except Exception as e:
        logger.error(f"Annual report task failed: {e}")
        self.retry(countdown=60 * 5)


@celery_app.task
def send_custom_report(user_id: str, report_type: str, params: dict = None):
    """
    カスタムレポート配信（オンデマンド）
    """
    params = params or {}
    
    try:
        db = next(get_db())
        
        if report_type == "profit_loss":
            year_month = params.get("year_month", date.today().strftime("%Y-%m"))
            report = report_generator.generate_month_end_report(
                db, user_id, year_month
            )
        elif report_type == "mid_month":
            report = report_generator.generate_mid_month_report(db, user_id)
        elif report_type == "quarterly":
            year = params.get("year", date.today().year)
            quarter = params.get("quarter", (date.today().month - 1) // 3 + 1)
            report = report_generator.generate_quarterly_report(
                db, user_id, year, quarter
            )
        elif report_type == "annual":
            year = params.get("year", date.today().year)
            report = report_generator.generate_annual_report(db, user_id, year)
        else:
            report = "指定されたレポートタイプが見つかりません"
        
        if report:
            line_service.send_text_message(user_id, report)
            return {"status": "sent", "report_type": report_type}
        else:
            return {"status": "no_data", "report_type": report_type}
            
    except Exception as e:
        logger.error(f"Custom report failed for user {user_id}: {e}")
        return {"status": "error", "error": str(e)}
