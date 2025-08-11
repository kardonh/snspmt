from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import sqlite3
from datetime import datetime, timedelta
import uuid
import os

app = Flask(__name__)
# CORS 설정을 더 구체적으로 지정
CORS(app, origins=['http://localhost:3000', 'http://127.0.0.1:3000'], 
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization'])

# snspop API 설정
SNSPOP_API_URL = 'https://snspop.com/api/v2'
API_KEY = '284ff0e3bc3dfff934914d1f30535b3c'

# 데이터베이스 초기화
def init_db():
    conn = None
    try:
        conn = sqlite3.connect('orders.db', timeout=20.0)
        cursor = conn.cursor()
        
        # 주문 테이블 생성
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                user_email TEXT NOT NULL,
                platform TEXT NOT NULL,
                service TEXT NOT NULL,
                link TEXT,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                snspop_order_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 추천인 코드 테이블 생성
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referral_codes (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                user_email TEXT NOT NULL,
                code TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 추천인 관계 테이블 생성
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                id TEXT PRIMARY KEY,
                referrer_id TEXT NOT NULL,
                referrer_email TEXT NOT NULL,
                referred_id TEXT NOT NULL,
                referred_email TEXT NOT NULL,
                referral_code TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 쿠폰 테이블 생성
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS coupons (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                user_email TEXT NOT NULL,
                code TEXT NOT NULL,
                discount_type TEXT NOT NULL,
                discount_value REAL NOT NULL,
                is_used BOOLEAN DEFAULT FALSE,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                used_at TIMESTAMP
            )
        ''')
        
        conn.commit()
        print("💾 Database initialized for order tracking...")
        
    except Exception as e:
        print(f"데이터베이스 초기화 실패: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

# 데이터베이스 초기화 실행
init_db()

# 추천인 코드 생성
def generate_referral_code(user_id, user_email):
    try:
        conn = sqlite3.connect('orders.db')
        cursor = conn.cursor()
        
        # 기존 추천인 코드가 있는지 확인
        cursor.execute('SELECT code FROM referral_codes WHERE user_id = ?', (user_id,))
        existing = cursor.fetchone()
        
        if existing:
            return existing[0]
        
        # 새로운 추천인 코드 생성 (8자리 랜덤)
        import random
        import string
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        # 중복 확인
        while True:
            cursor.execute('SELECT id FROM referral_codes WHERE code = ?', (code,))
            if not cursor.fetchone():
                break
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        # 추천인 코드 저장
        cursor.execute('''
            INSERT INTO referral_codes (id, code, user_id, user_email)
            VALUES (?, ?, ?, ?)
        ''', (str(uuid.uuid4()), code, user_id, user_email))
        
        conn.commit()
        conn.close()
        return code
        
    except Exception as e:
        print(f"추천인 코드 생성 실패: {e}")
        return None

# 쿠폰 생성
def create_coupon(user_id, user_email, discount_type, discount_value):
    conn = None
    try:
        conn = sqlite3.connect('orders.db', timeout=20.0)
        cursor = conn.cursor()
        
        # 30일 후 만료 (timedelta 사용)
        expires_at = datetime.now() + timedelta(days=30)
        
        cursor.execute('''
            INSERT INTO coupons (id, user_id, user_email, code, discount_type, discount_value, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(uuid.uuid4()),
            user_id,
            user_email,
            f"COUPON_{discount_type}_{discount_value}",
            discount_type,
            discount_value,
            expires_at
        ))
        
        conn.commit()
        print(f"쿠폰 생성 성공: {discount_type} {discount_value}% for {user_email}")
        return True
        
    except Exception as e:
        print(f"쿠폰 생성 실패: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

# 추천인 코드 검증 및 쿠폰 지급
def process_referral_code(referral_code, new_user_id, new_user_email):
    conn = None
    try:
        conn = sqlite3.connect('orders.db', timeout=20.0)
        cursor = conn.cursor()
        
        # 추천인 코드로 사용자 찾기
        cursor.execute('''
            SELECT user_id, user_email FROM referral_codes 
            WHERE code = ? AND user_id != ?
        ''', (referral_code, new_user_id))
        
        referrer = cursor.fetchone()
        if not referrer:
            return False, "유효하지 않은 추천인 코드입니다."
        
        referrer_id, referrer_email = referrer
        
        # 이미 추천받은 사용자인지 확인
        cursor.execute('''
            SELECT id FROM referrals WHERE referred_id = ?
        ''', (new_user_id,))
        
        if cursor.fetchone():
            return False, "이미 추천인 코드를 사용한 사용자입니다."
        
        # 추천인 관계 저장
        cursor.execute('''
            INSERT INTO referrals (id, referrer_id, referrer_email, referred_id, referred_email, referral_code)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            str(uuid.uuid4()),
            referrer_id,
            referrer_email,
            new_user_id,
            new_user_email,
            referral_code
        ))
        
        # 신규 사용자에게 5% 쿠폰 지급
        if not create_coupon(new_user_id, new_user_email, "percentage", 5):
            print(f"신규 사용자 쿠폰 생성 실패: {new_user_email}")
        
        # 추천인에게 15% 쿠폰 지급
        if not create_coupon(referrer_id, referrer_email, "percentage", 15):
            print(f"추천인 쿠폰 생성 실패: {referrer_email}")
        
        conn.commit()
        print(f"추천인 코드 처리 완료: {referral_code} -> {new_user_email}")
        return True, "추천인 코드가 성공적으로 적용되었습니다!"
        
    except Exception as e:
        print(f"추천인 코드 처리 실패: {e}")
        if conn:
            conn.rollback()
        return False, "추천인 코드 처리 중 오류가 발생했습니다."
    finally:
        if conn:
            conn.close()

@app.route('/api/snspop', methods=['POST'])
def proxy_snspop_api():
    try:
        data = request.get_json()
        
        # snspop API로 요청 전달
        response = requests.post(SNSPOP_API_URL, json=data, timeout=30)
        response_data = response.json()
        
        # 주문 생성인 경우 데이터베이스에 저장
        if data.get('action') == 'add' and response.status_code == 200:
            if response_data.get('order'):
                save_order_to_db(data, response_data['order'])
            elif response_data.get('error'):
                # 오류 로깅
                print(f"주문 생성 실패 - 오류: {response_data.get('error')}")
                if 'not_enough_funds' in response_data.get('error', ''):
                    print("잔액 부족 오류 발생")
        
        # 응답 반환
        return jsonify(response_data), response.status_code
        
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'API 요청 실패: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'서버 오류: {str(e)}'}), 500

def save_order_to_db(request_data, snspop_order):
    try:
        conn = sqlite3.connect('orders.db')
        cursor = conn.cursor()
        
        order_id = str(uuid.uuid4())
        user_id = request_data.get('user_id', 'anonymous')
        user_email = request_data.get('user_email', 'anonymous@example.com')
        
        cursor.execute('''
            INSERT INTO orders (
                id, user_id, user_email, platform, service, link,
                quantity, price, snspop_order_id, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            order_id, user_id, user_email,
            request_data.get('platform', 'unknown'),
            request_data.get('service_name', 'unknown'),
            request_data.get('link', ''),
            request_data.get('quantity', 0),
            request_data.get('price', 0),
            snspop_order,
            'pending'
        ))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"주문 저장 실패: {e}")

@app.route('/api/orders', methods=['GET'])
def get_user_orders():
    try:
        user_email = request.args.get('user_email')
        if not user_email:
            return jsonify({'error': '사용자 이메일이 필요합니다'}), 400
        
        conn = sqlite3.connect('orders.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM orders
            WHERE user_email = ?
            ORDER BY created_at DESC
        ''', (user_email,))
        
        orders = []
        for row in cursor.fetchall():
            orders.append({
                'id': row[0],
                'user_id': row[1],
                'user_email': row[2],
                'platform': row[3],
                'service': row[4],
                'link': row[5],
                'quantity': row[6],
                'price': row[7],
                'status': row[8],
                'snspop_order_id': row[9],
                'created_at': row[10],
                'updated_at': row[11]
            })
        
        conn.close()
        return jsonify({'orders': orders})
        
    except Exception as e:
        return jsonify({'error': f'주문 조회 실패: {str(e)}'}), 500

@app.route('/api/orders/<order_id>', methods=['PUT'])
def update_order_status(order_id):
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'error': '새로운 상태가 필요합니다'}), 400
        
        conn = sqlite3.connect('orders.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE orders
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (new_status, order_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': '주문을 찾을 수 없습니다'}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': '주문 상태가 업데이트되었습니다'})
        
    except Exception as e:
        return jsonify({'error': f'주문 상태 업데이트 실패: {str(e)}'}), 500

# 추천인 코드 생성 API
@app.route('/api/referral/generate', methods=['POST'])
def generate_referral():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        user_email = data.get('user_email')
        
        if not user_id or not user_email:
            return jsonify({'success': False, 'error': '사용자 정보가 필요합니다'}), 400
        
        code = generate_referral_code(user_id, user_email)
        if code:
            return jsonify({'success': True, 'referral_code': code})
        else:
            return jsonify({'success': False, 'error': '추천인 코드 생성에 실패했습니다'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'추천인 코드 생성 실패: {str(e)}'}), 500

# 추천인 코드 사용 API
@app.route('/api/referral/use', methods=['POST'])
def use_referral():
    try:
        data = request.get_json()
        referral_code = data.get('referral_code')
        user_id = data.get('user_id')
        user_email = data.get('user_email')
        
        if not referral_code or not user_id or not user_email:
            return jsonify({'error': '필수 정보가 누락되었습니다'}), 400
        
        success, message = process_referral_code(referral_code, user_id, user_email)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
            
    except Exception as e:
        return jsonify({'error': f'추천인 코드 사용 실패: {str(e)}'}), 500

# 사용자 쿠폰 조회 API
@app.route('/api/coupons', methods=['GET'])
def get_user_coupons():
    try:
        user_email = request.args.get('user_email')
        if not user_email:
            return jsonify({'error': '사용자 이메일이 필요합니다'}), 400
        
        conn = sqlite3.connect('orders.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM coupons
            WHERE user_email = ?
            ORDER BY created_at DESC
        ''', (user_email,))
        
        coupons = []
        for row in cursor.fetchall():
            coupons.append({
                'id': row[0],
                'user_id': row[1],
                'user_email': row[2],
                'code': row[3],
                'discount_type': row[4],
                'discount_value': row[5],
                'is_used': bool(row[6]),
                'expires_at': row[7],
                'created_at': row[8],
                'used_at': row[9]
            })
        
        conn.close()
        return jsonify({'coupons': coupons})
        
    except Exception as e:
        return jsonify({'error': f'쿠폰 조회 실패: {str(e)}'}), 500

# 쿠폰 사용 API
@app.route('/api/coupons/<coupon_id>/use', methods=['POST'])
def use_coupon(coupon_id):
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        
        if not order_id:
            return jsonify({'error': '주문 ID가 필요합니다'}), 400
        
        conn = sqlite3.connect('orders.db')
        cursor = conn.cursor()
        
        # 쿠폰 정보 조회
        cursor.execute('''
            SELECT * FROM coupons WHERE id = ? AND is_used = FALSE AND expires_at > datetime('now')
        ''', (coupon_id,))
        
        coupon = cursor.fetchone()
        if not coupon:
            conn.close()
            return jsonify({'error': '사용할 수 없는 쿠폰입니다'}), 400
        
        # 쿠폰 사용 처리
        cursor.execute('''
            UPDATE coupons
            SET is_used = TRUE, used_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (coupon_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '쿠폰이 성공적으로 사용되었습니다',
            'coupon': {
                'discount_type': coupon[4],
                'discount_value': coupon[5]
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'쿠폰 사용 실패: {str(e)}'}), 500

# 사용자 추천인 코드 조회 API
@app.route('/api/referral/user/<user_email>', methods=['GET'])
def get_user_referral_code(user_email):
    try:
        conn = sqlite3.connect('orders.db')
        cursor = conn.cursor()
        
        # 사용자의 추천인 코드 조회
        cursor.execute('''
            SELECT code FROM referral_codes WHERE user_email = ?
        ''', (user_email,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return jsonify({'referral_code': result[0]})
        else:
            return jsonify({'referral_code': None})
            
    except Exception as e:
        return jsonify({'error': f'추천인 코드 조회 실패: {str(e)}'}), 500

# 테스트용 엔드포인트 - 추천인 코드 생성 테스트
@app.route('/api/test/create-referral', methods=['POST'])
def test_create_referral():
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'test_user_123')
        user_email = data.get('user_email', 'test@example.com')
        
        print(f"테스트: 추천인 코드 생성 시도 - user_id: {user_id}, user_email: {user_email}")
        
        code = generate_referral_code(user_id, user_email)
        if code:
            print(f"테스트: 추천인 코드 생성 성공 - {code}")
            return jsonify({'success': True, 'referral_code': code})
        else:
            print("테스트: 추천인 코드 생성 실패")
            return jsonify({'success': False, 'error': '추천인 코드 생성 실패'}), 500
            
    except Exception as e:
        print(f"테스트: 에러 발생 - {e}")
        return jsonify({'error': f'테스트 실패: {str(e)}'}), 500

# 테스트용 엔드포인트 - 쿠폰 생성 테스트
@app.route('/api/test/create-coupon', methods=['POST'])
def test_create_coupon():
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'test_user_123')
        user_email = data.get('user_email', 'test@example.com')
        discount_type = data.get('discount_type', 'percentage')
        discount_value = data.get('discount_value', 10)
        
        print(f"테스트: 쿠폰 생성 시도 - user_id: {user_id}, user_email: {user_email}")
        
        coupon = create_coupon(user_id, user_email, discount_type, discount_value)
        if coupon:
            print(f"테스트: 쿠폰 생성 성공 - {coupon}")
            return jsonify({'success': True, 'coupon': coupon})
        else:
            print("테스트: 쿠폰 생성 실패")
            return jsonify({'success': False, 'error': '쿠폰 생성 실패'}), 500
            
    except Exception as e:
        print(f"테스트: 에러 발생 - {e}")
        return jsonify({'error': f'테스트 실패: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Backend server is running'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    print(f"🚀 Backend server starting on http://localhost:{port}")
    print("📡 Proxying requests to snspop API...")
    print("💾 Database initialized for order tracking...")
    print("🎫 Referral system and coupon management enabled...")
    app.run(host='0.0.0.0', port=port, debug=False)
