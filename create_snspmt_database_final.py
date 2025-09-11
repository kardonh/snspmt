#!/usr/bin/env python3
"""
snspmt-cluster에 snspmt 데이터베이스 생성
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def create_database():
    """snspmt 데이터베이스 생성"""
    try:
        # postgres 데이터베이스에 연결 (기본 데이터베이스)
        conn = psycopg2.connect(
            host="snspmt-cluster.cluster-cvmiee0q0zhs.ap-northeast-2.rds.amazonaws.com",
            port=5432,
            user="snspmt_admin",
            password="Snspmt2024!",
            database="postgres"  # 기본 데이터베이스
        )
        
        # 자동 커밋 모드 설정
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # snspmt 데이터베이스 생성
        cursor.execute("CREATE DATABASE snspmt;")
        print("✅ snspmt 데이터베이스 생성 완료!")
        
        cursor.close()
        conn.close()
        
    except psycopg2.errors.DuplicateDatabase:
        print("✅ snspmt 데이터베이스가 이미 존재합니다!")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    create_database()
