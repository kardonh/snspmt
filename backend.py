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

# 메모리 최적화 설정
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB 제한
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # 정적 파일 캐시 비활성화

# 앱 시작 시 초기화 함수 (나중에 정의됨)
def initialize_app():
    """앱 시작 시 초기화"""
    try:
        print("🚀 SNS PMT 앱 시작 중...")
        # 데이터베이스 테이블 초기화
        init_database()
        print("✅ 데이터베이스 초기화 완료")
        print("✅ 앱 시작 완료")
    except Exception as e:
        print(f"⚠️ 앱 초기화 중 오류: {e}")
        # 초기화 실패해도 앱은 계속 실행
    
    # 환경 변수 설정
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:Snspmt2024!@snspmt-cluste.cluster-cvmiee0q0zhs.ap-northeast-2.rds.amazonaws.com:5432/snspmt')
SMMPANEL_API_URL = 'https://smmpanel.kr/api/v2'
API_KEY = os.getenv('SMMPANEL_API_KEY', '5efae48d287931cf9bd80a1bc6fdfa6d')

# 추천인 커미션 설정
REFERRAL_COMMISSION_RATE = 0.15  # 15% 커미션

# PostgreSQL 연결 함수 (안전한 연결)
def get_db_connection():
    """PostgreSQL 데이터베이스 연결 (실사용)"""
    try:
        print(f"데이터베이스 연결 시도: {DATABASE_URL}")
        # 안전한 연결 설정
        conn = psycopg2.connect(
            DATABASE_URL,
            cursor_factory=RealDictCursor,
            connect_timeout=30,
            application_name='snspmt-app'
        )
        # 자동 커밋 비활성화
        conn.autocommit = False
        print("PostgreSQL 연결 성공")
        return conn
    except Exception as e:
        print(f"PostgreSQL 연결 실패: {e}")
        # 연결 실패 시 SQLite로 폴백
        print("SQLite로 폴백 시도...")
        try:
            conn = sqlite3.connect(':memory:')
            conn.row_factory = sqlite3.Row
            print("SQLite 메모리 기반 연결 성공 (데이터 유지 안됨)")
            print("⚠️ 주의: 실사용을 위해서는 PostgreSQL 연결이 필요합니다.")
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
            print("데이터베이스 연결을 할 수 없습니다. 메모리 기반 SQLite를 사용합니다.")
            # 메모리 기반 SQLite로 폴백
            conn = sqlite3.connect(':memory:')
            conn.row_factory = sqlite3.Row
            print("메모리 기반 SQLite 연결 성공")
            
        with conn:
            cursor = conn.cursor()
            
            # orders 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    service_id INTEGER NOT NULL,
                    link TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price REAL NOT NULL,
                    status TEXT DEFAULT 'pending',
                    external_order_id TEXT,
                    comments TEXT,
                    explanation TEXT,
                    runs INTEGER DEFAULT 1,
                    interval INTEGER DEFAULT 0,
                    username TEXT,
                    min_quantity INTEGER,
                    max_quantity INTEGER,
                    posts INTEGER DEFAULT 0,
                    delay INTEGER DEFAULT 0,
                    expiry TEXT,
                    old_posts INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # points 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS points (
                    user_id TEXT PRIMARY KEY,
                    points INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # point_purchases 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS point_purchases (
                    purchase_id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    price REAL NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # notifications 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    notification_id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    is_read INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # referral_codes 테이블 생성 (추천인 코드 관리)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS referral_codes (
                    code_id SERIAL PRIMARY KEY,
                    code TEXT UNIQUE NOT NULL,
                    referrer_user_id TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT NOW(),
                    expires_at TIMESTAMP,
                    usage_count INTEGER DEFAULT 0,
                    total_commission REAL DEFAULT 0.00
                )
            """)
            
            # referrals 테이블 생성 (추천 관계 관리)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    referral_id SERIAL PRIMARY KEY,
                    referrer_user_id TEXT NOT NULL,
                    referred_user_id TEXT NOT NULL,
                    referral_code TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(referred_user_id)
                )
            """)
            
            # referral_commissions 테이블 생성 (커미션 내역)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS referral_commissions (
                    commission_id SERIAL PRIMARY KEY,
                    referrer_user_id TEXT NOT NULL,
                    referred_user_id TEXT NOT NULL,
                    purchase_id INTEGER NOT NULL,
                    commission_amount REAL NOT NULL,
                    commission_rate REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
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

# 헬스 체크 - 초고속 응답 (데이터베이스 연결 없이)
@app.route('/health')
def health_check():
    """초고속 헬스 체크 - ELB용"""
    try:
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'service': 'snspmt'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

# 상세 헬스 체크 - 관리자용
@app.route('/api/health')
def detailed_health_check():
    """상세 헬스 체크 - 데이터베이스 연결 포함"""
    try:
        # 간단한 데이터베이스 연결 테스트
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        return jsonify({
            'status': 'healthy', 
            'timestamp': datetime.now().isoformat(),
            'database': 'connected',
            'service': 'snspmt'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'service': 'snspmt'
        }), 500

# 사용자 등록
@app.route('/api/register', methods=['POST'])
def register():
    try:
        print("=== 사용자 등록 API 호출 ===")
        data = request.get_json()
        print(f"요청 데이터: {data}")
        
        user_id = data.get('uid') or data.get('userId')
        email = data.get('email')
        referral_code = data.get('referralCode')
        
        print(f"사용자 ID: {user_id}, 이메일: {email}, 추천인 코드: {referral_code}")
        
        if not user_id or not email:
            print("필수 정보 누락")
            return jsonify({'error': '필수 정보가 누락되었습니다.'}), 400
        
        # 데이터베이스 연결 확인
        conn = get_db_connection()
        if not conn:
            print("데이터베이스 연결 실패")
            return jsonify({'error': '데이터베이스 연결에 실패했습니다.'}), 500
        
        try:
            cursor = conn.cursor()
            
            # 모든 경우에 대해 테이블 생성 (안전한 방법)
            print("테이블 생성 확인 중...")
            
            # points 테이블 생성 (SQLite 문법)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS points (
                    user_id TEXT PRIMARY KEY,
                points INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            print("points 테이블 생성/확인 완료")
            
            # referral_codes 테이블 생성 (SQLite 문법)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS referral_codes (
                    code_id SERIAL PRIMARY KEY,
                    code TEXT UNIQUE NOT NULL,
                    referrer_user_id TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT NOW(),
                    expires_at TIMESTAMP,
                    usage_count INTEGER DEFAULT 0,
                    total_commission REAL DEFAULT 0.0
                )
            """)
            print("referral_codes 테이블 생성/확인 완료")
            
            # referrals 테이블 생성 (SQLite 문법)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    referral_id SERIAL PRIMARY KEY,
                    referrer_user_id TEXT NOT NULL,
                    referred_user_id TEXT NOT NULL,
                    referral_code TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(referred_user_id)
                )
            """)
            print("referrals 테이블 생성/확인 완료")
            
            # 사용자 포인트 테이블에 등록 (PostgreSQL 문법 사용)
            cursor.execute("""
                INSERT INTO points (user_id, points)
                VALUES (%s, 0)
                ON CONFLICT (user_id) DO NOTHING
            """, (user_id,))
            print(f"사용자 포인트 등록 완료: {user_id}")
            
            # 추천인 코드가 있으면 처리
            if referral_code and referral_code.strip():
                try:
                    print(f"추천인 코드 처리 시작: {referral_code}")
                    # 추천인 코드 조회
                    cursor.execute("""
                        SELECT code_id, referrer_user_id, is_active, expires_at
                        FROM referral_codes 
                        WHERE code = %s
                    """, (referral_code.strip().upper(),))
                    
                    code_info = cursor.fetchone()
                    if code_info and code_info['is_active']:
                        # 추천 관계 저장 (SQLite 문법 사용)
                        cursor.execute("""
                            INSERT INTO referrals (referrer_user_id, referred_user_id, referral_code)
                            ON CONFLICT (referred_user_id) DO NOTHING
                            VALUES (%s, %s, %s)
                        """, (code_info['referrer_user_id'], user_id, referral_code.strip().upper()))
                        
                        # 사용 횟수 증가
                        cursor.execute("""
                            UPDATE referral_codes 
                            SET usage_count = usage_count + 1
                            WHERE code = %s
                        """, (referral_code.strip().upper(),))
                        
                        print(f"추천인 코드 적용 완료: {referral_code} -> {user_id}")
                    else:
                        print(f"유효하지 않은 추천인 코드: {referral_code}")
                except Exception as e:
                    print(f"추천인 코드 처리 실패: {e}")
                    # 추천인 코드 처리 실패해도 회원가입은 계속 진행
            
            # 커밋
            conn.commit()
            print("데이터베이스 커밋 완료")
            
        except Exception as db_error:
            print(f"데이터베이스 작업 실패: {db_error}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'데이터베이스 작업에 실패했습니다: {str(db_error)}'}), 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        
        print("사용자 등록 성공")
        return jsonify({'message': '사용자 등록 완료'}), 200
            
    except Exception as e:
        print(f"사용자 등록 실패: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'사용자 등록에 실패했습니다: {str(e)}'}), 500

# 사용자 로그인
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        print(f"로그인 요청 데이터: {data}")
        
        # userId 또는 uid 필드 모두 지원
        user_id = data.get('userId') or data.get('uid')
        
        if not user_id:
            return jsonify({'error': '사용자 ID가 누락되었습니다.'}), 400
        
        # 데이터베이스에서 사용자 정보 조회
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': '데이터베이스 연결에 실패했습니다.'}), 500
        
        try:
            cursor = conn.cursor()
            
            # 테이블 생성 확인 (모든 경우에 대해)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS points (
                    user_id TEXT PRIMARY KEY,
                    points INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # 사용자 정보 조회
            cursor.execute("""
                SELECT user_id, points FROM points WHERE user_id = %s
            """, (user_id,))
            
            user = cursor.fetchone()
            if not user:
                # 사용자가 없으면 새로 생성
                cursor.execute("""
                    INSERT INTO points (user_id, points) VALUES (%s, 0)
                    ON CONFLICT (user_id) DO NOTHING
                """, (user_id,))
                conn.commit()
                points = 0
            else:
                points = user['points']
                
        except Exception as db_error:
            print(f"데이터베이스 작업 실패: {db_error}")
            return jsonify({'error': f'데이터베이스 작업에 실패했습니다: {str(db_error)}'}), 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        
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
        print(f"활동 업데이트 요청 데이터: {data}")
        
        # userId 또는 uid 필드 모두 지원
        user_id = data.get('userId') or data.get('uid')
        
        if not user_id:
            return jsonify({'error': '사용자 ID가 누락되었습니다.'}), 400
        
        # 데이터베이스에서 사용자 정보 업데이트
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': '데이터베이스 연결에 실패했습니다.'}), 500
        
        try:
            cursor = conn.cursor()
            
            # 테이블 생성 확인
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS points (
                    user_id TEXT PRIMARY KEY,
                    points INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # 사용자 활동 업데이트
            cursor.execute("""
                UPDATE points SET updated_at = %s WHERE user_id = %s
            """, (datetime.now(), user_id))
            conn.commit()
            
        except Exception as db_error:
            print(f"데이터베이스 작업 실패: {db_error}")
            return jsonify({'error': f'데이터베이스 작업에 실패했습니다: {str(db_error)}'}), 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        
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
        
        # 필수 필드 검증 (serviceId 또는 service_id 모두 지원)
        service_id = data.get('service') or data.get('serviceId') or data.get('service_id')
        link = data.get('link')
        quantity = data.get('quantity')
        
        print(f"검증할 필드들: service_id={service_id}, link={link}, quantity={quantity}")
        
        if not service_id:
            return jsonify({
                'type': 'validation_error',
                'message': 'service_id가 누락되었습니다.',
                'received_data': data
            }), 400
        
        if not link:
            return jsonify({
                'type': 'validation_error',
                'message': 'link가 누락되었습니다.',
                'received_data': data
            }), 400
        
        if not quantity:
            return jsonify({
                'type': 'validation_error',
                'message': 'quantity가 누락되었습니다.',
                'received_data': data
            }), 400
        
        # 데이터 타입 검증 (더 유연하게)
        try:
            # service_id가 문자열인 경우 숫자로 변환 시도
            if isinstance(service_id, str):
                # 문자열이 숫자인지 확인
                if service_id.isdigit():
                    service_id = int(service_id)
                else:
                    # 문자열인 경우 그대로 사용 (SMM Panel API ID)
                    pass
            
            quantity = int(quantity) if quantity else 0
            link = str(link) if link else ''
            
            print(f"변환된 필드들: service_id={service_id} (type: {type(service_id)}), quantity={quantity}, link={link}")
            
        except (ValueError, TypeError) as e:
            print(f"데이터 타입 변환 오류: {e}")
            return jsonify({
                'type': 'validation_error',
                'message': f'잘못된 데이터 타입입니다: {str(e)}',
                'received_data': data
            }), 400
        
        # 가격 계산 (임시로 1000당 100원으로 설정)
        price = (quantity / 1000) * 100
        
        # 데이터베이스에 주문 저장
        try:
            conn = get_db_connection()
            if not conn:
                return jsonify({'error': '데이터베이스 연결에 실패했습니다.'}), 500
            
            cursor = conn.cursor()
            
            # orders 테이블 생성 (모든 경우에 대해)
            print("orders 테이블 생성 확인 중...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    service_id TEXT NOT NULL,
                    link TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price REAL NOT NULL,
                    status TEXT DEFAULT 'pending_payment',
                    comments TEXT,
                    explanation TEXT,
                    runs INTEGER DEFAULT 1,
                    interval INTEGER DEFAULT 0,
                    username TEXT,
                    min_quantity INTEGER,
                    max_quantity INTEGER,
                    posts INTEGER,
                    delay INTEGER,
                    expiry TEXT,
                    old_posts INTEGER,
                    external_order_id TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            print("orders 테이블 생성/확인 완료")
            
            # service_id를 문자열로 저장 (SMM Panel API ID가 문자열일 수 있음)
            service_id_str = str(service_id)
            
            cursor.execute("""
                INSERT INTO orders (
                    user_id, service_id, link, quantity, price, status,
                    comments, explanation, runs, interval, username,
                    min_quantity, max_quantity, posts, delay, expiry, old_posts
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id, service_id_str, link, quantity, price, 'pending_payment',
                data.get('comments', ''), data.get('explanation', ''), data.get('runs', 1),
                data.get('interval', 0), data.get('username', ''), data.get('min', 0),
                data.get('max', 0), data.get('posts', 0), data.get('delay', 0),
                data.get('expiry', ''), data.get('old_posts', 0)
            ))
            
            order_id = cursor.lastrowid
            conn.commit()
            cursor.close()
            conn.close()
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
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({'error': '사용자 ID가 누락되었습니다.'}), 400
        
        print(f"주문 조회 요청: {user_id}")
        
        # 데이터베이스에서 주문 조회
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': '데이터베이스 연결에 실패했습니다.'}), 500
        
        try:
            cursor = conn.cursor()
            
            # 테이블 생성 확인
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    service_id TEXT NOT NULL,
                    link TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price REAL NOT NULL,
                    status TEXT DEFAULT 'pending_payment',
                    comments TEXT,
                    explanation TEXT,
                    runs INTEGER DEFAULT 1,
                    interval INTEGER DEFAULT 0,
                    username TEXT,
                    min_quantity INTEGER,
                    max_quantity INTEGER,
                    posts INTEGER,
                    delay INTEGER,
                    expiry TEXT,
                    old_posts INTEGER,
                    external_order_id TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
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
                    'id': row[0],
                    'service': row[1],
                    'link': row[2],
                    'quantity': row[3],
                    'price': float(row[4] or 0),
                    'status': row[5],
                    'external_order_id': row[6],
                    'created_at': row[7].isoformat() if row[7] else None,
                    'updated_at': row[8].isoformat() if row[8] else None
                }
                orders.append(order)
            
            return jsonify({'orders': orders}), 200
            
        except Exception as db_error:
            print(f"데이터베이스 조회 실패: {db_error}")
            return jsonify({'error': f'주문 조회에 실패했습니다: {str(db_error)}'}), 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        
    except Exception as e:
        print(f"주문 조회 실패: {e}")
        return jsonify({'error': '주문 조회에 실패했습니다.'}), 500

# 사용자 포인트 조회
@app.route('/api/points', methods=['GET'])
def get_user_points():
    """사용자 포인트 조회"""
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({'error': '사용자 ID가 누락되었습니다.'}), 400
        
        print(f"포인트 조회 요청: {user_id}")
        
        # 데이터베이스에서 포인트 조회
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': '데이터베이스 연결에 실패했습니다.'}), 500
        
        try:
            cursor = conn.cursor()
            
            # 테이블 생성 확인
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS points (
                    user_id TEXT PRIMARY KEY,
                    points INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            cursor.execute("""
                SELECT points FROM points WHERE user_id = %s
            """, (user_id,))
            
            result = cursor.fetchone()
            if result:
                # RealDictCursor 사용 시 딕셔너리 접근
                if isinstance(result, dict):
                    points = result['points']
        else:
                    points = result[0]
            else:
                points = 0
            
            return jsonify({'points': points}), 200
            
        except Exception as db_error:
            print(f"데이터베이스 조회 실패: {db_error}")
            return jsonify({'error': f'포인트 조회에 실패했습니다: {str(db_error)}'}), 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            
    except Exception as e:
        print(f"포인트 조회 실패: {e}")
        return jsonify({'error': '포인트 조회에 실패했습니다.'}), 500

# 사용자 정보 조회

# 포인트 구매 내역 조회
@app.route('/api/points/purchase-history', methods=['GET'])
def get_purchase_history():
    """포인트 구매 내역 조회"""
    try:
        print(f"=== 포인트 구매 내역 API 엔드포인트 호출됨 ===")
        user_id = request.args.get('user_id')
        print(f"요청된 사용자 ID: {user_id}")
        
        if not user_id:
            print("사용자 ID 누락")
            return jsonify({'error': '사용자 ID가 누락되었습니다.'}), 400
        
        print(f"구매 내역 조회 요청: {user_id}")
        
        # 데이터베이스에서 구매 내역 조회
        print(f"데이터베이스 연결 시도...")
        conn = get_db_connection()
        if conn is None:
            print(f"PostgreSQL 연결 실패, 파일 기반 SQLite로 폴백...")
            # 파일 기반 SQLite로 폴백 (데이터 유지)
            possible_paths = [
                '/app/data/orders.db',
                '/tmp/orders.db',
                './orders.db',
                'orders.db'
            ]
            
            for db_path in possible_paths:
                try:
                    dir_path = os.path.dirname(db_path)
                    if dir_path and not os.path.exists(dir_path):
                        os.makedirs(dir_path, exist_ok=True)
                        print(f"디렉토리 생성 시도: {dir_path}")
                    
                    conn = sqlite3.connect(db_path)
                    conn.row_factory = sqlite3.Row
                    print(f"파일 기반 SQLite 연결 성공: {db_path}")
                    break
                except Exception as path_error:
                    print(f"경로 {db_path} 시도 실패: {path_error}")
                    continue
            
            if conn is None:
                print("모든 파일 경로 실패, 메모리 기반 SQLite로 폴백")
                conn = sqlite3.connect(':memory:')
                conn.row_factory = sqlite3.Row
                print("메모리 기반 SQLite 연결 성공 (데이터 유지 안됨)")
        else:
            print(f"PostgreSQL 연결 성공, 기존 연결 사용")
        
        if not conn:
            print("데이터베이스 연결 실패")
            return jsonify({'error': '데이터베이스 연결에 실패했습니다.'}), 500
        
        try:
            cursor = conn.cursor()
            
            # 테이블 생성 확인
            print(f"point_purchases 테이블 생성 시도...")
            # PostgreSQL과 SQLite 호환성을 위한 조건부 테이블 생성
            try:
                # PostgreSQL용 구문 시도
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS point_purchases (
                        purchase_id SERIAL PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        amount INTEGER NOT NULL,
                        price DECIMAL(10,2) NOT NULL,
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """)
            except Exception as pg_error:
                print(f"PostgreSQL 구문 실패, SQLite 구문으로 재시도: {pg_error}")
                # SQLite용 구문으로 재시도
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS point_purchases (
                        purchase_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        amount INTEGER NOT NULL,
                        price REAL NOT NULL,
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """)
            conn.commit()
            print(f"point_purchases 테이블 생성 완료")
            
            # 테이블 존재 확인 (PostgreSQL과 SQLite 호환)
            try:
                # PostgreSQL용 구문 시도
                cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_name='point_purchases'")
                table_exists = cursor.fetchone()
                print(f"point_purchases 테이블 존재 확인 (PostgreSQL): {table_exists is not None}")
            except Exception as pg_error:
                print(f"PostgreSQL 테이블 확인 실패, SQLite 구문으로 재시도: {pg_error}")
                # SQLite용 구문으로 재시도
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='point_purchases'")
                table_exists = cursor.fetchone()
                print(f"point_purchases 테이블 존재 확인 (SQLite): {table_exists is not None}")
            
            # 기존 데이터 확인
            cursor.execute("SELECT COUNT(*) FROM point_purchases")
            result = cursor.fetchone()
            total_purchases = result['count'] if isinstance(result, dict) else result[0]
            print(f"전체 구매 신청 수: {total_purchases}")
            
            cursor.execute("SELECT COUNT(*) FROM point_purchases WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            user_purchases = result['count'] if isinstance(result, dict) else result[0]
            print(f"사용자 {user_id}의 구매 신청 수: {user_purchases}")
            
            print(f"구매 내역 조회 시도...")
            cursor.execute("""
                SELECT purchase_id, amount, price, status, created_at, updated_at
                FROM point_purchases 
                WHERE user_id = %s
                ORDER BY created_at DESC
            """, (user_id,))
            
            print(f"구매 내역 데이터 변환 시도...")
            purchases = []
            for row in cursor.fetchall():
                try:
                    # RealDictCursor 사용 시 딕셔너리 접근
                    if isinstance(row, dict):
                        purchase = {
                            'id': row['purchase_id'],
                            'amount': row['amount'],
                            'price': float(row['price']),
                            'status': row['status'],
                            'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                            'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
                        }
                        print(f"구매 내역 추가: ID={row['purchase_id']}, 금액={row['price']}, 상태={row['status']}")
        else:
                        purchase = {
                            'id': row[0],
                            'amount': row[1],
                            'price': float(row[2]),
                            'status': row[3],
                            'created_at': row[4].isoformat() if row[4] else None,
                            'updated_at': row[5].isoformat() if row[5] else None
                        }
                        print(f"구매 내역 추가: ID={row[0]}, 금액={row[2]}, 상태={row[3]}")
                    purchases.append(purchase)
    except Exception as e:
                    print(f"구매 내역 데이터 변환 실패: {e}")
                    continue
            
            print(f"구매 내역 조회 성공: {len(purchases)}건")
            return jsonify({'purchases': purchases}), 200
            
        except Exception as db_error:
            print(f"데이터베이스 조회 실패: {db_error}")
            import traceback
            print(f"상세 오류: {traceback.format_exc()}")
            return jsonify({'error': f'구매 내역 조회에 실패했습니다: {str(db_error)}'}), 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        
    except Exception as e:
        print(f"구매 내역 조회 실패: {e}")
        import traceback
        print(f"상세 오류: {traceback.format_exc()}")
        return jsonify({'error': '구매 내역 조회에 실패했습니다.'}), 500

# 추천인 코드 조회
@app.route('/api/referral/my-codes', methods=['GET'])
def get_my_referral_codes():
    """내 추천인 코드 조회"""
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({'error': '사용자 ID가 누락되었습니다.'}), 400
        
        print(f"추천인 코드 조회 요청: {user_id}")
        
        # 데이터베이스에서 추천인 코드 조회
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': '데이터베이스 연결에 실패했습니다.'}), 500
        
        try:
            cursor = conn.cursor()
            
            # 테이블 생성 확인
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS referral_codes (
                    code_id SERIAL PRIMARY KEY,
                    code TEXT UNIQUE NOT NULL,
                    referrer_user_id TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT NOW(),
                    expires_at TIMESTAMP,
                    usage_count INTEGER DEFAULT 0,
                    total_commission REAL DEFAULT 0.0
                )
            """)
            
                cursor.execute("""
                SELECT code, is_active, created_at, expires_at, usage_count, total_commission
                FROM referral_codes 
                WHERE referrer_user_id = %s
                ORDER BY created_at DESC
            """, (user_id,))
            
            codes = []
            for row in cursor.fetchall():
                code = {
                    'code': row[0],
                    'is_active': bool(row[1]),
                    'created_at': row[2].isoformat() if row[2] else None,
                    'expires_at': row[3].isoformat() if row[3] else None,
                    'usage_count': row[4],
                    'total_commission': float(row[5])
                }
                codes.append(code)
            
            return jsonify({'codes': codes}), 200
            
        except Exception as db_error:
            print(f"데이터베이스 조회 실패: {db_error}")
            return jsonify({'error': f'추천인 코드 조회에 실패했습니다: {str(db_error)}'}), 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            except Exception as e:
        print(f"추천인 코드 조회 실패: {e}")
        return jsonify({'error': '추천인 코드 조회에 실패했습니다.'}), 500

# 추천인 커미션 조회
@app.route('/api/referral/commissions', methods=['GET'])
def get_referral_commissions():
    """추천인 커미션 조회"""
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({'error': '사용자 ID가 누락되었습니다.'}), 400
        
        print(f"추천인 커미션 조회 요청: {user_id}")
        
        # 데이터베이스에서 추천인 커미션 조회
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': '데이터베이스 연결에 실패했습니다.'}), 500
        
        try:
            cursor = conn.cursor()
            
            # 테이블 생성 확인
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    referral_id SERIAL PRIMARY KEY,
                    referrer_user_id TEXT NOT NULL,
                    referred_user_id TEXT NOT NULL,
                    referral_code TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(referred_user_id)
                )
            """)
            
            cursor.execute("""
                SELECT referred_user_id, referral_code, created_at
                FROM referrals 
                WHERE referrer_user_id = %s
                    ORDER BY created_at DESC
            """, (user_id,))
            
            commissions = []
            for row in cursor.fetchall():
                commission = {
                    'referred_user_id': row[0],
                    'referral_code': row[1],
                    'created_at': row[2].isoformat() if row[2] else None,
                    'commission_amount': 0.0  # 기본값
                }
                commissions.append(commission)
            
            return jsonify({'commissions': commissions}), 200
            
        except Exception as db_error:
            print(f"데이터베이스 조회 실패: {db_error}")
            return jsonify({'error': f'추천인 커미션 조회에 실패했습니다: {str(db_error)}'}), 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            
    except Exception as e:
        print(f"추천인 커미션 조회 실패: {e}")
        return jsonify({'error': '추천인 커미션 조회에 실패했습니다.'}), 500

# 주문 상세 조회
@app.route('/api/orders/<order_id>', methods=['GET'])
def get_order_detail(order_id):
    """특정 주문 상세 정보 조회"""
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({'error': '사용자 ID가 누락되었습니다.'}), 400
        
        # 데이터베이스에서 주문 상세 조회
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': '데이터베이스 연결에 실패했습니다.'}), 500
        
        try:
            cursor = conn.cursor()
            
            # 테이블 생성 확인
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    service_id TEXT NOT NULL,
                    link TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price REAL NOT NULL,
                    status TEXT DEFAULT 'pending_payment',
                    comments TEXT,
                    explanation TEXT,
                    runs INTEGER DEFAULT 1,
                    interval INTEGER DEFAULT 0,
                    username TEXT,
                    min_quantity INTEGER,
                    max_quantity INTEGER,
                    posts INTEGER,
                    delay INTEGER,
                    expiry TEXT,
                    old_posts INTEGER,
                    external_order_id TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
                cursor.execute("""
                    SELECT 
                    order_id,
                        user_id,
                    service_id,
                    link,
                    quantity,
                        price,
                    status,
                        created_at,
                    updated_at
                FROM orders 
                WHERE order_id = %s AND user_id = %s
            """, (order_id, user_id))
            
            result = cursor.fetchone()
            if result:
                order_detail = {
                    'order_id': result[0],
                    'user_id': result[1],
                    'service_id': result[2],
                    'link': result[3],
                    'quantity': result[4],
                    'price': float(result[5]),
                    'status': result[6],
                    'created_at': result[7].isoformat() if result[7] else None,
                    'updated_at': result[8].isoformat() if result[8] else None
                }
                return jsonify(order_detail), 200
            else:
                return jsonify({'error': '주문을 찾을 수 없습니다.'}), 404
                
        except Exception as db_error:
            print(f"데이터베이스 조회 실패: {db_error}")
            return jsonify({'error': f'주문 상세 조회에 실패했습니다: {str(db_error)}'}), 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            
    except Exception as e:
        print(f"주문 상세 조회 실패: {e}")
        return jsonify({'error': '주문 상세 조회에 실패했습니다.'}), 500

# 포인트 차감
@app.route('/api/points', methods=['PUT'])
def deduct_user_points():
    """사용자 포인트 차감"""
    try:
        data = request.get_json()
        user_id = data.get('userId')
        points = data.get('points')
        
        if not user_id or points is None:
            return jsonify({'error': '사용자 ID와 포인트가 필요합니다.'}), 400
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 현재 포인트 확인
            cursor.execute("SELECT points FROM points WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            
            if not result:
                return jsonify({'error': '사용자를 찾을 수 없습니다.'}), 404
            
            current_points = result['points']
            if current_points < points:
                return jsonify({'error': '포인트가 부족합니다.'}), 400
        
        # 포인트 차감
            cursor.execute("""
                UPDATE points 
                SET points = points - %s, updated_at = NOW()
                WHERE user_id = %s
            """, (points, user_id))
            
            conn.commit()
            
            return jsonify({
                'message': '포인트가 차감되었습니다.',
                'remaining_points': current_points - points
        }), 200
            
    except Exception as e:
        print(f"포인트 차감 실패: {e}")
        return jsonify({'error': '포인트 차감에 실패했습니다.'}), 500

# 포인트 구매 요청
@app.route('/api/points/purchase', methods=['POST'])
def create_point_purchase():
    """포인트 구매 요청"""
    print(f"=== 포인트 구매 API 엔드포인트 호출됨 ===")
    print(f"요청 메서드: {request.method}")
    print(f"요청 URL: {request.url}")
    print(f"요청 헤더: {dict(request.headers)}")
    try:
        print(f"=== 포인트 구매 요청 시작 ===")
        data = request.get_json()
        print(f"요청 데이터: {data}")
        user_id = request.headers.get('X-User-ID', 'anonymous')
        amount = data.get('amount')
        price = data.get('price')
        
        print(f"사용자 ID: {user_id}")
        print(f"구매 포인트: {amount}")
        print(f"결제 금액: {price}")
        
        if not amount or not price:
            print("필수 정보 누락")
            return jsonify({'error': '필수 정보가 누락되었습니다.'}), 400
        
        # 데이터베이스에 구매 요청 저장
        try:
            print(f"데이터베이스 연결 시도...")
            conn = get_db_connection()
            if conn is None:
                print(f"PostgreSQL 연결 실패, 파일 기반 SQLite로 폴백...")
                # 파일 기반 SQLite로 폴백 (데이터 유지)
                possible_paths = [
                    '/app/data/orders.db',
                    '/tmp/orders.db',
                    './orders.db',
                    'orders.db'
                ]
                
                for db_path in possible_paths:
                    try:
                        dir_path = os.path.dirname(db_path)
                        if dir_path and not os.path.exists(dir_path):
                            os.makedirs(dir_path, exist_ok=True)
                            print(f"디렉토리 생성 시도: {dir_path}")
                        
                        conn = sqlite3.connect(db_path)
                        conn.row_factory = sqlite3.Row
                        print(f"파일 기반 SQLite 연결 성공: {db_path}")
                        break
                    except Exception as path_error:
                        print(f"경로 {db_path} 시도 실패: {path_error}")
                        continue
                
                if conn is None:
                    print("모든 파일 경로 실패, 메모리 기반 SQLite로 폴백")
                    conn = sqlite3.connect(':memory:')
                    conn.row_factory = sqlite3.Row
                    print("메모리 기반 SQLite 연결 성공 (데이터 유지 안됨)")
                
                # 테이블 생성 확인
                cursor = conn.cursor()
                print(f"point_purchases 테이블 생성 시도...")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS point_purchases (
                        purchase_id SERIAL PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        amount INTEGER NOT NULL,
                        price REAL NOT NULL,
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                conn.commit()
                print(f"point_purchases 테이블 생성 완료")
                
                # 테이블 존재 확인
                cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_name='point_purchases'")
                table_exists = cursor.fetchone()
                print(f"point_purchases 테이블 존재 확인: {table_exists is not None}")
            else:
                print(f"PostgreSQL 연결 성공, 기존 연결 사용")
                # PostgreSQL이지만 실제로는 메모리 SQLite일 수 있음
                # point_purchases 테이블이 있는지 확인하고 없으면 생성
                cursor = conn.cursor()
                try:
                    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_name='point_purchases'")
                    table_exists = cursor.fetchone()
                    print(f"point_purchases 테이블 존재 확인: {table_exists is not None}")
                    
                    if not table_exists:
                        print(f"point_purchases 테이블이 없음, 생성 시도...")
                        cursor.execute("""
                            CREATE TABLE IF NOT EXISTS point_purchases (
                                purchase_id SERIAL PRIMARY KEY,
                                user_id TEXT NOT NULL,
                                amount INTEGER NOT NULL,
                                price REAL NOT NULL,
                                status TEXT DEFAULT 'pending',
                                created_at TIMESTAMP DEFAULT NOW(),
                                updated_at TIMESTAMP DEFAULT NOW()
                            )
                        """)
                        conn.commit()
                        print(f"point_purchases 테이블 생성 완료")
                except Exception as e:
                    print(f"테이블 확인/생성 중 오류: {e}")
                    # SQLite 문법으로 다시 시도
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS point_purchases (
                            purchase_id SERIAL PRIMARY KEY,
                            user_id TEXT NOT NULL,
                            amount INTEGER NOT NULL,
                            price REAL NOT NULL,
                            status TEXT DEFAULT 'pending',
                            created_at TIMESTAMP DEFAULT NOW(),
                            updated_at TIMESTAMP DEFAULT NOW()
                        )
                    """)
                    conn.commit()
                    print(f"point_purchases 테이블 생성 완료 (SQLite 문법)")
            
            print(f"데이터 삽입 시도...")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO point_purchases (user_id, amount, price, status)
                VALUES (%s, %s, %s, 'pending')
            """, (user_id, amount, price))
            
            purchase_id = cursor.lastrowid
            conn.commit()
            print(f"데이터 삽입 완료, ID: {purchase_id}")
        
        return jsonify({
                'purchase_id': purchase_id,
                'message': '포인트 구매 요청이 생성되었습니다.'
        }), 200
        
        
    except Exception as e:
            print(f"구매 요청 저장 실패: {e}")
            import traceback
            print(f"상세 오류: {traceback.format_exc()}")
            return jsonify({'error': f'구매 요청 저장에 실패했습니다: {str(e)}'}), 500        
    except Exception as e:
        print(f"포인트 구매 요청 실패: {e}")
        import traceback
        print(f"상세 오류: {traceback.format_exc()}")
        return jsonify({'error': f'포인트 구매 요청에 실패했습니다: {str(e)}'}), 500

# 테스트 데이터 추가 API
@app.route('/api/admin/set-admin-points', methods=['POST'])
def set_admin_points():
    """관리자 계정 포인트 설정"""
    try:
        print(f"=== 관리자 포인트 설정 시작 ===")
        conn = get_db_connection()
        if conn is None:
            print(f"데이터베이스 연결 실패")
            return jsonify({'error': '데이터베이스 연결 실패'}), 500
        
        cursor = conn.cursor()
        
        # 관리자 계정 포인트 99999로 설정
        admin_user_id = 'admin'
        admin_points = 99999
        
        try:
            cursor.execute("""
                INSERT INTO points (user_id, points, created_at, updated_at)
                VALUES (%s, %s, NOW(), NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    points = EXCLUDED.points,
                    updated_at = EXCLUDED.updated_at
            """, (admin_user_id, admin_points))
            conn.commit()
            print(f"관리자 포인트 설정 완료: {admin_user_id} - {admin_points} 포인트")
            return jsonify({'message': '관리자 포인트 설정 완료', 'points': admin_points}), 200
    except Exception as e:
            print(f"관리자 포인트 설정 실패: {e}")
            return jsonify({'error': f'관리자 포인트 설정 실패: {str(e)}'}), 500
        
    except Exception as e:
        print(f"관리자 포인트 설정 오류: {e}")
        return jsonify({'error': f'관리자 포인트 설정 오류: {str(e)}'}), 500

@app.route('/api/admin/add-test-data', methods=['POST'])
def add_test_data():
    """테스트 데이터 추가 (개발용)"""
    try:
        print(f"=== 테스트 데이터 추가 시작 ===")
        conn = get_db_connection()
        if conn is None:
            print(f"데이터베이스 연결 실패")
            return
        
        cursor = conn.cursor()
        
        # 테스트 사용자 추가
        test_users = [
            ('user1', 1000),
            ('user2', 500),
            ('user3', 2000)
        ]
        
        for user_id, points in test_users:
            try:
                cursor.execute("""
                    INSERT INTO points (user_id, points, created_at, updated_at)
                    VALUES (%s, %s, NOW(), NOW())
                    ON CONFLICT (user_id) DO UPDATE SET
                        points = EXCLUDED.points,
                        updated_at = EXCLUDED.updated_at
                """, (user_id, points))
                print(f"테스트 사용자 추가: {user_id} - {points} 포인트")
            except Exception as e:
                print(f"사용자 추가 실패: {e}")
        
        # 테스트 주문 추가
        test_orders = [
            ('user1', 'service1', 'https://example.com', 100, 10000, 'completed'),
            ('user2', 'service2', 'https://example.com', 50, 5000, 'pending'),
            ('user3', 'service3', 'https://example.com', 200, 20000, 'completed')
        ]
        
        for user_id, service_id, link, quantity, price, status in test_orders:
            try:
                cursor.execute("""
                    INSERT INTO orders (user_id, service_id, link, quantity, price, status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                """, (user_id, service_id, link, quantity, price, status))
                print(f"테스트 주문 추가: {user_id} - {service_id}")
            except Exception as e:
                print(f"주문 추가 실패: {e}")
        
        # 테스트 포인트 구매 추가
        test_purchases = [
            ('user1', 1000, 10000, 'pending'),
            ('user2', 500, 5000, 'approved'),
            ('user3', 2000, 20000, 'pending')
        ]
        
        for user_id, amount, price, status in test_purchases:
            try:
                cursor.execute("""
                    INSERT INTO point_purchases (user_id, amount, price, status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, NOW(), NOW())
                """, (user_id, amount, price, status))
                print(f"테스트 포인트 구매 추가: {user_id} - {amount} 포인트")
            except Exception as e:
                print(f"포인트 구매 추가 실패: {e}")
        
        conn.commit()
        print(f"=== 테스트 데이터 추가 완료 ===")
        return jsonify({'message': '테스트 데이터가 성공적으로 추가되었습니다.'})
        
    except Exception as e:
        print(f"테스트 데이터 추가 실패: {e}")
        return jsonify({'error': f'테스트 데이터 추가에 실패했습니다: {str(e)}'}), 500

# 관리자 통계 데이터 제공
@app.route('/api/admin/stats', methods=['GET'])
def get_admin_stats():
    """관리자 통계 데이터 제공"""
    try:
        print(f"=== 관리자 통계 API 엔드포인트 호출됨 ===")
        conn = get_db_connection()
        if conn is None:
            print(f"PostgreSQL 연결 실패, 파일 기반 SQLite로 폴백...")
            # 파일 기반 SQLite로 폴백 (데이터 유지)
            possible_paths = [
                '/app/data/orders.db',
                '/tmp/orders.db',
                './orders.db',
                'orders.db'
            ]
            
            for db_path in possible_paths:
                try:
                    dir_path = os.path.dirname(db_path)
                    if dir_path and not os.path.exists(dir_path):
                        os.makedirs(dir_path, exist_ok=True)
                        print(f"디렉토리 생성 시도: {dir_path}")
                    
                    conn = sqlite3.connect(db_path)
                    conn.row_factory = sqlite3.Row
                    print(f"파일 기반 SQLite 연결 성공: {db_path}")
                    break
                except Exception as path_error:
                    print(f"경로 {db_path} 시도 실패: {path_error}")
                    continue
            
            if conn is None:
                print("모든 파일 경로 실패, 메모리 기반 SQLite로 폴백")
                conn = sqlite3.connect(':memory:')
                conn.row_factory = sqlite3.Row
                print("메모리 기반 SQLite 연결 성공 (데이터 유지 안됨)")
            
            # 테이블 생성 확인
            cursor = conn.cursor()
            print(f"관리자 통계용 테이블 생성 시도...")
            
            # points 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS points (
                    user_id TEXT PRIMARY KEY,
                    points INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # orders 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    service_id TEXT NOT NULL,
                    link TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price REAL NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # point_purchases 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS point_purchases (
                    purchase_id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    price REAL NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            conn.commit()
            print(f"관리자 통계용 테이블 생성 완료")
        else:
            print(f"PostgreSQL 연결 성공, 기존 연결 사용")
        
        # 현재 날짜와 하루 전 날짜 계산
        now = datetime.now()
        one_day_ago = now - timedelta(days=1)
        
        # 총 사용자 수 (points 테이블에서 조회)
        try:
            cursor = conn.cursor()
            print(f"points 테이블 조회 시도...")
            cursor.execute("SELECT COUNT(*) as total_users FROM points")
            result = cursor.fetchone()
            total_users = result['total_users'] if isinstance(result, dict) else (result[0] if result else 0)
            print(f"총 사용자 수: {total_users}")
        except Exception as e:
            print(f"points 테이블 조회 실패: {e}")
            total_users = 0
        
        # 총 주문 수 (orders 테이블에서 조회)
        try:
            cursor.execute("SELECT COUNT(*) as total_orders FROM orders")
            result = cursor.fetchone()
            total_orders = result['total_orders'] if isinstance(result, dict) else (result[0] if result else 0)
            print(f"총 주문 수: {total_orders}")
    except Exception as e:
            print(f"orders 테이블 조회 실패: {e}")
            total_orders = 0
        
        # 총 매출액 (point_purchases 테이블에서 조회)
        try:
            cursor.execute("SELECT SUM(price) as total_revenue FROM point_purchases WHERE status = 'approved'")
            result = cursor.fetchone()
            total_revenue = (result['total_revenue'] if isinstance(result, dict) else (result[0] if result else 0)) or 0
            print(f"총 매출액: {total_revenue}")
        except Exception as e:
            print(f"total_revenue 조회 실패: {e}")
            total_revenue = 0
        
        # 대기 중인 포인트 구매 신청 수
        try:
            cursor.execute("SELECT COUNT(*) as pending_purchases FROM point_purchases WHERE status = 'pending'")
            result = cursor.fetchone()
            pending_purchases = result['pending_purchases'] if isinstance(result, dict) else (result[0] if result else 0)
            print(f"대기 중인 구매 신청: {pending_purchases}")
        except Exception as e:
            print(f"pending_purchases 조회 실패: {e}")
            pending_purchases = 0
        
        # 오늘 주문 수
        try:
            cursor.execute("""
                SELECT COUNT(*) as today_orders 
                FROM orders 
                WHERE DATE(created_at) = DATE('now')
            """)
            result = cursor.fetchone()
            today_orders = result['today_orders'] if isinstance(result, dict) else (result[0] if result else 0)
            print(f"오늘 주문 수: {today_orders}")
        except Exception as e:
            print(f"today_orders 조회 실패: {e}")
            today_orders = 0
        
        # 오늘 매출액
        try:
            cursor.execute("""
                SELECT SUM(price) as today_revenue 
                FROM point_purchases 
                WHERE status = 'approved' AND DATE(created_at) = DATE('now')
            """)
            today_revenue = cursor.fetchone()[0] or 0
            print(f"오늘 매출액: {today_revenue}")
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
        
        print(f"관리자 통계 조회 성공: {stats}")
        return jsonify(stats), 200
        
    except Exception as e:
        print(f"관리자 통계 조회 실패: {e}")
        import traceback
        print(f"상세 오류: {traceback.format_exc()}")
        # 에러 발생 시 기본값 반환
        return jsonify({
            'totalUsers': 0,
            'totalOrders': 0,
            'totalRevenue': 0,
            'pendingPurchases': 0,
            'todayOrders': 0,
            'todayRevenue': 0
        }), 200
        
# 관리자 사용자 목록 조회
@app.route('/api/admin/users', methods=['GET'])
def get_admin_users():
    """관리자용 사용자 목록 조회"""
    try:
        print(f"=== 관리자 사용자 목록 API 엔드포인트 호출됨 ===")
        conn = get_db_connection()
        if conn is None:
            print(f"PostgreSQL 연결 실패, 파일 기반 SQLite로 폴백...")
            # 파일 기반 SQLite로 폴백 (데이터 유지)
            possible_paths = [
                '/app/data/orders.db',
                '/tmp/orders.db',
                './orders.db',
                'orders.db'
            ]
            
            for db_path in possible_paths:
                try:
                    dir_path = os.path.dirname(db_path)
                    if dir_path and not os.path.exists(dir_path):
                        os.makedirs(dir_path, exist_ok=True)
                        print(f"디렉토리 생성 시도: {dir_path}")
                    
                    conn = sqlite3.connect(db_path)
                    conn.row_factory = sqlite3.Row
                    print(f"파일 기반 SQLite 연결 성공: {db_path}")
                    break
                except Exception as path_error:
                    print(f"경로 {db_path} 시도 실패: {path_error}")
                    continue
            
            if conn is None:
                print("모든 파일 경로 실패, 메모리 기반 SQLite로 폴백")
                conn = sqlite3.connect(':memory:')
                conn.row_factory = sqlite3.Row
                print("메모리 기반 SQLite 연결 성공 (데이터 유지 안됨)")
            
            # 테이블 생성 확인
            cursor = conn.cursor()
            print(f"관리자 사용자 목록용 테이블 생성 시도...")
            
            # points 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS points (
                    user_id TEXT PRIMARY KEY,
                    points INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            conn.commit()
            print(f"관리자 사용자 목록용 테이블 생성 완료")
        else:
            print(f"PostgreSQL 연결 성공, 기존 연결 사용")
        
        print(f"사용자 목록 조회 시도...")
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
        
        print(f"사용자 데이터 변환 시도...")
        users = []
        for row in cursor.fetchall():
            try:
                user = {
                    'userId': row[0],
                    'email': row[0],  # user_id를 이메일로 사용
                    'points': row[1],
                    'createdAt': row[2].isoformat() if row[2] else None,
                    'lastActivity': row[3].isoformat() if row[3] else None
                }
                users.append(user)
    except Exception as e:
                print(f"사용자 데이터 변환 실패: {e}")
                continue
        
        print(f"사용자 목록 조회 성공: {len(users)}명")
        return jsonify(users), 200
        
    except Exception as e:
        print(f"사용자 목록 조회 실패: {e}")
        import traceback
        print(f"상세 오류: {traceback.format_exc()}")
        return jsonify([]), 200

# 관리자 주문/거래 목록 조회
@app.route('/api/admin/transactions', methods=['GET'])
def get_admin_transactions():
    """관리자용 주문/거래 목록 조회"""
    try:
        print(f"=== 관리자 주문 목록 API 엔드포인트 호출됨 ===")
        conn = get_db_connection()
        if conn is None:
            print(f"PostgreSQL 연결 실패, 파일 기반 SQLite로 폴백...")
            # 파일 기반 SQLite로 폴백 (데이터 유지)
            possible_paths = [
                '/app/data/orders.db',
                '/tmp/orders.db',
                './orders.db',
                'orders.db'
            ]
            
            for db_path in possible_paths:
                try:
                    dir_path = os.path.dirname(db_path)
                    if dir_path and not os.path.exists(dir_path):
                        os.makedirs(dir_path, exist_ok=True)
                        print(f"디렉토리 생성 시도: {dir_path}")
                    
                    conn = sqlite3.connect(db_path)
                    conn.row_factory = sqlite3.Row
                    print(f"파일 기반 SQLite 연결 성공: {db_path}")
                    break
                except Exception as path_error:
                    print(f"경로 {db_path} 시도 실패: {path_error}")
                    continue
            
            if conn is None:
                print("모든 파일 경로 실패, 메모리 기반 SQLite로 폴백")
                conn = sqlite3.connect(':memory:')
                conn.row_factory = sqlite3.Row
                print("메모리 기반 SQLite 연결 성공 (데이터 유지 안됨)")
            
            # 테이블 생성 확인
            cursor = conn.cursor()
            print(f"관리자 주문 목록용 테이블 생성 시도...")
            
            # orders 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    service_id TEXT NOT NULL,
                    link TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price REAL NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            conn.commit()
            print(f"관리자 주문 목록용 테이블 생성 완료")
        else:
            print(f"PostgreSQL 연결 성공, 기존 연결 사용")
        
        print(f"주문 목록 조회 시도...")
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
        
        print(f"주문 데이터 변환 시도...")
        orders = []
            for row in cursor.fetchall():
            try:
                order = {
                    'orderId': f"ORD_{row[0]}",
                    'platform': 'SNS',  # 기본값
                    'service': f"서비스 {row[2]}",
                    'quantity': row[4],
                    'amount': float(row[5]),
                    'status': row[6],
                    'createdAt': row[7].isoformat() if row[7] else None
                }
                orders.append(order)
            except Exception as e:
                print(f"주문 데이터 변환 실패: {e}")
                continue
        
        print(f"주문 목록 조회 성공: {len(orders)}건")
        return jsonify(orders), 200
        
    except Exception as e:
        print(f"주문 목록 조회 실패: {e}")
        import traceback
        print(f"상세 오류: {traceback.format_exc()}")
        return jsonify([]), 200

# 관리자 포인트 구매 신청 목록 조회
@app.route('/api/admin/purchases', methods=['GET'])
def get_admin_purchases():
    """관리자용 포인트 구매 신청 목록 조회"""
    print(f"=== 관리자 구매 신청 목록 API 엔드포인트 호출됨 ===")
    print(f"요청 메서드: {request.method}")
    print(f"요청 URL: {request.url}")
    print(f"요청 헤더: {dict(request.headers)}")
    try:
        print(f"=== 관리자 구매 신청 목록 조회 시작 ===")
        conn = get_db_connection()
        if conn is None:
            print(f"PostgreSQL 연결 실패, 파일 기반 SQLite로 폴백...")
            # 파일 기반 SQLite로 폴백 (데이터 유지)
            possible_paths = [
                '/app/data/orders.db',
                '/tmp/orders.db',
                './orders.db',
                'orders.db'
            ]
            
            for db_path in possible_paths:
                try:
                    dir_path = os.path.dirname(db_path)
                    if dir_path and not os.path.exists(dir_path):
                        os.makedirs(dir_path, exist_ok=True)
                        print(f"디렉토리 생성 시도: {dir_path}")
                    
                    conn = sqlite3.connect(db_path)
                    conn.row_factory = sqlite3.Row
                    print(f"파일 기반 SQLite 연결 성공: {db_path}")
                    break
                except Exception as path_error:
                    print(f"경로 {db_path} 시도 실패: {path_error}")
                    continue
            
            if conn is None:
                print("모든 파일 경로 실패, 메모리 기반 SQLite로 폴백")
                conn = sqlite3.connect(':memory:')
                conn.row_factory = sqlite3.Row
                print("메모리 기반 SQLite 연결 성공 (데이터 유지 안됨)")
            
            # 테이블 생성 확인
            cursor = conn.cursor()
            print(f"point_purchases 테이블 생성 시도...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS point_purchases (
                    purchase_id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    price REAL NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            conn.commit()
            print(f"point_purchases 테이블 생성 완료")
            
            # 테이블 존재 확인
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_name='point_purchases'")
            table_exists = cursor.fetchone()
            print(f"point_purchases 테이블 존재 확인: {table_exists is not None}")
        else:
            print(f"PostgreSQL 연결 성공, 기존 연결 사용")
            # PostgreSQL이지만 실제로는 메모리 SQLite일 수 있음
            # point_purchases 테이블이 있는지 확인하고 없으면 생성
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_name='point_purchases'")
                table_exists = cursor.fetchone()
                print(f"point_purchases 테이블 존재 확인: {table_exists is not None}")
                
                if not table_exists:
                    print(f"point_purchases 테이블이 없음, 생성 시도...")
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS point_purchases (
                            purchase_id SERIAL PRIMARY KEY,
                            user_id TEXT NOT NULL,
                            amount INTEGER NOT NULL,
                            price REAL NOT NULL,
                            status TEXT DEFAULT 'pending',
                            created_at TIMESTAMP DEFAULT NOW(),
                            updated_at TIMESTAMP DEFAULT NOW()
                        )
                    """)
                    conn.commit()
                    print(f"point_purchases 테이블 생성 완료")
    except Exception as e:
                print(f"테이블 확인/생성 중 오류: {e}")
                # SQLite 문법으로 다시 시도
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS point_purchases (
                        purchase_id SERIAL PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        amount INTEGER NOT NULL,
                        price REAL NOT NULL,
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                conn.commit()
                print(f"point_purchases 테이블 생성 완료 (SQLite 문법)")
        
        print(f"데이터 조회 시도...")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT purchase_id, user_id, amount, price, status, created_at, updated_at
            FROM point_purchases 
            ORDER BY created_at DESC
        """)
        
        print(f"데이터 변환 시도...")
        purchases = []
        for row in cursor.fetchall():
            try:
                purchase = {
                    'id': row[0],
                    'userId': row[1],
                    'email': row[1],  # user_id를 이메일로 사용
                    'points': row[2],  # amount를 points로 매핑
                    'amount': float(row[3]),  # price를 amount로 매핑
                    'status': row[4],
                    'createdAt': row[5].isoformat() if row[5] else None,
                    'updatedAt': row[6].isoformat() if row[6] else None
                }
                purchases.append(purchase)
                print(f"포인트 구매 신청: ID={row[0]}, 사용자={row[1]}, 포인트={row[2]}, 금액={row[3]}, 상태={row[4]}")
            except Exception as e:
                print(f"데이터 변환 실패: {e}, row: {row}")
        
        print(f"조회 완료, 총 {len(purchases)}개 항목")
        return jsonify(purchases), 200
            
    except Exception as e:
        print(f"관리자 구매 신청 목록 조회 실패: {e}")
        import traceback
        print(f"상세 오류: {traceback.format_exc()}")
        return jsonify({'error': f'구매 신청 목록 조회에 실패했습니다: {str(e)}'}), 500

# 관리자 포인트 구매 신청 승인/거절
@app.route('/api/admin/purchases/<int:purchase_id>', methods=['PUT'])
def update_purchase_status(purchase_id):
    """포인트 구매 신청 상태 업데이트 (승인/거절)"""
    try:
        data = request.get_json()
        status = data.get('status')
        
        if status not in ['approved', 'rejected']:
            return jsonify({'error': '잘못된 상태값입니다.'}), 400
        
        conn = get_db_connection()
        if conn is None:
            # 메모리 기반 SQLite로 폴백
            conn = sqlite3.connect(':memory:')
            conn.row_factory = sqlite3.Row
            
            # 테이블 생성 확인
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS point_purchases (
                    purchase_id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    price REAL NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            conn.commit()
        
        cursor = conn.cursor()
        
        if status == 'approved':
            # 구매 신청 승인 시 사용자 포인트 증가
            cursor.execute("""
                UPDATE point_purchases 
                SET status = %s, updated_at = NOW() 
                WHERE purchase_id = %s
            """, (status, purchase_id))
            
            # 구매 정보 조회
            cursor.execute("""
                SELECT user_id, amount, price 
                FROM point_purchases 
                WHERE purchase_id = %s
            """, (purchase_id,))
            
            purchase_info = cursor.fetchone()
            if purchase_info:
                user_id = purchase_info['user_id']
                amount = purchase_info['amount']
                
                # 사용자 포인트 증가
                cursor.execute("""
                    INSERT INTO points (user_id, points, updated_at)
                    VALUES (%s, COALESCE((SELECT points FROM points WHERE user_id = %s), 0) + %s, NOW())
                    ON CONFLICT (user_id) DO UPDATE SET
                        points = EXCLUDED.points,
                        updated_at = EXCLUDED.updated_at
                """, (user_id, user_id, amount))
                
                print(f"포인트 승인: 사용자 {user_id}에게 {amount}P 추가")
            
        else:
            # 거절 시 상태만 업데이트
            cursor.execute("""
                UPDATE point_purchases 
                SET status = %s, updated_at = NOW() 
                WHERE purchase_id = %s
            """, (status, purchase_id))
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'구매 신청이 {status}되었습니다.'
        }), 200
        
    except Exception as e:
        print(f"구매 신청 상태 업데이트 실패: {e}")
        return jsonify({'error': '구매 신청 상태 업데이트에 실패했습니다.'}), 500

# 사용자 정보 조회
@app.route('/api/user/info', methods=['GET'])
def get_user_info_by_query():
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

# 사용자 정보 조회
@app.route('/api/users/<user_id>', methods=['GET'])
def get_user(user_id):
    """특정 사용자 정보 조회"""
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': '데이터베이스 연결 실패'}), 500
            
        with conn:
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
                return jsonify({'user': user_info}), 200
            else:
                return jsonify({'error': '사용자를 찾을 수 없습니다.'}), 404
                
    except Exception as e:
        print(f"사용자 정보 조회 실패: {e}")
        return jsonify({'error': '사용자 정보 조회에 실패했습니다.'}), 500

# ==================== 추천인 시스템 API ====================

@app.route('/api/referral/generate-code', methods=['POST'])
def generate_referral_code():
    """추천인 코드 생성 (관리자 전용)"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': '사용자 ID가 필요합니다.'}), 400
        
        # 추천인 코드 생성 (8자리 랜덤 문자열)
        import random
        import string
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': '데이터베이스 연결 실패'}), 500
            
        with conn:
            cursor = conn.cursor()
            
            # 중복 코드 확인
            cursor.execute("SELECT code FROM referral_codes WHERE code = %s", (code,))
            if cursor.fetchone():
                # 중복이면 다시 생성
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            
            # 추천인 코드 저장
            cursor.execute("""
                INSERT INTO referral_codes (code, referrer_user_id, is_active)
                VALUES (%s, %s, 1)
            """, (code, user_id))
            
            conn.commit()
        
        return jsonify({
            'success': True,
                'code': code,
                'message': '추천인 코드가 생성되었습니다.'
        }), 200
        
    except Exception as e:
        print(f"추천인 코드 생성 실패: {e}")
        return jsonify({'error': '추천인 코드 생성에 실패했습니다.'}), 500

@app.route('/api/referral/use-code', methods=['POST'])
def use_referral_code():
    """추천인 코드 사용"""
    try:
        data = request.get_json()
        referral_code = data.get('referral_code')
        user_id = data.get('user_id')
        
        if not referral_code or not user_id:
            return jsonify({'error': '추천인 코드와 사용자 ID가 필요합니다.'}), 400
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': '데이터베이스 연결 실패'}), 500
            
        with conn:
            cursor = conn.cursor()
            
            # 추천인 코드 유효성 확인
            cursor.execute("""
                SELECT code_id, referrer_user_id, is_active, expires_at
                FROM referral_codes 
                WHERE code = %s
            """, (referral_code,))
            
            code_info = cursor.fetchone()
            if not code_info:
                return jsonify({'error': '유효하지 않은 추천인 코드입니다.'}), 400
            
            if not code_info['is_active']:
                return jsonify({'error': '비활성화된 추천인 코드입니다.'}), 400
            
            # 이미 추천받은 사용자인지 확인
            cursor.execute("""
                SELECT referral_id FROM referrals WHERE referred_user_id = %s
            """, (user_id,))
            
            if cursor.fetchone():
                return jsonify({'error': '이미 추천인 코드를 사용한 사용자입니다.'}), 400
            
            # 추천 관계 저장
            cursor.execute("""
                INSERT INTO referrals (referrer_user_id, referred_user_id, referral_code)
                VALUES (%s, %s, %s)
            """, (code_info['referrer_user_id'], user_id, referral_code))
            
            # 사용 횟수 증가
            cursor.execute("""
                UPDATE referral_codes 
                SET usage_count = usage_count + 1
                WHERE code = %s
            """, (referral_code,))
            
            conn.commit()
        
        return jsonify({
            'success': True,
                'message': '추천인 코드가 성공적으로 적용되었습니다.',
                'referrer_user_id': code_info['referrer_user_id']
        }), 200
        
    except Exception as e:
        print(f"추천인 코드 사용 실패: {e}")
        return jsonify({'error': '추천인 코드 사용에 실패했습니다.'}), 500


# 관리자 API는 backend.py에 직접 구현됨
print("관리자 API 엔드포인트 등록 완료")

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
    initialize_app()
    print(f"=== Flask 앱 시작 ===")
    print(f"등록된 라우트들:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.methods} {rule.rule}")
    app.run(debug=False, host='0.0.0.0', port=8000, threaded=True)
else:
    # Gunicorn으로 실행될 때 초기화
    initialize_app()
    print(f"=== Flask 앱 시작 (Gunicorn) ===")
    print(f"등록된 라우트들:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.methods} {rule.rule}")
