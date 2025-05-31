import os
import sys
import asyncio
import logging
import tempfile
import datetime
import re
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# 導入您的 GaN 分析模組
try:
    from GaN import init_system, run_analysis_with_logout, login_success, sdk
except ImportError:
    print("請確保 GaN.py 在同一目錄下")
    sys.exit(1)

# 載入環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class StockAnalysisBot:
    def __init__(self, token):
        self.token = token
        self.app = Application.builder().token(token).build()
        self.gan_initialized = False
        
        # 註冊處理器
        self.setup_handlers()
    
    def setup_handlers(self):
        """設定機器人指令處理器"""
        # 指令處理器
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("status", self.status_command))
        self.app.add_handler(CommandHandler("init", self.init_command))
        
        # 訊息處理器 - 處理股票代碼
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.analyze_stock_message
        ))
    
    def is_valid_stock_code(self, code):
        """
        簡單的股票代碼驗證 - 只允許數字和英文字母
        
        Args:
            code (str): 股票代碼
            
        Returns:
            bool: 是否有效
        """
        if not code or not isinstance(code, str):
            return False
        
        # 去除空白並轉大寫
        code = code.strip().upper()
        
        # 長度檢查：3-6 字符
        if not (3 <= len(code) <= 6):
            return False
        
        # 只允許數字和英文字母的組合
        if not re.match(r'^[0-9A-Z]+$', code):
            return False
        
        return True
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """開始指令"""
        welcome_text = """
🤖 歡迎使用股票分析機器人！(增強版 v2.1)

📈 功能說明：
• 直接輸入股票代碼（如：2330）即可獲得完整分析
• 支援台股即時報價、技術指標、五檔力道分析等

🎯 新增功能：
• RSI 超買超賣分析
• 布林通道位置判斷
• 五檔買賣力道評估
• 綜合技術面評分

📋 可用指令：
/start - 顯示歡迎訊息
/help - 顯示說明
/status - 檢查系統狀態
/init - 重新初始化系統

💡 使用範例：
直接輸入「2330」查看台積電分析
直接輸入「0050」查看元大台灣50分析

⚠️ 注意：首次使用需要初始化，請稍候...
        """
        await update.message.reply_text(welcome_text)
        
        # 自動初始化系統
        if not self.gan_initialized:
            await self.initialize_gan_system(update, context)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """說明指令"""
        help_text = """
📖 使用說明：

🔍 股票查詢：
直接輸入股票代碼即可，例如：
• 2330 → 台積電分析
• 2454 → 聯發科分析
• 0050 → 元大台灣50分析

📊 分析內容包含：
• 💰 即時價格與漲跌幅
• 📈 技術指標（MA5/10/20）
• 🎯 MACD 多空訊號
• 📊 KD 指標 & 交叉訊號
• 🔥 RSI 超買超賣分析
• 📏 布林通道位置
• ⚖️ 五檔買賣力道
• 💼 大單流向分析
• 📋 綜合技術面評分
• 📄 五檔報價 & 成交明細
• 📊 分價量表 & 簡易走勢圖

⚙️ 系統指令：
/status - 檢查連線狀態
/init - 重新初始化（如遇問題可使用）

💬 支援格式：
• 長度：3-6 個字符
• 只能包含數字和英文字母
• 範例：2330、0050、2454、006208
        """
        await update.message.reply_text(help_text)
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """狀態檢查指令"""
        global login_success
        
        status_text = f"""
🔧 系統狀態檢查

機器人狀態: ✅ 運行中 (增強版 v2.1)
GaN系統: {'✅ 已初始化' if self.gan_initialized else '❌ 未初始化 (已登出)'}
富邦登入: {'✅ 已登入' if login_success else '❌ 未登入 (已登出)'}

{('🟢 系統正常，可以查詢股票' if self.gan_initialized and login_success 
  else '🟡 系統已登出，下次查詢時會自動重新登入')}

🆕 新功能狀態:
• RSI 指標: ✅ 可用
• 布林通道: ✅ 可用  
• 五檔力道: ✅ 可用
• 綜合評分: ✅ 可用
        """
        await update.message.reply_text(status_text)
    
    async def init_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """手動初始化指令"""
        await update.message.reply_text("🔄 正在重新初始化增強版系統...")
        await self.initialize_gan_system(update, context)
    
    async def initialize_gan_system(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """初始化 GaN 系統"""
        try:
            # 顯示初始化訊息
            init_msg = await update.message.reply_text("⏳ 正在初始化股票分析系統...")
            
            # 在後台執行初始化
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(None, init_system)
            
            if success:
                self.gan_initialized = True
                await init_msg.edit_text("✅ 增強版系統初始化成功！現在可以查詢股票了。")
            else:
                await init_msg.edit_text("❌ 增強版系統初始化失敗，請檢查網路連線或聯繫管理員。")
                
        except Exception as e:
            logger.error(f"初始化失敗: {e}")
            await update.message.reply_text(f"❌ 初始化過程中發生錯誤：{str(e)}")
    
    async def analyze_stock_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """處理股票代碼訊息"""
        user_input = update.message.text.strip().upper()
        
        # 簡單檢查是否為股票代碼格式
        if not self.is_valid_stock_code(user_input):
            await update.message.reply_text(
                "❓ 請輸入有效的股票代碼\n"
                "• 長度：3-6 個字符\n"
                "• 只能包含數字和英文字母\n"
                "• 範例：2330、0050、2454\n"
                "或使用 /help 查看說明"
            )
            return
        
        # 檢查系統狀態
        if not self.gan_initialized:
            await update.message.reply_text(
                "⚠️ 系統尚未初始化，正在初始化中..."
            )
            await self.initialize_gan_system(update, context)
            if not self.gan_initialized:
                return
        
        # 開始分析
        analysis_msg = await update.message.reply_text(f"📊 分析中")
        
        try:
            # 捕獲分析輸出
            output_buffer = StringIO()
            error_buffer = StringIO()
            
            with redirect_stdout(output_buffer), redirect_stderr(error_buffer):
                # 在後台執行分析 (使用帶登出功能的版本)
                loop = asyncio.get_event_loop()
                success = await loop.run_in_executor(
                    None, 
                    run_analysis_with_logout, 
                    user_input
                )
            
            # 取得輸出結果
            analysis_output = output_buffer.getvalue()
            error_output = error_buffer.getvalue()
            
            if success and analysis_output:
                # 先發送 TXT 檔案
                await self.send_analysis_file(update, analysis_output, user_input)
                
                # 再發送摘要訊息
                await self.send_analysis_summary(update, analysis_output, user_input)
                
                # 🔒 系統已在 GaN 模組中自動登出，更新本地狀態
                self.gan_initialized = False
                
                # 刪除分析中訊息
                try:
                    await analysis_msg.delete()
                except:
                    pass
                
            else:
                error_msg = f"❌ 分析 {user_input} 失敗"
                if error_output:
                    error_msg += f"\n錯誤訊息：{error_output[:200]}"
                await analysis_msg.edit_text(error_msg)
                
        except Exception as e:
            logger.error(f"分析股票 {user_input} 時發生錯誤: {e}")
            await analysis_msg.edit_text(f"❌ 分析過程中發生錯誤：{str(e)}")
            # 發生錯誤時重置狀態
            self.gan_initialized = False
    
    async def send_analysis_file(self, update: Update, analysis_content: str, stock_code: str):
        """將分析結果製作成 TXT 檔案並發送"""
        try:
            # 建立檔案名稱（包含時間戳記）
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{stock_code}_analysis_{timestamp}.txt"
            
            # 準備檔案內容
            file_content = f"""股票分析報告 (增強版)
==========================================
股票代碼: {stock_code}
分析時間: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
系統版本: GaN Stock Analysis Bot v2.1 Enhanced
==========================================

{analysis_content}

==========================================
報告結束 - 增強版功能
• RSI 超買超賣分析
• 布林通道位置判斷  
• 五檔買賣力道評估
• 綜合技術面評分
• 大單流向分析
• KD 黃金/死亡交叉
• VWAP 強弱判斷
==========================================
生成時間: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
            
            # 建立臨時檔案
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
            
            # 發送檔案
            with open(temp_file_path, 'rb') as file:
                await update.message.reply_document(
                    document=file,
                    filename=filename,
                    caption=f"📄 {stock_code} 完整分析報告 (增強版)\n🕐 時間: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n📊 包含RSI、布林通道、五檔力道等新功能"
                )
            
            # 清理臨時檔案
            os.unlink(temp_file_path)
            
            logger.info(f"已成功發送 {stock_code} 的增強版分析檔案")
            
        except Exception as e:
            logger.error(f"發送分析檔案時發生錯誤: {e}")
            await update.message.reply_text(f"❌ 檔案生成失敗：{str(e)}")
    
    async def send_analysis_summary(self, update: Update, analysis_content: str, stock_code: str):
        """發送分析摘要（增強版本）"""
        try:
            # 提取關鍵資訊製作摘要
            summary = self.extract_enhanced_summary(analysis_content, stock_code)
            
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 構建摘要訊息
            summary_message = (
                f"📋 {stock_code} 分析摘要\n"
                f"🕐 分析時間: {current_time}\n"
                f"{'='*30}\n"
                f"{summary}\n"
                f"{'='*30}\n"
            )
            
            await update.message.reply_text(summary_message)
            
        except Exception as e:
            logger.error(f"發送摘要時發生錯誤: {e}")
            # 發送簡化的成功訊息
            fallback_message = (
                f"✅ {stock_code} 分析完成\n\n"
            )
            try:
                await update.message.reply_text(fallback_message)
            except Exception as fallback_error:
                logger.error(f"發送備用訊息也失敗: {fallback_error}")
    
    def extract_enhanced_summary(self, analysis_content: str, stock_code: str):
        """從完整分析中提取關鍵摘要（增強版）"""
        try:
            lines = analysis_content.split('\n')
            summary_parts = []
            
            # 用於儲存特殊資訊
            vwap_info = {'value': None, 'status': None, 'current_price': None}
            order_book_info = {'bid_total': 0, 'ask_total': 0, 'sentiment': None}
            
            # 尋找關鍵資訊
            for i, line in enumerate(lines):
                line = line.strip()
                
                # 股價資訊
                if '目前價格:' in line:
                    summary_parts.append(f"💰 {line}")
                    # 提取現價用於 VWAP 對照
                    try:
                        import re
                        price_match = re.search(r'目前價格:\s*([0-9.]+)', line)
                        if price_match:
                            vwap_info['current_price'] = float(price_match.group(1))
                    except:
                        pass
                
                # VWAP 資訊收集
                elif line.startswith('VWAP:') and '股價' in line:
                    try:
                        import re
                        # 提取 VWAP 數值: "VWAP: 95.14 (股價+2.35%)"
                        vwap_match = re.search(r'VWAP:\s*([0-9.]+)', line)
                        if vwap_match:
                            vwap_info['value'] = float(vwap_match.group(1))
                    except:
                        pass
                elif 'VWAP狀態:' in line:
                    vwap_info['status'] = line.replace('VWAP狀態:', '').strip()
                
                # 五檔力道資訊收集
                elif '買盤力道:' in line and '%' in line:
                    try:
                        import re
                        # 提取買盤張數: "買盤力道: 45.2% (1200張)"
                        bid_match = re.search(r'\(([0-9,]+)張\)', line)
                        if bid_match:
                            order_book_info['bid_total'] = int(bid_match.group(1).replace(',', ''))
                    except:
                        pass
                elif '賣盤力道:' in line and '%' in line:
                    try:
                        import re
                        # 提取賣盤張數: "賣盤力道: 54.8% (1460張)"
                        ask_match = re.search(r'\(([0-9,]+)張\)', line)
                        if ask_match:
                            order_book_info['ask_total'] = int(ask_match.group(1).replace(',', ''))
                    except:
                        pass
                elif '市場情緒:' in line:
                    order_book_info['sentiment'] = line.replace('市場情緒:', '').strip()
                
                # 技術指標摘要
                elif line.startswith('MA5:') and i+2 < len(lines):
                    # 收集 MA 資訊
                    ma_info = []
                    for j in range(3):  # MA5, MA10, MA20
                        if i+j < len(lines) and ('MA' in lines[i+j] or '股價 vs MA' in lines[i+j]):
                            ma_line = lines[i+j].strip()
                            if ma_line.startswith('MA'):
                                ma_info.append(ma_line)
                    if ma_info:
                        summary_parts.append(f"📈 {' | '.join(ma_info[:2])}")
                
                # MA 排列
                elif 'MA排列:' in line:
                    summary_parts.append(f"📊 {line}")
                
                # RSI 狀態 (新增)
                elif 'RSI狀態:' in line:
                    rsi_line = None
                    # 找前一行的 RSI 數值
                    if i > 0:
                        prev_line = lines[i-1].strip()
                        if prev_line.startswith('RSI:'):
                            rsi_line = prev_line
                    summary_parts.append(f"🔥 {rsi_line + ' ' if rsi_line else ''}{line}")
                
                # 布林通道狀態 (新增)
                elif '布林狀態:' in line:
                    summary_parts.append(f"📏 {line}")
                
                # MACD 訊號
                elif 'MACD訊號:' in line:
                    summary_parts.append(f"🎯 {line}")
                
                # KD 狀態和交叉
                elif 'KD狀態:' in line:
                    summary_parts.append(f"📊 {line}")
                elif 'KD訊號:' in line and ('黃金交叉' in line or '死亡交叉' in line):
                    summary_parts.append(f"⚡ {line}")
                
                # 大單趨勢 (新增)
                elif '大單趨勢:' in line:
                    summary_parts.append(f"💼 {line}")
                
                # 綜合技術分析評分 (新增)
                elif '技術面評價:' in line:
                    # 尋找前一行的評分
                    score_line = None
                    if i > 0 and '技術面評分:' in lines[i-1]:
                        score_line = lines[i-1].strip()
                    summary_parts.append(f"🏆 {score_line + ' | ' if score_line else ''}{line}")
            
            # 生成 VWAP 對照資訊
            if vwap_info['value'] and vwap_info['current_price'] and vwap_info['status']:
                vwap_summary = f"🧭 VWAP: {vwap_info['value']:.2f} ｜目前價格{vwap_info['status'].replace('股價', '').replace('VWAP', 'VWAP')}"
                summary_parts.insert(1, vwap_summary)  # 插入到股價後面
            
            # 生成五檔買賣力道概況
            if order_book_info['bid_total'] > 0 and order_book_info['ask_total'] > 0:
                # 判斷上壓下撐
                if order_book_info['ask_total'] > order_book_info['bid_total']:
                    pressure_situation = "上壓>下撐"
                    pressure_detail = f"賣1~賣3 共{order_book_info['ask_total']:,}張 vs 買1~買3 約{order_book_info['bid_total']:,}張"
                elif order_book_info['bid_total'] > order_book_info['ask_total']:
                    pressure_situation = "下撐>上壓"
                    pressure_detail = f"買1~買3 共{order_book_info['bid_total']:,}張 vs 賣1~賣3 約{order_book_info['ask_total']:,}張"
                else:
                    pressure_situation = "上壓≈下撐"
                    pressure_detail = f"買賣力道均衡 約{order_book_info['bid_total']:,}張"
                
                order_book_summary = f"📦 五檔：{pressure_situation}（{pressure_detail}）"
                summary_parts.insert(2, order_book_summary)  # 插入到 VWAP 後面
            
            # 如果沒有找到關鍵資訊，返回基本摘要
            if not summary_parts:
                return f"✅ 已完成 {stock_code} 增強版分析\n📄 請查看 TXT 檔案獲取完整報告"
            
            # 限制摘要長度，優先顯示重要資訊
            important_keywords = ['目前價格', 'VWAP:', '五檔：', '技術面評價', 'RSI狀態', '市場情緒', 'MA排列', 'MACD訊號']
            
            # 先取重要資訊
            important_parts = []
            other_parts = []
            
            for part in summary_parts:
                is_important = any(keyword in part for keyword in important_keywords)
                if is_important:
                    important_parts.append(part)
                else:
                    other_parts.append(part)
            
            # 組合摘要，重要資訊優先，總共最多10行（增加2行給新功能）
            selected_parts = important_parts[:8] + other_parts[:2]
            
            return '\n'.join(selected_parts[:10])
            
        except Exception as e:
            logger.error(f"提取增強版摘要時發生錯誤: {e}")
            return f"✅ 已完成 {stock_code} 增強版分析\n📄 請查看 TXT 檔案獲取完整報告"
    
    def run(self):
        """啟動機器人"""
        logger.info("股票分析機器人 (增強版 v2.1) 啟動中...")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    """主程式"""
    # 從環境變數取得 Token
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not bot_token:
        print("❌ 請在 .env 檔案中設定 TELEGRAM_BOT_TOKEN")
        print("格式：TELEGRAM_BOT_TOKEN=你的機器人Token")
        return
    
    # 建立並啟動機器人
    bot = StockAnalysisBot(bot_token)
    
    try:
        print("🚀 啟動中")
        bot.run()
    except KeyboardInterrupt:
        logger.info("機器人已停止")
    except Exception as e:
        logger.error(f"運行錯誤: {e}")

if __name__ == "__main__":
    main()
