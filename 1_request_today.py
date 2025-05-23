import os
from datetime import datetime
from login_helper import login
from order_status_map import STATUS_MAP

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

def format_full_report(data):
    """格式化完整委託報表"""
    lines = []
    lines.append("📋 今日委託單完整報表")
    lines.append("=" * 70)
    lines.append("股票代號｜數量｜成交｜狀態｜說明")
    lines.append("-" * 70)
    
    for order in data:
        status_text = STATUS_MAP.get(order.status, f"未知狀態碼 {order.status}")
        remark = get_remark(order)
        quantity_display = order.quantity if order.quantity is not None else "-"
        filled_qty_display = order.filled_qty if order.filled_qty is not None else "-"
        
        line = f"{order.stock_no:<8}｜{quantity_display:>4}｜{filled_qty_display:>4}｜{status_text:<8}｜{remark}"
        lines.append(line)
    
    lines.append("-" * 70)
    lines.append("")
    lines.append("查詢時間：" + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    return "\n".join(lines)

def format_filled_report(filled_orders):
    """格式化成交明細報表"""
    if not filled_orders:
        return "📭 今日尚無成交紀錄"
    
    lines = []
    lines.append("💰 今日成交明細")
    lines.append("=" * 80)
    
    total_buy_amount = 0
    total_sell_amount = 0
    
    for order in filled_orders:
        buy_sell_text = "買進" if order.buy_sell == "Buy" else "賣出"
        icon = "🟢" if order.buy_sell == "Buy" else "🔴"
        
        lines.append(f"{icon} {order.stock_no} | {buy_sell_text} | "
                    f"成交：{order.filled_qty:,} 股 | "
                    f"價格：{order.after_price} | "
                    f"金額：{order.filled_money:,.0f} 元 | "
                    f"時間：{order.last_time}")
        
        # 計算總金額
        if order.buy_sell == "Buy":
            total_buy_amount += order.filled_money or 0
        else:
            total_sell_amount += order.filled_money or 0
    
    lines.append("-" * 80)
    lines.append(f"📊 成交統計：")
    lines.append(f"   買進總額：{total_buy_amount:,.0f} 元")
    lines.append(f"   賣出總額：{total_sell_amount:,.0f} 元")
    lines.append(f"   淨流入：{total_sell_amount - total_buy_amount:+,.0f} 元")
    lines.append("")
    lines.append("查詢時間：" + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    return "\n".join(lines)

def get_order_statistics(data):
    """產生委託統計"""
    total_orders = len(data)
    filled_orders = [o for o in data if o.filled_qty is not None and o.filled_qty > 0]
    unfilled_orders = [o for o in data if (o.filled_qty is None or o.filled_qty == 0) and o.status == 10]
    cancelled_orders = [o for o in data if o.status in [30, 40]]
    partial_filled = [o for o in data if o.filled_qty is not None and 0 < o.filled_qty < o.quantity]
    
    return {
        'total': total_orders,
        'filled': len(filled_orders),
        'unfilled': len(unfilled_orders),
        'cancelled': len(cancelled_orders),
        'partial': len(partial_filled),
        'filled_data': filled_orders
    }

def display_menu():
    """顯示選單"""
    print("\n" + "="*50)
    print("📊 今日委託單查詢工具")
    print("="*50)
    print("1️⃣  查看完整委託報表（包含所有狀態）")
    print("2️⃣  查看成交明細（只顯示已成交）")
    print("3️⃣  查看統計摘要")
    print("4️⃣  輸出完整報告到檔案")
    print("0️⃣  離開")
    print("-"*50)

def main():
    """主程式"""
    print("🔍 正在登入並查詢委託資料...")
    
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
        
        # 取得統計資料
        stats = get_order_statistics(result.data)
        
        # 主選單循環
        while True:
            display_menu()
            
            # 顯示基本統計
            print(f"📈 今日委託概況：總計 {stats['total']} 筆 | "
                  f"成交 {stats['filled']} 筆 | "
                  f"未成交 {stats['unfilled']} 筆 | "
                  f"已取消 {stats['cancelled']} 筆")
            
            choice = input("\n請選擇功能 (0-4)：").strip()
            
            if choice == "1":
                # 完整委託報表
                print("\n" + format_full_report(result.data))
                
            elif choice == "2":
                # 成交明細
                print("\n" + format_filled_report(stats['filled_data']))
                
            elif choice == "3":
                # 統計摘要
                print(f"\n📊 詳細統計：")
                print(f"   總委託單數：{stats['total']} 筆")
                print(f"   完全成交：{stats['filled']} 筆")
                print(f"   部分成交：{stats['partial']} 筆")
                print(f"   尚未成交：{stats['unfilled']} 筆")
                print(f"   已取消：{stats['cancelled']} 筆")
                
                if stats['filled_data']:
                    total_amount = sum(o.filled_money or 0 for o in stats['filled_data'])
                    print(f"   成交總金額：{total_amount:,.0f} 元")
                
            elif choice == "4":
                # 輸出檔案
                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                
                # 完整報表
                full_report = format_full_report(result.data)
                full_path = os.path.join(EXPORT_DIR, f"order_full_{timestamp}.txt")
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(full_report)
                
                # 成交明細
                filled_report = format_filled_report(stats['filled_data'])
                filled_path = os.path.join(EXPORT_DIR, f"order_filled_{timestamp}.txt")
                with open(filled_path, "w", encoding="utf-8") as f:
                    f.write(filled_report)
                
                print(f"\n✅ 報告已儲存：")
                print(f"   📋 完整報表：{full_path}")
                print(f"   💰 成交明細：{filled_path}")
                
            elif choice == "0":
                break
                
            else:
                print("❌ 無效選擇，請重新輸入")
            
            input("\n按 Enter 繼續...")
    
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
