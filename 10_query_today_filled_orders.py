from login_helper import login
from fubon_neo.sdk import FubonSDK

# 登入
sdk, account = login()
print(f"登入成功：帳號 {account.account}")

# 查詢今日成交明細
print("\n📈 查詢今日成交明細中...")
result = sdk.stock.get_order_results(account)

if result.is_success:
    # 修正: 檢查 filled_qty 是否為 None
    filled_orders = [o for o in result.data if o.filled_qty is not None and o.filled_qty > 0]
    if filled_orders:
        print("✅ 今日成交明細：")
        for o in filled_orders:
            print(f"- 股票代號: {o.stock_no}, "
                  f"買賣: {o.buy_sell}, "
                  f"成交股數: {o.filled_qty}, "
                  f"成交金額: {o.filled_money}, "
                  f"成交價格: {o.after_price}, "
                  f"時間: {o.last_time}")
    else:
        print("📭 今日尚無成交紀錄。")
else:
    print("❌ 查詢失敗：", result.message)

# 登出
sdk.logout()
