import os
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# 環境變數
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
FINMIND_TOKEN = os.getenv("FINMIND_TOKEN")
STOCKS = {"2606": "裕民", "2637": "慧洋-KY", "2605": "新興"}

def get_institutional_data(stock_id):
    url = "https://api.finmindtrade.com/api/v4/data"
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
        if df.empty: return "查無籌碼數據"
        latest_date = df['date'].max()
        today_df = df[df['date'] == latest_date]
        net_buy_sum = (today_df['buy'].sum() - today_df['sell'].sum()) / 1000
        status_icon = "🟢" if net_buy_sum > 0 else "🔴"
        return f"{status_icon} 法人合計: {int(net_buy_sum):+} 張"
    except:
        return "籌碼抓取失敗"

def run_strategy():
    # 改用 BDRY 避免 404 報錯
    print("正在抓取運價指標 (BDRY)...")
    bdi_data = yf.Ticker("BDRY").history(period="60d")
    
    if bdi_data.empty:
        print("BDRY 數據抓取失敗")
        return

    last_bdi = bdi_data['Close'].iloc[-1]
    ma20_bdi = bdi_data['Close'].rolling(window=20).mean().iloc[-1]
    change_bdi = bdi_data['Close'].pct_change().iloc[-1] * 100

    msg = f"🚢 **散裝航運策略監控** ({datetime.now().strftime('%Y-%m-%d')})\n"
    msg += f"📊 運價指標(BDRY): {last_bdi:.2f} ({change_bdi:+.2f}%)\n"
    msg += f"📈 指標趨勢: {'🔥 多頭 (20MA之上)' if last_bdi > ma20_bdi else '❄️ 弱勢 (20MA之下)'}\n"
    msg += "---"

    for sid, name in STOCKS.items():
        stock = yf.Ticker(f"{sid}.TW").history(period="60d")
        if stock.empty: continue
        
        price = stock['Close'].iloc[-1]
        ma20_stock = stock['Close'].rolling(window=20).mean().iloc[-1]
        bias_20 = ((price - ma20_stock) / ma20_stock) * 100
        chip_info = get_institutional_data(sid)
        
        # 乖離判斷
        bias_note = "⚠️ 過熱" if bias_20 > 10 else ("📉 超跌" if bias_20 < -10 else "正常")

        msg += f"\n📌 **{name} ({sid})**"
        msg += f"\n   價格: {price:.1f} (乖離: {bias_20:+.1f}%) -> {bias_note}"
        msg += f"\n   籌碼: {chip_info}"

        # 綜合策略邏輯
        if last_bdi > ma20_bdi and "🟢" in chip_info:
            msg += "\n   🚀 [策略: 雙多共振]" if bias_20 < 10 else "\n   ✋ [策略: 雖強但過熱，不追高]"
        elif last_bdi < ma20_bdi and "🟢" in chip_info:
            msg += "\n   💎 [策略: 逆勢抄底，觀察支撐]"
        msg += "\n"

    if DISCORD_WEBHOOK_URL:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": msg})

if __name__ == "__main__":
    run_strategy()
