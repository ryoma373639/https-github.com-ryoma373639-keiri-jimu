"""
会計エンジンのテスト
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date
from decimal import Decimal

from app.core.accounting_engine import AccountingEngine


class TestAccountingEngine:
    """AccountingEngineのテスト"""

    def setup_method(self):
        """テスト前のセットアップ"""
        self.engine = AccountingEngine()

    def test_parse_amount_basic(self):
        """金額パース - 基本ケース"""
        assert self.engine.parse_amount("1000") == 1000
        assert self.engine.parse_amount("1,000") == 1000
        assert self.engine.parse_amount("1000円") == 1000
        assert self.engine.parse_amount("¥1,000") == 1000

    def test_parse_amount_with_unit(self):
        """金額パース - 単位付き"""
        assert self.engine.parse_amount("1万円") == 10000
        assert self.engine.parse_amount("10万") == 100000
        assert self.engine.parse_amount("1.5万円") == 15000

    def test_parse_amount_invalid(self):
        """金額パース - 無効な入力"""
        assert self.engine.parse_amount("") is None
        assert self.engine.parse_amount("abc") is None
        assert self.engine.parse_amount(None) is None

    def test_parse_date_various_formats(self):
        """日付パース - 各種フォーマット"""
        today = date.today()
        
        # YYYY-MM-DD
        assert self.engine.parse_date("2024-01-15") == date(2024, 1, 15)
        
        # YYYY/MM/DD
        assert self.engine.parse_date("2024/01/15") == date(2024, 1, 15)
        
        # 日本語形式
        assert self.engine.parse_date("2024年1月15日") == date(2024, 1, 15)
        
        # 今日
        assert self.engine.parse_date("今日") == today
        
        # 昨日
        from datetime import timedelta
        assert self.engine.parse_date("昨日") == today - timedelta(days=1)

    def test_parse_date_default(self):
        """日付パース - デフォルト値"""
        today = date.today()
        assert self.engine.parse_date("") == today
        assert self.engine.parse_date(None) == today

    def test_infer_debit_account(self):
        """借方勘定科目推定"""
        # 経費系
        assert self.engine.infer_debit_account("電車代") == "旅費交通費"
        assert self.engine.infer_debit_account("タクシー代") == "旅費交通費"
        assert self.engine.infer_debit_account("接待費") == "接待交際費"
        assert self.engine.infer_debit_account("飲み会") == "接待交際費"
        assert self.engine.infer_debit_account("文房具") == "消耗品費"
        assert self.engine.infer_debit_account("インターネット代") == "通信費"

    def test_infer_credit_account(self):
        """貸方勘定科目推定"""
        assert self.engine.infer_credit_account("売上") == "売上高"
        assert self.engine.infer_credit_account("入金") == "売上高"
        assert self.engine.infer_credit_account("銀行振込") == "普通預金"

    def test_validate_double_entry_balance(self):
        """複式簿記の貸借一致バリデーション"""
        # 正常ケース
        entry = {
            "debit_amount": 1000,
            "credit_amount": 1000,
        }
        errors = self.engine.validate_entry(entry)
        assert len([e for e in errors if "貸借" in e]) == 0

        # 不一致ケース
        entry_unbalanced = {
            "debit_amount": 1000,
            "credit_amount": 500,
        }
        errors = self.engine.validate_entry(entry_unbalanced)
        assert any("貸借" in e for e in errors)

    def test_validate_entry_required_fields(self):
        """仕訳エントリの必須項目バリデーション"""
        # 金額なし
        entry = {
            "debit_account": "旅費交通費",
            "credit_account": "現金",
        }
        errors = self.engine.validate_entry(entry)
        assert any("金額" in e for e in errors)

        # 科目なし
        entry_no_account = {
            "debit_amount": 1000,
            "credit_amount": 1000,
        }
        errors = self.engine.validate_entry(entry_no_account)
        assert any("科目" in e for e in errors)

    @patch("app.core.accounting_engine.claude_service")
    def test_parse_natural_language_expense(self, mock_claude):
        """自然言語パース - 経費入力"""
        mock_claude.analyze_transaction.return_value = {
            "transaction_type": "expense",
            "amount": 1000,
            "debit_account": "旅費交通費",
            "credit_account": "現金",
            "description": "電車代",
        }

        result = self.engine.parse_natural_language("今日電車代1000円払った")
        
        assert result["amount"] == 1000
        assert result["debit_account"] == "旅費交通費"

    @patch("app.core.accounting_engine.claude_service")
    def test_parse_natural_language_income(self, mock_claude):
        """自然言語パース - 売上入力"""
        mock_claude.analyze_transaction.return_value = {
            "transaction_type": "income",
            "amount": 100000,
            "debit_account": "普通預金",
            "credit_account": "売上高",
            "description": "A社からの入金",
        }

        result = self.engine.parse_natural_language("A社から10万円振り込まれた")
        
        assert result["amount"] == 100000
        assert result["credit_account"] == "売上高"


class TestAccountingEngineIntegration:
    """会計エンジン統合テスト"""

    def setup_method(self):
        self.engine = AccountingEngine()

    def test_full_expense_flow(self):
        """経費入力のフルフロー"""
        # パース
        amount = self.engine.parse_amount("1,500円")
        transaction_date = self.engine.parse_date("今日")
        debit = self.engine.infer_debit_account("タクシー代")
        credit = self.engine.infer_credit_account("現金払い")

        entry = {
            "transaction_date": transaction_date,
            "debit_account": debit,
            "debit_amount": amount,
            "credit_account": credit,
            "credit_amount": amount,
            "description": "タクシー代",
        }

        # バリデーション
        errors = self.engine.validate_entry(entry)
        
        assert amount == 1500
        assert debit == "旅費交通費"
        assert len(errors) == 0

    def test_edge_cases(self):
        """エッジケースのテスト"""
        # 0円
        assert self.engine.parse_amount("0円") == 0
        
        # 非常に大きな金額
        assert self.engine.parse_amount("999,999,999円") == 999999999
        
        # 小数点
        assert self.engine.parse_amount("1,000.5") == 1000
