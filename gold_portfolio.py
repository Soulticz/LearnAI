from typing import Any

from money_tracker import ensure_portfolio_file, summarize_money

GOLD_TICKERS = {"GC=F", "GLD", "IAU", "XAUUSD=X", "YLG-GOLD", "GOLD"}


def is_gold_asset(asset: dict[str, Any]) -> bool:
    ticker = str(asset.get("ticker", "")).upper().strip()
    asset_type = str(asset.get("type", "")).lower().strip()
    name = str(asset.get("name", "")).lower()

    return (
        asset_type == "gold"
        or ticker in GOLD_TICKERS
        or "gold" in name
        or "ทอง" in name
        or "ylg" in name
    )


def split_gold_assets(summary: dict[str, Any] | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    summary = summary or summarize_money(ensure_portfolio_file())
    assets = summary.get("assets", [])
    gold_assets = [asset for asset in assets if is_gold_asset(asset)]
    other_assets = [asset for asset in assets if not is_gold_asset(asset)]
    return gold_assets, other_assets


def summarize_gold_portfolio(summary: dict[str, Any] | None = None) -> dict[str, Any]:
    summary = summary or summarize_money(ensure_portfolio_file())
    gold_assets, other_assets = split_gold_assets(summary)

    gold_cost = sum(float(asset.get("amount_thb", 0) or 0) for asset in gold_assets)
    gold_value = sum(float(asset.get("estimated_value_thb", asset.get("amount_thb", 0)) or 0) for asset in gold_assets)
    gold_profit = gold_value - gold_cost
    gold_profit_pct = (gold_profit / gold_cost * 100) if gold_cost > 0 else 0

    total = float(summary.get("total_thb", 0) or 0)
    gold_weight_pct = (gold_value / total * 100) if total > 0 else 0

    risk_notes = []
    if gold_weight_pct >= 40:
        risk_notes.append("ทองมีสัดส่วนสูงมากในพอร์ต ระวังกระจุกตัวเกินไป")
    elif gold_weight_pct >= 25:
        risk_notes.append("ทองมีสัดส่วนค่อนข้างสูง ควรดูความเสี่ยงจากราคาทองและค่าเงิน")

    if gold_profit_pct >= 10:
        risk_notes.append("ทองกำไรแรง ควรวางแผนล็อกกำไรบางส่วน")
    elif gold_profit_pct <= -10:
        risk_notes.append("ทองติดลบหนัก อย่าเติมเงินแก้มือทันที")

    if not risk_notes:
        risk_notes.append("พอร์ตทองยังไม่มีสัญญาณเสี่ยงเด่น")

    return {
        "gold_assets": gold_assets,
        "other_assets": other_assets,
        "gold_count": len(gold_assets),
        "gold_cost_thb": gold_cost,
        "gold_value_thb": gold_value,
        "gold_profit_thb": gold_profit,
        "gold_profit_pct": gold_profit_pct,
        "gold_weight_pct": gold_weight_pct,
        "risk_notes": risk_notes,
    }


if __name__ == "__main__":
    data = summarize_gold_portfolio()
    print(data)
