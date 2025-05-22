import pandas as pd
from datetime import datetime
import login_helper  # 使用你的現成登入模組

def generate_daily_trade_report_from_sdk(sdk, account, output_prefix='daily_report'):
    today_str = datetime.today().strftime('%Y%m%d')

    # ---------- 委託紀錄 ----------
    orders = sdk.stock.get_order_results(account).data
    order_data = [{
        '日期': o.date,
        '股票代號': o.stock_no,
        '買賣': o.buy_sell.name if hasattr(o.buy_sell, "name") else o.buy_sell,
        '委託價格': o.price,
        '數量': o.quantity,
        '成交股數': o.filled_qty,
        '成交金額': o.filled_money,
        '狀態': o.status,
        '委託單號': o.order_no,
        '最後異動': o.last_time,
        '備註': o.user_def
    } for o in orders]
    pd.DataFrame(order_data).to_csv(f"{output_prefix}_{today_str}_委託紀錄.csv", index=False)

    # ---------- 庫存資訊 ----------
    inventories = sdk.accounting.inventories(account).data
    inventory_data = [{
        '股票代號': i.stock_no,
        '昨日餘額': i.lastday_qty,
        '今日餘額': i.today_qty,
        '可用庫存': i.tradable_qty,
        '買進成交': i.buy_filled_qty,
        '賣出成交': i.sell_filled_qty
    } for i in inventories]
    pd.DataFrame(inventory_data).to_csv(f"{output_prefix}_{today_str}_庫存狀態.csv", index=False)

    # ---------- 未實現損益 ----------
    unrealized = sdk.accounting.unrealized_gains_and_loses(account).data
    unrealized_data = [{
        '股票代號': u.stock_no,
        '成本價': u.cost_price,
        '庫存量': u.tradable_qty,
        '未實現獲利': u.unrealized_profit,
        '未實現損失': u.unrealized_loss
    } for u in unrealized]
    pd.DataFrame(unrealized_data).to_csv(f"{output_prefix}_{today_str}_未實現損益.csv", index=False)

    # ---------- 交割資訊 ----------
    settlement = sdk.accounting.query_settlement(account, "0d").data
    settlement_data = [{
        '交割日期': d.settlement_date,
        '買進金額': d.buy_value,
        '買進手續費': d.buy_fee,
        '賣出金額': d.sell_value,
        '賣出手續費': d.sell_fee,
        '總交割金額': d.total_settlement_amount,
        '幣別': d.currency
    } for d in settlement.details]
    pd.DataFrame(settlement_data).to_csv(f"{output_prefix}_{today_str}_交割金額.csv", index=False)

    print(f"✅ CSV 報告已成功產生，前綴為：{output_prefix}_{today_str}_*.csv")

def main():
    sdk, account = login_helper.login()
    if sdk and account:
        generate_daily_trade_report_from_sdk(sdk, account)
        try:
            sdk.logout()
            print("🔓 已成功登出")
        except Exception as e:
            print(f"⚠️ 登出失敗: {e}")

if __name__ == "__main__":
    main()
