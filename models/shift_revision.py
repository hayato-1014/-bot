"""
シフト変更履歴モデル
監査証跡とトレーサビリティのための変更履歴管理
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from db.database import Base


class ShiftRevision(Base):
    """シフト変更履歴モデル"""
    __tablename__ = 'shift_revisions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    shift_id = Column(Integer, ForeignKey('shifts.id'), nullable=False, index=True)
    field_name = Column(String(50), nullable=False)  # 変更されたフィールド名
    old_value = Column(Text, nullable=True)          # 変更前の値
    new_value = Column(Text, nullable=True)          # 変更後の値
    changed_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    change_reason = Column(Text, nullable=True)      # 変更理由
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # リレーションシップ
    shift = relationship("Shift", backref="revisions")
    changer = relationship("User")
    
    def __repr__(self):
        return f"<ShiftRevision(id={self.id}, shift_id={self.shift_id}, field={self.field_name})>"
    
    def to_dict(self):
        """辞書形式に変換"""
        return {
            'id': self.id,
            'shift_id': self.shift_id,
            'field_name': self.field_name,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'changed_by': self.changer.name if self.changer else None,
            'change_reason': self.change_reason,
            'changed_at': self.changed_at.isoformat() if self.changed_at else None
        }
    
    @staticmethod
    def create_revision(shift_id, field_name, old_value, new_value, changed_by, reason=None):
        """変更履歴を作成（ヘルパーメソッド）"""
        return ShiftRevision(
            shift_id=shift_id,
            field_name=field_name,
            old_value=str(old_value) if old_value is not None else None,
            new_value=str(new_value) if new_value is not None else None,
            changed_by=changed_by,
            change_reason=reason
        )
