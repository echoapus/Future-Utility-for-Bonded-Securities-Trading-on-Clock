import json
import threading
import time
from fubon_neo.constant import BSAction, MarketType, OrderType, PriceType, TimeInForce
from fubon_neo.sdk import Order
from order_status_map import STATUS_MAP
from login_helper import login

# 全域變數
sdk = None
account = None
login_done = threading.Event()

# 背景登入流程


def async_login():
    global sdk, account
    try:
        sdk, account = login()
        login_done.set()
    except Exception as e:
        print("❌ 背景登入失敗：", e)
        login_done.set()

# 美化委託單資訊輸出


def print_order_result(order):
    status_label = STATUS_MAP.get(order.status, f"未知狀態碼：{order.status}")
    print("委託資訊如下：")
    print(f"  股票代號      ：{order.stock_no}")
    print(f"  委託別        ：{'買進' if order.buy_sell == BSAction.Buy else '賣出'}")
    print(f"  委託股數      ：{order.quantity}")
    print(f"  委託價格      ：{order.price}")
    print(f"  市場別        ：{order.market}")
    print(f"  盤別種類      ：{order.market_type}")
    print(f"  有效條件      ：{order.time_in_force}")
    print(f"  委託書號      ：{order.order_no or '（尚未回傳）'}")
    print(f"  狀態代碼      ：{order.status}（{status_label}）")
    print(f"  下單時間      ：{order.last_time}")
    print(f"  Debug 買賣別  ：{order.buy_sell}")

# 主程式


def main():
    # 啟動背景登入
    threading.Thread(target=async_login, daemon=True).start()

    # 開始互動流程（同時等待登入）
    action_input = input("請輸入動作（1=買進，2=賣出）：").strip()
    if action_input == "1":
        action = BSAction.Buy
    elif action_input == "2":
        action = BSAction.Sell
    else:
        print("無效的輸入，請輸入 1 或 2")
        return

    symbol = input("請輸入股票代號（如 2897）：").strip()
    quantity = int(input("請輸入股數（如 100）：").strip())
    price = input("請輸入價格（如 2.00）：").strip()

    # 等待登入完成
    print("\n⏳ 等待登入完成...")
    login_done.wait()

    if sdk is None or account is None:
        print("❌ 登入失敗，無法下單")
        return

    print(f"✅ 登入成功，帳號：{account.account}")

    # 建立委託單
    order = Order(
        buy_sell=action,
        symbol=symbol,
        price=price,
        quantity=quantity,
        market_type=MarketType.IntradayOdd,
        price_type=PriceType.Limit,
        time_in_force=TimeInForce.ROD,
        order_type=OrderType.Stock,
        user_def="CLI",
    )

    # 發送下單請求（同步模式）
    result = sdk.stock.place_order(account, order, unblock=False)

    if result.is_success and result.data:
        print("\n✅ 下單成功")
        print_order_result(result.data)
    elif result.is_success:
        print("\n⚠️ 送出成功但無有效資料，請稍候查詢狀態")
    else:
        print("\n❌ 下單失敗：", result.message)

    # 登出
    if sdk.logout():
        print("\n✅ 已登出")
    else:
        print("\n⚠️ 登出失敗")


# 執行主程式
if __name__ == "__main__":
    main()
