#!/usr/bin/env python3
"""
사용자를 관리자로 설정하는 스크립트
사용법: python set_admin.py <email>
"""
import os
import sys
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# .env 파일에서 환경 변수 로드
try:
    load_dotenv(encoding='utf-8')
except:
    load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL 환경 변수가 설정되지 않았습니다.")
    sys.exit(1)

if len(sys.argv) < 2:
    print("사용법: python set_admin.py <email>")
    print("예: python set_admin.py user@example.com")
    sys.exit(1)

email = sys.argv[1]

try:
    # 데이터베이스 연결
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    print(f"🔍 사용자 찾기: {email}")
    
    # 사용자 찾기
    cursor.execute("""
        SELECT user_id, email, is_admin, external_uid
        FROM users 
        WHERE email = %s OR external_uid = %s
        LIMIT 1
    """, (email, email))
    
    user = cursor.fetchone()
    
    if not user:
        print(f"❌ 사용자를 찾을 수 없습니다: {email}")
        sys.exit(1)
    
    print(f"✅ 사용자 찾음:")
    print(f"   - user_id: {user['user_id']}")
    print(f"   - email: {user['email']}")
    print(f"   - 현재 is_admin: {user['is_admin']}")
    print(f"   - external_uid: {user.get('external_uid', 'N/A')}")
    
    # 관리자 권한 설정
    cursor.execute("""
        UPDATE users 
        SET is_admin = TRUE, updated_at = NOW()
        WHERE email = %s OR external_uid = %s
    """, (email, email))
    
    conn.commit()
    
    # 확인
    cursor.execute("""
        SELECT is_admin 
        FROM users 
        WHERE email = %s OR external_uid = %s
        LIMIT 1
    """, (email, email))
    
    updated_user = cursor.fetchone()
    
    if updated_user['is_admin']:
        print(f"✅ 관리자 권한 설정 완료! is_admin: {updated_user['is_admin']}")
    else:
        print(f"⚠️ 관리자 권한 설정 실패. is_admin: {updated_user['is_admin']}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ 오류 발생: {e}")
    import traceback
    print(traceback.format_exc())
    sys.exit(1)

