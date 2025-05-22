from login_helper import login
from order_status_map import STATUS_MAP

# 登入
sdk, account = login()
print(f"✅ 登入成功，帳號：{account.account}")

# 輸入股票代號
stock_id = input("請輸入要取消的股票代號（如 2897）：").strip()

# 查詢委託單
result = sdk.stock.get_order_results(account)

if result.is_success and result.data:
    to_cancel = [o for o in result.data if o.stock_no ==
                 stock_id and o.filled_qty < o.quantity and o.status not in [30, 40, 50]]

    if to_cancel:
        print(f"\n🔍 找到 {len(to_cancel)} 筆待取消的 {stock_id} 委託單：")
        for order in to_cancel:
            status_text = STATUS_MAP.get(order.status, f"未知狀態碼 {order.status}")
            print(
                f"▶️ 委託書號 {order.order_no}｜數量 {order.quantity}｜成交 {order.filled_qty}｜價格 {order.price}｜時間 {order.last_time}｜狀態 {status_text}")

            cancel_result = sdk.stock.cancel_order(account, order)
            if cancel_result.is_success:
                print(f"✅ 取消成功：{order.order_no}")
            else:
                print(f"❌ 取消失敗：{order.order_no}｜{cancel_result.message}")
    else:
        print(f"\n📭 沒有可取消的 {stock_id} 委託單")
else:
    print("❌ 查詢失敗：", result.message)

# 登出
if sdk.logout():
    print("\n👋 登出成功")
else:
    print("\n⚠️ 登出失敗")
