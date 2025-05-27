import json
from datetime import datetime

def convert_stock_data(input_path: str, output_path: str):
    with open(input_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # 如果 timestamp 是字串，轉換成標準格式（可選）
    if isinstance(raw.get("timestamp"), str):
        try:
            raw["timestamp"] = datetime.strptime(raw["timestamp"], "%Y-%m-%d %H:%M:%S").isoformat()
        except:
            pass

    # 建立完整輸出（這裡不拆欄位，直接整包輸出）
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="轉換股票分析 JSON 格式")
    parser.add_argument("--input", required=True, help="輸入檔案路徑（.json）")
    parser.add_argument("--output", required=True, help="輸出檔案路徑（.json）")
    args = parser.parse_args()

    convert_stock_data(args.input, args.output)
