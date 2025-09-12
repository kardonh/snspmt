#!/usr/bin/env python3
"""
PostgreSQL 데이터베이스 생성 스크립트
snspmt-db 인스턴스에 snspmt 데이터베이스를 생성합니다.
"""

import psycopg2
from psycopg2 import sql
import sys

def create_database():
    """snspmt 데이터베이스 생성"""
    try:
        # 기본 postgres 데이터베이스에 연결
        conn = psycopg2.connect(
            host="snspmt-db.cvmiee0q0zhs.ap-northeast-2.rds.amazonaws.com",
            port=5432,
            database="postgres",
            user="postgres",
            password="Snspmt2024!"
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("PostgreSQL 연결 성공")
        
        # snspmt 데이터베이스 생성
        cursor.execute("CREATE DATABASE snspmt;")
        print("✅ snspmt 데이터베이스 생성 완료")
        
        # 생성된 데이터베이스에 연결하여 테이블 생성
        conn.close()
        
        # snspmt 데이터베이스에 연결
        conn = psycopg2.connect(
            host="snspmt-db.cvmiee0q0zhs.ap-northeast-2.rds.amazonaws.com",
            port=5432,
            database="snspmt",
            user="postgres",
            password="Snspmt2024!"
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("snspmt 데이터베이스 연결 성공")
        
        # 테이블 생성
        tables = [
            """
            CREATE TABLE IF NOT EXISTS points (
                user_id TEXT PRIMARY KEY,
                points INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS orders (
                order_id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                service_id TEXT NOT NULL,
                link TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS point_purchases (
                purchase_id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                amount INTEGER NOT NULL,
                price REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS referral_codes (
                code_id SERIAL PRIMARY KEY,
                referrer_user_id TEXT NOT NULL,
                code TEXT UNIQUE NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS referrals (
                referral_id SERIAL PRIMARY KEY,
                referrer_user_id TEXT NOT NULL,
                referred_user_id TEXT NOT NULL,
                commission_rate REAL DEFAULT 0.1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]
        
        for i, table_sql in enumerate(tables, 1):
            cursor.execute(table_sql)
            print(f"✅ 테이블 {i} 생성 완료")
        
        # 관리자 계정 포인트 설정
        cursor.execute("""
            INSERT INTO points (user_id, points, created_at, updated_at)
            VALUES ('admin', 99999, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) DO UPDATE SET 
                points = 99999,
                updated_at = CURRENT_TIMESTAMP
        """)
        print("✅ 관리자 계정 포인트 설정 완료 (99999)")
        
        # 테스트 데이터 추가
        test_users = [
            ('user1', 1000),
            ('user2', 500),
            ('user3', 2000)
        ]
        
        for user_id, points in test_users:
            cursor.execute("""
                INSERT INTO points (user_id, points, created_at, updated_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) DO UPDATE SET 
                    points = %s,
                    updated_at = CURRENT_TIMESTAMP
            """, (user_id, points, points))
        
        print("✅ 테스트 사용자 데이터 추가 완료")
        
        # 테스트 포인트 구매 신청 추가
        test_purchases = [
            ('user1', 1000, 10000, 'pending'),
            ('user2', 500, 5000, 'approved'),
            ('user3', 2000, 20000, 'pending')
        ]
        
        for user_id, amount, price, status in test_purchases:
            cursor.execute("""
                INSERT INTO point_purchases (user_id, amount, price, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (user_id, amount, price, status))
        
        print("✅ 테스트 포인트 구매 신청 데이터 추가 완료")
        
        conn.close()
        print("🎉 데이터베이스 설정 완료!")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_database()