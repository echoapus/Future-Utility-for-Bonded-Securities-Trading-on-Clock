#!/usr/bin/env python3
"""
直接使用 Telegram API 取得 Chat ID
不需要運行機器人，避免衝突
"""

import requests
import os
import json
from dotenv import load_dotenv


def get_chat_id_direct():
    """直接從 Telegram API 取得 Chat ID"""
    load_dotenv()

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("❌ 請先在 .env 檔案中設定 TELEGRAM_BOT_TOKEN")
        return

    print("🔍 正在取得 Chat ID...")
    print("📱 請先在 Telegram 中傳送任意訊息給您的機器人")
    print()

    # 使用 getUpdates API
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"

    try:
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            print(f"❌ API 請求失敗: {response.status_code}")
            print(f"錯誤內容: {response.text}")
            return

        data = response.json()

        if not data.get("ok"):
            print(f"❌ API 回應錯誤: {data}")
            return

        updates = data.get("result", [])

        if not updates:
            print("❌ 沒有找到訊息")
            print("📝 請確認您已經:")
            print("   1. 在 Telegram 中找到您的機器人")
            print("   2. 傳送了訊息給機器人 (例如: /start)")
            print("   3. 等待幾秒後再執行此腳本")
            return

        print("✅ 找到訊息！")
        print("=" * 50)

        # 收集所有不重複的 Chat ID
        chat_info = {}

        for update in updates:
            if "message" in update:
                chat = update["message"]["chat"]
                chat_id = chat["id"]

                if chat_id not in chat_info:
                    chat_info[chat_id] = {
                        "type": chat["type"],
                        "first_name": chat.get("first_name", ""),
                        "last_name": chat.get("last_name", ""),
                        "username": chat.get("username", ""),
                        "title": chat.get("title", ""),
                        "latest_message": update["message"].get("text", ""),
                    }

        # 顯示找到的聊天室
        for chat_id, info in chat_info.items():
            print(f"Chat ID: {chat_id}")
            print(f"類型: {info['type']}")

            if info["type"] == "private":
                name = f"{info['first_name']} {info['last_name']}".strip()
                if info["username"]:
                    name += f" (@{info['username']})"
                print(f"用戶: {name}")
            else:
                print(f"群組: {info['title']}")

            if info["latest_message"]:
                print(f"最新訊息: {info['latest_message'][:50]}...")

            print("-" * 30)

        # 如果只有一個 Chat ID，直接推薦
        if len(chat_info) == 1:
            recommended_chat_id = list(chat_info.keys())[0]
            print(f"🎯 推薦的 Chat ID: {recommended_chat_id}")
        else:
            # 選擇最新的私人聊天
            private_chats = [
                cid for cid, info in chat_info.items() if info["type"] == "private"
            ]
            if private_chats:
                recommended_chat_id = private_chats[-1]
                print(f"🎯 推薦的 Chat ID (私人聊天): {recommended_chat_id}")
            else:
                recommended_chat_id = list(chat_info.keys())[-1]
                print(f"🎯 推薦的 Chat ID (最新): {recommended_chat_id}")

        print("=" * 50)
        print("📝 請將以下內容加入您的 .env 檔案:")
        print(f"TELEGRAM_CHAT_ID={recommended_chat_id}")
        print()
        print("✅ 設定完成後即可使用成交監控功能！")

        # 自動更新 .env 檔案
        update_env = input("\n❓ 是否自動更新 .env 檔案? (y/N): ").strip().lower()
        if update_env == "y":
            update_env_file(recommended_chat_id)

    except requests.exceptions.Timeout:
        print("❌ 請求超時，請檢查網路連線")
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")


def update_env_file(chat_id):
    """自動更新 .env 檔案"""
    try:
        env_file = ".env"

        # 讀取現有的 .env 內容
        lines = []
        if os.path.exists(env_file):
            with open(env_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

        # 檢查是否已存在 TELEGRAM_CHAT_ID
        chat_id_exists = False
        for i, line in enumerate(lines):
            if line.strip().startswith("TELEGRAM_CHAT_ID="):
                lines[i] = f"TELEGRAM_CHAT_ID={chat_id}\n"
                chat_id_exists = True
                break

        # 如果不存在，則新增
        if not chat_id_exists:
            lines.append(f"TELEGRAM_CHAT_ID={chat_id}\n")

        # 寫回檔案
        with open(env_file, "w", encoding="utf-8") as f:
            f.writelines(lines)

        print(f"✅ 已自動更新 .env 檔案")
        print(f"📝 TELEGRAM_CHAT_ID={chat_id}")

    except Exception as e:
        print(f"❌ 更新 .env 檔案失敗: {e}")
        print(f"📝 請手動將 TELEGRAM_CHAT_ID={chat_id} 加入 .env 檔案")


def test_telegram_connection(chat_id):
    """測試 Telegram 連線"""
    load_dotenv()

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("❌ 找不到 TELEGRAM_BOT_TOKEN")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    test_message = f"""
🧪 測試訊息

✅ Chat ID: {chat_id}
⏰ 時間: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📱 Telegram API 連線正常

🎉 成交監控系統準備就緒！
    """

    try:
        response = requests.post(
            url, json={"chat_id": chat_id, "text": test_message.strip()}, timeout=10
        )

        if response.status_code == 200:
            print("✅ 測試訊息發送成功！")
            print("📱 請檢查您的 Telegram 是否收到測試訊息")
            return True
        else:
            print(f"❌ 測試訊息發送失敗: {response.status_code}")
            print(f"錯誤: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 測試連線時發生錯誤: {e}")
        return False


def main():
    """主程式"""
    print("🤖 Telegram Chat ID 取得工具")
    print("=" * 40)

    # 取得 Chat ID
    get_chat_id_direct()

    # 詢問是否測試連線
    test_connection = input("\n❓ 是否發送測試訊息驗證設定? (y/N): ").strip().lower()
    if test_connection == "y":
        load_dotenv()  # 重新載入環境變數
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if chat_id:
            print(f"\n🧪 正在發送測試訊息到 Chat ID: {chat_id}")
            test_telegram_connection(chat_id)
        else:
            print("❌ 找不到 TELEGRAM_CHAT_ID，請先設定")


if __name__ == "__main__":
    main()
