from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import json
from datetime import datetime, timedelta 
import os
import sqlite3
import csv
import io
import logging
from contextlib import contextmanager
import hashlib
import time

# Blueprint imports
try:
    from api.admin import admin_bp
    ADMIN_AVAILABLE = True
except ImportError as e:
    print(f"Admin blueprint import failed: {e}")
    ADMIN_AVAILABLE = False

try:
    from api.notifications import notifications_bp
    NOTIFICATIONS_AVAILABLE = True
except ImportError as e:
    print(f"Notifications blueprint import failed: {e}")
    NOTIFICATIONS_AVAILABLE = False

try:
    from api.analytics import analytics_bp
    ANALYTICS_AVAILABLE = True
except ImportError as e:
    print(f"Analytics blueprint import failed: {e}")
    ANALYTICS_AVAILABLE = False

# PostgreSQL 의존성 (개발 환경에서는 선택적)
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from psycopg2.pool import SimpleConnectionPool
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    print("PostgreSQL not available, using SQLite for development")

# Redis 캐싱 (선택적)
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("Redis not available, caching disabled")

# 임시 디렉토리 설정 (Docker 컨테이너 문제 해결)
import tempfile
import sys

# 임시 디렉토리 문제 해결
def setup_temp_directories():
    """임시 디렉토리 설정"""
    temp_dirs = ['/tmp', '/var/tmp', '/usr/tmp', '/app/tmp']
    for temp_dir in temp_dirs:
        try:
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir, exist_ok=True)
        except Exception as e:
            print(f"임시 디렉토리 생성 실패 {temp_dir}: {e}")
    
    # 환경 변수 설정
    os.environ['TMPDIR'] = '/tmp'
    os.environ['TEMP'] = '/tmp'
    os.environ['TMP'] = '/tmp'
    
    # tempfile 모듈 재설정
    tempfile.tempdir = '/tmp'

# 임시 디렉토리 설정 실행
setup_temp_directories()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Blueprint 등록
if ADMIN_AVAILABLE:
    app.register_blueprint(admin_bp)
    print("Admin blueprint registered successfully")
else:
    print("Admin blueprint not available")

if NOTIFICATIONS_AVAILABLE:
    app.register_blueprint(notifications_bp)
    print("Notifications blueprint registered successfully")
else:
    print("Notifications blueprint not available")

if ANALYTICS_AVAILABLE:
    app.register_blueprint(analytics_bp)
    print("Analytics blueprint registered successfully")
else:
    print("Analytics blueprint not available")

# 헬스 체크 엔드포인트 추가 (ECS 헬스 체크용)
@app.route('/health')
def health_check():
    """헬스 체크 엔드포인트"""
    try:
        # 임시 디렉토리 권한 확인
        temp_dir = os.environ.get('TEMP_DIR', '/tmp')
        temp_dir_writable = os.access(temp_dir, os.W_OK)
        
        # 데이터베이스 연결 확인
        db_status = "unknown"
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT 1')
                db_status = "healthy"
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"
        
        return {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'temp_dir': temp_dir,
            'temp_dir_writable': temp_dir_writable,
            'database': db_status,
            'environment': os.environ.get('FLASK_ENV', 'unknown')
        }, 200
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }, 500

# Redis 캐시 클라이언트
redis_client = None

def init_redis():
    """Redis 캐시 초기화"""
    global redis_client
    if REDIS_AVAILABLE and os.environ.get('REDIS_URL'):
        try:
            redis_client = redis.from_url(os.environ.get('REDIS_URL'))
            # 연결 테스트
            redis_client.ping()
            print("Redis 캐시 연결 성공")
        except Exception as e:
            print(f"Redis 연결 실패: {e}")
            redis_client = None

def cache_get(key, expire=300):
    """캐시에서 데이터 조회"""
    if redis_client:
        try:
            data = redis_client.get(key)
            return json.loads(data) if data else None
        except:
            return None
    return None

def cache_set_with_compression(key, data, expire=300):
    """압축된 데이터를 캐시에 저장 (성능 향상)"""
    if redis_client:
        try:
            # 데이터 압축
            compressed_data = json.dumps(data, separators=(',', ':'))
            redis_client.setex(key, expire, compressed_data)
            return True
        except:
            return False
    return False

def cache_set(key, data, expire=300):
    """캐시에 데이터 저장"""
    if redis_client:
        try:
            redis_client.setex(key, expire, json.dumps(data))
        except:
            pass

def generate_cache_key(*args):
    """캐시 키 생성"""
    key_string = "_".join(str(arg) for arg in args)
    return hashlib.md5(key_string.encode()).hexdigest()

# 데이터베이스 연결 풀 (프로덕션용)
db_pool = None

def init_db_pool():
    """데이터베이스 연결 풀 초기화"""
    global db_pool
    if os.environ.get('DATABASE_URL') and POSTGRES_AVAILABLE:
        try:
            db_pool = SimpleConnectionPool(
                minconn=5,  # 최소 연결 수
                maxconn=20,  # 최대 연결 수
                dsn=os.environ.get('DATABASE_URL')
            )
            print("PostgreSQL 연결 풀 초기화 완료")
        except Exception as e:
            print(f"PostgreSQL 연결 풀 초기화 실패: {e}")

@contextmanager
def get_db_connection():
    """데이터베이스 연결 (컨텍스트 매니저)"""
    # 항상 PostgreSQL 사용 (SQLite 문제 해결)
    if POSTGRES_AVAILABLE and db_pool:
        # PostgreSQL 연결 풀 사용
        conn = db_pool.getconn()
        try:
            yield conn
        finally:
            db_pool.putconn(conn)
    else:
        # PostgreSQL 연결 풀이 없으면 직접 연결
        if POSTGRES_AVAILABLE:
            # 올바른 연결 문자열 하드코딩
            database_url = "postgresql://snspmt_admin:Snspmt2024!@snspmt-db.cvmiee0q0zhs.ap-northeast-2.rds.amazonaws.com:5432/postgres"
            
            conn = psycopg2.connect(database_url)
            try:
                yield conn
            finally:
                conn.close()
        else:
            raise Exception("PostgreSQL is required but not available")

def init_database():
    """데이터베이스 초기화"""
    if not POSTGRES_AVAILABLE:
        print("PostgreSQL is required but not available")
        return
        
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # PostgreSQL 테이블 생성
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                order_id TEXT UNIQUE,
                user_id TEXT,
                service_id INTEGER,
                link TEXT,
                quantity INTEGER,
                price REAL,
                status TEXT,
                external_order_id TEXT,
                smmkings_cost REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                user_id TEXT UNIQUE,
                email TEXT,
                display_name TEXT,
                points INTEGER DEFAULT 0,
                account_type TEXT DEFAULT 'personal',
                business_info TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS purchases (
                id SERIAL PRIMARY KEY,
                purchase_id TEXT UNIQUE,
                user_id TEXT,
                amount INTEGER,
                price REAL,
                status TEXT DEFAULT 'pending',
                depositor_name TEXT,
                bank_name TEXT,
                receipt_type TEXT,
                business_info TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monthly_costs (
                id SERIAL PRIMARY KEY,
                month TEXT,
                total_cost REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()

# 데이터베이스 인덱스 생성 (성능 최적화)
def create_database_indexes():
    """데이터베이스 인덱스 생성"""
    try:
        with get_admin_db_connection() as conn:
            cursor = conn.cursor()
            
            # 주문 테이블 인덱스
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at)")
            
            # 사용자 테이블 인덱스
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at)")
            
            # 구매 내역 테이블 인덱스
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_purchases_user_id ON purchases(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_purchases_status ON purchases(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_purchases_created_at ON purchases(created_at)")
            
            conn.commit()
            print("데이터베이스 인덱스 생성 완료")
            
    except Exception as e:
        print(f"인덱스 생성 실패: {e}")

# 데이터베이스 초기화
init_database()
create_database_indexes()

# Flask 앱 설정
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)

# 보안 헤더 및 성능 모니터링 추가
@app.after_request
def add_security_headers_and_monitoring(response):
    # 보안 헤더
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # 성능 모니터링
    if hasattr(request, 'start_time'):
        response_time = time.time() - request.start_time
        response.headers['X-Response-Time'] = f'{response_time:.3f}s'
        
        # 느린 응답 로깅 (1초 이상)
        if response_time > 1.0:
            print(f"⚠️ 느린 응답 감지: {request.path} - {response_time:.3f}초")
    
    # CSP 헤더 임시 제거 (Firebase 오류 해결 후 재추가)
    # response.headers['Content-Security-Policy'] = "default-src 'self' https://*.firebase.googleapis.com https://*.firebaseinstallations.googleapis.com https://*.googleapis.com; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://*.firebase.googleapis.com https://*.googleapis.com; style-src 'self' 'unsafe-inline'; connect-src 'self' https://*.firebase.googleapis.com https://*.firebaseinstallations.googleapis.com https://*.googleapis.com https://*.google.com; img-src 'self' data: https:; font-src 'self' data:;"
    return response

# CORS 설정 - 개발 환경에서는 모든 origin 허용
CORS(app, origins=['http://localhost:3000', 'http://127.0.0.1:3000', 'https://snsinto.onrender.com'])

# smmpanel.kr API 설정
SMMPANEL_API_URL = 'https://smmpanel.kr/api/v2'
API_KEY = os.environ.get('SMMPANEL_API_KEY', 'your_api_key_here')

# 레이트 리미팅을 위한 간단한 캐시
from collections import defaultdict
import time
rate_limit_cache = defaultdict(list)

def check_rate_limit(ip, limit=1000, window=3600):
    """레이트 리미팅 체크 (완화됨)"""
    now = time.time()
    # 윈도우 시간 이전의 요청들 제거
    rate_limit_cache[ip] = [req_time for req_time in rate_limit_cache[ip] if now - req_time < window]
    
    if len(rate_limit_cache[ip]) >= limit:
        return False
    
    rate_limit_cache[ip].append(now)
    return True

@app.before_request
def before_request():
    """요청 전 처리"""
    # 요청 시작 시간 기록
    request.start_time = time.time()
    
    # 레이트 리미팅 체크
    if not check_rate_limit(request.remote_addr):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    
    # 보안 헤더 추가
    if request.method == 'OPTIONS':
        return

# 주문 데이터 저장소 (실제 프로덕션에서는 데이터베이스 사용)
orders_db = {}

# 포인트 관련 데이터베이스
points_db = {}  # 사용자별 포인트
purchases_db = {}  # 구매 신청 내역

# 사용자 관련 데이터베이스
users_db = {}  # 사용자 정보
user_sessions = {}  # 실시간 접속 사용자

# 월별 원가 통계 저장소
monthly_costs = {}  # {year_month: total_cost}

def calculate_and_store_cost(service_id, quantity, total_price):
    """주문의 원가를 계산하고 월별 통계에 저장"""
    try:
        # 원가 계산 (총 가격의 1/1.5 = 2/3 = 66.67% - 실제 원가)
        # 현재 가격이 1.5배 인상된 가격이므로, 실제 원가는 1/1.5배
        cost_rate = 1/1.5  # 원가율 66.67%
        cost = total_price * cost_rate
        
        # 현재 월 키 생성
        current_month = datetime.now().strftime('%Y-%m')
        
        # 월별 원가 통계 업데이트
        if current_month not in monthly_costs:
            monthly_costs[current_month] = 0
        
        monthly_costs[current_month] += cost
        
        # 보안상 민감한 정보는 로그에서 제거
        print(f"원가 계산 완료: service_id={service_id}, cost={cost}")
        
        return cost
        
    except Exception as e:
        print(f"원가 계산 오류: {str(e)}")
        return 0



@app.route('/api', methods=['POST'])
def proxy_api():
    try:
        # 클라이언트로부터 받은 데이터
        data = request.get_json()
        
        # 상세 로깅 추가
        print(f"=== 주문 생성 요청 시작 ===")
        print(f"요청 데이터: {data}")
        print(f"사용자 ID: {request.headers.get('X-User-ID', 'anonymous')}")
        
        # 주문 데이터 검증 (더 상세한 검증)
        service_id = data.get('service')
        link = data.get('link')
        quantity = data.get('quantity')
        price = data.get('price', 0)
        
        # 필수 필드 검증
        missing_fields = []
        if not service_id:
            missing_fields.append('service')
        if not link:
            missing_fields.append('link')
        if not quantity:
            missing_fields.append('quantity')
        
        if missing_fields:
            error_msg = f'필수 주문 정보가 누락되었습니다: {", ".join(missing_fields)}'
            print(f"검증 실패: {error_msg}")
            return jsonify({
                'type': 'validation_error',
                'message': error_msg,
                'missing_fields': missing_fields
            }), 400
        
        # 데이터 타입 검증
        try:
            service_id = int(service_id)
            quantity = int(quantity)
            price = float(price) if price else 0
        except (ValueError, TypeError) as e:
            error_msg = f'데이터 타입 오류: service_id와 quantity는 숫자여야 합니다.'
            print(f"타입 검증 실패: {error_msg}")
            return jsonify({
                'type': 'validation_error',
                'message': error_msg
            }), 400
        
        # 사용자 ID 가져오기
        user_id = request.headers.get('X-User-ID', 'anonymous')
        
        # 포인트 잔액 확인 (결제 전 검증)
        if price > 0:
            current_points = points_db.get(user_id, 0)
            if current_points < price:
                return jsonify({
                    'type': 'payment_error',
                    'message': f'포인트가 부족합니다. 현재: {current_points}P, 필요: {price}P'
                }), 400
            
            print(f"포인트 잔액 확인: {user_id} - 현재: {current_points}P, 필요: {price}P")
        
        # 주문 ID 생성 (우리 플랫폼 고유)
        order_id = f"SNSPMT_{int(time.time())}_{user_id[:8]}"
        
        # PostgreSQL에 주문 저장
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO orders (order_id, user_id, service_id, link, quantity, price, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (order_id, user_id, service_id, link, quantity, price, 'pending', datetime.now()))
                conn.commit()
                print(f"PostgreSQL 주문 저장 완료: {order_id}")
        except Exception as e:
            print(f"PostgreSQL 저장 실패: {e}")
            # 로컬 메모리에도 백업 저장
            if user_id not in orders_db:
                orders_db[user_id] = []
            
            order_info = {
                'id': order_id,
                'service': service_id,
                'link': link,
                'quantity': quantity,
                'runs': data.get('runs', 1),
                'interval': data.get('interval', 0),
                'comments': data.get('comments', ''),
                'username': data.get('username', ''),
                'min': data.get('min', 0),
                'max': data.get('max', 0),
                'posts': data.get('posts', 0),
                'delay': data.get('delay', 0),
                'expiry': data.get('expiry', ''),
                'old_posts': data.get('old_posts', 0),
                'status': 'pending',
                'created_at': datetime.now().isoformat(),
                'user_id': user_id,
                'total_price': price
            }
            orders_db[user_id].append(order_info)
        
        # 주문을 'pending_payment' 상태로 저장 (결제 대기)
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE orders 
                    SET status = 'pending_payment', updated_at = %s
                    WHERE order_id = %s
                """, (datetime.now(), order_id))
                conn.commit()
                print(f"주문 상태를 'pending_payment'로 업데이트: {order_id}")
        except Exception as e:
            print(f"주문 상태 업데이트 실패: {e}")
        
        # 알림 생성 (알림 시스템이 사용 가능한 경우)
        if NOTIFICATIONS_AVAILABLE:
            try:
                from api.notifications import notify_order_status_change
                notify_order_status_change(user_id, order_id, None, 'pending')
                print(f"주문 생성 알림 전송 완료: {user_id}")
            except Exception as e:
                print(f"알림 전송 실패: {e}")
        
        # 성공 응답 반환
        success_response = {
            'order': order_id,
            'status': 'pending_payment',
            'message': '주문이 생성되었습니다. 결제를 완료해주세요.',
            'price': price,
            'current_points': points_db.get(user_id, 0)
        }
        
        print(f"=== 주문 생성 완료 ===")
        print(f"주문 ID: {order_id}")
        return jsonify(success_response), 200
        
    except Exception as e:
        print(f"=== 주문 생성 실패 ===")
        print(f"오류: {str(e)}")
        return jsonify({'error': f'주문 생성 실패: {str(e)}'}), 500

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
                current_points = points_db.get(user_id, 0)
                if current_points < order['price']:
                    return jsonify({
                        'type': 'payment_error',
                        'message': f'포인트가 부족합니다. 현재: {current_points}P, 필요: {order["price"]}P'
                    }), 400
                
                # 포인트 차감
                points_db[user_id] = current_points - order['price']
                print(f"포인트 차감 완료: {user_id}에서 {order['price']}P 차감 (잔액: {points_db[user_id]}P)")
                
                # smmpanel.kr API로 주문 전송
                try:
                    print(f"smmpanel.kr API로 주문 전송 시작...")
                    
                    # API 요청 데이터 구성
                    api_data = {
                        'service': order['service_id'],
                        'link': order['link'],
                        'quantity': order['quantity']
                    }
                    
                    # 추가 옵션들 추가 (data에서 가져옴)
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
                        
                        # 알림 생성 (알림 시스템이 사용 가능한 경우)
                        if NOTIFICATIONS_AVAILABLE:
                            try:
                                from api.notifications import notify_order_status_change
                                notify_order_status_change(user_id, order_id, 'pending_payment', 'processing')
                                print(f"주문 처리 시작 알림 전송 완료: {user_id}")
                            except Exception as e:
                                print(f"알림 전송 실패: {e}")
                        
                        return jsonify({
                            'success': True,
                            'orderId': order_id,
                            'externalOrderId': external_order_id,
                            'status': 'processing',
                            'message': '결제가 완료되었고 주문이 처리 중입니다.',
                            'points_used': order['price'],
                            'remaining_points': points_db[user_id]
                        }), 200
                    else:
                        print(f"smmpanel.kr API 오류: {response.status_code} - {response.text}")
                        # API 실패 시 포인트 환불
                        points_db[user_id] = current_points
                        return jsonify({
                            'error': '외부 API 전송에 실패했습니다. 포인트가 환불되었습니다.'
                        }), 500
                        
                except Exception as e:
                    print(f"smmpanel.kr API 전송 실패: {e}")
                    # API 실패 시 포인트 환불
                    points_db[user_id] = current_points
                    return jsonify({
                        'error': f'외부 API 전송 실패: {str(e)}. 포인트가 환불되었습니다.'
                    }), 500
                    
        except Exception as e:
            print(f"데이터베이스 오류: {e}")
            return jsonify({'error': f'데이터베이스 오류: {str(e)}'}), 500
        
    except Exception as e:
        print(f"=== 주문 결제 완료 실패 ===")
        print(f"오류: {str(e)}")
        return jsonify({'error': f'주문 결제 완료 실패: {str(e)}'}), 500

@app.route('/api/orders', methods=['GET'])
def get_user_orders():
    """사용자별 주문 정보 조회"""
    try:
        user_id = request.args.get('user_id', 'anonymous')
        
        # 디버깅용 로그
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
                    
                    # 외부 주문 ID가 있으면 smmpanel.kr API에서 최신 상태 조회
                    if order['external_order_id']:
                        try:
                            status_response = requests.post(SMMPANEL_API_URL, json={
                                'key': API_KEY,
                                'action': 'status',
                                'order': order['external_order_id']
                            }, timeout=10)
                            
                            if status_response.status_code == 200:
                                status_data = status_response.json()
                                if 'status' in status_data:
                                    order['status'] = status_data['status']
                                    # PostgreSQL 상태 업데이트
                                    cursor.execute("""
                                        UPDATE orders 
                                        SET status = %s, updated_at = %s
                                        WHERE order_id = %s
                                    """, (status_data['status'], datetime.now(), order['id']))
                                if 'start_count' in status_data:
                                    order['start_count'] = status_data['start_count']
                                if 'remains' in status_data:
                                    order['remains'] = status_data['remains']
                        except Exception as e:
                            print(f"외부 API 상태 조회 실패: {e}")
                    
                    orders.append(order)
                
                conn.commit()
                return jsonify({'orders': orders}), 200
                
        except Exception as e:
            print(f"PostgreSQL 조회 실패: {e}")
            # 로컬 메모리에서 조회 (백업)
            if user_id not in orders_db:
                return jsonify({'orders': []}), 200
            
            return jsonify({'orders': orders_db[user_id]}), 200
        
    except Exception as e:
        return jsonify({'error': f'주문 조회 실패: {str(e)}'}), 500

@app.route('/api/orders/<order_id>', methods=['GET'])
def get_order_detail(order_id):
    """특정 주문 상세 정보 조회"""
    try:
        user_id = request.args.get('user_id', 'anonymous')
        
        if user_id not in orders_db:
            return jsonify({'error': '주문을 찾을 수 없습니다.'}), 404
        
        order = next((o for o in orders_db[user_id] if o['id'] == order_id), None)
        
        if not order:
            return jsonify({'error': '주문을 찾을 수 없습니다.'}), 404
        
        # smmpanel.kr API에서 최신 상태 조회
        try:
            status_response = requests.post(SMMPANEL_API_URL, json={
                'key': API_KEY,
                'action': 'status',
                'order': order_id
            }, timeout=10)
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                order.update(status_data)
        except:
            pass
        
        return jsonify(order), 200
        
    except Exception as e:
        return jsonify({'error': f'주문 상세 조회 실패: {str(e)}'}), 500

@app.route('/api/services', methods=['GET'])
def get_smmpanel_services():
    """smmpanel.kr API에서 실제 서비스 목록 조회 (캐싱 적용)"""
    # 캐시 키 생성
    cache_key = generate_cache_key('services', 'smmpanel')
    
    # 캐시에서 조회 시도
    cached_data = cache_get(cache_key, expire=600)  # 10분 캐시
    if cached_data:
        return jsonify(cached_data), 200
    
    try:
        response = requests.post(SMMPANEL_API_URL, json={
            'key': API_KEY,
            'action': 'services'
        }, timeout=30)
        
        if response.status_code == 200:
            services_data = response.json()
            # 캐시에 저장
            cache_set(cache_key, services_data, expire=600)
            return jsonify(services_data), 200
        else:
            return jsonify({'error': f'smmpanel.kr API 오류: {response.status_code}'}), response.status_code
            
    except Exception as e:
        return jsonify({'error': f'서비스 조회 실패: {str(e)}'}), 500



@app.route('/', methods=['GET'])
def root():
    return send_from_directory('dist', 'index.html')

@app.route('/admin', methods=['GET'])
def admin_page():
    """관리자 페이지 서빙"""
    return send_from_directory('dist', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('dist', path)

# smmpanel.kr API 추가 기능들
@app.route('/api/balance', methods=['GET'])
def get_balance():
    """smmpanel.kr API에서 잔액 조회"""
    try:
        response = requests.post(SMMPANEL_API_URL, json={
            'key': API_KEY,
            'action': 'balance'
        }, timeout=30)
        
        if response.status_code == 200:
            balance_data = response.json()
            print(f"smmpanel.kr API Balance Response: {balance_data}")
            return jsonify(balance_data), 200
        else:
            return jsonify({'error': f'smmpanel.kr API 오류: {response.status_code}'}), response.status_code
            
    except Exception as e:
        return jsonify({'error': f'잔액 조회 실패: {str(e)}'}), 500

@app.route('/api/refill', methods=['POST'])
def refill_order():
    """주문 리필"""
    try:
        data = request.get_json()
        data['key'] = API_KEY
        data['action'] = 'refill'
        
        response = requests.post(SMMPANEL_API_URL, json=data, timeout=30)
        return jsonify(response.json()), response.status_code
        
    except Exception as e:
        return jsonify({'error': f'리필 실패: {str(e)}'}), 500

@app.route('/api/cancel', methods=['POST'])
def cancel_orders():
    """주문 취소"""
    try:
        data = request.get_json()
        data['key'] = API_KEY
        data['action'] = 'cancel'
        
        response = requests.post(SMMPANEL_API_URL, json=data, timeout=30)
        return jsonify(response.json()), response.status_code
        
    except Exception as e:
        return jsonify({'error': f'취소 실패: {str(e)}'}), 500

# 관리자 API 엔드포인트 (PostgreSQL 사용)
def get_admin_db_connection():
    """관리자 API용 PostgreSQL 연결"""
    try:
        if POSTGRES_AVAILABLE and db_pool:
            # PostgreSQL 연결 풀 사용
            conn = db_pool.getconn()
            return conn
        else:
            # 직접 연결
            database_url = "postgresql://snspmt_admin:Snspmt2024!@snspmt-db.cvmiee0q0zhs.ap-northeast-2.rds.amazonaws.com:5432/postgres"
            conn = psycopg2.connect(database_url)
            return conn
    except Exception as e:
        print(f"관리자 DB 연결 실패: {e}")
        raise e

@app.route('/api/admin/stats', methods=['GET'])
def get_admin_stats():
    """관리자 통계 데이터 제공 (수정됨)"""
    
    try:
        with get_admin_db_connection() as conn:
            cursor = conn.cursor()
            
            # 현재 날짜와 한 달 전 날짜 계산
            now = datetime.now()
            one_month_ago = now - timedelta(days=30)
            
            # 기본값 설정
            total_users = 0
            monthly_users = 0
            total_revenue = 0
            monthly_revenue = 0
            total_smmkings_charge = 0
            monthly_smmkings_charge = 0
            
            try:
                # 총 가입자 수 (users 테이블에서 조회)
                cursor.execute("SELECT COUNT(*) FROM users")
                result = cursor.fetchone()
                total_users = result[0] if result else 0
            except Exception as e:
                print(f"총 가입자 수 조회 오류: {e}")
            
            try:
                # 한 달 가입자 수
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM users 
                    WHERE created_at >= %s
                """, (one_month_ago.strftime('%Y-%m-%d'),))
                result = cursor.fetchone()
                monthly_users = result[0] if result else 0
            except Exception as e:
                print(f"한 달 가입자 수 조회 오류: {e}")
            
            try:
                # 총 매출액 (포인트 충전 금액)
                cursor.execute("SELECT SUM(price) FROM purchases WHERE status = 'approved'")
                result = cursor.fetchone()
                total_revenue = result[0] if result and result[0] else 0
            except Exception as e:
                print(f"총 매출액 조회 오류: {e}")
            
            try:
                # 한 달 매출액 (포인트 충전 금액)
                cursor.execute("""
                    SELECT SUM(price) 
                    FROM purchases 
                    WHERE status = 'approved' AND created_at >= %s
                """, (one_month_ago.strftime('%Y-%m-%d'),))
                result = cursor.fetchone()
                monthly_revenue = result[0] if result and result[0] else 0
            except Exception as e:
                print(f"한 달 매출액 조회 오류: {e}")
            
            try:
                # 총 SMM KINGS 충전액 (실제 비용)
                cursor.execute("SELECT SUM(smmkings_cost) FROM orders WHERE status = 'completed'")
                result = cursor.fetchone()
                total_smmkings_charge = result[0] if result and result[0] else 0
            except Exception as e:
                print(f"총 SMM KINGS 충전액 조회 오류: {e}")
            
            try:
                # 한 달 SMM KINGS 충전액
                cursor.execute("""
                    SELECT SUM(smmkings_cost) 
                    FROM orders 
                    WHERE status = 'completed' AND created_at >= %s
                """, (one_month_ago.strftime('%Y-%m-%d'),))
                result = cursor.fetchone()
                monthly_smmkings_charge = result[0] if result and result[0] else 0
            except Exception as e:
                print(f"한 달 SMM KINGS 충전액 조회 오류: {e}")
            
            # 현재 월의 원가 계산
            current_month = now.strftime('%Y-%m')
            monthly_cost = 0
            try:
                cursor.execute("SELECT total_cost FROM monthly_costs WHERE month = %s", (current_month,))
                result = cursor.fetchone()
                monthly_cost = result[0] if result else 0
            except Exception as e:
                print(f"월별 원가 조회 오류: {e}")
            
            result_data = {
                'success': True,
                'data': {
                    'totalUsers': total_users,
                    'monthlyUsers': monthly_users,
                    'totalRevenue': total_revenue,
                    'monthlyRevenue': monthly_revenue,
                    'totalSMMKingsCharge': total_smmkings_charge,
                    'monthlySMMKingsCharge': monthly_smmkings_charge,
                    'monthlyCost': monthly_cost
                }
            }
            
            return jsonify(result_data)
            
    except Exception as e:
        print(f"관리자 통계 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/transactions', methods=['GET'])
def get_admin_transactions():
    """충전 및 환불 내역 제공 (수정됨)"""
    try:
        with get_admin_db_connection() as conn:
            cursor = conn.cursor()
            
            # 충전 내역 (purchases 테이블에서 조회)
            try:
                cursor.execute("""
                    SELECT 
                        id,
                        user_id,
                        price,
                        created_at,
                        status
                    FROM purchases 
                    WHERE status = 'approved'
                    ORDER BY created_at DESC
                    LIMIT 20
                """)
                charges = []
                for row in cursor.fetchall():
                    charges.append({
                        'id': row[0],
                        'user': row[1],
                        'amount': row[2],
                        'date': row[3],
                        'status': row[4]
                    })
            except Exception as e:
                print(f"충전 내역 조회 오류: {e}")
                charges = []
            
            # 환불 내역 (purchases 테이블에서 조회)
            try:
                cursor.execute("""
                    SELECT 
                        id,
                        user_id,
                        price,
                        created_at,
                        status
                    FROM purchases 
                    WHERE status = 'rejected'
                    ORDER BY created_at DESC
                    LIMIT 20
                """)
                refunds = []
                for row in cursor.fetchall():
                    refunds.append({
                        'id': row[0],
                        'user': row[1],
                        'amount': row[2],
                        'date': row[3],
                        'reason': '관리자 거절'
                    })
            except Exception as e:
                print(f"환불 내역 조회 오류: {e}")
                refunds = []
            
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

# 관리자 구매 내역 API
@app.route('/api/admin/purchases/pending', methods=['GET'])
def get_pending_purchases():
    """대기 중인 구매 내역 조회"""
    try:
        with get_admin_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    id,
                    purchase_id,
                    user_id,
                    amount,
                    price,
                    status,
                    depositor_name,
                    bank_name,
                    receipt_type,
                    created_at
                FROM purchases 
                WHERE status = 'pending'
                ORDER BY created_at DESC
            """)
            
            purchases = []
            for row in cursor.fetchall():
                purchases.append({
                    'id': row[0],
                    'purchaseId': row[1],
                    'userId': row[2],
                    'amount': row[3],
                    'price': row[4],
                    'status': row[5],
                    'depositorName': row[6],
                    'bankName': row[7],
                    'receiptType': row[8],
                    'createdAt': row[9]
                })
            
            return jsonify({
                'success': True,
                'purchases': purchases
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# 포인트 관련 API
@app.route('/api/points', methods=['GET', 'PUT'])
def points_endpoint():
    """포인트 관련 엔드포인트"""
    if request.method == 'PUT':
        return update_user_points()
    else:
        return get_user_points()

# 포인트 구매 승인/거절 API
@app.route('/api/purchases/<purchase_id>/approve', methods=['PUT'])
def approve_purchase(purchase_id):
    """포인트 구매 신청 승인"""
    try:
        user_id = request.headers.get('X-User-ID', 'anonymous')
        
        # 관리자 권한 확인 (실제로는 더 엄격한 인증 필요)
        if not user_id or user_id == 'anonymous':
            return jsonify({'error': '관리자 권한이 필요합니다.'}), 403
        
        # PostgreSQL에서 구매 신청 조회
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, user_id, points, amount, status, created_at
                    FROM purchases 
                    WHERE id = %s
                """, (purchase_id,))
                
                purchase = cursor.fetchone()
                if not purchase:
                    return jsonify({'error': '구매 신청을 찾을 수 없습니다.'}), 404
                
                if purchase['status'] != 'pending':
                    return jsonify({'error': '승인 대기 상태가 아닙니다.'}), 400
                
                # 포인트 추가
                current_points = points_db.get(purchase['user_id'], 0)
                points_db[purchase['user_id']] = current_points + purchase['points']
                
                # 구매 상태를 'approved'로 업데이트
                cursor.execute("""
                    UPDATE purchases 
                    SET status = 'approved', updated_at = %s
                    WHERE id = %s
                """, (datetime.now(), purchase_id))
                conn.commit()
                
                print(f"구매 승인 완료: {purchase_id} - {purchase['user_id']}에게 {purchase['points']}P 추가")
                
                # 알림 생성 (알림 시스템이 사용 가능한 경우)
                if NOTIFICATIONS_AVAILABLE:
                    try:
                        from api.notifications import notify_points_charged
                        notify_points_charged(purchase['user_id'], purchase['points'], purchase['amount'])
                        print(f"포인트 충전 알림 전송 완료: {purchase['user_id']}")
                    except Exception as e:
                        print(f"알림 전송 실패: {e}")
                
                return jsonify({
                    'success': True,
                    'message': f'{purchase["points"]}P가 성공적으로 추가되었습니다.',
                    'purchase_id': purchase_id,
                    'user_id': purchase['user_id'],
                    'points_added': purchase['points'],
                    'remaining_points': points_db[purchase['user_id']]
                }), 200
                
        except Exception as e:
            print(f"데이터베이스 오류: {e}")
            return jsonify({'error': f'데이터베이스 오류: {str(e)}'}), 500
        
    except Exception as e:
        print(f"구매 승인 실패: {str(e)}")
        return jsonify({'error': f'구매 승인 실패: {str(e)}'}), 500

@app.route('/api/purchases/<purchase_id>/reject', methods=['PUT'])
def reject_purchase(purchase_id):
    """포인트 구매 신청 거절"""
    try:
        user_id = request.headers.get('X-User-ID', 'anonymous')
        data = request.get_json()
        reason = data.get('reason', '관리자에 의해 거절되었습니다.')
        
        # 관리자 권한 확인
        if not user_id or user_id == 'anonymous':
            return jsonify({'error': '관리자 권한이 필요합니다.'}), 403
        
        # PostgreSQL에서 구매 신청 조회
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, user_id, points, amount, status, created_at
                    FROM purchases 
                    WHERE id = %s
                """, (purchase_id,))
                
                purchase = cursor.fetchone()
                if not purchase:
                    return jsonify({'error': '구매 신청을 찾을 수 없습니다.'}), 404
                
                if purchase['status'] != 'pending':
                    return jsonify({'error': '승인 대기 상태가 아닙니다.'}), 400
                
                # 구매 상태를 'rejected'로 업데이트
                cursor.execute("""
                    UPDATE purchases 
                    SET status = 'rejected', updated_at = %s, rejection_reason = %s
                    WHERE id = %s
                """, (datetime.now(), reason, purchase_id))
                conn.commit()
                
                print(f"구매 거절 완료: {purchase_id} - {purchase['user_id']}의 {purchase['points']}P 신청 거절")
                
                # 알림 생성 (알림 시스템이 사용 가능한 경우)
                if NOTIFICATIONS_AVAILABLE:
                    try:
                        from api.notifications import create_notification
                        create_notification(
                            purchase['user_id'],
                            'purchase_rejected',
                            '포인트 구매 신청 거절',
                            f'포인트 구매 신청이 거절되었습니다. 사유: {reason}',
                            {'purchase_id': purchase_id, 'points': purchase['points'], 'amount': purchase['amount']}
                        )
                        print(f"구매 거절 알림 전송 완료: {purchase['user_id']}")
                    except Exception as e:
                        print(f"알림 전송 실패: {e}")
                
                return jsonify({
                    'success': True,
                    'message': '구매 신청이 거절되었습니다.',
                    'purchase_id': purchase_id,
                    'user_id': purchase['user_id'],
                    'rejection_reason': reason
                }), 200
                
        except Exception as e:
            print(f"데이터베이스 오류: {e}")
            return jsonify({'error': f'데이터베이스 오류: {str(e)}'}), 500
        
    except Exception as e:
        print(f"구매 거절 실패: {str(e)}")
        return jsonify({'error': f'구매 거절 실패: {str(e)}'}), 500

@app.route('/api/purchases/bulk-approve', methods=['POST'])
def bulk_approve_purchases():
    """여러 포인트 구매 신청 일괄 승인"""
    try:
        user_id = request.headers.get('X-User-ID', 'anonymous')
        data = request.get_json()
        purchase_ids = data.get('purchase_ids', [])
        
        # 관리자 권한 확인
        if not user_id or user_id == 'anonymous':
            return jsonify({'error': '관리자 권한이 필요합니다.'}), 403
        
        if not purchase_ids:
            return jsonify({'error': '승인할 구매 신청을 선택해주세요.'}), 400
        
        approved_count = 0
        failed_count = 0
        results = []
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                for purchase_id in purchase_ids:
                    try:
                        # 구매 신청 조회
                        cursor.execute("""
                            SELECT id, user_id, points, amount, status
                            FROM purchases 
                            WHERE id = %s AND status = 'pending'
                        """, (purchase_id,))
                        
                        purchase = cursor.fetchone()
                        if not purchase:
                            results.append({
                                'purchase_id': purchase_id,
                                'success': False,
                                'message': '구매 신청을 찾을 수 없거나 이미 처리되었습니다.'
                            })
                            failed_count += 1
                            continue
                        
                        # 포인트 추가
                        current_points = points_db.get(purchase['user_id'], 0)
                        points_db[purchase['user_id']] = current_points + purchase['points']
                        
                        # 구매 상태를 'approved'로 업데이트
                        cursor.execute("""
                            UPDATE purchases 
                            SET status = 'approved', updated_at = %s
                            WHERE id = %s
                        """, (datetime.now(), purchase_id))
                        
                        approved_count += 1
                        results.append({
                            'purchase_id': purchase_id,
                            'success': True,
                            'message': f'{purchase["points"]}P 추가 완료',
                            'user_id': purchase['user_id'],
                            'points_added': purchase['points']
                        })
                        
                        # 알림 생성
                        if NOTIFICATIONS_AVAILABLE:
                            try:
                                from api.notifications import notify_points_charged
                                notify_points_charged(purchase['user_id'], purchase['points'], purchase['amount'])
                            except Exception as e:
                                print(f"알림 전송 실패: {e}")
                        
                    except Exception as e:
                        results.append({
                            'purchase_id': purchase_id,
                            'success': False,
                            'message': f'처리 실패: {str(e)}'
                        })
                        failed_count += 1
                
                conn.commit()
                
                print(f"일괄 승인 완료: {approved_count}개 승인, {failed_count}개 실패")
                
                return jsonify({
                    'success': True,
                    'message': f'{approved_count}개의 구매 신청이 승인되었습니다.',
                    'approved_count': approved_count,
                    'failed_count': failed_count,
                    'results': results
                }), 200
                
        except Exception as e:
            print(f"데이터베이스 오류: {e}")
            return jsonify({'error': f'데이터베이스 오류: {str(e)}'}), 500
        
    except Exception as e:
        print(f"일괄 승인 실패: {str(e)}")
        return jsonify({'error': f'일괄 승인 실패: {str(e)}'}), 500

def update_user_points():
    """사용자 포인트 차감"""
    try:
        data = request.get_json()
        user_id = data.get('userId')
        points_to_deduct = data.get('points')
        order_id = data.get('orderId')
        
        print(f"=== 포인트 차감 요청 ===")
        print(f"사용자 ID: {user_id}")
        print(f"차감 포인트: {points_to_deduct}")
        print(f"주문 ID: {order_id}")
        
        if not user_id or points_to_deduct is None:
            return jsonify({'error': 'userId and points are required'}), 400
        
        current_points = points_db.get(user_id, 0)
        print(f"현재 포인트: {current_points}")
        
        if current_points < points_to_deduct:
            return jsonify({'error': f'포인트가 부족합니다. 현재: {current_points}P, 필요: {points_to_deduct}P'}), 400
        
        # 포인트 차감
        points_db[user_id] = current_points - points_to_deduct
        
        # 포인트 사용 내역 저장
        if user_id not in purchases_db:
            purchases_db[user_id] = []
        
        purchase_record = {
            'id': f"purchase_{int(time.time())}",
            'purchase_id': order_id,
            'user_id': user_id,
            'amount': points_to_deduct,
            'price': points_to_deduct,  # 1포인트 = 1원
            'status': 'approved',
            'created_at': datetime.now().isoformat(),
            'type': 'order_payment',
            'order_id': order_id
        }
        
        purchases_db[user_id].append(purchase_record)
        
        print(f"포인트 차감 완료: 사용자 {user_id}에서 {points_to_deduct}P 차감 (잔액: {points_db[user_id]}P)")
        print(f"구매 내역 저장: {purchase_record}")
        
        return jsonify({
            'success': True,
            'remainingPoints': points_db[user_id],
            'pointsUsed': points_to_deduct,
            'message': '포인트가 성공적으로 차감되었습니다.'
        }), 200
        
    except Exception as e:
        print(f"포인트 차감 실패: {str(e)}")
        return jsonify({'error': str(e)}), 500

def get_user_points():
    """사용자 포인트 조회"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        points = points_db.get(user_id, 0)
        return jsonify({'points': points}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)        }), 500

@app.route('/api/purchases', methods=['GET', 'POST'])
def purchases_endpoint():
    """구매 관련 엔드포인트"""
    if request.method == 'POST':
        return create_purchase()
    else:
        return get_purchase_history()

def create_purchase():
    """포인트 구매 신청"""
    try:
        data = request.get_json()
        user_id = data.get('userId')
        depositor_name = data.get('depositorName')
        bank_name = data.get('bankName')
        receipt_type = data.get('receiptType', 'none')
        business_number = data.get('businessNumber', '')
        business_name = data.get('businessName', '')
        representative = data.get('representative', '')
        contact_phone = data.get('contactPhone', '')
        contact_email = data.get('contactEmail', '')
        cash_receipt_phone = data.get('cashReceiptPhone', '')
        amount = data.get('amount')
        price = data.get('price')
        
        if not all([user_id, depositor_name, bank_name, amount, price]):
            return jsonify({'error': '모든 필수 정보를 입력해주세요'}), 400
        
        purchase_id = f"purchase_{len(purchases_db) + 1}_{int(datetime.now().timestamp())}"
        
        purchase_info = {
            'id': purchase_id,
            'userId': user_id,
            'depositorName': depositor_name,
            'bankName': bank_name,
            'receiptType': receipt_type,
            'businessNumber': business_number,
            'businessName': business_name,
            'representative': representative,
            'contactPhone': contact_phone,
            'contactEmail': contact_email,
            'cashReceiptPhone': cash_receipt_phone,
            'amount': amount,
            'price': price,
            'status': 'pending',
            'createdAt': datetime.now().isoformat()
        }
        
        if user_id not in purchases_db:
            purchases_db[user_id] = []
        
        purchases_db[user_id].append(purchase_info)
        
        print(f"구매 신청 생성: {purchase_info}")
        
        return jsonify({
            'success': True,
            'purchaseId': purchase_id,
            'message': '구매 신청이 완료되었습니다.'
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_purchase_history():
    """구매 내역 조회"""
    try:
        user_id = request.args.get('user_id')
        
        if user_id:
            # 특정 사용자의 구매 내역 조회
            history = purchases_db.get(user_id, [])
            return jsonify({'history': history}), 200
        else:
            # 관리자용: 모든 구매 내역 조회
            all_history = {}
            for uid, purchases in purchases_db.items():
                all_history[uid] = purchases
            return jsonify({'history': all_history}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/api/users/register', methods=['POST'])
def register_user():
    """사용자 등록 (로그인 시 호출)"""
    try:
        data = request.get_json()
        user_id = data.get('userId')
        email = data.get('email')
        display_name = data.get('displayName', '')
        
        # 비즈니스 계정 정보
        account_type = data.get('accountType', 'personal')
        business_number = data.get('businessNumber', '')
        business_name = data.get('businessName', '')
        representative = data.get('representative', '')
        contact_phone = data.get('contactPhone', '')
        contact_email = data.get('contactEmail', '')
        
        if not user_id or not email:
            return jsonify({'error': 'userId and email are required'}), 400
        
        # 사용자 정보 저장/업데이트
        users_db[user_id] = {
            'id': user_id,
            'email': email,
            'displayName': display_name,
            'accountType': account_type,
            'businessNumber': business_number,
            'businessName': business_name,
            'representative': representative,
            'contactPhone': contact_phone,
            'contactEmail': contact_email,
            'registeredAt': datetime.now().isoformat(),
            'lastLoginAt': datetime.now().isoformat(),
            'totalOrders': 0,
            'totalSpent': 0,
            'currentPoints': points_db.get(user_id, 0)
        }
        
        print(f"사용자 등록/업데이트: {user_id} ({email}) - 계정타입: {account_type}")
        if account_type == 'business':
            print(f"비즈니스 정보: {business_name} ({business_number})")
        
        return jsonify({
            'success': True,
            'message': '사용자 정보가 저장되었습니다.'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/login', methods=['POST'])
def user_login():
    """사용자 로그인"""
    try:
        data = request.get_json()
        user_id = data.get('userId')
        
        if not user_id:
            return jsonify({'error': 'userId is required'}), 400
        
        # 마지막 로그인 시간 업데이트
        if user_id in users_db:
            users_db[user_id]['lastLoginAt'] = datetime.now().isoformat()
        
        # 실시간 접속 사용자에 추가
        user_sessions[user_id] = {
            'loginTime': datetime.now().isoformat(),
            'lastActivity': datetime.now().isoformat()
        }
        
        print(f"사용자 로그인: {user_id}")
        
        return jsonify({
            'success': True,
            'message': '로그인 정보가 기록되었습니다.'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/activity', methods=['POST'])
def update_user_activity():
    """사용자 활동 업데이트 (최적화됨)"""
    try:
        data = request.get_json()
        user_id = data.get('userId')
        
        if not user_id:
            return jsonify({'error': 'userId is required'}), 400
        
        # 사용자 활동 업데이트 제한 (30분마다만 허용)
        current_time = datetime.now()
        if user_id in user_sessions:
            last_update = user_sessions[user_id].get('lastActivityUpdate')
            if last_update:
                last_update_time = datetime.fromisoformat(last_update)
                time_diff = (current_time - last_update_time).total_seconds()
                
                # 30분(1800초) 이내에 이미 업데이트된 경우 스킵
                if time_diff < 1800:
                    return jsonify({'success': True, 'message': 'Activity already updated recently'}), 200
        
        # 실시간 접속 사용자 활동 시간 업데이트
        if user_id in user_sessions:
            user_sessions[user_id]['lastActivity'] = current_time.isoformat()
            user_sessions[user_id]['lastActivityUpdate'] = current_time.isoformat()
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/users', methods=['GET'])
def get_users_info():
    """관리자용 사용자 정보 조회 (수정됨)"""
    try:
        with get_admin_db_connection() as conn:
            cursor = conn.cursor()
            
            # 총 사용자 수
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            # 실시간 접속 사용자 수 (30분 이내 활동)
            now = datetime.now()
            thirty_minutes_ago = now - timedelta(minutes=30)
            cursor.execute("""
                SELECT COUNT(*) FROM users 
                WHERE last_activity >= %s
            """, (thirty_minutes_ago.strftime('%Y-%m-%d %H:%M:%S'),))
            active_users = cursor.fetchone()[0]
            
            # 오늘 신규 가입자 수
            today = now.strftime('%Y-%m-%d')
            cursor.execute("""
                SELECT COUNT(*) FROM users 
                WHERE created_at::date = %s
            """, (today,))
            new_users_today = cursor.fetchone()[0]
            
            # 이번 주 신규 가입자 수
            week_ago = (now - timedelta(days=7)).strftime('%Y-%m-%d')
            cursor.execute("""
                SELECT COUNT(*) FROM users 
                WHERE created_at::date >= %s
            """, (week_ago,))
            new_users_week = cursor.fetchone()[0]
            
            # 최근 사용자 목록 (최근 50명)
            cursor.execute("""
                SELECT user_id, email, display_name, created_at, last_activity
                FROM users 
                ORDER BY created_at DESC 
                LIMIT 50
            """)
            recent_users = []
            for row in cursor.fetchall():
                recent_users.append({
                    'userId': row[0],
                    'email': row[1],
                    'displayName': row[2],
                    'createdAt': row[3],
                    'lastActivity': row[4]
                })
            
            return jsonify({
                'totalUsers': total_users,
                'activeUsers': active_users,
                'newUsersToday': new_users_today,
                'newUsersWeek': new_users_week,
                'recentUsers': recent_users
            }), 200
        
    except Exception as e:
        print(f"사용자 정보 조회 오류: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<user_id>', methods=['GET'])
def get_user_info(user_id):
    """개별 사용자 정보 조회"""
    try:
        if user_id not in users_db:
            return jsonify({'error': 'User not found'}), 404
        
        user_data = users_db[user_id].copy()
        
        # 민감한 정보 제거
        if 'password' in user_data:
            del user_data['password']
        
        return jsonify({
            'success': True,
            'user': user_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/purchases/<purchase_id>', methods=['PUT'])
def update_purchase_status(purchase_id):
    """구매 신청 승인/거절"""
    try:
        data = request.get_json()
        status = data.get('status')  # 'approved' or 'rejected'
        
        if status not in ['approved', 'rejected']:
            return jsonify({'error': 'Invalid status'}), 400
        
        # 구매 신청 찾기
        purchase = None
        for user_id, purchases in purchases_db.items():
            for p in purchases:
                if p['id'] == purchase_id:
                    purchase = p
                    break
            if purchase:
                break
        
        if not purchase:
            return jsonify({'error': 'Purchase not found'}), 404
        
        # 상태 업데이트
        purchase['status'] = status
        purchase['updatedAt'] = datetime.now().isoformat()
        
        # 승인된 경우 포인트 추가
        if status == 'approved':
            user_id = purchase['userId']
            current_points = points_db.get(user_id, 0)
            points_db[user_id] = current_points + purchase['amount']
            
            print(f"포인트 승인: 사용자 {user_id}에게 {purchase['amount']}P 추가 (총 {points_db[user_id]}P)")
            
            # 포인트 충전 완료 알림 (알림 시스템이 사용 가능한 경우)
            if NOTIFICATIONS_AVAILABLE:
                try:
                    from api.notifications import notify_points_charged
                    notify_points_charged(user_id, purchase['amount'], points_db[user_id])
                    print(f"포인트 충전 알림 전송 완료: {user_id}")
                except Exception as e:
                    print(f"포인트 충전 알림 전송 실패: {e}")
        
        return jsonify({
            'success': True,
            'message': f'구매 신청이 {status}되었습니다.'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/export/purchases', methods=['GET'])
def export_purchases():
    """포인트 구매 내역 엑셀 다운로드"""
    try:
        # 모든 구매 내역 수집
        all_purchases = []
        for user_id, purchases in purchases_db.items():
            for purchase in purchases:
                all_purchases.append({
                    '구매ID': purchase['id'],
                    '사용자ID': purchase['userId'],
                    '입금자명': purchase.get('depositorName', ''),
                    '은행': purchase.get('bankName', ''),
                    '영수증타입': purchase.get('receiptType', 'none'),
                    '사업자등록번호': purchase.get('businessNumber', ''),
                    '회사명': purchase.get('businessName', ''),
                    '대표자': purchase.get('representative', ''),
                    '담당자연락처': purchase.get('contactPhone', ''),
                    '메일주소': purchase.get('contactEmail', ''),
                    '현금영수증전화번호': purchase.get('cashReceiptPhone', ''),
                    '포인트': purchase['amount'],
                    '금액': purchase['price'],
                    '상태': purchase['status'],
                    '신청일': purchase['createdAt'],
                    '처리일': purchase.get('updatedAt', '')
                })
        
        # 날짜순으로 정렬
        all_purchases.sort(key=lambda x: x['신청일'], reverse=True)
        
        # CSV 데이터 생성
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 헤더 작성
        writer.writerow(['구매ID', '사용자ID', '입금자명', '은행', '영수증타입', '사업자등록번호', '회사명', '대표자', '담당자연락처', '메일주소', '현금영수증전화번호', '포인트', '금액', '상태', '신청일', '처리일'])
        
        # 데이터 작성
        for purchase in all_purchases:
            writer.writerow([
                purchase['구매ID'],
                purchase['사용자ID'],
                purchase['입금자명'],
                purchase['은행'],
                purchase['영수증타입'],
                purchase['사업자등록번호'],
                purchase['회사명'],
                purchase['대표자'],
                purchase['담당자연락처'],
                purchase['메일주소'],
                purchase['현금영수증전화번호'],
                purchase['포인트'],
                purchase['금액'],
                purchase['상태'],
                purchase['신청일'],
                purchase['처리일']
            ])
        
        # CSV 파일 생성
        output.seek(0)
        csv_data = output.getvalue()
        
        # 파일명에 현재 날짜 추가
        filename = f"포인트구매내역_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return jsonify({
            'success': True,
            'filename': filename,
            'data': csv_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 프론트엔드 정적 파일 서빙 (프로덕션 환경에서만)
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """프론트엔드 정적 파일 서빙"""
    # 개발 환경에서는 API만 제공
    if os.environ.get('FLASK_ENV') == 'development':
        return jsonify({'message': 'API Server Running', 'status': 'ok'}), 200
    
    # 프로덕션 환경에서만 정적 파일 서빙
    if path and os.path.exists(os.path.join('dist', path)):
        return send_from_directory('dist', path)
    else:
        return send_from_directory('dist', 'index.html')

# 성능 모니터링
@app.before_request
def start_timer():
    request.start_time = time.time()

@app.after_request
def log_request(response):
    if hasattr(request, 'start_time'):
        duration = time.time() - request.start_time
        logger.info(f"{request.method} {request.path} - {response.status_code} - {duration:.3f}s")
    return response

if __name__ == '__main__':
    # 데이터베이스 초기화
    init_database()
    
    # 데이터베이스 연결 풀 초기화 (프로덕션용)
    init_db_pool()

    # Redis 캐시 초기화
    init_redis()
    
    # Render 환경에서 포트 설정
    port = int(os.environ.get('PORT', 8000))
    
    print(f"🚀 Backend server starting on port {port}")
    print("📡 Proxying requests to snspop API...")
    print("💾 Local order storage enabled...")
    print("🌐 Serving frontend from dist/ directory...")
    
    # 프로덕션 환경에서는 debug=False
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
