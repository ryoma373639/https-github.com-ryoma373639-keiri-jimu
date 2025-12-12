"""
取引データモデル
"""

from sqlalchemy import Column, String, Numeric, Date, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.models.database import Base


class Transaction(Base):
    """取引データ（仕訳）テーブル"""

    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_date = Column(Date, nullable=False, index=True)
    debit_account = Column(String(50), nullable=False)  # 借方勘定科目
    debit_amount = Column(Numeric(12, 2), nullable=False)  # 借方金額
    credit_account = Column(String(50), nullable=False)  # 貸方勘定科目
    credit_amount = Column(Numeric(12, 2), nullable=False)  # 貸方金額
    description = Column(Text)  # 摘要
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"))
    project_name = Column(String(100))  # プロジェクト名
    tax_type = Column(String(20), nullable=False)  # 課税区分
    tax_amount = Column(Numeric(10, 2), default=0)  # 消費税額
    receipt_image_url = Column(Text)  # レシート画像URL
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_from = Column(String(20), default="LINE")  # 作成元
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # リレーションシップ
    user = relationship("User", back_populates="transactions")
    client = relationship("Client", back_populates="transactions")

    def __repr__(self):
        return f"<Transaction(id={self.id}, date={self.transaction_date}, amount={self.debit_amount})>"
