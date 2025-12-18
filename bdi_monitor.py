import os
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# 讀取 GitHub Secrets
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
FINMIND_TOKEN = os.getenv("FINMIND_TOKEN")

# 監控標的：代碼與名稱
STOCKS = {"2606": "裕民", "2637": "慧洋-KY", "2605": "新興"}

def get_institutional_data(stock_id):
    """透過 FinMind 抓取三大法人買賣超"""
    url = "https://api.finmindtrade.com/api/v4/data"
    # 抓取最近 5 天的數據確保能抓到最後一個交易日
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    parameter = {
        "dataset": "TaiwanStockInstitutionalInvestorsBuySell",
        "data_id": stock_id,
        "start_date": start_date,
        "token": FINMIND_TOKEN,
    }
    try:
        resp = requests.get(url, params=parameter).json()
        df = pd.DataFrame(resp["data"])
        if df.empty:
            return "查無籌碼數據"
        
        # 取得最後一個交易日的數據
        latest_date = df['date'].max()
        today_df = df[df['date'] == latest_date]
        
        # 計算三大法人合計買賣超 (單位: 張)
        net_buy_sum = (today_df['buy'].sum() - today_df['sell'].sum()) / 1000
        
        status_icon = "🟢" if net_buy_sum > 0 else "🔴"
        return f"{status_icon} 法人合計: {int(net_buy_sum):+} 張 ({latest_date})"
    except Exception as e:
        return f"籌碼抓取失敗: {e}"

def run_strategy():
    # 1. 抓取運價替代指標 BDRY (美股 ETF，與 BDI 高度相關且數據穩定)
    print("正在抓取運價指標數據...")
    bdi_data = yf.Ticker("BDRY").history(period="30d")
    
    if bdi_data.empty:
        print("無法取得 BDRY 數據，請檢查網路或代碼。")
        return

    last_bdi = bdi_data['Close'].iloc[-1]
    ma20_bdi = bdi_data['Close'].rolling(window=20).mean().iloc[-1]
    change_bdi = bdi_data['Close'].pct_change().iloc[-1] * 100

    # 2. 建立 Discord 訊息內容
    msg = f"🚢 **散裝航運最強監控報告** ({datetime.now().strftime('%Y-%m-%d')})\n"
    msg += f"📊 運價指標(BDRY): {last_bdi:.2f} ({change_bdi:+.2f}%)\n"
    msg += f"📈 趨勢判斷: {'🔥 多頭 (高於20MA)' if last_bdi > ma20_bdi else '❄️ 弱勢 (低於20MA)'}\n"
    msg += "---"

    # 3. 掃描個股股價與籌碼
    for sid, name in STOCKS.items():
        # 抓取股價
        stock = yf.Ticker(f"{sid}.TW").history(period="5d")
        price = stock['Close'].iloc[-1] if not stock.empty else 0
        
        # 抓取法人籌碼
        chip_info = get_institutional_data(sid)
        
        msg += f"\n📌 **{name} ({sid})**\n   收盤價: {price:.1f}\n   籌碼面: {chip_info}"
        
        # 策略警示：指標與籌碼同向
        if last_bdi > ma20_bdi and "🟢" in chip_info:
            msg += "\n   🚀 [策略建議: 基本籌碼雙強，重點關注]"
        elif last_bdi < ma20_bdi and "🔴" in chip_info:
            msg += "\n   ⚠️ [策略建議: 走勢偏弱，注意風險]"

    # 4. 發送 Discord 訊息
    if DISCORD_WEBHOOK_URL:
        response = requests.post(DISCORD_WEBHOOK_URL, json={"content": msg})
        if response.status_code == 204:
            print("Discord 訊息發送成功！")
        else:
            print(f"發送失敗，狀態碼: {response.status_code}")
    else:
        print("未偵測到 DISCORD_WEBHOOK 變數。")

if __name__ == "__main__":
    run_strategy()
