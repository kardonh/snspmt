#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
packages 테이블에 product_id 컬럼 추가 및 기존 데이터 업데이트
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

def add_product_id_column():
    """packages 테이블에 product_id 컬럼 추가"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("=" * 80)
        print("📦 packages 테이블에 product_id 컬럼 추가")
        print("=" * 80)
        
        # 1. product_id 컬럼 존재 여부 확인
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'packages' AND column_name = 'product_id'
        """)
        has_product_id = cursor.fetchone() is not None
        
        if has_product_id:
            print("✅ product_id 컬럼이 이미 존재합니다.")
        else:
            # 2. product_id 컬럼 추가
            print("\n1️⃣ product_id 컬럼 추가 중...")
            cursor.execute("""
                ALTER TABLE packages 
                ADD COLUMN product_id BIGINT REFERENCES products(product_id)
            """)
            conn.commit()
            print("✅ product_id 컬럼 추가 완료")
        
        # 3. 기존 패키지들의 product_id 업데이트
        print("\n2️⃣ 기존 패키지의 product_id 업데이트 중...")
        
        # category_id로 첫 번째 상품 찾기
        cursor.execute("""
            SELECT 
                p.package_id,
                p.category_id,
                (SELECT product_id FROM products 
                 WHERE category_id = p.category_id 
                 ORDER BY product_id ASC 
                 LIMIT 1) as first_product_id
            FROM packages p
            WHERE p.product_id IS NULL
        """)
        
        packages_to_update = cursor.fetchall()
        
        updated_count = 0
        for pkg in packages_to_update:
            pkg_dict = dict(pkg)
            package_id = pkg_dict['package_id']
            category_id = pkg_dict['category_id']
            first_product_id = pkg_dict['first_product_id']
            
            if first_product_id:
                cursor.execute("""
                    UPDATE packages 
                    SET product_id = %s 
                    WHERE package_id = %s
                """, (first_product_id, package_id))
                updated_count += 1
                print(f"   ✅ 패키지 {package_id}: product_id = {first_product_id} (category_id: {category_id})")
            else:
                print(f"   ⚠️ 패키지 {package_id}: 해당 카테고리에 상품이 없음 (category_id: {category_id})")
        
        conn.commit()
        print(f"\n✅ {updated_count}개 패키지 업데이트 완료")
        
        # 4. 최종 확인
        print("\n3️⃣ 최종 확인:")
        cursor.execute("""
            SELECT 
                p.package_id,
                p.name,
                p.product_id,
                p.category_id,
                pr.name as product_name
            FROM packages p
            LEFT JOIN products pr ON p.product_id = pr.product_id
            ORDER BY p.package_id DESC
            LIMIT 10
        """)
        
        packages = cursor.fetchall()
        print(f"\n📦 패키지 목록 (최근 10개):")
        for pkg in packages:
            pkg_dict = dict(pkg)
            print(f"   패키지 {pkg_dict['package_id']}: {pkg_dict['name']}")
            print(f"      product_id: {pkg_dict.get('product_id', 'NULL')}")
            print(f"      상품: {pkg_dict.get('product_name', 'N/A')}")
        
        print("\n" + "=" * 80)
        print("✅ 마이그레이션 완료!")
        print("=" * 80)
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    add_product_id_column()

