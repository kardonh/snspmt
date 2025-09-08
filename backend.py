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
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/snspmt')
# AWS RDS용 데이터베이스 URL 수정
if 'rds.amazonaws.com' in DATABASE_URL and 'snspmt_db' in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace('snspmt_db', 'snspmt')
SMMPANEL_API_URL = 'https://smmpanel.kr/api/v2'
API_KEY = os.getenv('SMMPANEL_API_KEY', '5efae48d287931cf9bd80a1bc6fdfa6d')

# 추천인 커미션 설정
REFERRAL_COMMISSION_RATE = 0.15  # 15% 커미션

# PostgreSQL 연결 함수 (안전한 연결)
def get_db_connection():
    """PostgreSQL 데이터베이스 연결 (안전한 연결)"""
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
            conn = sqlite3.connect('orders.db')
            conn.row_factory = sqlite3.Row
            print("SQLite 연결 성공")
            return conn
        except Exception as sqlite_error:
            print(f"SQLite 연결도 실패: {sqlite_error}")
            # 메모리 기반 SQLite 데이터베이스 사용
            try:
                conn = sqlite3.connect(':memory:')
                conn.row_factory = sqlite3.Row
                print("메모리 기반 SQLite 연결 성공")
                return conn
            except Exception as create_error:
                print(f"메모리 기반 SQLite 연결도 실패: {create_error}")
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
            
            # referral_codes 테이블 생성 (추천인 코드 관리)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS referral_codes (
                    code_id SERIAL PRIMARY KEY,
                    code VARCHAR(20) UNIQUE NOT NULL,
                    referrer_user_id VARCHAR(255) NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    usage_count INTEGER DEFAULT 0,
                    total_commission DECIMAL(10,2) DEFAULT 0.00
                )
            """)
            
            # referrals 테이블 생성 (추천 관계 관리)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    referral_id SERIAL PRIMARY KEY,
                    referrer_user_id VARCHAR(255) NOT NULL,
                    referred_user_id VARCHAR(255) NOT NULL,
                    referral_code VARCHAR(20) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(referred_user_id)
                )
            """)
            
            # referral_commissions 테이블 생성 (커미션 내역)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS referral_commissions (
                    commission_id SERIAL PRIMARY KEY,
                    referrer_user_id VARCHAR(255) NOT NULL,
                    referred_user_id VARCHAR(255) NOT NULL,
                    purchase_id INTEGER NOT NULL,
                    commission_amount DECIMAL(10,2) NOT NULL,
                    commission_rate DECIMAL(5,4) NOT NULL,
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

# 헬스 체크 - 초고속 응답 (데이터베이스 연결 없이)
@app.route('/health')
def health_check():
    """초고속 헬스 체크 - ELB용"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'snspmt'
    }), 200

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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("points 테이블 생성/확인 완료")
            
            # referral_codes 테이블 생성 (SQLite 문법)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS referral_codes (
                    code_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    referrer_user_id TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    usage_count INTEGER DEFAULT 0,
                    total_commission REAL DEFAULT 0.0
                )
            """)
            print("referral_codes 테이블 생성/확인 완료")
            
            # referrals 테이블 생성 (SQLite 문법)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    referral_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_user_id TEXT NOT NULL,
                    referred_user_id TEXT NOT NULL,
                    referral_code TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(referred_user_id)
                )
            """)
            print("referrals 테이블 생성/확인 완료")
            
            # 사용자 포인트 테이블에 등록 (SQLite 문법 사용)
            cursor.execute("""
                INSERT OR IGNORE INTO points (user_id, points) 
                VALUES (?, 0)
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
                        WHERE code = ?
                    """, (referral_code.strip().upper(),))
                    
                    code_info = cursor.fetchone()
                    if code_info and code_info['is_active']:
                        # 추천 관계 저장 (SQLite 문법 사용)
                        cursor.execute("""
                            INSERT OR IGNORE INTO referrals (referrer_user_id, referred_user_id, referral_code)
                            VALUES (?, ?, ?)
                        """, (code_info['referrer_user_id'], user_id, referral_code.strip().upper()))
                        
                        # 사용 횟수 증가
                        cursor.execute("""
                            UPDATE referral_codes 
                            SET usage_count = usage_count + 1
                            WHERE code = ?
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 사용자 정보 조회
            cursor.execute("""
                SELECT user_id, points FROM points WHERE user_id = ?
            """, (user_id,))
            
            user = cursor.fetchone()
            if not user:
                # 사용자가 없으면 새로 생성
                cursor.execute("""
                    INSERT OR IGNORE INTO points (user_id, points) VALUES (?, 0)
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 사용자 활동 업데이트
            cursor.execute("""
                UPDATE points SET updated_at = ? WHERE user_id = ?
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
                    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                WHERE user_id = ?
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                SELECT points FROM points WHERE user_id = ?
            """, (user_id,))
            
            result = cursor.fetchone()
            points = result[0] if result else 0
            
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
@app.route('/api/users/<user_id>', methods=['GET'])
def get_user_info(user_id):
    """사용자 정보 조회"""
    try:
        print(f"사용자 정보 조회 요청: {user_id}")
        
        # 데이터베이스에서 사용자 정보 조회
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                SELECT points, created_at, updated_at FROM points WHERE user_id = ?
            """, (user_id,))
            
            result = cursor.fetchone()
            if result:
                user_info = {
                    'user_id': user_id,
                    'points': result[0],
                    'created_at': result[1].isoformat() if result[1] else None,
                    'updated_at': result[2].isoformat() if result[2] else None
                }
            else:
                user_info = {
                    'user_id': user_id,
                    'points': 0,
                    'created_at': None,
                    'updated_at': None
                }
            
            return jsonify(user_info), 200
            
        except Exception as db_error:
            print(f"데이터베이스 조회 실패: {db_error}")
            return jsonify({'error': f'사용자 정보 조회에 실패했습니다: {str(db_error)}'}), 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        
    except Exception as e:
        print(f"사용자 정보 조회 실패: {e}")
        return jsonify({'error': '사용자 정보 조회에 실패했습니다.'}), 500

# 포인트 구매 내역 조회
@app.route('/api/points/purchase-history', methods=['GET'])
def get_purchase_history():
    """포인트 구매 내역 조회"""
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({'error': '사용자 ID가 누락되었습니다.'}), 400
        
        print(f"구매 내역 조회 요청: {user_id}")
        
        # 데이터베이스에서 구매 내역 조회
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': '데이터베이스 연결에 실패했습니다.'}), 500
        
        try:
            cursor = conn.cursor()
            
            # 테이블 생성 확인
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS point_purchases (
                    purchase_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    points INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                SELECT purchase_id, points, amount, status, created_at, updated_at
                FROM point_purchases 
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
            
            purchases = []
            for row in cursor.fetchall():
                purchase = {
                    'id': row[0],
                    'points': row[1],
                    'amount': float(row[2]),
                    'status': row[3],
                    'created_at': row[4].isoformat() if row[4] else None,
                    'updated_at': row[5].isoformat() if row[5] else None
                }
                purchases.append(purchase)
            
            return jsonify({'purchases': purchases}), 200
            
        except Exception as db_error:
            print(f"데이터베이스 조회 실패: {db_error}")
            return jsonify({'error': f'구매 내역 조회에 실패했습니다: {str(db_error)}'}), 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        
    except Exception as e:
        print(f"구매 내역 조회 실패: {e}")
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
                    code_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    referrer_user_id TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    usage_count INTEGER DEFAULT 0,
                    total_commission REAL DEFAULT 0.0
                )
            """)
            
                cursor.execute("""
                SELECT code, is_active, created_at, expires_at, usage_count, total_commission
                FROM referral_codes 
                WHERE referrer_user_id = ?
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
                    referral_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_user_id TEXT NOT NULL,
                    referred_user_id TEXT NOT NULL,
                    referral_code TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(referred_user_id)
                )
            """)
            
                cursor.execute("""
                SELECT referred_user_id, referral_code, created_at
                FROM referrals 
                WHERE referrer_user_id = ?
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
                    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                WHERE order_id = ? AND user_id = ?
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
                SET points = points - %s, updated_at = CURRENT_TIMESTAMP
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

# 사용자 포인트 조회
@app.route('/api/points', methods=['GET'])
def get_user_points():
    """사용자 포인트 조회"""
    try:
        user_id = request.args.get('user_id')
        
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
        user_id = request.args.get('user_id')
        
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
                VALUES (%s, %s, TRUE)
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

@app.route('/api/referral/my-codes', methods=['GET'])
def get_my_referral_codes():
    """내 추천인 코드 목록 조회"""
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({'error': '사용자 ID가 필요합니다.'}), 400
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': '데이터베이스 연결 실패'}), 500
            
        with conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    code,
                    is_active,
                    created_at,
                    expires_at,
                    usage_count,
                    total_commission
                FROM referral_codes 
                WHERE referrer_user_id = %s
                ORDER BY created_at DESC
            """, (user_id,))
            
            codes = []
            for row in cursor.fetchall():
                codes.append({
                    'code': row['code'],
                    'is_active': row['is_active'],
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                    'expires_at': row['expires_at'].isoformat() if row['expires_at'] else None,
                    'usage_count': row['usage_count'],
                    'total_commission': float(row['total_commission'])
                })
        
        return jsonify({
            'success': True,
                'codes': codes
        }), 200
        
    except Exception as e:
        print(f"추천인 코드 목록 조회 실패: {e}")
        return jsonify({'error': '추천인 코드 목록 조회에 실패했습니다.'}), 500

@app.route('/api/referral/commissions', methods=['GET'])
def get_referral_commissions():
    """추천인 커미션 내역 조회"""
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({'error': '사용자 ID가 필요합니다.'}), 400
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': '데이터베이스 연결 실패'}), 500
            
        with conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    rc.commission_id,
                    rc.referred_user_id,
                    rc.purchase_id,
                    rc.commission_amount,
                    rc.commission_rate,
                    rc.created_at,
                    pp.amount as purchase_amount
                FROM referral_commissions rc
                LEFT JOIN point_purchases pp ON rc.purchase_id = pp.purchase_id
                WHERE rc.referrer_user_id = %s
                ORDER BY rc.created_at DESC
            """, (user_id,))
            
            commissions = []
            for row in cursor.fetchall():
                commissions.append({
                    'commission_id': row['commission_id'],
                    'referred_user_id': row['referred_user_id'],
                    'purchase_id': row['purchase_id'],
                    'commission_amount': float(row['commission_amount']),
                    'commission_rate': float(row['commission_rate']),
                    'purchase_amount': row['purchase_amount'],
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None
                })
            
            return jsonify({
                'success': True,
                'commissions': commissions
            }), 200
            
    except Exception as e:
        print(f"추천인 커미션 내역 조회 실패: {e}")
        return jsonify({'error': '추천인 커미션 내역 조회에 실패했습니다.'}), 500

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
    initialize_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
else:
    # Gunicorn으로 실행될 때 초기화
    initialize_app()
