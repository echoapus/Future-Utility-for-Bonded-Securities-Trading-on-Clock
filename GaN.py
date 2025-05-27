from login_helper import login
import time
import threading
import sys

# 全域變數
sdk = None
reststock = None
login_success = False

def login_thread():
    """登入線程"""
    global sdk, reststock, login_success
    try:
        sdk, account = login()
        sdk.init_realtime()
        reststock = sdk.marketdata.rest_client.stock
        login_success = True
        print("登入成功")
    except Exception as e:
        print(f"登入失敗: {e}")
        login_success = False

def logout_system():
    """登出富邦系統"""
    global sdk, reststock, login_success
    
    try:
        if sdk:
            sdk.logout()
            print("已登出富邦系統")
        
        # 重置全域變數
        sdk = None
        reststock = None
        login_success = False
        
        return True
        
    except Exception as e:
        print(f"登出失敗: {e}")
        return False

def analyze_big_orders(trades_data):
    """分析大單流向 (50張以上)"""
    if not trades_data or not trades_data.get('data'):
        return None
    
    big_orders = []
    total_big_volume = 0
    big_bid_volume = 0  # 內盤大單
    big_ask_volume = 0  # 外盤大單
    
    for trade in trades_data['data']:
        size = trade.get('size', 0)
        if size >= 50:  # 50張以上算大單
            big_orders.append(trade)
            total_big_volume += size
            
            # 判斷內外盤 (如果有bid/ask資訊)
            bid = trade.get('bid')
            ask = trade.get('ask')
            price = trade.get('price')
            
            if bid and ask and price:
                if price <= bid:
                    big_bid_volume += size  # 內盤
                elif price >= ask:
                    big_ask_volume += size  # 外盤
    
    if total_big_volume > 0:
        return {
            'total_orders': len(big_orders),
            'total_volume': total_big_volume,
            'bid_volume': big_bid_volume,
            'ask_volume': big_ask_volume,
            'bid_ratio': (big_bid_volume / total_big_volume) * 100 if total_big_volume > 0 else 0,
            'ask_ratio': (big_ask_volume / total_big_volume) * 100 if total_big_volume > 0 else 0,
            'orders': big_orders[:5]  # 只顯示前5筆
        }
    return None

def get_market_overview(reststock):
    """取得大盤概況"""
    try:
        # 查詢加權指數
        taiex = reststock.intraday.quote(symbol="TAIEX")
        
        # 查詢權值股
        tsmc = reststock.intraday.quote(symbol="2330")    # 台積電
        mediatek = reststock.intraday.quote(symbol="2454") # 聯發科
        mega = reststock.intraday.quote(symbol="2886")     # 兆豐金
        fubon = reststock.intraday.quote(symbol="2887")    # 富邦金  
        cement = reststock.intraday.quote(symbol="1101")   # 台泥
        steel = reststock.intraday.quote(symbol="2002")    # 中鋼
        
        return {
            'taiex': taiex,
            'tsmc': tsmc,
            'mediatek': mediatek,
            'mega': mega,
            'fubon': fubon,
            'cement': cement,
            'steel': steel
        }
    except Exception as e:
        print(f"取得大盤資料失敗: {e}")
        return None

def draw_simple_chart(candles_data):
    """繪製簡易1分鐘K線圖"""
    if not candles_data or not candles_data.get('data'):
        return
    
    data = candles_data['data'][-20:]  # 最近20根K線
    if len(data) < 2:
        return
    
    # 取得價格範圍
    prices = []
    for candle in data:
        prices.extend([candle.get('high', 0), candle.get('low', 0)])
    
    if not prices:
        return
        
    max_price = max(prices)
    min_price = min(prices)
    price_range = max_price - min_price
    
    if price_range == 0:
        return
    
    print("\n簡易1分鐘走勢圖 (最近20根)")
    print("-" * 40)
    
    # 繪製圖表 (10行高度)
    chart_height = 10
    
    for row in range(chart_height):
        price_level = max_price - (price_range * row / (chart_height - 1))
        line = f"{price_level:6.1f} |"
        
        for candle in data:
            high = candle.get('high', 0)
            low = candle.get('low', 0)
            close = candle.get('close', 0)
            
            if low <= price_level <= high:
                if abs(close - price_level) < price_range * 0.1:
                    line += "*"  # 收盤價附近
                else:
                    line += "|"  # K線實體
            else:
                line += " "
        
        print(line)
    
    # 時間軸
    print("       " + "".join([f"{i%10}" for i in range(len(data))]))
    print(f"       最近{len(data)}根1分K (每格1分鐘)")

def show_market_sentiment(market_data):
    """顯示市場情緒"""
    if not market_data:
        return
    
    print("\n市場概況")
    print("-" * 30)
    
    # 大盤
    taiex = market_data.get('taiex')
    if taiex:
        change = taiex.get('change', 0)
        change_pct = taiex.get('changePercent', 0)
        trend = "+" if change > 0 else "-" if change < 0 else "="
        print(f"加權指數: {taiex.get('closePrice', 'N/A')} {trend}{change:.0f} ({change_pct:+.2f}%)")
    
    # 權值股
    stocks = [
        ('tsmc', '2330 台積電'),
        ('mediatek', '2454 聯發科'),
        ('mega', '2886 兆豐金'),
        ('fubon', '2887 富邦金'),
        ('cement', '1101 台泥'),
        ('steel', '2002 中鋼')
    ]
    
    for key, name in stocks:
        stock = market_data.get(key)
        if stock:
            change = stock.get('change', 0)
            change_pct = stock.get('changePercent', 0)
            trend = "+" if change > 0 else "-" if change < 0 else "="
            print(f"{name}: {stock.get('closePrice', 'N/A')} {trend}{change:.1f} ({change_pct:+.2f}%)")

def calculate_vwap(candles_data):
    """計算當日VWAP (成交量加權平均價)"""
    if not candles_data or not candles_data.get('data'):
        return None
    
    total_pv = 0  # 價格×成交量總和
    total_volume = 0  # 成交量總和
    
    for candle in candles_data['data']:
        # 使用典型價格 (H+L+C)/3
        high = candle.get('high', 0)
        low = candle.get('low', 0)
        close = candle.get('close', 0)
        volume = candle.get('volume', 0)
        
        if volume > 0:
            typical_price = (high + low + close) / 3
            total_pv += typical_price * volume
            total_volume += volume
    
    if total_volume > 0:
        return total_pv / total_volume
    return None

def calculate_ma(prices, period):
    """計算移動平均線"""
    if len(prices) < period:
        return None
    
    ma_values = []
    for i in range(period - 1, len(prices)):
        ma = sum(prices[i - period + 1:i + 1]) / period
        ma_values.append(ma)
    
    return ma_values

def calculate_ema(prices, period):
    """計算指數移動平均線 (EMA)"""
    if len(prices) < period:
        return None
    
    ema_values = []
    multiplier = 2 / (period + 1)
    
    # 第一個EMA值使用SMA
    sma = sum(prices[:period]) / period
    ema_values.append(sma)
    
    # 後續EMA計算
    for i in range(period, len(prices)):
        ema = (prices[i] * multiplier) + (ema_values[-1] * (1 - multiplier))
        ema_values.append(ema)
    
    return ema_values

def calculate_macd(prices):
    """計算MACD指標"""
    if len(prices) < 26:
        return None
    
    # 計算EMA12和EMA26
    ema12 = calculate_ema(prices, 12)
    ema26 = calculate_ema(prices, 26)
    
    if not ema12 or not ema26:
        return None
    
    # 對齊EMA12和EMA26的長度 (EMA26比較短)
    ema12_aligned = ema12[14:]  # 跳過前14個(26-12)
    
    if len(ema12_aligned) != len(ema26):
        min_len = min(len(ema12_aligned), len(ema26))
        ema12_aligned = ema12_aligned[-min_len:]
        ema26 = ema26[-min_len:]
    
    # 計算DIF (快線 - 慢線)
    dif = [ema12_aligned[i] - ema26[i] for i in range(len(ema26))]
    
    # 計算MACD (DIF的9日EMA)
    if len(dif) < 9:
        return None
    
    macd = calculate_ema(dif, 9)
    if not macd:
        return None
    
    # 對齊DIF和MACD
    dif_aligned = dif[8:]  # 跳過前8個(9-1)
    
    # 計算OSC (柱狀圖)
    osc = [dif_aligned[i] - macd[i] for i in range(len(macd))]
    
    return {
        'dif': dif_aligned[-1] if dif_aligned else 0,
        'macd': macd[-1] if macd else 0,
        'osc': osc[-1] if osc else 0,
        'dif_history': dif_aligned[-5:] if len(dif_aligned) >= 5 else dif_aligned,
        'macd_history': macd[-5:] if len(macd) >= 5 else macd,
        'osc_history': osc[-5:] if len(osc) >= 5 else osc
    }

def calculate_kd(high_prices, low_prices, close_prices, k_period=9, d_period=3):
    """計算KD指標"""
    if len(high_prices) < k_period or len(low_prices) < k_period or len(close_prices) < k_period:
        return None
    
    rsv_values = []
    
    # 計算RSV
    for i in range(k_period - 1, len(close_prices)):
        period_high = max(high_prices[i - k_period + 1:i + 1])
        period_low = min(low_prices[i - k_period + 1:i + 1])
        current_close = close_prices[i]
        
        if period_high == period_low:
            rsv = 50  # 避免除零
        else:
            rsv = (current_close - period_low) / (period_high - period_low) * 100
        
        rsv_values.append(rsv)
    
    if not rsv_values:
        return None
    
    # 計算K值 (RSV的移動平均)
    k_values = []
    k_value = 50  # 初始K值
    
    for rsv in rsv_values:
        k_value = (rsv + (d_period - 1) * k_value) / d_period
        k_values.append(k_value)
    
    # 計算D值 (K值的移動平均)
    d_values = []
    d_value = 50  # 初始D值
    
    for k in k_values:
        d_value = (k + (d_period - 1) * d_value) / d_period
        d_values.append(d_value)
    
    return {
        'k': k_values[-1] if k_values else 50,
        'd': d_values[-1] if d_values else 50,
        'k_history': k_values[-5:] if len(k_values) >= 5 else k_values,
        'd_history': d_values[-5:] if len(d_values) >= 5 else d_values
    }

def analyze_stock_complete(reststock, symbol):
    """完整股票分析 (整合即時行情 + 技術指標)"""
    try:
        # === 取得所有必要資料 ===
        ticker = reststock.intraday.ticker(symbol=symbol)
        quote = reststock.intraday.quote(symbol=symbol)
        trades = reststock.intraday.trades(symbol=symbol, limit=50)
        volumes = reststock.intraday.volumes(symbol=symbol)
        candles_1m = reststock.intraday.candles(symbol=symbol, timeframe="1")  # 1分K
        
        # 取得歷史資料
        from_date = time.strftime('%Y-%m-%d', time.localtime(time.time() - 60*24*3600))
        to_date = time.strftime('%Y-%m-%d')
        historical_data = reststock.historical.candles(**{
            "symbol": symbol,
            "from": from_date,
            "to": to_date,
            "timeframe": "D"
        })
        
        if not ticker:
            print(f"找不到 {symbol}")
            return False
        
        # 顯示標題
        current_time = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n{'='*60}")
        print(f"{ticker['name']} ({symbol}) 完整分析")
        print(f"分析時間: {current_time}")
        print(f"{'='*60}")
        
        # === 1. 市場概況 ===
        market_data = get_market_overview(reststock)
        show_market_sentiment(market_data)
        
        # === 2. 個股即時資訊 ===
        current_price = quote.get('lastPrice') or quote.get('closePrice') if quote else None
        
        if quote:
            price = current_price
            change = quote.get('change', 0)
            change_pct = quote.get('changePercent', 0)
            
            trend = "+" if change > 0 else "-" if change < 0 else "="
            print(f"\n個股即時資訊")
            print("-" * 30)
            print(f"目前價格: {price} {trend} {change:+.1f} ({change_pct:+.2f}%)")
            print(f"開盤:{quote.get('openPrice')} 最高:{quote.get('highPrice')} 最低:{quote.get('lowPrice')}")
            print(f"成交量:{quote.get('total',{}).get('tradeVolume',0):,}張")
        
        # === 3. 技術指標分析 ===
        if historical_data and historical_data.get('data'):
            candles = historical_data['data']
            close_prices = [candle.get('close', 0) for candle in candles]
            high_prices = [candle.get('high', 0) for candle in candles]
            low_prices = [candle.get('low', 0) for candle in candles]
            
            # 過濾無效價格
            valid_data = [(h, l, c) for h, l, c in zip(high_prices, low_prices, close_prices) if h > 0 and l > 0 and c > 0]
            if valid_data:
                high_prices, low_prices, close_prices = zip(*valid_data)
                high_prices, low_prices, close_prices = list(high_prices), list(low_prices), list(close_prices)
            
            print(f"\n技術指標分析")
            print("-" * 30)
            
            # MA5/MA10
            if len(close_prices) >= 10:
                ma5_values = calculate_ma(close_prices, 5)
                ma10_values = calculate_ma(close_prices, 10)
                
                if ma5_values and ma10_values:
                    current_ma5 = ma5_values[-1]
                    current_ma10 = ma10_values[-1]
                    
                    print(f"MA5:  {current_ma5:.2f}")
                    print(f"MA10: {current_ma10:.2f}")
                    
                    if current_price:
                        ma5_diff = ((current_price - current_ma5) / current_ma5) * 100
                        ma10_diff = ((current_price - current_ma10) / current_ma10) * 100
                        print(f"股價 vs MA5:  {ma5_diff:+.2f}% ({'上方' if ma5_diff > 0 else '下方'})")
                        print(f"股價 vs MA10: {ma10_diff:+.2f}% ({'上方' if ma10_diff > 0 else '下方'})")
                        
                        # MA排列
                        if ma5_values[-1] > ma10_values[-1]:
                            print("MA排列: 多頭 (MA5 > MA10)")
                        else:
                            print("MA排列: 空頭 (MA5 < MA10)")
            
            # MACD
            if len(close_prices) >= 26:
                macd_data = calculate_macd(close_prices)
                if macd_data:
                    print(f"\nMACD: DIF:{macd_data['dif']:+.3f} MACD:{macd_data['macd']:+.3f} OSC:{macd_data['osc']:+.3f}")
                    if macd_data['dif'] > macd_data['macd'] and macd_data['osc'] > 0:
                        print("MACD訊號: 多頭")
                    else:
                        print("MACD訊號: 空頭")
            
            # KD
            if len(close_prices) >= 9:
                kd_data = calculate_kd(high_prices, low_prices, close_prices)
                if kd_data:
                    k_val = kd_data['k']
                    d_val = kd_data['d']
                    print(f"KD: K:{k_val:.1f} D:{d_val:.1f}")
                    
                    if k_val > 80:
                        print("KD狀態: 超買")
                    elif k_val < 20:
                        print("KD狀態: 超賣")
                    else:
                        print("KD狀態: 正常")
        
        # === 4. VWAP ===
        current_vwap = calculate_vwap(candles_1m)
        if current_vwap and current_price:
            vwap_diff = ((current_price - current_vwap) / current_vwap) * 100
            print(f"VWAP: {current_vwap:.2f} (股價{vwap_diff:+.2f}%)")
        
        # === 5. 大單分析 ===
        big_orders = analyze_big_orders(trades)
        if big_orders:
            print(f"\n大單流向 (50張以上)")
            print("-" * 30)
            print(f"大單: {big_orders['total_orders']}筆 {big_orders['total_volume']:,}張")
            if big_orders['bid_volume'] > 0 or big_orders['ask_volume'] > 0:
                print(f"內盤:{big_orders['bid_volume']:,}張 外盤:{big_orders['ask_volume']:,}張")
        
        # === 6. 簡易走勢圖 ===
        draw_simple_chart(candles_1m)
        
        # === 7. 五檔報價 ===
        if quote:
            print(f"\n五檔報價")
            print("-" * 15)
            asks = quote.get('asks', [])[:3]
            bids = quote.get('bids', [])[:3]
            
            for i, ask in enumerate(asks, 1):
                print(f"賣{i}:{ask.get('price'):>6}({ask.get('size'):>3}張)")
            print(f"現價:{current_price:>6}")
            for i, bid in enumerate(bids, 1):
                print(f"買{i}:{bid.get('price'):>6}({bid.get('size'):>3}張)")
        
        # === 8. 成交明細 ===
        if trades and trades.get('data'):
            print(f"\n成交明細")
            print("-" * 15)
            for trade in trades['data'][:5]:
                t = time.strftime('%H:%M:%S', time.localtime(trade.get('time',0)/1000000))
                size = trade.get('size', 0)
                size_mark = " *" if size >= 50 else ""
                print(f"{t} {trade.get('price'):>5} {size:>3}張{size_mark}")
        
        # === 9. 分價量表 ===
        if volumes and volumes.get('data'):
            print(f"\n分價量表")
            print("-" * 20)
            print("價格  總量  內盤  外盤")
            print("-" * 20)
            data = sorted(volumes['data'], key=lambda x: x.get('price', 0), reverse=True)
            for item in data[:5]:
                price_vol = item.get('price', 0)
                volume = item.get('volume', 0)
                bid_vol = item.get('volumeAtBid', 0)
                ask_vol = item.get('volumeAtAsk', 0)
                print(f"{price_vol:>4} {volume:>5} {bid_vol:>5} {ask_vol:>5}")
        
        print(f"{'='*60}")
        return True
        
    except Exception as e:
        print(f"分析失敗: {e}")
        return False

def init_system():
    """初始化系統並登入"""
    global sdk, reststock, login_success
    
    # 初始化全域變數
    sdk = None
    reststock = None
    login_success = False
    
    print("股票分析系統初始化中...")
    
    # 執行登入
    login_thread()
    
    return login_success

def analyze_stock(symbol):
    """分析指定股票 (外部調用接口 - 不登出版本)"""
    global reststock, login_success
    
    if not login_success:
        print("系統尚未登入成功")
        return False
    
    if not symbol:
        print("請提供股票代碼")
        return False
    
    symbol = symbol.strip().upper()
    return analyze_stock_complete(reststock, symbol)

def analyze_stock_with_logout(symbol):
    """分析股票後自動登出 (Telegram 機器人專用)"""
    global reststock, login_success
    
    if not login_success:
        print("系統尚未登入成功")
        return False
    
    if not symbol:
        print("請提供股票代碼")
        return False
    
    symbol = symbol.strip().upper()
    
    try:
        # 執行分析
        result = analyze_stock_complete(reststock, symbol)
        
        # 分析完成後立即登出
        logout_system()
        
        return result
        
    except Exception as e:
        print(f"分析過程中發生錯誤: {e}")
        # 即使發生錯誤也要嘗試登出
        try:
            logout_system()
        except:
            pass
        return False

def main():
    """主程序 - 支援命令列參數"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python GaN.py <股票代碼>")
        print("  例如: python GaN.py 2330")
        return
    
    # 從命令列取得股票代碼
    stock_code = sys.argv[1].strip().upper()
    
    # 初始化系統
    if not init_system():
        print("系統初始化失敗")
        return
    
    # 分析股票 (命令列使用不自動登出)
    success = analyze_stock(stock_code)
    
    if success:
        print("分析完成")
    else:
        print("分析失敗")

# 提供外部調用的接口
def run_analysis(stock_code):
    """供外部模組調用的分析函數 (不自動登出)"""
    # 初始化系統 (如果尚未初始化)
    if not login_success:
        if not init_system():
            return False
    
    return analyze_stock(stock_code)

def run_analysis_with_logout(stock_code):
    """供 Telegram 機器人調用的分析函數 (包含自動登出)"""
    # 初始化系統 (如果尚未初始化)
    if not login_success:
        if not init_system():
            return False
    
    return analyze_stock_with_logout(stock_code)

if __name__ == "__main__":
    main()
