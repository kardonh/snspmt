from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
import sqlite3
import os

admin_bp = Blueprint('admin', __name__)

def get_db_connection():
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'orders.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@admin_bp.route('/api/admin/stats', methods=['GET'])
def get_admin_stats():
    """관리자 통계 데이터 제공"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 현재 날짜와 한 달 전 날짜 계산
        now = datetime.now()
        one_month_ago = now - timedelta(days=30)
        
        # 총 가입자 수 (Firebase Auth 사용자 수는 별도로 관리 필요)
        cursor.execute("SELECT COUNT(DISTINCT user_id) as total_users FROM orders")
        total_users = cursor.fetchone()['total_users']
        
        # 한 달 가입자 수
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id) as monthly_users 
            FROM orders 
            WHERE created_at >= ?
        """, (one_month_ago.strftime('%Y-%m-%d'),))
        monthly_users = cursor.fetchone()['monthly_users']
        
        # 총 매출액
        cursor.execute("SELECT SUM(total_amount) as total_revenue FROM orders WHERE status = 'completed'")
        total_revenue = cursor.fetchone()['total_revenue'] or 0
        
        # 한 달 매출액
        cursor.execute("""
            SELECT SUM(total_amount) as monthly_revenue 
            FROM orders 
            WHERE status = 'completed' AND created_at >= ?
        """, (one_month_ago.strftime('%Y-%m-%d'),))
        monthly_revenue = cursor.fetchone()['monthly_revenue'] or 0
        
        # 총 SMM KINGS 충전액 (실제 비용)
        cursor.execute("SELECT SUM(smmkings_cost) as total_smmkings_charge FROM orders WHERE status = 'completed'")
        total_smmkings_charge = cursor.fetchone()['total_smmkings_charge'] or 0
        
        # 한 달 SMM KINGS 충전액
        cursor.execute("""
            SELECT SUM(smmkings_cost) as monthly_smmkings_charge 
            FROM orders 
            WHERE status = 'completed' AND created_at >= ?
        """, (one_month_ago.strftime('%Y-%m-%d'),))
        monthly_smmkings_charge = cursor.fetchone()['monthly_smmkings_charge'] or 0
        
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
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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
        
        # 사용자 ID, 이메일, 계좌번호로 검색
        cursor.execute("""
            SELECT DISTINCT
                user_id,
                COUNT(*) as order_count,
                SUM(total_amount) as total_spent,
                MIN(created_at) as first_order,
                MAX(created_at) as last_order,
                SUM(CASE WHEN status = 'completed' THEN total_amount ELSE 0 END) as completed_amount,
                SUM(CASE WHEN status = 'pending' THEN total_amount ELSE 0 END) as pending_amount,
                SUM(CASE WHEN status = 'canceled' THEN total_amount ELSE 0 END) as canceled_amount
            FROM orders 
            WHERE user_id LIKE ? OR user_id LIKE ?
            GROUP BY user_id
            ORDER BY total_spent DESC
        """, (f'%{search_query}%', f'%{search_query}%'))
        
        accounts = []
        for row in cursor.fetchall():
            accounts.append({
                'userId': row['user_id'],
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
            placeholders = ','.join(['?' for _ in user_ids])
            
            cursor.execute(f"""
                SELECT 
                    id,
                    user_id,
                    platform,
                    service_name,
                    quantity,
                    total_amount,
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
                    'platform': row['platform'],
                    'serviceName': row['service_name'],
                    'quantity': row['quantity'],
                    'totalAmount': row['total_amount'],
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
