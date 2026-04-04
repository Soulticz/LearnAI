import yfinance as yf
import pandas as pd
import ta as ta_lib
import matplotlib.pyplot as plt 

def run_backtest(ticker_symbol: str):
    df = yf.download(ticker_symbol, period="2y", interval="1d", progress=False)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = df.columns.str.lower()

    df["rsi"] = ta_lib.momentum.RSIIndicator(df["close"],window=14).rsi()
    macd_obj = ta_lib.trend.MACD(df["close"])
    df["macd_hist"] = macd_obj.macd_diff()
    
    initial_capital = 100000.0 #เงิน1 แสนบาท
    capital = initial_capital
    position = 0
    history = []
    for i in range(1, len(df)):
        current_price = df["close"].iloc[i]
        rsi = df["rsi"].iloc[i]
        macd_hist = df["macd_hist"].iloc[i]
        prev_macd_hist = df["macd_hist"].iloc[i-1]

        # Logic การตัดสินใจ
        if position == 0 and rsi < 35 and macd_hist > 0 and macd_hist > prev_macd_hist:
            position = capital / current_price
            capital = 0
            print(f"🛒ซื้อ at{df.index[i].date()} | Price: {current_price: .2f}")
        elif position > 0 and rsi > 65 and macd_hist < 0 and macd_hist < prev_macd_hist:
            capital = position * current_price
            position = 0
            print(f"🛒ขาย at{df.index[i].date()} | Price: {current_price: .2f} | capital: {capital: .2f}")
    
    final_value = capital if position == 0 else position * df["close"].iloc[-1]
    total_return = ((final_value - initial_capital) / initial_capital) * 100
    print(f"\n--- backtest result ของ {ticker_symbol} (2 ปี)---")
    print(f"initial Capital(เงินต้น): {initial_capital}")
    print(f"Final Capital(เงินสุดท้าย): {final_value: .2f}")
    print(f"Total Return(กำไร): {total_return: .2f}%")

if __name__ == "__main__":
    run_backtest("^GSPC")