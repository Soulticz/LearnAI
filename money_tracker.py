import json
import os
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
        # {"ticker": "GLD", "name": "Gold ETF", "amount_thb": 500, "avg_price": 300},
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
    try:
        df = yf.download(ticker, period="5d", interval="1d", progress=False)
        if df.empty:
            return None
        if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
            df.columns = df.columns.get_level_values(0)
        df.columns = df.columns.str.lower()
        return float(df["close"].iloc[-1])
    except Exception:
        return None


def analyze_asset(asset: dict[str, Any]) -> dict[str, Any]:
    ticker = str(asset.get("ticker", "")).upper().strip()
    avg_price = float(asset.get("avg_price", 0) or 0)
    amount_thb = float(asset.get("amount_thb", 0) or 0)
    current_price = get_latest_price(ticker) if ticker else None

    pnl_pct = None
    status = "ยังประเมินไม่ได้"
    action = "รอดู"

    if current_price is not None and avg_price > 0:
        pnl_pct = ((current_price - avg_price) / avg_price) * 100

        if pnl_pct >= 10:
            status = "กำไรดีมาก"
            action = "พิจารณาขายบางส่วน/ล็อกกำไร"
        elif pnl_pct >= 5:
            status = "กำไรเริ่มดี"
            action = "ถือได้ แต่เริ่มระวังย่อ"
        elif pnl_pct <= -10:
            status = "ขาดทุนหนัก"
            action = "ทบทวนเหตุผลที่ถือ อย่าเติมเงินแก้มือทันที"
        elif pnl_pct <= -5:
            status = "ขาดทุนเล็กน้อย"
            action = "รอดู อย่ารีบขายเพราะตกใจ"
        else:
            status = "แกว่งในกรอบ"
            action = "ถือ/รอสัญญาณชัด"

    return {
        "ticker": ticker,
        "name": asset.get("name", ticker),
        "amount_thb": amount_thb,
        "avg_price": avg_price,
        "current_price": current_price,
        "pnl_pct": pnl_pct,
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
    asset_total = sum(float(a.get("amount_thb", 0) or 0) for a in assets)
    total = cash_thb + fund_total + asset_total

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
        "asset_total_thb": asset_total,
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
    lines.append(f"หุ้น/ทองใน Dime: {summary['asset_total_thb']:,.2f} บาท")
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
            lines.append(
                f"- {asset['ticker']}: {asset['amount_thb']:,.2f} บาท | Last {price_text} | P/L {pnl_text} | {asset['action']}"
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
