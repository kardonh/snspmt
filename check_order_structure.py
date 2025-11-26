#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
주문 구조 확인 - 패키지 주문이 개별로 보이는 이유 확인
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

def check_order_structure(order_id=None, user_id=None):
    """주문 구조 확인"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("=" * 80)
        print("🔍 주문 구조 확인 - 패키지 주문이 개별로 보이는 이유 분석")
        print("=" * 80)
        
        # 최근 패키지 주문 찾기
        if not order_id:
            cursor.execute("""
                SELECT order_id, user_id, status, package_steps
                FROM orders
                WHERE package_steps IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 1
            """)
            recent_order = cursor.fetchone()
            if recent_order:
                order_id = recent_order['order_id']
                user_id = recent_order['user_id']
                print(f"\n📦 최근 패키지 주문 발견: order_id={order_id}, user_id={user_id}")
        
        if not order_id:
            print("❌ 확인할 주문을 찾을 수 없습니다.")
            return
        
        # 1. orders 테이블 확인
        print(f"\n{'='*80}")
        print(f"1️⃣ orders 테이블 - 주문 ID: {order_id}")
        print(f"{'='*80}")
        cursor.execute("""
            SELECT 
                order_id,
                user_id,
                status,
                total_amount,
                final_amount,
                link,
                quantity,
                package_steps,
                created_at
            FROM orders
            WHERE order_id = %s
        """, (order_id,))
        order = cursor.fetchone()
        if order:
            order_dict = dict(order)
            print(f"   주문 1개 존재:")
            print(f"   - order_id: {order_dict['order_id']}")
            print(f"   - user_id: {order_dict['user_id']}")
            print(f"   - status: {order_dict['status']}")
            print(f"   - link: {order_dict.get('link', 'N/A')}")
            print(f"   - quantity: {order_dict.get('quantity', 'N/A')}")
            print(f"   - package_steps 존재: {order_dict.get('package_steps') is not None}")
        else:
            print("   ❌ 주문을 찾을 수 없습니다.")
            return
        
        # 2. order_items 테이블 확인
        print(f"\n{'='*80}")
        print(f"2️⃣ order_items 테이블 - 주문 ID: {order_id}")
        print(f"{'='*80}")
        cursor.execute("""
            SELECT 
                order_item_id,
                order_id,
                variant_id,
                quantity,
                unit_price,
                line_amount,
                link,
                status
            FROM order_items
            WHERE order_id = %s
            ORDER BY order_item_id ASC
        """, (order_id,))
        items = cursor.fetchall()
        
        if items:
            print(f"   ⚠️ order_items에 {len(items)}개 항목이 저장되어 있습니다:")
            for i, item in enumerate(items, 1):
                item_dict = dict(item)
                print(f"\n   항목 {i}:")
                print(f"   - order_item_id: {item_dict['order_item_id']}")
                print(f"   - order_id: {item_dict['order_id']}")
                print(f"   - variant_id: {item_dict.get('variant_id', 'N/A')}")
                print(f"   - quantity: {item_dict.get('quantity', 'N/A')}")
                print(f"   - link: {item_dict.get('link', 'N/A')}")
        else:
            print("   ✅ order_items에 항목이 없습니다 (일반 주문)")
        
        # 3. 현재 주문 조회 쿼리 시뮬레이션
        print(f"\n{'='*80}")
        print(f"3️⃣ 현재 주문 조회 쿼리 시뮬레이션 (get_orders API)")
        print(f"{'='*80}")
        
        cursor.execute("""
            SELECT 
                o.order_id, 
                o.status, 
                COALESCE(o.final_amount, o.total_amount, 0) as price,
                o.total_amount,
                o.created_at,
                o.smm_panel_order_id, 
                o.detailed_service,
                o.package_steps,
                COALESCE(
                    NULLIF(o.link, ''),
                    (SELECT link FROM order_items WHERE order_id = o.order_id AND link IS NOT NULL AND link != '' ORDER BY order_item_id ASC LIMIT 1)
                ) as link,
                COALESCE(
                    NULLIF(o.quantity, 0),
                    (SELECT SUM(quantity) FROM order_items WHERE order_id = o.order_id)
                ) as quantity,
                oi_first.variant_id,
                oi_first.unit_price,
                pv.name as variant_name, 
                pv.meta_json as variant_meta
            FROM orders o
            LEFT JOIN (
                SELECT DISTINCT ON (order_id)
                    order_id, variant_id, unit_price
                FROM order_items
                ORDER BY order_id, order_item_id ASC
            ) oi_first ON o.order_id = oi_first.order_id
            LEFT JOIN product_variants pv ON oi_first.variant_id = pv.variant_id
            WHERE o.order_id = %s
        """, (order_id,))
        
        result = cursor.fetchone()
        if result:
            result_dict = dict(result)
            print(f"   조회 결과: 1개 주문")
            print(f"   - order_id: {result_dict['order_id']}")
            print(f"   - link: {result_dict.get('link', 'N/A')}")
            print(f"   - quantity: {result_dict.get('quantity', 'N/A')}")
            print(f"   - variant_name: {result_dict.get('variant_name', 'N/A')}")
        
        # 4. 문제 분석
        print(f"\n{'='*80}")
        print(f"4️⃣ 문제 분석")
        print(f"{'='*80}")
        
        if len(items) > 1:
            print(f"\n   ⚠️ 문제 발견!")
            print(f"   - orders 테이블: 1개 주문")
            print(f"   - order_items 테이블: {len(items)}개 항목 (각 단계별로 저장됨)")
            print(f"\n   💡 원인:")
            print(f"   - 패키지 주문 생성 시 각 단계마다 order_items에 개별 저장 (코드 6028-6036줄)")
            print(f"   - 주문 내역 조회 시 orders 테이블만 조회하므로 1개로 표시되어야 함")
            print(f"   - 하지만 만약 order_items와 JOIN이 잘못되면 개별로 보일 수 있음")
            print(f"\n   ✅ 해결 방법:")
            print(f"   - 주문 내역 조회 시 orders 테이블만 조회 (이미 그렇게 되어 있음)")
            print(f"   - DISTINCT ON (order_id) 사용으로 중복 방지 (이미 사용 중)")
            print(f"   - 패키지 주문은 하나의 주문으로 표시, 상세 조회 시에만 단계별 표시")
        else:
            print(f"   ✅ 정상: orders 테이블과 일치합니다.")
        
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
    import sys
    order_id = sys.argv[1] if len(sys.argv) > 1 else None
    check_order_structure(order_id)

