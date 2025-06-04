import os
import glob
import shutil
import threading
import time
from datetime import datetime
import twstock
from queue import Queue

# === 設定路徑 ===
BASE_DIR = "/home/botuser/FAngel/CatCage"
OLD_DIR = os.path.join(BASE_DIR, "old")


def ensure_dirs():
    os.makedirs(OLD_DIR, exist_ok=True)


def archive_old_quotes():
    for f in glob.glob(os.path.join(BASE_DIR, "quote_*.txt")):
        shutil.move(f, os.path.join(OLD_DIR, os.path.basename(f)))


def get_latest_symbols_file():
    symbol_files = sorted(
        glob.glob(os.path.join(BASE_DIR, "symbols_*.txt")),
        key=os.path.getmtime,
        reverse=True,
    )
    if not symbol_files:
        raise FileNotFoundError("❌ 找不到 symbols_*.txt")
    return symbol_files[0]


def read_symbols(path):
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def query_quote(stock_id):
    """查詢單一股票報價（使用原本可運行的邏輯）"""
    try:
        stock = twstock.Stock(stock_id)
        latest = stock.data[-1] if stock.data else None
        if not latest:
            return None

        # 使用原本的方式取得股票名稱
        stock_name = "未知"
        try:
            if stock_id in twstock.codes:
                stock_name = twstock.codes[stock_id].name
        except (KeyError, AttributeError):
            stock_name = "未知股票"

        return {
            "id": stock.sid,
            "name": stock_name,
            "date": latest.date,
            "open": latest.open,
            "high": latest.high,
            "low": latest.low,
            "close": latest.close,
            "capacity": latest.capacity,
        }
    except Exception as e:
        print(f"⚠️ 查詢 {stock_id} 發生錯誤：{e}")
        return None


def query_quote_worker(stock_queue, result_queue):
    """工作執行緒：查詢股價"""
    while True:
        try:
            stock_id = stock_queue.get(timeout=1)
            if stock_id is None:  # 結束信號
                break

            result = query_quote(stock_id)
            if result:
                result_queue.put(("success", stock_id, result))
            else:
                result_queue.put(("error", stock_id, "查詢失敗"))

            stock_queue.task_done()

        except:  # Queue timeout
            break


def query_quotes_concurrent(stock_ids, max_workers=3):
    """併發查詢股價"""
    if not stock_ids:
        return []

    stock_queue = Queue()
    result_queue = Queue()

    # 將股票代號放入佇列
    for stock_id in stock_ids:
        stock_queue.put(stock_id)

    # 建立工作執行緒
    workers = []
    worker_count = min(max_workers, len(stock_ids))
    for i in range(worker_count):
        worker = threading.Thread(
            target=query_quote_worker, args=(stock_queue, result_queue)
        )
        worker.daemon = True
        worker.start()
        workers.append(worker)

    # 收集結果
    quotes = []
    completed_count = 0
    start_time = time.time()

    print(f"📊 開始併發查詢 {len(stock_ids)} 檔股票（{worker_count} 個執行緒）...")

    while completed_count < len(stock_ids):
        try:
            status, stock_id, data = result_queue.get(timeout=20)
            completed_count += 1

            if status == "success":
                quotes.append(data)
                print(
                    f"✅ [{completed_count}/{len(stock_ids)}] {stock_id} - {data['name']} ${data['close']:.2f}"
                )
            else:
                print(f"❌ [{completed_count}/{len(stock_ids)}] {stock_id} - {data}")

        except:  # Timeout
            print(f"⏰ 查詢超時，已完成 {completed_count}/{len(stock_ids)}")
            break

    # 發送結束信號
    for _ in workers:
        stock_queue.put(None)

    # 等待執行緒結束
    for worker in workers:
        worker.join(timeout=2)

    elapsed = time.time() - start_time
    print(f"⚡ 併發查詢完成，成功 {len(quotes)} 檔，耗時 {elapsed:.1f} 秒")

    return quotes


def query_quotes_sequential(stock_ids):
    """順序查詢股價（原本的方式，作為備案）"""
    quotes = []
    total = len(stock_ids)

    print(f"📊 開始順序查詢 {total} 檔股票...")

    for idx, stock_id in enumerate(stock_ids, start=1):
        q = query_quote(stock_id)

        if q:
            quotes.append(q)
            print(f"✅ [{idx}/{total}] {stock_id} - {q['name']} ${q['close']:.2f}")
        else:
            print(f"❌ [{idx}/{total}] {stock_id} - 查詢失敗")

    return quotes


def format_quote_table(quotes):
    lines = []
    lines.append("股票報價查詢")
    lines.append("")
    lines.append(
        "股票代號｜名稱　　　　｜日期　　　｜開盤　｜最高　｜最低　｜收盤　｜成交張數"
    )
    lines.append("---------------------------------------------------------------")

    # 按股票代號排序
    quotes.sort(key=lambda x: x["id"])

    for q in quotes:
        name_fixed = q["name"].ljust(8, "　")
        line = "{:<8}｜{}｜{}｜{:>6.2f}｜{:>6.2f}｜{:>6.2f}｜{:>6.2f}｜{:>10}".format(
            q["id"],
            name_fixed,
            q["date"].strftime("%Y-%m-%d"),
            q["open"],
            q["high"],
            q["low"],
            q["close"],
            int(q["capacity"] / 1000),
        )
        lines.append(line)

    lines.append("")
    lines.append("查詢時間：" + datetime.now().strftime("%Y-%m-%d %H:%M"))
    return "\n".join(lines)


# === 主程式 ===
def main():
    ensure_dirs()
    archive_old_quotes()

    try:
        symbols_file = get_latest_symbols_file()
        symbols = read_symbols(symbols_file)
        print(f"✔️ 使用持股清單：{symbols_file}")
        print(f"📊 準備查詢 {len(symbols)} 檔股票")

        # 嘗試併發查詢，失敗則使用順序查詢
        try:
            quotes = query_quotes_concurrent(symbols, max_workers=3)
        except Exception as e:
            print(f"⚠️ 併發查詢失敗（{e}），改用順序查詢...")
            quotes = query_quotes_sequential(symbols)

        if quotes:
            # 生成並顯示報告
            text = format_quote_table(quotes)
            print(f"\n{text}")

            # 儲存檔案
            now = datetime.now().strftime("%Y%m%d_%H%M")
            outfile = os.path.join(BASE_DIR, f"quote_{now}.txt")
            with open(outfile, "w", encoding="utf-8") as f:
                f.write(text)

            print(f"\n✅ 報價已寫入：{outfile}")
        else:
            print("❌ 未取得任何股價資料")

    except Exception as e:
        print(f"❌ 程式執行失敗：{e}")


if __name__ == "__main__":
    main()
