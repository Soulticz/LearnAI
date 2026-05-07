from __future__ import annotations

from typing import Any


def clamp(value: float, min_value: int = 0, max_value: int = 100) -> int:
    return max(min_value, min(max_value, int(round(value))))


def calc_technical_score(pnl_pct: float | None, signals: dict[str, Any]) -> int:
    score = 50

    trend = signals.get("trend")
    if trend == "ขาขึ้น":
        score += 22
    elif trend == "เริ่มแข็งแรง":
        score += 12
    elif trend == "ขาลง":
        score -= 22
    elif trend == "อ่อนตัว/พักฐาน":
        score -= 10

    rsi = signals.get("rsi")
    if rsi is not None:
        rsi = float(rsi)
        if 45 <= rsi <= 65:
            score += 12
        elif 30 <= rsi < 45:
            score += 5
        elif rsi < 30:
            score += 8
        elif 65 < rsi <= 75:
            score -= 6
        elif rsi > 75:
            score -= 14

    if pnl_pct is not None:
        pnl_pct = float(pnl_pct)
        if pnl_pct >= 10:
            score += 8
        elif pnl_pct >= 3:
            score += 5
        elif pnl_pct <= -10:
            score -= 12
        elif pnl_pct <= -3:
            score -= 6

    return clamp(score)


def calc_risk_score(signals: dict[str, Any]) -> int:
    """Higher score = safer risk profile."""
    score = 75
    volatility_pct = signals.get("volatility_pct")

    if volatility_pct is not None:
        volatility_pct = float(volatility_pct)
        if volatility_pct <= 2:
            score += 10
        elif volatility_pct >= 7:
            score -= 35
        elif volatility_pct >= 5:
            score -= 24
        elif volatility_pct >= 3:
            score -= 12

    rsi = signals.get("rsi")
    if rsi is not None:
        rsi = float(rsi)
        if rsi > 75:
            score -= 15
        elif rsi < 25:
            score -= 8

    return clamp(score)


def calc_news_score(news_result: dict[str, Any] | None) -> int:
    if not news_result:
        return 50

    sentiment = news_result.get("sentiment", "NEUTRAL")
    raw_score = float(news_result.get("score", 0) or 0)

    score = 50 + (raw_score * 4)
    if sentiment == "BULLISH":
        score += 8
    elif sentiment == "BEARISH":
        score -= 8

    return clamp(score)


def calc_personal_fit_score(ticker: str, name: str, signals: dict[str, Any]) -> int:
    text = f"{ticker} {name}".lower()
    score = 60

    if any(word in text for word in ["msft", "nvda", "sndk", "ai", "tech"]):
        score += 15

    if any(word in text for word in ["gold", "gld", "gc=f", "ylg"]):
        score -= 8
        volatility_pct = signals.get("volatility_pct")
        if volatility_pct is not None and float(volatility_pct) >= 3:
            score -= 10

    return clamp(score)


def calc_confidence(score_breakdown: dict[str, int], signals: dict[str, Any], news_result: dict[str, Any] | None) -> str:
    data_points = 0
    if signals.get("rsi") is not None:
        data_points += 1
    if signals.get("trend") not in [None, "N/A", "ข้อมูลน้อย"]:
        data_points += 1
    if signals.get("volatility_pct") is not None:
        data_points += 1
    if news_result and news_result.get("news_count", 0) > 0:
        data_points += 1

    spread = max(score_breakdown.values()) - min(score_breakdown.values()) if score_breakdown else 100

    if data_points >= 4 and spread <= 35:
        return "HIGH"
    if data_points >= 3:
        return "MEDIUM"
    return "LOW"


def calc_ai_score_v2(
    ticker: str,
    name: str,
    pnl_pct: float | None,
    signals: dict[str, Any],
    news_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    technical_score = calc_technical_score(pnl_pct, signals)
    news_score = calc_news_score(news_result)
    risk_score = calc_risk_score(signals)
    personal_fit_score = calc_personal_fit_score(ticker, name, signals)

    weights = {
        "technical": 0.40,
        "news": 0.20,
        "risk": 0.20,
        "personal_fit": 0.20,
    }

    final_score = (
        technical_score * weights["technical"]
        + news_score * weights["news"]
        + risk_score * weights["risk"]
        + personal_fit_score * weights["personal_fit"]
    )

    breakdown = {
        "technical_score": technical_score,
        "news_score": news_score,
        "risk_score": risk_score,
        "personal_fit_score": personal_fit_score,
    }

    confidence = calc_confidence(breakdown, signals, news_result)

    return {
        "ai_score_v2": clamp(final_score),
        "ai_score_breakdown": breakdown,
        "ai_confidence": confidence,
        "ai_score_weights": weights,
    }


def build_score_v2_commentary(score_data: dict[str, Any]) -> str:
    score = score_data.get("ai_score_v2", 0)
    confidence = score_data.get("ai_confidence", "LOW")
    breakdown = score_data.get("ai_score_breakdown", {})

    parts = []
    if score >= 75:
        parts.append("Score 2.0 มองภาพรวมค่อนข้างแข็งแรง")
    elif score >= 55:
        parts.append("Score 2.0 มองว่ายังพอถือ/ติดตามได้")
    elif score >= 40:
        parts.append("Score 2.0 ยังไม่มั่นใจ ควรรอดู")
    else:
        parts.append("Score 2.0 มองว่าความเสี่ยงสูง")

    parts.append(f"Confidence: {confidence}")
    parts.append(
        " / ".join([
            f"Technical {breakdown.get('technical_score', 'N/A')}",
            f"News {breakdown.get('news_score', 'N/A')}",
            f"Risk {breakdown.get('risk_score', 'N/A')}",
            f"Fit {breakdown.get('personal_fit_score', 'N/A')}",
        ])
    )

    return " | ".join(parts)
