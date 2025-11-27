"""
예시 API 라우트 파일
새로운 API를 이 파일에 추가하거나, 새로운 파일을 만들어서 사용할 수 있습니다.
"""
from flask import Blueprint, request, jsonify
import os
from urllib.parse import urlparse
import psycopg2
from psycopg2.extras import RealDictCursor

# Blueprint 생성 (url_prefix는 선택사항)
new = Blueprint('new', __name__, url_prefix='/api/new')

# 데이터베이스 연결 함수 (backend.py에서 가져오거나 여기에 정의)
def get_db_connection():
    """데이터베이스 연결을 가져옵니다."""
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    if not DATABASE_URL:
        raise Exception("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
    
    try:
        parsed = urlparse(DATABASE_URL)
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path[1:],
            user=parsed.username,
            password=parsed.password,
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        print(f"❌ 데이터베이스 연결 오류: {e}")
        raise

# 예시 API 엔드포인트
@new.route('/test', methods=['GET'])
def example_test():
    """
    예시 테스트 API
    ---
    tags:
      - Example
    summary: 예시 테스트 API
    description: "새로운 API 파일 구조를 테스트하는 엔드포인트"
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Example API is working!"
    """
    return jsonify({
        'message': 'Example API is working!',
        'status': 'success'
    }), 200

@new.route('/data', methods=['GET'])
def example_get_data():
    """
    예시 데이터 조회 API
    ---
    tags:
      - Example
    summary: 예시 데이터 조회
    description: "데이터베이스에서 데이터를 조회하는 예시"
    responses:
      200:
        description: 성공
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 예시 쿼리 (실제 사용 시 수정 필요)
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchone()
        
        return jsonify({
            'data': dict(result) if result else None,
            'status': 'success'
        }), 200
    except Exception as e:
        print(f"❌ 데이터 조회 오류: {e}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

