import os
import requests

from money_tracker import ensure_portfolio_file, summarize_money, format_money_summary

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")


def send_money_summary_to_discord():
    portfolio = ensure_portfolio_file()
    summary = summarize_money(portfolio)
    message = format_money_summary(summary)

    if not WEBHOOK_URL:
        print(message)
        print("\n⚠️ ยังไม่ได้ตั้ง DISCORD_WEBHOOK เลยพิมพ์สรุปใน terminal แทน")
        return

    response = requests.post(WEBHOOK_URL, json={"content": message})
    if response.status_code in [200, 204]:
        print("✅ ส่ง Money Summary เข้า Discord สำเร็จ")
    else:
        print(f"❌ ส่ง Discord ไม่สำเร็จ: {response.status_code} {response.text}")


if __name__ == "__main__":
    send_money_summary_to_discord()
