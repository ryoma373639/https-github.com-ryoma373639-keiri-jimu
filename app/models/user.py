"""
ユーザーモデル
"""

from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.models.database import Base


class User(Base):
    """ユーザーテーブル"""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    line_user_id = Column(String(100), unique=True, nullable=False, index=True)
    business_name = Column(String(100))
    business_type = Column(String(50), default="個人事業主")
    fiscal_year_end = Column(String(5), default="12-31")
    tax_calculation_method = Column(String(20), default="原則課税")
    blue_return_eligible = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    settings = Column(JSONB, default={})

    # リレーションシップ
    transactions = relationship("Transaction", back_populates="user")
    clients = relationship("Client", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, line_user_id={self.line_user_id})>"
