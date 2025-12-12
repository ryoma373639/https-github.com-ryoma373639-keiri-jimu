"""
LINE Webhook処理
"""

from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks
from linebot import WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent,
    TextMessage,
    ImageMessage,
    AudioMessage,
)
from sqlalchemy.orm import Session
import logging

from app.config import settings
from app.models.database import get_db, SessionLocal
from app.core.accounting_engine import accounting_engine
from app.services.line_service import line_service

logger = logging.getLogger(__name__)

router = APIRouter()

# LINE Webhook Handler
handler = WebhookHandler(settings.LINE_CHANNEL_SECRET) if settings.LINE_CHANNEL_SECRET else None


def process_message(user_id: str, text: str):
    """メッセージ処理（バックグラウンドタスク）"""
    db = SessionLocal()
    try:
        logger.info(f"Processing message from {user_id}: {text}")

        # Claudeで解析
        result = accounting_engine.parse_natural_language(text, user_id)

        if result.get("error"):
            line_service.send_text_message(user_id, result.get("clarification_question", "エラーが発生しました"))
            return

        if result.get("clarification_needed"):
            # 確認が必要な場合
            line_service.send_text_message(user_id, result["clarification_question"])
        else:
            # 仕訳生成
            transaction = accounting_engine.create_journal_entry(result, db)

            # 確認メッセージ送信
            line_service.send_confirmation_message(
                user_id,
                {
                    "debit_account": transaction.debit_account,
                    "credit_account": transaction.credit_account,
                    "amount": float(transaction.debit_amount),
                    "description": transaction.description,
                },
            )

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        line_service.send_text_message(user_id, "エラーが発生しました。もう一度お試しください。")
    finally:
        db.close()


@router.post("/line")
async def line_webhook(request: Request, background_tasks: BackgroundTasks):
    """LINE Webhookエンドポイント"""
    if not handler:
        raise HTTPException(status_code=500, detail="LINE handler not configured")

    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    body_text = body.decode("utf-8")

    logger.info(f"Received webhook: {body_text[:200]}...")

    try:
        handler.handle(body_text, signature)
    except InvalidSignatureError:
        logger.error("Invalid signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    return "OK"


if handler:

    @handler.add(MessageEvent, message=TextMessage)
    def handle_text_message(event):
        """テキストメッセージ処理"""
        user_id = event.source.user_id
        text = event.message.text

        logger.info(f"Received text message from {user_id}: {text}")

        # 簡易コマンド処理
        if text.strip().lower() in ["help", "ヘルプ", "使い方"]:
            help_message = """【使い方】

経費登録:
「タクシー3200円」
「スタバでコーヒー550円」

売上登録:
「A社から50万円入金」
「コンサル料10万円」

レポート:
「今月の売上」
「経費一覧」

質問:
「消費税の計算方法は？」
"""
            line_service.send_text_message(user_id, help_message)
            return

        # バックグラウンドで処理
        from threading import Thread

        Thread(target=process_message, args=(user_id, text)).start()

    @handler.add(MessageEvent, message=ImageMessage)
    def handle_image_message(event):
        """画像メッセージ処理（レシートOCR）"""
        user_id = event.source.user_id
        message_id = event.message.id

        logger.info(f"Received image message from {user_id}: {message_id}")

        # TODO: OCRサービス連携
        line_service.send_text_message(
            user_id, "レシート画像を受け取りました。OCR機能は準備中です。"
        )

    @handler.add(MessageEvent, message=AudioMessage)
    def handle_audio_message(event):
        """音声メッセージ処理"""
        user_id = event.source.user_id
        message_id = event.message.id

        logger.info(f"Received audio message from {user_id}: {message_id}")

        # TODO: 音声認識サービス連携
        line_service.send_text_message(
            user_id, "音声メッセージを受け取りました。音声認識機能は準備中です。"
        )
