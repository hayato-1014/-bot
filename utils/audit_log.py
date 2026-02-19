"""
監査ログユーティリティ
システムの重要な操作を記録
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from db.database import Base, DatabaseSession


class AuditLog(Base):
    """監査ログモデル"""
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String(100), nullable=False, index=True)
    actor_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    target_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(Integer, nullable=True)
    data_accessed = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    result = Column(String(20), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


def log_action(action: str, 
               actor_id: Optional[int] = None,
               target_user_id: Optional[int] = None,
               resource_type: Optional[str] = None,
               resource_id: Optional[int] = None,
               data_accessed: Optional[str] = None,
               result: str = "SUCCESS",
               error_message: Optional[str] = None,
               ip_address: Optional[str] = None,
               user_agent: Optional[str] = None):
    """
    監査ログを記録
    
    Args:
        action: 実行されたアクション（例: "CREATE_SHIFT", "APPROVE_SHIFT"）
        actor_id: 実行者のユーザーID
        target_user_id: 対象ユーザーID（他のユーザーに対する操作の場合）
        resource_type: リソースタイプ（例: "SHIFT", "USER"）
        resource_id: リソースID
        data_accessed: アクセスしたデータの概要
        result: 結果（"SUCCESS" or "FAILURE"）
        error_message: エラーメッセージ（失敗時）
        ip_address: IPアドレス
        user_agent: User Agent
    """
    try:
        with DatabaseSession() as session:
            log_entry = AuditLog(
                action=action,
                actor_id=actor_id,
                target_user_id=target_user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                data_accessed=data_accessed[:1000] if data_accessed else None,  # 長さ制限
                result=result,
                error_message=error_message[:1000] if error_message else None,
                ip_address=ip_address,
                user_agent=user_agent[:500] if user_agent else None
            )
            session.add(log_entry)
            session.commit()
    except Exception as e:
        # ログ記録自体が失敗してもアプリケーションは継続
        print(f"⚠️ Failed to write audit log: {e}")


def get_user_activity_log(user_id: int, limit: int = 100):
    """
    特定ユーザーの活動ログを取得
    
    Args:
        user_id: ユーザーID
        limit: 取得件数
        
    Returns:
        ログエントリのリスト
    """
    with DatabaseSession() as session:
        logs = session.query(AuditLog)\
            .filter(AuditLog.actor_id == user_id)\
            .order_by(AuditLog.created_at.desc())\
            .limit(limit)\
            .all()
        
        return [
            {
                'action': log.action,
                'result': log.result,
                'created_at': log.created_at.isoformat() if log.created_at else None,
                'error_message': log.error_message
            }
            for log in logs
        ]


def get_resource_history(resource_type: str, resource_id: int, limit: int = 50):
    """
    特定リソースの操作履歴を取得
    
    Args:
        resource_type: リソースタイプ
        resource_id: リソースID
        limit: 取得件数
        
    Returns:
        操作履歴のリスト
    """
    with DatabaseSession() as session:
        logs = session.query(AuditLog)\
            .filter(
                AuditLog.resource_type == resource_type,
                AuditLog.resource_id == resource_id
            )\
            .order_by(AuditLog.created_at.desc())\
            .limit(limit)\
            .all()
        
        return [
            {
                'action': log.action,
                'actor_id': log.actor_id,
                'result': log.result,
                'created_at': log.created_at.isoformat() if log.created_at else None
            }
            for log in logs
        ]


# 使用例:
# log_action(
#     action='APPROVE_SHIFT',
#     actor_id=manager_id,
#     resource_type='SHIFT',
#     resource_id=shift_id,
#     result='SUCCESS'
# )
