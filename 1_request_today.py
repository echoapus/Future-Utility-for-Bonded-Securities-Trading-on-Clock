import os
from datetime import datetime
from login_helper import login
from order_status_map import STATUS_MAP
from fubon_neo.constant import BSAction

# 設定輸出目錄
EXPORT_DIR = "/home/botuser/FAngel/CatCage/"
os.makedirs(EXPORT_DIR, exist_ok=True)

def get_remark(order):
    """產生委託單狀態說明"""
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
    """格式化委託報表"""
    lines = []
    lines.append("📋 今日委託單報表")
    lines.append("=" * 60)
    lines.append("股票代號｜數量｜成交｜狀態｜說明")
    lines.append("-" * 60)
    
    for order in data:
        status_text = STATUS_MAP.get(order.status, f"未知狀態碼 {order.status}")
        remark = get_remark(order)
        quantity_display = order.quantity if order.quantity is not None else "-"
        filled_qty_display = order.filled_qty if order.filled_qty is not None else "-"
        
        line = f"{order.stock_no:<8}｜{quantity_display:>4}｜{filled_qty_display:>4}｜{status_text:<8}｜{remark}"
        lines.append(line)
    
    lines.append("-" * 60)
    lines.append("")
    lines.append("查詢時間：" + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    return "\n".join(lines)

def show_filled_summary(data):
    """顯示成交摘要"""
    filled_orders = [o for o in data if o.filled_qty is not None and o.filled_qty > 0]
    
    if not filled_orders:
        print("\n📭 今日尚無成交紀錄")
        return
    
    print(f"\n💰 今日成交摘要（共 {len(filled_orders)} 筆）：")
    print("-" * 70)
    
    total_buy_amount = 0
    total_sell_amount = 0
    
    for order in filled_orders:
        # 正確判斷 BSAction
        if order.buy_sell == BSAction.Buy:
            buy_sell_text = "買進"
            icon = "🟢"
            total_buy_amount += order.filled_money or 0
        elif order.buy_sell == BSAction.Sell:
            buy_sell_text = "賣出"
            icon = "🔴"
            total_sell_amount += order.filled_money or 0
        else:
            buy_sell_text = f"未知({order.buy_sell})"
            icon = "⚪"
        
        print(f"{icon} {order.stock_no} | {buy_sell_text} | "
              f"成交：{order.filled_qty:,} 股 | "
              f"價格：{order.after_price} | "
              f"金額：{order.filled_money:,.0f} 元")
    
    print("-" * 70)
    print(f"📊 買進總額：{total_buy_amount:,.0f} 元")
    print(f"📊 賣出總額：{total_sell_amount:,.0f} 元")
    print(f"📊 淨流入：{total_sell_amount - total_buy_amount:+,.0f} 元")

def get_statistics(data):
    """取得統計資訊"""
    total = len(data)
    filled = len([o for o in data if o.filled_qty is not None and o.filled_qty > 0])
    unfilled = len([o for o in data if (o.filled_qty is None or o.filled_qty == 0) and o.status == 10])
    cancelled = len([o for o in data if o.status in [30, 40]])
    partial = len([o for o in data if o.filled_qty is not None and 0 < o.filled_qty < o.quantity])
    
    return total, filled, unfilled, cancelled, partial

def main():
    """主程式"""
    print("🔍 正在查詢今日委託單...")
    
    # 登入
    try:
        sdk, account = login()
        print(f"✅ 登入成功，帳號：{account.account}")
    except Exception as e:
        print(f"❌ 登入失敗：{e}")
        return
    
    try:
        # 查詢委託結果
        result = sdk.stock.get_order_results(account)
        
        if not (result.is_success and result.data):
            print("❌ 查詢失敗：", result.message if hasattr(result, 'message') else '無資料')
            return
        
        # 顯示統計摘要
        total, filled, unfilled, cancelled, partial = get_statistics(result.data)
        print(f"\n📊 委託統計：總計 {total} 筆 | 成交 {filled} 筆 | 未成交 {unfilled} 筆 | 取消 {cancelled} 筆")
        
        # 顯示完整委託報表
        text = format_orders(result.data)
        print(f"\n{text}")
        
        # 顯示成交摘要
        show_filled_summary(result.data)
        
        # 輸出到檔案
        now = datetime.now().strftime("%Y%m%d_%H%M")
        file_path = os.path.join(EXPORT_DIR, f"request_today_{now}.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"\n✅ 檔案已輸出至 {file_path}")
        
    except Exception as e:
        print(f"❌ 執行過程發生錯誤：{e}")
    
    finally:
        # 登出
        try:
            if sdk.logout():
                print("\n👋 已成功登出")
            else:
                print("\n⚠️ 登出失敗")
        except Exception as e:
            print(f"\n⚠️ 登出時發生錯誤：{e}")

if __name__ == "__main__":
    main()
