"""
pytest共通設定
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.models.database import Base, get_db
from app.main import app


# テスト用インメモリデータベース
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """テスト用DBセッション"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """テスト用FastAPIクライアント"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def mock_claude_service():
    """Claude APIモック"""
    with patch("app.services.claude_service.claude_service") as mock:
        mock.analyze_transaction.return_value = {
            "transaction_type": "expense",
            "amount": 1000,
            "debit_account": "旅費交通費",
            "credit_account": "現金",
            "description": "テスト経費",
            "confidence": 0.9,
        }
        yield mock


@pytest.fixture
def mock_line_service():
    """LINE APIモック"""
    with patch("app.services.line_service.line_service") as mock:
        mock.send_text_message.return_value = True
        mock.send_flex_message.return_value = True
        mock.get_message_content.return_value = b"fake_content"
        yield mock


@pytest.fixture
def mock_ocr_service():
    """OCRサービスモック"""
    with patch("app.services.ocr_service.ocr_service") as mock:
        mock.process_receipt_image.return_value = {
            "store_name": "テスト店",
            "total_amount": 1000,
            "date": "2024-01-15",
            "items": [],
            "tax_amount": 100,
        }
        yield mock


@pytest.fixture
def sample_user(db_session):
    """サンプルユーザー"""
    from app.models.user import User
    
    user = User(
        line_user_id="test_user_123",
        display_name="テストユーザー",
        business_type="個人事業主",
        fiscal_year_start=1,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_transactions(db_session, sample_user):
    """サンプル取引データ"""
    from app.models.transaction import Transaction
    from datetime import date
    
    transactions = [
        Transaction(
            user_id=sample_user.id,
            transaction_date=date(2024, 1, 15),
            debit_account="旅費交通費",
            debit_amount=1000,
            credit_account="現金",
            credit_amount=1000,
            description="電車代",
            tax_type="課税仕入10%",
        ),
        Transaction(
            user_id=sample_user.id,
            transaction_date=date(2024, 1, 20),
            debit_account="普通預金",
            debit_amount=100000,
            credit_account="売上高",
            credit_amount=100000,
            description="A社からの入金",
            tax_type="課税売上10%",
        ),
    ]
    
    for tx in transactions:
        db_session.add(tx)
    db_session.commit()
    
    return transactions
