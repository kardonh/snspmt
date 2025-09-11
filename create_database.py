#!/usr/bin/env python3
"""
PostgreSQL 데이터베이스 생성 스크립트
기존 RDS 인스턴스에 'snspmt' 데이터베이스를 생성합니다.
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys

# RDS 연결 정보
HOST = "snspmt-db.cvmiee0q0zhs.ap-northeast-2.rds.amazonaws.com"
PORT = 5432
USER = "snspmt_admin"
PASSWORD = "Snspmt2024!"
DATABASE = "postgres"  # 기본 데이터베이스에 연결

def create_database():
    """snspmt 데이터베이스 생성"""
    try:
        print(f"RDS 인스턴스에 연결 중: {HOST}:{PORT}")
        
        # 기본 postgres 데이터베이스에 연결
        conn = psycopg2.connect(
            host=HOST,
            port=PORT,
            user=USER,
            password=PASSWORD,
            database=DATABASE
        )
        
        # 자동 커밋 모드 설정
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # 데이터베이스 존재 여부 확인
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'snspmt';")
        exists = cursor.fetchone()
        
        if exists:
            print("✅ 'snspmt' 데이터베이스가 이미 존재합니다.")
        else:
            # 데이터베이스 생성
            cursor.execute("CREATE DATABASE snspmt;")
            print("✅ 'snspmt' 데이터베이스가 성공적으로 생성되었습니다.")
        
        # 연결 종료
        cursor.close()
        conn.close()
        
        print("✅ 데이터베이스 생성 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 데이터베이스 생성 실패: {e}")
        return False

if __name__ == "__main__":
    print("🚀 PostgreSQL 데이터베이스 생성 시작...")
    success = create_database()
    
    if success:
        print("🎉 데이터베이스 생성이 완료되었습니다!")
        print("💡 이제 backend.py에서 PostgreSQL 연결을 활성화할 수 있습니다.")
    else:
        print("❌ 데이터베이스 생성에 실패했습니다.")
        print("💡 AWS RDS 콘솔에서 수동으로 데이터베이스를 생성해주세요.")
    
    sys.exit(0 if success else 1)
