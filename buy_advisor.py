from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

from money_tracker import ensure_portfolio_file, summarize_money

STRATEGY_FILE = Path("strategy_modes.csv")


def load_strategy_modes() -> pd.DataFrame:
    if not STRATEGY_FILE.exists():
        return pd.DataFrame()
    df = pd.read_csv(STRATEGY_FILE)
    if "mode" in df.columns:
        df["mode"] = df["mode"].astype(str).str.upper().str.strip()
    return df


def get_market_change(ticker: str = "SPY") -> float | None:
    try:
        df = yf.download(ticker, period="5d", interval="1d", progress=False)
        if df.empty or len(df) < 2:
            return None
        if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
            df.columns = df.columns.get_level_values(0)
        df.columns = df.columns.str.lower()
        close = df["close"]
        return float((close.iloc[-1] / close.iloc[-2] - 1) * 100)
    except Exception:
        return None


def build_buy_advice(summary: dict[str, Any] | None = None) -> dict[str, Any]:
    summary = summary or summarize_money(ensure_portfolio_file())
    strategy_df = load_strategy_modes()

    cash = float(summary.get("cash_thb", 0) or 0)
    total = float(summary.get("total_thb", 0) or 0)
    assets = summary.get("assets", [])
    high_risk_count = int(summary.get("high_risk_count", 0) or 0)

    score = 50
    reasons: list[str] = []

    if total <= 0:
        score -= 30
        reasons.append("ยังไม่มีข้อมูลเงินรวมชัดเจน")
    else:
        cash_ratio = cash / total
        if cash_ratio >= 0.2:
            score += 10
            reasons.append("มีเงินสดพอสำหรับรอจังหวะ")
        elif cash_ratio <= 0.05:
            score -= 15
            reasons.append("เงินสดเหลือน้อย ไม่ควรซื้อเพิ่ม")
        else:
            reasons.append("เงินสดอยู่ระดับกลาง")

    if high_risk_count > 0:
        score -= 20
        reasons.append("มีสินทรัพย์ติดลบหนัก ควรคุมความเสี่ยงก่อนซื้อเพิ่ม")

    if assets and len(assets) >= 5:
        score -= 5
        reasons.append("ถือหลายตัวแล้ว ระวังกระจายเยอะเกินไป")

    market_change = get_market_change("SPY")
    if market_change is not None:
        if market_change > 1:
            score += 5
            reasons.append(f"ตลาดสหรัฐวันนี้เป็นบวก SPY {market_change:+.2f}%")
        elif market_change < -1:
            score -= 10
            reasons.append(f"ตลาดสหรัฐวันนี้อ่อนตัว SPY {market_change:+.2f}%")
        else:
            reasons.append(f"ตลาดสหรัฐแกว่งไม่แรง SPY {market_change:+.2f}%")

    candidates = []
    if not strategy_df.empty:
        safe_df = strategy_df[
            (strategy_df["mode"].isin(["HYBRID", "ACTIVE_HYBRID", "HOLD", "WATCH"]))
        ].copy()

        if "hybrid_return_pct" in safe_df.columns and "hybrid_max_drawdown_pct" in safe_df.columns:
            safe_df = safe_df[
                (safe_df["hybrid_return_pct"] > 0) &
                (safe_df["hybrid_max_drawdown_pct"] > -30)
            ].copy()

        if not safe_df.empty and "hybrid_alpha_vs_hold_pct" in safe_df.columns:
            safe_df = safe_df.sort_values("hybrid_alpha_vs_hold_pct", ascending=False).head(3)
            for _, row in safe_df.iterrows():
                candidates.append({
                    "ticker": str(row.get("ticker", "")),
                    "mode": str(row.get("mode", "UNKNOWN")),
                    "hybrid_return_pct": float(row.get("hybrid_return_pct", 0) or 0),
                    "alpha_pct": float(row.get("hybrid_alpha_vs_hold_pct", 0) or 0),
                    "reason": str(row.get("reason", "")),
                })
            if candidates:
                score += 10
                reasons.append("มีตัวเลือกจาก strategy ที่ผ่านเงื่อนไขเบื้องต้น")
        else:
            reasons.append("ยังไม่พบตัวเลือกที่ผ่านเงื่อนไข strategy")
    else:
        score -= 5
        reasons.append("ยังไม่มี strategy_modes.csv สำหรับช่วยเลือกหุ้น")

    score = max(0, min(100, score))

    if score >= 70:
        verdict = "น่าสนใจ แต่ซื้อได้แค่ไม้เล็ก"
        action = "ซื้อได้แบบระวัง"
    elif score >= 40:
        verdict = "รอดู ยังไม่ต้องรีบซื้อ"
        action = "รอ"
    else:
        verdict = "ยังไม่ควรซื้อเพิ่ม"
        action = "ห้ามซื้อเพิ่มตอนนี้"

    return {
        "score": score,
        "verdict": verdict,
        "action": action,
        "reasons": reasons,
        "candidates": candidates,
        "market_change_spy": market_change,
    }


def format_buy_advice(advice: dict[str, Any]) -> str:
    lines = [
        "🎯 Buy Readiness",
        f"Score: {advice['score']}/100",
        f"Action: {advice['action']}",
        f"สรุป: {advice['verdict']}",
        "",
        "เหตุผล:",
    ]
    for reason in advice.get("reasons", []):
        lines.append(f"- {reason}")

    candidates = advice.get("candidates", [])
    if candidates:
        lines.append("\nตัวที่น่าดู:")
        for c in candidates:
            lines.append(f"- {c['ticker']} ({c['mode']}) Alpha {c['alpha_pct']:+.2f}%")
    else:
        lines.append("\nยังไม่มีตัวที่น่าซื้อชัดเจน")
    return "\n".join(lines)


if __name__ == "__main__":
    print(format_buy_advice(build_buy_advice()))
