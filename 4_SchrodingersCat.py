import os
import shutil
from datetime import datetime
from login_helper import login

EXPORT_DIR = "/home/botuser/FAngel/CatCage"
OLD_DIR = os.path.join(EXPORT_DIR, "old")


def ensure_dirs():
    os.makedirs(OLD_DIR, exist_ok=True)


def archive_old_files():
    for filename in os.listdir(EXPORT_DIR):
        full_path = os.path.join(EXPORT_DIR, filename)
        if os.path.isfile(full_path):
            shutil.move(full_path, os.path.join(OLD_DIR, filename))


def get_stock_cost_info(item):
    """分析股票的成本資訊"""
    # 整股成本（可能是累計損益，不是總成本）
    regular_buy = item.buy_value if item.buy_value and item.buy_value > 0 else 0
    regular_sell = item.sell_value if item.sell_value and item.sell_value > 0 else 0

    # 零股成本（比較可靠的成本資料）
    odd_buy = 0
    odd_sell = 0
    if hasattr(item, "odd") and item.odd:
        odd_buy = (
            item.odd.buy_value if item.odd.buy_value and item.odd.buy_value > 0 else 0
        )
        odd_sell = (
            item.odd.sell_value
            if item.odd.sell_value and item.odd.sell_value > 0
            else 0
        )

    # 估算平均成本
    total_cost = regular_buy + odd_buy
    total_qty = item.today_qty + (
        item.odd.today_qty if hasattr(item, "odd") and item.odd else 0
    )

    avg_cost = 0
    if total_cost > 0 and total_qty > 0:
        avg_cost = total_cost / total_qty

    return {
        "total_cost": total_cost,
        "avg_cost": avg_cost,
        "has_cost_data": total_cost > 0,
        "regular_buy": regular_buy,
        "odd_buy": odd_buy,
    }


def format_enhanced_inventory(data):
    """增強版庫存報告"""
    lines = []
    lines.append("📊 投資組合庫存分析")
    lines.append("=" * 90)
    lines.append("")
    lines.append("股票代號 | 整股 | 零股 | 總股數 | 成本資料 | 平均成本 | 備註")
    lines.append("-" * 90)

    total_known_cost = 0
    stocks_with_cost = 0

    for item in data:
        odd_qty = item.odd.today_qty if hasattr(item, "odd") and item.odd else 0
        total_qty = item.today_qty + odd_qty

        if total_qty <= 0:
            continue

        cost_info = get_stock_cost_info(item)

        # 成本狀態說明
        if cost_info["has_cost_data"]:
            cost_status = f"{cost_info['total_cost']:,.0f}"
            avg_cost_str = f"{cost_info['avg_cost']:.2f}"
            stocks_with_cost += 1
            total_known_cost += cost_info["total_cost"]

            # 判斷成本來源
            if cost_info["regular_buy"] > 0 and cost_info["odd_buy"] > 0:
                remark = "整股+零股成本"
            elif cost_info["odd_buy"] > 0:
                remark = "零股成本"
            elif cost_info["regular_buy"] > 0:
                remark = "整股成本"
            else:
                remark = "成本計算異常"
        else:
            cost_status = "無資料"
            avg_cost_str = "N/A"
            remark = "無成本記錄"

        line = f"{item.stock_no:<8} | {item.today_qty:>4} | {odd_qty:>4} | {total_qty:>6} | {cost_status:>8} | {avg_cost_str:>8} | {remark}"
        lines.append(line)

    lines.append("-" * 90)
    lines.append("")
    lines.append("📋 投資組合統計：")
    lines.append(
        f"   持股檔數：{len([i for i in data if (i.today_qty + (i.odd.today_qty if hasattr(i, 'odd') and i.odd else 0)) > 0])} 檔"
    )
    lines.append(f"   有成本資料：{stocks_with_cost} 檔")
    lines.append(f"   已知總成本：{total_known_cost:,.0f} 元")
    lines.append("")
    lines.append("查詢時間：" + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    lines.append("=" * 90)

    return "\n".join(lines)


def format_inventory(data):
    """原始格式的庫存報告（完全保留）"""
    lines = []
    lines.append("庫存查詢結果")
    lines.append("")
    lines.append("股票代號｜整股｜可賣｜買進金額｜賣出金額｜零股｜零股買｜零股賣")
    lines.append("------------------------------------------------------------")

    for item in data:
        odd = item.odd if hasattr(item, "odd") and item.odd else None
        line = "{:<8}｜{:>4}｜{:>4}｜{:>10}｜{:>10}｜{:>4}｜{:>8}｜{:>8}".format(
            item.stock_no,
            item.today_qty,
            item.tradable_qty,
            item.buy_value,
            item.sell_value,
            odd.today_qty if odd else 0,
            odd.buy_value if odd else 0,
            odd.sell_value if odd else 0,
        )
        lines.append(line)

    lines.append("")
    lines.append("查詢時間：" + datetime.now().strftime("%Y-%m-%d %H:%M"))
    return "\n".join(lines)


def extract_symbols(data):
    """提取有持股的股票代號"""
    symbols = set()
    for item in data:
        odd_qty = item.odd.today_qty if hasattr(item, "odd") and item.odd else 0
        total_qty = item.today_qty + odd_qty
        if total_qty > 0:
            symbols.add(item.stock_no)
    return "\n".join(sorted(symbols))


def show_cost_analysis(data):
    """顯示成本分析"""
    print("💰 成本資料分析：")

    stocks_with_cost = []
    stocks_without_cost = []

    for item in data:
        odd_qty = item.odd.today_qty if hasattr(item, "odd") and item.odd else 0
        total_qty = item.today_qty + odd_qty

        if total_qty <= 0:
            continue

        cost_info = get_stock_cost_info(item)

        if cost_info["has_cost_data"]:
            stocks_with_cost.append(
                {
                    "stock_no": item.stock_no,
                    "qty": total_qty,
                    "cost": cost_info["total_cost"],
                    "avg_cost": cost_info["avg_cost"],
                }
            )
        else:
            stocks_without_cost.append({"stock_no": item.stock_no, "qty": total_qty})

    print(f"   📊 有成本資料：{len(stocks_with_cost)} 檔")
    if stocks_with_cost:
        total_cost = sum(s["cost"] for s in stocks_with_cost)
        print(f"      總投入成本：{total_cost:,.0f} 元")
        for stock in sorted(stocks_with_cost, key=lambda x: x["cost"], reverse=True)[
            :5
        ]:
            print(
                f"      {stock['stock_no']}: {stock['qty']} 股, 成本 {stock['cost']:,.0f} 元 (平均 {stock['avg_cost']:.2f} 元/股)"
            )

    print(f"   ❓ 無成本資料：{len(stocks_without_cost)} 檔")
    if stocks_without_cost:
        for stock in stocks_without_cost:
            print(
                f"      {stock['stock_no']}: {stock['qty']} 股 (可能為轉入或早期持股)"
            )


def show_summary_stats(data):
    """顯示統計摘要"""
    total_stocks = 0
    total_regular_shares = 0
    total_odd_shares = 0

    for item in data:
        odd_qty = item.odd.today_qty if hasattr(item, "odd") and item.odd else 0
        total_qty = item.today_qty + odd_qty

        if total_qty > 0:
            total_stocks += 1
            total_regular_shares += item.today_qty
            total_odd_shares += odd_qty

    print(f"📊 持股統計：")
    print(f"   持有股票：{total_stocks} 檔")
    print(
        f"   整股合計：{total_regular_shares:,} 股 ({total_regular_shares/1000:.1f} 張)"
    )
    print(f"   零股合計：{total_odd_shares:,} 股")
    print(f"   總持股：{total_regular_shares + total_odd_shares:,} 股")


# === 主流程 ===
sdk, account = login()
print(f"🔍 薛丁格的貓正在觀察庫存...")
print(f"✅ 登入成功，帳號：{account.account}")

result = sdk.accounting.inventories(account)

if result.is_success and result.data:
    # 顯示統計摘要
    show_summary_stats(result.data)

    # 顯示成本分析
    print()
    show_cost_analysis(result.data)

    # 顯示增強版報告
    enhanced_text = format_enhanced_inventory(result.data)
    print(f"\n{enhanced_text}")

    # 原始格式報告
    original_text = format_inventory(result.data)
    print(f"\n{original_text}")

    # 提取符號
    symbols = extract_symbols(result.data)

    # 輸出到檔案
    ensure_dirs()
    archive_old_files()

    now = datetime.now().strftime("%Y%m%d_%H%M")

    # 輸出增強版報告
    enhanced_path = os.path.join(EXPORT_DIR, f"inventory_enhanced_{now}.txt")
    with open(enhanced_path, "w", encoding="utf-8") as f:
        f.write(enhanced_text)

    # 輸出原始格式（保持相容性）
    inv_path = os.path.join(EXPORT_DIR, f"inventory_{now}.txt")
    with open(inv_path, "w", encoding="utf-8") as f:
        f.write(original_text)

    # 輸出符號清單
    sym_path = os.path.join(EXPORT_DIR, f"symbols_{now}.txt")
    with open(sym_path, "w", encoding="utf-8") as f:
        f.write(symbols)

    print(f"\n✅ 檔案已輸出至 {EXPORT_DIR}：")
    print(f"   📊 增強版報告：inventory_enhanced_{now}.txt")
    print(f"   📋 原始格式：inventory_{now}.txt")
    print(f"   🎯 持股清單：symbols_{now}.txt")

else:
    print("❌ 查詢失敗，訊息：", result.message)

sdk.logout()
