import sqlite3
import json
from ._utils import set_cors_headers

def get_user_orders(request):
    # CORS preflight 요청 처리
    if request.method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': set_cors_headers(),
            'body': ''
        }
    
    if request.method != 'GET':
        return {
            'statusCode': 405,
            'headers': set_cors_headers(),
            'body': json.dumps({'error': 'Method not allowed'})
        }
    
    try:
        # 쿼리 파라미터에서 user_email 가져오기
        user_email = request.args.get('user_email')
        
        if not user_email:
            return {
                'statusCode': 400,
                'headers': set_cors_headers(),
                'body': json.dumps({'error': 'user_email parameter is required'})
            }
        
        conn = sqlite3.connect('/tmp/orders.db', timeout=20.0)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, platform, service, link, quantity, price, snspop_order_id, status, created_at, updated_at
            FROM orders 
            WHERE user_email = ?
            ORDER BY created_at DESC
        ''', (user_email,))
        
        orders = []
        for row in cursor.fetchall():
            orders.append({
                'id': row[0],
                'platform': row[1],
                'service': row[2],
                'link': row[3],
                'quantity': row[4],
                'price': row[5],
                'snspop_order_id': row[6],
                'status': row[7],
                'created_at': row[8],
                'updated_at': row[9]
            })
        
        conn.close()
        
        return {
            'statusCode': 200,
            'headers': set_cors_headers(),
            'body': json.dumps({'orders': orders})
        }
        
    except Exception as e:
        print(f"❌ Error getting orders: {e}")
        return {
            'statusCode': 500,
            'headers': set_cors_headers(),
            'body': json.dumps({
                'error': 'Internal server error',
                'details': str(e)
            })
        }

def update_order_status(request, order_id):
    # CORS preflight 요청 처리
    if request.method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': set_cors_headers(),
            'body': ''
        }
    
    if request.method != 'PUT':
        return {
            'statusCode': 405,
            'headers': set_cors_headers(),
            'body': json.dumps({'error': 'Method not allowed'})
        }
    
    try:
        # 요청 데이터 파싱
        request_data = request.get_json()
        new_status = request_data.get('status')
        
        if not new_status:
            return {
                'statusCode': 400,
                'headers': set_cors_headers(),
                'body': json.dumps({'error': 'status field is required'})
            }
        
        conn = sqlite3.connect('/tmp/orders.db', timeout=20.0)
        cursor = conn.cursor()
        
        # 주문 상태 업데이트
        cursor.execute('''
            UPDATE orders 
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (new_status, order_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return {
                'statusCode': 404,
                'headers': set_cors_headers(),
                'body': json.dumps({'error': 'Order not found'})
            }
        
        conn.commit()
        conn.close()
        
        return {
            'statusCode': 200,
            'headers': set_cors_headers(),
            'body': json.dumps({'message': 'Order status updated successfully'})
        }
        
    except Exception as e:
        print(f"❌ Error updating order status: {e}")
        return {
            'statusCode': 500,
            'headers': set_cors_headers(),
            'body': json.dumps({
                'error': 'Internal server error',
                'details': str(e)
            })
        }
