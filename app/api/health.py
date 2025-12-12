"""
ヘルスチェックエンドポイント
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import redis

from app.models.database import get_db
from app.config import settings

router = APIRouter()


def check_db_connection(db: Session) -> bool:
    """データベース接続確認"""
    try:
        db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def check_redis_connection() -> bool:
    """Redis接続確認"""
    try:
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        return True
    except Exception:
        return False


@router.get("/")
def health_check(db: Session = Depends(get_db)):
    """ヘルスチェック"""
    db_status = check_db_connection(db)
    redis_status = check_redis_connection()

    status = "healthy" if db_status and redis_status else "unhealthy"

    return {
        "status": status,
        "services": {
            "database": "connected" if db_status else "disconnected",
            "redis": "connected" if redis_status else "disconnected",
        },
    }


@router.get("/ready")
def readiness_check(db: Session = Depends(get_db)):
    """レディネスチェック"""
    db_status = check_db_connection(db)

    if db_status:
        return {"status": "ready"}
    else:
        return {"status": "not ready", "reason": "Database not available"}


@router.get("/live")
def liveness_check():
    """ライブネスチェック"""
    return {"status": "alive"}
