import requests
import json

# 추천인 코드 생성 테스트
def test_generate_referral():
    url = "http://localhost:8000/api/referral/generate"
    data = {
        "user_id": "test_user_123",
        "user_email": "test@example.com"
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"추천인 코드 생성 응답: {response.status_code}")
        print(f"응답 내용: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"오류 발생: {e}")
        return None

# 추천인 코드 사용 테스트
def test_use_referral(referral_code):
    url = "http://localhost:8000/api/referral/use"
    data = {
        "referral_code": referral_code,
        "user_id": "new_user_999",
        "user_email": "newuser3@example.com"
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"추천인 코드 사용 응답: {response.status_code}")
        print(f"응답 내용: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"오류 발생: {e}")
        return None

# 쿠폰 조회 테스트
def test_get_coupons():
    url = "http://localhost:8000/api/coupons?user_email=newuser3@example.com"
    
    try:
        response = requests.get(url)
        print(f"쿠폰 조회 응답: {response.status_code}")
        print(f"응답 내용: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"오류 발생: {e}")
        return None

if __name__ == "__main__":
    print("=== API 테스트 시작 ===")
    
    print("\n1. 추천인 코드 생성 테스트")
    referral_result = test_generate_referral()
    
    if referral_result and referral_result.get('success'):
        referral_code = referral_result.get('referral_code')
        print(f"\n생성된 추천인 코드: {referral_code}")
        
        print("\n2. 추천인 코드 사용 테스트")
        test_use_referral(referral_code)
        
        print("\n3. 쿠폰 조회 테스트")
        test_get_coupons()
    else:
        print("추천인 코드 생성 실패")
