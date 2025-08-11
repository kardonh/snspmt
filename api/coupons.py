import sqlite3
import json
from datetime import datetime
from ._utils import set_cors_headers

def get_user_coupons(request):
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
        
        # 사용자의 쿠폰 조회 (만료되지 않은 것만)
        cursor.execute('''
            SELECT id, code, discount_type, discount_value, is_used, expires_at, created_at
            FROM coupons 
            WHERE user_email = ? AND expires_at > CURRENT_TIMESTAMP
            ORDER BY created_at DESC
        ''', (user_email,))
        
        coupons = []
        for row in cursor.fetchall():
            coupons.append({
                'id': row[0],
                'code': row[1],
                'discount_type': row[2],
                'discount_value': row[3],
                'is_used': bool(row[4]),
                'expires_at': row[5],
                'created_at': row[6]
            })
        
        conn.close()
        
        return {
            'statusCode': 200,
            'headers': set_cors_headers(),
            'body': json.dumps({'coupons': coupons})
        }
        
    except Exception as e:
        print(f"❌ Error getting coupons: {e}")
        return {
            'statusCode': 500,
            'headers': set_cors_headers(),
            'body': json.dumps({
                'error': 'Internal server error',
                'details': str(e)
            })
        }

def use_coupon(request, coupon_id):
    # CORS preflight 요청 처리
    if request.method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': set_cors_headers(),
            'body': ''
        }
    
    if request.method != 'POST':
        return {
            'statusCode': 405,
            'headers': set_cors_headers(),
            'body': json.dumps({'error': 'Method not allowed'})
        }
    
    try:
        conn = sqlite3.connect('/tmp/orders.db', timeout=20.0)
        cursor = conn.cursor()
        
        # 쿠폰 정보 조회
        cursor.execute('''
            SELECT id, user_email, discount_type, discount_value, is_used, expires_at
            FROM coupons 
            WHERE id = ?
        ''', (coupon_id,))
        
        coupon = cursor.fetchone()
        if not coupon:
            conn.close()
            return {
                'statusCode': 404,
                'headers': set_cors_headers(),
                'body': json.dumps({'error': 'Coupon not found'})
            }
        
        coupon_id, user_email, discount_type, discount_value, is_used, expires_at = coupon
        
        # 쿠폰이 이미 사용되었는지 확인
        if is_used:
            conn.close()
            return {
                'statusCode': 400,
                'headers': set_cors_headers(),
                'body': json.dumps({'error': 'Coupon already used'})
            }
        
        # 쿠폰이 만료되었는지 확인
        if datetime.fromisoformat(expires_at) < datetime.now():
            conn.close()
            return {
                'statusCode': 400,
                'headers': set_cors_headers(),
                'body': json.dumps({'error': 'Coupon expired'})
            }
        
        # 쿠폰 사용 처리
        cursor.execute('''
            UPDATE coupons 
            SET is_used = TRUE, used_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (coupon_id,))
        
        conn.commit()
        conn.close()
        
        return {
            'statusCode': 200,
            'headers': set_cors_headers(),
            'body': json.dumps({
                'message': 'Coupon used successfully',
                'coupon': {
                    'id': coupon_id,
                    'discount_type': discount_type,
                    'discount_value': discount_value
                }
            })
        }
        
    except Exception as e:
        print(f"❌ Error using coupon: {e}")
        return {
            'statusCode': 500,
            'headers': set_cors_headers(),
            'body': json.dumps({
                'error': 'Internal server error',
                'details': str(e)
            })
        }
