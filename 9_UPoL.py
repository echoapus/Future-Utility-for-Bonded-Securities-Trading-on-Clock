from login_helper import login
sdk, account = login()

result = sdk.accounting.unrealized_gains_and_loses(account)

if result.is_success and result.data:
    print("📘 平均買入價格（未實現損益資料）：\n")
    for item in result.data:
        print(
            f"📌 股票: {item.stock_no}｜"
            f"庫存數: {item.tradable_qty}｜"
            f"平均買入價: {item.cost_price}｜"
            f"未實現損益: +{item.unrealized_profit} / -{item.unrealized_loss}"
        )
else:
    print("❌ 查詢失敗：", result.message)

sdk.logout()
