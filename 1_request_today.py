import os
from datetime import datetime
from login_helper import login
from order_status_map import STATUS_MAP
EXPORT_DIR = "/home/botuser/FAngel/CatCage/"
os.makedirs(EXPORT_DIR, exist_ok=True)

def get_remark(order):
    # Safely handle None values by ensuring filled_qty and quantity are defined
    filled_qty = order.filled_qty if order.filled_qty is not None else 0
    quantity = order.quantity if order.quantity is not None else 0
    
    if filled_qty == 0 and order.status == 10:
        return "🟡 尚未成交"
    elif 0 < filled_qty < quantity:
        return "🟠 部分成交"
    elif filled_qty == quantity or order.status == 50:
        return "🟢 完全成交"
    elif order.status in [30, 40]:
        return "🔴 已取消"
    else:
        return "⚪ 其他"

def format_orders(data):
    lines = []
    lines.append("查詢結果：")
    lines.append("股票代號｜數量｜成交｜狀態｜說明")
    lines.append("-----------------------------------")
    for order in data:
        status_text = STATUS_MAP.get(order.status, f"未知狀態碼 {order.status}")
        remark = get_remark(order)
        # Handle None values for display
        quantity_display = order.quantity if order.quantity is not None else "-"
        filled_qty_display = order.filled_qty if order.filled_qty is not None else "-"
        line = f"{order.stock_no:<8}｜{quantity_display:>4}｜{filled_qty_display:>4}｜{status_text:<8}｜{remark}"
        lines.append(line)
    lines.append("")
    lines.append("查詢時間：" + datetime.now().strftime("%Y-%m-%d %H:%M"))
    return "\n".join(lines)

# 主程式
sdk, account = login()
print(f"✅ 登入成功：帳號 {account.account}")
result = sdk.stock.get_order_results(account)
if result.is_success and result.data:
    text = format_orders(result.data)
    print(text)
    # 輸出到檔案
    now = datetime.now().strftime("%Y%m%d_%H%M")
    file_path = os.path.join(EXPORT_DIR, f"request_today_{now}.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"\n✅ 檔案已輸出至 {file_path}")
else:
    print("❌ 查詢失敗")
sdk.logout()
