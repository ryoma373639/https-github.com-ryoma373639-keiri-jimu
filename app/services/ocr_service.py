"""
Google Cloud Vision OCRサービス
レシート画像からテキストを抽出
"""

from app.config import settings
from typing import Dict, Optional
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class OCRService:
    """OCRサービス"""

    def __init__(self):
        self.client = None
        if settings.GOOGLE_CLOUD_VISION_API_KEY:
            try:
                from google.cloud import vision

                self.client = vision.ImageAnnotatorClient()
            except Exception as e:
                logger.warning(f"Google Cloud Vision not available: {e}")

    def extract_text_from_image(self, image_content: bytes) -> str:
        """画像からテキストを抽出"""
        if not self.client:
            logger.warning("OCR client not configured")
            return ""

        try:
            from google.cloud import vision

            image = vision.Image(content=image_content)
            response = self.client.text_detection(image=image)

            if response.error.message:
                raise Exception(f"OCR Error: {response.error.message}")

            texts = response.text_annotations
            if texts:
                return texts[0].description
            return ""
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return ""

    def parse_receipt(self, text: str) -> Dict:
        """レシートテキストから情報を抽出"""
        result = {
            "store_name": None,
            "date": None,
            "total_amount": None,
            "items": [],
            "tax_amount": None,
            "payment_method": None,
            "raw_text": text,
        }

        if not text:
            return result

        lines = text.split("\n")

        # 店舗名（最初の行を店名として推定）
        if lines:
            result["store_name"] = lines[0].strip()[:50]

        # 金額パターン（合計、計、Total等）
        amount_patterns = [
            r"合計[:\s]*[¥￥]?\s*([0-9,]+)",
            r"計[:\s]*[¥￥]?\s*([0-9,]+)",
            r"TOTAL[:\s]*[¥￥]?\s*([0-9,]+)",
            r"お会計[:\s]*[¥￥]?\s*([0-9,]+)",
            r"お買上[:\s]*[¥￥]?\s*([0-9,]+)",
            r"小計[:\s]*[¥￥]?\s*([0-9,]+)",
            r"[¥￥]\s*([0-9,]+)\s*$",
        ]

        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                amount_str = match.group(1).replace(",", "")
                try:
                    result["total_amount"] = int(amount_str)
                    break
                except ValueError:
                    continue

        # 日付パターン
        date_patterns = [
            (r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", "%Y-%m-%d"),
            (r"(\d{2})[/-](\d{1,2})[/-](\d{1,2})", "%y-%m-%d"),
            (r"(\d{4})年(\d{1,2})月(\d{1,2})日", "%Y-%m-%d"),
            (r"(\d{2})年(\d{1,2})月(\d{1,2})日", "%y-%m-%d"),
            (r"R(\d)[./](\d{1,2})[./](\d{1,2})", None),  # 令和
        ]

        for pattern, fmt in date_patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                try:
                    if fmt:
                        year = groups[0] if len(groups[0]) == 4 else f"20{groups[0]}"
                        result["date"] = (
                            f"{year}-{int(groups[1]):02d}-{int(groups[2]):02d}"
                        )
                    else:
                        # 令和変換
                        reiwa_year = int(groups[0])
                        year = 2018 + reiwa_year
                        result["date"] = (
                            f"{year}-{int(groups[1]):02d}-{int(groups[2]):02d}"
                        )
                    break
                except (ValueError, IndexError):
                    continue

        # 消費税額
        tax_patterns = [
            r"消費税[:\s]*[¥￥]?\s*([0-9,]+)",
            r"税[:\s]*[¥￥]?\s*([0-9,]+)",
            r"内税[:\s]*[¥￥]?\s*([0-9,]+)",
            r"外税[:\s]*[¥￥]?\s*([0-9,]+)",
        ]

        for pattern in tax_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                tax_str = match.group(1).replace(",", "")
                try:
                    result["tax_amount"] = int(tax_str)
                    break
                except ValueError:
                    continue

        # 支払方法
        payment_methods = {
            "現金": ["現金", "CASH"],
            "クレジットカード": ["クレジット", "CREDIT", "CARD", "カード"],
            "電子マネー": ["電子マネー", "IC", "Suica", "PASMO", "PayPay", "楽天ペイ"],
            "QRコード": ["QR", "LINE Pay", "d払い", "au PAY"],
        }

        for method, keywords in payment_methods.items():
            for keyword in keywords:
                if keyword.lower() in text.lower():
                    result["payment_method"] = method
                    break
            if result["payment_method"]:
                break

        return result

    def process_receipt_image(self, image_content: bytes) -> Dict:
        """レシート画像を処理して経費情報を返す"""
        text = self.extract_text_from_image(image_content)
        receipt_data = self.parse_receipt(text)
        return receipt_data

    def infer_expense_category(self, store_name: str, items: list = None) -> str:
        """店舗名から経費科目を推定"""
        if not store_name:
            return "消耗品費"

        store_lower = store_name.lower()

        # カテゴリ推定ルール
        categories = {
            "旅費交通費": [
                "タクシー",
                "JR",
                "電鉄",
                "バス",
                "駐車場",
                "コインパーキング",
                "ガソリン",
                "ENEOS",
                "出光",
            ],
            "接待交際費": [
                "レストラン",
                "居酒屋",
                "バー",
                "料亭",
                "ホテル",
                "飲食",
            ],
            "消耗品費": [
                "文具",
                "オフィス",
                "Amazon",
                "ヨドバシ",
                "ビックカメラ",
                "100均",
                "ダイソー",
            ],
            "通信費": [
                "NTT",
                "KDDI",
                "ソフトバンク",
                "携帯",
                "インターネット",
            ],
            "新聞図書費": [
                "書店",
                "本屋",
                "紀伊國屋",
                "丸善",
                "ジュンク堂",
                "Amazon Kindle",
            ],
            "研修費": ["セミナー", "研修", "講座", "スクール"],
            "水道光熱費": ["電力", "ガス", "水道"],
        }

        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword.lower() in store_lower:
                    return category

        return "消耗品費"  # デフォルト


ocr_service = OCRService()
