import sqlite3
from datetime import datetime, timedelta
import uuid

def test_create_coupon_direct():
    try:
        # 데이터베이스에 직접 연결
        conn = sqlite3.connect('orders.db', timeout=20.0)
        cursor = conn.cursor()
        
        # 테이블 구조 확인
        cursor.execute("PRAGMA table_info(coupons)")
        columns = cursor.fetchall()
        print("쿠폰 테이블 구조:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        
        # 30일 후 만료
        expires_at = datetime.now() + timedelta(days=30)
        
        # 테스트 쿠폰 생성
        coupon_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO coupons (id, user_id, user_email, code, discount_type, discount_value, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            coupon_id,
            "test_user_123",
            "test@example.com",
            "COUPON_percentage_5",
            "percentage",
            5,
            expires_at
        ))
        
        conn.commit()
        print(f"\n쿠폰 생성 성공!")
        print(f"쿠폰 ID: {coupon_id}")
        print(f"만료일: {expires_at}")
        
        # 생성된 쿠폰 확인
        cursor.execute("SELECT * FROM coupons WHERE id = ?", (coupon_id,))
        coupon = cursor.fetchone()
        if coupon:
            print(f"\n생성된 쿠폰 데이터:")
            print(f"  ID: {coupon[0]}")
            print(f"  사용자 ID: {coupon[1]}")
            print(f"  이메일: {coupon[2]}")
            print(f"  코드: {coupon[3]}")
            print(f"  할인 타입: {coupon[4]}")
            print(f"  할인 값: {coupon[5]}")
            print(f"  사용 여부: {coupon[6]}")
            print(f"  만료일: {coupon[7]}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"쿠폰 생성 실패: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("=== 직접 쿠폰 생성 테스트 ===")
    test_create_coupon_direct()
