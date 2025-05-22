from login_helper import login
from fubon_neo.sdk import FubonSDK

sdk, account = login()
print(f"登入成功：帳號 {account.account}")

# 查詢今日交割金額
settlement = sdk.accounting.query_settlement(account, "0d")

if settlement.is_success and settlement.data and settlement.data.details:
    s = settlement.data.details[0]  # 只取當日第一筆

    print("\n今日交割資訊：")
    print(f"交割日：{s.settlement_date}")
    print(f"買進金額：{s.buy_value} 元")
    print(f"手續費：{s.buy_fee} 元")
    print(f"應付金額：{s.buy_settlement} 元")
    print(f"總交割金額（含稅/費）：{s.total_settlement_amount} 元")
else:
    print("查詢失敗，錯誤訊息：", settlement.message)

sdk.logout()
