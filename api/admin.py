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
            database_url = "postgresql://snspmt_admin:Snspmt2024!@snspmt-db.cvmiee0q0zhs.ap-northeast-2.rds.amazonaws.com:5432/postgres"
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

@admin_bp.route('/api/admin/stats', methods=['GET'])
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
        
        # 현재 날짜와 한 달 전 날짜 계산
        now = datetime.now()
        one_month_ago = now - timedelta(days=30)
        
        # 총 가입자 수 (users 테이블에서 조회)
        try:
            cursor.execute("SELECT COUNT(*) as total_users FROM users")
            total_users = cursor.fetchone()['total_users']
        except Exception as e:
            print(f"users 테이블 조회 실패: {e}")
            total_users = 0
        
        # 한 달 가입자 수
        try:
            cursor.execute("""
                SELECT COUNT(*) as monthly_users 
                FROM users 
                WHERE created_at >= %s
            """, (one_month_ago.strftime('%Y-%m-%d'),))
            monthly_users = cursor.fetchone()['monthly_users']
        except Exception as e:
            print(f"monthly_users 조회 실패: {e}")
            monthly_users = 0
        
        # 총 매출액 (purchases 테이블에서 조회)
        try:
            cursor.execute("SELECT SUM(price) as total_revenue FROM purchases WHERE status = 'approved'")
            total_revenue = cursor.fetchone()['total_revenue'] or 0
        except Exception as e:
            print(f"total_revenue 조회 실패: {e}")
            total_revenue = 0
        
        # 한 달 매출액
        try:
            cursor.execute("""
                SELECT SUM(price) as monthly_revenue 
                FROM purchases 
                WHERE status = 'approved' AND created_at >= %s
            """, (one_month_ago.strftime('%Y-%m-%d'),))
            monthly_revenue = cursor.fetchone()['monthly_revenue'] or 0
        except Exception as e:
            print(f"monthly_revenue 조회 실패: {e}")
            monthly_revenue = 0
        
        # 총 SMM KINGS 충전액 (실제 비용)
        try:
            cursor.execute("SELECT SUM(smmkings_cost) as total_smmkings_charge FROM orders WHERE status = 'completed'")
            total_smmkings_charge = cursor.fetchone()['total_smmkings_charge'] or 0
        except Exception as e:
            print(f"total_smmkings_charge 조회 실패: {e}")
            total_smmkings_charge = 0
        
        # 한 달 SMM KINGS 충전액
        try:
            cursor.execute("""
                SELECT SUM(smmkings_cost) as monthly_smmkings_charge 
                FROM orders 
                WHERE status = 'completed' AND created_at >= %s
            """, (one_month_ago.strftime('%Y-%m-%d'),))
            monthly_smmkings_charge = cursor.fetchone()['monthly_smmkings_charge'] or 0
        except Exception as e:
            print(f"monthly_smmkings_charge 조회 실패: {e}")
            monthly_smmkings_charge = 0
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'totalUsers': total_users,
                'monthlyUsers': monthly_users,
                'totalRevenue': total_revenue,
                'monthlyRevenue': monthly_revenue,
                'totalSMMKingsCharge': total_smmkings_charge,
                'monthlySMMKingsCharge': monthly_smmkings_charge
            }
        })
        
    except Exception as e:
        print(f"Admin stats API 오류: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_bp.route('/api/admin/transactions', methods=['GET'])
def get_admin_transactions():
    """충전 및 환불 내역 제공"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 테이블 존재 여부 확인
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'orders'
            );
        """)
        
        if not cursor.fetchone()[0]:
            return jsonify({
                'success': True,
                'data': {
                    'charges': [],
                    'refunds': []
                }
            })
        
        # 충전 내역 (완료된 주문)
        cursor.execute("""
            SELECT 
                id,
                user_id as user,
                total_amount as amount,
                created_at as date,
                status
            FROM orders 
            WHERE status = 'completed'
            ORDER BY created_at DESC
            LIMIT 20
        """)
        charges = []
        for row in cursor.fetchall():
            charges.append({
                'id': row['id'],
                'user': row['user'],
                'amount': row['amount'],
                'date': row['date'],
                'status': row['status']
            })
        
        # 환불 내역 (취소된 주문)
        cursor.execute("""
            SELECT 
                id,
                user_id as user,
                total_amount as amount,
                created_at as date,
                '고객 요청' as reason
            FROM orders 
            WHERE status = 'cancelled'
            ORDER BY created_at DESC
            LIMIT 20
        """)
        refunds = []
        for row in cursor.fetchall():
            refunds.append({
                'id': row['id'],
                'user': row['user'],
                'amount': row['amount'],
                'date': row['date'],
                'reason': row['reason']
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'charges': charges,
                'refunds': refunds
            }
        })
        
    except Exception as e:
        print(f"Transactions API 오류: {e}")
        return jsonify({
            'success': True,
            'data': {
                'charges': [],
                'refunds': []
            }
        }), 200  # 500 대신 200 반환

@admin_bp.route('/api/admin/orders', methods=['GET'])
def get_admin_orders():
    """모든 주문 내역 제공"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                id,
                user_id,
                platform,
                service_name,
                quantity,
                total_amount,
                status,
                created_at,
                updated_at
            FROM orders 
            ORDER BY created_at DESC
            LIMIT 100
        """)
        
        orders = []
        for row in cursor.fetchall():
            orders.append({
                'id': row['id'],
                'userId': row['user_id'],
                'platform': row['platform'],
                'serviceName': row['service_name'],
                'quantity': row['quantity'],
                'totalAmount': row['total_amount'],
                'status': row['status'],
                'createdAt': row['created_at'],
                'updatedAt': row['updated_at']
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': orders
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_bp.route('/api/admin/users', methods=['GET'])
def get_admin_users():
    """사용자 목록 제공"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 테이블 존재 여부 확인
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'orders'
            );
        """)
        
        if not cursor.fetchone()[0]:
            return jsonify({
                'success': True,
                'data': []
            })
        
        cursor.execute("""
            SELECT 
                user_id,
                COUNT(*) as order_count,
                SUM(total_amount) as total_spent,
                MIN(created_at) as first_order,
                MAX(created_at) as last_order
            FROM orders 
            GROUP BY user_id
            ORDER BY total_spent DESC
        """)
        
        users = []
        for row in cursor.fetchall():
            users.append({
                'userId': row['user_id'],
                'orderCount': row['order_count'],
                'totalSpent': row['total_spent'] or 0,
                'firstOrder': row['first_order'],
                'lastOrder': row['last_order']
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': users
        })
        
    except Exception as e:
        print(f"Users API 오류: {e}")
        return jsonify({
            'success': True,
            'data': []
        }), 200  # 500 대신 200 반환

@admin_bp.route('/api/admin/search-account', methods=['GET'])
def search_account():
    """계좌 정보 검색"""
    try:
        search_query = request.args.get('query', '').strip()
        
        if not search_query:
            return jsonify({
                'success': False,
                'error': '검색어를 입력해주세요.'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 사용자 ID, 이메일로 검색
        cursor.execute("""
            SELECT DISTINCT
                u.user_id,
                u.email,
                u.display_name,
                COUNT(o.id) as order_count,
                COALESCE(SUM(o.price), 0) as total_spent,
                MIN(o.created_at) as first_order,
                MAX(o.created_at) as last_order,
                COALESCE(SUM(CASE WHEN o.status = 'completed' THEN o.price ELSE 0 END), 0) as completed_amount,
                COALESCE(SUM(CASE WHEN o.status = 'pending' THEN o.price ELSE 0 END), 0) as pending_amount,
                COALESCE(SUM(CASE WHEN o.status = 'canceled' THEN o.price ELSE 0 END), 0) as canceled_amount
            FROM users u
            LEFT JOIN orders o ON u.user_id = o.user_id
            WHERE u.user_id LIKE %s OR u.email LIKE %s OR u.display_name LIKE %s
            GROUP BY u.user_id, u.email, u.display_name
            ORDER BY total_spent DESC
        """, (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'))
        
        accounts = []
        for row in cursor.fetchall():
            accounts.append({
                'userId': row['user_id'],
                'email': row['email'],
                'displayName': row['display_name'],
                'orderCount': row['order_count'],
                'totalSpent': row['total_spent'] or 0,
                'completedAmount': row['completed_amount'] or 0,
                'pendingAmount': row['pending_amount'] or 0,
                'canceledAmount': row['canceled_amount'] or 0,
                'firstOrder': row['first_order'],
                'lastOrder': row['last_order']
            })
        
        # 최근 주문 내역도 함께 조회
        recent_orders = []
        if accounts:
            user_ids = [account['userId'] for account in accounts]
            placeholders = ','.join(['%s' for _ in user_ids])
            
            cursor.execute(f"""
                SELECT 
                    id,
                    user_id,
                    service_id,
                    quantity,
                    price,
                    status,
                    created_at
                FROM orders 
                WHERE user_id IN ({placeholders})
                ORDER BY created_at DESC
                LIMIT 50
            """, user_ids)
            
            for row in cursor.fetchall():
                recent_orders.append({
                    'id': row['id'],
                    'userId': row['user_id'],
                    'serviceId': row['service_id'],
                    'quantity': row['quantity'],
                    'totalAmount': row['price'],
                    'status': row['status'],
                    'createdAt': row['created_at']
                })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'accounts': accounts,
                'recentOrders': recent_orders,
                'totalFound': len(accounts)
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_bp.route('/api/admin/export/cash-receipts', methods=['GET'])
def export_cash_receipts():
    """현금영수증 엑셀 다운로드"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 현금영수증 발급 대상 조회 (완료된 주문 중 현금영수증 요청)
        cursor.execute("""
            SELECT 
                o.id as order_id,
                o.user_id,
                o.platform,
                o.service_name,
                o.quantity,
                o.total_amount,
                o.created_at,
                o.status,
                p.receipt_type,
                p.cash_receipt_phone,
                p.business_name,
                p.representative,
                p.business_number
            FROM orders o
            LEFT JOIN purchases p ON o.user_id = p.user_id AND o.created_at = p.created_at
            WHERE o.status = 'completed' 
            AND (p.receipt_type = 'cash' OR p.receipt_type IS NULL)
            ORDER BY o.created_at DESC
        """)
        
        rows = cursor.fetchall()
        
        # CSV 데이터 생성
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 헤더 작성
        writer.writerow([
            '주문번호',
            '사용자ID',
            '플랫폼',
            '서비스명',
            '수량',
            '결제금액',
            '주문일시',
            '상태',
            '영수증타입',
            '현금영수증전화번호',
            '상호명',
            '대표자명',
            '사업자번호'
        ])
        
        # 데이터 작성
        for row in rows:
            writer.writerow([
                row['order_id'],
                row['user_id'],
                row['platform'],
                row['service_name'],
                row['quantity'],
                row['total_amount'],
                row['created_at'],
                row['status'],
                row['receipt_type'] or '현금영수증',
                row['cash_receipt_phone'] or '',
                row['business_name'] or '',
                row['representative'] or '',
                row['business_number'] or ''
            ])
        
        conn.close()
        
        # 파일명 생성
        current_date = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'현금영수증_{current_date}.csv'
        
        # CSV 데이터를 바이트로 변환
        output.seek(0)
        csv_data = output.getvalue().encode('utf-8-sig')  # BOM 추가로 한글 깨짐 방지
        
        # 메모리 파일 객체 생성
        csv_file = io.BytesIO(csv_data)
        csv_file.seek(0)
        
        return send_file(
            csv_file,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
