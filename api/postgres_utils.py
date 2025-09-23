import psycopg2
import uuid
from datetime import datetime
import os
from .config import *

# PostgreSQL 연결
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'snspmt'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'password'),
            port=os.getenv('DB_PORT', '5432')
        )
        return conn
    except Exception as e:
        print(f"❌ PostgreSQL 연결 실패: {e}")
        return None

# 추천인 코드 생성 (관리자용)
def create_referral_code_admin(email, name=None, phone=None):
    try:
        conn = get_db_connection()
        if not conn:
            return None, "데이터베이스 연결 실패"
        
        cursor = conn.cursor()
        
        # 기존 코드가 있는지 확인
        cursor.execute('SELECT code FROM referral_codes WHERE user_email = %s', (email,))
        existing_code = cursor.fetchone()
        
        if existing_code:
            return existing_code[0], "기존 코드 반환"
        
        # 새 코드 생성
        code = f"REF{str(uuid.uuid4())[:8].upper()}"
        
        cursor.execute('''
            INSERT INTO referral_codes (id, user_id, user_email, code, name, phone, created_at, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            str(uuid.uuid4()),
            f"admin_{email}",
            email,
            code,
            name,
            phone,
            datetime.now(),
            True
        ))
        
        conn.commit()
        return code, "추천인 코드 생성 성공"
        
    except Exception as e:
        print(f"❌ 추천인 코드 생성 실패: {e}")
        return None, str(e)
    finally:
        if conn:
            conn.close()

# 추천인 목록 조회
def get_referral_codes():
    try:
        conn = get_db_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, code, user_email, name, phone, created_at, is_active, usage_count, total_commission
            FROM referral_codes 
            ORDER BY created_at DESC
        ''')
        
        codes = []
        for row in cursor.fetchall():
            codes.append({
                'id': row[0],
                'code': row[1],
                'email': row[2],
                'name': row[3],
                'phone': row[4],
                'createdAt': row[5].isoformat(),
                'isActive': row[6],
                'usage_count': row[7] or 0,
                'total_commission': row[8] or 0
            })
        
        return codes
        
    except Exception as e:
        print(f"❌ 추천인 코드 목록 조회 실패: {e}")
        return []
    finally:
        if conn:
            conn.close()

# 추천인 등록 (관리자용)
def register_referral_admin(email, referral_code, name=None, phone=None):
    try:
        conn = get_db_connection()
        if not conn:
            return None, "데이터베이스 연결 실패"
        
        cursor = conn.cursor()
        
        # 추천인 정보 저장
        cursor.execute('''
            INSERT INTO referrals (id, referrer_email, referral_code, name, phone, created_at, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (
            str(uuid.uuid4()),
            email,
            referral_code,
            name,
            phone,
            datetime.now(),
            'active'
        ))
        
        conn.commit()
        return True, "추천인 등록 성공"
        
    except Exception as e:
        print(f"❌ 추천인 등록 실패: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()

# 추천인 목록 조회
def get_referrals():
    try:
        conn = get_db_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, referrer_email, referral_code, name, phone, created_at, status
            FROM referrals 
            ORDER BY created_at DESC
        ''')
        
        referrals = []
        for row in cursor.fetchall():
            referrals.append({
                'id': row[0],
                'email': row[1],
                'referralCode': row[2],
                'name': row[3],
                'phone': row[4],
                'joinDate': row[5].strftime('%Y-%m-%d'),
                'status': row[6]
            })
        
        return referrals
        
    except Exception as e:
        print(f"❌ 추천인 목록 조회 실패: {e}")
        return []
    finally:
        if conn:
            conn.close()

# 커미션 내역 조회
def get_commissions():
    try:
        conn = get_db_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, referred_user, purchase_amount, commission_amount, commission_rate, payment_date
            FROM commissions 
            ORDER BY payment_date DESC
        ''')
        
        commissions = []
        for row in cursor.fetchall():
            commissions.append({
                'id': row[0],
                'referredUser': row[1],
                'purchaseAmount': row[2],
                'commissionAmount': row[3],
                'commissionRate': f"{row[4] * 100}%",
                'paymentDate': row[5].strftime('%Y-%m-%d')
            })
        
        return commissions
        
    except Exception as e:
        print(f"❌ 커미션 내역 조회 실패: {e}")
        return []
    finally:
        if conn:
            conn.close()
