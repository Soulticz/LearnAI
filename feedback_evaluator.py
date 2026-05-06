from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from decision_tracker import load_decision_log, save_decision_log
from money_tracker import get_latest_price

POSITIVE_ACTIONS = ["BUY", "BUY_SMALL", "ACCUMULATE", "HOLD", "STRONG_BUY"]
DEFENSIVE_ACTIONS = ["WAIT", "AVOID", "SELL", "TAKE_PROFIT", "REDUCE"]


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None

    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def normalize_action(action: str | None) -> str:
    text = str(action or "").upper().strip()

    if any(word in text for word in ["BUY", "ซื้อ", "ACCUMULATE", "HOLD", "ถือ"]):
        return "POSITIVE"

    if any(word in text for word in ["WAIT", "รอ", "AVOID", "SELL", "ขาย", "REDUCE", "TAKE"]):
        return "DEFENSIVE"

    return "UNKNOWN"


def evaluate_result(action: str | None, return_pct: float, threshold_pct: float = 3.0) -> str:
    action_type = normalize_action(action)

    if action_type == "POSITIVE":
        if return_pct >= threshold_pct:
            return "GOOD"
        if return_pct <= -threshold_pct:
            return "BAD"
        return "NEUTRAL"

    if action_type == "DEFENSIVE":
        if return_pct <= -threshold_pct:
            return "GOOD"
        if return_pct >= threshold_pct:
            return "BAD"
        return "NEUTRAL"

    return "NEUTRAL"


def auto_evaluate_decisions(days_after: int = 7, threshold_pct: float = 3.0) -> dict[str, Any]:
    """Evaluate pending AI decisions automatically.

    Required fields per decision:
    - ticker
    - price_at_decision
    - action
    - timestamp

    Old logs without these fields are skipped safely.
    """
    logs = load_decision_log()
    now = datetime.now()

    updated = 0
    skipped = 0

    for item in logs:
        if item.get("result") not in [None, "", "PENDING"]:
            skipped += 1
            continue

        ticker = str(item.get("ticker", "")).upper().strip()
        price_at_decision = item.get("price_at_decision")
        action = item.get("action")
        created_at = parse_timestamp(item.get("timestamp"))

        if not ticker or not price_at_decision or not action or created_at is None:
            item["auto_eval_note"] = "SKIPPED: missing ticker, price_at_decision, action, or timestamp"
            skipped += 1
            continue

        if now < created_at + timedelta(days=days_after):
            item["auto_eval_note"] = f"WAITING: need {days_after} days after decision"
            skipped += 1
            continue

        current_price = get_latest_price(ticker)
        if current_price is None:
            item["auto_eval_note"] = "SKIPPED: cannot fetch current price"
            skipped += 1
            continue

        price_at_decision = float(price_at_decision)
        return_pct = ((current_price - price_at_decision) / price_at_decision) * 100
        result = evaluate_result(action, return_pct, threshold_pct)

        item["price_after_eval"] = round(float(current_price), 4)
        item["return_after_eval_pct"] = round(return_pct, 2)
        item["eval_days_after"] = days_after
        item["eval_threshold_pct"] = threshold_pct
        item["result"] = result
        item["auto_eval_note"] = (
            f"AUTO: {ticker} {action} from {price_at_decision:.4f} "
            f"to {current_price:.4f} = {return_pct:+.2f}% => {result}"
        )
        updated += 1

    save_decision_log(logs)

    return {
        "total": len(logs),
        "updated": updated,
        "skipped": skipped,
        "days_after": days_after,
        "threshold_pct": threshold_pct,
    }


if __name__ == "__main__":
    print(auto_evaluate_decisions())
