from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from decision_tracker import load_decision_log

INVESTOR_MEMORY_FILE = Path("investor_memory.json")

DEFAULT_MEMORY: dict[str, Any] = {
    "risk_tolerance": "medium",
    "preferred_style": "learning_first",
    "preferred_assets": ["tech", "ai", "funds"],
    "avoid_notes": ["ไม่ชอบความผันผวนสูงเกินไป", "ไม่ควร all-in"],
    "gold_behavior": "ขายทองเท่าทุนเพราะรู้สึกว่าผันผวนเกิน รอจังหวะย่อลึกก่อนกลับเข้าใหม่",
    "buy_style": "แบ่งไม้เล็ก / DCA / รอจังหวะ ไม่ไล่ราคา",
    "goal_notes": [
        "เรียนรู้การลงทุนจากเงินจริงจำนวนน้อย",
        "ทำ AI portfolio dashboard ให้ฉลาดขึ้น",
        "รักษาเงินสดไว้บางส่วนเพราะมีภาระผ่อนรถและรายได้เสริม"
    ],
    "manual_notes": [],
}


def load_investor_memory(path: Path = INVESTOR_MEMORY_FILE) -> dict[str, Any]:
    if not path.exists():
        save_investor_memory(DEFAULT_MEMORY, path)
        return DEFAULT_MEMORY.copy()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return DEFAULT_MEMORY.copy()

    memory = DEFAULT_MEMORY.copy()
    memory.update(data)
    return memory


def save_investor_memory(memory: dict[str, Any], path: Path = INVESTOR_MEMORY_FILE) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)


def infer_memory_from_logs(memory: dict[str, Any] | None = None) -> dict[str, Any]:
    memory = memory or load_investor_memory()
    logs = load_decision_log()
    recent_text = "\n".join(
        f"{x.get('question', '')}\n{x.get('answer', '')}\n{x.get('note', '')}"
        for x in logs[-20:]
    ).lower()

    inferred_notes = []

    if any(word in recent_text for word in ["ทอง", "gold", "gc=f", "ผันผวน"]):
        inferred_notes.append("มีประสบการณ์กับทองแล้ว และค่อนข้างระวังความผันผวน")

    if any(word in recent_text for word in ["tech", "ai", "msft", "nvda", "sndk"]):
        inferred_notes.append("สนใจหุ้นเทคโนโลยีและ AI")

    if any(word in recent_text for word in ["dca", "แบ่งไม้", "ไม้เล็ก", "รอ"]):
        inferred_notes.append("เหมาะกับการทยอยซื้อแบบแบ่งไม้มากกว่าซื้อก้อนใหญ่")

    if any(word in recent_text for word in ["ขาดทุน", "เสี่ยง", "กลัว", "เครียด"]):
        memory["risk_tolerance"] = "medium_low"
        inferred_notes.append("ควรลดคำแนะนำที่เสี่ยงเกินไป และเน้นเงินเย็น")

    memory["inferred_notes"] = list(dict.fromkeys(inferred_notes))
    return memory


def format_investor_memory(memory: dict[str, Any] | None = None) -> str:
    memory = infer_memory_from_logs(memory)

    preferred_assets = ", ".join(memory.get("preferred_assets", [])) or "ยังไม่ชัด"
    avoid_notes = " / ".join(memory.get("avoid_notes", [])) or "ไม่มี"
    goal_notes = " / ".join(memory.get("goal_notes", [])) or "ไม่มี"
    inferred_notes = " / ".join(memory.get("inferred_notes", [])) or "ยังไม่มี pattern จาก log"
    manual_notes = " / ".join(memory.get("manual_notes", [])) or "ไม่มี"

    return f"""
Investor Memory ของคุณ Soul:
- Risk tolerance: {memory.get('risk_tolerance', 'medium')}
- Preferred style: {memory.get('preferred_style', 'learning_first')}
- Preferred assets: {preferred_assets}
- Buy style: {memory.get('buy_style', 'แบ่งไม้เล็ก / DCA')}
- Gold behavior: {memory.get('gold_behavior', 'ยังไม่มีข้อมูล')}
- Avoid notes: {avoid_notes}
- Goal notes: {goal_notes}
- Inferred notes from logs: {inferred_notes}
- Manual notes: {manual_notes}
""".strip()


def add_manual_memory_note(note: str) -> dict[str, Any]:
    memory = load_investor_memory()
    notes = memory.setdefault("manual_notes", [])
    clean_note = note.strip()
    if clean_note and clean_note not in notes:
        notes.append(clean_note)
    save_investor_memory(memory)
    return memory


if __name__ == "__main__":
    print(format_investor_memory())
