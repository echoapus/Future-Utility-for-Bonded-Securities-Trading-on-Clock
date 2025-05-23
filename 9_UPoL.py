import os
from datetime import datetime
from login_helper import login
from twstock import Stock, codes

# 確保輸出目錄存在
EXPORT_DIR = "/home/botuser/FAngel/CatCage/"
os.makedirs(EXPORT_DIR, exist_ok=True)

def get_stock_name(stock_id):
    """查詢股票中文名稱"""
    try:
        return codes[stock_id].name if stock_id in codes else "未知股票"
    except Exception:
        return "查詢失敗"

def get_current_price(stock_id):
    """查詢當前股價"""
    try:
        stock = Stock(stock_id)
        if stock.data:
            return stock.data[-1].close
        return None
    except Exception:
        return None

def calculate_profit_rate(cost_price, current_price):
    """計算獲利率"""
    if cost_price and current_price:
        return ((current_price - cost_price) / cost_price) * 100
    return 0

def format_currency(amount):
    """格式化金額顯示"""
    if amount is None:
        return "N/A"
    return f"{amount:,.0f}"

def format_percentage(percentage):
    """格式化百分比顯示"""
    if percentage > 0:
        return f"📈 +{percentage:.2f}%"
    elif percentage < 0:
        return f"📉 {percentage:.2f}%"
    else:
        return f"➖ {percentage:.2f}%"

def generate_summary_report(data):
    """產生總結報告"""
    total_cost = sum(item.cost_price * item.tradable_qty for item in data if item.cost_price and item.tradable_qty)
    total_profit = sum(item.unrealized_profit or 0 for item in data)
    total_loss = sum(item.unrealized_loss or 0 for item in data)
    net_profit = total_profit - total_loss
    
    if total_cost > 0:
        total_profit_rate = (net_profit / total_cost) * 100
    else:
        total_profit_rate = 0
    
    return {
        'total_cost': total_cost,
        'total_profit': total_profit,
        'total_loss': total_loss,
        'net_profit': net_profit,
        'profit_rate': total_profit_rate,
        'stock_count': len(data)
    }

def create_detailed_report(data):
    """建立詳細報告文字"""
    lines = []
    lines.append("=" * 80)
    lines.append("📊 未實現損益詳細報告")
    lines.append("=" * 80)
    lines.append("")
    
    # 表頭
    lines.append("股票代號 | 股票名稱     | 庫存量 | 平均成本 | 現價   | 獲利率    | 未實現損益")
    lines.append("-" * 80)
    
    # 每檔股票詳細資訊
    total_unrealized = 0
    for item in data:
        stock_name = get_stock_name(item.stock_no)
        current_price = get_current_price(item.stock_no)
        
        # 計算獲利率
        profit_rate = calculate_profit_rate(item.cost_price, current_price)
        profit_rate_str = format_percentage(profit_rate)
        
        # 計算淨未實現損益
        net_unrealized = (item.unrealized_profit or 0) - (item.unrealized_loss or 0)
        total_unrealized += net_unrealized
        
        # 格式化顯示
        current_price_str = f"{current_price:.2f}" if current_price else "N/A"
        unrealized_str = f"{net_unrealized:+,.0f}" if net_unrealized != 0 else "0"
        
        line = f"{item.stock_no:<8} | {stock_name:<10} | {item.tradable_qty:>6} | {item.cost_price:>8.2f} | {current_price_str:>6} | {profit_rate_str:<9} | {unrealized_str:>10}"
        lines.append(line)
    
    lines.append("-" * 80)
    
    # 總結
    summary = generate_summary_report(data)
    lines.append("")
    lines.append("📋 投資組合總結：")
    lines.append(f"   持股檔數：{summary['stock_count']} 檔")
    lines.append(f"   總投入成本：{format_currency(summary['total_cost'])} 元")
    lines.append(f"   未實現獲利：{format_currency(summary['total_profit'])} 元")
    lines.append(f"   未實現損失：{format_currency(summary['total_loss'])} 元")
    lines.append(f"   淨未實現損益：{summary['net_profit']:+,.0f} 元")
    lines.append(f"   總獲利率：{format_percentage(summary['profit_rate'])}")
    lines.append("")
    lines.append(f"查詢時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 80)
    
    return "\n".join(lines)

def main():
    """主程式"""
    print("🔍 正在查詢未實現損益...")
    
    # 登入 API
    try:
        sdk, account = login()
        print(f"✅ 登入成功，帳號：{account.account}")
    except Exception as e:
        print(f"❌ 登入失敗：{e}")
        return
    
    try:
        # 查詢未實現損益
        result = sdk.accounting.unrealized_gains_and_loses(account)
        
        if result.is_success and result.data:
            # 螢幕顯示簡化版
            print("\n📘 持股損益一覽：")
            print("-" * 60)
            
            for item in result.data:
                stock_name = get_stock_name(item.stock_no)
                current_price = get_current_price(item.stock_no)
                profit_rate = calculate_profit_rate(item.cost_price, current_price)
                net_unrealized = (item.unrealized_profit or 0) - (item.unrealized_loss or 0)
                
                profit_icon = "🟢" if net_unrealized > 0 else "🔴" if net_unrealized < 0 else "⚪"
                
                print(f"{profit_icon} {item.stock_no} ({stock_name})")
                print(f"   庫存：{item.tradable_qty:,} 股 | 成本：{item.cost_price:.2f} | 損益：{net_unrealized:+,.0f} ({profit_rate:+.2f}%)")
                print()
            
            # 產生詳細報告並儲存
            detailed_report = create_detailed_report(result.data)
            
            # 儲存到檔案
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"unrealized_pnl_{timestamp}.txt"
            filepath = os.path.join(EXPORT_DIR, filename)
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(detailed_report)
            
            print(f"📄 詳細報告已儲存至：{filepath}")
            
            # 總結資訊
            summary = generate_summary_report(result.data)
            print(f"\n💰 投資組合總結：")
            print(f"   📊 持股檔數：{summary['stock_count']} 檔")
            print(f"   💵 總成本：{format_currency(summary['total_cost'])} 元")
            print(f"   📈 淨損益：{summary['net_profit']:+,.0f} 元 ({summary['profit_rate']:+.2f}%)")
            
        else:
            print("❌ 查詢失敗：", result.message if hasattr(result, 'message') else '未知錯誤')
    
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
