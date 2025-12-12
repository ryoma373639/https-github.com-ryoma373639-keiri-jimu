"""
取引先マスタモデル
"""

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.models.database import Base


class Client(Base):
    """取引先マスタテーブル"""

    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_name = Column(String(100), nullable=False)
    client_type = Column(String(20), nullable=False)  # 顧客, 仕入先, 両方
    invoice_number = Column(String(20))  # インボイス番号
    payment_terms = Column(String(50))  # 支払条件
    contact_email = Column(String(100))
    contact_phone = Column(String(20))
    line_user_id = Column(String(100))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # リレーションシップ
    user = relationship("User", back_populates="clients")
    transactions = relationship("Transaction", back_populates="client")

    def __repr__(self):
        return f"<Client(id={self.id}, name={self.client_name})>"
