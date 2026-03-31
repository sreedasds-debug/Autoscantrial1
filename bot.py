import yfinance as yf
import pandas as pd
import ta
import requests
import time
from datetime import datetime
import os

# گرفتن المتغيرات من Railway
BOT_TOKEN = os.getenv("8329251588:AAEqrvL0X3R5cDL3sF1Yc9LRrwDnk5lxwJU")
CHAT_ID = os.getenv("567397871")

pairs = [
    "EURUSD=X", "GBPUSD=X", "USDJPY=X",
    "AUDUSD=X", "USDCAD=X", "USDCHF=X",
    "NZDUSD=X"
]

last_signal_time = {}

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except:
        print("Telegram send failed")

def calculate_indicators(df):
    adx = ta.trend.ADXIndicator(df['High'], df['Low'], df['Close'], window=14)
    df['ADX'] = adx.adx()
    df['DI+'] = adx.adx_pos()
    df['DI-'] = adx.adx_neg()
    df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()
    df['EMA50'] = ta.trend.EMAIndicator(df['Close'], window=50).ema_indicator()
    df['ATR'] = ta.volatility.AverageTrueRange(
        df['High'], df['Low'], df['Close'], window=14
    ).average_true_range()
    return df

def is_new_candle(df, pair):
    last_time = df.index[-1]
    if pair not in last_signal_time or last_signal_time[pair] != last_time:
        last_signal_time[pair] = last_time
        return True
    return False

def get_signal(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    # Core conditions
    adx_cond = last['ADX'] < 20
    rsi_cond = 40 < last['RSI'] < 60

    buy_cross = prev['DI+'] < prev['DI-'] and last['DI+'] > last['DI-']
    sell_cross = prev['DI-'] < prev['DI+'] and last['DI-'] > last['DI+']

    # Trend filter
    trend_buy = last['Close'] > last['EMA50']
    trend_sell = last['Close'] < last['EMA50']

    # Breakout filter
    breakout_buy = last['Close'] > prev['High']
    breakout_sell = last['Close'] < prev['Low']

    # Confidence scoring
    score = 0
    if adx_cond: score += 1
    if rsi_cond: score += 1
    if buy_cross: score += 2
    if sell_cross: score += 2
    if trend_buy or trend_sell: score += 1
    if breakout_buy or breakout_sell: score += 1

    confidence = int((score / 6) * 100)

    atr = last['ATR']

    # BUY signal
    if buy_cross and adx_cond and rsi_cond and trend_buy and breakout_buy:
        sl = last['Close'] - atr
        tp = last['Close'] + (2 * atr)
        return "BUY", confidence, sl, tp

    # SELL signal
    elif sell_cross and adx_cond and rsi_cond and trend_sell and breakout_sell:
        sl = last['Close'] + atr
        tp = last['Close'] - (2 * atr)
        return "SELL", confidence, sl, tp

    return None, None, None, None

def run_bot():
    for pair in pairs:
        try:
            df = yf.download(pair, interval="4h", period="60d")

            # Safety check
            if df.empty or len(df) < 50:
                continue

            df = calculate_indicators(df)

            # Avoid duplicate signals
            if not is_new_candle(df, pair):
                continue

            signal, confidence, sl, tp = get_signal(df)

            if signal:
                last = df.iloc[-1]

                msg = f"""
🚨 {signal} SIGNAL — {pair}

💰 Price: {round(last['Close'],5)}
📊 ADX: {round(last['ADX'],2)}
📈 RSI: {round(last['RSI'],2)}

🎯 Confidence: {confidence}%

🛑 Stop Loss: {round(sl,5)}
🎯 Take Profit: {round(tp,5)}

🕒 Time: {df.index[-1]}
"""

                send_telegram(msg)

        except Exception as e:
            print(f"Error {pair}: {e}")

# Send Startup message
send_telegram ("bot is live")
# Main loop
while True:
    run_bot()
    time.sleep(300)  # every 5 minutes


