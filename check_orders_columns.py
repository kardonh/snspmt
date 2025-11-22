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
cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'orders' 
    ORDER BY ordinal_position
""")

cols = cur.fetchall()
print('orders 테이블 컬럼:')
for c in cols:
    print(f"  {c['column_name']} ({c['data_type']})")

conn.close()

