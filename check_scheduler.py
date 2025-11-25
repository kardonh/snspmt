#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
스케줄러 상태 확인 스크립트
execution_progress 테이블에서 패키지 주문 진행 상황 확인
"""
import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv
from datetime import datetime

# .env 파일 로드
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

def check_execution_progress(order_id=None):
    """execution_progress 테이블에서 스케줄러 정보 확인"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("=" * 80)
        print("📦 패키지 주문 스케줄러 상태 확인")
        print("=" * 80)
        
        if order_id:
            # 특정 주문 ID로 조회
            cursor.execute("""
                SELECT 
                    exec_id,
                    order_id,
                    exec_type,
                    step_number,
                    step_name,
                    service_id,
                    quantity,
                    scheduled_datetime,
                    status,
                    smm_panel_order_id,
                    error_message,
                    created_at,
                    completed_at,
                    failed_at
                FROM execution_progress
                WHERE order_id = %s
                ORDER BY step_number ASC
            """, (order_id,))
        else:
            # 모든 실행 중인 패키지 주문 조회
            cursor.execute("""
                SELECT 
                    exec_id,
                    order_id,
                    exec_type,
                    step_number,
                    step_name,
                    service_id,
                    quantity,
                    scheduled_datetime,
                    status,
                    smm_panel_order_id,
                    error_message,
                    created_at,
                    completed_at,
                    failed_at
                FROM execution_progress
                WHERE exec_type = 'package'
                ORDER BY order_id, step_number ASC
                LIMIT 50
            """)
        
        results = cursor.fetchall()
        
        if not results:
            print("\n❌ 실행 중인 패키지 주문이 없습니다.")
            return
        
        # 주문별로 그룹화
        orders_dict = {}
        for row in results:
            oid = row['order_id']
            if oid not in orders_dict:
                orders_dict[oid] = []
            orders_dict[oid].append(dict(row))
        
        # 각 주문별로 출력
        for order_id, steps in orders_dict.items():
            print(f"\n{'='*80}")
            print(f"📋 주문 ID: {order_id}")
            print(f"{'='*80}")
            
            # 주문 기본 정보 조회
            cursor.execute("""
                SELECT 
                    order_id,
                    user_id,
                    status,
                    total_amount,
                    final_amount,
                    created_at,
                    smm_panel_order_id
                FROM orders
                WHERE order_id = %s
                LIMIT 1
            """, (order_id,))
            order_info = cursor.fetchone()
            
            if order_info:
                order_dict = dict(order_info)
                print(f"\n📦 주문 정보:")
                print(f"   상태: {order_dict.get('status', 'N/A')}")
                print(f"   사용자 ID: {order_dict.get('user_id', 'N/A')}")
                print(f"   총 금액: {order_dict.get('total_amount') or order_dict.get('final_amount', 0):,}원")
                print(f"   생성 시간: {order_dict.get('created_at', 'N/A')}")
                print(f"   SMM Panel 주문 ID: {order_dict.get('smm_panel_order_id', 'N/A')}")
            
            print(f"\n🔄 스케줄된 단계: {len(steps)}개")
            print(f"\n{'단계':<6} {'서비스 ID':<12} {'수량':<8} {'상태':<12} {'예약 시간':<20} {'실행 시간':<20}")
            print("-" * 80)
            
            for step in steps:
                step_num = step.get('step_number', 'N/A')
                service_id = step.get('service_id', 'N/A')
                quantity = step.get('quantity', 0)
                status = step.get('status', 'N/A')
                scheduled = step.get('scheduled_datetime')
                completed = step.get('completed_at')
                failed = step.get('failed_at')
                
                scheduled_str = scheduled.strftime('%Y-%m-%d %H:%M:%S') if scheduled else 'N/A'
                exec_time = completed or failed or 'N/A'
                if isinstance(exec_time, datetime):
                    exec_time = exec_time.strftime('%Y-%m-%d %H:%M:%S')
                
                status_emoji = {
                    'pending': '⏳',
                    'running': '🔄',
                    'completed': '✅',
                    'failed': '❌',
                    'scheduled': '📅'
                }.get(status, '❓')
                
                print(f"{step_num:<6} {service_id:<12} {quantity:<8} {status_emoji} {status:<10} {scheduled_str:<20} {exec_time:<20}")
                
                if step.get('error_message'):
                    print(f"      ⚠️ 오류: {step['error_message']}")
                if step.get('smm_panel_order_id'):
                    print(f"      📝 SMM Panel 주문 ID: {step['smm_panel_order_id']}")
            
            # 실행 대기 중인 단계 확인
            pending_steps = [s for s in steps if s.get('status') == 'pending']
            if pending_steps:
                now = datetime.now()
                ready_steps = [s for s in pending_steps 
                             if s.get('scheduled_datetime') and s['scheduled_datetime'] <= now]
                
                if ready_steps:
                    print(f"\n⏰ 실행 대기 중인 단계: {len(ready_steps)}개 (예약 시간 경과)")
                else:
                    next_step = min([s for s in pending_steps if s.get('scheduled_datetime')], 
                                  key=lambda x: x['scheduled_datetime'], default=None)
                    if next_step:
                        next_time = next_step['scheduled_datetime']
                        remaining = (next_time - now).total_seconds() / 60  # 분
                        print(f"\n⏰ 다음 단계 실행까지: {remaining:.1f}분 후 (단계 {next_step['step_number']})")
        
        print(f"\n{'='*80}")
        print(f"📊 총 {len(orders_dict)}개 주문, {len(results)}개 단계")
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def check_recent_orders():
    """최근 패키지 주문 조회"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("\n" + "=" * 80)
        print("📋 최근 패키지 주문 목록")
        print("=" * 80)
        
        cursor.execute("""
            SELECT 
                order_id,
                user_id,
                status,
                total_amount,
                final_amount,
                created_at,
                package_steps IS NOT NULL as is_package
            FROM orders
            WHERE package_steps IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        orders = cursor.fetchall()
        
        if not orders:
            print("\n❌ 패키지 주문이 없습니다.")
            return
        
        print(f"\n{'주문 ID':<20} {'사용자':<15} {'상태':<12} {'금액':<15} {'생성 시간':<20}")
        print("-" * 80)
        
        for order in orders:
            oid = order['order_id']
            user = str(order['user_id'])[:14]
            status = order['status']
            amount = order.get('total_amount') or order.get('final_amount', 0)
            created = order['created_at']
            
            if isinstance(created, datetime):
                created = created.strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"{oid:<20} {user:<15} {status:<12} {amount:>12,}원 {created:<20}")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def main():
    import sys
    
    print("=" * 80)
    print("🔍 스케줄러 상태 확인 도구")
    print("=" * 80)
    
    # 명령줄 인자 확인
    if len(sys.argv) > 1:
        order_id = sys.argv[1]
        print(f"\n📦 주문 ID {order_id}의 스케줄러 상태를 확인합니다...")
        check_execution_progress(order_id)
    else:
        # 최근 패키지 주문 목록 표시
        check_recent_orders()
        
        # 실행 중인 모든 패키지 주문 확인
        print("\n")
        check_execution_progress()

if __name__ == "__main__":
    main()

