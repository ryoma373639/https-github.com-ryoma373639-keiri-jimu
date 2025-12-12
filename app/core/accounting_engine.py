"""
会計エンジン
仕訳の生成、検証、帳簿への転記を実行
"""

from typing import Dict, Optional
from decimal import Decimal
from datetime import date, datetime
from sqlalchemy.orm import Session
from app.models.transaction import Transaction
from app.models.user import User
from app.services.claude_service import claude_service
import logging
import uuid

logger = logging.getLogger(__name__)


class AccountingEngine:
    """会計処理エンジン"""

    def parse_natural_language(self, text: str, user_id: str) -> Dict:
        """
        自然言語を解析して取引情報を抽出
        """
        result = claude_service.analyze_transaction(text)
        result["user_id"] = user_id
        return result

    def create_journal_entry(self, transaction_data: Dict, db: Session) -> Transaction:
        """
        仕訳を生成してDBに保存
        """
        try:
            # ユーザー取得または作成
            line_user_id = transaction_data.get("user_id")
            user = db.query(User).filter(User.line_user_id == line_user_id).first()

            if not user:
                user = User(line_user_id=line_user_id)
                db.add(user)
                db.commit()
                db.refresh(user)
                logger.info(f"New user created: {user.id}")

            # 日付処理
            trans_date = transaction_data.get("date")
            if isinstance(trans_date, str):
                trans_date = datetime.strptime(trans_date, "%Y-%m-%d").date()
            elif trans_date is None:
                trans_date = date.today()

            # 金額処理
            amount = Decimal(str(transaction_data["amount"]))

            # 消費税計算
            tax_type = transaction_data.get("tax_type", "課税10%")
            tax_amount = self._calculate_tax(amount, tax_type)

            # Transactionオブジェクト作成
            transaction = Transaction(
                transaction_date=trans_date,
                debit_account=transaction_data["debit_account"],
                debit_amount=amount,
                credit_account=transaction_data["credit_account"],
                credit_amount=amount,
                description=transaction_data.get("description", ""),
                project_name=transaction_data.get("project"),
                tax_type=tax_type,
                tax_amount=tax_amount,
                user_id=user.id,
            )

            # 検証
            if not self.validate_entry(transaction):
                raise ValueError("仕訳の妥当性検証に失敗しました")

            # 保存
            db.add(transaction)
            db.commit()
            db.refresh(transaction)

            logger.info(f"Transaction created: {transaction.id}")
            return transaction

        except Exception as e:
            logger.error(f"Failed to create journal entry: {e}")
            db.rollback()
            raise

    def validate_entry(self, entry: Transaction) -> bool:
        """
        仕訳の妥当性検証
        """
        # 借方 = 貸方チェック
        if entry.debit_amount != entry.credit_amount:
            logger.error("Debit and credit amounts do not match")
            return False

        # 金額が正の数チェック
        if entry.debit_amount <= 0:
            logger.error("Amount must be positive")
            return False

        # 勘定科目の存在チェック（簡易）
        if not entry.debit_account or not entry.credit_account:
            logger.error("Account names are required")
            return False

        return True

    def _calculate_tax(self, amount: Decimal, tax_type: str) -> Decimal:
        """
        消費税計算（税込金額から税額を算出）
        """
        if tax_type == "課税10%":
            return (amount * Decimal("10")) / Decimal("110")
        elif tax_type == "課税8%":
            return (amount * Decimal("8")) / Decimal("108")
        else:
            return Decimal("0")

    def get_user_transactions(
        self, db: Session, user_id: str, start_date: date = None, end_date: date = None
    ):
        """
        ユーザーの取引履歴を取得
        """
        query = db.query(Transaction).join(User).filter(User.line_user_id == user_id)

        if start_date:
            query = query.filter(Transaction.transaction_date >= start_date)
        if end_date:
            query = query.filter(Transaction.transaction_date <= end_date)

        return query.order_by(Transaction.transaction_date.desc()).all()

    def delete_transaction(self, db: Session, transaction_id: str, user_id: str) -> bool:
        """
        取引を削除
        """
        try:
            transaction = (
                db.query(Transaction)
                .join(User)
                .filter(
                    Transaction.id == transaction_id,
                    User.line_user_id == user_id,
                )
                .first()
            )

            if transaction:
                db.delete(transaction)
                db.commit()
                logger.info(f"Transaction deleted: {transaction_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete transaction: {e}")
            db.rollback()
            return False


accounting_engine = AccountingEngine()
