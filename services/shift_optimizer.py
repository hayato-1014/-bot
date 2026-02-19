"""
シフト最適化サービス
PuLPを使用した線形計画法によるシフト自動作成
"""
from datetime import datetime, timedelta, time
from typing import List, Dict, Optional
import pulp
from models.shift import Shift, ShiftStatus
from models.shift_request import ShiftRequest, RequestStatus
from models.user import User
from config import Config
from utils.labor_law import LaborLawChecker


class ShiftOptimizer:
    """シフト最適化クラス"""
    
    def __init__(self):
        self.solver = pulp.PULP_CBC_CMD(msg=0)  # メッセージ非表示
    
    def create_shifts(self, 
                     start_date: datetime.date,
                     end_date: datetime.date,
                     shift_requests: List[ShiftRequest],
                     users: List[User],
                     group_id: str,
                     created_by: int) -> List[Shift]:
        """
        シフトを自動作成
        
        Args:
            start_date: 開始日
            end_date: 終了日
            shift_requests: シフト希望リスト
            users: ユーザーリスト
            group_id: シフトグループID
            created_by: 作成者ID
            
        Returns:
            作成されたシフトリスト
        """
        # 問題の定義
        prob = pulp.LpProblem("ShiftScheduling", pulp.LpMaximize)
        
        # 日付範囲を生成
        date_range = self._generate_date_range(start_date, end_date)
        
        # 決定変数: shift_vars[user_id][date][request_id] = 0 or 1
        shift_vars = {}
        
        # 目的関数の係数
        objective_coefficients = []
        
        for user in users:
            if not user.is_active:
                continue
            
            shift_vars[user.id] = {}
            user_requests = [r for r in shift_requests if r.user_id == user.id]
            
            for date in date_range:
                shift_vars[user.id][date] = {}
                date_requests = [r for r in user_requests if r.date == date]
                
                for request in date_requests:
                    # 決定変数作成
                    var_name = f"shift_u{user.id}_d{date}_r{request.id}"
                    var = pulp.LpVariable(var_name, cat='Binary')
                    shift_vars[user.id][date][request.id] = var
                    
                    # 優先度に応じた重み付け（優先度が高いほど係数大）
                    weight = 4 - request.priority  # priority 1 → weight 3
                    objective_coefficients.append(weight * var)
        
        # 目的関数: シフト希望の充足度を最大化
        prob += pulp.lpSum(objective_coefficients), "TotalSatisfaction"
        
        # 制約条件1: 各日の最小・最大人数
        for date in date_range:
            daily_workers = []
            for user_id in shift_vars:
                if date in shift_vars[user_id]:
                    daily_workers.extend(shift_vars[user_id][date].values())
            
            if daily_workers:
                # 最小人数制約
                prob += (
                    pulp.lpSum(daily_workers) >= Config.MIN_STAFF_PER_SHIFT,
                    f"MinStaff_{date}"
                )
                # 最大人数制約
                prob += (
                    pulp.lpSum(daily_workers) <= Config.MAX_STAFF_PER_SHIFT,
                    f"MaxStaff_{date}"
                )
        
        # 制約条件2: 1人1日1シフトまで
        for user_id in shift_vars:
            for date in shift_vars[user_id]:
                prob += (
                    pulp.lpSum(shift_vars[user_id][date].values()) <= 1,
                    f"OneShiftPerDay_u{user_id}_d{date}"
                )
        
        # 制約条件3: 週の労働時間上限（簡易版）
        # 注意: より正確には時間単位で計算すべき
        for user_id in shift_vars:
            for week_start in self._get_week_starts(date_range):
                week_dates = [week_start + timedelta(days=i) for i in range(7)]
                week_shifts = []
                
                for date in week_dates:
                    if date in shift_vars.get(user_id, {}):
                        week_shifts.extend(shift_vars[user_id][date].values())
                
                if week_shifts:
                    # 1日8時間と仮定して週40時間 = 5日まで
                    max_days = Config.MAX_WORK_HOURS_PER_WEEK // 8
                    prob += (
                        pulp.lpSum(week_shifts) <= max_days,
                        f"WeeklyHours_u{user_id}_w{week_start}"
                    )
        
        # 問題を解く
        prob.solve(self.solver)
        
        # 結果を取得
        created_shifts = []
        
        if prob.status == pulp.LpStatusOptimal:
            for user_id in shift_vars:
                for date in shift_vars[user_id]:
                    for request_id, var in shift_vars[user_id][date].items():
                        if pulp.value(var) == 1:
                            # このリクエストが採用された
                            request = next(r for r in shift_requests if r.id == request_id)
                            
                            shift = Shift(
                                group_id=group_id,
                                user_id=user_id,
                                date=date,
                                start_time=request.start_time,
                                end_time=request.end_time,
                                status=ShiftStatus.DRAFT,
                                created_by=created_by,
                                created_at=datetime.now()
                            )
                            created_shifts.append(shift)
        
        return created_shifts
    
    def _generate_date_range(self, start_date, end_date):
        """日付範囲を生成"""
        dates = []
        current = start_date
        while current <= end_date:
            dates.append(current)
            current += timedelta(days=1)
        return dates
    
    def _get_week_starts(self, date_range):
        """週の開始日リストを取得（月曜日基準）"""
        if not date_range:
            return []
        
        week_starts = []
        current = date_range[0]
        
        # 最初の月曜日を見つける
        while current.weekday() != 0:  # 0 = Monday
            current -= timedelta(days=1)
        
        while current <= date_range[-1]:
            week_starts.append(current)
            current += timedelta(days=7)
        
        return week_starts
    
    @staticmethod
    def validate_shifts(shifts: List[Shift]) -> Dict:
        """
        作成されたシフトの検証
        
        Returns:
            検証結果の辞書
        """
        # 労働法チェック
        violations = LaborLawChecker.check_all_violations(shifts)
        
        # 統計情報
        stats = {
            'total_shifts': len(shifts),
            'unique_users': len(set(s.user_id for s in shifts)),
            'date_range': {
                'start': min(s.date for s in shifts) if shifts else None,
                'end': max(s.date for s in shifts) if shifts else None
            },
            'violations': [v.to_dict() for v in violations]
        }
        
        return stats


# 使用例:
# optimizer = ShiftOptimizer()
# shifts = optimizer.create_shifts(
#     start_date=datetime(2024, 3, 1).date(),
#     end_date=datetime(2024, 3, 7).date(),
#     shift_requests=requests,
#     users=active_users,
#     group_id='2024-03-W09',
#     created_by=manager_id
# )
# validation_result = ShiftOptimizer.validate_shifts(shifts)
