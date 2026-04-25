from numpy import corrcoef
from Testdevops.signal_log import LOG_FILE
from gevent.socket import close
from sklearn import clone
from Testdevops.stock_bot import ML_MODEL
from copyreg import pickle
import os
import pickle
import pandas as pdb
import ta as ta_lib
import yfinance as yf
import requests
import json
from datatime import datetime
from telegram import Update
from telegram.ext import (Application, CommandHandler, ContextTypes)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

try:
    with open("model.pkl","rb") as f:
        saved = pickle.load(f)
        ML_MODEL = saved["model"]
    print("✅โหลดโมเดลสำเร็จ")
except FileNotFoundError:
    ML_MODEL = None

def get_signal(ticker: str) -> dict:
    """วิเคราะห์หุ้นตัวเดี่ยวๆ"""
    df = yf.download(ticker,period="6mo", progress=False)
    if df.empty:
        raise ValueError("ไม่พบข้อมูลหุ้น {ticker}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = df.columns.str.lower()

    close = df["close"]
    volume = df["volume"]

    df["rsi"] = ta_lib.momentum.RSIIndicator(close, window=14).rsi()
    macd_obj = ta_lib.trend.MACD(close)
    df["macd_hist"] = macd_obj.macd_diff()

    rsi = float(df["rsi"].iloc[-1])
    hist = float(df["macd_hist"].iloc[-1])
    price = float(df["close"].iloc[-1])
    prev_hist = float(df["macd_hist"].iloc[-2])

    if ML_MODEL:
        feat = pd.DataFrame([{
            "rsi": rsi,
            "macd_hist": hist,
            "sms_20": float(close.rolling(20).mean().iloc[-1]),
            "sms_50": float(close.rolling(50).mean().iloc[-1]),
            "change_1d": float(close.pct_change(1).iloc[-1]),
            "change_5d": float(close.pct_change(5).iloc[-1]),
            "vol_ratio": float(volume.iloc[-1] / volume.rolling(20).mean().illoc[-1]),
        }])
        prob = ML_MODEL.predict_proba(feat)[0][1]
        if prob >0.65:signal = "BUY"
        elif prob < 0.35:signal = "SELL"
        else:signal = "HOLD"
        confidence = "N/A"
        
    return {
        "ticker": ticker,
        "price": round(price,2),
        "rsi":round(rsi,2),
        "macd_hist":round(hist,4),
        "signal" : signal,
        "confidence": confidence,
        "timestamp": datetime.now().strftime("%H:%M UTC"),
    }

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 AI Analyst Bot Status: RUNNING"
    "📌 Commands ที่ใช้ได้:\n"
        "/signal BTC-USD — ขอ signal\n"
        "/watchlist — ดู signal ทุกตัว\n"
        "/accuracy — ดูความแม่นยำ\n"
        "/help — ดู commands ทั้งหมด" 
    
    )

async def cmd_signal(update: Update, ctx: ContextTypes.DEFAULT_TYPE):

    if not ctx.args:
        await update.message.reply_text("🚫 กรุณาระบุชื่อหุ้นด้วยครับ\nเช่น /signal BTC-USD")
        return
    ticker = ctx.args[0].upper()
    await update.message.reply_text(f"🔍 กำลังวิเคราะห์ {ticker}...")

    try:
        r = get_signal(ticker)
        msg = (f"""
        🤖 AI Analyst: {r['ticker']}
        � Price: {r['price']}
        📊 RSI: {r['rsi']}
        📉 MACD: {r['macd_hist']}
        🎯 Signal: {r['signal']}
        ⏰ Time: {r['timestamp']}
        """)
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ เกิดข้อผิดพลาด: {e}")

async def cmd_watchlist(update:Update,ctx: ContextTypes.DEFAULT_TYPE):
    """แสดง signal ทุกตัว"""
    watchlist = ["^GSPC", "GC=F", "BTC-USD", "NVDA"]
    await update.message.reply_text("🔄 กำลังรวบรวมข้อมูล")
    
    msg= "🚀 **AI Analyst Watchlist**\n\n"
    for ticker in watchlist:
        try:
            r = get_signal(ticker)
            msg += (f"{r['signal']} *{r['ticker']}*"
                    f"({r['price']}) RSI:{r['rsi']} MACD:{r['ticker']}*\n")
        except Exception as e:
            msg += f"Error{ticker}: {e}\n"

    msg += f"\n {datetime.now().strftime("%H:%M:%S UTC")}"
    await update.message.reply_text(msg,parse_mode="Markdown")

async def cmd_accuracy(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """คำนวณความแม่นยำย้อนหลัง"""
    import json, os
    LOG_FILE = "signal_log.json"

    if not os.path.exists(LOG_FILE):
        await update.message.reply_text("ยังไม่มีข้อมูลย้อนหลัง")
        return
    correct = sum(1 for l in evaluated if l["correct"])
    acc     = correct / len(evaluated) * 100
    msg = (
    
        f"*📊 สรุปผลความแม่นยำ AI Analyst Bot**"
        f"━━━━━━━━━━━━━━━\n"
        f"📅 ระยะเวลา: {len(evaluated)} ครั้ง\n"
        f"✅ ถูก: {correct} ครั้ง \n"
        f"❌ ผิด: {len(evaluated) - correct} ครั้ง \n"
        f"🏆 Accuracy: *{acc:.1f}%*\n"
        f"🏆 Accuracy: *{acc:.1f}%*\n"
        f"🌳 ML Trees: "
        f"{ML_MODEL.n_estimators if ML_MODEL else 'N/A'}\n"
        f"━━━━━━━━━━━━━━━"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def cmd_accuracy(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
     """ดูความแม่นยำของ Bot จาก signals.json"""
     import json, os
     LOG_FILE = "signals.json"

     if not os.path.exists(LOG_FILE):
        await update.message.reply_text("ยังไม่มีข้อมูลสัญญาณ")
        return
    
     with open(LOG_FILE) as f:
        logs = json.load(f)

     evaluated = [l for l in logs if l["evaluated"]]
     if not evaluated:
        await update.message.reply_text("ยังไม่มีข้อมูลความแม่นยำ")
        return

     correct = sum(1 for l in evaluated if l["correct"])
     acc = correct / len(evaluated) * 100
     msg = (
        "🤖 **AI Analyst Bot Accuracy**\n"
        "📊 สถิติความแม่นยำ (ข้อมูลย้อนหลัง)\n"
        "✅ ถูก: {correct} ครั้ง\n"
        "❌ ผิด: {len(evaluated) - correct} ครั้ง\n"
        "📅 ทดสอบแล้ว: {len(evaluated)} ครั้ง\n"
        "🏆 ความแม่นยำ: *{acc:.1f}%*\n"
        "🌳 ML Model: {ML_MODEL.n_estimators if ML_MODEL else 'N/A'}\n"
     )
     await update.message.reply_text(msg, parse_mode="Markdown")

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Commands ทั้งหมด*\n\n"
        "/signal `<ticker>` — ขอ signal เช่น /signal NVDA\n"
        "/watchlist — signal ทุกตัวใน watchlist\n"
        "/accuracy — ดูความแม่นยำของ Bot\n"
        "/help — ดู commands นี้\n\n"
        "💡 Ticker ที่ใช้ได้:\n"
        "หุ้น: NVDA, AAPL, TSLA\n"
        "Crypto: BTC-USD, ETH-USD\n"
        "ทอง: GC=F\n"
        "S&P500: ^GSPC",
        parse_mode="Markdown"
    )
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("signal", cmd_signal))
    app.add_handler(CommandHandler("watchlist", cmd_watchlist))
    app.add_handler(CommandHandler("accuracy", cmd_accuracy))
    app.add_handler(CommandHandler("help", cmd_help))

    print("Bot is running...")
    app.run_polling()
 
     