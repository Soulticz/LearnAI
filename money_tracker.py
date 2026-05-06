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


def get_latest_price(ticker: str) -> float | None:
    """Get latest close price for one ticker only.

    Using yf.Ticker().history() avoids the shifted-price issue that can happen
    when yf.download() returns a multi-index dataframe or cached batch data.
    """
    ticker = str(ticker or "").upper().strip()
    if not ticker:
        return None

    try:
        hist = yf.Ticker(ticker).history(period="5d", interval="1d", auto_adjust=False)
        if hist.empty or "Close" not in hist.columns:
            return None

        close = hist["Close"].dropna()
        if close.empty:
            return None

        price = float(close.iloc[-1])
        if price <= 0:
            return None
        return price
    except Exception:
        return None


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
        if pnl_pct is not None and pnl_pct <= -10:
            high_risk_count += 1
            risk_notes.append(f"{asset['ticker']} ขาดทุนหนัก {pnl_pct:.2f}%")
        elif pnl_pct is not None and pnl_pct >= 10:
            risk_notes.append(f"{asset['ticker']} กำไรแรง {pnl_pct:.2f}% ระวังย่อ")

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
                f"- {asset['ticker']}: ต้นทุน {asset['amount_thb']:,.2f} บาท | มูลค่า {value_text} | Last {price_text} | P/L {pnl_text} | {asset['action']}"
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
