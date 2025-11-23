"""
관리자 접속 문제 진단 스크립트
사용자의 이메일을 입력하면 데이터베이스에서 is_admin 상태를 확인합니다.
"""
import os
import sys
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# .env 파일 로드
load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')

def check_admin_status(email=None, user_id=None):
    """데이터베이스에서 관리자 상태 확인"""
    if not DATABASE_URL or not DATABASE_URL.startswith('postgresql://'):
        print("❌ PostgreSQL 데이터베이스가 아닙니다.")
        return
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("=" * 60)
        print("관리자 접속 진단 도구")
        print("=" * 60)
        
        # 이메일 또는 user_id로 조회
        if email:
            print(f"\n🔍 이메일로 조회: {email}")
            cursor.execute("""
                SELECT user_id, email, external_uid, is_admin, created_at
                FROM users 
                WHERE email = %s
                LIMIT 1
            """, (email,))
        elif user_id:
            print(f"\n🔍 external_uid로 조회: {user_id}")
            cursor.execute("""
                SELECT user_id, email, external_uid, is_admin, created_at
                FROM users 
                WHERE external_uid = %s
                LIMIT 1
            """, (user_id,))
        else:
            print("❌ 이메일 또는 user_id를 입력해주세요.")
            return
        
        user = cursor.fetchone()
        
        if not user:
            print(f"❌ 사용자를 찾을 수 없습니다.")
            print(f"\n📋 데이터베이스의 모든 사용자 목록 (최대 10개):")
            cursor.execute("""
                SELECT user_id, email, external_uid, is_admin 
                FROM users 
                ORDER BY created_at DESC 
                LIMIT 10
            """)
            all_users = cursor.fetchall()
            for u in all_users:
                print(f"   - email: {u['email']}, external_uid: {u['external_uid']}, is_admin: {u['is_admin']}")
            return
        
        print(f"\n✅ 사용자 발견!")
        print(f"   - user_id: {user['user_id']}")
        print(f"   - email: {user['email']}")
        print(f"   - external_uid: {user['external_uid']}")
        print(f"   - is_admin: {user['is_admin']} (타입: {type(user['is_admin'])})")
        print(f"   - created_at: {user['created_at']}")
        
        # is_admin 값 분석
        is_admin_raw = user['is_admin']
        is_admin_bool = None
        
        if is_admin_raw is None:
            is_admin_bool = False
            print(f"\n⚠️ is_admin이 None입니다. False로 처리됩니다.")
        elif isinstance(is_admin_raw, bool):
            is_admin_bool = is_admin_raw
            print(f"\n✅ is_admin이 불린 타입입니다: {is_admin_bool}")
        elif isinstance(is_admin_raw, (int, float)):
            is_admin_bool = bool(is_admin_raw and is_admin_raw != 0)
            print(f"\n✅ is_admin이 숫자 타입입니다: {is_admin_raw} -> {is_admin_bool}")
        else:
            # 문자열인 경우
            if str(is_admin_raw).lower() in ['true', '1', 'yes', 't']:
                is_admin_bool = True
            else:
                is_admin_bool = False
            print(f"\n✅ is_admin이 문자열 타입입니다: '{is_admin_raw}' -> {is_admin_bool}")
        
        print(f"\n{'=' * 60}")
        if is_admin_bool:
            print("✅ 관리자 권한이 있습니다!")
            print("   관리자 페이지에 접속할 수 있어야 합니다.")
        else:
            print("❌ 관리자 권한이 없습니다!")
            print("   관리자 페이지에 접속하려면 is_admin을 True로 설정해야 합니다.")
        print(f"{'=' * 60}")
        
        # JWT와의 매칭 확인
        print(f"\n📋 JWT 토큰과의 매칭 확인:")
        print(f"   - JWT의 'sub' (user_id)는 데이터베이스의 'external_uid'와 일치해야 합니다.")
        print(f"   - JWT의 'email'은 데이터베이스의 'email'과 일치해야 합니다.")
        print(f"\n   현재 데이터베이스 값:")
        print(f"   - external_uid: {user['external_uid']}")
        print(f"   - email: {user['email']}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("사용법:")
        print("  python check_admin_access.py <email>")
        print("  또는")
        print("  python check_admin_access.py --user-id <external_uid>")
        print("\n예시:")
        print("  python check_admin_access.py user@example.com")
        sys.exit(1)
    
    if sys.argv[1] == '--user-id' and len(sys.argv) > 2:
        check_admin_status(user_id=sys.argv[2])
    else:
        check_admin_status(email=sys.argv[1])

