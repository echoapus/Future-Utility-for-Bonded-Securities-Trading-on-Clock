import csv
import threading
import time
import os
from datetime import datetime
from fubon_neo.constant import BSAction, MarketType, OrderType, PriceType, TimeInForce
from fubon_neo.sdk import Order
from order_status_map import STATUS_MAP
from login_helper import login

# 全域變數
sdk = None
account = None
login_done = threading.Event()


def async_login():
    """背景非同步登入"""
    global sdk, account
    try:
        sdk, account = login()
        login_done.set()
    except Exception as e:
        print("❌ 背景登入失敗：", e)
        login_done.set()


def validate_csv_row(row_num, row):
    """驗證CSV資料行"""
    errors = []

    # 檢查欄位數量
    if len(row) != 3:
        errors.append(f"第{row_num}行：欄位數量錯誤，應該有3個欄位")
        return errors, None

    code, quantity_str, price_str = row

    # 驗證股票代號
    if not code or not code.isdigit() or len(code) < 4 or len(code) > 6:
        errors.append(f"第{row_num}行：股票代號格式錯誤 '{code}'")

    # 驗證股數
    try:
        quantity = int(quantity_str)
        if quantity < 1 or quantity > 999:
            errors.append(f"第{row_num}行：股數超出範圍 {quantity}（允許範圍：1-999）")
    except ValueError:
        errors.append(f"第{row_num}行：股數格式錯誤 '{quantity_str}'")
        quantity = 0

    # 驗證股價
    try:
        price = float(price_str)
        if price <= 0:
            errors.append(f"第{row_num}行：股價必須大於0 '{price_str}'")
    except ValueError:
        errors.append(f"第{row_num}行：股價格式錯誤 '{price_str}'")
        price = 0

    if errors:
        return errors, None

    return [], {
        "code": code,
        "quantity": quantity,
        "price": price_str,  # 保持字串格式供API使用
        "price_float": price,  # 數字格式供顯示使用
    }


def read_csv_orders(filename):
    """讀取CSV檔案並驗證"""
    if not os.path.exists(filename):
        print(f"❌ 找不到檔案：{filename}")
        return None

    orders = []
    all_errors = []

    try:
        with open(filename, "r", encoding="utf-8") as file:
            csv_reader = csv.reader(file)

            # 跳過標題行
            try:
                header = next(csv_reader)
                print(f"📄 CSV標題：{', '.join(header)}")
            except StopIteration:
                print("❌ CSV檔案是空的")
                return None

            # 讀取資料行
            for row_num, row in enumerate(csv_reader, start=2):
                if not any(row):  # 跳過空行
                    continue

                errors, order_data = validate_csv_row(row_num, row)

                if errors:
                    all_errors.extend(errors)
                else:
                    orders.append(order_data)

    except Exception as e:
        print(f"❌ 讀取CSV檔案時發生錯誤：{e}")
        return None

    # 顯示驗證結果
    if all_errors:
        print("⚠️ CSV檔案驗證發現以下錯誤：")
        for error in all_errors:
            print(f"   {error}")

        if orders:
            print(f"\n✅ 有效的下單資料：{len(orders)} 筆")
            choice = input("是否繼續處理有效的資料？(y/N)：").strip().lower()
            if choice != "y":
                return None
        else:
            print("❌ 沒有有效的下單資料")
            return None

    return orders


def display_orders_preview(orders):
    """顯示下單預覽"""
    print(f"\n📋 即將下單清單（共 {len(orders)} 筆）：")
    print("-" * 50)
    print(f"{'序號':<4} {'股票代號':<8} {'股數':<6} {'股價':<10} {'金額':<10}")
    print("-" * 50)

    total_amount = 0
    for i, order in enumerate(orders, 1):
        amount = order["quantity"] * order["price_float"]
        total_amount += amount
        print(
            f"{i:<4} {order['code']:<8} {order['quantity']:<6} {order['price']:<10} {amount:>8,.0f}"
        )

    print("-" * 50)
    print(f"預估總金額：{total_amount:,.0f} 元")
    print("-" * 50)


def place_single_order(order_data, index, total):
    """執行單筆下單"""
    try:
        # 建立委託單
        order = Order(
            buy_sell=BSAction.Buy,  # 目前固定為買進，可以後續擴展
            symbol=order_data["code"],
            price=order_data["price"],
            quantity=order_data["quantity"],
            market_type=MarketType.IntradayOdd,
            price_type=PriceType.Limit,
            time_in_force=TimeInForce.ROD,
            order_type=OrderType.Stock,
            user_def="CSV_BATCH",
        )

        print(
            f"⏳ [{index}/{total}] 處理中：{order_data['code']} {order_data['quantity']}股..."
        )

        # 發送下單請求
        result = sdk.stock.place_order(account, order, unblock=False)

        if result.is_success and result.data:
            status_label = STATUS_MAP.get(
                result.data.status, f"狀態碼：{result.data.status}"
            )
            print(
                f"✅ [{index}/{total}] 成功：{order_data['code']} - 委託書號：{result.data.order_no or '未回傳'} - {status_label}"
            )
            return True, result.data
        elif result.is_success:
            print(f"⚠️ [{index}/{total}] 送出成功但無詳細資料：{order_data['code']}")
            return True, None
        else:
            print(f"❌ [{index}/{total}] 失敗：{order_data['code']} - {result.message}")
            return False, result.message

    except Exception as e:
        print(f"❌ [{index}/{total}] 異常：{order_data['code']} - {str(e)}")
        return False, str(e)


def batch_place_orders(orders):
    """批次執行下單"""
    if not orders:
        print("❌ 沒有訂單可以執行")
        return

    print(f"\n🚀 開始批次下單（共 {len(orders)} 筆）...")
    print("=" * 60)

    success_orders = []
    failed_orders = []

    for i, order_data in enumerate(orders, 1):
        success, result = place_single_order(order_data, i, len(orders))

        if success:
            success_orders.append({"order_data": order_data, "result": result})
        else:
            failed_orders.append({"order_data": order_data, "error": result})

        # 避免下單過於頻繁，稍作延遲
        if i < len(orders):
            time.sleep(0.5)

    # 顯示執行結果摘要
    print("\n" + "=" * 60)
    print(f"📊 批次下單完成")
    print(f"✅ 成功：{len(success_orders)} 筆")
    print(f"❌ 失敗：{len(failed_orders)} 筆")

    if failed_orders:
        print("\n❌ 失敗清單：")
        for item in failed_orders:
            order = item["order_data"]
            print(f"   {order['code']} {order['quantity']}股 - {item['error']}")

    # 生成執行報告
    generate_report(success_orders, failed_orders)


def generate_report(success_orders, failed_orders):
    """生成執行報告"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"batch_order_report_{timestamp}.txt"

    try:
        with open(report_filename, "w", encoding="utf-8") as f:
            f.write(f"批次下單執行報告\n")
            f.write(f"執行時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"帳號：{account.account if account else '未知'}\n")
            f.write("=" * 50 + "\n\n")

            f.write(f"執行摘要：\n")
            f.write(f"成功：{len(success_orders)} 筆\n")
            f.write(f"失敗：{len(failed_orders)} 筆\n")
            f.write(f"總計：{len(success_orders) + len(failed_orders)} 筆\n\n")

            if success_orders:
                f.write("成功訂單明細：\n")
                f.write("-" * 30 + "\n")
                for item in success_orders:
                    order = item["order_data"]
                    result = item["result"]
                    order_no = result.order_no if result else "未回傳"
                    status = (
                        STATUS_MAP.get(result.status, f"狀態碼：{result.status}")
                        if result
                        else "未知"
                    )
                    f.write(
                        f"股票：{order['code']}, 股數：{order['quantity']}, 價格：{order['price']}, 委託書號：{order_no}, 狀態：{status}\n"
                    )
                f.write("\n")

            if failed_orders:
                f.write("失敗訂單明細：\n")
                f.write("-" * 30 + "\n")
                for item in failed_orders:
                    order = item["order_data"]
                    f.write(
                        f"股票：{order['code']}, 股數：{order['quantity']}, 價格：{order['price']}, 錯誤：{item['error']}\n"
                    )

        print(f"\n📄 執行報告已儲存：{report_filename}")

    except Exception as e:
        print(f"⚠️ 無法儲存執行報告：{e}")


def main():
    """主程式"""
    print("🔄 CSV批次下單程式")
    print("=" * 30)

    # 啟動背景登入
    threading.Thread(target=async_login, daemon=True).start()

    # 讀取CSV檔案
    csv_filename = input("請輸入CSV檔案名稱（預設：orders.csv）：").strip()
    if not csv_filename:
        csv_filename = "orders.csv"

    orders = read_csv_orders(csv_filename)
    if not orders:
        print("❌ 無法讀取有效的下單資料")
        return

    # 顯示下單預覽
    display_orders_preview(orders)

    # 等待登入完成
    print("\n⏳ 等待登入完成...")
    login_done.wait()

    if sdk is None or account is None:
        print("❌ 登入失敗，無法執行批次下單")
        return

    print(f"✅ 登入成功，帳號：{account.account}")

    # 最終確認
    print(f"\n⚠️ 即將對帳號 {account.account} 執行 {len(orders)} 筆買進下單")
    input("按 Enter 鍵確認執行，或按 Ctrl+C 取消...")
    print("🚀 開始執行批次下單...")

    # 執行批次下單
    batch_place_orders(orders)

    # 登出
    if sdk.logout():
        print("\n✅ 已登出")
    else:
        print("\n⚠️ 登出失敗")


if __name__ == "__main__":
    main()
