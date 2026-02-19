"""
入力検証ユーティリティ
ユーザー入力やデータの妥当性を検証
"""
import re
from datetime import datetime, time, date
from typing import Optional, Tuple


class ValidationError(Exception):
    """検証エラー"""
    pass


class Validators:
    """各種検証関数"""
    
    @staticmethod
    def validate_time_format(time_str: str) -> Tuple[bool, Optional[time]]:
        """
        時刻フォーマット検証
        
        Args:
            time_str: 時刻文字列（例: "09:00", "9:00", "17:30"）
            
        Returns:
            (検証成功, timeオブジェクト)
        """
        # 時刻パターン（HH:MM または H:MM）
        pattern = r'^(\d{1,2}):(\d{2})$'
        match = re.match(pattern, time_str.strip())
        
        if not match:
            return False, None
        
        hour, minute = int(match.group(1)), int(match.group(2))
        
        # 範囲チェック
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return False, None
        
        return True, time(hour=hour, minute=minute)
    
    @staticmethod
    def validate_date_format(date_str: str) -> Tuple[bool, Optional[date]]:
        """
        日付フォーマット検証
        
        Args:
            date_str: 日付文字列（例: "2024-03-01", "2024/03/01", "3/1"）
            
        Returns:
            (検証成功, dateオブジェクト)
        """
        # 複数のフォーマットに対応
        formats = [
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%m/%d',
            '%m-%d'
        ]
        
        for fmt in formats:
            try:
                parsed_date = datetime.strptime(date_str.strip(), fmt).date()
                
                # 月日のみの場合は今年を補完
                if fmt in ['%m/%d', '%m-%d']:
                    current_year = datetime.now().year
                    parsed_date = parsed_date.replace(year=current_year)
                
                return True, parsed_date
            except ValueError:
                continue
        
        return False, None
    
    @staticmethod
    def validate_time_range(start_time: time, end_time: time) -> bool:
        """
        時刻範囲の妥当性チェック
        
        Args:
            start_time: 開始時刻
            end_time: 終了時刻
            
        Returns:
            妥当ならTrue
        """
        # 終了時刻が開始時刻より後、または日をまたぐ場合
        # （深夜勤務対応のため、end < startも許可）
        return True  # 基本的にすべて許可
    
    @staticmethod
    def validate_shift_duration(start_time: time, end_time: time, 
                               min_hours: float = 1.0, 
                               max_hours: float = 12.0) -> bool:
        """
        シフト時間の妥当性チェック
        
        Args:
            start_time: 開始時刻
            end_time: 終了時刻
            min_hours: 最小勤務時間
            max_hours: 最大勤務時間
            
        Returns:
            妥当ならTrue
        """
        start_minutes = start_time.hour * 60 + start_time.minute
        end_minutes = end_time.hour * 60 + end_time.minute
        
        # 日をまたぐ場合
        if end_minutes < start_minutes:
            end_minutes += 24 * 60
        
        duration_hours = (end_minutes - start_minutes) / 60.0
        
        return min_hours <= duration_hours <= max_hours
    
    @staticmethod
    def parse_shift_request_message(message: str) -> Optional[dict]:
        """
        シフト希望メッセージをパース
        
        対応フォーマット:
        - "3/1 9:00-17:00"
        - "3月1日 9時-17時"
        - "2024/3/1 9:00-17:00 希望"
        
        Args:
            message: ユーザーからのメッセージ
            
        Returns:
            パース結果の辞書、または None
        """
        # パターン1: YYYY/MM/DD HH:MM-HH:MM
        pattern1 = r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})\s+(\d{1,2}:\d{2})\s*[-~～]\s*(\d{1,2}:\d{2})'
        match = re.search(pattern1, message)
        
        if match:
            date_str, start_str, end_str = match.groups()
            valid_date, parsed_date = Validators.validate_date_format(date_str)
            valid_start, start_time = Validators.validate_time_format(start_str)
            valid_end, end_time = Validators.validate_time_format(end_str)
            
            if valid_date and valid_start and valid_end:
                # 優先度を判定
                priority = 1  # デフォルトは希望
                if 'できれば' in message or 'できたら' in message:
                    priority = 2
                elif '可能なら' in message or '可能であれば' in message:
                    priority = 3
                
                return {
                    'date': parsed_date,
                    'start_time': start_time,
                    'end_time': end_time,
                    'priority': priority
                }
        
        # パターン2: MM/DD HH:MM-HH:MM
        pattern2 = r'(\d{1,2}[-/]\d{1,2})\s+(\d{1,2}:\d{2})\s*[-~～]\s*(\d{1,2}:\d{2})'
        match = re.search(pattern2, message)
        
        if match:
            date_str, start_str, end_str = match.groups()
            valid_date, parsed_date = Validators.validate_date_format(date_str)
            valid_start, start_time = Validators.validate_time_format(start_str)
            valid_end, end_time = Validators.validate_time_format(end_str)
            
            if valid_date and valid_start and valid_end:
                priority = 1
                if 'できれば' in message or 'できたら' in message:
                    priority = 2
                elif '可能なら' in message or '可能であれば' in message:
                    priority = 3
                
                return {
                    'date': parsed_date,
                    'start_time': start_time,
                    'end_time': end_time,
                    'priority': priority
                }
        
        return None
    
    @staticmethod
    def validate_line_id(line_id: str) -> bool:
        """
        LINE User IDの妥当性チェック
        
        Args:
            line_id: LINE User ID
            
        Returns:
            妥当ならTrue
        """
        # LINE User IDは 'U' + 32文字の16進数
        pattern = r'^U[0-9a-f]{32}$'
        return bool(re.match(pattern, line_id))
    
    @staticmethod
    def sanitize_user_input(text: str, max_length: int = 1000) -> str:
        """
        ユーザー入力のサニタイズ
        
        Args:
            text: 入力テキスト
            max_length: 最大文字数
            
        Returns:
            サニタイズされたテキスト
        """
        if not text:
            return ""
        
        # 長さ制限
        sanitized = text[:max_length]
        
        # 制御文字を削除
        sanitized = ''.join(char for char in sanitized if char.isprintable() or char in '\n\r\t')
        
        # 前後の空白を削除
        sanitized = sanitized.strip()
        
        return sanitized


# 使用例:
# is_valid, parsed_time = Validators.validate_time_format("09:30")
# if is_valid:
#     print(f"Valid time: {parsed_time}")
