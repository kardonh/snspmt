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

# 데이터베이스 연결 설정
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:Snspmt2024!@snspmt-cluste.cluster-cvmiee0q0zhs.ap-northeast-2.rds.amazonaws.com:5432/snspmt')

def get_db_connection():
    """데이터베이스 연결을 가져옵니다."""
    try:
        if DATABASE_URL.startswith('postgresql://'):
            conn = psycopg2.connect(DATABASE_URL)
            return conn
        else:
            # SQLite fallback
            db_path = os.path.join(tempfile.gettempdir(), 'snspmt.db')
            conn = sqlite3.connect(db_path)
            return conn
    except Exception as e:
        print(f"데이터베이스 연결 실패: {e}")
        # SQLite fallback
        db_path = os.path.join(tempfile.gettempdir(), 'snspmt.db')
        conn = sqlite3.connect(db_path)
        return conn

def init_database():
    """데이터베이스 테이블을 초기화합니다."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # PostgreSQL인지 SQLite인지 확인
        is_postgresql = DATABASE_URL.startswith('postgresql://')
        
        if is_postgresql:
            # PostgreSQL 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id VARCHAR(255) PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    name VARCHAR(255) NOT NULL,
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
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                    order_id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    service_id VARCHAR(255) NOT NULL,
                    link TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price DECIMAL(10,2) NOT NULL,
                    status VARCHAR(50) DEFAULT 'pending_payment',
                    external_order_id VARCHAR(255),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            cursor.execute("""
                DROP TABLE IF EXISTS point_purchases
            """)
            cursor.execute("""
                CREATE TABLE point_purchases (
                id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    amount INTEGER NOT NULL,
                    price DECIMAL(10,2) NOT NULL,
                    status VARCHAR(50) DEFAULT 'pending',
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
                CREATE TABLE IF NOT EXISTS orders (
                    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    service_id TEXT NOT NULL,
                    link TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price REAL NOT NULL,
                    status TEXT DEFAULT 'pending_payment',
                    external_order_id TEXT,
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
        
        if not all([user_id, amount, price]):
            return jsonify({'error': '필수 필드가 누락되었습니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                INSERT INTO point_purchases (user_id, amount, price, status, created_at, updated_at)
                VALUES (%s, %s, %s, 'pending', NOW(), NOW())
                RETURNING id
            """, (user_id, amount, price))
        else:
            cursor.execute("""
                INSERT INTO point_purchases (user_id, amount, price, status, created_at, updated_at)
                VALUES (?, ?, ?, 'pending', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (user_id, amount, price))
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
            
            # 총 매출
            cursor.execute("SELECT COALESCE(SUM(price), 0) FROM orders WHERE status = 'completed'")
            total_revenue = cursor.fetchone()[0]
            
            # 대기 중인 포인트 구매
            cursor.execute("SELECT COUNT(*) FROM point_purchases WHERE status = 'pending'")
            pending_purchases = cursor.fetchone()[0]
            
            # 오늘 주문 수
            cursor.execute("SELECT COUNT(*) FROM orders WHERE DATE(created_at) = CURRENT_DATE")
            today_orders = cursor.fetchone()[0]
        else:
            # SQLite 버전
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM orders")
            total_orders = cursor.fetchone()[0]
            
            cursor.execute("SELECT COALESCE(SUM(price), 0) FROM orders WHERE status = 'completed'")
            total_revenue = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM point_purchases WHERE status = 'pending'")
            pending_purchases = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM orders WHERE DATE(created_at) = DATE('now')")
            today_orders = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'total_users': total_users,
            'total_orders': total_orders,
            'total_revenue': float(total_revenue),
            'pending_purchases': pending_purchases,
            'today_orders': today_orders
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'통계 조회 실패: {str(e)}'}), 500

# 관리자 포인트 구매 목록
@app.route('/api/admin/purchases', methods=['GET'])
def get_admin_purchases():
    """관리자 포인트 구매 목록"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT id, user_id, amount, price, status, created_at
                FROM point_purchases
                ORDER BY created_at DESC
            """)
        else:
            cursor.execute("""
                SELECT id, user_id, amount, price, status, created_at
                FROM point_purchases
                ORDER BY created_at DESC
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
                'created_at': purchase[5].isoformat() if hasattr(purchase[5], 'isoformat') else str(purchase[5])
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
        if conn:
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
        
        # 포인트 사용 내역 기록은 현재 비활성화 (테이블이 없음)
        # TODO: point_transactions 테이블 생성 후 활성화
        # if order_id:
        #     if DATABASE_URL.startswith('postgresql://'):
        #         cursor.execute("""
        #             INSERT INTO point_transactions (user_id, order_id, amount, type, created_at)
        #             VALUES (%s, %s, %s, 'deduct', CURRENT_TIMESTAMP)
        #         """, (user_id, order_id, amount))
        #     else:
        #         cursor.execute("""
        #             INSERT INTO point_transactions (user_id, order_id, amount, type, created_at)
        #             VALUES (?, ?, ?, 'deduct', CURRENT_TIMESTAMP)
        #         """, (user_id, order_id, amount))
        
        conn.commit()
        
        return jsonify({
            'message': '포인트가 성공적으로 차감되었습니다.',
            'remaining_points': new_points,
            'deducted_amount': amount
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'포인트 차감 실패: {str(e)}'}), 500
    finally:
        if conn:
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
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id가 필요합니다.'}), 400
        
        # 임시로 빈 배열 반환 (추천인 기능은 나중에 구현)
        return jsonify({
            'commissions': []
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'수수료 조회 실패: {str(e)}'}), 500

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
        conn = get_db_connection()
            cursor = conn.cursor()
            
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT user_id, email, name, created_at
                FROM users
                ORDER BY created_at DESC
            """)
        else:
            cursor.execute("""
                SELECT user_id, email, name, created_at
                FROM users 
                ORDER BY created_at DESC 
            """)
        
        users = cursor.fetchall()
        conn.close()
        
        user_list = []
        for user in users:
            user_list.append({
                'user_id': user[0],
                'email': user[1],
                'name': user[2],
                'created_at': user[3].isoformat() if hasattr(user[3], 'isoformat') else str(user[3])
            })
        
        return jsonify({
            'users': user_list
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'사용자 목록 조회 실패: {str(e)}'}), 500

# 관리자 거래 내역
@app.route('/api/admin/transactions', methods=['GET'])
def get_admin_transactions():
    """관리자 거래 내역"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT order_id, user_id, service_id, price, status, created_at
                FROM orders
                ORDER BY created_at DESC
            """)
        else:
            cursor.execute("""
                SELECT order_id, user_id, service_id, price, status, created_at
                FROM orders
                ORDER BY created_at DESC
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
                'created_at': transaction[5].isoformat() if hasattr(transaction[5], 'isoformat') else str(transaction[5])
            })
        
        return jsonify({
            'transactions': transaction_list
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'거래 내역 조회 실패: {str(e)}'}), 500

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

# 앱 시작 시 자동 초기화
initialize_app()

if __name__ == '__main__':
    # 개발 서버 실행
    app.run(host='0.0.0.0', port=8000, debug=False)