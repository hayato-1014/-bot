-- Initial Database Schema
-- PostgreSQL用（本番環境）
-- SQLiteでも動作するように記述

-- ユーザーテーブル
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    line_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'STAFF',
    email VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_line_id ON users(line_id);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);

-- シフト希望テーブル
CREATE TABLE IF NOT EXISTS shift_requests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    priority INTEGER DEFAULT 1,
    status VARCHAR(20) DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_shift_requests_user_date ON shift_requests(user_id, date);
CREATE INDEX IF NOT EXISTS idx_shift_requests_date ON shift_requests(date);
CREATE INDEX IF NOT EXISTS idx_shift_requests_status ON shift_requests(status);

-- シフトテーブル
CREATE TABLE IF NOT EXISTS shifts (
    id SERIAL PRIMARY KEY,
    group_id VARCHAR(50) NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    version INTEGER DEFAULT 1,
    required_skill_level DECIMAL(3,2),
    predicted_traffic INTEGER,
    
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    adjusted_by INTEGER REFERENCES users(id),
    adjusted_at TIMESTAMP,
    
    approved_by INTEGER REFERENCES users(id),
    approved_at TIMESTAMP,
    
    published_by INTEGER REFERENCES users(id),
    published_at TIMESTAMP,
    
    rejected_by INTEGER REFERENCES users(id),
    rejected_at TIMESTAMP,
    rejection_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_shifts_group ON shifts(group_id);
CREATE INDEX IF NOT EXISTS idx_shifts_user_date ON shifts(user_id, date);
CREATE INDEX IF NOT EXISTS idx_shifts_status ON shifts(status);
CREATE INDEX IF NOT EXISTS idx_shifts_date ON shifts(date);

-- シフト変更履歴テーブル
CREATE TABLE IF NOT EXISTS shift_revisions (
    id SERIAL PRIMARY KEY,
    shift_id INTEGER NOT NULL REFERENCES shifts(id) ON DELETE CASCADE,
    field_name VARCHAR(50) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by INTEGER NOT NULL REFERENCES users(id),
    change_reason TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_shift_revisions_shift ON shift_revisions(shift_id);
CREATE INDEX IF NOT EXISTS idx_shift_revisions_changed_at ON shift_revisions(changed_at);

-- 監査ログテーブル
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    action VARCHAR(100) NOT NULL,
    actor_id INTEGER REFERENCES users(id),
    target_user_id INTEGER REFERENCES users(id),
    resource_type VARCHAR(50),
    resource_id INTEGER,
    data_accessed TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    result VARCHAR(20),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_actor ON audit_logs(actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);

-- 通知履歴テーブル
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    notification_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_unread ON notifications(user_id, is_read);

-- 初期管理者ユーザー作成用関数（手動で実行）
-- INSERT INTO users (line_id, name, role, is_active) 
-- VALUES ('ADMIN_LINE_ID_HERE', '管理者', 'ADMIN', true);

-- サンプルコメント
COMMENT ON TABLE users IS 'ユーザー情報テーブル';
COMMENT ON TABLE shifts IS 'シフト情報テーブル（承認ワークフロー対応）';
COMMENT ON TABLE shift_requests IS 'シフト希望提出テーブル';
COMMENT ON TABLE shift_revisions IS '変更履歴テーブル（監査証跡）';
COMMENT ON TABLE audit_logs IS '監査ログテーブル';
