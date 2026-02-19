"""
動作確認スクリプト
基本的な機能が動作するかテスト
"""
import sys
from datetime import datetime, timedelta, time

def test_imports():
    """モジュールのインポートテスト"""
    print("📦 モジュールインポートテスト...")
    
    try:
        from config import Config
        from db.database import init_db, create_tables
        from models.user import User, UserRole, Permission
        from models.shift import Shift, ShiftStatus
        from models.shift_request import ShiftRequest, RequestStatus
        from utils.validators import Validators
        from utils.labor_law import LaborLawChecker
        from services.shift_optimizer import ShiftOptimizer
        from services.shift_approval import ShiftApprovalService
        
        print("  ✅ すべてのモジュールを正常にインポートできました")
        return True
    except Exception as e:
        print(f"  ❌ インポートエラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config():
    """設定のテスト"""
    print("\n⚙️  設定テスト...")
    
    try:
        from config import Config
        
        print(f"  環境: {Config.ENVIRONMENT}")
        print(f"  デバッグ: {Config.DEBUG}")
        print(f"  データベース: {Config.DATABASE_URL[:30]}...")
        print(f"  タイムゾーン: {Config.TIMEZONE}")
        
        # 労働法設定
        print(f"  最大労働時間/日: {Config.MAX_WORK_HOURS_PER_DAY}時間")
        print(f"  最大労働時間/週: {Config.MAX_WORK_HOURS_PER_WEEK}時間")
        
        print("  ✅ 設定は正常です")
        return True
    except Exception as e:
        print(f"  ❌ 設定エラー: {e}")
        return False


def test_database():
    """データベース接続テスト"""
    print("\n🗄️  データベーステスト...")
    
    try:
        from db.database import init_db, create_tables, DatabaseSession
        
        # 初期化
        init_db()
        print("  ✅ データベース接続成功")
        
        # テーブル作成
        create_tables()
        print("  ✅ テーブル作成成功")
        
        # 簡単なクエリテスト
        with DatabaseSession() as session:
            result = session.execute('SELECT 1')
            print("  ✅ クエリ実行成功")
        
        return True
    except Exception as e:
        print(f"  ❌ データベースエラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_validators():
    """バリデーターのテスト"""
    print("\n✔️  バリデーターテスト...")
    
    try:
        from utils.validators import Validators
        
        # 時刻フォーマット
        valid, time_obj = Validators.validate_time_format("09:30")
        assert valid, "時刻フォーマットテスト失敗"
        print(f"  ✅ 時刻フォーマット: {time_obj}")
        
        # 日付フォーマット
        valid, date_obj = Validators.validate_date_format("2024/3/1")
        assert valid, "日付フォーマットテスト失敗"
        print(f"  ✅ 日付フォーマット: {date_obj}")
        
        # メッセージパース
        parsed = Validators.parse_shift_request_message("3/1 9:00-17:00 希望")
        assert parsed is not None, "メッセージパーステスト失敗"
        print(f"  ✅ メッセージパース: {parsed}")
        
        return True
    except Exception as e:
        print(f"  ❌ バリデーターエラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_labor_law():
    """労働法チェックのテスト"""
    print("\n⚖️  労働法チェックテスト...")
    
    try:
        from utils.labor_law import LaborLawChecker
        from models.shift import Shift
        from models.user import User
        from datetime import date, time
        
        # テスト用シフトを作成
        class MockUser:
            def __init__(self, id, name):
                self.id = id
                self.name = name
        
        class MockShift:
            def __init__(self, user_id, date, start, end):
                self.user_id = user_id
                self.user = MockUser(user_id, f"User {user_id}")
                self.date = date
                self.start_time = start
                self.end_time = end
            
            def get_duration_hours(self):
                start_min = self.start_time.hour * 60 + self.start_time.minute
                end_min = self.end_time.hour * 60 + self.end_time.minute
                return (end_min - start_min) / 60.0
        
        shifts = [
            MockShift(1, date(2024, 3, 1), time(9, 0), time(18, 0)),  # 9時間（違反）
            MockShift(1, date(2024, 3, 2), time(9, 0), time(17, 0)),  # 8時間
        ]
        
        violations = LaborLawChecker.check_all_violations(shifts)
        
        if violations:
            print(f"  ⚠️  {len(violations)}件の違反を検出:")
            for v in violations:
                print(f"    - {v.violation_type}: {v.details}")
        else:
            print("  ✅ 労働法違反なし")
        
        return True
    except Exception as e:
        print(f"  ❌ 労働法チェックエラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """メインテスト実行"""
    print("=" * 60)
    print("シフトBot 動作確認テスト")
    print("=" * 60)
    
    tests = [
        ("モジュールインポート", test_imports),
        ("設定", test_config),
        ("データベース", test_database),
        ("バリデーター", test_validators),
        ("労働法チェック", test_labor_law),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name}テストでエラー: {e}")
            results.append((name, False))
    
    # サマリー
    print("\n" + "=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\n合計: {passed}/{total} テスト通過")
    
    if passed == total:
        print("\n🎉 すべてのテストに合格しました！")
        sys.exit(0)
    else:
        print("\n⚠️  一部のテストが失敗しました")
        sys.exit(1)


if __name__ == "__main__":
    main()
