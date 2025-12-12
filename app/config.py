"""
アプリケーション設定を管理
環境変数から設定を読み込む
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """アプリケーション設定"""

    # データベース
    DATABASE_URL: str = "postgresql://postgres:password@db:5432/accounting_db"

    # LINE
    LINE_CHANNEL_ACCESS_TOKEN: str = ""
    LINE_CHANNEL_SECRET: str = ""

    # Claude API
    CLAUDE_API_KEY: str = ""

    # OCR
    GOOGLE_CLOUD_VISION_API_KEY: Optional[str] = None

    # 音声認識
    OPENAI_API_KEY: Optional[str] = None

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Celery
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    # アプリケーション
    APP_NAME: str = "LINE会計AGI"
    DEBUG: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
