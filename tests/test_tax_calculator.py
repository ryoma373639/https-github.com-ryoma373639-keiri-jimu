"""
税務計算エンジンのテスト
"""

import pytest
from decimal import Decimal

from app.core.tax_calculator import TaxCalculator


class TestIncomeTax:
    """所得税計算テスト"""

    def setup_method(self):
        self.calc = TaxCalculator()

    def test_income_tax_zero(self):
        """所得0円の場合"""
        result = self.calc.calculate_income_tax(Decimal("0"))
        assert result["income_tax"] == 0
        assert result["total_tax"] == 0

    def test_income_tax_negative(self):
        """マイナス所得の場合"""
        result = self.calc.calculate_income_tax(Decimal("-100000"))
        assert result["income_tax"] == 0
        assert result["total_tax"] == 0

    def test_income_tax_bracket_1(self):
        """税率5%の区間（195万円以下）"""
        result = self.calc.calculate_income_tax(Decimal("1000000"))  # 100万円
        # 100万円 * 5% = 5万円
        assert result["income_tax"] == 50000
        assert result["tax_rate"] == 0.05

    def test_income_tax_bracket_2(self):
        """税率10%の区間（195万円超～330万円以下）"""
        result = self.calc.calculate_income_tax(Decimal("3000000"))  # 300万円
        # 300万円 * 10% - 97,500円 = 202,500円
        assert result["income_tax"] == 202500
        assert result["tax_rate"] == 0.10

    def test_income_tax_bracket_3(self):
        """税率20%の区間（330万円超～695万円以下）"""
        result = self.calc.calculate_income_tax(Decimal("5000000"))  # 500万円
        # 500万円 * 20% - 427,500円 = 572,500円
        assert result["income_tax"] == 572500
        assert result["tax_rate"] == 0.20

    def test_reconstruction_tax(self):
        """復興特別所得税（2.1%）"""
        result = self.calc.calculate_income_tax(Decimal("1000000"))
        # 所得税5万円 * 2.1% = 1,050円
        assert result["reconstruction_tax"] == 1050

    def test_total_tax_calculation(self):
        """合計税額"""
        result = self.calc.calculate_income_tax(Decimal("1000000"))
        # 50,000 + 1,050 = 51,050円
        assert result["total_tax"] == 51050


class TestConsumptionTax:
    """消費税計算テスト"""

    def setup_method(self):
        self.calc = TaxCalculator()

    def test_standard_method(self):
        """原則課税"""
        result = self.calc.calculate_consumption_tax(
            Decimal("100000"),  # 売上消費税10万円
            Decimal("30000"),   # 仕入消費税3万円
            method="原則課税"
        )
        # 10万円 - 3万円 = 7万円
        assert result["payable_tax"] == 70000
        assert result["is_refund"] == False

    def test_simplified_method_type5(self):
        """簡易課税（第5種：サービス業50%）"""
        result = self.calc.calculate_consumption_tax(
            Decimal("100000"),  # 売上消費税10万円
            Decimal("0"),
            method="簡易課税",
            business_type="第5種"
        )
        # 10万円 - (10万円 * 50%) = 5万円
        assert result["payable_tax"] == 50000

    def test_simplified_method_type1(self):
        """簡易課税（第1種：卸売業90%）"""
        result = self.calc.calculate_consumption_tax(
            Decimal("100000"),
            Decimal("0"),
            method="簡易課税",
            business_type="第1種"
        )
        # 10万円 - (10万円 * 90%) = 1万円
        assert result["payable_tax"] == 10000

    def test_refund_case(self):
        """還付ケース"""
        result = self.calc.calculate_consumption_tax(
            Decimal("30000"),   # 売上消費税3万円
            Decimal("100000"),  # 仕入消費税10万円（設備投資等）
            method="原則課税"
        )
        # 3万円 - 10万円 = -7万円（還付）
        assert result["payable_tax"] == -70000
        assert result["is_refund"] == True


class TestDepreciation:
    """減価償却計算テスト"""

    def setup_method(self):
        self.calc = TaxCalculator()

    def test_straight_line_method(self):
        """定額法"""
        result = self.calc.calculate_depreciation(
            Decimal("1000000"),  # 取得価額100万円
            useful_life=5,       # 耐用年数5年
            method="定額法",
            months_used=12       # 12ヶ月使用
        )
        # (100万円 - 10万円) / 5年 = 18万円/年
        assert result["annual_depreciation"] == 180000
        assert result["depreciation"] == 180000

    def test_straight_line_partial_year(self):
        """定額法（月割り）"""
        result = self.calc.calculate_depreciation(
            Decimal("1000000"),
            useful_life=5,
            method="定額法",
            months_used=6  # 6ヶ月使用
        )
        # 18万円 * 6/12 = 9万円
        assert result["depreciation"] == 90000

    def test_declining_balance_method(self):
        """定率法"""
        result = self.calc.calculate_depreciation(
            Decimal("1000000"),
            useful_life=5,
            method="定率法",
            months_used=12
        )
        # 200%定率法: 100万円 * (2/5) = 40万円
        assert result["annual_depreciation"] == 400000


class TestDeductions:
    """各種控除計算テスト"""

    def setup_method(self):
        self.calc = TaxCalculator()

    def test_basic_deduction_standard(self):
        """基礎控除（通常）"""
        deduction = self.calc.calculate_basic_deduction(Decimal("5000000"))
        assert deduction == Decimal("480000")  # 48万円

    def test_basic_deduction_high_income(self):
        """基礎控除（高所得）"""
        deduction = self.calc.calculate_basic_deduction(Decimal("25000000"))
        assert deduction == Decimal("160000")  # 16万円

    def test_basic_deduction_very_high_income(self):
        """基礎控除（超高所得）"""
        deduction = self.calc.calculate_basic_deduction(Decimal("30000000"))
        assert deduction == Decimal("0")  # 控除なし

    def test_blue_return_deduction_e_filing(self):
        """青色申告特別控除（e-Tax + 複式簿記）"""
        deduction = self.calc.calculate_blue_return_deduction(
            Decimal("5000000"),
            has_e_filing=True,
            has_double_entry=True
        )
        assert deduction == Decimal("650000")  # 65万円

    def test_blue_return_deduction_no_e_filing(self):
        """青色申告特別控除（複式簿記のみ）"""
        deduction = self.calc.calculate_blue_return_deduction(
            Decimal("5000000"),
            has_e_filing=False,
            has_double_entry=True
        )
        assert deduction == Decimal("550000")  # 55万円

    def test_blue_return_deduction_simple(self):
        """青色申告特別控除（簡易簿記）"""
        deduction = self.calc.calculate_blue_return_deduction(
            Decimal("5000000"),
            has_e_filing=False,
            has_double_entry=False
        )
        assert deduction == Decimal("100000")  # 10万円


class TestAnnualTaxEstimate:
    """年間税額概算テスト"""

    def setup_method(self):
        self.calc = TaxCalculator()

    def test_estimate_with_profit(self):
        """黒字の場合"""
        result = self.calc.estimate_annual_tax(
            Decimal("10000000"),  # 売上1000万円
            Decimal("5000000"),   # 経費500万円
            has_e_filing=True
        )
        
        assert result["売上"] == 10000000
        assert result["経費"] == 5000000
        assert result["事業所得"] == 5000000
        assert result["所得税"] > 0
        assert result["住民税（概算）"] > 0

    def test_estimate_no_business_tax(self):
        """事業税なし（290万円以下）"""
        result = self.calc.estimate_annual_tax(
            Decimal("4000000"),  # 売上400万円
            Decimal("2000000"),  # 経費200万円
        )
        # 事業所得200万円は290万円以下なので事業税なし
        assert result["個人事業税（概算）"] == 0

    def test_estimate_with_business_tax(self):
        """事業税あり（290万円超）"""
        result = self.calc.estimate_annual_tax(
            Decimal("10000000"),  # 売上1000万円
            Decimal("3000000"),   # 経費300万円
        )
        # 事業所得700万円 - 290万円 = 410万円 * 5%
        assert result["個人事業税（概算）"] == 205000
