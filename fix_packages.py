#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
패키지 데이터 수정 스크립트
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

# 패키지 데이터 정의
PACKAGES = [
    {
        'name': '🎯 추천탭 상위노출 (내계정) - 진입단계 [4단계 패키지]',
        'price': 20000000,
        'description': '진입단계 4단계 완전 패키지',
        'time': '24-48시간',
        'steps': [
            {'service_id': 122, 'quantity': 300, 'delay': 0, 'repeat': 1},
            {'service_id': 329, 'quantity': 10000, 'delay': 10, 'repeat': 1},
            {'service_id': 328, 'quantity': 1000, 'delay': 10, 'repeat': 1},
            {'service_id': 342, 'quantity': 5, 'delay': 10, 'repeat': 1}
        ]
    },
    {
        'name': '🎯 추천탭 상위노출 (내계정) - 유지단계 [2단계 패키지]',
        'price': 15000000,
        'description': '유지단계 2단계 완전 패키지 (90분 간격, 각 단계 10회 반복)',
        'time': '30시간',
        'steps': [
            {'service_id': 325, 'quantity': 100, 'delay': 90, 'repeat': 10},
            {'service_id': 331, 'quantity': 200, 'delay': 90, 'repeat': 10}
        ]
    },
    {
        'name': '인스타 계정 상위노출 [30일]',
        'price': 150000000,
        'description': '인스타그램 프로필 방문 하루 400개씩 30일간',
        'time': '30일',
        'drip_feed': True,
        'runs': 30,
        'interval': 1440,
        'drip_quantity': 400,
        'smmkings_id': 515,
        'steps': []  # drip-feed는 steps가 없음
    }
]

def main():
    conn = None
    cursor = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("🔧 패키지 데이터 수정 중...\n")
        
        # 1. meta_json 컬럼 추가 (없으면)
        print("1️⃣ meta_json 컬럼 확인/추가 중...")
        try:
            cursor.execute("""
                ALTER TABLE packages 
                ADD COLUMN IF NOT EXISTS meta_json JSONB
            """)
            print("   ✅ meta_json 컬럼 확인 완료")
        except Exception as e:
            if 'already exists' not in str(e).lower() and 'duplicate' not in str(e).lower():
                print(f"   ⚠️  meta_json 컬럼 추가 실패 (이미 존재할 수 있음): {e}")
        
        conn.commit()
        
        for pkg_data in PACKAGES:
            # 패키지 찾기
            cursor.execute("SELECT package_id FROM packages WHERE name = %s", (pkg_data['name'],))
            pkg = cursor.fetchone()
            
            if not pkg:
                print(f"❌ 패키지를 찾을 수 없음: {pkg_data['name']}")
                continue
            
            package_id = pkg['package_id']
            print(f"\n📦 패키지 수정: {pkg_data['name']} (package_id={package_id})")
            
            # meta_json 생성
            meta_json = {
                'price': pkg_data['price'],
                'time': pkg_data['time'],
                'min': 1,
                'max': 1
            }
            
            if pkg_data.get('drip_feed'):
                meta_json['drip_feed'] = True
                meta_json['runs'] = pkg_data.get('runs')
                meta_json['interval'] = pkg_data.get('interval')
                meta_json['drip_quantity'] = pkg_data.get('drip_quantity')
                if pkg_data.get('smmkings_id'):
                    meta_json['smmkings_id'] = pkg_data['smmkings_id']
            
            # 패키지 업데이트 (meta_json, description)
            cursor.execute("""
                UPDATE packages 
                SET meta_json = %s::jsonb,
                    description = %s,
                    updated_at = NOW()
                WHERE package_id = %s
            """, (json.dumps(meta_json, ensure_ascii=False), pkg_data['description'], package_id))
            print(f"   ✅ meta_json 및 description 업데이트 완료")
            
            # 패키지 아이템 업데이트/추가
            if pkg_data.get('steps'):
                # 기존 아이템 삭제
                cursor.execute("DELETE FROM package_items WHERE package_id = %s", (package_id,))
                deleted_count = cursor.rowcount
                print(f"   🗑️  기존 아이템 {deleted_count}개 삭제")
                
                # 새 아이템 추가
                for step_idx, step in enumerate(pkg_data['steps'], 1):
                    # service_id로 variant_id 찾기
                    cursor.execute("""
                        SELECT variant_id FROM product_variants 
                        WHERE (meta_json->>'service_id')::text = %s
                        LIMIT 1
                    """, (str(step['service_id']),))
                    variant_result = cursor.fetchone()
                    
                    if variant_result:
                        variant_id = variant_result['variant_id']
                        
                        cursor.execute("""
                            INSERT INTO package_items (
                                package_id, variant_id, step, quantity,
                                term_value, term_unit, repeat_count,
                                created_at, updated_at
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                        """, (
                            package_id,
                            variant_id,
                            step_idx,
                            step['quantity'],
                            step['delay'],
                            'minute',
                            step.get('repeat', 1)
                        ))
                        print(f"   ✅ Step {step_idx} 추가: service_id={step['service_id']}, quantity={step['quantity']}, delay={step['delay']}분, repeat={step.get('repeat', 1)}회")
                    else:
                        print(f"   ⚠️  variant를 찾을 수 없음: service_id={step['service_id']}")
            else:
                print(f"   ℹ️  steps가 없음 (drip-feed 패키지)")
        
        conn.commit()
        print(f"\n✅ 패키지 수정 완료!")
        
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
