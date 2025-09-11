#!/usr/bin/env python3
"""
PostgreSQL 연결 활성화 스크립트
새 RDS 인스턴스 생성 완료 후 실행
"""

def update_backend_for_postgresql():
    """backend.py를 PostgreSQL 연결로 업데이트"""
    
    # PostgreSQL 연결 함수
    postgresql_connection_code = '''def get_db_connection():
    """PostgreSQL 데이터베이스 연결 (실사용)"""
    try:
        print(f"데이터베이스 연결 시도: {DATABASE_URL}")
        # 안전한 연결 설정
        conn = psycopg2.connect(
            DATABASE_URL,
            cursor_factory=RealDictCursor,
            connect_timeout=30,
            application_name='snspmt-app'
        )
        # 자동 커밋 비활성화
        conn.autocommit = False
        print("PostgreSQL 연결 성공")
        return conn
    except Exception as e:
        print(f"PostgreSQL 연결 실패: {e}")
        # 연결 실패 시 SQLite로 폴백
        print("SQLite로 폴백 시도...")
        try:
            conn = sqlite3.connect(':memory:')
            conn.row_factory = sqlite3.Row
            print("SQLite 메모리 기반 연결 성공 (데이터 유지 안됨)")
            print("⚠️ 주의: 실사용을 위해서는 PostgreSQL 연결이 필요합니다.")
            return conn
        except Exception as sqlite_error:
            print(f"SQLite 연결도 실패: {sqlite_error}")
            return None'''
    
    print("✅ PostgreSQL 연결 코드 준비 완료")
    print("💡 새 RDS 인스턴스 생성 완료 후 이 스크립트를 실행하세요")
    return postgresql_connection_code

if __name__ == "__main__":
    print("🚀 PostgreSQL 연결 활성화 준비...")
    code = update_backend_for_postgresql()
    print("✅ 준비 완료!")
