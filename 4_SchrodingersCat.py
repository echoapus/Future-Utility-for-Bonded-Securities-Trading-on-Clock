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


def format_inventory(data):
    lines = []
    lines.append("庫存查詢結果")
    lines.append("")
    lines.append("股票代號｜整股｜可賣｜買進金額｜賣出金額｜零股｜零股買｜零股賣")
    lines.append(
        "------------------------------------------------------------")

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
            odd.sell_value if odd else 0
        )
        lines.append(line)

    lines.append("")
    lines.append("查詢時間：" + datetime.now().strftime("%Y-%m-%d %H:%M"))
    return "\n".join(lines)


def extract_symbols(data):
    symbols = set()
    for item in data:
        odd_qty = item.odd.today_qty if hasattr(
            item, "odd") and item.odd else 0
        total_qty = item.today_qty + odd_qty
        if total_qty > 0:
            symbols.add(item.stock_no)
    return "\n".join(sorted(symbols))

# === 主流程 ===


sdk, account = login()
print(f"登入成功，帳號：{account.account}")

result = sdk.accounting.inventories(account)

if result.is_success and result.data:
    text = format_inventory(result.data)
    symbols = extract_symbols(result.data)

    print(text)  # 螢幕顯示

    # 輸出到檔案
    ensure_dirs()
    archive_old_files()

    now = datetime.now().strftime("%Y%m%d_%H%M")
    inv_path = os.path.join(EXPORT_DIR, f"inventory_{now}.txt")
    sym_path = os.path.join(EXPORT_DIR, f"symbols_{now}.txt")

    with open(inv_path, "w", encoding="utf-8") as f:
        f.write(text)

    with open(sym_path, "w", encoding="utf-8") as f:
        f.write(symbols)

    print(f"\n✅ 檔案已輸出至 {EXPORT_DIR}")

else:
    print("❌ 查詢失敗，訊息：", result.message)

sdk.logout()
