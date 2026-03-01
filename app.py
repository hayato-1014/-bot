"""
シフトBot メインアプリケーション
Flask + LINE Messaging API
"""
from flask import Flask, request, abort
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage
from datetime import datetime
from config import Config
from db.database import init_db, create_tables
from services.line_service import line_service
from models.user import User, UserRole
from handlers.staff_handler import StaffHandler
from handlers.manager_handler import ManagerHandler
from monitoring.error_handler import error_handler, ErrorLevel, ErrorCategory
from db.database import DatabaseSession
import os

# Flaskアプリケーション初期化
app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY

# データベース初期化
init_db()

# アプリケーション起動時にテーブル作成
with app.app_context():
    try:
        create_tables()
        print("✅ Database initialized")
    except Exception as e:
        print(f"⚠️ Database initialization warning: {e}")


@app.route("/")
def index():
    """ヘルスチェック用エンドポイント"""
    return {
        'status': 'ok',
        'service': 'shift_bot',
        'version': '1.0.0',
        'environment': Config.ENVIRONMENT
    }


@app.route("/health")
def health():
    """詳細ヘルスチェック"""
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'checks': {}
    }
    
    # データベース接続チェック
    try:
        with DatabaseSession() as session:
            session.execute('SELECT 1')
        health_status['checks']['database'] = 'ok'
    except Exception as e:
        health_status['checks']['database'] = 'error'
        health_status['status'] = 'unhealthy'
        error_handler.handle_error(
            e,
            ErrorLevel.CRITICAL,
            ErrorCategory.DATABASE
        )
    
    return health_status, 200 if health_status['status'] == 'healthy' else 503


@app.route("/callback", methods=['POST'])
def callback():
    """LINE Webhookコールバック"""
    # 署名検証
    signature = request.headers.get('X-Line-Signature')
    if not signature:
        abort(400)
    
    body = request.get_data(as_text=True)
    
    try:
        line_service.handler.handle(body, signature)
    except InvalidSignatureError:
        error_handler.handle_error(
            Exception("Invalid signature"),
            ErrorLevel.WARNING,
            ErrorCategory.LINE_API
        )
        abort(400)
    
    return 'OK'


@line_service.handler.add(MessageEvent, message=TextMessage)
def handle_message(event: MessageEvent):
    """
    メッセージイベントハンドラー
    """
    try:
        # ユーザーを取得または作成
        user = get_or_create_user(event.source.user_id)
        
        if not user:
            line_service.reply_message(
                event.reply_token,
                "ユーザー情報の取得に失敗しました。管理者に連絡してください。"
            )
            return
        
        message_text = event.message.text.strip()
        
        # コマンド判定
        if message_text in ['ヘルプ', 'help', '使い方']:
            if user.is_manager_or_above():
                ManagerHandler.show_manager_help(event)
            else:
                StaffHandler.show_help(event)
        
        elif message_text in ['シフト', 'シフト確認']:
            StaffHandler.handle_view_shifts(event, user)
        
        elif message_text in ['希望', '希望確認']:
            StaffHandler.handle_view_requests(event, user)
        
        elif message_text.startswith('シフト作成'):
            ManagerHandler.handle_create_shift(event, user)
        
        elif message_text == '承認':
            ManagerHandler.handle_approve_shift(event, user)
        
        else:
            # シフト希望の可能性をチェック
            from utils.validators import Validators
            parsed = Validators.parse_shift_request_message(message_text)
            
            if parsed:
                StaffHandler.handle_shift_request(event, user)
            else:
                # 認識できないメッセージ
                help_msg = "メッセージを認識できませんでした。\n「ヘルプ」と送信すると使い方を確認できます。"
                line_service.reply_message(event.reply_token, help_msg)
    
    except Exception as e:
        error_handler.handle_error(
            e,
            ErrorLevel.ERROR,
            ErrorCategory.BUSINESS_LOGIC,
            {'user_id': event.source.user_id if event.source else None}
        )
        
        line_service.reply_message(
            event.reply_token,
            "エラーが発生しました。しばらく経ってから再度お試しください。"
        )


def get_or_create_user(line_id: str) -> User:
    """
    ユーザーを取得、存在しない場合は作成
    
    Args:
        line_id: LINE User ID
        
    Returns:
        Userオブジェクト
    """
    try:
        with DatabaseSession() as session:
            user = session.query(User).filter(User.line_id == line_id).first()
            
            if not user:
                # 新規ユーザー作成
                profile = line_service.get_user_profile(line_id)
                
                if profile:
                    user = User(
                        line_id=line_id,
                        name=profile.get('display_name', '名前未設定'),
                        role=UserRole.STAFF,  # デフォルトはスタッフ
                        is_active=True
                    )
                    session.add(user)
                    session.commit()
                    
                    # ウェルカムメッセージ
                    welcome_msg = f"""
ようこそ、{user.name}さん！

シフトBotに登録されました。
「ヘルプ」と送信すると使い方を確認できます。
"""
                    line_service.send_text_message(line_id, welcome_msg.strip())
            
            return user
    
    except Exception as e:
        error_handler.handle_error(
            e,
            ErrorLevel.ERROR,
            ErrorCategory.DATABASE,
            {'line_id': line_id}
        )
        return None

@app.route("/admin/set_role/<line_id>/<role>")
def set_user_role(line_id: str, role: str):
    """管理者権限設定用（セキュリティ上、初回設定後は削除推奨）"""
    try:
        with DatabaseSession() as session:
            user = session.query(User).filter(User.line_id == line_id).first()
            if user:
                if role == 'admin':
                    user.role = UserRole.ADMIN
                elif role == 'manager':
                    user.role = UserRole.MANAGER
                elif role == 'leader':
                    user.role = UserRole.LEADER
                elif role == 'staff':
                    user.role = UserRole.STAFF
                session.commit()
                return f'✅ {user.name}の権限を{role}に変更しました'
            else:
                return '❌ ユーザーが見つかりません'
    except Exception as e:
        return f'❌ エラー: {str(e)}'


@app.route("/admin/list_users")
def list_users():
    """全ユーザー一覧"""
    try:
        with DatabaseSession() as session:
            users = session.query(User).all()
            result = []
            for user in users:
                result.append(f'{user.name} (LINE ID: {user.line_id}, 権限: {user.role.value})')
            return '<br>'.join(result)
    except Exception as e:
        return f'❌ エラー: {str(e)}'
if __name__ == "__main__":
    # 開発環境での実行
    port = int(os.environ.get('PORT', 5000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=Config.DEBUG
    )
