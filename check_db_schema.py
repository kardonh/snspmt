#!/usr/bin/env python3
"""
실제 데이터베이스 스키마 확인 스크립트
"""
import os
import sys
from urllib.parse import urlparse, unquote
import psycopg2
from psycopg2.extras import RealDictCursor
import socket
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

def get_db_connection():
    """데이터베이스 연결을 가져옵니다."""
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    if not DATABASE_URL:
        raise Exception("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
    
    try:
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
            connect_timeout=30,
            sslmode='require'
        )
        conn.autocommit = False
        return conn
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")
        raise

def get_table_columns(conn, table_name):
    """테이블의 컬럼 정보를 조회합니다."""
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cursor.execute("""
            SELECT 
                column_name,
                data_type,
                character_maximum_length,
                numeric_precision,
                numeric_scale,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position
        """, (table_name,))
        
        columns = cursor.fetchall()
        return columns
    except Exception as e:
        print(f"⚠️ {table_name} 테이블 조회 실패: {e}")
        return []
    finally:
        cursor.close()

def get_foreign_keys(conn, table_name):
    """테이블의 외래 키 정보를 조회합니다."""
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cursor.execute("""
            SELECT
                tc.constraint_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = %s
        """, (table_name,))
        
        fks = cursor.fetchall()
        return fks
    except Exception as e:
        print(f"⚠️ {table_name} 외래 키 조회 실패: {e}")
        return []
    finally:
        cursor.close()

def print_table_schema(conn, table_name):
    """테이블 스키마를 출력합니다."""
    print(f"\n{'='*80}")
    print(f"📋 테이블: {table_name}")
    print(f"{'='*80}")
    
    # 컬럼 정보
    columns = get_table_columns(conn, table_name)
    if not columns:
        print(f"⚠️ 테이블 '{table_name}'이 존재하지 않거나 조회할 수 없습니다.")
        return
    
    print(f"\n📊 컬럼 정보 ({len(columns)}개):")
    print("-" * 80)
    print(f"{'컬럼명':<30} {'타입':<25} {'NULL':<8} {'기본값'}")
    print("-" * 80)
    
    for col in columns:
        col_name = col['column_name']
        data_type = col['data_type']
        
        # 타입 상세 정보 추가
        if col['character_maximum_length']:
            data_type += f"({col['character_maximum_length']})"
        elif col['numeric_precision']:
            if col['numeric_scale']:
                data_type += f"({col['numeric_precision']},{col['numeric_scale']})"
            else:
                data_type += f"({col['numeric_precision']})"
        
        is_nullable = "YES" if col['is_nullable'] == 'YES' else "NO"
        default = col['column_default'] or ''
        if len(default) > 30:
            default = default[:27] + "..."
        
        print(f"{col_name:<30} {data_type:<25} {is_nullable:<8} {default}")
    
    # 외래 키 정보
    fks = get_foreign_keys(conn, table_name)
    if fks:
        print(f"\n🔗 외래 키 ({len(fks)}개):")
        print("-" * 80)
        for fk in fks:
            print(f"  {fk['column_name']} -> {fk['foreign_table_name']}.{fk['foreign_column_name']}")

def main():
    """메인 함수"""
    print("🔍 데이터베이스 스키마 확인 시작...\n")
    
    try:
        conn = get_db_connection()
        print("✅ 데이터베이스 연결 성공\n")
        
        # 주요 테이블 확인
        tables_to_check = [
            'orders',
            'order_items',
            'commissions',
            'referrals',
            'coupons',
            'users',
            'wallets',
            'products',
            'product_variants',
            'packages',
            'package_items'
        ]
        
        for table in tables_to_check:
            print_table_schema(conn, table)
        
        print(f"\n{'='*80}")
        print("✅ 스키마 확인 완료")
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    main()

