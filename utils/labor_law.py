"""
労働基準法チェックユーティリティ
シフト作成時に労働法違反がないか検証
"""
from datetime import datetime, timedelta, time
from typing import List, Dict, Optional
from config import Config


class LaborLawViolation:
    """労働法違反情報"""
    def __init__(self, user_id: int, user_name: str, violation_type: str, 
                 details: str, severity: str = "warning"):
        self.user_id = user_id
        self.user_name = user_name
        self.violation_type = violation_type
        self.details = details
        self.severity = severity  # "critical", "warning", "info"
    
    def __repr__(self):
        return f"<Violation({self.severity}): {self.violation_type} - {self.user_name}>"
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'user_name': self.user_name,
            'violation_type': self.violation_type,
            'details': self.details,
            'severity': self.severity
        }


class LaborLawChecker:
    """労働基準法チェッカー"""
    
    @staticmethod
    def check_daily_work_hours(shifts: List, user_id: int, user_name: str) -> Optional[LaborLawViolation]:
        """
        1日の労働時間チェック
        - 8時間超で要確認
        - 休憩時間の確保
        """
        user_shifts = [s for s in shifts if s.user_id == user_id]
        
        # 日付ごとにグループ化
        daily_hours = {}
        for shift in user_shifts:
            date_key = shift.date
            if date_key not in daily_hours:
                daily_hours[date_key] = 0
            daily_hours[date_key] += shift.get_duration_hours()
        
        # 違反チェック
        for date, hours in daily_hours.items():
            if hours > Config.MAX_WORK_HOURS_PER_DAY:
                return LaborLawViolation(
                    user_id=user_id,
                    user_name=user_name,
                    violation_type="daily_hours_exceeded",
                    details=f"{date}: {hours:.1f}時間（上限{Config.MAX_WORK_HOURS_PER_DAY}時間）",
                    severity="critical"
                )
        
        return None
    
    @staticmethod
    def check_weekly_work_hours(shifts: List, user_id: int, user_name: str) -> Optional[LaborLawViolation]:
        """
        週の労働時間チェック
        - 40時間超で要確認
        """
        user_shifts = [s for s in shifts if s.user_id == user_id]
        
        # 週ごとにグループ化
        weekly_hours = {}
        for shift in user_shifts:
            # ISO週番号を使用
            week_key = f"{shift.date.year}-W{shift.date.isocalendar()[1]}"
            if week_key not in weekly_hours:
                weekly_hours[week_key] = 0
            weekly_hours[week_key] += shift.get_duration_hours()
        
        # 違反チェック
        for week, hours in weekly_hours.items():
            if hours > Config.MAX_WORK_HOURS_PER_WEEK:
                return LaborLawViolation(
                    user_id=user_id,
                    user_name=user_name,
                    violation_type="weekly_hours_exceeded",
                    details=f"{week}: {hours:.1f}時間（上限{Config.MAX_WORK_HOURS_PER_WEEK}時間）",
                    severity="critical"
                )
        
        return None
    
    @staticmethod
    def check_rest_time(shift) -> Optional[LaborLawViolation]:
        """
        休憩時間チェック
        - 6時間超: 45分以上の休憩
        - 8時間超: 60分以上の休憩
        
        注意: このバージョンでは休憩時間を別途記録していないため、
              勤務時間から推定。将来的には休憩時間フィールドを追加推奨。
        """
        duration = shift.get_duration_hours()
        
        # 6時間超で45分休憩必要
        if 6 < duration <= 8:
            # 実際の休憩時間が記録されていない場合は警告のみ
            return LaborLawViolation(
                user_id=shift.user_id,
                user_name=shift.user.name if shift.user else "不明",
                violation_type="rest_time_required",
                details=f"{shift.date}: {duration:.1f}時間勤務（45分以上の休憩が必要）",
                severity="warning"
            )
        elif duration > 8:
            return LaborLawViolation(
                user_id=shift.user_id,
                user_name=shift.user.name if shift.user else "不明",
                violation_type="rest_time_required",
                details=f"{shift.date}: {duration:.1f}時間勤務（60分以上の休憩が必要）",
                severity="warning"
            )
        
        return None
    
    @staticmethod
    def check_consecutive_work_days(shifts: List, user_id: int, user_name: str) -> Optional[LaborLawViolation]:
        """
        連続勤務日数チェック
        - 6日連続勤務で要確認（7日目は休日）
        """
        user_shifts = [s for s in shifts if s.user_id == user_id]
        
        # 日付でソート
        sorted_shifts = sorted(user_shifts, key=lambda s: s.date)
        
        if not sorted_shifts:
            return None
        
        consecutive_days = 1
        prev_date = sorted_shifts[0].date
        
        for shift in sorted_shifts[1:]:
            if shift.date == prev_date + timedelta(days=1):
                consecutive_days += 1
                
                if consecutive_days > Config.MAX_CONSECUTIVE_WORK_DAYS:
                    return LaborLawViolation(
                        user_id=user_id,
                        user_name=user_name,
                        violation_type="consecutive_days_exceeded",
                        details=f"{consecutive_days}日連続勤務（上限{Config.MAX_CONSECUTIVE_WORK_DAYS}日）",
                        severity="critical"
                    )
            else:
                consecutive_days = 1
            
            prev_date = shift.date
        
        return None
    
    @staticmethod
    def check_all_violations(shifts: List) -> List[LaborLawViolation]:
        """
        すべての労働法違反をチェック
        
        Args:
            shifts: チェック対象のシフトリスト
            
        Returns:
            違反情報のリスト
        """
        violations = []
        
        # ユーザーごとにチェック
        user_ids = set(shift.user_id for shift in shifts)
        
        for user_id in user_ids:
            user_shifts = [s for s in shifts if s.user_id == user_id]
            if not user_shifts:
                continue
            
            user_name = user_shifts[0].user.name if user_shifts[0].user else "不明"
            
            # 日次労働時間チェック
            violation = LaborLawChecker.check_daily_work_hours(shifts, user_id, user_name)
            if violation:
                violations.append(violation)
            
            # 週次労働時間チェック
            violation = LaborLawChecker.check_weekly_work_hours(shifts, user_id, user_name)
            if violation:
                violations.append(violation)
            
            # 連続勤務日数チェック
            violation = LaborLawChecker.check_consecutive_work_days(shifts, user_id, user_name)
            if violation:
                violations.append(violation)
        
        # 個別シフトの休憩時間チェック
        for shift in shifts:
            violation = LaborLawChecker.check_rest_time(shift)
            if violation:
                violations.append(violation)
        
        return violations
    
    @staticmethod
    def format_violations_for_display(violations: List[LaborLawViolation]) -> str:
        """
        違反情報を表示用にフォーマット
        """
        if not violations:
            return "✅ 労働法違反はありません"
        
        critical = [v for v in violations if v.severity == "critical"]
        warning = [v for v in violations if v.severity == "warning"]
        
        message = ""
        
        if critical:
            message += "🚨 **重大な違反**\n"
            for v in critical:
                message += f"  • {v.user_name}: {v.details}\n"
            message += "\n"
        
        if warning:
            message += "⚠️ **要確認事項**\n"
            for v in warning:
                message += f"  • {v.user_name}: {v.details}\n"
        
        return message.strip()


# 使用例:
# violations = LaborLawChecker.check_all_violations(shifts)
# if violations:
#     print(LaborLawChecker.format_violations_for_display(violations))
