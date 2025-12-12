"""
FastAPIアプリケーションのエントリーポイント
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.api import line_webhook, health
from app.models.database import engine, Base
from app.config import settings

# ログ設定
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフサイクル管理"""
    # 起動時
    logger.info(f"Starting {settings.APP_NAME}...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    yield
    # 終了時
    logger.info(f"Shutting down {settings.APP_NAME}...")


app = FastAPI(
    title=settings.APP_NAME,
    description="LINE一つで全ての経理・事務処理・確定申告を完結させる統合AGI経理システム",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーター登録
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(line_webhook.router, prefix="/webhook", tags=["LINE"])


@app.get("/")
def root():
    """ルートエンドポイント"""
    return {
        "message": f"{settings.APP_NAME} APIサーバー稼働中",
        "version": "1.0.0",
        "docs": "/docs",
    }
