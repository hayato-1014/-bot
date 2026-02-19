"""
エラーハンドラー
エラー監視と通知の中央管理
"""
import traceback
import sys
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Optional
from utils.audit_log import log_action


class ErrorLevel(Enum):
    """エラーレベル"""
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ErrorCategory(Enum):
    """エラーカテゴリ"""
    DATABASE = "database"
    LINE_API = "line_api"
    BUSINESS_LOGIC = "business_logic"
    LABOR_LAW = "labor_law"
    PERMISSION = "permission"
    VALIDATION = "validation"
    SYSTEM = "system"


class ErrorHandler:
    """エラーハンドラー"""
    
    def __init__(self):
        self.error_cache = {}
    
    def handle_error(self, 
                    error: Exception,
                    level: ErrorLevel = ErrorLevel.ERROR,
                    category: ErrorCategory = ErrorCategory.SYSTEM,
                    context: Optional[dict] = None):
        """
        エラーを処理
        
        Args:
            error: Exception
            level: エラーレベル
            category: エラーカテゴリ
            context: コンテキスト情報
        """
        try:
            error_info = {
                'timestamp': datetime.now().isoformat(),
                'level': level.value,
                'category': category.value,
                'message': str(error),
                'type': type(error).__name__,
                'traceback': traceback.format_exc(),
                'context': context or {}
            }
            
            # 監査ログに記録
            log_action(
                action='ERROR_OCCURRED',
                actor_id=context.get('user_id') if context else None,
                result='FAILURE',
                error_message=error_info['message']
            )
            
            # コンソール出力
            self._log_to_console(error_info, level)
            
            # Sentryに送信（設定されている場合）
            self._send_to_sentry(error_info, level)
            
            # 開発者に通知（CRITICALの場合）
            if level == ErrorLevel.CRITICAL:
                self._notify_developer(error_info)
            
        except Exception as e:
            print(f"CRITICAL: Error handler failed: {e}", file=sys.stderr)
    
    def _log_to_console(self, error_info: dict, level: ErrorLevel):
        """コンソールにログ出力"""
        emoji_map = {
            ErrorLevel.CRITICAL: "🚨",
            ErrorLevel.ERROR: "❌",
            ErrorLevel.WARNING: "⚠️",
            ErrorLevel.INFO: "ℹ️"
        }
        
        emoji = emoji_map.get(level, "❗")
        print(f"\n{emoji} {level.value.upper()} [{error_info['category']}]", file=sys.stderr)
        print(f"Time: {error_info['timestamp']}", file=sys.stderr)
        print(f"Message: {error_info['message']}", file=sys.stderr)
        
        if level in [ErrorLevel.CRITICAL, ErrorLevel.ERROR]:
            print(f"Traceback:\n{error_info['traceback']}", file=sys.stderr)
    
    def _send_to_sentry(self, error_info: dict, level: ErrorLevel):
        """Sentryに送信（設定されている場合）"""
        try:
            import sentry_sdk
            from config import Config
            
            if Config.SENTRY_DSN:
                with sentry_sdk.push_scope() as scope:
                    scope.set_level(level.value)
                    scope.set_tag("category", error_info['category'])
                    
                    if error_info.get('context'):
                        for key, value in error_info['context'].items():
                            scope.set_context(key, value)
                    
                    sentry_sdk.capture_message(
                        error_info['message'],
                        level=level.value
                    )
        except ImportError:
            # Sentryがインストールされていない場合はスキップ
            pass
        except Exception as e:
            print(f"Failed to send to Sentry: {e}", file=sys.stderr)
    
    def _notify_developer(self, error_info: dict):
        """開発者に通知（LINE Notify）"""
        try:
            from config import Config
            import requests
            
            if Config.LINE_NOTIFY_TOKEN:
                message = f"""
🚨 CRITICAL ERROR

時刻: {error_info['timestamp']}
カテゴリ: {error_info['category']}
メッセージ: {error_info['message'][:200]}

即座の対応が必要です
"""
                
                requests.post(
                    'https://notify-api.line.me/api/notify',
                    headers={'Authorization': f'Bearer {Config.LINE_NOTIFY_TOKEN}'},
                    data={'message': message.strip()},
                    timeout=10
                )
        except Exception as e:
            print(f"Failed to notify developer: {e}", file=sys.stderr)


# グローバルインスタンス
error_handler = ErrorHandler()


# デコレーター
def handle_errors(level=ErrorLevel.ERROR, category=ErrorCategory.SYSTEM):
    """エラーハンドリングデコレーター"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = {
                    'function': func.__name__,
                    'args': str(args)[:100],
                    'kwargs': str(kwargs)[:100]
                }
                
                error_handler.handle_error(e, level, category, context)
                
                if level == ErrorLevel.CRITICAL:
                    raise
                
                return None
        
        return wrapper
    return decorator


# 使用例:
# @handle_errors(level=ErrorLevel.ERROR, category=ErrorCategory.DATABASE)
# def some_function():
#     ...
