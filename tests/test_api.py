"""
APIエンドポイントのテスト
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import json
import hmac
import hashlib
import base64

from app.main import app
from app.config import settings


@pytest.fixture
def client():
    """テストクライアント"""
    return TestClient(app)


class TestHealthEndpoints:
    """ヘルスチェックエンドポイントテスト"""

    def test_health_check(self, client):
        """基本ヘルスチェック"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data

    def test_health_detailed(self, client):
        """詳細ヘルスチェック"""
        response = client.get("/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert "database" in data
        assert "redis" in data


class TestLINEWebhook:
    """LINE Webhookテスト"""

    def _create_signature(self, body: str) -> str:
        """署名生成"""
        secret = settings.LINE_CHANNEL_SECRET.encode("utf-8")
        hash_obj = hmac.new(secret, body.encode("utf-8"), hashlib.sha256)
        return base64.b64encode(hash_obj.digest()).decode("utf-8")

    @patch("app.api.line_webhook.accounting_engine")
    @patch("app.api.line_webhook.line_service")
    def test_text_message_webhook(self, mock_line, mock_engine, client):
        """テキストメッセージ受信"""
        mock_engine.process_user_input.return_value = {
            "success": True,
            "message": "仕訳を登録しました",
        }

        body = json.dumps({
            "events": [{
                "type": "message",
                "replyToken": "test_token",
                "source": {"userId": "test_user_123", "type": "user"},
                "message": {"type": "text", "text": "電車代500円"}
            }]
        })

        signature = self._create_signature(body)
        
        response = client.post(
            "/webhook",
            content=body,
            headers={
                "X-Line-Signature": signature,
                "Content-Type": "application/json"
            }
        )

        assert response.status_code == 200

    def test_webhook_invalid_signature(self, client):
        """不正な署名"""
        body = json.dumps({
            "events": [{
                "type": "message",
                "source": {"userId": "test_user"},
                "message": {"type": "text", "text": "テスト"}
            }]
        })

        response = client.post(
            "/webhook",
            content=body,
            headers={
                "X-Line-Signature": "invalid_signature",
                "Content-Type": "application/json"
            }
        )

        assert response.status_code == 400

    @patch("app.api.line_webhook.ocr_service")
    @patch("app.api.line_webhook.line_service")
    def test_image_message_webhook(self, mock_line, mock_ocr, client):
        """画像メッセージ受信（レシートOCR）"""
        mock_line.get_message_content.return_value = b"fake_image_data"
        mock_ocr.process_receipt_image.return_value = {
            "store_name": "テスト店",
            "total_amount": 1000,
            "date": "2024-01-15",
        }

        body = json.dumps({
            "events": [{
                "type": "message",
                "replyToken": "test_token",
                "source": {"userId": "test_user_123", "type": "user"},
                "message": {"type": "image", "id": "image_123"}
            }]
        })

        signature = self._create_signature(body)
        
        response = client.post(
            "/webhook",
            content=body,
            headers={
                "X-Line-Signature": signature,
                "Content-Type": "application/json"
            }
        )

        assert response.status_code == 200


class TestRootEndpoint:
    """ルートエンドポイントテスト"""

    def test_root(self, client):
        """ルートエンドポイント"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data


class TestErrorHandling:
    """エラーハンドリングテスト"""

    def test_404_not_found(self, client):
        """存在しないエンドポイント"""
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_method_not_allowed(self, client):
        """許可されていないメソッド"""
        response = client.put("/health")
        assert response.status_code == 405
