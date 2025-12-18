import os
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# 設定環境變數
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
FINMIND_TOKEN = os.getenv("FINMIND_TOKEN")
STOCKS = {"2606": "裕民", "2637": "慧洋-KY", "2605": "新興"}

def get_chip_info(stock_id):
    """抓取三大法人買賣超張數"""
    url = "https://api.finmindtrade.com/api/v4/data"
    # 抓取最近 3 天的數據以判斷連買
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
        if df.empty: return "無數據"
        
        # 整理當日法人合計買賣超 (外資+投信+自營商)
        latest_date = df['date'].max()
        today_data = df[df['date'] == latest_date]
        net_buy = today_data['buy'].sum() - today_data['sell'].sum()
        
        # 計算張數 (單位通常是股，除以 1000)
        net_shares = int(net_buy / 1000)
        status = "🔴 賣超" if net_shares < 0 else "🟢 買超"
        return f"{status} {abs(net_shares):,} 張"
    except:
        return "讀取失敗"

def run_strategy():
    # 1. BDI 數據判斷
    bdi = yf.Ticker("^BDI").history(period="20d")
    bdi_last = bdi['Close'].iloc[-1]
    bdi_ma20 = bdi['Close'].rolling(window=20).mean().iloc[-1]
    bdi_change = bdi['Close'].pct_change().iloc[-1] * 100

    # 2. 組合 Discord 訊息
    msg = f"🚢 **散裝航運最強監控** ({datetime.now().strftime('%Y-%m-%d')})\n"
    msg += f"📊 BDI 指數: {bdi_last:.0f} ({bdi_change:+.2f}%)\n"
    msg += f"📈 趨勢: {'高於 20MA (多頭)' if bdi_last > bdi_ma20 else '低於 20MA (空頭)'}\n"
    msg += "---"

    for sid, name in STOCKS.items():
        chip = get_chip_info(sid)
        msg += f"\n📌 **{name} ({sid})**\n   籌碼面: {chip}"
        
        # 綜合評價邏輯
        if bdi_last > bdi_ma20 and "🟢" in chip:
            msg += " ✨ [建議關注: 雙多共振]"
        elif bdi_last < bdi_ma20 and "🔴" in chip:
            msg += " ⚠️ [建議避開: 基本籌碼雙弱]"

    # 3. 發送
    requests.post(DISCORD_WEBHOOK_URL, json={"content": msg})

if __name__ == "__main__":
    run_strategy()
