#!/usr/bin/env python3
"""
Pooler 연결 테스트 - 다양한 사용자명 형식 시도
"""

import psycopg2

PROJECT_REF = "gvtrizwkstaznrlloixi"
PASSWORD = "VEOdjCwztZm4oynz"
POOLER_HOST = "aws-0-ap-southeast-2.pooler.supabase.com"

# 테스트할 사용자명 형식들
USER_FORMATS = [
    f"postgres.{PROJECT_REF}",  # 현재 사용 중
    "postgres",  # Direct 형식
    f"postgres.{PROJECT_REF}@postgres",  # 일부 환경에서 사용
]

print("=" * 60)
print("Pooler 연결 테스트")
print("=" * 60)
print(f"프로젝트 참조: {PROJECT_REF}")
print(f"비밀번호: {PASSWORD}")
print()

# Transaction mode (포트 6543)
print("\n[Transaction Mode - 포트 6543]")
print("-" * 60)
for user in USER_FORMATS:
    try:
        conn = psycopg2.connect(
            host=POOLER_HOST,
            port=6543,
            database='postgres',
            user=user,
            password=PASSWORD,
            connect_timeout=10
        )
        cursor = conn.cursor()
        cursor.execute("SELECT current_user, current_database();")
        result = cursor.fetchone()
        print(f"✅ 성공: {user}")
        print(f"   현재 사용자: {result[0]}, 데이터베이스: {result[1]}")
        cursor.close()
        conn.close()
        break
    except psycopg2.OperationalError as e:
        error_msg = str(e)
        if "Tenant or user not found" in error_msg:
            print(f"❌ 실패: {user} - Tenant or user not found")
        else:
            print(f"❌ 실패: {user} - {error_msg[:80]}")

# Session mode (포트 5432)
print("\n[Session Mode - 포트 5432]")
print("-" * 60)
for user in USER_FORMATS:
    try:
        conn = psycopg2.connect(
            host=POOLER_HOST,
            port=5432,
            database='postgres',
            user=user,
            password=PASSWORD,
            connect_timeout=10
        )
        cursor = conn.cursor()
        cursor.execute("SELECT current_user, current_database();")
        result = cursor.fetchone()
        print(f"✅ 성공: {user}")
        print(f"   현재 사용자: {result[0]}, 데이터베이스: {result[1]}")
        cursor.close()
        conn.close()
        break
    except psycopg2.OperationalError as e:
        error_msg = str(e)
        if "Tenant or user not found" in error_msg:
            print(f"❌ 실패: {user} - Tenant or user not found")
        else:
            print(f"❌ 실패: {user} - {error_msg[:80]}")

print("\n" + "=" * 60)
print("테스트 완료")
print("=" * 60)

