from curl_cffi import request
import yfinance as yf
import pandas as pd
import pickle
import ta as ta_lib
from fx_analyzer import analyze_all_fx, format_fx_message
import requests
import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import os
import anthropic
import matplotlib.pyplot as plt
from signal_log import save_signal, evaluate_old_signals, retrain_if_needed
class Action(Enum):
    BUY = "🟢 ซื้อเพิ่ม (Oversold)"
    SELL = "🔴 ขายทำกำไร (Overbought)"
    HOLD = "🟡 ถือไว้ก่อน (Neutral)"

@dataclass
class AnalysisResult:
    ticker: str
    action: Action 
    current_price: float
    macd_hist: float
    rsi_14: float
    timestamp: str
    df_history: pd.DataFrame # เก็บข้อมูลไว้ทำกราฟ

# --- Configuration ---
TICKER = os.getenv("TICKER_SYMBOL", "^GSPC,GC=F,BTC-USD,NVDA")
watchlist = [t.strip() for t in TICKER.split(",")]
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
#GEMINI_KEY = os.getenv("GEMINI_API_KEY") # เช็คชื่อตัวแปรใน GitHub ให้ตรงนะครับ
#client = genai.Client(api_key=GEMINI_KEY)
cliant = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
try:
    with open("model.pkl", "rb") as f:
        saved = pickle.load(f)
        ML_MODEL = saved["model"]
    print("✅ โหลดโมเดลสำเร็จ")
except FileNotFoundError:
    print("❌ ไม่พบไฟล์ model.pkl")
    ML_MODEL = None
    print("⚠️  ระบบจะทำงานในโหมด AI Only (ไม่มีการใช้ ML)")

def ask_claude(result: AnalysisResult):
    prompt = f"""
    คุณคือผู้เชี่ยวชาญด้านการลงทุน วิเคราะห์หุ้น {result.ticker} จากข้อมูล:
    - ราคาปัจจุบัน: {result.current_price}
    - RSI: {result.rsi_14}
    - MACD: {result.macd_hist}
    - สัญญาณระบบ: {result.action.value}
    หากเป็นทองคำ (GC=F) ให้เน้นวิเคราะห์ความผันผวนด้วย 
    สรุป 3 ข้อสั้นๆ (ภาษาไทยกันเอง) แนะนำกลยุทธ์ ซื้อ/ขาย/ถือ
    """
    try:
        # ใช้โมเดล 1.5-flash เพื่อความเสถียรและฟรี
        response = cliant.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            messages=[
                {"role": "user", "content":prompt}
            ]
        )
        return response.content[0].text
    except Exception as e:
        return f"เกิดข้อผิดพลาดในการวิเคราะห์ AI: {str(e)}"

def notify_discord(result: AnalysisResult, ai_insight: str):
    """ส่งข้อความพร้อมรูปเข้า Discord"""
    color = 0x2ecc71 if result.action == Action.BUY else \
            0xe74c3c if result.action == Action.SELL else 0xf1c40f

    # สร้าง Payload สำหรับ Embed
    payload = {
        "embeds": [{
            "title": f"🤖 AI Analyst Report: {result.ticker}",
            "description": ai_insight,
            "color": color,
            "image": {"url": "attachment://chart.png"}, # อ้างอิงไฟล์ภาพ
            "fields": [
                {"name": "💰 Price", "value": f"**{result.current_price:,.2f}**", "inline": True},
                {"name": "📊 RSI", "value": f"**{result.rsi_14}**", "inline": True},
                {"name": "📉 MACD", "value": f"**{result.macd_hist}**", "inline": True},
                {"name": "🎯 Decision", "value": f"**{result.action.value}**", "inline": True}
            ],
            "footer": {"text": f"Analysis at: {result.timestamp}"},
            "thumbnail": {"url": "https://cdn-icons-png.flaticon.com/512/2422/2422796.png"}
        }]
    }

    try:
        # เปิดไฟล์ภาพและส่งไปพร้อมกับ JSON ในก้อนเดียว
        with open("chart.png", "rb") as f:
            files = {
                "file": ("chart.png", f, "image/png")
            }
            # ส่งแบบ Multipart form-data
            response = requests.post(
                WEBHOOK_URL,
                data={"payload_json": json.dumps(payload)},
                files=files
            )
            
        if response.status_code in [200, 204]:
            print("✅ ส่ง Discord พร้อมรูปสำเร็จ!")
        else:
            print(f"❌ ส่ง Discord ไม่สำเร็จ: {response.status_code} {response.text}")
    except FileNotFoundError:
        print("❌ ไม่พบไฟล์ chart.png!")
def create_chart(df, ticker):
    """ฟังก์ชันสร้างกราฟ"""
    plt.figure(figsize=(10, 5))
    plt.style.use('dark_background') # เปลี่ยนเป็น Dark Mode ให้ดูโปร
    plt.plot(df.index[-30:], df['close'].tail(30), color='#00ff00', linewidth=2)
    plt.title(f"{ticker} Price Action (Last 30 Days)")
    plt.grid(True, alpha=0.3)
    plt.savefig('chart.png')
    plt.close()
def analyze_market(ticker_symbol: str) -> AnalysisResult:
    df = yf.download(ticker_symbol, period="6mo", progress=False)
    if df.empty: raise ValueError("ไม่พบข้อมูลหุ้น")
    
    # จัดการชื่อ Column ให้เรียบง่าย
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = df.columns.str.lower()

    # คำนวณ Indicators
    df["rsi"] = ta_lib.momentum.RSIIndicator(df["close"], window=14).rsi()
    macd_obj = ta_lib.trend.MACD(df["close"])
    df["macd_hist"] = macd_obj.macd_diff()

    lasted_rsi = df["rsi"].iloc[-1]
    lasted_close = df["close"].iloc[-1]
    lasted_hist = df["macd_hist"].iloc[-1]
    prev_hist = df["macd_hist"].iloc[-2]

    # Logic การตัดสินใจ
    if lasted_rsi < 35 and lasted_hist >0:
        action = Action.BUY
    elif lasted_rsi > 65 and lasted_hist <0:
        action = Action.SELL
    else:
        action = Action.HOLD
    
    if ML_MODEL:
        close = df["close"]
        volume =  df["volume"]
        feat_row = pd.DataFrame([{
            "rsi": float(df["rsi"].iloc[-1]),
            "macd": float(df["macd_hist"].iloc[-1]),
            "macd_hist": float(df["macd_hist"].iloc[-1]),
            "sma_20": float(close.rolling(20).mean().iloc[-1]),
            "sma_50": float(close.rolling(50).mean().iloc[-1]),
            "bb_upper": float(close.rolling(20).mean().iloc[-1] +2 * close.rolling(20).std().iloc[-1]),
            "bb_lower": float(close.rolling(20).mean().iloc[-1] -2 * close.rolling(20).std().iloc[-1]),
            "change_1d": float(close.pct_change(1).iloc[-1]),
            "change_5d": float(close.pct_change(5).iloc[-1]),
            "vol_ratio": float(volume.iloc[-1] / volume.rolling(20).mean().iloc[-1]),


        }])

        prob = ML_MODEL.predict_proba(feat_row)[0][1]
        print(f"ความน่าจะเป็นที่ราคาจะขึ้น >1% ใน 5 วัน: {prob:.1%}")

        if prob > 0.65:
            action = Action.BUY
        elif prob < 0.35:
            action = Action.SELL
        else:
            action = Action.HOLD
    else : 
        print("⚠️  ไม่พบโมเดล ML กำลังใช้ Logic พื้นฐาน")
        if lasted_rsi <35 and lasted_hist > 0:
            action = Action.BUY
        elif lasted_rsi > 65 and lasted_hist <0:
            action = Action.SELL
        else:
            action = Action.HOLD


    return AnalysisResult(
        ticker=ticker_symbol,
        current_price=round(lasted_close, 2),
        rsi_14=round(lasted_rsi, 2),
        macd_hist=round(lasted_hist, 4),
        action=action,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        df_history=df # ส่ง df ไปใช้วาดกราฟ
    )

if __name__ == "__main__":

    print("🤖 AI Stock Bot กำลังทำงาน...")
    new_data = evaluate_old_signals()
    retrain_if_needed(new_data)

    print("\n💰 วิเคราะห์อัตราแลกเปลี่ยน (FX)...")
    fx_results = analyze_all_fx()
    if fx_results:
        fx_msg = format_fx_message(fx_results)

        print("💱 กำลังวิเคราะห์อัตราแลกเปลี่ยน...")
    fx_results = analyze_all_fx()
    if fx_results:
        fx_msg = format_fx_message(fx_results)
        # ส่ง Discord
        requests.post(WEBHOOK_URL, json={
            "content": fx_msg.replace("*", "**")
                                .replace("`", "`")
        })
        print("✅ ส่ง FX report แล้ว")
    for ticker in watchlist:
        try:
        # 1. วิเคราะห์ตลาด
            result = analyze_market( ticker)

            save_signal(
                ticker=ticker,
                action=result.action.value,
                price=result.current_price,
                features={
                     "rsi":       result.rsi_14,
                     "macd_hist": result.macd_hist,
                     "sma_20":    float(result.df_history["close"].rolling(20).mean().iloc[-1]),
                     "sma_50":    float(result.df_history["close"].rolling(50).mean().iloc[-1]),
                     "change_1d": float(result.df_history["close"].pct_change(1).iloc[-1]),
                     "change_5d": float(result.df_history["close"].pct_change(5).iloc[-1]),
                     "vol_ratio": float(result.df_history["volume"].iloc[-1]
                                     / result.df_history["volume"].rolling(20).mean().iloc[-1]),
                }

            )
        
        # 2. วาดกราฟ
            print("🎨 สร้างกราฟ...")
            create_chart(result.df_history, ticker)
        
        # 3. ให้ AI วิเคราะห์
            print(f"🤖 AI กำลังคิด...{ticker}")
            ai_insight = ask_claude(result)
        
        # 4. ส่งแจ้งเตือน
            notify_discord(result, ai_insight)
            print(f"AI Insight: {ticker}")
        
        except Exception as e:
            print(f"❌{ticker} Error: {str(e)}")


