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
    print("PostgreSQL not available in notifications module")

notifications_bp = Blueprint('notifications', __name__)

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

def init_notifications_table():
    """알림 테이블 초기화"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    data JSONB,
                    is_read BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    read_at TIMESTAMP
                )
            ''')
            
            # 인덱스 생성
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read)")
            
            conn.commit()
            print("알림 테이블 초기화 완료")
            
    except Exception as e:
        print(f"알림 테이블 초기화 실패: {e}")

@notifications_bp.route('/api/notifications', methods=['GET'])
def get_user_notifications():
    """사용자 알림 목록 조회"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    id,
                    type,
                    title,
                    message,
                    data,
                    is_read,
                    created_at,
                    read_at
                FROM notifications 
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 50
            """, (user_id,))
            
            notifications = []
            for row in cursor.fetchall():
                notifications.append({
                    'id': row['id'],
                    'type': row['type'],
                    'title': row['title'],
                    'message': row['message'],
                    'data': row['data'],
                    'isRead': row['is_read'],
                    'createdAt': row['created_at'],
                    'readAt': row['read_at']
                })
            
            # 읽지 않은 알림 수
            cursor.execute("""
                SELECT COUNT(*) as unread_count
                FROM notifications 
                WHERE user_id = %s AND is_read = FALSE
            """, (user_id,))
            
            unread_count = cursor.fetchone()['unread_count']
            
            return jsonify({
                'success': True,
                'notifications': notifications,
                'unreadCount': unread_count
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@notifications_bp.route('/api/notifications/<int:notification_id>/read', methods=['PUT'])
def mark_notification_read(notification_id):
    """알림 읽음 처리"""
    try:
        user_id = request.json.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE notifications 
                SET is_read = TRUE, read_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s
            """, (notification_id, user_id))
            
            if cursor.rowcount == 0:
                return jsonify({'error': 'Notification not found'}), 404
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': '알림이 읽음 처리되었습니다.'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@notifications_bp.route('/api/notifications/read-all', methods=['PUT'])
def mark_all_notifications_read():
    """모든 알림 읽음 처리"""
    try:
        user_id = request.json.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE notifications 
                SET is_read = TRUE, read_at = CURRENT_TIMESTAMP
                WHERE user_id = %s AND is_read = FALSE
            """, (user_id,))
            
            updated_count = cursor.rowcount
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': f'{updated_count}개의 알림이 읽음 처리되었습니다.',
                'updatedCount': updated_count
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def create_notification(user_id, notification_type, title, message, data=None):
    """알림 생성 (내부 함수)"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO notifications (user_id, type, title, message, data)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, notification_type, title, message, json.dumps(data) if data else None))
            
            conn.commit()
            print(f"알림 생성 완료: {user_id} - {title}")
            
    except Exception as e:
        print(f"알림 생성 실패: {e}")

# 알림 타입별 생성 함수들
def notify_order_status_change(user_id, order_id, old_status, new_status):
    """주문 상태 변경 알림"""
    status_messages = {
        'pending': '주문이 접수되었습니다.',
        'processing': '주문이 처리 중입니다.',
        'completed': '주문이 완료되었습니다.',
        'canceled': '주문이 취소되었습니다.'
    }
    
    title = "주문 상태 변경"
    message = status_messages.get(new_status, f"주문 상태가 {new_status}로 변경되었습니다.")
    
    create_notification(user_id, 'order_status', title, message, {
        'orderId': order_id,
        'oldStatus': old_status,
        'newStatus': new_status
    })

def notify_points_charged(user_id, amount, total_points):
    """포인트 충전 완료 알림"""
    title = "포인트 충전 완료"
    message = f"{amount}P가 충전되었습니다. (총 {total_points}P)"
    
    create_notification(user_id, 'points_charged', title, message, {
        'amount': amount,
        'totalPoints': total_points
    })

def notify_low_points(user_id, current_points):
    """포인트 부족 알림"""
    title = "포인트 부족"
    message = f"포인트가 부족합니다. 현재 {current_points}P"
    
    create_notification(user_id, 'low_points', title, message, {
        'currentPoints': current_points
    })

def notify_system_maintenance(user_id, maintenance_info):
    """시스템 점검 알림"""
    title = "시스템 점검 안내"
    message = maintenance_info.get('message', '시스템 점검이 예정되어 있습니다.')
    
    create_notification(user_id, 'system_maintenance', title, message, maintenance_info)

# 테이블 초기화
init_notifications_table()
