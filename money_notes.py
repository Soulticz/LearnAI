from typing import Any

from money_tracker import ensure_portfolio_file, summarize_money


def build_money_notes(summary: dict[str, Any] | None = None) -> list[str]:
    summary = summary or summarize_money(ensure_portfolio_file())
    notes: list[str] = []

    for asset in summary.get("assets", []):
        ticker = asset.get("ticker", "UNKNOWN")
        pnl_pct = asset.get("pnl_pct")
        action = asset.get("action", "รอดู")

        if pnl_pct is None:
            notes.append(f"⚪ {ticker}: ยังไม่มีข้อมูล P/L ชัดเจน")
            continue

        if pnl_pct <= -10:
            notes.append(f"🔴 {ticker}: ขาดทุน {pnl_pct:.2f}% — ระวัง อย่าเติมเงินแก้มือทันที")
        elif pnl_pct <= -5:
            notes.append(f"🟠 {ticker}: ติดลบ {pnl_pct:.2f}% — เฝ้าดูใกล้ชิด")
        elif pnl_pct >= 10:
            notes.append(f"🟢 {ticker}: กำไร {pnl_pct:.2f}% — พิจารณาล็อกกำไรบางส่วน")
        elif pnl_pct >= 5:
            notes.append(f"🟡 {ticker}: กำไร {pnl_pct:.2f}% — ถือได้แต่ระวังย่อ")
        else:
            notes.append(f"⚪ {ticker}: {pnl_pct:+.2f}% — {action}")

    if not summary.get("assets"):
        notes.append("ยังไม่ได้กรอกหุ้น/ทองใน personal_portfolio.json")

    return notes


def format_money_notes(summary: dict[str, Any] | None = None) -> str:
    notes = build_money_notes(summary)
    return "🔔 Money Notes\n" + "\n".join(f"- {note}" for note in notes)


if __name__ == "__main__":
    print(format_money_notes())
