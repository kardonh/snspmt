from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import os
import json
import sqlite3
    import psycopg2
    from psycopg2.extras import RealDictCursor
from datetime import datetime
import requests
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

# Flask 앱 생성
app = Flask(__name__)
CORS(app)
    
    # 환경 변수 설정
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/snspmt')
# AWS RDS용 데이터베이스 URL 수정
if 'rds.amazonaws.com' in DATABASE_URL and 'snspmt_db' in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace('snspmt_db', 'snspmt')
SMMPANEL_API_URL = 'https://smmpanel.kr/api/v2'
API_KEY = os.getenv('SMMPANEL_API_KEY', '5efae48d287931cf9bd80a1bc6fdfa6d')

# PostgreSQL 연결 함수
def get_db_connection():
    """PostgreSQL 데이터베이스 연결"""
    try:
        print(f"데이터베이스 연결 시도: {DATABASE_URL}")
        conn = psycopg2.connect(DATABASE_URL)
        print("데이터베이스 연결 성공")
        return conn
        except Exception as e:
        print(f"데이터베이스 연결 실패: {e}")
        # 연결 실패 시 SQLite로 폴백
        print("SQLite로 폴백 시도...")
        try:
            conn = sqlite3.connect('orders.db')
            conn.row_factory = sqlite3.Row
            print("SQLite 연결 성공")
            return conn
        except Exception as sqlite_error:
            print(f"SQLite 연결도 실패: {sqlite_error}")
            return None

# SQLite 연결 함수 (로컬 개발용)
def get_sqlite_connection():
    """SQLite 데이터베이스 연결"""
    try:
        conn = sqlite3.connect('orders.db')
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"SQLite 연결 실패: {e}")
    return None

# 데이터베이스 초기화
def init_database():
    """데이터베이스 테이블 초기화"""
    try:
        conn = get_db_connection()
        if conn is None:
            print("데이터베이스 연결을 할 수 없습니다.")
    return False

        with conn:
        cursor = conn.cursor()
        
            # orders 테이블 생성
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                    order_id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    service_id INTEGER NOT NULL,
                    link TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price DECIMAL(10,2) NOT NULL,
                    status VARCHAR(50) DEFAULT 'pending',
                    external_order_id VARCHAR(255),
                    comments TEXT,
                    explanation TEXT,
                    runs INTEGER DEFAULT 1,
                    interval INTEGER DEFAULT 0,
                    username VARCHAR(255),
                    min_quantity INTEGER,
                    max_quantity INTEGER,
                    posts INTEGER DEFAULT 0,
                    delay INTEGER DEFAULT 0,
                    expiry DATE,
                    old_posts INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # points 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS points (
                    user_id VARCHAR(255) PRIMARY KEY,
                points INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # point_purchases 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS point_purchases (
                    purchase_id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    amount INTEGER NOT NULL,
                    price DECIMAL(10,2) NOT NULL,
                    status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # notifications 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    notification_id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    type VARCHAR(50) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    is_read BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        conn.commit()
            print("데이터베이스 초기화 완료")
            return True
            
    except Exception as e:
        print(f"데이터베이스 초기화 실패: {e}")
        return False

# 정적 파일 서빙
@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('dist', filename)

# 메인 페이지 - React 앱 서빙
@app.route('/')
def index():
    return send_from_directory('dist', 'index.html')

# 헬스 체크 - 간단하고 빠른 응답
@app.route('/health')
def health_check():
    try:
        # 간단한 데이터베이스 연결 테스트
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        return jsonify({
            'status': 'healthy', 
            'timestamp': datetime.now().isoformat(),
            'database': 'connected'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# 사용자 등록
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        user_id = data.get('uid')
        email = data.get('email')
        
        if not user_id or not email:
            return jsonify({'error': '필수 정보가 누락되었습니다.'}), 400
        
        # PostgreSQL에 사용자 정보 저장
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO points (user_id, points) 
                VALUES (%s, 0) 
                ON CONFLICT (user_id) DO NOTHING
            """, (user_id,))
            conn.commit()
        
        return jsonify({'message': '사용자 등록 완료'}), 200
        
    except Exception as e:
        print(f"사용자 등록 실패: {e}")
        return jsonify({'error': '사용자 등록에 실패했습니다.'}), 500

# 사용자 로그인
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        user_id = data.get('uid')
        
        if not user_id:
            return jsonify({'error': '사용자 ID가 누락되었습니다.'}), 400
        
        # PostgreSQL에서 사용자 정보 조회
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, points FROM points WHERE user_id = %s
            """, (user_id,))
            
            user = cursor.fetchone()
            if not user:
                # 사용자가 없으면 새로 생성
                cursor.execute("""
                    INSERT INTO points (user_id, points) VALUES (%s, 0)
                """, (user_id,))
                conn.commit()
                points = 0
            else:
                points = user['points']
        
        return jsonify({
            'user_id': user_id,
            'points': points
        }), 200
        
    except Exception as e:
        print(f"로그인 실패: {e}")
        return jsonify({'error': '로그인에 실패했습니다.'}), 500

# 사용자 활동 업데이트
@app.route('/api/activity', methods=['POST'])
def update_activity():
    try:
        data = request.get_json()
        user_id = data.get('uid')
        
        if not user_id:
            return jsonify({'error': '사용자 ID가 누락되었습니다.'}), 400
        
        # PostgreSQL에서 사용자 정보 업데이트
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE points SET updated_at = %s WHERE user_id = %s
            """, (datetime.now(), user_id))
            conn.commit()
        
        return jsonify({'message': '활동 업데이트 완료'}), 200
        
    except Exception as e:
        print(f"활동 업데이트 실패: {e}")
        return jsonify({'error': '활동 업데이트에 실패했습니다.'}), 500

# 주문 생성
@app.route('/api/orders', methods=['POST'])
def create_order():
    """주문 생성 API"""
    try:
        data = request.get_json()
        user_id = request.headers.get('X-User-ID', 'anonymous')
        
        print(f"=== 주문 생성 요청 ===")
        print(f"사용자 ID: {user_id}")
        print(f"요청 데이터: {data}")
        
        # 필수 필드 검증
        required_fields = ['service_id', 'link', 'quantity']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'type': 'validation_error',
                    'message': f'{field}가 누락되었습니다.'
                }), 400
        
        # 데이터 타입 검증
        try:
            service_id = int(data['service_id'])
            quantity = int(data['quantity'])
            link = str(data['link'])
        except (ValueError, TypeError):
            return jsonify({
                'type': 'validation_error',
                'message': '잘못된 데이터 타입입니다.'
            }), 400
        
        # 가격 계산 (임시로 1000당 100원으로 설정)
        price = (quantity / 1000) * 100
        
        # PostgreSQL에 주문 저장
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO orders (
                        user_id, service_id, link, quantity, price, status,
                        comments, explanation, runs, interval, username,
                        min_quantity, max_quantity, posts, delay, expiry, old_posts
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING order_id
                """, (
                    user_id, service_id, link, quantity, price, 'pending_payment',
                    data.get('comments'), data.get('explanation'), data.get('runs', 1),
                    data.get('interval', 0), data.get('username'), data.get('min'),
                    data.get('max'), data.get('posts', 0), data.get('delay', 0),
                    data.get('expiry'), data.get('old_posts', 0)
                ))
                
                order_id = cursor.fetchone()[0]
                conn.commit()
        print(f"주문 저장 완료: {order_id}")
                
        except Exception as e:
            print(f"데이터베이스 저장 실패: {e}")
            return jsonify({
                'type': 'database_error',
                'message': '주문 저장에 실패했습니다.'
            }), 500
        
        # 성공 응답 반환
        success_response = {
            'order': order_id,
            'status': 'pending_payment',
            'message': '주문이 생성되었습니다. 결제를 완료해주세요.',
            'price': price
        }
        
        print(f"=== 주문 생성 완료 ===")
        print(f"주문 ID: {order_id}")
        return jsonify(success_response), 200
        
    except Exception as e:
        print(f"=== 주문 생성 실패 ===")
        print(f"오류: {str(e)}")
        return jsonify({'error': f'주문 생성 실패: {str(e)}'}), 500

# 주문 결제 완료
@app.route('/api/orders/<order_id>/complete-payment', methods=['POST'])
def complete_order_payment(order_id):
    """주문 결제 완료 및 외부 API 전송"""
    try:
        data = request.get_json()
        user_id = request.headers.get('X-User-ID', 'anonymous')
        
        print(f"=== 주문 결제 완료 요청 ===")
        print(f"주문 ID: {order_id}")
        print(f"사용자 ID: {user_id}")
        
        # 주문 정보 조회
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT order_id, user_id, service_id, link, quantity, price, status
                    FROM orders 
                    WHERE order_id = %s AND user_id = %s
                """, (order_id, user_id))
                
                order = cursor.fetchone()
        if not order:
            return jsonify({'error': '주문을 찾을 수 없습니다.'}), 404
        
                if order['status'] != 'pending_payment':
                    return jsonify({'error': '결제 대기 상태가 아닙니다.'}), 400
                
                # 포인트 차감
                current_points = 0  # 임시로 0으로 설정
                if current_points < order['price']:
                    return jsonify({
                        'type': 'payment_error',
                        'message': f'포인트가 부족합니다. 현재: {current_points}P, 필요: {order["price"]}P'
                    }), 400
                
                # 포인트 차감 (실제로는 points 테이블에서 업데이트)
                print(f"포인트 차감 완료: {user_id}에서 {order['price']}P 차감")
                
                # smmpanel.kr API로 주문 전송
                try:
                    print(f"smmpanel.kr API로 주문 전송 시작...")
                    
                    # API 요청 데이터 구성
                    api_data = {
                        'service': order['service_id'],
                        'link': order['link'],
                        'quantity': order['quantity']
                    }
                    
                    # 추가 옵션들 추가
                    if data.get('runs'):
                        api_data['runs'] = data.get('runs')
                    if data.get('interval'):
                        api_data['interval'] = data.get('interval')
                    if data.get('comments'):
                        api_data['comments'] = data.get('comments')
                    if data.get('username'):
                        api_data['username'] = data.get('username')
                    if data.get('min'):
                        api_data['min'] = data.get('min')
                    if data.get('max'):
                        api_data['max'] = data.get('max')
                    if data.get('posts'):
                        api_data['posts'] = data.get('posts')
                    if data.get('delay'):
                        api_data['delay'] = data.get('delay')
                    if data.get('expiry'):
                        api_data['expiry'] = data.get('expiry')
                    if data.get('old_posts'):
                        api_data['old_posts'] = data.get('old_posts')
                    
                    # smmpanel.kr API 호출
        response = requests.post(SMMPANEL_API_URL, json={
            'key': API_KEY,
                        'action': 'add',
                        **api_data
        }, timeout=30)
        
        if response.status_code == 200:
                        api_response = response.json()
                        print(f"smmpanel.kr API 응답: {api_response}")
                        
                        # API 응답에서 외부 주문 ID 추출
                        external_order_id = api_response.get('order')
                        
                        # PostgreSQL에 외부 주문 ID 업데이트
                cursor.execute("""
                            UPDATE orders 
                            SET external_order_id = %s, status = 'processing', updated_at = %s
                            WHERE order_id = %s
                        """, (external_order_id, datetime.now(), order_id))
                        conn.commit()
                        
                        print(f"smmpanel.kr 주문 전송 성공: {external_order_id}")
                        
                        return jsonify({
                'success': True,
                            'orderId': order_id,
                            'externalOrderId': external_order_id,
                            'status': 'processing',
                            'message': '결제가 완료되었고 주문이 처리 중입니다.',
                            'points_used': order['price'],
                            'remaining_points': current_points - order['price']
                        }), 200
                    else:
                        print(f"smmpanel.kr API 오류: {response.status_code} - {response.text}")
                        return jsonify({
                            'error': '외부 API 전송에 실패했습니다.'
                        }), 500
            
    except Exception as e:
                    print(f"smmpanel.kr API 전송 실패: {e}")
        return jsonify({
                        'error': f'외부 API 전송 실패: {str(e)}'
        }), 500

        except Exception as e:
            print(f"데이터베이스 오류: {e}")
            return jsonify({'error': f'데이터베이스 오류: {str(e)}'}), 500
        
            except Exception as e:
        print(f"=== 주문 결제 완료 실패 ===")
        print(f"오류: {str(e)}")
        return jsonify({'error': f'주문 결제 완료 실패: {str(e)}'}), 500

# 사용자 주문 조회
@app.route('/api/orders', methods=['GET'])
def get_user_orders():
    """사용자별 주문 정보 조회"""
    try:
        user_id = request.args.get('user_id', 'anonymous')
        
        print(f"주문 조회 요청: {user_id}")
        
        # PostgreSQL에서 주문 조회
        try:
            with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                        order_id,
                        service_id,
                        link,
                        quantity,
                    price,
                    status,
                        external_order_id,
                        created_at,
                        updated_at
                    FROM orders 
                    WHERE user_id = %s
                ORDER BY created_at DESC
                """, (user_id,))
            
                orders = []
            for row in cursor.fetchall():
                    order = {
                        'id': row['order_id'],
                        'service': row['service_id'],
                        'link': row['link'],
                        'quantity': row['quantity'],
                        'price': float(row['price'] or 0),
                        'status': row['status'],
                        'external_order_id': row['external_order_id'],
                        'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                        'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
                    }
                    orders.append(order)
                
                return jsonify({'orders': orders}), 200
            
    except Exception as e:
            print(f"데이터베이스 조회 실패: {e}")
            return jsonify({'error': '주문 조회에 실패했습니다.'}), 500
        
    except Exception as e:
        print(f"주문 조회 실패: {e}")
        return jsonify({'error': '주문 조회에 실패했습니다.'}), 500

# 사용자 포인트 조회
@app.route('/api/points', methods=['GET'])
def get_user_points():
    """사용자 포인트 조회"""
    try:
        user_id = request.args.get('user_id', 'anonymous')
        
        if not user_id:
            return jsonify({'error': '사용자 ID가 누락되었습니다.'}), 400
        
        # PostgreSQL에서 포인트 조회
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT points FROM points WHERE user_id = %s
                """, (user_id,))
                
                result = cursor.fetchone()
                if result:
                    points = result['points']
                else:
                    points = 0
                
        return jsonify({'points': points}), 200
        
    except Exception as e:
            print(f"포인트 조회 실패: {e}")
            return jsonify({'error': '포인트 조회에 실패했습니다.'}), 500
        
    except Exception as e:
        print(f"포인트 조회 실패: {e}")
        return jsonify({'error': '포인트 조회에 실패했습니다.'}), 500

# 포인트 구매 요청
@app.route('/api/points/purchase', methods=['POST'])
def create_point_purchase():
    """포인트 구매 요청"""
    try:
        data = request.get_json()
        user_id = request.headers.get('X-User-ID', 'anonymous')
        amount = data.get('amount')
        price = data.get('price')
        
        if not amount or not price:
            return jsonify({'error': '필수 정보가 누락되었습니다.'}), 400
        
        # PostgreSQL에 구매 요청 저장
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO point_purchases (user_id, amount, price, status)
                    VALUES (%s, %s, %s, 'pending')
                    RETURNING purchase_id
                """, (user_id, amount, price))
                
                purchase_id = cursor.fetchone()[0]
                conn.commit()
        
        return jsonify({
                    'purchase_id': purchase_id,
                    'message': '포인트 구매 요청이 생성되었습니다.'
                }), 200
        
    except Exception as e:
            print(f"구매 요청 저장 실패: {e}")
            return jsonify({'error': '구매 요청 저장에 실패했습니다.'}), 500
        
    except Exception as e:
        print(f"포인트 구매 요청 실패: {e}")
        return jsonify({'error': '포인트 구매 요청에 실패했습니다.'}), 500

# 포인트 구매 내역 조회
@app.route('/api/points/purchase-history', methods=['GET'])
def get_purchase_history():
    """포인트 구매 내역 조회"""
    try:
        user_id = request.args.get('user_id', 'anonymous')
        
        if not user_id:
            return jsonify({'error': '사용자 ID가 누락되었습니다.'}), 400
        
        # PostgreSQL에서 구매 내역 조회
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        purchase_id,
                        amount,
                        price,
                        status,
                        created_at,
                        updated_at
                    FROM point_purchases 
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                """, (user_id,))
                
                purchases = []
                for row in cursor.fetchall():
                    purchase = {
                        'id': row['purchase_id'],
                        'amount': row['amount'],
                        'price': float(row['price'] or 0),
                        'status': row['status'],
                        'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                        'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
                    }
                    purchases.append(purchase)
                
                return jsonify({'purchases': purchases}), 200
        
    except Exception as e:
            print(f"구매 내역 조회 실패: {e}")
            return jsonify({'error': '구매 내역 조회에 실패했습니다.'}), 500
        
    except Exception as e:
        print(f"구매 내역 조회 실패: {e}")
        return jsonify({'error': '구매 내역 조회에 실패했습니다.'}), 500

# 사용자 정보 조회
@app.route('/api/user/info', methods=['GET'])
def get_user_info():
    """사용자 정보 조회"""
    try:
        user_id = request.args.get('user_id', 'anonymous')
        
        if not user_id:
            return jsonify({'error': '사용자 ID가 누락되었습니다.'}), 400
        
        # PostgreSQL에서 사용자 정보 조회
        try:
            with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                    SELECT 
                        user_id,
                        points,
                        created_at,
                        updated_at
                    FROM points 
                    WHERE user_id = %s
                """, (user_id,))
                
                result = cursor.fetchone()
                if result:
                    user_info = {
                        'user_id': result['user_id'],
                        'points': result['points'],
                        'created_at': result['created_at'].isoformat() if result['created_at'] else None,
                        'updated_at': result['updated_at'].isoformat() if result['updated_at'] else None
                    }
                else:
                    user_info = {
                        'user_id': user_id,
                        'points': 0,
                        'created_at': None,
                        'updated_at': None
                    }
                
                return jsonify(user_info), 200
                
        except Exception as e:
            print(f"사용자 정보 조회 실패: {e}")
            return jsonify({'error': '사용자 정보 조회에 실패했습니다.'}), 500
        
    except Exception as e:
        print(f"사용자 정보 조회 실패: {e}")
        return jsonify({'error': '사용자 정보 조회에 실패했습니다.'}), 500

# 관리자 API 블루프린트 등록
try:
    from api.admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    print("관리자 API 블루프린트 등록 완료")
except ImportError as e:
    print(f"관리자 API 블루프린트 등록 실패: {e}")

# 알림 API 블루프린트 등록
try:
    from api.notifications import notifications_bp
    app.register_blueprint(notifications_bp, url_prefix='/api/notifications')
    print("알림 API 블루프린트 등록 완료")
except ImportError as e:
    print(f"알림 API 블루프린트 등록 실패: {e}")

# 분석 API 블루프린트 등록
try:
    from api.analytics import analytics_bp
    app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
    print("분석 API 블루프린트 등록 완료")
except ImportError as e:
    print(f"분석 API 블루프린트 등록 실패: {e}")

# 애플리케이션 시작 시 데이터베이스 초기화
if __name__ == '__main__':
    init_database()
    app.run(debug=True, host='0.0.0.0', port=5000)
else:
    init_database()
