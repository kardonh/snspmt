#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
패키지 7번 주문 생성 스크립트 (데이터베이스 직접 조회)
"""
import os
import sys
import json
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')
BACKEND_URL = os.environ.get('BACKEND_URL', 'http://localhost:8000')
API_URL = f"{BACKEND_URL}/api"

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
    
    print(f"🔗 데이터베이스 연결: {host}:{port}/{database}")
    
    conn = psycopg2.connect(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        connect_timeout=30
    )
    return conn

def get_package_from_db(package_id=7):
    """데이터베이스에서 패키지 정보 직접 조회"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 패키지 정보 조회
        cursor.execute("""
            SELECT p.*, c.name as category_name
            FROM packages p
            LEFT JOIN categories c ON p.category_id = c.category_id
            WHERE p.package_id = %s
        """, (package_id,))
        
        package = cursor.fetchone()
        if not package:
            print(f"❌ 패키지 {package_id}번을 찾을 수 없습니다.")
            return None
        
        package_dict = dict(package)
        
        # meta_json 파싱
        if package_dict.get('meta_json') and isinstance(package_dict['meta_json'], str):
            try:
                package_dict['meta_json'] = json.loads(package_dict['meta_json'])
            except:
                pass
        
        # 패키지 아이템 조회
        cursor.execute("""
            SELECT pi.*, pv.name as variant_name, pv.meta_json as variant_meta_json
            FROM package_items pi
            LEFT JOIN product_variants pv ON pi.variant_id = pv.variant_id
            WHERE pi.package_id = %s
            ORDER BY pi.step ASC
        """, (package_id,))
        
        items = cursor.fetchall()
        package_dict['items'] = [dict(item) for item in items]
        
        # items를 steps 형식으로 변환
        steps = []
        for item in package_dict['items']:
            item_dict = dict(item)
            
            # variant_meta_json에서 service_id 찾기
            service_id = None
            variant_meta = item_dict.get('variant_meta_json')
            if variant_meta:
                if isinstance(variant_meta, dict):
                    service_id = variant_meta.get('service_id') or variant_meta.get('smm_service_id')
                elif isinstance(variant_meta, str):
                    try:
                        meta_dict = json.loads(variant_meta)
                        service_id = meta_dict.get('service_id') or meta_dict.get('smm_service_id')
                    except:
                        pass
            
            # term_value와 term_unit을 delay(분)로 변환
            term_value = item_dict.get('term_value') or 0
            term_unit = item_dict.get('term_unit', 'minute')
            delay = 0
            
            if term_unit == 'minute':
                delay = int(term_value) if term_value else 0
            elif term_unit == 'hour':
                delay = int(term_value) * 60 if term_value else 0
            elif term_unit == 'day':
                delay = int(term_value) * 1440 if term_value else 0
            elif term_unit == 'week':
                delay = int(term_value) * 10080 if term_value else 0
            elif term_unit == 'month':
                delay = int(term_value) * 43200 if term_value else 0
            
            step = {
                'id': service_id or item_dict.get('variant_id'),
                'name': item_dict.get('variant_name') or f"단계 {item_dict.get('step', 0)}",
                'quantity': int(item_dict.get('quantity', 0)) if item_dict.get('quantity') else 0,
                'delay': delay,
                'repeat': int(item_dict.get('repeat_count', 1)) if item_dict.get('repeat_count') else 1
            }
            steps.append(step)
        
        package_dict['steps'] = steps
        
        return package_dict
        
    except Exception as e:
        print(f"❌ 데이터베이스 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def create_package_order(package_info, user_id=None, link=None):
    """패키지 주문 생성"""
    if not package_info:
        print("❌ 패키지 정보가 없습니다.")
        return None
    
    # 기본값 설정
    if not user_id:
        user_id = input("사용자 ID를 입력하세요 (또는 Enter로 기본값 사용): ").strip()
        if not user_id:
            user_id = "test-user-123"  # 테스트용 기본값
            print(f"⚠️ 기본 사용자 ID 사용: {user_id}")
    
    if not link:
        link = input("주문할 링크를 입력하세요 (또는 Enter로 기본값 사용): ").strip()
        if not link:
            link = "https://instagram.com/p/test123"  # 테스트용 기본값
            print(f"⚠️ 기본 링크 사용: {link}")
    
    # 패키지 정보에서 steps 추출
    steps = package_info.get('steps', [])
    if not steps:
        print("❌ 패키지에 steps 정보가 없습니다.")
        print(f"📋 패키지 정보: {json.dumps(package_info, indent=2, ensure_ascii=False)}")
        return None
    
    # 가격 계산 (너무 큰 값은 제한)
    price = 0
    if package_info.get('meta_json') and isinstance(package_info['meta_json'], dict):
        price = package_info['meta_json'].get('price', 0)
    if not price:
        price = package_info.get('price', 0)
    
    # NUMERIC(14,2) 최대값: 999,999,999,999,999.99 (약 10^15)
    # 안전한 최대값: 999,999,999,999.99 (약 10^12)
    max_price = 999999999999.99
    if price > max_price:
        print(f"⚠️ 가격이 너무 큽니다 ({price:,}원). 최대값으로 제한합니다 ({max_price:,}원).")
        price = max_price
    
    # 주문 데이터 구성
    order_data = {
        "user_id": user_id,
        "service_id": steps[0].get('id') if steps else None,  # 첫 번째 단계의 service_id
        "link": link,
        "quantity": 1,  # 패키지는 수량이 1로 고정
        "price": price,
        "package_steps": steps,  # 패키지 단계 정보
        "comments": f"테스트 주문 - 패키지 {package_info.get('package_id')}번"
    }
    
    print(f"\n📦 주문 생성 중...")
    print(f"   패키지: {package_info.get('name')}")
    print(f"   사용자: {user_id}")
    print(f"   링크: {link}")
    print(f"   단계 수: {len(steps)}")
    print(f"   가격: {price:,}원")
    print(f"\n📋 단계 정보:")
    for i, step in enumerate(steps, 1):
        print(f"   {i}. {step.get('name')} - 수량: {step.get('quantity')}, 지연: {step.get('delay')}분")
    
    try:
        response = requests.post(
            f"{API_URL}/orders",
            json=order_data,
            headers={
                "Content-Type": "application/json",
                "X-User-ID": user_id
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ 주문 생성 성공!")
            print(f"   주문 ID: {result.get('order_id')}")
            print(f"   상태: {result.get('status')}")
            print(f"   최종 가격: {result.get('final_price', 0):,}원")
            if result.get('is_package'):
                print(f"   패키지 주문: {len(result.get('package_steps', []))}개 단계")
            return result
        else:
            print(f"\n❌ 주문 생성 실패: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   오류: {error_data.get('error', '알 수 없는 오류')}")
            except:
                print(f"   응답: {response.text}")
            return None
    except Exception as e:
        print(f"\n❌ 주문 생성 오류: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    print("=" * 60)
    print("패키지 7번 주문 생성 스크립트")
    print("=" * 60)
    
    # 패키지 정보 조회
    print("\n1️⃣ 패키지 정보 조회 중...")
    package_info = get_package_from_db(7)
    
    if not package_info:
        print("\n❌ 패키지 7번을 찾을 수 없습니다.")
        print("\n💡 다른 패키지 ID를 사용하시겠습니까?")
        package_id = input("패키지 ID 입력 (또는 Enter로 종료): ").strip()
        if package_id:
            try:
                package_info = get_package_from_db(int(package_id))
            except ValueError:
                print("❌ 잘못된 패키지 ID입니다.")
                return
        else:
            return
    
    # 패키지 정보 출력
    print(f"\n📦 패키지 정보:")
    print(f"   ID: {package_info.get('package_id')}")
    print(f"   이름: {package_info.get('name')}")
    print(f"   설명: {package_info.get('description', 'N/A')}")
    print(f"   단계 수: {len(package_info.get('steps', []))}")
    
    # 주문 생성 확인
    print(f"\n2️⃣ 주문 생성 준비")
    confirm = input("주문을 생성하시겠습니까? (y/N, 또는 'auto'로 자동 생성): ").strip().lower()
    if confirm != 'y' and confirm != 'auto':
        print("❌ 주문 생성이 취소되었습니다.")
        return
    
    # 자동 생성 모드
    auto_mode = confirm == 'auto'
    user_id = None
    link = None
    
    if auto_mode:
        # 사용자가 지정한 값 사용
        user_id = "4"
        link = "jjj"
        print(f"\n🤖 자동 생성 모드:")
        print(f"   사용자 ID: {user_id}")
        print(f"   링크: {link}")
    
    # 주문 생성
    result = create_package_order(package_info, user_id=user_id, link=link)
    
    if result:
        print("\n" + "=" * 60)
        print("✅ 주문 생성 완료!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ 주문 생성 실패")
        print("=" * 60)

if __name__ == "__main__":
    main()
