"""
シフト希望モデル
スタッフからのシフト希望提出を管理
"""
from enum import Enum
from datetime import datetime
from sqlalchemy import Column, Integer, Date, Time, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from db.database import Base


class RequestStatus(Enum):
    """シフト希望のステータス"""
    PENDING = "pending"      # 受付済み（未処理）
    ACCEPTED = "accepted"    # 採用された
    REJECTED = "rejected"    # 不採用
    CANCELLED = "cancelled"  # スタッフがキャンセル


class ShiftRequest(Base):
    """シフト希望モデル"""
    __tablename__ = 'shift_requests'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    priority = Column(Integer, default=1, nullable=False)  # 1:希望, 2:できれば, 3:可能なら
    status = Column(SQLEnum(RequestStatus), default=RequestStatus.PENDING, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # リレーションシップ
    user = relationship("User", backref="shift_requests")
    
    def __repr__(self):
        return f"<ShiftRequest(id={self.id}, user_id={self.user_id}, date={self.date}, status={self.status.name})>"
    
    def is_pending(self) -> bool:
        """未処理かどうか"""
        return self.status == RequestStatus.PENDING
    
    def is_accepted(self) -> bool:
        """採用されたかどうか"""
        return self.status == RequestStatus.ACCEPTED
    
    def get_duration_hours(self) -> float:
        """希望勤務時間を計算（時間単位）"""
        if not self.start_time or not self.end_time:
            return 0.0
        
        start_minutes = self.start_time.hour * 60 + self.start_time.minute
        end_minutes = self.end_time.hour * 60 + self.end_time.minute
        
        if end_minutes < start_minutes:
            end_minutes += 24 * 60
        
        duration_minutes = end_minutes - start_minutes
        return duration_minutes / 60.0
    
    def get_priority_label(self) -> str:
        """優先度ラベルを取得"""
        labels = {
            1: "希望",
            2: "できれば",
            3: "可能なら"
        }
        return labels.get(self.priority, "不明")
    
    def to_dict(self):
        """辞書形式に変換"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else None,
            'date': self.date.isoformat() if self.date else None,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else None,
            'priority': self.priority,
            'priority_label': self.get_priority_label(),
            'status': self.status.name,
            'duration_hours': self.get_duration_hours(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
