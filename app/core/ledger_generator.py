"""
帳簿生成エンジン
各種帳簿を自動生成
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.models.transaction import Transaction
from app.models.user import User
import pandas as pd
from datetime import date, datetime
from typing import List, Dict, Optional
import calendar
import logging

logger = logging.getLogger(__name__)


class LedgerGenerator:
    """帳簿生成エンジン"""

    def generate_journal(
        self, db: Session, user_id: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """
        仕訳帳生成
        """
        user = db.query(User).filter(User.line_user_id == user_id).first()
        if not user:
            return pd.DataFrame()

        transactions = (
            db.query(Transaction)
            .filter(
                and_(
                    Transaction.user_id == user.id,
                    Transaction.transaction_date >= start_date,
                    Transaction.transaction_date <= end_date,
                )
            )
            .order_by(Transaction.transaction_date)
            .all()
        )

        data = []
        for t in transactions:
            data.append(
                {
                    "日付": t.transaction_date.strftime("%Y-%m-%d"),
                    "借方科目": t.debit_account,
                    "借方金額": float(t.debit_amount),
                    "貸方科目": t.credit_account,
                    "貸方金額": float(t.credit_amount),
                    "摘要": t.description or "",
                    "税区分": t.tax_type,
                    "消費税額": float(t.tax_amount) if t.tax_amount else 0,
                }
            )

        return pd.DataFrame(data)

    def generate_trial_balance(
        self, db: Session, user_id: str, as_of_date: date
    ) -> pd.DataFrame:
        """
        残高試算表生成
        """
        user = db.query(User).filter(User.line_user_id == user_id).first()
        if not user:
            return pd.DataFrame()

        # 借方合計
        debit_totals = (
            db.query(
                Transaction.debit_account.label("account"),
                func.sum(Transaction.debit_amount).label("debit_total"),
            )
            .filter(
                and_(
                    Transaction.user_id == user.id,
                    Transaction.transaction_date <= as_of_date,
                )
            )
            .group_by(Transaction.debit_account)
            .all()
        )

        # 貸方合計
        credit_totals = (
            db.query(
                Transaction.credit_account.label("account"),
                func.sum(Transaction.credit_amount).label("credit_total"),
            )
            .filter(
                and_(
                    Transaction.user_id == user.id,
                    Transaction.transaction_date <= as_of_date,
                )
            )
            .group_by(Transaction.credit_account)
            .all()
        )

        # データ整形
        accounts = {}
        for account, debit in debit_totals:
            accounts[account] = {"debit": float(debit), "credit": 0}

        for account, credit in credit_totals:
            if account in accounts:
                accounts[account]["credit"] = float(credit)
            else:
                accounts[account] = {"debit": 0, "credit": float(credit)}

        # 残高計算
        data = []
        total_debit = 0
        total_credit = 0

        for account, totals in sorted(accounts.items()):
            balance = totals["debit"] - totals["credit"]
            data.append(
                {
                    "勘定科目": account,
                    "借方合計": totals["debit"],
                    "貸方合計": totals["credit"],
                    "借方残高": balance if balance > 0 else 0,
                    "貸方残高": -balance if balance < 0 else 0,
                }
            )
            total_debit += totals["debit"]
            total_credit += totals["credit"]

        # 合計行追加
        data.append(
            {
                "勘定科目": "【合計】",
                "借方合計": total_debit,
                "貸方合計": total_credit,
                "借方残高": total_debit,
                "貸方残高": total_credit,
            }
        )

        return pd.DataFrame(data)

    def generate_cash_book(
        self, db: Session, user_id: str, year_month: str
    ) -> pd.DataFrame:
        """
        現金出納帳生成
        """
        user = db.query(User).filter(User.line_user_id == user_id).first()
        if not user:
            return pd.DataFrame()

        start_date = datetime.strptime(f"{year_month}-01", "%Y-%m-%d").date()
        last_day = calendar.monthrange(start_date.year, start_date.month)[1]
        end_date = datetime.strptime(f"{year_month}-{last_day}", "%Y-%m-%d").date()

        # 現金に関連する取引を抽出
        transactions = (
            db.query(Transaction)
            .filter(
                and_(
                    Transaction.user_id == user.id,
                    Transaction.transaction_date >= start_date,
                    Transaction.transaction_date <= end_date,
                    (Transaction.debit_account == "現金")
                    | (Transaction.credit_account == "現金"),
                )
            )
            .order_by(Transaction.transaction_date)
            .all()
        )

        data = []
        balance = 0  # 簡易的な残高（本来は前月繰越を考慮）

        for t in transactions:
            if t.debit_account == "現金":
                income = float(t.debit_amount)
                expense = 0
                balance += income
                counterpart = t.credit_account
            else:
                income = 0
                expense = float(t.credit_amount)
                balance -= expense
                counterpart = t.debit_account

            data.append(
                {
                    "日付": t.transaction_date.strftime("%Y-%m-%d"),
                    "摘要": t.description or "",
                    "相手科目": counterpart,
                    "収入": income,
                    "支出": expense,
                    "残高": balance,
                }
            )

        return pd.DataFrame(data)

    def generate_general_ledger(
        self,
        db: Session,
        user_id: str,
        account_name: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """
        総勘定元帳生成（特定勘定科目の詳細）
        """
        user = db.query(User).filter(User.line_user_id == user_id).first()
        if not user:
            return pd.DataFrame()

        transactions = (
            db.query(Transaction)
            .filter(
                and_(
                    Transaction.user_id == user.id,
                    Transaction.transaction_date >= start_date,
                    Transaction.transaction_date <= end_date,
                    (Transaction.debit_account == account_name)
                    | (Transaction.credit_account == account_name),
                )
            )
            .order_by(Transaction.transaction_date)
            .all()
        )

        data = []
        balance = 0

        for t in transactions:
            if t.debit_account == account_name:
                debit = float(t.debit_amount)
                credit = 0
                counterpart = t.credit_account
                balance += debit
            else:
                debit = 0
                credit = float(t.credit_amount)
                counterpart = t.debit_account
                balance -= credit

            data.append(
                {
                    "日付": t.transaction_date.strftime("%Y-%m-%d"),
                    "摘要": t.description or "",
                    "相手科目": counterpart,
                    "借方": debit,
                    "貸方": credit,
                    "残高": balance,
                }
            )

        return pd.DataFrame(data)

    def generate_expense_summary(
        self, db: Session, user_id: str, year_month: str
    ) -> Dict:
        """
        経費科目別集計
        """
        user = db.query(User).filter(User.line_user_id == user_id).first()
        if not user:
            return {}

        start_date = datetime.strptime(f"{year_month}-01", "%Y-%m-%d").date()
        last_day = calendar.monthrange(start_date.year, start_date.month)[1]
        end_date = datetime.strptime(f"{year_month}-{last_day}", "%Y-%m-%d").date()

        expense_accounts = [
            "旅費交通費",
            "接待交際費",
            "消耗品費",
            "広告宣伝費",
            "通信費",
            "地代家賃",
            "水道光熱費",
            "外注費",
            "雑費",
            "研修費",
            "新聞図書費",
            "支払手数料",
            "租税公課",
        ]

        results = (
            db.query(
                Transaction.debit_account, func.sum(Transaction.debit_amount).label("total")
            )
            .filter(
                and_(
                    Transaction.user_id == user.id,
                    Transaction.transaction_date >= start_date,
                    Transaction.transaction_date <= end_date,
                    Transaction.debit_account.in_(expense_accounts),
                )
            )
            .group_by(Transaction.debit_account)
            .all()
        )

        summary = {account: 0 for account in expense_accounts}
        for account, total in results:
            summary[account] = float(total)

        summary["合計"] = sum(summary.values())

        return summary

    def format_journal_for_line(self, df: pd.DataFrame, limit: int = 10) -> str:
        """
        仕訳帳をLINE用テキストに整形
        """
        if df.empty:
            return "取引データがありません。"

        lines = ["【仕訳帳】\n"]
        for i, row in df.head(limit).iterrows():
            lines.append(
                f"{row['日付']}\n"
                f"  {row['借方科目']} {row['借方金額']:,.0f}円\n"
                f"  　/ {row['貸方科目']} {row['貸方金額']:,.0f}円\n"
                f"  摘要: {row['摘要']}\n"
            )

        if len(df) > limit:
            lines.append(f"\n...他{len(df) - limit}件")

        return "\n".join(lines)

    def format_trial_balance_for_line(self, df: pd.DataFrame) -> str:
        """
        残高試算表をLINE用テキストに整形
        """
        if df.empty:
            return "データがありません。"

        lines = ["【残高試算表】\n"]
        lines.append("科目 | 借方 | 貸方\n")
        lines.append("-" * 30 + "\n")

        for _, row in df.iterrows():
            if row["借方残高"] > 0 or row["貸方残高"] > 0:
                lines.append(
                    f"{row['勘定科目']}: "
                    f"借方 {row['借方残高']:,.0f}円 / "
                    f"貸方 {row['貸方残高']:,.0f}円\n"
                )

        return "".join(lines)


ledger_generator = LedgerGenerator()
