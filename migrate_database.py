#!/usr/bin/env python3
"""
데이터베이스 마이그레이션 스크립트
AWS 테스크 서비스 업데이트 시 데이터 유지를 위한 스크립트
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
import sqlite3
import tempfile
from datetime import datetime

# 데이터베이스 연결 설정
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:Snspmt2024!@snspmt-cluste.cluster-cvmiee0q0zhs.ap-northeast-2.rds.amazonaws.com:5432/snspmt')

def get_db_connection():
    """데이터베이스 연결을 가져옵니다."""
    try:
        if DATABASE_URL.startswith('postgresql://'):
            conn = psycopg2.connect(
                DATABASE_URL,
                connect_timeout=30,
                keepalives_idle=600,
                keepalives_interval=30,
                keepalives_count=3
            )
            conn.autocommit = False
            return conn
        else:
            db_path = os.path.join(tempfile.gettempdir(), 'snspmt.db')
            conn = sqlite3.connect(db_path, timeout=30)
            conn.row_factory = sqlite3.Row
            return conn
    except Exception as e:
        print(f"데이터베이스 연결 실패: {e}")
        raise

def create_migration_table():
    """마이그레이션 테이블을 생성합니다."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id SERIAL PRIMARY KEY,
                    version VARCHAR(255) UNIQUE NOT NULL,
                    description TEXT,
                    executed_at TIMESTAMP DEFAULT NOW()
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT UNIQUE NOT NULL,
                    description TEXT,
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        conn.commit()
        print("✅ 마이그레이션 테이블 생성 완료")
        
    except Exception as e:
        print(f"❌ 마이그레이션 테이블 생성 실패: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_executed_migrations():
    """실행된 마이그레이션 목록을 가져옵니다."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT version FROM schema_migrations ORDER BY version")
        return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"❌ 마이그레이션 목록 조회 실패: {e}")
        return []
    finally:
        conn.close()

def execute_migration(version, description, sql_commands):
    """마이그레이션을 실행합니다."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        print(f"🔄 마이그레이션 {version} 실행 중: {description}")
        
        # SQL 명령어들을 실행
        for sql in sql_commands:
            cursor.execute(sql)
        
        # 마이그레이션 기록 추가
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                INSERT INTO schema_migrations (version, description, executed_at)
                VALUES (%s, %s, NOW())
            """, (version, description))
        else:
            cursor.execute("""
                INSERT INTO schema_migrations (version, description, executed_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (version, description))
        
        conn.commit()
        print(f"✅ 마이그레이션 {version} 완료")
        
    except Exception as e:
        print(f"❌ 마이그레이션 {version} 실패: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def run_migrations():
    """모든 마이그레이션을 실행합니다."""
    print("🚀 데이터베이스 마이그레이션 시작")
    
    # 마이그레이션 테이블 생성
    create_migration_table()
    
    # 실행된 마이그레이션 목록 가져오기
    executed_migrations = get_executed_migrations()
    print(f"📋 실행된 마이그레이션: {executed_migrations}")
    
    # 마이그레이션 정의
    migrations = [
        {
            'version': '001',
            'description': '사용자 테이블 개선 - last_activity, display_name 필드 추가',
            'sql': [
                """
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS display_name VARCHAR(255)
                """,
                """
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS last_activity TIMESTAMP DEFAULT NOW()
                """
            ]
        },
        {
            'version': '002',
            'description': '주문 테이블 개선 - 추가 필드들 추가',
            'sql': [
                """
                ALTER TABLE orders 
                ADD COLUMN IF NOT EXISTS user_email VARCHAR(255)
                """,
                """
                ALTER TABLE orders 
                ADD COLUMN IF NOT EXISTS service_type VARCHAR(255)
                """,
                """
                ALTER TABLE orders 
                ADD COLUMN IF NOT EXISTS service_platform VARCHAR(255)
                """,
                """
                ALTER TABLE orders 
                ADD COLUMN IF NOT EXISTS service_quantity INTEGER
                """,
                """
                ALTER TABLE orders 
                ADD COLUMN IF NOT EXISTS service_link TEXT
                """,
                """
                ALTER TABLE orders 
                ADD COLUMN IF NOT EXISTS total_price DECIMAL(10,2)
                """,
                """
                ALTER TABLE orders 
                ADD COLUMN IF NOT EXISTS amount DECIMAL(10,2)
                """,
                """
                ALTER TABLE orders 
                ADD COLUMN IF NOT EXISTS remarks TEXT
                """
            ]
        },
        {
            'version': '003',
            'description': '포인트 구매 테이블 개선 - 추가 필드들 추가',
            'sql': [
                """
                ALTER TABLE point_purchases 
                ADD COLUMN IF NOT EXISTS purchase_id VARCHAR(255) UNIQUE
                """,
                """
                ALTER TABLE point_purchases 
                ADD COLUMN IF NOT EXISTS user_email VARCHAR(255)
                """,
                """
                ALTER TABLE point_purchases 
                ADD COLUMN IF NOT EXISTS depositor_name VARCHAR(255)
                """,
                """
                ALTER TABLE point_purchases 
                ADD COLUMN IF NOT EXISTS bank_name VARCHAR(255)
                """,
                """
                ALTER TABLE point_purchases 
                ADD COLUMN IF NOT EXISTS receipt_type VARCHAR(50)
                """,
                """
                ALTER TABLE point_purchases 
                ADD COLUMN IF NOT EXISTS business_info TEXT
                """
            ]
        },
        {
            'version': '004',
            'description': '추천인 시스템 테이블 생성',
            'sql': [
                """
                CREATE TABLE IF NOT EXISTS referral_codes (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(50) UNIQUE NOT NULL,
                    user_id VARCHAR(255),
                    user_email VARCHAR(255),
                    is_active BOOLEAN DEFAULT true,
                    usage_count INTEGER DEFAULT 0,
                    total_commission DECIMAL(10,2) DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS referrals (
                    id SERIAL PRIMARY KEY,
                    referrer_id VARCHAR(255) NOT NULL,
                    referrer_email VARCHAR(255) NOT NULL,
                    referred_id VARCHAR(255) NOT NULL,
                    referred_email VARCHAR(255) NOT NULL,
                    referral_code VARCHAR(50) NOT NULL,
                    commission DECIMAL(10,2) DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW()
                )
                """
            ]
        }
    ]
    
    # 마이그레이션 실행
    for migration in migrations:
        if migration['version'] not in executed_migrations:
            execute_migration(
                migration['version'],
                migration['description'],
                migration['sql']
            )
        else:
            print(f"⏭️ 마이그레이션 {migration['version']} 이미 실행됨")
    
    print("🎉 모든 마이그레이션 완료")

def backup_data():
    """데이터 백업 (선택사항)"""
    print("📦 데이터 백업 기능은 별도 구현 필요")
    # 실제 운영 환경에서는 S3나 다른 스토리지에 백업하는 로직 추가

def restore_data():
    """데이터 복원 (선택사항)"""
    print("🔄 데이터 복원 기능은 별도 구현 필요")
    # 실제 운영 환경에서는 백업에서 복원하는 로직 추가

if __name__ == "__main__":
    try:
        run_migrations()
        print(f"✅ 마이그레이션 완료 - {datetime.now()}")
    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        exit(1)
