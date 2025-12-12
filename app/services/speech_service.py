"""
OpenAI Whisper音声認識サービス
音声メッセージをテキスト化
"""

import openai
from app.config import settings
import tempfile
import os
import logging

logger = logging.getLogger(__name__)


class SpeechService:
    """音声認識サービス"""

    def __init__(self):
        self.client = None
        if settings.OPENAI_API_KEY:
            openai.api_key = settings.OPENAI_API_KEY
            self.client = openai

    def transcribe_audio(
        self, audio_content: bytes, file_extension: str = "m4a"
    ) -> str:
        """音声をテキストに変換"""
        if not self.client:
            logger.warning("OpenAI client not configured")
            return ""

        # 一時ファイルに保存
        with tempfile.NamedTemporaryFile(
            suffix=f".{file_extension}", delete=False
        ) as temp_file:
            temp_file.write(audio_content)
            temp_file_path = temp_file.name

        try:
            with open(temp_file_path, "rb") as audio_file:
                response = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ja",  # 日本語指定
                    response_format="text",
                )

            return response.strip() if isinstance(response, str) else response.text.strip()
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return ""
        finally:
            # 一時ファイル削除
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass

    def process_voice_message(self, audio_content: bytes) -> dict:
        """音声メッセージを処理"""
        text = self.transcribe_audio(audio_content)

        return {
            "transcribed_text": text,
            "success": bool(text),
            "error": None if text else "音声認識に失敗しました",
        }

    def get_supported_formats(self) -> list:
        """サポートする音声フォーマット"""
        return ["m4a", "mp3", "wav", "webm", "mp4", "mpeg", "mpga", "oga", "ogg"]


speech_service = SpeechService()
