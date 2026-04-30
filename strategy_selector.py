import os
from dataclasses import dataclass

import pandas as pd

SUMMARY_FILE = "backtest_summary.csv"
OUTPUT_FILE = "strategy_modes.csv"

# เกณฑ์ปรับได้ตามสไตล์ความเสี่ยงของคุณ
HYBRID_ALPHA_MIN = 5.0          # Hybrid ต้องชนะ Buy & Hold อย่างน้อย 5%
HYBRID_DRAWDOWN_LIMIT = -45.0   # Hybrid drawdown ห้ามแย่กว่า -45%
HOLD_BUYHOLD_MIN = 10.0         # ถ้า Buy & Hold ยังบวกดี ให้ถือยาวมากกว่า
AVOID_DRAWDOWN_LIMIT = -50.0    # Drawdown แย่มากให้เลี่ยง
AVOID_RETURN_LIMIT = -20.0      # Hybrid return แย่มากให้เลี่ยง


@dataclass
class StrategyDecision:
    ticker: str
    mode: str
    reason: str
    ai_return_pct: float
    hybrid_return_pct: float
    buy_hold_pct: float
    hybrid_alpha_vs_hold_pct: float
    hybrid_max_drawdown_pct: float


def decide_strategy(row: pd.Series) -> StrategyDecision:
    ticker = str(row["ticker"])
    ai_return = float(row.get("ai_return_pct", 0))
    hybrid_return = float(row.get("hybrid_return_pct", 0))
    buy_hold = float(row.get("buy_hold_pct", 0))
    hybrid_alpha = float(row.get("hybrid_alpha_vs_hold_pct", hybrid_return - buy_hold))
    hybrid_dd = float(row.get("hybrid_max_drawdown_pct", row.get("max_drawdown_pct", 0)))

    if hybrid_dd <= AVOID_DRAWDOWN_LIMIT or hybrid_return <= AVOID_RETURN_LIMIT:
        mode = "AVOID"
        reason = (
            f"ความเสี่ยงสูง: Hybrid return {hybrid_return:+.2f}% "
            f"และ drawdown {hybrid_dd:.2f}%"
        )
    elif hybrid_alpha >= HYBRID_ALPHA_MIN and hybrid_dd > HYBRID_DRAWDOWN_LIMIT:
        mode = "HYBRID"
        reason = (
            f"Hybrid ชนะ Buy & Hold {hybrid_alpha:+.2f}% "
            f"โดย drawdown {hybrid_dd:.2f}%"
        )
    elif buy_hold > hybrid_return and buy_hold >= HOLD_BUYHOLD_MIN:
        mode = "HOLD"
        reason = (
            f"Buy & Hold ดีกว่า Hybrid: B&H {buy_hold:+.2f}% "
            f"vs Hybrid {hybrid_return:+.2f}%"
        )
    elif hybrid_return > 0:
        mode = "WATCH"
        reason = (
            f"Hybrid ยังบวก {hybrid_return:+.2f}% แต่ยังไม่ชนะตลาดชัดเจน"
        )
    else:
        mode = "AVOID"
        reason = f"ผลรวมยังไม่น่าไว้ใจ: Hybrid {hybrid_return:+.2f}%"

    return StrategyDecision(
        ticker=ticker,
        mode=mode,
        reason=reason,
        ai_return_pct=ai_return,
        hybrid_return_pct=hybrid_return,
        buy_hold_pct=buy_hold,
        hybrid_alpha_vs_hold_pct=hybrid_alpha,
        hybrid_max_drawdown_pct=hybrid_dd,
    )


def load_summary(path: str = SUMMARY_FILE) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"ไม่พบ {path} กรุณารัน python backtest.py ก่อน เพื่อสร้างไฟล์นี้"
        )
    return pd.read_csv(path)


def build_strategy_modes(summary_path: str = SUMMARY_FILE, output_path: str = OUTPUT_FILE) -> pd.DataFrame:
    summary = load_summary(summary_path)
    decisions = [decide_strategy(row).__dict__ for _, row in summary.iterrows()]
    df = pd.DataFrame(decisions)

    order = {"HYBRID": 0, "HOLD": 1, "WATCH": 2, "AVOID": 3}
    df["mode_order"] = df["mode"].map(order).fillna(99)
    df = df.sort_values(["mode_order", "hybrid_alpha_vs_hold_pct"], ascending=[True, False])
    df = df.drop(columns=["mode_order"])
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    return df


def get_strategy_mode(ticker: str, summary_path: str = SUMMARY_FILE) -> StrategyDecision | None:
    summary = load_summary(summary_path)
    row = summary[summary["ticker"].str.upper() == ticker.upper()]
    if row.empty:
        return None
    return decide_strategy(row.iloc[0])


def print_summary(df: pd.DataFrame):
    print("\n========== Strategy Selector ==========")
    for mode in ["HYBRID", "HOLD", "WATCH", "AVOID"]:
        group = df[df["mode"] == mode]
        if group.empty:
            continue
        tickers = ", ".join(group["ticker"].tolist())
        print(f"\n{mode} ({len(group)}): {tickers}")

    print("\n---------- Detail ----------")
    print(df.to_string(index=False, formatters={
        "ai_return_pct": "{:+.2f}".format,
        "hybrid_return_pct": "{:+.2f}".format,
        "buy_hold_pct": "{:+.2f}".format,
        "hybrid_alpha_vs_hold_pct": "{:+.2f}".format,
        "hybrid_max_drawdown_pct": "{:.2f}".format,
    }))
    print(f"\n💾 Saved strategy modes to {OUTPUT_FILE}")


if __name__ == "__main__":
    modes = build_strategy_modes()
    print_summary(modes)
