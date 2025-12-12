"""
勘定科目マスタモデル
"""

from sqlalchemy import Column, String, Numeric, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.models.database import Base


class Account(Base):
    """勘定科目マスタテーブル"""

    __tablename__ = "accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_code = Column(String(10), unique=True, nullable=False)
    account_name = Column(String(50), nullable=False)
    account_type = Column(String(20), nullable=False)  # 資産, 負債, 資本, 収益, 費用
    account_category = Column(String(20))  # 流動資産, 固定資産, 販管費 etc.
    tax_default = Column(String(20), default="課税10%")
    budget_annual = Column(Numeric(12, 2))
    sort_order = Column(Integer)
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<Account(code={self.account_code}, name={self.account_name})>"


# 勘定科目マスタ初期データ
ACCOUNT_MASTER = [
    # 資産
    {"code": "100", "name": "現金", "type": "資産", "category": "流動資産", "tax_default": "不課税"},
    {"code": "101", "name": "普通預金", "type": "資産", "category": "流動資産", "tax_default": "不課税"},
    {"code": "102", "name": "当座預金", "type": "資産", "category": "流動資産", "tax_default": "不課税"},
    {"code": "110", "name": "売掛金", "type": "資産", "category": "流動資産", "tax_default": "不課税"},
    {"code": "111", "name": "受取手形", "type": "資産", "category": "流動資産", "tax_default": "不課税"},
    {"code": "120", "name": "前払金", "type": "資産", "category": "流動資産", "tax_default": "課税10%"},
    {"code": "130", "name": "貯蔵品", "type": "資産", "category": "流動資産", "tax_default": "課税10%"},
    {"code": "200", "name": "建物", "type": "資産", "category": "固定資産", "tax_default": "課税10%"},
    {"code": "201", "name": "車両運搬具", "type": "資産", "category": "固定資産", "tax_default": "課税10%"},
    {"code": "202", "name": "工具器具備品", "type": "資産", "category": "固定資産", "tax_default": "課税10%"},
    {"code": "203", "name": "ソフトウェア", "type": "資産", "category": "固定資産", "tax_default": "課税10%"},
    # 負債
    {"code": "300", "name": "買掛金", "type": "負債", "category": "流動負債", "tax_default": "不課税"},
    {"code": "301", "name": "未払金", "type": "負債", "category": "流動負債", "tax_default": "不課税"},
    {"code": "302", "name": "前受金", "type": "負債", "category": "流動負債", "tax_default": "不課税"},
    {"code": "303", "name": "預り金", "type": "負債", "category": "流動負債", "tax_default": "不課税"},
    {"code": "310", "name": "短期借入金", "type": "負債", "category": "流動負債", "tax_default": "不課税"},
    {"code": "320", "name": "長期借入金", "type": "負債", "category": "固定負債", "tax_default": "不課税"},
    # 資本
    {"code": "400", "name": "元入金", "type": "資本", "category": "資本", "tax_default": "不課税"},
    {"code": "401", "name": "事業主借", "type": "資本", "category": "資本", "tax_default": "不課税"},
    {"code": "402", "name": "事業主貸", "type": "資本", "category": "資本", "tax_default": "不課税"},
    # 収益
    {"code": "500", "name": "売上高", "type": "収益", "category": "営業収益", "tax_default": "課税10%"},
    {"code": "510", "name": "雑収入", "type": "収益", "category": "営業外収益", "tax_default": "課税10%"},
    {"code": "511", "name": "受取利息", "type": "収益", "category": "営業外収益", "tax_default": "非課税"},
    # 費用
    {"code": "600", "name": "仕入高", "type": "費用", "category": "売上原価", "tax_default": "課税10%"},
    {"code": "610", "name": "外注費", "type": "費用", "category": "販管費", "tax_default": "課税10%"},
    {"code": "620", "name": "給料賃金", "type": "費用", "category": "販管費", "tax_default": "不課税"},
    {"code": "630", "name": "地代家賃", "type": "費用", "category": "販管費", "tax_default": "非課税"},
    {"code": "640", "name": "水道光熱費", "type": "費用", "category": "販管費", "tax_default": "課税10%"},
    {"code": "650", "name": "通信費", "type": "費用", "category": "販管費", "tax_default": "課税10%"},
    {"code": "660", "name": "旅費交通費", "type": "費用", "category": "販管費", "tax_default": "課税10%"},
    {"code": "670", "name": "接待交際費", "type": "費用", "category": "販管費", "tax_default": "課税10%"},
    {"code": "680", "name": "消耗品費", "type": "費用", "category": "販管費", "tax_default": "課税10%"},
    {"code": "690", "name": "減価償却費", "type": "費用", "category": "販管費", "tax_default": "不課税"},
    {"code": "700", "name": "租税公課", "type": "費用", "category": "販管費", "tax_default": "不課税"},
    {"code": "710", "name": "支払利息", "type": "費用", "category": "営業外費用", "tax_default": "非課税"},
    {"code": "720", "name": "雑費", "type": "費用", "category": "販管費", "tax_default": "課税10%"},
    {"code": "730", "name": "広告宣伝費", "type": "費用", "category": "販管費", "tax_default": "課税10%"},
    {"code": "740", "name": "研修費", "type": "費用", "category": "販管費", "tax_default": "課税10%"},
    {"code": "750", "name": "新聞図書費", "type": "費用", "category": "販管費", "tax_default": "課税8%"},
    {"code": "760", "name": "支払手数料", "type": "費用", "category": "販管費", "tax_default": "課税10%"},
]
