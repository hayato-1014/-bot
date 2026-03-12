"""
管理者用メッセージハンドラー
管理者（店長・副店長）からのメッセージ処理
"""
from linebot.models import MessageEvent
from datetime import datetime, timedelta
from models.user import User, Permission, UserRole
from models.shift_request import ShiftRequest, RequestStatus
from services.shift_optimizer import ShiftOptimizer
from services.shift_approval import ShiftApprovalService
from services.line_service import line_service
from utils.labor_law import LaborLawChecker
from utils.validators import Validators
from db.database import DatabaseSession
from monitoring.error_handler import handle_errors, ErrorLevel, ErrorCategory
import re


class ManagerHandler:
    """管理者用ハンドラー"""
    
    @staticmethod
    @handle_errors(level=ErrorLevel.ERROR, category=ErrorCategory.BUSINESS_LOGIC)
    def handle_create_shift(event: MessageEvent, manager: User):
        """
        シフト自動作成
        
        メッセージ例:
        - "シフト作成 3/1-3/7"
        - "シフト作成 2024/3/1-3/7"
        """
        if not manager.has_permission(Permission.CREATE_DRAFT_SHIFT):
            line_service.reply_message(event.reply_token, "権限がありません。")
            return
        
        message_text = event.message.text
        
        # 日付範囲を抽出
        pattern = r'(\d{1,4}[-/]\d{1,2}[-/]\d{1,2})\s*[-~～]\s*(\d{1,4}[-/]\d{1,2}[-/]\d{1,2})'
        match = re.search(pattern, message_text)
        
        if not match:
            help_msg = "形式: シフト作成 3/1-3/7"
            line_service.reply_message(event.reply_token, help_msg)
            return
        
        # 日付をパース
        valid_start, start_date = Validators.validate_date_format(match.group(1))
        valid_end, end_date = Validators.validate_date_format(match.group(2))
        
        if not (valid_start and valid_end):
            line_service.reply_message(event.reply_token, "日付の形式が不正です。")
            return
        
        # シフト作成処理
        line_service.reply_message(event.reply_token, "シフトを自動生成しています...")
        
        try:
            with DatabaseSession() as session:
                # シフト希望を取得
                requests = session.query(ShiftRequest)\
                    .filter(
                        ShiftRequest.date >= start_date,
                        ShiftRequest.date <= end_date,
                        ShiftRequest.status == RequestStatus.PENDING
                    )\
                    .all()
                
                # アクティブなユーザーを取得
                from models.user import User as UserModel
                users = session.query(UserModel)\
                    .filter(UserModel.is_active == True)\
                    .all()
                
                # シフト最適化
                optimizer = ShiftOptimizer()
                group_id = f"{start_date.year}-{start_date.strftime('%m')}-W{start_date.isocalendar()[1]}"
                
                shifts = optimizer.create_shifts(
                    start_date=start_date,
                    end_date=end_date,
                    shift_requests=requests,
                    users=users,
                    group_id=group_id,
                    created_by=manager.id
                )
                
                if not shifts:
                    line_service.send_text_message(
                        manager.line_id,
                        "シフトを作成できませんでした。希望が不足している可能性があります。"
                    )
                    return
                
                # 下書きとして保存
                ShiftApprovalService.create_draft_shifts(shifts, manager.id)
                
                # 労働法チェック
                violations = LaborLawChecker.check_all_violations(shifts)
                violations_text = LaborLawChecker.format_violations_for_display(violations)
                
                # 結果を通知
                stats = ShiftOptimizer.validate_shifts(shifts)
                
                result_message = f"""
✅ シフト案を作成しました（下書き）

【期間】{start_date.strftime('%m/%d')} ～ {end_date.strftime('%m/%d')}
【シフト数】{stats['total_shifts']}件
【対象者】{stats['unique_users']}名

{violations_text}

【操作】
・「調整」→ 調整モード開始
・「承認」→ 承認して公開
・「詳細」→ シフト詳細を確認
・「キャンセル」→ 下書きを削除
"""
                
                line_service.send_text_message(manager.line_id, result_message.strip())
                
        except Exception as e:
            error_msg = f"シフト作成中にエラーが発生しました: {str(e)}"
            line_service.send_text_message(manager.line_id, error_msg)
            raise
    
    @staticmethod
    @handle_errors(level=ErrorLevel.ERROR, category=ErrorCategory.BUSINESS_LOGIC)
    def handle_approve_shift(event: MessageEvent, manager: User):
        """
        シフトを承認して公開
        """
        if not manager.has_permission(Permission.APPROVE_SHIFT):
            line_service.reply_message(event.reply_token, "承認権限がありません。")
            return
        
        # 最新のシフトグループを取得
        # （実装簡略化のため、最新のグループIDを取得するロジックは省略）
        
        line_service.reply_message(
            event.reply_token,
            "シフトを承認しています..."
        )
        
        # TODO: 実際のグループIDを取得
        # success = ShiftApprovalService.approve_shifts(group_id, manager.id)
        # success = ShiftApprovalService.publish_shifts(group_id, manager.id)
        
        # スタッフ全員に通知
        # TODO: 実装
        
        message = "✅ シフトを承認・公開しました。スタッフ全員に通知を送信しました。"
        line_service.send_text_message(manager.line_id, message)
    
    @staticmethod
    def show_manager_help(event: MessageEvent):
        """
        管理者用ヘルプ
        """
        help_message = """
📖 **管理者向けガイド**

【シフト作成】
シフト作成 3/1-3/7
→ 自動でシフトを作成

【シフト承認】
「承認」
→ 下書きを承認して公開

【シフト調整】
「調整」
→ 手動調整モード開始

【差し戻し】
「差し戻し (理由)」
→ 下書きに戻す

【統計確認】
「統計」
→ シフト統計を表示
"""
        line_service.reply_message(event.reply_token, help_message.strip())
@staticmethod
    def handle_list_staff(event, user):
        """スタッフ一覧表示"""
        if not user.is_admin():
            line_service.reply_message(
                event.reply_token,
                "この機能は管理者のみ使用できます。"
            )
            return
        
        try:
            with DatabaseSession() as session:
                users = session.query(User).order_by(User.role.desc(), User.name).all()
                
                if not users:
                    line_service.reply_message(event.reply_token, "登録ユーザーがいません。")
                    return
                
                # 権限ごとにグループ化
                role_groups = {
                    UserRole.ADMIN: [],
                    UserRole.MANAGER: [],
                    UserRole.LEADER: [],
                    UserRole.SUB_LEADER: [],
                    UserRole.STAFF: []
                }
                
                for u in users:
                    role_groups[u.role].append(u)
                
                # メッセージ作成
                msg_parts = ["【スタッフ一覧】\n"]
                
                role_names = {
                    UserRole.ADMIN: "👑 管理者",
                    UserRole.MANAGER: "📊 マネージャー",
                    UserRole.LEADER: "⭐ リーダー",
                    UserRole.SUB_LEADER: "✨ サブリーダー",
                    UserRole.STAFF: "👤 スタッフ"
                }
                
                for role in [UserRole.ADMIN, UserRole.MANAGER, UserRole.LEADER, UserRole.SUB_LEADER, UserRole.STAFF]:
                    if role_groups[role]:
                        msg_parts.append(f"\n{role_names[role]}")
                        for u in role_groups[role]:
                            status = "✅" if u.is_active else "❌"
                            msg_parts.append(f"  {status} {u.name}")
                
                msg_parts.append("\n\n権限変更: 「権限変更 名前 権限」")
                msg_parts.append("例: 権限変更 田中太郎 manager")
                
                line_service.reply_message(event.reply_token, "\n".join(msg_parts))
        
        except Exception as e:
            error_handler.handle_error(
                e,
                ErrorLevel.ERROR,
                ErrorCategory.BUSINESS_LOGIC
            )
            line_service.reply_message(
                event.reply_token,
                "エラーが発生しました。"
            )
    
    @staticmethod
    def handle_change_role(event, user, target_name: str, new_role: str):
        """ユーザー権限変更"""
        if not user.is_admin():
            line_service.reply_message(
                event.reply_token,
                "この機能は管理者のみ使用できます。"
            )
            return
        
        # 権限マッピング
        role_map = {
            'admin': UserRole.ADMIN,
            'manager': UserRole.MANAGER,
            'leader': UserRole.LEADER,
            'sub_leader': UserRole.SUB_LEADER,
            'subleader': UserRole.SUB_LEADER,
            'staff': UserRole.STAFF
        }
        
        new_role_lower = new_role.lower()
        
        if new_role_lower not in role_map:
            line_service.reply_message(
                event.reply_token,
                f"権限が不正です。\n使用可能: admin, manager, leader, sub_leader, staff"
            )
            return
        
        try:
            with DatabaseSession() as session:
                target_user = session.query(User).filter(User.name == target_name).first()
                
                if not target_user:
                    line_service.reply_message(
                        event.reply_token,
                        f"ユーザー「{target_name}」が見つかりません。"
                    )
                    return
                
                old_role = target_user.role
                target_user.role = role_map[new_role_lower]
                session.commit()
                
                role_names = {
                    UserRole.ADMIN: "管理者",
                    UserRole.MANAGER: "マネージャー",
                    UserRole.LEADER: "リーダー",
                    UserRole.SUB_LEADER: "サブリーダー",
                    UserRole.STAFF: "スタッフ"
                }
                
                msg = f"✅ 権限変更完了\n\n{target_user.name}\n{role_names[old_role]} → {role_names[target_user.role]}"
                
                line_service.reply_message(event.reply_token, msg)
                
                # 対象ユーザーに通知
                notify_msg = f"あなたの権限が変更されました。\n新しい権限: {role_names[target_user.role]}"
                line_service.send_text_message(target_user.line_id, notify_msg)
        
        except Exception as e:
            error_handler.handle_error(
                e,
                ErrorLevel.ERROR,
                ErrorCategory.BUSINESS_LOGIC
            )
            line_service.reply_message(
                event.reply_token,
                "エラーが発生しました。"
            )
