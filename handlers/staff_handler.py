"""
スタッフ用メッセージハンドラー
一般スタッフからのメッセージ処理
"""
from linebot.models import MessageEvent, TextMessage
from datetime import datetime, timedelta
from models.user import User
from models.shift_request import ShiftRequest, RequestStatus
from services.line_service import line_service
from services.shift_approval import ShiftApprovalService
from utils.validators import Validators
from db.database import DatabaseSession
from monitoring.error_handler import handle_errors, ErrorLevel, ErrorCategory


class StaffHandler:
    """スタッフ用ハンドラー"""
    
    @staticmethod
    @handle_errors(level=ErrorLevel.ERROR, category=ErrorCategory.BUSINESS_LOGIC)
    def handle_shift_request(event: MessageEvent, user: User):
        """
        シフト希望の提出を処理
        
        メッセージ例:
        - "3/1 9:00-17:00"
        - "2024/3/1 9:00-17:00 希望"
        """
        message_text = event.message.text
        
        # メッセージをパース
        parsed = Validators.parse_shift_request_message(message_text)
        
        if not parsed:
            # パースに失敗
            help_message = """
シフト希望を受け付けられませんでした。
以下の形式で送信してください:

例: 3/1 9:00-17:00
例: 2024/3/1 9:00-17:00 希望
例: 3/5 13:00-21:00 できれば

「希望」「できれば」「可能なら」で優先度を指定できます。
"""
            line_service.reply_message(event.reply_token, help_message.strip())
            return
        
        # シフト希望を保存
        try:
            with DatabaseSession() as session:
                shift_request = ShiftRequest(
                    user_id=user.id,
                    date=parsed['date'],
                    start_time=parsed['start_time'],
                    end_time=parsed['end_time'],
                    priority=parsed['priority'],
                    status=RequestStatus.PENDING
                )
                
                session.add(shift_request)
                session.commit()
                
                # 確認メッセージ
                priority_label = shift_request.get_priority_label()
                date_str = parsed['date'].strftime('%m/%d(%a)')
                time_str = f"{parsed['start_time'].strftime('%H:%M')}-{parsed['end_time'].strftime('%H:%M')}"
                duration = shift_request.get_duration_hours()
                
                reply_message = f"""
✅ シフト希望を受け付けました

【日時】{date_str}
【時間】{time_str} ({duration:.1f}時間)
【優先度】{priority_label}

シフト確定時に通知します。
"""
                line_service.reply_message(event.reply_token, reply_message.strip())
                
        except Exception as e:
            error_message = "シフト希望の登録に失敗しました。もう一度お試しください。"
            line_service.reply_message(event.reply_token, error_message)
            raise
    
    @staticmethod
    @handle_errors(level=ErrorLevel.ERROR, category=ErrorCategory.BUSINESS_LOGIC)
    def handle_view_shifts(event: MessageEvent, user: User):
        """
        自分のシフトを確認
        """
        # 今月と来月のシフトを取得
        today = datetime.now().date()
        start_date = today
        end_date = today + timedelta(days=30)
        
        shifts = ShiftApprovalService.get_published_shifts_for_user(
            user.id,
            start_date,
            end_date
        )
        
        if not shifts:
            message = "確定しているシフトはありません。"
            line_service.reply_message(event.reply_token, message)
            return
        
        # シフトをフォーマット
        message = f"📅 **{user.name}さんのシフト**\n\n"
        
        for shift in shifts:
            date_str = shift.date.strftime('%m/%d(%a)')
            time_str = f"{shift.start_time.strftime('%H:%M')}-{shift.end_time.strftime('%H:%M')}"
            duration = shift.get_duration_hours()
            
            message += f"・{date_str} {time_str} ({duration:.1f}h)\n"
        
        line_service.reply_message(event.reply_token, message.strip())
    
    @staticmethod
    @handle_errors(level=ErrorLevel.ERROR, category=ErrorCategory.BUSINESS_LOGIC)
    def handle_view_requests(event: MessageEvent, user: User):
        """
        提出済みのシフト希望を確認
        """
        with DatabaseSession() as session:
            # 未来の希望のみ取得
            today = datetime.now().date()
            
            requests = session.query(ShiftRequest)\
                .filter(
                    ShiftRequest.user_id == user.id,
                    ShiftRequest.date >= today,
                    ShiftRequest.status == RequestStatus.PENDING
                )\
                .order_by(ShiftRequest.date)\
                .all()
            
            if not requests:
                message = "提出済みのシフト希望はありません。"
                line_service.reply_message(event.reply_token, message)
                return
            
            # 希望をフォーマット
            message = f"📝 **提出済みのシフト希望**\n\n"
            
            for req in requests:
                date_str = req.date.strftime('%m/%d(%a)')
                time_str = f"{req.start_time.strftime('%H:%M')}-{req.end_time.strftime('%H:%M')}"
                priority = req.get_priority_label()
                
                message += f"・{date_str} {time_str} [{priority}]\n"
            
            line_service.reply_message(event.reply_token, message.strip())
    
    @staticmethod
    def show_help(event: MessageEvent):
        """
        ヘルプメッセージを表示
        """
        help_message = """
📖 **使い方ガイド**

【シフト希望を提出】
3/1 9:00-17:00
→ 日付と時間を入力

【自分のシフトを確認】
「シフト」または「シフト確認」

【希望を確認】
「希望」または「希望確認」

【優先度の指定】
・「希望」（デフォルト）
・「できれば」
・「可能なら」

例: 3/5 10:00-18:00 できれば
"""
        line_service.reply_message(event.reply_token, help_message.strip())
