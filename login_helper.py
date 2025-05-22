import os
import json
from dotenv import load_dotenv
from fubon_neo.sdk import FubonSDK


def login():
    load_dotenv()

    # 讀取 config + .env 組合帳密
    with open("config.json", "r") as f:
        config = json.load(f)

    config["personal_id"] = os.getenv("FUBON_ID")
    config["password"] = os.getenv("FUBON_PASS")
    config["cert_pass"] = os.getenv("FUBON_CERT_PASS")

    # 登入
    sdk = FubonSDK()
    accounts = sdk.login(
        config["personal_id"],
        config["password"],
        config["cert_path"],
        config["cert_pass"]
    )

    if hasattr(accounts, "data") and accounts.data:
        return sdk, accounts.data[0]
    else:
        raise Exception("登入失敗")
