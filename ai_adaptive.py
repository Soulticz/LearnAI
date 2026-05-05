from decision_tracker import load_decision_log, summarize_decisions


def get_ai_adaptive_profile() -> dict:
    """อ่านผลย้อนหลังของ AI แล้วกำหนดโหมดความระวัง

    ใช้เพื่อปรับคำแนะนำให้ conservative/aggressive ขึ้นตามผลงานจริง
    """
    logs = load_decision_log()
    summary = summarize_decisions(logs)

    evaluated = summary.get("evaluated", 0)
    win_rate = summary.get("win_rate", 0)
    bad = summary.get("bad", 0)

    if evaluated < 5:
        mode = "LEARNING"
        adjustment = "ข้อมูลยังน้อย ให้ระวังไว้ก่อน"
        buy_score_offset = -5
    elif win_rate >= 70 and bad <= 2:
        mode = "CONFIDENT"
        adjustment = "AI เคยตัดสินใจได้ดีพอสมควร แต่ยังต้องแบ่งไม้"
        buy_score_offset = 5
    elif win_rate < 45 or bad >= 3:
        mode = "CONSERVATIVE"
        adjustment = "AI เคยพลาดหลายครั้ง ให้ลดความเสี่ยงและรอ confirmation"
        buy_score_offset = -15
    else:
        mode = "BALANCED"
        adjustment = "ผลงาน AI กลาง ๆ ใช้ตามระบบปกติ"
        buy_score_offset = 0

    return {
        "mode": mode,
        "adjustment": adjustment,
        "buy_score_offset": buy_score_offset,
        "summary": summary,
    }


def apply_adaptive_score(base_score: int) -> int:
    profile = get_ai_adaptive_profile()
    adjusted = int(base_score) + int(profile.get("buy_score_offset", 0))
    return max(0, min(100, adjusted))


if __name__ == "__main__":
    print(get_ai_adaptive_profile())
