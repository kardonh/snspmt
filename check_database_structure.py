#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
데이터베이스 구조 확인: 세부서비스와 패키지
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

def check_structure():
    """데이터베이스 구조 확인"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("=" * 80)
        print("📊 데이터베이스 구조 확인: 세부서비스와 패키지")
        print("=" * 80)
        
        # 1. product_variants 테이블 구조 확인
        print("\n1️⃣ product_variants 테이블 구조:")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'product_variants'
            ORDER BY ordinal_position
        """)
        variant_columns = cursor.fetchall()
        for col in variant_columns:
            print(f"   - {col['column_name']}: {col['data_type']} ({'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'})")
        
        # 2. product_variants 샘플 데이터 확인
        print("\n2️⃣ product_variants 샘플 데이터 (최근 3개):")
        cursor.execute("""
            SELECT 
                v.variant_id,
                v.product_id,
                v.category_id,
                v.name,
                v.price,
                p.name as product_name,
                c.name as category_name
            FROM product_variants v
            LEFT JOIN products p ON v.product_id = p.product_id
            LEFT JOIN categories c ON v.category_id = c.category_id
            ORDER BY v.variant_id DESC
            LIMIT 3
        """)
        variants = cursor.fetchall()
        for v in variants:
            print(f"\n   세부서비스 ID: {v['variant_id']}")
            print(f"   이름: {v['name']}")
            print(f"   product_id: {v['product_id']}")
            print(f"   상품: {v['product_name']}")
            print(f"   category_id: {v['category_id']}")
            print(f"   카테고리: {v['category_name']}")
            print(f"   가격: {v['price']}")
        
        # 3. packages 테이블 구조 확인
        print("\n3️⃣ packages 테이블 구조:")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'packages'
            ORDER BY ordinal_position
        """)
        package_columns = cursor.fetchall()
        for col in package_columns:
            print(f"   - {col['column_name']}: {col['data_type']} ({'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'})")
        
        # 4. packages 샘플 데이터 확인
        print("\n4️⃣ packages 샘플 데이터 (최근 3개):")
        cursor.execute("""
            SELECT 
                p.package_id,
                p.product_id,
                p.category_id,
                p.name,
                p.description,
                pr.name as product_name,
                c.name as category_name
            FROM packages p
            LEFT JOIN products pr ON p.product_id = pr.product_id
            LEFT JOIN categories c ON p.category_id = c.category_id
            ORDER BY p.package_id DESC
            LIMIT 3
        """)
        packages = cursor.fetchall()
        for pkg in packages:
            print(f"\n   패키지 ID: {pkg['package_id']}")
            print(f"   이름: {pkg['name']}")
            print(f"   product_id: {pkg.get('product_id', 'NULL')}")
            print(f"   상품: {pkg.get('product_name', 'N/A')}")
            print(f"   category_id: {pkg['category_id']}")
            print(f"   카테고리: {pkg.get('category_name', 'N/A')}")
        
        # 5. package_items 샘플 데이터 확인
        print("\n5️⃣ package_items 샘플 데이터 (최근 패키지의 items):")
        cursor.execute("""
            SELECT 
                pi.package_item_id,
                pi.package_id,
                pi.variant_id,
                pi.step,
                pi.quantity,
                pi.term_value,
                pi.term_unit,
                pi.repeat_count,
                p.name as package_name,
                pv.name as variant_name
            FROM package_items pi
            LEFT JOIN packages p ON pi.package_id = p.package_id
            LEFT JOIN product_variants pv ON pi.variant_id = pv.variant_id
            ORDER BY pi.package_id DESC, pi.step ASC
            LIMIT 10
        """)
        items = cursor.fetchall()
        for item in items:
            print(f"\n   패키지: {item['package_name']}")
            print(f"   단계: {item['step']}")
            print(f"   세부서비스: {item.get('variant_name', 'N/A')} (variant_id: {item['variant_id']})")
            print(f"   수량: {item['quantity']}")
            print(f"   지연: {item['term_value']} {item['term_unit']}")
            print(f"   반복: {item.get('repeat_count', 0)}회")
        
        print("\n" + "=" * 80)
        print("✅ 구조 확인 완료!")
        print("=" * 80)
        
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
    check_structure()

