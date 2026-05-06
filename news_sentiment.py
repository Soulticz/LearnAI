from __future__ import annotations

from typing import Any

import yfinance as yf

POSITIVE_KEYWORDS = [
    "beat",
    "beats",
    "growth",
    "surge",
    "rally",
    "strong",
    "bullish",
    "upgrade",
    "record high",
    "ai boom",
    "profit jumps",
    "outperform",
    "optimistic",
    "raises guidance",
    "revenue rises",
    "earnings beat",
]

NEGATIVE_KEYWORDS = [
    "crash",
    "drop",
    "plunge",
    "lawsuit",
    "bearish",
    "downgrade",
    "recession",
    "inflation fear",
    "selloff",
    "weak guidance",
    "rate hike",
    "warning",
    "misses",
    "slump",
    "cuts guidance",
]


def score_news_text(text: str) -> dict[str, Any]:
    text_lower = str(text or "").lower()

    positive_hits = [word for word in POSITIVE_KEYWORDS if word in text_lower]
    negative_hits = [word for word in NEGATIVE_KEYWORDS if word in text_lower]

    score = (len(positive_hits) * 2) - (len(negative_hits) * 2)

    if score >= 4:
        sentiment = "BULLISH"
    elif score <= -4:
        sentiment = "BEARISH"
    else:
        sentiment = "NEUTRAL"

    return {
        "sentiment": sentiment,
        "score": score,
        "positive_hits": positive_hits,
        "negative_hits": negative_hits,
    }


def get_yfinance_news(ticker: str, limit: int = 5) -> list[dict[str, Any]]:
    ticker = str(ticker or "").upper().strip()
    if not ticker:
        return []

    try:
        news = yf.Ticker(ticker).news or []
    except Exception:
        return []

    normalized = []
    for item in news[:limit]:
        content = item.get("content") if isinstance(item, dict) else None

        if isinstance(content, dict):
            title = content.get("title", "")
            summary = content.get("summary", "")
            provider = content.get("provider", {}).get("displayName", "") if isinstance(content.get("provider"), dict) else ""
            url = content.get("canonicalUrl", {}).get("url", "") if isinstance(content.get("canonicalUrl"), dict) else ""
        else:
            title = item.get("title", "") if isinstance(item, dict) else ""
            summary = item.get("summary", "") if isinstance(item, dict) else ""
            provider = item.get("publisher", "") if isinstance(item, dict) else ""
            url = item.get("link", "") if isinstance(item, dict) else ""

        normalized.append({
            "title": title,
            "summary": summary,
            "provider": provider,
            "url": url,
        })

    return normalized


def analyze_ticker_news(ticker: str, limit: int = 5) -> dict[str, Any]:
    news = get_yfinance_news(ticker, limit=limit)
    combined_text = "\n".join(f"{x.get('title', '')} {x.get('summary', '')}" for x in news)
    result = score_news_text(combined_text)
    result["ticker"] = str(ticker or "").upper().strip()
    result["news_count"] = len(news)
    result["headlines"] = [x.get("title", "") for x in news if x.get("title")]
    result["news"] = news
    result["commentary"] = build_news_commentary(result)
    return result


def build_news_commentary(result: dict[str, Any]) -> str:
    sentiment = result.get("sentiment", "NEUTRAL")
    score = result.get("score", 0)
    news_count = result.get("news_count", 0)

    if news_count == 0:
        return "ยังดึงข่าวล่าสุดไม่ได้ หรือไม่มีข่าวจาก yfinance"

    if sentiment == "BULLISH":
        return f"ข่าวล่าสุด {news_count} รายการค่อนข้างเป็นบวก (+{score}) ตลาดอาจมองสินทรัพย์นี้เชิงบวก"

    if sentiment == "BEARISH":
        return f"ข่าวล่าสุด {news_count} รายการค่อนข้างเป็นลบ ({score}) ควรระวังแรงขายหรือความผันผวน"

    return f"ข่าวล่าสุด {news_count} รายการยังไม่มี sentiment ชัดเจน ตลาดอาจกำลังรอปัจจัยใหม่"


if __name__ == "__main__":
    result = analyze_ticker_news("NVDA")
    print(result)
