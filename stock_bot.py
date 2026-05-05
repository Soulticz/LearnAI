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
from screener import run_screener, format_screener_message
import os
import anthropic
import matplotlib.pyplot as plt
from paper_trading import apply_signal
from signal_log import save_signal, evaluate_old_signals, retrain_if_needed
from news_analyzer import analyze_news, format_news_context
from gold_analyzer import analyze_gold_context

try:
    from strategy_selector import get_strategy_mode
except Exception:
    get_strategy_mode = None

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
    df_history: pd.DataFrame
    ml_probability: float | None = None
    decision_reasons: list[str] | None = None
    strategy_mode: str = "UNKNOWN"
    strategy_reason: str = "ยังไม่มีข้อมูล strategy selector"
    news_sentiment_label: str = "UNKNOWN"
    news_sentiment_score: int = 0
    news_summary: str = "ไม่มีข้อมูลข่าว"
    gold_bias_label: str = "N/A"
    gold_bias_score: int = 0
    gold_summary: str = "ไม่ใช่สินทรัพย์กลุ่มทอง"

TICKER = os.getenv("TICKER_SYMBOL", "^GSPC,GC=F,BTC-USD,NVDA")
watchlist = [t.strip() for t in TICKER.split(",")]
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

try:
    with open("model.pkl", "rb") as f:
        saved = pickle.load(f)
        ML_MODEL = saved["model"]
        ML_FEATURES = saved.get("features")
    print("✅ โหลดโมเดลสำเร็จ")
except FileNotFoundError:
    print("❌ ไม่พบไฟล์ model.pkl")
    ML_MODEL = None
    ML_FEATURES = None
    print("⚠️  ระบบจะทำงานในโหมด AI Only (ไม่มีการใช้ ML)")

def load_strategy_info(ticker: str):
    if get_strategy_mode is None:
        return "UNKNOWN", "ยังโหลด strategy_selector ไม่ได้"
    try:
        strategy = get_strategy_mode(ticker)
        if strategy is None:
            return "UNKNOWN", "ยังไม่มีข้อมูล backtest/strategy ของ ticker นี้"
        return strategy.mode, strategy.reason
    except Exception as e:
        return "UNKNOWN", f"อ่าน strategy_modes ไม่ได้: {str(e)}"

def ask_claude(result: AnalysisResult):
    reasons_text = "\n".join(f"- {reason}" for reason in (result.decision_reasons or []))
    ml_text = "ไม่มีข้อมูล ML" if result.ml_probability is None else f"{result.ml_probability:.1%}"
    gold_text = ""
    if result.gold_bias_label != "N/A":
        gold_text = f"""
Gold Macro Bias: {result.gold_bias_label} ({result.gold_bias_score:+d})
Gold Macro Context:
{result.gold_summary}
"""

    prompt = f"""คุณคือนักวิเคราะห์การลงทุนมืออาชีพ
วิเคราะห์ {result.ticker} จากข้อมูลเชิงเทคนิค + ข่าว + macro ถ้ามี:
ราคา  : {result.current_price:,.2f}
RSI   : {result.rsi_14}
MACD Histogram : {result.macd_hist}
ML Probability ราคาขึ้น >1% ใน 5 วัน: {ml_text}
News Sentiment: {result.news_sentiment_label} ({result.news_sentiment_score:+d})
{gold_text}
Final Signal: {result.action.value}
Strategy Mode จาก Backtest: {result.strategy_mode}
Strategy Reason: {result.strategy_reason}

เหตุผลจาก Decision Engine:
{reasons_text}

ข่าวล่าสุด:
{result.news_summary}

กรุณาวิเคราะห์ 3 ข้อโดยให้สอดคล้องกับ Final Signal, Strategy Mode, News Sentiment และ Gold Macro Bias ถ้าเป็นทอง:
1. สภาวะตลาดตอนนี้เป็นอย่างไร
2. ความเสี่ยงที่ต้องระวัง รวมถึงข่าวและ macro
3. กลยุทธ์แนะนำ (ซื้อ/ขาย/ถือ) พร้อมเหตุผล

กติกาสำคัญ:
- ถ้า Strategy Mode เป็น HOLD ให้ย้ำว่าไม่ควรขายหมดตามสัญญาณสั้น ๆ
- ถ้า Strategy Mode เป็น HYBRID ให้แนะนำถือบางส่วนและให้ AI ช่วยจับจังหวะบางส่วน
- ถ้า Strategy Mode เป็น WATCH ให้ระวังและรอสัญญาณชัดขึ้น
- ถ้า Strategy Mode เป็น AVOID ให้เน้นหลีกเลี่ยง/ลดความเสี่ยง
- ถ้าข่าวเป็น NEGATIVE ให้ลดความมั่นใจในการซื้อ
- ถ้าข่าวเป็น POSITIVE แต่ technical ยังไม่ชัด ให้บอกว่ารอดู confirmation
- ถ้าเป็นทองและ Gold Macro Bias เป็น BEARISH ให้ลดความมั่นใจฝั่งซื้อ
- ถ้าเป็นทองและ Gold Macro Bias เป็น BULLISH ให้เพิ่มน้ำหนักฝั่งถือ/ซื้ออย่างระวัง

ตอบเป็นภาษาไทย กระชับ เข้าใจง่าย"""
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=750,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        return f"เกิดข้อผิดพลาดในการวิเคราะห์ AI: {str(e)}"

def notify_discord(result: AnalysisResult, ai_insight: str):
    color = 0x2ecc71 if result.action == Action.BUY else 0xe74c3c if result.action == Action.SELL else 0xf1c40f
    ml_value = "N/A" if result.ml_probability is None else f"**{result.ml_probability:.1%}**"
    fields = [
        {"name": "💰 Price", "value": f"**{result.current_price:,.2f}**", "inline": True},
        {"name": "📊 RSI", "value": f"**{result.rsi_14}**", "inline": True},
        {"name": "📉 MACD Hist", "value": f"**{result.macd_hist}**", "inline": True},
        {"name": "🤖 ML Prob", "value": ml_value, "inline": True},
        {"name": "📰 News", "value": f"**{result.news_sentiment_label} ({result.news_sentiment_score:+d})**", "inline": True},
        {"name": "🎯 Decision", "value": f"**{result.action.value}**", "inline": True},
        {"name": "🧭 Strategy", "value": f"**{result.strategy_mode}**", "inline": True},
    ]
    if result.gold_bias_label != "N/A":
        fields.append({"name": "🟡 Gold Macro", "value": f"**{result.gold_bias_label} ({result.gold_bias_score:+d})**", "inline": True})
    fields.append({"name": "📌 Strategy Reason", "value": result.strategy_reason[:1024], "inline": False})

    payload = {
        "embeds": [{
            "title": f"🤖 AI Analyst Report: {result.ticker}",
            "description": ai_insight,
            "color": color,
            "image": {"url": "attachment://chart.png"},
            "fields": fields,
            "footer": {"text": f"Analysis at: {result.timestamp}"},
            "thumbnail": {"url": "https://cdn-icons-png.flaticon.com/512/2422/2422796.png"}
        }]
    }

    try:
        with open("chart.png", "rb") as f:
            files = {"file": ("chart.png", f, "image/png")}
            response = requests.post(WEBHOOK_URL, data={"payload_json": json.dumps(payload)}, files=files)
        if response.status_code in [200, 204]:
            print("✅ ส่ง Discord พร้อมรูปสำเร็จ!")
        else:
            print(f"❌ ส่ง Discord ไม่สำเร็จ: {response.status_code} {response.text}")
    except FileNotFoundError:
        print("❌ ไม่พบไฟล์ chart.png!")

def create_chart(df, ticker):
    plt.figure(figsize=(10, 5))
    plt.style.use('dark_background')
    plt.plot(df.index[-30:], df['close'].tail(30), color='#00ff00', linewidth=2)
    plt.title(f"{ticker} Price Action (Last 30 Days)")
    plt.grid(True, alpha=0.3)
    plt.savefig('chart.png')
    plt.close()

def make_decision(rsi, macd_hist, prob=None, news_score: int = 0, gold_score: int = 0):
    score = 0
    reasons = []

    if rsi < 35:
        score += 1
        reasons.append("RSI ต่ำ มีโอกาสเด้ง")
    elif rsi > 65:
        score -= 1
        reasons.append("RSI สูง ระวังย่อตัว")
    else:
        reasons.append("RSI อยู่โซนกลาง ยังไม่สุดทาง")

    if macd_hist > 0:
        score += 1
        reasons.append("MACD Histogram เป็นบวก โมเมนตัมยังดี")
    else:
        score -= 1
        reasons.append("MACD Histogram เป็นลบ โมเมนตัมอ่อน")

    if prob is not None:
        if prob > 0.65:
            score += 2
            reasons.append(f"ML ให้โอกาสขึ้นสูง {prob:.1%}")
        elif prob < 0.35:
            score -= 2
            reasons.append(f"ML ให้โอกาสขึ้นต่ำ {prob:.1%}")
        else:
            reasons.append(f"ML ยังไม่ชัดเจน {prob:.1%}")

    if news_score >= 2:
        score += 1
        reasons.append(f"ข่าวโดยรวมเป็นบวก ({news_score:+d}) เพิ่มความมั่นใจเล็กน้อย")
    elif news_score <= -2:
        score -= 1
        reasons.append(f"ข่าวโดยรวมเป็นลบ ({news_score:+d}) ลดความมั่นใจ")
    else:
        reasons.append(f"ข่าวยังเป็นกลาง ({news_score:+d})")

    if gold_score >= 2:
        score += 1
        reasons.append(f"Gold Macro เป็นบวก ({gold_score:+d}) หนุนทอง")
    elif gold_score <= -2:
        score -= 1
        reasons.append(f"Gold Macro เป็นลบ ({gold_score:+d}) กดดันทอง")

    if score >= 2:
        return Action.BUY, reasons
    elif score <= -2:
        return Action.SELL, reasons
    return Action.HOLD, reasons

def analyze_market(ticker_symbol: str) -> AnalysisResult:
    df = yf.download(ticker_symbol, period="6mo", progress=False)
    if df.empty:
        raise ValueError("ไม่พบข้อมูลหุ้น")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = df.columns.str.lower()

    df["rsi"] = ta_lib.momentum.RSIIndicator(df["close"], window=14).rsi()
    macd_obj = ta_lib.trend.MACD(df["close"])
    df["macd"] = macd_obj.macd()
    df["macd_hist"] = macd_obj.macd_diff()

    lasted_rsi = df["rsi"].iloc[-1]
    lasted_close = df["close"].iloc[-1]
    lasted_hist = df["macd_hist"].iloc[-1]
    close = df["close"]
    volume = df["volume"]
    prob = None

    if ML_MODEL:
        feat_row = pd.DataFrame([{
            "rsi": float(df["rsi"].iloc[-1]),
            "macd": float(df["macd"].iloc[-1]),
            "macd_hist": float(df["macd_hist"].iloc[-1]),
            "sma_20": float(close.rolling(20).mean().iloc[-1]),
            "sma_50": float(close.rolling(50).mean().iloc[-1]),
            "bb_upper": float(close.rolling(20).mean().iloc[-1] + 2 * close.rolling(20).std().iloc[-1]),
            "bb_lower": float(close.rolling(20).mean().iloc[-1] - 2 * close.rolling(20).std().iloc[-1]),
            "change_1d": float(close.pct_change(1).iloc[-1]),
            "change_5d": float(close.pct_change(5).iloc[-1]),
            "vol_ratio": float(volume.iloc[-1] / volume.rolling(20).mean().iloc[-1]),
        }])
        if ML_FEATURES:
            feat_row = feat_row[ML_FEATURES]
        prob = ML_MODEL.predict_proba(feat_row)[0][1]
        print(f"ความน่าจะเป็นที่ราคาจะขึ้น >1% ใน 5 วัน: {prob:.1%}")
    else:
        print("⚠️  ไม่พบโมเดล ML กำลังใช้ Logic พื้นฐาน")

    news_result = analyze_news(ticker_symbol)
    news_score = int(news_result.get("sentiment_score", 0))
    news_label = str(news_result.get("sentiment_label", "UNKNOWN"))
    news_summary = format_news_context(news_result)
    print(f"📰 News sentiment {ticker_symbol}: {news_label} ({news_score:+d})")

    gold_context = analyze_gold_context(ticker_symbol)
    gold_score = gold_context.bias_score if gold_context.is_gold else 0
    gold_label = gold_context.bias_label if gold_context.is_gold else "N/A"
    gold_summary = gold_context.summary
    if gold_context.is_gold:
        print(f"🟡 Gold macro {ticker_symbol}: {gold_label} ({gold_score:+d})")

    action, reasons = make_decision(lasted_rsi, lasted_hist, prob, news_score, gold_score)
    strategy_mode, strategy_reason = load_strategy_info(ticker_symbol)

    return AnalysisResult(
        ticker=ticker_symbol,
        current_price=round(lasted_close, 2),
        rsi_14=round(lasted_rsi, 2),
        macd_hist=round(lasted_hist, 4),
        action=action,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        df_history=df,
        ml_probability=prob,
        decision_reasons=reasons,
        strategy_mode=strategy_mode,
        strategy_reason=strategy_reason,
        news_sentiment_label=news_label,
        news_sentiment_score=news_score,
        news_summary=news_summary,
        gold_bias_label=gold_label,
        gold_bias_score=gold_score,
        gold_summary=gold_summary,
    )

if __name__ == "__main__":
    print("🤖 AI Stock Bot กำลังทำงาน...")
    new_data = evaluate_old_signals()
    retrain_if_needed(new_data)

    print("\n🤖 กำลังวิเคราะห์หุ้น...")
    top5 = run_screener(top_n=5)
    msg = format_screener_message(top5)
    requests.post(WEBHOOK_URL, json={"content": msg})
    print("✅ ส่ง Screener report แล้ว")

    print("💱 กำลังวิเคราะห์อัตราแลกเปลี่ยน...")
    fx_results = analyze_all_fx()
    if fx_results:
        fx_msg = format_fx_message(fx_results)
        requests.post(WEBHOOK_URL, json={"content": fx_msg.replace("*", "**").replace("`", "`")})
        print("✅ ส่ง FX report แล้ว")

    for ticker in watchlist:
        try:
            result = analyze_market(ticker)
            save_signal(
                ticker=ticker,
                action=result.action.value,
                price=result.current_price,
                features={
                    "rsi": result.rsi_14,
                    "macd_hist": result.macd_hist,
                    "sma_20": float(result.df_history["close"].rolling(20).mean().iloc[-1]),
                    "sma_50": float(result.df_history["close"].rolling(50).mean().iloc[-1]),
                    "change_1d": float(result.df_history["close"].pct_change(1).iloc[-1]),
                    "change_5d": float(result.df_history["close"].pct_change(5).iloc[-1]),
                    "vol_ratio": float(result.df_history["volume"].iloc[-1] / result.df_history["volume"].rolling(20).mean().iloc[-1]),
                    "news_score": result.news_sentiment_score,
                    "gold_score": result.gold_bias_score,
                }
            )
            executed, msg, portfolio = apply_signal(
                ticker=result.ticker,
                action_value=result.action.value,
                price=result.current_price,
                strategy_mode=result.strategy_mode,
                strategy_reason=result.strategy_reason
            )
            print(f" paper trading {msg}")

            print("🎨 สร้างกราฟ...")
            create_chart(result.df_history, ticker)

            print(f"🤖 AI กำลังคิด...{ticker}")
            ai_insight = ask_claude(result)

            notify_discord(result, ai_insight)
            print(f"AI Insight: {ticker}")

        except Exception as e:
            print(f"❌{ticker} Error: {str(e)}")
