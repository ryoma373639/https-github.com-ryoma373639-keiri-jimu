"""
リマインダータスク
確定申告、消費税納付、入金催促などのリマインダー配信
"""

from app.tasks.celery_app import celery_app
from app.models.database import get_db
from app.models.user import User
from app.models.transaction import Transaction
from app.models.client import Client
from app.core.tax_calculator import tax_calculator
from app.core.report_generator import report_generator
from app.services.line_service import line_service
from sqlalchemy import func, and_
from datetime import date, datetime, timedelta
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def send_tax_filing_reminders(self):
    """
    確定申告リマインダー（1-3月の毎週月曜）
    """
    today = date.today()
    
    # 申告期限（3月15日）までの日数
    deadline = date(today.year, 3, 15)
    days_remaining = (deadline - today).days
    
    if days_remaining < 0:
        logger.info("Tax filing deadline passed")
        return {"status": "skipped", "reason": "deadline_passed"}
    
    logger.info(f"Sending tax filing reminders, {days_remaining} days remaining")
    
    try:
        db = next(get_db())
        users = db.query(User).filter(User.is_active == True).all()
        
        success_count = 0
        
        for user in users:
            try:
                # 前年の売上・経費概算
                last_year = today.year - 1
                annual_report = report_generator.generate_annual_report(
                    db, user.line_user_id, last_year
                )
                
                message = f"""【確定申告リマインダー】

申告期限まであと{days_remaining}日です！

📅 期限: {today.year}年3月15日

⚠️ 準備チェックリスト:
□ 売上帳・仕訳帳の確認
□ 経費の領収書整理
□ 医療費の領収書
□ 生命保険料控除証明書
□ 社会保険料控除証明書
□ マイナンバーカード

「年次レポート」と送信すると
{last_year}年の収支サマリーを確認できます。

「確定申告」と送信すると
申告書作成サポートを開始します。
"""
                
                line_service.send_text_message(user.line_user_id, message)
                success_count += 1
                
            except Exception as e:
                logger.error(f"Failed to send reminder to user {user.id}: {e}")
        
        return {
            "status": "completed",
            "days_remaining": days_remaining,
            "success_count": success_count,
        }
        
    except Exception as e:
        logger.error(f"Tax filing reminder task failed: {e}")
        self.retry(countdown=60 * 5)


@celery_app.task(bind=True, max_retries=3)
def send_consumption_tax_reminders(self):
    """
    消費税納付リマインダー（3月上旬）
    """
    today = date.today()
    deadline = date(today.year, 3, 31)
    days_remaining = (deadline - today).days
    
    if days_remaining < 0:
        logger.info("Consumption tax deadline passed")
        return {"status": "skipped", "reason": "deadline_passed"}
    
    logger.info(f"Sending consumption tax reminders, {days_remaining} days remaining")
    
    try:
        db = next(get_db())
        users = db.query(User).filter(User.is_active == True).all()
        
        success_count = 0
        
        for user in users:
            try:
                message = f"""【消費税納付リマインダー】

消費税の納付期限まであと{days_remaining}日です！

📅 期限: {today.year}年3月31日

課税事業者の方は納付をお忘れなく。

「消費税計算」と送信すると
納税額の概算を確認できます。
"""
                
                line_service.send_text_message(user.line_user_id, message)
                success_count += 1
                
            except Exception as e:
                logger.error(f"Failed to send reminder to user {user.id}: {e}")
        
        return {
            "status": "completed",
            "days_remaining": days_remaining,
            "success_count": success_count,
        }
        
    except Exception as e:
        logger.error(f"Consumption tax reminder task failed: {e}")
        self.retry(countdown=60 * 5)


@celery_app.task(bind=True, max_retries=3)
def send_payment_reminders(self):
    """
    入金催促リマインダー（毎月5日、15日、25日）
    売掛金の回収状況を通知
    """
    today = date.today()
    logger.info(f"Checking overdue receivables as of {today}")
    
    try:
        db = next(get_db())
        users = db.query(User).filter(User.is_active == True).all()
        
        success_count = 0
        
        for user in users:
            try:
                # 売掛金残高を確認
                receivables = (
                    db.query(
                        Transaction.description,
                        func.sum(Transaction.debit_amount).label("debit"),
                        func.sum(Transaction.credit_amount).label("credit"),
                    )
                    .filter(
                        and_(
                            Transaction.user_id == user.id,
                            Transaction.debit_account == "売掛金",
                        )
                    )
                    .group_by(Transaction.description)
                    .all()
                )
                
                # 未回収の売掛金をリスト化
                overdue_list = []
                total_overdue = 0
                
                for item in receivables:
                    balance = float(item.debit or 0) - float(item.credit or 0)
                    if balance > 0:
                        overdue_list.append(f"  ・{item.description[:20]}: {balance:,.0f}円")
                        total_overdue += balance
                
                if overdue_list and total_overdue > 0:
                    message = f"""【入金確認リマインダー】

未回収の売掛金があります。

💰 未回収合計: {total_overdue:,.0f}円

【内訳】
{chr(10).join(overdue_list[:5])}
{"..." if len(overdue_list) > 5 else ""}

請求書の再送や入金確認をご検討ください。

「売掛金」と送信すると
詳細な売掛金管理画面を表示します。
"""
                    
                    line_service.send_text_message(user.line_user_id, message)
                    success_count += 1
                    logger.info(f"Payment reminder sent to user {user.id}")
                    
            except Exception as e:
                logger.error(f"Failed to send reminder to user {user.id}: {e}")
        
        return {
            "status": "completed",
            "success_count": success_count,
        }
        
    except Exception as e:
        logger.error(f"Payment reminder task failed: {e}")
        self.retry(countdown=60 * 5)


@celery_app.task
def send_expense_alert(user_id: str, category: str, amount: float, threshold: float):
    """
    経費アラート（予算超過時に配信）
    """
    try:
        message = f"""【経費アラート】

{category}の経費が予算を超過しました！

📊 今月の実績: {amount:,.0f}円
📌 予算: {threshold:,.0f}円
⚠️ 超過額: {amount - threshold:,.0f}円

経費の見直しをご検討ください。

「経費明細」と送信すると
詳細な経費内訳を確認できます。
"""
        
        line_service.send_text_message(user_id, message)
        logger.info(f"Expense alert sent to user {user_id}")
        return {"status": "sent", "category": category}
        
    except Exception as e:
        logger.error(f"Expense alert failed for user {user_id}: {e}")
        return {"status": "error", "error": str(e)}


@celery_app.task
def send_low_balance_alert(user_id: str, account: str, balance: float, threshold: float):
    """
    残高低下アラート
    """
    try:
        message = f"""【残高アラート】

{account}の残高が低下しています！

💰 現在残高: {balance:,.0f}円
📌 警告しきい値: {threshold:,.0f}円

資金繰りにご注意ください。

「残高」と送信すると
全口座の残高を確認できます。
"""
        
        line_service.send_text_message(user_id, message)
        logger.info(f"Low balance alert sent to user {user_id}")
        return {"status": "sent", "account": account}
        
    except Exception as e:
        logger.error(f"Low balance alert failed for user {user_id}: {e}")
        return {"status": "error", "error": str(e)}


@celery_app.task
def send_periodic_backup_reminder(user_id: str):
    """
    定期バックアップリマインダー
    """
    try:
        message = """【データバックアップのお知らせ】

定期的なデータバックアップをお勧めします。

「帳簿ダウンロード」と送信すると
仕訳帳をExcel形式で取得できます。

「PDFダウンロード」と送信すると
各種帳簿をPDF形式で取得できます。

大切なデータは定期的にバックアップしましょう。
"""
        
        line_service.send_text_message(user_id, message)
        return {"status": "sent"}
        
    except Exception as e:
        logger.error(f"Backup reminder failed for user {user_id}: {e}")
        return {"status": "error", "error": str(e)}
