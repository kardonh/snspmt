#!/usr/bin/env python3
"""
snspmt 데이터베이스 생성 스크립트
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def create_database():
    """snspmt 데이터베이스 생성"""
    try:
        # postgres 데이터베이스에 연결
        conn = psycopg2.connect(
            host="snspmt-db.cvmiee0q0zhs.ap-northeast-2.rds.amazonaws.com",
            port=5432,
            user="snspmt_admin",
            password="Snspmt2024!",
            database="postgres"
        )
        
        # 자동 커밋 모드 설정
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # snspmt 데이터베이스 생성
        cursor.execute("CREATE DATABASE snspmt;")
        print("✅ snspmt 데이터베이스가 성공적으로 생성되었습니다.")
        
        # 연결 종료
        cursor.close()
        conn.close()
        
        return True
        
    except psycopg2.errors.DuplicateDatabase:
        print("ℹ️ snspmt 데이터베이스가 이미 존재합니다.")
        return True
        
    except Exception as e:
        print(f"❌ 데이터베이스 생성 실패: {e}")
        return False

if __name__ == "__main__":
    print("🚀 snspmt 데이터베이스 생성 시작...")
    success = create_database()
    
    if success:
        print("🎉 데이터베이스 생성 완료!")
        print("이제 애플리케이션이 PostgreSQL에 연결됩니다.")
    else:
        print("💥 데이터베이스 생성에 실패했습니다.")
        print("AWS 콘솔에서 수동으로 생성해주세요.")
