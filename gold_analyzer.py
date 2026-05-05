from dataclasses import dataclass

import yfinance as yf


GOLD_TICKERS = {"GC=F", "XAUUSD=X", "GLD", "IAU"}
USD_PROXY = "UUP"      # Invesco DB US Dollar Index Bullish Fund ใช้เป็น proxy ของ USD
YIELD_PROXY = "^TNX"   # US 10Y Treasury Yield


@dataclass
class GoldContext:
    ticker: str
    is_gold: bool
    gold_change_5d: float | None = None
    usd_change_5d: float | None = None
    yield_change_5d: float | None = None
    bias_score: int = 0
    bias_label: str = "UNKNOWN"
    summary: str = ""


def pct_change_5d(ticker: str) -> float | None:
    try:
        df = yf.download(ticker, period="1mo", interval="1d", progress=False)
        if df.empty or len(df) < 6:
            return None
        if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
            df.columns = df.columns.get_level_values(0)
        df.columns = df.columns.str.lower()
        close = df["close"]
        return float((close.iloc[-1] / close.iloc[-6] - 1) * 100)
    except Exception:
        return None


def analyze_gold_context(ticker: str) -> GoldContext:
    ticker = ticker.upper().strip()
    if ticker not in GOLD_TICKERS:
        return GoldContext(ticker=ticker, is_gold=False, summary="ไม่ใช่สินทรัพย์กลุ่มทอง")

    gold_chg = pct_change_5d(ticker)
    usd_chg = pct_change_5d(USD_PROXY)
    yield_chg = pct_change_5d(YIELD_PROXY)

    score = 0
    reasons = []

    if gold_chg is not None:
        if gold_chg > 1:
            score += 1
            reasons.append(f"ทองขึ้นแรงใน 5 วัน ({gold_chg:+.2f}%)")
        elif gold_chg < -1:
            score -= 1
            reasons.append(f"ทองอ่อนตัวใน 5 วัน ({gold_chg:+.2f}%)")
        else:
            reasons.append(f"ทองแกว่งไม่แรงใน 5 วัน ({gold_chg:+.2f}%)")

    # USD แข็งมักกดดันทอง / USD อ่อนมักช่วยทอง
    if usd_chg is not None:
        if usd_chg > 0.5:
            score -= 1
            reasons.append(f"USD proxy แข็งขึ้น ({usd_chg:+.2f}%) กดดันทอง")
        elif usd_chg < -0.5:
            score += 1
            reasons.append(f"USD proxy อ่อนลง ({usd_chg:+.2f}%) หนุนทอง")
        else:
            reasons.append(f"USD proxy เปลี่ยนไม่มาก ({usd_chg:+.2f}%)")

    # Yield ขึ้นมักกดดันทอง / Yield ลงมักหนุนทอง
    if yield_chg is not None:
        if yield_chg > 2:
            score -= 1
            reasons.append(f"US 10Y yield ขึ้น ({yield_chg:+.2f}%) กดดันทอง")
        elif yield_chg < -2:
            score += 1
            reasons.append(f"US 10Y yield ลง ({yield_chg:+.2f}%) หนุนทอง")
        else:
            reasons.append(f"US 10Y yield เปลี่ยนไม่มาก ({yield_chg:+.2f}%)")

    if score >= 2:
        label = "BULLISH"
    elif score <= -2:
        label = "BEARISH"
    else:
        label = "NEUTRAL"

    summary = f"Gold Macro Bias: {label} ({score:+d})\n" + "\n".join(f"- {r}" for r in reasons)

    return GoldContext(
        ticker=ticker,
        is_gold=True,
        gold_change_5d=gold_chg,
        usd_change_5d=usd_chg,
        yield_change_5d=yield_chg,
        bias_score=score,
        bias_label=label,
        summary=summary,
    )


if __name__ == "__main__":
    result = analyze_gold_context("GC=F")
    print(result.summary)
