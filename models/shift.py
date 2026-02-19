"""
シフトモデル
確定シフトと承認ワークフロー管理
"""
from enum import Enum
from datetime import datetime, time, date
from sqlalchemy import Column, Integer, String, Date, Time, DateTime, ForeignKey, Text, Enum as SQLEnum, Numeric
from sqlalchemy.orm import relationship
from db.database import Base


class ShiftStatus(Enum):
    """シフトステータス"""
    DRAFT = "draft"                    # 下書き（管理者のみ閲覧可）
    ADJUSTING = "adjusting"            # 調整中
    ADJUSTED = "adjusted"              # 調整完了
    PENDING = "pending"                # 承認待ち
    APPROVED = "approved"              # 承認済み（未公開）
    PUBLISHED = "published"            # 公開済み
    REJECTED = "rejected"              # 差し戻し


class Shift(Base):
    """シフトモデル"""
    __tablename__ = 'shifts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(String(50), nullable=False, index=True)  # シフト表グループID
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    status = Column(SQLEnum(ShiftStatus), nullable=False, default=ShiftStatus.DRAFT, index=True)
    version = Column(Integer, default=1, nullable=False)
    
    # Phase 2/3で使用予定
    required_skill_level = Column(Numeric(3, 2), nullable=True)  # 必要スキルレベル
    predicted_traffic = Column(Integer, nullable=True)           # 予測客数
    
    # 作成情報
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # 調整情報
    adjusted_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    adjusted_at = Column(DateTime, nullable=True)
    
    # 承認情報
    approved_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    # 公開情報
    published_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    published_at = Column(DateTime, nullable=True)
    
    # 差し戻し情報
    rejected_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # リレーションシップ
    user = relationship("User", foreign_keys=[user_id])
    creator = relationship("User", foreign_keys=[created_by])
    adjuster = relationship("User", foreign_keys=[adjusted_by])
    approver = relationship("User", foreign_keys=[approved_by])
    publisher = relationship("User", foreign_keys=[published_by])
    rejecter = relationship("User", foreign_keys=[rejected_by])
    
    def __repr__(self):
        return f"<Shift(id={self.id}, user_id={self.user_id}, date={self.date}, status={self.status.name})>"
    
    def can_publish(self) -> bool:
        """公開可能かチェック"""
        return self.status == ShiftStatus.APPROVED
    
    def can_edit(self) -> bool:
        """編集可能かチェック"""
        return self.status in [
            ShiftStatus.DRAFT,
            ShiftStatus.ADJUSTING,
            ShiftStatus.ADJUSTED
        ]
    
    def can_approve(self) -> bool:
        """承認可能かチェック"""
        return self.status in [ShiftStatus.ADJUSTED, ShiftStatus.PENDING]
    
    def can_reject(self) -> bool:
        """差し戻し可能かチェック"""
        return self.status in [
            ShiftStatus.ADJUSTING,
            ShiftStatus.ADJUSTED,
            ShiftStatus.PENDING,
            ShiftStatus.APPROVED
        ]
    
    def is_published(self) -> bool:
        """公開済みかチェック"""
        return self.status == ShiftStatus.PUBLISHED
    
    def get_duration_hours(self) -> float:
        """勤務時間を計算（時間単位）"""
        if not self.start_time or not self.end_time:
            return 0.0
        
        start_minutes = self.start_time.hour * 60 + self.start_time.minute
        end_minutes = self.end_time.hour * 60 + self.end_time.minute
        
        # 日をまたぐ場合の処理
        if end_minutes < start_minutes:
            end_minutes += 24 * 60
        
        duration_minutes = end_minutes - start_minutes
        return duration_minutes / 60.0
    
    def to_dict(self):
        """辞書形式に変換"""
        return {
            'id': self.id,
            'group_id': self.group_id,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else None,
            'date': self.date.isoformat() if self.date else None,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else None,
            'status': self.status.name,
            'duration_hours': self.get_duration_hours(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'published_at': self.published_at.isoformat() if self.published_at else None
        }
