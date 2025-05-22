import os
import glob
import shutil
from datetime import datetime
import twstock

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
        reverse=True
    )
    if not symbol_files:
        raise FileNotFoundError("❌ 找不到 symbols_*.txt")
    return symbol_files[0]


def read_symbols(path):
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def query_quote(stock_id):
    try:
        stock = twstock.Stock(stock_id)
        latest = stock.data[-1] if stock.data else None
        if not latest:
            return None
        return {
            "id": stock.sid,
            "name": twstock.codes.get(
                stock.sid).name if stock.sid in twstock.codes else "未知",
            "date": latest.date,
            "open": latest.open,
            "high": latest.high,
            "low": latest.low,
            "close": latest.close,
            "capacity": latest.capacity}
    except Exception as e:
        print(f"⚠️ 查詢 {stock_id} 發生錯誤：{e}")
        return None


def format_quote_table(quotes):
    lines = []
    lines.append("股票報價查詢")
    lines.append("")
    lines.append("股票代號｜名稱　　　　｜日期　　　｜開盤　｜最高　｜最低　｜收盤　｜成交張數")
    lines.append(
        "---------------------------------------------------------------")

    for q in quotes:
        name_fixed = q["name"].ljust(8, "　")  # 全形空格對齊中文
        line = "{:<8}｜{}｜{}｜{:>6.2f}｜{:>6.2f}｜{:>6.2f}｜{:>6.2f}｜{:>10}".format(
            q["id"],
            name_fixed,
            q["date"].strftime("%Y-%m-%d"),
            q["open"],
            q["high"],
            q["low"],
            q["close"],
            int(q["capacity"] / 1000)
        )
        lines.append(line)

    lines.append("")
    lines.append("查詢時間：" + datetime.now().strftime("%Y-%m-%d %H:%M"))
    return "\n".join(lines)

# === 主程式 ===


ensure_dirs()
archive_old_quotes()

symbols_file = get_latest_symbols_file()
symbols = read_symbols(symbols_file)
print(f"✔️ 使用持股清單：{symbols_file}\n")

quotes = []
total = len(symbols)

for idx, sid in enumerate(symbols, start=1):
    q = query_quote(sid)

    if q:
        quotes.append(q)
        print("[{}/{}] {:<6} {:<8} {}  開:{:>6.2f} 高:{:>6.2f} 低:{:>6.2f} 收:{:>6.2f} 張:{:>6}".format(
            idx, total,
            q["id"],
            q["name"],
            q["date"].strftime("%Y-%m-%d"),
            q["open"],
            q["high"],
            q["low"],
            q["close"],
            int(q["capacity"] / 1000)
        ))
    else:
        print(f"[{idx}/{total}] 查詢 {sid}... ❌ 失敗")


# 整理成完整表格並寫入檔案
text = format_quote_table(quotes)
print("\n" + text)

now = datetime.now().strftime("%Y%m%d_%H%M")
outfile = os.path.join(BASE_DIR, f"quote_{now}.txt")
with open(outfile, "w", encoding="utf-8") as f:
    f.write(text)

print(f"\n✅ 報價已寫入：{outfile}")
