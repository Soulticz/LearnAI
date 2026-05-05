import json
from datetime import datetime
from pathlib import Path
from typing import Any

DECISION_LOG_FILE = Path("ai_decision_log.json")


def load_decision_log(path: Path = DECISION_LOG_FILE) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_decision_log(logs: list[dict[str, Any]], path: Path = DECISION_LOG_FILE):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)


def log_ai_decision(
    source: str,
    question: str,
    answer: str,
    buy_score: int | None = None,
    action: str | None = None,
    total_thb: float | None = None,
):
    logs = load_decision_log()
    logs.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": source,
        "question": question,
        "answer": answer,
        "buy_score": buy_score,
        "action": action,
        "total_thb": total_thb,
        "result": "PENDING",
        "note": "",
    })
    save_decision_log(logs)


def update_decision_result(index: int, result: str, note: str = ""):
    logs = load_decision_log()
    if 0 <= index < len(logs):
        logs[index]["result"] = result
        logs[index]["note"] = note
        save_decision_log(logs)
        return True
    return False


def summarize_decisions(logs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    logs = logs if logs is not None else load_decision_log()
    total = len(logs)
    done = [x for x in logs if x.get("result") not in [None, "", "PENDING"]]
    wins = [x for x in done if x.get("result") == "GOOD"]
    bads = [x for x in done if x.get("result") == "BAD"]
    neutrals = [x for x in done if x.get("result") == "NEUTRAL"]
    win_rate = (len(wins) / len(done) * 100) if done else 0
    return {
        "total": total,
        "evaluated": len(done),
        "pending": total - len(done),
        "good": len(wins),
        "bad": len(bads),
        "neutral": len(neutrals),
        "win_rate": win_rate,
    }


if __name__ == "__main__":
    print(summarize_decisions())
