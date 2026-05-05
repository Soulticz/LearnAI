from dataclasses import dataclass
from datetime import datetime

import yfinance as yf


@dataclass
class NewsItem:
    title: str
    publisher: str
    link: str
    published_at: str


POSITIVE_WORDS = [
    "beat", "beats", "growth", "upgrade", "outperform", "strong", "profit", "record",
    "surge", "rally", "bullish", "buy", "positive", "raise", "raised", "partnership",
    "expansion", "approval", "launch", "revenue", "earnings",
]

NEGATIVE_WORDS = [
    "miss", "misses", "downgrade", "underperform", "weak", "loss", "lawsuit", "probe",
    "investigation", "fall", "drop", "plunge", "bearish", "sell", "negative", "cut",
    "recall", "delay", "risk", "warning", "fraud", "decline",
]


def normalize_news(raw_item: dict) -> NewsItem:
    content = raw_item.get("content") or raw_item
    title = content.get("title") or raw_item.get("title") or "No title"
    publisher = content.get("provider", {}).get("displayName") or raw_item.get("publisher") or "Unknown"
    link = content.get("canonicalUrl", {}).get("url") or raw_item.get("link") or ""

    published_raw = content.get("pubDate") or raw_item.get("providerPublishTime") or ""
    if isinstance(published_raw, int):
        published_at = datetime.fromtimestamp(published_raw).strftime("%Y-%m-%d %H:%M")
    else:
        published_at = str(published_raw)[:19]

    return NewsItem(
        title=str(title),
        publisher=str(publisher),
        link=str(link),
        published_at=published_at,
    )


def score_news_title(title: str) -> int:
    text = title.lower()
    score = 0
    for word in POSITIVE_WORDS:
        if word in text:
            score += 1
    for word in NEGATIVE_WORDS:
        if word in text:
            score -= 1
    return score


def analyze_news(ticker: str, limit: int = 5) -> dict:
    """ดึงข่าวจาก yfinance แล้วให้คะแนน sentiment แบบ rule-based ง่าย ๆ

    หมายเหตุ: เป็นตัวช่วยเบื้องต้น ไม่ใช่ financial news API แบบ premium
    """
    try:
        raw_news = yf.Ticker(ticker).news or []
    except Exception as e:
        return {
            "ticker": ticker,
            "items": [],
            "sentiment_score": 0,
            "sentiment_label": "UNKNOWN",
            "summary": f"ดึงข่าวไม่สำเร็จ: {str(e)}",
        }

    items = []
    total_score = 0

    for raw in raw_news[:limit]:
        item = normalize_news(raw)
        item_score = score_news_title(item.title)
        total_score += item_score
        items.append({
            "title": item.title,
            "publisher": item.publisher,
            "published_at": item.published_at,
            "link": item.link,
            "score": item_score,
        })

    if total_score > 1:
        label = "POSITIVE"
    elif total_score < -1:
        label = "NEGATIVE"
    else:
        label = "NEUTRAL"

    if not items:
        summary = "ยังไม่พบข่าวล่าสุดจาก yfinance"
    else:
        summary = f"News sentiment: {label} ({total_score:+d}) จากข่าว {len(items)} รายการ"

    return {
        "ticker": ticker,
        "items": items,
        "sentiment_score": total_score,
        "sentiment_label": label,
        "summary": summary,
    }


def format_news_context(news_result: dict) -> str:
    if not news_result or not news_result.get("items"):
        return news_result.get("summary", "ไม่มีข้อมูลข่าว") if news_result else "ไม่มีข้อมูลข่าว"

    lines = [news_result.get("summary", "News sentiment")]
    for item in news_result["items"]:
        lines.append(
            f"- [{item.get('sentiment', item.get('score', 0)):+}] "
            f"{item.get('title')} ({item.get('publisher')}, {item.get('published_at')})"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    result = analyze_news("NVDA")
    print(format_news_context(result))
