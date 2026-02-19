"""
データベース接続管理
SQLAlchemyを使用したデータベースセットアップ
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from config import Config

# ベースモデルクラス
Base = declarative_base()

# データベースエンジン
engine = None
Session = None


def init_db(database_url=None):
    """データベースを初期化"""
    global engine, Session
    
    url = database_url or Config.DATABASE_URL
    
    # エンジン作成
    engine = create_engine(
        url,
        # SQLiteの場合の設定
        connect_args={'check_same_thread': False} if 'sqlite' in url else {},
        # 接続プール設定（PostgreSQLの場合）
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,  # 接続チェック
        echo=Config.DEBUG     # SQLログ出力（開発時のみ）
    )
    
    # セッションファクトリー
    session_factory = sessionmaker(bind=engine)
    Session = scoped_session(session_factory)
    
    return engine


def create_tables():
    """全テーブルを作成"""
    # モデルをインポート（循環参照回避）
    from models.user import User
    from models.shift import Shift
    from models.shift_request import ShiftRequest
    from models.shift_revision import ShiftRevision
    
    Base.metadata.create_all(bind=engine)
    print("✅ All tables created successfully")


def drop_tables():
    """全テーブルを削除（注意: 本番では使用禁止）"""
    if Config.is_production():
        raise RuntimeError("Cannot drop tables in production!")
    
    Base.metadata.drop_all(bind=engine)
    print("⚠️ All tables dropped")


def get_session():
    """セッションを取得"""
    if Session is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return Session()


def close_session():
    """セッションをクローズ"""
    if Session:
        Session.remove()


# コンテキストマネージャー（推奨使用方法）
class DatabaseSession:
    """データベースセッション管理コンテキストマネージャー"""
    
    def __enter__(self):
        self.session = get_session()
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # エラーが発生した場合はロールバック
            self.session.rollback()
        else:
            # 正常終了時はコミット
            self.session.commit()
        
        self.session.close()
        return False  # 例外を再送出


# 使用例:
# with DatabaseSession() as session:
#     user = session.query(User).filter_by(line_id='xxx').first()
#     ...
# # 自動的にcommit/rollback/closeされる
