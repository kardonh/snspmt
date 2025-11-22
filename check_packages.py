#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
패키지 상태 확인 스크립트
"""
import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    raise Exception("DATABASE_URL 환경 변수가 설정되지 않았습니다.")

def get_db_connection():
    """데이터베이스 연결"""
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
    conn.autocommit = False
    return conn

def main():
    conn = None
    cursor = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("🔍 패키지 상태 확인 중...\n")
        
        # 패키지 목록 조회
        cursor.execute("""
            SELECT p.*, c.name as category_name
            FROM packages p
            LEFT JOIN categories c ON p.category_id = c.category_id
            WHERE p.name LIKE '%추천탭%' OR p.name LIKE '%상위노출%'
            ORDER BY p.created_at DESC
        """)
        
        packages = cursor.fetchall()
        
        print(f"📦 패키지 개수: {len(packages)}개\n")
        
        for pkg in packages:
            pkg_dict = dict(pkg)
            print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print(f"패키지 ID: {pkg_dict['package_id']}")
            print(f"이름: {pkg_dict['name']}")
            print(f"설명: {pkg_dict.get('description', 'N/A')}")
            print(f"카테고리: {pkg_dict.get('category_name', 'N/A')}")
            
            # meta_json 확인
            meta_json = pkg_dict.get('meta_json')
            if meta_json:
                if isinstance(meta_json, str):
                    try:
                        meta_json = json.loads(meta_json)
                    except:
                        pass
                print(f"meta_json: {json.dumps(meta_json, ensure_ascii=False, indent=2)}")
            else:
                print("meta_json: 없음 ❌")
            
            # 패키지 아이템 확인
            cursor.execute("""
                SELECT pi.*, pv.name as variant_name, pv.variant_id
                FROM package_items pi
                LEFT JOIN product_variants pv ON pi.variant_id = pv.variant_id
                WHERE pi.package_id = %s
                ORDER BY pi.step
            """, (pkg_dict['package_id'],))
            
            items = cursor.fetchall()
            print(f"\n패키지 아이템 개수: {len(items)}개")
            
            if len(items) == 0:
                print("⚠️  패키지 아이템이 없습니다! ❌")
            else:
                for item in items:
                    item_dict = dict(item)
                    print(f"  - Step {item_dict['step']}: {item_dict.get('variant_name', 'N/A')} (variant_id: {item_dict.get('variant_id')})")
                    print(f"    수량: {item_dict.get('quantity')}, 지연: {item_dict.get('term_value')}분, 반복: {item_dict.get('repeat_count', 1)}회")
            
            print()
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    main()

