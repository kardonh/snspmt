from flask import Blueprint, jsonify, request, send_file
from datetime import datetime, timedelta
import os
import csv
import io

# PostgreSQL 의존성
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    print("PostgreSQL not available in admin module")

admin_bp = Blueprint('admin', __name__)

def get_db_connection():
    """PostgreSQL 연결 (backend.py와 동일한 설정)"""
    if POSTGRES_AVAILABLE:
        try:
            # backend.py와 동일한 연결 문자열 사용
            database_url = "postgresql://snspmt_admin:Snspmt2024!@snspmt-cluster.cluster-cvmiee0q0zhs.ap-northeast-2.rds.amazonaws.com:5432/snspmt"
            conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
            return conn
        except Exception as e:
            print(f"PostgreSQL 연결 실패: {e}")
            raise e
    else:
        raise Exception("PostgreSQL is required but not available")

def get_admin_db_connection():
    """관리자용 PostgreSQL 연결 (backend.py와 호환)"""
    return get_db_connection()

@admin_bp.route('/stats', methods=['GET'])
def get_admin_stats():
    """관리자 통계 데이터 제공"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 데이터베이스 테이블 존재 여부 확인
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        existing_tables = [row['table_name'] for row in cursor.fetchall()]
        print(f"존재하는 테이블: {existing_tables}")
        
        # 현재 날짜와 하루 전 날짜 계산
        now = datetime.now()
        one_day_ago = now - timedelta(days=1)
        
        # 총 사용자 수 (points 테이블에서 조회)
        try:
            cursor.execute("SELECT COUNT(*) as total_users FROM points")
            total_users = cursor.fetchone()['total_users']
        except Exception as e:
            print(f"points 테이블 조회 실패: {e}")
            total_users = 0
        
        # 총 주문 수 (orders 테이블에서 조회)
        try:
            cursor.execute("SELECT COUNT(*) as total_orders FROM orders")
            total_orders = cursor.fetchone()['total_orders']
        except Exception as e:
            print(f"orders 테이블 조회 실패: {e}")
            total_orders = 0
        
        # 총 매출액 (point_purchases 테이블에서 조회)
        try:
            cursor.execute("SELECT SUM(price) as total_revenue FROM point_purchases WHERE status = 'approved'")
            total_revenue = cursor.fetchone()['total_revenue'] or 0
        except Exception as e:
            print(f"total_revenue 조회 실패: {e}")
            total_revenue = 0
        
        # 대기 중인 포인트 구매 신청 수
        try:
            cursor.execute("SELECT COUNT(*) as pending_purchases FROM point_purchases WHERE status = 'pending'")
            pending_purchases = cursor.fetchone()['pending_purchases']
        except Exception as e:
            print(f"pending_purchases 조회 실패: {e}")
            pending_purchases = 0
        
        # 오늘 주문 수
        try:
            cursor.execute("""
                SELECT COUNT(*) as today_orders 
                FROM orders 
                WHERE DATE(created_at) = CURRENT_DATE
            """)
            today_orders = cursor.fetchone()['today_orders']
        except Exception as e:
            print(f"today_orders 조회 실패: {e}")
            today_orders = 0
        
        # 오늘 매출액
        try:
            cursor.execute("""
                SELECT SUM(price) as today_revenue 
                FROM point_purchases 
                WHERE status = 'approved' AND DATE(created_at) = CURRENT_DATE
            """)
            today_revenue = cursor.fetchone()['today_revenue'] or 0
        except Exception as e:
            print(f"today_revenue 조회 실패: {e}")
            today_revenue = 0
        
        stats = {
            'totalUsers': total_users,
            'totalOrders': total_orders,
            'totalRevenue': float(total_revenue),
            'pendingPurchases': pending_purchases,
            'todayOrders': today_orders,
            'todayRevenue': float(today_revenue)
        }
        
        cursor.close()
        conn.close()
        
        return jsonify(stats), 200
        
    except Exception as e:
        print(f"관리자 통계 조회 실패: {e}")
        # 에러 발생 시 기본값 반환
        return jsonify({
            'totalUsers': 0,
            'totalOrders': 0,
            'totalRevenue': 0,
            'pendingPurchases': 0,
            'todayOrders': 0,
            'todayRevenue': 0
        }), 200

@admin_bp.route('/users', methods=['GET'])
def get_admin_users():
    """관리자용 사용자 목록 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                user_id,
                points,
                created_at,
                updated_at
            FROM points 
            ORDER BY created_at DESC
        """)
        
        users = []
        for row in cursor.fetchall():
            user = {
                'userId': row['user_id'],
                'email': row['user_id'],  # user_id를 이메일로 사용
                'points': row['points'],
                'createdAt': row['created_at'].isoformat() if row['created_at'] else None,
                'lastActivity': row['updated_at'].isoformat() if row['updated_at'] else None
            }
            users.append(user)
        
        cursor.close()
        conn.close()
        
        return jsonify(users), 200
        
    except Exception as e:
        print(f"사용자 목록 조회 실패: {e}")
        return jsonify([]), 200

@admin_bp.route('/transactions', methods=['GET'])
def get_admin_transactions():
    """관리자용 주문/거래 목록 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                order_id,
                user_id,
                service_id,
                link,
                quantity,
                price,
                status,
                created_at
            FROM orders 
            ORDER BY created_at DESC
        """)
        
        orders = []
        for row in cursor.fetchall():
            order = {
                'orderId': f"ORD_{row['order_id']}",
                'platform': 'SNS',  # 기본값
                'service': f"서비스 {row['service_id']}",
                'quantity': row['quantity'],
                'amount': float(row['price']),
                'status': row['status'],
                'createdAt': row['created_at'].isoformat() if row['created_at'] else None
            }
            orders.append(order)
        
        cursor.close()
        conn.close()
        
        return jsonify(orders), 200
        
    except Exception as e:
        print(f"주문 목록 조회 실패: {e}")
        return jsonify([]), 200

@admin_bp.route('/purchases', methods=['GET'])
def get_admin_purchases():
    """관리자용 포인트 구매 신청 목록 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                purchase_id,
                user_id,
                amount,
                price,
                status,
                created_at
            FROM point_purchases 
            ORDER BY created_at DESC
        """)
        
        purchases = []
        for row in cursor.fetchall():
            purchase = {
                'id': row['purchase_id'],
                'userId': row['user_id'],
                'email': row['user_id'],  # user_id를 이메일로 사용
                'points': row['amount'],
                'amount': float(row['price']),
                'status': row['status'],
                'createdAt': row['created_at'].isoformat() if row['created_at'] else None
            }
            purchases.append(purchase)
        
        cursor.close()
        conn.close()
        
        return jsonify(purchases), 200
        
    except Exception as e:
        print(f"구매 신청 목록 조회 실패: {e}")
        return jsonify([]), 200

@admin_bp.route('/purchases/<int:purchase_id>', methods=['PUT'])
def update_purchase_status(purchase_id):
    """포인트 구매 신청 상태 업데이트 (승인/거절)"""
    try:
        data = request.get_json()
        status = data.get('status')
        
        if status not in ['approved', 'rejected']:
            return jsonify({'error': '잘못된 상태값입니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if status == 'approved':
            # 구매 신청 승인 시 사용자 포인트 증가
            cursor.execute("""
                UPDATE point_purchases 
                SET status = %s, updated_at = CURRENT_TIMESTAMP 
                WHERE purchase_id = %s
            """, (status, purchase_id))
            
            # 구매 정보 조회 (추천인 커미션 계산용)
            cursor.execute("""
                SELECT user_id, amount, price 
                FROM point_purchases 
                WHERE purchase_id = %s
            """, (purchase_id,))
            
            purchase_info = cursor.fetchone()
            if purchase_info:
                user_id = purchase_info['user_id']
                purchase_amount = purchase_info['amount']
                purchase_price = purchase_info['price']
                
                # 사용자 포인트 증가
                cursor.execute("""
                    UPDATE points 
                    SET points = points + %s,
                    updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """, (purchase_amount, user_id))
                
                # 추천인 커미션 처리
                cursor.execute("""
                    SELECT referrer_user_id 
                    FROM referrals 
                    WHERE referred_user_id = %s
                """, (user_id,))
                
                referral_info = cursor.fetchone()
                if referral_info:
                    referrer_user_id = referral_info['referrer_user_id']
                    
                    # 15% 커미션 계산
                    commission_amount = purchase_price * 0.15
                    
                    # 추천인에게 포인트 지급
                    cursor.execute("""
                        UPDATE points 
                        SET points = points + %s,
                        updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = %s
                    """, (commission_amount, referrer_user_id))
                    
                    # 커미션 내역 저장
                    cursor.execute("""
                        INSERT INTO referral_commissions 
                        (referrer_user_id, referred_user_id, purchase_id, commission_amount, commission_rate)
                        VALUES (%s, %s, %s, %s, 0.15)
                    """, (referrer_user_id, user_id, purchase_id, commission_amount))
                    
                    # 추천인 코드의 총 커미션 업데이트
                    cursor.execute("""
                        UPDATE referral_codes 
                        SET total_commission = total_commission + %s
                        WHERE referrer_user_id = %s
                    """, (commission_amount, referrer_user_id))
                    
                    print(f"추천인 커미션 지급: {referrer_user_id}에게 {commission_amount}원 지급")
            
        else:
            # 거절 시 상태만 업데이트
            cursor.execute("""
                UPDATE point_purchases 
                SET status = %s, updated_at = CURRENT_TIMESTAMP 
                WHERE purchase_id = %s
            """, (status, purchase_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': '상태가 업데이트되었습니다.'}), 200
        
    except Exception as e:
        print(f"구매 신청 상태 업데이트 실패: {e}")
        return jsonify({'error': '상태 업데이트에 실패했습니다.'}), 500

@admin_bp.route('/search-account', methods=['GET'])
def search_account():
    """계정 검색 (기존 기능 유지)"""
    try:
        query = request.args.get('query', '')
        if not query:
            return jsonify({'error': '검색어를 입력해주세요.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 사용자 검색 (user_id 또는 이메일로 검색)
        cursor.execute("""
            SELECT 
                user_id,
                points,
                created_at,
                updated_at
            FROM points 
            WHERE user_id ILIKE %s
            ORDER BY created_at DESC
        """, (f'%{query}%',))
        
        users = []
        for row in cursor.fetchall():
            user = {
                'userId': row['user_id'],
                'email': row['user_id'],
                'points': row['points'],
                'createdAt': row['created_at'].isoformat() if row['created_at'] else None,
                'lastActivity': row['updated_at'].isoformat() if row['updated_at'] else None
            }
            users.append(user)
        
        cursor.close()
        conn.close()
        
        return jsonify({'users': users}), 200
        
    except Exception as e:
        print(f"계정 검색 실패: {e}")
        return jsonify({'error': '검색에 실패했습니다.'}), 500
