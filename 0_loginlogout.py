import json
import os
from fubon_neo.sdk import FubonSDK
from dotenv import load_dotenv

# 載入 .env 檔（帳密從環境變數取得）
load_dotenv()

# 讀取設定檔（只包含 cert_path）
with open("config.json", "r") as file:
    config = json.load(file)

# 補上敏感資訊（從 .env 抓）
config["personal_id"] = os.getenv("FUBON_ID")
config["password"] = os.getenv("FUBON_PASS")
config["cert_pass"] = os.getenv("FUBON_CERT_PASS")

# 初始化 SDK 並登入
sdk = FubonSDK()
accounts = sdk.login(
    config["personal_id"],
    config["password"],
    config["cert_path"],
    config["cert_pass"]
)

# 檢查登入結果
if hasattr(accounts, "data") and accounts.data:
    print("✅ 登入成功，帳號列表：", accounts.data)

    # ...這裡可以下單或查詢
    # 例如 sdk.buy(...)、sdk.get_balance() 之類

    # 登出
    if sdk.logout():
        print("✅ 登出成功")
    else:
        print("⚠️ 登出失敗")
else:
    print("❌ 登入失敗，回應內容：", accounts)
