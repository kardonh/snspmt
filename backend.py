import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta 
import requests
import tempfile
import sqlite3

# Flask 앱 초기화
app = Flask(__name__, static_folder='dist', static_url_path='')
CORS(app)

# 데이터베이스 연결 설정 (AWS Secrets Manager 우선, 환경 변수 폴백)
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:Snspmt2024!@snspmt-cluste.cluster-cvmiee0q0zhs.ap-northeast-2.rds.amazonaws.com:5432/snspmt')
SMMPANEL_API_KEY = os.environ.get('SMMPANEL_API_KEY', '5efae48d287931cf9bd80a1bc6fdfa6d')

# AWS Secrets Manager 시도 (선택사항)
try:
    from aws_secrets_manager import get_database_url, get_smmpanel_api_key
    aws_db_url = get_database_url()
    aws_api_key = get_smmpanel_api_key()
    if aws_db_url and aws_db_url != DATABASE_URL:
        DATABASE_URL = aws_db_url
        print("✅ AWS Secrets Manager에서 데이터베이스 URL 로드")
    if aws_api_key and aws_api_key != SMMPANEL_API_KEY:
        SMMPANEL_API_KEY = aws_api_key
        print("✅ AWS Secrets Manager에서 API 키 로드")
except ImportError as e:
    print(f"⚠️ AWS Secrets Manager 사용 불가: {e}")
except Exception as e:
    print(f"⚠️ AWS Secrets Manager 오류: {e}")

print(f"🔗 데이터베이스 URL: {DATABASE_URL[:50]}...")
print(f"🔑 API 키: {SMMPANEL_API_KEY[:20]}...")

def get_db_connection():
    """데이터베이스 연결을 가져옵니다."""
    try:
        print(f"🔗 데이터베이스 연결 시도: {DATABASE_URL[:50]}...")
        
        if DATABASE_URL.startswith('postgresql://'):
            # PostgreSQL 연결 설정 최적화
            conn = psycopg2.connect(
                DATABASE_URL,
                connect_timeout=30,
                keepalives_idle=600,
                keepalives_interval=30,
                keepalives_count=3
            )
            # 자동 커밋 비활성화 (트랜잭션 제어를 위해)
            conn.autocommit = False
            print("✅ PostgreSQL 연결 성공")
            return conn
        else:
            # SQLite fallback
            db_path = os.path.join(tempfile.gettempdir(), 'snspmt.db')
            conn = sqlite3.connect(db_path, timeout=30)
            conn.row_factory = sqlite3.Row  # 딕셔너리 형태로 결과 반환
            print("✅ SQLite 연결 성공")
            return conn
    except psycopg2.Error as e:
        print(f"❌ PostgreSQL 연결 실패: {e}")
        print(f"   데이터베이스 URL: {DATABASE_URL[:50]}...")
        raise e
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")
        # SQLite fallback
        try:
            print("🔄 SQLite 폴백 시도...")
            db_path = os.path.join(tempfile.gettempdir(), 'snspmt.db')
            conn = sqlite3.connect(db_path, timeout=30)
            conn.row_factory = sqlite3.Row
            print("✅ SQLite 폴백 연결 성공")
            return conn
        except Exception as fallback_error:
            print(f"❌ SQLite 폴백도 실패: {fallback_error}")
            raise fallback_error

def init_database():
    """데이터베이스 테이블을 초기화합니다."""
    try:
        print("🔧 데이터베이스 초기화 시작")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # PostgreSQL인지 SQLite인지 확인
        is_postgresql = DATABASE_URL.startswith('postgresql://')
        print(f"📊 데이터베이스 타입: {'PostgreSQL' if is_postgresql else 'SQLite'}")
        
        if is_postgresql:
            # PostgreSQL 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id VARCHAR(255) PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    display_name VARCHAR(255),
                    last_activity TIMESTAMP DEFAULT NOW(),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS points (
                    user_id VARCHAR(255) PRIMARY KEY,
                    points INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # 기존 테이블 삭제 후 재생성
            cursor.execute("DROP TABLE IF EXISTS referral_codes CASCADE")
            cursor.execute("""
                CREATE TABLE referral_codes (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(50) UNIQUE NOT NULL,
                    user_id VARCHAR(255),
                    user_email VARCHAR(255) UNIQUE,
                    name VARCHAR(255),
                    phone VARCHAR(255),
                    is_active BOOLEAN DEFAULT true,
                    usage_count INTEGER DEFAULT 0,
                    total_commission DECIMAL(10,2) DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # 기존 테이블 삭제 후 재생성
            cursor.execute("DROP TABLE IF EXISTS referrals CASCADE")
            cursor.execute("""
                CREATE TABLE referrals (
                    id SERIAL PRIMARY KEY,
                    referrer_email VARCHAR(255) NOT NULL,
                    referral_code VARCHAR(50) NOT NULL,
                    name VARCHAR(255),
                    phone VARCHAR(255),
                    status VARCHAR(50) DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # 기존 테이블 삭제 후 재생성
            cursor.execute("DROP TABLE IF EXISTS commissions CASCADE")
            cursor.execute("""
                CREATE TABLE commissions (
                    id SERIAL PRIMARY KEY,
                    referred_user VARCHAR(255) NOT NULL,
                    referrer_id VARCHAR(255) NOT NULL,
                    purchase_amount DECIMAL(10,2) NOT NULL,
                    commission_amount DECIMAL(10,2) NOT NULL,
                    commission_rate DECIMAL(5,4) NOT NULL,
                    payment_date TIMESTAMP DEFAULT NOW(),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    user_email VARCHAR(255),
                    service_id VARCHAR(255) NOT NULL,
                    platform VARCHAR(255),
                    service_name VARCHAR(255),
                    service_type VARCHAR(255),
                    service_platform VARCHAR(255),
                    service_quantity INTEGER,
                    service_link TEXT,
                    link TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price DECIMAL(10,2) NOT NULL,
                    total_price DECIMAL(10,2),
                    amount DECIMAL(10,2),
                    status VARCHAR(50) DEFAULT 'pending',
                    external_order_id VARCHAR(255),
                    remarks TEXT,
                    comments TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS point_purchases (
                    id SERIAL PRIMARY KEY,
                    purchase_id VARCHAR(255) UNIQUE,
                    user_id VARCHAR(255) NOT NULL,
                    user_email VARCHAR(255),
                    amount INTEGER NOT NULL,
                    price DECIMAL(10,2) NOT NULL,
                    status VARCHAR(50) DEFAULT 'pending',
                    depositor_name VARCHAR(255),
                    buyer_name VARCHAR(255),
                    bank_name VARCHAR(255),
                    bank_info TEXT,
                    receipt_type VARCHAR(50),
                    business_info TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
        else:
            # SQLite 테이블 생성
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS points (
                    user_id TEXT PRIMARY KEY,
                points INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                DROP TABLE IF EXISTS orders
            """)
            cursor.execute("""
                CREATE TABLE orders (
                    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    service_id TEXT NOT NULL,
                    link TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price REAL NOT NULL,
                    status TEXT DEFAULT 'pending_payment',
                    external_order_id TEXT,
                    platform TEXT,
                    service_name TEXT,
                    comments TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            cursor.execute("""
                DROP TABLE IF EXISTS point_purchases
            """)
            cursor.execute("""
                CREATE TABLE point_purchases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    price REAL NOT NULL,
                    status TEXT DEFAULT 'pending',
                    buyer_name TEXT,
                    bank_info TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
        
        conn.commit()
        print("✅ 데이터베이스 테이블 초기화 완료")
            
    except Exception as e:
        print(f"❌ 데이터베이스 초기화 실패: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

# 앱 시작 시 초기화
def initialize_app():
    """앱 시작 시 초기화"""
    try:
        print("🚀 SNS PMT 앱 시작 중...")
        init_database()
        print("✅ 앱 시작 완료")
    except Exception as e:
        print(f"⚠️ 앱 초기화 중 오류: {e}")

# 데이터베이스 연결 테스트
@app.route('/api/test/db', methods=['GET'])
def test_database_connection():
    """데이터베이스 연결 테스트"""
    try:
        print("🔍 데이터베이스 연결 테스트 시작")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            
            # 테이블 목록 조회
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            return jsonify({
                'status': 'success',
                'database': 'postgresql',
                'connection': 'ok',
                'test_result': result[0] if result else None,
                'tables': tables
            }), 200
        else:
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            conn.close()
            return jsonify({
                'status': 'success',
                'database': 'sqlite',
                'connection': 'ok',
                'test_result': result[0] if result else None
            }), 200
            
    except Exception as e:
        print(f"❌ 데이터베이스 연결 테스트 실패: {e}")
        return jsonify({
            'status': 'error',
            'database': 'unknown',
            'connection': 'failed',
            'error': str(e)
        }), 500

# 사용자 테이블 테스트
@app.route('/api/test/users', methods=['GET'])
def test_users_table():
    """사용자 테이블 테스트"""
    try:
        print("🔍 사용자 테이블 테스트 시작")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # users 테이블 존재 확인
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'users'
            );
        """)
        users_exists = cursor.fetchone()[0]
        
        if users_exists:
            # 테이블 구조 확인
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'users' AND table_schema = 'public'
                ORDER BY ordinal_position
            """)
            columns = cursor.fetchall()
            
            # 레코드 수 확인
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            
            conn.close()
            return jsonify({
                'status': 'success',
                'table_exists': True,
                'columns': [{'name': col[0], 'type': col[1], 'nullable': col[2]} for col in columns],
                'record_count': count
            }), 200
        else:
            conn.close()
            return jsonify({
                'status': 'error',
                'table_exists': False,
                'message': 'users 테이블이 존재하지 않습니다'
            }), 404
            
    except Exception as e:
        print(f"❌ 사용자 테이블 테스트 실패: {e}")
        import traceback
        print(f"❌ 상세 오류: {traceback.format_exc()}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

# 헬스 체크
@app.route('/health', methods=['GET'])
@app.route('/api/health', methods=['GET'])
def health_check():
    """헬스 체크 엔드포인트"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# 사용자 등록
@app.route('/api/register', methods=['POST'])
def register():
    """사용자 등록"""
    try:
        data = request.get_json()
        print(f"🔍 등록 요청 데이터: {data}")
        
        user_id = data.get('user_id')
        email = data.get('email')
        name = data.get('name')
        
        print(f"🔍 파싱된 데이터 - user_id: {user_id}, email: {email}, name: {name}")
        
        if not all([user_id, email, name]):
            print(f"❌ 필수 필드 누락 - user_id: {user_id}, email: {email}, name: {name}")
            return jsonify({'error': '필수 필드가 누락되었습니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 사용자 정보 저장
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                INSERT INTO users (user_id, email, name, created_at, updated_at)
                VALUES (%s, %s, %s, NOW(), NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    email = EXCLUDED.email,
                    name = EXCLUDED.name,
                    updated_at = NOW()
            """, (user_id, email, name))
            
            # 포인트 초기화
            cursor.execute("""
                INSERT INTO points (user_id, points, created_at, updated_at)
                VALUES (%s, 0, NOW(), NOW())
                ON CONFLICT (user_id) DO NOTHING
            """, (user_id,))
        else:
            cursor.execute("""
                INSERT OR REPLACE INTO users (user_id, email, name, created_at, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (user_id, email, name))
            
            cursor.execute("""
                INSERT OR IGNORE INTO points (user_id, points, created_at, updated_at)
                VALUES (?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (user_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '사용자 등록이 완료되었습니다.',
            'user_id': user_id
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'사용자 등록 실패: {str(e)}'}), 500

# 사용자 포인트 조회
@app.route('/api/points', methods=['GET'])
def get_user_points():
    """사용자 포인트 조회"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id가 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("SELECT points FROM points WHERE user_id = %s", (user_id,))
        else:
            cursor.execute("SELECT points FROM points WHERE user_id = ?", (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            points = result[0] if isinstance(result, tuple) else result['points']
        else:
            points = 0
        
        return jsonify({
            'user_id': user_id,
            'points': points
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'포인트 조회 실패: {str(e)}'}), 500

# 주문 생성
@app.route('/api/orders', methods=['POST'])
def create_order():
    """주문 생성"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        service_id = data.get('service_id')
        link = data.get('link')
        quantity = data.get('quantity')
        price = data.get('price')
        
        if not all([user_id, service_id, link, quantity, price]):
            return jsonify({'error': '필수 필드가 누락되었습니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                INSERT INTO orders (user_id, service_id, link, quantity, price, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, 'pending_payment', NOW(), NOW())
                RETURNING order_id
            """, (user_id, service_id, link, quantity, price))
        else:
            cursor.execute("""
                INSERT INTO orders (user_id, service_id, link, quantity, price, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'pending_payment', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (user_id, service_id, link, quantity, price))
            cursor.execute("SELECT last_insert_rowid()")
        
        order_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'order_id': order_id,
            'status': 'pending_payment',
            'message': '주문이 생성되었습니다.'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'주문 생성 실패: {str(e)}'}), 500

# 주문 목록 조회
@app.route('/api/orders', methods=['GET'])
def get_orders():
    """주문 목록 조회"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id가 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT order_id, service_id, link, quantity, price, status, created_at
                FROM orders WHERE user_id = %s
                ORDER BY created_at DESC
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT order_id, service_id, link, quantity, price, status, created_at
                FROM orders WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
        
        orders = cursor.fetchall()
        conn.close()
        
        order_list = []
        for order in orders:
            order_list.append({
                'order_id': order[0],
                'service_id': order[1],
                'link': order[2],
                'quantity': order[3],
                'price': float(order[4]),
                'status': order[5],
                'created_at': order[6].isoformat() if hasattr(order[6], 'isoformat') else str(order[6])
            })
        
        return jsonify({
            'orders': order_list
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'주문 목록 조회 실패: {str(e)}'}), 500

# 포인트 구매 신청
@app.route('/api/points/purchase', methods=['POST'])
def purchase_points():
    """포인트 구매 신청"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        amount = data.get('amount')
        price = data.get('price')
        buyer_name = data.get('buyer_name', '')
        bank_info = data.get('bank_info', '')
        
        if not all([user_id, amount, price]):
            return jsonify({'error': '필수 필드가 누락되었습니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                INSERT INTO point_purchases (user_id, amount, price, status, buyer_name, bank_info, created_at, updated_at)
                VALUES (%s, %s, %s, 'pending', %s, %s, NOW(), NOW())
                RETURNING id
            """, (user_id, amount, price, buyer_name, bank_info))
        else:
            cursor.execute("""
                INSERT INTO point_purchases (user_id, amount, price, status, buyer_name, bank_info, created_at, updated_at)
                VALUES (?, ?, ?, 'pending', ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (user_id, amount, price, buyer_name, bank_info))
            cursor.execute("SELECT last_insert_rowid()")
        
        purchase_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'purchase_id': purchase_id,
            'status': 'pending',
            'message': '포인트 구매 신청이 완료되었습니다.'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'포인트 구매 신청 실패: {str(e)}'}), 500

# 관리자 통계
@app.route('/api/admin/stats', methods=['GET'])
def get_admin_stats():
    """관리자 통계"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            # 총 사용자 수
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            # 총 주문 수
            cursor.execute("SELECT COUNT(*) FROM orders")
            total_orders = cursor.fetchone()[0]
            
            # 총 매출 (주문 + 포인트 구매)
            cursor.execute("""
                SELECT COALESCE(SUM(price), 0) FROM orders WHERE status = 'completed'
                UNION ALL
                SELECT COALESCE(SUM(price), 0) FROM point_purchases WHERE status = 'approved'
            """)
            order_revenue = cursor.fetchone()[0] if cursor.rowcount > 0 else 0
            cursor.execute("SELECT COALESCE(SUM(price), 0) FROM point_purchases WHERE status = 'approved'")
            purchase_revenue = cursor.fetchone()[0]
            total_revenue = order_revenue + purchase_revenue
            
            # 대기 중인 포인트 구매
            cursor.execute("SELECT COUNT(*) FROM point_purchases WHERE status = 'pending'")
            pending_purchases = cursor.fetchone()[0]
            
            # 오늘 주문 수
            cursor.execute("SELECT COUNT(*) FROM orders WHERE DATE(created_at) = CURRENT_DATE")
            today_orders = cursor.fetchone()[0]
            
            # 오늘 매출 (주문 + 포인트 구매)
            cursor.execute("SELECT COALESCE(SUM(price), 0) FROM orders WHERE DATE(created_at) = CURRENT_DATE AND status = 'completed'")
            today_order_revenue = cursor.fetchone()[0]
            cursor.execute("SELECT COALESCE(SUM(price), 0) FROM point_purchases WHERE DATE(created_at) = CURRENT_DATE AND status = 'approved'")
            today_purchase_revenue = cursor.fetchone()[0]
            today_revenue = today_order_revenue + today_purchase_revenue
        else:
            # SQLite 버전
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM orders")
            total_orders = cursor.fetchone()[0]
            
            # 총 매출 (주문 + 포인트 구매)
            cursor.execute("SELECT COALESCE(SUM(price), 0) FROM orders WHERE status = 'completed'")
            order_revenue = cursor.fetchone()[0]
            cursor.execute("SELECT COALESCE(SUM(price), 0) FROM point_purchases WHERE status = 'approved'")
            purchase_revenue = cursor.fetchone()[0]
            total_revenue = order_revenue + purchase_revenue
            
            cursor.execute("SELECT COUNT(*) FROM point_purchases WHERE status = 'pending'")
            pending_purchases = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM orders WHERE DATE(created_at) = DATE('now')")
            today_orders = cursor.fetchone()[0]
            
            # 오늘 매출 (주문 + 포인트 구매)
            cursor.execute("SELECT COALESCE(SUM(price), 0) FROM orders WHERE DATE(created_at) = DATE('now') AND status = 'completed'")
            today_order_revenue = cursor.fetchone()[0]
            cursor.execute("SELECT COALESCE(SUM(price), 0) FROM point_purchases WHERE DATE(created_at) = DATE('now') AND status = 'approved'")
            today_purchase_revenue = cursor.fetchone()[0]
            today_revenue = today_order_revenue + today_purchase_revenue
        
        conn.close()
        
        return jsonify({
            'total_users': total_users,
            'total_orders': total_orders,
            'total_revenue': float(total_revenue),
            'pending_purchases': pending_purchases,
            'today_orders': today_orders,
            'today_revenue': float(today_revenue)
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'통계 조회 실패: {str(e)}'}), 500

# 관리자 포인트 구매 목록
@app.route('/api/admin/purchases', methods=['GET'])
def get_admin_purchases():
    """관리자 포인트 구매 목록"""
    try:
        print("🔍 관리자 포인트 구매 목록 조회 시작")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            # 테이블 존재 여부 확인
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'point_purchases'
                );
            """)
            purchases_table_exists = cursor.fetchone()[0]
            
            print(f"📊 point_purchases 테이블 존재 여부: {purchases_table_exists}")
            
            if purchases_table_exists:
                cursor.execute("""
                    SELECT pp.id, pp.user_id, pp.amount, pp.price, pp.status, 
                           pp.buyer_name, pp.bank_info, pp.created_at
                    FROM point_purchases pp
                    ORDER BY pp.created_at DESC
                """)
            else:
                print("⚠️ point_purchases 테이블이 존재하지 않습니다. 빈 배열을 반환합니다.")
                purchases = []
                conn.close()
                return jsonify({'purchases': []}), 200
        else:
            cursor.execute("""
                SELECT pp.id, pp.user_id, pp.amount, pp.price, pp.status, pp.created_at,
                       pp.buyer_name, pp.bank_info, u.email
                FROM point_purchases pp
                LEFT JOIN users u ON pp.user_id = u.user_id
                ORDER BY pp.created_at DESC
            """)
        
        purchases = cursor.fetchall()
        conn.close()
        
        purchase_list = []
        for purchase in purchases:
            purchase_list.append({
                'id': purchase[0],
                'user_id': purchase[1],
                'amount': purchase[2],
                'price': float(purchase[3]),
                'status': purchase[4],
                'created_at': purchase[5].isoformat() if hasattr(purchase[5], 'isoformat') else str(purchase[5]),
                'buyer_name': purchase[6] if len(purchase) > 6 else 'N/A',
                'bank_info': purchase[7] if len(purchase) > 7 else 'N/A',
                'email': purchase[8] if len(purchase) > 8 else 'N/A'
            })
        
        return jsonify({
            'purchases': purchase_list
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'포인트 구매 목록 조회 실패: {str(e)}'}), 500

# 포인트 구매 승인/거절
@app.route('/api/admin/purchases/<int:purchase_id>', methods=['PUT'])
def update_purchase_status(purchase_id):
    """포인트 구매 승인/거절"""
    try:
        data = request.get_json()
        status = data.get('status')  # 'approved' 또는 'rejected'
        
        if status not in ['approved', 'rejected']:
            return jsonify({'error': '유효하지 않은 상태입니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 구매 신청 정보 조회
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT user_id, amount, status
                FROM point_purchases
                WHERE id = %s
            """, (purchase_id,))
        else:
            cursor.execute("""
                SELECT user_id, amount, status
                FROM point_purchases
                WHERE id = ?
            """, (purchase_id,))
        
        purchase = cursor.fetchone()
        
        if not purchase:
            return jsonify({'error': '구매 신청을 찾을 수 없습니다.'}), 404
        
        if purchase[2] != 'pending':
            return jsonify({'error': '이미 처리된 구매 신청입니다.'}), 400
        
        # 상태 업데이트
        if DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                UPDATE point_purchases
                SET status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (status, purchase_id))
        else:
            cursor.execute("""
                UPDATE point_purchases
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, purchase_id))
        
        # 승인된 경우 사용자 포인트 증가
        if status == 'approved':
            user_id = purchase[0]
            amount = purchase[1]
            
            # 사용자 포인트 조회
            if DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    SELECT points FROM points WHERE user_id = %s
                """, (user_id,))
            else:
                cursor.execute("""
                    SELECT points FROM points WHERE user_id = ?
                """, (user_id,))
            
            user_points = cursor.fetchone()
            current_points = user_points[0] if user_points else 0
            new_points = current_points + amount
            
            # 포인트 업데이트
            if DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    UPDATE points
                    SET points = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """, (new_points, user_id))
            else:
                cursor.execute("""
                    UPDATE points
                    SET points = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (new_points, user_id))
        
        conn.commit()
        
        return jsonify({
            'message': f'구매 신청이 {status}되었습니다.',
            'status': status
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'구매 신청 처리 실패: {str(e)}'}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 포인트 차감 (주문 결제용)
@app.route('/api/points/deduct', methods=['POST'])
def deduct_points():
    """포인트 차감 (주문 결제)"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        amount = data.get('amount')  # 차감할 포인트
        order_id = data.get('order_id')  # 주문 ID (선택사항)
        
        if not all([user_id, amount]):
            return jsonify({'error': '필수 필드가 누락되었습니다.'}), 400
        
        if amount <= 0:
            return jsonify({'error': '차감할 포인트는 0보다 커야 합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
            
        # 사용자 포인트 조회
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT points FROM points WHERE user_id = %s
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT points FROM points WHERE user_id = ?
            """, (user_id,))
        
        user_points = cursor.fetchone()
        
        if not user_points:
            return jsonify({'error': '사용자를 찾을 수 없습니다.'}), 404
        
        current_points = user_points[0]
        
        if current_points < amount:
            return jsonify({'error': '포인트가 부족합니다.'}), 400
        
        # 포인트 차감
        new_points = current_points - amount
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                UPDATE points
                SET points = %s, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
            """, (new_points, user_id))
        else:
            cursor.execute("""
                UPDATE points
                SET points = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (new_points, user_id))
        
        conn.commit()
        
        return jsonify({
            'message': '포인트가 성공적으로 차감되었습니다.',
            'remaining_points': new_points,
            'deducted_amount': amount
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'포인트 차감 실패: {str(e)}'}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 사용자 정보 조회
@app.route('/api/users/<user_id>', methods=['GET'])
def get_user(user_id):
    """사용자 정보 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT user_id, email, name, created_at
                FROM users WHERE user_id = %s
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT user_id, email, name, created_at
                FROM users WHERE user_id = ?
            """, (user_id,))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return jsonify({
                'user_id': user[0],
                'email': user[1],
                'name': user[2],
                'created_at': user[3].isoformat() if hasattr(user[3], 'isoformat') else str(user[3])
            }), 200
        else:
            return jsonify({'error': '사용자를 찾을 수 없습니다.'}), 404
        
    except Exception as e:
        return jsonify({'error': f'사용자 정보 조회 실패: {str(e)}'}), 500

# 추천인 코드 생성
@app.route('/api/referral/generate-code', methods=['POST'])
def generate_referral_code():
    """추천인 코드 생성"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'user_id가 필요합니다.'}), 400
        
        # 간단한 추천인 코드 생성 (사용자 ID + 타임스탬프)
        import time
        code = f"REF_{user_id}_{int(time.time())}"
        
        return jsonify({
            'code': code,
            'message': '추천인 코드가 생성되었습니다.'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'추천인 코드 생성 실패: {str(e)}'}), 500

# 추천인 코드 조회
@app.route('/api/referral/my-codes', methods=['GET'])
def get_my_codes():
    """내 추천인 코드 조회"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id가 필요합니다.'}), 400
        
        # 임시로 빈 배열 반환 (추천인 기능은 나중에 구현)
        return jsonify({
            'codes': []
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'추천인 코드 조회 실패: {str(e)}'}), 500

# 추천인 코드 사용
@app.route('/api/referral/use-code', methods=['POST'])
def use_referral_code():
    """추천인 코드 사용"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        code = data.get('code')
        
        if not user_id or not code:
            return jsonify({'error': 'user_id와 code가 필요합니다.'}), 400
        
        # 임시로 성공 응답 반환 (추천인 기능은 나중에 구현)
        return jsonify({
            'message': '추천인 코드가 적용되었습니다.',
            'code': code
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'추천인 코드 사용 실패: {str(e)}'}), 500

# 추천인 수수료 조회
@app.route('/api/referral/commissions', methods=['GET'])
def get_commissions():
    """추천인 수수료 조회"""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id가 필요합니다.'}), 400
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT id, referred_user, purchase_amount, commission_amount, 
                       commission_rate, payment_date
                FROM commissions 
                WHERE referrer_id = %s
                ORDER BY payment_date DESC
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT id, referred_user, purchase_amount, commission_amount, 
                       commission_rate, payment_date
                FROM commissions 
                WHERE referrer_id = ?
                ORDER BY payment_date DESC
            """, (user_id,))
        
        commissions = []
        for row in cursor.fetchall():
            # 날짜 형식 처리
            payment_date = row[5]
            if hasattr(payment_date, 'strftime'):
                payment_date = payment_date.strftime('%Y-%m-%d')
            elif hasattr(payment_date, 'isoformat'):
                payment_date = payment_date.isoformat()[:10]
            else:
                payment_date = str(payment_date)[:10]
            
            commissions.append({
                'id': row[0],
                'referredUser': row[1],
                'purchaseAmount': row[2],
                'commissionAmount': row[3],
                'commissionRate': f"{row[4] * 100}%" if row[4] else "0%",
                'paymentDate': payment_date
            })
        
        return jsonify({
            'commissions': commissions
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'수수료 조회 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 사용자용 추천인 통계 조회
@app.route('/api/referral/stats', methods=['GET'])
def get_referral_stats():
    """사용자용 추천인 통계 조회"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id가 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            # 총 추천인 수
            cursor.execute("""
                SELECT COUNT(*) FROM referrals 
                WHERE referrer_email = %s
            """, (f"{user_id}@example.com",))
            total_referrals = cursor.fetchone()[0] or 0
            
            # 활성 추천인 수
            cursor.execute("""
                SELECT COUNT(*) FROM referrals 
                WHERE referrer_email = %s AND status = 'active'
            """, (f"{user_id}@example.com",))
            active_referrals = cursor.fetchone()[0] or 0
            
            # 총 커미션
            cursor.execute("""
                SELECT COALESCE(SUM(commission_amount), 0) FROM commissions 
                WHERE referrer_id = %s
            """, (user_id,))
            total_commission = cursor.fetchone()[0] or 0
            
            # 이번 달 추천인 수
            cursor.execute("""
                SELECT COUNT(*) FROM referrals 
                WHERE referrer_email = %s 
                AND DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
            """, (f"{user_id}@example.com",))
            this_month_referrals = cursor.fetchone()[0] or 0
            
            # 이번 달 커미션
            cursor.execute("""
                SELECT COALESCE(SUM(commission_amount), 0) FROM commissions 
                WHERE referrer_id = %s 
                AND DATE_TRUNC('month', payment_date) = DATE_TRUNC('month', CURRENT_DATE)
            """, (user_id,))
            this_month_commission = cursor.fetchone()[0] or 0
        else:
            # SQLite 버전
            cursor.execute("""
                SELECT COUNT(*) FROM referrals 
                WHERE referrer_email = ?
            """, (f"{user_id}@example.com",))
            total_referrals = cursor.fetchone()[0] or 0
            
            cursor.execute("""
                SELECT COUNT(*) FROM referrals 
                WHERE referrer_email = ? AND status = 'active'
            """, (f"{user_id}@example.com",))
            active_referrals = cursor.fetchone()[0] or 0
            
            cursor.execute("""
                SELECT COALESCE(SUM(commission_amount), 0) FROM commissions 
                WHERE referrer_id = ?
            """, (user_id,))
            total_commission = cursor.fetchone()[0] or 0
            
            cursor.execute("""
                SELECT COUNT(*) FROM referrals 
                WHERE referrer_email = ? 
                AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
            """, (f"{user_id}@example.com",))
            this_month_referrals = cursor.fetchone()[0] or 0
            
            cursor.execute("""
                SELECT COALESCE(SUM(commission_amount), 0) FROM commissions 
                WHERE referrer_id = ? 
                AND strftime('%Y-%m', payment_date) = strftime('%Y-%m', 'now')
            """, (user_id,))
            this_month_commission = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return jsonify({
            'totalReferrals': total_referrals,
            'totalCommission': total_commission,
            'activeReferrals': active_referrals,
            'thisMonthReferrals': this_month_referrals,
            'thisMonthCommission': this_month_commission
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'통계 조회 실패: {str(e)}'}), 500

# 사용자용 추천인 목록 조회
@app.route('/api/referral/referrals', methods=['GET'])
def get_user_referrals():
    """사용자용 추천인 목록 조회"""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id가 필요합니다.'}), 400
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT id, referrer_email, referral_code, name, phone, created_at, status
                FROM referrals 
                WHERE referrer_email = %s
                ORDER BY created_at DESC
            """, (f"{user_id}@example.com",))
        else:
            cursor.execute("""
                SELECT id, referrer_email, referral_code, name, phone, created_at, status
                FROM referrals 
                WHERE referrer_email = ?
                ORDER BY created_at DESC
            """, (f"{user_id}@example.com",))
        
        referrals = []
        for row in cursor.fetchall():
            # 날짜 형식 처리
            join_date = row[5]
            if hasattr(join_date, 'strftime'):
                join_date = join_date.strftime('%Y-%m-%d')
            elif hasattr(join_date, 'isoformat'):
                join_date = join_date.isoformat()[:10]
            else:
                join_date = str(join_date)[:10]
            
            referrals.append({
                'id': row[0],
                'user': row[1],
                'joinDate': join_date,
                'status': row[6],
                'commission': 0  # 개별 커미션은 별도 계산 필요
            })
        
        return jsonify({
            'referrals': referrals
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'추천인 목록 조회 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 관리자용 추천인 등록
@app.route('/api/admin/referral/register', methods=['POST'])
def admin_register_referral():
    """관리자용 추천인 등록"""
    try:
        data = request.get_json()
        email = data.get('email')
        name = data.get('name')
        phone = data.get('phone')
        
        if not email:
            return jsonify({'error': '이메일은 필수입니다.'}), 400
        
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 추천인 코드 생성
            import uuid
            import time
            code = f"REF{str(uuid.uuid4())[:8].upper()}"
            
            if DATABASE_URL.startswith('postgresql://'):
                # PostgreSQL - 먼저 기존 코드가 있는지 확인
                cursor.execute("SELECT id FROM referral_codes WHERE user_email = %s", (email,))
                existing_code = cursor.fetchone()
                
                if existing_code:
                    # 기존 코드 업데이트
                    cursor.execute("""
                        UPDATE referral_codes 
                        SET code = %s, name = %s, phone = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE user_email = %s
                    """, (code, name, phone, email))
                else:
                    # 새 코드 생성
                    cursor.execute("""
                        INSERT INTO referral_codes (user_email, code, name, phone, created_at, is_active)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (email, code, name, phone, datetime.now(), True))
                
                # 추천인 등록
                cursor.execute("""
                    INSERT INTO referrals (referrer_email, referral_code, name, phone, created_at, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (email, code, name, phone, datetime.now(), 'active'))
            else:
                # SQLite
                cursor.execute("""
                    INSERT OR REPLACE INTO referral_codes (user_email, code, name, phone, created_at, is_active)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (email, code, name, phone, datetime.now(), True))
                
                cursor.execute("""
                    INSERT INTO referrals (referrer_email, referral_code, name, phone, created_at, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (email, code, name, phone, datetime.now(), 'active'))
            
            conn.commit()
            
        except Exception as db_error:
            if conn:
                conn.rollback()
            raise db_error
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        
        return jsonify({
            'id': str(uuid.uuid4()),
            'email': email,
            'referralCode': code,
            'name': name,
            'phone': phone,
            'message': '추천인 등록 성공'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'추천인 등록 실패: {str(e)}'}), 500

# 관리자용 추천인 목록 조회
@app.route('/api/admin/referral/list', methods=['GET'])
def admin_get_referrals():
    """관리자용 추천인 목록 조회"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT id, referrer_email, referral_code, name, phone, created_at, status
                FROM referrals 
                ORDER BY created_at DESC
            """)
        else:
            cursor.execute("""
                SELECT id, referrer_email, referral_code, name, phone, created_at, status
                FROM referrals 
                ORDER BY created_at DESC
            """)
        
        referrals = []
        for row in cursor.fetchall():
            # 날짜 형식 처리
            join_date = row[5]
            if hasattr(join_date, 'strftime'):
                join_date = join_date.strftime('%Y-%m-%d')
            elif hasattr(join_date, 'isoformat'):
                join_date = join_date.isoformat()[:10]
            else:
                join_date = str(join_date)[:10]
            
            referrals.append({
                'id': row[0],
                'email': row[1],
                'referralCode': row[2],
                'name': row[3],
                'phone': row[4],
                'joinDate': join_date,
                'status': row[6]
            })
        
        return jsonify({
            'referrals': referrals,
            'count': len(referrals)
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'추천인 목록 조회 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 관리자용 추천인 코드 목록 조회
@app.route('/api/admin/referral/codes', methods=['GET'])
def admin_get_referral_codes():
    """관리자용 추천인 코드 목록 조회"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT id, code, user_email, name, phone, created_at, is_active, 
                       COALESCE(usage_count, 0) as usage_count, 
                       COALESCE(total_commission, 0) as total_commission
                FROM referral_codes 
                ORDER BY created_at DESC
            """)
        else:
            cursor.execute("""
                SELECT id, code, user_email, name, phone, created_at, is_active, 
                       COALESCE(usage_count, 0) as usage_count, 
                       COALESCE(total_commission, 0) as total_commission
                FROM referral_codes 
                ORDER BY created_at DESC
            """)
        
        codes = []
        for row in cursor.fetchall():
            # 날짜 형식 처리
            created_at = row[5]
            if hasattr(created_at, 'isoformat'):
                created_at = created_at.isoformat()
            elif hasattr(created_at, 'strftime'):
                created_at = created_at.strftime('%Y-%m-%dT%H:%M:%S')
            else:
                created_at = str(created_at)
            
            codes.append({
                'id': row[0],
                'code': row[1],
                'email': row[2],
                'name': row[3],
                'phone': row[4],
                'createdAt': created_at,
                'isActive': row[6],
                'usage_count': row[7],
                'total_commission': row[8]
            })
        
        return jsonify({
            'codes': codes,
            'count': len(codes)
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'추천인 코드 목록 조회 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 관리자용 커미션 내역 조회
@app.route('/api/admin/referral/commissions', methods=['GET'])
def admin_get_commissions():
    """관리자용 커미션 내역 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT id, referred_user, purchase_amount, commission_amount, 
                       commission_rate, payment_date
                FROM commissions 
                ORDER BY payment_date DESC
            """)
        else:
            cursor.execute("""
                SELECT id, referred_user, purchase_amount, commission_amount, 
                       commission_rate, payment_date
                FROM commissions 
                ORDER BY payment_date DESC
            """)
        
        commissions = []
        for row in cursor.fetchall():
            commissions.append({
                'id': row[0],
                'referredUser': row[1],
                'purchaseAmount': row[2],
                'commissionAmount': row[3],
                'commissionRate': f"{row[4] * 100}%" if row[4] else "0%",
                'paymentDate': row[5].strftime('%Y-%m-%d') if hasattr(row[5], 'strftime') else row[5]
            })
        
        conn.close()
        return jsonify({
            'commissions': commissions,
            'count': len(commissions)
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'커미션 내역 조회 실패: {str(e)}'}), 500

# 포인트 구매 내역 조회
@app.route('/api/points/purchase-history', methods=['GET'])
def get_purchase_history():
    """포인트 구매 내역 조회"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id가 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT id, amount, price, status, created_at
                FROM point_purchases WHERE user_id = %s
                ORDER BY created_at DESC
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT id, amount, price, status, created_at
                FROM point_purchases WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
        
        purchases = cursor.fetchall()
        conn.close()
        
        purchase_list = []
        for purchase in purchases:
            purchase_list.append({
                'id': purchase[0],
                'amount': purchase[1],
                'price': float(purchase[2]),
                'status': purchase[3],
                'created_at': purchase[4].isoformat() if hasattr(purchase[4], 'isoformat') else str(purchase[4])
            })
        
        return jsonify({
            'purchases': purchase_list
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'구매 내역 조회 실패: {str(e)}'}), 500

# 관리자 사용자 목록
@app.route('/api/admin/users', methods=['GET'])
def get_admin_users():
    """관리자 사용자 목록"""
    try:
        print("🔍 관리자 사용자 목록 조회 시작")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 먼저 간단한 쿼리로 테스트
        print("📊 기본 연결 테스트 중...")
        cursor.execute("SELECT 1")
        test_result = cursor.fetchone()
        print(f"✅ 기본 쿼리 성공: {test_result}")
        
        # 테이블 목록 확인
        print("📊 테이블 목록 조회 중...")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📊 존재하는 테이블: {tables}")
        
        user_list = []
        
        if 'users' in tables:
            print("📊 users 테이블 발견, 데이터 조회 중...")
            try:
                # 간단한 쿼리부터 시작
                cursor.execute("SELECT COUNT(*) FROM users")
                user_count = cursor.fetchone()[0]
                print(f"📊 users 테이블 레코드 수: {user_count}")
                
                if user_count > 0:
                    # 기본 컬럼만 조회
                    cursor.execute("""
                        SELECT user_id, email, name, created_at
                        FROM users
                        ORDER BY created_at DESC
                        LIMIT 50
                    """)
                    users = cursor.fetchall()
                    
                    for user in users:
                        user_list.append({
                            'user_id': user[0] if user[0] else 'N/A',
                            'email': user[1] if user[1] else 'N/A',
                            'name': user[2] if user[2] else 'N/A',
                            'created_at': user[3].isoformat() if user[3] and hasattr(user[3], 'isoformat') else str(user[3]) if user[3] else 'N/A',
                            'points': 0,  # 기본값
                            'last_activity': 'N/A'  # 기본값
                        })
                else:
                    print("📊 users 테이블이 비어있습니다.")
                    
            except Exception as table_e:
                print(f"❌ users 테이블 조회 실패: {table_e}")
                # 테이블 구조 확인
                try:
                    cursor.execute("""
                        SELECT column_name, data_type
                        FROM information_schema.columns
                        WHERE table_name = 'users' AND table_schema = 'public'
                        ORDER BY ordinal_position
                    """)
                    columns = cursor.fetchall()
                    print(f"📊 users 테이블 컬럼: {columns}")
                except Exception as col_e:
                    print(f"❌ 컬럼 정보 조회 실패: {col_e}")
        else:
            print("⚠️ users 테이블이 존재하지 않습니다.")
        
        conn.close()
        print(f"✅ 사용자 목록 반환: {len(user_list)}명")
        
        return jsonify({
            'users': user_list,
            'debug_info': {
                'tables': tables,
                'user_count': len(user_list)
            }
        }), 200
        
    except Exception as e:
        print(f"❌ 사용자 목록 조회 실패: {str(e)}")
        import traceback
        print(f"❌ 상세 오류: {traceback.format_exc()}")
        
        return jsonify({
            'error': f'사용자 목록 조회 실패: {str(e)}',
            'details': str(e),
            'traceback': traceback.format_exc()
        }), 500

# 관리자 거래 내역
@app.route('/api/admin/transactions', methods=['GET'])
def get_admin_transactions():
    """관리자 거래 내역"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT o.order_id, o.user_id, o.service_id, o.price, o.status, o.created_at,
                       o.platform, o.service_name, o.quantity, o.link, o.comments
                FROM orders o
                ORDER BY o.created_at DESC
            """)
        else:
            cursor.execute("""
                SELECT o.order_id, o.user_id, o.service_id, o.price, o.status, o.created_at,
                       o.platform, o.service_name, o.quantity, o.link, o.comments
                FROM orders o
                ORDER BY o.created_at DESC
            """)
        
        transactions = cursor.fetchall()
        conn.close()
        
        transaction_list = []
        for transaction in transactions:
            transaction_list.append({
                'order_id': transaction[0],
                'user_id': transaction[1],
                'service_id': transaction[2],
                'price': float(transaction[3]),
                'status': transaction[4],
                'created_at': transaction[5].isoformat() if hasattr(transaction[5], 'isoformat') else str(transaction[5]),
                'platform': transaction[6] if len(transaction) > 6 else 'N/A',
                'service_name': transaction[7] if len(transaction) > 7 else 'N/A',
                'quantity': transaction[8] if len(transaction) > 8 else 0,
                'link': transaction[9] if len(transaction) > 9 else 'N/A',
                'comments': transaction[10] if len(transaction) > 10 else 'N/A'
            })
        
        return jsonify({
            'transactions': transaction_list
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'거래 내역 조회 실패: {str(e)}'}), 500

# 관리자 페이지 라우트
@app.route('/admin')
def serve_admin():
    """관리자 페이지 서빙"""
    try:
        return app.send_static_file('index.html')
    except:
        return "Admin page not found", 404

# 정적 파일 서빙
@app.route('/<path:filename>')
def serve_static(filename):
    """정적 파일 서빙"""
    try:
        return app.send_static_file(filename)
    except:
        return "File not found", 404

@app.route('/')
def serve_index():
    """메인 페이지 서빙"""
    try:
        return app.send_static_file('index.html')
    except:
        # index.html이 없으면 기본 HTML 반환
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>SNS PMT</title>
            <meta charset="utf-8">
        </head>
        <body>
            <h1>SNS PMT 서비스</h1>
            <p>서비스가 정상적으로 실행되고 있습니다.</p>
            <p>API 엔드포인트:</p>
            <ul>
                <li>GET /api/health - 헬스 체크</li>
                <li>POST /api/register - 사용자 등록</li>
                <li>GET /api/points - 포인트 조회</li>
                <li>POST /api/orders - 주문 생성</li>
                <li>GET /api/orders - 주문 목록</li>
                <li>POST /api/points/purchase - 포인트 구매 신청</li>
                <li>GET /api/admin/stats - 관리자 통계</li>
                <li>GET /api/admin/purchases - 관리자 포인트 구매 목록</li>
            </ul>
        </body>
        </html>
        """, 200

# SMM Panel API 테스트 엔드포인트
@app.route('/api/smm-panel/test', methods=['GET'])
def smm_panel_test():
    """SMM Panel API 연결 테스트"""
    try:
        import requests
        
        # 간단한 테스트 요청
        test_data = {
            'action': 'balance',
            'key': '35246b890345d819e1110d5cea9d5565'
        }
        
        smm_panel_url = 'https://smmpanel.kr/api/v2'
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.post(smm_panel_url, json=test_data, headers=headers, timeout=10)
        
        return jsonify({
            'success': True,
            'status_code': response.status_code,
            'response': response.text[:500],
            'url': smm_panel_url
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# SMM Panel API 프록시 엔드포인트
@app.route('/api/smm-panel', methods=['POST'])
def smm_panel_proxy():
    """SMM Panel API 프록시 - CORS 문제 해결"""
    try:
        import requests
        
        data = request.get_json()
        print(f"🔍 SMM Panel 프록시 요청: {data}")
        
        # SMM Panel API 호출
        smm_panel_url = 'https://smmpanel.kr/api/v2'
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.post(smm_panel_url, json=data, headers=headers, timeout=30)
        
        print(f"✅ SMM Panel API 응답: {response.status_code}")
        print(f"📄 SMM Panel API 응답 내용: {response.text[:500]}...")
        
        # 응답 데이터 파싱
        try:
            response_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        except:
            response_data = response.text
        
        return jsonify({
            'success': True,
            'data': response_data,
            'status_code': response.status_code,
            'raw_response': response.text
        })
        
    except requests.exceptions.RequestException as e:
        print(f"❌ SMM Panel API 요청 실패: {e}")
        return jsonify({
            'success': False,
            'error': f'API 요청 실패: {str(e)}'
        }), 500
    except Exception as e:
        print(f"❌ SMM Panel 프록시 오류: {e}")
        return jsonify({
            'success': False,
            'error': f'프록시 오류: {str(e)}'
        }), 500

# 앱 시작 시 자동 초기화
initialize_app()

if __name__ == '__main__':
    # 개발 서버 실행
    app.run(host='0.0.0.0', port=8000, debug=False)