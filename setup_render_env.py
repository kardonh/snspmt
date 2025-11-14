#!/usr/bin/env python3
"""
Render 환경변수 설정을 위한 스크립트
Supabase 연결 문자열을 생성하고 Render 설정 가이드를 제공합니다.
"""

import os
import urllib.parse

# Supabase 프로젝트 정보
SUPABASE_PROJECT_REF = "gvtrizwkstaznrlloixi"
SUPABASE_REGION = "ap-southeast-2"

def generate_connection_strings(password: str):
    """Supabase 연결 문자열 생성"""
    
    # URL 인코딩된 비밀번호
    encoded_password = urllib.parse.quote(password, safe='')
    
    # 방식 1: Connection Pooler (권장)
    pooler_url = f"postgresql://postgres.{SUPABASE_PROJECT_REF}:{encoded_password}@aws-0-{SUPABASE_REGION}.pooler.supabase.com:6543/postgres"
    
    # 방식 2: Direct Connection
    direct_url = f"postgresql://postgres:{encoded_password}@db.{SUPABASE_PROJECT_REF}.supabase.co:5432/postgres"
    
    return {
        "pooler": pooler_url,
        "direct": direct_url
    }

def print_setup_guide(connection_string: str):
    """Render 설정 가이드 출력"""
    print("\n" + "="*60)
    print("Render 환경변수 설정 가이드")
    print("="*60)
    print("\n1. Render 대시보드 접속:")
    print("   https://dashboard.render.com")
    print("\n2. 백엔드 서비스 선택")
    print("\n3. Environment 탭 클릭")
    print("\n4. DATABASE_URL 환경변수 설정:")
    print(f"   {connection_string}")
    print("\n5. Save Changes 클릭")
    print("\n6. Render가 자동으로 재배포를 시작합니다")
    print("\n" + "="*60)

def main():
    print("Supabase 연결 문자열 생성기")
    print("-" * 60)
    
    # 비밀번호 입력
    password = input("\nSupabase 데이터베이스 비밀번호를 입력하세요: ").strip()
    
    if not password:
        print("❌ 비밀번호가 입력되지 않았습니다.")
        return
    
    # 연결 문자열 생성
    connections = generate_connection_strings(password)
    
    print("\n✅ 연결 문자열 생성 완료!\n")
    
    # Connection Pooler 사용 (권장)
    print("📌 권장: Connection Pooler 사용")
    print_setup_guide(connections["pooler"])
    
    print("\n\n" + "-"*60)
    print("대안: Direct Connection (필요시)")
    print("-"*60)
    print(f"\n{connections['direct']}")
    
    # 파일로 저장
    save_to_file = input("\n연결 문자열을 파일로 저장하시겠습니까? (y/n): ").strip().lower()
    if save_to_file == 'y':
        with open("render_database_url.txt", "w", encoding="utf-8") as f:
            f.write("# Render DATABASE_URL 환경변수\n")
            f.write(f"# Connection Pooler (권장)\n")
            f.write(f"DATABASE_URL={connections['pooler']}\n\n")
            f.write(f"# Direct Connection (대안)\n")
            f.write(f"DATABASE_URL={connections['direct']}\n")
        print("✅ render_database_url.txt 파일에 저장되었습니다.")
    
    print("\n✅ 완료!")

if __name__ == "__main__":
    main()

