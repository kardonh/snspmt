#!/usr/bin/env python3
"""
Supabase 연결 테스트 스크립트
다양한 사용자명 형식과 비밀번호를 시도합니다.
"""

import psycopg2

# 테스트할 연결 정보
PROJECT_REF = "gvtrizwkstaznrlloixi"
PASSWORD = "VEOdjCwztZm4oynz"
POOLER_HOST = "aws-0-ap-southeast-2.pooler.supabase.com"
DIRECT_HOST = "db.gvtrizwkstaznrlloixi.supabase.co"

# 테스트할 사용자명 형식들
USER_FORMATS = [
    "postgres.gvtrizwkstaznrlloixi",  # 현재 사용 중
    "postgres",  # Direct connection 형식
    f"postgres.{PROJECT_REF}",  # 명시적 형식
]

# 테스트할 연결 설정들
CONNECTION_TESTS = [
    # Pooler Transaction mode (포트 6543)
    {
        "name": "Pooler Transaction mode",
        "host": POOLER_HOST,
        "port": 6543,
        "users": USER_FORMATS,
    },
    # Pooler Session mode (포트 5432)
    {
        "name": "Pooler Session mode",
        "host": POOLER_HOST,
        "port": 5432,
        "users": USER_FORMATS,
    },
    # Direct Connection (포트 5432)
    {
        "name": "Direct Connection",
        "host": DIRECT_HOST,
        "port": 5432,
        "users": ["postgres"],  # Direct는 항상 postgres
    },
]

print("=" * 60)
print("Supabase 연결 테스트 시작")
print("=" * 60)
print(f"프로젝트 참조: {PROJECT_REF}")
print(f"비밀번호: {PASSWORD}")
print()

success_count = 0
failure_count = 0

for test in CONNECTION_TESTS:
    print(f"\n[{test['name']}]")
    print("-" * 60)
    
    for user in test['users']:
        try:
            conn = psycopg2.connect(
                host=test['host'],
                port=test['port'],
                database='postgres',
                user=user,
                password=PASSWORD,
                connect_timeout=10
            )
            
            # 연결 성공
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            
            print(f"✅ 성공: {user}@{test['host']}:{test['port']}")
            print(f"   PostgreSQL 버전: {version[:50]}...")
            success_count += 1
            
        except psycopg2.OperationalError as e:
            error_msg = str(e)
            if "Tenant or user not found" in error_msg:
                print(f"❌ 실패: {user}@{test['host']}:{test['port']}")
                print(f"   오류: Tenant or user not found (사용자명 또는 비밀번호 오류)")
            elif "could not translate host name" in error_msg:
                print(f"⚠️  DNS 실패: {user}@{test['host']}:{test['port']}")
                print(f"   오류: DNS 해석 실패 (IPv6 문제 가능)")
            else:
                print(f"❌ 실패: {user}@{test['host']}:{test['port']}")
                print(f"   오류: {error_msg[:100]}")
            failure_count += 1
        except Exception as e:
            print(f"❌ 예외: {user}@{test['host']}:{test['port']}")
            print(f"   오류: {type(e).__name__}: {str(e)[:100]}")
            failure_count += 1

print()
print("=" * 60)
print(f"테스트 완료: 성공 {success_count}개, 실패 {failure_count}개")
print("=" * 60)

if success_count == 0:
    print("\n⚠️  모든 연결 시도가 실패했습니다.")
    print("다음을 확인하세요:")
    print("1. Supabase 대시보드에서 정확한 비밀번호 확인")
    print("2. 프로젝트 참조가 올바른지 확인")
    print("3. 네트워크 연결 확인")

