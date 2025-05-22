# utils.py
class TradingUtils:
    @staticmethod
    @contextmanager
    def trading_session():
        """一次處理登入登出"""
        sdk, account = login()
        print(f"✅ 登入成功：{account.account}")
        try:
            yield sdk, account
        finally:
            sdk.logout()
            print("✅ 已登出")
    
    @staticmethod
    def save_with_timestamp(content, prefix):
        """自動產生時間戳檔名並儲存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"{prefix}_{timestamp}.txt"
        # ... 儲存邏輯
