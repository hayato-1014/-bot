"""
設定管理モジュール
環境変数を読み込み、アプリケーション全体で使用する設定を管理
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# .envファイルの読み込み
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)


class Config:
    """アプリケーション設定クラス"""
    
    # 基本設定
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # LINE Bot設定
    LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
    LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
    
    # データベース設定
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///shift_bot.db')
    
    # エラー監視設定
    SENTRY_DSN = os.getenv('SENTRY_DSN')
    LINE_NOTIFY_TOKEN = os.getenv('LINE_NOTIFY_TOKEN')
    DEVELOPER_EMAIL = os.getenv('DEVELOPER_EMAIL')
    
    # メール設定
    SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USER = os.getenv('SMTP_USER')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
    
    # セキュリティ設定
    ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'True').lower() == 'true'
    MAX_REQUESTS_PER_HOUR = int(os.getenv('MAX_REQUESTS_PER_HOUR', '100'))
    
    # セッション設定
    SESSION_TIMEOUT_MINUTES = int(os.getenv('SESSION_TIMEOUT_MINUTES', '30'))
    
    # タイムゾーン
    TIMEZONE = os.getenv('TIMEZONE', 'Asia/Tokyo')
    
    # 労働法設定
    MAX_WORK_HOURS_PER_DAY = int(os.getenv('MAX_WORK_HOURS_PER_DAY', '8'))
    MAX_WORK_HOURS_PER_WEEK = int(os.getenv('MAX_WORK_HOURS_PER_WEEK', '40'))
    MIN_REST_TIME_6H = int(os.getenv('MIN_REST_TIME_6H', '45'))
    MIN_REST_TIME_8H = int(os.getenv('MIN_REST_TIME_8H', '60'))
    MAX_CONSECUTIVE_WORK_DAYS = int(os.getenv('MAX_CONSECUTIVE_WORK_DAYS', '6'))
    
    # シフト設定
    MAX_STAFF_PER_SHIFT = int(os.getenv('MAX_STAFF_PER_SHIFT', '10'))
    MIN_STAFF_PER_SHIFT = int(os.getenv('MIN_STAFF_PER_SHIFT', '2'))
    SHIFT_GENERATION_LOOKAHEAD_DAYS = int(os.getenv('SHIFT_GENERATION_LOOKAHEAD_DAYS', '14'))
    
    @classmethod
    def validate(cls):
        """必須設定の検証"""
        errors = []
        
        # 本番環境での必須チェック
        if cls.ENVIRONMENT == 'production':
            if not cls.LINE_CHANNEL_SECRET:
                errors.append('LINE_CHANNEL_SECRET is required in production')
            if not cls.LINE_CHANNEL_ACCESS_TOKEN:
                errors.append('LINE_CHANNEL_ACCESS_TOKEN is required in production')
            if cls.SECRET_KEY == 'dev-secret-key-change-in-production':
                errors.append('SECRET_KEY must be changed in production')
            if not cls.DATABASE_URL or 'sqlite' in cls.DATABASE_URL:
                errors.append('PostgreSQL DATABASE_URL is required in production')
        
        if errors:
            raise ValueError(f"Configuration errors:\n" + "\n".join(errors))
        
        return True
    
    @classmethod
    def is_production(cls):
        """本番環境かどうか"""
        return cls.ENVIRONMENT == 'production'
    
    @classmethod
    def is_development(cls):
        """開発環境かどうか"""
        return cls.ENVIRONMENT == 'development'


# 設定の検証（アプリ起動時）
try:
    Config.validate()
except ValueError as e:
    if Config.is_production():
        raise  # 本番環境では起動を停止
    else:
        print(f"⚠️ Configuration warning: {e}")
