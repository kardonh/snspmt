#!/usr/bin/env python3
"""
새 스키마 기반 데이터베이스 마이그레이션 스크립트
Supabase/PostgreSQL 환경 전용
"""

import os
from datetime import datetime

import psycopg2
from psycopg2 import sql

# 필수 환경 변수
DATABASE_URL = os.environ.get("DATABASE_URL", "")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL 환경 변수가 설정되어 있지 않습니다.")

if not DATABASE_URL.startswith("postgresql://"):
    raise ValueError("현재 마이그레이션 스크립트는 PostgreSQL 전용입니다. Supabase/PostgreSQL URL을 사용하세요.")


def get_db_connection():
    """PostgreSQL 연결 반환"""
    try:
        conn = psycopg2.connect(
            DATABASE_URL,
            connect_timeout=30,
            keepalives_idle=600,
            keepalives_interval=30,
            keepalives_count=3,
        )
        conn.autocommit = False
        return conn
    except Exception as exc:
        print(f"❌ 데이터베이스 연결 실패: {exc}")
        raise


def create_migration_table():
    """schema_migrations 테이블 생성"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                version VARCHAR(255) UNIQUE NOT NULL,
                description TEXT,
                executed_at TIMESTAMP DEFAULT NOW()
            )
            """
        )
        conn.commit()
        print("✅ schema_migrations 테이블 확인 완료")
    except Exception as exc:
        conn.rollback()
        print(f"❌ schema_migrations 테이블 생성 실패: {exc}")
        raise
    finally:
        conn.close()


def get_executed_migrations():
    """이미 실행된 마이그레이션 버전 목록 반환"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT version FROM schema_migrations ORDER BY version")
        return [row[0] for row in cursor.fetchall()]
    except Exception as exc:
        print(f"❌ 마이그레이션 목록 조회 실패: {exc}")
        return []
    finally:
        conn.close()


def execute_migration(version, description, sql_commands):
    """단일 마이그레이션 실행"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        print(f"🔄 마이그레이션 {version} 실행 중: {description}")

        for command in sql_commands:
            cursor.execute(command)

        cursor.execute(
            """
            INSERT INTO schema_migrations (version, description, executed_at)
            VALUES (%s, %s, NOW())
            """,
            (version, description),
        )

        conn.commit()
        print(f"✅ 마이그레이션 {version} 완료")
    except Exception as exc:
        conn.rollback()
        print(f"❌ 마이그레이션 {version} 실패: {exc}")
        raise
    finally:
        conn.close()


def run_migrations():
    """마이그레이션 메인 실행 함수"""
    print("🚀 데이터베이스 마이그레이션 시작")

    create_migration_table()

    executed = set(get_executed_migrations())
    print(f"📋 실행된 마이그레이션: {sorted(executed)}")

    migrations = [
        {
            "version": "100",
            "description": "신규 통합 스키마 생성",
            "sql": [
                # 기존 테이블 및 타입 제거
                """
                DROP TABLE IF EXISTS
                    payout_commissions,
                    payouts,
                    payout_requests,
                    wallet_transactions,
                    wallets,
                    commissions,
                    referrals,
                    order_items,
                    orders,
                    user_coupons,
                    coupons,
                    package_items,
                    packages,
                    product_variants,
                    products,
                    categories,
                    user_sessions,
                    work_jobs,
                    blogs,
                    blog_lists,
                    notices,
                    users,
                    merchants
                CASCADE
                """,
                """
                DROP TYPE IF EXISTS
                    job_status,
                    payout_status,
                    payout_request_status,
                    wallet_tx_status,
                    wallet_tx_type,
                    commission_status,
                    referral_status,
                    order_item_status,
                    order_status,
                    coupon_status,
                    coupon_discount_type,
                    package_repeat_unit,
                    package_term_unit
                CASCADE
                """,
                # ENUM 타입 생성
                """
                CREATE TYPE package_term_unit AS ENUM ('minute','hour','day','week','month')
                """,
                """
                CREATE TYPE package_repeat_unit AS ENUM ('minute','hour','day','week','month')
                """,
                """
                CREATE TYPE coupon_discount_type AS ENUM ('fixed','percentage','free_shipping','none')
                """,
                """
                CREATE TYPE coupon_status AS ENUM ('active','used','expired','revoked')
                """,
                """
                CREATE TYPE order_status AS ENUM ('pending','paid','processing','completed','canceled','refunded')
                """,
                """
                CREATE TYPE order_item_status AS ENUM ('pending','in_progress','done','canceled')
                """,
                """
                CREATE TYPE referral_status AS ENUM ('pending','approved','rejected')
                """,
                """
                CREATE TYPE commission_status AS ENUM ('accrued','void','paid_out')
                """,
                """
                CREATE TYPE wallet_tx_type AS ENUM ('topup','order_debit','commission_credit','refund','admin_adjust')
                """,
                """
                CREATE TYPE wallet_tx_status AS ENUM ('pending','approved','rejected')
                """,
                """
                CREATE TYPE payout_request_status AS ENUM ('requested','approved','rejected')
                """,
                """
                CREATE TYPE payout_status AS ENUM ('processing','paid','failed')
                """,
                """
                CREATE TYPE job_status AS ENUM ('pending','processing','completed','failed','canceled')
                """,
                # 기본 테이블 생성
                """
                CREATE TABLE IF NOT EXISTS merchants (
                    merchant_id BIGSERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    phone VARCHAR(20),
                    business_number VARCHAR(255),
                    business_type VARCHAR(255),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGSERIAL PRIMARY KEY,
                    external_uid VARCHAR(255) UNIQUE,
                    merchant_id BIGINT REFERENCES merchants (merchant_id),
                    email VARCHAR(255) NOT NULL UNIQUE,
                    password_hash VARCHAR(255),
                    phone VARCHAR(20),
                    google_id VARCHAR(64),
                    kakao_id VARCHAR(64),
                    referral_code VARCHAR(32) UNIQUE,
                    referral_status VARCHAR(32),
                    source VARCHAR(255),
                    username VARCHAR(255),
                    is_admin BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS categories (
                    category_id BIGSERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    slug VARCHAR(255) UNIQUE,
                    is_active BOOLEAN DEFAULT TRUE,
                    image_url VARCHAR(255),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS products (
                    product_id BIGSERIAL PRIMARY KEY,
                    category_id BIGINT REFERENCES categories (category_id),
                    name VARCHAR(150) NOT NULL,
                    description TEXT,
                    is_domestic BOOLEAN DEFAULT TRUE,
                    auto_tag BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS product_variants (
                    variant_id BIGSERIAL PRIMARY KEY,
                    product_id BIGINT NOT NULL REFERENCES products (product_id),
                    name VARCHAR(255) NOT NULL,
                    price NUMERIC(14,2) NOT NULL,
                    min_quantity INTEGER,
                    max_quantity INTEGER,
                    delivery_time_days INTEGER,
                    is_active BOOLEAN DEFAULT TRUE,
                    meta_json JSONB,
                    api_endpoint VARCHAR(255),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS packages (
                    package_id BIGSERIAL PRIMARY KEY,
                    category_id BIGINT REFERENCES categories (category_id),
                    name VARCHAR(150) NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS package_items (
                    package_item_id BIGSERIAL PRIMARY KEY,
                    package_id BIGINT NOT NULL REFERENCES packages (package_id),
                    variant_id BIGINT NOT NULL REFERENCES product_variants (variant_id),
                    step INTEGER NOT NULL,
                    term_value INTEGER,
                    term_unit package_term_unit,
                    quantity INTEGER,
                    repeat_count INTEGER,
                    repeat_term_value INTEGER,
                    repeat_term_unit package_repeat_unit,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS coupons (
                    coupon_id BIGSERIAL PRIMARY KEY,
                    coupon_code VARCHAR(255) NOT NULL UNIQUE,
                    coupon_name VARCHAR(255),
                    discount_type coupon_discount_type DEFAULT 'none',
                    discount_value NUMERIC(14,2),
                    min_order_amount NUMERIC(14,2),
                    product_variant_id BIGINT REFERENCES product_variants (variant_id),
                    valid_from TIMESTAMP,
                    valid_until TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS user_coupons (
                    user_coupon_id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users (user_id),
                    coupon_id BIGINT NOT NULL REFERENCES coupons (coupon_id),
                    issued_at TIMESTAMP DEFAULT NOW(),
                    used_at TIMESTAMP,
                    status coupon_status DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS orders (
                    order_id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users (user_id),
                    referrer_user_id BIGINT REFERENCES users (user_id),
                    coupon_id BIGINT REFERENCES user_coupons (user_coupon_id),
                    total_amount NUMERIC(14,2) NOT NULL,
                    discount_amount NUMERIC(14,2) DEFAULT 0,
                    final_amount NUMERIC(14,2),
                    status order_status DEFAULT 'pending',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS order_items (
                    order_item_id BIGSERIAL PRIMARY KEY,
                    order_id BIGINT NOT NULL REFERENCES orders (order_id),
                    variant_id BIGINT NOT NULL REFERENCES product_variants (variant_id),
                    quantity INTEGER NOT NULL,
                    unit_price NUMERIC(14,2) NOT NULL,
                    line_amount NUMERIC(14,2),
                    link TEXT,
                    status order_item_status DEFAULT 'pending',
                    package_id BIGINT REFERENCES packages (package_id),
                    package_item_id BIGINT REFERENCES package_items (package_item_id),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS referrals (
                    referral_id BIGSERIAL PRIMARY KEY,
                    referrer_user_id BIGINT NOT NULL REFERENCES users (user_id),
                    referred_user_id BIGINT NOT NULL REFERENCES users (user_id),
                    status referral_status DEFAULT 'approved',
                    created_at TIMESTAMP DEFAULT NOW()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS commissions (
                    commission_id BIGSERIAL PRIMARY KEY,
                    referral_id BIGINT NOT NULL REFERENCES referrals (referral_id),
                    order_id BIGINT NOT NULL REFERENCES orders (order_id),
                    amount NUMERIC(14,2) NOT NULL,
                    status commission_status DEFAULT 'accrued',
                    paid_amount NUMERIC(14,2),
                    paid_out_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS wallets (
                    wallet_id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL UNIQUE REFERENCES users (user_id),
                    balance NUMERIC(14,2) NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS wallet_transactions (
                    transaction_id BIGSERIAL PRIMARY KEY,
                    wallet_id BIGINT NOT NULL REFERENCES wallets (wallet_id),
                    type wallet_tx_type NOT NULL,
                    amount NUMERIC(14,2) NOT NULL,
                    status wallet_tx_status DEFAULT 'approved',
                    locked BOOLEAN DEFAULT FALSE,
                    meta_json JSONB,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS payout_requests (
                    request_id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users (user_id),
                    amount NUMERIC(14,2) NOT NULL,
                    bank_name VARCHAR(100) NOT NULL,
                    account_number VARCHAR(64) NOT NULL,
                    status payout_request_status DEFAULT 'requested',
                    requested_at TIMESTAMP DEFAULT NOW(),
                    processed_at TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS payouts (
                    payout_id BIGSERIAL PRIMARY KEY,
                    request_id BIGINT NOT NULL REFERENCES payout_requests (request_id),
                    paid_amount NUMERIC(14,2) NOT NULL,
                    status payout_status DEFAULT 'processing',
                    processed_at TIMESTAMP DEFAULT NOW()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS payout_commissions (
                    payout_commission_id BIGSERIAL PRIMARY KEY,
                    payout_id BIGINT NOT NULL REFERENCES payouts (payout_id),
                    commission_id BIGINT NOT NULL REFERENCES commissions (commission_id),
                    amount_paid NUMERIC(14,2) NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS work_jobs (
                    job_id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users (user_id),
                    order_item_id BIGINT REFERENCES order_items (order_item_id),
                    package_item_id BIGINT REFERENCES package_items (package_item_id),
                    schedule_at TIMESTAMP,
                    status job_status DEFAULT 'pending',
                    attempts INTEGER DEFAULT 0,
                    last_run_at TIMESTAMP,
                    payload_json JSONB,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users (user_id),
                    session_token VARCHAR(255) NOT NULL UNIQUE,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    last_activity_at TIMESTAMP DEFAULT NOW()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS blog_lists (
                    list_id BIGSERIAL PRIMARY KEY,
                    tag VARCHAR(255),
                    categories VARCHAR(255),
                    image_url VARCHAR(255),
                    status VARCHAR(50),
                    meta_json JSONB,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS blogs (
                    blog_id BIGSERIAL PRIMARY KEY,
                    list_id BIGINT REFERENCES blog_lists (list_id),
                    title VARCHAR(255),
                    content TEXT,
                    views INTEGER DEFAULT 0,
                    category VARCHAR(255),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS notices (
                    notice_id BIGSERIAL PRIMARY KEY,
                    title VARCHAR(255),
                    image_url VARCHAR(255),
                    body TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
                """,
                # 인덱스 생성
                "CREATE INDEX IF NOT EXISTS idx_users_referral_code ON users (referral_code)",
                "CREATE INDEX IF NOT EXISTS idx_users_external_uid ON users (external_uid)",
                "CREATE INDEX IF NOT EXISTS idx_products_category_id ON products (category_id)",
                "CREATE INDEX IF NOT EXISTS idx_product_variants_product_id ON product_variants (product_id)",
                "CREATE INDEX IF NOT EXISTS idx_packages_category_id ON packages (category_id)",
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_user_coupons_unique ON user_coupons (user_id, coupon_id)",
                "CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders (user_id)",
                "CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items (order_id)",
                "CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals (referrer_user_id)",
                "CREATE INDEX IF NOT EXISTS idx_referrals_referred ON referrals (referred_user_id)",
                "CREATE INDEX IF NOT EXISTS idx_commissions_order_id ON commissions (order_id)",
                "CREATE INDEX IF NOT EXISTS idx_wallet_transactions_wallet_id ON wallet_transactions (wallet_id)",
                "CREATE INDEX IF NOT EXISTS idx_wallet_transactions_created_at ON wallet_transactions (created_at)",
                "CREATE INDEX IF NOT EXISTS idx_work_jobs_schedule_at ON work_jobs (schedule_at)",
                "CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions (user_id)"
            ],
        }
    ]

    for migration in migrations:
        if migration["version"] in executed:
            print(f"⏭️ 마이그레이션 {migration['version']} 이미 실행됨")
            continue

        execute_migration(migration["version"], migration["description"], migration["sql"])

    print("🎉 모든 마이그레이션 완료")


def backup_data():
    """TODO: 백업 로직"""
    print("📦 데이터 백업 기능은 아직 구현되어 있지 않습니다.")


def restore_data():
    """TODO: 복원 로직"""
    print("🔄 데이터 복원 기능은 아직 구현되어 있지 않습니다.")


if __name__ == "__main__":
    try:
        run_migrations()
        print(f"✅ 마이그레이션 완료 - {datetime.now()}")
    except Exception as exc:
        print(f"❌ 마이그레이션 실패: {exc}")
        exit(1)
