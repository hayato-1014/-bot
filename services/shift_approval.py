"""
シフト承認ワークフローサービス
承認プロセス（下書き→調整→承認→公開）の管理
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from models.shift import Shift, ShiftStatus
from models.shift_revision import ShiftRevision
from models.user import User, Permission
from utils.audit_log import log_action
from db.database import DatabaseSession


class ShiftApprovalService:
    """シフト承認サービス"""
    
    @staticmethod
    def create_draft_shifts(shifts: List[Shift], admin_id: int) -> bool:
        """
        下書きシフトを作成
        
        Args:
            shifts: シフトリスト
            admin_id: 作成者ID
            
        Returns:
            成功したらTrue
        """
        try:
            with DatabaseSession() as session:
                for shift in shifts:
                    shift.status = ShiftStatus.DRAFT
                    shift.created_by = admin_id
                    shift.created_at = datetime.now()
                    session.add(shift)
                
                session.commit()
                
                # 監査ログ
                log_action(
                    action='CREATE_DRAFT_SHIFTS',
                    actor_id=admin_id,
                    resource_type='SHIFT',
                    data_accessed=f'{len(shifts)} shifts created',
                    result='SUCCESS'
                )
                
                return True
        except Exception as e:
            log_action(
                action='CREATE_DRAFT_SHIFTS',
                actor_id=admin_id,
                result='FAILURE',
                error_message=str(e)
            )
            return False
    
    @staticmethod
    def get_draft_shifts(group_id: str, admin: User) -> Optional[List[Shift]]:
        """
        下書きシフトを取得（管理者のみ）
        
        Args:
            group_id: シフトグループID
            admin: 管理者ユーザー
            
        Returns:
            シフトリスト
        """
        if not admin.can_adjust_shifts():
            return None
        
        with DatabaseSession() as session:
            shifts = session.query(Shift)\
                .filter(
                    Shift.group_id == group_id,
                    Shift.status.in_([
                        ShiftStatus.DRAFT,
                        ShiftStatus.ADJUSTING,
                        ShiftStatus.ADJUSTED
                    ])
                )\
                .all()
            
            return shifts
    
    @staticmethod
    def start_adjustment(group_id: str, admin_id: int) -> bool:
        """
        調整モード開始
        
        Args:
            group_id: シフトグループID
            admin_id: 管理者ID
            
        Returns:
            成功したらTrue
        """
        try:
            with DatabaseSession() as session:
                shifts = session.query(Shift)\
                    .filter(
                        Shift.group_id == group_id,
                        Shift.status == ShiftStatus.DRAFT
                    )\
                    .all()
                
                for shift in shifts:
                    shift.status = ShiftStatus.ADJUSTING
                
                session.commit()
                
                log_action(
                    action='START_ADJUSTMENT',
                    actor_id=admin_id,
                    resource_type='SHIFT',
                    data_accessed=f'group_id={group_id}',
                    result='SUCCESS'
                )
                
                return True
        except Exception as e:
            log_action(
                action='START_ADJUSTMENT',
                actor_id=admin_id,
                result='FAILURE',
                error_message=str(e)
            )
            return False
    
    @staticmethod
    def adjust_shift(shift_id: int, new_data: dict, admin_id: int, 
                    reason: Optional[str] = None) -> bool:
        """
        シフトを調整
        
        Args:
            shift_id: シフトID
            new_data: 新しいデータ（user_id, start_time, end_time等）
            admin_id: 管理者ID
            reason: 変更理由
            
        Returns:
            成功したらTrue
        """
        try:
            with DatabaseSession() as session:
                shift = session.query(Shift).filter(Shift.id == shift_id).first()
                
                if not shift or not shift.can_edit():
                    return False
                
                # 変更履歴を記録
                revisions = []
                
                if 'user_id' in new_data and new_data['user_id'] != shift.user_id:
                    revisions.append(ShiftRevision.create_revision(
                        shift_id=shift_id,
                        field_name='user_id',
                        old_value=shift.user_id,
                        new_value=new_data['user_id'],
                        changed_by=admin_id,
                        reason=reason
                    ))
                    shift.user_id = new_data['user_id']
                
                if 'start_time' in new_data and new_data['start_time'] != shift.start_time:
                    revisions.append(ShiftRevision.create_revision(
                        shift_id=shift_id,
                        field_name='start_time',
                        old_value=shift.start_time,
                        new_value=new_data['start_time'],
                        changed_by=admin_id,
                        reason=reason
                    ))
                    shift.start_time = new_data['start_time']
                
                if 'end_time' in new_data and new_data['end_time'] != shift.end_time:
                    revisions.append(ShiftRevision.create_revision(
                        shift_id=shift_id,
                        field_name='end_time',
                        old_value=shift.end_time,
                        new_value=new_data['end_time'],
                        changed_by=admin_id,
                        reason=reason
                    ))
                    shift.end_time = new_data['end_time']
                
                # 調整情報を更新
                shift.adjusted_by = admin_id
                shift.adjusted_at = datetime.now()
                shift.status = ShiftStatus.ADJUSTED
                shift.version += 1
                
                # 変更履歴を保存
                for revision in revisions:
                    session.add(revision)
                
                session.commit()
                
                log_action(
                    action='ADJUST_SHIFT',
                    actor_id=admin_id,
                    resource_type='SHIFT',
                    resource_id=shift_id,
                    data_accessed=f'{len(revisions)} fields changed',
                    result='SUCCESS'
                )
                
                return True
        except Exception as e:
            log_action(
                action='ADJUST_SHIFT',
                actor_id=admin_id,
                result='FAILURE',
                error_message=str(e)
            )
            return False
    
    @staticmethod
    def approve_shifts(group_id: str, approver_id: int) -> bool:
        """
        シフトを承認
        
        Args:
            group_id: シフトグループID
            approver_id: 承認者ID
            
        Returns:
            成功したらTrue
        """
        try:
            with DatabaseSession() as session:
                shifts = session.query(Shift)\
                    .filter(
                        Shift.group_id == group_id,
                        Shift.status.in_([ShiftStatus.ADJUSTED, ShiftStatus.PENDING])
                    )\
                    .all()
                
                for shift in shifts:
                    shift.status = ShiftStatus.APPROVED
                    shift.approved_by = approver_id
                    shift.approved_at = datetime.now()
                
                session.commit()
                
                log_action(
                    action='APPROVE_SHIFTS',
                    actor_id=approver_id,
                    resource_type='SHIFT',
                    data_accessed=f'{len(shifts)} shifts approved',
                    result='SUCCESS'
                )
                
                return True
        except Exception as e:
            log_action(
                action='APPROVE_SHIFTS',
                actor_id=approver_id,
                result='FAILURE',
                error_message=str(e)
            )
            return False
    
    @staticmethod
    def publish_shifts(group_id: str, publisher_id: int) -> bool:
        """
        シフトを公開
        
        Args:
            group_id: シフトグループID
            publisher_id: 公開者ID
            
        Returns:
            成功したらTrue
        """
        try:
            with DatabaseSession() as session:
                shifts = session.query(Shift)\
                    .filter(
                        Shift.group_id == group_id,
                        Shift.status == ShiftStatus.APPROVED
                    )\
                    .all()
                
                for shift in shifts:
                    shift.status = ShiftStatus.PUBLISHED
                    shift.published_by = publisher_id
                    shift.published_at = datetime.now()
                
                session.commit()
                
                log_action(
                    action='PUBLISH_SHIFTS',
                    actor_id=publisher_id,
                    resource_type='SHIFT',
                    data_accessed=f'{len(shifts)} shifts published',
                    result='SUCCESS'
                )
                
                return True
        except Exception as e:
            log_action(
                action='PUBLISH_SHIFTS',
                actor_id=publisher_id,
                result='FAILURE',
                error_message=str(e)
            )
            return False
    
    @staticmethod
    def reject_shifts(group_id: str, rejecter_id: int, reason: str) -> bool:
        """
        シフトを差し戻し
        
        Args:
            group_id: シフトグループID
            rejecter_id: 差し戻し者ID
            reason: 差し戻し理由
            
        Returns:
            成功したらTrue
        """
        try:
            with DatabaseSession() as session:
                shifts = session.query(Shift)\
                    .filter(
                        Shift.group_id == group_id,
                        Shift.status.in_([
                            ShiftStatus.ADJUSTED,
                            ShiftStatus.PENDING,
                            ShiftStatus.APPROVED
                        ])
                    )\
                    .all()
                
                for shift in shifts:
                    shift.status = ShiftStatus.DRAFT
                    shift.rejected_by = rejecter_id
                    shift.rejected_at = datetime.now()
                    shift.rejection_reason = reason
                
                session.commit()
                
                log_action(
                    action='REJECT_SHIFTS',
                    actor_id=rejecter_id,
                    resource_type='SHIFT',
                    data_accessed=f'{len(shifts)} shifts rejected: {reason}',
                    result='SUCCESS'
                )
                
                return True
        except Exception as e:
            log_action(
                action='REJECT_SHIFTS',
                actor_id=rejecter_id,
                result='FAILURE',
                error_message=str(e)
            )
            return False
    
    @staticmethod
    def get_published_shifts_for_user(user_id: int, start_date, end_date) -> List[Shift]:
        """
        公開済みシフトを取得（スタッフ用）
        
        Args:
            user_id: ユーザーID
            start_date: 開始日
            end_date: 終了日
            
        Returns:
            シフトリスト
        """
        with DatabaseSession() as session:
            shifts = session.query(Shift)\
                .filter(
                    Shift.user_id == user_id,
                    Shift.status == ShiftStatus.PUBLISHED,
                    Shift.date >= start_date,
                    Shift.date <= end_date
                )\
                .order_by(Shift.date, Shift.start_time)\
                .all()
            
            return shifts
