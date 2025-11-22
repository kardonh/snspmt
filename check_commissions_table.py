#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get('DATABASE_URL')
parsed = urlparse(url)

conn = psycopg2.connect(
    host=parsed.hostname,
    port=parsed.port or 5432,
    database=parsed.path.lstrip('/'),
    user=parsed.username,
    password=unquote(parsed.password or '')
)

cur = conn.cursor(cursor_factory=RealDictCursor)

# commissions 테이블 컬럼 확인
print("=== commissions 테이블 컬럼 ===")
cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'commissions' 
    ORDER BY ordinal_position
""")
cols = cur.fetchall()
for c in cols:
    print(f"  {c['column_name']} ({c['data_type']})")

# referrals 테이블 컬럼 확인
print("\n=== referrals 테이블 컬럼 ===")
cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'referrals' 
    ORDER BY ordinal_position
""")
cols = cur.fetchall()
for c in cols:
    print(f"  {c['column_name']} ({c['data_type']})")

# orders 테이블의 order_id 타입 확인
print("\n=== orders 테이블 order_id 타입 ===")
cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'orders' AND column_name = 'order_id'
""")
cols = cur.fetchall()
for c in cols:
    print(f"  {c['column_name']} ({c['data_type']})")

conn.close()

