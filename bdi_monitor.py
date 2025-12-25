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
        if df.empty: return "查無籌碼"
        latest_date = df['date'].max()
        today_df = df[df['date'] == latest_date]
        net_buy_sum = (today_df['buy'].sum() - today_df['sell'].sum()) / 1000
        status_icon = "🟢" if net_buy_sum > 0 else "🔴"
        return f"{status_icon} 法人: {int(net_buy_sum):+} 張"
    except:
        return "籌碼抓取失敗"

def run_strategy():
    print("正在抓取運價指標 (BDRY)...")
    bdi_data = yf.Ticker("BDRY").history(period="60d")
    
    if bdi_data.empty:
        print("BDRY 數據抓取失敗")
        return

    last_bdi = bdi_data['Close'].iloc[-1]
    ma20_bdi = bdi_data['Close'].rolling(window=20).mean().iloc[-1]
    change_bdi = bdi_data['Close'].pct_change().iloc[-1] * 100

    msg = f"🚢 **散裝航運監控報表** ({datetime.now().strftime('%Y-%m-%d')})\n"
    msg += f"📊 運價(BDRY): {last_bdi:.2f} ({change_bdi:+.2f}%)\n"
    msg += f"📈 運價趨勢: {'🔥 多頭' if last_bdi > ma20_bdi else '❄️ 弱勢'}\n"
    msg += "---"

    for sid, name in STOCKS.items():
        stock = yf.Ticker(f"{sid}.TW").history(period="60d")
        if stock.empty: continue
        
        # 價格與漲跌幅
        price = stock['Close'].iloc[-1]
        prev_price = stock['Close'].iloc[-2]
        daily_change = ((price - prev_price) / prev_price) * 100
        
        # 成交量分析
        vol_today = stock['Volume'].iloc[-1]
        vol_ma5 = stock['Volume'].rolling(window=5).mean().iloc[-1]
        vol_ratio = vol_today / vol_ma5  # 量比
        
        # 均線與乖離
        ma20_stock = stock['Close'].rolling(window=20).mean().iloc[-1]
        bias_20 = ((price - ma20_stock) / ma20_stock) * 100
        chip_info = get_institutional_data(sid)

        # 格式化輸出
        msg += f"\n📌 **{name} ({sid})**"
        msg += f"\n   價格: {price:.2f} ({daily_change:+.1f}%) | 乖離: {bias_20:+.1f}%"
        msg += f"\n   成交: {int(vol_today):,} 股 (量比: {vol_ratio:.2f}x)"
        msg += f"\n   籌碼: {chip_info}"

        # --- 進階策略邏輯 ---
        strategy_tips = []
        
        # 1. 攻擊信號：運價強 + 股價強 + 量增 + 法人買
        if last_bdi > ma20_bdi and daily_change > 0 and vol_ratio > 1.2 and "🟢" in chip_info:
            strategy_tips.append("🚀 [強勢攻擊: 量價齊揚]")
        
        # 2. 警示信號：價漲量縮
        elif daily_change > 2 and vol_ratio < 0.8:
            strategy_tips.append("⚠️ [背離: 價漲量縮，追高小心]")
            
        # 3. 支撐信號：超跌 + 法人轉買
        elif bias_20 < -8 and "🟢" in chip_info:
            strategy_tips.append("💎 [潛在反彈: 乖離過大+法人抄底]")

        if strategy_tips:
            msg += f"\n   💡 提示: {' '.join(strategy_tips)}"
        msg += "\n"

    print(msg) # 終端機預覽
    if DISCORD_WEBHOOK_URL:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": msg})

if __name__ == "__main__":
    run_strategy()
