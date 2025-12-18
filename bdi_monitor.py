import os
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# 讀取 GitHub Secrets
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
FINMIND_TOKEN = os.getenv("FINMIND_TOKEN")

# 監控標的
STOCKS = {"2606": "裕民", "2637": "慧洋-KY", "2605": "新興"}

def get_institutional_data(stock_id):
    """抓取三大法人買賣超"""
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
        if df.empty: return "查無數據"
        
        latest_date = df['date'].max()
        today_df = df[df['date'] == latest_date]
        net_buy_sum = (today_df['buy'].sum() - today_df['sell'].sum()) / 1000
        
        status_icon = "🟢" if net_buy_sum > 0 else "🔴"
        return f"{status_icon} 法人合計: {int(net_buy_sum):+} 張 ({latest_date})"
    except:
        return "籌碼抓取失敗"

def run_strategy():
    # 1. 抓取運價指標 BDRY
    bdi_data = yf.Ticker("BDRY").history(period="30d")
    if bdi_data.empty: return

    last_bdi = bdi_data['Close'].iloc[-1]
    ma20_bdi = bdi_data['Close'].rolling(window=20).mean().iloc[-1]
    change_bdi = bdi_data['Close'].pct_change().iloc[-1] * 100

    # 2. 訊息標題與指標
    msg = f"🚢 **散裝航運策略監控** ({datetime.now().strftime('%Y-%m-%d')})\n"
    msg += f"📊 運價指標(BDRY): {last_bdi:.2f} ({change_bdi:+.2f}%)\n"
    msg += f"📈 指標趨勢: {'🔥 多頭 (高於20MA)' if last_bdi > ma20_bdi else '❄️ 弱勢 (低於20MA)'}\n"
    msg += "---"

    # 3. 掃描個股並套用四象限策略
    for sid, name in STOCKS.items():
        stock = yf.Ticker(f"{sid}.TW").history(period="5d")
        price = stock['Close'].iloc[-1] if not stock.empty else 0
        chip_info = get_institutional_data(sid)
        
        msg += f"\n📌 **{name} ({sid})**\n   收盤價: {price:.1f}\n   籌碼面: {chip_info}"
        
        # --- 策略判斷邏輯 ---
        is_bdi_strong = last_bdi > ma20_bdi
        is_chip_strong = "🟢" in chip_info

        if is_bdi_strong and is_chip_strong:
            msg += "\n   🚀 [策略: 雙多共振] 指標與籌碼同步走強，建議加碼關注。"
        elif not is_bdi_strong and is_chip_strong:
            msg += "\n   💎 [策略: 逆勢抄底] 運價偏弱但法人買超，觀察是否利空不跌。"
        elif is_bdi_strong and not is_chip_strong:
            msg += "\n   ⚠️ [策略: 警戒拉回] 指標雖強但法人獲利了結，暫不追高。"
        else:
            msg += "\n   📉 [策略: 雙弱觀望] 運價與籌碼皆無支撐，保守看待。"

    # 4. 發送訊息
    if DISCORD_WEBHOOK_URL:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": msg})

if __name__ == "__main__":
    run_strategy()
