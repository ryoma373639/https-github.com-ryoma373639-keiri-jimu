"""
LINE Messaging API連携サービス
"""

from linebot import LineBotApi
from linebot.models import TextSendMessage, QuickReply, QuickReplyButton, MessageAction
from app.config import settings
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class LineService:
    """LINE Messaging API連携サービス"""

    def __init__(self):
        self.line_bot_api = None
        if settings.LINE_CHANNEL_ACCESS_TOKEN:
            self.line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)

    def send_text_message(self, user_id: str, text: str):
        """テキストメッセージ送信"""
        if not self.line_bot_api:
            logger.warning(f"LINE API not configured. Message to {user_id}: {text}")
            return

        try:
            self.line_bot_api.push_message(user_id, TextSendMessage(text=text))
            logger.info(f"Message sent to {user_id}")
        except Exception as e:
            logger.error(f"Failed to send message: {e}")

    def send_confirmation_message(self, user_id: str, transaction: Dict):
        """取引登録確認メッセージ"""
        message = f"""取引を登録しました。

【仕訳内容】
借方: {transaction['debit_account']} {transaction['amount']:,.0f}円
貸方: {transaction['credit_account']} {transaction['amount']:,.0f}円
摘要: {transaction.get('description', '')}

修正が必要な場合は「修正」と入力してください。
"""
        self.send_text_message(user_id, message)

    def send_clarification_question(self, user_id: str, question: str, options: List[str]):
        """確認質問の送信（クイックリプライ使用）"""
        if not self.line_bot_api:
            logger.warning(f"LINE API not configured. Question to {user_id}: {question}")
            return

        try:
            quick_reply_buttons = [
                QuickReplyButton(action=MessageAction(label=option[:20], text=option))
                for option in options[:13]  # 最大13個
            ]

            self.line_bot_api.push_message(
                user_id,
                TextSendMessage(
                    text=question, quick_reply=QuickReply(items=quick_reply_buttons)
                ),
            )
            logger.info(f"Clarification question sent to {user_id}")
        except Exception as e:
            logger.error(f"Failed to send clarification question: {e}")

    def send_report(self, user_id: str, report_text: str, report_type: str = "月次"):
        """レポート送信"""
        header = f"📊 【{report_type}レポート】\n\n"
        self.send_text_message(user_id, header + report_text)

    def send_reminder(self, user_id: str, title: str, description: str, due_date: str):
        """リマインダー送信"""
        message = f"""⏰ 【リマインダー】

{title}

{description}

期限: {due_date}
"""
        self.send_text_message(user_id, message)


line_service = LineService()
