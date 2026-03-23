def notify_discord(result: AnalysisResult, ai_insight: str):
    """ส่งข้อความพร้อมรูปเข้า Discord (แบบแก้บั๊กแล้ว)"""
    color = 0x2ecc71 if result.action == Action.BUY else \
            0xe74c3c if result.action == Action.SELL else 0xf1c40f

    payload = {
        "embeds": [{
            "title": f"🤖 AI Analyst Report: {result.ticker}",
            "description": ai_insight,
            "color": color,
            "image": {"url": "attachment://chart.png"}, # ต้องมีบรรทัดนี้เพื่อโชว์รูป
            "fields": [
                {"name": "💰 Price", "value": f"**{result.current_price:,.2f}**", "inline": True},
                {"name": "📊 RSI", "value": f"**{result.rsi_14}**", "inline": True},
                {"name": "📉 MACD", "value": f"**{result.macd_hist}**", "inline": True},
                {"name": "🎯 Decision", "value": f"**{result.action.value}**", "inline": True}
            ],
            "footer": {"text": f"Analysis at: {result.timestamp}"}
        }]
    }

    try:
        with open("chart.png", "rb") as f:
            # เตรียมไฟล์ส่ง
            files = {"file": ("chart.png", f, "image/png")}
            # ส่ง payload พร้อมไฟล์ในครั้งเดียว (ห้ามส่งแยก!)
            response = requests.post(
                WEBHOOK_URL,
                data={"payload_json": json.dumps(payload)},
                files=files
            )
            
        if response.status_code in [200, 204]:
            print(f"✅ [Discord] ส่งรายงาน {result.ticker} พร้อมรูปสำเร็จ")
        else:
            print(f"❌ [Discord] ส่งไม่สำเร็จ: {response.text}")
    except Exception as e:
        print(f"❌ [Discord] เกิดข้อผิดพลาด: {e}")

def create_chart(df, ticker):
    """ฟังก์ชันสร้างกราฟ (แบบแก้บั๊กแล้ว)"""
    plt.figure(figsize=(10, 5))
    plt.style.use('dark_background')
    # แก้ไขจุดเป็นคอมม่าตรง df.index, df['close']
    plt.plot(df.index[-30:], df['close'].tail(30), color='#00ff00', linewidth=2)
    plt.title(f"{ticker} Price Action (Last 30 Days)")
    plt.grid(True, alpha=0.2)
    plt.savefig('chart.png') # เซฟไฟล์
    plt.close() # ปิดเพื่อเคลียร์แรม