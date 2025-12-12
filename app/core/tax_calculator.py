"""
税務計算エンジン
所得税、消費税、減価償却費の計算
"""

from decimal import Decimal, ROUND_DOWN
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class TaxCalculator:
    """税務計算エンジン"""

    # 所得税率表（2024年時点）
    INCOME_TAX_BRACKETS = [
        (Decimal("1950000"), Decimal("0.05"), Decimal("0")),
        (Decimal("3300000"), Decimal("0.10"), Decimal("97500")),
        (Decimal("6950000"), Decimal("0.20"), Decimal("427500")),
        (Decimal("9000000"), Decimal("0.23"), Decimal("636000")),
        (Decimal("18000000"), Decimal("0.33"), Decimal("1536000")),
        (Decimal("40000000"), Decimal("0.40"), Decimal("2796000")),
        (Decimal("999999999999"), Decimal("0.45"), Decimal("4796000")),
    ]

    # 簡易課税のみなし仕入率
    SIMPLIFIED_TAX_RATES = {
        "第1種": Decimal("0.90"),  # 卸売業
        "第2種": Decimal("0.80"),  # 小売業
        "第3種": Decimal("0.70"),  # 製造業等
        "第4種": Decimal("0.60"),  # その他
        "第5種": Decimal("0.50"),  # サービス業等
        "第6種": Decimal("0.40"),  # 不動産業
    }

    def calculate_income_tax(self, taxable_income: Decimal) -> Dict:
        """
        所得税計算（累進課税）
        """
        income = Decimal(str(taxable_income))

        if income <= 0:
            return {
                "taxable_income": 0,
                "income_tax": 0,
                "reconstruction_tax": 0,
                "total_tax": 0,
                "tax_rate": 0,
            }

        # 税率表から計算
        income_tax = Decimal("0")
        applied_rate = Decimal("0")

        for threshold, rate, deduction in self.INCOME_TAX_BRACKETS:
            if income <= threshold:
                income_tax = income * rate - deduction
                applied_rate = rate
                break

        # 負の税額は0に
        if income_tax < 0:
            income_tax = Decimal("0")

        # 復興特別所得税 2.1%
        reconstruction_tax = (income_tax * Decimal("0.021")).quantize(
            Decimal("1"), rounding=ROUND_DOWN
        )
        total_tax = income_tax + reconstruction_tax

        return {
            "taxable_income": float(income),
            "income_tax": float(income_tax.quantize(Decimal("1"), rounding=ROUND_DOWN)),
            "reconstruction_tax": float(reconstruction_tax),
            "total_tax": float(total_tax.quantize(Decimal("1"), rounding=ROUND_DOWN)),
            "tax_rate": float(applied_rate),
        }

    def calculate_consumption_tax(
        self,
        sales_tax: Decimal,
        purchase_tax: Decimal,
        method: str = "原則課税",
        business_type: str = "第5種",
    ) -> Dict:
        """
        消費税計算
        """
        sales = Decimal(str(sales_tax))
        purchase = Decimal(str(purchase_tax))

        if method == "原則課税":
            # 原則課税: 売上消費税 - 仕入消費税
            payable_tax = sales - purchase
        else:
            # 簡易課税
            deemed_rate = self.SIMPLIFIED_TAX_RATES.get(business_type, Decimal("0.50"))
            deemed_purchase = sales * deemed_rate
            payable_tax = sales - deemed_purchase

        # 負の税額（還付）も許容
        return {
            "sales_tax": float(sales),
            "purchase_tax": float(purchase),
            "payable_tax": float(payable_tax.quantize(Decimal("1"), rounding=ROUND_DOWN)),
            "method": method,
            "is_refund": payable_tax < 0,
        }

    def calculate_depreciation(
        self,
        acquisition_cost: Decimal,
        useful_life: int,
        method: str = "定額法",
        months_used: int = 12,
        salvage_rate: Decimal = Decimal("0.10"),
    ) -> Dict:
        """
        減価償却費計算
        """
        cost = Decimal(str(acquisition_cost))

        if method == "定額法":
            # 定額法: (取得価額 - 残存価額) / 耐用年数
            salvage_value = cost * salvage_rate
            depreciable_amount = cost - salvage_value
            annual_depreciation = depreciable_amount / Decimal(str(useful_life))
            depreciation = annual_depreciation * Decimal(str(months_used)) / Decimal("12")

        elif method == "定率法":
            # 200%定率法
            rate = Decimal("2") / Decimal(str(useful_life))
            # 簡易的に初年度計算
            annual_depreciation = cost * rate
            depreciation = annual_depreciation * Decimal(str(months_used)) / Decimal("12")

        else:
            depreciation = Decimal("0")

        return {
            "acquisition_cost": float(cost),
            "useful_life": useful_life,
            "method": method,
            "annual_depreciation": float(
                annual_depreciation.quantize(Decimal("1"), rounding=ROUND_DOWN)
            ),
            "depreciation": float(
                depreciation.quantize(Decimal("1"), rounding=ROUND_DOWN)
            ),
            "months_used": months_used,
        }

    def calculate_blue_return_deduction(
        self,
        income: Decimal,
        has_e_filing: bool = False,
        has_double_entry: bool = True,
    ) -> Decimal:
        """
        青色申告特別控除計算
        """
        income_val = Decimal(str(income))

        if has_double_entry and has_e_filing:
            max_deduction = Decimal("650000")  # 65万円
        elif has_double_entry:
            max_deduction = Decimal("550000")  # 55万円
        else:
            max_deduction = Decimal("100000")  # 10万円

        return min(income_val, max_deduction)

    def calculate_basic_deduction(self, total_income: Decimal) -> Decimal:
        """
        基礎控除計算（2020年改正後）
        """
        income = Decimal(str(total_income))

        if income <= Decimal("24000000"):
            return Decimal("480000")  # 48万円
        elif income <= Decimal("24500000"):
            return Decimal("320000")  # 32万円
        elif income <= Decimal("25000000"):
            return Decimal("160000")  # 16万円
        else:
            return Decimal("0")  # 控除なし

    def calculate_all_deductions(
        self,
        total_income: Decimal,
        social_insurance: Decimal = Decimal("0"),
        small_business_mutual: Decimal = Decimal("0"),
        life_insurance: Decimal = Decimal("0"),
        medical_expense: Decimal = Decimal("0"),
        has_e_filing: bool = False,
        has_double_entry: bool = True,
    ) -> Dict:
        """
        各種控除の一括計算
        """
        income = Decimal(str(total_income))

        # 基礎控除
        basic = self.calculate_basic_deduction(income)

        # 青色申告特別控除
        blue_return = self.calculate_blue_return_deduction(
            income, has_e_filing, has_double_entry
        )

        # 社会保険料控除（全額控除）
        social = Decimal(str(social_insurance))

        # 小規模企業共済等掛金控除（全額控除）
        small_biz = Decimal(str(small_business_mutual))

        # 生命保険料控除（上限12万円）
        life = min(Decimal(str(life_insurance)), Decimal("120000"))

        # 医療費控除（10万円または所得5%の低い方を超えた額）
        medical = Decimal(str(medical_expense))
        medical_threshold = min(Decimal("100000"), income * Decimal("0.05"))
        medical_deduction = max(Decimal("0"), medical - medical_threshold)
        medical_deduction = min(medical_deduction, Decimal("2000000"))  # 上限200万円

        total_deductions = basic + blue_return + social + small_biz + life + medical_deduction

        return {
            "基礎控除": float(basic),
            "青色申告特別控除": float(blue_return),
            "社会保険料控除": float(social),
            "小規模企業共済等掛金控除": float(small_biz),
            "生命保険料控除": float(life),
            "医療費控除": float(medical_deduction),
            "控除合計": float(total_deductions),
        }

    def estimate_annual_tax(
        self,
        estimated_sales: Decimal,
        estimated_expenses: Decimal,
        has_e_filing: bool = True,
    ) -> Dict:
        """
        年間税額の概算
        """
        sales = Decimal(str(estimated_sales))
        expenses = Decimal(str(estimated_expenses))

        # 事業所得
        business_income = sales - expenses

        # 控除
        deductions = self.calculate_all_deductions(
            business_income, has_e_filing=has_e_filing
        )

        # 課税所得
        taxable_income = business_income - Decimal(str(deductions["控除合計"]))
        if taxable_income < 0:
            taxable_income = Decimal("0")

        # 所得税
        income_tax = self.calculate_income_tax(taxable_income)

        # 住民税（概算10%）
        resident_tax = float(taxable_income * Decimal("0.10"))

        # 個人事業税（概算5%、290万円控除後）
        business_tax_base = business_income - Decimal("2900000")
        if business_tax_base > 0:
            business_tax = float(business_tax_base * Decimal("0.05"))
        else:
            business_tax = 0

        return {
            "売上": float(sales),
            "経費": float(expenses),
            "事業所得": float(business_income),
            "控除合計": deductions["控除合計"],
            "課税所得": float(taxable_income),
            "所得税": income_tax["total_tax"],
            "住民税（概算）": resident_tax,
            "個人事業税（概算）": business_tax,
            "税金合計（概算）": income_tax["total_tax"] + resident_tax + business_tax,
        }


tax_calculator = TaxCalculator()
