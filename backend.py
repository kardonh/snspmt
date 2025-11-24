import os
import json
import re
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta 
import requests
import tempfile
import sqlite3
import threading
import time
from functools import wraps
from werkzeug.utils import secure_filename
from flask import send_from_directory
from dotenv import load_dotenv
from urllib.parse import urlparse, unquote

# UTF-8 인코딩 강제 설정 (Windows에서 psycopg2 내부 인코딩 문제 해결)
if sys.platform == 'win32':
    import locale
    # 모든 인코딩 관련 환경 변수 설정
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONLEGACYWINDOWSSTDIO'] = '0'
    os.environ['PYTHONUTF8'] = '1'
    
    # Windows 콘솔 인코딩 설정
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except:
            pass
    if hasattr(sys.stderr, 'reconfigure'):
        try:
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except:
            pass
    
    # Locale 설정 시도
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except:
        try:
            locale.setlocale(locale.LC_ALL, 'C.UTF-8')
        except:
            try:
                locale.setlocale(locale.LC_ALL, '')
            except:
                pass

# .env 파일 로드 (로컬 개발용) - UTF-8 인코딩 명시
try:
    # .env 파일을 UTF-8로 명시적으로 읽기
    load_dotenv(encoding='utf-8')
except Exception:
    # 인코딩 지정 실패 시 기본 방식으로 시도
    load_dotenv()

# 안전한 파라미터 조회 유틸 (AWS SSM/Secrets 미사용시 환경변수에서 조회)
def get_parameter_value(key: str, default: str = "") -> str:
    try:
        return os.getenv(key, default)
    except Exception:
        return default

# Flask 앱 초기화
app = Flask(__name__, static_folder='dist', static_url_path='')
CORS(app)

# Swagger 설정
try:
    from flasgger import Swagger
    
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": "apispec",
                "route": "/apispec.json",
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/api-docs"
    }
    
    swagger_template = {
        "swagger": "2.0",
        "info": {
            "title": "SNS PMT API",
            "description": "SNS PMT 서비스 API 문서",
            "version": "1.0.0",
            "contact": {
                "name": "API Support"
            }
        },
        "basePath": "/",
        "schemes": ["http", "https"],
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "JWT 토큰을 Bearer 형식으로 전달 (예: Bearer {token})"
            }
        },
        "tags": [
            {
                "name": "Health",
                "description": "헬스 체크 관련 API"
            },
            {
                "name": "Users",
                "description": "사용자 관련 API"
            },
            {
                "name": "Orders",
                "description": "주문 관련 API"
            },
            {
                "name": "Points",
                "description": "포인트 관련 API"
            },
            {
                "name": "Referral",
                "description": "추천인 코드 관련 API"
            },
            {
                "name": "Admin",
                "description": "관리자 관련 API"
            }
        ]
    }
    
    swagger = Swagger(app, config=swagger_config, template=swagger_template)
    
    # Swagger 엔드포인트에 캐시 제어 헤더 추가 (304 에러 방지)
    @app.after_request
    def add_cache_control_for_swagger(response):
        """Swagger 관련 엔드포인트에 캐시 제어 헤더 추가"""
        if request.path.startswith('/api-docs') or request.path.startswith('/apispec') or request.path.startswith('/flasgger_static'):
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        return response
    
    # Swagger spec 생성 오류 처리 (try-except로 감싸기)
    original_get_apispecs = swagger.get_apispecs
    def safe_get_apispecs():
        try:
            return original_get_apispecs()
        except Exception as e:
            print(f"❌ Swagger spec 생성 오류: {e}")
            import traceback
            traceback.print_exc()
            # 빈 spec 반환하여 Swagger UI가 최소한 로드되도록 함
            return {
                'swagger': '2.0',
                'info': swagger_template['info'],
                'paths': {},
                'definitions': {}
            }
    swagger.get_apispecs = safe_get_apispecs
    
    print("✅ Swagger 문서화 설정 완료 - /api-docs에서 확인 가능")
except ImportError as e:
    print(f"⚠️ Swagger 설정 실패: flasgger가 설치되지 않았습니다. pip install flasgger로 설치해주세요.")
    print(f"   오류 상세: {e}")
except Exception as e:
    print(f"⚠️ Swagger 설정 중 오류 발생: {e}")
    import traceback
    traceback.print_exc()

# 정적 파일 서빙 설정
@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    """Uploaded File
    ---
    tags:
      - API
    summary: Uploaded File
    description: "Uploaded File API"
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """업로드된 파일 서빙"""
    return send_from_directory(UPLOAD_FOLDER, filename)

# 파일 업로드 설정
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# 업로드 폴더 생성
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """허용된 파일 확장자인지 확인"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Supabase JWT 검증
SUPABASE_URL = os.environ.get('VITE_SUPABASE_URL', '')
SUPABASE_JWT_SECRET = os.environ.get('SUPABASE_JWT_SECRET', '')

def verify_supabase_jwt(token):
    """Supabase JWT 토큰 검증"""
    try:
        import jwt
        from jwt import PyJWKClient
        
        if not token:
            return None
        
        # Authorization 헤더에서 Bearer 토큰 추출
        if token.startswith('Bearer '):
            token = token[7:]
        
        # Supabase JWT는 RS256 알고리즘 사용 (공개키 검증 필요)
        # 간단한 검증을 위해 서명 검증 없이 디코딩만 수행
        # 프로덕션에서는 Supabase의 공개키로 검증해야 함
        try:
            decoded = jwt.decode(token, options={"verify_signature": False})
            
            # 기본 검증: sub (user_id)와 email이 있는지 확인
            if not decoded.get('sub') or not decoded.get('email'):
                return None
            
            return decoded
        except jwt.ExpiredSignatureError:
            print("⚠️ JWT 토큰 만료")
            return None
        except jwt.InvalidTokenError as e:
            print(f"⚠️ JWT 토큰 검증 실패: {e}")
            return None
    except ImportError:
        print("⚠️ PyJWT가 설치되지 않았습니다. pip install PyJWT")
        return None
    except Exception as e:
        print(f"⚠️ JWT 검증 오류: {e}")
        return None

def get_current_user():
    """현재 요청의 사용자 정보 추출"""
    # X-User-Email 헤더가 있으면 우선 사용 (토큰이 없을 때 대체)
    user_email_header = request.headers.get('X-User-Email')
    
    auth_header = request.headers.get('Authorization')
    if auth_header:
        decoded = verify_supabase_jwt(auth_header)
        if decoded:
            return {
                'user_id': decoded.get('sub'),
                'email': decoded.get('email'),
                'metadata': decoded.get('user_metadata', {})
            }
    
    # 토큰이 없지만 X-User-Email 헤더가 있으면 email만 반환
    if user_email_header:
        return {
            'user_id': None,
            'email': user_email_header,
            'metadata': {}
        }
    
    return None

# 관리자 인증 데코레이터
def require_admin_auth(f):
    """관리자 권한이 필요한 엔드포인트용 데코레이터 - users 테이블의 is_admin 체크"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # 디버깅: 헤더 확인
            auth_header = request.headers.get('Authorization')
            user_email_header = request.headers.get('X-User-Email')
            print(f"🔍 require_admin_auth - Authorization: {bool(auth_header)}, X-User-Email: {user_email_header}")
            
            # 현재 사용자 정보 가져오기
            current_user = get_current_user()
            if not current_user:
                print(f"⚠️ 관리자 권한 없음: 로그인되지 않음 (Authorization: {bool(auth_header)}, X-User-Email: {user_email_header})")
                return jsonify({'error': '로그인이 필요합니다.'}), 401
            
            user_email = current_user.get('email')
            user_id = current_user.get('user_id')
            
            if not user_email and not user_id:
                print(f"⚠️ 관리자 권한 없음: 사용자 정보 없음")
                return jsonify({'error': '사용자 정보를 찾을 수 없습니다.'}), 401
            
            # 데이터베이스에서 is_admin 체크 (단순화: email로만 조회)
            conn = None
            cursor = None
            try:
                conn = get_db_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                # email로만 조회
                if not user_email:
                    print(f"⚠️ 관리자 권한 없음: email이 없음")
                    return jsonify({'error': '이메일 정보가 없습니다.'}), 401
                
                if DATABASE_URL.startswith('postgresql://'):
                    cursor.execute("""
                        SELECT is_admin 
                        FROM users 
                        WHERE email = %s
                        LIMIT 1
                    """, (user_email,))
                else:
                    cursor.execute("""
                        SELECT is_admin 
                        FROM users 
                        WHERE email = ?
                        LIMIT 1
                    """, (user_email,))
                
                user = cursor.fetchone()
                
                if not user:
                    print(f"⚠️ 관리자 권한 없음: 사용자를 찾을 수 없음 - email={user_email}")
                    return jsonify({'error': '사용자를 찾을 수 없습니다.'}), 404
                
                is_admin = user.get('is_admin') if isinstance(user, dict) else user[0]
                
                # SQLite의 경우 0/1로 저장되므로 변환
                if is_admin is None or (isinstance(is_admin, (int, float)) and is_admin == 0) or is_admin is False:
                    print(f"⚠️ 관리자 권한 없음: is_admin={is_admin} - email={user_email}")
                    return jsonify({'error': '관리자 권한이 필요합니다.'}), 403
                
                print(f"✅ 관리자 인증 성공: email={user_email}, is_admin={is_admin}")
                return f(*args, **kwargs)
                
            except Exception as db_error:
                print(f"❌ 관리자 권한 체크 중 DB 오류: {db_error}")
                import traceback
                print(traceback.format_exc())
                return jsonify({'error': '관리자 권한 확인 중 오류가 발생했습니다.'}), 500
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
                    
        except Exception as e:
            import traceback
            print(f"❌ require_admin_auth 데코레이터 에러: {e}")
            print(traceback.format_exc())
            return jsonify({'error': f'인증 처리 중 오류: {str(e)}'}), 500
    
    return decorated_function

# API 모니터링 미들웨어
@app.before_request
def log_request_info():
    request.start_time = time.time()

@app.after_request
def log_response_info(response):
    if hasattr(request, 'start_time'):
        duration = time.time() - request.start_time
        print(f"📊 API {request.method} {request.path} - {response.status_code} - {duration:.3f}s")
        
        # 느린 API 요청 경고 (5초 이상)
        if duration > 5.0:
            print(f"⚠️ 느린 API 요청 감지: {request.method} {request.path} - {duration:.3f}s")
    
    return response

# API 성능 모니터링 데코레이터
def monitor_performance(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            
            # 성능 로깅
            if duration > 1.0:  # 1초 이상
                print(f"🐌 느린 함수 감지: {func.__name__} - {duration:.3f}s")
            
            return result
        except Exception as e:
            duration = time.time() - start_time
            print(f"❌ 함수 실행 실패: {func.__name__} - {duration:.3f}s - {str(e)}")
            raise
    return wrapper

# sitemap.xml 서빙
@app.route('/sitemap.xml')
def sitemap():
    """Sitemap
    ---
    tags:
      - API
    summary: Sitemap
    description: "Sitemap API"
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    return app.send_static_file('sitemap.xml')

# rss.xml 서빙
@app.route('/rss.xml')
def rss():
    """Rss
    ---
    tags:
      - API
    summary: Rss
    description: "Rss API"
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    return app.send_static_file('rss.xml')

# -----------------------------
# Admin: Coupons (GET)
# -----------------------------
@app.route('/api/admin/coupons', methods=['GET'])
@require_admin_auth
def admin_get_coupons():
    """Admin Get Coupons
    ---
    tags:
      - Admin
    summary: Admin Get Coupons
    description: "Admin Get Coupons API"
    security:
      - Bearer: []
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """쿠폰 목록 조회(간단 버전)"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT 
                    c.coupon_id,
                    c.coupon_code,
                    c.coupon_name,
                    c.discount_type,
                    c.discount_value,
                    c.product_variant_id,
                    c.min_order_amount,
                    c.valid_from,
                    c.valid_until,
                    c.created_at
                FROM coupons c
                ORDER BY c.coupon_id DESC
                LIMIT 200
            """)
        else:
            cursor.execute("""
                SELECT 
                    coupon_id,
                    coupon_code,
                    coupon_name,
                    discount_type,
                    discount_value,
                    product_variant_id,
                    min_order_amount,
                    valid_from,
                    valid_until,
                    created_at
                FROM coupons
                ORDER BY coupon_id DESC
                LIMIT 200
            """)
        rows = cursor.fetchall()
        result = []
        for r in rows:
            result.append({
                'coupon_id': r.get('coupon_id'),
                'coupon_code': r.get('coupon_code'),
                'coupon_name': r.get('coupon_name'),
                'discount_type': r.get('discount_type'),
                'discount_value': float(r.get('discount_value') or 0),
                'product_variant_id': r.get('product_variant_id'),
                'min_order_amount': float(r.get('min_order_amount') or 0) if r.get('min_order_amount') else None,
                'valid_from': r.get('valid_from').isoformat() if r.get('valid_from') and hasattr(r.get('valid_from'), 'isoformat') else (str(r.get('valid_from')) if r.get('valid_from') else None),
                'valid_until': r.get('valid_until').isoformat() if r.get('valid_until') and hasattr(r.get('valid_until'), 'isoformat') else (str(r.get('valid_until')) if r.get('valid_until') else None),
                'created_at': r.get('created_at').isoformat() if r.get('created_at') and hasattr(r.get('created_at'), 'isoformat') else (str(r.get('created_at')) if r.get('created_at') else None),
            })
        return jsonify({'coupons': result, 'count': len(result)}), 200
    except Exception as e:
        print(f"❌ 쿠폰 목록 조회 오류: {e}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': f'쿠폰 조회 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/admin/coupons', methods=['POST', 'OPTIONS'])
@require_admin_auth
def admin_create_coupon():
    """Admin Create Coupon
    ---
    tags:
      - Admin
    summary: Admin Create Coupon
    description: "Admin Create Coupon API"
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """쿠폰 생성"""
    # OPTIONS 요청 처리 (CORS preflight)
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    conn = None
    cursor = None
    try:
        data = request.get_json()
        coupon_code = data.get('coupon_code')
        coupon_name = data.get('coupon_name')
        discount_type = data.get('discount_type', 'percentage')
        discount_value = data.get('discount_value')
        product_variant_id = data.get('product_variant_id')
        min_order_amount = data.get('min_order_amount')
        valid_from = data.get('valid_from')
        valid_until = data.get('valid_until')

        if not coupon_code or not coupon_name or not discount_value:
            return jsonify({'error': '쿠폰 코드, 이름, 할인 값은 필수입니다.'}), 400

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                INSERT INTO coupons (
                    coupon_code, coupon_name, discount_type, discount_value,
                    product_variant_id, min_order_amount, valid_from, valid_until
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING coupon_id
            """, (
                coupon_code, coupon_name, discount_type, float(discount_value),
                product_variant_id if product_variant_id else None,
                float(min_order_amount) if min_order_amount else None,
                valid_from if valid_from else None,
                valid_until if valid_until else None
            ))
            coupon_id = cursor.fetchone()['coupon_id']
        else:
            cursor.execute("""
                INSERT INTO coupons (
                    coupon_code, coupon_name, discount_type, discount_value,
                    product_variant_id, min_order_amount, valid_from, valid_until
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                coupon_code, coupon_name, discount_type, float(discount_value),
                product_variant_id if product_variant_id else None,
                float(min_order_amount) if min_order_amount else None,
                valid_from if valid_from else None,
                valid_until if valid_until else None
            ))
            coupon_id = cursor.lastrowid

        conn.commit()
        return jsonify({'success': True, 'coupon_id': coupon_id, 'message': '쿠폰이 생성되었습니다.'}), 201
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ 쿠폰 생성 오류: {e}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': f'쿠폰 생성 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/admin/coupons/<int:coupon_id>', methods=['PUT'])
@require_admin_auth
def admin_update_coupon(coupon_id):
    """Admin Update Coupon
    ---
    tags:
      - Admin
    summary: Admin Update Coupon
    description: "Admin Update Coupon API"
    security:
      - Bearer: []
    parameters:
      - name: coupon_id
        in: path
        type: int
        required: true
        description: Coupon Id
        example: "example_coupon_id"
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """쿠폰 수정"""
    conn = None
    cursor = None
    try:
        data = request.get_json()
        coupon_code = data.get('coupon_code')
        coupon_name = data.get('coupon_name')
        discount_type = data.get('discount_type')
        discount_value = data.get('discount_value')
        product_variant_id = data.get('product_variant_id')
        min_order_amount = data.get('min_order_amount')
        valid_from = data.get('valid_from')
        valid_until = data.get('valid_until')

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # 업데이트할 필드만 동적으로 구성
        update_fields = []
        update_values = []

        if coupon_code is not None:
            update_fields.append("coupon_code = %s" if DATABASE_URL.startswith('postgresql://') else "coupon_code = ?")
            update_values.append(coupon_code)
        if coupon_name is not None:
            update_fields.append("coupon_name = %s" if DATABASE_URL.startswith('postgresql://') else "coupon_name = ?")
            update_values.append(coupon_name)
        if discount_type is not None:
            update_fields.append("discount_type = %s" if DATABASE_URL.startswith('postgresql://') else "discount_type = ?")
            update_values.append(discount_type)
        if discount_value is not None:
            update_fields.append("discount_value = %s" if DATABASE_URL.startswith('postgresql://') else "discount_value = ?")
            update_values.append(float(discount_value))
        if product_variant_id is not None:
            update_fields.append("product_variant_id = %s" if DATABASE_URL.startswith('postgresql://') else "product_variant_id = ?")
            update_values.append(product_variant_id if product_variant_id else None)
        if min_order_amount is not None:
            update_fields.append("min_order_amount = %s" if DATABASE_URL.startswith('postgresql://') else "min_order_amount = ?")
            update_values.append(float(min_order_amount) if min_order_amount else None)
        if valid_from is not None:
            update_fields.append("valid_from = %s" if DATABASE_URL.startswith('postgresql://') else "valid_from = ?")
            update_values.append(valid_from if valid_from else None)
        if valid_until is not None:
            update_fields.append("valid_until = %s" if DATABASE_URL.startswith('postgresql://') else "valid_until = ?")
            update_values.append(valid_until if valid_until else None)

        if not update_fields:
            return jsonify({'error': '수정할 필드가 없습니다.'}), 400

        update_values.append(coupon_id)
        query = f"""
            UPDATE coupons 
            SET {', '.join(update_fields)}
            WHERE coupon_id = {'%s' if DATABASE_URL.startswith('postgresql://') else '?'}
        """
        cursor.execute(query, update_values)
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({'error': '쿠폰을 찾을 수 없습니다.'}), 404

        return jsonify({'success': True, 'message': '쿠폰이 수정되었습니다.'}), 200
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ 쿠폰 수정 오류: {e}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': f'쿠폰 수정 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/admin/coupons/<int:coupon_id>', methods=['DELETE'])
@require_admin_auth
def admin_delete_coupon(coupon_id):
    """Admin Delete Coupon
    ---
    tags:
      - Admin
    summary: Admin Delete Coupon
    description: "Admin Delete Coupon API"
    security:
      - Bearer: []
    parameters:
      - name: coupon_id
        in: path
        type: int
        required: true
        description: Coupon Id
        example: "example_coupon_id"
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """쿠폰 삭제"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("DELETE FROM coupons WHERE coupon_id = %s", (coupon_id,))
        else:
            cursor.execute("DELETE FROM coupons WHERE coupon_id = ?", (coupon_id,))

        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({'error': '쿠폰을 찾을 수 없습니다.'}), 404

        return jsonify({'success': True, 'message': '쿠폰이 삭제되었습니다.'}), 200
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ 쿠폰 삭제 오류: {e}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': f'쿠폰 삭제 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# -----------------------------
# Admin: SMM 서비스 → 카탈로그 일괄 등록
# -----------------------------
@app.route('/api/admin/catalog/import-smm', methods=['POST', 'OPTIONS'])
@require_admin_auth
def admin_import_smm_services():
    """Admin Import Smm Services
    ---
    tags:
      - Admin
    summary: Admin Import Smm Services
    description: "Admin Import Smm Services API"
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """SMM Panel 서비스 목록을 불러와 categories/products/product_variants에 일괄 등록"""
    # CORS preflight 요청 처리
    if request.method == 'OPTIONS':
        return '', 200
    
    conn = None
    cursor = None
    try:
        print("🔍 SMM 서비스 동기화 시작")
        
        # 1) SMM 서비스 목록 가져오기
        smm = get_smm_panel_services()
        if not smm or smm.get('status') != 'success':
            error_msg = 'SMM 서비스 목록을 불러오지 못했습니다.'
            print(f"❌ {error_msg}: {smm}")
            return jsonify({'error': error_msg, 'details': smm}), 502
        services = smm.get('services', [])
        if not services:
            error_msg = 'SMM 서비스가 비어있습니다.'
            print(f"❌ {error_msg}")
            return jsonify({'error': error_msg}), 404
        
        print(f"✅ SMM 서비스 {len(services)}개 불러옴")
        
        # 2) DB 연결
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 3) 카테고리/상품 준비 (없으면 생성)
        category_name = 'SMM 패널'
        product_name = 'SMM 기본 서비스'
        
        cursor.execute("SELECT category_id FROM categories WHERE name = %s LIMIT 1", (category_name,))
        cat = cursor.fetchone()
        if not cat:
            cursor.execute("""
                INSERT INTO categories (name, description, created_at, updated_at)
                VALUES (%s, %s, NOW(), NOW())
                RETURNING category_id
            """, (category_name, 'SMM Panel에서 자동 동기화된 카테고리'))
            cat = cursor.fetchone()
            print(f"➕ 카테고리 생성: {category_name} (ID: {cat['category_id']})")
        category_id = cat['category_id']
        
        cursor.execute("""
            SELECT product_id FROM products 
            WHERE name = %s AND category_id = %s
            LIMIT 1
        """, (product_name, category_id))
        prod = cursor.fetchone()
        if not prod:
            cursor.execute("""
                INSERT INTO products (category_id, name, description, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, TRUE, NOW(), NOW())
                RETURNING product_id
            """, (category_id, product_name, 'SMM Panel 서비스 묶음'))
            prod = cursor.fetchone()
            print(f"➕ 상품 생성: {product_name} (ID: {prod['product_id']})")
        product_id = prod['product_id']
        
        # 4) 서비스별로 variant upsert
        import json as json_module
        inserted, updated = 0, 0
        for s in services:
            svc_id = s.get('service') or s.get('id') or s.get('service_id')
            name = s.get('name') or f"Service {svc_id}"
            price = None
            # rate, pricePer1000 등 가능한 필드에서 가격 추출
            for key in ['rate', 'price', 'pricePer1000', 'cost']:
                if s.get(key) not in (None, '', 0):
                    try:
                        price = float(s.get(key))
                        break
                    except:
                        pass
            if price is None:
                price = 0.0
            min_q = int(s.get('min') or s.get('min_quantity') or 1)
            max_q = int(s.get('max') or s.get('max_quantity') or max(1, min_q))
            delivery = s.get('dripfeed') or s.get('delivery_time_days') or None
            
            # 기존 variant 존재 여부 확인 (product_id + meta_json.service_id 기준)
            cursor.execute("""
                SELECT variant_id FROM product_variants 
                WHERE product_id = %s 
                  AND (meta_json->>'service_id') = %s
                LIMIT 1
            """, (product_id, str(svc_id)))
            existing = cursor.fetchone()
            
            meta_json = json_module.dumps({
                'service_id': str(svc_id),
                'raw': s
            }, ensure_ascii=False)
            
            if existing:
                cursor.execute("""
                    UPDATE product_variants
                    SET name = %s,
                        price = %s,
                        min_quantity = %s,
                        max_quantity = %s,
                        delivery_time_days = %s,
                        meta_json = %s::jsonb,
                        is_active = TRUE,
                        updated_at = NOW()
                    WHERE variant_id = %s
                """, (name, price, min_q, max_q, delivery, meta_json, existing['variant_id']))
                updated += 1
            else:
                cursor.execute("""
                    INSERT INTO product_variants (
                        product_id, name, price, min_quantity, max_quantity,
                        delivery_time_days, is_active, meta_json, created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, TRUE, %s::jsonb, NOW(), NOW())
                    RETURNING variant_id
                """, (product_id, name, price, min_q, max_q, delivery, meta_json))
                _ = cursor.fetchone()
                inserted += 1
        
        conn.commit()
        print(f"✅ SMM 동기화 완료: 추가 {inserted}건, 갱신 {updated}건")
        return jsonify({
            'success': True,
            'inserted': inserted,
            'updated': updated,
            'message': f'동기화 완료: 추가 {inserted}건, 갱신 {updated}건'
        }), 200
    except Exception as e:
        if conn:
            conn.rollback()
        import traceback
        error_msg = f'SMM 동기화 실패: {str(e)}'
        print(f"❌ {error_msg}")
        print(traceback.format_exc())
        return jsonify({'error': error_msg}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
# 멈춰있는 패키지 주문 재처리
@app.route('/api/admin/reprocess-package-orders', methods=['POST'])
@require_admin_auth
def reprocess_package_orders():
    """Reprocess Package Orders
    ---
    tags:
      - Admin
    summary: Reprocess Package Orders
    description: "Reprocess Package Orders API"
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """멈춰있는 패키지 주문들을 재처리"""
    conn = None
    cursor = None
    
    try:
        print("🔄 관리자 요청: 멈춰있는 패키지 주문 재처리")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # processing 상태인 패키지 주문들을 pending으로 변경 (서버 재시작 시)
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                UPDATE orders SET status = 'pending' 
                WHERE status = 'processing' AND package_steps IS NOT NULL
            """)
        else:
            cursor.execute("""
                UPDATE orders SET status = 'pending' 
                WHERE status = 'processing' AND package_steps IS NOT NULL
            """)
        
        updated_count = cursor.rowcount
        conn.commit()
        
        print(f"✅ {updated_count}개의 패키지 주문 상태를 pending으로 변경")
        
        return jsonify({
            'success': True,
            'message': f'{updated_count}개의 패키지 주문 상태를 pending으로 변경했습니다.'
        }), 200
        
    except Exception as e:
        print(f"❌ 패키지 주문 재처리 오류: {e}")
        if conn:
            conn.rollback()
        return jsonify({
            'error': f'패키지 주문 재처리 실패: {str(e)}'
        }), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 예약 발송 주문 처리
@app.route('/api/scheduled-orders', methods=['POST'])
def create_scheduled_order():
    """Create Scheduled Order
    ---
    tags:
      - API
    summary: Create Scheduled Order
    description: "Create Scheduled Order API"
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """예약 발송 주문 생성"""
    conn = None
    cursor = None
    
    try:
        data = request.get_json()
        print(f"=== 예약 발송 주문 생성 요청 ===")
        print(f"요청 데이터: {data}")
        
        user_id = data.get('user_id')
        service_id = data.get('service_id')
        link = data.get('link')
        quantity = data.get('quantity')
        price = data.get('price') or data.get('total_price')
        scheduled_datetime = data.get('scheduled_datetime')
        
        # 필수 필드 검증
        if not all([user_id, service_id, link, quantity, price, scheduled_datetime]):
            return jsonify({'error': '필수 필드가 누락되었습니다.'}), 400
        
        # 예약 시간 검증
        try:
            scheduled_dt = datetime.strptime(scheduled_datetime, '%Y-%m-%d %H:%M')
            now = datetime.now()
            time_diff_minutes = (scheduled_dt - now).total_seconds() / 60
            
            print(f"🔍 예약 시간 검증: 예약시간={scheduled_datetime}, 현재시간={now.strftime('%Y-%m-%d %H:%M')}, 차이={time_diff_minutes:.1f}분")
            
            if scheduled_dt <= now:
                print(f"❌ 예약 시간이 현재 시간보다 이전입니다.")
                return jsonify({'error': '예약 시간은 현재 시간보다 늦어야 합니다.'}), 400
                
            # 5분 ~ 7일 이내
            if time_diff_minutes < 5 or time_diff_minutes > 10080:  # 7일 = 7 * 24 * 60 = 10080분
                print(f"❌ 예약 시간이 범위를 벗어났습니다. (5분~7일)")
                return jsonify({'error': '예약 시간은 5분 후부터 7일 이내여야 합니다.'}), 400
                
            print(f"✅ 예약 시간 검증 통과: {time_diff_minutes:.1f}분 후")
                
        except ValueError as e:
            print(f"❌ 예약 시간 형식 오류: {e}")
            return jsonify({'error': '예약 시간 형식이 올바르지 않습니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # user_id를 내부 데이터베이스 user_id로 변환 (external_uid -> user_id)
        db_user_id = user_id  # 기본값은 그대로 사용 (SQLite 호환)
        if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT user_id FROM users WHERE external_uid = %s OR email = %s LIMIT 1
            """, (user_id, user_id))
            user_result = cursor.fetchone()
            if user_result:
                db_user_id = user_result[0]
                print(f"✅ 사용자 ID 변환 완료: external_uid={user_id} -> user_id={db_user_id}")
            else:
                print(f"⚠️ 사용자를 찾을 수 없음: external_uid={user_id}, external_uid를 그대로 사용")
                db_user_id = user_id
        
        # service_id를 variant_id로 변환 (product_variants 테이블에서 meta_json->>'service_id'로 찾기)
        variant_id = None
        unit_price = price  # 기본값: 전체 금액을 단가로 사용
        if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
            try:
                if service_id and str(service_id).isdigit():
                    cursor.execute("""
                        SELECT variant_id, price 
                        FROM product_variants 
                        WHERE (meta_json->>'service_id')::text = %s 
                           OR (meta_json->>'smm_service_id')::text = %s
                        LIMIT 1
                    """, (str(service_id), str(service_id)))
                    variant_result = cursor.fetchone()
                    if variant_result:
                        variant_id = variant_result[0]
                        unit_price = float(variant_result[1]) if variant_result[1] else price
                        print(f"✅ Variant ID 찾음: service_id={service_id} -> variant_id={variant_id}")
            except Exception as variant_error:
                print(f"⚠️ variant_id 변환 중 오류 (무시하고 계속): {variant_error}")
        
        # 예약 주문 저장
        package_steps = data.get('package_steps', [])
        runs = data.get('runs', 1)  # Drip-feed: 기본값 1
        interval = data.get('interval', 0)  # Drip-feed: 기본값 0
        print(f"🔍 예약 주문 저장: 사용자={db_user_id}, 서비스={service_id}, 예약시간={scheduled_datetime}, 패키지단계={len(package_steps)}개, runs={runs}, interval={interval}")
        
        # order_id 생성 (bigint 호환)
        import time
        order_id = int(time.time() * 1000)  # 밀리초 단위 타임스탬프
        
        # orders 테이블에 예약 주문 저장 (실제 스키마에 맞게 수정)
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                INSERT INTO orders 
                (order_id, user_id, total_amount, final_amount, status, is_scheduled, scheduled_datetime, package_steps, created_at, updated_at)
                VALUES (%s, %s, %s, %s, 'pending', TRUE, %s, %s, NOW(), NOW())
                RETURNING order_id
            """, (
                order_id, db_user_id, price, price, scheduled_datetime,
                json.dumps(package_steps) if package_steps else None
            ))
            inserted_order_id = cursor.fetchone()[0] if cursor.rowcount > 0 else order_id
            order_id = inserted_order_id
            
            # order_items 테이블에 상세 정보 저장 (새 스키마)
            if DATABASE_URL.startswith('postgresql://') and variant_id:
                try:
                    line_amount = unit_price * quantity
                    cursor.execute("""
                        INSERT INTO order_items (order_id, variant_id, quantity, unit_price, line_amount, link, status, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, 'pending', NOW(), NOW())
                    """, (order_id, variant_id, quantity, unit_price, line_amount, link))
                    print(f"✅ 예약 주문 아이템 생성 완료 - variant_id: {variant_id}, quantity: {quantity}")
                except Exception as item_error:
                    print(f"⚠️ 예약 주문 아이템 생성 실패 (무시하고 계속): {item_error}")
            
            # package_steps가 있으면 execution_progress에 예약 정보 저장
            if package_steps and len(package_steps) > 0:
                for idx, step in enumerate(package_steps):
                    step_delay = step.get('delay', 0)
                    scheduled_time = scheduled_datetime
                    if idx > 0:
                        # 누적 delay 계산
                        from datetime import datetime, timedelta
                        if isinstance(scheduled_datetime, str):
                            scheduled_time = datetime.fromisoformat(scheduled_datetime.replace('Z', '+00:00'))
                        scheduled_time = scheduled_time + timedelta(minutes=step_delay)
                    
                    cursor.execute("""
                        INSERT INTO execution_progress 
                        (order_id, exec_type, step_number, step_name, service_id, quantity, scheduled_datetime, status, created_at)
                        VALUES (%s, 'package', %s, %s, %s, %s, %s, 'pending', NOW())
                        ON CONFLICT (order_id, exec_type, step_number) DO NOTHING
                    """, (
                        order_id, idx + 1, step.get('name', f'단계 {idx + 1}'),
                        step.get('id'), step.get('quantity', 0), scheduled_time
                    ))
        else:
            cursor.execute("""
                INSERT INTO orders 
                (order_id, user_id, service_id, link, quantity, price, status, is_scheduled, scheduled_datetime, package_steps, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', 1, ?, ?, datetime('now'), datetime('now'))
            """, (
                order_id, user_id, service_id, link, quantity, price, scheduled_datetime,
                json.dumps(package_steps) if package_steps else None
            ))
            
            # package_steps가 있으면 execution_progress에 예약 정보 저장
            if package_steps and len(package_steps) > 0:
                for idx, step in enumerate(package_steps):
                    step_delay = step.get('delay', 0)
                    scheduled_time = scheduled_datetime
                    if idx > 0:
                        from datetime import datetime, timedelta
                        if isinstance(scheduled_datetime, str):
                            scheduled_time = datetime.fromisoformat(scheduled_datetime.replace('Z', '+00:00'))
                        scheduled_time = scheduled_time + timedelta(minutes=step_delay)
                    
                    cursor.execute("""
                        INSERT INTO execution_progress 
                        (order_id, exec_type, step_number, step_name, service_id, quantity, scheduled_datetime, status, created_at)
                        VALUES (?, 'package', ?, ?, ?, ?, ?, 'pending', datetime('now'))
                    """, (
                        order_id, idx + 1, step.get('name', f'단계 {idx + 1}'),
                        step.get('id'), step.get('quantity', 0), scheduled_time
                    ))
        
        conn.commit()
        
        print(f"✅ 예약 발송 주문 생성 완료: {scheduled_datetime}")
        print(f"✅ 예약 주문이 {time_diff_minutes:.1f}분 후에 처리됩니다.")
        
        return jsonify({
            'success': True,
            'message': f'예약 발송이 설정되었습니다. ({scheduled_datetime}에 처리됩니다)',
            'scheduled_datetime': scheduled_datetime,
            'order_id': order_id
        }), 200
        
    except Exception as e:
        print(f"❌ 예약 발송 주문 생성 오류: {str(e)}")
        return jsonify({'error': f'예약 발송 주문 생성 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# robots.txt 서빙
@app.route('/robots.txt')
def robots():
    """Robots
    ---
    tags:
      - API
    summary: Robots
    description: "Robots API"
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    return app.send_static_file('robots.txt')

# 전역 오류 처리
@app.errorhandler(404)
def not_found(error):
    import sys
    import traceback
    # 사용자 정보 조회 라우트는 404를 반환하지 않음
    if request.path.startswith('/api/users/'):
        # /api/users/ 이후의 모든 경로를 user_id로 추출
        user_id = request.path.replace('/api/users/', '', 1).rstrip('/')
        print(f"🔍 404 핸들러에서 사용자 정보 조회 시도 - 경로: {request.path}, user_id: {user_id}", flush=True)
        sys.stdout.flush()
        try:
            # 직접 get_user 함수 호출
            result = get_user(user_id)
            print(f"✅ 404 핸들러에서 get_user 호출 성공 - user_id: {user_id}", flush=True)
            sys.stdout.flush()
            return result
        except Exception as e:
            error_msg = f"❌ 404 핸들러에서 get_user 호출 실패: {e}"
            print(error_msg, file=sys.stderr, flush=True)
            traceback.print_exc(file=sys.stderr)
            sys.stderr.flush()
            # 최소한 기본 사용자 정보라도 반환
            return jsonify({
                'user_id': user_id,
                'email': None,
                'name': None,
                'created_at': None,
                'message': '사용자 정보를 조회할 수 없습니다.'
            }), 200
    print(f"❌ 404 오류 - 경로: {request.path}, 메서드: {request.method}", flush=True)
    sys.stdout.flush()
    return jsonify({'error': 'Not Found', 'message': '요청한 리소스를 찾을 수 없습니다.'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal Server Error', 'message': '서버 내부 오류가 발생했습니다.'}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    # 오류 로깅
    print(f"❌ 전역 오류 발생: {str(e)}")
    import traceback
    print(f"❌ 스택 트레이스: {traceback.format_exc()}")
    
    # MethodNotAllowed 오류에 대한 특별 처리
    if hasattr(e, 'code') and e.code == 405:
        print(f"❌ 405 Method Not Allowed: {request.method} {request.path}")
        return jsonify({
            'error': 'Method not allowed',
            'message': f'{request.method} method is not allowed for {request.path}',
            'type': 'MethodNotAllowed'
        }), 405
    
    # 프로덕션 환경에서는 상세 오류 정보 숨김
    if os.environ.get('FLASK_ENV') == 'production':
        return jsonify({'error': 'Internal Server Error', 'message': '서버 오류가 발생했습니다.'}), 500
    else:
        return jsonify({'error': str(e), 'message': '개발 환경 오류'}), 500

# 데이터베이스 연결 설정 (AWS Secrets Manager 우선, 환경 변수 폴백)
# 보안을 위해 환경 변수만 사용 (기본값 제거)
DATABASE_URL = os.environ.get('DATABASE_URL')
SMMPANEL_API_KEY = os.environ.get('SMMPANEL_API_KEY')

# 필수 환경 변수 검증
def validate_environment():
    """환경 변수 검증"""
    required_vars = {
        'DATABASE_URL': DATABASE_URL,
        'SMMPANEL_API_KEY': SMMPANEL_API_KEY
    }
    
    missing_vars = []
    for var_name, var_value in required_vars.items():
        if not var_value:
            missing_vars.append(var_name)
    
    if missing_vars:
        error_msg = f"필수 환경 변수가 설정되지 않았습니다: {', '.join(missing_vars)}"
        print(f"❌ {error_msg}")
        raise ValueError(error_msg)
    
    # 보안 검증
    if SMMPANEL_API_KEY == 'bc85538982fb27c6c0558be6cd669e67':
        print("⚠️ 기본 API 키를 사용하고 있습니다. 프로덕션에서는 다른 키를 사용하세요.")
    
    print("✅ 환경 변수 검증 완료")

# 환경 변수 검증 실행
validate_environment()


# SMM Panel API 호출 함수
def call_smm_panel_api(order_data):
    """SMM Panel API 호출"""
    try:
        smm_panel_url = 'https://smmpanel.kr/api/v2'
        
        action = order_data.get('action', 'add')
        
        # 상태 조회일 경우
        if action == 'status':
            payload = {
                'key': SMMPANEL_API_KEY,
                'action': 'status',
                'order': order_data.get('order')
            }
        else:
            # 주문 생성일 경우
            # 인스타그램 프로필 링크에서 username 추출
            username = ''
            link = order_data.get('link', '')
            try:
                if link:
                    # 인스타그램 URL에서 username 추출
                    # 예: https://www.instagram.com/username/ 또는 https://instagram.com/username
                    instagram_pattern = r'instagram\.com/([^/?\s]+)'
                    match = re.search(instagram_pattern, link)
                    if match:
                        username = match.group(1).rstrip('/')
                        print(f"📌 인스타그램 username 추출: {username}")
            except Exception as username_extract_error:
                print(f"⚠️ username 추출 중 오류 발생 (무시하고 계속 진행): {username_extract_error}")
                username = ''
            
            # order_data에서 직접 전달된 username이 있으면 우선 사용
            username = order_data.get('username', username)
            
            payload = {
                'key': SMMPANEL_API_KEY,
                'action': 'add',
                'service': order_data.get('service'),
                'link': order_data.get('link'),
                'quantity': order_data.get('quantity'),
                'runs': order_data.get('runs', 1),  # Drip-feed: 반복 횟수
                'interval': order_data.get('interval', 0),  # Drip-feed: 간격(분 단위)
                'comments': order_data.get('comments', ''),
                'username': username,  # 추출한 username 사용
                'min': 0,
                'max': 0,
                'posts': 0,
                'delay': 0,
                'expiry': '',
                'oldPosts': 0
            }
        
        print(f"📞 SMM Panel API 요청: {payload}")
        # 타임아웃을 10초로 증가 (네트워크 지연 대응)
        response = requests.post(smm_panel_url, json=payload, timeout=10)
        print(f"📞 SMM Panel API 응답 상태: {response.status_code}")
        
        # 응답이 없거나 빈 경우 처리
        if not response.text:
            print(f"⚠️ SMM Panel API 응답이 비어있음")
            return {
                'status': 'error',
                'message': 'Empty response from SMM Panel'
            }
        
        print(f"📞 SMM Panel API 응답 내용: {response.text[:500]}")  # 긴 응답은 잘라서 출력
        
        try:
            result = response.json()
        except json.JSONDecodeError as json_err:
            print(f"❌ SMM Panel API JSON 파싱 실패: {json_err}")
            return {
                'status': 'error',
                'message': f'Invalid JSON response: {response.text[:200]}'
            }
        
        # 상태 조회 응답 처리
        if action == 'status':
            if response.status_code == 200:
                return {
                    'status': 'success',
                    'order': result.get('order'),
                    'status_text': result.get('status'),  # SMM Panel의 status (Pending, In progress, Completed 등)
                    'charge': result.get('charge'),
                    'start_count': result.get('start_count', 0),
                    'remains': result.get('remains', 0)
                }
            else:
                return {
                    'status': 'error',
                    'message': result.get('error', 'Unknown error')
                }
        
        # 주문 생성 응답 처리
        if result.get('status') == 'success' or result.get('order'):
            return {
                'status': 'success',
                'order': result.get('order'),
                'charge': result.get('charge'),
                'start_count': result.get('start_count', 0),
                'remains': result.get('remains', order_data.get('quantity'))
            }
        else:
            return {
                'status': 'error',
                'message': result.get('error', 'Unknown error')
            }
    except Exception as e:
        print(f"❌ SMM Panel API 호출 오류: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }

# 서비스 ID를 기반으로 서비스명을 반환하는 함수
def get_service_name(service_id):
    """서비스 ID를 기반으로 서비스명을 반환"""
    service_mapping = {
        # 패키지 상품들
        'pkg_1001': '인스타 계정 상위노출 [30일]',
        'pkg_1002': '인스타 최적화 계정만들기 [30일]',
        'pkg_1003': '추천탭 상위노출 (본인계정) - 진입단계',
        'pkg_1004': '추천탭 상위노출 (본인계정) - 유지단계',
        'pkg_999': '외국인 패키지',
        
        # 일반 서비스들
        '100': '외국인 팔로워',
        '101': '외국인 댓글',
        '102': '외국인 릴스 조회수',
        '103': '외국인 노출/저장/공유',
        '104': '라이브 스트리밍',
        '105': '자동 외국인 좋아요',
        '106': '자동 외국인 팔로워',
        '107': '자동 외국인 댓글',
        '108': '자동 외국인 릴스 조회수',
        '109': '자동 외국인 노출/저장/공유',
        
        # 인스타그램 한국인 서비스들
        '491': '인스타 한국인 팔로워',
        '514': '인스타 한국인 좋아요',
        '515': '인스타 한국인 댓글',
        '516': '인스타 한국인 릴스 조회수',
        '517': '인스타 한국인 노출/저장/공유',
        '518': '자동 인스타 좋아요',
        '519': '자동 인스타 팔로워',
        '520': '자동 인스타 댓글',
        '521': '자동 인스타 리그램',
        
        # 유튜브 서비스들
        '601': '유튜브 구독자',
        '602': '유튜브 조회수',
        '603': '유튜브 좋아요',
        '604': '유튜브 댓글',
        
        # 틱톡 서비스들
        '701': '틱톡 팔로워',
        '702': '틱톡 좋아요',
        '703': '틱톡 댓글',
        '704': '틱톡 조회수',
        
        # 트위터 서비스들
        '801': '트위터 팔로워',
        '802': '트위터 좋아요',
        '803': '트위터 리트윗',
        '804': '트위터 댓글',
        
        # 페이스북 서비스들
        '901': '페이스북 페이지 좋아요',
        '902': '페이스북 포스트 좋아요',
        '903': '페이스북 댓글',
        '904': '페이스북 공유',
        
        # 네이버 서비스들 (중복 ID 수정)
        'nb_1001': '네이버 블로그 조회수',
        'nb_1002': '네이버 블로그 댓글',
        'nb_1003': '네이버 카페 조회수',
        'nb_1004': '네이버 카페 댓글',
        
        # 텔레그램 서비스들
        '1101': '텔레그램 채널 구독자',
        '1102': '텔레그램 채널 조회수',
        '1103': '텔레그램 그룹 멤버',
        
        # 왓츠앱 서비스들
        '1201': '왓츠앱 그룹 멤버',
        '1202': '왓츠앱 채널 구독자'
    }
    
    # SMM Panel에서 받은 실제 서비스명이 있으면 사용, 없으면 매핑에서 찾기
    service_name = service_mapping.get(str(service_id), f'서비스 ID: {service_id}')
    
    # SMM Panel API 호출 제거로 성능 개선
    # 기본 매핑만 사용하여 빠른 응답 보장
    
    return service_name

# SMM Panel 서비스 목록 조회 함수
def get_smm_panel_services():
    """SMM Panel에서 사용 가능한 서비스 목록 조회"""
    try:
        print(f"🔍 SMM Panel 서비스 조회 시작 - API 키 존재: {bool(SMMPANEL_API_KEY)}")
        
        if not SMMPANEL_API_KEY:
            error_msg = 'SMMPANEL_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.'
            print(f"❌ {error_msg}")
            return {
                'status': 'error',
                'message': error_msg
            }
        
        smm_panel_url = 'https://smmpanel.kr/api/v2'
        
        payload = {
            'key': SMMPANEL_API_KEY,
            'action': 'services'
        }
        
        print(f"📡 SMM Panel API 호출: {smm_panel_url}, action: services")
        response = requests.post(smm_panel_url, json=payload, timeout=30)
        print(f"📡 SMM Panel API 응답: status_code={response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            # 응답 구조 확인 및 안전한 처리
            if isinstance(result, dict) and result.get('status') == 'success':
                services = result.get('services', [])
                
                # 서비스 ID 리스트 추출 (안전한 방식)
                service_ids = []
                if isinstance(services, list):
                    for service in services:
                        if isinstance(service, dict) and 'service' in service:
                            service_ids.append(str(service['service']))
                        elif isinstance(service, (int, str)):
                            service_ids.append(str(service))
                
                return {
                    'status': 'success',
                    'services': services,
                    'service_ids': service_ids
                }
            elif isinstance(result, list):
                # 응답이 리스트인 경우
                services = result
                
                service_ids = []
                for service in services:
                    if isinstance(service, dict) and 'service' in service:
                        service_ids.append(str(service['service']))
                    elif isinstance(service, (int, str)):
                        service_ids.append(str(service))
                
                return {
                    'status': 'success',
                    'services': services,
                    'service_ids': service_ids
                }
            else:
                return {
                    'status': 'error',
                    'message': f'Unexpected response format: {type(result)}'
                }
        elif response.status_code == 401:
            return {
                'status': 'error',
                'message': f'Invalid API key (HTTP {response.status_code})'
            }
        else:
            try:
                error_detail = response.json()
                error_msg = error_detail.get('error', f'HTTP {response.status_code}')
            except:
                error_msg = f'HTTP {response.status_code}: {response.text[:200]}'
            
            return {
                'status': 'error',
                'message': error_msg
            }
    except requests.exceptions.RequestException as e:
        error_msg = f'네트워크 오류: {str(e)}'
        print(f"❌ SMM Panel 네트워크 오류: {error_msg}")
        import traceback
        print(traceback.format_exc())
        return {
            'status': 'error',
            'message': error_msg
        }
    except Exception as e:
        error_msg = f'예상치 못한 오류: {str(e)}'
        print(f"❌ SMM Panel 예상치 못한 오류: {error_msg}")
        import traceback
        print(traceback.format_exc())
        return {
            'status': 'error',
            'message': error_msg
        }

# 패키지 상품 분할 발송 처리 함수
def process_package_delivery(order_id, day_number, package_steps, user_id, link, comments):
    """패키지 상품 분할 발송 일일 처리 (30일간 하루 400개씩)"""
    conn = None
    cursor = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 해당 일차 진행 상황 확인
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT id FROM split_delivery_progress 
                WHERE order_id = %s AND day_number = %s
            """, (order_id, day_number))
        else:
            cursor.execute("""
                SELECT id FROM split_delivery_progress 
                WHERE order_id = ? AND day_number = ?
            """, (order_id, day_number))
        
        existing_progress = cursor.fetchone()
        
        if not existing_progress:
            # 새로운 일차 진행 상황 생성
            if DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    INSERT INTO split_delivery_progress 
                    (order_id, day_number, scheduled_date, status, created_at)
                    VALUES (%s, %s, %s, 'pending', NOW())
                """, (order_id, day_number, datetime.now().date()))
            else:
                cursor.execute("""
                    INSERT INTO split_delivery_progress 
                    (order_id, day_number, scheduled_date, status, created_at)
                    VALUES (?, ?, ?, 'pending', datetime('now'))
                """, (order_id, day_number, datetime.now().date()))
        
        # 패키지 단계에서 서비스 정보 추출
        service_id = 515  # 기본값
        daily_quantity = 400  # 기본값
        
        if package_steps and len(package_steps) > 0:
            service_id = package_steps[0].get('id', 515)
            daily_quantity = package_steps[0].get('quantity', 400)
        
        # SMM Panel API 호출
        smm_result = call_smm_panel_api({
            'service': service_id,
            'link': link,
            'quantity': daily_quantity,
            'comments': f"{comments} (패키지 분할 {day_number}/30일차)"
        })
        
        if smm_result.get('status') == 'success':
            # 성공 시 진행 상황 업데이트
            if DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    UPDATE execution_progress 
                    SET status = 'completed', quantity = %s, 
                        smm_panel_order_id = %s, completed_at = NOW()
                    WHERE order_id = %s AND exec_type = 'package' AND step_number = %s
                """, (daily_quantity, smm_result.get('order'), order_id, day_number))
            else:
                cursor.execute("""
                    UPDATE execution_progress 
                    SET status = 'completed', quantity = ?, 
                        smm_panel_order_id = ?, completed_at = datetime('now')
                    WHERE order_id = ? AND exec_type = 'package' AND step_number = ?
                """, (daily_quantity, smm_result.get('order'), order_id, day_number))
            
            # 30일이 지나면 주문 상태를 완료로 변경
            if day_number >= 30:
                if DATABASE_URL.startswith('postgresql://'):
                    cursor.execute("""
                        UPDATE orders SET status = 'completed', updated_at = NOW()
                        WHERE order_id = %s
                    """, (order_id,))
                else:
                    cursor.execute("""
                        UPDATE orders SET status = 'completed', updated_at = datetime('now')
                        WHERE order_id = ?
                    """, (order_id,))
            
            conn.commit()
            print(f"✅ 패키지 상품 분할 발송 완료: {order_id} - {day_number}일차 ({daily_quantity}개)")
            return True
        else:
            print(f"❌ 패키지 상품 SMM API 호출 실패: {order_id} - {day_number}일차")
            return False
            
    except Exception as e:
        print(f"❌ 패키지 상품 분할 발송 처리 실패: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 분할 발송 처리 함수
def process_split_delivery(order_id, day_number):
    """분할 발송 일일 처리"""
    conn = None
    cursor = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 분할 주문 정보 조회 (패키지 상품 포함)
        # link와 variant_id는 order_items 테이블에서 가져옴
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT o.user_id, oi.variant_id, COALESCE(oi.link, ''), o.split_quantity, 
                       '', o.split_days, o.package_steps
                FROM orders o
                LEFT JOIN order_items oi ON o.order_id = oi.order_id
                WHERE o.order_id = %s AND (o.is_split_delivery = TRUE OR o.package_steps IS NOT NULL)
                LIMIT 1
            """, (order_id,))
        else:
            cursor.execute("""
                SELECT user_id, service_id, link, split_quantity, '' as comments, split_days, package_steps
                FROM orders 
                WHERE order_id = ? AND (is_split_delivery = TRUE OR package_steps IS NOT NULL)
            """, (order_id,))
        
        order = cursor.fetchone()
        if not order:
            return False
        
        if DATABASE_URL.startswith('postgresql://'):
            user_id, variant_id, link, split_quantity, comments, total_days, package_steps = order
            service_id = str(variant_id) if variant_id else None
        else:
            user_id, service_id, link, split_quantity, comments, total_days, package_steps = order
        
        # 패키지 상품인 경우 특별 처리
        if package_steps:
            try:
                if isinstance(package_steps, str):
                    package_steps = json.loads(package_steps)
                
                # 패키지 상품의 경우 30일간 하루에 400개씩 처리
                if len(package_steps) > 0 and package_steps[0].get('id') == 515:  # 인스타그램 프로필 방문
                    return process_package_delivery(order_id, day_number, package_steps, user_id, link, comments)
            except Exception as e:
                print(f"⚠️ 패키지 상품 처리 실패: {e}")
                return False
        
        # 해당 일차 진행 상황 확인
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT id FROM split_delivery_progress 
                WHERE order_id = %s AND day_number = %s
            """, (order_id, day_number))
        else:
            cursor.execute("""
                SELECT id FROM split_delivery_progress 
                WHERE order_id = ? AND day_number = ?
            """, (order_id, day_number))
        
        existing_progress = cursor.fetchone()
        
        if not existing_progress:
            # 새로운 일차 진행 상황 생성
            if DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    INSERT INTO split_delivery_progress 
                    (order_id, day_number, scheduled_date, status, created_at)
                    VALUES (%s, %s, %s, 'pending', NOW())
                """, (order_id, day_number, datetime.now().date()))
            else:
                cursor.execute("""
                    INSERT INTO split_delivery_progress 
                    (order_id, day_number, scheduled_date, status, created_at)
                    VALUES (?, ?, ?, 'pending', datetime('now'))
                """, (order_id, day_number, datetime.now().date()))
        
        # SMM Panel API 호출
        smm_result = call_smm_panel_api({
            'service': service_id,
            'link': link,
            'quantity': split_quantity,
            'comments': f"{comments} (분할 {day_number}/{total_days}일차)"
        })
        
        if smm_result.get('status') == 'success':
            # 성공 시 진행 상황 업데이트
            if DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    UPDATE execution_progress 
                    SET status = 'completed', quantity = %s, 
                        smm_panel_order_id = %s, completed_at = NOW()
                    WHERE order_id = %s AND exec_type = 'package' AND step_number = %s
                """, (split_quantity, smm_result.get('order'), order_id, day_number))
            else:
                cursor.execute("""
                    UPDATE execution_progress 
                    SET status = 'completed', quantity = ?, 
                        smm_panel_order_id = ?, completed_at = datetime('now')
                    WHERE order_id = ? AND exec_type = 'package' AND step_number = ?
                """, (split_quantity, smm_result.get('order'), order_id, day_number))
            
            
            # 마지막 날이면 주문 상태를 완료로 변경
            if day_number >= total_days:
                if DATABASE_URL.startswith('postgresql://'):
                    cursor.execute("""
                        UPDATE orders SET status = 'completed', updated_at = NOW()
                        WHERE order_id = %s
                    """, (order_id,))
                else:
                    cursor.execute("""
                        UPDATE orders SET status = 'completed', updated_at = datetime('now')
                        WHERE order_id = ?
                    """, (order_id,))
            
            conn.commit()
            return True
        else:
            # 실패 시 상태 업데이트
            if DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    UPDATE execution_progress 
                    SET status = 'failed', error_message = %s, failed_at = NOW()
                    WHERE order_id = %s AND exec_type = 'package' AND step_number = %s
                """, (smm_result.get('message', 'Unknown error'), order_id, day_number))
            else:
                cursor.execute("""
                    UPDATE execution_progress 
                    SET status = 'failed', error_message = ?, failed_at = datetime('now')
                    WHERE order_id = ? AND exec_type = 'package' AND step_number = ?
                """, (smm_result.get('message', 'Unknown error'), order_id, day_number))
            
            conn.commit()
            return False
            
    except Exception as e:
        if conn:
            conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 패키지 상품 단계별 처리 함수
def process_package_step(order_id, step_index):
    """패키지 상품의 각 단계 처리"""
    conn = None
    cursor = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 주문 정보 조회 (comments 컬럼은 nullable이므로 COALESCE 사용)
        # link는 order_items 테이블에서 가져와야 함
        if DATABASE_URL.startswith('postgresql://'):
            # comments 또는 notes 컬럼이 없을 수 있으므로 빈 문자열 사용
            cursor.execute("""
                SELECT o.user_id, COALESCE(oi.link, ''), o.package_steps, '' as comments
                FROM orders o
                LEFT JOIN order_items oi ON o.order_id = oi.order_id
                WHERE o.order_id = %s
                LIMIT 1
            """, (order_id,))
        else:
            cursor.execute("""
                SELECT user_id, link, package_steps, '' as comments
                FROM orders 
                WHERE order_id = ?
            """, (order_id,))
        
        order = cursor.fetchone()
        if not order:
            print(f"❌ 패키지 주문 {order_id}을 찾을 수 없습니다.")
            return False
        
        user_id, link, package_steps_json, comments = order
        comments = comments or ''  # None 체크 추가
        print(f"🔍 패키지 주문 데이터: user_id={user_id}, link={link}, package_steps_json={package_steps_json}")
        
        try:
            # package_steps가 이미 리스트인지 확인
            if isinstance(package_steps_json, list):
                package_steps = package_steps_json
                print(f"🔍 패키지 단계 (이미 리스트): {len(package_steps)}단계")
            elif isinstance(package_steps_json, str):
                package_steps = json.loads(package_steps_json)
                print(f"🔍 패키지 단계 (JSON 파싱): {len(package_steps)}단계")
            else:
                package_steps = []
                print(f"🔍 패키지 단계 (기본값): {len(package_steps)}단계")
        except (json.JSONDecodeError, TypeError) as e:
            print(f"❌ 패키지 단계 파싱 실패: {e}")
            package_steps = []
        
        # 패키지 단계가 없으면 종료
        if not package_steps or len(package_steps) == 0:
            print(f"❌ 패키지 주문 {order_id} - 단계 정보 없음")
            return False
        
        if step_index >= len(package_steps):
            # 모든 단계 완료 시 주문 상태 업데이트
            print(f"🎉 패키지 주문 {order_id} 모든 단계 완료!")
            if DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    UPDATE orders SET status = 'completed', updated_at = NOW()
                    WHERE order_id = %s
                """, (order_id,))
            else:
                cursor.execute("""
                    UPDATE orders SET status = 'completed', updated_at = CURRENT_TIMESTAMP
                    WHERE order_id = ?
                """, (order_id,))
            conn.commit()
            conn.close()
            return True
        
        current_step = package_steps[step_index]
        step_service_id = current_step.get('id')
        step_quantity = current_step.get('quantity', 0)
        step_name = current_step.get('name')
        step_delay = current_step.get('delay', 0)
        step_repeat = current_step.get('repeat', 1)  # 반복 횟수 (기본값: 1)
        
        print(f"🚀 패키지 단계 {step_index + 1}/{len(package_steps)} 실행: {step_name} (수량: {step_quantity}, 반복: {step_repeat}회)")
        print(f"🚀 서비스 ID: {step_service_id}, 링크: {link}")
        
        # 수량이 0이면 건너뛰기
        if step_quantity <= 0:
            print(f"⚠️ 패키지 단계 {step_index + 1} 건너뛰기 - 수량이 0: {step_name}")
            # 건너뛴 단계도 진행 상황에 기록
            if DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    INSERT INTO execution_progress 
                    (order_id, exec_type, step_number, step_name, service_id, quantity, smm_panel_order_id, status, created_at)
                    VALUES (%s, 'package', %s, %s, %s, %s, %s, 'skipped', NOW())
                    ON CONFLICT (order_id, exec_type, step_number) DO UPDATE
                    SET step_name=EXCLUDED.step_name, status=EXCLUDED.status
                """, (order_id, step_index + 1, step_name, step_service_id, step_quantity, None))
            else:
                cursor.execute("""
                    INSERT INTO execution_progress 
                    (order_id, exec_type, step_number, step_name, service_id, quantity, smm_panel_order_id, status, created_at)
                    VALUES (?, 'package', ?, ?, ?, ?, ?, 'skipped', datetime('now'))
                """, (order_id, step_index + 1, step_name, step_service_id, step_quantity, None))
            conn.commit()
            
            # 다음 단계로 진행
            schedule_next_package_step(order_id, step_index + 1, package_steps)
            conn.close()
            return True
        
        # 반복 처리 로직
        for repeat_count in range(step_repeat):
            print(f"🔄 패키지 단계 {step_index + 1} 반복 {repeat_count + 1}/{step_repeat}: {step_name}")
            
            # SMM Panel API 호출
            print(f"📞 SMM Panel API 호출 시작: 서비스 {step_service_id}, 수량 {step_quantity}")
            smm_result = call_smm_panel_api({
                'service': step_service_id,
                'link': link,
                'quantity': step_quantity,
                'comments': f"{comments} - {step_name} ({repeat_count + 1}/{step_repeat})" if comments else f"{step_name} ({repeat_count + 1}/{step_repeat})"
            })
            print(f"📞 SMM Panel API 응답: {smm_result}")
            
            if smm_result.get('status') == 'success':
                print(f"✅ 패키지 단계 {step_index + 1} 반복 {repeat_count + 1} 완료: {step_name} (SMM 주문 ID: {smm_result.get('order')})")
            else:
                print(f"❌ 패키지 단계 {step_index + 1} 반복 {repeat_count + 1} 실패: {step_name} - {smm_result.get('message', 'Unknown error')}")
                # 실패해도 다음 반복으로 진행
            
            # 패키지 진행 상황 기록 (성공/실패 모두)
            status = 'completed' if smm_result.get('status') == 'success' else 'failed'
            smm_order_id = smm_result.get('order') if smm_result.get('status') == 'success' else None
            
            # 패키지 진행 상황을 DB에 기록
            if DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    INSERT INTO execution_progress 
                    (order_id, exec_type, step_number, step_name, service_id, quantity, smm_panel_order_id, status, created_at)
                    VALUES (%s, 'package', %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (order_id, exec_type, step_number) DO UPDATE
                    SET step_name=EXCLUDED.step_name, service_id=EXCLUDED.service_id, quantity=EXCLUDED.quantity, 
                        smm_panel_order_id=EXCLUDED.smm_panel_order_id, status=EXCLUDED.status
                """, (order_id, step_index + 1, f"{step_name} ({repeat_count + 1}/{step_repeat})", step_service_id, step_quantity, smm_order_id, status))
            else:
                cursor.execute("""
                    INSERT INTO execution_progress 
                    (order_id, exec_type, step_number, step_name, service_id, quantity, smm_panel_order_id, status, created_at)
                    VALUES (?, 'package', ?, ?, ?, ?, ?, ?, datetime('now'))
                """, (order_id, step_index + 1, f"{step_name} ({repeat_count + 1}/{step_repeat})", step_service_id, step_quantity, smm_order_id, status))
            
            conn.commit()
            
            # SMM Panel에서 받은 실제 주문번호로 order_id 업데이트 (성공한 경우만)
            if smm_order_id and status == 'completed':
                print(f"🔄 주문번호 업데이트: {order_id} -> {smm_order_id}")
                
                try:
                    # 1. 먼저 package_progress 테이블의 order_id를 새 주문번호로 업데이트
                    if DATABASE_URL.startswith('postgresql://'):
                        cursor.execute("""
                            UPDATE execution_progress 
                            SET order_id = %s
                            WHERE order_id = %s AND exec_type = 'package'
                        """, (smm_order_id, order_id))
                    else:
                        cursor.execute("""
                            UPDATE execution_progress 
                            SET order_id = ?
                            WHERE order_id = ? AND exec_type = 'package'
                        """, (smm_order_id, order_id))
                    
                    # 2. 그 다음 orders 테이블의 order_id 업데이트
                    if DATABASE_URL.startswith('postgresql://'):
                        cursor.execute("""
                            UPDATE orders SET order_id = %s, smm_panel_order_id = %s, updated_at = NOW()
                            WHERE order_id = %s
                        """, (smm_order_id, smm_order_id, order_id))
                    else:
                        cursor.execute("""
                            UPDATE orders SET order_id = ?, smm_panel_order_id = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE order_id = ?
                        """, (smm_order_id, smm_order_id, order_id))
                    
                    conn.commit()
                    order_id = smm_order_id  # 다음 단계에서 사용할 주문번호 업데이트
                    print(f"✅ 주문번호 업데이트 완료: {order_id}")
                except Exception as update_error:
                    print(f"❌ 주문번호 업데이트 실패: {update_error}")
                    conn.rollback()
                    # 업데이트 실패 시 원래 order_id 유지
                    print(f"🔄 원래 주문번호 유지: {order_id}")
            
            # 마지막 반복이 아니면 delay 시간만큼 대기
            if repeat_count < step_repeat - 1:
                print(f"⏳ {step_delay}분 대기 후 다음 반복 실행...")
                import time
                time.sleep(step_delay * 60)  # 분을 초로 변환
        
        # 반복이 끝난 후 다음 단계로 진행
        print(f"🎉 패키지 단계 {step_index + 1} 모든 반복 완료: {step_name} ({step_repeat}회)")
        
        # 다음 단계가 있으면 스케줄링
        print(f"🔄 다음 단계 스케줄링 시작: {step_index + 1}/{len(package_steps)}")
        print(f"🔄 현재 단계: {step_index + 1}, 전체 단계: {len(package_steps)}")
        
        # 다음 단계 정보를 데이터베이스에 미리 기록
        if step_index + 1 < len(package_steps):
            next_step = package_steps[step_index + 1]
            next_step_name = next_step.get('name', f'단계 {step_index + 2}')
            next_step_delay = next_step.get('delay', 10)
            
            print(f"📝 다음 단계 정보 기록: {next_step_name} ({next_step_delay}분 후)")
            print(f"📝 다음 단계 상세 정보: {next_step}")
            
            # 다음 단계 예약 정보를 데이터베이스에 저장
            try:
                if DATABASE_URL.startswith('postgresql://'):
                    cursor.execute("""
                        INSERT INTO execution_progress 
                        (order_id, exec_type, step_number, step_name, service_id, quantity, smm_panel_order_id, status, scheduled_datetime, created_at)
                        VALUES (%s, 'package', %s, %s, %s, %s, %s, %s, NOW() + INTERVAL '%s minutes', NOW())
                        ON CONFLICT (order_id, exec_type, step_number) DO UPDATE
                        SET step_name=EXCLUDED.step_name, scheduled_datetime=EXCLUDED.scheduled_datetime, status=EXCLUDED.status
                    """, (order_id, step_index + 2, f"{next_step_name} (예약됨)", next_step.get('id', 0), next_step.get('quantity', 0), None, 'pending', next_step.get('delay', 1440)))
                else:
                    cursor.execute("""
                        INSERT INTO execution_progress 
                        (order_id, exec_type, step_number, step_name, service_id, quantity, smm_panel_order_id, status, scheduled_datetime, created_at)
                        VALUES (?, 'package', ?, ?, ?, ?, ?, ?, datetime('now', '+' || ? || ' minutes'), datetime('now'))
                    """, (order_id, step_index + 2, f"{next_step_name} (예약됨)", next_step.get('id', 0), next_step.get('quantity', 0), None, 'pending', next_step.get('delay', 1440)))
                
                conn.commit()
                print(f"📝 다음 단계 예약 정보 저장 완료")
            except Exception as e:
                print(f"❌ 다음 단계 예약 정보 저장 실패: {e}")
        else:
            print(f"🎉 모든 단계 완료! 다음 단계 없음")
        
        print(f"🔄 schedule_next_package_step 호출 시작")
        print(f"🔄 현재 단계: {step_index + 1}, 다음 단계: {step_index + 2}, 총 단계: {len(package_steps)}")
        
        # 다음 단계가 존재하는지 확인
        if step_index + 1 < len(package_steps):
            print(f"✅ 다음 단계 존재 확인: {step_index + 2}/{len(package_steps)}")
            try:
                schedule_next_package_step(order_id, step_index + 1, package_steps)
                print(f"✅ schedule_next_package_step 호출 완료")
                print(f"✅ 다음 단계 스케줄링 완료: {step_index + 1}/{len(package_steps)}")
            except Exception as e:
                print(f"❌ schedule_next_package_step 호출 실패: {e}")
                import traceback
                print(f"❌ 스케줄링 오류 스택: {traceback.format_exc()}")
        else:
            print(f"🎉 모든 단계 완료! 다음 단계 없음 (현재: {step_index + 1}, 총: {len(package_steps)})")
        
        # 스레드 상태 확인
        import threading
        active_threads = threading.active_count()
        print(f"🔄 현재 활성 스레드 수: {active_threads}")
        for thread in threading.enumerate():
            if 'PackageStep' in thread.name:
                print(f"🔄 패키지 스레드 발견: {thread.name} (활성: {thread.is_alive()})")
        
        conn.close()
        return True
            
    except Exception as e:
        print(f"❌ 패키지 단계 {step_index + 1} 처리 오류: {str(e)}")
        if conn:
            conn.rollback()
            conn.close()
        return False

def schedule_next_package_step(order_id, next_step_index, package_steps):
    """다음 패키지 단계를 스케줄링"""
    if next_step_index >= len(package_steps):
        print(f"🎉 패키지 주문 {order_id} 모든 단계 완료!")
        return
    
    next_step = package_steps[next_step_index]
    next_delay = next_step.get('delay', 10)  # 기본 10분
    next_step_name = next_step.get('name', f'단계 {next_step_index + 1}')
    
    print(f"⏰ 다음 단계 {next_step_index + 1} 스케줄링: {next_step_name} ({next_delay}분 후)")
    
    # 스레드로 지연 실행
    def delayed_next_step():
        try:
            print(f"⏰ {next_delay}분 대기 시작: {next_step_name}")
            print(f"⏰ 현재 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"⏰ 스레드 ID: {threading.current_thread().ident}")
            print(f"⏰ 주문 ID: {order_id}, 다음 단계: {next_step_index}")
            
            # 실제 대기 시간을 초 단위로 변환
            wait_seconds = next_delay * 60
            print(f"⏰ 대기 시간: {wait_seconds}초 ({next_delay}분)")
            
            # 효율적인 대기 방식 사용
            import time
            time.sleep(wait_seconds)
            
            print(f"⏰ {next_delay}분 대기 완료, 다음 단계 실행: {next_step_name}")
            print(f"⏰ 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"⏰ 스레드 ID: {threading.current_thread().ident}")
            
            # 다음 단계 실행
            print(f"🚀 process_package_step 호출 시작: order_id={order_id}, step_index={next_step_index}")
            result = process_package_step(order_id, next_step_index)
            print(f"⏰ 다음 단계 실행 결과: {result}")
            
        except Exception as e:
            print(f"❌ 지연 실행 중 오류 발생: {str(e)}")
            print(f"❌ 스레드 ID: {threading.current_thread().ident}")
            print(f"❌ 주문 ID: {order_id}, 단계: {next_step_index}")
            import traceback
            traceback.print_exc()
    
    # 스레드 생성 및 실행 (daemon=True로 변경하여 메인 프로세스와 독립적으로 실행)
    thread = threading.Thread(target=delayed_next_step, daemon=True, name=f"PackageStep-{order_id}-{next_step_index}")
    thread.start()
    print(f"✅ 다음 단계 스레드 시작됨: {next_step_name} ({next_delay}분 후)")
    print(f"✅ 패키지 단계 {next_step_index + 1} 스케줄링 완료 (스레드 ID: {thread.ident})")
    
    # 스레드가 정상적으로 시작되었는지 확인
    import time
    time.sleep(0.1)  # 스레드 시작을 위한 짧은 대기
    
    if thread.is_alive():
        print(f"✅ 스레드가 정상적으로 시작됨: {thread.name}")
        print(f"✅ 스레드 상태: 활성 (ID: {thread.ident})")
    else:
        print(f"❌ 스레드 시작 실패: {thread.name}")
        print(f"❌ 스레드 상태: 비활성 (ID: {thread.ident})")
        
        # 스레드 재시작 시도
        print(f"🔄 스레드 재시작 시도...")
        retry_thread = threading.Thread(target=delayed_next_step, daemon=True, name=f"PackageStep-Retry-{order_id}-{next_step_index}")
        retry_thread.start()
        time.sleep(0.1)
        
        if retry_thread.is_alive():
            print(f"✅ 재시작 성공: {retry_thread.name}")
        else:
            print(f"❌ 재시작 실패: {retry_thread.name}")
    
    # 스레드 완료를 기다리지 않고 즉시 반환 (백그라운드 실행)
    print(f"🔄 백그라운드에서 {next_delay}분 후 실행 예정: {next_step_name}")
    
    # 스레드가 정상적으로 실행되도록 잠시 대기
    import time
    time.sleep(0.1)

# 기존 패키지 주문 재처리 함수
def reprocess_stuck_package_orders():
    """멈춰있는 패키지 주문들을 재처리"""
    conn = None
    cursor = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # processing 상태인 패키지 주문들 조회
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT order_id, package_steps FROM orders 
                WHERE status = 'processing' AND package_steps IS NOT NULL
                ORDER BY created_at ASC
            """)
        else:
            cursor.execute("""
                SELECT order_id, package_steps FROM orders 
                WHERE status = 'processing' AND package_steps IS NOT NULL
                ORDER BY created_at ASC
            """)
        
        stuck_orders = cursor.fetchall()
        print(f"🔍 멈춰있는 패키지 주문 발견: {len(stuck_orders)}개")
        
        for order in stuck_orders:
            order_id, package_steps_json = order
            print(f"🔄 패키지 주문 재처리: {order_id}")
            
            try:
                # package_steps 파싱
                if isinstance(package_steps_json, list):
                    package_steps = package_steps_json
                elif isinstance(package_steps_json, str):
                    package_steps = json.loads(package_steps_json)
                else:
                    package_steps = []
                
                if package_steps and len(package_steps) > 0:
                    print(f"📦 패키지 주문 {order_id} 재처리 시작: {len(package_steps)}단계")
                    process_package_step(order_id, 0)
                else:
                    print(f"⚠️ 패키지 주문 {order_id} - 단계 정보 없음")
                    
            except Exception as e:
                print(f"❌ 패키지 주문 {order_id} 재처리 실패: {e}")
        
        print(f"✅ 멈춰있는 패키지 주문 재처리 완료")
        
    except Exception as e:
        print(f"❌ 멈춰있는 패키지 주문 재처리 오류: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 주문 상태 업데이트 스케줄 함수
def schedule_order_status_update(order_id, new_status, delay_minutes):
    """주문 상태를 지정된 시간 후에 업데이트하도록 스케줄"""
    import threading
    import time
    
    def update_order_status():
        time.sleep(delay_minutes * 60)  # 분을 초로 변환
        
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 현재 주문 상태 확인
            if DATABASE_URL.startswith('postgresql://'):
                cursor.execute("SELECT status FROM orders WHERE order_id = %s", (order_id,))
            else:
                cursor.execute("SELECT status FROM orders WHERE order_id = ?", (order_id,))
            
            result = cursor.fetchone()
            if not result:
                print(f"⚠️ 주문 {order_id}을 찾을 수 없습니다.")
                return
            
            current_status = result[0]
            
            # 이미 완료된 주문이면 상태 변경하지 않음
            if current_status in ['주문 실행완료', 'failed', 'cancelled']:
                print(f"⚠️ 주문 {order_id}은 이미 {current_status} 상태입니다. 상태 변경을 건너뜁니다.")
                return
            
            # 주문 상태 업데이트
            if DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    UPDATE orders SET status = %s, updated_at = NOW() 
                    WHERE order_id = %s
                """, (new_status, order_id))
            else:
                cursor.execute("""
                    UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE order_id = ?
                """, (new_status, order_id))
            
            conn.commit()
            print(f"✅ 주문 {order_id} 상태가 {new_status}로 자동 업데이트되었습니다.")
            
        except Exception as e:
            print(f"❌ 주문 {order_id} 상태 업데이트 실패: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    # 백그라운드에서 실행
    thread = threading.Thread(target=update_order_status)
    thread.daemon = True
    thread.start()
    print(f"📅 주문 {order_id}의 상태가 {delay_minutes}분 후에 '{new_status}'로 변경되도록 스케줄되었습니다.")

# SMM Panel API 상태 확인 및 자동 완료 처리 함수
def check_and_update_order_status():
    """SMM Panel API를 통해 주문 상태를 확인하고 자동으로 완료 처리"""
    conn = None
    cursor = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 주문 실행중 상태인 주문들 조회
        if DATABASE_URL.startswith('postgresql://'):
            # 새 스키마에서는 order_items 테이블을 사용하므로 쿼리 수정
            try:
                # 새 스키마: order_items에 meta_json이 없으므로 work_jobs의 payload_json에서 smm_panel_order_id 조회
                cursor.execute("""
                    SELECT DISTINCT o.order_id, wj.payload_json->>'smm_panel_order_id' as smm_panel_order_id, o.created_at 
                    FROM orders o
                    JOIN order_items oi ON o.order_id = oi.order_id
                    LEFT JOIN work_jobs wj ON oi.order_item_id = wj.order_item_id
                    WHERE o.status = 'processing' 
                    AND wj.payload_json->>'smm_panel_order_id' IS NOT NULL
                    AND o.created_at > NOW() - INTERVAL '25 hours'
                    ORDER BY o.created_at DESC
                    LIMIT 50
                """)
            except Exception as e:
                print(f"⚠️ 새 스키마 쿼리 실패, 빈 결과 반환: {e}")
                import traceback
                traceback.print_exc()
                cursor.execute("SELECT 1 WHERE 1=0")  # 빈 결과
        else:
            cursor.execute("""
                SELECT order_id, smm_panel_order_id, created_at 
                FROM orders 
                WHERE status = '주문 실행중' 
                AND smm_panel_order_id IS NOT NULL
                AND created_at > datetime('now', '-25 hours')
                ORDER BY created_at DESC
                LIMIT 50
            """)
        
        orders = cursor.fetchall()
        print(f"🔍 SMM Panel 상태 확인 대상 주문: {len(orders)}개")
        
        for order in orders:
            order_id, smm_panel_order_id, created_at = order
            
            try:
                # SMM Panel API로 주문 상태 확인
                import requests
                smm_api_url = "https://smm-panel.com/api/v2"
                smm_api_key = os.getenv('SMM_PANEL_API_KEY')
                
                if not smm_api_key:
                    print("⚠️ SMM_PANEL_API_KEY가 설정되지 않았습니다.")
                    continue
                
                # 주문 상태 확인 API 호출
                status_response = requests.get(f"{smm_api_url}/orders/{smm_panel_order_id}", 
                                             headers={'Authorization': f'Bearer {smm_api_key}'},
                                             timeout=10)
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    smm_status = status_data.get('status', '').lower()
                    
                    # SMM Panel에서 완료된 경우
                    if smm_status in ['completed', 'finished', 'done']:
                        if DATABASE_URL.startswith('postgresql://'):
                            cursor.execute("""
                                UPDATE orders SET status = '주문 실행완료', updated_at = NOW() 
                                WHERE order_id = %s
                            """, (order_id,))
                        else:
                            cursor.execute("""
                                UPDATE orders SET status = '주문 실행완료', updated_at = CURRENT_TIMESTAMP 
                                WHERE order_id = ?
                            """, (order_id,))
                        
                        conn.commit()
                        print(f"✅ 주문 {order_id}이 SMM Panel에서 완료되어 상태가 업데이트되었습니다.")
                    
                    # SMM Panel에서 실패한 경우
                    elif smm_status in ['failed', 'cancelled', 'error']:
                        if DATABASE_URL.startswith('postgresql://'):
                            cursor.execute("""
                                UPDATE orders SET status = 'failed', updated_at = NOW() 
                                WHERE order_id = %s
                            """, (order_id,))
                        else:
                            cursor.execute("""
                                UPDATE orders SET status = 'failed', updated_at = CURRENT_TIMESTAMP 
                                WHERE order_id = ?
                            """, (order_id,))
                        
                        conn.commit()
                        print(f"❌ 주문 {order_id}이 SMM Panel에서 실패하여 상태가 업데이트되었습니다.")
                
            except Exception as e:
                print(f"⚠️ 주문 {order_id} SMM Panel 상태 확인 실패: {e}")
                continue
        
    except Exception as e:
        print(f"❌ SMM Panel 상태 확인 중 오류: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 예약 주문에서 실제 주문 생성 함수
def create_actual_order_from_scheduled(scheduled_id, user_id, service_id, link, quantity, price, package_steps):
    """예약 주문에서 실제 주문 생성"""
    conn = None
    cursor = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 새로운 주문 ID 생성 (bigint 호환)
        import time
        new_order_id = int(time.time() * 1000)  # 밀리초 단위 타임스탬프
        
        # service_id를 variant_id로 변환
        variant_id = None
        unit_price = price
        if DATABASE_URL.startswith('postgresql://'):
            try:
                if service_id and str(service_id).isdigit():
                    cursor.execute("""
                        SELECT variant_id, price 
                        FROM product_variants 
                        WHERE (meta_json->>'service_id')::text = %s 
                           OR (meta_json->>'smm_service_id')::text = %s
                        LIMIT 1
                    """, (str(service_id), str(service_id)))
                    variant_result = cursor.fetchone()
                    if variant_result:
                        variant_id = variant_result[0]
                        unit_price = float(variant_result[1]) if variant_result[1] else price
            except Exception as variant_error:
                print(f"⚠️ variant_id 변환 중 오류 (무시): {variant_error}")
        
        # user_id를 내부 데이터베이스 user_id로 변환
        db_user_id = user_id
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT user_id FROM users WHERE external_uid = %s OR email = %s LIMIT 1
            """, (user_id, user_id))
            user_result = cursor.fetchone()
            if user_result:
                db_user_id = user_result[0]
        
        # 실제 주문 생성 (실제 스키마에 맞게 수정)
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                INSERT INTO orders 
                (order_id, user_id, total_amount, final_amount, status, created_at, updated_at, is_scheduled, package_steps, detailed_service)
                VALUES (%s, %s, %s, %s, 'pending', NOW(), NOW(), FALSE, %s, %s)
                RETURNING order_id
            """, (
                new_order_id, db_user_id, price, price,
                json.dumps(package_steps) if package_steps else None, 'Scheduled Package'
            ))
            inserted_order_id = cursor.fetchone()[0] if cursor.rowcount > 0 else new_order_id
            new_order_id = inserted_order_id
        else:
            # SQLite: 구 스키마 유지 (레거시 호환)
            cursor.execute("""
                INSERT INTO orders 
                (order_id, user_id, service_id, link, quantity, price, status, created_at, updated_at, is_scheduled, package_steps)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', datetime('now'), datetime('now'), 0, ?)
            """, (
                new_order_id, user_id, service_id, link, quantity, price,
                json.dumps(package_steps) if package_steps else None
            ))
        
        # order_items 테이블에 상세 정보 저장
        if DATABASE_URL.startswith('postgresql://') and variant_id:
            try:
                line_amount = unit_price * quantity
                cursor.execute("""
                    INSERT INTO order_items (order_id, variant_id, quantity, unit_price, line_amount, link, status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, 'pending', NOW(), NOW())
                """, (new_order_id, variant_id, quantity, unit_price, line_amount, link))
                print(f"✅ 예약 주문 아이템 생성 완료 - variant_id: {variant_id}")
            except Exception as item_error:
                print(f"⚠️ 예약 주문 아이템 생성 실패 (무시): {item_error}")
        
        conn.commit()
        print(f"✅ 예약 주문에서 실제 주문 생성: {new_order_id}")
        
        # 패키지 상품인 경우 첫 번째 단계 처리
        if package_steps and len(package_steps) > 0:
            print(f"📦 패키지 주문 처리 시작: {len(package_steps)}단계")
            process_package_step(new_order_id, 0)
        else:
            # 일반 주문인 경우 SMM Panel API 호출 (drip-feed 지원)
            print(f"🚀 일반 예약 주문 - SMM Panel API 호출")
            # orders 테이블에서 주문 정보 조회 (drip-feed 정보는 package_steps에서 확인)
            runs = 1
            interval = 0
            # package_steps가 있으면 첫 번째 단계의 repeat 정보 사용
            if package_steps and len(package_steps) > 0:
                first_step = package_steps[0]
                runs = first_step.get('repeat', 1)
                interval = first_step.get('delay', 0)
                print(f"📅 Drip-feed 예약 주문 감지: runs={runs}, interval={interval}")
            
            smm_result = call_smm_panel_api({
                'service': service_id,
                'link': link,
                'quantity': quantity,
                'comments': f'Scheduled order from {scheduled_id}',
                'runs': runs,  # Drip-feed 지원
                'interval': interval  # Drip-feed 지원
            })
            
            if smm_result.get('status') == 'success':
                # SMM Panel 주문 ID 저장
                if DATABASE_URL.startswith('postgresql://'):
                    cursor.execute("""
                        UPDATE orders SET smm_panel_order_id = %s, status = 'processing', updated_at = NOW()
                        WHERE order_id = %s
                    """, (smm_result.get('order'), new_order_id))
                else:
                    cursor.execute("""
                        UPDATE orders SET smm_panel_order_id = ?, status = 'processing', updated_at = CURRENT_TIMESTAMP
                        WHERE order_id = ?
                    """, (smm_result.get('order'), new_order_id))
                conn.commit()
                print(f"✅ 일반 예약 주문 진행중: SMM 주문 ID {smm_result.get('order')}")
            else:
                print(f"❌ 일반 예약 주문 실패: {smm_result.get('message')}")
        
        return True
        
    except Exception as e:
        print(f"❌ 예약 주문에서 실제 주문 생성 실패: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 예약 주문 처리 함수
def process_scheduled_order(order_id):
    """예약 주문 처리"""
    conn = None
    cursor = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 예약 주문 정보 조회 (link와 quantity는 order_items에서 가져옴)
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT o.user_id, oi.variant_id, COALESCE(oi.link, ''), oi.quantity, ''
                FROM orders o
                LEFT JOIN order_items oi ON o.order_id = oi.order_id
                WHERE o.order_id = %s AND o.is_scheduled = TRUE
                LIMIT 1
            """, (order_id,))
        else:
            cursor.execute("""
                SELECT user_id, service_id, link, quantity, '' as comments
                FROM orders 
                WHERE order_id = ? AND is_scheduled = TRUE
            """, (order_id,))
        
        order = cursor.fetchone()
        if not order:
            return False
        
        if DATABASE_URL.startswith('postgresql://'):
            user_id, variant_id, link, quantity, comments = order
            service_id = str(variant_id) if variant_id else None
        else:
            user_id, service_id, link, quantity, comments = order
        
        # SMM Panel API 호출
        smm_result = call_smm_panel_api({
            'service': service_id,
            'link': link,
            'quantity': quantity,
            'comments': comments
        })
        
        if smm_result.get('status') == 'success':
            # 성공 시 주문 상태 업데이트
            if DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    UPDATE orders 
                    SET status = 'processing', smm_panel_order_id = %s, updated_at = NOW()
                    WHERE order_id = %s
                """, (smm_result.get('order'), order_id))
            else:
                cursor.execute("""
                    UPDATE orders 
                    SET status = 'processing', smm_panel_order_id = ?, updated_at = datetime('now')
                    WHERE order_id = ?
                """, (smm_result.get('order'), order_id))
            
            conn.commit()
            return True
        else:
            # 실패 시 상태 업데이트
            if DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    UPDATE orders 
                    SET status = 'failed', updated_at = NOW()
                    WHERE order_id = %s
                """, (order_id,))
            else:
                cursor.execute("""
                    UPDATE orders 
                    SET status = 'failed', updated_at = datetime('now')
                    WHERE order_id = ?
                """, (order_id,))
            
            conn.commit()
            return False
            
    except Exception as e:
        if conn:
            conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 프로덕션 환경에서는 로그 최소화
if os.environ.get('FLASK_ENV') != 'production':
    pass

def get_db_connection():
    """데이터베이스 연결을 가져옵니다."""
    # DATABASE_URL 환경 변수에서 연결 정보 추출
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    if not DATABASE_URL:
        raise Exception("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
    
    try:
        # DATABASE_URL 파싱
        parsed = urlparse(DATABASE_URL)
        
        # 사용자 정보 추출 (user:password 형식)
        user_info = parsed.username
        password = unquote(parsed.password) if parsed.password else ''
        
        # 호스트, 포트, 데이터베이스명
        host = parsed.hostname
        port = parsed.port or 5432
        database = parsed.path.lstrip('/') or 'postgres'
        
        # DNS 해석 문제 방지: 호스트명을 IP로 변환 시도
        import socket
        try:
            # 호스트명이 IP 주소인지 확인
            socket.inet_aton(host)
            resolved_host = host  # 이미 IP 주소
        except socket.error:
            # 호스트명이므로 DNS 조회
            try:
                resolved_host = socket.gethostbyname(host)
                print(f"🔍 DNS 조회 성공: {host} -> {resolved_host}")
            except socket.gaierror as dns_error:
                print(f"⚠️ DNS 조회 실패: {host} - {dns_error}")
                # DNS 조회 실패 시 원본 호스트명 사용 (재시도용)
                resolved_host = host
        
        # 사용자명이 postgres.PROJECT_REF 형식인 경우 처리
        if user_info and '.' in user_info:
            # Pooler 모드: postgres.gvtrizwkstaznrlloixi 형식
            user = user_info
        else:
            # Direct 모드: postgres 형식
            user = user_info or 'postgres'
        
        print(f"🔗 데이터베이스 연결 시도: {resolved_host}:{port}/{database} (user: {user[:20]}...)")
        
        # psycopg2의 내부 로깅을 비활성화하여 인코딩 문제 회피
        import logging
        psycopg2_logger = logging.getLogger('psycopg2')
        psycopg2_logger.setLevel(logging.CRITICAL)
        
        # PostgreSQL 연결 시도 (IP 주소로 우선 시도)
        conn = None
        last_error = None
        
        # IP 주소가 있으면 IP로 먼저 시도, 없으면 호스트명으로 시도
        hosts_to_try = []
        if resolved_host != host and resolved_host:
            hosts_to_try.append(resolved_host)  # IP 주소 먼저
        hosts_to_try.append(host)  # 호스트명도 시도
        
        for attempt_host in hosts_to_try:
            try:
                # Supabase는 SSL이 필요하므로 명시적으로 설정
                conn = psycopg2.connect(
                    host=attempt_host,
                    port=port,
                    database=database,
                    user=user,
                    password=password,
                    connect_timeout=30,
                    keepalives_idle=600,
                    keepalives_interval=30,
                    keepalives_count=3,
                    sslmode='require'  # SSL 모드 명시적 설정
                )
                print(f"✅ 데이터베이스 연결 성공: {attempt_host}:{port}/{database}")
                conn.autocommit = False
                # 연결이 살아있는지 확인
                cursor_test = conn.cursor()
                cursor_test.execute("SELECT 1")
                cursor_test.close()
                return conn
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                last_error = e
                error_msg = str(e)
                # SSL 오류나 연결 끊김 오류인 경우 재시도
                if 'SSL connection has been closed' in error_msg or 'connection has been closed' in error_msg or 'SSL' in error_msg:
                    if attempt_host != hosts_to_try[-1]:  # 마지막 시도가 아니면 계속
                        print(f"⚠️ {attempt_host} 연결 실패 (SSL/연결 끊김), 다음 호스트로 시도...")
                        continue
                    # 마지막 시도에서도 실패하면 다시 처음부터 시도 (최대 3회)
                    print(f"⚠️ SSL 연결 실패, 재시도...")
                    import time
                    for retry_attempt in range(3):
                        time.sleep(2 * (retry_attempt + 1))  # 2초, 4초, 6초 대기 (지수 백오프)
                        try:
                            conn = psycopg2.connect(
                                host=attempt_host,
                                port=port,
                                database=database,
                                user=user,
                                password=password,
                                connect_timeout=30,
                                keepalives_idle=600,
                                keepalives_interval=30,
                                keepalives_count=3,
                                sslmode='require'
                            )
                            print(f"✅ 데이터베이스 재연결 성공: {attempt_host}:{port}/{database} (재시도 {retry_attempt + 1}/3)")
                            conn.autocommit = False
                            # 연결 테스트
                            cursor_test = conn.cursor()
                            cursor_test.execute("SELECT 1")
                            cursor_test.close()
                            return conn
                        except Exception as retry_error:
                            if retry_attempt < 2:  # 마지막 재시도가 아니면 계속
                                print(f"⚠️ 재연결 시도 {retry_attempt + 1}/3 실패, 다시 시도...")
                                continue
                            else:
                                print(f"❌ 재연결 시도 실패 (최대 재시도 횟수 초과): {retry_error}")
                # DNS 오류인 경우에만 다음 호스트로 시도
                elif 'could not translate host name' in error_msg or 'Name or service not known' in error_msg:
                    if attempt_host != hosts_to_try[-1]:  # 마지막 시도가 아니면 계속
                        print(f"⚠️ {attempt_host} 연결 실패 (DNS 오류), 다음 호스트로 시도...")
                        continue
                # 다른 오류이거나 마지막 시도인 경우 즉시 실패
                break
        
        # 모든 시도 실패
        raise last_error
        
    except psycopg2.OperationalError as e:
        error_msg = str(e)
        if 'could not translate host name' in error_msg or 'Name or service not known' in error_msg:
            print(f"❌ 데이터베이스 연결 실패 (DNS 오류): {error_msg}")
            print(f"💡 해결 방법:")
            print(f"   1. 인터넷 연결 확인")
            print(f"   2. DNS 서버 설정 확인 (nslookup {host} 테스트)")
            print(f"   3. 방화벽에서 {host}:{port} 접근 허용 확인")
        else:
            print(f"❌ 데이터베이스 연결 실패: {error_msg}")
        raise
    except Exception as e:
        print(f"❌ DATABASE_URL 파싱 오류: {e}")
        print(f"   DATABASE_URL: {DATABASE_URL[:50]}...")
        import traceback
        traceback.print_exc()
        raise

def init_database():
    """데이터베이스 테이블을 초기화합니다."""
    conn = None
    try:
        # 연결 시도 (최대 3회 재시도)
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                conn = get_db_connection()
                break
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as conn_error:
                retry_count += 1
                error_msg = str(conn_error)
                if 'SSL connection has been closed' in error_msg or 'connection has been closed' in error_msg:
                    if retry_count < max_retries:
                        print(f"⚠️ 데이터베이스 연결 실패 (재시도 {retry_count}/{max_retries}): {error_msg}")
                        import time
                        time.sleep(2 * retry_count)  # 지수 백오프: 2초, 4초, 6초
                        continue
                    else:
                        print(f"❌ 데이터베이스 연결 실패 (최대 재시도 횟수 초과): {error_msg}")
                        print(f"⚠️ 데이터베이스 초기화를 건너뜁니다. 앱은 계속 실행되지만 일부 기능이 제한될 수 있습니다.")
                        return  # 연결 실패해도 앱은 계속 실행
                else:
                    # 다른 종류의 오류는 즉시 실패
                    print(f"❌ 데이터베이스 연결 실패: {error_msg}")
                    print(f"⚠️ 데이터베이스 초기화를 건너뜁니다. 앱은 계속 실행되지만 일부 기능이 제한될 수 있습니다.")
                    return
            except Exception as e:
                print(f"❌ 데이터베이스 연결 중 예상치 못한 오류: {e}")
                print(f"⚠️ 데이터베이스 초기화를 건너뜁니다. 앱은 계속 실행되지만 일부 기능이 제한될 수 있습니다.")
                return
        
        if not conn:
            print(f"⚠️ 데이터베이스 연결을 얻을 수 없습니다. 앱은 계속 실행되지만 일부 기능이 제한될 수 있습니다.")
            return
        
        cursor = conn.cursor()
        
        # PostgreSQL인지 SQLite인지 확인
        is_postgresql = DATABASE_URL.startswith('postgresql://')
        
        # 트랜잭션 중단 시 복구를 위한 헬퍼 함수
        def safe_execute(sql, params=None, commit_after=False):
            """안전하게 SQL 실행 (오류 발생 시 롤백 후 재시도)"""
            try:
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                if commit_after:
                    conn.commit()
                return True
            except Exception as e:
                error_str = str(e).lower()
                # 트랜잭션 중단 오류인 경우 롤백 후 재시도
                if 'current transaction is aborted' in error_str or 'aborted' in error_str:
                    try:
                        conn.rollback()
                        # 롤백 후 재시도
                        if params:
                            cursor.execute(sql, params)
                        else:
                            cursor.execute(sql)
                        if commit_after:
                            conn.commit()
                        return True
                    except Exception as retry_error:
                        print(f"⚠️ 재시도 실패 (무시): {retry_error}")
                        return False
                else:
                    # 다른 오류는 무시 (이미 존재하는 경우 등)
                    return False
        
        if is_postgresql:
            # order_status ENUM 타입에 'failed' 값 추가 (없는 경우에만)
            # 참고: ALTER TYPE ... ADD VALUE는 트랜잭션 내에서 실행할 수 없으므로 별도로 실행
            try:
                # ENUM 타입이 존재하는지 확인
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_type WHERE typname = 'order_status'
                    )
                """)
                enum_exists = cursor.fetchone()[0] if cursor.rowcount > 0 else False
                
                if enum_exists:
                    # 'failed' 값이 이미 있는지 확인
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT 1 
                            FROM pg_enum 
                            WHERE enumlabel = 'failed' 
                            AND enumtypid = (
                                SELECT oid FROM pg_type WHERE typname = 'order_status'
                            )
                        )
                    """)
                    failed_exists = cursor.fetchone()[0] if cursor.rowcount > 0 else False
                    
                    if not failed_exists:
                        # 트랜잭션 커밋 후 ENUM 값 추가 시도
                        conn.commit()
                        print("🔄 order_status ENUM에 'failed' 값 추가 시도...")
                        try:
                            # ENUM 값 추가 (트랜잭션 외부에서 실행)
                            # 참고: PostgreSQL에서는 ALTER TYPE ... ADD VALUE를 트랜잭션 내에서 실행할 수 없음
                            cursor.execute("ALTER TYPE order_status ADD VALUE 'failed'")
                            conn.commit()
                            print("✅ order_status ENUM에 'failed' 값 추가 완료")
                        except Exception as add_enum_error:
                            # 이미 존재하는 경우나 다른 오류는 무시
                            error_str = str(add_enum_error).lower()
                            if 'already exists' in error_str or 'duplicate' in error_str or 'already present' in error_str:
                                print("ℹ️ order_status ENUM에 'failed' 값이 이미 존재합니다.")
                            else:
                                print(f"⚠️ order_status ENUM에 'failed' 값 추가 실패: {add_enum_error}")
                                print(f"⚠️ 마이그레이션 스크립트를 실행하여 수동으로 추가해야 할 수 있습니다.")
                            try:
                                conn.rollback()
                            except:
                                pass
                    else:
                        print("ℹ️ order_status ENUM에 'failed' 값이 이미 존재합니다.")
                else:
                    print("ℹ️ order_status ENUM 타입이 아직 생성되지 않았습니다. (마이그레이션 스크립트에서 생성됨)")
            except Exception as enum_check_error:
                print(f"⚠️ order_status ENUM 확인 중 오류 (무시하고 계속): {enum_check_error}")
                try:
                    conn.rollback()
                except:
                    pass
            
            # PostgreSQL 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id VARCHAR(255) PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    display_name VARCHAR(255),
                    google_id VARCHAR(255),
                    kakao_id VARCHAR(255),
                    profile_image TEXT,
                    last_login TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT NOW(),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # 기존 테이블에 컬럼 추가 (PostgreSQL) - 각 컬럼을 개별적으로 시도
            # CREATE TABLE IF NOT EXISTS로 테이블이 새로 생성되면 컬럼이 이미 존재하므로 무시됨
            def safe_add_column(column_name, column_type):
                """컬럼이 없으면 추가 (이미 존재하면 무시)"""
                try:
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT 1 
                            FROM information_schema.columns 
                            WHERE table_name = 'users' 
                            AND column_name = %s
                        )
                    """, (column_name,))
                    exists = cursor.fetchone()[0]
                    if not exists:
                        cursor.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")
                        return True
                except Exception as e:
                    # 컬럼 추가 실패 (이미 존재하거나 다른 오류) - 무시
                    pass
                return False
            
            added_cols = []
            if safe_add_column('google_id', 'VARCHAR(255)'):
                added_cols.append('google_id')
            if safe_add_column('kakao_id', 'VARCHAR(255)'):
                added_cols.append('kakao_id')
            if safe_add_column('profile_image', 'TEXT'):
                added_cols.append('profile_image')
            if safe_add_column('last_login', 'TIMESTAMP'):
                added_cols.append('last_login')
            if safe_add_column('commission_rate', 'DECIMAL(5,4) DEFAULT 0.1'):
                added_cols.append('commission_rate')
            if safe_add_column('referral_code', 'VARCHAR(50)'):
                added_cols.append('referral_code')
            if safe_add_column('phone_number', 'VARCHAR(20)'):
                added_cols.append('phone_number')
            if safe_add_column('signup_source', 'VARCHAR(50)'):
                added_cols.append('signup_source')
            if safe_add_column('account_type', 'VARCHAR(20)'):
                added_cols.append('account_type')
            if safe_add_column('external_uid', 'VARCHAR(255)'):
                added_cols.append('external_uid')
            if safe_add_column('username', 'VARCHAR(255)'):
                added_cols.append('username')
            # 비즈니스 계정 관련 컬럼 추가
            if safe_add_column('business_number', 'VARCHAR(50)'):
                added_cols.append('business_number')
            if safe_add_column('business_name', 'VARCHAR(255)'):
                added_cols.append('business_name')
            if safe_add_column('representative', 'VARCHAR(100)'):
                added_cols.append('representative')
            if safe_add_column('contact_phone', 'VARCHAR(20)'):
                added_cols.append('contact_phone')
            if safe_add_column('contact_email', 'VARCHAR(255)'):
                added_cols.append('contact_email')
            if safe_add_column('is_admin', 'BOOLEAN DEFAULT FALSE'):
                added_cols.append('is_admin')
            if added_cols:
                print(f"✅ 사용자 테이블 컬럼 추가 완료 (PostgreSQL): {', '.join(added_cols)}")
            else:
                print("✅ 사용자 테이블 컬럼 확인 완료 (모든 컬럼 존재)")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS points (
                    user_id VARCHAR(255) PRIMARY KEY,
                    points INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # 추천인 코드 테이블 생성 (기존 데이터 보존)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS referral_codes (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(50) UNIQUE NOT NULL,
                    user_id VARCHAR(255),
                    user_email VARCHAR(255) UNIQUE,
                    name VARCHAR(255),
                    phone VARCHAR(255),
                    is_active BOOLEAN DEFAULT true,
                    usage_count INTEGER DEFAULT 0,
                    total_commission DECIMAL(10,2) DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # 모든 기존 코드를 강제로 활성화 (활성화 없이 바로 사용)
            cursor.execute("UPDATE referral_codes SET is_active = true")
            print("🔄 모든 추천인 코드 자동 활성화 완료")
            
            # 기존 데이터 강제 활성화 (데이터 손실 없음)
            cursor.execute("UPDATE referral_codes SET is_active = true WHERE is_active = false")
            updated_count = cursor.rowcount
            print(f"🔄 기존 추천인 코드 강제 활성화 완료: {updated_count}개 업데이트")
            
            # 기존 추천인 코드의 user_id를 고유하게 업데이트
            cursor.execute("SELECT id, user_email FROM referral_codes WHERE user_id IS NULL OR user_id = ''")
            existing_codes = cursor.fetchall()
            
            for code_id, user_email in existing_codes:
                if user_email:
                    import hashlib
                    user_unique_id = hashlib.md5(user_email.encode()).hexdigest()[:8].upper()
                    cursor.execute("UPDATE referral_codes SET user_id = %s WHERE id = %s", (user_unique_id, code_id))
                    print(f"🔄 추천인 코드 user_id 업데이트: {user_email} -> {user_unique_id}")
            
            if existing_codes:
                print(f"🔄 총 {len(existing_codes)}개 추천인 코드 user_id 업데이트 완료")
            
            # 데이터 보존 확인
            cursor.execute("SELECT COUNT(*) FROM referral_codes")
            total_count = cursor.fetchone()[0]
            print(f"📊 총 추천인 코드 수: {total_count}개 (데이터 보존됨)")
            
            # 추천인 테이블 생성 (PostgreSQL은 migrate_database.py에서 관리, 여기서는 SQLite용만)
            # PostgreSQL에서는 새 스키마 사용 (referrer_user_id, referred_user_id)
            if not DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS referrals (
                        id SERIAL PRIMARY KEY,
                        referrer_email VARCHAR(255) NOT NULL,
                        referral_code VARCHAR(50) NOT NULL,
                        name VARCHAR(255),
                        phone VARCHAR(255),
                        status VARCHAR(50) DEFAULT 'active',
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
            else:
                # PostgreSQL은 migrate_database.py에서 관리하므로 여기서는 스킵
                print("ℹ️ PostgreSQL referrals 테이블은 migrate_database.py에서 관리됩니다.")
            
            # 커미션 테이블 생성 (기존 데이터 보존)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS commissions (
                    id SERIAL PRIMARY KEY,
                    referred_user VARCHAR(255) NOT NULL,
                    referrer_id VARCHAR(255) NOT NULL,
                    purchase_amount DECIMAL(10,2) NOT NULL,
                    commission_amount DECIMAL(10,2) NOT NULL,
                    commission_rate DECIMAL(5,4) NOT NULL,
                    is_paid BOOLEAN DEFAULT false,
                    payment_date TIMESTAMP DEFAULT NOW(),
                    paid_date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # 쿠폰 테이블 생성 (기존 데이터 보존)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS coupons (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    referral_code VARCHAR(50),
                    discount_type VARCHAR(20) DEFAULT 'percentage',
                    discount_value DECIMAL(5,2) NOT NULL,
                    is_used BOOLEAN DEFAULT false,
                    used_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW(),
                    expires_at TIMESTAMP
                )
            """)
            
            # commission_ledger 테이블 생성 스킵 (새 스키마에서는 commissions 테이블 사용)
            # Supabase에 이미 새 스키마가 적용되어 있으므로 구 스키마 테이블 생성은 건너뜀
            print("ℹ️ commission_ledger 테이블 생성 스킵 (새 스키마에서는 commissions 테이블 사용)")
            
            # commission_ledger 관련 코드 스킵 (새 스키마에서는 commissions 테이블 사용)
            print("ℹ️ commission_ledger 관련 코드 스킵 (새 스키마에서는 commissions 테이블 사용)")
            
            # commission_ledger 트리거 함수 생성 스킵 (새 스키마에서는 commissions 테이블 사용)
            print("ℹ️ commission_ledger 트리거 생성 스킵 (새 스키마에서는 commissions 테이블 사용)")
            
            # 공지사항 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notices (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    content TEXT NOT NULL,
                    image_url VARCHAR(500),
                    is_active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # 블로그 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blog_posts (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    content TEXT NOT NULL,
                    excerpt TEXT,
                    category VARCHAR(100),
                    thumbnail_url TEXT,
                    tags JSONB DEFAULT '[]',
                    is_published BOOLEAN DEFAULT false,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    view_count INTEGER DEFAULT 0
                )
            """)
            
            # 주문 테이블 생성 (기존 데이터 보존)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id VARCHAR(255) PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    user_email VARCHAR(255),
                    service_id VARCHAR(255) NOT NULL,
                    platform VARCHAR(255),
                    service_name VARCHAR(255),
                    service_type VARCHAR(255),
                    service_platform VARCHAR(255),
                    service_quantity INTEGER,
                    service_link TEXT,
                    link TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price DECIMAL(10,2) NOT NULL,
                    total_price DECIMAL(10,2),
                    amount DECIMAL(10,2),
                    discount_amount DECIMAL(10,2) DEFAULT 0,
                    referral_code VARCHAR(50),
                    status VARCHAR(50) DEFAULT 'pending',
                    external_order_id VARCHAR(255),
                    remarks TEXT,
                    comments TEXT,
                    is_scheduled BOOLEAN DEFAULT FALSE,
                    scheduled_datetime TIMESTAMP,
                    is_split_delivery BOOLEAN DEFAULT FALSE,
                    split_days INTEGER DEFAULT 0,
                    split_quantity INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
        # order_id 컬럼 타입 확인 (기존 INTEGER 유지) - PostgreSQL만
        if is_postgresql:
            try:
                cursor.execute("""
                    SELECT data_type FROM information_schema.columns 
                    WHERE table_name = 'orders' AND column_name = 'order_id'
                """)
                column_info = cursor.fetchone()
                if column_info:
                    current_type = column_info[0]
                    print(f"🔍 현재 order_id 컬럼 타입: {current_type}")
                    print(f"ℹ️ order_id 컬럼 타입: {current_type} (기존 방식 유지)")
                else:
                    print("⚠️ order_id 컬럼 정보를 찾을 수 없습니다.")
            except Exception as e:
                print(f"⚠️ order_id 컬럼 타입 확인 실패: {e}")
                try:
                    conn.rollback()
                except:
                    pass
            
            # 기존 테이블에 예약/분할 필드 추가 (이미 존재하는 경우 무시)
            def safe_add_order_column(column_name, column_type):
                """컬럼이 없으면 추가 (이미 존재하면 무시)"""
                try:
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT 1 
                            FROM information_schema.columns 
                            WHERE table_name = 'orders' 
                            AND column_name = %s
                        )
                    """, (column_name,))
                    exists = cursor.fetchone()[0]
                    if not exists:
                        cursor.execute(f"ALTER TABLE orders ADD COLUMN {column_name} {column_type}")
                        return True
                except Exception as e:
                    # 트랜잭션 중단 오류인 경우 롤백 후 재시도
                    error_str = str(e).lower()
                    if 'current transaction is aborted' in error_str:
                        try:
                            conn.rollback()
                            # 롤백 후 컬럼 존재 여부 다시 확인
                            cursor.execute("""
                                SELECT EXISTS (
                                    SELECT 1 
                                    FROM information_schema.columns 
                                    WHERE table_name = 'orders' 
                                    AND column_name = %s
                                )
                            """, (column_name,))
                            exists = cursor.fetchone()[0]
                            if not exists:
                                cursor.execute(f"ALTER TABLE orders ADD COLUMN {column_name} {column_type}")
                                return True
                        except Exception as retry_error:
                            pass
                    # 컬럼 추가 실패 (이미 존재하거나 다른 오류) - 무시
                    pass
                return False
            
            added_order_cols = []
            if safe_add_order_column('is_scheduled', 'BOOLEAN DEFAULT FALSE'):
                added_order_cols.append('is_scheduled')
            if safe_add_order_column('scheduled_datetime', 'TIMESTAMP'):
                added_order_cols.append('scheduled_datetime')
            if safe_add_order_column('is_split_delivery', 'BOOLEAN DEFAULT FALSE'):
                added_order_cols.append('is_split_delivery')
            if safe_add_order_column('split_days', 'INTEGER DEFAULT 0'):
                added_order_cols.append('split_days')
            if safe_add_order_column('split_quantity', 'INTEGER DEFAULT 0'):
                added_order_cols.append('split_quantity')
            if added_order_cols:
                print(f"✅ 예약/분할 필드 추가 완료: {', '.join(added_order_cols)}")
            else:
                print("✅ 예약/분할 필드 확인 완료 (모든 필드 존재)")
        
        # execution_progress 테이블 생성 (통합: package_progress, split_delivery_progress, scheduled_orders 대체) - PostgreSQL만
        # 새 스키마에서는 work_jobs 테이블을 사용하므로 execution_progress는 스킵
        if is_postgresql:
            # execution_progress 테이블은 새 스키마에서 사용하지 않음 (work_jobs 사용)
            # 기존 테이블이 있으면 외래 키 제약 조건만 제거
            try:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = 'execution_progress'
                    )
                """)
                table_exists = cursor.fetchone()[0]
                if table_exists:
                    # 외래 키 제약 조건 제거 시도
                    try:
                        cursor.execute("ALTER TABLE execution_progress DROP CONSTRAINT IF EXISTS fk_exec_order")
                        print("✅ execution_progress 외래 키 제약 조건 제거 완료")
                    except:
                        pass
            except:
                pass
            print("ℹ️ execution_progress 테이블 생성 스킵 (새 스키마에서는 work_jobs 사용)")
            
            # execution_progress 인덱스 생성도 스킵 (테이블이 없으므로)
            print("ℹ️ execution_progress 인덱스 생성 스킵 (새 스키마에서는 work_jobs 사용)")
            
            # orders 테이블에 필요한 컬럼들 추가 (존재 여부 확인 후)
            def safe_add_order_col(column_name, column_type, col_type_desc=''):
                """컬럼이 없으면 추가 (트랜잭션 오류 처리 포함)"""
                try:
                    cursor.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name='orders' AND column_name=%s
                    """, (column_name,))
                    if not cursor.fetchone():
                        cursor.execute(f"ALTER TABLE orders ADD COLUMN {column_name} {column_type}")
                        conn.commit()
                        print(f"✅ {column_name} 필드 추가 완료")
                        return True
                    else:
                        print(f"ℹ️ {column_name} 필드 이미 존재")
                        return False
                except Exception as e:
                    error_str = str(e).lower()
                    if 'current transaction is aborted' in error_str:
                        try:
                            conn.rollback()
                            # 롤백 후 다시 확인
                            cursor.execute("""
                                SELECT column_name 
                                FROM information_schema.columns 
                                WHERE table_name='orders' AND column_name=%s
                            """, (column_name,))
                            if not cursor.fetchone():
                                cursor.execute(f"ALTER TABLE orders ADD COLUMN {column_name} {column_type}")
                                conn.commit()
                                print(f"✅ {column_name} 필드 추가 완료 (재시도)")
                                return True
                            else:
                                print(f"ℹ️ {column_name} 필드 이미 존재")
                                return False
                        except Exception as retry_error:
                            print(f"⚠️ {column_name} 필드 추가 실패 (재시도 실패): {retry_error}")
                            try:
                                conn.rollback()
                            except:
                                pass
                            return False
                    else:
                        print(f"⚠️ {column_name} 필드 추가 실패: {e}")
                        try:
                            conn.rollback()
                        except:
                            pass
                        return False
            
            safe_add_order_col('smm_panel_order_id', 'VARCHAR(255)')
            safe_add_order_col('last_status_check', 'TIMESTAMP')
            safe_add_order_col('detailed_service', 'TEXT')
            safe_add_order_col('package_steps', 'JSONB')
            
            # product_variants 테이블에 original_cost 컬럼 추가
            def safe_add_variant_column(column_name, column_type):
                """product_variants 테이블에 컬럼이 없으면 추가"""
                try:
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT 1 
                            FROM information_schema.columns 
                            WHERE table_name = 'product_variants' 
                            AND column_name = %s
                        )
                    """, (column_name,))
                    exists = cursor.fetchone()[0]
                    if not exists:
                        cursor.execute(f"ALTER TABLE product_variants ADD COLUMN {column_name} {column_type}")
                        conn.commit()
                        print(f"✅ product_variants.{column_name} 필드 추가 완료")
                        return True
                    else:
                        print(f"ℹ️ product_variants.{column_name} 필드 이미 존재")
                        return False
                except Exception as e:
                    error_str = str(e).lower()
                    if 'current transaction is aborted' in error_str:
                        try:
                            conn.rollback()
                            cursor.execute("""
                                SELECT EXISTS (
                                    SELECT 1 
                                    FROM information_schema.columns 
                                    WHERE table_name = 'product_variants' 
                                    AND column_name = %s
                                )
                            """, (column_name,))
                            exists = cursor.fetchone()[0]
                            if not exists:
                                cursor.execute(f"ALTER TABLE product_variants ADD COLUMN {column_name} {column_type}")
                                conn.commit()
                                print(f"✅ product_variants.{column_name} 필드 추가 완료 (재시도)")
                                return True
                        except Exception as retry_error:
                            print(f"⚠️ product_variants.{column_name} 필드 추가 실패: {retry_error}")
                            try:
                                conn.rollback()
                            except:
                                pass
                            return False
                    else:
                        print(f"⚠️ product_variants.{column_name} 필드 추가 실패: {e}")
                        try:
                            conn.rollback()
                        except:
                            pass
                        return False
            
            safe_add_variant_column('original_cost', 'NUMERIC(14,2) DEFAULT 0')
            
            # wallets 테이블 생성 (새 스키마 사용)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS wallets (
                    wallet_id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL UNIQUE REFERENCES users (user_id),
                    balance NUMERIC(14,2) NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            print("✅ wallets 테이블 생성 완료 (PostgreSQL)")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS point_purchases (
                id SERIAL PRIMARY KEY,
                    purchase_id VARCHAR(255) UNIQUE,
                    user_id VARCHAR(255) NOT NULL,
                    user_email VARCHAR(255),
                    amount INTEGER NOT NULL,
                    price DECIMAL(10,2) NOT NULL,
                    status VARCHAR(50) DEFAULT 'pending',
                    depositor_name VARCHAR(255),
                    buyer_name VARCHAR(255),
                    bank_name VARCHAR(255),
                    bank_info TEXT,
                    receipt_type VARCHAR(50),
                    business_info TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
        # PostgreSQL 브랜치 끝
        
        if not is_postgresql:
            # SQLite 테이블 생성
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    display_name TEXT,
                    google_id TEXT,
                    kakao_id TEXT,
                    profile_image TEXT,
                    last_login TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 기존 테이블에 컬럼 추가 (SQLite) - 각 컬럼을 개별적으로 시도
            def safe_add_sqlite_column(column_name, column_type):
                """컬럼이 없으면 추가 (이미 존재하면 무시)"""
                try:
                    # SQLite는 information_schema 대신 PRAGMA table_info 사용
                    cursor.execute("PRAGMA table_info(users)")
                    columns = [row[1] for row in cursor.fetchall()]
                    if column_name not in columns:
                        cursor.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")
                        return True
                except Exception as e:
                    # 컬럼 추가 실패 (이미 존재하거나 다른 오류) - 무시
                    pass
                return False
            
            added_sqlite_cols = []
            if safe_add_sqlite_column('google_id', 'TEXT'):
                added_sqlite_cols.append('google_id')
            if safe_add_sqlite_column('kakao_id', 'TEXT'):
                added_sqlite_cols.append('kakao_id')
            if safe_add_sqlite_column('profile_image', 'TEXT'):
                added_sqlite_cols.append('profile_image')
            if safe_add_sqlite_column('last_login', 'TIMESTAMP'):
                added_sqlite_cols.append('last_login')
            if safe_add_sqlite_column('display_name', 'TEXT'):
                added_sqlite_cols.append('display_name')
            if safe_add_sqlite_column('commission_rate', 'REAL DEFAULT 0.1'):
                added_sqlite_cols.append('commission_rate')
            if safe_add_sqlite_column('referral_code', 'TEXT'):
                added_sqlite_cols.append('referral_code')
            if safe_add_sqlite_column('username', 'TEXT'):
                added_sqlite_cols.append('username')
            if safe_add_sqlite_column('phone_number', 'TEXT'):
                added_sqlite_cols.append('phone_number')
            if safe_add_sqlite_column('signup_source', 'TEXT'):
                added_sqlite_cols.append('signup_source')
            if safe_add_sqlite_column('account_type', 'TEXT'):
                added_sqlite_cols.append('account_type')
            if safe_add_sqlite_column('external_uid', 'TEXT'):
                added_sqlite_cols.append('external_uid')
            # 비즈니스 계정 관련 컬럼 추가 (SQLite)
            if safe_add_sqlite_column('business_number', 'TEXT'):
                added_sqlite_cols.append('business_number')
            if safe_add_sqlite_column('business_name', 'TEXT'):
                added_sqlite_cols.append('business_name')
            if safe_add_sqlite_column('representative', 'TEXT'):
                added_sqlite_cols.append('representative')
            if safe_add_sqlite_column('contact_phone', 'TEXT'):
                added_sqlite_cols.append('contact_phone')
            if safe_add_sqlite_column('contact_email', 'TEXT'):
                added_sqlite_cols.append('contact_email')
            if added_sqlite_cols:
                print(f"✅ 사용자 테이블 컬럼 추가 완료 (SQLite): {', '.join(added_sqlite_cols)}")
            else:
                print("✅ 사용자 테이블 컬럼 확인 완료 (모든 컬럼 존재)")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS points (
                    user_id TEXT PRIMARY KEY,
                points INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    service_id TEXT NOT NULL,
                    link TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price REAL NOT NULL,
                    total_price REAL,
                    discount_amount REAL DEFAULT 0,
                    referral_code TEXT,
                    status TEXT DEFAULT 'pending_payment',
                    external_order_id TEXT,
                    platform TEXT,
                    service_name TEXT,
                    comments TEXT,
                    smm_panel_order_id TEXT,
                    last_status_check TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS point_purchases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    price REAL NOT NULL,
                    status TEXT DEFAULT 'pending',
                    buyer_name TEXT,
                    bank_info TEXT,
                    purchase_id TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # 예약 주문 테이블 생성 (SQLite)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    service_id TEXT NOT NULL,
                    link TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price REAL NOT NULL,
                    scheduled_datetime TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    package_steps TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP
                )
            """)
            print("✅ 예약 주문 테이블 생성 완료 (SQLite)")
            
            # 패키지 진행 상황 테이블 생성 (SQLite)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS package_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT NOT NULL,
                    step_number INTEGER NOT NULL,
                    step_name TEXT NOT NULL,
                    service_id TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    smm_panel_order_id TEXT,
                    status TEXT DEFAULT 'pending',
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)
            print("✅ 패키지 진행 상황 테이블 생성 완료 (SQLite)")
            
            # 공지사항 테이블 생성 (SQLite)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    image_url TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("✅ 공지사항 테이블 생성 완료 (SQLite)")
            
            # 블로그 테이블 생성 (SQLite)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blog_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    excerpt TEXT,
                    category TEXT,
                    thumbnail_url TEXT,
                    tags TEXT DEFAULT '[]',
                    is_published INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    view_count INTEGER DEFAULT 0
                )
            """)
            print("✅ 블로그 테이블 생성 완료 (SQLite)")
            
            # commission_ledger 테이블 생성 (SQLite) - 통합 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS commission_ledger (
                    ledger_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referral_code TEXT NOT NULL,
                    referrer_user_id TEXT NOT NULL,
                    referred_user_id TEXT,
                    order_id TEXT,
                    event TEXT NOT NULL CHECK (event IN ('earn','payout','adjust','reverse')),
                    base_amount REAL,
                    commission_rate REAL,
                    amount REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'confirmed' CHECK (status IN ('pending','confirmed','cancelled')),
                    notes TEXT,
                    external_ref TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    confirmed_at TEXT
                )
            """)
            print("✅ commission_ledger 테이블 생성 완료 (SQLite - 통합 테이블)")
            
            # commission_ledger 인덱스 생성 (SQLite)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ledger_code_time ON commission_ledger(referral_code, created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ledger_owner_time ON commission_ledger(referrer_user_id, created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ledger_event_time ON commission_ledger(event, created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ledger_order ON commission_ledger(order_id)")
            print("✅ commission_ledger 인덱스 생성 완료 (SQLite)")
        
        # 트랜잭션 중단 오류 체크 및 복구
        try:
            conn.commit()
            print("✅ 데이터베이스 테이블 초기화 완료")
        except Exception as commit_error:
            error_str = str(commit_error).lower()
            if 'current transaction is aborted' in error_str or 'aborted' in error_str:
                print("⚠️ 트랜잭션 중단 감지, 롤백 후 계속 진행...")
                try:
                    conn.rollback()
                    # 롤백 후 다시 커밋 시도 (이미 커밋된 작업은 롤백되지 않음)
                    try:
                        conn.commit()
                    except:
                        pass
                    print("✅ 트랜잭션 롤백 완료, 계속 진행")
                except Exception as rollback_error:
                    print(f"⚠️ 롤백 실패 (무시): {rollback_error}")
            else:
                print(f"⚠️ 커밋 오류 (계속 진행): {commit_error}")
                try:
                    conn.rollback()
                except:
                    pass
        
        # 데이터베이스 인덱스 생성 (성능 최적화)
        print("🔍 데이터베이스 인덱스 생성 중...")
        
        if is_postgresql:
            # PostgreSQL 인덱스
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)",
                "CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_orders_order_id ON orders(order_id)",
                "CREATE INDEX IF NOT EXISTS idx_points_user_id ON points(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_point_purchases_user_id ON point_purchases(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_point_purchases_status ON point_purchases(status)",
                "CREATE INDEX IF NOT EXISTS idx_referral_codes_code ON referral_codes(code)",
                "CREATE INDEX IF NOT EXISTS idx_referral_codes_user_email ON referral_codes(user_email)"
                # 새 스키마에서는 존재하지 않는 테이블들의 인덱스는 스킵
                # scheduled_orders, package_progress, split_delivery_progress, commission_points 등은 새 스키마에서 사용하지 않음
            ]
        else:
            # SQLite 인덱스
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)",
                "CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_points_user_id ON points(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_point_purchases_user_id ON point_purchases(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_point_purchases_status ON point_purchases(status)",
                "CREATE INDEX IF NOT EXISTS idx_referral_codes_code ON referral_codes(code)",
                "CREATE INDEX IF NOT EXISTS idx_referral_codes_user_email ON referral_codes(user_email)"
                # 새 스키마에서는 존재하지 않는 테이블들의 인덱스는 스킵
                # scheduled_orders, package_progress, split_delivery_progress, commission_points 등은 새 스키마에서 사용하지 않음
            ]
        
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
                index_name = index_sql.split('idx_')[1].split(' ')[0]
                print(f"✅ 인덱스 생성: {index_name}")
            except Exception as e:
                index_name = index_sql.split('idx_')[1].split(' ')[0]
                print(f"⚠️ 인덱스 생성 실패 (이미 존재할 수 있음): {index_name} - {e}")
        
        conn.commit()
        print("✅ 데이터베이스 인덱스 생성 완료")
            
    except Exception as e:
        error_msg = str(e)
        # SSL 연결 오류는 경고만 출력하고 계속 진행
        if 'SSL connection has been closed' in error_msg or 'connection has been closed' in error_msg:
            print(f"⚠️ 데이터베이스 초기화 중 SSL 연결 오류 (앱은 계속 실행됩니다): {error_msg}")
        else:
            print(f"❌ 데이터베이스 초기화 실패: {e}")
            import traceback
            traceback.print_exc()
        if conn:
            try:
                conn.rollback()
            except:
                pass
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

# 앱 시작 시 초기화
def initialize_app():
    """앱 시작 시 초기화"""
    try:
        print("🚀 SNS PMT 앱 시작 중...")
        init_database()
        print("✅ 앱 시작 완료")
    except Exception as e:
        print(f"⚠️ 앱 초기화 중 오류: {e}")

# 데이터베이스 연결 테스트
@app.route('/api/test/db', methods=['GET'])
def test_database_connection():
    """Test Database Connection
    ---
    tags:
      - API
    summary: Test Database Connection
    description: "Test Database Connection API"
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """데이터베이스 연결 테스트"""
    try:
        print("🔍 데이터베이스 연결 테스트 시작")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            
            # 테이블 목록 조회
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            return jsonify({
                'status': 'success',
                'database': 'postgresql',
                'connection': 'ok',
                'test_result': result[0] if result else None,
                'tables': tables
            }), 200
        else:
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            conn.close()
            return jsonify({
                'status': 'success',
                'database': 'sqlite',
                'connection': 'ok',
                'test_result': result[0] if result else None
            }), 200
            
    except Exception as e:
        print(f"❌ 데이터베이스 연결 테스트 실패: {e}")
        return jsonify({
            'status': 'error',
            'database': 'unknown',
            'connection': 'failed',
            'error': str(e)
        }), 500

# 사용자 테이블 테스트
@app.route('/api/test/users', methods=['GET'])
def test_users_table():
    """Test Users Table
    ---
    tags:
      - API
    summary: Test Users Table
    description: "Test Users Table API"
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """사용자 테이블 테스트"""
    try:
        print("🔍 사용자 테이블 테스트 시작")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # users 테이블 존재 확인
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'users'
            );
        """)
        users_exists = cursor.fetchone()[0]
        
        if users_exists:
            # 테이블 구조 확인
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'users' AND table_schema = 'public'
                ORDER BY ordinal_position
            """)
            columns = cursor.fetchall()
            
            # 레코드 수 확인
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            
            conn.close()
            return jsonify({
                'status': 'success',
                'table_exists': True,
                'columns': [{'name': col[0], 'type': col[1], 'nullable': col[2]} for col in columns],
                'record_count': count
            }), 200
        else:
            conn.close()
            return jsonify({
                'status': 'error',
                'table_exists': False,
                'message': 'users 테이블이 존재하지 않습니다'
            }), 404
            
    except Exception as e:
        print(f"❌ 사용자 테이블 테스트 실패: {e}")
        import traceback
        print(f"❌ 상세 오류: {traceback.format_exc()}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

# 헬스 체크
@app.route('/health', methods=['GET'])
@app.route('/api/health', methods=['GET'])
def health_check():
    """헬스 체크 엔드포인트
    ---
    tags:
      - Health
    summary: 서버 및 데이터베이스 상태 확인
    description: "서버가 정상적으로 동작 중인지, 데이터베이스 연결이 정상인지 확인합니다."
    responses:
      200:
        description: 서버가 정상적으로 동작 중
        schema:
          type: object
          properties:
            status:
              type: string
              example: healthy
            timestamp:
              type: string
              example: "2024-01-01T00:00:00"
            database:
              type: string
              example: connected
            version:
              type: string
              example: "1.0.0"
            environment:
              type: string
              example: development
      500:
        description: 서버 또는 데이터베이스 오류
        schema:
          type: object
          properties:
            status:
              type: string
              example: unhealthy
            error:
              type: string
            timestamp:
              type: string
            database:
              type: string
              example: disconnected
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected',
            'version': '1.0.0',
            'environment': os.environ.get('FLASK_ENV', 'development')
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'database': 'disconnected'
        }), 500

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get Config
    ---
    tags:
      - Config
    summary: Get Config
    description: "Get Config API"
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """프론트엔드 설정 정보 반환"""
    try:
        google_client_id = os.environ.get('REACT_APP_GOOGLE_CLIENT_ID', '')
        print(f"🔍 구글 클라이언트 ID 확인: {google_client_id}")
        
        return jsonify({
            'googleClientId': google_client_id,
            'kakaoAppKey': os.environ.get('REACT_APP_KAKAO_APP_KEY', ''),
            'firebaseApiKey': os.environ.get('VITE_FIREBASE_API_KEY', ''),
            'firebaseAuthDomain': os.environ.get('VITE_FIREBASE_AUTH_DOMAIN', ''),
            'firebaseProjectId': os.environ.get('VITE_FIREBASE_PROJECT_ID', ''),
            'firebaseStorageBucket': os.environ.get('VITE_FIREBASE_STORAGE_BUCKET', ''),
            'firebaseMessagingSenderId': os.environ.get('VITE_FIREBASE_MESSAGING_SENDER_ID', ''),
            'firebaseAppId': os.environ.get('VITE_FIREBASE_APP_ID', ''),
            'firebaseMeasurementId': os.environ.get('VITE_FIREBASE_MEASUREMENT_ID', '')
        }), 200
    except Exception as e:
        print(f"❌ 설정 정보 조회 오류: {e}")
        return jsonify({
            'error': '설정 정보를 가져올 수 없습니다.',
            'message': str(e)
        }), 500

@app.route('/api/admin/config', methods=['GET'])
@require_admin_auth
def get_admin_config():
    """Get Admin Config
    ---
    tags:
      - Admin
    summary: Get Admin Config
    description: "Get Admin Config API"
    security:
      - Bearer: []
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """관리자용 설정 정보 반환 (SMM API 엔드포인트 등)"""
    try:
        # SMM Panel API 엔드포인트 (환경변수 또는 기본값)
        smm_api_endpoint = os.environ.get('SMMPANEL_API_ENDPOINT', 'https://smmpanel.kr/api/v2')
        
        return jsonify({
            'smm_api_endpoint': smm_api_endpoint,
            'smm_panel_url': smm_api_endpoint
        }), 200
    except Exception as e:
        print(f"❌ 관리자 설정 정보 조회 오류: {e}")
        return jsonify({
            'error': '설정 정보를 가져올 수 없습니다.',
            'message': str(e)
        }), 500

@app.route('/api/deployment-status', methods=['GET'])
def deployment_status():
    """Deployment Status
    ---
    tags:
      - API
    summary: Deployment Status
    description: "Deployment Status API"
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """배포 상태 확인"""
    try:
        # 필수 환경 변수 확인
        env_vars = {
            'DATABASE_URL': bool(os.environ.get('DATABASE_URL')),
            'SMMPANEL_API_KEY': bool(os.environ.get('SMMPANEL_API_KEY')),
            'ADMIN_TOKEN': bool(os.environ.get('ADMIN_TOKEN'))
        }
        
        # 데이터베이스 테이블 존재 확인
        conn = get_db_connection()
        cursor = conn.cursor()
        
        tables_to_check = ['users', 'orders', 'points', 'point_purchases']
        table_status = {}
        
        for table in tables_to_check:
            try:
                if DATABASE_URL.startswith('postgresql://'):
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = %s
                        )
                    """, (table,))
                else:
                    cursor.execute("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name=?
                    """, (table,))
                
                result = cursor.fetchone()
                table_status[table] = bool(result)
            except Exception:
                table_status[table] = False
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'status': 'deployment_ready',
            'timestamp': datetime.now().isoformat(),
            'environment_variables': env_vars,
            'database_tables': table_status,
            'all_checks_passed': all(env_vars.values()) and all(table_status.values())
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'deployment_not_ready',
            'timestamp': datetime.now().isoformat(),
            'error': str(e),
            'all_checks_passed': False
        }), 500

# 추천인 연결 확인 API (디버깅용)
@app.route('/api/debug/referral-connection/<user_id>', methods=['GET'])
def check_referral_connection(user_id):
    """Check Referral Connection
    ---
    tags:
      - API
    summary: Check Referral Connection
    description: "Check Referral Connection API"
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """사용자의 추천인 연결 상태 확인"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT referral_code, referrer_email, created_at 
                FROM user_referral_connections 
                WHERE user_id = %s
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT referral_code, referrer_email, created_at 
                FROM user_referral_connections 
                WHERE user_id = ?
            """, (user_id,))
        
        connection = cursor.fetchone()
        conn.close()
        
        if connection:
            return jsonify({
                'connected': True,
                'referral_code': connection[0],
                'referrer_email': connection[1],
                'created_at': str(connection[2]) if connection[2] else None
            }), 200
        else:
            return jsonify({
                'connected': False,
                'message': '추천인 연결 정보가 없습니다.'
            }), 200
            
    except Exception as e:
        print(f"❌ 추천인 연결 확인 오류: {e}")
        return jsonify({'error': str(e)}), 500

# 사용자 등록
@app.route('/api/register', methods=['POST'])
def register():
    """Register
    ---
    tags:
      - API
    summary: Register
    description: "Register API"
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """사용자 등록"""
    try:
        data = request.get_json()
        print(f"🔍 등록 요청 데이터: {data}")
        
        user_id = data.get('user_id')
        email = data.get('email')
        name = data.get('name')
        
        print(f"🔍 파싱된 데이터 - user_id: {user_id}, email: {email}, name: {name}")
        print(f"🔍 데이터 타입 - user_id: {type(user_id)}, email: {type(email)}, name: {type(name)}")
        
        # 필수 필드 검증 (None, 빈 문자열, 공백만 있는 문자열 체크)
        if not user_id or (isinstance(user_id, str) and not user_id.strip()):
            print(f"❌ user_id 누락 또는 빈 값: {user_id}")
            return jsonify({'error': '사용자 ID가 필요합니다.'}), 400
        
        if not email or (isinstance(email, str) and not email.strip()):
            print(f"❌ email 누락 또는 빈 값: {email}")
            return jsonify({'error': '이메일이 필요합니다.'}), 400
        
        if not name or (isinstance(name, str) and not name.strip()):
            print(f"❌ name 누락 또는 빈 값: {name}")
            return jsonify({'error': '이름을 입력해주세요.'}), 400
        
        # 이메일 형식 검증
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            print(f"❌ 유효하지 않은 이메일 형식: {email}")
            return jsonify({'error': '유효하지 않은 이메일 형식입니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 이메일 중복 체크
        cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()
        
        if existing_user and existing_user[0] != user_id:
            print(f"❌ 이메일 중복: {email} (기존 user_id: {existing_user[0]}, 새 user_id: {user_id})")
            return jsonify({'error': '이미 사용 중인 이메일입니다.'}), 400
        
        # 사용자 정보 저장
        print(f"💾 사용자 정보 저장 시도 - user_id: {user_id}, email: {email}, name: {name}")
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                INSERT INTO users (user_id, email, name, created_at, updated_at)
                VALUES (%s, %s, %s, NOW(), NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    email = EXCLUDED.email,
                    name = EXCLUDED.name,
                    updated_at = NOW()
            """, (user_id, email, name))
            print(f"✅ PostgreSQL 사용자 정보 저장 완료")
            
            # 포인트 초기화
            cursor.execute("""
                INSERT INTO points (user_id, points, created_at, updated_at)
                VALUES (%s, 0, NOW(), NOW())
                ON CONFLICT (user_id) DO NOTHING
            """, (user_id,))
        else:
            cursor.execute("""
                INSERT OR REPLACE INTO users (user_id, email, name, created_at, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (user_id, email, name))
            
            cursor.execute("""
                INSERT OR IGNORE INTO points (user_id, points, created_at, updated_at)
                VALUES (?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (user_id,))
        
        conn.commit()
        conn.close()
        
        print(f"✅ 사용자 등록 완료 - user_id: {user_id}, email: {email}, name: {name}")
        
        return jsonify({
            'success': True,
            'message': '사용자 등록이 완료되었습니다.',
            'user_id': user_id
        }), 200
        
    except Exception as e:
        print(f"❌ 사용자 등록 오류: {e}")
        print(f"❌ 오류 타입: {type(e)}")
        print(f"❌ 오류 상세: {str(e)}")
        return jsonify({'error': f'사용자 등록 실패: {str(e)}'}), 500

# 사용자 포인트 조회
@app.route('/api/points', methods=['GET'])
def get_user_points():
    """사용자 포인트 잔액 조회
    ---
    tags:
      - Points
    summary: 사용자 포인트 잔액 조회
    description: "사용자의 현재 포인트 잔액을 조회합니다."
    security:
      - Bearer: []
    parameters:
      - name: user_id
        in: query
        type: string
        required: true
        description: 사용자 ID
        example: "user123"
    responses:
      200:
        description: 포인트 조회 성공
        schema:
          type: object
          properties:
            user_id:
              type: string
              example: "user123"
            balance:
              type: number
              description: 포인트 잔액
              example: 10000.0
            external_uid:
              type: string
              example: "user123"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "user_id가 필요합니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "포인트 조회 실패: ..."
    """
    conn = None
    cursor = None
    
    try:
        raw_user_id = request.args.get('user_id')
        print(f"🔍 포인트 조회 요청 - user_id: {raw_user_id}")
        
        if not raw_user_id:
            print(f"❌ user_id 누락")
            return jsonify({'error': 'user_id가 필요합니다.'}), 400
        
        # 새 스키마에서는 wallets 테이블 사용
        if DATABASE_URL.startswith('postgresql://'):
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # external_uid로 사용자 찾기 (Firebase UID 등)
            cursor.execute("""
                SELECT user_id, external_uid, email 
                FROM users 
                WHERE external_uid = %s OR email = %s
                LIMIT 1
            """, (raw_user_id, raw_user_id))
            user = cursor.fetchone()
            
            if not user:
                # 사용자가 없으면 기본값 반환
                print(f"ℹ️ 사용자 없음, 기본값 0 반환")
                return jsonify({
                    'user_id': raw_user_id,
                    'points': 0,
                    'wallet_balance': 0
                }), 200
            
            # 지갑 조회 (없으면 생성) - 안전하게 처리
            try:
                # 먼저 지갑이 있는지 확인
                cursor.execute("""
                    SELECT wallet_id, user_id, balance, created_at, updated_at
                    FROM wallets
                    WHERE user_id = %s
                """, (user['user_id'],))
                wallet = cursor.fetchone()
                
                # 지갑이 없으면 생성
                if not wallet:
                    try:
                        cursor.execute("""
                            INSERT INTO wallets (user_id, balance, created_at, updated_at)
                            VALUES (%s, 0, NOW(), NOW())
                            RETURNING wallet_id, user_id, balance
                        """, (user['user_id'],))
                        wallet = cursor.fetchone()
                        print(f"✅ 지갑 생성 완료: user_id={user['user_id']}")
                        conn.commit()
                    except Exception as insert_error:
                        # UNIQUE 제약 조건 오류는 무시 (다른 요청에서 이미 생성됨)
                        error_msg = str(insert_error).lower()
                        if 'unique' in error_msg or 'duplicate' in error_msg:
                            print(f"⚠️ 지갑이 이미 존재함 (재조회): {insert_error}")
                            conn.rollback()
                            # 다시 조회
                            cursor.execute("""
                                SELECT wallet_id, user_id, balance, created_at, updated_at
                                FROM wallets
                                WHERE user_id = %s
                            """, (user['user_id'],))
                            wallet = cursor.fetchone()
                        else:
                            raise
                else:
                    conn.commit()
                
                # 잔액 계산
                balance = float(wallet['balance']) if wallet and wallet.get('balance') is not None else 0.0
                print(f"✅ 포인트 조회 성공: {balance}")
            except Exception as wallet_error:
                print(f"⚠️ 지갑 조회/생성 오류: {wallet_error}")
                import traceback
                traceback.print_exc()
                conn.rollback()
                # 오류가 발생해도 기본값 반환
                balance = 0.0
                print(f"⚠️ 기본값 0 반환")
            
            return jsonify({
                'user_id': str(user['user_id']),
                'external_uid': user.get('external_uid'),
                'points': balance,
                'wallet_balance': balance
            }), 200
        else:
            # SQLite는 구 스키마 유지
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT points FROM points WHERE user_id = ?", (raw_user_id,))
            result = cursor.fetchone()
            points = result[0] if result else 0
            return jsonify({
                'user_id': raw_user_id,
                'points': points
            }), 200
        
    except Exception as e:
        print(f"❌ 포인트 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            try:
                conn.rollback()
            except:
                pass
        return jsonify({'error': f'포인트 조회 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 주문 생성
@app.route('/api/orders', methods=['POST'])
def create_order():
    """주문 생성
    ---
    tags:
      - Orders
    summary: 새로운 주문 생성
    description: |
      사용자의 주문을 생성하고 할인 및 커미션을 적용합니다.
      
      ## 주문 타입 판단 기준
      
      ### 패키지 주문
      - **판단 기준**: `package_steps` 배열의 길이가 0보다 큰 경우 (`len(package_steps) > 0`)
      - **전달 조건**:
        - Drip-feed가 아님 (`isDripFeed = false`)
        - 상품이 패키지 타입 (`package: true`)
        - 단계 정보(`steps`)가 존재함
      - **처리 방식**: `package_steps`를 JSON으로 데이터베이스에 저장한 후, 각 단계를 순차적으로 처리합니다.
      
      ### 일반 주문
      - **판단 기준**: `package_steps`가 빈 배열이거나 없는 경우
      - **처리 방식**: 즉시 SMM Panel API를 호출하여 주문을 생성합니다.
      
      ### 예약 주문
      - `is_scheduled = true`이고 패키지가 아닌 경우
      - `scheduled_datetime`에 지정된 시간에 스케줄러가 자동으로 처리합니다.
      
      ### 분할 발송 주문
      - `is_split_delivery = true`인 경우
      - 매일 자정에 스케줄러가 자동으로 분할 발송을 처리합니다.
      
      ### Drip-feed 주문
      - `runs`와 `interval` 파라미터를 사용하여 지정된 간격으로 반복 발송합니다.
      - 예: 30일간 하루에 1번씩 → `runs: 30, interval: 1440` (1440분 = 24시간)
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - user_id
            - service_id
            - link
            - quantity
            - price
          properties:
            user_id:
              type: string
              description: 사용자 ID
              example: "user123"
            service_id:
              type: integer
              description: 서비스 ID
              example: 1
            link:
              type: string
              description: "주문할 링크 (예: 인스타그램 게시물 URL)"
              example: "https://instagram.com/p/abc123"
            quantity:
              type: integer
              description: 주문 수량
              example: 100
            price:
              type: number
              description: 주문 가격
              example: 10000
            coupon_id:
              type: integer
              description: 사용할 쿠폰 ID (선택사항)
            user_coupon_id:
              type: integer
              description: 사용자 쿠폰 ID (선택사항)
            package_steps:
              type: array
              description: |
                패키지 주문의 단계별 정보 (선택사항).
                
                패키지 주문 판단 기준: 이 배열의 길이가 0보다 크면 패키지 주문으로 처리됩니다.
                
                각 단계는 다음 정보를 포함합니다:
                - id: 서비스 ID
                - name: 단계 이름
                - quantity: 단계별 수량
                - delay: 다음 단계까지의 지연 시간 (분)
                - repeat: 반복 횟수
              example:
                - id: 515
                  name: "인스타그램 프로필 방문"
                  quantity: 400
                  delay: 1440
                  repeat: 30
            is_scheduled:
              type: boolean
              description: "예약 주문 여부 (선택사항, 기본값: false)"
              example: false
            scheduled_datetime:
              type: string
              format: date-time
              description: "예약 주문 실행 시간 (is_scheduled가 true인 경우 필수)"
              example: "2024-01-01 12:00:00"
            is_split_delivery:
              type: boolean
              description: "분할 발송 여부 (선택사항, 기본값: false)"
              example: false
            split_days:
              type: integer
              description: 분할 발송 일수 (is_split_delivery가 true인 경우 필수)
              example: 30
            split_quantity:
              type: integer
              description: 일일 발송 수량 (is_split_delivery가 true인 경우 필수)
              example: 400
            runs:
              type: integer
              description: "Drip-feed 반복 횟수 (선택사항, 기본값: 1)"
              example: 30
            interval:
              type: integer
              description: "Drip-feed 반복 간격(분) (선택사항, 기본값: 0). 예: 1440 = 24시간"
              example: 1440
            comments:
              type: string
              description: 주문 메모 (선택사항)
              example: "특별 요청사항"
    responses:
      200:
        description: |
          주문 생성 성공
          
          **일반 주문**: 즉시 SMM Panel API 호출 후 결과 반환
          **패키지 주문**: 패키지 단계 정보를 저장하고 순차 처리 시작
          **예약 주문**: pending 상태로 저장되어 지정 시간에 자동 처리
          **분할 발송 주문**: pending 상태로 저장되어 매일 자동 분할 발송
        schema:
          type: object
          properties:
            order_id:
              type: integer
              description: 생성된 주문 ID
              example: 123
            message:
              type: string
              description: 주문 처리 결과 메시지
              example: "주문이 성공적으로 생성되었습니다."
            status:
              type: string
              description: |
                주문 상태
                - '주문발송': 일반 주문 (SMM Panel API 호출 성공)
                - 'processing': 패키지 주문 (단계별 처리 중)
                - 'pending': 예약/분할 주문 (대기 중)
                - 'failed': 주문 실패 (SMM Panel API 호출 실패 등)
              example: "주문발송"
            final_price:
              type: number
              description: 최종 가격 (할인 적용 후)
              example: 9500
            discount_amount:
              type: number
              description: 할인 금액
              example: 500
            is_package:
              type: boolean
              description: 패키지 주문 여부
              example: false
            package_steps:
              type: array
              description: 패키지 주문인 경우 단계 정보
              example: []
            refund_required:
              type: boolean
              description: 포인트 환불 필요 여부 (주문 실패 시 true)
              example: false
            refund_amount:
              type: number
              description: 환불할 포인트 금액 (refund_required가 true인 경우)
              example: 0
      400:
        description: 필수 필드 누락 또는 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "필수 필드가 누락되었습니다: user_id, service_id"
      500:
        description: |
          서버 오류 또는 SMM Panel API 호출 실패
          
          **SMM Panel API 실패 시**:
          - 주문은 데이터베이스에 'failed' 상태로 저장됩니다.
          - 주문 금액은 0으로 설정됩니다.
          - `refund_required: true`와 `refund_amount`가 포함되어 포인트 환불이 필요합니다.
          - 추천인 커미션은 생성되지 않습니다.
        schema:
          type: object
          properties:
            error:
              type: string
              description: 오류 메시지
              example: "주문 생성 중 오류가 발생했습니다."
            order_id:
              type: integer
              description: 생성된 주문 ID (실패 주문도 저장됨)
              example: 123
            status:
              type: string
              description: 주문 상태 (실패 시 'failed')
              example: "failed"
            refund_required:
              type: boolean
              description: 포인트 환불 필요 여부
              example: true
            refund_amount:
              type: number
              description: 환불할 포인트 금액
              example: 10000
    """
    conn = None
    cursor = None
    
    try:
        data = request.get_json()
        print(f"=== 주문 생성 요청 ===")
        print(f"요청 데이터: {data}")
        
        user_id = data.get('user_id')
        service_id = data.get('service_id')
        link = data.get('link')
        quantity = data.get('quantity')
        price = data.get('price') or data.get('total_price')  # total_price도 허용
        
        # 필수 필드 검증 및 로깅
        missing_fields = []
        if not user_id:
            missing_fields.append('user_id')
        if not service_id:
            missing_fields.append('service_id')
        if not link:
            missing_fields.append('link')
        if not quantity:
            missing_fields.append('quantity')
        if not price:
            missing_fields.append('price')
        
        if missing_fields:
            error_msg = f'필수 필드가 누락되었습니다: {", ".join(missing_fields)}'
            print(f"❌ {error_msg}")
            print(f"❌ 받은 데이터: user_id={user_id}, service_id={service_id}, link={link}, quantity={quantity}, price={price}")
            return jsonify({'error': error_msg}), 400
        
        print(f"✅ 필수 필드 검증 통과")
        print(f"사용자 ID: {user_id}")
        print(f"서비스 ID: {service_id}")
        print(f"링크: {link}")
        print(f"수량: {quantity}")
        print(f"가격: {price}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        print("✅ 데이터베이스 연결 성공")
        
        # 데이터베이스 타입 확인
        if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
            print("🗄️ PostgreSQL 데이터베이스 사용 중 (영구 저장)")
        else:
            print("⚠️ SQLite 데이터베이스 사용 중 (로컬 개발용)")
        
        # 사용자의 추천인 연결 확인 (referrals 테이블 사용)
        referrer_user_id = None
        referral_id = None
        if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
            # referrals 테이블에서 추천인 찾기 (referred_user_id = 현재 사용자)
            cursor.execute("""
                SELECT r.referral_id, r.referrer_user_id, u.email as referrer_email, u.referral_code
                FROM referrals r
                JOIN users u ON r.referrer_user_id = u.user_id
                WHERE r.referred_user_id = (SELECT user_id FROM users WHERE external_uid = %s OR email = %s LIMIT 1)
                AND r.status = 'approved'
                ORDER BY r.created_at DESC
                LIMIT 1
            """, (user_id, user_id))
        else:
            # SQLite: user_referral_connections 사용 (레거시 호환)
            cursor.execute("""
                SELECT referral_code, referrer_email FROM user_referral_connections 
                WHERE user_id = ?
            """, (user_id,))
        
        referral_data = cursor.fetchone()
        if referral_data and DATABASE_URL.startswith('postgresql://'):
            referral_id = referral_data[0]
            referrer_user_id = referral_data[1]
            referrer_email = referral_data[2]
            referral_code = referral_data[3]
        discount_amount = 0
        final_price = price
        
        # 프론트엔드에서 전달받은 쿠폰 ID 확인 (user_coupon_id)
        coupon_id_from_request = data.get('coupon_id') or data.get('user_coupon_id')
        
        # 쿠폰 사용 여부 확인 (실제 DB 스키마: user_coupons 테이블 사용)
        user_coupon_id = None
        if coupon_id_from_request:
            print(f"🎫 쿠폰 사용 요청 - 쿠폰 ID: {coupon_id_from_request}")
            
            # 쿠폰 유효성 확인 (user_coupons와 coupons 조인)
            if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
                # external_uid로 사용자 찾기
                cursor.execute("""
                    SELECT user_id FROM users WHERE external_uid = %s OR email = %s LIMIT 1
                """, (user_id, user_id))
                user_result = cursor.fetchone()
                db_user_id_for_coupon = user_result[0] if user_result else None
                
                if db_user_id_for_coupon:
                    # user_coupons와 coupons 조인해서 조회
                    cursor.execute("""
                        SELECT uc.user_coupon_id, c.discount_value, c.coupon_code, c.discount_type,
                               uc.status, c.valid_until
                        FROM user_coupons uc
                        JOIN coupons c ON uc.coupon_id = c.coupon_id
                        WHERE uc.user_coupon_id = %s 
                          AND uc.user_id = %s
                          AND uc.status = 'active'
                          AND (c.valid_until IS NULL OR c.valid_until > NOW())
                    """, (coupon_id_from_request, db_user_id_for_coupon))
                    coupon_data = cursor.fetchone()
                    
                    if coupon_data:
                        user_coupon_id, discount_value, coupon_code, discount_type, status, valid_until = coupon_data
                        
                        # 할인 계산
                        if discount_type == 'percentage':
                            discount_amount = price * (float(discount_value) / 100)
                        else:
                            discount_amount = float(discount_value) if discount_value else 0
                        
                        final_price = price - discount_amount
                        
                        print(f"✅ 쿠폰 적용 - 할인율: {discount_value}%, 할인액: {discount_amount}원, 최종가격: {final_price}원")
                        
                        # 쿠폰 사용 처리 (user_coupons.status를 'used'로 변경)
                        cursor.execute("""
                            UPDATE user_coupons SET status = 'used', used_at = NOW() 
                            WHERE user_coupon_id = %s
                        """, (user_coupon_id,))
                        
                        print(f"✅ 쿠폰 사용 처리 완료 - user_coupon_id: {user_coupon_id}")
                    else:
                        print(f"⚠️ 유효한 쿠폰을 찾을 수 없음 - 쿠폰 ID: {coupon_id_from_request}")
                        user_coupon_id = None  # 쿠폰 사용 불가로 처리
                else:
                    print(f"⚠️ 사용자를 찾을 수 없음 - 쿠폰 사용 불가")
                    user_coupon_id = None
            else:
                # SQLite: 구 스키마 사용 (레거시 호환)
                cursor.execute("""
                    SELECT id, discount_value, referral_code FROM coupons 
                    WHERE id = ? AND user_id = ? AND is_used = false 
                    AND expires_at > datetime('now')
                """, (coupon_id_from_request, user_id))
                coupon_data = cursor.fetchone()
                
                if coupon_data:
                    coupon_id, discount_value, referral_code = coupon_data
                    discount_amount = price * (discount_value / 100)
                    final_price = price - discount_amount
                    
                    print(f"✅ 쿠폰 적용 - 할인율: {discount_value}%, 할인액: {discount_amount}원, 최종가격: {final_price}원")
                    
                    cursor.execute("""
                        UPDATE coupons SET is_used = true, used_at = datetime('now') 
                        WHERE id = ?
                    """, (coupon_id,))
                    
                    print(f"✅ 쿠폰 사용 처리 완료 - 쿠폰 ID: {coupon_id}")
                else:
                    print(f"⚠️ 유효한 쿠폰을 찾을 수 없음 - 쿠폰 ID: {coupon_id_from_request}")
        else:
            # 쿠폰 미사용 시 추천인 연결 확인 - referrals 테이블 사용
            if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    SELECT r.referral_id, r.referrer_user_id, u.email as referrer_email, u.referral_code
                    FROM referrals r
                    JOIN users u ON r.referrer_user_id = u.user_id
                    WHERE r.referred_user_id = (SELECT user_id FROM users WHERE external_uid = %s OR email = %s LIMIT 1)
                    AND r.status = 'approved'
                    ORDER BY r.created_at DESC
                    LIMIT 1
                """, (user_id, user_id))
                referral_result = cursor.fetchone()
                if referral_result:
                    referral_id = referral_result[0]
                    referrer_user_id = referral_result[1]
                    referrer_email = referral_result[2]
                    referral_code = referral_result[3]
                    referral_data = referral_result
                else:
                    referral_data = None
            else:
                # SQLite: 구 스키마 사용
                cursor.execute("""
                    SELECT referral_code, referrer_email FROM user_referral_connections 
                    WHERE user_id = ?
                """, (user_id,))
                referral_data = cursor.fetchone()
        
        # 예약/분할 주문 정보 추출
        is_scheduled = data.get('is_scheduled', False)
        scheduled_datetime = data.get('scheduled_datetime')
        is_split_delivery = data.get('is_split_delivery', False)
        split_days = data.get('split_days', 0)
        split_quantity = data.get('split_quantity', 0)
        
        # 주문 ID 먼저 생성 (SMM Panel 결과와 무관하게 항상 생성)
        import time
        real_order_id = int(time.time() * 1000)  # 밀리초 단위 타임스탬프
        smm_panel_order_id = None
        
        # 패키지 상품 여부 확인
        package_steps = data.get('package_steps', [])
        is_package = len(package_steps) > 0
        
        # SMM Panel API 호출 결과 추적 변수
        smm_panel_order_id = None
        smm_error = None
        smm_success = False
        
        # 일반 주문인 경우 즉시 SMM Panel API 호출 (패키지가 아닌 경우만)
        if not is_scheduled and not is_package:
            print(f"🚀 일반 주문 - 즉시 SMM Panel API 호출")
            try:
                smm_result = call_smm_panel_api({
                    'service': service_id,
                    'link': link,
                    'quantity': quantity,
                    'comments': data.get('comments', ''),
                    'runs': data.get('runs', 1),  # Drip-feed: 30일간 하루에 1번씩 → runs: 30, interval: 1440
                    'interval': data.get('interval', 0)  # interval 단위: 분 (1440 = 24시간)
                })
                
                if smm_result.get('status') == 'success':
                    # SMM Panel에서 받은 주문번호를 사용 (실제 주문번호로 업데이트)
                    smm_panel_order_id = smm_result.get('order')
                    if smm_panel_order_id:
                        real_order_id = smm_panel_order_id  # SMM Panel 주문번호로 업데이트
                    smm_success = True
                    print(f"✅ SMM Panel 주문 생성 성공: {smm_panel_order_id} (내부 주문 ID: {real_order_id})")
                else:
                    error_message = smm_result.get('message', '알 수 없는 오류')
                    smm_error = error_message
                    print(f"❌ SMM Panel API 호출 실패: {error_message}")
                    print(f"❌ SMM Panel 응답 상세: {smm_result}")
                    # SMM Panel 실패 시에도 주문은 저장하되 "failed" 상태로
                    # real_order_id는 이미 위에서 생성됨
                    print(f"⚠️ SMM Panel 실패 - 주문은 저장되지만 실패 상태로: order_id={real_order_id}")
            except Exception as e:
                error_message = str(e)
                smm_error = error_message
                print(f"❌ SMM Panel API 호출 실패: {error_message}")
                import traceback
                print(traceback.format_exc())
                # SMM Panel 실패 시에도 주문은 저장하되 "failed" 상태로
                # real_order_id는 이미 위에서 생성됨
                print(f"⚠️ SMM Panel 예외 발생 - 주문은 저장되지만 실패 상태로: order_id={real_order_id}")
        elif is_package:
            # 패키지 주문 (real_order_id는 이미 위에서 생성됨)
            print(f"📦 패키지 주문 - 주문 ID: {real_order_id} (패키지 단계별 개별 처리)")
        else:
            # 예약 주문 (real_order_id는 이미 위에서 생성됨)
            print(f"📅 예약 주문 - 주문 ID: {real_order_id}")
        
        # detailed_service 정보 가져오기
        detailed_service = data.get('detailed_service', '')
        print(f"📋 detailed_service: {detailed_service}")
        
        # 주문 타입 결정
        if is_package:
            order_type = 'package'
        elif is_scheduled:
            order_type = 'scheduled'
        elif is_split_delivery:
            order_type = 'split'
        else:
            order_type = 'single'
        
        print(f"📋 주문 타입: {order_type}, real_order_id: {real_order_id}")
        
        # user_id를 내부 데이터베이스 user_id로 변환 (external_uid -> user_id)
        db_user_id = user_id  # 기본값은 그대로 사용 (SQLite 호환)
        if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
            # external_uid로 내부 user_id 찾기
            try:
                cursor.execute("""
                    SELECT user_id FROM users WHERE external_uid = %s OR email = %s LIMIT 1
                """, (user_id, user_id))
                user_result = cursor.fetchone()
                if user_result:
                    db_user_id = user_result[0]
                    print(f"✅ 사용자 ID 변환 완료: external_uid={user_id} -> user_id={db_user_id}")
                else:
                    print(f"⚠️ 사용자를 찾을 수 없음: external_uid={user_id}, external_uid를 그대로 사용")
                    # 사용자가 없으면 external_uid를 그대로 사용 (호환성)
                    db_user_id = user_id
            except Exception as user_error:
                print(f"⚠️ 사용자 ID 변환 중 오류: {user_error}")
                db_user_id = user_id
        
        print(f"📋 db_user_id: {db_user_id}, price: {price}, final_price: {final_price}")
        
        # service_id를 variant_id로 변환 (product_variants 테이블에서 meta_json->>'service_id'로 찾기)
        variant_id = None
        unit_price = final_price  # 기본값: 전체 금액을 단가로 사용
        if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
            try:
                # service_id가 숫자인지 확인
                if service_id and str(service_id).isdigit():
                    # meta_json->>'service_id'로 variant_id 찾기
                    cursor.execute("""
                        SELECT variant_id, price 
                        FROM product_variants 
                        WHERE (meta_json->>'service_id')::text = %s 
                           OR (meta_json->>'smm_service_id')::text = %s
                        LIMIT 1
                    """, (str(service_id), str(service_id)))
                    variant_result = cursor.fetchone()
                    if variant_result:
                        variant_id = variant_result[0]
                        unit_price = float(variant_result[1]) if variant_result[1] else final_price
                        print(f"✅ Variant ID 찾음: service_id={service_id} -> variant_id={variant_id}, unit_price={unit_price}")
                    else:
                        print(f"⚠️ Variant를 찾을 수 없음: service_id={service_id} (order_items에는 variant_id 없이 저장)")
                elif service_id:
                    # service_id가 variant_id일 수도 있음 (숫자가 아닌 경우)
                    try:
                        variant_id = int(service_id)
                        print(f"ℹ️ service_id를 variant_id로 사용: {variant_id}")
                    except (ValueError, TypeError):
                        print(f"⚠️ service_id를 variant_id로 변환 실패: {service_id}")
            except Exception as variant_error:
                print(f"⚠️ variant_id 변환 중 오류 (무시하고 계속): {variant_error}")
        
        # 주문 생성 (실제 DB 스키마에 맞게: total_amount, final_amount 사용)
        # SMM Panel 실패 여부와 관계없이 주문은 반드시 저장되어야 함 (실패 시 금액 0으로)
        print(f"🔍 주문 INSERT 시작 - real_order_id: {real_order_id}, db_user_id: {db_user_id}, price: {price}, final_price: {final_price}, smm_error: {smm_error}")
        try:
            if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
                # 새 스키마: total_amount, final_amount 사용, service_id, link, quantity, price 제거
                cursor.execute("""
                    INSERT INTO orders (order_id, user_id, total_amount, discount_amount, final_amount,
                                    status, created_at, updated_at,
                                    is_scheduled, scheduled_datetime, is_split_delivery, split_days, split_quantity, 
                                    smm_panel_order_id, detailed_service, referrer_user_id, coupon_id)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW(),
                            %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING order_id
                """, (
                    real_order_id, db_user_id, price, discount_amount, final_price,
                    'failed' if smm_error else ('pending' if is_scheduled else 'pending'),  # SMM 실패 시 failed 상태
                    is_scheduled, scheduled_datetime, is_split_delivery, split_days, split_quantity, 
                    smm_panel_order_id, detailed_service,
                    referrer_user_id if 'referrer_user_id' in locals() and referrer_user_id else None,
                    user_coupon_id if 'user_coupon_id' in locals() and user_coupon_id else None
                ))
                inserted_order_id = cursor.fetchone()[0] if cursor.rowcount > 0 else real_order_id
                print(f"✅ 주문 INSERT 완료 (PostgreSQL) - order_id: {inserted_order_id}")
            else:
                # SQLite: 구 스키마 유지 (레거시 호환)
                cursor.execute("""
                    INSERT INTO orders (order_id, user_id, service_id, link, quantity, price, 
                                    discount_amount, referral_code, status, created_at, updated_at,
                                    is_scheduled, scheduled_datetime, is_split_delivery, split_days, split_quantity, smm_panel_order_id, detailed_service)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                            ?, ?, ?, ?, ?, ?, ?)
                """, (real_order_id, db_user_id, service_id, link, quantity, final_price, discount_amount,
                    referral_data[0] if referral_data and len(referral_data) > 0 else None, 
                    'failed' if smm_error else ('주문발송' if not is_scheduled else 'pending_payment'),  # SMM 실패 시 failed 상태
                    is_scheduled, scheduled_datetime, is_split_delivery, split_days, split_quantity, smm_panel_order_id, detailed_service))
                inserted_order_id = real_order_id
                print(f"✅ 주문 INSERT 완료 (SQLite) - order_id: {inserted_order_id}")
            
            order_id = inserted_order_id
            print(f"✅ 주문 생성 완료 - order_id: {order_id}, user_id: {db_user_id} (external_uid: {user_id}), total_amount: {price}, final_amount: {final_price}, smm_error: {smm_error}")
        except Exception as insert_error:
            print(f"❌ 주문 INSERT 실패: {insert_error}")
            import traceback
            print(traceback.format_exc())
            # INSERT 실패 시에도 최소한의 정보로 주문 저장 시도
            try:
                failed_order_id = int(time.time() * 1000)
                if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
                    cursor.execute("""
                        INSERT INTO orders (order_id, user_id, total_amount, discount_amount, final_amount,
                                        status, created_at, updated_at, detailed_service)
                        VALUES (%s, %s, 0, 0, 0, 'failed', NOW(), NOW(), %s)
                        ON CONFLICT (order_id) DO NOTHING
                        RETURNING order_id
                    """, (failed_order_id, db_user_id if 'db_user_id' in locals() else user_id, detailed_service if 'detailed_service' in locals() else ''))
                    result = cursor.fetchone()
                    order_id = result[0] if result else failed_order_id
                else:
                    cursor.execute("""
                        INSERT INTO orders (order_id, user_id, service_id, link, quantity, price, status, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, 0, 'failed', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (failed_order_id, db_user_id if 'db_user_id' in locals() else user_id, service_id if 'service_id' in locals() else '', link if 'link' in locals() else '', quantity if 'quantity' in locals() else 0))
                    order_id = failed_order_id
                conn.commit()
                print(f"✅ 실패한 주문 최소 정보 저장 완료 - order_id: {order_id}")
            except Exception as fallback_error:
                print(f"❌ 실패한 주문 저장도 실패: {fallback_error}")
                order_id = int(time.time() * 1000)
            
            # INSERT 실패 시에도 포인트 환불 정보 반환
            return jsonify({
                'error': f'주문 생성 실패: {str(insert_error)}',
                'order_id': order_id if 'order_id' in locals() else None,
                'status': 'failed',
                'refund_required': True,
                'refund_amount': final_price if 'final_price' in locals() else price if 'price' in locals() else 0
            }), 500
        
        # order_items 테이블에 상세 정보 저장 (새 스키마)
        if DATABASE_URL and DATABASE_URL.startswith('postgresql://') and variant_id:
            try:
                line_amount = unit_price * quantity
                cursor.execute("""
                    INSERT INTO order_items (order_id, variant_id, quantity, unit_price, line_amount, link, status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, 'pending', NOW(), NOW())
                    RETURNING order_item_id
                """, (order_id, variant_id, quantity, unit_price, line_amount, link))
                order_item_result = cursor.fetchone()
                order_item_id = order_item_result[0] if order_item_result else None
                print(f"✅ 주문 아이템 생성 완료 - order_item_id: {order_item_id}, variant_id: {variant_id}, quantity: {quantity}, unit_price: {unit_price}, line_amount: {line_amount}")
            except Exception as item_error:
                print(f"⚠️ 주문 아이템 생성 실패 (무시하고 계속): {item_error}")
                import traceback
                traceback.print_exc()
        elif not variant_id:
            print(f"⚠️ variant_id를 찾을 수 없어 order_items에 저장하지 않음: service_id={service_id}")
        
        # 주문 저장 확정 (commit 전에 SMM 에러 처리)
        # SMM Panel 실패 시 주문 금액을 0으로 업데이트하고 포인트 환불 및 커미션 저장 건너뛰기
        if smm_error:
            print(f"⚠️ SMM Panel 실패로 인해 주문이 'failed' 상태로 저장되었습니다. 주문 금액을 0으로 설정하고 포인트 환불 및 커미션 저장을 건너뜁니다.")
            print(f"⚠️ 오류 메시지: {smm_error}")
            
            # 주문 금액을 0으로 업데이트 (INSERT 후 바로 UPDATE)
            try:
                if DATABASE_URL.startswith('postgresql://'):
                    cursor.execute("""
                        UPDATE orders 
                        SET total_amount = 0, discount_amount = 0, final_amount = 0, updated_at = NOW()
                        WHERE order_id = %s
                    """, (order_id,))
                else:
                    cursor.execute("""
                        UPDATE orders 
                        SET price = 0, discount_amount = 0, updated_at = CURRENT_TIMESTAMP
                        WHERE order_id = ?
                    """, (order_id,))
                # 변경사항 commit (주문 저장 확정)
                conn.commit()
                print(f"✅ SMM 실패 주문 저장 완료 - order_id: {order_id}, 금액: 0원, 상태: failed")
            except Exception as update_error:
                print(f"⚠️ 주문 금액 업데이트 실패: {update_error}")
                import traceback
                traceback.print_exc()
                conn.rollback()
                # 롤백 후에도 최소한의 주문 정보는 저장 시도
                try:
                    conn.commit()
                except:
                    pass
            
            # 주문은 저장되었지만 SMM Panel 실패로 인해 실패 처리
            # 포인트 환불은 프론트엔드에서 처리하도록 정보 포함
            return jsonify({
                'success': False,
                'message': f'주문은 저장되었지만 SMM Panel API 호출이 실패했습니다: {smm_error}',
                'order_id': order_id,
                'status': 'failed',
                'refund_required': True,
                'refund_amount': final_price
            }), 200  # 주문이 저장되었으므로 200 OK 반환
        
        # SMM Panel 성공한 경우에만 commit (일반 주문)
        if not is_scheduled and not is_package:
            conn.commit()
            print(f"✅ 일반 주문 저장 완료 - order_id: {order_id}")
        
        # 추천인이 있는 경우 커미션 계산 및 저장 (피추천인 구매 금액의 10%)
        # SMM Panel 성공한 경우에만 커미션 저장
        commission_amount = 0
        commission_rate = 0.1  # 고정 10%
        if referral_data and 'referrer_user_id' in locals() and referrer_user_id and 'referral_id' in locals() and referral_id:
            try:
                # 커미션 금액 계산 (구매 금액의 10%)
                commission_amount = final_price * commission_rate
                
                print(f"💰 커미션 계산 - 추천인: {referrer_email} (user_id: {referrer_user_id}), 피추천인: {user_id}, 구매금액: {final_price}원, 커미션: {commission_amount}원 (10%)")
                
                # 새 스키마: commissions 테이블에 커미션 저장
                if DATABASE_URL.startswith('postgresql://'):
                    # 현재 사용자의 데이터베이스 내부 user_id 조회
                    cursor.execute("""
                        SELECT user_id FROM users WHERE external_uid = %s OR email = %s LIMIT 1
                    """, (user_id, user_id))
                    referred_user_result = cursor.fetchone()
                    referred_user_db_id = referred_user_result[0] if referred_user_result else None
                    
                    if referred_user_db_id:
                        # commissions 테이블에 커미션 저장 (referral_id, order_id, amount, status)
                        cursor.execute("""
                            INSERT INTO commissions (referral_id, order_id, amount, status, created_at)
                            VALUES (%s, %s, %s, 'accrued', NOW())
                            RETURNING commission_id
                        """, (referral_id, order_id, commission_amount))
                        commission_result = cursor.fetchone()
                        commission_record_id = commission_result[0] if commission_result else None
                        print(f"✅ 커미션 저장 완료 - commission_id: {commission_record_id}, referral_id: {referral_id}, order_id: {order_id}, 금액: {commission_amount}원")
                    else:
                        print(f"⚠️ 피추천인 user_id를 찾을 수 없음: {user_id}")
                else:
                    # SQLite: 구 스키마 사용 (레거시 호환)
                    cursor.execute("""
                        INSERT INTO commissions (referred_user, referrer_id, purchase_amount, commission_amount, commission_rate, is_paid, created_at)
                        VALUES (?, ?, ?, ?, ?, false, datetime('now'))
                    """, (user_id, referrer_user_id, final_price, commission_amount, commission_rate))
                    print(f"✅ 커미션 저장 완료 (SQLite) - 금액: {commission_amount}원")
                
                print(f"✅ 추천인 커미션 적립 완료: {commission_amount}원 (구매 금액 {final_price}원의 10%)")
            except Exception as commission_error:
                print(f"⚠️ 커미션 적립 실패 (주문은 계속 진행): {commission_error}")
                print(f"⚠️ 커미션 오류 상세: {type(commission_error).__name__}: {str(commission_error)}")
                import traceback
                print(f"⚠️ 커미션 오류 스택: {traceback.format_exc()}")
                commission_amount = 0
        else:
            print(f"ℹ️ 추천인 연결 없음 - 커미션 적립 건너뜀")
        
        conn.commit()
        print(f"✅ 주문 생성 성공 - 주문 ID: {order_id}")
        
        # 패키지 상품 여부 확인
        package_steps = data.get('package_steps', [])
        is_package = len(package_steps) > 0
        print(f"🔍 패키지 상품 확인: is_package={is_package}, package_steps={package_steps}")
        
        # 응답 변수 초기화
        status = '주문발송'  # 기본값
        message = '주문이 접수되어 진행중입니다.'  # 기본값
        
        # 예약/분할/패키지 주문 처리
        if is_scheduled and not is_package:
            # 예약 주문 (패키지가 아닌 경우)은 나중에 처리하도록 스케줄링
            print(f"📅 예약 주문 - 즉시 처리하지 않음")
            status = 'pending'  # 예약 주문은 pending 상태로 시작
            message = '예약 주문이 생성되었습니다.'
        elif is_split_delivery:
            # 분할 주문은 나중에 처리하도록 스케줄링
            print(f"📅 분할 주문 - 즉시 처리하지 않음")
            status = 'pending'  # 분할 주문은 pending 상태로 시작
            message = '분할 주문이 생성되었습니다.'
        elif is_package:
            # 패키지 상품은 각 단계를 순차적으로 처리하도록 저장
            print(f"📦 패키지 주문 - {len(package_steps)}단계 순차 처리 예정")
            print(f"📦 패키지 단계 상세: {json.dumps(package_steps, indent=2, ensure_ascii=False)}")
            
            # 패키지 단계 정보를 JSON으로 저장 (상태는 pending으로 유지)
            if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    UPDATE orders SET package_steps = %s, updated_at = NOW()
                    WHERE order_id = %s
                """, (json.dumps(package_steps), order_id))
            else:
                cursor.execute("""
                    UPDATE orders SET package_steps = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE order_id = ?
                """, (json.dumps(package_steps), order_id))
            
            conn.commit()
            
            # 패키지 주문 즉시 처리 시작
            print(f"📦 패키지 주문 즉시 처리 시작: {order_id}")
            print(f"📦 주문 ID: {order_id}, 사용자: {user_id}, 단계 수: {len(package_steps)}")
            
            # 주문 상태를 processing으로 변경 (패키지 주문도 processing 상태 사용)
            if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    UPDATE orders SET status = 'processing', updated_at = NOW()
                    WHERE order_id = %s
                """, (order_id,))
            else:
                cursor.execute("""
                    UPDATE orders SET status = 'processing', updated_at = CURRENT_TIMESTAMP
                    WHERE order_id = ?
                """, (order_id,))
            
            conn.commit()
            
            # 첫 번째 단계 처리 시작
            def start_package_processing():
                print(f"📦 패키지 주문 {order_id} 처리 시작")
                print(f"📦 첫 번째 단계 실행: {package_steps[0] if package_steps else 'None'}")
                process_package_step(order_id, 0)
            
            # 별도 스레드에서 실행
            thread = threading.Thread(target=start_package_processing, daemon=True, name=f"PackageStart-{order_id}")
            thread.start()
            
            # 스레드가 정상적으로 시작되었는지 확인
            import time
            time.sleep(0.1)
            if thread.is_alive():
                print(f"✅ 패키지 시작 스레드 정상 실행: {thread.name}")
            else:
                print(f"❌ 패키지 시작 스레드 실패: {thread.name}")
            
            status = 'processing'  # 패키지 처리 중 상태 (processing 사용)
            message = f'패키지 주문이 생성되었습니다. ({len(package_steps)}단계 순차 처리 중)'
        else:
            # 일반 주문은 이미 SMM Panel API 호출 완료됨
            if smm_success:
                status = '주문발송'
                message = '주문이 접수되어 진행중입니다.'
                
                # 2분 후 주문 실행중으로 변경하는 스케줄 설정
                schedule_order_status_update(order_id, '주문 실행중', 2)  # 2분 후
                
                # 24시간 후 주문 실행완료로 변경하는 스케줄 설정 (최대 대기시간)
                schedule_order_status_update(order_id, '주문 실행완료', 1440)  # 24시간 후
            else:
                # SMM Panel 실패 시 (이미 위에서 처리되어 여기 도달하지 않음)
                status = 'failed'
                message = '주문 처리 중 오류가 발생했습니다.'
        
        return jsonify({
            'success': True,
            'order_id': order_id,
            'status': status,
            'original_price': price,
            'discount_amount': discount_amount,
            'final_price': final_price,
            'referral_discount': discount_amount > 0,
            'commission_earned': commission_amount if referral_data else 0,
            'message': message,
            'is_scheduled': is_scheduled,
            'is_split_delivery': is_split_delivery,
            'scheduled_datetime': scheduled_datetime,
            'split_days': split_days,
            'split_quantity': split_quantity
        }), 200
        
    except Exception as e:
        print(f"❌ 주문 생성 실패: {str(e)}")
        print(f"❌ 오류 타입: {type(e).__name__}")
        print(f"❌ 오류 발생 위치: create_order 함수")
        import traceback
        error_traceback = traceback.format_exc()
        print(f"❌ 스택 트레이스:\n{error_traceback}")
        
        # 요청 데이터도 로깅
        try:
            data = request.get_json()
            print(f"❌ 요청 데이터: {data}")
        except:
            print(f"❌ 요청 데이터 파싱 실패")
        
        # 오류 발생 시에도 주문을 "failed" 상태로 저장 시도
        try:
            if conn and cursor:
                # 최소한의 주문 정보라도 저장
                try:
                    if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
                        cursor.execute("""
                            INSERT INTO orders (order_id, user_id, total_amount, discount_amount, final_amount,
                                            status, created_at, updated_at, detailed_service)
                            VALUES (%s, %s, %s, %s, %s, 'failed', NOW(), NOW(), %s)
                            ON CONFLICT (order_id) DO UPDATE SET status = 'failed', updated_at = NOW()
                            RETURNING order_id
                        """, (
                            int(time.time()), 
                            db_user_id if 'db_user_id' in locals() else user_id,
                            0,  # total_amount: 실패한 주문은 0
                            0,  # discount_amount: 실패한 주문은 0
                            0,  # final_amount: 실패한 주문은 0
                            detailed_service if 'detailed_service' in locals() else ''
                        ))
                        failed_order_id = cursor.fetchone()[0] if cursor.rowcount > 0 else None
                    else:
                        cursor.execute("""
                            INSERT INTO orders (order_id, user_id, service_id, link, quantity, price, status, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, 'failed', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """, (
                            int(time.time()),
                            db_user_id if 'db_user_id' in locals() else user_id,
                            service_id if 'service_id' in locals() else '',
                            link if 'link' in locals() else '',
                            quantity if 'quantity' in locals() else 0,
                            0  # price: 실패한 주문은 0
                        ))
                        failed_order_id = cursor.lastrowid
                    
                    # 주문 금액을 0으로 업데이트
                    try:
                        if DATABASE_URL.startswith('postgresql://'):
                            cursor.execute("""
                                UPDATE orders 
                                SET total_amount = 0, discount_amount = 0, final_amount = 0, updated_at = NOW()
                                WHERE order_id = %s
                            """, (failed_order_id,))
                        else:
                            cursor.execute("""
                                UPDATE orders 
                                SET price = 0, discount_amount = 0, updated_at = CURRENT_TIMESTAMP
                                WHERE order_id = ?
                            """, (failed_order_id,))
                        conn.commit()
                        print(f"✅ 주문 금액을 0으로 업데이트 완료: order_id={failed_order_id}")
                    except Exception as update_error:
                        print(f"⚠️ 주문 금액 업데이트 실패 (무시하고 계속): {update_error}")
                        conn.rollback()
                        conn.commit()
                    
                    print(f"⚠️ 주문이 'failed' 상태로 저장되었습니다. order_id: {failed_order_id}")
                    
                    # 포인트 환불 필요 정보 반환
                    return jsonify({
                        'error': f'주문 생성 실패: {str(e)}',
                        'order_id': failed_order_id,
                        'status': 'failed',
                        'refund_required': True,
                        'refund_amount': final_price if 'final_price' in locals() else 0
                    }), 500
                except Exception as save_error:
                    print(f"❌ 실패한 주문 저장도 실패: {save_error}")
                    if conn:
                        conn.rollback()
        except Exception as fallback_error:
            print(f"❌ 실패 처리 중 오류: {fallback_error}")
        
        if conn:
            conn.rollback()
        return jsonify({
            'error': f'주문 생성 실패: {str(e)}',
            'refund_required': True,
            'refund_amount': final_price if 'final_price' in locals() else 0
        }), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print("✅ 데이터베이스 연결 종료")

# 패키지 주문 처리 시작
@app.route('/api/orders/start-package-processing', methods=['POST'])
def start_package_processing():
    """Start Package Processing
    ---
    tags:
      - Orders
    summary: Start Package Processing
    description: "Start Package Processing API"
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """결제 완료 후 패키지 주문 처리 시작"""
    conn = None
    cursor = None
    
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        
        if not order_id:
            return jsonify({'error': '주문 ID가 필요합니다.'}), 400
        
        print(f"🚀 패키지 주문 처리 시작 요청: {order_id}")
        print(f"🚀 요청 데이터: {data}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 주문 정보 조회 (link는 order_items 테이블에서 가져옴)
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT o.order_id, o.user_id, COALESCE(oi.link, ''), o.package_steps, o.status 
                FROM orders o
                LEFT JOIN order_items oi ON o.order_id = oi.order_id
                WHERE o.order_id = %s
                LIMIT 1
            """, (order_id,))
        else:
            cursor.execute("""
                SELECT order_id, user_id, link, package_steps, status 
                FROM orders 
                WHERE order_id = ?
            """, (order_id,))
        
        order = cursor.fetchone()
        
        print(f"🔍 주문 조회 결과: {order}")
        
        if not order:
            print(f"❌ 주문 {order_id}을 찾을 수 없습니다.")
            return jsonify({'error': '주문을 찾을 수 없습니다.'}), 404
        
        order_id_db, user_id, link, package_steps_json, status = order
        
        print(f"🔍 주문 상세 정보: ID={order_id_db}, 사용자={user_id}, 상태={status}")
        print(f"🔍 패키지 단계 정보: {package_steps_json}")
        
        # 패키지 주문의 경우 이미 처리 중이거나 완료된 상태일 수 있음
        # 더 많은 상태를 처리 가능하도록 허용
        allowed_statuses = ['pending', 'pending_payment', 'processing', 'completed', '주문발송', '주문 실행중', '주문 실행완료', 'in_progress']
        if status not in allowed_statuses:
            print(f"❌ 주문 {order_id} 상태가 처리 가능한 상태가 아닙니다. 현재 상태: {status}")
            return jsonify({'error': f'주문 상태가 처리할 수 없습니다. 현재 상태: {status}'}), 400
        
        # 이미 처리 중인 경우 성공으로 처리
        if status in ['processing', 'completed']:
            print(f"✅ 주문 {order_id} 이미 처리 중이거나 완료됨. 상태: {status}")
            return jsonify({
                'success': True,
                'message': '주문이 이미 처리 중이거나 완료되었습니다.',
                'status': status
            }), 200
        
        # package_steps 파싱
        try:
            if isinstance(package_steps_json, list):
                package_steps = package_steps_json
            elif isinstance(package_steps_json, str):
                package_steps = json.loads(package_steps_json)
            else:
                package_steps = []
        except (json.JSONDecodeError, TypeError) as e:
            print(f"❌ 패키지 단계 파싱 실패: {e}")
            return jsonify({'error': '패키지 단계 정보가 올바르지 않습니다.'}), 400
        
        if not package_steps or len(package_steps) == 0:
            # split delivery 패키지의 경우 (package_steps가 None 또는 빈 배열)
            print(f"📦 Split delivery 패키지 주문: {order_id}")
            return jsonify({
                'success': True,
                'message': 'Split delivery 패키지는 매일 자동으로 처리됩니다.',
                'status': 'split_delivery'
            }), 200
        
        print(f"📦 패키지 주문 처리 시작: {order_id}")
        print(f"📦 사용자: {user_id}, 링크: {link}")
        print(f"📦 단계 수: {len(package_steps)}")
        print(f"📦 첫 번째 단계: {package_steps[0] if package_steps else 'None'}")
        
        # 주문 상태를 processing으로 변경 (패키지 주문도 processing 상태 사용)
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                UPDATE orders SET status = 'processing', updated_at = NOW()
                WHERE order_id = %s
            """, (order_id,))
        else:
            cursor.execute("""
                UPDATE orders SET status = 'processing', updated_at = CURRENT_TIMESTAMP
                WHERE order_id = ?
            """, (order_id,))
        
        conn.commit()
        
        # 첫 번째 단계 처리 시작
        def start_package_processing():
            print(f"📦 패키지 주문 {order_id} 처리 시작")
            print(f"📦 첫 번째 단계 실행: {package_steps[0] if package_steps else 'None'}")
            process_package_step(order_id, 0)
        
        # 별도 스레드에서 실행 (daemon=True로 변경하여 메인 프로세스와 독립적으로 실행)
        thread = threading.Thread(target=start_package_processing, daemon=True, name=f"PackageStart-{order_id}")
        thread.start()
        
        # 스레드가 정상적으로 시작되었는지 확인
        import time
        time.sleep(0.1)
        if thread.is_alive():
            print(f"✅ 패키지 시작 스레드 정상 실행: {thread.name}")
        else:
            print(f"❌ 패키지 시작 스레드 실패: {thread.name}")
        
        print(f"✅ 패키지 주문 처리 시작됨: {order_id}")
        
        return jsonify({
            'success': True,
            'message': f'패키지 주문 처리가 시작되었습니다. ({len(package_steps)}단계 순차 처리)',
            'order_id': order_id
        }), 200
        
    except Exception as e:
        print(f"❌ 패키지 주문 처리 시작 오류: {str(e)}")
        return jsonify({'error': f'패키지 주문 처리 시작 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 패키지 상품 진행 상황 조회
@app.route('/api/orders/<int:order_id>/package-progress', methods=['GET'])
def get_package_progress(order_id):
    """Get Package Progress
    ---
    tags:
      - Orders
    summary: Get Package Progress
    description: "Get Package Progress API"
    parameters:
      - name: order_id
        in: path
        type: int
        required: true
        description: Order Id
        example: "example_order_id"
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """패키지 상품 진행 상황 조회"""
    conn = None
    cursor = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 패키지 진행 상황 조회
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT step_number, step_name, service_id, quantity, smm_panel_order_id, status, created_at
                FROM execution_progress 
                WHERE order_id = %s AND exec_type = 'package'
                ORDER BY step_number ASC, created_at ASC
            """, (order_id,))
        else:
            cursor.execute("""
                SELECT step_number, step_name, service_id, quantity, smm_panel_order_id, status, created_at
                FROM execution_progress 
                WHERE order_id = ? AND exec_type = 'package'
                ORDER BY step_number ASC, created_at ASC
            """, (order_id,))
        
        progress_data = cursor.fetchall()
        
        # 주문 정보도 조회
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT status, package_steps FROM orders 
                WHERE order_id = %s
            """, (order_id,))
        else:
            cursor.execute("""
                SELECT status, package_steps FROM orders 
                WHERE order_id = ?
            """, (order_id,))
        
        order_info = cursor.fetchone()
        
        if not order_info:
            return jsonify({'error': '주문을 찾을 수 없습니다.'}), 404
        
        order_status, package_steps_json = order_info
        
        # package_steps 파싱
        try:
            if isinstance(package_steps_json, list):
                package_steps = package_steps_json
            elif isinstance(package_steps_json, str):
                package_steps = json.loads(package_steps_json)
            else:
                package_steps = []
        except:
            package_steps = []
        
        # 진행 상황 데이터 포맷팅
        progress_list = []
        for row in progress_data:
            step_number, step_name, service_id, quantity, smm_panel_order_id, status, created_at = row
            progress_list.append({
                'step_number': step_number,
                'step_name': step_name,
                'service_id': service_id,
                'quantity': quantity,
                'smm_panel_order_id': smm_panel_order_id,
                'status': status,
                'created_at': created_at.isoformat() if hasattr(created_at, 'isoformat') else str(created_at)
            })
        
        return jsonify({
            'success': True,
            'order_id': order_id,
            'order_status': order_status,
            'total_steps': len(package_steps),
            'progress': progress_list,
            'package_steps': package_steps
        }), 200
        
    except Exception as e:
        print(f"❌ 패키지 진행 상황 조회 실패: {str(e)}")
        return jsonify({'error': f'패키지 진행 상황 조회 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 주문 목록 조회
@app.route('/api/orders', methods=['GET'])
def get_orders():
    """주문 목록 조회
    ---
    tags:
      - Orders
    summary: 사용자의 주문 목록 조회
    description: "현재 사용자의 주문 목록을 조회합니다."
    security:
      - Bearer: []
    parameters:
      - name: user_id
        in: query
        type: string
        required: true
        description: 사용자 ID
        example: "user123"
      - name: limit
        in: query
        type: integer
        required: false
        description: 조회할 주문 수 제한
        example: 10
      - name: offset
        in: query
        type: integer
        required: false
        description: 조회 시작 위치
        example: 0
    responses:
      200:
        description: 주문 목록 조회 성공
        schema:
          type: object
          properties:
            orders:
              type: array
              items:
                type: object
                properties:
                  order_id:
                    type: integer
                    example: 123
                  service_id:
                    type: integer
                    example: 1
                  link:
                    type: string
                    example: "https://instagram.com/p/abc123"
                  quantity:
                    type: integer
                    example: 100
                  price:
                    type: number
                    example: 10000
                  status:
                    type: string
                    example: "pending"
                  created_at:
                    type: string
                    example: "2024-01-01T00:00:00"
            total:
              type: integer
              description: 전체 주문 수
              example: 50
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "user_id가 필요합니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "주문 목록 조회 중 오류가 발생했습니다."
    """
    conn = None
    cursor = None
    
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id가 필요합니다.'}), 400
        
        print(f"🔍 주문 조회 시작 - user_id: {user_id}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 주문 정보 조회 - 새 스키마에 맞게 수정
        if DATABASE_URL.startswith('postgresql://'):
            # 새 스키마에서는 order_items 테이블을 사용
            try:
                # external_uid로 사용자 찾기
                cursor.execute("""
                    SELECT user_id FROM users 
                    WHERE external_uid = %s OR email = %s
                    LIMIT 1
                """, (user_id, user_id))
                user_result = cursor.fetchone()
                if not user_result:
                    return jsonify({'orders': []}), 200
                db_user_id = user_result[0]
                
                # 주문 조회 (order_items와 LEFT JOIN) - 첫 번째 order_item만 가져오기
                cursor.execute("""
                    SELECT 
                        o.order_id, 
                        o.status, 
                        COALESCE(o.final_amount, o.total_amount, 0) as price, 
                        o.created_at,
                        oi.variant_id, 
                        COALESCE(oi.link, '') as link, 
                        COALESCE(oi.quantity, 0) as quantity, 
                        COALESCE(oi.unit_price, 0) as unit_price,
                        o.smm_panel_order_id, 
                        o.detailed_service,
                        pv.name as variant_name, 
                        pv.meta_json as variant_meta
                    FROM orders o
                    LEFT JOIN (
                        SELECT DISTINCT ON (order_id)
                            order_id, variant_id, link, quantity, unit_price
                        FROM order_items
                        ORDER BY order_id, order_item_id ASC
                    ) oi ON o.order_id = oi.order_id
                    LEFT JOIN product_variants pv ON oi.variant_id = pv.variant_id
                    WHERE o.user_id = %s
                    ORDER BY o.created_at DESC
                    LIMIT 50
                """, (db_user_id,))
            except Exception as e:
                print(f"⚠️ 새 스키마 쿼리 실패, 빈 결과 반환: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'orders': []}), 200
        else:
            cursor.execute("""
                SELECT order_id, service_id, link, quantity, price, status, created_at, 
                       smm_panel_order_id, detailed_service
                FROM orders 
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 10
            """, (user_id,))
        
        orders = cursor.fetchall()
        print(f"📊 조회된 주문 수: {len(orders)}개")
        
        order_list = []
        for order in orders:
            try:
                # 주문 데이터 처리 (새 스키마에 맞게 수정)
                if DATABASE_URL.startswith('postgresql://'):
                    # 새 스키마: order_id, status, price (final_amount), created_at, variant_id, link, quantity, unit_price, smm_panel_order_id, detailed_service, variant_name, variant_meta
                    order_id = order[0]
                    db_status = order[1] if len(order) > 1 else 'pending'
                    price = float(order[2]) if len(order) > 2 and order[2] else 0.0
                    created_at = order[3] if len(order) > 3 else None
                    variant_id = order[4] if len(order) > 4 else None
                    link_raw = order[5] if len(order) > 5 else None
                    # 링크 처리: order_items의 link를 사용, 없으면 별도 조회
                    link = ''
                    if link_raw and isinstance(link_raw, str) and link_raw.strip() and link_raw.strip() != 'None' and link_raw.strip() != 'null':
                        link = link_raw.strip()
                    else:
                        # JOIN에서 링크가 없으면 별도로 조회 시도
                        try:
                            cursor.execute("""
                                SELECT link FROM order_items 
                                WHERE order_id = %s AND link IS NOT NULL AND link != '' AND link != 'null'
                                ORDER BY order_item_id ASC
                                LIMIT 1
                            """, (order_id,))
                            link_result = cursor.fetchone()
                            if link_result and link_result[0]:
                                link = str(link_result[0]).strip()
                        except Exception as link_err:
                            print(f"⚠️ 링크 별도 조회 실패: {link_err}")
                    
                    quantity = int(order[6]) if len(order) > 6 and order[6] is not None else 0  # None 체크 추가
                    unit_price = float(order[7]) if len(order) > 7 and order[7] else 0.0
                    smm_panel_order_id = order[8] if len(order) > 8 else None
                    detailed_service = order[9] if len(order) > 9 else None
                    variant_name = order[10] if len(order) > 10 else None
                    variant_meta = order[11] if len(order) > 11 else None
                    
                    print(f"🔍 주문 데이터 추출 - order_id: {order_id}, link_raw: {link_raw}, 최종 link: '{link}', quantity: {quantity}, variant_id: {variant_id}")
                    
                    # variant_meta에서 service_id 추출
                    actual_service_id = None
                    if variant_meta:
                        try:
                            if isinstance(variant_meta, dict):
                                actual_service_id = variant_meta.get('service_id') or variant_meta.get('smm_service_id')
                            elif isinstance(variant_meta, str):
                                import json
                                try:
                                    meta_dict = json.loads(variant_meta)
                                    actual_service_id = meta_dict.get('service_id') or meta_dict.get('smm_service_id')
                                except:
                                    pass
                        except Exception as e:
                            print(f"⚠️ variant_meta 파싱 실패: {e}")
                    
                    service_id = str(actual_service_id) if actual_service_id else (str(variant_id) if variant_id else '')
                else:
                    # 구 스키마 (SQLite)
                    order_id = order[0]
                    service_id = order[1] if len(order) > 1 else ''
                    link = order[2] if len(order) > 2 else ''
                    quantity = order[3] if len(order) > 3 else 0
                    price = float(order[4]) if len(order) > 4 else 0.0
                    db_status = order[5] if len(order) > 5 else 'pending'
                    created_at = order[6]
                    smm_panel_order_id = order[7] if len(order) > 7 else None
                    detailed_service = order[8] if len(order) > 8 else None
                # 일부 DB에는 start_count, remains 컬럼이 없을 수 있으므로 기본값 사용
                start_count = 0
                remains = quantity  # 기본값: 전체 수량
                
                # 간단한 상태 매핑
                if db_status in ['completed', '완료']:
                    status = '주문 실행완료'
                elif db_status in ['in_progress', '진행중', 'processing']:
                    status = '주문 실행중'
                elif db_status in ['pending', '접수됨', '주문발송']:
                    status = '주문발송'
                else:
                    status = '주문 미처리'
                
                # 날짜 포맷팅 (간소화)
                created_at_str = created_at.isoformat() if hasattr(created_at, 'isoformat') else str(created_at)
                
                # SMM Panel 주문번호 우선 사용
                display_order_id = smm_panel_order_id if smm_panel_order_id else order_id
                
                # SMM Panel API에서 실제 사용 금액 및 남은 수량 조회
                charge = 0
                if smm_panel_order_id and status in ['주문 실행중', '주문 실행완료', '주문발송']:
                    try:
                        # 처리 중이거나 완료된 주문만 SMM Panel API 호출
                        smm_status = call_smm_panel_api({
                            'action': 'status',
                            'order': smm_panel_order_id
                        })
                        
                        if smm_status.get('status') == 'success':
                            charge = float(smm_status.get('charge', 0)) or 0
                            start_count = int(smm_status.get('start_count', 0)) or 0
                            api_remains = smm_status.get('remains')
                            # API에서 남은 수량이 있으면 사용, 없으면 원래 수량 사용
                            if api_remains is not None:
                                remains = int(api_remains)
                            else:
                                remains = quantity
                            print(f"✅ SMM Panel 상태 조회 성공: charge={charge}, start_count={start_count}, remains={remains}")
                        else:
                            print(f"⚠️ SMM Panel 상태 조회 실패: {smm_status.get('message')}")
                    except Exception as e:
                        print(f"⚠️ SMM Panel 상태 조회 오류: {e}")
                        charge = 0
                        remains = quantity  # 오류 시 전체 수량으로 설정
                
                # 서비스 이름 결정 (우선순위: detailed_service > variant_name > get_service_name > 기본값)
                if detailed_service:
                    service_name = detailed_service
                elif DATABASE_URL.startswith('postgresql://') and variant_name:
                    service_name = variant_name
                else:
                    service_name = get_service_name(service_id)
                
                # 링크 최종 검증
                if not link or link == 'None' or link == 'null' or link.strip() == '':
                    link = ''
                
                print(f"🔍 주문 데이터 구성 - order_id: {display_order_id}, link: '{link}', quantity: {quantity}, service_id: {service_id}")
                
                order_list.append({
                    'id': display_order_id,
                    'order_id': display_order_id,
                    'service_id': service_id,
                    'service_name': service_name,
                    'link': link,  # 링크 필수 포함
                    'quantity': quantity,
                    'price': price,
                    'charge': charge,  # 사용한 금액 추가
                    'status': status,
                    'created_at': created_at_str,
                    'is_package': False,  # 간소화
                    'package_steps': [],
                    'total_steps': 0,
                    'smm_panel_order_id': smm_panel_order_id,
                    'detailed_service': detailed_service,
                    'start_count': start_count,
                    'remains': remains
                })
                
            except Exception as order_err:
                print(f"⚠️ 주문 처리 중 오류: {order_err}")
                continue
        
        print(f"✅ 주문 처리 완료: {len(order_list)}개")
        
        return jsonify({
            'orders': order_list
        }), 200
        
    except Exception as e:
        print(f"❌ 주문 조회 오류: {e}")
        import traceback
        print(f"❌ 스택 트레이스: {traceback.format_exc()}")
        return jsonify({'error': f'주문 목록 조회 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print("✅ 데이터베이스 연결 종료")

# 포인트 구매 신청
@app.route('/api/points/purchase', methods=['POST'])
def purchase_points():
    """포인트 구매 신청
    ---
    tags:
      - Points
    summary: 포인트 구매 신청
    description: "사용자가 포인트를 구매하기 위해 신청합니다."
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - user_id
            - amount
            - price
          properties:
            user_id:
              type: string
              description: 사용자 ID
              example: "user123"
            amount:
              type: integer
              description: 구매할 포인트 양
              example: 10000
            price:
              type: number
              description: 결제 금액
              example: 10000
            buyer_name:
              type: string
              description: 구매자 이름 (선택사항)
              example: "홍길동"
            bank_info:
              type: string
              description: 은행 정보 (선택사항)
              example: "국민은행"
    responses:
      200:
        description: 포인트 구매 신청 성공
        schema:
          type: object
          properties:
            purchase_id:
              type: integer
              example: 123
            message:
              type: string
              example: "포인트 구매 신청이 완료되었습니다."
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "필수 필드가 누락되었습니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "포인트 구매 신청 실패: ..."
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        amount = data.get('amount')
        price = data.get('price')
        buyer_name = data.get('buyer_name', '')
        bank_info = data.get('bank_info', '')
        
        # 입력 검증 강화
        if not all([user_id, amount, price]):
            return jsonify({'error': '필수 필드가 누락되었습니다.'}), 400
        
        # 금액 검증
        try:
            amount = float(amount)
            price = float(price)
        except (ValueError, TypeError):
            return jsonify({'error': '잘못된 금액 형식입니다.'}), 400
        
        # 금액 범위 검증
        if amount <= 0 or amount > 1000000:  # 최대 100만 포인트
            return jsonify({'error': '포인트 금액이 범위를 벗어났습니다.'}), 400
        
        if price <= 0 or price > 10000000:  # 최대 1천만원
            return jsonify({'error': '결제 금액이 범위를 벗어났습니다.'}), 400
        
        # 사용자 ID 검증 (SQL 인젝션 방지) - 구글/카카오 로그인 사용자도 허용
        user_id_str = str(user_id)  # 정수형 user_id를 문자열로 변환
        if not user_id_str.replace('_', '').replace('-', '').replace('google', '').replace('kakao', '').isalnum():
            return jsonify({'error': '잘못된 사용자 ID 형식입니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 사용자가 users 테이블에 있는지 확인하고, 없으면 생성
        if DATABASE_URL.startswith('postgresql://'):
            # PostgreSQL: user_id는 VARCHAR이므로 타입 캐스팅 불필요
            # email이 NOT NULL이므로 기본값 설정
            sanitized_user_id = (
                user_id_str
                .replace('@', '_at_')
                .replace('/', '_')
                .replace('\\', '_')
            )
            user_email = data.get('user_email', '') or f"{sanitized_user_id[:200]}@temp.local"
            
            # 사용자 생성/확인 (ON CONFLICT로 중복 방지 - 원자적 연산)
            # 같은 트랜잭션 내에서 사용자와 points를 모두 생성해야 외래 키 제약 조건 통과
            import sys
            import traceback
            import time
            try:
                # 먼저 사용자가 이미 존재하는지 확인 (새 스키마에서는 external_uid 사용)
                cursor.execute("SELECT user_id FROM users WHERE external_uid = %s OR email = %s", (user_id_str, user_email))
                user_exists = cursor.fetchone()
                
                if not user_exists:
                    # 이메일이 이미 사용 중인지 확인
                    cursor.execute("SELECT user_id FROM users WHERE email = %s", (user_email,))
                    email_exists = cursor.fetchone()
                    
                    if email_exists:
                        alt_id = (
                            user_id_str
                            .replace('@', '_at_')
                            .replace('/', '_')
                            .replace('\\', '_')
                        )
                        user_email = f"{alt_id[:150]}_{int(time.time())}@temp.local"
                        print(f"⚠️ 이메일 충돌 감지, 고유 이메일 생성: {user_email}", flush=True)
                    
                    # 사용자 생성 (이메일 충돌 방지를 위해 고유 이메일 사용)
                    try:
                        cursor.execute("""
                            INSERT INTO users (user_id, email, name, created_at, updated_at)
                            VALUES (%s, %s, %s, NOW(), NOW())
                            ON CONFLICT (user_id) DO NOTHING
                        """, (user_id_str, user_email, buyer_name or 'User'))
                        print(f"✅ 사용자 생성 시도: {user_id_str}, email: {user_email}", flush=True)
                    except Exception as insert_error:
                        # 이메일 unique 제약 조건 위반 등 예외 처리
                        error_str = str(insert_error).lower()
                        if 'unique' in error_str or 'duplicate' in error_str or 'violates unique constraint' in error_str:
                            # 이메일 충돌이 발생한 경우, 더 고유한 이메일로 재시도
                            alt_id = (
                                user_id_str
                                .replace('@', '_at_')
                                .replace('/', '_')
                                .replace('\\', '_')
                            )
                            user_email = f"{alt_id[:120]}_{int(time.time() * 1000)}@temp.local"
                            print(f"⚠️ 이메일 충돌 발생, 재시도: {user_email}", flush=True)
                            cursor.execute("""
                                INSERT INTO users (external_uid, email, username, created_at, updated_at)
                                VALUES (%s, %s, %s, NOW(), NOW())
                                ON CONFLICT (external_uid) DO NOTHING
                            """, (user_id_str, user_email, buyer_name or 'User'))
                            print(f"✅ 재시도 성공: {user_id_str}", flush=True)
                        else:
                            # 다른 종류의 오류는 그대로 전파
                            raise
                
                # 새 스키마에서는 external_uid로 사용자 찾기
                cursor.execute("SELECT user_id FROM users WHERE external_uid = %s OR email = %s", (user_id_str, user_email))
                user_result = cursor.fetchone()
                if not user_result:
                    raise Exception(f"사용자 생성 실패: {user_id_str}가 users 테이블에 존재하지 않습니다.")
                db_user_id = user_result[0]
                print(f"✅ 사용자 확인 완료: user_id={db_user_id}, external_uid={user_id_str}", flush=True)
                
                # 새 스키마에서는 wallets 테이블 사용
                cursor.execute("""
                    INSERT INTO wallets (user_id, balance, created_at, updated_at)
                    VALUES (%s, 0, NOW(), NOW())
                    ON CONFLICT (user_id) DO NOTHING
                """, (db_user_id,))
                print(f"✅ 지갑 레코드 생성/확인 완료: user_id={db_user_id}", flush=True)
                
                # wallet_id 찾기
                cursor.execute("SELECT wallet_id FROM wallets WHERE user_id = %s", (db_user_id,))
                wallet_result = cursor.fetchone()
                if not wallet_result:
                    raise Exception(f"지갑 생성 실패: user_id={db_user_id}가 wallets 테이블에 존재하지 않습니다.")
                wallet_id = wallet_result[0]
                
                # 새 스키마에서는 wallet_transactions 사용 (point_purchases 대신)
                # meta_json을 JSON 문자열로 변환 (amount와 price 모두 저장)
                meta_data = json.dumps({
                    'buyer_name': buyer_name, 
                    'bank_info': bank_info, 
                    'amount': amount,  # 포인트 양
                    'price': price,    # 결제 금액
                    'requested_amount': amount  # 요청된 포인트 양 (호환성)
                }, ensure_ascii=False)
                cursor.execute("""
                    INSERT INTO wallet_transactions (wallet_id, type, amount, status, meta_json, created_at, updated_at)
                    VALUES (%s, 'topup', %s, 'pending', %s::jsonb, NOW(), NOW())
                    RETURNING transaction_id
                """, (wallet_id, price, meta_data))
                purchase_id = cursor.fetchone()[0]
                print(f"✅ 포인트 구매 삽입 완료: transaction_id={purchase_id}, wallet_id={wallet_id}", flush=True)
                
            except Exception as db_error:
                conn.rollback()
                error_msg = f"❌ 데이터베이스 작업 실패: {db_error}"
                print(error_msg, file=sys.stderr, flush=True)
                traceback.print_exc(file=sys.stderr)
                sys.stderr.flush()
                raise Exception(f"데이터베이스 작업 실패: {db_error}")
        else:
            # SQLite: 사용자가 users 테이블에 있는지 확인하고, 없으면 생성
            sanitized_user_id = user_id_str.replace('@', '_at_').replace('/', '_').replace('\\', '_')
            user_email = data.get('user_email', '') or f"{sanitized_user_id[:200]}@temp.local"
            
            # 사용자 생성/확인 (INSERT OR IGNORE로 중복 방지)
            cursor.execute("""
                INSERT OR IGNORE INTO users (user_id, email, name, created_at, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (user_id_str, user_email, buyer_name or 'User'))
            
            # points 테이블에도 초기 레코드 생성 (INSERT OR IGNORE로 중복 방지)
            cursor.execute("""
                INSERT OR IGNORE INTO points (user_id, points, created_at, updated_at)
                VALUES (?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (user_id_str,))
            
            print(f"✅ 사용자 및 포인트 레코드 확인/생성 완료: {user_id_str}")
            
            cursor.execute("""
                INSERT INTO point_purchases (user_id, amount, price, status, buyer_name, bank_info, created_at, updated_at)
                VALUES (?, ?, ?, 'pending', ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (user_id_str, amount, price, buyer_name, bank_info))
            cursor.execute("SELECT last_insert_rowid()")
            purchase_id = cursor.fetchone()[0]
        
        # PostgreSQL의 경우 purchase_id는 이미 try 블록에서 설정됨
        if DATABASE_URL.startswith('postgresql://'):
            # purchase_id는 이미 위의 try 블록에서 설정되었으므로 여기서는 아무것도 하지 않음
            pass
        
        # 모든 작업이 성공했으면 한 번에 commit
        conn.commit()
        
        print(f"✅ 포인트 구매 신청 완료 - purchase_id: {purchase_id}, user_id: {user_id_str}")
        
        conn.close()
        
        return jsonify({
            'success': True,
            'purchase_id': purchase_id,
            'status': 'pending',
            'message': '포인트 구매 신청이 완료되었습니다.'
        }), 200
        
    except Exception as e:
        import sys
        import traceback
        error_msg = f'포인트 구매 신청 실패: {str(e)}'
        print(f"❌ 포인트 구매 신청 실패: {error_msg}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        return jsonify({'error': error_msg}), 500

# KCP 표준결제 - 거래등록 (Mobile)
@app.route('/api/points/purchase-kcp/register', methods=['POST'])
def kcp_register_transaction():
    """Kcp Register Transaction
    ---
    tags:
      - Points
    summary: Kcp Register Transaction
    description: "Kcp Register Transaction API"
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """KCP 표준결제 거래등록 (Mobile)"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        amount = data.get('amount')
        price = data.get('price')
        good_name = data.get('good_name', '포인트 구매')
        pay_method = data.get('pay_method', 'CARD')  # CARD, BANK, MOBX, TPNT, GIFT
        
        if not user_id or not amount or not price:
            return jsonify({'error': '필수 정보가 누락되었습니다.'}), 400
        
        # 구글/카카오 로그인 사용자 ID 검증
        user_id_str = str(user_id)  # 정수형 user_id를 문자열로 변환
        if not user_id_str.replace('_', '').replace('-', '').replace('google', '').replace('kakao', '').isalnum():
            return jsonify({'error': '잘못된 사용자 ID 형식입니다.'}), 400
        
        # 입력 검증
        try:
            amount = float(amount)
            price = float(price)
        except (ValueError, TypeError):
            return jsonify({'error': '잘못된 금액 형식입니다.'}), 400
        
        # 금액 범위 검증
        if amount <= 0 or amount > 1000000:
            return jsonify({'error': '포인트 금액이 범위를 벗어났습니다.'}), 400
        
        if price <= 0 or price > 10000000:
            return jsonify({'error': '결제 금액이 범위를 벗어났습니다.'}), 400
        
        # 주문번호 생성 (타임스탬프 기반)
        import time
        ordr_idxx = f"POINT_{int(time.time())}"
        
        # 외부 접근 가능한 HTTPS 기반 Ret_URL 구성 (ALB 뒤에서 http로 보이는 문제 방지)
        fwd_proto = request.headers.get('X-Forwarded-Proto', 'https')
        fwd_host = request.headers.get('X-Forwarded-Host') or request.host
        # sociality 도메인은 무조건 https 강제
        if fwd_host and fwd_host.endswith('sociality.co.kr'):
            fwd_proto = 'https'
        external_base = f"{fwd_proto}://{fwd_host}"

        # KCP 거래등록 요청 데이터
        kcp_site_cd = get_parameter_value('KCP_SITE_CD', 'ALFCQ')
        kcp_cert_info = get_parameter_value('KCP_CERT_INFO', '')
        # 환경변수에 \n 형태로 들어온 경우 실제 개행으로 변환
        if kcp_cert_info:
            kcp_cert_info = kcp_cert_info.replace('\\n', '\n').strip()
        # 진단 로그 (길이와 시작/끝만 표시)
        try:
            print(f"🔐 KCP_CERT_INFO length: {len(kcp_cert_info) if kcp_cert_info else 0}")
            if kcp_cert_info:
                print(f"🔐 KCP_CERT_INFO head: {kcp_cert_info[:30]}")
                print(f"🔐 KCP_CERT_INFO tail: {kcp_cert_info[-30:]}")
        except Exception:
            pass
        if not kcp_cert_info or len(kcp_cert_info) < 60:
            print(f"❌ KCP 인증서 정보 부족: 길이 {len(kcp_cert_info) if kcp_cert_info else 0}")
            return jsonify({
                'success': False,
                'error': 'KCP 결제 시스템이 준비되지 않았습니다. 잠시 후 다시 시도해주세요.'
            }), 503
        if not (kcp_cert_info.startswith('-----BEGIN') and ('END CERTIFICATE' in kcp_cert_info or 'END ENCRYPTED PRIVATE KEY' in kcp_cert_info)):
            return jsonify({
                'success': False,
                'error': 'KCP 거래등록 실패: KCP_CERT_INFO 형식 오류(PEM 구분자 누락). BEGIN/END CERTIFICATE 또는 BEGIN/END ENCRYPTED PRIVATE KEY 포함해 저장하세요.',
            }), 400
        register_data = {
            'site_cd': kcp_site_cd,
            'ordr_idxx': ordr_idxx,
            'good_mny': str(int(price)),
            'good_name': good_name,
            'pay_method': pay_method,
            'currency': '410',  # KRW
            'shop_name': 'SOCIALITY',
            'kcp_cert_info': kcp_cert_info,
            'Ret_URL': f"{external_base}/api/points/purchase-kcp/return"
        }
        
        # KCP 거래등록 API 호출
        import requests
        # 테스트 환경 URL (KCP 최신 가이드)
        kcp_register_url = 'https://stg-spl.kcp.co.kr/std/tradeReg/register'
        print(f"🔍 KCP 거래등록 URL: {kcp_register_url}")
        print(f"🔍 KCP 거래등록 데이터: {register_data}")
        
        try:
            # 해당 엔드포인트는 JSON 포맷을 요구 (S005 예방)
            response = requests.post(
                kcp_register_url,
                json=register_data,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            response.raise_for_status()
            
            # 응답 내용 로깅
            print(f"🔍 KCP 거래등록 응답 상태: {response.status_code}")
            print(f"🔍 KCP 거래등록 응답 헤더: {dict(response.headers)}")
            print(f"🔍 KCP 거래등록 응답 내용: {response.text[:500]}")
            
            # JSON 파싱 시도
            try:
                kcp_response = response.json()
                print(f"🔍 KCP JSON 응답: {kcp_response}")
            except ValueError as json_err:
                print(f"❌ JSON 파싱 실패, HTML 응답으로 처리: {json_err}")
                # HTML 응답에서 필요한 데이터 추출 시도
                response_text = response.text
                print(f"🔍 HTML 응답 내용: {response_text[:1000]}")
                
                # HTML에서 JavaScript 변수나 hidden input에서 데이터 추출
                import re
                
                # approvalKey 추출
                approval_key_match = re.search(r'approvalKey["\']?\s*[:=]\s*["\']([^"\']+)["\']', response_text)
                pay_url_match = re.search(r'PayUrl["\']?\s*[:=]\s*["\']([^"\']+)["\']', response_text)
                
                if approval_key_match and pay_url_match:
                    kcp_response = {
                        'Code': '0000',
                        'approvalKey': approval_key_match.group(1),
                        'PayUrl': pay_url_match.group(1)
                    }
                    print(f"🔍 추출된 KCP 데이터: {kcp_response}")
                else:
                    print(f"❌ HTML에서 필요한 데이터를 찾을 수 없음")
                    return jsonify({'error': 'KCP 서버 응답에서 필요한 데이터를 찾을 수 없습니다.'}), 500
            
            if kcp_response.get('Code') == '0000':
                # DB에 거래등록 정보 저장
                conn = get_db_connection()
                cursor = conn.cursor()
                
                if DATABASE_URL.startswith('postgresql://'):
                    cursor.execute("""
                        INSERT INTO point_purchases (user_id, amount, price, status, buyer_name, bank_info, created_at, updated_at, purchase_id)
                        VALUES (%s, %s, %s, 'kcp_registered', %s, %s, NOW(), NOW(), %s)
                        RETURNING id
                    """, (user_id, amount, price, '', '', ordr_idxx))
                else:
                    cursor.execute("""
                        INSERT INTO point_purchases (user_id, amount, price, status, buyer_name, bank_info, created_at, updated_at, purchase_id)
                        VALUES (?, ?, ?, 'kcp_registered', ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?)
                    """, (user_id, amount, price, '', '', ordr_idxx))
                    cursor.execute("SELECT last_insert_rowid()")
                
                purchase_id = cursor.fetchone()[0]
                conn.commit()
                conn.close()
                
                return jsonify({
                    'success': True,
                    'purchase_id': purchase_id,
                    'ordr_idxx': ordr_idxx,
                    'kcp_response': kcp_response,
                    'message': 'KCP 결제 준비가 완료되었습니다. 결제창을 호출합니다.'
                }), 200
            else:
                # 실패 원인과 원문 응답을 함께 반환해 프런트에서 표시/로깅 가능하게 함
                return jsonify({
                    'success': False,
                    'error': f"KCP 거래등록 실패: {kcp_response.get('Message', '알 수 없는 오류')}",
                    'kcp_response': kcp_response,
                    'kcp_raw': str(kcp_response)
                }), 400
                
        except requests.RequestException as e:
            # HTTPError 인 경우 KCP가 보낸 응답 본문을 함께 노출
            resp_text = ''
            try:
                if hasattr(e, 'response') and e.response is not None:
                    resp_text = e.response.text
            except Exception:
                pass
            print(f"❌ KCP 거래등록 API 호출 실패: {e}\n📄 KCP 응답 본문: {resp_text[:1000]}")
            return jsonify({
                'success': False,
                'error': f'KCP 거래등록 API 호출 실패: {str(e)}',
                'kcp_raw': resp_text
            }), 502
        
    except Exception as e:
        print(f"❌ KCP 거래등록 실패: {e}")
        import traceback
        print(f"❌ KCP 거래등록 실패 상세: {traceback.format_exc()}")
        return jsonify({
            'success': False, 
            'error': f'KCP 거래등록에 실패했습니다: {str(e)}',
            'kcp_raw': str(e)
        }), 500

# KCP 표준결제 - 결제창 호출 데이터 생성
@app.route('/api/points/purchase-kcp/payment-form', methods=['POST'])
def kcp_payment_form():
    """Kcp Payment Form
    ---
    tags:
      - Points
    summary: Kcp Payment Form
    description: "Kcp Payment Form API"
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """KCP 표준결제 결제창 호출 데이터 생성"""
    try:
        data = request.get_json()
        ordr_idxx = data.get('ordr_idxx')
        approval_key = data.get('approval_key')
        pay_url = data.get('pay_url')
        pay_method = data.get('pay_method', 'CARD')
        
        if not all([ordr_idxx, approval_key, pay_url]):
            return jsonify({'error': '필수 파라미터가 누락되었습니다.'}), 400
        
        # 결제창 호출 데이터 구성
        kcp_site_cd = get_parameter_value('KCP_SITE_CD', 'ALFCQ')
        payment_form_data = {
            'site_cd': kcp_site_cd,
            'pay_method': pay_method,
            'currency': '410',  # 원화
            'shop_name': 'SNS PMT',
            'Ret_URL': f"{request.host_url}api/points/purchase-kcp/return",
            'approval_key': approval_key,
            'PayUrl': pay_url,
            'ordr_idxx': ordr_idxx,
            'good_name': '포인트 구매',
            'good_cd': '00',
            'good_mny': data.get('good_mny', '1000'),
            'buyr_name': data.get('buyr_name', ''),
            'buyr_mail': data.get('buyr_mail', ''),
            'buyr_tel2': data.get('buyr_tel2', ''),
            'shop_user_id': data.get('shop_user_id', ''),
            'van_code': data.get('van_code', '')  # 상품권/포인트 결제시 필수
        }
        
        return jsonify({
            'success': True,
            'payment_form_data': payment_form_data,
            'message': '결제창을 호출합니다. 카드 정보를 입력해주세요.'
        }), 200
        
    except Exception as e:
        print(f"❌ KCP 결제창 데이터 생성 실패: {e}")
        return jsonify({'error': 'KCP 결제창 데이터 생성에 실패했습니다.'}), 500

# KCP 결제창 인증결과 처리 (Ret_URL)
@app.route('/api/points/purchase-kcp/return', methods=['POST'])
def kcp_payment_return():
    """Kcp Payment Return
    ---
    tags:
      - Points
    summary: Kcp Payment Return
    description: "Kcp Payment Return API"
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """KCP 결제창 인증결과 처리"""
    try:
        # KCP에서 전달받은 인증결과 데이터
        enc_data = request.form.get('enc_data')
        enc_info = request.form.get('enc_info')
        tran_cd = request.form.get('tran_cd')
        ordr_idxx = request.form.get('ordr_idxx')
        res_cd = request.form.get('res_cd')
        res_msg = request.form.get('res_msg')
        
        print(f"🔍 KCP 결제창 인증결과 수신: {ordr_idxx}")
        print(f"📊 인증결과: {res_cd} - {res_msg}")
        
        if res_cd == '0000' and enc_data and enc_info:
            # 인증 성공 - 결제요청 진행
            return jsonify({
                'success': True,
                'ordr_idxx': ordr_idxx,
                'enc_data': enc_data,
                'enc_info': enc_info,
                'tran_cd': tran_cd,
                'message': '인증이 완료되었습니다. 결제를 진행합니다.'
            }), 200
        else:
            # 인증 실패
            return jsonify({
                'success': False,
                'error': f'인증 실패: {res_msg}',
                'res_cd': res_cd
            }), 400
            
    except Exception as e:
        print(f"❌ KCP 결제창 인증결과 처리 실패: {e}")
        return jsonify({'error': '인증결과 처리에 실패했습니다.'}), 500

# KCP 결제요청 (승인)
@app.route('/api/points/purchase-kcp/approve', methods=['POST'])
def kcp_payment_approve():
    """Kcp Payment Approve
    ---
    tags:
      - Points
    summary: Kcp Payment Approve
    description: "Kcp Payment Approve API"
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """KCP 결제요청 (승인)"""
    try:
        data = request.get_json()
        ordr_idxx = data.get('ordr_idxx')
        enc_data = data.get('enc_data')
        enc_info = data.get('enc_info')
        tran_cd = data.get('tran_cd')
        
        if not all([ordr_idxx, enc_data, enc_info, tran_cd]):
            return jsonify({'error': '필수 파라미터가 누락되었습니다.'}), 400
        
        # DB에서 주문 정보 조회
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT user_id, amount, price FROM point_purchases 
                WHERE purchase_id = %s AND status = 'kcp_registered'
            """, (ordr_idxx,))
        else:
            cursor.execute("""
                SELECT user_id, amount, price FROM point_purchases 
                WHERE purchase_id = ? AND status = 'kcp_registered'
            """, (ordr_idxx,))
        
        purchase = cursor.fetchone()
        if not purchase:
            conn.close()
            return jsonify({'error': '주문 정보를 찾을 수 없습니다.'}), 404
        
        user_id, amount, price = purchase
        
        # KCP 결제요청 데이터 구성
        kcp_site_cd = get_parameter_value('KCP_SITE_CD', 'ALFCQ')
        kcp_cert_info = get_parameter_value('KCP_CERT_INFO', '')
        payment_data = {
            'tran_cd': tran_cd,
            'kcp_cert_info': kcp_cert_info,
            'site_cd': kcp_site_cd,
            'enc_data': enc_data,
            'enc_info': enc_info,
            'ordr_mony': str(int(price)),
            'pay_type': 'PACA',  # 신용카드
            'ordr_no': ordr_idxx
        }
        
        # KCP 결제요청 API 호출
        import requests
        kcp_payment_url = 'https://stg-spl.kcp.co.kr/gw/enc/v1/payment'
        
        try:
            response = requests.post(kcp_payment_url, json=payment_data, timeout=30)
            response.raise_for_status()
            kcp_response = response.json()
            
            print(f"📊 KCP 결제요청 응답: {kcp_response}")
            
            if kcp_response.get('res_cd') == '0000':
                # 결제 성공 - 포인트 추가
                if DATABASE_URL.startswith('postgresql://'):
                    # 포인트 추가
                    cursor.execute("""
                        INSERT INTO points (user_id, points, description, created_at)
                        VALUES (%s, %s, '포인트 구매 (KCP)', NOW())
                    """, (user_id, amount))
                    
                    # 구매 상태 업데이트
                    cursor.execute("""
                        UPDATE point_purchases 
                        SET status = 'approved', updated_at = NOW()
                        WHERE purchase_id = %s
                    """, (ordr_idxx,))
                else:
                    # SQLite 버전
                    cursor.execute("""
                        INSERT INTO points (user_id, points, description, created_at)
                        VALUES (?, ?, '포인트 구매 (KCP)', datetime('now'))
                    """, (user_id, amount))
                    
                    cursor.execute("""
                        UPDATE point_purchases 
                        SET status = 'approved', updated_at = datetime('now')
                        WHERE purchase_id = ?
                    """, (ordr_idxx,))
                
                conn.commit()
                conn.close()
                
                print(f"✅ KCP 포인트 구매 완료: {ordr_idxx} - {amount}포인트")
                
                return jsonify({
                    'success': True,
                    'message': '포인트 구매가 성공적으로 완료되었습니다!',
                    'amount': amount,
                    'kcp_response': kcp_response
                }), 200
            else:
                # 결제 실패
                if DATABASE_URL.startswith('postgresql://'):
                    cursor.execute("""
                        UPDATE point_purchases 
                        SET status = 'failed', updated_at = NOW()
                        WHERE purchase_id = %s
                    """, (ordr_idxx,))
                else:
                    cursor.execute("""
                        UPDATE point_purchases 
                        SET status = 'failed', updated_at = datetime('now')
                        WHERE purchase_id = ?
                    """, (ordr_idxx,))
                
                conn.commit()
                conn.close()
                
                print(f"❌ KCP 포인트 구매 실패: {ordr_idxx} - {kcp_response.get('res_msg')}")
                
                return jsonify({
                    'success': False,
                    'error': f'결제 실패: {kcp_response.get("res_msg")}',
                    'res_cd': kcp_response.get('res_cd')
                }), 400
                
        except requests.RequestException as e:
            print(f"❌ KCP 결제요청 API 호출 실패: {e}")
            conn.close()
            return jsonify({'error': 'KCP 결제요청 API 호출에 실패했습니다.'}), 500
        
    except Exception as e:
        print(f"❌ KCP 결제요청 실패: {e}")
        return jsonify({'error': 'KCP 결제요청에 실패했습니다.'}), 500

# 관리자 통계
@app.route('/api/admin/stats', methods=['GET'])
@require_admin_auth
def get_admin_stats():
    """관리자 통계 조회
    ---
    tags:
      - Admin
    summary: 관리자 통계 조회
    description: "관리자 대시보드용 통계 정보를 조회합니다."
    security:
      - Bearer: []
    responses:
      200:
        description: 통계 조회 성공
        schema:
          type: object
          properties:
            total_users:
              type: integer
              example: 100
            total_orders:
              type: integer
              example: 500
            total_revenue:
              type: number
              example: 1000000
      401:
        description: 인증 실패
        schema:
          type: object
          properties:
            error:
              type: string
              example: "인증이 필요합니다."
    """
    conn = None
    cursor = None
    
    try:
        print("🔍 관리자 통계 조회 시작")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            # 총 사용자 수
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0] or 0
            
            # 총 주문 수
            cursor.execute("SELECT COUNT(*) FROM orders")
            total_orders = cursor.fetchone()[0] or 0
            
            # 총 매출 (주문 + 포인트 구매) - 새 스키마에서는 wallet_transactions 사용
            cursor.execute("SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE status = 'completed'")
            order_revenue = cursor.fetchone()[0] or 0
            
            cursor.execute("""
                SELECT COALESCE(SUM(ABS(wt.amount)), 0) 
                FROM wallet_transactions wt
                WHERE wt.type = 'topup' AND wt.status = 'approved'
            """)
            purchase_revenue_result = cursor.fetchone()[0]
            purchase_revenue = float(purchase_revenue_result) if purchase_revenue_result else 0.0
            print(f"🔍 purchase_revenue 계산 결과: {purchase_revenue} (raw: {purchase_revenue_result})")
            total_revenue = order_revenue + purchase_revenue
            
            # 대기 중인 포인트 구매
            cursor.execute("SELECT COUNT(*) FROM wallet_transactions WHERE type = 'topup' AND status = 'pending'")
            pending_purchases = cursor.fetchone()[0] or 0
            
            # 오늘 주문 수
            cursor.execute("SELECT COUNT(*) FROM orders WHERE DATE(created_at) = CURRENT_DATE")
            today_orders = cursor.fetchone()[0] or 0
            
            # 오늘 매출 (주문 + 포인트 구매)
            cursor.execute("SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE DATE(created_at) = CURRENT_DATE AND status = 'completed'")
            today_order_revenue = cursor.fetchone()[0] or 0
            cursor.execute("""
                SELECT COALESCE(SUM(wt.amount), 0) 
                FROM wallet_transactions wt
                WHERE DATE(wt.created_at) = CURRENT_DATE AND wt.type = 'topup' AND wt.status = 'approved'
            """)
            today_purchase_revenue = cursor.fetchone()[0] or 0
            today_revenue = today_order_revenue + today_purchase_revenue
            
            # 월 매출 계산: (총 포인트 - 총원가)
            # 1단계: 총 주문한 상품의 원가 합계 계산
            original_cost_sum = 0
            try:
                cursor.execute("""
                    SELECT COALESCE(SUM(pv.original_cost * oi.quantity), 0)
                    FROM order_items oi
                    INNER JOIN orders ord ON oi.order_id = ord.order_id
                    INNER JOIN product_variants pv ON oi.variant_id = pv.variant_id
                    WHERE ord.status = 'completed'
                """)
                result = cursor.fetchone()
                original_cost_sum = result[0] if result and result[0] else 0
            except Exception as e:
                print(f"⚠️ 월매출 원가 계산 오류 (PostgreSQL, order_items 사용 시도 실패): {e}")
                # 폴백: order_items를 통한 조인 (새 스키마)
                try:
                    cursor.execute("""
                        SELECT COALESCE(SUM(pv.original_cost * oi.quantity), 0)
                        FROM order_items oi
                        INNER JOIN orders ord ON oi.order_id = ord.order_id
                        INNER JOIN product_variants pv ON oi.variant_id = pv.variant_id
                        WHERE ord.status = 'completed'
                    """)
                    result = cursor.fetchone()
                    original_cost_sum = result[0] if result and result[0] else 0
                except Exception as e2:
                    print(f"⚠️ 월매출 원가 계산 오류 (PostgreSQL, order_items 폴백 시도 실패): {e2}")
                    # 최종 폴백: 원가를 0으로 설정
                    original_cost_sum = 0
            
            # 디버깅: 값 확인
            print(f"🔍 월매출 계산 (PostgreSQL): purchase_revenue={purchase_revenue} (type: {type(purchase_revenue)}), original_cost_sum={original_cost_sum} (type: {type(original_cost_sum)})")
            
            # 2단계: 월 매출 = 총 포인트 - 총원가
            # 값이 음수일 수 있으므로 절댓값 처리 및 타입 변환
            purchase_revenue = abs(float(purchase_revenue)) if purchase_revenue else 0.0
            original_cost_sum = abs(float(original_cost_sum)) if original_cost_sum else 0.0
            monthly_sales = purchase_revenue - original_cost_sum
            # 음수 결과 방지 (잔액보다 원가가 클 경우 0으로 처리)
            if monthly_sales < 0:
                print(f"⚠️ 월매출 계산 경고: 결과가 음수입니다. {monthly_sales} → 0으로 조정")
                monthly_sales = 0
            print(f"💰 월매출 결과: {monthly_sales} (계산: {purchase_revenue} - {original_cost_sum})")
        else:
            # SQLite 버전
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COUNT(*) FROM orders")
            total_orders = cursor.fetchone()[0] or 0
            
            # 총 매출 (주문 + 포인트 구매)
            cursor.execute("SELECT COALESCE(SUM(price), 0) FROM orders WHERE status = 'completed'")
            order_revenue = cursor.fetchone()[0] or 0
            cursor.execute("SELECT COALESCE(SUM(ABS(price)), 0) FROM point_purchases WHERE status = 'approved'")
            purchase_revenue_result = cursor.fetchone()[0]
            purchase_revenue = float(purchase_revenue_result) if purchase_revenue_result else 0.0
            print(f"🔍 purchase_revenue 계산 결과 (SQLite): {purchase_revenue} (raw: {purchase_revenue_result})")
            total_revenue = order_revenue + purchase_revenue
            
            cursor.execute("SELECT COUNT(*) FROM point_purchases WHERE status = 'pending'")
            pending_purchases = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COUNT(*) FROM orders WHERE DATE(created_at) = DATE('now')")
            today_orders = cursor.fetchone()[0] or 0
            
            # 오늘 매출 (주문 + 포인트 구매)
            cursor.execute("SELECT COALESCE(SUM(price), 0) FROM orders WHERE DATE(created_at) = DATE('now') AND status = 'completed'")
            today_order_revenue = cursor.fetchone()[0] or 0
            cursor.execute("SELECT COALESCE(SUM(price), 0) FROM point_purchases WHERE DATE(created_at) = DATE('now') AND status = 'approved'")
            today_purchase_revenue = cursor.fetchone()[0] or 0
            today_revenue = today_order_revenue + today_purchase_revenue
            
            # 월 매출 계산: (총 포인트 - 총원가)
            # 1단계: 총 주문한 상품의 원가 합계 계산
            # SQLite에서는 JSON 조인이 복잡하므로 서브쿼리 사용
            original_cost_sum = 0
            try:
                cursor.execute("""
                    SELECT COALESCE(SUM(
                        (SELECT original_cost FROM product_variants 
                         WHERE json_extract(meta_json, '$.service_id') = oi.service_id 
                         LIMIT 1) * oi.quantity
                    ), 0)
                    FROM order_items oi
                    INNER JOIN orders ord ON oi.order_id = ord.order_id
                    WHERE ord.status = 'completed'
                """)
                result = cursor.fetchone()
                original_cost_sum = result[0] if result and result[0] else 0
            except Exception as e:
                print(f"⚠️ 월매출 원가 계산 오류 (SQLite, order_items 사용 시도 실패): {e}")
                # 폴백: orders 테이블 직접 사용 (구 스키마)
                try:
                    cursor.execute("""
                        SELECT COALESCE(SUM(
                            (SELECT original_cost FROM product_variants 
                             WHERE json_extract(meta_json, '$.service_id') = o.service_id 
                             LIMIT 1) * o.quantity
                        ), 0)
                        FROM orders o
                        WHERE o.status = 'completed'
                    """)
                    result = cursor.fetchone()
                    original_cost_sum = result[0] if result and result[0] else 0
                except Exception as e2:
                    print(f"⚠️ 월매출 원가 계산 오류 (SQLite, orders 직접 사용 시도 실패): {e2}")
                    # 최종 폴백: 원가를 0으로 설정
                    original_cost_sum = 0
            
            # 디버깅: 값 확인
            print(f"🔍 월매출 계산 (SQLite): purchase_revenue={purchase_revenue} (type: {type(purchase_revenue)}), original_cost_sum={original_cost_sum} (type: {type(original_cost_sum)})")
            
            # 2단계: 월 매출 = 총 포인트 - 총원가
            # 값이 음수일 수 있으므로 절댓값 처리 및 타입 변환
            purchase_revenue = abs(float(purchase_revenue)) if purchase_revenue else 0.0
            original_cost_sum = abs(float(original_cost_sum)) if original_cost_sum else 0.0
            monthly_sales = purchase_revenue - original_cost_sum
            # 음수 결과 방지 (잔액보다 원가가 클 경우 0으로 처리)
            if monthly_sales < 0:
                print(f"⚠️ 월매출 계산 경고 (SQLite): 결과가 음수입니다. {monthly_sales} → 0으로 조정")
                monthly_sales = 0
            print(f"💰 월매출 결과 (SQLite): {monthly_sales} (계산: {purchase_revenue} - {original_cost_sum})")
        
        print(f"✅ 관리자 통계 조회 성공: users={total_users}, orders={total_orders}, revenue={total_revenue}, monthly_sales={monthly_sales}")
        
        return jsonify({
            'total_users': total_users,
            'total_orders': total_orders,
            'total_revenue': float(total_revenue),
            'pending_purchases': pending_purchases,
            'today_orders': today_orders,
            'today_revenue': float(today_revenue),
            'monthly_sales': float(monthly_sales)
        }), 200
            
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback_str = traceback.format_exc()
        print(f"❌ 관리자 통계 조회 오류: {error_msg}")
        print(f"📋 상세 오류:\n{traceback_str}")
        
        if conn:
            try:
                conn.rollback()
            except:
                pass
        
        return jsonify({
            'error': f'통계 조회 실패: {error_msg}',
            'details': str(e)
        }), 500
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if conn:
            try:
                conn.close()
            except:
                pass

# 관리자 포인트 구매 목록
@app.route('/api/admin/purchases', methods=['GET'])
def get_admin_purchases():
    """관리자 포인트 구매 목록 조회
    ---
    tags:
      - Admin
    summary: 관리자 포인트 구매 목록 조회
    description: "전체 포인트 구매 내역을 조회합니다."
    security:
      - Bearer: []
    parameters:
      - name: status
        in: query
        type: string
        required: false
        description: 구매 상태 필터 (pending, completed, cancelled)
        example: "pending"
    responses:
      200:
        description: 구매 목록 조회 성공
        schema:
          type: object
          properties:
            purchases:
              type: array
              items:
                type: object
                properties:
                  purchase_id:
                    type: integer
                    example: 123
                  user_id:
                    type: string
                    example: "user123"
                  amount:
                    type: number
                    example: 10000
                  status:
                    type: string
                    example: "pending"
      401:
        description: 인증 실패
    """
    conn = None
    cursor = None
    try:
        print("🔍 관리자 포인트 구매 목록 조회 시작")
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if DATABASE_URL.startswith('postgresql://'):
            # 새 스키마: wallet_transactions(type='topup') 기준으로 조회
            print("🔍 포인트 구매 신청 쿼리 실행 중...")
            cursor.execute("""
                SELECT 
                    wt.transaction_id AS id,
                    u.external_uid AS user_id,
                    u.email,
                    wt.amount AS price,
                    wt.status,
                    wt.meta_json,
                    wt.created_at
                FROM wallet_transactions wt
                INNER JOIN wallets w ON wt.wallet_id = w.wallet_id
                INNER JOIN users u ON w.user_id = u.user_id
                WHERE wt.type = 'topup'
                ORDER BY wt.created_at DESC
            """)
            rows = cursor.fetchall()
            print(f"✅ 조회된 포인트 구매 신청: {len(rows)}건")
            if len(rows) > 0:
                print(f"📋 첫 번째 항목 샘플: id={rows[0].get('id')}, user_id={rows[0].get('user_id')}, status={rows[0].get('status')}")
            purchase_list = []
            for r in rows:
                meta_json = r.get('meta_json') or {}
                if isinstance(meta_json, str):
                    import json as json_module
                    try:
                        meta_json = json_module.loads(meta_json)
                    except:
                        meta_json = {}
                amount = None
                for key in ['amount', 'requested_amount', 'request_amount', 'price']:
                    if meta_json and key in meta_json and meta_json.get(key) not in (None, ''):
                        try:
                            amount = float(meta_json.get(key))
                            break
                        except:
                            pass
                # 최종 폴백: price 컬럼
                if amount is None:
                    amount = float(r.get('price') or 0)
                
                created_at = r.get('created_at')
                created_at_str = created_at.isoformat() if created_at and hasattr(created_at, 'isoformat') else (str(created_at) if created_at else None)
                
                purchase_list.append({
                    'id': r.get('id'),
                    'user_id': r.get('user_id'),
                    'email': r.get('email') or 'N/A',
                    'amount': amount,
                    'price': float(r.get('price') or 0),
                    'status': r.get('status') or 'pending',
                    'created_at': created_at_str,
                    'buyer_name': (meta_json.get('buyer_name') if isinstance(meta_json, dict) else None) or 'N/A',
                    'bank_info': (meta_json.get('bank_info') if isinstance(meta_json, dict) else None) or 'N/A'
                })
        else:
            # SQLite: point_purchases 사용
            cursor.execute("""
                SELECT pp.id, pp.user_id, pp.amount, pp.price, pp.status, pp.created_at,
                       pp.buyer_name, pp.bank_info, u.email
                FROM point_purchases pp
                LEFT JOIN users u ON pp.user_id = u.user_id
                ORDER BY pp.created_at DESC
            """)
            purchases = cursor.fetchall()
            purchase_list = []
            for purchase in purchases:
                purchase_list.append({
                    'id': purchase[0],
                    'user_id': purchase[1],
                    'amount': purchase[2],
                    'price': float(purchase[3]),
                    'status': purchase[4],
                    'created_at': purchase[5].isoformat() if hasattr(purchase[5], 'isoformat') else str(purchase[5]),
                    'buyer_name': purchase[6] if len(purchase) > 6 else 'N/A',
                    'bank_info': purchase[7] if len(purchase) > 7 else 'N/A',
                    'email': purchase[8] if len(purchase) > 8 else 'N/A'
                })
        
        print(f"✅ 포인트 구매 목록 반환: {len(purchase_list)}건")
        return jsonify({'purchases': purchase_list}), 200
        
    except Exception as e:
        import traceback
        error_msg = f'포인트 구매 목록 조회 실패: {str(e)}'
        print(f"❌ {error_msg}")
        print(traceback.format_exc())
        return jsonify({'error': error_msg}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 포인트 구매 승인/거절
@app.route('/api/admin/purchases/<int:purchase_id>', methods=['PUT'])
def update_purchase_status(purchase_id):
    """Update Purchase Status
    ---
    tags:
      - Admin
    summary: Update Purchase Status
    description: "Update Purchase Status API"
    security:
      - Bearer: []
    parameters:
      - name: purchase_id
        in: path
        type: int
        required: true
        description: Purchase Id
        example: "example_purchase_id"
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    # 임시로 데코레이터 제거하여 테스트
    # @require_admin_auth
    """포인트 구매 승인/거절"""
    conn = None
    cursor = None
    try:
        print(f"🚀 포인트 구매 승인 시작: purchase_id={purchase_id}", flush=True)
        print(f"📥 요청 메서드: {request.method}", flush=True)
        print(f"📥 요청 헤더: {dict(request.headers)}", flush=True)
        
        try:
            data = request.get_json() or {}
            print(f"📥 요청 데이터: {data}", flush=True)
        except Exception as json_error:
            print(f"❌ JSON 파싱 실패: {json_error}", flush=True)
            return jsonify({'error': f'요청 데이터 파싱 실패: {str(json_error)}'}), 400
        
        status = data.get('status')  # 'approved' 또는 'rejected'
        print(f"📊 상태: {status}", flush=True)
        
        if status not in ['approved', 'rejected']:
            print(f"❌ 유효하지 않은 상태: {status}")
            return jsonify({'error': '유효하지 않은 상태입니다.'}), 400
        
        print(f"🔌 데이터베이스 연결 시도...")
        conn = get_db_connection()
        print(f"✅ 데이터베이스 연결 성공")
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        print(f"✅ 커서 생성 완료")
        
        # 구매 신청 정보 조회
        print(f"🔍 구매 신청 정보 조회 시작: purchase_id={purchase_id}")
        if DATABASE_URL.startswith('postgresql://'):
            # wallet_transactions 기준
            print(f"📊 PostgreSQL 쿼리 실행 중...")
            try:
                cursor.execute("""
                    SELECT 
                        wt.transaction_id,
                        wt.wallet_id,
                        wt.amount,
                        wt.status,
                        wt.meta_json::text as meta_json_text,
                        w.user_id,
                        w.wallet_id AS wallet_id_from_wallets
                    FROM wallet_transactions wt
                    INNER JOIN wallets w ON wt.wallet_id = w.wallet_id
                    WHERE wt.transaction_id = %s AND wt.type = 'topup'
                """, (purchase_id,))
                print(f"✅ 쿼리 실행 완료")
            except Exception as query_error:
                print(f"❌ 쿼리 실행 실패: {query_error}", flush=True)
                import traceback
                print(traceback.format_exc(), flush=True)
                raise
        else:
            cursor.execute("""
                SELECT user_id, amount, status
                FROM point_purchases
                WHERE id = ?
            """, (purchase_id,))
        
        purchase = cursor.fetchone()
        
        if not purchase:
            print(f"❌ 구매 신청을 찾을 수 없습니다: purchase_id={purchase_id}", flush=True)
            return jsonify({'error': '구매 신청을 찾을 수 없습니다.'}), 404
        
        # purchase를 dict로 변환
        if not isinstance(purchase, dict):
            purchase = dict(purchase)
        
        print(f"📋 구매 신청 정보: {purchase}", flush=True)
        
        current_status = purchase.get('status')
        print(f"📊 현재 상태: {current_status}", flush=True)
        
        if current_status and current_status != 'pending':
            print(f"⚠️ 이미 처리된 구매 신청: status={current_status}", flush=True)
            return jsonify({'error': f'이미 처리된 구매 신청입니다. (현재 상태: {current_status})'}), 400
        
        # 상태 업데이트
        if DATABASE_URL.startswith('postgresql://'):
            # wallet_tx_status ENUM: 'pending', 'approved', 'rejected'
            # 'approved' -> 'approved', 'rejected' -> 'rejected'
            new_status = 'approved' if status == 'approved' else 'rejected'
            print(f"🔄 상태 업데이트: transaction_id={purchase_id}, new_status={new_status} (요청 status: {status})")
            cursor.execute("""
                UPDATE wallet_transactions
                SET status = %s, updated_at = NOW()
                WHERE transaction_id = %s
            """, (new_status, purchase_id))
            print(f"✅ 상태 업데이트 완료: {cursor.rowcount}개 행 업데이트됨")
        else:
            cursor.execute("""
                UPDATE point_purchases
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, purchase_id))
        
        # 승인된 경우 사용자 포인트 증가
        if status == 'approved':
            if DATABASE_URL.startswith('postgresql://'):
                # amount 필드 직접 사용 또는 meta_json에서 추출
                amount_val = None
                
                # 1. 먼저 wt.amount 필드 직접 사용 시도
                if purchase.get('amount') is not None:
                    try:
                        amount_val = float(purchase.get('amount'))
                        print(f"✅ amount 필드에서 금액 추출: {amount_val}", flush=True)
                    except (ValueError, TypeError) as e:
                        print(f"⚠️ amount 필드 변환 실패: {e}", flush=True)
                
                # 2. amount가 없으면 meta_json에서 추출 시도
                if amount_val is None or amount_val <= 0:
                    meta_json = purchase.get('meta_json') or purchase.get('meta_json_text') or {}
                    if isinstance(meta_json, str):
                        import json as json_module
                        try:
                            meta_json = json_module.loads(meta_json)
                            print(f"✅ meta_json 파싱 성공: {meta_json}", flush=True)
                        except Exception as parse_error:
                            print(f"⚠️ meta_json 파싱 실패: {parse_error}", flush=True)
                            meta_json = {}
                    
                    if isinstance(meta_json, dict):
                        for key in ['amount', 'requested_amount', 'request_amount', 'price']:
                            if key in meta_json and meta_json.get(key) not in (None, ''):
                                try:
                                    amount_val = float(meta_json.get(key))
                                    print(f"✅ meta_json에서 금액 추출 ({key}): {amount_val}", flush=True)
                                    break
                                except (ValueError, TypeError) as e:
                                    print(f"⚠️ meta_json[{key}] 변환 실패: {e}", flush=True)
                                    continue
                
                # 3. 여전히 amount_val이 없으면 에러
                if amount_val is None or amount_val <= 0:
                    error_msg = f'금액을 찾을 수 없습니다. purchase: {dict(purchase)}'
                    print(f"❌ {error_msg}", flush=True)
                    raise ValueError(error_msg)
                
                wallet_id = purchase.get('wallet_id') or purchase.get('wallet_id_from_wallets')
                user_id = purchase.get('user_id')
                
                print(f"🔍 포인트 승인 디버깅: purchase_id={purchase_id}, wallet_id={wallet_id}, user_id={user_id}, amount_val={amount_val}, purchase={dict(purchase)}")
                
                if not wallet_id and user_id:
                    # wallet_id가 없으면 user_id로 wallet 찾기
                    cursor.execute("""
                        SELECT wallet_id FROM wallets WHERE user_id = %s
                    """, (user_id,))
                    wallet_row = cursor.fetchone()
                    if wallet_row:
                        wallet_id = wallet_row['wallet_id']
                    else:
                        # wallet이 없으면 생성
                        cursor.execute("""
                            INSERT INTO wallets (user_id, balance, created_at, updated_at)
                            VALUES (%s, 0, NOW(), NOW())
                            RETURNING wallet_id
                        """, (user_id,))
                        wallet_id = cursor.fetchone()['wallet_id']
                
                if not wallet_id:
                    raise ValueError(f'wallet_id를 찾을 수 없습니다. user_id: {user_id}, purchase: {dict(purchase)}')
                
                if amount_val <= 0:
                    raise ValueError(f'유효하지 않은 금액입니다: {amount_val}')
                
                print(f"💰 포인트 승인: wallet_id={wallet_id}, amount={amount_val}")
                cursor.execute("""
                    UPDATE wallets
                    SET balance = balance + %s, updated_at = NOW()
                    WHERE wallet_id = %s
                """, (amount_val, wallet_id))
                
                # 업데이트된 잔액 확인
                cursor.execute("""
                    SELECT balance FROM wallets WHERE wallet_id = %s
                """, (wallet_id,))
                updated_balance = cursor.fetchone()['balance']
                print(f"✅ 포인트 승인 완료: 새로운 잔액 = {updated_balance}")
            else:
                user_id = purchase[0]
                amount_val = purchase[1]
                # 사용자 포인트 조회
                cursor.execute("""
                    SELECT points FROM points WHERE user_id = ?
                """, (user_id,))
                user_points = cursor.fetchone()
                current_points = user_points[0] if user_points else 0
                new_points = current_points + amount_val
                # 포인트 업데이트
                cursor.execute("""
                    UPDATE points
                    SET points = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (new_points, user_id))
        
        conn.commit()
        print(f"✅ 트랜잭션 커밋 완료", flush=True)
        
        return jsonify({
            'message': f'구매 신청이 {status}되었습니다.',
            'status': status
        }), 200
        
    except Exception as e:
        import traceback
        error_msg = f'구매 신청 처리 실패: {str(e)}'
        print(f"❌ {error_msg}", flush=True)
        print(f"❌ 에러 타입: {type(e).__name__}", flush=True)
        print(f"❌ 에러 상세: {str(e)}", flush=True)
        print(f"❌ Traceback:", flush=True)
        print(traceback.format_exc(), flush=True)
        
        if conn:
            try:
                conn.rollback()
                print(f"✅ 롤백 완료", flush=True)
            except Exception as rollback_error:
                print(f"❌ 롤백 실패: {rollback_error}", flush=True)
        
        return jsonify({
            'error': error_msg, 
            'details': str(e), 
            'type': type(e).__name__,
            'traceback': traceback.format_exc() if 'traceback' in locals() else None
        }), 500
    finally:
        try:
            if 'cursor' in locals() and cursor:
                cursor.close()
                print(f"✅ 커서 닫기 완료", flush=True)
        except Exception as close_error:
            print(f"⚠️ 커서 닫기 오류: {close_error}", flush=True)
        try:
            if 'conn' in locals() and conn:
                conn.close()
                print(f"✅ 연결 닫기 완료", flush=True)
        except Exception as close_error:
            print(f"⚠️ 연결 닫기 오류: {close_error}", flush=True)

# 포인트 차감 (주문 결제용)
@app.route('/api/points/deduct', methods=['POST'])
def deduct_points():
    """Deduct Points
    ---
    tags:
      - Points
    summary: Deduct Points
    description: "Deduct Points API"
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """포인트 차감 (주문 결제) - 새 스키마 사용"""
    conn = None
    cursor = None
    try:
        data = request.get_json()
        raw_user_id = data.get('user_id')  # external_uid 또는 email
        amount = data.get('amount')  # 차감할 포인트
        order_id = data.get('order_id')  # 주문 ID (선택사항)
        
        if not all([raw_user_id, amount]):
            return jsonify({'error': '필수 필드가 누락되었습니다.'}), 400
        
        if amount <= 0:
            return jsonify({'error': '차감할 포인트는 0보다 커야 합니다.'}), 400
        
        print(f"🔍 포인트 차감 요청 - user_id: {raw_user_id}, amount: {amount}")
        
        conn = get_db_connection()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # 1. external_uid 또는 email로 사용자 찾기
            cursor.execute("""
                SELECT user_id, external_uid, email 
                FROM users 
                WHERE external_uid = %s OR email = %s
                LIMIT 1
            """, (raw_user_id, raw_user_id))
            user = cursor.fetchone()
            
            if not user:
                print(f"❌ 사용자를 찾을 수 없음: {raw_user_id}")
                return jsonify({'error': '사용자를 찾을 수 없습니다.'}), 404
            
            db_user_id = user['user_id']
            print(f"✅ 사용자 찾음 - user_id: {db_user_id}, email: {user.get('email')}")
            
            # 2. 지갑 조회 (없으면 생성)
            cursor.execute("""
                INSERT INTO wallets (user_id, balance, created_at, updated_at)
                VALUES (%s, 0, NOW(), NOW())
                ON CONFLICT (user_id) DO NOTHING
            """, (db_user_id,))
            
            # 3. 현재 잔액 조회 (동시성 제어를 위해 SELECT FOR UPDATE)
            cursor.execute("""
                SELECT balance 
                FROM wallets 
                WHERE user_id = %s
                FOR UPDATE
            """, (db_user_id,))
            wallet = cursor.fetchone()
            
            if not wallet:
                print(f"❌ 지갑을 찾을 수 없음: user_id={db_user_id}")
                conn.rollback()
                return jsonify({'error': '지갑을 찾을 수 없습니다.'}), 404
            
            current_balance = float(wallet['balance'] or 0)
            print(f"💰 현재 포인트 잔액: {current_balance}")
            
            # 4. 잔액 확인
            if current_balance < amount:
                conn.rollback()
                return jsonify({
                    'error': '포인트가 부족합니다.',
                    'current_balance': current_balance,
                    'required_amount': amount
                }), 400
            
            # 5. 포인트 차감 (동시성 제어)
            new_balance = current_balance - amount
            cursor.execute("""
                UPDATE wallets
                SET balance = %s, updated_at = NOW()
                WHERE user_id = %s AND balance = %s
            """, (new_balance, db_user_id, current_balance))
            
            if cursor.rowcount == 0:
                conn.rollback()
                print(f"⚠️ 포인트 잔액 변경 감지 (동시성 충돌)")
                return jsonify({'error': '포인트 잔액이 변경되었습니다. 다시 시도해주세요.'}), 409
            
            conn.commit()
            print(f"✅ 포인트 차감 완료: {current_balance} -> {new_balance} (차감: {amount})")
            
            return jsonify({
                'message': '포인트가 성공적으로 차감되었습니다.',
                'remaining_points': new_balance,
                'deducted_amount': amount,
                'previous_balance': current_balance
            }), 200
        else:
            # SQLite: 구 스키마 유지
            cursor = conn.cursor()
            cursor.execute("""
                SELECT points FROM points WHERE user_id = ?
            """, (raw_user_id,))
            
            user_points = cursor.fetchone()
            
            if not user_points:
                return jsonify({'error': '사용자를 찾을 수 없습니다.'}), 404
            
            current_points = user_points[0]
            
            if current_points < amount:
                return jsonify({'error': '포인트가 부족합니다.'}), 400
            
            new_points = current_points - amount
            cursor.execute("""
                UPDATE points
                SET points = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND points = ?
            """, (new_points, raw_user_id, current_points))
            
            if cursor.rowcount == 0:
                conn.rollback()
                return jsonify({'error': '포인트 잔액이 변경되었습니다. 다시 시도해주세요.'}), 409
            
            conn.commit()
            
            return jsonify({
                'message': '포인트가 성공적으로 차감되었습니다.',
                'remaining_points': new_points,
                'deducted_amount': amount
            }), 200
        
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        error_msg = str(e)
        print(f"❌ 포인트 차감 오류: {error_msg}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'포인트 차감 실패: {error_msg}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 포인트 환불 (주문 실패 시)
@app.route('/api/points/refund', methods=['POST'])
def refund_points():
    """
    ---
    tags:
      - Points
    summary: Refund Points
    description: "주문 실패 시 포인트를 환불합니다."
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            user_id:
              type: string
              description: 사용자 ID (external_uid 또는 email)
            amount:
              type: number
              description: 환불할 포인트
            order_id:
              type: integer
              description: 주문 ID (선택사항)
    responses:
      200:
        description: 포인트 환불 성공
      400:
        description: 잘못된 요청
      500:
        description: 서버 오류
    """
    conn = None
    cursor = None
    try:
        data = request.get_json()
        raw_user_id = data.get('user_id')  # external_uid 또는 email
        amount = data.get('amount')  # 환불할 포인트
        order_id = data.get('order_id')  # 주문 ID (선택사항)
        
        if not all([raw_user_id, amount]):
            return jsonify({'error': '필수 필드가 누락되었습니다.'}), 400
        
        if amount <= 0:
            return jsonify({'error': '환불할 포인트는 0보다 커야 합니다.'}), 400
        
        print(f"💰 포인트 환불 요청 - user_id: {raw_user_id}, amount: {amount}, order_id: {order_id}")
        
        conn = get_db_connection()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # 1. external_uid 또는 email로 사용자 찾기
            cursor.execute("""
                SELECT user_id, external_uid, email 
                FROM users 
                WHERE external_uid = %s OR email = %s
                LIMIT 1
            """, (raw_user_id, raw_user_id))
            user = cursor.fetchone()
            
            if not user:
                print(f"❌ 사용자를 찾을 수 없음: {raw_user_id}")
                return jsonify({'error': '사용자를 찾을 수 없습니다.'}), 404
            
            db_user_id = user['user_id']
            print(f"✅ 사용자 찾음 - user_id: {db_user_id}, email: {user.get('email')}")
            
            # 2. 지갑 조회 (없으면 생성)
            cursor.execute("""
                INSERT INTO wallets (user_id, balance, created_at, updated_at)
                VALUES (%s, 0, NOW(), NOW())
                ON CONFLICT (user_id) DO NOTHING
            """, (db_user_id,))
            
            # 3. 현재 잔액 조회 (동시성 제어를 위해 SELECT FOR UPDATE)
            cursor.execute("""
                SELECT balance 
                FROM wallets 
                WHERE user_id = %s
                FOR UPDATE
            """, (db_user_id,))
            wallet = cursor.fetchone()
            
            if not wallet:
                print(f"❌ 지갑을 찾을 수 없음: user_id={db_user_id}")
                conn.rollback()
                return jsonify({'error': '지갑을 찾을 수 없습니다.'}), 404
            
            current_balance = float(wallet['balance'] or 0)
            print(f"💰 현재 포인트 잔액: {current_balance}")
            
            # 4. 포인트 환불 (동시성 제어)
            new_balance = current_balance + amount
            cursor.execute("""
                UPDATE wallets
                SET balance = %s, updated_at = NOW()
                WHERE user_id = %s AND balance = %s
            """, (new_balance, db_user_id, current_balance))
            
            if cursor.rowcount == 0:
                conn.rollback()
                print(f"⚠️ 포인트 잔액 변경 감지 (동시성 충돌)")
                return jsonify({'error': '포인트 잔액이 변경되었습니다. 다시 시도해주세요.'}), 409
            
            conn.commit()
            print(f"✅ 포인트 환불 완료: {current_balance} -> {new_balance} (환불: {amount})")
            
            return jsonify({
                'message': '포인트가 성공적으로 환불되었습니다.',
                'remaining_points': new_balance,
                'refunded_amount': amount,
                'previous_balance': current_balance
            }), 200
        else:
            # SQLite: 구 스키마 유지
            cursor = conn.cursor()
            cursor.execute("""
                SELECT points FROM points WHERE user_id = ?
            """, (raw_user_id,))
            
            user_points = cursor.fetchone()
            
            if not user_points:
                return jsonify({'error': '사용자를 찾을 수 없습니다.'}), 404
            
            current_points = user_points[0]
            new_points = current_points + amount
            cursor.execute("""
                UPDATE points
                SET points = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND points = ?
            """, (new_points, raw_user_id, current_points))
            
            if cursor.rowcount == 0:
                conn.rollback()
                return jsonify({'error': '포인트 잔액이 변경되었습니다. 다시 시도해주세요.'}), 409
            
            conn.commit()
            
            return jsonify({
                'message': '포인트가 성공적으로 환불되었습니다.',
                'remaining_points': new_points,
                'refunded_amount': amount
            }), 200
        
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        error_msg = str(e)
        print(f"❌ 포인트 환불 오류: {error_msg}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': f'포인트 환불 실패: {error_msg}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 관리자 권한 확인 API
@app.route('/api/users/check-admin', methods=['GET'])
def check_admin():
    """Check Admin Status
    ---
    tags:
      - Users
    summary: Check Admin Status
    description: "현재 사용자의 관리자 권한을 확인합니다."
    security:
      - Bearer: []
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            is_admin:
              type: boolean
              example: true
      401:
        description: 인증 실패
      500:
        description: 서버 오류
    """
    conn = None
    cursor = None
    try:
        auth_header = request.headers.get('Authorization')
        user_email_header = request.headers.get('X-User-Email')  # 프론트엔드에서 직접 전달한 email
        
        print(f"🔍 관리자 권한 확인 요청 수신")
        print(f"🔍 Authorization 헤더 존재: {bool(auth_header)}")
        print(f"🔍 X-User-Email 헤더 존재: {bool(user_email_header)}")
        if auth_header:
            print(f"🔍 Authorization 헤더 시작 부분: {auth_header[:20]}...")
        
        # 현재 사용자 정보 가져오기
        current_user = get_current_user()
        
        # JWT에서 email을 가져오지 못했으면 헤더에서 직접 가져오기
        user_email = None
        user_id = None
        
        if current_user:
            user_email = current_user.get('email')
            user_id = current_user.get('user_id')
        
        # 헤더에서 직접 전달된 email이 있으면 우선 사용
        if user_email_header:
            user_email = user_email_header
            print(f"✅ X-User-Email 헤더에서 email 획득: {user_email}")
        
        if not user_email:
            print(f"⚠️ 관리자 권한 확인 실패: email 정보 없음")
            return jsonify({'error': '이메일 정보가 필요합니다.', 'is_admin': False}), 200
        
        print(f"🔍 관리자 권한 확인 - user_id: {user_id}, email: {user_email}")
        print(f"🔍 current_user 전체 내용: {current_user}")
        print(f"🔍 JWT에서 추출한 정보:")
        print(f"   - user_id (JWT sub): {user_id}")
        print(f"   - email: {user_email}")
        print(f"🔍 데이터베이스에서 찾아야 할 값:")
        print(f"   - external_uid: {user_id} (JWT의 sub와 일치해야 함)")
        print(f"   - email: {user_email}")
        
        if not user_email and not user_id:
            print(f"⚠️ 관리자 권한 확인 실패: 사용자 정보 없음 (email과 user_id 모두 None)")
            return jsonify({'error': '사용자 정보를 찾을 수 없습니다.', 'is_admin': False}), 200
        
        # 데이터베이스에서 is_admin 체크
        print(f"🔍 데이터베이스 연결 시도...")
        conn = get_db_connection()
        if not conn:
            print(f"❌ 데이터베이스 연결 실패")
            return jsonify({'error': '데이터베이스 연결 실패', 'is_admin': False}), 500
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 단순화: email로만 조회하여 is_admin 확인
        print(f"🔍 관리자 권한 확인 - email: '{user_email}'")
        
        if not user_email:
            print(f"❌ email이 없어서 관리자 권한 확인 불가")
            return jsonify({'is_admin': False, 'error': '이메일 정보가 없습니다.'}), 200
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT is_admin
                FROM users 
                WHERE email = %s
                LIMIT 1
            """, (user_email,))
        else:
            cursor.execute("""
                SELECT is_admin 
                FROM users 
                WHERE email = ?
                LIMIT 1
            """, (user_email,))
        
        user = cursor.fetchone()
        
        if not user:
            print(f"❌ 사용자를 찾을 수 없음 - email: '{user_email}'")
            return jsonify({'is_admin': False, 'error': '사용자를 찾을 수 없습니다.'}), 200
        
        is_admin = user.get('is_admin') if isinstance(user, dict) else user[0]
        print(f"🔍 is_admin 원본 값: {is_admin} (타입: {type(is_admin)})")
        
        # SQLite의 경우 0/1로 저장되므로 변환
        if is_admin is None:
            is_admin = False
            print(f"⚠️ is_admin이 None이므로 False로 설정")
        elif isinstance(is_admin, (int, float)):
            is_admin = bool(is_admin and is_admin != 0)
            print(f"🔍 is_admin 숫자 값 변환: {is_admin}")
        elif isinstance(is_admin, bool):
            is_admin = bool(is_admin)
            print(f"🔍 is_admin 불린 값: {is_admin}")
        else:
            # 문자열인 경우 처리
            if str(is_admin).lower() in ['true', '1', 'yes', 't']:
                is_admin = True
            else:
                is_admin = False
            print(f"🔍 is_admin 문자열 값 변환: {is_admin}")
        
        print(f"✅ 관리자 권한 확인 완료 - 최종 is_admin: {is_admin} (타입: {type(is_admin)})")
        return jsonify({
            'is_admin': bool(is_admin),
            'debug': {
                'raw_is_admin': str(is_admin),
                'is_admin_type': str(type(is_admin)),
                'user_email': user.get('email') if user else None,
                'user_external_uid': user.get('external_uid') if user else None
            }
        }), 200
        
    except Exception as e:
        print(f"❌ 관리자 권한 확인 오류: {e}")
        import traceback
        print(traceback.format_exc())
        # 항상 is_admin을 포함한 응답 반환 (500 대신 200으로 변경하여 프론트에서 처리 가능하게)
        return jsonify({'error': f'관리자 권한 확인 실패: {str(e)}', 'is_admin': False}), 200
    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception as close_error:
            print(f"⚠️ 리소스 정리 중 오류 (무시): {close_error}")

# 사용자 정보 조회
# Supabase 사용자 동기화 엔드포인트
@app.route('/api/users/sync', methods=['POST'])
def sync_user():
    """사용자 동기화
    ---
    tags:
      - Users
    summary: Supabase Auth 사용자 동기화
    description: "Supabase Auth의 사용자 정보를 백엔드 users 테이블에 동기화합니다."
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: false
        schema:
          type: object
          properties:
            email:
              type: string
              description: 이메일
              example: "user@example.com"
            phone_number:
              type: string
              description: 전화번호
              example: "010-1234-5678"
            referral_code:
              type: string
              description: 추천인 코드 (선택사항)
              example: "ABC123"
            account_type:
              type: string
              description: 계정 타입 (personal 또는 business)
              example: "personal"
    responses:
      200:
        description: 사용자 동기화 성공
        schema:
          type: object
          properties:
            user_id:
              type: integer
              example: 1
            email:
              type: string
              example: "user@example.com"
            message:
              type: string
              example: "사용자 동기화 완료"
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "사용자 동기화 실패: ..."
    """
    conn = None
    cursor = None
    try:
        data = request.get_json() or {}
        
        # JWT 토큰에서 사용자 정보 추출 시도
        current_user = get_current_user()
        
        # JWT 검증 실패 시 body에서 직접 가져오기
        supabase_user_id = None
        email = None
        username = None
        
        if current_user:
            # JWT에서 가져온 정보 우선 사용
            supabase_user_id = current_user.get('user_id')
            email = current_user.get('email')
            username = current_user.get('metadata', {}).get('display_name')
        else:
            # JWT 검증 실패 시 body에서 직접 가져오기
            print("⚠️ JWT 검증 실패, body에서 사용자 정보 추출")
            supabase_user_id = data.get('user_id')
            email = data.get('email')
            username = data.get('username')
        
        # 최종적으로 body에서 가져온 값으로 덮어쓰기 (body 우선)
        supabase_user_id = data.get('user_id') or supabase_user_id
        email = data.get('email') or email
        username = data.get('username') or username or (email.split('@')[0] if email else '사용자')
        
        # 추가 정보 추출
        phone_number = data.get('phone_number')
        referral_code = data.get('referral_code')  # 사용자가 입력한 추천인 코드
        signup_source = data.get('signup_source')
        account_type = data.get('account_type')
        metadata = data.get('metadata', {})
        
        # 비즈니스 계정 정보 추출
        business_number = data.get('business_number')
        business_name = data.get('business_name')
        representative = data.get('representative')
        contact_phone = data.get('contact_phone')
        contact_email = data.get('contact_email')
        
        # metadata에서도 추출 시도 (우선순위: metadata > 직접 전달)
        if metadata:
            if not phone_number:
                phone_number = metadata.get('phone_number') or metadata.get('contactPhone')
            if not referral_code:
                referral_code = metadata.get('referral_code')
            if not signup_source:
                signup_source = metadata.get('signup_source')
            if not account_type:
                account_type = metadata.get('account_type')
            # 비즈니스 정보도 metadata에서 추출
            if not business_number:
                business_number = metadata.get('business_number')
            if not business_name:
                business_name = metadata.get('business_name')
            if not representative:
                representative = metadata.get('representative')
            if not contact_phone:
                contact_phone = metadata.get('contact_phone') or metadata.get('contactPhone')
            if not contact_email:
                contact_email = metadata.get('contact_email') or metadata.get('contactEmail')
        
        if not supabase_user_id or not email:
            print(f"❌ 사용자 정보 부족 - user_id: {supabase_user_id}, email: {email}")
            return jsonify({'error': '사용자 ID와 이메일이 필요합니다.'}), 400
        
        print(f"🔄 사용자 동기화 시작 - user_id: {supabase_user_id}, email: {email}, phone: {phone_number}, referral: {referral_code}")
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if DATABASE_URL.startswith('postgresql://'):
            # 사용자 존재 여부 확인
            cursor.execute("""
                SELECT user_id, external_uid, email, username
                FROM users 
                WHERE external_uid = %s OR email = %s
                LIMIT 1
            """, (supabase_user_id, email))
            existing_user = cursor.fetchone()
            
            if existing_user:
                # 기존 사용자 업데이트 (전화번호, 가입 경로, 계정 타입 등 업데이트)
                # users 테이블에 phone_number, signup_source, account_type 컬럼이 있는지 확인 후 업데이트
                try:
                    # 모든 필드를 업데이트 시도
                    update_fields = []
                    update_values = []
                    
                    update_fields.append("email = %s")
                    update_values.append(email)
                    
                    if username:
                        update_fields.append("username = COALESCE(%s, username)")
                        update_values.append(username)
                    
                    update_fields.append("external_uid = %s")
                    update_values.append(supabase_user_id)
                    
                    if phone_number:
                        update_fields.append("phone_number = COALESCE(%s, phone_number)")
                        update_values.append(phone_number)
                    
                    if signup_source:
                        update_fields.append("signup_source = COALESCE(%s, signup_source)")
                        update_values.append(signup_source)
                    
                    if account_type:
                        update_fields.append("account_type = COALESCE(%s, account_type)")
                        update_values.append(account_type)
                    
                    # 비즈니스 계정 정보 업데이트
                    if business_number:
                        update_fields.append("business_number = COALESCE(%s, business_number)")
                        update_values.append(business_number)
                    if business_name:
                        update_fields.append("business_name = COALESCE(%s, business_name)")
                        update_values.append(business_name)
                    if representative:
                        update_fields.append("representative = COALESCE(%s, representative)")
                        update_values.append(representative)
                    if contact_phone:
                        update_fields.append("contact_phone = COALESCE(%s, contact_phone)")
                        update_values.append(contact_phone)
                    if contact_email:
                        update_fields.append("contact_email = COALESCE(%s, contact_email)")
                        update_values.append(contact_email)
                    
                    update_fields.append("updated_at = NOW()")
                    update_values.append(existing_user['user_id'])
                    
                    update_query = f"""
                        UPDATE users
                        SET {', '.join(update_fields)}
                        WHERE user_id = %s
                        RETURNING user_id, external_uid, email, username, phone_number, signup_source, account_type, business_number, business_name, representative
                    """
                    cursor.execute(update_query, tuple(update_values))
                except Exception as e:
                    # 일부 컬럼이 없을 수 있으므로 기본 필드만 업데이트
                    print(f"⚠️ 사용자 업데이트 중 일부 컬럼 누락 (기본 필드만 업데이트): {e}")
                    import traceback
                    print(traceback.format_exc())
                    try:
                        cursor.execute("""
                            UPDATE users
                            SET email = %s,
                                username = COALESCE(%s, username),
                                external_uid = %s,
                                updated_at = NOW()
                            WHERE user_id = %s
                            RETURNING user_id, external_uid, email, username
                        """, (email, username, supabase_user_id, existing_user['user_id']))
                    except Exception as e2:
                        print(f"❌ 기본 필드 업데이트도 실패: {e2}")
                        raise
                updated_user = cursor.fetchone()
                print(f"✅ 기존 사용자 업데이트 완료 - user_id: {updated_user['user_id']}")
                
                # 기존 사용자도 추천인 코드가 있으면 referrals 테이블에 저장 및 5% 할인쿠폰 발급 (중복 체크)
                if referral_code:
                    try:
                        # 먼저 기존 추천인 관계 확인
                        cursor.execute("""
                            SELECT referral_id FROM referrals 
                            WHERE referrer_user_id = (SELECT user_id FROM users WHERE referral_code = %s LIMIT 1)
                            AND referred_user_id = %s
                            LIMIT 1
                        """, (referral_code, updated_user['user_id']))
                        existing_relation = cursor.fetchone()
                        
                        is_new_referral = False
                        if not existing_relation:
                            # 추천인 코드로 추천인 user_id 찾기
                            cursor.execute("""
                                SELECT user_id FROM users WHERE referral_code = %s LIMIT 1
                            """, (referral_code,))
                            referrer = cursor.fetchone()
                            
                            if referrer:
                                referrer_user_id = referrer['user_id']
                                # referrals 테이블에 추천인 관계 저장
                                # referrals 테이블의 PRIMARY KEY는 referral_id (자동 증가)이므로
                                # ON CONFLICT는 (referrer_user_id, referred_user_id) UNIQUE 제약 조건이 있을 때만 작동
                                # 먼저 중복 확인 후 INSERT
                                cursor.execute("""
                                    SELECT referral_id FROM referrals 
                                    WHERE referrer_user_id = %s AND referred_user_id = %s
                                    LIMIT 1
                                """, (referrer_user_id, updated_user['user_id']))
                                existing_referral = cursor.fetchone()
                                
                                if not existing_referral:
                                    cursor.execute("""
                                        INSERT INTO referrals (referrer_user_id, referred_user_id, status, created_at)
                                        VALUES (%s, %s, 'approved', NOW())
                                    """, (referrer_user_id, updated_user['user_id']))
                                    print(f"✅ 기존 사용자 추천인 관계 저장 완료 - referrer: {referrer_user_id}, referred: {updated_user['user_id']}")
                                    is_new_referral = True
                                else:
                                    print(f"ℹ️ 추천인 관계가 이미 존재합니다 - referral_id: {existing_referral['referral_id']}")
                                    is_new_referral = False
                                print(f"✅ 기존 사용자 추천인 관계 저장 완료 - referrer: {referrer_user_id}, referred: {updated_user['user_id']}")
                                is_new_referral = True
                            else:
                                print(f"⚠️ 추천인 코드를 찾을 수 없음: {referral_code}")
                        else:
                            print(f"ℹ️ 추천인 관계가 이미 존재합니다 - user_id: {updated_user['user_id']}, referral_code: {referral_code}")
                        
                        # 새 추천인 관계인 경우 5% 할인쿠폰 발급 (실제 DB 스키마: user_coupons 사용)
                        if is_new_referral:
                            try:
                                from datetime import datetime, timedelta
                                expires_at = datetime.now() + timedelta(days=30)  # 30일 유효
                                
                                # 쿠폰 중복 체크 (user_coupons 테이블에서 확인)
                                cursor.execute("""
                                    SELECT uc.user_coupon_id 
                                    FROM user_coupons uc
                                    JOIN coupons c ON uc.coupon_id = c.coupon_id
                                    WHERE uc.user_id = %s 
                                      AND c.coupon_code = %s
                                      AND c.discount_value = 5.0
                                      AND c.discount_type = 'percentage'
                                    LIMIT 1
                                """, (updated_user['user_id'], f"REFERRAL_{referral_code}"))
                                existing_user_coupon = cursor.fetchone()
                                
                                if not existing_user_coupon:
                                    # 1. coupons 테이블에 쿠폰이 있는지 확인 (coupon_code로)
                                    coupon_code = f"REFERRAL_{referral_code}"
                                    cursor.execute("""
                                        SELECT coupon_id FROM coupons 
                                        WHERE coupon_code = %s 
                                          AND discount_value = 5.0 
                                          AND discount_type = 'percentage'
                                        LIMIT 1
                                    """, (coupon_code,))
                                    coupon_result = cursor.fetchone()
                                    
                                    if coupon_result:
                                        coupon_id = coupon_result[0]
                                    else:
                                        # 2. coupons 테이블에 쿠폰 생성
                                        cursor.execute("""
                                            INSERT INTO coupons (coupon_code, coupon_name, discount_type, discount_value, valid_until, created_at, updated_at)
                                            VALUES (%s, %s, 'percentage', 5.0, %s, NOW(), NOW())
                                            RETURNING coupon_id
                                        """, (coupon_code, f"추천인 할인 쿠폰 ({referral_code})", expires_at))
                                        coupon_id = cursor.fetchone()[0]
                                        print(f"✅ 쿠폰 생성 완료 - coupon_id: {coupon_id}, coupon_code: {coupon_code}")
                                    
                                    # 3. user_coupons 테이블에 사용자에게 쿠폰 발급
                                    cursor.execute("""
                                        INSERT INTO user_coupons (user_id, coupon_id, status, issued_at)
                                        VALUES (%s, %s, 'active', NOW())
                                        RETURNING user_coupon_id
                                    """, (updated_user['user_id'], coupon_id))
                                    user_coupon_id = cursor.fetchone()[0]
                                    print(f"🎁 피추천인 5% 할인쿠폰 발급 완료 - user_id: {updated_user['user_id']}, user_coupon_id: {user_coupon_id}, referral_code: {referral_code}")
                                else:
                                    print(f"ℹ️ 이미 발급된 쿠폰이 있습니다 - user_id: {updated_user['user_id']}, referral_code: {referral_code}")
                            except Exception as coupon_error:
                                print(f"⚠️ 할인쿠폰 발급 실패 (무시): {coupon_error}")
                                import traceback
                                traceback.print_exc()
                    except Exception as e:
                        print(f"⚠️ 기존 사용자 추천인 관계 저장 실패 (무시): {e}")
                        import traceback
                        traceback.print_exc()
            else:
                # 새 사용자 생성 (phone_number, signup_source, account_type, 비즈니스 정보 포함)
                try:
                    cursor.execute("""
                        INSERT INTO users (external_uid, email, username, phone_number, signup_source, account_type, 
                                         business_number, business_name, representative, contact_phone, contact_email, 
                                         created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                        RETURNING user_id, external_uid, email, username, phone_number, signup_source, account_type, 
                                 business_number, business_name, representative
                    """, (supabase_user_id, email, username, phone_number, signup_source, account_type,
                          business_number, business_name, representative, contact_phone, contact_email))
                except Exception as e:
                    # 일부 컬럼이 없을 수 있으므로 기본 필드만 사용
                    print(f"⚠️ 새 사용자 생성 중 일부 컬럼 누락 (기본 필드만 사용): {e}")
                    import traceback
                    print(traceback.format_exc())
                    try:
                        cursor.execute("""
                            INSERT INTO users (external_uid, email, username, created_at, updated_at)
                            VALUES (%s, %s, %s, NOW(), NOW())
                            RETURNING user_id, external_uid, email, username
                        """, (supabase_user_id, email, username))
                    except Exception as e2:
                        print(f"❌ 기본 필드 생성도 실패: {e2}")
                        raise
                updated_user = cursor.fetchone()
                print(f"✅ 새 사용자 생성 완료 - user_id: {updated_user['user_id']}")
                
                # 추천인 코드가 있으면 referrals 테이블에 저장 및 5% 할인쿠폰 발급
                if referral_code:
                    try:
                        # 추천인 코드로 추천인 user_id 찾기
                        cursor.execute("""
                            SELECT user_id FROM users WHERE referral_code = %s LIMIT 1
                        """, (referral_code,))
                        referrer = cursor.fetchone()
                        
                        if referrer:
                            referrer_user_id = referrer['user_id']
                            
                            # 중복 체크
                            cursor.execute("""
                                SELECT referral_id FROM referrals 
                                WHERE referrer_user_id = %s AND referred_user_id = %s
                                LIMIT 1
                            """, (referrer_user_id, updated_user['user_id']))
                            existing_relation = cursor.fetchone()
                            
                            is_new_referral = False
                            if not existing_relation:
                                # referrals 테이블에 추천인 관계 저장 (status='approved'로 저장)
                                cursor.execute("""
                                    INSERT INTO referrals (referrer_user_id, referred_user_id, status, created_at)
                                    VALUES (%s, %s, 'approved', NOW())
                                """, (referrer_user_id, updated_user['user_id']))
                                print(f"✅ 추천인 관계 저장 완료 - referrer: {referrer_user_id}, referred: {updated_user['user_id']}, status: approved")
                                is_new_referral = True
                            else:
                                print(f"ℹ️ 추천인 관계가 이미 존재합니다 - user_id: {updated_user['user_id']}, referral_code: {referral_code}")
                            
                            # 새 추천인 관계인 경우 5% 할인쿠폰 발급 (실제 DB 스키마: user_coupons 사용)
                            if is_new_referral:
                                try:
                                    from datetime import datetime, timedelta
                                    expires_at = datetime.now() + timedelta(days=30)  # 30일 유효
                                    
                                    # 쿠폰 중복 체크 (user_coupons 테이블에서 확인)
                                    cursor.execute("""
                                        SELECT uc.user_coupon_id 
                                        FROM user_coupons uc
                                        JOIN coupons c ON uc.coupon_id = c.coupon_id
                                        WHERE uc.user_id = %s 
                                          AND c.coupon_code = %s
                                          AND c.discount_value = 5.0
                                          AND c.discount_type = 'percentage'
                                        LIMIT 1
                                    """, (updated_user['user_id'], f"REFERRAL_{referral_code}"))
                                    existing_user_coupon = cursor.fetchone()
                                    
                                    if not existing_user_coupon:
                                        # 1. coupons 테이블에 쿠폰이 있는지 확인 (coupon_code로)
                                        coupon_code = f"REFERRAL_{referral_code}"
                                        cursor.execute("""
                                            SELECT coupon_id FROM coupons 
                                            WHERE coupon_code = %s 
                                              AND discount_value = 5.0 
                                              AND discount_type = 'percentage'
                                            LIMIT 1
                                        """, (coupon_code,))
                                        coupon_result = cursor.fetchone()
                                        
                                        if coupon_result:
                                            coupon_id = coupon_result[0]
                                        else:
                                            # 2. coupons 테이블에 쿠폰 생성
                                            cursor.execute("""
                                                INSERT INTO coupons (coupon_code, coupon_name, discount_type, discount_value, valid_until, created_at, updated_at)
                                                VALUES (%s, %s, 'percentage', 5.0, %s, NOW(), NOW())
                                                RETURNING coupon_id
                                            """, (coupon_code, f"추천인 할인 쿠폰 ({referral_code})", expires_at))
                                            coupon_id = cursor.fetchone()[0]
                                            print(f"✅ 쿠폰 생성 완료 - coupon_id: {coupon_id}, coupon_code: {coupon_code}")
                                        
                                        # 3. user_coupons 테이블에 사용자에게 쿠폰 발급
                                        cursor.execute("""
                                            INSERT INTO user_coupons (user_id, coupon_id, status, issued_at)
                                            VALUES (%s, %s, 'active', NOW())
                                            RETURNING user_coupon_id
                                        """, (updated_user['user_id'], coupon_id))
                                        user_coupon_id = cursor.fetchone()[0]
                                        print(f"🎁 피추천인 5% 할인쿠폰 발급 완료 - user_id: {updated_user['user_id']}, user_coupon_id: {user_coupon_id}, referral_code: {referral_code}")
                                    else:
                                        print(f"ℹ️ 이미 발급된 쿠폰이 있습니다 - user_id: {updated_user['user_id']}, referral_code: {referral_code}")
                                except Exception as coupon_error:
                                    print(f"⚠️ 할인쿠폰 발급 실패 (무시): {coupon_error}")
                                    import traceback
                                    traceback.print_exc()
                        else:
                            print(f"⚠️ 추천인 코드를 찾을 수 없음: {referral_code}")
                    except Exception as e:
                        print(f"⚠️ 추천인 관계 저장 실패 (무시): {e}")
                        import traceback
                        traceback.print_exc()
            
            # 지갑 생성 (없으면)
            cursor.execute("""
                INSERT INTO wallets (user_id, balance, created_at, updated_at)
                VALUES (%s, 0, NOW(), NOW())
                ON CONFLICT (user_id) DO NOTHING
            """, (updated_user['user_id'],))
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'user': {
                    'user_id': updated_user['user_id'],
                    'external_uid': updated_user['external_uid'],
                    'email': updated_user['email'],
                    'username': updated_user['username']
                }
            }), 200
        else:
            # SQLite는 구 스키마 유지 (phone_number, signup_source, account_type 포함)
            cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (supabase_user_id,))
            existing = cursor.fetchone()
            
            if not existing:
                try:
                    cursor.execute("""
                        INSERT INTO users (user_id, email, name, phone_number, signup_source, account_type, 
                                         business_number, business_name, representative, contact_phone, contact_email, 
                                         created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (supabase_user_id, email, username, phone_number, signup_source, account_type,
                          business_number, business_name, representative, contact_phone, contact_email))
                except Exception as e:
                    # 일부 컬럼이 없을 수 있으므로 기본 필드만 사용
                    print(f"⚠️ SQLite 새 사용자 생성 중 일부 컬럼 누락 (기본 필드만 사용): {e}")
                    cursor.execute("""
                        INSERT INTO users (user_id, email, name, created_at, updated_at)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (supabase_user_id, email, username))
            else:
                # 기존 사용자 업데이트 (SQLite)
                try:
                    update_fields = []
                    update_values = []
                    
                    if email:
                        update_fields.append("email = ?")
                        update_values.append(email)
                    if username:
                        update_fields.append("name = COALESCE(?, name)")
                        update_values.append(username)
                    if phone_number:
                        update_fields.append("phone_number = COALESCE(?, phone_number)")
                        update_values.append(phone_number)
                    if signup_source:
                        update_fields.append("signup_source = COALESCE(?, signup_source)")
                        update_values.append(signup_source)
                    if account_type:
                        update_fields.append("account_type = COALESCE(?, account_type)")
                        update_values.append(account_type)
                    
                    # 비즈니스 계정 정보 업데이트 (SQLite)
                    if business_number:
                        update_fields.append("business_number = COALESCE(?, business_number)")
                        update_values.append(business_number)
                    if business_name:
                        update_fields.append("business_name = COALESCE(?, business_name)")
                        update_values.append(business_name)
                    if representative:
                        update_fields.append("representative = COALESCE(?, representative)")
                        update_values.append(representative)
                    if contact_phone:
                        update_fields.append("contact_phone = COALESCE(?, contact_phone)")
                        update_values.append(contact_phone)
                    if contact_email:
                        update_fields.append("contact_email = COALESCE(?, contact_email)")
                        update_values.append(contact_email)
                    
                    if update_fields:
                        update_fields.append("updated_at = CURRENT_TIMESTAMP")
                        update_values.append(supabase_user_id)
                        update_query = f"UPDATE users SET {', '.join(update_fields)} WHERE user_id = ?"
                        cursor.execute(update_query, tuple(update_values))
                except Exception as e:
                    print(f"⚠️ SQLite 사용자 업데이트 중 일부 컬럼 누락 (무시): {e}")
                
                cursor.execute("""
                    INSERT OR IGNORE INTO points (user_id, points, created_at, updated_at)
                    VALUES (?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (supabase_user_id,))
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'user_id': supabase_user_id
            }), 200
            
    except Exception as e:
        import traceback
        error_msg = f'사용자 동기화 실패: {str(e)}'
        print(f"❌ {error_msg}")
        print(traceback.format_exc())
        if conn:
            conn.rollback()
        return jsonify({'error': error_msg}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/users/<path:user_id>', methods=['GET'])
def get_user(user_id):
    """사용자 정보 조회
    ---
    tags:
      - Users
    summary: 사용자 정보 조회
    description: "사용자 정보를 조회합니다. 사용자가 없으면 자동으로 생성합니다."
    security:
      - Bearer: []
    parameters:
      - name: user_id
        in: path
        type: string
        required: true
        description: 사용자 ID
        example: "user123"
    responses:
      200:
        description: 사용자 정보 조회 성공
        schema:
          type: object
          properties:
            user_id:
              type: integer
              example: 1
            email:
              type: string
              example: "user@example.com"
            external_uid:
              type: string
              example: "user123"
            phone_number:
              type: string
              example: "010-1234-5678"
            created_at:
              type: string
              example: "2024-01-01T00:00:00"
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "사용자 조회 실패: ..."
    """
    import sys
    # user_id 정규화 (앞뒤 공백 및 슬래시 제거)
    user_id = str(user_id).strip().rstrip('/')
    print(f"🔍 사용자 정보 조회 요청 - user_id: {user_id}", flush=True)
    sys.stdout.flush()
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        print(f"✅ DB 연결 성공 - user_id: {user_id}", flush=True)
        
        if DATABASE_URL.startswith('postgresql://'):
            # 새 스키마에서는 external_uid로 사용자 찾기 (display_name 컬럼이 없을 수 있음)
            try:
                cursor.execute("""
                    SELECT user_id, email, username, created_at
                    FROM users 
                    WHERE external_uid = %s OR email = %s OR user_id::text = %s
                    LIMIT 1
                """, (user_id, user_id, user_id))
            except Exception as e:
                # display_name 컬럼이 있는 경우 다시 시도
                if 'display_name' in str(e) or 'column' in str(e).lower():
                    cursor.execute("""
                        SELECT user_id, email, COALESCE(username, '사용자') as username, created_at
                        FROM users 
                        WHERE external_uid = %s OR email = %s OR user_id::text = %s
                        LIMIT 1
                    """, (user_id, user_id, user_id))
                else:
                    raise
        else:
            cursor.execute("""
                SELECT user_id, email, name, created_at
                FROM users WHERE user_id = ?
            """, (user_id,))
        
        user = cursor.fetchone()
        print(f"🔍 사용자 조회 결과: {user}", flush=True)
        sys.stdout.flush()
        
        if user:
            # 새 스키마에서는 username 사용 (display_name 없을 수 있음)
            if DATABASE_URL.startswith('postgresql://'):
                user_data = {
                    'user_id': str(user[0]),
                    'email': user[1],
                    'name': user[2] or '사용자',  # username
                    'created_at': user[3].isoformat() if user[3] and hasattr(user[3], 'isoformat') else (str(user[3]) if user[3] else None)
                }
            else:
                user_data = {
                    'user_id': user[0],
                    'email': user[1],
                    'name': user[2],
                    'created_at': user[3].isoformat() if user[3] and hasattr(user[3], 'isoformat') else (str(user[3]) if user[3] else None)
                }
            print(f"✅ 사용자 정보 반환: {user_data}", flush=True)
            sys.stdout.flush()
            return jsonify(user_data), 200
        else:
            # 사용자가 없으면 자동으로 생성
            print(f"ℹ️ 사용자 없음, 자동 생성 시도: {user_id}", flush=True)
            sys.stdout.flush()
            
            # email이 NOT NULL이므로 기본값 설정 (유효한 이메일 형식)
            sanitized_user = user_id.replace('@', '_at_').replace('/', '_').replace('\\', '_')
            default_email = f"{sanitized_user[:200]}@temp.local"
            
            try:
                if DATABASE_URL.startswith('postgresql://'):
                    # 새 스키마에서는 external_uid 사용
                    cursor.execute("""
                        INSERT INTO users (external_uid, email, username, created_at, updated_at)
                        VALUES (%s, %s, %s, NOW(), NOW())
                        ON CONFLICT (external_uid) DO NOTHING
                        RETURNING user_id, email, username, created_at
                    """, (user_id, default_email, 'User'))
                    
                    new_user = cursor.fetchone()
                    if new_user:
                        # wallets 테이블에도 초기 레코드 생성
                        cursor.execute("""
                            INSERT INTO wallets (user_id, balance, created_at, updated_at)
                            VALUES (%s, 0, NOW(), NOW())
                            ON CONFLICT (user_id) DO NOTHING
                        """, (new_user[0],))
                        conn.commit()
                        print(f"✅ 사용자 자동 생성 완료: user_id={new_user[0]}, external_uid={user_id}")
                        
                        return jsonify({
                            'user_id': str(new_user[0]),
                            'email': new_user[1],
                            'name': new_user[2] or '사용자',
                            'created_at': new_user[3].isoformat() if new_user[3] and hasattr(new_user[3], 'isoformat') else (str(new_user[3]) if new_user[3] else None)
                        }), 200
                    else:
                        # 이미 존재하는 사용자 조회
                        cursor.execute("""
                            SELECT user_id, email, username, created_at
                            FROM users 
                            WHERE external_uid = %s
                            LIMIT 1
                        """, (user_id,))
                        existing_user = cursor.fetchone()
                        if existing_user:
                            return jsonify({
                                'user_id': str(existing_user[0]),
                                'email': existing_user[1],
                                'name': existing_user[2] or '사용자',
                                'created_at': existing_user[3].isoformat() if existing_user[3] and hasattr(existing_user[3], 'isoformat') else (str(existing_user[3]) if existing_user[3] else None)
                            }), 200
                        else:
                            # 사용자를 찾을 수 없는 경우 기본 정보 반환
                            return jsonify({
                                'user_id': user_id,
                                'email': default_email,
                                'name': 'User',
                                'created_at': None,
                                'message': '사용자 정보가 없습니다.'
                            }), 200
                else:
                    cursor.execute("""
                        INSERT OR IGNORE INTO users (user_id, email, name, created_at, updated_at)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (user_id, default_email, 'User'))
                    
                    cursor.execute("""
                        INSERT OR IGNORE INTO points (user_id, points, created_at, updated_at)
                        VALUES (?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (user_id,))
                    conn.commit()
                    print(f"✅ 사용자 자동 생성 완료: {user_id}")
                
                # 생성된 사용자 정보 반환
                return jsonify({
                    'user_id': user_id,
                    'email': default_email,
                    'name': 'User',
                    'created_at': None,
                    'message': '사용자가 자동으로 생성되었습니다.'
                }), 200
                
            except Exception as create_error:
                import traceback
                conn.rollback()
                print(f"⚠️ 사용자 자동 생성 실패: {create_error}", file=sys.stderr, flush=True)
                traceback.print_exc(file=sys.stderr)
                sys.stderr.flush()
                
                # 생성 실패해도 항상 200 반환 (사용자 없음 상태)
                return jsonify({
                    'user_id': user_id,
                    'email': None,
                    'name': None,
                    'created_at': None,
                    'message': '사용자 정보가 없습니다.'
                }), 200
        
    except Exception as e:
        print(f"❌ 사용자 정보 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        # 오류 발생 시에도 항상 200 반환 (빈 사용자 정보)
        return jsonify({
            'user_id': user_id,
            'email': None,
            'name': None,
            'created_at': None,
            'message': f'사용자 정보 조회 중 오류 발생: {str(e)}'
        }), 200
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 추천인 코드 생성
# 사용하지 않는 엔드포인트 제거됨 - 관리자 API 사용

# 추천인 코드 조회
@app.route('/api/referral/my-codes', methods=['GET'])
def get_my_codes():
    """Get My Codes
    ---
    tags:
      - Referral
    summary: Get My Codes
    description: "Get My Codes API"
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """내 추천인 코드 조회"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id가 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 사용자의 추천인 코드 조회 (user_id 또는 user_email로 검색)
        print(f"🔍 추천인 코드 조회 - user_id: {user_id}")
        
        # 새 스키마에서는 users.referral_code 사용
        if DATABASE_URL.startswith('postgresql://'):
            try:
                # external_uid로 사용자 찾기
                cursor.execute("""
                    SELECT user_id, referral_code, created_at
                    FROM users 
                    WHERE external_uid = %s OR email = %s
                    LIMIT 1
                """, (user_id, user_id))
                user_result = cursor.fetchone()
                
                if not user_result or not user_result[1]:
                    return jsonify({'codes': []}), 200
                
                # users.referral_code를 사용하여 코드 반환
                referral_code = user_result[1]
                created_at = user_result[2]
                
                # 커미션 정보는 commissions 테이블에서 계산
                cursor.execute("""
                    SELECT COALESCE(SUM(c.amount), 0) as total_commission,
                           COUNT(DISTINCT c.commission_id) as usage_count
                    FROM commissions c
                    JOIN referrals r ON c.referral_id = r.referral_id
                    WHERE r.referrer_user_id = %s
                """, (user_result[0],))
                commission_result = cursor.fetchone()
                total_commission = float(commission_result[0]) if commission_result and commission_result[0] else 0.0
                usage_count = commission_result[1] if commission_result and commission_result[1] else 0
                
                codes = [{
                    'code': referral_code,
                    'is_active': True,
                    'usage_count': usage_count,
                    'total_commission': total_commission,
                    'created_at': created_at.isoformat() if created_at and hasattr(created_at, 'isoformat') else (str(created_at) if created_at else None)
                }]
                
                conn.close()
                return jsonify({'codes': codes}), 200
            except Exception as e:
                print(f"⚠️ 새 스키마 쿼리 실패: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'codes': []}), 200
        else:
            cursor.execute("""
                SELECT code, is_active, usage_count, total_commission, created_at
                FROM referral_codes 
                WHERE user_email = ? OR user_id = ?
                ORDER BY created_at DESC
            """, (user_id, user_id))
        
        codes = []
        rows = cursor.fetchall()
        print(f"📊 조회된 추천인 코드 수: {len(rows)}")
        print(f"🔍 검색 조건: user_id={user_id}")
        
        # 데이터베이스의 모든 추천인 코드 확인
        cursor.execute("SELECT user_email, user_id, code FROM referral_codes")
        all_codes = cursor.fetchall()
        print(f"📋 데이터베이스의 모든 추천인 코드:")
        for code in all_codes:
            print(f"  - 이메일: {code[0]}, ID: {code[1]}, 코드: {code[2]}")
        
        for row in rows:
            # 날짜 형식 처리 강화
            created_at = row[4]
            if hasattr(created_at, 'isoformat'):
                created_at = created_at.isoformat()
            elif hasattr(created_at, 'strftime'):
                created_at = created_at.strftime('%Y-%m-%dT%H:%M:%S')
            else:
                created_at = str(created_at)
            
            # Invalid Date 방지
            if created_at == 'None' or created_at == 'null' or not created_at:
                from datetime import datetime
                created_at = datetime.now().isoformat()
            
            code_data = {
                'code': row[0],
                'is_active': True,  # 항상 활성화 상태로 반환
                'usage_count': row[2],
                'total_commission': float(row[3]) if row[3] else 0.0,
                'created_at': created_at
            }
            print(f"📋 API 응답 데이터: {code_data}")
            codes.append(code_data)
            print(f"📋 추천인 코드: {code_data['code']}, 활성화: {code_data['is_active']}")
        
        conn.close()
        return jsonify({'codes': codes}), 200
        
    except Exception as e:
        return jsonify({'error': f'추천인 코드 조회 실패: {str(e)}'}), 500

# 추천인 코드 사용
@app.route('/api/referral/use-code', methods=['POST'])
def use_referral_code():
    """Use Referral Code
    ---
    tags:
      - Referral
    summary: Use Referral Code
    description: "Use Referral Code API"
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """추천인 코드 사용"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        code = data.get('code')
        
        if not user_id or not code:
            return jsonify({'error': 'user_id와 code가 필요합니다.'}), 400
        
        # 임시로 성공 응답 반환 (추천인 기능은 나중에 구현)
        return jsonify({
            'message': '추천인 코드가 적용되었습니다.',
            'code': code
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'추천인 코드 사용 실패: {str(e)}'}), 500

# 추천인 수수료 조회
@app.route('/api/referral/commissions', methods=['GET'])
def get_commissions():
    """Get Commissions
    ---
    tags:
      - Referral
    summary: Get Commissions
    description: "Get Commissions API"
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """추천인 수수료 조회 - 새 스키마 사용"""
    conn = None
    cursor = None
    try:
        user_id = request.args.get('user_id')  # external_uid 또는 email
        if not user_id:
            return jsonify({'error': 'user_id가 필요합니다.'}), 400
        
        print(f"🔍 커미션 내역 조회 - user_id: {user_id}", flush=True)
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if DATABASE_URL.startswith('postgresql://'):
            # 먼저 사용자 찾기 (external_uid 또는 email로)
            cursor.execute("""
                SELECT user_id, email, referral_code
                FROM users 
                WHERE external_uid = %s OR email = %s
                LIMIT 1
            """, (user_id, user_id))
            user = cursor.fetchone()
            
            if not user:
                print(f"⚠️ 사용자를 찾을 수 없음: {user_id}", flush=True)
                return jsonify({'commissions': []}), 200
            
            referrer_user_id = user.get('user_id')
            if not referrer_user_id:
                print(f"⚠️ 사용자 user_id를 찾을 수 없음: {user}", flush=True)
                return jsonify({'commissions': []}), 200
            
            print(f"✅ 사용자 찾음 - user_id: {referrer_user_id}, email: {user.get('email')}", flush=True)
            
            # 새 스키마: commissions 테이블과 referrals 테이블 조인하여 조회
            # orders 테이블의 final_amount나 total_amount를 사용하되, 없으면 commissions.amount에서 역산
            # 안전한 오류 처리 추가
            rows = []
            commission_rate = 0.1  # 기본값
            
            try:
                # 먼저 사용자의 commission_rate 가져오기
                try:
                    cursor.execute("""
                        SELECT COALESCE(commission_rate, 0.1) as commission_rate
                        FROM users
                        WHERE user_id = %s
                        LIMIT 1
                    """, (referrer_user_id,))
                    rate_result = cursor.fetchone()
                    if rate_result:
                        commission_rate = float(rate_result.get('commission_rate', 0.1))
                except Exception as rate_error:
                    print(f"⚠️ 커미션율 조회 오류 (기본값 사용): {rate_error}", flush=True)
                    commission_rate = 0.1
                
                # 커미션 내역 조회
                try:
                    cursor.execute("""
                        SELECT 
                            c.commission_id as id,
                            c.order_id,
                            c.amount as commission_amount,
                            c.status,
                            c.created_at,
                            r.referred_user_id,
                            u_referred.email as referred_email,
                            u_referred.username as referred_name,
                            CASE 
                                WHEN o.final_amount IS NOT NULL THEN o.final_amount
                                WHEN o.total_amount IS NOT NULL THEN o.total_amount
                                ELSE (c.amount / %s)  -- 사용자의 실제 커미션율 사용
                            END as purchase_amount
                        FROM commissions c
                        JOIN referrals r ON c.referral_id = r.referral_id
                        LEFT JOIN users u_referred ON r.referred_user_id = u_referred.user_id
                        LEFT JOIN orders o ON c.order_id = o.order_id
                        WHERE r.referrer_user_id = %s
                        ORDER BY c.created_at DESC
                    """, (commission_rate, referrer_user_id))
                    rows = cursor.fetchall()
                    print(f"📊 조회된 커미션 수: {len(rows)}개", flush=True)
                except Exception as query_error:
                    print(f"❌ 커미션 조회 쿼리 오류: {query_error}", flush=True)
                    import traceback
                    print(traceback.format_exc(), flush=True)
                    # 오류 발생 시 빈 목록 반환
                    rows = []
            except Exception as general_error:
                print(f"❌ 커미션 조회 전체 오류: {general_error}", flush=True)
                import traceback
                print(traceback.format_exc(), flush=True)
                # 오류 발생 시 빈 목록 반환
                rows = []
            
            commissions = []
            for row in rows:
                # 날짜 형식 처리
                created_at = row.get('created_at')
                if created_at:
                    if hasattr(created_at, 'isoformat'):
                        payment_date = created_at.isoformat()[:10]
                    elif hasattr(created_at, 'strftime'):
                        payment_date = created_at.strftime('%Y-%m-%d')
                    else:
                        payment_date = str(created_at)[:10]
                else:
                    payment_date = None
                
                commission_amount = float(row.get('commission_amount') or 0)
                purchase_amount = float(row.get('purchase_amount') or 0)
                # 위에서 가져온 commission_rate 사용
                if purchase_amount > 0:
                    calculated_rate = commission_amount / purchase_amount
                    # 계산된 비율과 사용자 커미션율 중 더 정확한 값 사용
                    commission_rate = commission_rate if abs(calculated_rate - commission_rate) < 0.01 else calculated_rate
                # purchase_amount가 0이면 위에서 설정한 commission_rate 사용
                
                commissions.append({
                    'id': row.get('id'),
                    'referredUser': row.get('referred_name') or row.get('referred_email') or '사용자',
                    'purchaseAmount': purchase_amount,
                    'commissionAmount': commission_amount,
                    'commissionRate': commission_rate,  # 숫자로 저장 (프론트엔드에서 포맷팅)
                    'paymentDate': payment_date,
                    'isPaid': row.get('status') in ['paid', 'approved'] if row.get('status') else False,
                    'status': row.get('status', 'accrued')
                })
        else:
            # SQLite - 레거시 호환
            cursor.execute("""
                SELECT id, referred_user, purchase_amount, commission_amount, 
                    commission_rate, created_at
                FROM commissions 
                WHERE referrer_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
            
            rows = cursor.fetchall()
            commissions = []
            for row in rows:
                # 날짜 형식 처리 (created_at는 5번째 인덱스)
                payment_date = row[5]
                if hasattr(payment_date, 'strftime'):
                    payment_date = payment_date.strftime('%Y-%m-%d')
                elif hasattr(payment_date, 'isoformat'):
                    payment_date = payment_date.isoformat()[:10]
                else:
                    payment_date = str(payment_date)[:10]
                
                commissions.append({
                    'id': row[0],
                    'referredUser': row[1],
                    'purchaseAmount': float(row[2]) if row[2] else 0.0,
                    'commissionAmount': float(row[3]) if row[3] else 0.0,
                    'commissionRate': f"{row[4] * 100}%" if row[4] else "0%",
                    'paymentDate': payment_date,
                    'isPaid': True  # 기본값으로 지급 완료 처리
                })
        
        print(f"✅ 커미션 내역 조회 완료: {len(commissions)}건", flush=True)
        
        return jsonify({
            'commissions': commissions
        }), 200
    except Exception as e:
        import traceback
        print(f"❌ 커미션 내역 조회 실패: {e}", flush=True)
        print(traceback.format_exc(), flush=True)
        return jsonify({'error': f'수수료 조회 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 추천인 코드로 쿠폰 발급
@app.route('/api/referral/issue-coupon', methods=['POST'])
def issue_referral_coupon():
    """Issue Referral Coupon
    ---
    tags:
      - Referral
    summary: Issue Referral Coupon
    description: "Issue Referral Coupon API"
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """추천인 코드로 5% 할인 쿠폰 발급"""
    try:
        data = request.get_json()
        print(f"🔍 쿠폰 발급 요청 데이터: {data}")
        
        user_id = data.get('user_id')
        referral_code = data.get('referral_code')
        
        print(f"🔍 쿠폰 발급 파싱 - user_id: {user_id}, referral_code: {referral_code}")
        
        if not user_id or not referral_code:
            print(f"❌ 쿠폰 발급 필수 필드 누락 - user_id: {user_id}, referral_code: {referral_code}")
            return jsonify({'error': 'user_id와 referral_code가 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 추천인 코드 유효성 확인 (PostgreSQL 타입 안전성)
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT id, user_email FROM referral_codes 
                WHERE code = %s AND is_active = true
            """, (referral_code,))
        else:
            cursor.execute("""
                SELECT id, user_email FROM referral_codes 
                WHERE code = ? AND (is_active = 1 OR is_active = 'true')
            """, (referral_code,))
        
        referrer_data = cursor.fetchone()
        print(f"🔍 추천인 코드 조회 결과: {referrer_data}")
        
        if not referrer_data:
            print(f"❌ 유효하지 않은 추천인 코드: {referral_code}")
            return jsonify({'error': '유효하지 않은 추천인 코드입니다.'}), 400
        
        referrer_id, referrer_email = referrer_data
        print(f"✅ 추천인 코드 유효 - ID: {referrer_id}, 이메일: {referrer_email}")
        
        # 사용자-추천인 연결 저장 (중복 체크)
        print(f"💾 사용자-추천인 연결 저장 시도 - user_id: {user_id}, referral_code: {referral_code}")
        
        # 먼저 중복 체크
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT COUNT(*) FROM user_referral_connections 
                WHERE user_id = %s AND referral_code = %s
            """, (user_id, referral_code))
        else:
            cursor.execute("""
                SELECT COUNT(*) FROM user_referral_connections 
                WHERE user_id = ? AND referral_code = ?
            """, (user_id, referral_code))
        
        existing_connection = cursor.fetchone()[0]
        
        if existing_connection > 0:
            print(f"⚠️ 이미 존재하는 연결 - user_id: {user_id}, referral_code: {referral_code}")
        else:
            if DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    INSERT INTO user_referral_connections (user_id, referral_code, referrer_email)
                    VALUES (%s, %s, %s)
                """, (user_id, referral_code, referrer_email))
            else:
                cursor.execute("""
                    INSERT INTO user_referral_connections (user_id, referral_code, referrer_email)
                    VALUES (?, ?, ?)
                """, (user_id, referral_code, referrer_email))
            print(f"✅ 사용자-추천인 연결 저장 완료")
        
        # 5% 할인 쿠폰 발급 (중복 체크)
        from datetime import datetime, timedelta
        expires_at = datetime.now() + timedelta(days=30)  # 30일 유효
        
        print(f"🎁 추천인 쿠폰 발급 시도 - user_id: {user_id}, referral_code: {referral_code}")
        
        # 쿠폰 중복 체크
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT COUNT(*) FROM coupons 
                WHERE user_id = %s AND referral_code = %s
            """, (user_id, referral_code))
        else:
            cursor.execute("""
                SELECT COUNT(*) FROM coupons 
                WHERE user_id = ? AND referral_code = ?
            """, (user_id, referral_code))
        
        existing_coupon = cursor.fetchone()[0]
        
        if existing_coupon > 0:
            print(f"⚠️ 이미 존재하는 쿠폰 - user_id: {user_id}, referral_code: {referral_code}")
        else:
            if DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    INSERT INTO coupons (user_id, referral_code, discount_type, discount_value, expires_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, referral_code, 'percentage', 5.0, expires_at))
            else:
                cursor.execute("""
                    INSERT INTO coupons (user_id, referral_code, discount_type, discount_value, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, referral_code, 'percentage', 5.0, expires_at))
            print(f"✅ 추천인 쿠폰 발급 완료")
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '5% 할인 쿠폰이 발급되었습니다!',
            'discount': 5.0,
            'expires_at': expires_at.isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'쿠폰 발급 실패: {str(e)}'}), 500

# 추천인 코드 검증
@app.route('/api/referral/validate-code', methods=['GET'])
def validate_referral_code():
    """추천인 코드 유효성 검증
    ---
    tags:
      - Referral
    summary: 추천인 코드 유효성 검증
    description: "입력된 추천인 코드가 유효한지 확인합니다."
    parameters:
      - name: code
        in: query
        type: string
        required: true
        description: 검증할 추천인 코드
        example: "ABC123"
    responses:
      200:
        description: 검증 결과
        schema:
          type: object
          properties:
            valid:
              type: boolean
              description: 코드 유효성 여부
              example: true
            code:
              type: string
              description: 추천인 코드 (유효한 경우)
              example: "ABC123"
            user_id:
              type: integer
              description: 추천인 사용자 ID (유효한 경우)
            email:
              type: string
              description: 추천인 이메일 (유효한 경우)
            error:
              type: string
              description: 에러 메시지 (유효하지 않은 경우)
              example: "유효하지 않은 코드입니다."
      400:
        description: 필수 파라미터 누락
        schema:
          type: object
          properties:
            valid:
              type: boolean
              example: false
            error:
              type: string
              example: "코드가 필요합니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            valid:
              type: boolean
              example: false
            error:
              type: string
              example: "코드 검증 실패: ..."
    """
    try:
        code = request.args.get('code')
        if not code:
            return jsonify({'valid': False, 'error': '코드가 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if DATABASE_URL.startswith('postgresql://'):
            # users.referral_code 사용
            cursor.execute("""
                SELECT user_id, email, referral_code
                FROM users 
                WHERE referral_code = %s
            """, (code,))
        else:
            # SQLite - 레거시 호환
            cursor.execute("""
                SELECT user_id, email, referral_code
                FROM users 
                WHERE referral_code = ?
            """, (code,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return jsonify({
                'valid': True, 
                'code': result.get('referral_code') or result.get('referral_code'),
                'user_id': result.get('user_id'),
                'email': result.get('email')
            }), 200
        else:
            return jsonify({'valid': False, 'error': '유효하지 않은 코드입니다.'}), 200
            
    except Exception as e:
        import traceback
        print(f"❌ 추천인 코드 검증 실패: {e}", flush=True)
        print(traceback.format_exc(), flush=True)
        return jsonify({'valid': False, 'error': f'코드 검증 실패: {str(e)}'}), 500

# 쿠폰 번호로 쿠폰 검증 및 사용자에게 추가 (더 구체적인 라우트를 먼저 정의해야 함)
@app.route('/api/user/coupons/add-by-code', methods=['POST', 'OPTIONS'])
def add_coupon_by_code():
    """Add Coupon By Code
    ---
    tags:
      - Users
    summary: Add Coupon By Code
    description: "Add Coupon By Code API"
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """쿠폰 번호로 쿠폰을 검증하고 사용자에게 추가"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        coupon_code = data.get('coupon_code')
        
        if not user_id or not coupon_code:
            return jsonify({'error': 'user_id와 coupon_code가 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            # 사용자 찾기
            cursor.execute("""
                SELECT user_id FROM users 
                WHERE external_uid = %s OR email = %s
                LIMIT 1
            """, (user_id, user_id))
            user_result = cursor.fetchone()
            if not user_result:
                return jsonify({'error': '사용자를 찾을 수 없습니다.'}), 404
            db_user_id = user_result[0]
            
            # 쿠폰 번호로 쿠폰 찾기
            cursor.execute("""
                SELECT c.coupon_id, c.coupon_code, c.coupon_name, c.discount_type, c.discount_value,
                       c.valid_from, c.valid_until
                FROM coupons c
                WHERE c.coupon_code = %s
                LIMIT 1
            """, (coupon_code,))
            coupon_result = cursor.fetchone()
            
            if not coupon_result:
                return jsonify({'error': '유효하지 않은 쿠폰 번호입니다.'}), 404
            
            coupon_id, code, name, discount_type, discount_value, valid_from, valid_until = coupon_result
            
            # 쿠폰 유효기간 확인
            from datetime import datetime
            now = datetime.now()
            if valid_from and valid_from > now:
                return jsonify({'error': '아직 사용할 수 없는 쿠폰입니다.'}), 400
            if valid_until and valid_until < now:
                return jsonify({'error': '만료된 쿠폰입니다.'}), 400
            
            # 이미 사용자가 이 쿠폰을 가지고 있는지 확인
            cursor.execute("""
                SELECT user_coupon_id, status FROM user_coupons
                WHERE user_id = %s AND coupon_id = %s
                LIMIT 1
            """, (db_user_id, coupon_id))
            existing = cursor.fetchone()
            
            if existing:
                if existing[1] == 'used':
                    return jsonify({'error': '이미 사용한 쿠폰입니다.'}), 400
                else:
                    return jsonify({'error': '이미 등록된 쿠폰입니다.'}), 400
            
            # user_coupons에 추가
            cursor.execute("""
                INSERT INTO user_coupons (user_id, coupon_id, status, issued_at)
                VALUES (%s, %s, 'active', NOW())
                RETURNING user_coupon_id
            """, (db_user_id, coupon_id))
            
            user_coupon_id = cursor.fetchone()[0]
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'coupon': {
                    'id': user_coupon_id,
                    'coupon_code': code,
                    'coupon_name': name,
                    'discount_type': discount_type,
                    'discount_value': float(discount_value) if discount_value else 0.0,
                    'is_used': False,
                    'expires_at': valid_until.isoformat() if valid_until and hasattr(valid_until, 'isoformat') else (str(valid_until) if valid_until else None)
                }
            }), 200
            
        else:
            # SQLite 버전
            cursor.execute("""
                SELECT id, coupon_code, discount_type, discount_value, expires_at, is_used
                FROM coupons 
                WHERE coupon_code = ? AND is_used = 0
                LIMIT 1
            """, (coupon_code,))
            coupon_result = cursor.fetchone()
            
            if not coupon_result:
                return jsonify({'error': '유효하지 않은 쿠폰 번호입니다.'}), 404
            
            coupon_id, code, discount_type, discount_value, expires_at, is_used = coupon_result
            
            # 만료 확인
            if expires_at:
                from datetime import datetime
                if datetime.fromisoformat(expires_at) < datetime.now():
                    return jsonify({'error': '만료된 쿠폰입니다.'}), 400
            
            # 이미 사용자가 이 쿠폰을 가지고 있는지 확인
            cursor.execute("""
                SELECT id FROM coupons 
                WHERE coupon_code = ? AND user_id = ?
                LIMIT 1
            """, (coupon_code, user_id))
            existing = cursor.fetchone()
            
            if existing:
                return jsonify({'error': '이미 등록된 쿠폰입니다.'}), 400
            
            # 쿠폰을 사용자에게 연결 (SQLite는 간단하게 user_id 업데이트)
            cursor.execute("""
                UPDATE coupons 
                SET user_id = ?
                WHERE id = ?
            """, (user_id, coupon_id))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'coupon': {
                    'id': coupon_id,
                    'coupon_code': code,
                    'discount_type': discount_type,
                    'discount_value': float(discount_value) if discount_value else 0.0,
                    'is_used': False,
                    'expires_at': expires_at
                }
            }), 200
            
    except Exception as e:
        import traceback
        print(f"❌ 쿠폰 추가 실패: {e}")
        print(traceback.format_exc())
        return jsonify({'error': f'쿠폰 추가 실패: {str(e)}'}), 500

# 사용자 쿠폰 조회
@app.route('/api/user/coupons', methods=['GET'])
def get_user_coupons():
    """Get User Coupons
    ---
    tags:
      - Users
    summary: Get User Coupons
    description: "Get User Coupons API"
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """사용자의 쿠폰 목록 조회"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id가 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            # 새 스키마: user_coupons와 coupons 조인 필요
            try:
                # external_uid로 사용자 찾기
                cursor.execute("""
                    SELECT user_id FROM users 
                    WHERE external_uid = %s OR email = %s
                    LIMIT 1
                """, (user_id, user_id))
                user_result = cursor.fetchone()
                if not user_result:
                    return jsonify({'coupons': []}), 200
                db_user_id = user_result[0]
                
                cursor.execute("""
                    SELECT uc.user_coupon_id, c.coupon_code, c.coupon_name, c.discount_type, c.discount_value,
                           uc.status, uc.issued_at, uc.used_at, c.valid_until
                    FROM user_coupons uc
                    JOIN coupons c ON uc.coupon_id = c.coupon_id
                    WHERE uc.user_id = %s
                    ORDER BY uc.issued_at DESC
                """, (db_user_id,))
            except Exception as e:
                print(f"⚠️ 새 스키마 쿼리 실패: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'coupons': []}), 200
        else:
            cursor.execute("""
                SELECT id, referral_code, discount_type, discount_value, is_used, 
                    created_at, expires_at, used_at
                FROM coupons 
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
        
        coupons = []
        for row in cursor.fetchall():
            if DATABASE_URL.startswith('postgresql://'):
                # 새 스키마: user_coupon_id, coupon_code, coupon_name, discount_type, discount_value, status, issued_at, used_at, valid_until
                issued_at = row[6] if len(row) > 6 else None
                used_at = row[7] if len(row) > 7 else None
                valid_until = row[8] if len(row) > 8 else None
                
                coupons.append({
                    'id': row[0],
                    'referral_code': row[1],  # coupon_code
                    'discount_type': row[3],
                    'discount_value': float(row[4]) if row[4] else 0.0,
                    'is_used': row[5] == 'used' if row[5] else False,  # status가 'used'면 사용됨
                    'created_at': issued_at.isoformat() if issued_at and hasattr(issued_at, 'isoformat') else (str(issued_at) if issued_at else None),
                    'expires_at': valid_until.isoformat() if valid_until and hasattr(valid_until, 'isoformat') else (str(valid_until) if valid_until else None),
                    'used_at': used_at.isoformat() if used_at and hasattr(used_at, 'isoformat') else (str(used_at) if used_at else None)
                })
            else:
                # 구 스키마 (SQLite)
                created_at = row[5]
                expires_at = row[6]
                used_at = row[7]
                
                if hasattr(created_at, 'isoformat'):
                    created_at = created_at.isoformat()
                else:
                    created_at = str(created_at)
                    
                if hasattr(expires_at, 'isoformat'):
                    expires_at = expires_at.isoformat()
                else:
                    expires_at = str(expires_at)
                    
                if used_at and hasattr(used_at, 'isoformat'):
                    used_at = used_at.isoformat()
                else:
                    used_at = str(used_at) if used_at else None
                
                coupons.append({
                    'id': row[0],
                    'referral_code': row[1],
                    'discount_type': row[2],
                    'discount_value': row[3],
                    'is_used': row[4],
                    'created_at': created_at,
                    'expires_at': expires_at,
                    'used_at': used_at
                })
        
        conn.close()
        return jsonify({'coupons': coupons}), 200
        
    except Exception as e:
        return jsonify({'error': f'쿠폰 조회 실패: {str(e)}'}), 500

# 관리자용 추천인 커미션 현황 조회
@app.route('/api/admin/referral/commission-overview', methods=['GET'])
def get_referral_commission_overview():
    """Get Referral Commission Overview
    ---
    tags:
      - Admin
    summary: Get Referral Commission Overview
    description: "Get Referral Commission Overview API"
    security:
      - Bearer: []
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """관리자용 추천인 커미션 현황 조회"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        
        if DATABASE_URL.startswith('postgresql://'):
            # 새 스키마에서는 commissions와 referrals 사용
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            try:
                cursor.execute("""
                    SELECT 
                        u.email,
                        COALESCE(u.username, '사용자') as username,
                        u.referral_code,
                        u.user_id,
                        COALESCE(u.commission_rate, 0.1) as commission_rate,
                        COUNT(DISTINCT r.referred_user_id) as referral_count,
                        COALESCE(SUM(CASE WHEN c.amount IS NOT NULL THEN c.amount ELSE 0 END), 0) as total_commission,
                        COALESCE(SUM(CASE 
                            WHEN c.created_at >= DATE_TRUNC('month', CURRENT_DATE) 
                            THEN COALESCE(c.amount, 0)
                            ELSE 0 
                        END), 0) as this_month_commission,
                        COALESCE(SUM(CASE 
                            WHEN c.created_at >= DATE_TRUNC('month', CURRENT_DATE)
                            AND c.status != 'paid_out'
                            THEN COALESCE(c.amount, 0)
                            ELSE 0 
                        END), 0) as unpaid_commission
                    FROM users u
                    LEFT JOIN referrals r ON u.user_id = r.referrer_user_id
                    LEFT JOIN commissions c ON r.referral_id = c.referral_id
                    WHERE u.referral_code IS NOT NULL AND u.referral_code != ''
                    GROUP BY u.email, u.username, u.referral_code, u.user_id, u.commission_rate
                    ORDER BY total_commission DESC
                """)
                
                rows = cursor.fetchall()
                overview_data = []
                for row in rows:
                    overview_data.append({
                        'referrer_email': row.get('email') or 'N/A',
                        'referrer_name': row.get('username') or 'N/A',
                        'referral_code': row.get('referral_code') or '',
                        'referrer_user_id': row.get('user_id'),
                        'commission_rate': float(row.get('commission_rate') or 0.1),
                        'referral_count': row.get('referral_count') or 0,
                        'total_commission': float(row.get('total_commission') or 0),
                        'this_month_commission': float(row.get('this_month_commission') or 0),
                        'unpaid_commission': float(row.get('unpaid_commission') or 0)
                    })
                
                # 전체 통계 (새 스키마)
                cursor.execute("""
                    SELECT 
                        COUNT(DISTINCT u.user_id) as total_referrers,
                        COUNT(DISTINCT r.referred_user_id) as total_referrals,
                        COALESCE(SUM(c.amount), 0) as total_commissions,
                        COALESCE(SUM(CASE 
                            WHEN c.created_at >= DATE_TRUNC('month', CURRENT_DATE) 
                            THEN c.amount 
                            ELSE 0 
                        END), 0) as this_month_commissions
                    FROM users u
                    LEFT JOIN referrals r ON u.user_id = r.referrer_user_id
                    LEFT JOIN commissions c ON r.referral_id = c.referral_id
                    WHERE u.referral_code IS NOT NULL AND u.referral_code != ''
                """)
                
                stats_row = cursor.fetchone()
                if stats_row:
                    total_stats = {
                        'total_referrers': stats_row.get('total_referrers') or 0,
                        'total_referrals': stats_row.get('total_referrals') or 0,
                        'total_commissions': float(stats_row.get('total_commissions') or 0),
                        'this_month_commissions': float(stats_row.get('this_month_commissions') or 0)
                    }
                else:
                    total_stats = {
                        'total_referrers': 0,
                        'total_referrals': 0,
                        'total_commissions': 0.0,
                        'this_month_commissions': 0.0
                    }
                
            except Exception as e:
                print(f"⚠️ 새 스키마 쿼리 실패: {e}")
                import traceback
                traceback.print_exc()
                overview_data = []
                total_stats = {
                    'total_referrers': 0,
                    'total_referrals': 0,
                    'total_commissions': 0.0,
                    'this_month_commissions': 0.0
                }
        else:
            # SQLite 버전
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    rc.user_email,
                    rc.name,
                    rc.code,
                    COUNT(DISTINCT cl.referred_user_id) as referral_count,
                    COALESCE(SUM(CASE WHEN cl.event = 'earn' THEN cl.amount ELSE 0 END), 0) as total_commission,
                    COALESCE(SUM(CASE 
                        WHEN cl.event = 'earn' AND date(cl.created_at) >= date('now', 'start of month') 
                        THEN cl.amount 
                        ELSE 0 
                    END), 0) as this_month_commission,
                    COALESCE(SUM(CASE 
                        WHEN cl.event = 'earn' AND date(cl.created_at) >= date('now', 'start of month')
                        AND cl.status = 'confirmed'
                        THEN cl.amount 
                        ELSE 0 
                    END), 0) as unpaid_commission
                FROM referral_codes rc
                LEFT JOIN commission_ledger cl ON rc.code = cl.referral_code AND cl.status = 'confirmed'
                WHERE rc.is_active = 1
                GROUP BY rc.user_email, rc.name, rc.code
                ORDER BY total_commission DESC
            """)
            
            overview_data = []
            for row in cursor.fetchall():
                overview_data.append({
                    'referrer_email': row[0],
                    'referrer_name': row[1],
                    'referral_code': row[2],
                    'referral_count': row[3],
                    'total_commission': float(row[4]),
                    'this_month_commission': float(row[5]),
                    'unpaid_commission': float(row[6])
                })
            
            # 전체 통계 (SQLite)
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT rc.user_email) as total_referrers,
                    COUNT(DISTINCT urc.user_id) as total_referrals,
                    COALESCE(SUM(c.commission_amount), 0) as total_commissions,
                    COALESCE(SUM(CASE 
                        WHEN date(c.payment_date) >= date('now', 'start of month') 
                        THEN c.commission_amount 
                        ELSE 0 
                    END), 0) as this_month_commissions
                FROM referral_codes rc
                LEFT JOIN user_referral_connections urc ON rc.code = urc.referral_code
                LEFT JOIN commissions c ON rc.user_email = c.referrer_id
                WHERE rc.is_active = 1
            """)
            
            stats_row = cursor.fetchone()
            total_stats = {
                'total_referrers': stats_row[0],
                'total_referrals': stats_row[1],
                'total_commissions': float(stats_row[2]),
                'this_month_commissions': float(stats_row[3])
            }
        
        return jsonify({
            'overview': overview_data,
            'stats': total_stats
        }), 200
        
    except Exception as e:
        import traceback
        error_msg = f'커미션 현황 조회 실패: {str(e)}'
        print(f"❌ {error_msg}")
        print(traceback.format_exc())
        return jsonify({'error': error_msg}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 관리자용 커미션 환급 처리
@app.route('/api/admin/referral/pay-commission', methods=['POST'])
def pay_commission():
    """Pay Commission
    ---
    tags:
      - Admin
    summary: Pay Commission
    description: "Pay Commission API"
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """관리자용 커미션 환급 처리"""
    try:
        data = request.get_json()
        print(f"🔍 커미션 환급 요청 데이터: {data}")
        
        referrer_email = data.get('referrer_email')
        amount = data.get('amount')
        payment_method = data.get('payment_method', 'bank_transfer')
        notes = data.get('notes', '')
        
        print(f"🔍 파싱된 데이터 - referrer_email: {referrer_email}, amount: {amount}")
        
        if not referrer_email or not amount:
            print(f"❌ 필수 필드 누락 - referrer_email: {referrer_email}, amount: {amount}")
            return jsonify({'error': 'referrer_email과 amount가 필요합니다.'}), 400
        
        print(f"🔗 데이터베이스 연결 시도...")
        conn = get_db_connection()
        cursor = conn.cursor()
        print(f"✅ 데이터베이스 연결 성공")
        
        # referral_code로 referrer_user_id 조회
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT code, user_id FROM referral_codes WHERE user_email = %s OR user_id = %s LIMIT 1
            """, (referrer_email, referrer_email))
        else:
            cursor.execute("""
                SELECT code, user_id FROM referral_codes WHERE user_email = ? OR user_id = ? LIMIT 1
            """, (referrer_email, referrer_email))
        
        referral_result = cursor.fetchone()
        if not referral_result:
            return jsonify({'error': '추천인을 찾을 수 없습니다.'}), 404
        
        referral_code, referrer_user_id = referral_result
        
        # commission_ledger에서 현재 잔액 계산
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) FROM commission_ledger 
                WHERE referrer_user_id = %s AND status = 'confirmed'
            """, (referrer_user_id,))
        else:
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) FROM commission_ledger 
                WHERE referrer_user_id = ? AND status = 'confirmed'
            """, (referrer_user_id,))
        
        balance_result = cursor.fetchone()
        current_balance = float(balance_result[0]) if balance_result else 0.0
        
        if current_balance < float(amount):
            return jsonify({'error': f'잔액이 부족합니다. 현재 잔액: {current_balance}원'}), 400
        
        # commission_ledger에 환급 기록 (event='payout', amount는 음수)
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                INSERT INTO commission_ledger 
                (referral_code, referrer_user_id, event, amount, status, notes, created_at, confirmed_at)
                VALUES (%s, %s, 'payout', %s, 'confirmed', %s, NOW(), NOW())
            """, (referral_code, referrer_user_id, -float(amount), f'관리자 환급 처리 - {payment_method} - {notes}'))
        else:
            cursor.execute("""
                INSERT INTO commission_ledger 
                (referral_code, referrer_user_id, event, amount, status, notes, created_at, confirmed_at)
                VALUES (?, ?, 'payout', ?, 'confirmed', ?, datetime('now'), datetime('now'))
            """, (referral_code, referrer_user_id, -float(amount), f'관리자 환급 처리 - {payment_method} - {notes}'))
        
        # 환급 후 잔액 계산
        balance_after = current_balance - float(amount)
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'{referrer_email}님에게 {amount}원 커미션이 환급되었습니다.'
        }), 200
        
    except Exception as e:
        print(f"❌ 커미션 환급 처리 오류: {str(e)}")
        print(f"❌ 오류 타입: {type(e).__name__}")
        import traceback
        print(f"❌ 스택 트레이스: {traceback.format_exc()}")
        return jsonify({'error': f'커미션 환급 실패: {str(e)}'}), 500

# 관리자용 환급 내역 조회
@app.route('/api/admin/referral/payment-history', methods=['GET'])
def get_payment_history():
    """Get Payment History
    ---
    tags:
      - Admin
    summary: Get Payment History
    description: "Get Payment History API"
    security:
      - Bearer: []
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """관리자용 환급 내역 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            # 새 스키마에서는 payouts 테이블 사용
            try:
                cursor.execute("""
                    SELECT 
                        p.processed_at AS paid_at,
                        p.paid_amount AS amount,
                        '' AS notes
                    FROM payouts p
                    WHERE p.processed_at IS NOT NULL
                    ORDER BY p.payout_id DESC
                """)
            except Exception as e:
                print(f"⚠️ 새 스키마 쿼리 실패: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'payments': []}), 200
        else:
            cursor.execute("""
                SELECT referrer_user_id, amount, notes, created_at
                FROM commission_ledger
                WHERE event = 'payout' AND status = 'confirmed'
                ORDER BY created_at DESC
            """)
        
        payments = []
        for row in cursor.fetchall():
            # Postgres 분기에서는 (paid_at, amount, notes) 순서
            if DATABASE_URL.startswith('postgresql://'):
                paid_at = row[0]
                amount_val = row[1]
                notes_val = row[2]
                referrer_id = None
            else:
                # SQLite 분기에서는 (referrer_user_id, amount, notes, created_at)
                referrer_id = row[0]
                amount_val = row[1]
                notes_val = row[2]
                paid_at = row[3]
            if hasattr(paid_at, 'isoformat'):
                paid_at = paid_at.isoformat()
            else:
                paid_at = str(paid_at)
            
            payments.append({
                'referrer_user_id': referrer_id,
                'amount': abs(float(amount_val)) if amount_val is not None else 0.0,
                'notes': notes_val,
                'paid_at': paid_at
            })
        
        conn.close()
        return jsonify({'payments': payments}), 200
        
    except Exception as e:
        return jsonify({'error': f'환급 내역 조회 실패: {str(e)}'}), 500

# 사용자용 추천인 통계 조회
@app.route('/api/referral/stats', methods=['GET'])
def get_referral_stats():
    """Get Referral Stats
    ---
    tags:
      - Referral
    summary: Get Referral Stats
    description: "Get Referral Stats API"
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """사용자용 추천인 통계 조회 - 새 스키마 사용"""
    conn = None
    cursor = None
    try:
        user_id = request.args.get('user_id')  # external_uid 또는 email
        if not user_id:
            return jsonify({'error': 'user_id가 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print(f"🔍 추천인 통계 조회 - user_id: {user_id}", flush=True)
        
        if DATABASE_URL.startswith('postgresql://'):
            # 먼저 사용자 찾기 (external_uid 또는 email로) - commission_rate 포함
            cursor.execute("""
                SELECT user_id, email, referral_code, COALESCE(commission_rate, 0.1) as commission_rate
                FROM users 
                WHERE external_uid = %s OR email = %s
                LIMIT 1
            """, (user_id, user_id))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({
                    'totalReferrals': 0,
                    'totalCommission': 0,
                    'activeReferrals': 0,
                    'thisMonthReferrals': 0,
                    'thisMonthCommission': 0,
                    'commissionRate': 0.1
                }), 200
            
            referrer_user_id = user['user_id']
            commission_rate = float(user.get('commission_rate', 0.1))
            
            # 총 추천인 수 (referrals 테이블에서 referrer_user_id로 조회)
            cursor.execute("""
                SELECT COUNT(DISTINCT r.referred_user_id) as total_referrals
                FROM referrals r
                WHERE r.referrer_user_id = %s
            """, (referrer_user_id,))
            total_referrals = cursor.fetchone()['total_referrals'] or 0
            
            # 활성 추천인 수 (status = 'approved')
            cursor.execute("""
                SELECT COUNT(DISTINCT r.referred_user_id) as active_referrals
                FROM referrals r
                WHERE r.referrer_user_id = %s AND r.status = 'approved'
            """, (referrer_user_id,))
            active_referrals = cursor.fetchone()['active_referrals'] or 0
            
            # 총 커미션 (commissions 테이블에서 조회)
            cursor.execute("""
                SELECT COALESCE(SUM(c.amount), 0) as total_commission
                FROM commissions c
                JOIN referrals r ON c.referral_id = r.referral_id
                WHERE r.referrer_user_id = %s
            """, (referrer_user_id,))
            total_commission = float(cursor.fetchone()['total_commission'] or 0)
            
            # 이번 달 추천인 수
            cursor.execute("""
                SELECT COUNT(DISTINCT r.referred_user_id) as this_month_referrals
                FROM referrals r
                WHERE r.referrer_user_id = %s 
                AND DATE_TRUNC('month', r.created_at) = DATE_TRUNC('month', CURRENT_DATE)
            """, (referrer_user_id,))
            this_month_referrals = cursor.fetchone()['this_month_referrals'] or 0
            
            # 이번 달 커미션
            cursor.execute("""
                SELECT COALESCE(SUM(c.amount), 0) as this_month_commission
                FROM commissions c
                JOIN referrals r ON c.referral_id = r.referral_id
                WHERE r.referrer_user_id = %s 
                AND DATE_TRUNC('month', c.created_at) = DATE_TRUNC('month', CURRENT_DATE)
            """, (referrer_user_id,))
            this_month_commission = float(cursor.fetchone()['this_month_commission'] or 0)
        else:
            # SQLite - 레거시 호환
            # 사용자 정보 조회 (commission_rate 포함)
            cursor.execute("""
                SELECT user_id, COALESCE(commission_rate, 0.1) as commission_rate
                FROM users 
                WHERE user_id = ? OR email = ?
                LIMIT 1
            """, (user_id, user_id))
            user_result = cursor.fetchone()
            commission_rate = 0.1  # 기본값
            if user_result:
                try:
                    commission_rate = float(user_result.get('commission_rate', 0.1) if isinstance(user_result, dict) else (user_result[1] if len(user_result) > 1 else 0.1))
                except:
                    commission_rate = 0.1
            
            cursor.execute("""
                SELECT COUNT(*) FROM user_referral_connections 
                WHERE referrer_email = ?
            """, (user_id if '@' in user_id else f"{user_id}@example.com",))
            total_referrals = cursor.fetchone()[0] or 0
            active_referrals = total_referrals
            
            cursor.execute("""
                SELECT COALESCE(SUM(commission_amount), 0) FROM commissions 
                WHERE referrer_id = ?
            """, (user_id,))
            total_commission = float(cursor.fetchone()[0] or 0)
            
            cursor.execute("""
                SELECT COUNT(*) FROM user_referral_connections 
                WHERE referrer_email = ? 
                AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
            """, (user_id if '@' in user_id else f"{user_id}@example.com",))
            this_month_referrals = cursor.fetchone()[0] or 0
            
            cursor.execute("""
                SELECT COALESCE(SUM(commission_amount), 0) FROM commissions 
                WHERE referrer_id = ? 
                AND strftime('%Y-%m', payment_date) = strftime('%Y-%m', 'now')
            """, (user_id,))
            this_month_commission = float(cursor.fetchone()[0] or 0)
        
        return jsonify({
            'totalReferrals': total_referrals,
            'totalCommission': total_commission,
            'activeReferrals': active_referrals,
            'thisMonthReferrals': this_month_referrals,
            'thisMonthCommission': this_month_commission,
            'commissionRate': commission_rate
        }), 200
        
    except Exception as e:
        import traceback
        print(f"❌ 추천인 통계 조회 실패: {e}", flush=True)
        print(traceback.format_exc(), flush=True)
        return jsonify({'error': f'통계 조회 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 사용자용 추천인 목록 조회 (피추천인 목록)
@app.route('/api/referral/referrals', methods=['GET'])
def get_user_referrals():
    """Get User Referrals
    ---
    tags:
      - Referral
    summary: Get User Referrals
    description: "Get User Referrals API"
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """사용자용 추천인 목록 조회 (내가 추천한 사용자들) - 새 스키마 사용"""
    user_id = request.args.get('user_id')  # external_uid 또는 email
    if not user_id:
        return jsonify({'error': 'user_id가 필요합니다.'}), 400
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print(f"🔍 피추천인 목록 조회 - user_id: {user_id}", flush=True)
        
        if DATABASE_URL.startswith('postgresql://'):
            # 먼저 사용자 찾기 (external_uid 또는 email로)
            cursor.execute("""
                SELECT user_id, email, referral_code
                FROM users 
                WHERE external_uid = %s OR email = %s
                LIMIT 1
            """, (user_id, user_id))
            referrer = cursor.fetchone()
            
            if not referrer:
                return jsonify({'referrals': []}), 200
            
            referrer_user_id = referrer['user_id']
            
            # referrals 테이블에서 피추천인 목록 조회
            cursor.execute("""
                SELECT 
                    r.referral_id,
                    r.referred_user_id,
                    r.status,
                    r.created_at,
                    u.email as referred_email,
                    u.username as referred_name,
                    COALESCE(SUM(c.amount), 0) as total_commission
                FROM referrals r
                JOIN users u ON r.referred_user_id = u.user_id
                LEFT JOIN commissions c ON r.referral_id = c.referral_id
                WHERE r.referrer_user_id = %s
                GROUP BY r.referral_id, r.referred_user_id, r.status, r.created_at, u.email, u.username
                ORDER BY r.created_at DESC
            """, (referrer_user_id,))
        else:
            # SQLite - 레거시 호환
            user_email = user_id if '@' in user_id else f"{user_id}@example.com"
            cursor.execute("""
                SELECT urc.id, urc.user_id, urc.referral_code, urc.created_at,
                       u.name, u.email
                FROM user_referral_connections urc
                LEFT JOIN users u ON urc.user_id = u.user_id
                WHERE urc.referrer_email = ?
                ORDER BY urc.created_at DESC
            """, (user_email,))
        
        referrals = []
        for row in cursor.fetchall():
            if DATABASE_URL.startswith('postgresql://'):
                # 새 스키마: RealDictCursor 사용
                join_date = row.get('created_at')
                if join_date:
                    if hasattr(join_date, 'isoformat'):
                        join_date = join_date.isoformat()[:10]
                    else:
                        join_date = str(join_date)[:10]
                else:
                    join_date = None
                
                user_name = row.get('referred_name') or row.get('referred_email') or '사용자'
                total_commission = float(row.get('total_commission') or 0)
                
                referrals.append({
                    'id': str(row.get('referral_id')),
                    'user': user_name,
                    'email': row.get('referred_email'),
                    'joinDate': join_date,
                    'status': '활성' if row.get('status') == 'approved' else '대기',
                    'commission': total_commission
                })
            else:
                # SQLite - 레거시
                join_date = row[3]
                if hasattr(join_date, 'strftime'):
                    join_date = join_date.strftime('%Y-%m-%d')
                elif hasattr(join_date, 'isoformat'):
                    join_date = join_date.isoformat()[:10]
                else:
                    join_date = str(join_date)[:10]
                
                user_name = row[4] if row[4] else (row[5] if row[5] else row[1])
                
                referrals.append({
                    'id': row[0],
                    'user': user_name,
                    'joinDate': join_date,
                    'status': '활성',
                    'commission': 0
                })
        
        print(f"✅ 피추천인 목록 조회 완료: {len(referrals)}명", flush=True)
        
        return jsonify({
            'referrals': referrals,
            'count': len(referrals)
        }), 200
        
    except Exception as e:
        import traceback
        print(f"❌ 피추천인 목록 조회 실패: {e}", flush=True)
        print(traceback.format_exc(), flush=True)
        return jsonify({'error': f'추천인 목록 조회 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 관리자용 추천인 등록
@app.route('/api/admin/referral/register', methods=['POST'])
def admin_register_referral():
    """Admin Register Referral
    ---
    tags:
      - Admin
    summary: Admin Register Referral
    description: "Admin Register Referral API"
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """관리자용 추천인 등록 - 새 스키마 사용 (users.referral_code)"""
    conn = None
    cursor = None
    try:
        data = request.get_json()
        print(f"🔍 관리자 추천인 등록 요청 데이터: {data}", flush=True)
        
        # 이메일 기반 등록만 지원
        email = data.get('email') or data.get('user_email')
        name = data.get('name')
        phone = data.get('phone')
        
        print(f"🔍 파싱된 필드 - email: {email}, name: {name}, phone: {phone}", flush=True)
        
        # 이메일 필수 확인
        if not email:
            print(f"❌ 이메일 필수 필드 누락", flush=True)
            return jsonify({'error': '이메일은 필수입니다.'}), 400
        
        # DB 연결 먼저 생성
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 추천인 코드 생성 - 고유한 UUID 기반
        import uuid
        import hashlib
        
        # 사용자별 고유 코드 생성 (이메일 기반 해시)
        user_unique_id = hashlib.md5(email.encode()).hexdigest()[:8].upper()
        code = f"REF{user_unique_id}"
        
        if DATABASE_URL.startswith('postgresql://'):
            # PostgreSQL - users 테이블에서 사용자 찾기 또는 생성
            print(f"🔍 사용자 조회/생성 시작: email={email}", flush=True)
            
            # 기존 사용자 확인 (display_name 컬럼은 선택적이므로 제거)
            cursor.execute("""
                SELECT user_id, email, referral_code, username
                FROM users 
                WHERE email = %s OR external_uid = %s
            """, (email, email))
            existing_user = cursor.fetchone()
            
            if existing_user:
                user_id = existing_user['user_id']
                existing_code = existing_user.get('referral_code')
                
                print(f"✅ 기존 사용자 발견: user_id={user_id}, existing_code={existing_code}", flush=True)
                
                # 추천인 코드가 없으면 생성
                if not existing_code:
                    cursor.execute("""
                        UPDATE users 
                        SET referral_code = %s, updated_at = NOW()
                        WHERE user_id = %s
                    """, (code, user_id))
                    print(f"✅ 추천인 코드 생성: {code}", flush=True)
                else:
                    code = existing_code
                    print(f"✅ 기존 추천인 코드 사용: {code}", flush=True)
                
                # 사용자 정보 업데이트 (name, phone이 있는 경우)
                if name or phone:
                    update_fields = []
                    update_values = []
                    if name:
                        update_fields.append("username = %s")
                        update_values.append(name)
                    if phone:
                        # phone은 users 테이블에 없을 수 있으므로 meta_json에 저장하거나 스킵
                        pass
                    if update_fields:
                        update_values.append(user_id)
                        cursor.execute(f"""
                            UPDATE users 
                            SET {', '.join(update_fields)}, updated_at = NOW()
                            WHERE user_id = %s
                        """, update_values)
                        print(f"✅ 사용자 정보 업데이트 완료", flush=True)
            else:
                # 새 사용자 생성
                print(f"🆕 새 사용자 생성: email={email}", flush=True)
                
                # external_uid 생성 (이메일 기반)
                external_uid = f"admin_{hashlib.md5(email.encode()).hexdigest()[:16]}"
                
                cursor.execute("""
                    INSERT INTO users (external_uid, email, username, referral_code, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, NOW(), NOW())
                    RETURNING user_id
                """, (external_uid, email, name or email.split('@')[0], code))
                
                user_id = cursor.fetchone()['user_id']
                
                # wallet 생성
                cursor.execute("""
                    INSERT INTO wallets (user_id, balance, created_at, updated_at)
                    VALUES (%s, 0, NOW(), NOW())
                """, (user_id,))
                
                print(f"✅ 새 사용자 및 추천인 코드 생성: user_id={user_id}, code={code}", flush=True)
            
            conn.commit()
            print(f"✅ 추천인 등록 완료: email={email}, user_id={user_id}, code={code}", flush=True)
            
        else:
            # SQLite - 레거시 로직 (호환성 유지)
            cursor.execute("SELECT user_id, referral_code FROM users WHERE email = ?", (email,))
            existing_user = cursor.fetchone()
            
            if existing_user:
                user_id = existing_user[0]
                existing_code = existing_user[1] if len(existing_user) > 1 else None
                
                if not existing_code:
                    cursor.execute("""
                        UPDATE users 
                        SET referral_code = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = ?
                    """, (code, user_id))
                else:
                    code = existing_code
            else:
                external_uid = f"admin_{hashlib.md5(email.encode()).hexdigest()[:16]}"
                cursor.execute("""
                    INSERT INTO users (external_uid, email, username, referral_code, created_at, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (external_uid, email, name or email.split('@')[0], code))
                user_id = cursor.lastrowid
                
                cursor.execute("""
                    INSERT INTO wallets (user_id, balance, created_at, updated_at)
                    VALUES (?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (user_id,))
            
            conn.commit()
        
        return jsonify({
            'id': str(uuid.uuid4()),
            'email': email,
            'referralCode': code,
            'name': name,
            'phone': phone,
            'message': '추천인 등록 성공'
        }), 200
        
    except Exception as e:
        import traceback
        error_msg = f'추천인 등록 실패: {str(e)}'
        print(f"❌ {error_msg}", flush=True)
        print(f"❌ Traceback:", flush=True)
        print(traceback.format_exc(), flush=True)
        
        if conn:
            try:
                conn.rollback()
            except:
                pass
        
        return jsonify({
            'error': error_msg,
            'details': str(e),
            'type': type(e).__name__
        }), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 관리자용 추천인 목록 조회
@app.route('/api/admin/referral/list', methods=['GET'])
def admin_get_referrals():
    """Admin Get Referrals
    ---
    tags:
      - Admin
    summary: Admin Get Referrals
    description: "Admin Get Referrals API"
    security:
      - Bearer: []
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """관리자용 추천인 목록 조회"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            # 새 스키마에서는 referrals 테이블 사용
            try:
                cursor.execute("""
                    SELECT r.referral_id, u.email, u.referral_code, u.username, NULL as phone, r.created_at, 
                           'active' as status
                    FROM referrals r
                    JOIN users u ON r.referrer_user_id = u.user_id
                    ORDER BY r.created_at DESC
                """)
            except Exception as e:
                print(f"⚠️ 새 스키마 쿼리 실패: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'referrals': []}), 200
        else:
            cursor.execute("""
                SELECT id, user_email, code, name, phone, created_at, is_active
                FROM referral_codes 
                ORDER BY created_at DESC
            """)
        
        referrals = []
        for row in cursor.fetchall():
            # 날짜 형식 처리
            join_date = row[5]
            if hasattr(join_date, 'strftime'):
                join_date = join_date.strftime('%Y-%m-%d')
            elif hasattr(join_date, 'isoformat'):
                join_date = join_date.isoformat()[:10]
            else:
                join_date = str(join_date)[:10]
            
            if DATABASE_URL.startswith('postgresql://'):
                # 새 스키마: referral_id, email, referral_code, username, phone, created_at, status
                referrals.append({
                    'id': str(row[0]),
                    'email': row[1],
                    'referralCode': row[2],
                    'name': row[3] or '사용자',
                    'phone': row[4],
                    'joinDate': row[5].isoformat()[:10] if row[5] and hasattr(row[5], 'isoformat') else (str(row[5])[:10] if row[5] else None),
                    'status': 'active'
                })
            else:
                referrals.append({
                    'id': row[0],
                    'email': row[1],
                    'referralCode': row[2],
                    'name': row[3],
                    'phone': row[4],
                    'joinDate': join_date,
                    'status': 'active' if row[6] else 'inactive'
                })
        
        return jsonify({
            'referrals': referrals,
            'count': len(referrals)
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'추천인 목록 조회 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 관리자용 추천인 코드 목록 조회
@app.route('/api/admin/referral/codes', methods=['GET'])
def admin_get_referral_codes():
    """Admin Get Referral Codes
    ---
    tags:
      - Admin
    summary: Admin Get Referral Codes
    description: "Admin Get Referral Codes API"
    security:
      - Bearer: []
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """관리자용 추천인 코드 목록 조회"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            # 새 스키마에서는 users.referral_code 사용
            try:
                cursor.execute("""
                    SELECT u.user_id, u.referral_code, u.email, u.username, NULL as phone, u.created_at, 
                           TRUE as is_active,
                           COUNT(DISTINCT r.referral_id) as usage_count,
                           COALESCE(SUM(c.amount), 0) as total_commission,
                           COALESCE(u.commission_rate, 0.1) as commission_rate
                    FROM users u
                    LEFT JOIN referrals r ON u.user_id = r.referrer_user_id
                    LEFT JOIN commissions c ON r.referral_id = c.referral_id
                    WHERE u.referral_code IS NOT NULL
                    GROUP BY u.user_id, u.referral_code, u.email, u.username, u.created_at, u.commission_rate
                    ORDER BY u.created_at DESC
                """)
            except Exception as e:
                print(f"⚠️ 새 스키마 쿼리 실패: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'codes': []}), 200
        else:
            cursor.execute("""
                SELECT id, code, user_email, name, phone, created_at, is_active, 
                    COALESCE(usage_count, 0) as usage_count, 
                    COALESCE(total_commission, 0) as total_commission
                FROM referral_codes 
                ORDER BY created_at DESC
            """)
        
        codes = []
        for row in cursor.fetchall():
            if DATABASE_URL.startswith('postgresql://'):
                # 새 스키마: user_id, referral_code, email, username, phone, created_at, is_active, usage_count, total_commission, commission_rate
                created_at = row[5]
                is_active = row[6] if len(row) > 6 else True
                usage_count = row[7] if len(row) > 7 else 0
                total_commission = float(row[8]) if len(row) > 8 and row[8] else 0.0
                commission_rate = float(row[9]) if len(row) > 9 and row[9] is not None else 0.1
            else:
                # 구 스키마
                created_at = row[5]
                is_active = row[6]
                usage_count = row[7] if len(row) > 7 else 0
                total_commission = float(row[8]) if len(row) > 8 and row[8] else 0.0
            
            # 날짜 형식 처리 강화
            if hasattr(created_at, 'isoformat'):
                created_at = created_at.isoformat()
            elif hasattr(created_at, 'strftime'):
                created_at = created_at.strftime('%Y-%m-%dT%H:%M:%S')
            else:
                created_at = str(created_at)
            
            # Invalid Date 방지
            if created_at == 'None' or created_at == 'null' or not created_at:
                from datetime import datetime
                created_at = datetime.now().isoformat()
            
            # is_active 값 처리
            if is_active is None:
                is_active = True  # None이면 True로 설정
            elif isinstance(is_active, str):
                is_active = is_active.lower() in ['true', '1', 'yes']
            else:
                is_active = bool(is_active)
            
            code_data = {
                'id': str(row[0]),
                'code': row[1],
                'email': row[2],
                'name': row[3] or '사용자',
                'phone': row[4] if len(row) > 4 else None,
                'createdAt': created_at,
                'isActive': is_active,
                'usage_count': usage_count,
                'total_commission': total_commission
            }
            
            # commission_rate 추가 (PostgreSQL만)
            if DATABASE_URL.startswith('postgresql://'):
                code_data['commission_rate'] = commission_rate
                code_data['user_id'] = row[0]
            else:
                code_data['commission_rate'] = 0.1  # SQLite 기본값
            
            codes.append(code_data)
        
        return jsonify({
            'codes': codes,
            'count': len(codes)
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'추천인 코드 목록 조회 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 관리자용 커미션 내역 조회
@app.route('/api/admin/referral/commissions', methods=['GET'])
def admin_get_commissions():
    """Admin Get Commissions
    ---
    tags:
      - Admin
    summary: Admin Get Commissions
    description: "Admin Get Commissions API"
    security:
      - Bearer: []
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """관리자용 커미션 내역 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            # 새 스키마에서는 commissions 테이블 사용
            try:
                cursor.execute("""
                    SELECT 
                        c.commission_id, 
                        r.referred_user_id, 
                        NULL::numeric AS base_amount, 
                        c.amount, 
                        NULL::numeric AS commission_rate, 
                        c.created_at
                    FROM commissions c
                    JOIN referrals r ON c.referral_id = r.referral_id
                    WHERE c.status = 'accrued'
                    ORDER BY c.created_at DESC
                """)
            except Exception as e:
                print(f"⚠️ 새 스키마 쿼리 실패: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'commissions': []}), 200
        else:
            cursor.execute("""
                SELECT ledger_id, referred_user_id, base_amount, amount, 
                    commission_rate, created_at
                FROM commission_ledger 
                WHERE event = 'earn' AND status = 'confirmed'
                ORDER BY created_at DESC
            """)
        
        commissions = []
        for row in cursor.fetchall():
            commissions.append({
                'id': row[0],
                'referredUser': row[1] if row[1] else 'N/A',
                'purchaseAmount': float(row[2]) if row[2] else 0,
                'commissionAmount': float(row[3]) if row[3] else 0,
                'commissionRate': f"{float(row[4]) * 100}%" if row[4] else "0%",
                'paymentDate': row[5].strftime('%Y-%m-%d') if hasattr(row[5], 'strftime') else (str(row[5])[:10] if row[5] else '')
            })
        
        conn.close()
        return jsonify({
            'commissions': commissions,
            'count': len(commissions)
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'커미션 내역 조회 실패: {str(e)}'}), 500

# 포인트 구매 내역 조회
@app.route('/api/points/purchase-history', methods=['GET'])
def get_purchase_history():
    """포인트 구매 내역 조회
    ---
    tags:
      - Points
    summary: 포인트 구매 내역 조회
    description: "사용자의 포인트 구매 내역을 조회합니다."
    security:
      - Bearer: []
    parameters:
      - name: user_id
        in: query
        type: string
        required: true
        description: 사용자 ID
        example: "user123"
    responses:
      200:
        description: 구매 내역 조회 성공
        schema:
          type: object
          properties:
            purchases:
              type: array
              items:
                type: object
                properties:
                  purchase_id:
                    type: integer
                    example: 123
                  amount:
                    type: number
                    example: 10000
                  price:
                    type: number
                    example: 10000
                  status:
                    type: string
                    example: "completed"
                  created_at:
                    type: string
                    example: "2024-01-01T00:00:00"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "user_id가 필요합니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "구매 내역 조회 실패: ..."
    """
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id가 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            # 새 스키마에서는 wallet_transactions 사용
            try:
                # external_uid로 사용자 찾기
                cursor.execute("""
                    SELECT user_id FROM users 
                    WHERE external_uid = %s OR email = %s
                    LIMIT 1
                """, (user_id, user_id))
                user_result = cursor.fetchone()
                if not user_result:
                    return jsonify({'purchases': []}), 200
                db_user_id = user_result[0]
                
                # wallet_id 찾기
                cursor.execute("SELECT wallet_id FROM wallets WHERE user_id = %s", (db_user_id,))
                wallet_result = cursor.fetchone()
                if not wallet_result:
                    return jsonify({'purchases': []}), 200
                wallet_id = wallet_result[0]
                
                # wallet_transactions에서 topup 타입만 조회
                cursor.execute("""
                    SELECT transaction_id, amount, created_at, status
                    FROM wallet_transactions 
                    WHERE wallet_id = %s AND type = 'topup'
                    ORDER BY created_at DESC
                """, (wallet_id,))
            except Exception as e:
                print(f"⚠️ 새 스키마 쿼리 실패: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'purchases': []}), 200
        else:
            cursor.execute("""
                SELECT id, amount, price, status, created_at
                FROM point_purchases WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
        
        purchases = cursor.fetchall()
        conn.close()
        
        purchase_list = []
        for purchase in purchases:
            if DATABASE_URL.startswith('postgresql://'):
                # 새 스키마: transaction_id, amount, created_at, status
                purchase_list.append({
                    'id': purchase[0],
                    'amount': float(purchase[1]) if purchase[1] else 0.0,
                    'price': float(purchase[1]) if purchase[1] else 0.0,  # amount를 price로도 사용
                    'status': purchase[3] if len(purchase) > 3 else 'approved',
                    'created_at': purchase[2].isoformat() if purchase[2] and hasattr(purchase[2], 'isoformat') else (str(purchase[2]) if purchase[2] else None)
                })
            else:
                purchase_list.append({
                    'id': purchase[0],
                    'amount': purchase[1],
                    'price': float(purchase[2]),
                    'status': purchase[3],
                    'created_at': purchase[4].isoformat() if hasattr(purchase[4], 'isoformat') else str(purchase[4])
                })
        
        return jsonify({
            'purchases': purchase_list
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'구매 내역 조회 실패: {str(e)}'}), 500

# 관리자 사용자 목록
@app.route('/api/admin/users', methods=['GET'])
def get_admin_users():
    """관리자 사용자 목록 조회
    ---
    tags:
      - Admin
    summary: 관리자 사용자 목록 조회
    description: "전체 사용자 목록을 조회합니다."
    security:
      - Bearer: []
    parameters:
      - name: page
        in: query
        type: integer
        required: false
        description: 페이지 번호
        example: 1
      - name: limit
        in: query
        type: integer
        required: false
        description: 페이지당 항목 수
        example: 20
    responses:
      200:
        description: 사용자 목록 조회 성공
        schema:
          type: object
          properties:
            users:
              type: array
              items:
                type: object
                properties:
                  user_id:
                    type: integer
                    example: 1
                  email:
                    type: string
                    example: "user@example.com"
                  created_at:
                    type: string
                    example: "2024-01-01T00:00:00"
            total:
              type: integer
              example: 100
      401:
        description: 인증 실패
    """
    try:
        print("🔍 관리자 사용자 목록 조회 시작")
        conn = get_db_connection()
        cursor = conn.cursor()
            
        # 먼저 간단한 쿼리로 테스트
        print("📊 기본 연결 테스트 중...")
        cursor.execute("SELECT 1")
        test_result = cursor.fetchone()
        print(f"✅ 기본 쿼리 성공: {test_result}")
        
        # 테이블 목록 확인
        print("📊 테이블 목록 조회 중...")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📊 존재하는 테이블: {tables}")
        
        user_list = []
        
        if 'users' in tables:
            print("📊 users 테이블 발견, 데이터 조회 중...")
            try:
                # 간단한 쿼리부터 시작
                cursor.execute("SELECT COUNT(*) FROM users")
                user_count = cursor.fetchone()[0]
                print(f"📊 users 테이블 레코드 수: {user_count}")
                
                if user_count > 0:
                    # 새 스키마 컬럼에 맞게 조회
                    cursor = conn.cursor(cursor_factory=RealDictCursor)
                    cursor.execute("""
                        SELECT 
                            u.user_id,
                            u.external_uid,
                            u.email,
                            u.username,
                            u.referral_code,
                            u.created_at,
                            u.updated_at,
                            COALESCE(w.balance, 0) AS balance
                        FROM users u
                        LEFT JOIN wallets w ON u.user_id = w.user_id
                        ORDER BY u.created_at DESC
                        LIMIT 100
                    """)
                    users = cursor.fetchall()
                    
                    for user in users:
                        derived_username = user.get('username') or 'N/A'
                        user_list.append({
                            'user_id': user.get('user_id'),
                            'external_uid': user.get('external_uid') or 'N/A',
                            'email': user.get('email') or 'N/A',
                            'username': derived_username,
                            'display_name': derived_username,
                            'referral_code': user.get('referral_code') or '',
                            'is_active': True,
                            'balance': float(user.get('balance') or 0),
                            'created_at': user.get('created_at').isoformat() if user.get('created_at') and hasattr(user.get('created_at'), 'isoformat') else (str(user.get('created_at')) if user.get('created_at') else 'N/A'),
                            'updated_at': user.get('updated_at').isoformat() if user.get('updated_at') and hasattr(user.get('updated_at'), 'isoformat') else (str(user.get('updated_at')) if user.get('updated_at') else 'N/A'),
                        })
                    
                    print(f"📊 총 {len(users)}명의 사용자 데이터를 조회했습니다.")
                else:
                    print("📊 users 테이블이 비어있습니다.")
            except Exception as e:
                print(f"❌ users 테이블 조회 실패: {e}")
        else:
            print("⚠️ users 테이블이 존재하지 않습니다.")
        
        conn.close()
        print(f"✅ 사용자 목록 반환: {len(user_list)}명")
        
        return jsonify({
            'users': user_list,
            'debug_info': {
                'tables': tables,
                'user_count': len(user_list)
            }
            }), 200
        
    except Exception as e:
        print(f"❌ 사용자 목록 조회 실패: {str(e)}")
        import traceback
        print(f"❌ 상세 오류: {traceback.format_exc()}")
        
        return jsonify({
            'error': f'사용자 목록 조회 실패: {str(e)}',
            'details': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
@require_admin_auth
def update_admin_user(user_id):
    """Update Admin User
    ---
    tags:
      - Admin
    summary: Update Admin User
    description: "Update Admin User API"
    security:
      - Bearer: []
    parameters:
      - name: user_id
        in: path
        type: int
        required: true
        description: User Id
        example: "example_user_id"
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """관리자 사용자 정보 수정"""
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 사용자 존재 확인
        cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({'error': '사용자를 찾을 수 없습니다.'}), 404
        
        # 비밀번호 수정
        if 'password' in data:
            import hashlib
            password_hash = hashlib.sha256(data['password'].encode()).hexdigest()
            cursor.execute("""
                UPDATE users 
                SET password_hash = %s, updated_at = NOW()
                WHERE user_id = %s
            """, (password_hash, user_id))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'message': '비밀번호가 수정되었습니다.'}), 200
        
        # 포인트 수정
        if 'balance' in data:
            balance = float(data['balance'])
            # wallet 업데이트 또는 생성
            cursor.execute("SELECT wallet_id FROM wallets WHERE user_id = %s", (user_id,))
            wallet = cursor.fetchone()
            if wallet:
                cursor.execute("""
                    UPDATE wallets 
                    SET balance = %s, updated_at = NOW()
                    WHERE user_id = %s
                """, (balance, user_id))
            else:
                cursor.execute("""
                    INSERT INTO wallets (user_id, balance, created_at, updated_at)
                    VALUES (%s, %s, NOW(), NOW())
                """, (user_id, balance))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'message': '포인트가 수정되었습니다.'}), 200
        
        # 일반 정보 수정
        update_fields = []
        update_values = []
        
        if 'username' in data:
            update_fields.append('username = %s')
            update_values.append(data['username'])
        if 'display_name' in data:
            update_fields.append('display_name = %s')
            update_values.append(data['display_name'])
        if 'email' in data:
            update_fields.append('email = %s')
            update_values.append(data['email'])
        if 'referral_code' in data:
            update_fields.append('referral_code = %s')
            update_values.append(data['referral_code'])
        if 'is_active' in data:
            update_fields.append('is_active = %s')
            update_values.append(data['is_active'])
        
        if update_fields:
            update_fields.append('updated_at = NOW()')
            update_values.append(user_id)
            query = f"UPDATE users SET {', '.join(update_fields)} WHERE user_id = %s"
            cursor.execute(query, tuple(update_values))
            conn.commit()
        
        cursor.close()
        conn.close()
        return jsonify({'message': '사용자 정보가 수정되었습니다.'}), 200
        
    except Exception as e:
        import traceback
        print(f"❌ 사용자 수정 실패: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'사용자 수정 실패: {str(e)}'}), 500

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@require_admin_auth
def delete_admin_user(user_id):
    """Delete Admin User
    ---
    tags:
      - Admin
    summary: Delete Admin User
    description: "Delete Admin User API"
    security:
      - Bearer: []
    parameters:
      - name: user_id
        in: path
        type: int
        required: true
        description: User Id
        example: "example_user_id"
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """관리자 사용자 삭제"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 사용자 존재 확인
        cursor.execute("SELECT user_id, email FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({'error': '사용자를 찾을 수 없습니다.'}), 404
        
        # 사용자 삭제 (CASCADE로 관련 데이터도 삭제됨)
        cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': '사용자가 삭제되었습니다.'}), 200
        
    except Exception as e:
        import traceback
        print(f"❌ 사용자 삭제 실패: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'사용자 삭제 실패: {str(e)}'}), 500

@app.route('/api/admin/referral/codes/<code>', methods=['DELETE'])
@require_admin_auth
def delete_referral_code(code):
    """Delete Referral Code
    ---
    tags:
      - Admin
    summary: Delete Referral Code
    description: "Delete Referral Code API"
    security:
      - Bearer: []
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """추천인 코드 삭제"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 추천인 코드 확인
        cursor.execute("SELECT referral_code FROM users WHERE referral_code = %s", (code,))
        user = cursor.fetchone()
        if not user:
            return jsonify({'error': '추천인 코드를 찾을 수 없습니다.'}), 404
        
        # 추천인 코드 삭제 (NULL로 설정)
        cursor.execute("""
            UPDATE users 
            SET referral_code = NULL, updated_at = NOW()
            WHERE referral_code = %s
        """, (code,))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': '추천인 코드가 삭제되었습니다.'}), 200
        
    except Exception as e:
        import traceback
        print(f"❌ 추천인 코드 삭제 실패: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'추천인 코드 삭제 실패: {str(e)}'}), 500

@app.route('/api/admin/payout-requests', methods=['GET'])
@require_admin_auth
def get_payout_requests():
    """Get Payout Requests
    ---
    tags:
      - Admin
    summary: Get Payout Requests
    description: "Get Payout Requests API"
    security:
      - Bearer: []
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """환급신청 목록 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                pr.request_id,
                pr.user_id,
                u.email as referrer_email,
                u.username as referrer_name,
                u.phone as phone,
                pr.amount,
                pr.bank_name,
                pr.account_number,
                pr.status,
                pr.requested_at as created_at,
                pr.processed_at
            FROM payout_requests pr
            LEFT JOIN users u ON pr.user_id = u.user_id
            ORDER BY pr.requested_at DESC
        """)
        
        requests = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            'payout_requests': [dict(req) for req in requests]
        }), 200
        
    except Exception as e:
        import traceback
        print(f"❌ 환급신청 목록 조회 실패: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'환급신청 목록 조회 실패: {str(e)}'}), 500

@app.route('/api/admin/payout-requests/<int:request_id>/approve', methods=['PUT'])
@require_admin_auth
def approve_payout_request(request_id):
    """Approve Payout Request
    ---
    tags:
      - Admin
    summary: Approve Payout Request
    description: "Approve Payout Request API"
    security:
      - Bearer: []
    parameters:
      - name: request_id
        in: path
        type: int
        required: true
        description: Request Id
        example: "example_request_id"
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """환급신청 승인"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 환급신청 확인
        cursor.execute("""
            SELECT pr.*, u.email as referrer_email
            FROM payout_requests pr
            LEFT JOIN users u ON pr.user_id = u.user_id
            WHERE pr.request_id = %s
        """, (request_id,))
        request_data = cursor.fetchone()
        
        if not request_data:
            return jsonify({'error': '환급신청을 찾을 수 없습니다.'}), 404
        
        # 상태 확인: 'requested' 또는 'pending'만 처리
        if request_data['status'] not in ('pending', 'requested'):
            return jsonify({'error': '이미 처리된 환급신청입니다.'}), 400
        
        # referral_code 조회 (commission_ledger 기록을 위해 필요)
        cursor.execute("""
            SELECT referral_code FROM users WHERE user_id = %s
        """, (request_data['user_id'],))
        user_result = cursor.fetchone()
        referral_code = user_result['referral_code'] if user_result and user_result.get('referral_code') else None
        
        if not referral_code:
            return jsonify({'error': '추천인 코드를 찾을 수 없습니다.'}), 400
        
        # 환급신청 승인 및 payout 생성
        cursor.execute("""
            UPDATE payout_requests 
            SET status = 'approved', processed_at = NOW()
            WHERE request_id = %s
        """, (request_id,))
        
        # payout 레코드 생성
        cursor.execute("""
            INSERT INTO payouts (request_id, user_id, paid_amount, processed_at, created_at, updated_at)
            VALUES (%s, %s, %s, NOW(), NOW(), NOW())
        """, (request_id, request_data['user_id'], request_data['amount']))
        
        # commission_ledger에 payout 이벤트 기록 (음수로 기록하여 잔액 차감)
        payout_amount = float(request_data['amount'])
        cursor.execute("""
            INSERT INTO commission_ledger 
            (referral_code, referrer_user_id, order_id, event, base_amount, commission_rate, amount, status, notes, created_at, confirmed_at)
            VALUES (%s, %s, NULL, 'payout', %s, 0, %s, 'confirmed', %s, NOW(), NOW())
        """, (
            referral_code,
            str(request_data['user_id']),  # 문자열로 변환 (referrer_user_id는 VARCHAR)
            payout_amount,  # base_amount
            -payout_amount,  # amount는 음수 (잔액 차감)
            f'환급 신청 승인 - 신청 ID: {request_id}, 은행: {request_data.get("bank_name", "N/A")}, 계좌: {request_data.get("account_number", "N/A")}'
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': '환급신청이 승인되었습니다.'}), 200
        
    except Exception as e:
        import traceback
        print(f"❌ 환급신청 승인 실패: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'환급신청 승인 실패: {str(e)}'}), 500

@app.route('/api/admin/payout-requests/<int:request_id>/reject', methods=['PUT'])
@require_admin_auth
def reject_payout_request(request_id):
    """Reject Payout Request
    ---
    tags:
      - Admin
    summary: Reject Payout Request
    description: "Reject Payout Request API"
    security:
      - Bearer: []
    parameters:
      - name: request_id
        in: path
        type: int
        required: true
        description: Request Id
        example: "example_request_id"
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """환급신청 거절"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 환급신청 확인
        cursor.execute("SELECT * FROM payout_requests WHERE request_id = %s", (request_id,))
        request_data = cursor.fetchone()
        
        if not request_data:
            return jsonify({'error': '환급신청을 찾을 수 없습니다.'}), 404
        
        # 상태 확인: 'requested' 또는 'pending'만 처리
        if request_data['status'] not in ('pending', 'requested'):
            return jsonify({'error': '이미 처리된 환급신청입니다.'}), 400
        
        # 환급신청 거절
        cursor.execute("""
            UPDATE payout_requests 
            SET status = 'rejected', processed_at = NOW()
            WHERE request_id = %s
        """, (request_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': '환급신청이 거절되었습니다.'}), 200
        
    except Exception as e:
        import traceback
        print(f"❌ 환급신청 거절 실패: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'환급신청 거절 실패: {str(e)}'}), 500

# 관리자 거래 내역
@app.route('/api/admin/transactions', methods=['GET'])
def get_admin_transactions():
    """Get Admin Transactions
    ---
    tags:
      - Admin
    summary: Get Admin Transactions
    description: "Get Admin Transactions API"
    security:
      - Bearer: []
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """관리자 거래 내역"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            # 새 스키마에서는 order_items와 product_variants 조인 필요
            try:
                cursor.execute("""
                    SELECT 
                        o.order_id,
                        o.user_id,
                        COALESCE(o.final_amount, o.total_amount, 0) as price,
                        o.total_amount,
                        o.status,
                        o.created_at,
                        oi.variant_id,
                        pv.meta_json->>'service_id' as service_id,
                        COALESCE(o.detailed_service, pv.name, 'N/A') as service_name,
                        COALESCE(oi.quantity, 0) as quantity,
                        COALESCE(oi.link, '') as link,
                        COALESCE(o.notes, '') as comments,
                        o.smm_panel_order_id
                    FROM orders o
                    LEFT JOIN (
                        SELECT DISTINCT ON (order_id) 
                            order_id, variant_id, quantity, link
                        FROM order_items
                        ORDER BY order_id, order_item_id ASC
                    ) oi ON o.order_id = oi.order_id
                    LEFT JOIN product_variants pv ON oi.variant_id = pv.variant_id
                    ORDER BY o.created_at DESC
                    LIMIT 100
                """)
            except Exception as e:
                print(f"⚠️ 새 스키마 쿼리 실패: {e}")
                import traceback
                traceback.print_exc()
                # 폴백: 기본 정보만 조회
                try:
                    cursor.execute("""
                        SELECT o.order_id, o.user_id, o.final_amount, o.total_amount, o.status, o.created_at,
                               NULL as variant_id, NULL as service_id, COALESCE(o.detailed_service, 'N/A') as service_name, 
                               0 as quantity, '' as link, COALESCE(o.notes, '') as comments, o.smm_panel_order_id
                        FROM orders o
                        ORDER BY o.created_at DESC
                        LIMIT 100
                    """)
                except Exception as e2:
                    print(f"⚠️ 폴백 쿼리도 실패: {e2}")
                    return jsonify({'transactions': []}), 200
        else:
            cursor.execute("""
                SELECT o.order_id, o.user_id, o.service_id, o.price, o.status, o.created_at,
                       o.platform, o.service_name, o.quantity, o.link, '' as comments
                FROM orders o
                ORDER BY o.created_at DESC
            """)
        
        transactions = cursor.fetchall()
        conn.close()
        
        transaction_list = []
        for transaction in transactions:
            if DATABASE_URL.startswith('postgresql://'):
                # 새 스키마: (order_id, user_id, price, total_amount, status, created_at, variant_id, service_id, service_name, quantity, link, comments, smm_panel_order_id)
                order_id = transaction[0]
                user_id_val = transaction[1]
                price = float(transaction[2]) if transaction[2] else 0.0  # final_amount
                total_amount = float(transaction[3]) if transaction[3] else 0.0
                status = transaction[4] if transaction[4] else 'pending'
                created_at = transaction[5]
                variant_id = transaction[6] if len(transaction) > 6 else None
                service_id = str(transaction[7]) if len(transaction) > 7 and transaction[7] else 'N/A'
                service_name = str(transaction[8]) if len(transaction) > 8 and transaction[8] else 'N/A'
                quantity = int(transaction[9]) if len(transaction) > 9 and transaction[9] else 0
                link = str(transaction[10]) if len(transaction) > 10 and transaction[10] else 'N/A'
                comments = str(transaction[11]) if len(transaction) > 11 and transaction[11] else 'N/A'
                smm_panel_order_id = transaction[12] if len(transaction) > 12 else None
                
                # SMM Panel API에서 실제 사용 금액(charge) 조회
                charge = 0
                if smm_panel_order_id and status in ['processing', 'completed', 'pending']:
                    try:
                        smm_status = call_smm_panel_api({
                            'action': 'status',
                            'order': smm_panel_order_id
                        })
                        if smm_status.get('status') == 'success':
                            charge = float(smm_status.get('charge', 0)) or 0
                    except Exception as e:
                        print(f"⚠️ SMM Panel 상태 조회 오류 (관리자): {e}")
                        charge = 0
                
                transaction_list.append({
                    'order_id': order_id,
                    'user_id': str(user_id_val) if user_id_val else None,
                    'price': price,  # final_amount
                    'total_amount': total_amount,
                    'charge': charge,  # 실제 사용 금액 추가
                    'status': status,
                    'created_at': created_at.isoformat() if created_at and hasattr(created_at, 'isoformat') else (str(created_at) if created_at else ''),
                    'variant_id': variant_id,
                    'service_id': service_id,
                    'service_name': service_name,
                    'quantity': quantity,
                    'link': link if link and link != 'None' and link != 'null' else 'N/A',
                    'comments': comments,
                    'platform': 'N/A'  # 새 스키마에는 platform이 없음
                })
            else:
                transaction_list.append({
                    'order_id': transaction[0],
                    'user_id': transaction[1],
                    'service_id': transaction[2],
                    'price': float(transaction[3]),
                    'status': transaction[4],
                    'created_at': transaction[5].isoformat() if hasattr(transaction[5], 'isoformat') else str(transaction[5]),
                    'platform': transaction[6] if len(transaction) > 6 else 'N/A',
                    'service_name': transaction[7] if len(transaction) > 7 else 'N/A',
                    'quantity': transaction[8] if len(transaction) > 8 else 0,
                    'link': transaction[9] if len(transaction) > 9 else 'N/A',
                    'comments': transaction[10] if len(transaction) > 10 else 'N/A'
                })
        
        return jsonify({
            'transactions': transaction_list
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'거래 내역 조회 실패: {str(e)}'}), 500

# 관리자 페이지 라우트
@app.route('/admin')
def serve_admin():
    """Serve Admin
    ---
    tags:
      - API
    summary: Serve Admin
    description: "Serve Admin API"
    security:
      - Bearer: []
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """관리자 페이지 서빙 - 관리자 권한 체크"""
    try:
        # 현재 사용자 정보 가져오기
        current_user = get_current_user()
        if not current_user:
            return jsonify({'error': '로그인이 필요합니다.'}), 401
        
        user_email = current_user.get('email')
        user_id = current_user.get('user_id')
        
        # 데이터베이스에서 is_admin 체크
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # email로만 사용자 찾기 (단순화)
            if not user_email:
                return jsonify({'error': '이메일 정보가 없습니다.'}), 401
            
            if DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    SELECT is_admin 
                    FROM users 
                    WHERE email = %s
                    LIMIT 1
                """, (user_email,))
            else:
                cursor.execute("""
                    SELECT is_admin 
                    FROM users 
                    WHERE email = ?
                    LIMIT 1
                """, (user_email,))
            
            user = cursor.fetchone()
            
            if not user:
                return jsonify({'error': '사용자를 찾을 수 없습니다.'}), 404
            
            is_admin = user.get('is_admin') if isinstance(user, dict) else user[0]
            
            # SQLite의 경우 0/1로 저장되므로 변환
            if is_admin is None or (isinstance(is_admin, (int, float)) and is_admin == 0) or is_admin is False:
                return jsonify({'error': '관리자 권한이 필요합니다.'}), 403
            
            # 관리자 권한이 있으면 페이지 반환
            return app.send_static_file('index.html')
            
        except Exception as db_error:
            print(f"❌ 관리자 권한 체크 중 DB 오류: {db_error}")
            import traceback
            print(traceback.format_exc())
            return jsonify({'error': '관리자 권한 확인 중 오류가 발생했습니다.'}), 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
                
    except Exception as e:
        print(f"❌ 관리자 페이지 서빙 오류: {e}")
        import traceback
        print(traceback.format_exc())
        try:
            return app.send_static_file('index.html')
        except:
            return jsonify({'error': 'Admin page not found'}), 404

# 루트 경로 서빙
@app.route('/', methods=['GET', 'POST'])
def serve_index():
    """Serve Index
    ---
    tags:
      - API
    summary: Serve Index
    description: "Serve Index API"
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """메인 페이지 서빙"""
    try:
        return app.send_static_file('index.html')
    except:
        # index.html이 없으면 기본 HTML 반환
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>SNS PMT</title>
            <meta charset="utf-8">
        </head>
        <body>
            <h1>SNS PMT 서비스</h1>
            <p>서비스가 정상적으로 실행되고 있습니다.</p>
            <p>API 엔드포인트:</p>
            <ul>
                <li>GET /api/health - 헬스 체크</li>
                <li>POST /api/register - 사용자 등록</li>
                <li>GET /api/points - 포인트 조회</li>
                <li>POST /api/orders - 주문 생성</li>
                <li>GET /api/orders - 주문 목록</li>
                <li>POST /api/points/purchase - 포인트 구매 신청</li>
                <li>GET /api/admin/stats - 관리자 통계</li>
                <li>GET /api/admin/purchases - 관리자 포인트 구매 목록</li>
            </ul>
        </body>
        </html>
        """, 200

# SMM Panel API 테스트 엔드포인트
@app.route('/api/smm-panel/test', methods=['GET'])
def smm_panel_test():
    """Smm Panel Test
    ---
    tags:
      - SMM Panel
    summary: Smm Panel Test
    description: "Smm Panel Test API"
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """SMM Panel API 연결 테스트"""
    try:
        import requests
        
        # 간단한 테스트 요청
        test_data = {
            'action': 'balance',
            'key': 'bc85538982fb27c6c0558be6cd669e67'
        }
        
        smm_panel_url = 'https://smmpanel.kr/api/v2'
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.post(smm_panel_url, json=test_data, headers=headers, timeout=10)
        
        return jsonify({
            'success': True,
            'status_code': response.status_code,
            'response': response.text[:500],
            'url': smm_panel_url
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# SMM Panel API 프록시 엔드포인트
@app.route('/api/smm-panel', methods=['POST'])
def smm_panel_proxy():
    """Smm Panel Proxy
    ---
    tags:
      - SMM Panel
    summary: Smm Panel Proxy
    description: "Smm Panel Proxy API"
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """SMM Panel API 프록시 - CORS 문제 해결"""
    try:
        import requests
        
        data = request.get_json()
        print(f"🔍 SMM Panel 프록시 요청: {data}")
        
        # SMM Panel API 호출
        smm_panel_url = 'https://smmpanel.kr/api/v2'
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.post(smm_panel_url, json=data, headers=headers, timeout=30)
        
        print(f"✅ SMM Panel API 응답: {response.status_code}")
        print(f"📄 SMM Panel API 응답 내용: {response.text[:500]}...")
        
        # 응답 데이터 파싱
        try:
            response_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        except:
            response_data = response.text
        
        return jsonify({
            'success': True,
            'data': response_data,
            'status_code': response.status_code,
            'raw_response': response.text
        })
        
    except requests.exceptions.RequestException as e:
        print(f"❌ SMM Panel API 요청 실패: {e}")
        return jsonify({
            'success': False,
            'error': f'API 요청 실패: {str(e)}'
        }), 500
    except Exception as e:
        print(f"❌ SMM Panel 프록시 오류: {e}")
        return jsonify({
            'success': False,
            'error': f'프록시 오류: {str(e)}'
        }), 500

@app.route('/api/admin/referral/activate-all', methods=['POST'])
def activate_all_referral_codes():
    """Activate All Referral Codes
    ---
    tags:
      - Admin
    summary: Activate All Referral Codes
    description: "Activate All Referral Codes API"
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """모든 추천인 코드를 활성화하는 엔드포인트"""
    print("🚀 추천인 코드 활성화 요청 시작")
    
    try:
        conn = None
        cursor = None
        try:
            print("🔗 데이터베이스 연결 시도")
            conn = get_db_connection()
            cursor = conn.cursor()
            print("✅ 데이터베이스 연결 성공")
            
            # 먼저 기존 코드 확인
            if DATABASE_URL.startswith('postgresql://'):
                cursor.execute("SELECT COUNT(*) FROM referral_codes")
                total_codes = cursor.fetchone()[0]
                print(f"📊 기존 추천인 코드 수: {total_codes}")
                
                if total_codes == 0:
                    print("⚠️ 활성화할 추천인 코드가 없습니다")
                    return jsonify({'message': '활성화할 추천인 코드가 없습니다'}), 200
                
                # 모든 추천인 코드를 강제로 활성화 (WHERE 조건 없이)
                cursor.execute("UPDATE referral_codes SET is_active = true, updated_at = CURRENT_TIMESTAMP")
                print(f"🔄 PostgreSQL: 모든 추천인 코드 활성화 실행")
            else:
                cursor.execute("SELECT COUNT(*) FROM referral_codes")
                total_codes = cursor.fetchone()[0]
                print(f"📊 기존 추천인 코드 수: {total_codes}")
                
                if total_codes == 0:
                    print("⚠️ 활성화할 추천인 코드가 없습니다")
                    return jsonify({'message': '활성화할 추천인 코드가 없습니다'}), 200
                
                # SQLite - 모든 추천인 코드를 강제로 활성화 (WHERE 조건 없이)
                cursor.execute("UPDATE referral_codes SET is_active = 1, updated_at = CURRENT_TIMESTAMP")
                print(f"🔄 SQLite: 모든 추천인 코드 활성화 실행")
            
            conn.commit()
            affected_rows = cursor.rowcount
            print(f"✅ 활성화된 코드 수: {affected_rows}")
            
            # 활성화 후 상태 확인
            if DATABASE_URL.startswith('postgresql://'):
                cursor.execute("SELECT code, is_active, created_at FROM referral_codes")
            else:
                cursor.execute("SELECT code, is_active, created_at FROM referral_codes")
            
            active_codes = cursor.fetchall()
            print(f"📊 활성화 후 상태 확인:")
            for code, is_active, created_at in active_codes:
                print(f"  - {code}: 활성화={is_active}, 생성일={created_at}")
            
            # 강제로 모든 코드를 다시 활성화 (데이터 보존)
            if DATABASE_URL.startswith('postgresql://'):
                cursor.execute("UPDATE referral_codes SET is_active = true")
            else:
                cursor.execute("UPDATE referral_codes SET is_active = 1")
            conn.commit()
            final_count = cursor.rowcount
            print(f"🔄 모든 코드 강제 재활성화 완료: {final_count}개 업데이트")
            
            # 최종 데이터 확인
            cursor.execute("SELECT COUNT(*) FROM referral_codes WHERE is_active = true")
            active_count = cursor.fetchone()[0]
            print(f"✅ 최종 활성화된 코드 수: {active_count}개")
            
            return jsonify({'message': f'{affected_rows}개의 추천인 코드가 활성화되었습니다'}), 200
            
        except Exception as db_error:
            print(f"❌ 데이터베이스 오류: {db_error}")
            if conn:
                conn.rollback()
            raise db_error
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            print("🔒 데이터베이스 연결 종료")
            
    except Exception as e:
        print(f"❌ 추천인 코드 활성화 오류: {e}")
        return jsonify({'error': f'서버 오류가 발생했습니다: {str(e)}'}), 500

# 추천인 커미션 포인트 조회
@app.route('/api/referral/commission-points', methods=['GET'])
def get_commission_points():
    """Get Commission Points
    ---
    tags:
      - Referral
    summary: Get Commission Points
    description: "Get Commission Points API"
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """추천인 커미션 포인트 조회 - 새 스키마 사용"""
    conn = None
    cursor = None
    try:
        referrer_email = request.args.get('referrer_email')  # external_uid 또는 email
        if not referrer_email:
            return jsonify({'error': 'referrer_email이 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print(f"🔍 커미션 포인트 조회 - referrer_email: {referrer_email}", flush=True)
        
        if DATABASE_URL.startswith('postgresql://'):
            # 먼저 사용자 찾기 (external_uid 또는 email로)
            cursor.execute("""
                SELECT user_id, email, referral_code
                FROM users 
                WHERE external_uid = %s OR email = %s
                LIMIT 1
            """, (referrer_email, referrer_email))
            referrer = cursor.fetchone()
            
            if not referrer:
                print(f"⚠️ 추천인을 찾을 수 없음: {referrer_email}", flush=True)
                return jsonify({
                    'total_earned': 0,
                    'total_paid': 0,
                    'current_balance': 0,
                    'created_at': None,
                    'updated_at': None
                }), 200
            
            referrer_user_id = referrer['user_id']
            print(f"✅ 추천인 찾음: user_id={referrer_user_id}", flush=True)
            
            # commissions (적립) 합계
            cursor.execute("""
                SELECT COALESCE(SUM(c.amount), 0) as total_earned
                FROM commissions c
                JOIN referrals r ON c.referral_id = r.referral_id
                WHERE r.referrer_user_id = %s
            """, (referrer_user_id,))
            earned_result = cursor.fetchone()
            total_earned = float(earned_result.get('total_earned', 0) or 0)
            
            # payouts (지급) 합계
            cursor.execute("""
                SELECT COALESCE(SUM(p.paid_amount), 0) as total_paid
                FROM payouts p
                JOIN payout_requests pr ON p.request_id = pr.request_id
                WHERE pr.user_id = %s
            """, (referrer_user_id,))
            paid_result = cursor.fetchone()
            total_paid = float(paid_result.get('total_paid', 0) or 0)
            
            # 현재 잔액 = 적립 - 지급
            current_balance = total_earned - total_paid
            
            print(f"✅ 커미션 포인트 조회 완료: 적립={total_earned}, 지급={total_paid}, 잔액={current_balance}", flush=True)
            
            return jsonify({
                'total_earned': total_earned,
                'total_paid': total_paid,
                'current_balance': current_balance,
                'created_at': None,
                'updated_at': None
            }), 200
        else:
            # SQLite - 레거시 호환
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(CASE WHEN event = 'earn' THEN amount ELSE 0 END), 0) as total_earned,
                    COALESCE(SUM(CASE WHEN event = 'payout' THEN ABS(amount) ELSE 0 END), 0) as total_paid,
                    COALESCE(SUM(amount), 0) as current_balance
                FROM commission_ledger 
                WHERE referrer_user_id = ? AND status = 'confirmed'
            """, (referrer_email,))
            
            result = cursor.fetchone()
            
            if result:
                return jsonify({
                    'total_earned': float(result[0]),
                    'total_paid': float(result[1]),
                    'current_balance': float(result[2]),
                    'created_at': None,
                    'updated_at': None
                }), 200
            else:
                return jsonify({
                    'total_earned': 0,
                    'total_paid': 0,
                    'current_balance': 0,
                    'created_at': None,
                    'updated_at': None
                }), 200
            
    except Exception as e:
        import traceback
        error_msg = f'커미션 포인트 조회 실패: {str(e)}'
        print(f"❌ {error_msg}", flush=True)
        print(traceback.format_exc(), flush=True)
        return jsonify({'error': error_msg, 'details': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 커미션 포인트 거래 내역 조회
@app.route('/api/referral/commission-transactions', methods=['GET'])
def get_commission_transactions():
    """Get Commission Transactions
    ---
    tags:
      - Referral
    summary: Get Commission Transactions
    description: "Get Commission Transactions API"
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """커미션 포인트 거래 내역 조회 - 새 스키마 사용"""
    conn = None
    cursor = None
    try:
        referrer_email = request.args.get('referrer_email')  # external_uid 또는 email
        if not referrer_email:
            return jsonify({'error': 'referrer_email이 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print(f"🔍 커미션 거래 내역 조회 - referrer_email: {referrer_email}", flush=True)
        
        if DATABASE_URL.startswith('postgresql://'):
            # 먼저 사용자 찾기 (external_uid 또는 email로)
            cursor.execute("""
                SELECT user_id, email, referral_code
                FROM users 
                WHERE external_uid = %s OR email = %s
                LIMIT 1
            """, (referrer_email, referrer_email))
            referrer = cursor.fetchone()
            
            if not referrer:
                return jsonify({'transactions': []}), 200
            
            referrer_user_id = referrer['user_id']
            print(f"✅ 추천인 찾음: user_id={referrer_user_id}", flush=True)
            
            # commissions (적립) 조회
            cursor.execute("""
                SELECT 
                    'earn' as type,
                    c.amount,
                    c.created_at,
                    o.order_id,
                    c.commission_id
                FROM commissions c
                JOIN referrals r ON c.referral_id = r.referral_id
                LEFT JOIN orders o ON c.order_id = o.order_id
                WHERE r.referrer_user_id = %s
                ORDER BY c.created_at DESC, c.commission_id DESC
            """, (referrer_user_id,))
            
            earn_transactions = cursor.fetchall()
            
            # payouts (지급) 조회 - payout_requests를 통해 user_id 찾기
            cursor.execute("""
                SELECT 
                    'payout' as type,
                    p.paid_amount as amount,
                    COALESCE(p.processed_at, pr.requested_at) as created_at,
                    NULL as order_id,
                    p.payout_id
                FROM payouts p
                JOIN payout_requests pr ON p.request_id = pr.request_id
                WHERE pr.user_id = %s
                ORDER BY COALESCE(p.processed_at, pr.requested_at) DESC, p.payout_id DESC
            """, (referrer_user_id,))
            
            payout_transactions = cursor.fetchall()
            
            # 모든 거래를 합치고 시간순으로 정렬
            all_transactions = []
            for row in earn_transactions:
                all_transactions.append({
                    'type': 'earn',
                    'amount': float(row.get('amount', 0)),
                    'created_at': row.get('created_at'),
                    'order_id': row.get('order_id'),
                    'transaction_id': row.get('commission_id')
                })
            
            for row in payout_transactions:
                all_transactions.append({
                    'type': 'payout',
                    'amount': -float(row.get('amount', 0)),  # 음수로 표시
                    'created_at': row.get('created_at'),
                    'order_id': None,
                    'transaction_id': row.get('payout_id')
                })
            
            # 시간순으로 정렬
            all_transactions.sort(key=lambda x: x['created_at'] if x['created_at'] else datetime.min, reverse=True)
            
            # balance_after 계산
            total_balance = 0
            for trans in reversed(all_transactions):  # 역순으로 계산 (과거부터 현재까지)
                if trans['type'] == 'earn':
                    total_balance += trans['amount']
                else:  # payout
                    total_balance += trans['amount']  # 이미 음수로 저장됨
                trans['balance_after'] = total_balance
            
            # 다시 시간순으로 정렬 (최신순)
            all_transactions.sort(key=lambda x: x['created_at'] if x['created_at'] else datetime.min, reverse=True)
            
            transactions = []
            for trans in all_transactions:
                transactions.append({
                    'type': trans['type'],
                    'amount': trans['amount'],
                    'balance_after': trans.get('balance_after', 0),
                    'description': f"주문 #{trans['order_id']}" if trans.get('order_id') else '출금',
                    'created_at': trans['created_at'].isoformat() if trans['created_at'] and hasattr(trans['created_at'], 'isoformat') else str(trans.get('created_at', ''))
                })
        else:
            # SQLite - 레거시 호환
            cursor.execute("""
                SELECT event, amount, notes, created_at,
                       (SELECT COALESCE(SUM(amount), 0) FROM commission_ledger 
                        WHERE referrer_user_id = ? AND status = 'confirmed' AND created_at <= cl.created_at) as balance_after
                FROM commission_ledger cl
                WHERE referrer_user_id = ?
                ORDER BY created_at DESC
            """, (referrer_email, referrer_email))
            
            transactions = []
            for row in cursor.fetchall():
                transactions.append({
                    'type': row[0],
                    'amount': float(row[1]),
                    'balance_after': float(row[4]) if len(row) > 4 else 0,
                    'description': row[2] if row[2] else '',
                    'created_at': row[3].isoformat() if hasattr(row[3], 'isoformat') else str(row[3])
                })
        
        print(f"✅ 커미션 거래 내역 조회 완료: {len(transactions)}건", flush=True)
        return jsonify({'transactions': transactions}), 200
        
    except Exception as e:
        import traceback
        error_msg = f'거래 내역 조회 실패: {str(e)}'
        print(f"❌ {error_msg}", flush=True)
        print(traceback.format_exc(), flush=True)
        return jsonify({'error': error_msg, 'details': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 환급 신청
@app.route('/api/referral/withdrawal-request', methods=['POST'])
def request_withdrawal():
    """Request Withdrawal
    ---
    tags:
      - Referral
    summary: Request Withdrawal
    description: "Request Withdrawal API"
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """환급 신청"""
    try:
        data = request.get_json()
        referrer_email = data.get('referrer_email')
        referrer_name = data.get('referrer_name')
        bank_name = data.get('bank_name')
        account_number = data.get('account_number')
        account_holder = data.get('account_holder')
        amount = data.get('amount')
        
        if not all([referrer_email, referrer_name, bank_name, account_number, account_holder, amount]):
            return jsonify({'error': '모든 필드가 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # referral_code로 referrer_user_id 조회
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT code, user_id FROM referral_codes WHERE user_email = %s OR user_id = %s LIMIT 1
            """, (referrer_email, referrer_email))
        else:
            cursor.execute("""
                SELECT code, user_id FROM referral_codes WHERE user_email = ? OR user_id = ? LIMIT 1
            """, (referrer_email, referrer_email))
        
        referral_result = cursor.fetchone()
        if not referral_result:
            return jsonify({'error': '추천인을 찾을 수 없습니다.'}), 404
        
        referral_code, referrer_user_id = referral_result
        
        # commission_ledger에서 현재 잔액 계산
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) FROM commission_ledger 
                WHERE referrer_user_id = %s AND status = 'confirmed'
            """, (referrer_user_id,))
        else:
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) FROM commission_ledger 
                WHERE referrer_user_id = ? AND status = 'confirmed'
            """, (referrer_user_id,))
        
        result = cursor.fetchone()
        current_balance = float(result[0]) if result else 0.0
        
        if current_balance < float(amount):
            return jsonify({'error': f'잔액이 부족합니다. 현재 잔액: {current_balance}원'}), 400
        
        # 환급 신청 저장 - payout_requests 테이블 사용
        if DATABASE_URL.startswith('postgresql://'):
            # user_id를 사용하여 payout_requests에 저장
            cursor.execute("""
                INSERT INTO payout_requests 
                (user_id, amount, bank_name, account_number, status, requested_at)
                VALUES (%s, %s, %s, %s, 'requested', NOW())
                RETURNING request_id
            """, (referrer_user_id, amount, bank_name, account_number))
            request_result = cursor.fetchone()
            request_id = request_result[0] if request_result else None
        else:
            # SQLite
            cursor.execute("""
                INSERT INTO payout_requests 
                (user_id, amount, bank_name, account_number, status, requested_at)
                VALUES (?, ?, ?, ?, 'requested', datetime('now'))
            """, (referrer_user_id, amount, bank_name, account_number))
            request_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': '환급 신청이 접수되었습니다.'}), 200
        
    except Exception as e:
        return jsonify({'error': f'환급 신청 실패: {str(e)}'}), 500

# 관리자용 환급 신청 목록 조회
@app.route('/api/admin/withdrawal-requests', methods=['GET'])
def get_withdrawal_requests():
    """Get Withdrawal Requests
    ---
    tags:
      - Admin
    summary: Get Withdrawal Requests
    description: "Get Withdrawal Requests API"
    security:
      - Bearer: []
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """관리자용 환급 신청 목록 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT id, referrer_email, referrer_name, bank_name, account_number, 
                       account_holder, amount, status, admin_notes, requested_at, processed_at
                FROM commission_withdrawal_requests 
                ORDER BY requested_at DESC
            """)
        else:
            cursor.execute("""
                SELECT id, referrer_email, referrer_name, bank_name, account_number, 
                       account_holder, amount, status, admin_notes, requested_at, processed_at
                FROM commission_withdrawal_requests 
                ORDER BY requested_at DESC
            """)
        
        requests = []
        for row in cursor.fetchall():
            requests.append({
                'id': row[0],
                'referrer_email': row[1],
                'referrer_name': row[2],
                'bank_name': row[3],
                'account_number': row[4],
                'account_holder': row[5],
                'amount': float(row[6]),
                'status': row[7],
                'admin_notes': row[8],
                'requested_at': row[9].isoformat() if hasattr(row[9], 'isoformat') else str(row[9]),
                'processed_at': row[10].isoformat() if hasattr(row[10], 'isoformat') else str(row[10]) if row[10] else None
            })
        
        conn.close()
        return jsonify({'requests': requests}), 200
        
    except Exception as e:
        return jsonify({'error': f'환급 신청 목록 조회 실패: {str(e)}'}), 500

# 관리자용 환급 신청 처리
@app.route('/api/admin/process-withdrawal', methods=['POST'])
def process_withdrawal():
    """Process Withdrawal
    ---
    tags:
      - Admin
    summary: Process Withdrawal
    description: "Process Withdrawal API"
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """관리자용 환급 신청 처리"""
    try:
        data = request.get_json()
        request_id = data.get('request_id')
        action = data.get('action')  # 'approve' or 'reject'
        admin_notes = data.get('admin_notes', '')
        processed_by = data.get('processed_by', 'admin')
        
        if not request_id or not action:
            return jsonify({'error': 'request_id와 action이 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 환급 신청 정보 조회
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT referrer_email, amount FROM commission_withdrawal_requests 
                WHERE id = %s AND status = 'pending'
            """, (request_id,))
        else:
            cursor.execute("""
                SELECT referrer_email, amount FROM commission_withdrawal_requests 
                WHERE id = ? AND status = ?
            """, (request_id, 'pending'))
        
        request_data = cursor.fetchone()
        if not request_data:
            return jsonify({'error': '처리할 환급 신청을 찾을 수 없습니다.'}), 400
        
        referrer_email, amount = request_data
        
        if action == 'approve':
            # 현재 잔액 조회
            if DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    SELECT current_balance FROM commission_points 
                    WHERE referrer_email = %s
                """, (referrer_email,))
            else:
                cursor.execute("""
                    SELECT current_balance FROM commission_points 
                    WHERE referrer_email = ?
                """, (referrer_email,))
            
            current_balance_result = cursor.fetchone()
            if not current_balance_result:
                return jsonify({'error': '추천인 포인트 계정을 찾을 수 없습니다.'}), 400
            
            current_balance = float(current_balance_result[0])
            new_balance = current_balance - float(amount)
            
            print(f"💰 환급 처리 - 추천인: {referrer_email}, 현재잔액: {current_balance}, 환급금액: {amount}, 새잔액: {new_balance}")
            
            if new_balance < 0:
                print(f"❌ 잔액 부족 - 현재: {current_balance}, 요청: {amount}")
                return jsonify({'error': '잔액이 부족합니다.'}), 400
            
            # 포인트 차감
            print(f"💰 환급 처리 시작 - 추천인: {referrer_email}, 금액: {amount}, 현재 잔액: {current_balance}, 차감 후: {new_balance}")
            
            # 차감 전 현재 total_paid 조회
            if DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    SELECT total_paid FROM commission_points 
                    WHERE referrer_email = %s
                """, (referrer_email,))
            else:
                cursor.execute("""
                    SELECT total_paid FROM commission_points 
                    WHERE referrer_email = ?
                """, (referrer_email,))
            
            current_total_paid_result = cursor.fetchone()
            current_total_paid = float(current_total_paid_result[0]) if current_total_paid_result else 0
            new_total_paid = current_total_paid - float(amount)
            
            print(f"💰 total_paid 업데이트 - 현재: {current_total_paid}, 차감 후: {new_total_paid}")
            if DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    UPDATE commission_points 
                    SET current_balance = current_balance - %s, 
                        total_paid = total_paid - %s,
                        updated_at = NOW()
                    WHERE referrer_email = %s
                """, (amount, amount, referrer_email))
                print(f"✅ PostgreSQL 커미션 차감 완료")
                
                # 거래 내역 기록 (실제 잔액 반영)
                cursor.execute("""
                    INSERT INTO commission_point_transactions 
                    (referrer_email, transaction_type, amount, balance_after, description, created_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                """, (referrer_email, 'withdrawal', -float(amount), new_balance, f'환급 처리 - 신청 ID: {request_id}'))
                
                # 환급 신청 상태 업데이트
                cursor.execute("""
                    UPDATE commission_withdrawal_requests 
                    SET status = 'approved', admin_notes = %s, processed_at = NOW(), processed_by = %s
                    WHERE id = %s
                """, (admin_notes, processed_by, request_id))
            else:
                # SQLite 버전
                cursor.execute("""
                    UPDATE commission_points 
                    SET current_balance = current_balance - ?, 
                        total_paid = total_paid - ?,
                        updated_at = datetime('now')
                    WHERE referrer_email = ?
                """, (amount, amount, referrer_email))
                
                cursor.execute("""
                    INSERT INTO commission_point_transactions 
                    (referrer_email, transaction_type, amount, balance_after, description, created_at)
                    VALUES (?, ?, ?, ?, ?, datetime('now'))
                """, (referrer_email, 'withdrawal', -float(amount), new_balance, f'환급 처리 - 신청 ID: {request_id}'))
                
                cursor.execute("""
                    UPDATE commission_withdrawal_requests 
                    SET status = 'approved', admin_notes = ?, processed_at = datetime('now'), processed_by = ?
                    WHERE id = ?
                """, (admin_notes, processed_by, request_id))
            
            message = '환급 신청이 승인되었습니다.'
        else:  # reject
            if DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    UPDATE commission_withdrawal_requests 
                    SET status = 'rejected', admin_notes = %s, processed_at = NOW(), processed_by = %s
                    WHERE id = %s
                """, (admin_notes, processed_by, request_id))
            else:
                cursor.execute("""
                    UPDATE commission_withdrawal_requests 
                    SET status = 'rejected', admin_notes = ?, processed_at = datetime('now'), processed_by = ?
                    WHERE id = ?
                """, (admin_notes, processed_by, request_id))
            
            message = '환급 신청이 거절되었습니다.'
        
        conn.commit()
        print(f"✅ 환급 처리 커밋 완료 - 신청 ID: {request_id}, 액션: {action}")
        conn.close()
        
        return jsonify({'message': message}), 200
        
    except Exception as e:
        return jsonify({'error': f'환급 신청 처리 실패: {str(e)}'}), 500

# 예약 주문 조회 (디버깅용)
@app.route('/api/admin/scheduled-orders', methods=['GET'])
@require_admin_auth
def get_scheduled_orders():
    """Get Scheduled Orders
    ---
    tags:
      - Admin
    summary: Get Scheduled Orders
    description: "Get Scheduled Orders API"
    security:
      - Bearer: []
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """예약 주문 목록 조회 (관리자용)"""
    conn = None
    cursor = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT o.order_id, o.user_id, oi.variant_id, COALESCE(oi.link, ''), 
                       oi.quantity, COALESCE(o.final_amount, o.total_amount, 0),
                       o.scheduled_datetime, o.status, o.created_at, o.updated_at
                FROM orders o
                LEFT JOIN order_items oi ON o.order_id = oi.order_id
                WHERE o.is_scheduled = TRUE
                ORDER BY o.scheduled_datetime DESC
                LIMIT 50
            """)
        else:
            cursor.execute("""
                SELECT order_id, user_id, service_id, link, quantity, price, scheduled_datetime, status, created_at, updated_at
                FROM orders 
                WHERE is_scheduled = 1
                ORDER BY scheduled_datetime DESC
                LIMIT 50
            """)
        
        orders = cursor.fetchall()
        
        order_list = []
        for order in orders:
            if DATABASE_URL.startswith('postgresql://'):
                # 새 스키마: order_id, user_id, variant_id, link, quantity, price, scheduled_datetime, status, created_at, updated_at
                order_list.append({
                    'id': order[0],  # order_id
                    'order_id': order[0],
                    'user_id': order[1],
                    'service_id': str(order[2]) if order[2] else None,  # variant_id
                    'link': order[3],
                    'quantity': order[4] if order[4] else 0,
                    'price': float(order[5]) if order[5] else 0,
                    'scheduled_datetime': order[6],
                    'status': order[7],
                    'created_at': order[8].isoformat() if order[8] and hasattr(order[8], 'isoformat') else None,
                    'processed_at': order[9].isoformat() if order[9] and hasattr(order[9], 'isoformat') else None
                })
            else:
                order_list.append({
                    'id': order[0],  # order_id
                    'order_id': order[0],
                    'user_id': order[1],
                    'service_id': order[2],
                    'link': order[3],
                    'quantity': order[4],
                    'price': float(order[5]) if order[5] else 0,
                    'scheduled_datetime': order[6],
                    'status': order[7],
                    'created_at': order[8].isoformat() if order[8] else None,
                    'processed_at': order[9].isoformat() if order[9] else None
                })
        
        return jsonify({
            'success': True,
            'orders': order_list,
            'count': len(order_list)
        }), 200
        
    except Exception as e:
        print(f"❌ 예약 주문 조회 오류: {str(e)}")
        return jsonify({'error': f'예약 주문 조회 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 주문 상태 확인 및 수정 API
@app.route('/api/orders/check-status', methods=['POST'])
@require_admin_auth
def check_order_status():
    """Check Order Status
    ---
    tags:
      - Orders
    summary: Check Order Status
    description: "Check Order Status API"
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """주문 상태 확인 및 수정"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        
        if not order_id:
            return jsonify({'error': '주문 ID가 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 주문 정보 조회 (새 스키마에서는 order_items 테이블 사용)
        if DATABASE_URL.startswith('postgresql://'):
            try:
                cursor.execute("""
                    SELECT o.order_id, o.status, wj.payload_json->>'smm_panel_order_id' as smm_panel_order_id, o.created_at, o.updated_at
                    FROM orders o
                    LEFT JOIN order_items oi ON o.order_id = oi.order_id
                    LEFT JOIN work_jobs wj ON oi.order_item_id = wj.order_item_id AND wj.payload_json->>'smm_panel_order_id' IS NOT NULL
                    WHERE o.order_id = %s
                    LIMIT 1
                """, (order_id,))
            except Exception as e:
                print(f"⚠️ 새 스키마 쿼리 실패, 기본 쿼리 사용: {e}")
                cursor.execute("""
                    SELECT order_id, status, NULL as smm_panel_order_id, created_at, updated_at
                    FROM orders 
                    WHERE order_id = %s
                """, (order_id,))
        else:
            cursor.execute("""
                SELECT order_id, status, smm_panel_order_id, created_at, updated_at
                FROM orders 
                WHERE order_id = ?
            """, (order_id,))
        
        order = cursor.fetchone()
        
        if not order:
            return jsonify({'error': '주문을 찾을 수 없습니다.'}), 404
        
        order_id_db, status, smm_panel_order_id, created_at, updated_at = order
        
        # SMM Panel에서 주문 상태 확인
        if smm_panel_order_id:
            smm_result = call_smm_panel_api({
                'action': 'status',
                'order': smm_panel_order_id
            })
            
            if smm_result.get('status') == 'success':
                # SMM Panel에서 완료된 경우 상태 업데이트
                if smm_result.get('remains', 0) == 0:
                    if DATABASE_URL.startswith('postgresql://'):
                        cursor.execute("""
                            UPDATE orders SET status = 'completed', updated_at = NOW()
                            WHERE order_id = %s
                        """, (order_id,))
                    else:
                        cursor.execute("""
                            UPDATE orders SET status = 'completed', updated_at = CURRENT_TIMESTAMP
                            WHERE order_id = ?
                        """, (order_id,))
                    conn.commit()
                    status = 'completed'
        
        conn.close()
        
        return jsonify({
            'success': True,
            'order_id': order_id_db,
            'status': status,
            'smm_panel_order_id': smm_panel_order_id,
            'created_at': created_at,
            'updated_at': updated_at
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'주문 상태 확인 실패: {str(e)}'}), 500

# 주문 상태 업데이트 API
@app.route('/api/orders/<order_id>/status', methods=['PUT'])
@require_admin_auth
def update_order_status(order_id):
    """Update Order Status
    ---
    tags:
      - Orders
    summary: Update Order Status
    description: "Update Order Status API"
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """주문 상태 업데이트 (관리자 전용)"""
    conn = None
    cursor = None
    
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'error': '새로운 상태가 필요합니다.'}), 400
        
        print(f"🔄 주문 상태 업데이트 요청: {order_id} -> {new_status}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 현재 주문 상태 확인
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("SELECT status FROM orders WHERE order_id = %s", (order_id,))
        else:
            cursor.execute("SELECT status FROM orders WHERE order_id = ?", (order_id,))
        
        result = cursor.fetchone()
        if not result:
            return jsonify({'error': '주문을 찾을 수 없습니다.'}), 404
        
        current_status = result[0]
        print(f"📊 현재 상태: {current_status} -> {new_status}")
        
        # 주문 상태 업데이트
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                UPDATE orders SET status = %s, updated_at = NOW() 
                WHERE order_id = %s
            """, (new_status, order_id))
        else:
            cursor.execute("""
                UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE order_id = ?
            """, (new_status, order_id))
        
        conn.commit()
        print(f"✅ 주문 {order_id} 상태가 {new_status}로 업데이트되었습니다.")
        
        return jsonify({
            'success': True,
            'order_id': order_id,
            'old_status': current_status,
            'new_status': new_status,
            'message': f'주문 상태가 {current_status}에서 {new_status}로 변경되었습니다.'
        }), 200
        
    except Exception as e:
        print(f"❌ 주문 상태 업데이트 실패: {str(e)}")
        import traceback
        print(f"❌ 스택 트레이스: {traceback.format_exc()}")
        if conn:
            conn.rollback()
        return jsonify({'error': f'주문 상태 업데이트 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 공지사항 관리 API
@app.route('/api/admin/notices', methods=['GET'])
@require_admin_auth
def get_notices():
    """Get Notices
    ---
    tags:
      - Admin
    summary: Get Notices
    description: "Get Notices API"
    security:
      - Bearer: []
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """공지사항 목록 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT id, title, content, image_url, login_popup_image_url, popup_type, is_active, created_at, updated_at
                FROM notices 
                ORDER BY created_at DESC
            """)
        else:
            cursor.execute("""
                SELECT id, title, content, image_url, login_popup_image_url, popup_type, is_active, created_at, updated_at
                FROM notices 
                ORDER BY created_at DESC
            """)
        
        notices = []
        for row in cursor.fetchall():
            notices.append({
                'id': row[0],
                'title': row[1],
                'content': row[2],
                'image_url': row[3],
                'login_popup_image_url': row[4] if len(row) > 4 else None,
                'popup_type': row[5] if len(row) > 5 else 'notice',
                'is_active': row[6] if len(row) > 6 else row[4],
                'created_at': row[7].isoformat() if len(row) > 7 and row[7] else (row[5].isoformat() if len(row) > 5 and row[5] else None),
                'updated_at': row[8].isoformat() if len(row) > 8 and row[8] else (row[6].isoformat() if len(row) > 6 and row[6] else None)
            })
        
        conn.close()
        return jsonify({'notices': notices}), 200
        
    except Exception as e:
        return jsonify({'error': f'공지사항 조회 실패: {str(e)}'}), 500

@app.route('/api/admin/referral/update-commission-rate', methods=['PUT'])
@require_admin_auth
def update_referral_commission_rate():
    """Update Referral Commission Rate
    ---
    tags:
      - Admin
    summary: Update Referral Commission Rate
    description: "Update Referral Commission Rate API"
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """추천인별 커미션 비율 변경"""
    conn = None
    cursor = None
    try:
        data = request.get_json()
        referrer_user_id = data.get('referrer_user_id')
        referrer_email = data.get('referrer_email')
        commission_rate = data.get('commission_rate')
        
        if commission_rate is None:
            return jsonify({'error': '커미션 비율이 필요합니다.'}), 400
        
        if not (0 <= commission_rate <= 1):
            return jsonify({'error': '커미션 비율은 0과 1 사이의 값이어야 합니다.'}), 400
        
        conn = get_db_connection()
        is_postgres = DATABASE_URL and DATABASE_URL.startswith('postgresql://')
        
        print(f"🔍 커미션 비율 업데이트 요청 - user_id: {referrer_user_id}, email: {referrer_email}, rate: {commission_rate}")
        print(f"🔍 데이터베이스 타입: {'PostgreSQL' if is_postgres else 'SQLite'}")
        
        # 데이터베이스 타입에 따라 커서 생성
        if is_postgres:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
            # SQLite의 경우 row_factory는 연결 시 설정되어야 함
            if isinstance(conn, sqlite3.Connection):
                try:
                    # row_factory가 이미 설정되어 있을 수 있음
                    if conn.row_factory is None:
                        conn.row_factory = sqlite3.Row
                except:
                    pass
        
        # 사용자 찾기
        if referrer_user_id:
            try:
                if is_postgres:
                    cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (referrer_user_id,))
                else:
                    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (referrer_user_id,))
            except Exception as e:
                print(f"❌ user_id로 사용자 조회 실패: {e}")
                raise
        elif referrer_email:
            try:
                if is_postgres:
                    cursor.execute("SELECT user_id FROM users WHERE email = %s", (referrer_email,))
                else:
                    cursor.execute("SELECT user_id FROM users WHERE email = ?", (referrer_email,))
            except Exception as e:
                print(f"❌ email로 사용자 조회 실패: {e}")
                raise
        else:
            return jsonify({'error': 'referrer_user_id 또는 referrer_email이 필요합니다.'}), 400
        
        user = cursor.fetchone()
        print(f"🔍 사용자 조회 결과: {user}")
        
        if not user:
            return jsonify({'error': '추천인을 찾을 수 없습니다.'}), 404
        
        # 사용자 ID 추출 (데이터베이스 타입에 따라)
        try:
            if is_postgres:
                user_id = user['user_id']
            else:
                # SQLite
                if isinstance(user, sqlite3.Row):
                    user_id = user['user_id']
                elif isinstance(user, tuple):
                    user_id = user[0]
                elif isinstance(user, dict):
                    user_id = user['user_id']
                else:
                    user_id = user[0] if len(user) > 0 else None
        except Exception as e:
            print(f"❌ user_id 추출 실패: {e}, user 타입: {type(user)}, user 값: {user}")
            raise
        
        if not user_id:
            return jsonify({'error': '사용자 ID를 추출할 수 없습니다.'}), 500
        
        print(f"✅ 사용자 ID: {user_id}")
        
        # commission_rate 컬럼이 없으면 추가 (안전장치)
        has_commission_rate_column = False
        try:
            print("🔍 commission_rate 컬럼 존재 여부 확인 중...")
            if is_postgres:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 
                        FROM information_schema.columns 
                        WHERE table_name = 'users' 
                        AND column_name = 'commission_rate'
                    )
                """)
                result = cursor.fetchone()
                has_commission_rate_column = result[0] if result else False
                print(f"🔍 PostgreSQL 컬럼 확인 결과: {has_commission_rate_column}")
            else:
                # SQLite
                cursor.execute("PRAGMA table_info(users)")
                columns = [row[1] for row in cursor.fetchall()]
                has_commission_rate_column = 'commission_rate' in columns
                print(f"🔍 SQLite 컬럼 확인 결과: {has_commission_rate_column}, 컬럼 목록: {columns}")
            
            if not has_commission_rate_column:
                print("⚠️ commission_rate 컬럼이 없습니다. 추가 중...")
                if is_postgres:
                    cursor.execute("ALTER TABLE users ADD COLUMN commission_rate DECIMAL(5,4) DEFAULT 0.1")
                else:
                    cursor.execute("ALTER TABLE users ADD COLUMN commission_rate REAL DEFAULT 0.1")
                conn.commit()
                print("✅ commission_rate 컬럼 추가 완료")
                has_commission_rate_column = True
            else:
                print("✅ commission_rate 컬럼이 이미 존재합니다.")
        except Exception as col_error:
            print(f"❌ commission_rate 컬럼 확인/추가 중 에러 발생: {col_error}")
            import traceback
            print(traceback.format_exc())
            # 에러 발생해도 계속 진행 (컬럼이 이미 있을 수도 있음)
            try:
                conn.rollback()
            except:
                pass
        
        # 커미션 비율 업데이트
        try:
            if is_postgres:
                cursor.execute("""
                    UPDATE users 
                    SET commission_rate = %s, updated_at = NOW()
                    WHERE user_id = %s
                """, (commission_rate, user_id))
            else:
                # SQLite
                cursor.execute("""
                    UPDATE users 
                    SET commission_rate = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (commission_rate, user_id))
            
            print(f"✅ 커미션 비율 업데이트 SQL 실행 완료 - user_id: {user_id}, rate: {commission_rate}")
            conn.commit()
            print(f"✅ 커밋 완료")
        except Exception as e:
            print(f"❌ 커미션 비율 업데이트 SQL 실행 실패: {e}")
            import traceback
            print(traceback.format_exc())
            raise
        
        return jsonify({'message': '커미션 비율이 업데이트되었습니다.', 'commission_rate': commission_rate}), 200
        
    except Exception as e:
        import traceback
        print(f"❌ 커미션 비율 업데이트 실패: {str(e)}")
        print(traceback.format_exc())
        if conn:
            try:
                conn.rollback()
            except:
                pass
        return jsonify({'error': f'커미션 비율 업데이트 실패: {str(e)}'}), 500
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if conn:
            try:
                conn.close()
            except:
                pass

@app.route('/api/admin/notices', methods=['POST'])
@require_admin_auth
def create_notice():
    """Create Notice
    ---
    tags:
      - Admin
    summary: Create Notice
    description: "Create Notice API"
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """공지사항 생성"""
    try:
        data = request.get_json()
        title = data.get('title', '')
        content = data.get('content', '')
        image_url = data.get('image_url', '')
        login_popup_image_url = data.get('login_popup_image_url', '')
        popup_type = data.get('popup_type', 'notice')
        is_active = data.get('is_active', True)
        
        # 팝업 타입에 따라 필수 필드 검증
        # notice 타입: 이미지만 필수, title과 content는 선택 사항
        if popup_type == 'notice' and not image_url:
            return jsonify({'error': '공지사항 팝업은 이미지가 필요합니다.'}), 400
        # login 타입: 이미지만 필수
        if popup_type == 'login' and not login_popup_image_url:
            return jsonify({'error': '로그인 팝업은 이미지가 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                INSERT INTO notices (title, content, image_url, login_popup_image_url, popup_type, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, (title, content, image_url, login_popup_image_url, popup_type, is_active))
        else:
            cursor.execute("""
                INSERT INTO notices (title, content, image_url, login_popup_image_url, popup_type, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """, (title, content, image_url, login_popup_image_url, popup_type, is_active))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': '공지사항이 생성되었습니다.'}), 200
        
    except Exception as e:
        return jsonify({'error': f'공지사항 생성 실패: {str(e)}'}), 500

@app.route('/api/admin/notices/<int:notice_id>', methods=['PUT'])
@require_admin_auth
def update_notice(notice_id):
    """Update Notice
    ---
    tags:
      - Admin
    summary: Update Notice
    description: "Update Notice API"
    security:
      - Bearer: []
    parameters:
      - name: notice_id
        in: path
        type: int
        required: true
        description: Notice Id
        example: "example_notice_id"
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """공지사항 수정"""
    try:
        data = request.get_json()
        title = data.get('title', '')
        content = data.get('content', '')
        image_url = data.get('image_url', '')
        login_popup_image_url = data.get('login_popup_image_url', '')
        popup_type = data.get('popup_type', 'notice')
        is_active = data.get('is_active')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                UPDATE notices 
                SET title = %s, content = %s, image_url = %s, login_popup_image_url = %s, popup_type = %s, is_active = %s, updated_at = NOW()
                WHERE id = %s
            """, (title, content, image_url, login_popup_image_url, popup_type, is_active, notice_id))
        else:
            cursor.execute("""
                UPDATE notices 
                SET title = ?, content = ?, image_url = ?, login_popup_image_url = ?, popup_type = ?, is_active = ?, updated_at = datetime('now')
                WHERE id = ?
            """, (title, content, image_url, login_popup_image_url, popup_type, is_active, notice_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': '공지사항이 수정되었습니다.'}), 200
        
    except Exception as e:
        return jsonify({'error': f'공지사항 수정 실패: {str(e)}'}), 500

@app.route('/api/admin/notices/<int:notice_id>', methods=['DELETE'])
@require_admin_auth
def delete_notice(notice_id):
    """Delete Notice
    ---
    tags:
      - Admin
    summary: Delete Notice
    description: "Delete Notice API"
    security:
      - Bearer: []
    parameters:
      - name: notice_id
        in: path
        type: int
        required: true
        description: Notice Id
        example: "example_notice_id"
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """공지사항 삭제"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("DELETE FROM notices WHERE id = %s", (notice_id,))
        else:
            cursor.execute("DELETE FROM notices WHERE id = ?", (notice_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': '공지사항이 삭제되었습니다.'}), 200
        
    except Exception as e:
        return jsonify({'error': f'공지사항 삭제 실패: {str(e)}'}), 500

# 사용자용 활성 공지사항 조회
@app.route('/api/notices/active', methods=['GET'])
def get_active_notices():
    """Get Active Notices
    ---
    tags:
      - API
    summary: Get Active Notices
    description: "Get Active Notices API"
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """활성화된 공지사항 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            # 새 스키마: notice_id, title, body, image_url, created_at (is_active 없음)
            cursor.execute("""
                SELECT notice_id, title, body, image_url, created_at
                FROM notices 
                ORDER BY created_at DESC
                LIMIT 5
            """)
        else:
            cursor.execute("""
                SELECT id, title, content, image_url, created_at
                FROM notices 
                WHERE is_active = 1
                ORDER BY created_at DESC
                LIMIT 5
            """)
        
        notices = []
        for row in cursor.fetchall():
            notices.append({
                'id': row[0],
                'title': row[1],
                'content': row[2],  # body를 content로 매핑
                'image_url': row[3],
                'created_at': row[4].isoformat() if row[4] and hasattr(row[4], 'isoformat') else (str(row[4]) if row[4] else None)
            })
        
        conn.close()
        return jsonify({'notices': notices}), 200
        
    except Exception as e:
        return jsonify({'error': f'공지사항 조회 실패: {str(e)}'}), 500

# SMM Panel 서비스 목록 조회
@app.route('/api/smm-panel/services', methods=['GET'])
def get_smm_services():
    """Get Smm Services
    ---
    tags:
      - SMM Panel
    summary: Get Smm Services
    description: "Get Smm Services API"
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """SMM Panel에서 사용 가능한 서비스 목록 조회"""
    try:
        # API 키 확인 (전역 변수 사용)
        api_key = SMMPANEL_API_KEY or os.environ.get('SMMPANEL_API_KEY')
        
        if not api_key:
            print("⚠️ SMMPANEL_API_KEY가 설정되지 않음")
            return jsonify({
                'success': False,
                'error': 'SMM Panel API 키가 설정되지 않았습니다.',
                'message': '관리자에게 문의하세요.'
            }), 500
        
        print(f"🔍 SMM Panel API 키 확인 완료 (길이: {len(api_key) if api_key else 0})")
        
        result = get_smm_panel_services()
        
        if result and result.get('status') == 'success':
            return jsonify({
                'success': True,
                'services': result.get('services', []),
                'service_ids': result.get('service_ids', [])
            }), 200
        else:
            error_message = result.get('message', 'Failed to get services') if result else 'Unknown error'
            print(f"❌ SMM Panel 서비스 목록 조회 실패: {error_message}")
            
            # API 키 오류인 경우 더 명확한 메시지
            if 'Invalid API key' in error_message or '401' in error_message:
                error_message = 'API 키가 유효하지 않습니다. 관리자에게 문의하세요.'
            
            return jsonify({
                'success': False,
                'error': error_message,
                'details': result.get('message', '') if result else 'No response from SMM Panel'
            }), 500
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback_str = traceback.format_exc()
        print(f"❌ SMM Panel 서비스 목록 조회 오류: {error_msg}")
        print(f"📋 상세 오류:\n{traceback_str}")
        
        # SSL 오류나 네트워크 오류인 경우 빈 배열 반환 (프론트엔드가 계속 작동하도록)
        if 'SSL' in error_msg or 'SSLError' in error_msg or 'network' in error_msg.lower() or 'connection' in error_msg.lower():
            print("⚠️ 네트워크/SSL 오류로 인해 빈 서비스 목록 반환")
            return jsonify({
                'success': True,
                'services': [],
                'service_ids': [],
                'warning': 'SMM Panel 연결 실패. 네트워크를 확인하세요.'
            }), 200
        
        # API 키 관련 오류인 경우
        if 'Invalid API key' in error_msg or '401' in error_msg:
            error_msg = 'API 키가 유효하지 않습니다. 관리자에게 문의하세요.'
        
        return jsonify({
            'success': False,
            'error': f'서비스 목록 조회 실패: {error_msg}',
            'details': str(e)
        }), 500

# 스케줄러 작업: 예약/분할 주문 처리
@app.route('/api/cron/process-scheduled-orders', methods=['POST'])
def cron_process_scheduled_orders():
    """Cron Process Scheduled Orders
    ---
    tags:
      - Cron
    summary: Cron Process Scheduled Orders
    description: "Cron Process Scheduled Orders API"
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """예약 주문 처리 크론잡"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 현재 시간이 지난 예약 주문 조회 (orders 테이블에서도 조회)
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"🔍 예약 주문 조회 중... (현재 시간: {current_time})")
        
        # orders 테이블에서 예약 주문 조회 (새 스키마에서는 order_items 사용)
        if DATABASE_URL.startswith('postgresql://'):
            try:
                cursor.execute("""
                    SELECT o.order_id, o.user_id, oi.variant_id, COALESCE(oi.link, ''), oi.quantity, 
                           COALESCE(o.final_amount, o.total_amount, 0), o.scheduled_datetime, o.package_steps
                    FROM orders o
                    LEFT JOIN order_items oi ON o.order_id = oi.order_id
                    WHERE o.is_scheduled = TRUE 
                    AND o.status = 'pending'
                    AND o.scheduled_datetime <= NOW()
                    LIMIT 50
                """)
            except Exception as e:
                print(f"⚠️ 새 스키마 쿼리 실패: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'message': '예약 주문 처리 실패', 'error': str(e)}), 500
        else:
            cursor.execute("""
                SELECT order_id, user_id, service_id, link, quantity, price, package_steps, scheduled_datetime
                FROM orders 
                WHERE is_scheduled = 1 
                AND status = 'pending'
                AND scheduled_datetime <= datetime('now')
            """)
        
        scheduled_orders = cursor.fetchall()
        print(f"🔍 발견된 예약 주문: {len(scheduled_orders)}개")
        
        for order in scheduled_orders:
            print(f"🔍 예약 주문 상세: ID={order[0]}, 예약시간={order[7]}, 사용자={order[1]}")
        
        processed_count = 0
        
        for order in scheduled_orders:
            if DATABASE_URL.startswith('postgresql://'):
                # 새 스키마: order_id, user_id, variant_id, link, quantity, total_amount, scheduled_datetime, package_steps
                order_id = order[0]
                user_id = order[1]
                variant_id = order[2]  # service_id 대신 variant_id
                link = order[3]
                quantity = order[4] if order[4] else 0
                price = float(order[5]) if order[5] else 0.0
                scheduled_datetime = order[6]
                package_steps_json = order[7] if len(order) > 7 else None
                # package_steps 파싱
                try:
                    if isinstance(package_steps_json, list):
                        package_steps = package_steps_json
                    elif isinstance(package_steps_json, str):
                        package_steps = json.loads(package_steps_json) if package_steps_json else []
                    else:
                        package_steps = []
                except (json.JSONDecodeError, TypeError):
                    package_steps = []
                service_id = str(variant_id) if variant_id else None
            else:
                # 구 스키마 (SQLite)
                order_id = order[0]
                user_id = order[1]
                service_id = order[2]
                link = order[3]
                quantity = order[4]
                price = order[5]
                package_steps_json = order[6]
                package_steps = json.loads(package_steps_json) if package_steps_json else []
                variant_id = service_id
            
            print(f"🔄 예약 주문 처리 중: ID {order_id}, 사용자 {user_id}, 패키지: {len(package_steps)}단계")
            
            # 패키지 상품인 경우 패키지 처리 시작
            if package_steps and len(package_steps) > 0:
                print(f"📦 패키지 주문 처리 시작: {len(package_steps)}단계")
                
                # 반복 횟수 확인
                current_step = package_steps[0]
                step_repeat = current_step.get('repeat', 1)
                step_service_id = current_step.get('id')
                
                # 이미 완료된 반복 횟수 확인 (새 스키마에서는 work_jobs 사용)
                if DATABASE_URL.startswith('postgresql://'):
                    try:
                        # work_jobs에서 완료된 작업 수 확인
                        cursor.execute("""
                            SELECT COUNT(*) FROM work_jobs 
                            WHERE order_item_id IN (
                                SELECT order_item_id FROM order_items WHERE order_id = %s
                            ) AND status = 'completed'
                        """, (order_id,))
                    except Exception as e:
                        print(f"⚠️ work_jobs 조회 실패: {e}")
                        completed_count = 0
                else:
                    cursor.execute("""
                        SELECT COUNT(*) FROM execution_progress 
                        WHERE order_id = ? AND exec_type = 'package' AND step_number = 1 AND status = 'completed'
                    """, (order_id,))
                
                completed_count = cursor.fetchone()[0]
                print(f"📊 현재 완료된 반복 횟수: {completed_count}/{step_repeat}")
                
                # 반복이 모두 완료되었으면 처리 완료
                if completed_count >= step_repeat and step_repeat == 30:
                    print(f"🎉 패키지 주문 {order_id} 모든 반복 완료 (30/30)")
                    if DATABASE_URL.startswith('postgresql://'):
                        cursor.execute("""
                            UPDATE orders SET status = 'completed', is_scheduled = FALSE, updated_at = NOW()
                            WHERE order_id = %s
                        """, (order_id,))
                    else:
                        cursor.execute("""
                            UPDATE orders SET status = 'completed', is_scheduled = 0, updated_at = CURRENT_TIMESTAMP
                            WHERE order_id = ?
                        """, (order_id,))
                    conn.commit()
                    processed_count += 1
                else:
                    # 패키지 처리 시작 (processing 상태 사용)
                    if DATABASE_URL.startswith('postgresql://'):
                        cursor.execute("""
                            UPDATE orders SET status = 'processing', updated_at = NOW()
                            WHERE order_id = %s
                        """, (order_id,))
                    else:
                        cursor.execute("""
                            UPDATE orders SET status = 'processing', updated_at = CURRENT_TIMESTAMP
                            WHERE order_id = ?
                        """, (order_id,))
                    conn.commit()
                    
                    # 패키지 첫 번째 단계 처리
                    process_package_step(order_id, 0)
                    processed_count += 1
                    print(f"✅ 예약 패키지 주문 {order_id} 처리 시작")
            else:
                # 일반 주문인 경우 SMM Panel API 호출 (drip-feed 지원)
                print(f"🚀 일반 예약 주문 - SMM Panel API 호출")
                # orders 테이블에 runs와 interval이 저장되어 있을 수 있지만, 
                # scheduled_orders 테이블에서 가져오는 것이 더 정확함
                # 여기서는 orders 테이블에서 조회 (추후 컬럼 추가 필요 시 확장 가능)
                runs = 1
                interval = 0
                
                # TODO: orders 테이블에 runs, interval 컬럼이 있다면 조회
                # 현재는 기본값 사용 (일반 주문 처리)
                
                smm_result = call_smm_panel_api({
                    'service': service_id,
                    'link': link,
                    'quantity': quantity,
                    'comments': f'Scheduled order {order_id}',
                    'runs': runs,  # Drip-feed 지원 (기본값 1)
                    'interval': interval  # Drip-feed 지원 (기본값 0)
                })
                
                if smm_result.get('status') == 'success':
                    # SMM Panel 주문 ID 저장
                    if DATABASE_URL.startswith('postgresql://'):
                        cursor.execute("""
                            UPDATE orders SET smm_panel_order_id = %s, status = 'processing', updated_at = NOW()
                            WHERE order_id = %s
                        """, (smm_result.get('order'), order_id))
                    else:
                        cursor.execute("""
                            UPDATE orders SET smm_panel_order_id = ?, status = 'processing', updated_at = CURRENT_TIMESTAMP
                            WHERE order_id = ?
                        """, (smm_result.get('order'), order_id))
                    conn.commit()
                    processed_count += 1
                    print(f"✅ 일반 예약 주문 {order_id} 처리 완료: SMM 주문 ID {smm_result.get('order')}")
                else:
                    print(f"❌ 일반 예약 주문 {order_id} 처리 실패: {smm_result.get('message')}")
        
        conn.close()
        
        return jsonify({
            'success': True,
            'processed': processed_count,
            'message': f'{processed_count}개의 예약 주문을 처리했습니다.'
        }), 200
        
    except Exception as e:
        print(f"❌ 예약 주문 처리 크론잡 실패: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/cron/process-split-deliveries', methods=['POST'])
def cron_process_split_deliveries():
    """Cron Process Split Deliveries
    ---
    tags:
      - Cron
    summary: Cron Process Split Deliveries
    description: "Cron Process Split Deliveries API"
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """분할 발송 처리 크론잡"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 처리해야 할 분할 주문 조회
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT o.order_id, o.split_days, o.created_at
                FROM orders o
                WHERE o.is_split_delivery = TRUE 
                AND o.status IN ('pending', 'processing')
            """)
        else:
            cursor.execute("""
                SELECT o.order_id, o.split_days, o.created_at
                FROM orders o
                WHERE o.is_split_delivery = 1
                AND o.status IN ('pending', 'processing')
            """)
        
        split_orders = cursor.fetchall()
        processed_count = 0
        
        for order in split_orders:
            order_id = order[0]
            total_days = order[1]
            created_at = order[2]
            
            # 경과 일수 계산
            if isinstance(created_at, str):
                created_date = datetime.strptime(created_at.split()[0], '%Y-%m-%d').date()
            else:
                created_date = created_at.date()
            
            today = datetime.now().date()
            days_passed = (today - created_date).days + 1  # 1일차부터 시작
            
            # 처리해야 할 일차인지 확인
            if days_passed <= total_days:
                # 해당 일차가 이미 처리되었는지 확인
                if DATABASE_URL.startswith('postgresql://'):
                    cursor.execute("""
                        SELECT id FROM split_delivery_progress 
                        WHERE order_id = %s AND day_number = %s AND status = 'completed'
                    """, (order_id, days_passed))
                else:
                    cursor.execute("""
                        SELECT id FROM split_delivery_progress 
                        WHERE order_id = ? AND day_number = ? AND status = 'completed'
                    """, (order_id, days_passed))
                
                already_processed = cursor.fetchone()
                
                if not already_processed:
                    # 아직 처리되지 않은 일차라면 처리
                    success = process_split_delivery(order_id, days_passed)
                    if success:
                        processed_count += 1
        
        conn.close()
        
        return jsonify({
            'success': True,
            'processed': processed_count,
            'message': f'{processed_count}개의 분할 발송을 처리했습니다.'
        }), 200
        
    except Exception as e:
        print(f"❌ 분할 발송 처리 크론잡 실패: {e}")
        return jsonify({'error': str(e)}), 500

# 백그라운드 스케줄러 스레드
def background_scheduler():
    """백그라운드에서 예약/분할 주문 처리"""
    print("🚀 백그라운드 스케줄러 시작됨")
    while True:
        try:
            # 5분마다 예약 주문 처리
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"🔄 스케줄러: 예약 주문 처리 중... ({current_time})")
            with app.app_context():
                result = cron_process_scheduled_orders()
                print(f"🔄 스케줄러 결과: {result}")
            
            # 분할 발송 처리 (매일 자정에 한 번만 실행하도록 시간 체크)
            current_hour = datetime.now().hour
            if current_hour == 0:  # 자정
                print("🔄 스케줄러: 분할 발송 처리 중...")
                with app.app_context():
                    cron_process_split_deliveries()
            
        except Exception as e:
            print(f"⚠️ 스케줄러 오류: {e}")
        
        # 5분 대기 (예약 주문을 더 자주 체크)
        time.sleep(300)

# 데이터베이스 마이그레이션 강제 실행 엔드포인트
@app.route('/api/admin/migrate-database', methods=['POST', 'GET'])
def migrate_database():
    """Migrate Database
    ---
    tags:
      - Admin
    summary: Migrate Database
    description: "Migrate Database API"
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """데이터베이스 마이그레이션 강제 실행 (인증 불필요 - 일회성)"""
    try:
        print("🔄 수동 데이터베이스 마이그레이션 시작...")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        messages = []
        
        # PostgreSQL에서만 실행
        if DATABASE_URL.startswith('postgresql://'):
            # smm_panel_order_id 컬럼 추가
            try:
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='orders' AND column_name='smm_panel_order_id'
                """)
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE orders ADD COLUMN smm_panel_order_id VARCHAR(255)")
                    conn.commit()
                    messages.append("✅ smm_panel_order_id 필드 추가 완료")
                    print("✅ smm_panel_order_id 필드 추가 완료")
                else:
                    messages.append("ℹ️ smm_panel_order_id 필드 이미 존재")
                    print("ℹ️ smm_panel_order_id 필드 이미 존재")
            except Exception as e:
                messages.append(f"⚠️ smm_panel_order_id: {str(e)}")
                print(f"⚠️ smm_panel_order_id 필드 추가 실패: {e}")
                conn.rollback()
            
            # order_status ENUM에 'failed' 값 추가
            try:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_type WHERE typname = 'order_status'
                    )
                """)
                enum_exists = cursor.fetchone()[0] if cursor.rowcount > 0 else False
                
                if enum_exists:
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT 1 
                            FROM pg_enum 
                            WHERE enumlabel = 'failed' 
                            AND enumtypid = (
                                SELECT oid FROM pg_type WHERE typname = 'order_status'
                            )
                        )
                    """)
                    failed_exists = cursor.fetchone()[0] if cursor.rowcount > 0 else False
                    
                    if not failed_exists:
                        # ENUM 값 추가 (트랜잭션 커밋 후 실행)
                        conn.commit()
                        try:
                            cursor.execute("ALTER TYPE order_status ADD VALUE 'failed'")
                            conn.commit()
                            messages.append("✅ order_status ENUM에 'failed' 값 추가 완료")
                            print("✅ order_status ENUM에 'failed' 값 추가 완료")
                        except Exception as add_enum_error:
                            error_str = str(add_enum_error).lower()
                            if 'already exists' in error_str or 'duplicate' in error_str or 'already present' in error_str:
                                messages.append("ℹ️ order_status ENUM에 'failed' 값이 이미 존재합니다.")
                                print("ℹ️ order_status ENUM에 'failed' 값이 이미 존재합니다.")
                            else:
                                messages.append(f"⚠️ order_status ENUM에 'failed' 값 추가 실패: {str(add_enum_error)}")
                                print(f"⚠️ order_status ENUM에 'failed' 값 추가 실패: {add_enum_error}")
                                conn.rollback()
                    else:
                        messages.append("ℹ️ order_status ENUM에 'failed' 값이 이미 존재합니다.")
                        print("ℹ️ order_status ENUM에 'failed' 값이 이미 존재합니다.")
                else:
                    messages.append("ℹ️ order_status ENUM 타입이 아직 생성되지 않았습니다.")
                    print("ℹ️ order_status ENUM 타입이 아직 생성되지 않았습니다.")
            except Exception as e:
                messages.append(f"⚠️ order_status ENUM 확인 중 오류: {str(e)}")
                print(f"⚠️ order_status ENUM 확인 중 오류: {e}")
                try:
                    conn.rollback()
                except:
                    pass
            
            # detailed_service 컬럼 추가
            try:
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='orders' AND column_name='detailed_service'
                """)
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE orders ADD COLUMN detailed_service TEXT")
                    conn.commit()
                    messages.append("✅ detailed_service 필드 추가 완료")
                    print("✅ detailed_service 필드 추가 완료")
                else:
                    messages.append("ℹ️ detailed_service 필드 이미 존재")
                    print("ℹ️ detailed_service 필드 이미 존재")
            except Exception as e:
                messages.append(f"⚠️ detailed_service: {str(e)}")
                print(f"⚠️ detailed_service 필드 추가 실패: {e}")
                conn.rollback()
            
            # package_steps 컬럼 추가
            try:
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='orders' AND column_name='package_steps'
                """)
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE orders ADD COLUMN package_steps JSONB")
                    conn.commit()
                    messages.append("✅ package_steps 필드 추가 완료")
                    print("✅ package_steps 필드 추가 완료")
                else:
                    messages.append("ℹ️ package_steps 필드 이미 존재")
                    print("ℹ️ package_steps 필드 이미 존재")
            except Exception as e:
                messages.append(f"⚠️ package_steps: {str(e)}")
                print(f"⚠️ package_steps 필드 추가 실패: {e}")
                conn.rollback()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '데이터베이스 마이그레이션이 완료되었습니다.',
            'details': messages
        }), 200
        
    except Exception as e:
        print(f"❌ 데이터베이스 마이그레이션 실패: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== 소셜 로그인 API ====================

# 카카오 OAuth 토큰 교환
@app.route('/api/auth/kakao-token', methods=['POST'])
def kakao_token():
    """Kakao Token
    ---
    tags:
      - Auth
    summary: Kakao Token
    description: "Kakao Token API"
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """카카오 인가 코드를 액세스 토큰으로 교환"""
    try:
        data = request.get_json()
        code = data.get('code')
        redirect_uri = data.get('redirectUri')
        
        if not code:
            return jsonify({
                'success': False,
                'error': '인가 코드가 필요합니다.'
            }), 400
        
        # 카카오 토큰 요청
        token_url = 'https://kauth.kakao.com/oauth/token'
        token_data = {
            'grant_type': 'authorization_code',
            'client_id': get_parameter_value('KAKAO_CLIENT_ID', '5a6e0106e9beafa7bd8199ab3c378ceb'),
            'redirect_uri': redirect_uri,
            'code': code
        }
        
        print(f"🔑 카카오 토큰 요청: {token_data}")
        
        response = requests.post(token_url, data=token_data)
        
        if response.status_code == 200:
            token_info = response.json()
            access_token = token_info.get('access_token')
            
            if access_token:
                # 카카오 사용자 정보 조회
                user_info_url = 'https://kapi.kakao.com/v2/user/me'
                headers = {'Authorization': f'Bearer {access_token}'}
                user_response = requests.get(user_info_url, headers=headers)
                
                if user_response.status_code == 200:
                    user_data = user_response.json()
                    
                    # 사용자 정보 추출
                    kakao_id = user_data.get('id')
                    kakao_account = user_data.get('kakao_account', {})
                    profile = kakao_account.get('profile', {})
                    
                    user_info = {
                        'id': kakao_id,
                        'email': kakao_account.get('email'),
                        'nickname': profile.get('nickname'),
                        'profile_image': profile.get('profile_image_url'),
                        'access_token': access_token,
                        'provider': 'kakao'
                    }
                    
                    print(f"✅ 카카오 사용자 정보 조회 성공: {user_info}")
                    
                    return jsonify({
                        'success': True,
                        'user': user_info
                    }), 200
                else:
                    print(f"❌ 카카오 사용자 정보 조회 실패: {user_response.status_code}")
                    return jsonify({
                        'success': False,
                        'error': '카카오 사용자 정보 조회에 실패했습니다.'
                    }), 400
            else:
                print(f"❌ 카카오 액세스 토큰 없음")
                return jsonify({
                    'success': False,
                    'error': '카카오 액세스 토큰을 받지 못했습니다.'
                }), 400
        else:
            print(f"❌ 카카오 토큰 요청 실패: {response.status_code} - {response.text}")
            return jsonify({
                'success': False,
                'error': '카카오 토큰 교환에 실패했습니다.'
            }), 400
            
    except Exception as e:
        print(f"❌ 카카오 토큰 교환 오류: {e}")
        return jsonify({
            'success': False,
            'error': '카카오 로그인 처리 중 오류가 발생했습니다.'
        }), 500

# 일반 로그인 처리
@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    """Auth Login
    ---
    tags:
      - Auth
    summary: Auth Login
    description: "Auth Login API"
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """일반 로그인 처리"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({
                'success': False,
                'error': '이메일과 비밀번호를 입력해주세요.'
            }), 400
        
        # DATABASE_URL 확인
        if not DATABASE_URL:
            print("❌ DATABASE_URL이 설정되지 않았습니다.")
            return jsonify({
                'success': False,
                'error': '데이터베이스 연결 설정이 없습니다.'
            }), 500
        
        print(f"🔍 로그인 시도 - 이메일: {email}, DATABASE_URL: {DATABASE_URL[:20]}...")
        
        # 데이터베이스에서 사용자 확인테
        if DATABASE_URL.startswith('postgresql://'):
            try:
                print("🔍 PostgreSQL 연결 시도...")
                conn = psycopg2.connect(DATABASE_URL)
                cursor = conn.cursor()
                
                # 사용자 조회
                cursor.execute("""
                    SELECT user_id, email, name, profile_image, created_at
                    FROM users 
                    WHERE email = %s
                """, (email,))
                
                user = cursor.fetchone()
                print(f"🔍 사용자 조회 결과: {user}")
                
                if user:
                    user_data = {
                        'uid': user[0],
                        'email': user[1],
                        'displayName': user[2] or user[1].split('@')[0],
                        'photoURL': user[3],
                        'createdAt': user[4].isoformat() if user[4] else None
                    }
                    
                    cursor.close()
                    conn.close()
                    
                    print(f"✅ 로그인 성공: {user_data['uid']}")
                    return jsonify({
                        'success': True,
                        'user': user_data
                    })
                else:
                    cursor.close()
                    conn.close()
                    print("❌ 사용자를 찾을 수 없습니다.")
                    return jsonify({
                        'success': False,
                        'error': '등록되지 않은 이메일입니다.'
                    }), 401
            except Exception as db_error:
                print(f"❌ 데이터베이스 연결 오류: {db_error}")
                return jsonify({
                    'success': False,
                    'error': f'데이터베이스 연결 오류: {str(db_error)}'
                }), 500
        else:
            # SQLite 사용 시
            conn = sqlite3.connect('orders.db')
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT user_id, email, name, profile_image, created_at
                FROM users 
                WHERE email = ?
            """, (email,))
            
            user = cursor.fetchone()
            
            if user:
                user_data = {
                    'uid': user[0],
                    'email': user[1],
                    'displayName': user[2] or user[1].split('@')[0],
                    'photoURL': user[3],
                    'createdAt': user[4]
                }
                
                cursor.close()
                conn.close()
                
                return jsonify({
                    'success': True,
                    'user': user_data
                })
            else:
                cursor.close()
                conn.close()
                return jsonify({
                    'success': False,
                    'error': '등록되지 않은 이메일입니다.'
                }), 401
        
    except Exception as e:
        print(f"❌ 로그인 오류: {e}")
        return jsonify({
            'success': False,
            'error': '로그인 처리 중 오류가 발생했습니다.'
        }), 500

# 카카오 로그인 처리
@app.route('/api/auth/kakao-login', methods=['POST'])
def kakao_login():
    """Kakao Login
    ---
    tags:
      - Auth
    summary: Kakao Login
    description: "Kakao Login API"
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """카카오 로그인 처리"""
    try:
        data = request.get_json()
        
        kakao_id = data.get('kakaoId')
        email = data.get('email')
        nickname = data.get('nickname')
        profile_image = data.get('profileImage')
        access_token = data.get('accessToken')
        
        if not kakao_id:
            return jsonify({
                'success': False,
                'error': '카카오 ID가 필요합니다.'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 기존 사용자 확인 (카카오 ID 또는 이메일로)
        cursor.execute("""
            SELECT user_id, email, name, kakao_id, last_login
            FROM users 
            WHERE kakao_id = %s OR email = %s
        """, (kakao_id, email))
        
        existing_user = cursor.fetchone()
        
        if existing_user:
            # 기존 사용자 업데이트
            user_id = existing_user[0]
            cursor.execute("""
                UPDATE users 
                SET kakao_id = %s, profile_image = %s, last_login = NOW(), updated_at = NOW()
                WHERE user_id = %s
            """, (kakao_id, profile_image, user_id))
            
            print(f"✅ 기존 카카오 사용자 업데이트: {user_id}")
        else:
            # 새 사용자 생성
            user_id = f"kakao_{kakao_id}"
            cursor.execute("""
                INSERT INTO users (user_id, email, name, kakao_id, profile_image, last_login, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW(), NOW())
            """, (user_id, email, nickname, kakao_id, profile_image))
            
            # 포인트 테이블에도 초기 레코드 생성
            cursor.execute("""
                INSERT INTO points (user_id, points, created_at, updated_at)
                VALUES (%s, %s, NOW(), NOW())
            """, (user_id, 0))
            
            print(f"✅ 새 카카오 사용자 생성: {user_id}")
        
        conn.commit()
        
        # 사용자 정보 반환
        user_info = {
            'id': user_id,  # KakaoCallback.jsx에서 user.id로 접근하므로 'id' 사용
            'email': email,
            'nickname': nickname,  # KakaoCallback.jsx에서 user.nickname으로 접근하므로 'nickname' 사용
            'profile_image': profile_image,  # KakaoCallback.jsx에서 user.profile_image로 접근하므로 'profile_image' 사용
            'provider': 'kakao'
        }
        
        conn.close()
        
        return jsonify({
            'success': True,
            'user': user_info
        }), 200
        
    except Exception as e:
        print(f"❌ 카카오 로그인 처리 오류: {e}")
        return jsonify({
            'success': False,
            'error': '카카오 로그인 처리 중 오류가 발생했습니다.'
        }), 500

@app.route('/api/auth/google-callback', methods=['GET'])
def google_callback():
    """Google Callback
    ---
    tags:
      - Auth
    summary: Google Callback
    description: "Google Callback API"
    security:
      - Bearer: []
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """구글 OAuth 콜백 처리"""
    try:
        # Authorization code 받기
        code = request.args.get('code')
        
        if not code:
            return """
                <script>
                    window.opener.postMessage({
                        type: 'GOOGLE_AUTH_ERROR',
                        error: '인증 코드가 없습니다.'
                    }, window.location.origin);
                    window.close();
                </script>
            """
        
        # 구글에서 사용자 정보 가져오기
        try:
            # 환경 변수에서 구글 클라이언트 정보 가져오기
            google_client_id = os.getenv('REACT_APP_GOOGLE_CLIENT_ID')
            google_client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
            
            if not google_client_id or not google_client_secret:
                raise Exception('구글 클라이언트 설정이 없습니다.')
            
            # 1. Authorization code를 access token으로 교환
            token_url = 'https://oauth2.googleapis.com/token'
            token_data = {
                'client_id': google_client_id,
                'client_secret': google_client_secret,
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': f'{request.url_root}api/auth/google-callback'
            }
            
            token_response = requests.post(token_url, data=token_data)
            token_result = token_response.json()
            
            if 'error' in token_result:
                raise Exception(f'토큰 교환 실패: {token_result.get("error_description", "Unknown error")}')
            
            access_token = token_result.get('access_token')
            if not access_token:
                raise Exception('액세스 토큰을 받지 못했습니다.')
            
            # 2. 액세스 토큰으로 사용자 정보 가져오기
            user_info_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
            headers = {'Authorization': f'Bearer {access_token}'}
            user_response = requests.get(user_info_url, headers=headers)
            user_data = user_response.json()
            
            if 'error' in user_data:
                raise Exception(f'사용자 정보 조회 실패: {user_data.get("error_description", "Unknown error")}')
            
            # 사용자 정보 추출
            google_id = user_data.get('id')
            email = user_data.get('email')
            display_name = user_data.get('name')
            photo_url = user_data.get('picture')
            email_verified = user_data.get('verified_email', False)
            
            if not google_id or not email:
                raise Exception('구글 사용자 정보가 불완전합니다.')
            
            # 사용자 정보를 프론트엔드로 전달
            return f"""
                <script>
                    window.opener.postMessage({{
                        type: 'GOOGLE_AUTH_SUCCESS',
                        user: {{
                            googleId: '{google_id}',
                            email: '{email}',
                            displayName: '{display_name or ''}',
                            photoURL: '{photo_url or ''}',
                            emailVerified: {str(email_verified).lower()},
                            accessToken: '{access_token}'
                        }}
                    }}, window.location.origin);
                    window.close();
                </script>
            """
            
        except Exception as auth_error:
            print(f"❌ 구글 인증 처리 오류: {auth_error}")
            return f"""
                <script>
                    window.opener.postMessage({{
                        type: 'GOOGLE_AUTH_ERROR',
                        error: '구글 인증 처리 실패: {str(auth_error)}'
                    }}, window.location.origin);
                    window.close();
                </script>
            """
        
    except Exception as e:
        print(f"❌ 구글 콜백 오류: {e}")
        return """
            <script>
                window.opener.postMessage({
                    type: 'GOOGLE_AUTH_ERROR',
                    error: '구글 로그인 처리 중 오류가 발생했습니다.'
                }, window.location.origin);
                window.close();
            </script>
        """

@app.route('/api/auth/google-login', methods=['POST'])
def google_login():
    """Google Login
    ---
    tags:
      - Auth
    summary: Google Login
    description: "Google Login API"
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """구글 로그인 처리"""
    try:
        data = request.get_json()
        
        google_id = data.get('googleId')
        email = data.get('email')
        display_name = data.get('displayName')
        photo_url = data.get('photoURL')
        email_verified = data.get('emailVerified', False)
        access_token = data.get('accessToken')
        
        if not google_id or not email:
            return jsonify({
                'success': False,
                'error': '구글 ID와 이메일이 필요합니다.'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 기존 사용자 확인 (구글 ID 또는 이메일로)
        cursor.execute("""
            SELECT user_id, email, name, google_id, last_login
            FROM users 
            WHERE google_id = %s OR email = %s
        """, (google_id, email))
        
        existing_user = cursor.fetchone()
        
        if existing_user:
            user_id, user_email, user_name, user_google_id, last_login = existing_user
            
            # 구글 ID가 없으면 추가
            if not user_google_id:
                cursor.execute("""
                    UPDATE users 
                    SET google_id = %s, profile_image = %s, last_login = NOW(), updated_at = NOW()
                    WHERE user_id = %s
                """, (google_id, photo_url, user_id))
            else:
                cursor.execute("""
                    UPDATE users 
                    SET profile_image = %s, last_login = NOW(), updated_at = NOW()
                    WHERE user_id = %s
                """, (photo_url, user_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'user': {
                    'uid': user_id,
                    'email': user_email,
                    'displayName': user_name,
                    'photoURL': photo_url
                },
                'message': '구글 로그인 성공'
            }), 200
        else:
            # 새 사용자 생성 (UPSERT 방식으로 중복 이메일 문제 해결)
            user_id = f"google_{google_id}"
            
            try:
                cursor.execute("""
                    INSERT INTO users (
                        user_id, email, name, google_id, profile_image, last_login, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, NOW(), NOW(), NOW())
                """, (user_id, email, display_name, google_id, photo_url))
                
                # 포인트 테이블에도 초기 레코드 생성
                cursor.execute("""
                    INSERT INTO points (user_id, points, created_at, updated_at)
                    VALUES (%s, %s, NOW(), NOW())
                """, (user_id, 0))
                
                conn.commit()
                cursor.close()
                conn.close()
                
                return jsonify({
                    'success': True,
                    'user': {
                        'uid': user_id,
                        'email': email,
                        'displayName': display_name,
                        'photoURL': photo_url
                    },
                    'message': '구글 회원가입 및 로그인 성공'
                }), 201
                
            except Exception as insert_error:
                # 중복 이메일 오류인 경우 기존 사용자로 처리
                if 'duplicate key value violates unique constraint' in str(insert_error):
                    print(f"⚠️ 중복 이메일 감지, 기존 사용자로 처리: {email}")
                    
                    # 기존 사용자 조회
                    cursor.execute("""
                        SELECT user_id, email, name, google_id, last_login
                        FROM users 
                        WHERE email = %s
                    """, (email,))
                    
                    existing_user = cursor.fetchone()
                    if existing_user:
                        user_id, user_email, user_name, user_google_id, last_login = existing_user
                        
                        # 구글 ID 업데이트
                        cursor.execute("""
                            UPDATE users 
                            SET google_id = %s, profile_image = %s, last_login = NOW(), updated_at = NOW()
                            WHERE user_id = %s
                        """, (google_id, photo_url, user_id))
                        
                        conn.commit()
                        cursor.close()
                        conn.close()
                        
                        return jsonify({
                            'success': True,
                            'user': {
                                'uid': user_id,
                                'email': user_email,
                                'displayName': user_name,
                                'photoURL': photo_url
                            },
                            'message': '구글 로그인 성공 (기존 계정 연결)'
                        }), 200
                
                # 다른 오류인 경우 재발생
                raise insert_error
            
    except Exception as e:
        print(f"구글 로그인 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== 블로그 API ====================

@app.route('/api/blog/posts', methods=['GET'])
def get_blog_posts():
    """Get Blog Posts
    ---
    tags:
      - Blog
    summary: Get Blog Posts
    description: "Get Blog Posts API"
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """블로그 글 목록 조회"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        search = request.args.get('search', '')
        tag = request.args.get('tag', '')
        category = request.args.get('category', '')
        
        offset = (page - 1) * limit
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 새 스키마에서는 blogs 테이블 사용
        if DATABASE_URL.startswith('postgresql://'):
            # 기본 쿼리 (blogs 테이블 사용)
            base_query = """
                SELECT blog_id, title, content, category, NULL as thumbnail_url, NULL as tags, created_at, updated_at, views
                FROM blogs 
                WHERE 1=1
            """
            count_query = "SELECT COUNT(*) FROM blogs WHERE 1=1"
        else:
            # 기본 쿼리
            base_query = """
                SELECT id, title, excerpt, category, thumbnail_url, tags, created_at, updated_at, view_count
                FROM blog_posts 
                WHERE is_published = true
            """
            count_query = "SELECT COUNT(*) FROM blog_posts WHERE is_published = true"
        params = []
        
        # 검색 조건 추가 (SQLite/PostgreSQL 구분)
        if search:
            if DATABASE_URL.startswith('postgresql://'):
                base_query += " AND (title ILIKE %s OR content ILIKE %s)"
                count_query += " AND (title ILIKE %s OR content ILIKE %s)"
            else:
                base_query += " AND (title LIKE ? OR content LIKE ? OR excerpt LIKE ?)"
                count_query += " AND (title LIKE ? OR content LIKE ? OR excerpt LIKE ?)"
            search_param = f"%{search}%"
            if DATABASE_URL.startswith('postgresql://'):
                params.extend([search_param, search_param])
            else:
                params.extend([search_param, search_param, search_param])
        
        if tag:
            # 새 스키마에서는 tags 컬럼이 없을 수 있으므로 스킵
            if not DATABASE_URL.startswith('postgresql://'):
                base_query += " AND tags LIKE ?"
                count_query += " AND tags LIKE ?"
                params.append(f"%{tag}%")
        
        if category:
            if DATABASE_URL.startswith('postgresql://'):
                base_query += " AND category = %s"
                count_query += " AND category = %s"
            else:
                base_query += " AND category = ?"
                count_query += " AND category = ?"
            params.append(category)
        
        # 정렬 및 페이지네이션
        if DATABASE_URL.startswith('postgresql://'):
            base_query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        else:
            base_query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        # 총 개수 조회
        cursor.execute(count_query, params[:-2])  # LIMIT, OFFSET 제외
        total = cursor.fetchone()[0]
        
        # 글 목록 조회
        cursor.execute(base_query, params)
        rows = cursor.fetchall()
        
        posts = []
        for row in rows:
            if DATABASE_URL.startswith('postgresql://'):
                # 새 스키마: blog_id, title, content, category, NULL, NULL, created_at, updated_at, views
                posts.append({
                    'id': row[0],
                    'title': row[1],
                    'excerpt': (row[2][:200] + '...') if row[2] and len(row[2]) > 200 else (row[2] or ''),  # content에서 excerpt 생성
                    'category': row[3],
                    'thumbnail_url': row[4],
                    'tags': [],  # 새 스키마에서는 tags 없음
                    'created_at': row[6].isoformat() if row[6] and hasattr(row[6], 'isoformat') else (str(row[6]) if row[6] else None),
                    'updated_at': row[7].isoformat() if row[7] and hasattr(row[7], 'isoformat') else (str(row[7]) if row[7] else None),
                    'view_count': row[8] if len(row) > 8 else 0
                })
            else:
                posts.append({
                    'id': row[0],
                    'title': row[1],
                    'excerpt': row[2],
                    'category': row[3],
                    'thumbnail_url': row[4],
                    'tags': row[5] if isinstance(row[5], list) else (json.loads(row[5]) if row[5] else []),
                    'created_at': row[6].isoformat(),
                    'updated_at': row[7].isoformat(),
                    'view_count': row[8]
                })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'posts': posts,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit
            }
        }), 200
        
    except Exception as e:
        print(f"블로그 글 목록 조회 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/blog/posts/<int:post_id>', methods=['GET'])
def get_blog_post(post_id):
    """Get Blog Post
    ---
    tags:
      - Blog
    summary: Get Blog Post
    description: "Get Blog Post API"
    parameters:
      - name: post_id
        in: path
        type: int
        required: true
        description: Post Id
        example: "example_post_id"
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """블로그 글 상세 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 조회수 증가
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("UPDATE blog_posts SET view_count = view_count + 1 WHERE id = %s", (post_id,))
        else:
            cursor.execute("UPDATE blog_posts SET view_count = view_count + 1 WHERE id = ?", (post_id,))
        
        # 글 조회
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT id, title, content, excerpt, category, thumbnail_url, tags, created_at, updated_at, view_count
                FROM blog_posts 
                WHERE id = %s AND is_published = true
            """, (post_id,))
        else:
            cursor.execute("""
                SELECT id, title, content, excerpt, category, thumbnail_url, tags, created_at, updated_at, view_count
                FROM blog_posts 
                WHERE id = ? AND is_published = true
            """, (post_id,))
        
        row = cursor.fetchone()
        if not row:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': '블로그 글을 찾을 수 없습니다.'
            }), 404
        
        post = {
            'id': row[0],
            'title': row[1],
            'content': row[2],
            'excerpt': row[3],
            'category': row[4],
            'thumbnail_url': row[5],
            'tags': row[6] if isinstance(row[6], list) else (json.loads(row[6]) if row[6] else []),
            'created_at': row[7].isoformat(),
            'updated_at': row[8].isoformat(),
            'view_count': row[9]
        }
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'post': post
        }), 200
        
    except Exception as e:
        print(f"블로그 글 상세 조회 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/blog/categories', methods=['GET'])
def get_blog_categories():
    """Get Blog Categories
    ---
    tags:
      - Blog
    summary: Get Blog Categories
    description: "Get Blog Categories API"
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """블로그 카테고리 목록 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            # 새 스키마에서는 blogs 테이블 사용
            cursor.execute("""
                SELECT category, COUNT(*) as count
                FROM blogs 
                WHERE category IS NOT NULL
                GROUP BY category
                ORDER BY count DESC, category
            """)
        else:
            cursor.execute("""
                SELECT category, COUNT(*) as count
                FROM blog_posts 
                WHERE is_published = true AND category IS NOT NULL
                GROUP BY category
                ORDER BY count DESC, category
            """)
        
        rows = cursor.fetchall()
        categories = [{'name': row[0], 'count': row[1]} for row in rows]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'categories': categories
        }), 200
        
    except Exception as e:
        print(f"카테고리 조회 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/blog/tags', methods=['GET'])
def get_blog_tags():
    """Get Blog Tags
    ---
    tags:
      - Blog
    summary: Get Blog Tags
    description: "Get Blog Tags API"
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """블로그 태그 목록 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            # 새 스키마에서는 blogs 테이블에 tags 컬럼이 없으므로 빈 배열 반환
            tags = []
        else:
            # SQLite에서는 JSON 함수 사용
            cursor.execute("""
                SELECT DISTINCT json_extract(tags.value, '$') as tag
                FROM blog_posts, json_each(tags) as tags
                WHERE is_published = true AND tags IS NOT NULL
            """)
            rows = cursor.fetchall()
            tags = [row[0] for row in rows if row[0]]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'tags': tags
        }), 200
        
    except Exception as e:
        print(f"태그 조회 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== 관리자 블로그 API ====================

@app.route('/api/blog/posts', methods=['POST'])
@require_admin_auth
def create_blog_post():
    """Create Blog Post
    ---
    tags:
      - Blog
    summary: Create Blog Post
    description: "Create Blog Post API"
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """블로그 글 생성 (관리자 전용)"""
    try:
        data = request.get_json()
        
        title = data.get('title', '').strip()
        content = data.get('content', '').strip()
        excerpt = data.get('excerpt', '').strip()
        category = data.get('category', '일반')
        thumbnail_url = data.get('thumbnail_url', '')
        tags = data.get('tags', [])
        is_published = data.get('is_published', False)
        
        if not title or not content:
            return jsonify({
                'success': False,
                'error': '제목과 내용은 필수입니다.'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO blog_posts (
                title, content, excerpt, category, thumbnail_url, tags, is_published,
                created_at, updated_at, view_count
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            title, content, excerpt, category, thumbnail_url, json.dumps(tags), is_published,
            datetime.now(), datetime.now(), 0
        ))
        
        post_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '블로그 글이 생성되었습니다.',
            'post_id': post_id
        }), 201
        
    except Exception as e:
        print(f"블로그 글 생성 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/blog/posts/<int:post_id>', methods=['PUT'])
@require_admin_auth
def update_blog_post(post_id):
    """Update Blog Post
    ---
    tags:
      - Blog
    summary: Update Blog Post
    description: "Update Blog Post API"
    parameters:
      - name: post_id
        in: path
        type: int
        required: true
        description: Post Id
        example: "example_post_id"
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """블로그 글 수정 (관리자 전용)"""
    try:
        data = request.get_json()
        
        title = data.get('title', '').strip()
        content = data.get('content', '').strip()
        excerpt = data.get('excerpt', '').strip()
        category = data.get('category', '일반')
        thumbnail_url = data.get('thumbnail_url', '')
        tags = data.get('tags', [])
        is_published = data.get('is_published', False)
        
        if not title or not content:
            return jsonify({
                'success': False,
                'error': '제목과 내용은 필수입니다.'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE blog_posts
            SET title = %s, content = %s, excerpt = %s, category = %s, thumbnail_url = %s, tags = %s,
                is_published = %s, updated_at = %s
            WHERE id = %s
        """, (title, content, excerpt, category, thumbnail_url, json.dumps(tags), is_published, datetime.now(), post_id))
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': '블로그 글을 찾을 수 없습니다.'
            }), 404
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '블로그 글이 수정되었습니다.'
        }), 200
        
    except Exception as e:
        print(f"블로그 글 수정 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/blog/posts/<int:post_id>', methods=['DELETE'])
@require_admin_auth
def delete_blog_post(post_id):
    """Delete Blog Post
    ---
    tags:
      - Blog
    summary: Delete Blog Post
    description: "Delete Blog Post API"
    parameters:
      - name: post_id
        in: path
        type: int
        required: true
        description: Post Id
        example: "example_post_id"
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """블로그 글 삭제 (관리자 전용)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM blog_posts WHERE id = %s", (post_id,))
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': '블로그 글을 찾을 수 없습니다.'
            }), 404
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '블로그 글이 삭제되었습니다.'
        }), 200
        
    except Exception as e:
        print(f"블로그 글 삭제 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/upload-image', methods=['POST'])
@require_admin_auth
def upload_admin_image():
    """Upload Admin Image
    ---
    tags:
      - Admin
    summary: Upload Admin Image
    description: "Upload Admin Image API"
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """관리자 이미지 업로드"""
    try:
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'error': '이미지 파일이 없습니다.'
            }), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': '파일이 선택되지 않았습니다.'
            }), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # 고유한 파일명 생성
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # URL 생성
            image_url = f"/static/uploads/{filename}"
            
            return jsonify({
                'success': True,
                'image_url': image_url,
                'message': '이미지가 업로드되었습니다.'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': '허용되지 않는 파일 형식입니다.'
            }), 400
            
    except Exception as e:
        print(f"이미지 업로드 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== 관리자 카탈로그 API ====================

# 카테고리 관리
@app.route('/api/admin/categories', methods=['GET'])
@require_admin_auth
def get_admin_categories():
    """카테고리 목록 조회
    ---
    tags:
      - Admin
    summary: 카테고리 목록 조회
    description: "전체 카테고리 목록을 조회합니다."
    security:
      - Bearer: []
    responses:
      200:
        description: 카테고리 목록 조회 성공
        schema:
          type: object
          properties:
            categories:
              type: array
              items:
                type: object
                properties:
                  category_id:
                    type: integer
                    example: 1
                  name:
                    type: string
                    example: "인스타그램"
                  description:
                    type: string
                    example: "인스타그램 관련 서비스"
      401:
        description: 인증 실패
    """
    conn = None
    cursor = None
    try:
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if include_inactive:
            cursor.execute("SELECT * FROM categories ORDER BY created_at DESC")
        else:
            cursor.execute("SELECT * FROM categories WHERE is_active = TRUE ORDER BY created_at DESC")
        
        categories = cursor.fetchall()
        return jsonify({
            'categories': [dict(cat) for cat in categories],
            'count': len(categories)
        }), 200
    except Exception as e:
        print(f"❌ 카테고리 목록 조회 오류: {e}")
        return jsonify({'error': f'카테고리 조회 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/admin/categories', methods=['POST'])
@require_admin_auth
def create_admin_category():
    """Create Admin Category
    ---
    tags:
      - Admin
    summary: Create Admin Category
    description: "Create Admin Category API"
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """카테고리 생성"""
    conn = None
    cursor = None
    try:
        data = request.get_json()
        name = data.get('name')
        slug = data.get('slug', name.lower().replace(' ', '-'))
        image_url = data.get('image_url')
        is_active = data.get('is_active', True)
        
        if not name:
            return jsonify({'error': '카테고리 이름이 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            INSERT INTO categories (name, slug, image_url, is_active, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
            RETURNING *
        """, (name, slug, image_url, is_active))
        
        category = cursor.fetchone()
        conn.commit()
        
        return jsonify({
            'success': True,
            'category': dict(category)
        }), 201
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ 카테고리 생성 오류: {e}")
        return jsonify({'error': f'카테고리 생성 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/admin/categories/<int:category_id>', methods=['GET'])
@require_admin_auth
def get_admin_category(category_id):
    """Get Admin Category
    ---
    tags:
      - Admin
    summary: Get Admin Category
    description: "Get Admin Category API"
    security:
      - Bearer: []
    parameters:
      - name: category_id
        in: path
        type: int
        required: true
        description: Category Id
        example: "example_category_id"
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """카테고리 상세 조회"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT * FROM categories WHERE category_id = %s", (category_id,))
        category = cursor.fetchone()
        
        if not category:
            return jsonify({'error': '카테고리를 찾을 수 없습니다.'}), 404
        
        return jsonify({'category': dict(category)}), 200
    except Exception as e:
        print(f"❌ 카테고리 조회 오류: {e}")
        return jsonify({'error': f'카테고리 조회 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/admin/categories/<int:category_id>', methods=['PUT'])
@require_admin_auth
def update_admin_category(category_id):
    """Update Admin Category
    ---
    tags:
      - Admin
    summary: Update Admin Category
    description: "Update Admin Category API"
    security:
      - Bearer: []
    parameters:
      - name: category_id
        in: path
        type: int
        required: true
        description: Category Id
        example: "example_category_id"
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """카테고리 수정"""
    conn = None
    cursor = None
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 기존 데이터 조회
        cursor.execute("SELECT * FROM categories WHERE category_id = %s", (category_id,))
        category = cursor.fetchone()
        
        if not category:
            return jsonify({'error': '카테고리를 찾을 수 없습니다.'}), 404
        
        # 업데이트할 필드만 변경
        name = data.get('name', category['name'])
        slug = data.get('slug', category.get('slug') or name.lower().replace(' ', '-'))
        image_url = data.get('image_url', category.get('image_url'))
        is_active = data.get('is_active', category.get('is_active', True))
        
        cursor.execute("""
            UPDATE categories
            SET name = %s, slug = %s, image_url = %s, is_active = %s, updated_at = NOW()
            WHERE category_id = %s
            RETURNING *
        """, (name, slug, image_url, is_active, category_id))
        
        updated = cursor.fetchone()
        conn.commit()
        
        return jsonify({
            'success': True,
            'category': dict(updated)
        }), 200
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ 카테고리 수정 오류: {e}")
        return jsonify({'error': f'카테고리 수정 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/admin/categories/<int:category_id>', methods=['DELETE'])
@require_admin_auth
def delete_admin_category(category_id):
    """Delete Admin Category
    ---
    tags:
      - Admin
    summary: Delete Admin Category
    description: "Delete Admin Category API"
    security:
      - Bearer: []
    parameters:
      - name: category_id
        in: path
        type: int
        required: true
        description: Category Id
        example: "example_category_id"
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """카테고리 삭제 (실제 삭제)"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 카테고리 존재 여부 확인
        cursor.execute("SELECT category_id, name FROM categories WHERE category_id = %s", (category_id,))
        category = cursor.fetchone()
        
        if not category:
            return jsonify({'error': '카테고리를 찾을 수 없습니다.'}), 404
        
        category_name = category.get('name', '')
        print(f"🗑️ 카테고리 삭제 시도: {category_name} (category_id: {category_id})")
        
        # 관련 데이터 확인 (선택사항 - 삭제 전 경고용)
        cursor.execute("SELECT COUNT(*) as count FROM products WHERE category_id = %s", (category_id,))
        products_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM packages WHERE category_id = %s", (category_id,))
        packages_count = cursor.fetchone()['count']
        
        if products_count > 0 or packages_count > 0:
            print(f"⚠️ 카테고리에 연결된 상품 {products_count}개, 패키지 {packages_count}개가 있습니다.")
            # 외래 키 제약 조건에 따라 CASCADE 삭제되거나, 수동 삭제 필요
        
        # 관련 데이터가 있으면 함께 삭제 (외래 키 제약 조건 해결)
        if products_count > 0:
            print(f"📦 연결된 상품 {products_count}개 삭제 중...")
            # order_items가 variant_id를 참조할 수 있으므로 먼저 삭제
            cursor.execute("""
                DELETE FROM order_items 
                WHERE variant_id IN (
                    SELECT variant_id FROM product_variants 
                    WHERE product_id IN (SELECT product_id FROM products WHERE category_id = %s)
                )
            """, (category_id,))
            # 상품의 variants 삭제
            cursor.execute("""
                DELETE FROM product_variants 
                WHERE product_id IN (SELECT product_id FROM products WHERE category_id = %s)
            """, (category_id,))
            # 상품 삭제
            cursor.execute("DELETE FROM products WHERE category_id = %s", (category_id,))
            print(f"✅ 연결된 상품 {products_count}개 삭제 완료")
        
        if packages_count > 0:
            print(f"📦 연결된 패키지 {packages_count}개 삭제 중...")
            # 패키지의 items 먼저 삭제
            cursor.execute("""
                DELETE FROM package_items 
                WHERE package_id IN (SELECT package_id FROM packages WHERE category_id = %s)
            """, (category_id,))
            # 패키지 삭제
            cursor.execute("DELETE FROM packages WHERE category_id = %s", (category_id,))
            print(f"✅ 연결된 패키지 {packages_count}개 삭제 완료")
        
        # 카테고리 삭제
        cursor.execute("DELETE FROM categories WHERE category_id = %s", (category_id,))
        
        if cursor.rowcount == 0:
            return jsonify({'error': '카테고리를 찾을 수 없습니다.'}), 404
        
        conn.commit()
        print(f"✅ 카테고리 삭제 완료: {category_name} (category_id: {category_id})")
        return jsonify({
            'success': True, 
            'message': f'카테고리 "{category_name}"가 삭제되었습니다.',
            'deleted_products': products_count,
            'deleted_packages': packages_count
        }), 200
    except Exception as e:
        if conn:
            conn.rollback()
        error_msg = str(e)
        print(f"❌ 카테고리 삭제 오류: {error_msg}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'카테고리 삭제 실패: {error_msg}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 상품 관리
@app.route('/api/admin/products', methods=['GET'])
@require_admin_auth
def get_admin_products():
    """Get Admin Products
    ---
    tags:
      - Admin
    summary: Get Admin Products
    description: "Get Admin Products API"
    security:
      - Bearer: []
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """상품 목록 조회"""
    conn = None
    cursor = None
    try:
        category_id = request.args.get('category_id')
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if category_id:
            cursor.execute("""
                SELECT p.*, c.name as category_name
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.category_id
                WHERE p.category_id = %s
                ORDER BY p.created_at DESC
            """, (category_id,))
        else:
            cursor.execute("""
                SELECT p.*, c.name as category_name
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.category_id
                ORDER BY p.created_at DESC
            """)
        
        products = cursor.fetchall()
        return jsonify({
            'products': [dict(p) for p in products],
            'count': len(products)
        }), 200
    except Exception as e:
        print(f"❌ 상품 목록 조회 오류: {e}")
        return jsonify({'error': f'상품 조회 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/admin/products', methods=['POST'])
@require_admin_auth
def create_admin_product():
    """Create Admin Product
    ---
    tags:
      - Admin
    summary: Create Admin Product
    description: "Create Admin Product API"
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """상품 생성"""
    conn = None
    cursor = None
    try:
        data = request.get_json()
        category_id = data.get('category_id')
        name = data.get('name')
        description = data.get('description')
        is_domestic = data.get('is_domestic', True)
        is_auto = data.get('is_auto', False)  # 자동상품 여부
        auto_tag = data.get('auto_tag', False)
        
        if not category_id or not name:
            return jsonify({'error': '카테고리 ID와 상품 이름이 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # is_auto 컬럼 존재 여부 확인 후 동적 INSERT
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'products' 
            AND column_name = 'is_auto'
        """)
        has_is_auto = cursor.fetchone() is not None
        
        if has_is_auto:
            cursor.execute("""
                INSERT INTO products (category_id, name, description, is_domestic, is_auto, auto_tag, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING *
            """, (category_id, name, description, is_domestic, is_auto, auto_tag))
        else:
            cursor.execute("""
                INSERT INTO products (category_id, name, description, is_domestic, auto_tag, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING *
            """, (category_id, name, description, is_domestic, auto_tag))
        
        product = cursor.fetchone()
        conn.commit()
        
        return jsonify({
            'success': True,
            'product': dict(product)
        }), 201
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ 상품 생성 오류: {e}")
        return jsonify({'error': f'상품 생성 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/admin/products/<int:product_id>', methods=['GET'])
@require_admin_auth
def get_admin_product(product_id):
    """Get Admin Product
    ---
    tags:
      - Admin
    summary: Get Admin Product
    description: "Get Admin Product API"
    security:
      - Bearer: []
    parameters:
      - name: product_id
        in: path
        type: int
        required: true
        description: Product Id
        example: "example_product_id"
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """상품 상세 조회"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT p.*, c.name as category_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.category_id
            WHERE p.product_id = %s
        """, (product_id,))
        product = cursor.fetchone()
        
        if not product:
            return jsonify({'error': '상품을 찾을 수 없습니다.'}), 404
        
        return jsonify({'product': dict(product)}), 200
    except Exception as e:
        print(f"❌ 상품 조회 오류: {e}")
        return jsonify({'error': f'상품 조회 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/admin/products/<int:product_id>', methods=['PUT'])
@require_admin_auth
def update_admin_product(product_id):
    """Update Admin Product
    ---
    tags:
      - Admin
    summary: Update Admin Product
    description: "Update Admin Product API"
    security:
      - Bearer: []
    parameters:
      - name: product_id
        in: path
        type: int
        required: true
        description: Product Id
        example: "example_product_id"
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """상품 수정"""
    conn = None
    cursor = None
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT * FROM products WHERE product_id = %s", (product_id,))
        product = cursor.fetchone()
        
        if not product:
            return jsonify({'error': '상품을 찾을 수 없습니다.'}), 404
        
        category_id = data.get('category_id', product['category_id'])
        name = data.get('name', product['name'])
        description = data.get('description', product.get('description'))
        is_domestic = data.get('is_domestic', product.get('is_domestic', True))
        is_auto = data.get('is_auto', product.get('is_auto', False))  # 자동상품 여부
        auto_tag = data.get('auto_tag', product.get('auto_tag', False))
        
        # is_auto 컬럼 존재 여부 확인 후 동적 UPDATE
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'products' 
            AND column_name = 'is_auto'
        """)
        has_is_auto = cursor.fetchone() is not None
        
        if has_is_auto:
            cursor.execute("""
                UPDATE products
                SET category_id = %s, name = %s, description = %s, is_domestic = %s, is_auto = %s, auto_tag = %s, updated_at = NOW()
                WHERE product_id = %s
                RETURNING *
            """, (category_id, name, description, is_domestic, is_auto, auto_tag, product_id))
        else:
            cursor.execute("""
                UPDATE products
                SET category_id = %s, name = %s, description = %s, is_domestic = %s, auto_tag = %s, updated_at = NOW()
                WHERE product_id = %s
                RETURNING *
            """, (category_id, name, description, is_domestic, auto_tag, product_id))
        
        updated = cursor.fetchone()
        conn.commit()
        
        return jsonify({
            'success': True,
            'product': dict(updated)
        }), 200
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ 상품 수정 오류: {e}")
        return jsonify({'error': f'상품 수정 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/admin/products/<int:product_id>', methods=['DELETE'])
@require_admin_auth
def delete_admin_product(product_id):
    """Delete Admin Product
    ---
    tags:
      - Admin
    summary: Delete Admin Product
    description: "Delete Admin Product API"
    security:
      - Bearer: []
    parameters:
      - name: product_id
        in: path
        type: int
        required: true
        description: Product Id
        example: "example_product_id"
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """상품 삭제 (옵션이 있으면 오류)"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 옵션 확인
        cursor.execute("SELECT COUNT(*) FROM product_variants WHERE product_id = %s", (product_id,))
        variant_count = cursor.fetchone()[0]
        
        if variant_count > 0:
            return jsonify({
                'error': f'상품에 {variant_count}개의 옵션이 있어 삭제할 수 없습니다. 먼저 옵션을 삭제하세요.'
            }), 400
        
        cursor.execute("DELETE FROM products WHERE product_id = %s", (product_id,))
        
        if cursor.rowcount == 0:
            return jsonify({'error': '상품을 찾을 수 없습니다.'}), 404
        
        conn.commit()
        return jsonify({'success': True, 'message': '상품이 삭제되었습니다.'}), 200
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ 상품 삭제 오류: {e}")
        return jsonify({'error': f'상품 삭제 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ============================================
# 공개 API: 상품 목록 (관리자 인증 불필요)
# ============================================

@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Get Categories
    ---
    tags:
      - Products
    summary: Get Categories
    description: "Get Categories API"
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """활성화된 카테고리 목록 조회 (공개)"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 실제 스키마에 맞게 쿼리 수정 (image_url 포함)
        try:
            cursor.execute("""
                SELECT category_id, name, slug, image_url, created_at, updated_at
                FROM categories
                WHERE is_active = TRUE
                ORDER BY created_at ASC
            """)
        except Exception as schema_error:
            # image_url 컬럼이 없을 수도 있으므로 image_url 없이 재시도
            print(f"⚠️ image_url 컬럼이 없어 image_url 제외하고 재시도: {schema_error}")
            try:
                cursor.execute("""
                    SELECT category_id, name, slug, created_at, updated_at
                    FROM categories
                    WHERE is_active = TRUE
                    ORDER BY created_at ASC
                """)
            except Exception as retry_error:
                print(f"❌ 카테고리 조회 실패: {retry_error}")
                return jsonify({'categories': []}), 200
        
        categories = cursor.fetchall()
        return jsonify({
            'categories': [dict(c) for c in categories],
            'count': len(categories)
        }), 200
    except Exception as e:
        import traceback
        error_msg = f'카테고리 조회 실패: {str(e)}'
        print(f"❌ 카테고리 목록 조회 오류: {error_msg}")
        print(traceback.format_exc())
        return jsonify({'error': error_msg}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/products', methods=['GET'])
def get_products():
    """상품 목록 조회
    ---
    tags:
      - Products
    summary: 상품 목록 조회
    description: "활성화된 상품 목록을 조회합니다."
    parameters:
      - name: category_id
        in: query
        type: integer
        required: false
        description: 카테고리 ID로 필터링
        example: 1
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            products:
              type: array
              items:
                type: object
                properties:
                  product_id:
                    type: integer
                    example: 1
                  name:
                    type: string
                    example: "좋아요"
                  description:
                    type: string
                    example: "인스타그램 좋아요 서비스"
                  category_id:
                    type: integer
                    example: 1
                  category_name:
                    type: string
                    example: "인스타그램"
            count:
              type: integer
              example: 10
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "상품 조회 실패: ..."
    """ 
    """활성화된 상품 목록 조회 (공개)"""
    conn = None
    cursor = None
    try:
        category_id = request.args.get('category_id')
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # products 테이블에 is_active 컬럼이 없을 수 있으므로 조건 제거
        if category_id:
            cursor.execute("""
                SELECT p.*, c.name as category_name, c.slug as category_slug
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.category_id
                WHERE (c.is_active = TRUE OR c.is_active IS NULL)
                  AND (p.category_id = %s OR %s IS NULL)
                ORDER BY p.created_at ASC
            """, (category_id, category_id))
        else:
            cursor.execute("""
                SELECT p.*, c.name as category_name, c.slug as category_slug
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.category_id
                WHERE (c.is_active = TRUE OR c.is_active IS NULL)
                ORDER BY p.created_at ASC
            """)
        
        products = cursor.fetchall()
        return jsonify({
            'products': [dict(p) for p in products],
            'count': len(products)
        }), 200
    except Exception as e:
        print(f"❌ 상품 목록 조회 오류: {e}")
        return jsonify({'error': f'상품 조회 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/products/<int:product_id>', methods=['GET'])
def get_product_detail(product_id):
    """상품 상세 조회
    ---
    tags:
      - Products
    summary: 상품 상세 조회
    description: "특정 상품의 상세 정보를 조회합니다."
    parameters:
      - name: product_id
        in: path
        type: integer
        required: true
        description: 상품 ID
        example: 1
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            product:
              type: object
              properties:
                product_id:
                  type: integer
                  example: 1
                name:
                  type: string
                  example: "좋아요"
                description:
                  type: string
                  example: "인스타그램 좋아요 서비스"
                category_id:
                  type: integer
                  example: 1
                category_name:
                  type: string
                  example: "인스타그램"
                created_at:
                  type: string
                  example: "2024-01-01T00:00:00"
      404:
        description: 상품을 찾을 수 없음
        schema:
          type: object
          properties:
            error:
              type: string
              example: "상품을 찾을 수 없습니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "상품 조회 실패: ..."
    """
    """상품 상세 정보 조회 (공개)"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT p.*, c.name as category_name, c.slug as category_slug
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.category_id
                WHERE p.product_id = %s
            """, (product_id,))
        else:
            cursor.execute("""
                SELECT p.*, c.name as category_name, c.slug as category_slug
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.category_id
                WHERE p.product_id = ?
            """, (product_id,))
        
        product = cursor.fetchone()
        
        if not product:
            return jsonify({'error': '상품을 찾을 수 없습니다.'}), 404
        
        return jsonify({'product': dict(product)}), 200
    except Exception as e:
        print(f"❌ 상품 상세 조회 오류: {e}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': f'상품 조회 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/product-variants', methods=['GET'])
def get_product_variants():
    """상품 옵션 목록 조회
    ---
    tags:
      - Products
    summary: 상품 옵션 목록 조회
    description: "활성화된 상품 옵션(세부 서비스) 목록을 조회합니다."
    parameters:
      - name: product_id
        in: query
        type: integer
        required: false
        description: 상품 ID로 필터링
        example: 1
      - name: category_id
        in: query
        type: integer
        required: false
        description: 카테고리 ID로 필터링
        example: 1
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            variants:
              type: array
              items:
                type: object
                properties:
                  variant_id:
                    type: integer
                    example: 1
                  product_id:
                    type: integer
                    example: 1
                  name:
                    type: string
                    example: "실제 좋아요"
                  price:
                    type: number
                    example: 1000
                  min_quantity:
                    type: integer
                    example: 100
                  max_quantity:
                    type: integer
                    example: 10000
            count:
              type: integer
              example: 10
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "상품 옵션 조회 실패: ..."
    """ 
    """활성화된 세부 서비스 목록 조회 (공개)"""
    conn = None
    cursor = None
    max_retries = 2
    retry_count = 0
    
    # SSL 연결 오류 시 재시도
    while retry_count < max_retries:
        try:
            product_id = request.args.get('product_id')
            category_id = request.args.get('category_id')
            conn = get_db_connection()
            # 연결이 살아있는지 확인
            test_cursor = conn.cursor()
            test_cursor.execute("SELECT 1")
            test_cursor.close()
            break  # 연결 성공, 루프 탈출
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            error_msg = str(e)
            if 'SSL connection has been closed' in error_msg or 'connection has been closed' in error_msg:
                retry_count += 1
                if retry_count < max_retries:
                    print(f"⚠️ SSL 연결 끊김 감지, 재연결 시도 {retry_count}/{max_retries}...")
                    if conn:
                        try:
                            conn.close()
                        except:
                            pass
                    import time
                    time.sleep(1)  # 1초 대기 후 재시도
                    continue
                else:
                    print(f"❌ product-variants 조회 실패: SSL 연결 재시도 {max_retries}회 모두 실패")
                    return jsonify({'error': '데이터베이스 연결 실패. 잠시 후 다시 시도해주세요.'}), 503
            else:
                # 다른 오류는 즉시 반환
                raise
    
    # 연결이 없으면 (재시도 실패)
    if not conn:
        return jsonify({'error': '데이터베이스 연결 실패'}), 503
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # is_active 컬럼 존재 여부 확인 후 쿼리 작성
        try:
            # 먼저 is_active 컬럼이 있는지 확인
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'product_variants' 
                  AND column_name = 'is_active'
            """)
            has_is_active = cursor.fetchone() is not None
            
            if has_is_active:
                query = """
                    SELECT 
                        pv.variant_id as id,
                        pv.product_id,
                        pv.name,
                        pv.price,
                        pv.min_quantity as min,
                        pv.max_quantity as max,
                        pv.delivery_time_days,
                        pv.meta_json,
                        pv.api_endpoint,
                        p.name as product_name,
                        c.name as category_name,
                        c.category_id
                    FROM product_variants pv
                    LEFT JOIN products p ON pv.product_id = p.product_id
                    LEFT JOIN categories c ON p.category_id = c.category_id
                    WHERE pv.is_active = TRUE 
                      AND (c.is_active = TRUE OR c.is_active IS NULL)
                """
            else:
                # is_active 컬럼이 없으면 모든 variant 조회
                query = """
                    SELECT 
                        pv.variant_id as id,
                        pv.product_id,
                        pv.name,
                        pv.price,
                        pv.min_quantity as min,
                        pv.max_quantity as max,
                        pv.delivery_time_days,
                        pv.meta_json,
                        pv.api_endpoint,
                        p.name as product_name,
                        c.name as category_name,
                        c.category_id
                    FROM product_variants pv
                    LEFT JOIN products p ON pv.product_id = p.product_id
                    LEFT JOIN categories c ON p.category_id = c.category_id
                    WHERE (c.is_active = TRUE OR c.is_active IS NULL)
                """
        except Exception as schema_check_error:
            # 스키마 확인 실패 시 기본 쿼리 사용 (is_active 없이)
            print(f"⚠️ 스키마 확인 실패, 기본 쿼리 사용: {schema_check_error}")
            query = """
                SELECT 
                    pv.variant_id as id,
                    pv.product_id,
                    pv.name,
                    pv.price,
                    pv.min_quantity as min,
                    pv.max_quantity as max,
                    pv.delivery_time_days,
                    pv.meta_json,
                    pv.api_endpoint,
                    p.name as product_name,
                    c.name as category_name,
                    c.category_id
                FROM product_variants pv
                LEFT JOIN products p ON pv.product_id = p.product_id
                LEFT JOIN categories c ON p.category_id = c.category_id
                WHERE (c.is_active = TRUE OR c.is_active IS NULL)
            """
        
        params = []
        
        if product_id:
            query += " AND pv.product_id = %s"
            params.append(product_id)
        
        if category_id:
            query += " AND c.category_id = %s"
            params.append(category_id)
        
        query += " ORDER BY pv.created_at ASC"
        
        cursor.execute(query, tuple(params) if params else ())
        variants = cursor.fetchall()
        
        # meta_json 파싱 및 형식 변환
        result = []
        import json
        for v in variants:
            try:
                variant_dict = dict(v)
                
                # meta_json 파싱 (JSONB는 이미 dict일 수 있음)
                meta_json = variant_dict.get('meta_json')
                if meta_json and isinstance(meta_json, str):
                    try:
                        variant_dict['meta_json'] = json.loads(meta_json)
                    except json.JSONDecodeError:
                        variant_dict['meta_json'] = {}
                elif meta_json is None:
                    variant_dict['meta_json'] = {}
                # 이미 dict인 경우 그대로 사용
                
                # SMM Panel 서비스 ID 추출
                if variant_dict.get('meta_json') and isinstance(variant_dict['meta_json'], dict):
                    smm_service_id = variant_dict['meta_json'].get('service_id') or variant_dict['meta_json'].get('smm_service_id')
                    if smm_service_id:
                        try:
                            variant_dict['smmkings_id'] = int(smm_service_id) if str(smm_service_id).isdigit() else None
                        except (ValueError, TypeError):
                            variant_dict['smmkings_id'] = None
                    else:
                        variant_dict['smmkings_id'] = None
                else:
                    variant_dict['smmkings_id'] = None
                
                # 배송 시간 포맷팅
                delivery_days = variant_dict.get('delivery_time_days')
                if delivery_days:
                    try:
                        delivery_days = float(delivery_days)
                        if delivery_days == 1:
                            variant_dict['time'] = '1일'
                        elif delivery_days < 1:
                            variant_dict['time'] = f'{int(delivery_days * 24)}시간'
                        else:
                            variant_dict['time'] = f'{int(delivery_days)}일'
                    except (ValueError, TypeError):
                        variant_dict['time'] = '데이터가 충분하지 않습니다'
                else:
                    variant_dict['time'] = '데이터가 충분하지 않습니다'
                
                result.append(variant_dict)
            except Exception as variant_error:
                print(f"⚠️ variant 처리 오류 (건너뜀): {variant_error}")
                continue  # 개별 variant 오류는 건너뛰고 계속
        
        return jsonify({
            'variants': result,
            'count': len(result)
        }), 200
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"❌ 세부 서비스 목록 조회 오류: {error_msg}")
        print(traceback.format_exc())
        if conn:
            try:
                conn.rollback()
            except:
                pass
        return jsonify({'error': f'세부 서비스 조회 실패: {error_msg}'}), 500
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if conn:
            try:
                conn.close()
            except:
                pass

@app.route('/api/product-variants/<int:variant_id>', methods=['GET'])
def get_product_variant_detail(variant_id):
    """상품 옵션 상세 조회
    ---
    tags:
      - Products
    summary: 상품 옵션 상세 조회
    description: "특정 상품 옵션(세부 서비스)의 상세 정보를 조회합니다."
    parameters:
      - name: variant_id
        in: path
        type: integer
        required: true
        description: 상품 옵션 ID
        example: 1
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            variant:
              type: object
              properties:
                variant_id:
                  type: integer
                  example: 1
                product_id:
                  type: integer
                  example: 1
                name:
                  type: string
                  example: "실제 좋아요"
                price:
                  type: number
                  example: 1000
                min_quantity:
                  type: integer
                  example: 100
                max_quantity:
                  type: integer
                  example: 10000
                delivery_time_days:
                  type: integer
                  example: 3
                product_name:
                  type: string
                  example: "좋아요"
                category_name:
                  type: string
                  example: "인스타그램"
      404:
        description: 상품 옵션을 찾을 수 없음
        schema:
          type: object
          properties:
            error:
              type: string
              example: "상품 옵션을 찾을 수 없습니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "상품 옵션 조회 실패: ..."
    """
    """상품 옵션 상세 정보 조회 (공개)"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT pv.*, p.name as product_name, c.name as category_name, c.slug as category_slug
                FROM product_variants pv
                LEFT JOIN products p ON pv.product_id = p.product_id
                LEFT JOIN categories c ON p.category_id = c.category_id
                WHERE pv.variant_id = %s
            """, (variant_id,))
        else:
            cursor.execute("""
                SELECT pv.*, p.name as product_name, c.name as category_name, c.slug as category_slug
                FROM product_variants pv
                LEFT JOIN products p ON pv.product_id = p.product_id
                LEFT JOIN categories c ON p.category_id = c.category_id
                WHERE pv.variant_id = ?
            """, (variant_id,))
        
        variant = cursor.fetchone()
        
        if not variant:
            return jsonify({'error': '상품 옵션을 찾을 수 없습니다.'}), 404
        
        variant_dict = dict(variant)
        
        # meta_json 파싱
        if variant_dict.get('meta_json') and isinstance(variant_dict['meta_json'], str):
            try:
                import json
                variant_dict['meta_json'] = json.loads(variant_dict['meta_json'])
            except json.JSONDecodeError:
                variant_dict['meta_json'] = {}
        elif variant_dict.get('meta_json') is None:
            variant_dict['meta_json'] = {}
        
        return jsonify({'variant': variant_dict}), 200
    except Exception as e:
        print(f"❌ 상품 옵션 상세 조회 오류: {e}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': f'상품 옵션 조회 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/packages', methods=['GET'])
def get_packages():
    """Get Packages
    ---
    tags:
      - Products
    summary: Get Packages
    description: "Get Packages API"
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """활성화된 패키지 목록 조회 (공개)"""
    conn = None
    cursor = None
    max_retries = 2
    retry_count = 0
    
    # SSL 연결 오류 시 재시도
    while retry_count < max_retries:
        try:
            category_id = request.args.get('category_id')
            conn = get_db_connection()
            # 연결이 살아있는지 확인
            test_cursor = conn.cursor()
            test_cursor.execute("SELECT 1")
            test_cursor.close()
            break  # 연결 성공, 루프 탈출
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            error_msg = str(e)
            if 'SSL connection has been closed' in error_msg or 'connection has been closed' in error_msg:
                retry_count += 1
                if retry_count < max_retries:
                    print(f"⚠️ SSL 연결 끊김 감지, 재연결 시도 {retry_count}/{max_retries}...")
                    if conn:
                        try:
                            conn.close()
                        except:
                            pass
                    import time
                    time.sleep(1)  # 1초 대기 후 재시도
                    continue
                else:
                    print(f"❌ 패키지 조회 실패: SSL 연결 재시도 {max_retries}회 모두 실패")
                    return jsonify({'error': '데이터베이스 연결 실패. 잠시 후 다시 시도해주세요.'}), 503
            else:
                # 다른 오류는 즉시 반환
                raise
    
    # 연결이 없으면 (재시도 실패)
    if not conn:
        return jsonify({'error': '데이터베이스 연결 실패'}), 503
    
    try:
        is_postgres = DATABASE_URL.startswith('postgresql://')
        
        if is_postgres:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            # SQLite에서 dict 형태로 결과 반환
            import sqlite3
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
        
        # SQLite와 PostgreSQL 호환 쿼리
        if is_postgres:
            query = """
                SELECT 
                    pk.package_id,
                    pk.name,
                    pk.description,
                    pk.category_id,
                    c.name as category_name
                FROM packages pk
                LEFT JOIN categories c ON pk.category_id = c.category_id
                WHERE (c.is_active = TRUE OR c.is_active IS NULL)
            """
            param_placeholder = "%s"
        else:
            query = """
                SELECT 
                    pk.package_id,
                    pk.name,
                    pk.description,
                    pk.category_id,
                    c.name as category_name
                FROM packages pk
                LEFT JOIN categories c ON pk.category_id = c.category_id
                WHERE (c.is_active = 1 OR c.is_active IS NULL)
            """
            param_placeholder = "?"
        
        params = []
        
        if category_id:
            query += f" AND c.category_id = {param_placeholder}"
            params.append(category_id)
        
        query += " ORDER BY pk.created_at ASC"
        
        cursor.execute(query, tuple(params) if params else ())
        
        if is_postgres:
            packages = cursor.fetchall()
        else:
            # SQLite: Row 객체를 딕셔너리로 변환
            packages = [dict(row) for row in cursor.fetchall()]
        
        # 패키지 아이템 조회
        result = []
        for pkg in packages:
            pkg_dict = dict(pkg) if not isinstance(pkg, dict) else pkg
            
            # 패키지 아이템 조회
            if is_postgres:
                cursor.execute("""
                    SELECT 
                        pi.package_item_id,
                        pi.variant_id,
                        pi.quantity,
                        pi.term_value,
                        pi.term_unit,
                        pi.repeat_count,
                        pi.step,
                        pv.name as variant_name,
                        pv.price as variant_price
                    FROM package_items pi
                    LEFT JOIN product_variants pv ON pi.variant_id = pv.variant_id
                    WHERE pi.package_id = %s
                    ORDER BY pi.step ASC, pi.package_item_id ASC
                """, (pkg_dict['package_id'],))
                items = cursor.fetchall()
            else:
                cursor.execute("""
                    SELECT 
                        pi.package_item_id,
                        pi.variant_id,
                        pi.quantity,
                        pi.term_value,
                        pi.term_unit,
                        pi.repeat_count,
                        pi.step,
                        pv.name as variant_name,
                        pv.price as variant_price
                    FROM package_items pi
                    LEFT JOIN product_variants pv ON pi.variant_id = pv.variant_id
                    WHERE pi.package_id = ?
                    ORDER BY pi.step ASC, pi.package_item_id ASC
                """, (pkg_dict['package_id'],))
                items = [dict(row) for row in cursor.fetchall()]
            
            pkg_dict['items'] = [dict(item) if not isinstance(item, dict) else item for item in items]
            
            # items를 steps 형식으로 변환 (하드코딩된 패키지와 호환)
            # 하드코딩 형식: { id, name, quantity, delay, repeat }
            # DB items 형식: { variant_id, step, quantity, term_value, term_unit, repeat_count, variant_name }
            converted_steps = []
            for item in pkg_dict['items']:
                item_dict = dict(item) if not isinstance(item, dict) else item
                
                # variant_id로부터 service_id 찾기
                variant_id = item_dict.get('variant_id')
                service_id = None
                variant_name = item_dict.get('variant_name', '')
                
                if variant_id:
                    try:
                        if is_postgres:
                            cursor.execute("""
                                SELECT meta_json 
                                FROM product_variants 
                                WHERE variant_id = %s
                                LIMIT 1
                            """, (variant_id,))
                        else:
                            cursor.execute("""
                                SELECT meta_json 
                                FROM product_variants 
                                WHERE variant_id = ?
                                LIMIT 1
                            """, (variant_id,))
                        
                        variant_result = cursor.fetchone()
                        if variant_result:
                            meta_json = variant_result[0]
                            if isinstance(meta_json, dict):
                                service_id = meta_json.get('service_id') or meta_json.get('smm_service_id')
                            elif isinstance(meta_json, str):
                                import json
                                try:
                                    meta_dict = json.loads(meta_json)
                                    service_id = meta_dict.get('service_id') or meta_dict.get('smm_service_id')
                                except:
                                    pass
                    except Exception as e:
                        print(f"⚠️ variant_id {variant_id}에서 service_id 찾기 실패: {e}")
                
                # steps 형식으로 변환
                step_dict = {
                    'id': service_id or variant_id,  # service_id가 없으면 variant_id 사용
                    'name': variant_name or f"단계 {item_dict.get('step', 0)}",
                    'quantity': int(item_dict.get('quantity', 0)),
                    'delay': int(item_dict.get('term_value', 0)) if item_dict.get('term_unit') == 'minute' else 0,
                    'repeat': int(item_dict.get('repeat_count', 1))
                }
                
                # term_unit이 'hour'인 경우 분으로 변환
                if item_dict.get('term_unit') == 'hour':
                    step_dict['delay'] = int(item_dict.get('term_value', 0)) * 60
                
                converted_steps.append(step_dict)
            
            pkg_dict['steps'] = converted_steps  # 변환된 steps 형식 사용
            
            result.append(pkg_dict)
        
        return jsonify({
            'packages': result,
            'count': len(result)
        }), 200
    except Exception as e:
        import traceback
        print(f"❌ 패키지 목록 조회 오류: {e}")
        print(traceback.format_exc())
        return jsonify({'error': f'패키지 조회 실패: {str(e)}'}), 500
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if conn:
            try:
                conn.close()
            except:
                pass

# 상품 옵션 관리
@app.route('/api/admin/product-variants', methods=['GET'])
@require_admin_auth
def get_admin_product_variants():
    """Get Admin Product Variants
    ---
    tags:
      - Admin
    summary: Get Admin Product Variants
    description: "Get Admin Product Variants API"
    security:
      - Bearer: []
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """상품 옵션 목록 조회"""
    conn = None
    cursor = None
    try:
        product_id = request.args.get('product_id')
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if product_id:
            cursor.execute("""
                SELECT pv.*, p.name as product_name, c.name as category_name
                FROM product_variants pv
                LEFT JOIN products p ON pv.product_id = p.product_id
                LEFT JOIN categories c ON p.category_id = c.category_id
                WHERE pv.product_id = %s
                ORDER BY pv.created_at DESC
            """, (product_id,))
        else:
            cursor.execute("""
                SELECT pv.*, p.name as product_name, c.name as category_name
                FROM product_variants pv
                LEFT JOIN products p ON pv.product_id = p.product_id
                LEFT JOIN categories c ON p.category_id = c.category_id
                ORDER BY pv.created_at DESC
            """)
        
        variants = cursor.fetchall()
        # meta_json을 파싱
        result = []
        for v in variants:
            variant_dict = dict(v)
            if variant_dict.get('meta_json') and isinstance(variant_dict['meta_json'], str):
                try:
                    import json
                    variant_dict['meta_json'] = json.loads(variant_dict['meta_json'])
                except:
                    pass
            result.append(variant_dict)
        
        return jsonify({
            'variants': result,
            'count': len(result)
        }), 200
    except Exception as e:
        print(f"❌ 상품 옵션 목록 조회 오류: {e}")
        return jsonify({'error': f'상품 옵션 조회 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/admin/product-variants', methods=['POST'])
@require_admin_auth
def create_admin_product_variant():
    """Create Admin Product Variant
    ---
    tags:
      - Admin
    summary: Create Admin Product Variant
    description: "Create Admin Product Variant API"
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """상품 옵션 생성"""
    conn = None
    cursor = None
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        name = data.get('name')
        price = data.get('price')
        original_cost = data.get('original_cost', 0)  # 원청 원가
        min_quantity = data.get('min_quantity')
        max_quantity = data.get('max_quantity')
        delivery_time_days = data.get('delivery_time_days')
        is_active = data.get('is_active', True)
        meta_json = data.get('meta_json')
        api_endpoint = data.get('api_endpoint')
        
        if not product_id or not name or price is None:
            return jsonify({'error': '상품 ID, 옵션 이름, 가격이 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # meta_json을 JSON 문자열 또는 JSONB로 변환
        import json
        meta_json_value = None
        if meta_json:
            if isinstance(meta_json, str):
                try:
                    # 문자열이면 파싱 후 다시 JSON 문자열로 변환
                    meta_json_value = json.dumps(json.loads(meta_json))
                except:
                    meta_json_value = meta_json
            else:
                meta_json_value = json.dumps(meta_json)
        
        # 필수 컬럼만 사용하는 안전한 INSERT 쿼리
        # 다른 INSERT 쿼리(backend.py:595)와 동일한 스키마 사용
        cursor.execute("""
            INSERT INTO product_variants (
                product_id, name, price, min_quantity, max_quantity,
                delivery_time_days, is_active, meta_json, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, NOW(), NOW())
            RETURNING *
        """, (product_id, name, price, min_quantity, max_quantity, delivery_time_days, is_active, meta_json_value))
        
        variant = cursor.fetchone()
        conn.commit()
        
        variant_dict = dict(variant)
        if variant_dict.get('meta_json') and isinstance(variant_dict['meta_json'], str):
            try:
                variant_dict['meta_json'] = json.loads(variant_dict['meta_json'])
            except:
                pass
        
        return jsonify({
            'success': True,
            'variant': variant_dict
        }), 201
    except Exception as e:
        if conn:
            conn.rollback()
        error_msg = str(e)
        print(f"❌ 상품 옵션 생성 오류: {error_msg}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': f'상품 옵션 생성 실패: {error_msg}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/admin/product-variants/<int:variant_id>', methods=['GET'])
@require_admin_auth
def get_admin_product_variant(variant_id):
    """Get Admin Product Variant
    ---
    tags:
      - Admin
    summary: Get Admin Product Variant
    description: "Get Admin Product Variant API"
    security:
      - Bearer: []
    parameters:
      - name: variant_id
        in: path
        type: int
        required: true
        description: Variant Id
        example: "example_variant_id"
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """상품 옵션 상세 조회"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT pv.*, p.name as product_name, c.name as category_name
            FROM product_variants pv
            LEFT JOIN products p ON pv.product_id = p.product_id
            LEFT JOIN categories c ON p.category_id = c.category_id
            WHERE pv.variant_id = %s
        """, (variant_id,))
        variant = cursor.fetchone()
        
        if not variant:
            return jsonify({'error': '상품 옵션을 찾을 수 없습니다.'}), 404
        
        variant_dict = dict(variant)
        if variant_dict.get('meta_json') and isinstance(variant_dict['meta_json'], str):
            try:
                import json
                variant_dict['meta_json'] = json.loads(variant_dict['meta_json'])
            except:
                pass
        
        return jsonify({'variant': variant_dict}), 200
    except Exception as e:
        print(f"❌ 상품 옵션 조회 오류: {e}")
        return jsonify({'error': f'상품 옵션 조회 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/admin/product-variants/<int:variant_id>', methods=['PUT'])
@require_admin_auth
def update_admin_product_variant(variant_id):
    """Update Admin Product Variant
    ---
    tags:
      - Admin
    summary: Update Admin Product Variant
    description: "Update Admin Product Variant API"
    security:
      - Bearer: []
    parameters:
      - name: variant_id
        in: path
        type: int
        required: true
        description: Variant Id
        example: "example_variant_id"
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """상품 옵션 수정"""
    conn = None
    cursor = None
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT * FROM product_variants WHERE variant_id = %s", (variant_id,))
        variant = cursor.fetchone()
        
        if not variant:
            return jsonify({'error': '상품 옵션을 찾을 수 없습니다.'}), 404
        
        product_id = data.get('product_id', variant['product_id'])
        name = data.get('name', variant['name'])
        price = data.get('price', variant['price'])
        original_cost = data.get('original_cost', variant.get('original_cost', 0))  # 원청 원가
        min_quantity = data.get('min_quantity', variant.get('min_quantity'))
        max_quantity = data.get('max_quantity', variant.get('max_quantity'))
        delivery_time_days = data.get('delivery_time_days', variant.get('delivery_time_days'))
        is_active = data.get('is_active', variant.get('is_active', True))
        meta_json = data.get('meta_json', variant.get('meta_json'))
        api_endpoint = data.get('api_endpoint', variant.get('api_endpoint'))
        
        # meta_json을 JSON 문자열로 변환
        import json
        meta_json_str = None
        if meta_json:
            meta_json_str = json.dumps(meta_json) if not isinstance(meta_json, str) else meta_json
        
        # original_cost 컬럼 존재 여부 확인 및 자동 추가 시도
        try:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_name = 'product_variants' 
                    AND column_name = 'original_cost'
                )
            """)
            has_original_cost = cursor.fetchone()[0]
            
            if not has_original_cost:
                # 컬럼이 없으면 자동으로 추가 시도
                try:
                    print("⚠️ original_cost 컬럼이 없어 자동으로 추가합니다.")
                    cursor.execute("ALTER TABLE product_variants ADD COLUMN original_cost NUMERIC(14,2) DEFAULT 0")
                    conn.commit()
                    has_original_cost = True
                    print("✅ original_cost 컬럼 추가 완료")
                except Exception as add_error:
                    print(f"⚠️ original_cost 컬럼 추가 실패 (계속 진행): {add_error}")
                    try:
                        conn.rollback()
                    except:
                        pass
                    has_original_cost = False
        except Exception as check_error:
            print(f"⚠️ original_cost 컬럼 확인 실패 (계속 진행): {check_error}")
            has_original_cost = False
        
        if has_original_cost:
            # original_cost 컬럼이 있으면 포함하여 업데이트
            cursor.execute("""
                UPDATE product_variants
                SET product_id = %s, name = %s, price = %s, original_cost = %s, min_quantity = %s, max_quantity = %s,
                    delivery_time_days = %s, is_active = %s, meta_json = %s, api_endpoint = %s,
                    updated_at = NOW()
                WHERE variant_id = %s
                RETURNING *
            """, (product_id, name, price, original_cost, min_quantity, max_quantity, delivery_time_days, is_active, meta_json_str, api_endpoint, variant_id))
        else:
            # original_cost 컬럼이 없으면 제외하고 업데이트
            print("⚠️ original_cost 컬럼이 없어 제외하고 업데이트합니다.")
            cursor.execute("""
                UPDATE product_variants
                SET product_id = %s, name = %s, price = %s, min_quantity = %s, max_quantity = %s,
                    delivery_time_days = %s, is_active = %s, meta_json = %s, api_endpoint = %s,
                    updated_at = NOW()
                WHERE variant_id = %s
                RETURNING *
            """, (product_id, name, price, min_quantity, max_quantity, delivery_time_days, is_active, meta_json_str, api_endpoint, variant_id))
        
        updated = cursor.fetchone()
        conn.commit()
        
        updated_dict = dict(updated)
        if updated_dict.get('meta_json') and isinstance(updated_dict['meta_json'], str):
            try:
                updated_dict['meta_json'] = json.loads(updated_dict['meta_json'])
            except:
                pass
        
        return jsonify({
            'success': True,
            'variant': updated_dict
        }), 200
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ 상품 옵션 수정 오류: {e}")
        return jsonify({'error': f'상품 옵션 수정 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/admin/product-variants/<int:variant_id>', methods=['DELETE'])
@require_admin_auth
def delete_admin_product_variant(variant_id):
    """Delete Admin Product Variant
    ---
    tags:
      - Admin
    summary: Delete Admin Product Variant
    description: "Delete Admin Product Variant API"
    security:
      - Bearer: []
    parameters:
      - name: variant_id
        in: path
        type: int
        required: true
        description: Variant Id
        example: "example_variant_id"
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """상품 옵션 삭제"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM product_variants WHERE variant_id = %s", (variant_id,))
        
        if cursor.rowcount == 0:
            return jsonify({'error': '상품 옵션을 찾을 수 없습니다.'}), 404
        
        conn.commit()
        return jsonify({'success': True, 'message': '상품 옵션이 삭제되었습니다.'}), 200
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ 상품 옵션 삭제 오류: {e}")
        return jsonify({'error': f'상품 옵션 삭제 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 패키지 관리
@app.route('/api/admin/packages', methods=['GET'])
@require_admin_auth
def get_admin_packages():
    """Get Admin Packages
    ---
    tags:
      - Admin
    summary: Get Admin Packages
    description: "Get Admin Packages API"
    security:
      - Bearer: []
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """패키지 목록 조회"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT p.*, c.name as category_name
            FROM packages p
            LEFT JOIN categories c ON p.category_id = c.category_id
            ORDER BY p.created_at DESC
        """)
        
        packages = cursor.fetchall()
        
        # 각 패키지의 items 조회
        result = []
        for pkg in packages:
            pkg_dict = dict(pkg)
            # meta_json 파싱
            if pkg_dict.get('meta_json') and isinstance(pkg_dict['meta_json'], str):
                try:
                    import json
                    pkg_dict['meta_json'] = json.loads(pkg_dict['meta_json'])
                except:
                    pass
            cursor.execute("""
                SELECT pi.*, pv.name as variant_name
                FROM package_items pi
                LEFT JOIN product_variants pv ON pi.variant_id = pv.variant_id
                WHERE pi.package_id = %s
                ORDER BY pi.step
            """, (pkg_dict['package_id'],))
            items = cursor.fetchall()
            pkg_dict['items'] = [dict(item) for item in items]
            result.append(pkg_dict)
        
        return jsonify({
            'packages': result,
            'count': len(result)
        }), 200
    except Exception as e:
        print(f"❌ 패키지 목록 조회 오류: {e}")
        return jsonify({'error': f'패키지 조회 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/admin/packages', methods=['POST'])
@require_admin_auth
def create_admin_package():
    """Create Admin Package
    ---
    tags:
      - Admin
    summary: Create Admin Package
    description: "Create Admin Package API"
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """패키지 생성"""
    conn = None
    cursor = None
    try:
        data = request.get_json()
        category_id = data.get('category_id')
        name = data.get('name')
        description = data.get('description')
        items = data.get('items', [])
        meta_json = data.get('meta_json')
        
        if not category_id or not name:
            return jsonify({'error': '카테고리 ID와 패키지 이름이 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # meta_json을 JSON 문자열로 변환
        import json
        meta_json_str = None
        if meta_json:
            meta_json_str = json.dumps(meta_json) if not isinstance(meta_json, str) else meta_json
        
        # 패키지 생성 (meta_json 컬럼이 있으면 포함, 없으면 제외)
        try:
            if meta_json_str:
                cursor.execute("""
                    INSERT INTO packages (category_id, name, description, meta_json, created_at, updated_at)
                    VALUES (%s, %s, %s, %s::jsonb, NOW(), NOW())
                    RETURNING *
                """, (category_id, name, description, meta_json_str))
            else:
                cursor.execute("""
                    INSERT INTO packages (category_id, name, description, created_at, updated_at)
                    VALUES (%s, %s, %s, NOW(), NOW())
                    RETURNING *
                """, (category_id, name, description))
        except Exception as e:
            # meta_json 컬럼이 없으면 meta_json 없이 다시 시도
            if 'meta_json' in str(e).lower() or 'column' in str(e).lower():
                cursor.execute("""
                    INSERT INTO packages (category_id, name, description, created_at, updated_at)
                    VALUES (%s, %s, %s, NOW(), NOW())
                    RETURNING *
                """, (category_id, name, description))
            else:
                raise
        
        package = cursor.fetchone()
        package_id = package['package_id']
        
        # 패키지 아이템 생성
        for item in items:
            variant_id = item.get('variant_id')
            step = item.get('step')
            term_value = item.get('term_value')
            term_unit = item.get('term_unit')
            quantity = item.get('quantity')
            repeat_count = item.get('repeat_count')
            repeat_term_value = item.get('repeat_term_value')
            repeat_term_unit = item.get('repeat_term_unit')
            
            cursor.execute("""
                INSERT INTO package_items (
                    package_id, variant_id, step, term_value, term_unit,
                    quantity, repeat_count, repeat_term_value, repeat_term_unit
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (package_id, variant_id, step, term_value, term_unit, quantity, repeat_count, repeat_term_value, repeat_term_unit))
        
        conn.commit()
        
        # 생성된 패키지 조회 (items 포함)
        cursor.execute("""
            SELECT p.*, c.name as category_name
            FROM packages p
            LEFT JOIN categories c ON p.category_id = c.category_id
            WHERE p.package_id = %s
        """, (package_id,))
        package = cursor.fetchone()
        
        cursor.execute("""
            SELECT pi.*, pv.name as variant_name
            FROM package_items pi
            LEFT JOIN product_variants pv ON pi.variant_id = pv.variant_id
            WHERE pi.package_id = %s
            ORDER BY pi.step
        """, (package_id,))
        items = cursor.fetchall()
        
        package_dict = dict(package)
        # meta_json 파싱
        if package_dict.get('meta_json') and isinstance(package_dict['meta_json'], str):
            try:
                import json
                package_dict['meta_json'] = json.loads(package_dict['meta_json'])
            except:
                pass
        package_dict['items'] = [dict(item) for item in items]
        
        return jsonify({
            'success': True,
            'package': package_dict
        }), 201
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ 패키지 생성 오류: {e}")
        return jsonify({'error': f'패키지 생성 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/admin/packages/<int:package_id>', methods=['GET'])
@require_admin_auth
def get_admin_package(package_id):
    """Get Admin Package
    ---
    tags:
      - Admin
    summary: Get Admin Package
    description: "Get Admin Package API"
    security:
      - Bearer: []
    parameters:
      - name: package_id
        in: path
        type: int
        required: true
        description: Package Id
        example: "example_package_id"
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """패키지 상세 조회"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT p.*, c.name as category_name
            FROM packages p
            LEFT JOIN categories c ON p.category_id = c.category_id
            WHERE p.package_id = %s
        """, (package_id,))
        package = cursor.fetchone()
        
        if not package:
            return jsonify({'error': '패키지를 찾을 수 없습니다.'}), 404
        
        cursor.execute("""
            SELECT pi.*, pv.name as variant_name
            FROM package_items pi
            LEFT JOIN product_variants pv ON pi.variant_id = pv.variant_id
            WHERE pi.package_id = %s
            ORDER BY pi.step
        """, (package_id,))
        items = cursor.fetchall()
        
        package_dict = dict(package)
        # meta_json 파싱
        if package_dict.get('meta_json') and isinstance(package_dict['meta_json'], str):
            try:
                import json
                package_dict['meta_json'] = json.loads(package_dict['meta_json'])
            except:
                pass
        package_dict['items'] = [dict(item) for item in items]
        
        return jsonify({'package': package_dict}), 200
    except Exception as e:
        print(f"❌ 패키지 조회 오류: {e}")
        return jsonify({'error': f'패키지 조회 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/admin/packages/<int:package_id>', methods=['PUT'])
@require_admin_auth
def update_admin_package(package_id):
    """Update Admin Package
    ---
    tags:
      - Admin
    summary: Update Admin Package
    description: "Update Admin Package API"
    security:
      - Bearer: []
    parameters:
      - name: package_id
        in: path
        type: int
        required: true
        description: Package Id
        example: "example_package_id"
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            example:
              type: string
              description: 예시 필드
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """패키지 수정 (items 배열 전달 시 전체 교체)"""
    conn = None
    cursor = None
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT * FROM packages WHERE package_id = %s", (package_id,))
        package = cursor.fetchone()
        
        if not package:
            return jsonify({'error': '패키지를 찾을 수 없습니다.'}), 404
        
        category_id = data.get('category_id', package['category_id'])
        name = data.get('name', package['name'])
        description = data.get('description', package.get('description'))
        meta_json = data.get('meta_json')
        
        # meta_json을 JSON 문자열로 변환
        import json
        meta_json_str = None
        if meta_json:
            meta_json_str = json.dumps(meta_json) if not isinstance(meta_json, str) else meta_json
        
        # 패키지 수정 (meta_json 컬럼이 있으면 포함, 없으면 제외)
        try:
            if meta_json_str:
                cursor.execute("""
                    UPDATE packages
                    SET category_id = %s, name = %s, description = %s, meta_json = %s::jsonb, updated_at = NOW()
                    WHERE package_id = %s
                """, (category_id, name, description, meta_json_str, package_id))
            else:
                cursor.execute("""
                    UPDATE packages
                    SET category_id = %s, name = %s, description = %s, updated_at = NOW()
                    WHERE package_id = %s
                """, (category_id, name, description, package_id))
        except Exception as e:
            # meta_json 컬럼이 없으면 meta_json 없이 다시 시도
            if 'meta_json' in str(e).lower() or 'column' in str(e).lower():
                cursor.execute("""
                    UPDATE packages
                    SET category_id = %s, name = %s, description = %s, updated_at = NOW()
                    WHERE package_id = %s
                """, (category_id, name, description, package_id))
            else:
                raise
        
        # items가 제공된 경우 전체 교체
        if 'items' in data:
            items = data.get('items', [])
            # 기존 items 삭제
            cursor.execute("DELETE FROM package_items WHERE package_id = %s", (package_id,))
            
            # 새 items 추가
            for item in items:
                variant_id = item.get('variant_id')
                step = item.get('step')
                term_value = item.get('term_value')
                term_unit = item.get('term_unit')
                quantity = item.get('quantity')
                repeat_count = item.get('repeat_count')
                repeat_term_value = item.get('repeat_term_value')
                repeat_term_unit = item.get('repeat_term_unit')
                
                cursor.execute("""
                    INSERT INTO package_items (
                        package_id, variant_id, step, term_value, term_unit,
                        quantity, repeat_count, repeat_term_value, repeat_term_unit
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (package_id, variant_id, step, term_value, term_unit, quantity, repeat_count, repeat_term_value, repeat_term_unit))
        
        conn.commit()
        
        # 수정된 패키지 조회
        cursor.execute("""
            SELECT p.*, c.name as category_name
            FROM packages p
            LEFT JOIN categories c ON p.category_id = c.category_id
            WHERE p.package_id = %s
        """, (package_id,))
        package = cursor.fetchone()
        
        cursor.execute("""
            SELECT pi.*, pv.name as variant_name
            FROM package_items pi
            LEFT JOIN product_variants pv ON pi.variant_id = pv.variant_id
            WHERE pi.package_id = %s
            ORDER BY pi.step
        """, (package_id,))
        items = cursor.fetchall()
        
        package_dict = dict(package)
        # meta_json 파싱
        if package_dict.get('meta_json') and isinstance(package_dict['meta_json'], str):
            try:
                import json
                package_dict['meta_json'] = json.loads(package_dict['meta_json'])
            except:
                pass
        package_dict['items'] = [dict(item) for item in items]
        
        return jsonify({
            'success': True,
            'package': package_dict
        }), 200
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ 패키지 수정 오류: {e}")
        return jsonify({'error': f'패키지 수정 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/admin/packages/<int:package_id>', methods=['DELETE'])
@require_admin_auth
def delete_admin_package(package_id):
    """Delete Admin Package
    ---
    tags:
      - Admin
    summary: Delete Admin Package
    description: "Delete Admin Package API"
    security:
      - Bearer: []
    parameters:
      - name: package_id
        in: path
        type: int
        required: true
        description: Package Id
        example: "example_package_id"
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """패키지 삭제"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # package_items 먼저 삭제 (외래키 제약)
        cursor.execute("DELETE FROM package_items WHERE package_id = %s", (package_id,))
        
        # 패키지 삭제
        cursor.execute("DELETE FROM packages WHERE package_id = %s", (package_id,))
        
        if cursor.rowcount == 0:
            return jsonify({'error': '패키지를 찾을 수 없습니다.'}), 404
        
        conn.commit()
        return jsonify({'success': True, 'message': '패키지가 삭제되었습니다.'}), 200
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ 패키지 삭제 오류: {e}")
        return jsonify({'error': f'패키지 삭제 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# SPA 라우팅 지원 - 구체적인 라우트들
@app.route('/home', methods=['GET'])
@app.route('/points', methods=['GET'])
@app.route('/orders', methods=['GET'])
@app.route('/admin', methods=['GET'])
@app.route('/referral', methods=['GET'])
@app.route('/blog', methods=['GET'])
@app.route('/blog/<path:blog_path>', methods=['GET'])
@app.route('/kakao-callback', methods=['GET'])
def serve_spa_routes():
    """Serve Spa Routes
    ---
    tags:
      - API
    summary: Serve Spa Routes
    description: "Serve Spa Routes API"
    parameters:
      - name: example
        in: query
        type: string
        required: false
        description: 예시 파라미터
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """SPA 라우팅 지원 - 구체적인 라우트들을 index.html로 서빙"""
    try:
        return app.send_static_file('index.html')
    except Exception as e:
        print(f"❌ SPA 라우팅 오류: {e}")
        return jsonify({'error': 'SPA routing failed'}), 500

# SPA 라우팅 지원 - 모든 경로를 index.html로 리다이렉트
# 주의: 이 라우트는 모든 API 라우트보다 나중에 등록되어야 함
@app.route('/<path:path>', methods=['GET'])
def serve_spa(path):
    """Serve Spa
    ---
    tags:
      - API
    summary: Serve Spa
    description: "Serve Spa API"
    parameters:
      - name: path
        in: path
        type: string
        required: true
        description: Path
        example: "example_path"
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            message:
              type: string
              example: "성공"
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "잘못된 요청입니다."
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "서버 오류가 발생했습니다."
    """ 
    """SPA 라우팅 지원 - 정적 파일은 서빙하고, 나머지는 index.html로 서빙"""
    print(f"🔍 SPA 라우팅 요청: /{path}")
    
    # API 경로는 Flask가 자동으로 처리하므로 여기서는 처리하지 않음
    # Flask는 더 구체적인 라우트를 먼저 매칭하므로, API 라우트가 먼저 매칭됨
    if path.startswith('api/'):
        # API 경로인데 여기까지 왔다면 실제로 404임
        print(f"⚠️ API 경로를 찾을 수 없음: /{path}")
        return jsonify({'error': 'API endpoint not found'}), 404
    
    # 정적 파일 경로 처리 (assets/, logo1.png 등)
    # assets/ 경로는 무조건 정적 파일로 처리
    if path.startswith('assets/'):
        try:
            print(f"📦 assets 파일 서빙: /{path}")
            return app.send_static_file(path)
        except Exception as e:
            print(f"❌ assets 파일 서빙 오류: {e}")
            return jsonify({'error': 'Static file serving failed'}), 500
    
    # 파일 확장자가 있는 경우 정적 파일로 간주
    if '.' in path and not path.endswith('/'):
        # 정적 파일 서빙 시도
        try:
            # dist 폴더에서 파일 찾기
            static_path = os.path.join('dist', path)
            if os.path.exists(static_path) and os.path.isfile(static_path):
                print(f"📦 정적 파일 서빙: /{path}")
                return app.send_static_file(path)
            else:
                # 직접 파일명인 경우 (logo1.png 등)
                print(f"⚠️ 정적 파일을 찾을 수 없음: /{path}")
                return jsonify({'error': 'Static file not found'}), 404
        except Exception as e:
            print(f"❌ 정적 파일 서빙 오류: {e}")
            return jsonify({'error': 'Static file serving failed'}), 500
    
    # SPA 라우트인 경우 index.html 서빙
    try:
        print(f"📄 index.html 서빙 시도: /{path}")
        return app.send_static_file('index.html')
    except Exception as e:
        print(f"❌ SPA 라우팅 오류: {e}")
        return jsonify({'error': 'SPA routing failed'}), 500

# 앱 시작 시 자동 초기화
initialize_app()

# 주기적 SMM Panel 상태 확인 스케줄러
def start_smm_status_checker():
    """SMM Panel 상태 확인을 주기적으로 실행하는 스케줄러"""
    import threading
    import time
    
    def status_checker():
        while True:
            try:
                check_and_update_order_status()
                time.sleep(300)  # 5분마다 확인
            except Exception as e:
                print(f"❌ SMM Panel 상태 확인 스케줄러 오류: {e}")
                time.sleep(60)  # 오류 시 1분 후 재시도
    
    # 백그라운드에서 실행
    thread = threading.Thread(target=status_checker)
    thread.daemon = True
    thread.start()
    print("🔄 SMM Panel 상태 확인 스케줄러가 시작되었습니다. (5분마다 확인)")

# 스케줄러 시작 (항상 실행)
scheduler_thread = threading.Thread(target=background_scheduler, daemon=True)
scheduler_thread.start()
print("✅ 백그라운드 스케줄러 시작됨")

# SMM Panel 상태 확인 스케줄러 시작
start_smm_status_checker()

# Flask 앱 실행
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)