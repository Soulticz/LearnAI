from __future__ import annotations

from typing import Any

POSITIVE_KEYWORDS = [
    "beat",
    "growth",
    "surge",
    "strong",
    "bullish",
    "upgrade",
    "record high",
    "ai boom",
    "profit jumps",
    "outperform",
    "optimistic",
]

NEGATIVE_KEYWORDS = [
    "crash",
    "drop",
    "lawsuit",
    "bearish",
    "downgrade",
    "recession",
    "inflation fear",
    "selloff",
    "weak guidance",
    "rate hike",
    "warning",
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


def build_news_commentary(result: dict[str, Any]) -> str:
    sentiment = result.get("sentiment", "NEUTRAL")
    score = result.get("score", 0)

    if sentiment == "BULLISH":
        return f"ข่าวรวมค่อนข้างเป็นบวก (+{score}) ตลาดอาจมองสินทรัพย์นี้เชิงบวก"

    if sentiment == "BEARISH":
        return f"ข่าวรวมค่อนข้างเป็นลบ ({score}) ควรระวังแรงขายหรือความผันผวน"

    return "ข่าวยังไม่มี sentiment ชัดเจน ตลาดอาจกำลังรอปัจจัยใหม่"


if __name__ == "__main__":
    sample = "NVIDIA reports strong growth and AI boom with optimistic guidance"
    result = score_news_text(sample)
    print(result)
    print(build_news_commentary(result))
