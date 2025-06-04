from fubon_neo.constant import BSAction, MarketType, OrderType, PriceType, TimeInForce
from fubon_neo.sdk import Order
from order_status_map import STATUS_MAP
from login_helper import login


def print_order_result(order):
    status_label = STATUS_MAP.get(order.status, f"未知狀態碼：{order.status}")
    print("\n✅ 委託結果")
    print(f"股票代號      ：{order.stock_no}")
    print(f"委託別        ：{'買進' if order.buy_sell == 'Buy' else '賣出'}")
    print(f"委託價格      ：{order.price}")
    print(f"委託股數      ：{order.quantity}（張數：約 {order.quantity // 1000} 張）")
    print(f"盤別種類      ：{order.market_type}")
    print(f"價格型態      ：{order.price_type}")
    print(f"有效條件      ：{order.time_in_force}")
    print(f"委託書號      ：{order.order_no or '尚未回傳'}")
    print(f"狀態代碼      ：{order.status}（{status_label}）")
    print(f"下單時間      ：{order.last_time}")


def main():
    sdk, account = login()
    print(f"\n登入成功，帳號：{account.account}")

    # ==== 使用者輸入 ====
    action_input = input("請輸入動作（1=買進，2=賣出）：").strip()
    if action_input == "1":
        action = BSAction.Buy
    elif action_input == "2":
        action = BSAction.Sell
    else:
        print("❌ 無效的輸入，請輸入 1 或 2")
        return

    symbol = input("請輸入股票代號（如 2881）：").strip()

    lots_input = input("請輸入幾張（1 張 = 1000 股）：").strip()
    if not lots_input.isdigit():
        print("❌ 請輸入有效的整數張數（不接受小數或非數字）")
        return
    lots = int(lots_input)
    quantity = lots * 1000

    price = input("請輸入限價價格（如 66.0）：").strip()
    try:
        float(price)  # 僅檢查格式，保留為字串
    except ValueError:
        print("❌ 請輸入有效的價格（數字）")
        return

    # ==== 建立整股委託單 ====
    order = Order(
        buy_sell=action,
        symbol=symbol,
        price=price,
        quantity=quantity,
        market_type=MarketType.Common,
        price_type=PriceType.Limit,
        time_in_force=TimeInForce.ROD,
        order_type=OrderType.Stock,
        user_def="FullLot",
    )

    result = sdk.stock.place_order(account, order, unblock=False)

    if result.is_success and result.data:
        print_order_result(result.data)
    elif result.is_success:
        print("\n🟡 指令送出成功但尚未回傳委託資料，請稍後查詢委託狀態")
    else:
        print("\n🔴 下單失敗：", result.message)

    if sdk.logout():
        print("✅ 已登出")
    else:
        print("⚠️ 登出失敗")


if __name__ == "__main__":
    main()
