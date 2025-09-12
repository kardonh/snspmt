from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
import json
import os

# PostgreSQL 의존성
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    print("PostgreSQL not available in analytics module")

analytics_bp = Blueprint('analytics', __name__)

def get_db_connection():
    """PostgreSQL 연결"""
    if POSTGRES_AVAILABLE:
        try:
            database_url = "postgresql://postgres:Snspmt2024!@snspmt-cluste.cluster-cvmiee0q0zhs.ap-northeast-2.rds.amazonaws.com:5432/snspmt"
            conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
            return conn
        except Exception as e:
            print(f"PostgreSQL 연결 실패: {e}")
            raise e
    else:
        raise Exception("PostgreSQL is required but not available")

@analytics_bp.route('/api/analytics/revenue', methods=['GET'])
def get_revenue_analytics():
    """수익 분석 데이터"""
    try:
        period = request.args.get('period', '30')  # 기본 30일
        days = int(period)
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 일별 수익 데이터
            cursor.execute("""
                SELECT 
                    DATE(created_at) as date,
                    SUM(price) as daily_revenue,
                    COUNT(*) as order_count,
                    AVG(price) as avg_order_value
                FROM purchases 
                WHERE status = 'approved' 
                AND created_at >= CURRENT_DATE - INTERVAL '%s days'
                GROUP BY DATE(created_at)
                ORDER BY date
            """, (days,))
            
            daily_data = []
            for row in cursor.fetchall():
                daily_data.append({
                    'date': row['date'].strftime('%Y-%m-%d'),
                    'revenue': float(row['daily_revenue'] or 0),
                    'orderCount': row['order_count'],
                    'avgOrderValue': float(row['avg_order_value'] or 0)
                })
            
            # 월별 수익 데이터
            cursor.execute("""
                SELECT 
                    DATE_TRUNC('month', created_at) as month,
                    SUM(price) as monthly_revenue,
                    COUNT(*) as order_count
                FROM purchases 
                WHERE status = 'approved' 
                AND created_at >= CURRENT_DATE - INTERVAL '12 months'
                GROUP BY DATE_TRUNC('month', created_at)
                ORDER BY month
            """)
            
            monthly_data = []
            for row in cursor.fetchall():
                monthly_data.append({
                    'month': row['month'].strftime('%Y-%m'),
                    'revenue': float(row['monthly_revenue'] or 0),
                    'orderCount': row['order_count']
                })
            
            # 총계
            cursor.execute("""
                SELECT 
                    SUM(price) as total_revenue,
                    COUNT(*) as total_orders,
                    AVG(price) as overall_avg_order
                FROM purchases 
                WHERE status = 'approved'
            """)
            
            summary = cursor.fetchone()
            
            return jsonify({
                'success': True,
                'data': {
                    'daily': daily_data,
                    'monthly': monthly_data,
                    'summary': {
                        'totalRevenue': float(summary['total_revenue'] or 0),
                        'totalOrders': summary['total_orders'],
                        'avgOrderValue': float(summary['overall_avg_order'] or 0)
                    }
                }
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@analytics_bp.route('/api/analytics/user-behavior', methods=['GET'])
def get_user_behavior_analytics():
    """사용자 행동 분석"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 사용자별 주문 패턴
            cursor.execute("""
                SELECT 
                    user_id,
                    COUNT(*) as order_count,
                    SUM(price) as total_spent,
                    AVG(price) as avg_order_value,
                    MIN(created_at) as first_order,
                    MAX(created_at) as last_order,
                    EXTRACT(DAYS FROM MAX(created_at) - MIN(created_at)) as customer_lifetime_days
                FROM orders 
                GROUP BY user_id
                HAVING COUNT(*) > 1
                ORDER BY total_spent DESC
                LIMIT 20
            """)
            
            top_customers = []
            for row in cursor.fetchall():
                top_customers.append({
                    'userId': row['user_id'],
                    'orderCount': row['order_count'],
                    'totalSpent': float(row['total_spent'] or 0),
                    'avgOrderValue': float(row['avg_order_value'] or 0),
                    'firstOrder': row['first_order'],
                    'lastOrder': row['last_order'],
                    'customerLifetimeDays': int(row['customer_lifetime_days'] or 0)
                })
            
            # 시간대별 주문 패턴
            cursor.execute("""
                SELECT 
                    EXTRACT(HOUR FROM created_at) as hour,
                    COUNT(*) as order_count,
                    AVG(price) as avg_order_value
                FROM orders 
                WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY EXTRACT(HOUR FROM created_at)
                ORDER BY hour
            """)
            
            hourly_pattern = []
            for row in cursor.fetchall():
                hourly_pattern.append({
                    'hour': int(row['hour']),
                    'orderCount': row['order_count'],
                    'avgOrderValue': float(row['avg_order_value'] or 0)
                })
            
            # 요일별 주문 패턴
            cursor.execute("""
                SELECT 
                    EXTRACT(DOW FROM created_at) as day_of_week,
                    COUNT(*) as order_count,
                    AVG(price) as avg_order_value
                FROM orders 
                WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY EXTRACT(DOW FROM created_at)
                ORDER BY day_of_week
            """)
            
            daily_pattern = []
            day_names = ['일요일', '월요일', '화요일', '수요일', '목요일', '금요일', '토요일']
            for row in cursor.fetchall():
                daily_pattern.append({
                    'dayOfWeek': int(row['day_of_week']),
                    'dayName': day_names[int(row['day_of_week'])],
                    'orderCount': row['order_count'],
                    'avgOrderValue': float(row['avg_order_value'] or 0)
                })
            
            return jsonify({
                'success': True,
                'data': {
                    'topCustomers': top_customers,
                    'hourlyPattern': hourly_pattern,
                    'dailyPattern': daily_pattern
                }
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@analytics_bp.route('/api/analytics/service-performance', methods=['GET'])
def get_service_performance_analytics():
    """서비스별 성과 분석"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 서비스별 주문 통계
            cursor.execute("""
                SELECT 
                    service_id,
                    COUNT(*) as order_count,
                    SUM(price) as total_revenue,
                    AVG(price) as avg_price,
                    AVG(quantity) as avg_quantity,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_orders,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_orders,
                    SUM(CASE WHEN status = 'canceled' THEN 1 ELSE 0 END) as canceled_orders
                FROM orders 
                GROUP BY service_id
                ORDER BY total_revenue DESC
            """)
            
            service_stats = []
            for row in cursor.fetchall():
                total_orders = row['order_count']
                completion_rate = (row['completed_orders'] / total_orders * 100) if total_orders > 0 else 0
                
                service_stats.append({
                    'serviceId': row['service_id'],
                    'orderCount': row['order_count'],
                    'totalRevenue': float(row['total_revenue'] or 0),
                    'avgPrice': float(row['avg_price'] or 0),
                    'avgQuantity': float(row['avg_quantity'] or 0),
                    'completedOrders': row['completed_orders'],
                    'pendingOrders': row['pending_orders'],
                    'canceledOrders': row['canceled_orders'],
                    'completionRate': round(completion_rate, 2)
                })
            
            # 서비스별 월별 트렌드
            cursor.execute("""
                SELECT 
                    service_id,
                    DATE_TRUNC('month', created_at) as month,
                    COUNT(*) as order_count,
                    SUM(price) as revenue
                FROM orders 
                WHERE created_at >= CURRENT_DATE - INTERVAL '6 months'
                GROUP BY service_id, DATE_TRUNC('month', created_at)
                ORDER BY service_id, month
            """)
            
            service_trends = {}
            for row in cursor.fetchall():
                service_id = row['service_id']
                if service_id not in service_trends:
                    service_trends[service_id] = []
                
                service_trends[service_id].append({
                    'month': row['month'].strftime('%Y-%m'),
                    'orderCount': row['order_count'],
                    'revenue': float(row['revenue'] or 0)
                })
            
            return jsonify({
                'success': True,
                'data': {
                    'serviceStats': service_stats,
                    'serviceTrends': service_trends
                }
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@analytics_bp.route('/api/analytics/retention', methods=['GET'])
def get_retention_analytics():
    """고객 유지율 분석"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 신규 vs 재구매 고객 분석
            cursor.execute("""
                WITH customer_orders AS (
                    SELECT 
                        user_id,
                        COUNT(*) as order_count,
                        MIN(created_at) as first_order,
                        MAX(created_at) as last_order
                    FROM orders 
                    GROUP BY user_id
                )
                SELECT 
                    CASE 
                        WHEN order_count = 1 THEN '신규 고객'
                        WHEN order_count = 2 THEN '2회 구매'
                        WHEN order_count = 3 THEN '3회 구매'
                        WHEN order_count <= 5 THEN '4-5회 구매'
                        ELSE 'VIP 고객'
                    END as customer_type,
                    COUNT(*) as customer_count,
                    AVG(order_count) as avg_orders_per_customer
                FROM customer_orders
                GROUP BY 
                    CASE 
                        WHEN order_count = 1 THEN '신규 고객'
                        WHEN order_count = 2 THEN '2회 구매'
                        WHEN order_count = 3 THEN '3회 구매'
                        WHEN order_count <= 5 THEN '4-5회 구매'
                        ELSE 'VIP 고객'
                    END
                ORDER BY avg_orders_per_customer DESC
            """)
            
            customer_segments = []
            for row in cursor.fetchall():
                customer_segments.append({
                    'customerType': row['customer_type'],
                    'customerCount': row['customer_count'],
                    'avgOrdersPerCustomer': float(row['avg_orders_per_customer'] or 0)
                })
            
            # 월별 신규 고객 vs 재구매 고객
            cursor.execute("""
                WITH monthly_customers AS (
                    SELECT 
                        user_id,
                        DATE_TRUNC('month', created_at) as month,
                        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at) as order_sequence
                    FROM orders
                )
                SELECT 
                    month,
                    SUM(CASE WHEN order_sequence = 1 THEN 1 ELSE 0 END) as new_customers,
                    SUM(CASE WHEN order_sequence > 1 THEN 1 ELSE 0 END) as returning_customers
                FROM monthly_customers
                WHERE month >= CURRENT_DATE - INTERVAL '12 months'
                GROUP BY month
                ORDER BY month
            """)
            
            monthly_retention = []
            for row in cursor.fetchall():
                monthly_retention.append({
                    'month': row['month'].strftime('%Y-%m'),
                    'newCustomers': row['new_customers'],
                    'returningCustomers': row['returning_customers']
                })
            
            return jsonify({
                'success': True,
                'data': {
                    'customerSegments': customer_segments,
                    'monthlyRetention': monthly_retention
                }
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
