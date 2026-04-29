from pandas.core import window
from Testdevops.stock_bot import ML_MODEL
from copyreg import pickle
from numpy import save
import yfinance as yf
import pandas as pd
import ta as ta_lib
import pickle
from dataclasses import dataclass

WATCHLIST = ["SNDK","AAPL", "MSFT", "NVDA", "GOOGL", "META",
    "AMZN", "TSLA", "AMD", "INTC", "CRM",
    "ORCL", "ADBE", "QCOM", "TXN", "AVGO",
    # Finance
    "JPM", "BAC", "GS", "MS", "V", "MA",
    # Health
    "JNJ", "PFE", "MRNA", "UNH", "ABBV",
    # Energy
    "XOM", "CVX", "OXY",
    # Consumer
    "MCD", "SBUX", "NKE", "DIS", "NFLX",
    # ETF
    "SPY", "QQQ", "IWM",
    # Crypto-related
    "COIN", "MSTR", "MARA",
]
@dataclass
class screenResult:
    ticker: str
    price: float
    rsi: float
    macd_hist: float
    change_1d: float
    ml_prob: float
    score: float
    reason: str

try:
    with open("model.pkl", "rb") as f:
        saved = pickle.load(f)
        ML_MODEL = saved["model"]

except FileNotFoundError:
    ML_MODEL = None

def analyze_stock(ticker: str) -> screenResult | None:
    try:
        df = yf.download(ticker , period="3mo", progress=False)
        if df.empty or len(df) < 50:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = df.columns.str.lower()

        close = df["close"]
        volume = df["volume"]  

        #indicator 
        df["rsi"] = ta_lib.momentum.RSIIndicator(close, window=14).rsi()
        macd_obj  = ta_lib.trend.MACD(close)
        df["macd_hist"] = macd_obj.macd_diff()

        rsi  = float(df["rsi"].iloc[-1])
        hist = float(df["macd_hist"].iloc[-1])
        prev_hist = float(df["macd_hist"].iloc[-2])
        price = float(close.iloc[-1])
        change_1d = float(close.pct_change(1).iloc[-1] * 100)

        if pd.isna(rsi) or pd.isna(hist):
            return None

        ml_prob = 0.5
        if ML_MODEL:
            feat = pd.DataFrame([{
                "rsi": rsi,
                "macd_hist": hist,
                "sma_20": float(close.rolling(20) .mean().iloc[-1]),
                "sma_50": float(close.rolling(50) .mean().iloc[-1]),
                "change_1d": float(close.pct_change(1).iloc[-1]),
                "change_5d": float(close.pct_change(5).iloc[-1]),
                "vol_ratio": float(volume.iloc[-1]/ volume.rolling(20).mean().iloc[-1])
                
            }])
            ml_prob = float(ML_MODEL.predict_predict_proba(feat)[0][1])

        score = 0
        reason = []

        if rsi < 30:
            score += 40
            reason.append(f"RSI {rsi:.1f} Oversold มาก")
        elif rsi< 40:
            score += 25
            reason.append(f"RSI {rsi:.1f} Oversold")
        elif rsi< 50:
            score +=10
            reason.append(f"RSI {rsi:.1f} กำลังฟื้นตัว")

        if hist > 0 and hist > prev_hist:
            score += 30
            reason.append("MACD กำลังฟื้นตัว (Bullish)")
        elif hist < 0 and hist < prev_hist:
            score -= 20
            reason.append("MACD กำลังอ่อนแรง (Bearish)")
        
        if ml_prob > 0.65:
            score += 30
            reason.append(f"ML มั่นใจ {ml_prob:.0%}")
        elif ml_prob > 0.55:
            score +=15
            reason.append(f"ML prob {ml_prob: .0%}")

        if score < 40:
            return None

        return ScreenResult(
            ticker= ticker,
            price=round(price , 2),
            rsi=round(rsi, 2),
            macd_hist=round(hist, 4),
            change_1d=round(change_1d, 2),
            ml_prob=round(ml_prob, 3),
            score=round(score, 1 ),
            reason=" | ".join(reason),
        )
    except Exception as e:
        print(f"skip {ticker}: {e}")
        return None
def run_screener(top_n: int = 5) -> list[screenResult]:
    print(f"🔍 Running screener on {len(WATCHLIST)} stocks...")
    results = []

    for i, ticker in enumerate(WATCHLIST):
        print(f" [{i+1}/{len(WATCHLIST)}] {ticker}", end="\r")
        r = analyze_stock(ticker)
        if r:
            results.append(r)

        print(f"\n[✓] พบ {len(results)} หุ้นน่าสนใจ คัด TOP {top_n}")
        return top

def format_screener_message(results: list[ScreenResult]) -> str:
    if not results:
        return "ไม่พบหุ้นที่เข้าเกณฑ์ในรอบนี้"
    
    msg = "🚨 *AI Stock Screener - 5 หุ้นน่าจับตา*\n\n"
    msg += f"รายงานวันที่ : {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    msg += "================================================\n\n"
    
    medals = ["🥇", "🥈", "🥉","4","5"]
    for i , r in enumerate(results):
        arrow = "🔴" if r.change_1d > 0 else "🟢"
        msg += (
            f"{medals[i]} **{r.ticker}**\n"
            f"ราคา: **{r.price:,.2f}** | {arrow} {r.change_1d:+.2f}%\n"
            f" RSI: {r.rsi} | ML: {r.ml_prob: .0%}\n"
            f" Score: {r.score}/100\n"
            f" {r.reason}\n\n"
           
        )
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "⚠️ ข้อมูลเพื่อการศึกษาเท่านั้น ไม่ใช่คำแนะนำการลงทุน"
    return msg