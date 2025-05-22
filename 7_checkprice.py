import twstock
from datetime import datetime
import unicodedata

# 中文名稱對齊


def calc_display_width(text):
    width = 0
    for ch in text:
        width += 2 if unicodedata.east_asian_width(ch) in ('F', 'W') else 1
    return width


def pad_name(name, total_width=10):
    real_width = calc_display_width(name)
    return name + ' ' * (total_width - real_width)

# 查單一股票報價


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
    except Exception:
        return None

# 主互動邏輯


def main():
    stock_id = input("請輸入股票代號（例如 2330）：").strip()

    print(f"\n查詢 {stock_id} 中...\n")

    result = query_quote(stock_id)

    if result:
        name_fixed = pad_name(result["name"], 10)
        print("股票代號｜名稱　　　　｜日期　　　｜開盤　｜最高　｜最低　｜收盤　｜成交張數")
        print("---------------------------------------------------------------")
        print("{:<8}｜{}｜{}｜{:>6.2f}｜{:>6.2f}｜{:>6.2f}｜{:>6.2f}｜{:>10}".format(
            result["id"],
            name_fixed,
            result["date"].strftime("%Y-%m-%d"),
            result["open"],
            result["high"],
            result["low"],
            result["close"],
            int(result["capacity"] / 1000)
        ))
        print("\n查詢時間：", datetime.now().strftime("%Y-%m-%d %H:%M"))
    else:
        print("❌ 查無資料，請確認股票代號是否正確。")


if __name__ == "__main__":
    main()
