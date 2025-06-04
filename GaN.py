# GaN.py - 股票技術分析系統 (A1/A2 邏輯修正版)
# 修正時間: 2025-06-04
# 修正內容: A1-MA排列邏輯矛盾, A2-MACD訊號判定

from login_helper import login
import time
import threading
import sys
import math

# 全域變數
sdk = None
reststock = None
login_success = False

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
    """登出富邦系統 - 加強版"""
    global sdk, reststock, login_success
    
    try:
        if sdk:
            # 關閉即時資料連線
            if hasattr(sdk, 'close_realtime'):
                try:
                    sdk.close_realtime()
                    print("已關閉即時資料連線")
                except:
                    pass
            
            # 登出系統
            sdk.logout()
            print("已登出富邦系統")
        
        # 重置全域變數
        sdk = None
        reststock = None
        login_success = False
        
        # 強制垃圾回收
        import gc
        gc.collect()
        
        return True
        
    except Exception as e:
        print(f"登出失敗: {e}")
        # 即使登出失敗也要重置變數
        sdk = None
        reststock = None
        login_success = False
        return False

def analyze_big_orders(trades_data):
    """分析大單流向 (50張以上) - 修正版"""
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
            
            # 改進的內外盤判斷
            price = trade.get('price', 0)
            
            # 方法1：使用交易標記
            if 'tick' in trade:
                tick = trade['tick']
                if tick in ['up', 'plus', '+', 1]:
                    big_ask_volume += size  # 外盤（主動買進）
                elif tick in ['down', 'minus', '-', -1]:
                    big_bid_volume += size  # 內盤（主動賣出）
                # 平盤不歸類
            
            # 方法2：如果沒有tick資訊，使用五檔價格判斷
            elif 'bid' in trade and 'ask' in trade:
                bid = trade.get('bid', 0)
                ask = trade.get('ask', 0)
                
                if bid and ask and price:
                    # 接近賣價表示主動買進（外盤）
                    if abs(price - ask) < abs(price - bid):
                        big_ask_volume += size
                    # 接近買價表示主動賣出（內盤）
                    elif abs(price - bid) < abs(price - ask):
                        big_bid_volume += size
                    # 距離相等則不歸類
    
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
    
def analyze_order_book_strength(quote_data):
    """分析五檔買賣力道 - 修正版"""
    if not quote_data:
        return None
    
    bids = quote_data.get('bids', [])
    asks = quote_data.get('asks', [])
    
    if not bids or not asks:
        return None
    
    # 計算買賣壓力
    total_bid_size = sum(bid.get('size', 0) for bid in bids)
    total_ask_size = sum(ask.get('size', 0) for ask in asks)
    total_size = total_bid_size + total_ask_size
    
    if total_size == 0:
        return None
    
    # 取得當前價格
    current_price = quote_data.get('lastPrice') or quote_data.get('closePrice', 0)
    if current_price == 0:
        return None
    
    # 修正：改進價格加權計算
    bid_strength = 0
    ask_strength = 0
    
    # 買盤力道計算（距離現價越近權重越高）
    for i, bid in enumerate(bids):
        price = bid.get('price', 0)
        size = bid.get('size', 0)
        if price > 0 and current_price > 0:
            # 距離現價的比例 (0-1之間)
            distance_ratio = price / current_price
            # 檔次權重 (第一檔權重最高)
            level_weight = 1 - (i * 0.15)  # 每檔遞減15%
            # 綜合權重
            weight = distance_ratio * level_weight
            bid_strength += size * weight
    
    # 賣盤力道計算（距離現價越近權重越高）
    for i, ask in enumerate(asks):
        price = ask.get('price', 0)
        size = ask.get('size', 0)
        if price > 0 and current_price > 0:
            # 距離現價的比例 (0-1之間)
            distance_ratio = current_price / price
            # 檔次權重 (第一檔權重最高)
            level_weight = 1 - (i * 0.15)  # 每檔遞減15%
            # 綜合權重
            weight = distance_ratio * level_weight
            ask_strength += size * weight
    
    # 計算力道比例
    total_strength = bid_strength + ask_strength
    if total_strength == 0:
        return None
    
    bid_ratio = (bid_strength / total_strength) * 100
    ask_ratio = (ask_strength / total_strength) * 100
    
    # 判斷買賣勢力
    if bid_ratio > 65:
        market_sentiment = "買盤強勢"
    elif ask_ratio > 65:
        market_sentiment = "賣盤強勢"
    elif bid_ratio > 55:
        market_sentiment = "買盤偏強"
    elif ask_ratio > 55:
        market_sentiment = "賣盤偏強"
    else:
        market_sentiment = "買賣均衡"
    
    # 計算價差分析
    best_bid = bids[0].get('price', 0) if bids else 0
    best_ask = asks[0].get('price', 0) if asks else 0
    spread = best_ask - best_bid if best_ask > 0 and best_bid > 0 else 0
    spread_pct = (spread / current_price) * 100 if current_price > 0 and spread > 0 else 0
    
    return {
        'total_bid_size': total_bid_size,
        'total_ask_size': total_ask_size,
        'bid_ratio': bid_ratio,
        'ask_ratio': ask_ratio,
        'bid_strength': bid_strength,
        'ask_strength': ask_strength,
        'market_sentiment': market_sentiment,
        'spread': spread,
        'spread_pct': spread_pct,
        'best_bid': best_bid,
        'best_ask': best_ask
    }


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

def calculate_ema(prices, period):
    """計算指數移動平均線 (EMA) - 修正版"""
    if len(prices) < period:
        return None
    
    ema_values = []
    multiplier = 2 / (period + 1)
    
    # 第一個EMA值使用SMA
    sma = sum(prices[:period]) / period
    ema_values.append(sma)
    
    # 後續EMA計算 - 從period開始
    for i in range(period, len(prices)):
        ema = (prices[i] * multiplier) + (ema_values[-1] * (1 - multiplier))
        ema_values.append(ema)
    
    return ema_values

def calculate_ma(prices, period):
    """計算移動平均線"""
    if len(prices) < period:
        return None
    
    ma_values = []
    for i in range(period - 1, len(prices)):
        ma = sum(prices[i - period + 1:i + 1]) / period
        ma_values.append(ma)
    
    return ma_values

def calculate_rsi(prices, period=14):
    """計算RSI指標"""
    if len(prices) < period + 1:
        return None
    
    # 計算價格變化
    gains = []
    losses = []
    
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    if len(gains) < period:
        return None
    
    # 計算第一個RS值
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    if avg_loss == 0:
        return 100  # 避免除零
    
    rs_values = []
    rsi_values = []
    
    # 第一個RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    rs_values.append(rs)
    rsi_values.append(rsi)
    
    # 後續RSI (使用平滑移動平均)
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        if avg_loss == 0:
            rs = float('inf')
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        rs_values.append(rs)
        rsi_values.append(rsi)
    
    return {
        'current': rsi_values[-1] if rsi_values else 50,
        'history': rsi_values[-5:] if len(rsi_values) >= 5 else rsi_values
    }

def calculate_bollinger_bands(prices, period=20, std_dev=2):
    """計算布林通道 - 修正版"""
    if len(prices) < period:
        return None
    
    bb_upper = []
    bb_lower = []
    bb_middle = []
    
    for i in range(period - 1, len(prices)):
        # 取得當前期間的價格
        period_prices = prices[i - period + 1:i + 1]
        
        # 計算移動平均
        mean = sum(period_prices) / period
        bb_middle.append(mean)
        
        # 計算標準差
        variance = sum((x - mean) ** 2 for x in period_prices) / period
        std = math.sqrt(variance)
        
        bb_upper.append(mean + (std_dev * std))
        bb_lower.append(mean - (std_dev * std))
    
    current_price = prices[-1]
    current_upper = bb_upper[-1] if bb_upper else 0
    current_lower = bb_lower[-1] if bb_lower else 0
    current_middle = bb_middle[-1] if bb_middle else 0
    
    # 計算價格在布林通道中的位置
    if current_upper != current_lower:
        bb_position = (current_price - current_lower) / (current_upper - current_lower)
    else:
        bb_position = 0.5
    
    # 確保位置在0-1之間
    bb_position = max(0, min(1, bb_position))
    
    return {
        'upper': current_upper,
        'middle': current_middle,
        'lower': current_lower,
        'position': bb_position,
        'width': current_upper - current_lower,
        'squeeze': (current_upper - current_lower) / current_middle if current_middle > 0 else 0
    }


def calculate_macd(prices):
    """計算MACD指標 - 修正版"""
    if len(prices) < 26:
        return None
    
    # 計算EMA12和EMA26
    ema12 = calculate_ema(prices, 12)
    ema26 = calculate_ema(prices, 26)
    
    if not ema12 or not ema26:
        return None
    
    # 由於EMA26比EMA12晚開始14個點，需要對齊
    # EMA12 從第12個價格開始，EMA26 從第26個價格開始
    # 所以 EMA12 需要從第 (26-12) = 14 個位置開始取值
    start_offset = 26 - 12  # 14
    ema12_aligned = ema12[start_offset:] if len(ema12) > start_offset else ema12
    
    # 確保兩個數組長度相同
    min_length = min(len(ema12_aligned), len(ema26))
    ema12_aligned = ema12_aligned[:min_length]
    ema26_aligned = ema26[:min_length]
    
    # 計算DIF
    dif = [ema12_aligned[i] - ema26_aligned[i] for i in range(len(ema26_aligned))]
    
    # 計算MACD (DIF的9日EMA)
    if len(dif) < 9:
        return None
    
    macd = calculate_ema(dif, 9)
    if not macd:
        return None
    
    # 對齊DIF和MACD
    dif_aligned = dif[-len(macd):]
    
    # 計算OSC
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
    """計算KD指標 - 修正版"""
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
    
    # 傳統KD計算方式
    # K值 = (2/3) * 前一日K值 + (1/3) * 當日RSV
    # D值 = (2/3) * 前一日D值 + (1/3) * 當日K值
    k_values = []
    d_values = []
    
    k_value = 50  # 初始K值
    d_value = 50  # 初始D值
    
    for rsv in rsv_values:
        # 計算K值 - 使用傳統公式
        k_value = (2/3) * k_value + (1/3) * rsv
        k_values.append(k_value)
        
        # 計算D值 - 使用傳統公式
        d_value = (2/3) * d_value + (1/3) * k_value
        d_values.append(d_value)
    
    return {
        'k': k_values[-1] if k_values else 50,
        'd': d_values[-1] if d_values else 50,
        'k_history': k_values[-5:] if len(k_values) >= 5 else k_values,
        'd_history': d_values[-5:] if len(d_values) >= 5 else d_values
    }

# === A1/A2 修正函數 ===

def analyze_ma_arrangement_fixed(ma5, ma10, ma20, current_price):
    """修正版MA排列分析 - 解決邏輯矛盾"""
    # 基本MA排列
    if ma5 > ma10 > ma20:
        basic = "多頭"
    elif ma5 < ma10 < ma20:
        basic = "空頭"
    else:
        basic = "糾結"
    
    # 股價位置檢查
    above_all_ma = current_price > ma5 and current_price > ma10 and current_price > ma20
    below_all_ma = current_price < ma5 and current_price < ma10 and current_price < ma20
    
    # 計算乖離率
    ma5_deviation = ((current_price - ma5) / ma5) * 100 if ma5 > 0 else 0
    
    # 修正邏輯矛盾
    if basic == "空頭" and above_all_ma:
        if ma5_deviation > 15:
            return "空頭排列，但股價強勢突破"
        else:
            return "空頭排列，股價暫時突破"
    elif basic == "多頭" and below_all_ma:
        if abs(ma5_deviation) > 10:
            return "多頭排列，但股價深度回檔"
        else:
            return "多頭排列，股價暫時回檔"
    else:
        if above_all_ma:
            return f"{basic}排列，股價位於MA上方"
        elif below_all_ma:
            return f"{basic}排列，股價位於MA下方"
        else:
            return f"{basic}排列，股價穿梭於MA間"

def analyze_macd_signal_fixed(dif, macd, osc):
    """修正版MACD訊號判定"""
    signals = []
    
    # 1. 快慢線關係
    if dif > macd:
        signals.append("快線上")
    else:
        signals.append("快線下")
    
    # 2. 零軸位置
    if dif > 0 and macd > 0:
        signals.append("零軸上")
    elif dif < 0 and macd < 0:
        signals.append("零軸下")
    else:
        signals.append("零軸跨")
    
    # 3. OSC動能
    if osc > 0:
        signals.append("動能+")
    else:
        signals.append("動能-")
    
    # 綜合判定
    positive_count = sum([
        dif > macd,
        dif > 0 and macd > 0,
        osc > 0
    ])
    
    if positive_count >= 2:
        signal = "多頭"
    elif positive_count == 1:
        signal = "偏多"
    else:
        signal = "空頭"
    
    detail = " | ".join(signals)
    return signal, detail

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
        
        # === 3. 五檔買賣力道分析 ===
        order_book_analysis = analyze_order_book_strength(quote)
        if order_book_analysis:
            print(f"\n五檔買賣力道")
            print("-" * 30)
            print(f"買盤力道: {order_book_analysis['bid_ratio']:.1f}% ({order_book_analysis['total_bid_size']:,}張)")
            print(f"賣盤力道: {order_book_analysis['ask_ratio']:.1f}% ({order_book_analysis['total_ask_size']:,}張)")
            print(f"市場情緒: {order_book_analysis['market_sentiment']}")
            print(f"買賣價差: {order_book_analysis['spread']:.2f} ({order_book_analysis['spread_pct']:.3f}%)")
        
        # === 4. 技術指標分析 ===
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
            
            # MA5/MA10/MA20
            if len(close_prices) >= 20:
                ma5_values = calculate_ma(close_prices, 5)
                ma10_values = calculate_ma(close_prices, 10)
                ma20_values = calculate_ma(close_prices, 20)
                
                if ma5_values and ma10_values and ma20_values:
                    current_ma5 = ma5_values[-1]
                    current_ma10 = ma10_values[-1]
                    current_ma20 = ma20_values[-1]
                    
                    print(f"MA5:  {current_ma5:.2f}")
                    print(f"MA10: {current_ma10:.2f}")
                    print(f"MA20: {current_ma20:.2f}")
                    
                    if current_price:
                        ma5_diff = ((current_price - current_ma5) / current_ma5) * 100
                        ma10_diff = ((current_price - current_ma10) / current_ma10) * 100
                        ma20_diff = ((current_price - current_ma20) / current_ma20) * 100
                        print(f"股價 vs MA5:  {ma5_diff:+.2f}% ({'上方' if ma5_diff > 0 else '下方'})")
                        print(f"股價 vs MA10: {ma10_diff:+.2f}% ({'上方' if ma10_diff > 0 else '下方'})")
                        print(f"股價 vs MA20: {ma20_diff:+.2f}% ({'上方' if ma20_diff > 0 else '下方'})")
                        
                        # A1修正: MA排列分析 (修正版)
                        ma_result = analyze_ma_arrangement_fixed(
                            current_ma5, current_ma10, current_ma20, current_price
                        )
                        print(f"MA分析: {ma_result}")
            
            # RSI
            if len(close_prices) >= 15:
                rsi_data = calculate_rsi(close_prices)
                if rsi_data:
                    rsi = rsi_data['current']
                    print(f"\nRSI: {rsi:.1f}")
                    if rsi > 70:
                        print("RSI狀態: 超買")
                    elif rsi < 30:
                        print("RSI狀態: 超賣")
                    else:
                        print("RSI狀態: 正常")
            
            # 布林通道
            if len(close_prices) >= 20:
                bb_data = calculate_bollinger_bands(close_prices)
                if bb_data and current_price:
                    print(f"\n布林通道:")
                    print(f"上軌: {bb_data['upper']:.2f}")
                    print(f"中軌: {bb_data['middle']:.2f}")
                    print(f"下軌: {bb_data['lower']:.2f}")
                    print(f"位置: {bb_data['position']*100:.1f}% ({'上半部' if bb_data['position'] > 0.5 else '下半部'})")
                    
                    if bb_data['position'] > 0.8:
                        print("布林狀態: 接近上軌")
                    elif bb_data['position'] < 0.2:
                        print("布林狀態: 接近下軌")
                    else:
                        print("布林狀態: 通道中間")
            
            # A2修正: MACD
            if len(close_prices) >= 26:
                macd_data = calculate_macd(close_prices)
                if macd_data:
                    print(f"\nMACD: DIF:{macd_data['dif']:+.3f} MACD:{macd_data['macd']:+.3f} OSC:{macd_data['osc']:+.3f}")
                    
                    # 使用修正版MACD訊號判定
                    macd_signal, macd_detail = analyze_macd_signal_fixed(
                        macd_data['dif'], macd_data['macd'], macd_data['osc']
                    )
                    print(f"MACD分析: {macd_detail}")
                    print(f"MACD訊號: {macd_signal}")
            
            # KD
            if len(close_prices) >= 9:
                kd_data = calculate_kd(high_prices, low_prices, close_prices)
                if kd_data:
                    k_val = kd_data['k']
                    d_val = kd_data['d']
                    print(f"\nKD: K:{k_val:.1f} D:{d_val:.1f}")
                    
                    if k_val > 80:
                        print("KD狀態: 超買")
                    elif k_val < 20:
                        print("KD狀態: 超賣")
                    else:
                        print("KD狀態: 正常")
                    
                    # KD交叉
                    if len(kd_data['k_history']) >= 2 and len(kd_data['d_history']) >= 2:
                        k_prev = kd_data['k_history'][-2]
                        d_prev = kd_data['d_history'][-2]
                        if k_prev <= d_prev and k_val > d_val:
                            print("KD訊號: 黃金交叉")
                        elif k_prev >= d_prev and k_val < d_val:
                            print("KD訊號: 死亡交叉")
        
        # === 5. VWAP ===
        current_vwap = calculate_vwap(candles_1m)
        if current_vwap and current_price:
            vwap_diff = ((current_price - current_vwap) / current_vwap) * 100
            print(f"\nVWAP: {current_vwap:.2f} (股價{vwap_diff:+.2f}%)")
            if vwap_diff > 0:
                print("VWAP狀態: 股價高於VWAP (偏強)")
            else:
                print("VWAP狀態: 股價低於VWAP (偏弱)")
        
        # === 6. 大單分析 ===
        big_orders = analyze_big_orders(trades)
        if big_orders:
            print(f"\n大單流向 (50張以上)")
            print("-" * 30)
            print(f"大單: {big_orders['total_orders']}筆 {big_orders['total_volume']:,}張")
            if big_orders['bid_volume'] > 0 or big_orders['ask_volume'] > 0:
                print(f"內盤大單:{big_orders['bid_volume']:,}張 ({big_orders['bid_ratio']:.1f}%)")
                print(f"外盤大單:{big_orders['ask_volume']:,}張 ({big_orders['ask_ratio']:.1f}%)")
                
                if big_orders['ask_ratio'] > big_orders['bid_ratio']:
                    print("大單趨勢: 積極買進")
                elif big_orders['bid_ratio'] > big_orders['ask_ratio']:
                    print("大單趨勢: 積極賣出")
                else:
                    print("大單趨勢: 均衡")
        
        # === 7. 簡易走勢圖 ===
        draw_simple_chart(candles_1m)
        
        # === 8. 五檔報價 ===
        if quote:
            print(f"\n五檔報價")
            print("-" * 20)
            asks = quote.get('asks', [])[:5]
            bids = quote.get('bids', [])[:5]
            
            # 顯示賣檔
            for i, ask in enumerate(asks, 1):
                size = ask.get('size', 0)
                price = ask.get('price', 0)
                print(f"賣{i}: {price:>6.2f} ({size:>4}張)")
            
            print(f"{'現價':>4}: {current_price:>6.2f}")
            print("-" * 20)
            
            # 顯示買檔
            for i, bid in enumerate(bids, 1):
                size = bid.get('size', 0)
                price = bid.get('price', 0)
                print(f"買{i}: {price:>6.2f} ({size:>4}張)")
        
        # === 9. 成交明細 ===
        if trades and trades.get('data'):
            print(f"\n成交明細 (最近5筆)")
            print("-" * 25)
            print("時間     價格  張數")
            print("-" * 25)
            for trade in trades['data'][:5]:
                timestamp = trade.get('time', 0)
                if timestamp > 0:
                    t = time.strftime('%H:%M:%S', time.localtime(timestamp/1000000))
                else:
                    t = "N/A"
                size = trade.get('size', 0)
                price = trade.get('price', 0)
                size_mark = " *" if size >= 50 else ""
                print(f"{t} {price:>6.2f} {size:>4}張{size_mark}")
        
        # === 10. 分價量表 ===
        if volumes and volumes.get('data'):
            print(f"\n分價量表 (前5檔)")
            print("-" * 25)
            print(" 價格   總量  內盤  外盤")
            print("-" * 25)
            data = sorted(volumes['data'], key=lambda x: x.get('price', 0), reverse=True)
            for item in data[:5]:
                price_vol = item.get('price', 0)
                volume = item.get('volume', 0)
                bid_vol = item.get('volumeAtBid', 0)
                ask_vol = item.get('volumeAtAsk', 0)
                print(f"{price_vol:>5.1f} {volume:>6} {bid_vol:>5} {ask_vol:>5}")
        
        # === 11. 綜合評分 (修正版) ===
        print(f"\n綜合技術分析評分")
        print("-" * 30)
        
        score = 0
        total_indicators = 0
        
        # MA評分
        if len(close_prices) >= 10 and current_price:
            ma5_values = calculate_ma(close_prices, 5)
            ma10_values = calculate_ma(close_prices, 10)
            if ma5_values and ma10_values:
                if current_price > ma5_values[-1]:
                    score += 1
                if current_price > ma10_values[-1]:
                    score += 1
                if ma5_values[-1] > ma10_values[-1]:
                    score += 1
                total_indicators += 3
        
        # RSI評分
        if len(close_prices) >= 15:
            rsi_data = calculate_rsi(close_prices)
            if rsi_data:
                rsi = rsi_data['current']
                if 30 < rsi < 70:
                    score += 1  # 正常區間
                if rsi > 50:
                    score += 1  # 偏多
                total_indicators += 2
        
        # MACD評分 (修正版)
        if len(close_prices) >= 26:
            macd_data = calculate_macd(close_prices)
            if macd_data:
                dif, macd_val, osc = macd_data['dif'], macd_data['macd'], macd_data['osc']
                
                # 重新計算評分
                bullish_signals = sum([
                    dif > macd_val,              # 快線站上慢線
                    dif > 0 and macd_val > 0,    # 雙線位於零軸上方
                    osc > 0                      # OSC為正
                ])
                
                if bullish_signals >= 2:
                    score += 2  # 多頭
                elif bullish_signals == 1:
                    score += 1  # 偏多
                # 空頭不加分
                
                total_indicators += 2
        
        # KD評分
        if len(close_prices) >= 9:
            kd_data = calculate_kd(high_prices, low_prices, close_prices)
            if kd_data:
                if kd_data['k'] > kd_data['d']:
                    score += 1
                if 20 < kd_data['k'] < 80:
                    score += 1  # 正常區間
                total_indicators += 2
        
        # VWAP評分
        if current_vwap and current_price:
            if current_price > current_vwap:
                score += 1
            total_indicators += 1
        
        # 五檔力道評分
        if order_book_analysis:
            if order_book_analysis['bid_ratio'] > 55:
                score += 1
            total_indicators += 1
        
        if total_indicators > 0:
            final_score = (score / total_indicators) * 100
            print(f"技術面評分: {score}/{total_indicators} ({final_score:.1f}%)")
            
            if final_score >= 70:
                print("技術面評價: 強勢")
            elif final_score >= 50:
                print("技術面評價: 中性偏多")
            elif final_score >= 30:
                print("技術面評價: 中性偏空")
            else:
                print("技術面評價: 弱勢")
        
        print(f"{'='*60}")
        return True
        
    except Exception as e:
        print(f"分析失敗: {e}")
        import traceback
        traceback.print_exc()
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
