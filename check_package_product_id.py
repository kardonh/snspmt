#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
패키지의 product_id 확인 스크립트
"""
import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    """데이터베이스 연결"""
    if not DATABASE_URL:
        raise Exception("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
    
    parsed = urlparse(DATABASE_URL)
    user_info = parsed.username
    password = unquote(parsed.password) if parsed.password else ''
    host = parsed.hostname
    port = parsed.port or 5432
    database = parsed.path.lstrip('/') or 'postgres'
    
    if user_info and '.' in user_info:
        user = user_info
    else:
        user = user_info or 'postgres'
    
    conn = psycopg2.connect(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        connect_timeout=30
    )
    return conn

def check_packages():
    """패키지의 product_id 확인"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # product_id 컬럼 존재 여부 확인
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'packages' AND column_name = 'product_id'
        """)
        has_product_id = cursor.fetchone() is not None
        print(f"📋 packages 테이블에 product_id 컬럼 존재: {has_product_id}")
        
        # 패키지 목록 조회
        if has_product_id:
            cursor.execute("""
                SELECT 
                    p.package_id,
                    p.name,
                    p.product_id,
                    p.category_id,
                    pr.name as product_name,
                    c.name as category_name
                FROM packages p
                LEFT JOIN products pr ON p.product_id = pr.product_id
                LEFT JOIN categories c ON p.category_id = c.category_id
                ORDER BY p.created_at DESC
            """)
        else:
            cursor.execute("""
                SELECT 
                    p.package_id,
                    p.name,
                    p.category_id,
                    c.name as category_name
                FROM packages p
                LEFT JOIN categories c ON p.category_id = c.category_id
                ORDER BY p.created_at DESC
            """)
        
        packages = cursor.fetchall()
        
        print(f"\n📦 패키지 목록 ({len(packages)}개):")
        print("=" * 80)
        
        for pkg in packages:
            pkg_dict = dict(pkg)
            print(f"\n패키지 ID: {pkg_dict['package_id']}")
            print(f"  이름: {pkg_dict['name']}")
            if has_product_id:
                print(f"  product_id: {pkg_dict.get('product_id', 'NULL')}")
                print(f"  상품 이름: {pkg_dict.get('product_name', 'N/A')}")
            print(f"  category_id: {pkg_dict.get('category_id', 'NULL')}")
            print(f"  카테고리 이름: {pkg_dict.get('category_name', 'N/A')}")
        
        if not has_product_id:
            print(f"\n⚠️ packages 테이블에 product_id 컬럼이 없습니다!")
            print(f"   패키지를 상품의 세부서비스로 표시하려면 product_id 컬럼이 필요합니다.")
            print(f"\n💡 해결 방법:")
            print(f"   1. 데이터베이스 마이그레이션 실행")
            print(f"   2. 또는 ALTER TABLE로 product_id 컬럼 추가")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    check_packages()

