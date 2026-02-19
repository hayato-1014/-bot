"""
ユーザーモデル
スタッフ情報と権限管理
"""
from enum import Enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from db.database import Base


class UserRole(Enum):
    """ユーザー役割（階層構造）"""
    STAFF = 1              # 一般スタッフ
    EVALUATOR = 2          # 評価権限者
    SUB_MANAGER = 3        # 副店長（調整まで）
    MANAGER = 4            # 店長（承認・公開可能）
    ADMIN = 5              # システム管理者


class Permission(Enum):
    """権限種別"""
    VIEW_OWN_SHIFT = "view_own_shift"
    VIEW_ALL_SHIFTS = "view_all_shifts"
    REQUEST_SHIFT = "request_shift"
    EVALUATE_STAFF = "evaluate_staff"
    CREATE_DRAFT_SHIFT = "create_draft_shift"
    ADJUST_SHIFT = "adjust_shift"
    APPROVE_SHIFT = "approve_shift"
    PUBLISH_SHIFT = "publish_shift"
    REJECT_SHIFT = "reject_shift"
    VIEW_ANALYTICS = "view_analytics"


# 役割ごとの権限マッピング
ROLE_PERMISSIONS = {
    UserRole.STAFF: [
        Permission.VIEW_OWN_SHIFT,
        Permission.REQUEST_SHIFT
    ],
    UserRole.EVALUATOR: [
        Permission.VIEW_OWN_SHIFT,
        Permission.REQUEST_SHIFT,
        Permission.EVALUATE_STAFF,
        Permission.VIEW_ALL_SHIFTS
    ],
    UserRole.SUB_MANAGER: [
        Permission.VIEW_OWN_SHIFT,
        Permission.REQUEST_SHIFT,
        Permission.VIEW_ALL_SHIFTS,
        Permission.CREATE_DRAFT_SHIFT,
        Permission.ADJUST_SHIFT,
        Permission.REJECT_SHIFT,
        Permission.VIEW_ANALYTICS
    ],
    UserRole.MANAGER: [
        # すべての権限
        Permission.VIEW_OWN_SHIFT,
        Permission.VIEW_ALL_SHIFTS,
        Permission.REQUEST_SHIFT,
        Permission.EVALUATE_STAFF,
        Permission.CREATE_DRAFT_SHIFT,
        Permission.ADJUST_SHIFT,
        Permission.APPROVE_SHIFT,
        Permission.PUBLISH_SHIFT,
        Permission.REJECT_SHIFT,
        Permission.VIEW_ANALYTICS
    ],
    UserRole.ADMIN: [
        # すべての権限
        Permission.VIEW_OWN_SHIFT,
        Permission.VIEW_ALL_SHIFTS,
        Permission.REQUEST_SHIFT,
        Permission.EVALUATE_STAFF,
        Permission.CREATE_DRAFT_SHIFT,
        Permission.ADJUST_SHIFT,
        Permission.APPROVE_SHIFT,
        Permission.PUBLISH_SHIFT,
        Permission.REJECT_SHIFT,
        Permission.VIEW_ANALYTICS
    ]
}


class User(Base):
    """ユーザーモデル"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    line_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.STAFF, index=True)
    email = Column(String(255), nullable=True)  # 任意: 緊急連絡用
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}', role={self.role.name})>"
    
    def has_permission(self, permission: Permission) -> bool:
        """指定された権限を持っているか確認"""
        return permission in ROLE_PERMISSIONS.get(self.role, [])
    
    def can_approve_shifts(self) -> bool:
        """シフト承認権限を持っているか"""
        return self.has_permission(Permission.APPROVE_SHIFT)
    
    def can_adjust_shifts(self) -> bool:
        """シフト調整権限を持っているか"""
        return self.has_permission(Permission.ADJUST_SHIFT)
    
    def can_view_all_shifts(self) -> bool:
        """全員のシフトを閲覧できるか"""
        return self.has_permission(Permission.VIEW_ALL_SHIFTS)
    
    def can_evaluate_staff(self) -> bool:
        """能力評価権限を持っているか"""
        return self.has_permission(Permission.EVALUATE_STAFF)
    
    def is_manager_or_above(self) -> bool:
        """マネージャー以上の権限を持っているか"""
        return self.role.value >= UserRole.SUB_MANAGER.value
    
    def to_dict(self):
        """辞書形式に変換（API返却用）"""
        return {
            'id': self.id,
            'line_id': self.line_id,
            'name': self.name,
            'role': self.role.name,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
