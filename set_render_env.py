#!/usr/bin/env python3
"""
Render API를 통해 환경변수 설정 스크립트
"""

import requests
import json

# Render API 설정
RENDER_API_KEY = "rnd_yfNO7ZpoMQY8R2dsTLRNums7OxvV"
RENDER_API_BASE = "https://api.render.com/v1"

# 서비스 정보
SERVICE_NAME = "snspmt"  # 프로젝트 이름

# 설정할 환경변수
DATABASE_URL = "postgresql://postgres.gvtrizwkstaznrlloixi:KARDONH0813%21@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres"

def get_services():
    """Render 서비스 목록 조회"""
    headers = {
        "Authorization": f"Bearer {RENDER_API_KEY}",
        "Accept": "application/json"
    }
    
    response = requests.get(f"{RENDER_API_BASE}/services", headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ 서비스 목록 조회 실패: {response.status_code}")
        print(response.text)
        return None

def find_service_by_name(services, name):
    """이름으로 서비스 찾기"""
    if not services:
        return None
    
    for service in services:
        if service.get("name") == name or name.lower() in service.get("name", "").lower():
            return service
    return None

def get_service_env_vars(service_id):
    """서비스의 환경변수 조회"""
    headers = {
        "Authorization": f"Bearer {RENDER_API_KEY}",
        "Accept": "application/json"
    }
    
    response = requests.get(
        f"{RENDER_API_BASE}/services/{service_id}/env-vars",
        headers=headers
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ 환경변수 조회 실패: {response.status_code}")
        print(response.text)
        return None

def set_env_var(service_id, key, value):
    """환경변수 설정"""
    headers = {
        "Authorization": f"Bearer {RENDER_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # 기존 환경변수 확인
    existing_vars = get_service_env_vars(service_id)
    if existing_vars:
        # 이미 존재하는지 확인
        for env_var in existing_vars:
            if env_var.get("key") == key:
                # 업데이트
                env_var_id = env_var.get("id")
                print(f"🔄 기존 환경변수 업데이트: {key}")
                response = requests.patch(
                    f"{RENDER_API_BASE}/services/{service_id}/env-vars/{env_var_id}",
                    headers=headers,
                    json={"value": value}
                )
                if response.status_code == 200:
                    print(f"✅ 환경변수 업데이트 성공: {key}")
                    return True
                else:
                    print(f"❌ 환경변수 업데이트 실패: {response.status_code}")
                    print(response.text)
                    return False
    
    # 새로 생성
    print(f"➕ 새 환경변수 생성: {key}")
    response = requests.post(
        f"{RENDER_API_BASE}/services/{service_id}/env-vars",
        headers=headers,
        json={"key": key, "value": value}
    )
    
    if response.status_code == 201 or response.status_code == 200:
        print(f"✅ 환경변수 생성 성공: {key}")
        return True
    else:
        print(f"❌ 환경변수 생성 실패: {response.status_code}")
        print(response.text)
        return False

def main():
    print("🚀 Render 환경변수 설정 시작")
    print("-" * 60)
    
    # 서비스 목록 조회
    print(f"📋 서비스 목록 조회 중... (이름: {SERVICE_NAME})")
    services = get_services()
    
    if not services:
        print("❌ 서비스를 찾을 수 없습니다.")
        return
    
    # 서비스 찾기
    service = find_service_by_name(services, SERVICE_NAME)
    
    if not service:
        print(f"❌ '{SERVICE_NAME}' 서비스를 찾을 수 없습니다.")
        print("\n사용 가능한 서비스:")
        for svc in services:
            print(f"  - {svc.get('name')} (ID: {svc.get('id')})")
        return
    
    service_id = service.get("id")
    service_name = service.get("name")
    print(f"✅ 서비스 찾음: {service_name} (ID: {service_id})")
    
    # 환경변수 설정
    print(f"\n🔧 환경변수 설정 중...")
    print(f"   Key: DATABASE_URL")
    print(f"   Value: {DATABASE_URL[:50]}...")
    
    success = set_env_var(service_id, "DATABASE_URL", DATABASE_URL)
    
    if success:
        print("\n✅ 환경변수 설정 완료!")
        print("🔄 Render가 자동으로 재배포를 시작합니다.")
        print("\n다음 단계:")
        print("1. Render 대시보드에서 배포 상태 확인")
        print("2. 로그에서 '✅ 환경 변수 검증 완료' 메시지 확인")
    else:
        print("\n❌ 환경변수 설정 실패")
        print("Render 대시보드에서 수동으로 설정해주세요.")

if __name__ == "__main__":
    main()

