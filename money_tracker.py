import json
from pathlib import Path
from typing import Any

import yfinance as yf

PORTFOLIO_FILE = Path("personal_portfolio.json")

DEFAULT_PORTFOLIO = {
    "cash_thb": 0,
    "funds": [
        {
            "name": "TSP5",
            "amount_thb": 2000,
            "note": "กองทุนรวม ถือยาว ไม่ต้องดูรายวัน"
        }
    ],
    "assets": [
        # ตัวอย่าง:
        # {"ticker": "AAPL", "name": "Apple", "amount_thb": 500, "avg_price": 200},
        # {"ticker": "GC=F", "name": "YLG GOLD 99.99", "amount_thb": 995.58, "avg_price": 4702.13, "current_price_manual": 4695.43},
    ]
}


def ensure_portfolio_file(path: Path = PORTFOLIO_FILE) -> dict[str, Any]:
    if not path.exists():
        with open(path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_PORTFOLIO, f, ensure_ascii=False, indent=2)
        return DEFAULT_PORTFOLIO

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_price_history(ticker: str, period: str = "6mo", interval: str = "1d"):
    ticker = str(ticker or "").upper().strip()
    if not ticker:
        return None

    try:
        hist = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=False)
        if hist.empty or "Close" not in hist.columns:
            return None
        return hist
    except Exception:
        return None


def get_latest_price(ticker: str) -> float | None:
    """Get latest close price for one ticker only.

    Using yf.Ticker().history() avoids the shifted-price issue that can happen
    when yf.download() returns a multi-index dataframe or cached batch data.
    """
    hist = get_price_history(ticker, period="5d", interval="1d")
    if hist is None:
        return None

    try:
        close = hist["Close"].dropna()
        if close.empty:
            return None

        price = float(close.iloc[-1])
        if price <= 0:
            return None
        return price
    except Exception:
        return None


def calc_rsi(close, period: int = 14) -> float | None:
    try:
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        latest_rsi = rsi.dropna().iloc[-1]
        return float(latest_rsi)
    except Exception:
        return None


def get_technical_signals(ticker: str) -> dict[str, Any]:
    hist = get_price_history(ticker, period="6mo", interval="1d")
    if hist is None:
        return {
            "rsi": None,
            "sma20": None,
            "sma50": None,
            "trend": "N/A",
            "volatility_pct": None,
        }

    try:
        close = hist["Close"].dropna()
        if len(close) < 20:
            return {
                "rsi": None,
                "sma20": None,
                "sma50": None,
                "trend": "ข้อมูลน้อย",
                "volatility_pct": None,
            }

        latest_close = float(close.iloc[-1])
        sma20 = float(close.rolling(window=20).mean().iloc[-1])
        sma50 = float(close.rolling(window=50).mean().iloc[-1]) if len(close) >= 50 else None
        rsi = calc_rsi(close)
        volatility_pct = float(close.pct_change().dropna().std() * 100)

        if sma50 is not None and latest_close > sma20 > sma50:
            trend = "ขาขึ้น"
        elif sma50 is not None and latest_close < sma20 < sma50:
            trend = "ขาลง"
        elif latest_close > sma20:
            trend = "เริ่มแข็งแรง"
        else:
            trend = "อ่อนตัว/พักฐาน"

        return {
            "rsi": round(rsi, 2) if rsi is not None else None,
            "sma20": round(sma20, 2),
            "sma50": round(sma50, 2) if sma50 is not None else None,
            "trend": trend,
            "volatility_pct": round(volatility_pct, 2),
        }
    except Exception:
        return {
            "rsi": None,
            "sma20": None,
            "sma50": None,
            "trend": "N/A",
            "volatility_pct": None,
        }


def calc_status_and_action(pnl_pct: float | None) -> tuple[str, str]:
    if pnl_pct is None:
        return "ยังประเมินไม่ได้", "รอดู"

    if pnl_pct >= 10:
        return "กำไรดีมาก", "พิจารณาขายบางส่วน/ล็อกกำไร"
    if pnl_pct >= 5:
        return "กำไรเริ่มดี", "ถือได้ แต่เริ่มระวังย่อ"
    if pnl_pct <= -10:
        return "ขาดทุนหนัก", "ทบทวนเหตุผลที่ถือ อย่าเติมเงินแก้มือทันที"
    if pnl_pct <= -5:
        return "ขาดทุนเล็กน้อย", "รอดู อย่ารีบขายเพราะตกใจ"
    return "แกว่งในกรอบ", "ถือ/รอสัญญาณชัด"


def calc_ai_score(pnl_pct: float | None, signals: dict[str, Any]) -> int:
    score = 50

    if pnl_pct is not None:
        if pnl_pct >= 10:
            score += 10
        elif pnl_pct >= 3:
            score += 6
        elif pnl_pct <= -10:
            score -= 12
        elif pnl_pct <= -3:
            score -= 6

    trend = signals.get("trend")
    if trend == "ขาขึ้น":
        score += 16
    elif trend == "เริ่มแข็งแรง":
        score += 8
    elif trend == "ขาลง":
        score -= 16
    elif trend == "อ่อนตัว/พักฐาน":
        score -= 6

    rsi = signals.get("rsi")
    if rsi is not None:
        if 45 <= rsi <= 65:
            score += 8
        elif 30 <= rsi < 45:
            score += 3
        elif rsi < 30:
            score += 5
        elif 65 < rsi <= 75:
            score -= 4
        elif rsi > 75:
            score -= 10

    volatility_pct = signals.get("volatility_pct")
    if volatility_pct is not None:
        if volatility_pct <= 2:
            score += 4
        elif volatility_pct >= 6:
            score -= 8
        elif volatility_pct >= 4:
            score -= 4

    return max(0, min(100, int(round(score))))


def build_ai_commentary(ticker: str, pnl_pct: float | None, signals: dict[str, Any], ai_score: int) -> str:
    trend = signals.get("trend", "N/A")
    rsi = signals.get("rsi")
    volatility_pct = signals.get("volatility_pct")

    parts = []

    if ai_score >= 75:
        parts.append("ภาพรวมแข็งแรง")
    elif ai_score >= 55:
        parts.append("ภาพรวมพอถือได้")
    elif ai_score >= 40:
        parts.append("ยังไม่นิ่ง ควรรอดู")
    else:
        parts.append("ความเสี่ยงสูง ควรระวัง")

    if trend not in (None, "N/A"):
        parts.append(f"แนวโน้มเป็น{trend}")

    if rsi is not None:
        if rsi < 30:
            parts.append(f"RSI {rsi:.2f} อยู่โซนขายมาก อาจมีเด้งได้แต่ยังเสี่ยง")
        elif rsi > 75:
            parts.append(f"RSI {rsi:.2f} ร้อนแรง ระวังย่อ")
        else:
            parts.append(f"RSI {rsi:.2f} ยังไม่สุดโต่ง")

    if pnl_pct is not None:
        if pnl_pct >= 10:
            parts.append("กำไรเริ่มเยอะ คิดแผนล็อกกำไรบางส่วนได้")
        elif pnl_pct <= -10:
            parts.append("ขาดทุนเริ่มลึก อย่าเติมเงินแก้มือทันที")

    if volatility_pct is not None and volatility_pct >= 5:
        parts.append(f"ความผันผวน {volatility_pct:.2f}% ต่อวัน ค่อนข้างแกว่ง")

    return " | ".join(parts) if parts else f"{ticker} ยังมีข้อมูลไม่พอให้ AI วิเคราะห์"


def analyze_asset(asset: dict[str, Any]) -> dict[str, Any]:
    ticker = str(asset.get("ticker", "")).upper().strip()
    avg_price = float(asset.get("avg_price", 0) or 0)
    amount_thb = float(asset.get("amount_thb", 0) or 0)
    qty = float(asset.get("qty", 0) or 0)

    manual_price = asset.get("current_price_manual")
    if manual_price not in (None, "", 0):
        current_price = float(manual_price)
        price_source = "manual"
    else:
        current_price = get_latest_price(ticker) if ticker else None
        price_source = "yfinance" if current_price is not None else "none"

    signals = get_technical_signals(ticker) if ticker and price_source != "none" else {
        "rsi": None,
        "sma20": None,
        "sma50": None,
        "trend": "N/A",
        "volatility_pct": None,
    }

    pnl_pct = None
    estimated_value_thb = amount_thb
    profit_thb = 0.0

    if current_price is not None and avg_price > 0:
        pnl_pct = ((current_price - avg_price) / avg_price) * 100
        estimated_value_thb = amount_thb * (1 + pnl_pct / 100)
        profit_thb = estimated_value_thb - amount_thb

    cost_value = qty * avg_price if qty > 0 and avg_price > 0 else None
    market_value = qty * current_price if qty > 0 and current_price is not None else None

    status, action = calc_status_and_action(pnl_pct)
    ai_score = calc_ai_score(pnl_pct, signals)
    ai_commentary = build_ai_commentary(ticker, pnl_pct, signals, ai_score)

    return {
        "ticker": ticker,
        "name": asset.get("name", ticker),
        "amount_thb": amount_thb,
        "qty": qty,
        "avg_price": avg_price,
        "current_price": current_price,
        "current_price_manual": float(manual_price) if manual_price not in (None, "", 0) else None,
        "price_source": price_source,
        "pnl_pct": pnl_pct,
        "estimated_value_thb": estimated_value_thb,
        "profit_thb": profit_thb,
        "cost_value": cost_value,
        "market_value": market_value,
        "rsi": signals.get("rsi"),
        "sma20": signals.get("sma20"),
        "sma50": signals.get("sma50"),
        "trend": signals.get("trend"),
        "volatility_pct": signals.get("volatility_pct"),
        "ai_score": ai_score,
        "ai_commentary": ai_commentary,
        "status": status,
        "action": action,
    }


def summarize_money(portfolio: dict[str, Any] | None = None) -> dict[str, Any]:
    portfolio = portfolio or ensure_portfolio_file()
    funds = portfolio.get("funds", [])
    assets = portfolio.get("assets", [])
    cash_thb = float(portfolio.get("cash_thb", 0) or 0)

    analyzed_assets = [analyze_asset(asset) for asset in assets]
    fund_total = sum(float(f.get("amount_thb", 0) or 0) for f in funds)
    asset_cost_total = sum(float(a.get("amount_thb", 0) or 0) for a in assets)
    asset_market_total = sum(float(a.get("estimated_value_thb", a.get("amount_thb", 0)) or 0) for a in analyzed_assets)
    asset_profit_total = asset_market_total - asset_cost_total
    asset_profit_pct = (asset_profit_total / asset_cost_total * 100) if asset_cost_total > 0 else 0
    total = cash_thb + fund_total + asset_market_total

    risk_notes = []
    high_risk_count = 0
    for asset in analyzed_assets:
        pnl_pct = asset.get("pnl_pct")
        ai_score = asset.get("ai_score")
        if pnl_pct is not None and pnl_pct <= -10:
            high_risk_count += 1
            risk_notes.append(f"{asset['ticker']} ขาดทุนหนัก {pnl_pct:.2f}%")
        elif pnl_pct is not None and pnl_pct >= 10:
            risk_notes.append(f"{asset['ticker']} กำไรแรง {pnl_pct:.2f}% ระวังย่อ")

        if ai_score is not None and ai_score < 40:
            high_risk_count += 1
            risk_notes.append(f"{asset['ticker']} AI Score ต่ำ {ai_score}/100 ควรระวัง")

    if not risk_notes:
        risk_notes.append("ยังไม่มีสัญญาณเสี่ยงหนักจากรายการที่กรอก")

    return {
        "cash_thb": cash_thb,
        "fund_total_thb": fund_total,
        "asset_total_thb": asset_cost_total,
        "asset_market_total_thb": asset_market_total,
        "asset_profit_thb": asset_profit_total,
        "asset_profit_pct": asset_profit_pct,
        "total_thb": total,
        "funds": funds,
        "assets": analyzed_assets,
        "risk_notes": risk_notes,
        "high_risk_count": high_risk_count,
    }


def format_money_summary(summary: dict[str, Any]) -> str:
    lines = []
    lines.append("💰 Soul Money Checker")
    lines.append(f"เงินสด: {summary['cash_thb']:,.2f} บาท")
    lines.append(f"กองทุน: {summary['fund_total_thb']:,.2f} บาท")
    lines.append(f"ต้นทุนหุ้น/ทองใน Dime: {summary['asset_total_thb']:,.2f} บาท")
    lines.append(f"มูลค่าหุ้น/ทองโดยประมาณ: {summary['asset_market_total_thb']:,.2f} บาท")
    lines.append(f"กำไร/ขาดทุนหุ้น/ทอง: {summary['asset_profit_thb']:+,.2f} บาท ({summary['asset_profit_pct']:+.2f}%)")
    lines.append(f"รวมโดยประมาณ: {summary['total_thb']:,.2f} บาท")

    lines.append("\n🐢 กองทุน")
    for fund in summary.get("funds", []):
        lines.append(f"- {fund.get('name')}: {float(fund.get('amount_thb', 0)):,.2f} บาท | {fund.get('note', 'ถือยาว')}")

    lines.append("\n📊 Dime / หุ้น / ทอง")
    assets = summary.get("assets", [])
    if not assets:
        lines.append("- ยังไม่ได้กรอก asset ใน personal_portfolio.json")
    else:
        for asset in assets:
            pnl_text = "N/A" if asset.get("pnl_pct") is None else f"{asset['pnl_pct']:+.2f}%"
            price_text = "N/A" if asset.get("current_price") is None else f"{asset['current_price']:,.2f}"
            value_text = f"{asset.get('estimated_value_thb', asset['amount_thb']):,.2f} บาท"
            lines.append(
                f"- {asset['ticker']}: ต้นทุน {asset['amount_thb']:,.2f} บาท | มูลค่า {value_text} | Last {price_text} | P/L {pnl_text} | AI {asset.get('ai_score', 'N/A')}/100 | {asset['action']}"
            )

    lines.append("\n⚠️ สิ่งที่ต้องระวัง")
    for note in summary.get("risk_notes", []):
        lines.append(f"- {note}")

    lines.append("\n🎯 สรุปวันนี้: ใช้บอทเป็นตัวช่วยเช็กพอร์ต ไม่ใช่สั่งซื้อขายแทนคุณ")
    return "\n".join(lines)


if __name__ == "__main__":
    portfolio = ensure_portfolio_file()
    summary = summarize_money(portfolio)
    print(format_money_summary(summary))
