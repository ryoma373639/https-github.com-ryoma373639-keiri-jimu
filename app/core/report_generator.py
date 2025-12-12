"""
レポート生成エンジン
各種財務レポートを生成
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.models.transaction import Transaction
from app.models.user import User
from app.core.ledger_generator import ledger_generator
from app.core.tax_calculator import tax_calculator
from datetime import date, datetime
from typing import Dict, Optional
from decimal import Decimal
import calendar
import logging

logger = logging.getLogger(__name__)


class ReportGenerator:
    """レポート生成エンジン"""

    def generate_profit_loss_statement(
        self, db: Session, user_id: str, year_month: str
    ) -> Dict:
        """
        損益計算書生成
        """
        user = db.query(User).filter(User.line_user_id == user_id).first()
        if not user:
            return {"error": "ユーザーが見つかりません"}

        start_date = datetime.strptime(f"{year_month}-01", "%Y-%m-%d").date()
        last_day = calendar.monthrange(start_date.year, start_date.month)[1]
        end_date = datetime.strptime(f"{year_month}-{last_day}", "%Y-%m-%d").date()

        # 売上高
        sales = (
            db.query(func.sum(Transaction.credit_amount))
            .filter(
                and_(
                    Transaction.user_id == user.id,
                    Transaction.transaction_date >= start_date,
                    Transaction.transaction_date <= end_date,
                    Transaction.credit_account == "売上高",
                )
            )
            .scalar()
            or 0
        )

        # 売上原価
        cost_of_sales = (
            db.query(func.sum(Transaction.debit_amount))
            .filter(
                and_(
                    Transaction.user_id == user.id,
                    Transaction.transaction_date >= start_date,
                    Transaction.transaction_date <= end_date,
                    Transaction.debit_account == "仕入高",
                )
            )
            .scalar()
            or 0
        )

        # 経費（販管費）
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
            "減価償却費",
            "給料賃金",
        ]

        expenses_detail = {}
        for account in expense_accounts:
            amount = (
                db.query(func.sum(Transaction.debit_amount))
                .filter(
                    and_(
                        Transaction.user_id == user.id,
                        Transaction.transaction_date >= start_date,
                        Transaction.transaction_date <= end_date,
                        Transaction.debit_account == account,
                    )
                )
                .scalar()
                or 0
            )
            if amount > 0:
                expenses_detail[account] = float(amount)

        total_expenses = sum(expenses_detail.values())

        # 営業利益
        gross_profit = float(sales) - float(cost_of_sales)
        operating_profit = gross_profit - total_expenses

        # 利益率
        profit_margin = (
            (operating_profit / float(sales) * 100) if float(sales) > 0 else 0
        )

        return {
            "period": year_month,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "sales": float(sales),
            "cost_of_sales": float(cost_of_sales),
            "gross_profit": gross_profit,
            "expenses_detail": expenses_detail,
            "total_expenses": total_expenses,
            "operating_profit": operating_profit,
            "profit_margin": round(profit_margin, 2),
        }

    def generate_balance_sheet(
        self, db: Session, user_id: str, as_of_date: date
    ) -> Dict:
        """
        貸借対照表生成
        """
        user = db.query(User).filter(User.line_user_id == user_id).first()
        if not user:
            return {"error": "ユーザーが見つかりません"}

        # 資産科目
        asset_accounts = [
            "現金",
            "普通預金",
            "当座預金",
            "売掛金",
            "受取手形",
            "前払金",
            "貯蔵品",
            "建物",
            "車両運搬具",
            "工具器具備品",
            "ソフトウェア",
        ]

        # 負債科目
        liability_accounts = [
            "買掛金",
            "未払金",
            "前受金",
            "預り金",
            "短期借入金",
            "長期借入金",
        ]

        # 資本科目
        capital_accounts = ["元入金", "事業主借", "事業主貸"]

        assets = {}
        liabilities = {}
        capital = {}

        # 資産集計
        for account in asset_accounts:
            debit = (
                db.query(func.sum(Transaction.debit_amount))
                .filter(
                    and_(
                        Transaction.user_id == user.id,
                        Transaction.transaction_date <= as_of_date,
                        Transaction.debit_account == account,
                    )
                )
                .scalar()
                or 0
            )
            credit = (
                db.query(func.sum(Transaction.credit_amount))
                .filter(
                    and_(
                        Transaction.user_id == user.id,
                        Transaction.transaction_date <= as_of_date,
                        Transaction.credit_account == account,
                    )
                )
                .scalar()
                or 0
            )
            balance = float(debit) - float(credit)
            if balance != 0:
                assets[account] = balance

        # 負債集計
        for account in liability_accounts:
            credit = (
                db.query(func.sum(Transaction.credit_amount))
                .filter(
                    and_(
                        Transaction.user_id == user.id,
                        Transaction.transaction_date <= as_of_date,
                        Transaction.credit_account == account,
                    )
                )
                .scalar()
                or 0
            )
            debit = (
                db.query(func.sum(Transaction.debit_amount))
                .filter(
                    and_(
                        Transaction.user_id == user.id,
                        Transaction.transaction_date <= as_of_date,
                        Transaction.debit_account == account,
                    )
                )
                .scalar()
                or 0
            )
            balance = float(credit) - float(debit)
            if balance != 0:
                liabilities[account] = balance

        # 資本集計
        for account in capital_accounts:
            if account == "事業主貸":
                # 事業主貸は借方
                debit = (
                    db.query(func.sum(Transaction.debit_amount))
                    .filter(
                        and_(
                            Transaction.user_id == user.id,
                            Transaction.transaction_date <= as_of_date,
                            Transaction.debit_account == account,
                        )
                    )
                    .scalar()
                    or 0
                )
                balance = -float(debit)  # マイナス表示
            else:
                credit = (
                    db.query(func.sum(Transaction.credit_amount))
                    .filter(
                        and_(
                            Transaction.user_id == user.id,
                            Transaction.transaction_date <= as_of_date,
                            Transaction.credit_account == account,
                        )
                    )
                    .scalar()
                    or 0
                )
                balance = float(credit)

            if balance != 0:
                capital[account] = balance

        total_assets = sum(assets.values())
        total_liabilities = sum(liabilities.values())
        total_capital = sum(capital.values())

        return {
            "as_of_date": as_of_date.strftime("%Y-%m-%d"),
            "assets": assets,
            "total_assets": total_assets,
            "liabilities": liabilities,
            "total_liabilities": total_liabilities,
            "capital": capital,
            "total_capital": total_capital,
            "total_liabilities_and_capital": total_liabilities + total_capital,
        }

    def generate_mid_month_report(self, db: Session, user_id: str) -> str:
        """
        月中レポート生成（15日配信用）
        """
        today = date.today()
        year_month = today.strftime("%Y-%m")

        pl = self.generate_profit_loss_statement(db, user_id, year_month)

        if "error" in pl:
            return pl["error"]

        # 経費トップ3
        top_expenses = sorted(
            pl["expenses_detail"].items(), key=lambda x: x[1], reverse=True
        )[:3]
        expense_text = "\n".join(
            [f"  ・{name}: {amount:,.0f}円" for name, amount in top_expenses]
        )

        report = f"""【月中レポート {today.strftime('%Y年%m月%d日')}】

■ 売上状況
確定売上: {pl['sales']:,.0f}円

■ 経費状況
今月累計: {pl['total_expenses']:,.0f}円
主な経費:
{expense_text}

■ 収支
売上総利益: {pl['gross_profit']:,.0f}円
営業利益: {pl['operating_profit']:,.0f}円
利益率: {pl['profit_margin']:.1f}%

※月末までの見込みに注意して経営判断を行ってください
"""
        return report

    def generate_month_end_report(
        self, db: Session, user_id: str, year_month: str
    ) -> str:
        """
        月末レポート生成
        """
        pl = self.generate_profit_loss_statement(db, user_id, year_month)

        if "error" in pl:
            return pl["error"]

        # 経費詳細
        expense_lines = []
        for account, amount in sorted(
            pl["expenses_detail"].items(), key=lambda x: x[1], reverse=True
        ):
            expense_lines.append(f"  {account}: {amount:,.0f}円")
        expense_text = "\n".join(expense_lines) if expense_lines else "  なし"

        report = f"""【月次決算レポート {year_month}】

━━━━━━ 損益サマリー ━━━━━━

売上高: {pl['sales']:,.0f}円
売上原価: {pl['cost_of_sales']:,.0f}円
売上総利益: {pl['gross_profit']:,.0f}円

━━━━━━ 経費内訳 ━━━━━━

{expense_text}

経費合計: {pl['total_expenses']:,.0f}円

━━━━━━ 利益 ━━━━━━

営業利益: {pl['operating_profit']:,.0f}円
利益率: {pl['profit_margin']:.1f}%

━━━━━━━━━━━━━━━━━━

詳細な帳簿データが必要な場合は
「帳簿表示」とメッセージしてください。
"""
        return report

    def generate_quarterly_report(
        self, db: Session, user_id: str, year: int, quarter: int
    ) -> str:
        """
        四半期レポート生成
        """
        quarter_months = {
            1: ["01", "02", "03"],
            2: ["04", "05", "06"],
            3: ["07", "08", "09"],
            4: ["10", "11", "12"],
        }

        months = quarter_months.get(quarter, [])
        if not months:
            return "無効な四半期です"

        total_sales = 0
        total_expenses = 0
        monthly_data = []

        for month in months:
            year_month = f"{year}-{month}"
            pl = self.generate_profit_loss_statement(db, user_id, year_month)
            if "error" not in pl:
                total_sales += pl["sales"]
                total_expenses += pl["total_expenses"]
                monthly_data.append(
                    {
                        "month": year_month,
                        "sales": pl["sales"],
                        "expenses": pl["total_expenses"],
                        "profit": pl["operating_profit"],
                    }
                )

        quarterly_profit = total_sales - total_expenses

        # 月別推移
        monthly_lines = []
        for data in monthly_data:
            monthly_lines.append(
                f"  {data['month']}: 売上 {data['sales']:,.0f}円 / 利益 {data['profit']:,.0f}円"
            )
        monthly_text = "\n".join(monthly_lines)

        report = f"""【第{quarter}四半期レポート {year}年】

━━━━━━ 四半期サマリー ━━━━━━

売上高合計: {total_sales:,.0f}円
経費合計: {total_expenses:,.0f}円
四半期利益: {quarterly_profit:,.0f}円

━━━━━━ 月別推移 ━━━━━━

{monthly_text}

━━━━━━━━━━━━━━━━━━
"""
        return report

    def generate_annual_report(self, db: Session, user_id: str, year: int) -> str:
        """
        年次レポート生成
        """
        total_sales = 0
        total_cost = 0
        total_expenses = 0
        monthly_data = []

        for month in range(1, 13):
            year_month = f"{year}-{month:02d}"
            pl = self.generate_profit_loss_statement(db, user_id, year_month)
            if "error" not in pl:
                total_sales += pl["sales"]
                total_cost += pl["cost_of_sales"]
                total_expenses += pl["total_expenses"]
                monthly_data.append(
                    {
                        "month": month,
                        "sales": pl["sales"],
                        "profit": pl["operating_profit"],
                    }
                )

        annual_profit = total_sales - total_cost - total_expenses

        # 税額概算
        tax_estimate = tax_calculator.estimate_annual_tax(
            Decimal(str(total_sales)), Decimal(str(total_cost + total_expenses))
        )

        report = f"""【年次決算レポート {year}年】

━━━━━━ 年間損益サマリー ━━━━━━

売上高: {total_sales:,.0f}円
売上原価: {total_cost:,.0f}円
経費: {total_expenses:,.0f}円
事業所得: {annual_profit:,.0f}円

━━━━━━ 税金概算 ━━━━━━

所得税: {tax_estimate['所得税']:,.0f}円
住民税: {tax_estimate['住民税（概算）']:,.0f}円
事業税: {tax_estimate['個人事業税（概算）']:,.0f}円
合計: {tax_estimate['税金合計（概算）']:,.0f}円

※確定申告時に正確な税額を計算してください

━━━━━━━━━━━━━━━━━━
"""
        return report


report_generator = ReportGenerator()
