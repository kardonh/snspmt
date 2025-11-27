#!/usr/bin/env python3
"""
개발 환경용 서버 실행 스크립트
파일 변경 시 자동으로 서버가 재시작됩니다 (npm처럼 동작)
"""
import os
import sys

# 개발 환경 설정
os.environ['FLASK_ENV'] = 'development'
os.environ['DEBUG'] = 'True'

# backend.py import 및 실행
if __name__ == '__main__':
    from backend import app
    
    port = int(os.environ.get('PORT', 8000))
    print(f"🚀 개발 서버 시작: http://localhost:{port}")
    print("📝 파일 변경 시 자동으로 재시작됩니다 (Ctrl+C로 종료)")
    print("=" * 50)
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=True,
        use_reloader=True,
        use_debugger=True,
        reloader_type='stat'  # 'stat' 또는 'watchdog' (watchdog이 더 빠름)
    )

