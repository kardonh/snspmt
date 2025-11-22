#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Home.jsx에 하드코딩된 상품 데이터를 데이터베이스에 추가하는 스크립트
"""
import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv

# .env 파일 로드
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
    
    print(f"🔗 데이터베이스 연결: {host}:{port}/{database}")
    
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

# Home.jsx에서 하드코딩된 상품 데이터 (패키지 포함)
HARDCODED_PRODUCTS = {
    # 패키지 상품
    'packages': [
        {
            'id': 1003,
            'name': '🎯 추천탭 상위노출 (내계정) - 진입단계 [4단계 패키지]',
            'price': 20000000,
            'description': '진입단계 4단계 완전 패키지',
            'time': '24-48시간',
            'category': '인스타그램',
            'steps': [
                {'id': 122, 'name': '1단계: 실제 한국인 게시물 좋아요 [진입 단계]', 'quantity': 300, 'delay': 0},
                {'id': 329, 'name': '2단계: 파워 게시물 노출 + 도달 + 기타 유입', 'quantity': 10000, 'delay': 10},
                {'id': 328, 'name': '3단계: 파워 게시물 저장 유입', 'quantity': 1000, 'delay': 10},
                {'id': 342, 'name': '4단계: KR 인스타그램 리얼 한국인 랜덤 댓글', 'quantity': 5, 'delay': 10}
            ]
        },
        {
            'id': 1004,
            'name': '🎯 추천탭 상위노출 (내계정) - 유지단계 [2단계 패키지]',
            'price': 15000000,
            'description': '유지단계 2단계 완전 패키지 (90분 간격, 각 단계 10회 반복)',
            'time': '30시간',
            'category': '인스타그램',
            'steps': [
                {'id': 325, 'name': '1단계: 실제 한국인 게시물 좋아요 [90분당 100개씩 10회]', 'quantity': 100, 'delay': 90, 'repeat': 10},
                {'id': 331, 'name': '2단계: 게시물 노출+도달+홈 [90분당 200개씩 10회]', 'quantity': 200, 'delay': 90, 'repeat': 10}
            ]
        },
        {
            'id': 1005,
            'name': '인스타 계정 상위노출 [30일]',
            'price': 150000000,
            'description': '인스타그램 프로필 방문 하루 400개씩 30일간',
            'time': '30일',
            'category': '인스타그램',
            'drip_feed': True,
            'runs': 30,
            'interval': 1440,
            'drip_quantity': 400,
            'smmkings_id': 515
        }
    ],
    
    # 일반 상품들 (상세 서비스 - variants)
    'variants': [
        # popular_posts
        {'id': 361, 'name': '🥇인기게시물 상위 노출[🎨사진] TI1', 'price': 3000000, 'min': 1, 'max': 10, 'time': '6 시간 10 분'},
        {'id': 444, 'name': '🥇인기게시물 상위 노출 유지[🎨사진] TI1-1', 'price': 90000, 'min': 100, 'max': 3000},
        {'id': 435, 'name': '🥇인기게시물 상위 노출[🎬릴스] TV1', 'price': 12000000, 'min': 1, 'max': 10, 'time': '23 시간 32 분'},
        {'id': 443, 'name': '🥇인기게시물 상위 노출[🎨사진] TI2', 'price': 27000, 'min': 100, 'max': 500, 'time': '16 분'},
        {'id': 445, 'name': '🥇인기게시물 상위 노출 유지[🎨사진] TI2-1', 'price': 90000, 'min': 100, 'max': 3000},
        {'id': 332, 'name': '0️⃣.[준비단계]:최적화 계정 준비', 'price': 0, 'min': 1, 'max': 1},
        {'id': 325, 'name': '1️⃣.[상승단계]:리얼 한국인 좋아요 유입', 'price': 19500, 'min': 100, 'max': 10000},
        {'id': 326, 'name': '2️⃣.[상승단계]:리얼 한국인 댓글 유입', 'price': 225000, 'min': 10, 'max': 300},
        {'id': 327, 'name': '3️⃣.[상승단계]:파워 외국인 좋아요 유입', 'price': 1800, 'min': 100, 'max': 200000},
        {'id': 328, 'name': '4️⃣.[등록단계]:파워 게시물 저장 유입', 'price': 315, 'min': 100, 'max': 1000000, 'time': '1 시간 52 분'},
        {'id': 329, 'name': '5️⃣.[등록단계]:파워 게시물 노출 + 도달 + 홈 유입', 'price': 450, 'min': 1000, 'max': 1000000},
        {'id': 330, 'name': '6️⃣.[유지단계]:파워 게시물 저장 [✔연속 유입] 작업', 'price': 300, 'min': 100, 'max': 1000000, 'time': '7 시간 5 분'},
        {'id': 331, 'name': '7️⃣.[유지단계]:게시물 노출+도달+홈 [✔연속 유입] 작업', 'price': 450, 'min': 100, 'max': 1000000},
        
        # likes_korean
        {'id': 122, 'name': 'KR 인스타그램 한국인 ❤️ 파워업 좋아요', 'price': 20000, 'min': 30, 'max': 2500, 'time': '14시간 54분'},
        {'id': 333, 'name': 'KR 인스타그램 한국인 ❤️ 슈퍼프리미엄 좋아요', 'price': 30000, 'min': 100, 'max': 1000},
        {'id': 276, 'name': 'KR 인스타그램 리얼 한국인 [여자] 좋아요', 'price': 30000, 'min': 30, 'max': 5000, 'time': '9분'},
        {'id': 275, 'name': 'KR 인스타그램 리얼 한국인 [남자] 좋아요', 'price': 30000, 'min': 30, 'max': 5000, 'time': '10분'},
        
        # followers_korean
        {'id': 491, 'name': 'KR 인스타그램 💯 리얼 한국인 팔로워 [일반]', 'price': 160000, 'min': 10, 'max': 1000},
        {'id': 334, 'name': 'KR 인스타그램 💯 리얼 한국인 팔로워 [디럭스]', 'price': 210000, 'min': 10, 'max': 40000, 'time': '1시간 3분'},
        {'id': 383, 'name': 'KR 인스타그램 💯 리얼 한국인 팔로워 [프리미엄]', 'price': 270000, 'min': 10, 'max': 40000, 'time': '1시간 3분'},
        
        # 기타 중요한 상품들
        {'id': 342, 'name': 'KR 인스타그램 리얼 한국인 랜덤 댓글', 'price': 260000, 'min': 5, 'max': 5000},
        {'id': 305, 'name': 'KR 인스타그램 한국인 리그램', 'price': 450000, 'min': 3, 'max': 3000, 'time': '6시간 12분'},
        {'id': 111, 'name': 'KR 인스타그램 리얼 한국인 동영상 조회수', 'price': 2000, 'min': 100, 'max': 2147483647, 'time': '20시간 33분'},
        {'id': 515, 'name': '인스타그램 프로필 방문', 'price': 1000, 'min': 10, 'max': 10000},
    ]
}

def main():
    conn = None
    cursor = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("📦 하드코딩된 상품 데이터를 데이터베이스에 추가합니다...\n")
        
        # 1. 카테고리 확인/생성
        print("1️⃣ 카테고리 확인 중...")
        cursor.execute("SELECT category_id, name FROM categories WHERE name = %s", ('인스타그램',))
        instagram_category = cursor.fetchone()
        
        if not instagram_category:
            cursor.execute("""
                INSERT INTO categories (name, slug, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, NOW(), NOW())
                RETURNING category_id
            """, ('인스타그램', 'instagram', True))
            instagram_category = cursor.fetchone()
            print(f"   ✅ 인스타그램 카테고리 생성: category_id={instagram_category['category_id']}")
        else:
            print(f"   ✅ 인스타그램 카테고리 확인: category_id={instagram_category['category_id']}")
        
        category_id = instagram_category['category_id']
        
        # 2. 상품 확인/생성 (패키지를 위한 상품)
        print("\n2️⃣ 상품 확인/생성 중...")
        
        # 패키지 상품용 상품 확인/생성
        cursor.execute("SELECT product_id, name FROM products WHERE name LIKE %s AND category_id = %s", ('%패키지%', category_id))
        package_product = cursor.fetchone()
        
        if not package_product:
            cursor.execute("""
                INSERT INTO products (category_id, name, description, is_domestic, created_at, updated_at)
                VALUES (%s, %s, %s, %s, NOW(), NOW())
                RETURNING product_id
            """, (category_id, '인스타그램 패키지 상품', '인스타그램 패키지 서비스', True))
            package_product = cursor.fetchone()
            print(f"   ✅ 패키지 상품 생성: product_id={package_product['product_id']}")
        else:
            print(f"   ✅ 패키지 상품 확인: product_id={package_product['product_id']}")
        
        package_product_id = package_product['product_id']
        
        # 3. 패키지 추가
        print("\n3️⃣ 패키지 추가 중...")
        added_packages = 0
        
        for pkg in HARDCODED_PRODUCTS['packages']:
            # 패키지가 이미 존재하는지 확인 (이름으로)
            cursor.execute("SELECT package_id FROM packages WHERE name = %s", (pkg['name'],))
            existing = cursor.fetchone()
            
            if existing:
                print(f"   ⏭️  패키지 이미 존재: {pkg['name']}")
                continue
            
            # meta_json 생성 (price는 meta_json에 저장)
            meta_json = {
                'time': pkg.get('time', '데이터가 충분하지 않습니다'),
                'drip_feed': pkg.get('drip_feed', False),
                'price': pkg.get('price', 0),
                'min': 1,
                'max': 1
            }
            
            if pkg.get('runs'):
                meta_json['runs'] = pkg['runs']
            if pkg.get('interval'):
                meta_json['interval'] = pkg['interval']
            if pkg.get('drip_quantity'):
                meta_json['drip_quantity'] = pkg['drip_quantity']
            if pkg.get('smmkings_id'):
                meta_json['smmkings_id'] = pkg['smmkings_id']
            
            # 패키지 생성 (meta_json 컬럼이 없을 수 있으므로 예외 처리)
            try:
                cursor.execute("""
                    INSERT INTO packages (category_id, name, description, meta_json, created_at, updated_at)
                    VALUES (%s, %s, %s, %s::jsonb, NOW(), NOW())
                    RETURNING package_id
                """, (category_id, pkg['name'], pkg.get('description', ''), json.dumps(meta_json, ensure_ascii=False)))
            except Exception as e:
                # meta_json 컬럼이 없으면 meta_json 없이 다시 시도
                if 'meta_json' in str(e).lower() or 'column' in str(e).lower():
                    cursor.execute("""
                        INSERT INTO packages (category_id, name, description, created_at, updated_at)
                        VALUES (%s, %s, %s, NOW(), NOW())
                        RETURNING package_id
                    """, (category_id, pkg['name'], pkg.get('description', '')))
                else:
                    raise
            
            package_result = cursor.fetchone()
            package_db_id = package_result['package_id']
            print(f"   ✅ 패키지 추가: {pkg['name']} (package_id={package_db_id})")
            
            # 패키지 아이템 추가
            if pkg.get('steps'):
                for step_idx, step in enumerate(pkg['steps'], 1):
                    # variant_id 찾기 (service_id로)
                    variant_id = None
                    if step.get('id'):
                        cursor.execute("""
                            SELECT variant_id FROM product_variants 
                            WHERE (meta_json->>'service_id')::text = %s
                            LIMIT 1
                        """, (str(step['id']),))
                        variant_result = cursor.fetchone()
                        if variant_result:
                            variant_id = variant_result['variant_id']
                    
                    if variant_id:
                        # package_items에 추가
                        cursor.execute("""
                            INSERT INTO package_items (
                                package_id, variant_id, step, quantity,
                                term_value, term_unit, repeat_count,
                                created_at, updated_at
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                        """, (
                            package_db_id,
                            variant_id,
                            step_idx,
                            step.get('quantity', 0),
                            step.get('delay', 0),  # term_value
                            'minute',  # term_unit
                            step.get('repeat', 1)  # repeat_count
                        ))
                        print(f"      ✅ 패키지 아이템 추가: {step['name']} (step={step_idx})")
                    else:
                        print(f"      ⚠️  variant를 찾을 수 없음: service_id={step.get('id')} - {step['name']}")
            
            added_packages += 1
        
        # 4. 일반 상품 variants 추가
        print("\n4️⃣ 상품 variants 추가 중...")
        added_variants = 0
        
        # 상품 확인/생성 (일반 상품용)
        cursor.execute("SELECT product_id FROM products WHERE name = %s AND category_id = %s", ('인스타그램 일반 상품', category_id))
        general_product = cursor.fetchone()
        
        if not general_product:
            cursor.execute("""
                INSERT INTO products (category_id, name, description, is_domestic, created_at, updated_at)
                VALUES (%s, %s, %s, %s, NOW(), NOW())
                RETURNING product_id
            """, (category_id, '인스타그램 일반 상품', '인스타그램 일반 서비스', True))
            general_product = cursor.fetchone()
        
        general_product_id = general_product['product_id']
        
        for variant in HARDCODED_PRODUCTS['variants']:
            # 이미 존재하는지 확인
            cursor.execute("""
                SELECT variant_id FROM product_variants 
                WHERE product_id = %s 
                  AND (meta_json->>'service_id')::text = %s
            """, (general_product_id, str(variant['id'])))
            existing = cursor.fetchone()
            
            if existing:
                print(f"   ⏭️  variant 이미 존재: {variant['name']}")
                continue
            
            # meta_json 생성
            meta_json = {
                'service_id': str(variant['id']),
                'time': variant.get('time', '데이터가 충분하지 않습니다')
            }
            
            # variant 추가
            cursor.execute("""
                INSERT INTO product_variants (
                    product_id, name, price, min_quantity, max_quantity,
                    delivery_time_days, is_active, meta_json, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, NOW(), NOW())
                RETURNING variant_id
            """, (
                general_product_id,
                variant['name'],
                variant['price'],
                variant['min'],
                variant['max'],
                None,  # delivery_time_days
                True,
                json.dumps(meta_json)
            ))
            
            added_variants += 1
            print(f"   ✅ variant 추가: {variant['name']}")
        
        conn.commit()
        print(f"\n✅ 완료!")
        print(f"   - 패키지 추가: {added_packages}개")
        print(f"   - Variant 추가: {added_variants}개")
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    main()

