from login_helper import login
from twstock import Stock, codes

# 查詢股票名稱
def get_stock_name(stock_id):
    try:
        return codes[stock_id].name if stock_id in codes else "未知"
    except Exception:
        return "未知"

# 登入 API
sdk, account = login()

# 查詢未實現損益
result = sdk.accounting.unrealized_gains_and_loses(account)

# 顯示結果
if result.is_success and result.data:
    print("📘 平均買入價格（未實現損益資料）：\n")
    for item in result.data:
        stock_name = get_stock_name(item.stock_no)
        print(
            f"📌 股票: {item.stock_no}（{stock_name}）｜"
            f"庫存數: {item.tradable_qty}｜"
            f"平均買入價: {item.cost_price}｜"
            f"未實現損益: +{item.unrealized_profit} / -{item.unrealized_loss}"
        )
else:
    print("❌ 查詢失敗：", result.message)

# 登出
sdk.logout()
