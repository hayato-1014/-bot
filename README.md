# シフト管理Bot - セットアップガイド

LINEbotを使用したシフト管理システム（Phase 1: 基本機能）

## 📋 目次

1. [機能概要](#機能概要)
2. [必要なもの](#必要なもの)
3. [セットアップ手順](#セットアップ手順)
4. [LINE Developers設定](#line-developers設定)
5. [デプロイ手順](#デプロイ手順)
6. [使い方](#使い方)
7. [トラブルシューティング](#トラブルシューティング)

---

## 機能概要

### Phase 1で実装されている機能

- ✅ ユーザー登録・権限管理（スタッフ/評価者/副店長/店長/管理者）
- ✅ シフト希望の提出・収集
- ✅ 自動シフト作成（PuLPによる最適化）
- ✅ 承認ワークフロー（下書き→調整→承認→公開）
- ✅ 差し戻し機能
- ✅ 労働基準法チェック
- ✅ LINE通知
- ✅ エラー監視・通知システム

---

## 必要なもの

### 1. アカウント

- [ ] LINEアカウント（個人用）
- [ ] LINE Developers アカウント（無料）
- [ ] Render または Railway アカウント（無料枠あり）
- [ ] Sentry アカウント（任意、エラー監視用）

### 2. ソフトウェア

- [ ] Python 3.11以上
- [ ] Git（バージョン管理）
- [ ] テキストエディタ（VS Code推奨）

---

## セットアップ手順

### ステップ1: プロジェクトのダウンロード

```bash
# プロジェクトをダウンロード（または展開）
cd shift_bot
```

### ステップ2: 仮想環境の作成

```bash
# 仮想環境を作成
python -m venv venv

# 仮想環境を有効化
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### ステップ3: 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### ステップ4: 環境変数の設定

```bash
# .env.exampleをコピー
cp .env.example .env

# .envファイルを編集（後述のLINE設定後に値を入力）
```

---

## LINE Developers設定

### 1. LINE Developersコンソールにアクセス

1. https://developers.line.biz/console/ にアクセス
2. LINEアカウントでログイン

### 2. プロバイダーを作成

1. 「作成」ボタンをクリック
2. プロバイダー名を入力（例: 「マイ店舗」）

### 3. Messaging APIチャネルを作成

1. 「Messaging API」を選択
2. 以下の情報を入力:
   - チャネル名: シフト管理Bot
   - チャネル説明: スタッフのシフト管理用Bot
   - 大業種: 小売
   - 小業種: その他
3. 利用規約に同意して「作成」

### 4. チャネルの設定

#### 4-1. Channel Secret を取得

1. 「チャネル基本設定」タブ
2. 「Channel Secret」をコピー
3. `.env`ファイルの`LINE_CHANNEL_SECRET`に貼り付け

#### 4-2. Channel Access Token を発行

1. 「Messaging API設定」タブ
2. 「チャネルアクセストークン（長期）」の「発行」をクリック
3. トークンをコピー
4. `.env`ファイルの`LINE_CHANNEL_ACCESS_TOKEN`に貼り付け

#### 4-3. Webhookの設定

1. 「Messaging API設定」タブ
2. 「Webhook URL」に以下を設定:
   ```
   https://your-app-name.onrender.com/callback
   ```
   （デプロイ後に実際のURLに変更）
3. 「Webhookの利用」をONにする

#### 4-4. 応答メッセージをOFF

1. 「Messaging API設定」タブ
2. 「応答メッセージ」→「編集」
3. 「応答メッセージ」をOFF
4. 「Webhook」をON

---

## デプロイ手順

### 方法1: Renderでデプロイ（推奨）

#### 1. Renderアカウント作成

https://render.com/ でアカウント作成（GitHubアカウントで連携可能）

#### 2. PostgreSQLデータベースを作成

1. Renderダッシュボードで「New +」→「PostgreSQL」
2. 名前を入力（例: shift-bot-db）
3. プランを「Free」に設定
4. 「Create Database」をクリック
5. 「Internal Database URL」をコピー

#### 3. Webサービスを作成

1. 「New +」→「Web Service」
2. GitHubリポジトリを接続（またはPublic Gitリポジトリ）
3. 以下の設定:
   - Name: shift-bot
   - Region: Singapore（日本に最も近い）
   - Branch: main
   - Root Directory: （空欄）
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
   - Instance Type: Free

#### 4. 環境変数を設定

「Environment」タブで以下を追加:

```
LINE_CHANNEL_SECRET=（LINE Developersからコピー）
LINE_CHANNEL_ACCESS_TOKEN=（LINE Developersからコピー）
DATABASE_URL=（RenderのPostgreSQLからコピー）
ENVIRONMENT=production
SECRET_KEY=（ランダムな文字列を生成）
```

SECRET_KEYの生成方法:
```python
python -c "import secrets; print(secrets.token_hex(32))"
```

#### 5. デプロイ

「Create Web Service」をクリック

デプロイ完了後、URLが表示されます（例: https://shift-bot-xyz.onrender.com）

#### 6. LINE DevelopersでWebhook URLを更新

1. LINE Developersコンソールに戻る
2. 「Messaging API設定」→「Webhook URL」
3. `https://shift-bot-xyz.onrender.com/callback`に更新
4. 「検証」ボタンで接続確認

---

### 方法2: ローカル開発環境で動作確認

#### 1. データベースの初期化

```bash
# SQLiteを使用（開発用）
python -c "from db.database import init_db, create_tables; init_db(); create_tables()"
```

#### 2. アプリケーションの起動

```bash
python app.py
```

#### 3. ngrokでトンネルを作成

```bash
# ngrokをインストール
# https://ngrok.com/download

# トンネルを開始
ngrok http 5000
```

ngrokが生成したURLをLINE DevelopersのWebhook URLに設定

---

## 初期管理者の登録

### 方法1: データベースに直接追加

```python
# scripts/setup_admin.py を実行
python scripts/setup_admin.py
```

または手動で:

```python
from db.database import init_db, DatabaseSession
from models.user import User, UserRole

init_db()

with DatabaseSession() as session:
    admin = User(
        line_id='YOUR_LINE_ID',  # LINEのUser IDを入力
        name='管理者名',
        role=UserRole.ADMIN,
        is_active=True
    )
    session.add(admin)
    session.commit()
    print(f"✅ 管理者を作成しました: {admin.name}")
```

LINE User IDの確認方法:
1. Botにメッセージを送信
2. ログに表示されるUser IDを確認

---

## 使い方

### スタッフ（一般ユーザー）

#### シフト希望を提出

```
3/1 9:00-17:00
```

または

```
2024/3/1 9:00-17:00 希望
```

優先度の指定:
- 「希望」（デフォルト）
- 「できれば」
- 「可能なら」

例:
```
3/5 10:00-18:00 できれば
```

#### 自分のシフトを確認

```
シフト
```

または

```
シフト確認
```

#### 提出済みの希望を確認

```
希望
```

または

```
希望確認
```

---

### 管理者（店長・副店長）

#### シフトを自動作成

```
シフト作成 3/1-3/7
```

#### シフトを承認・公開

```
承認
```

#### ヘルプを表示

```
ヘルプ
```

---

## トラブルシューティング

### エラー: "Database not initialized"

```bash
# データベースを初期化
python -c "from db.database import init_db, create_tables; init_db(); create_tables()"
```

### エラー: "Invalid signature"

- LINE DevelopersのChannel Secretが正しいか確認
- Webhook URLが正しいか確認

### Botが応答しない

1. Webhook URLが正しく設定されているか確認
2. RenderまたはRailwayのログを確認
3. LINE Developersの「Webhook」がONになっているか確認
4. 「応答メッセージ」がOFFになっているか確認

### シフトが作成されない

- スタッフがシフト希望を提出しているか確認
- アクティブなユーザーが存在するか確認
- ログでエラーメッセージを確認

---

## エラー監視の設定（任意）

### Sentryの設定

1. https://sentry.io/ でアカウント作成
2. 新しいプロジェクトを作成（Python/Flask）
3. DSNをコピー
4. `.env`の`SENTRY_DSN`に貼り付け

### LINE Notifyの設定

1. https://notify-bot.line.me/ にアクセス
2. 「マイページ」→「トークンを発行する」
3. トークン名: シフトBot開発者通知
4. 通知先: 自分のLINEアカウント
5. トークンをコピー
6. `.env`の`LINE_NOTIFY_TOKEN`に貼り付け

---

## 次のステップ

Phase 1が完了したら、以下の機能を追加できます:

- **Phase 2**: Excel取り込み、能力評価システム
- **Phase 3**: 客足予測、機械学習による最適化
- **Phase 4**: シフト交換、自動リマインダー

詳細は開発者にお問い合わせください。

---

## サポート

問題が発生した場合:

1. このREADMEのトラブルシューティングを確認
2. ログファイルを確認
3. GitHubのIssuesを検索
4. 開発者に連絡

---

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

---

**⚠️ 重要な注意事項**

1. 本番環境では必ずPostgreSQLを使用してください
2. SECRET_KEYは絶対に公開しないでください
3. 個人情報は適切に管理してください
4. 労働基準法を遵守してください
5. 定期的にバックアップを取ってください

---

以上でセットアップは完了です！ご不明な点があればお気軽にお問い合わせください。
