import sqlite3
import uuid
from datetime import datetime, timedelta
import json
from .config import *

# 데이터베이스 초기화
def init_db():
    conn = None
    try:
        conn = sqlite3.connect('/tmp/orders.db', timeout=20.0)
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

# 추천인 코드 생성
def generate_referral_code(user_id, user_email):
    try:
        conn = sqlite3.connect('/tmp/orders.db', timeout=20.0)
        cursor = conn.cursor()
        
        # 기존 코드가 있는지 확인
        cursor.execute('SELECT code FROM referral_codes WHERE user_email = ?', (user_email,))
        existing_code = cursor.fetchone()
        
        if existing_code:
            return existing_code[0]
        
        # 새 코드 생성
        code = f"REF{user_id[:8].upper()}"
        
        cursor.execute('''
            INSERT INTO referral_codes (id, user_id, user_email, code)
            VALUES (?, ?, ?, ?)
        ''', (str(uuid.uuid4()), user_id, user_email, code))
        
        conn.commit()
        return code
        
    except Exception as e:
        print(f"추천인 코드 생성 실패: {e}")
        return None
    finally:
        if conn:
            conn.close()

# 쿠폰 생성
def create_coupon(user_id, user_email, discount_type, discount_value):
    try:
        conn = sqlite3.connect('/tmp/orders.db', timeout=20.0)
        cursor = conn.cursor()
        
        # 30일 후 만료
        expires_at = datetime.now() + timedelta(days=30)
        
        cursor.execute('''
            INSERT INTO coupons (id, user_id, user_email, code, discount_type, discount_value, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(uuid.uuid4()), 
            user_id, 
            user_email, 
            f"COUPON{user_id[:8].upper()}", 
            discount_type, 
            discount_value, 
            expires_at
        ))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"쿠폰 생성 실패: {e}")
        return False
    finally:
        if conn:
            conn.close()

# 추천인 코드 처리
def process_referral_code(referral_code, new_user_id, new_user_email):
    try:
        conn = sqlite3.connect('/tmp/orders.db', timeout=20.0)
        cursor = conn.cursor()
        
        # 추천인 코드 찾기
        cursor.execute('''
            SELECT user_id, user_email FROM referral_codes 
            WHERE code = ?
        ''', (referral_code,))
        
        referrer = cursor.fetchone()
        if not referrer:
            return False, "Invalid referral code"
        
        referrer_id, referrer_email = referrer
        
        # 자기 자신을 추천할 수 없음
        if referrer_email == new_user_email:
            return False, "Cannot refer yourself"
        
        # 이미 추천 관계가 있는지 확인
        cursor.execute('''
            SELECT id FROM referrals 
            WHERE referred_email = ?
        ''', (new_user_email,))
        
        if cursor.fetchone():
            return False, "User already referred"
        
        # 추천 관계 생성
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
        
        # 추천인에게 쿠폰 지급 (10% 할인)
        create_coupon(referrer_id, referrer_email, 'percentage', 10.0)
        
        # 추천받은 사용자에게 쿠폰 지급 (5% 할인)
        create_coupon(new_user_id, new_user_email, 'percentage', 5.0)
        
        conn.commit()
        return True, "Referral processed successfully"
        
    except Exception as e:
        print(f"추천인 코드 처리 실패: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()

# 주문 저장
def save_order_to_db(request_data, snspop_order):
    try:
        conn = sqlite3.connect('/tmp/orders.db', timeout=20.0)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO orders (id, user_id, user_email, platform, service, link, quantity, price, snspop_order_id, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(uuid.uuid4()),
            request_data.get('user_id'),
            request_data.get('user_email'),
            request_data.get('platform'),
            request_data.get('service'),
            request_data.get('link'),
            request_data.get('quantity'),
            request_data.get('price'),
            smmkings_order.get('order'),
            'pending'
        ))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"주문 저장 실패: {e}")
        return False
    finally:
        if conn:
            conn.close()

# CORS 헤더 설정
def set_cors_headers():
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    }
