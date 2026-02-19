"""
初期管理者作成スクリプト
最初の管理者アカウントを作成するためのツール
"""
from db.database import init_db, DatabaseSession
from models.user import User, UserRole

def create_admin():
    """対話式で管理者を作成"""
    print("=" * 50)
    print("初期管理者アカウント作成")
    print("=" * 50)
    
    # データベース初期化
    init_db()
    
    print("\n管理者情報を入力してください:")
    
    line_id = input("LINE User ID: ").strip()
    if not line_id:
        print("❌ LINE User IDは必須です")
        return
    
    name = input("管理者名: ").strip()
    if not name:
        print("❌ 管理者名は必須です")
        return
    
    email = input("メールアドレス（任意）: ").strip() or None
    
    # 役割を選択
    print("\n役割を選択してください:")
    print("1. STAFF (一般スタッフ)")
    print("2. EVALUATOR (評価権限者)")
    print("3. SUB_MANAGER (副店長)")
    print("4. MANAGER (店長)")
    print("5. ADMIN (システム管理者)")
    
    role_choice = input("選択 (1-5): ").strip()
    
    role_map = {
        '1': UserRole.STAFF,
        '2': UserRole.EVALUATOR,
        '3': UserRole.SUB_MANAGER,
        '4': UserRole.MANAGER,
        '5': UserRole.ADMIN
    }
    
    role = role_map.get(role_choice, UserRole.STAFF)
    
    # 確認
    print(f"\n以下の内容で作成します:")
    print(f"  LINE User ID: {line_id}")
    print(f"  名前: {name}")
    print(f"  メール: {email if email else '(なし)'}")
    print(f"  役割: {role.name}")
    
    confirm = input("\nよろしいですか？ (y/n): ").strip().lower()
    
    if confirm != 'y':
        print("キャンセルしました")
        return
    
    # ユーザー作成
    try:
        with DatabaseSession() as session:
            # 既存チェック
            existing = session.query(User).filter(User.line_id == line_id).first()
            if existing:
                print(f"⚠️ このLINE IDは既に登録されています: {existing.name}")
                update = input("更新しますか？ (y/n): ").strip().lower()
                
                if update == 'y':
                    existing.name = name
                    existing.role = role
                    existing.email = email
                    existing.is_active = True
                    session.commit()
                    print(f"✅ ユーザーを更新しました: {existing.name} ({existing.role.name})")
                else:
                    print("キャンセルしました")
                return
            
            # 新規作成
            user = User(
                line_id=line_id,
                name=name,
                role=role,
                email=email,
                is_active=True
            )
            
            session.add(user)
            session.commit()
            
            print(f"\n✅ 管理者を作成しました！")
            print(f"  ID: {user.id}")
            print(f"  名前: {user.name}")
            print(f"  役割: {user.role.name}")
            
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    create_admin()
