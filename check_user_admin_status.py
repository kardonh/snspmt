#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
사용자의 관리자 권한 확인 스크립트
"""
import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    """데이터베이스 연결"""
    if not DATABASE_URL:
        raise Exception("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
    
    parsed = urlparse(DATABASE_URL)
    user_info = parsed.username
    password = unquote(parsed.password) if parsed.password else ''
    host = parsed.hostname
    port = parsed.port or 5432
    database = parsed.path.lstrip('/') or 'postgres'
    
    if user_info and '.' in user_info:
        user = user_info
    else:
        user = user_info or 'postgres'
    
    conn = psycopg2.connect(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        connect_timeout=30
    )
    return conn

def check_admin_status():
    """사용자의 관리자 권한 확인"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        email = 'tambleofficial@gmail.com'
        
        print("=" * 80)
        print(f"📧 사용자 관리자 권한 확인: {email}")
        print("=" * 80)
        
        # 대소문자 구분 없이 검색
        cursor.execute("""
            SELECT 
                user_id,
                email,
                is_admin,
                external_uid,
                created_at
            FROM users 
            WHERE LOWER(email) = LOWER(%s)
            LIMIT 1
        """, (email,))
        
        user = cursor.fetchone()
        
        if not user:
            print(f"❌ 사용자를 찾을 수 없습니다: {email}")
            
            # 비슷한 이메일 찾기
            cursor.execute("""
                SELECT email, is_admin 
                FROM users 
                WHERE email ILIKE %s
                LIMIT 5
            """, (f'%{email.split("@")[0]}%',))
            
            similar = cursor.fetchall()
            if similar:
                print(f"\n📋 비슷한 이메일 목록:")
                for u in similar:
                    print(f"   - {u['email']}: is_admin={u['is_admin']}")
        else:
            user_dict = dict(user)
            print(f"\n✅ 사용자 찾음:")
            print(f"   user_id: {user_dict.get('user_id')}")
            print(f"   email: {user_dict.get('email')}")
            print(f"   is_admin: {user_dict.get('is_admin')} (타입: {type(user_dict.get('is_admin'))})")
            print(f"   external_uid: {user_dict.get('external_uid')}")
            print(f"   created_at: {user_dict.get('created_at')}")
            
            # is_admin 값 분석
            is_admin = user_dict.get('is_admin')
            if is_admin is None:
                print(f"\n⚠️ is_admin이 None입니다!")
            elif isinstance(is_admin, bool):
                print(f"\n✅ is_admin은 boolean 타입: {is_admin}")
            elif isinstance(is_admin, (int, float)):
                print(f"\n⚠️ is_admin은 숫자 타입: {is_admin} (boolean 변환: {bool(is_admin and is_admin != 0)})")
            else:
                print(f"\n⚠️ is_admin은 기타 타입: {type(is_admin)} = {is_admin}")
        
        # 모든 관리자 계정 확인
        print(f"\n" + "=" * 80)
        print(f"📋 모든 관리자 계정 목록:")
        print("=" * 80)
        
        cursor.execute("""
            SELECT 
                email,
                is_admin,
                user_id,
                external_uid
            FROM users 
            WHERE is_admin = TRUE OR is_admin = 1
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        admins = cursor.fetchall()
        if admins:
            for admin in admins:
                admin_dict = dict(admin)
                print(f"   - {admin_dict['email']}: is_admin={admin_dict['is_admin']} (타입: {type(admin_dict['is_admin'])})")
        else:
            print("   관리자 계정이 없습니다.")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    check_admin_status()

