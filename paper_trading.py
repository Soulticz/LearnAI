import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime

import pandas as pd

PORTFOLIO_FILE = "paper_portfolio.json"
STRATEGY_FILE = "strategy_modes.csv"
INITIAL_CASH = 100000.0
TRADE_FEE_RATE = 0.001
MAX_POSITION_RATIO = 0.25  # ต่อ 1 ตัว ใช้เงินไม่เกิน 25% ของพอร์ต
STOP_LOSS_PCT = 0.05       # cut loss 5% จากราคาเฉลี่ย
TAKE_PROFIT_PCT = 0.05     # กำไร 5% ขายครึ่ง
TAKE_PROFIT_FULL = 0.10    # กำไร 10% ขายหมด


@dataclass
class PaperTrade:
    timestamp: str
    ticker: str
    action: str
    price: float
    shares: float
    cash_after: float
    reason: str


def default_portfolio():
    return {
        "cash": INITIAL_CASH,
        "positions": {},
        "trades": [],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def load_portfolio(path: str = PORTFOLIO_FILE) -> dict:
    if not os.path.exists(path):
        portfolio = default_portfolio()
        save_portfolio(portfolio, path)
        return portfolio

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_portfolio(portfolio: dict, path: str = PORTFOLIO_FILE):
    portfolio["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, ensure_ascii=False, indent=2)


def load_strategy_modes(path: str = STRATEGY_FILE) -> dict:
    if not os.path.exists(path):
        print(f"⚠️ ไม่พบ {path} กรุณารัน python strategy_selector.py ก่อน")
        return {}

    df = pd.read_csv(path)
    return {
        str(row["ticker"]).upper(): {
            "mode": str(row["mode"]),
            "reason": str(row["reason"]),
        }
        for _, row in df.iterrows()
    }


def portfolio_value(portfolio: dict, latest_prices: dict[str, float] | None = None) -> float:
    latest_prices = latest_prices or {}
    value = float(portfolio.get("cash", 0.0))

    for ticker, pos in portfolio.get("positions", {}).items():
        price = latest_prices.get(ticker, pos.get("last_price", pos.get("avg_price", 0)))
        value += float(pos.get("shares", 0)) * float(price)

    return value


def paper_buy(portfolio: dict, ticker: str, price: float, reason: str):
    ticker = ticker.upper()
    cash = float(portfolio.get("cash", 0.0))
    total_value = portfolio_value(portfolio, {ticker: price})
    budget = min(cash, total_value * MAX_POSITION_RATIO)

    if budget <= 0:
        return False, "เงินสดไม่พอสำหรับซื้อ"

    cost_after_fee = budget * (1 - TRADE_FEE_RATE)
    shares = cost_after_fee / price

    if shares <= 0:
        return False, "จำนวนหุ้นที่ซื้อได้เป็น 0"

    pos = portfolio["positions"].get(ticker, {"shares": 0.0, "avg_price": 0.0, "last_price": price})
    old_shares = float(pos.get("shares", 0.0))
    old_avg = float(pos.get("avg_price", 0.0))
    new_shares = old_shares + shares
    new_avg = ((old_shares * old_avg) + (shares * price)) / new_shares

    portfolio["cash"] = cash - budget
    portfolio["positions"][ticker] = {
        "shares": new_shares,
        "avg_price": new_avg,
        "last_price": price,
        "stop_loss": new_avg * (1 - STOP_LOSS_PCT),
        "take_profit_half_done": bool(pos.get("take_profit_half_done", False)),
    }

    trade = PaperTrade(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ticker=ticker,
        action="BUY",
        price=price,
        shares=shares,
        cash_after=portfolio["cash"],
        reason=reason,
    )
    portfolio["trades"].append(asdict(trade))
    return True, f"BUY {ticker} {shares:.4f} shares at {price:.2f} | Stop Loss {new_avg * (1 - STOP_LOSS_PCT):.2f}"


def paper_sell(portfolio: dict, ticker: str, price: float, reason: str):
    ticker = ticker.upper()
    pos = portfolio.get("positions", {}).get(ticker)
    if not pos:
        return False, "ไม่มี position ให้ขาย"

    shares = float(pos.get("shares", 0.0))
    if shares <= 0:
        return False, "จำนวนหุ้นเป็น 0"

    gross = shares * price
    net = gross * (1 - TRADE_FEE_RATE)
    portfolio["cash"] = float(portfolio.get("cash", 0.0)) + net
    del portfolio["positions"][ticker]

    trade = PaperTrade(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ticker=ticker,
        action="SELL",
        price=price,
        shares=shares,
        cash_after=portfolio["cash"],
        reason=reason,
    )
    portfolio["trades"].append(asdict(trade))
    return True, f"SELL {ticker} {shares:.4f} shares at {price:.2f}"


def paper_sell_half(portfolio: dict, ticker: str, price: float, reason: str):
    ticker = ticker.upper()
    pos = portfolio.get("positions", {}).get(ticker)
    if not pos:
        return False, "ไม่มี position ให้ขายครึ่ง"

    current_shares = float(pos.get("shares", 0.0))
    shares_to_sell = current_shares / 2
    if shares_to_sell <= 0:
        return False, "จำนวนหุ้นเป็น 0"

    gross = shares_to_sell * price
    net = gross * (1 - TRADE_FEE_RATE)
    portfolio["cash"] = float(portfolio.get("cash", 0.0)) + net
    pos["shares"] = current_shares - shares_to_sell
    pos["last_price"] = price
    pos["take_profit_half_done"] = True

    if pos["shares"] <= 0:
        del portfolio["positions"][ticker]

    trade = PaperTrade(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ticker=ticker,
        action="SELL_HALF",
        price=price,
        shares=shares_to_sell,
        cash_after=portfolio["cash"],
        reason=reason,
    )
    portfolio["trades"].append(asdict(trade))
    return True, f"SELL HALF {ticker} {shares_to_sell:.4f} shares at {price:.2f}"


def update_last_price(portfolio: dict, ticker: str, price: float):
    ticker = ticker.upper()
    if ticker in portfolio.get("positions", {}):
        portfolio["positions"][ticker]["last_price"] = price


def apply_signal(ticker: str, action_value: str, price: float, strategy_mode: str, strategy_reason: str):
    """ใช้ signal จาก stock_bot มาจำลองซื้อขาย

    กติกาแรก:
    - Stop Loss: ถ้าราคาหลุด stop loss ให้ขายก่อน logic อื่น
    - Take Profit: +10% ขายหมด, +5% ขายครึ่งหนึ่งครั้ง
    - HYBRID: ทำตาม BUY/SELL จาก AI
    - WATCH: ยังไม่ซื้อ แต่ถ้ามี position แล้วเจอ SELL ให้ขายลดเสี่ยง
    - HOLD: ไม่ขายตามสัญญาณสั้น ๆ และไม่เปิด position ใหม่จาก paper bot
    - AVOID: ถ้ามี position ให้ขายออกเมื่อเจอ SELL หรือเลี่ยงไม่ซื้อใหม่
    """
    portfolio = load_portfolio()
    update_last_price(portfolio, ticker, price)

    ticker = ticker.upper()
    strategy_mode = (strategy_mode or "UNKNOWN").upper()
    action_text = action_value or ""

    executed = False
    message = "No action"
    reason = f"{strategy_mode}: {strategy_reason} | Signal: {action_value}"

    position = portfolio.get("positions", {}).get(ticker)

    # Stop loss ต้องมาก่อนทุก logic
    if position:
        stop_loss = float(position.get("stop_loss", 0.0))
        if stop_loss > 0 and price <= stop_loss:
            executed, message = paper_sell(
                portfolio,
                ticker,
                price,
                reason=f"Stop Loss Triggered: price {price:.2f} <= stop {stop_loss:.2f}",
            )
            save_portfolio(portfolio)
            return executed, message, portfolio

    # Take profit มาก่อน signal ปกติ เพื่อ lock กำไร
    position = portfolio.get("positions", {}).get(ticker)
    if position:
        avg_price = float(position.get("avg_price", 0.0))
        if avg_price > 0:
            profit_pct = (price - avg_price) / avg_price

            if profit_pct >= TAKE_PROFIT_FULL:
                executed, message = paper_sell(
                    portfolio,
                    ticker,
                    price,
                    reason=f"Take Profit FULL: +{profit_pct * 100:.2f}%",
                )
                save_portfolio(portfolio)
                return executed, message, portfolio

            if profit_pct >= TAKE_PROFIT_PCT and not bool(position.get("take_profit_half_done", False)):
                executed, message = paper_sell_half(
                    portfolio,
                    ticker,
                    price,
                    reason=f"Take Profit HALF: +{profit_pct * 100:.2f}%",
                )
                save_portfolio(portfolio)
                return executed, message, portfolio

    is_buy_signal = "ซื้อ" in action_text or "BUY" in action_text.upper()
    is_sell_signal = "ขาย" in action_text or "SELL" in action_text.upper()

    if strategy_mode == "HYBRID":
        if is_buy_signal and ticker not in portfolio.get("positions", {}):
            executed, message = paper_buy(portfolio, ticker, price, reason)
        elif is_sell_signal and ticker in portfolio.get("positions", {}):
            executed, message = paper_sell(portfolio, ticker, price, reason)
    elif strategy_mode == "WATCH":
        if is_sell_signal and ticker in portfolio.get("positions", {}):
            executed, message = paper_sell(portfolio, ticker, price, reason)
        else:
            message = "WATCH mode: รอสัญญาณชัดขึ้น ยังไม่เปิด position ใหม่"
    elif strategy_mode == "HOLD":
        message = "HOLD mode: ถือยาวเป็นหลัก ไม่ให้ paper bot เข้าออกสั้น"
    elif strategy_mode == "AVOID":
        if is_sell_signal and ticker in portfolio.get("positions", {}):
            executed, message = paper_sell(portfolio, ticker, price, reason)
        else:
            message = "AVOID mode: เลี่ยง ไม่ซื้อใหม่"

    save_portfolio(portfolio)
    return executed, message, portfolio


def format_portfolio_summary(portfolio: dict) -> str:
    positions = portfolio.get("positions", {})
    lines = [
        "📒 Paper Portfolio",
        f"Cash: {float(portfolio.get('cash', 0.0)):,.2f}",
        f"Positions: {len(positions)}",
    ]

    for ticker, pos in positions.items():
        shares = float(pos.get("shares", 0))
        avg_price = float(pos.get("avg_price", 0))
        last_price = float(pos.get("last_price", avg_price))
        stop_loss = float(pos.get("stop_loss", 0))
        pnl = ((last_price - avg_price) / avg_price * 100) if avg_price else 0
        lines.append(
            f"- {ticker}: {shares:.4f} @ {avg_price:.2f} | Last {last_price:.2f} | "
            f"Stop {stop_loss:.2f} | P/L {pnl:+.2f}%"
        )

    return "\n".join(lines)


if __name__ == "__main__":
    portfolio = load_portfolio()
    print(format_portfolio_summary(portfolio))
