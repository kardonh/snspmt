#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
packages 테이블에 product_id 컬럼 추가 (간단 버전)
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

def migrate():
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
            # 2. product_id 컬럼 추가 (IF NOT EXISTS는 PostgreSQL에서 지원 안 함)
            print("\n1️⃣ product_id 컬럼 추가 중...")
            try:
                cursor.execute("""
                    ALTER TABLE packages 
                    ADD COLUMN product_id BIGINT
                """)
                conn.commit()
                print("✅ product_id 컬럼 추가 완료")
            except Exception as e:
                if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
                    print("✅ product_id 컬럼이 이미 존재합니다.")
                else:
                    raise
        
        # 3. 외래 키 제약 조건 추가 (없는 경우)
        print("\n2️⃣ 외래 키 제약 조건 확인 중...")
        try:
            cursor.execute("""
                SELECT constraint_name 
                FROM information_schema.table_constraints 
                WHERE table_name = 'packages' 
                AND constraint_type = 'FOREIGN KEY'
                AND constraint_name LIKE '%product_id%'
            """)
            fk_exists = cursor.fetchone() is not None
            
            if not fk_exists:
                print("   외래 키 제약 조건 추가 중...")
                cursor.execute("""
                    ALTER TABLE packages 
                    ADD CONSTRAINT packages_product_id_fkey 
                    FOREIGN KEY (product_id) REFERENCES products(product_id)
                """)
                conn.commit()
                print("✅ 외래 키 제약 조건 추가 완료")
            else:
                print("✅ 외래 키 제약 조건이 이미 존재합니다.")
        except Exception as e:
            if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
                print("✅ 외래 키 제약 조건이 이미 존재합니다.")
            else:
                print(f"⚠️ 외래 키 제약 조건 추가 실패 (무시): {e}")
                conn.rollback()
        
        # 4. 기존 패키지들의 product_id 업데이트
        print("\n3️⃣ 기존 패키지의 product_id 업데이트 중...")
        cursor.execute("""
            UPDATE packages p
            SET product_id = (
                SELECT product_id 
                FROM products pr 
                WHERE pr.category_id = p.category_id 
                ORDER BY pr.product_id ASC 
                LIMIT 1
            )
            WHERE p.product_id IS NULL
        """)
        updated_count = cursor.rowcount
        conn.commit()
        
        if updated_count > 0:
            print(f"✅ {updated_count}개 패키지 업데이트 완료")
        else:
            print("ℹ️ 업데이트할 패키지가 없습니다.")
        
        # 5. 최종 확인
        print("\n4️⃣ 최종 확인:")
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
        sys.exit(1)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate()

