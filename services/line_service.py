"""
LINE連携サービス
LINE Messaging APIとのやり取りを管理
"""
from linebot import LineBotApi, WebhookHandler
from linebot.models import (
    TextSendMessage, QuickReply, QuickReplyButton,
    MessageAction, FlexSendMessage
)
from linebot.exceptions import LineBotApiError
from config import Config
from typing import List, Optional


class LineService:
    """LINE Bot サービス"""
    
    def __init__(self):
        self.line_bot_api = LineBotApi(Config.LINE_CHANNEL_ACCESS_TOKEN)
        self.handler = WebhookHandler(Config.LINE_CHANNEL_SECRET)
    
    def send_text_message(self, user_line_id: str, text: str) -> bool:
        """
        テキストメッセージを送信
        
        Args:
            user_line_id: 送信先のLINE User ID
            text: メッセージテキスト
            
        Returns:
            成功したらTrue
        """
        try:
            self.line_bot_api.push_message(
                user_line_id,
                TextSendMessage(text=text)
            )
            return True
        except LineBotApiError as e:
            print(f"LINE API Error: {e}")
            return False
    
    def send_shift_notification(self, user_line_id: str, shifts: List) -> bool:
        """
        シフト通知を送信
        
        Args:
            user_line_id: 送信先のLINE User ID
            shifts: シフトリスト
            
        Returns:
            成功したらTrue
        """
        if not shifts:
            return False
        
        # シフト情報をフォーマット
        message = "📅 **シフトが確定しました**\n\n"
        
        for shift in shifts:
            date_str = shift.date.strftime('%m/%d(%a)')
            time_str = f"{shift.start_time.strftime('%H:%M')}-{shift.end_time.strftime('%H:%M')}"
            duration = shift.get_duration_hours()
            
            message += f"・{date_str} {time_str} ({duration:.1f}時間)\n"
        
        return self.send_text_message(user_line_id, message)
    
    def send_quick_reply(self, user_line_id: str, text: str, options: List[str]) -> bool:
        """
        クイックリプライ付きメッセージを送信
        
        Args:
            user_line_id: 送信先のLINE User ID
            text: メッセージテキスト
            options: 選択肢リスト
            
        Returns:
            成功したらTrue
        """
        try:
            quick_reply_buttons = [
                QuickReplyButton(action=MessageAction(label=option, text=option))
                for option in options[:13]  # LINEの制限: 最大13個
            ]
            
            self.line_bot_api.push_message(
                user_line_id,
                TextSendMessage(
                    text=text,
                    quick_reply=QuickReply(items=quick_reply_buttons)
                )
            )
            return True
        except LineBotApiError as e:
            print(f"LINE API Error: {e}")
            return False
    
    def reply_message(self, reply_token: str, text: str) -> bool:
        """
        返信メッセージを送信
        
        Args:
            reply_token: リプライトークン
            text: メッセージテキスト
            
        Returns:
            成功したらTrue
        """
        try:
            self.line_bot_api.reply_message(
                reply_token,
                TextSendMessage(text=text)
            )
            return True
        except LineBotApiError as e:
            print(f"LINE API Error: {e}")
            return False
    
    def broadcast_message(self, user_line_ids: List[str], text: str) -> int:
        """
        複数ユーザーにメッセージを送信
        
        Args:
            user_line_ids: 送信先のLINE User IDリスト
            text: メッセージテキスト
            
        Returns:
            送信成功数
        """
        success_count = 0
        
        for line_id in user_line_ids:
            if self.send_text_message(line_id, text):
                success_count += 1
        
        return success_count
    
    def get_user_profile(self, user_line_id: str) -> Optional[dict]:
        """
        ユーザープロフィールを取得
        
        Args:
            user_line_id: LINE User ID
            
        Returns:
            プロフィール情報（辞書）
        """
        try:
            profile = self.line_bot_api.get_profile(user_line_id)
            return {
                'user_id': profile.user_id,
                'display_name': profile.display_name,
                'picture_url': profile.picture_url,
                'status_message': profile.status_message
            }
        except LineBotApiError as e:
            print(f"LINE API Error: {e}")
            return None


# グローバルインスタンス
line_service = LineService()
