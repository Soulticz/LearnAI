import pandas as pd
import yfinance as yf 
import ta as ta_lib
from datatime import datetime
from dataclasses import dataclass

FX_PAIRS = {
"USD/THB":"USDTHB=X",
"EUR/THB":"EURTHB=X",
"JPY/THB":"JPYTHB=X",

}

@dataclass
class FXResult:
    pair: str
    rate: float
    change_1d: float
    change_1w: float
    rsi: float
    signal: str
    tip: str
    timestamp: str

def analyze_fx(pair_name: str, ticker: str) -> FXResult:
    df = yf.download(ticker, period="3mo", progress=False)
    if df.empty:
        raise ValueError(f"ไม่พบข้อมูล {pair_name}")
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = df.columns.str.lower()

    close = df["close"] 

    df["rsi"] = ta_lib.momentum.RSIIndicator(close, window=14).rsi()

    rate = float(close.iloc[-1])
    prev_day = float(close.iloc[-2])
    prev_wk = float(close.iloc[-6]) if len(close) >=6 else prev_day

    change_1d = (rate - prev_day) / prev_day *100
    change_1w = (rate - prev_wk) / prev_wk *100
    rsi = float(df["rsi"].iloc[-1])



    if change_1d > 0.3 and rsi > 60:
        signal = "THB อ่อน"
        tip = "ระวัง! ของนำเข้าแพงขึ้น ถ้าจะแลกเงินรอก่อน"
    elif change_1d < -0.3 and rsi < 40 :
        signal = "✅ THB แข็ง"
        tip = "จังหวะดีถ้าจะซื้อ USD หรือโอนเงินออกนอก"
    else:
        signal = " neutral"
        tip = "ตลาดกำลัง Sideway รอดู"
   
    return FXResult(
        pair=pair_name,
        rate=round(rate, 4 ),
        change_1d=round(change_1d, 3),
        change_1w=round(change_1w, 3),
        rsi =round(rsi, 2),
        signal=signal,
        tip=tip,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
    
def analyze_all_fx():
    result = []
    for pair_name, ticker in FX_PAIRS.items():
        try:
            r = analyze_fx(pair_name, ticker)
            result.append(r)
            print(f"✓ วิเคราะห์ {pair_name} :{r.rate}{r.signal} เรียบร้อย")
        except Exception as e:
            print(f"✗ วิเคราะห์ {pair_name} ไม่สำเร็จ: {e}")
    return result

def format_fx_message(results: list[FXResult])-> str:
    """แปลงผลเป็น message ส่ง Discord/Telegram"""
    msg = f"💰 **FX Market Update**\n"
    msg += f"━━━━━━━━━━━━━━━\n"

    for r in results:
        arrow = "⬆️" if r.change_1d > 0 else "⬇️"
        msg += (
            f"{arrow} * {r.pair}*\n"
            f"🏷️ Rate: '{r.rate}'THB\n"
            f"{r.signal}\n"
            f"1 วัน'{r.change_1d:+.3f}'%\n"
            f"1 สัปดาห์'{r.change_1w:+.3f}'%\n"
            f"RSI '{r.rsi}'\n"
            f"💡{r.tip}\n"
            
        )


    msg += f"เวลา '{results[0].timestamp}'"
    return msg