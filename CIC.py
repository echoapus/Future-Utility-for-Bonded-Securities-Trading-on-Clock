from login_helper import login
import time
import threading
import math
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue
import os

# 全域變數
sdk = None
reststock = None
login_success = False


def load_exclude_list(file_path="etf.list"):
    """讀取排除清單"""
    exclude_symbols = set()

    if not os.path.exists(file_path):
        print(f"警告: 找不到排除清單檔案 {file_path}")
        return exclude_symbols

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # 跳過空行和註解行
                if line and not line.startswith("#"):
                    exclude_symbols.add(line)

        print(f"已載入排除清單: {len(exclude_symbols)} 個代碼 (來源: {file_path})")
        if exclude_symbols:
            # 顯示前10個排除代碼做確認
            sample_codes = list(exclude_symbols)[:10]
            print(
                f"排除代碼範例: {', '.join(sample_codes)}"
                + (
                    f" ...等{len(exclude_symbols)}個"
                    if len(exclude_symbols) > 10
                    else ""
                )
            )

    except Exception as e:
        print(f"讀取排除清單失敗: {e}")

    return exclude_symbols


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


def calculate_volume_ratio(symbol, reststock):
    """計算5分鐘量比"""
    try:
        # 取得5分鐘K線
        candles = reststock.intraday.candles(symbol=symbol, timeframe="5")
        if not candles or not candles.get("data") or len(candles["data"]) < 2:
            return 0

        data = candles["data"]
        current_volume = data[-1].get("volume", 0)

        # 計算平均5分鐘成交量 (前10根K線平均)
        if len(data) >= 11:
            avg_volumes = [candle.get("volume", 0) for candle in data[-11:-1]]
            avg_volume = sum(avg_volumes) / len(avg_volumes) if avg_volumes else 1
        else:
            avg_volume = current_volume

        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
        return volume_ratio

    except Exception as e:
        return 0


def calculate_opening_momentum(symbol, reststock):
    """計算開盤5分鐘內漲跌幅"""
    try:
        # 取得1分鐘K線
        candles = reststock.intraday.candles(symbol=symbol, timeframe="1")
        if not candles or not candles.get("data") or len(candles["data"]) < 5:
            return 0

        data = candles["data"]

        # 取得開盤價和開盤後5分鐘的價格
        open_price = data[0].get("open", 0)
        five_min_price = (
            data[4].get("close", 0) if len(data) >= 5 else data[-1].get("close", 0)
        )

        if open_price > 0:
            momentum = ((five_min_price - open_price) / open_price) * 100
            return abs(momentum)
        return 0

    except Exception as e:
        return 0


def calculate_vwap(candles_data):
    """計算當日VWAP"""
    if not candles_data or not candles_data.get("data"):
        return None

    total_pv = 0
    total_volume = 0

    for candle in candles_data["data"]:
        high = candle.get("high", 0)
        low = candle.get("low", 0)
        close = candle.get("close", 0)
        volume = candle.get("volume", 0)

        if volume > 0:
            typical_price = (high + low + close) / 3
            total_pv += typical_price * volume
            total_volume += volume

    return total_pv / total_volume if total_volume > 0 else None


def check_price_breakthrough(quote_data):
    """檢查是否突破昨高/昨低"""
    if not quote_data:
        return False, ""

    open_price = quote_data.get("openPrice", 0)
    prev_close = quote_data.get("previousClose", 0)
    high_price = quote_data.get("highPrice", 0)
    low_price = quote_data.get("lowPrice", 0)

    breakthrough = False
    signal = ""

    # 簡單判斷：開盤突破昨收盤價
    if open_price > prev_close * 1.02:  # 開盤突破昨收2%以上
        breakthrough = True
        signal = "突破昨高"
    elif open_price < prev_close * 0.98:  # 開盤跌破昨收2%以上
        breakthrough = True
        signal = "跌破昨低"

    return breakthrough, signal


def analyze_order_book(quote_data):
    """分析五檔掛單"""
    if not quote_data:
        return False, ""

    bids = quote_data.get("bids", [])
    asks = quote_data.get("asks", [])

    if not bids or not asks:
        return False, ""

    # 分析賣1是否超厚
    sell1_size = asks[0].get("size", 0) if asks else 0
    buy1_size = bids[0].get("size", 0) if bids else 0

    signals = []

    # 賣1超厚 (大於買1的3倍以上)
    if sell1_size > buy1_size * 3 and sell1_size > 100:
        signals.append("賣1超厚")

    # 買1虛虛的但價格推升
    current_price = quote_data.get("lastPrice", 0)
    prev_close = quote_data.get("previousClose", 0)

    if buy1_size < 50 and current_price > prev_close * 1.01:
        signals.append("買盤虛但推升")

    has_signal = len(signals) > 0
    return has_signal, " | ".join(signals)


def analyze_single_stock(stock_info, reststock):
    """分析單一股票的函數 (供多線程使用)"""
    symbol = stock_info.get("symbol", "")
    name = stock_info.get("name", "")

    if not symbol:
        return None

    try:
        # 取得股票資料
        quote = reststock.intraday.quote(symbol=symbol)

        if not quote:
            return None

        # 第二階段篩選：技術條件
        required_pass = []  # 必要條件
        bonus_pass = []  # 加分條件

        # 成交量已在第一階段篩選，這裡只需記錄
        trade_volume = quote.get("total", {}).get("tradeVolume", 0)
        required_pass.append(f"量{trade_volume:,}張")

        # 必要條件：價格波動篩選
        high_price = quote.get("highPrice", 0)
        low_price = quote.get("lowPrice", 0)
        ref_price = quote.get("referencePrice", 0) or quote.get("previousClose", 0)

        price_range = 0
        if ref_price > 0:
            price_range = ((high_price - low_price) / ref_price) * 100
            if price_range >= 2.0:  # 日內波動 >= 2%
                required_pass.append(f"波動{price_range:.1f}%")

        # 如果必要條件未全部通過，返回None
        if len(required_pass) < 2:
            return None

        # 加分條件：量比篩選 (簡化版)
        vol_ratio = 0
        try:
            candles_5m = reststock.intraday.candles(symbol=symbol, timeframe="5")
            if candles_5m and candles_5m.get("data") and len(candles_5m["data"]) >= 2:
                data = candles_5m["data"]
                current_vol = data[-1].get("volume", 0)
                prev_vol = data[-2].get("volume", 1)
                vol_ratio = current_vol / prev_vol if prev_vol > 0 else 0
        except:
            vol_ratio = 0

        if vol_ratio >= 2.0:  # 量比 >= 2.0
            bonus_pass.append(f"量比{vol_ratio:.1f}")

        # 加分條件：開盤動能篩選 (簡化版)
        momentum = 0
        try:
            open_price = quote.get("openPrice", 0)
            current_price = quote.get("lastPrice") or quote.get("closePrice", 0)
            if open_price > 0:
                momentum = abs((current_price - open_price) / open_price) * 100
        except:
            momentum = 0

        if momentum >= 1.5:  # 開盤動能 >= 1.5%
            bonus_pass.append(f"動能{momentum:.1f}%")

        # 加分條件：VWAP乖離篩選 (簡化版)
        current_price = quote.get("lastPrice") or quote.get("closePrice", 0)
        vwap_dev = 0

        # 簡化VWAP計算 - 使用當日均價估算
        avg_price = quote.get("avgPrice", 0)
        if avg_price > 0 and current_price > 0:
            vwap_dev = abs((current_price - avg_price) / avg_price) * 100
            if vwap_dev >= 0.7:  # VWAP乖離 >= 0.7%
                bonus_pass.append(f"VWAP{vwap_dev:.1f}%")

        # 型態和掛單分析
        breakthrough, breakthrough_signal = check_price_breakthrough(quote)
        order_signal, order_detail = analyze_order_book(quote)

        # 計算綜合分數
        base_score = len(required_pass)  # 基礎分數 (2分)
        bonus_score = len(bonus_pass)  # 加分項目
        extra_score = 0

        # 額外加分項目
        if breakthrough:
            extra_score += 1
        if order_signal:
            extra_score += 1

        total_score = base_score + bonus_score + extra_score

        change = quote.get("change", 0)
        change_pct = quote.get("changePercent", 0)

        # 組合所有通過條件
        all_conditions = required_pass + bonus_pass

        return {
            "symbol": symbol,
            "name": name,
            "price": current_price,
            "change": change,
            "change_pct": change_pct,
            "volume": trade_volume,
            "price_range": price_range,
            "vol_ratio": vol_ratio,
            "momentum": momentum,
            "vwap_dev": vwap_dev,
            "required_pass": required_pass,
            "bonus_pass": bonus_pass,
            "all_conditions": all_conditions,
            "breakthrough": breakthrough_signal,
            "order_signal": order_detail,
            "base_score": base_score,
            "bonus_score": bonus_score,
            "extra_score": extra_score,
            "total_score": total_score,
        }

    except Exception as e:
        return None


def screen_stocks(reststock):
    """股票篩選主程式"""
    # 載入排除清單
    exclude_symbols = load_exclude_list("etf.list")

    # 第一階段：建立精確的候選池
    try:
        print("第一階段：建立候選池")
        print("正在取得全市場上市股票資料...")

        # 使用 snapshot/quotes 取得全市場上市股票
        market_snapshot = reststock.snapshot.quotes(market="TSE", type="COMMONSTOCK")

        if not market_snapshot or not market_snapshot.get("data"):
            print("無法取得市場快照資料")
            return []

        all_stocks = market_snapshot["data"]
        print(f"取得 {len(all_stocks)} 檔上市股票資料")

        # 第一階段篩選條件
        print("正在進行第一階段篩選...")
        filtered_stocks = []

        # 排除清單統計
        exclude_keywords = ["ETF", "ETN", "債", "期"]
        excluded_by_keyword = 0
        excluded_by_list = 0
        excluded_no_volume = 0
        excluded_low_volume = 0

        for stock in all_stocks:
            symbol = stock.get("symbol", "")
            name = stock.get("name", "")
            volume = stock.get("tradeVolume", 0)

            if not symbol or not name:
                continue

            # 排除條件檢查
            should_exclude = False
            exclude_reason = ""

            # 1. 檢查是否在排除清單中
            if symbol in exclude_symbols:
                should_exclude = True
                exclude_reason = "排除清單"
                excluded_by_list += 1

            # 2. 檢查名稱是否包含排除關鍵字
            elif any(keyword in name for keyword in exclude_keywords):
                should_exclude = True
                exclude_reason = "關鍵字"
                excluded_by_keyword += 1

            # 3. 檢查是否停牌（無成交量）
            elif volume == 0:
                should_exclude = True
                exclude_reason = "停牌"
                excluded_no_volume += 1

            # 4. 檢查成交量是否 >= 2,000張
            elif volume < 2000:
                should_exclude = True
                exclude_reason = "成交量不足"
                excluded_low_volume += 1

            # 如果通過所有檢查，加入候選池
            if not should_exclude:
                filtered_stocks.append(
                    {
                        "symbol": symbol,
                        "name": name,
                        "volume": volume,
                        "price": stock.get("closePrice", 0),
                        "change_pct": stock.get("changePercent", 0),
                    }
                )

        # 按成交量排序 (大到小)
        filtered_stocks.sort(key=lambda x: x["volume"], reverse=True)

        print(f"第一階段篩選完成:")
        print(f"   原始股票: {len(all_stocks)} 檔")
        print(
            f"   篩選條件: 排除清單 + 排除ETF/ETN/債券/期貨 + 排除停牌股 + 成交量>=2,000張"
        )
        print(f"   候選池: {len(filtered_stocks)} 檔符合條件")

        if len(filtered_stocks) == 0:
            print("沒有股票符合第一階段條件！")
            return []

        # 顯示詳細篩選統計
        print(f"排除統計:")
        print(f"   排除清單: {excluded_by_list} 檔")
        print(f"   ETF/ETN/債券/期貨關鍵字: {excluded_by_keyword} 檔")
        print(f"   停牌無交易: {excluded_no_volume} 檔")
        print(f"   成交量<2,000張: {excluded_low_volume} 檔")
        print(
            f"   總排除: {excluded_by_list + excluded_by_keyword + excluded_no_volume + excluded_low_volume} 檔"
        )

        # 顯示候選池前10大
        print(f"\n候選池成交量前10大:")
        print(f"{'排名':<4} {'代碼':<8} {'股名':<12} {'成交量(張)':<12} {'漲跌幅':<8}")
        print("-" * 50)

        for i, stock in enumerate(filtered_stocks[:10], 1):
            print(
                f"{i:<4} {stock['symbol']:<8} {stock['name']:<12} {stock['volume']:>10,} {stock['change_pct']:>+6.2f}%"
            )

        # 重新組織成原來的格式供後續分析
        stock_list = [
            {"symbol": s["symbol"], "name": s["name"]} for s in filtered_stocks
        ]

        # 分析設定：分析全部符合條件的股票
        total_candidates = len(stock_list)
        analyze_count = total_candidates

        print(f"\n第二階段分析設定:")
        print(f"將對全部 {analyze_count} 檔候選股票進行技術分析")

    except Exception as e:
        print(f"第一階段篩選失敗: {e}")
        print("嘗試使用備用方法...")

        # 備用方法：原來的方式
        try:
            tickers = reststock.intraday.tickers(
                type="EQUITY", exchange="TWSE", isNormal=True
            )
            stock_list = tickers.get("data", [])[:100] if tickers else []
            analyze_count = len(stock_list)
            print(f"使用備用方法，分析 {analyze_count} 檔股票")
        except:
            return []

    # 第二階段：多線程技術分析
    print("\n第二階段：多線程技術分析")
    print("=" * 80)

    # 篩選條件說明
    print(f"篩選條件:")
    print(f"成交量 >= 2,000張 (必要) - 第一階段已篩選")
    print(f"日內波動 >= 2.0% (必要)")
    print(f"量比 >= 2.0 (加分)")
    print(f"開盤動能 >= 1.5% (加分)")
    print(f"VWAP乖離 >= 0.7% (加分)")
    print("符合越多加分條件，排序越優先!")
    print("=" * 80)

    # 多線程設定
    max_workers = min(10, len(stock_list))  # 最多10個線程，避免API限制

    qualified_stocks = []
    processed = 0
    start_time = time.time()

    # 使用 ThreadPoolExecutor 進行多線程處理
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任務到線程池
        future_to_stock = {
            executor.submit(analyze_single_stock, stock, reststock): stock
            for stock in stock_list
        }

        # 處理完成的任務
        for future in as_completed(future_to_stock):
            processed += 1
            stock = future_to_stock[future]

            # 顯示進度和速度
            elapsed = time.time() - start_time
            rate = processed / elapsed if elapsed > 0 else 0
            eta = (analyze_count - processed) / rate if rate > 0 else 0

            print(
                f"分析中... {processed}/{analyze_count} "
                f"({processed/analyze_count*100:.1f}%) "
                f"速度:{rate:.1f}檔/秒 預計剩餘:{eta:.0f}秒",
                end="\r",
            )

            try:
                result = future.result()
                if result:  # 如果股票符合條件
                    qualified_stocks.append(result)
            except Exception as e:
                # 個別股票分析失敗不影響整體
                pass

    total_time = time.time() - start_time
    print(
        f"\n第二階段完成！耗時 {total_time:.1f} 秒，平均 {len(stock_list)/total_time:.1f} 檔/秒"
    )
    print("=" * 80)
    return qualified_stocks


def display_results(stocks):
    """顯示篩選結果"""
    if not stocks:
        print("沒有找到符合條件的股票")
        return

    # 按分數排序 (總分 > 加分項 > 額外分)
    stocks.sort(
        key=lambda x: (x["total_score"], x["bonus_score"], x["extra_score"]),
        reverse=True,
    )

    print(f"\n篩選結果 (共 {len(stocks)} 檔)")
    print("=" * 110)
    print(
        f"{'代碼':<8} {'股名':<12} {'價格':<8} {'漲跌':<10} {'量(張)':<10} {'必要':<15} {'加分':<25} {'總分':<6}"
    )
    print("-" * 110)

    for i, stock in enumerate(stocks[:20], 1):  # 顯示前20檔
        symbol = stock["symbol"]
        name = stock["name"][:8]  # 截斷股名
        price = f"{stock['price']:.1f}"
        change_text = f"{stock['change']:+.1f}({stock['change_pct']:+.1f}%)"
        volume = f"{stock['volume']:,}"

        # 必要條件 (應該都有2個)
        required_text = " | ".join(stock["required_pass"])

        # 加分條件
        bonus_text = " | ".join(stock["bonus_pass"]) if stock["bonus_pass"] else "無"

        # 總分顯示
        score_text = f"{stock['total_score']}分"
        if stock["bonus_score"] > 0:
            score_text += "+"
        if stock["extra_score"] > 0:
            score_text += "*"

        print(
            f"{symbol:<8} {name:<12} {price:<8} {change_text:<10} {volume:<10} {required_text:<15} {bonus_text:<25} {score_text:<6}"
        )

    print("=" * 110)

    # 統計資訊
    if stocks:
        avg_score = sum(s["total_score"] for s in stocks) / len(stocks)
        max_score = max(s["total_score"] for s in stocks)

        # 分組統計
        full_bonus = [s for s in stocks if s["bonus_score"] == 3]  # 加分項全滿
        high_bonus = [s for s in stocks if s["bonus_score"] >= 2]  # 高加分
        basic_only = [s for s in stocks if s["bonus_score"] == 0]  # 僅符合基本條件

        print(f"\n統計資訊:")
        print(f"平均分數: {avg_score:.1f} | 最高分數: {max_score}")
        print(f"滿分加分股: {len(full_bonus)}檔")
        print(f"高加分股: {len(high_bonus)}檔")
        print(f"基本條件股: {len(basic_only)}檔")

        if full_bonus:
            print(
                f"滿分推薦: "
                + ", ".join(
                    [f"{s['symbol']}({s['total_score']}分)" for s in full_bonus[:5]]
                )
            )

        # 各加分條件統計
        vol_ratio_pass = [s for s in stocks if s["vol_ratio"] >= 2.0]
        momentum_pass = [s for s in stocks if s["momentum"] >= 1.5]
        vwap_pass = [s for s in stocks if s["vwap_dev"] >= 0.7]

        print(f"\n加分條件統計:")
        print(
            f"量比達標: {len(vol_ratio_pass)}檔 | 開盤動能: {len(momentum_pass)}檔 | VWAP乖離: {len(vwap_pass)}檔"
        )


def main():
    global sdk, reststock, login_success

    print("股票即時篩選系統")
    print("=" * 50)

    # 啟動登入線程
    print("系統初始化中...")
    login_thread_obj = threading.Thread(target=login_thread)
    login_thread_obj.start()

    # 等待登入完成
    login_thread_obj.join()

    if not login_success:
        print("登入失敗，程式結束")
        return

    try:
        # 執行篩選
        qualified_stocks = screen_stocks(reststock)

        # 顯示結果
        display_results(qualified_stocks)

    except KeyboardInterrupt:
        print("\n使用者中斷程式")
    except Exception as e:
        print(f"程式執行錯誤: {e}")
    finally:
        print("程式結束")


if __name__ == "__main__":
    main()
