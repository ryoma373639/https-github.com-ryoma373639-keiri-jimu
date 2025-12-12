"""
Claude API連携サービス
自然言語解析、仕訳判定、税務相談を実行
"""

import anthropic
from app.config import settings
import json
from typing import Dict, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ClaudeService:
    """Claude API連携サービス"""

    def __init__(self):
        self.client = None
        if settings.CLAUDE_API_KEY:
            self.client = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY)
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        return """
あなたは完全自動経理AGIです。

【役割】
1. ユーザーの入力から取引情報を抽出
2. 適切な勘定科目を判定
3. 仕訳データをJSON形式で出力
4. 税務相談に回答

【出力形式】
必ず以下のJSON形式のみを出力してください（他の文章は不要）:
{
    "transaction_type": "expense/income/transfer",
    "date": "YYYY-MM-DD",
    "amount": 金額(数値),
    "debit_account": "借方勘定科目",
    "credit_account": "貸方勘定科目",
    "description": "摘要",
    "client": "取引先名(あれば)",
    "project": "プロジェクト名(あれば)",
    "tax_type": "課税10%/課税8%/非課税/不課税",
    "confidence": 0-1の確信度,
    "clarification_needed": true/false,
    "clarification_question": "確認が必要な場合の質問"
}

【勘定科目判定ルール】
経費系:
- タクシー、電車、バス、Uber → 旅費交通費
- カフェ、レストラン(取引先と) → 接待交際費
- Amazon、文房具、事務用品 → 消耗品費
- 広告、マーケティング、SNS広告 → 広告宣伝費
- サーバー、ドメイン、SaaS、クラウド → 通信費
- 家賃、駐車場、倉庫 → 地代家賃
- 電気、ガス、水道 → 水道光熱費
- 受講料、セミナー、研修 → 研修費
- 書籍、Kindle、オンライン教材 → 新聞図書費
- 外注、業務委託、フリーランス → 外注費
- ホテル、宿泊 → 旅費交通費
- クリーニング → 雑費
- 振込手数料 → 支払手数料
- 税金、印紙 → 租税公課

収入系:
- 売上、コンサル料、受講料、報酬 → 売上高
- 利息、配当 → 受取利息
- その他収入 → 雑収入

【消費税判定ルール】
- 課税10%: 通常の商品・サービス
- 課税8%: 飲食料品(外食除く)、定期購読新聞
- 非課税: 土地取引、住宅家賃、有価証券、郵便切手、社会保険診療、介護保険サービス
- 不課税: 給与、寄付金、海外取引、配当金、保険金

【日付推定】
- 「今日」「さっき」「先ほど」→ 今日の日付
- 「昨日」→ 昨日の日付
- 「○日」→ 今月の○日
- 日付明示なし → 今日の日付

【金額抽出】
- 「3200円」「3,200円」「3200」→ 3200
- 「50万」「50万円」→ 500000
- 「5000円くらい」→ 5000
"""

    def analyze_transaction(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        """
        ユーザー入力を解析して取引データを抽出
        """
        if not self.client:
            logger.warning("Claude API not configured, using mock response")
            return self._mock_analysis(user_input)

        try:
            # 現在日時をコンテキストに追加
            current_date = datetime.now().strftime("%Y-%m-%d")

            prompt = f"""
今日の日付: {current_date}

ユーザー入力: {user_input}

上記の入力から取引情報を抽出し、JSON形式で出力してください。
"""

            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                system=self.system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = message.content[0].text
            logger.info(f"Claude response: {response_text}")

            # JSONパース
            result = json.loads(response_text)
            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return {
                "error": "応答の解析に失敗しました",
                "clarification_needed": True,
                "clarification_question": "もう一度詳しく教えていただけますか？",
            }
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return {
                "error": str(e),
                "clarification_needed": True,
                "clarification_question": "エラーが発生しました。もう一度お試しください。",
            }

    def _mock_analysis(self, user_input: str) -> Dict:
        """モック解析（APIキー未設定時）"""
        # 簡易的なルールベース解析
        today = datetime.now().strftime("%Y-%m-%d")

        # 金額抽出
        import re

        amount_match = re.search(r"(\d+(?:,\d+)?)\s*円", user_input)
        amount = int(amount_match.group(1).replace(",", "")) if amount_match else 1000

        # キーワードベースで勘定科目判定
        keywords_map = {
            "タクシー": ("旅費交通費", "expense"),
            "電車": ("旅費交通費", "expense"),
            "バス": ("旅費交通費", "expense"),
            "カフェ": ("接待交際費", "expense"),
            "スタバ": ("接待交際費", "expense"),
            "Amazon": ("消耗品費", "expense"),
            "売上": ("売上高", "income"),
            "入金": ("売上高", "income"),
        }

        debit = "消耗品費"
        credit = "現金"
        trans_type = "expense"

        for keyword, (account, t_type) in keywords_map.items():
            if keyword in user_input:
                if t_type == "expense":
                    debit = account
                    credit = "現金"
                else:
                    debit = "普通預金"
                    credit = account
                trans_type = t_type
                break

        return {
            "transaction_type": trans_type,
            "date": today,
            "amount": amount,
            "debit_account": debit,
            "credit_account": credit,
            "description": user_input[:50],
            "tax_type": "課税10%",
            "confidence": 0.7,
            "clarification_needed": False,
        }

    def answer_tax_question(self, question: str, user_context: Optional[Dict] = None) -> str:
        """
        税務相談に回答
        """
        if not self.client:
            return "税務相談機能を使用するにはClaude APIキーの設定が必要です。"

        try:
            system = """
あなたは日本の税務に詳しい経理AIアシスタントです。
税法に基づいた正確な回答を、わかりやすく説明してください。
不確実な場合は、税理士への相談を推奨してください。
"""

            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                system=system,
                messages=[{"role": "user", "content": question}],
            )

            return message.content[0].text

        except Exception as e:
            logger.error(f"Tax consultation error: {e}")
            return "申し訳ございません。回答の生成に失敗しました。"


claude_service = ClaudeService()
