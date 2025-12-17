import yfinance as yf
import pandas as pd
import requests
import os
from datetime import datetime

# 從 GitHub Secrets 讀取 Webhook 網址
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

def send_discord_message(content):
    if not DISCORD_WEBHOOK_URL:
        print("錯誤: 找不到 Discord Webhook 網址，請檢查 Secrets 設定。")
        return
    data = {"content": content}
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=data)
        response.raise_for_status()
        print("訊息發送成功！")
    except Exception as e:
        print(f"發送失敗: {e}")

def monitor_bdi_strategy():
    # BDI 在 yfinance 上的代碼通常是 BDI.L (倫敦) 或 ^BDI，
    # 這裡使用較穩定的替代方案 BDRY (散裝航運 ETF，與 BDI 極度正相關) 或嘗試抓取 ^BDI
    symbol = "^BDI" 
    print(f"正在抓取 {symbol} 數據...")
    
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="60d")
    
    if df.empty or len(df) < 20:
        # 如果 BDI 沒數據，改抓 BDRY (散裝航運 ETF) 作為備案
        print("BDI 數據獲取失敗，嘗試抓取 BDRY ETF...")
        df = yf.Ticker("BDRY").history(period="60d")

    # 計算技術指標
    df['MA10'] = df['Close'].rolling(window=10).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['Change'] = df['Close'].pct_change() * 100

    last_price = df['Close'].iloc[-1]
    prev_price = df['Close'].iloc[-2]
    last_ma10 = df['MA10'].iloc[-1]
    last_ma20 = df['MA20'].iloc[-1]
    daily_change = df['Change'].iloc[-1]

    msg = f"🚢 **BDI 散裝航運監控報告** ({datetime.now().strftime('%Y-%m-%d')})\n" \
          f"最新收盤: {last_price:.2f}\n" \
          f"漲跌幅: {daily_change:+.2f}%\n" \
          f"10日均線: {last_ma10:.2f} / 20日均線: {last_ma20:.2f}\n" \
          f"---"

    signal = ""
    # 多頭訊號：收盤突破20日線
    if last_price > last_ma20 and prev_price <= df['MA20'].iloc[-2]:
        signal = "\n🚀 **【買入訊號】** 指數突破 20 日線，散裝航運轉強，關注：裕民、慧洋、新興。"
    # 空頭訊號：收盤跌破10日線
    elif last_price < last_ma10 and prev_price >= df['MA10'].iloc[-2]:
        signal = "\n⚠️ **【警示訊號】** 指數跌破 10 日線，短線動能轉弱，注意停損。"
    else:
        signal = "\n✅ 目前趨勢穩定，無變動訊號。"

    send_discord_message(msg + signal)

if __name__ == "__main__":
    monitor_bdi_strategy()
