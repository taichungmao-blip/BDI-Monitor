import yfinance as yf
import pandas as pd
import requests
from datetime import datetime

# --- 設定區 ---
import os
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
SYMBOL = "^BDI"  # yfinance 上的 BDI 指數代碼 (註：若無數據需改用爬蟲獲取)

def send_discord_message(content):
    data = {"content": content}
    response = requests.post(DISCORD_WEBHOOK_URL, json=data)
    return response.status_code

def monitor_bdi_strategy():
    # 1. 抓取歷史數據 (最近 60 天)
    ticker = yf.Ticker(SYMBOL)
    df = ticker.history(period="60d")
    
    if df.empty:
        print("無法取得 BDI 數據，請檢查代碼或來源。")
        return

    # 2. 計算技術指標
    df['MA10'] = df['Close'].rolling(window=10).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['Change'] = df['Close'].pct_change() * 100

    last_price = df['Close'].iloc[-1]
    prev_price = df['Close'].iloc[-2]
    last_ma10 = df['MA10'].iloc[-1]
    last_ma20 = df['MA20'].iloc[-1]
    daily_change = df['Change'].iloc[-1]

    # 3. 策略判斷
    signal = None
    msg = f"📊 **BDI 指數監控報告 ({datetime.now().strftime('%Y-%m-%d')})**\n" \
          f"最新收盤價: {last_price:.2f} ({daily_change:+.2f}%)\n"

    # 多頭訊號：突破20日線且漲幅大
    if last_price > last_ma20 and prev_price <= df['MA20'].iloc[-2] and daily_change > 2:
        signal = "🚀 **【買入訊號】** BDI 帶量突破 20 日線，散裝航運動能轉強！"
    
    # 空頭訊號：跌破10日線
    elif last_price < last_ma10 and prev_price >= df['MA10'].iloc[-2]:
        signal = "⚠️ **【賣出訊號】** BDI 跌破 10 日支撐，短線趨勢轉弱，請注意部位。"

    # 4. 發送通知
    if signal:
        send_discord_message(msg + signal)
        print("訊號已發送至 Discord")
    else:
        print("今日無顯著訊號")

if __name__ == "__main__":
    monitor_bdi_strategy()
