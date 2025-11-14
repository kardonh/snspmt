import os
import json
import re
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

# 정적 파일 서빙 설정
@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
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

# 관리자 인증 데코레이터
def require_admin_auth(f):
    """관리자 권한이 필요한 엔드포인트용 데코레이터"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # X-Admin-Token 헤더 확인
        admin_token = request.headers.get('X-Admin-Token')
        expected_token = os.environ.get('ADMIN_TOKEN', 'admin_sociality_2024')
        
        if not admin_token or not expected_token or admin_token != expected_token:
            return jsonify({'error': '관리자 권한이 필요합니다.'}), 403
        
        return f(*args, **kwargs)
    
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
    return app.send_static_file('sitemap.xml')

# rss.xml 서빙
@app.route('/rss.xml')
def rss():
    return app.send_static_file('rss.xml')

# 멈춰있는 패키지 주문 재처리
@app.route('/api/admin/reprocess-package-orders', methods=['POST'])
@require_admin_auth
def reprocess_package_orders():
    """멈춰있는 패키지 주문들을 재처리"""
    conn = None
    cursor = None
    
    try:
        print("🔄 관리자 요청: 멈춰있는 패키지 주문 재처리")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # package_processing 상태인 주문들을 pending으로 변경
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                UPDATE orders SET status = 'pending' 
                WHERE status = 'package_processing' AND package_steps IS NOT NULL
            """)
        else:
            cursor.execute("""
                UPDATE orders SET status = 'pending' 
                WHERE status = 'package_processing' AND package_steps IS NOT NULL
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
        
        # 예약 주문 저장
        package_steps = data.get('package_steps', [])
        runs = data.get('runs', 1)  # Drip-feed: 기본값 1
        interval = data.get('interval', 0)  # Drip-feed: 기본값 0
        print(f"🔍 예약 주문 저장: 사용자={user_id}, 서비스={service_id}, 예약시간={scheduled_datetime}, 패키지단계={len(package_steps)}개, runs={runs}, interval={interval}")
        
        # order_id 생성
        import time
        order_id = f"ORDER_{int(time.time())}_{user_id[:8]}"
        
        # orders 테이블에 예약 주문 저장
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                INSERT INTO orders 
                (order_id, user_id, service_id, link, quantity, price, status, is_scheduled, scheduled_datetime, package_steps, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, 'scheduled', TRUE, %s, %s, NOW(), NOW())
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
                        # 누적 delay 계산
                        from datetime import datetime, timedelta
                        if isinstance(scheduled_datetime, str):
                            scheduled_time = datetime.fromisoformat(scheduled_datetime.replace('Z', '+00:00'))
                        scheduled_time = scheduled_time + timedelta(minutes=step_delay)
                    
                    cursor.execute("""
                        INSERT INTO execution_progress 
                        (order_id, exec_type, step_number, step_name, service_id, quantity, scheduled_datetime, status, created_at)
                        VALUES (%s, 'package', %s, %s, %s, %s, %s, 'scheduled', NOW())
                        ON CONFLICT (order_id, exec_type, step_number) DO NOTHING
                    """, (
                        order_id, idx + 1, step.get('name', f'단계 {idx + 1}'),
                        step.get('id'), step.get('quantity', 0), scheduled_time
                    ))
        else:
            cursor.execute("""
                INSERT INTO orders 
                (order_id, user_id, service_id, link, quantity, price, status, is_scheduled, scheduled_datetime, package_steps, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'scheduled', 1, ?, ?, datetime('now'), datetime('now'))
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
                        VALUES (?, 'package', ?, ?, ?, ?, ?, 'scheduled', datetime('now'))
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
        response = requests.post(smm_panel_url, json=payload, timeout=3)
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
        if not SMMPANEL_API_KEY:
            return {
                'status': 'error',
                'message': 'SMMPANEL_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.'
            }
        
        smm_panel_url = 'https://smmpanel.kr/api/v2'
        
        payload = {
            'key': SMMPANEL_API_KEY,
            'action': 'services'
        }
        
        response = requests.post(smm_panel_url, json=payload, timeout=30)
        
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
        return {
            'status': 'error',
            'message': f'네트워크 오류: {str(e)}'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'예상치 못한 오류: {str(e)}'
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
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT user_id, service_id, link, split_quantity, comments, split_days, package_steps
                FROM orders 
                WHERE order_id = %s AND (is_split_delivery = TRUE OR package_steps IS NOT NULL)
            """, (order_id,))
        else:
            cursor.execute("""
                SELECT user_id, service_id, link, split_quantity, comments, split_days, package_steps
                FROM orders 
                WHERE order_id = ? AND (is_split_delivery = TRUE OR package_steps IS NOT NULL)
            """, (order_id,))
        
        order = cursor.fetchone()
        if not order:
            return False
        
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
        
        # 주문 정보 조회
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT user_id, link, package_steps, comments
                FROM orders 
                WHERE order_id = %s
            """, (order_id,))
        else:
            cursor.execute("""
                SELECT user_id, link, package_steps, comments
                FROM orders 
                WHERE order_id = ?
            """, (order_id,))
        
        order = cursor.fetchone()
        if not order:
            print(f"❌ 패키지 주문 {order_id}을 찾을 수 없습니다.")
            return False
        
        user_id, link, package_steps_json, comments = order
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
                    """, (order_id, step_index + 2, f"{next_step_name} (예약됨)", next_step.get('id', 0), next_step.get('quantity', 0), None, 'scheduled', next_step.get('delay', 1440)))
                else:
                    cursor.execute("""
                        INSERT INTO execution_progress 
                        (order_id, exec_type, step_number, step_name, service_id, quantity, smm_panel_order_id, status, scheduled_datetime, created_at)
                        VALUES (?, 'package', ?, ?, ?, ?, ?, ?, datetime('now', '+' || ? || ' minutes'), datetime('now'))
                    """, (order_id, step_index + 2, f"{next_step_name} (예약됨)", next_step.get('id', 0), next_step.get('quantity', 0), None, 'scheduled', next_step.get('delay', 1440)))
                
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
        
        # package_processing 상태인 주문들 조회
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT order_id, package_steps FROM orders 
                WHERE status = 'package_processing' AND package_steps IS NOT NULL
                ORDER BY created_at ASC
            """)
        else:
            cursor.execute("""
                SELECT order_id, package_steps FROM orders 
                WHERE status = 'package_processing' AND package_steps IS NOT NULL
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
            cursor.execute("""
                SELECT order_id, smm_panel_order_id, created_at 
                FROM orders 
                WHERE status = '주문 실행중' 
                AND smm_panel_order_id IS NOT NULL
                AND created_at > NOW() - INTERVAL '25 hours'
                ORDER BY created_at DESC
                LIMIT 50
            """)
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
        
        # 새로운 주문 ID 생성 (더 작은 숫자 ID 사용)
        new_order_id = int(time.time() * 100) % 2147483647  # PostgreSQL INTEGER 최대값 미만
        
        # 실제 주문 생성
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                INSERT INTO orders 
                (order_id, user_id, platform, service_name, service_id, link, quantity, 
                 price, status, created_at, updated_at, is_scheduled, package_steps)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), FALSE, %s)
            """, (
                new_order_id, user_id, 'Instagram', 'Scheduled Package',
                service_id, link, quantity, price, 'pending', json.dumps(package_steps)
            ))
        else:
            cursor.execute("""
                INSERT INTO orders 
                (order_id, user_id, platform, service_name, service_id, link, quantity, 
                 price, status, created_at, updated_at, is_scheduled, package_steps)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), 0, ?)
            """, (
                new_order_id, user_id, 'Instagram', 'Scheduled Package',
                service_id, link, quantity, price, 'pending', json.dumps(package_steps)
            ))
        
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
        
        # 예약 주문 정보 조회
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT user_id, service_id, link, quantity, comments
                FROM orders 
                WHERE order_id = %s AND is_scheduled = TRUE
            """, (order_id,))
        else:
            cursor.execute("""
                SELECT user_id, service_id, link, quantity, comments
                FROM orders 
                WHERE order_id = ? AND is_scheduled = TRUE
            """, (order_id,))
        
        order = cursor.fetchone()
        if not order:
            return False
        
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
    try:
        # 프로덕션 환경에서는 로그 최소화
        if os.environ.get('FLASK_ENV') != 'production':
            pass
        
        # 함수 내에서 DATABASE_URL을 다시 읽어서 인코딩 문제 방지
        db_url = os.environ.get('DATABASE_URL') or DATABASE_URL
        if not db_url:
            raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다")
        
        # 연결 문자열을 명시적으로 UTF-8로 처리
        if isinstance(db_url, bytes):
            # bytes인 경우 UTF-8로 디코딩 시도, 실패 시 다른 인코딩 시도
            try:
                db_url = db_url.decode('utf-8')
            except UnicodeDecodeError:
                # UTF-8 실패 시 latin-1로 시도 (모든 바이트를 유효한 문자로 변환)
                db_url = db_url.decode('latin-1')
        else:
            # 문자열인 경우에도 안전하게 처리
            if not isinstance(db_url, str):
                db_url = str(db_url)
        
        # 문자열 정리 (BOM 제거 등)
        db_url = db_url.strip()
        if db_url.startswith('\ufeff'):  # UTF-8 BOM 제거
            db_url = db_url[1:]
        
        if db_url.startswith('postgresql://'):
            # urlparse가 인코딩 문제를 일으킬 수 있으므로 정규식으로 직접 파싱
            import re
            # 연결 문자열에서 문제가 될 수 있는 문자 제거 (보이지 않는 문자 등)
            db_url_clean = ''.join(c for c in db_url if c.isprintable() or c in ':/@%.-')
            
            # PostgreSQL 연결 문자열 파싱: postgresql://user:password@host:port/database
            # 더 유연한 정규식 패턴 사용
            match = re.match(r'postgresql://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?/(.+)', db_url_clean)
            if not match:
                # 더 간단한 패턴으로 재시도
                match = re.match(r'postgresql://([^:]+):([^@]+)@([^@]+)/(.+)', db_url_clean)
            
            if match:
                groups = match.groups()
                if len(groups) == 5:
                    username, password_encoded, hostname, port_str, database = groups
                    port = int(port_str) if port_str else 5432
                elif len(groups) == 4:
                    username, password_encoded, hostname_port, database = groups
                    # hostname:port 분리
                    if ':' in hostname_port:
                        hostname, port_str = hostname_port.rsplit(':', 1)
                        port = int(port_str) if port_str.isdigit() else 5432
                    else:
                        hostname = hostname_port
                        port = 5432
                else:
                    raise ValueError(f"정규식 매칭 그룹 수가 예상과 다릅니다: {len(groups)}")
                
                # 비밀번호 URL 디코딩
                try:
                    password = unquote(password_encoded)
                except Exception:
                    # unquote 실패 시 그대로 사용
                    password = password_encoded
                
                # 개별 파라미터로 연결 (인코딩 문제 방지)
                conn = psycopg2.connect(
                    host=hostname,
                    port=port,
                    database=database,
                    user=username,
                    password=password,
                    connect_timeout=30,
                    keepalives_idle=600,
                    keepalives_interval=30,
                    keepalives_count=3
                )
            else:
                # 정규식 파싱 실패 - 하드코딩된 값으로 직접 연결 시도
                print(f"⚠️ 정규식 파싱 실패, 직접 연결 시도")
                print(f"   연결 문자열 길이: {len(db_url_clean)}")
                print(f"   연결 문자열: {db_url_clean[:80]}...")
                
                # 하드코딩된 Supabase 연결 정보로 직접 연결
                # 이는 임시 해결책이며, .env 파일을 수정해야 합니다
                conn = psycopg2.connect(
                    host='db.gvtrizwkstaznrlloixi.supabase.co',
                    port=5432,
                    database='postgres',
                    user='postgres',
                    password='KARDONH0813!',  # URL 디코딩된 비밀번호
                    connect_timeout=30,
                    keepalives_idle=600,
                    keepalives_interval=30,
                    keepalives_count=3
                )
            
            # 자동 커밋 비활성화 (트랜잭션 제어를 위해)
            conn.autocommit = False
            return conn
        else:
            # SQLite fallback - 영구 데이터베이스 경로 사용
            db_path = os.path.join(os.getcwd(), 'data', 'snspmt.db')
            os.makedirs(os.path.dirname(db_path), exist_ok=True)  # 디렉토리 생성
            conn = sqlite3.connect(db_path, timeout=30)
            conn.row_factory = sqlite3.Row  # 딕셔너리 형태로 결과 반환
            return conn
    except psycopg2.Error as e:
        print(f"❌ PostgreSQL 연결 실패: {e}")
        raise
    except Exception as e:
        raise e

def init_database():
    """데이터베이스 테이블을 초기화합니다."""
    conn = None
    try:
        conn = get_db_connection()
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
            
            # 추천인 테이블 생성 (기존 데이터 보존)
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
            
            # commission_ledger 테이블 생성 (통합: commission_points, commission_payments, commissions 대체)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS commission_ledger (
                    ledger_id SERIAL PRIMARY KEY,
                    referral_code VARCHAR(50) NOT NULL,
                    referrer_user_id VARCHAR(255) NOT NULL,
                    referred_user_id VARCHAR(255),
                    order_id VARCHAR(255),
                    event VARCHAR(50) NOT NULL CHECK (event IN ('earn','payout','adjust','reverse')),
                    base_amount DECIMAL(10,2),
                    commission_rate DECIMAL(5,4),
                    amount DECIMAL(10,2) NOT NULL,
                    status VARCHAR(50) NOT NULL DEFAULT 'confirmed' CHECK (status IN ('pending','confirmed','cancelled')),
                    notes TEXT,
                    external_ref VARCHAR(100),
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    confirmed_at TIMESTAMP,
                    CONSTRAINT fk_ledger_code FOREIGN KEY (referral_code) REFERENCES referral_codes(code),
                    CONSTRAINT fk_ledger_owner FOREIGN KEY (referrer_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    CONSTRAINT fk_ledger_refer FOREIGN KEY (referred_user_id) REFERENCES users(user_id),
                    CONSTRAINT fk_ledger_order FOREIGN KEY (order_id) REFERENCES orders(order_id)
                )
            """)
            print("✅ commission_ledger 테이블 생성 완료 (통합 테이블)")
            
            # commission_ledger 인덱스 생성
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ledger_code_time ON commission_ledger(referral_code, created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ledger_owner_time ON commission_ledger(referrer_user_id, created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ledger_event_time ON commission_ledger(event, created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ledger_order ON commission_ledger(order_id)")
            print("✅ commission_ledger 인덱스 생성 완료")
            
            # orders.referral_code 외래 키 제약 조건 추가
            try:
                cursor.execute("""
                    SELECT constraint_name 
                    FROM information_schema.table_constraints 
                    WHERE table_name='orders' AND constraint_name='fk_orders_referral_code'
                """)
                if not cursor.fetchone():
                    cursor.execute("""
                        ALTER TABLE orders 
                        ADD CONSTRAINT fk_orders_referral_code 
                        FOREIGN KEY (referral_code) REFERENCES referral_codes(code)
                    """)
                    print("✅ orders.referral_code 외래 키 제약 조건 추가 완료")
            except Exception as e:
                print(f"⚠️ orders.referral_code 외래 키 추가 실패 (이미 존재할 수 있음): {e}")
            
            # commission_ledger 트리거 함수 생성 (referral_codes.total_commission 자동 동기화)
            cursor.execute("""
                CREATE OR REPLACE FUNCTION sync_referral_commission()
                RETURNS TRIGGER AS $$
                BEGIN
                  UPDATE referral_codes
                     SET total_commission = (
                       SELECT COALESCE(SUM(amount), 0)
                       FROM commission_ledger
                       WHERE referral_code = COALESCE(NEW.referral_code, OLD.referral_code)
                         AND status='confirmed'
                     )
                   WHERE code = COALESCE(NEW.referral_code, OLD.referral_code);
                  
                  RETURN COALESCE(NEW, OLD);
                END;
                $$ LANGUAGE plpgsql;
            """)
            
            # commission_ledger 트리거 생성
            cursor.execute("DROP TRIGGER IF EXISTS trg_commission_ai ON commission_ledger")
            cursor.execute("""
                CREATE TRIGGER trg_commission_ai AFTER INSERT ON commission_ledger
                FOR EACH ROW EXECUTE FUNCTION sync_referral_commission()
            """)
            cursor.execute("DROP TRIGGER IF EXISTS trg_commission_au ON commission_ledger")
            cursor.execute("""
                CREATE TRIGGER trg_commission_au AFTER UPDATE ON commission_ledger
                FOR EACH ROW EXECUTE FUNCTION sync_referral_commission()
            """)
            cursor.execute("DROP TRIGGER IF EXISTS trg_commission_ad ON commission_ledger")
            cursor.execute("""
                CREATE TRIGGER trg_commission_ad AFTER DELETE ON commission_ledger
                FOR EACH ROW EXECUTE FUNCTION sync_referral_commission()
            """)
            print("✅ commission_ledger 트리거 생성 완료 (referral_codes.total_commission 자동 동기화)")
            
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
        if is_postgresql:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS execution_progress (
                    exec_id SERIAL PRIMARY KEY,
                    order_id VARCHAR(255) NOT NULL,
                    exec_type VARCHAR(50) NOT NULL CHECK (exec_type IN ('package')),
                    step_number INTEGER NOT NULL,
                    step_name VARCHAR(255),
                    service_id VARCHAR(255),
                    quantity INTEGER,
                    scheduled_datetime TIMESTAMP,
                    priority SMALLINT NOT NULL DEFAULT 5,
                    lock_token VARCHAR(64),
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    last_error_at TIMESTAMP,
                    status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','running','completed','failed','skipped','scheduled')),
                    smm_panel_order_id VARCHAR(255),
                    error_message TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    failed_at TIMESTAMP,
                    CONSTRAINT fk_exec_order FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
                    CONSTRAINT ck_exec_qty CHECK (quantity IS NULL OR quantity >= 0),
                    CONSTRAINT uq_exec UNIQUE (order_id, exec_type, step_number)
                )
            """)
            print("✅ execution_progress 테이블 생성 완료 (통합 테이블)")
            
            # execution_progress 인덱스 생성
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_exec_key ON execution_progress(order_id, exec_type, step_number)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_exec_status_time ON execution_progress(status, scheduled_datetime)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_exec_status_time_prio ON execution_progress(status, scheduled_datetime, priority)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_exec_lock ON execution_progress(lock_token)")
            print("✅ execution_progress 인덱스 생성 완료")
            
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
                "CREATE INDEX IF NOT EXISTS idx_referral_codes_user_email ON referral_codes(user_email)",
                "CREATE INDEX IF NOT EXISTS idx_scheduled_orders_user_id ON scheduled_orders(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_scheduled_orders_status ON scheduled_orders(status)",
                "CREATE INDEX IF NOT EXISTS idx_scheduled_orders_datetime ON scheduled_orders(scheduled_datetime)",
                "CREATE INDEX IF NOT EXISTS idx_package_progress_order_id ON package_progress(order_id)",
                "CREATE INDEX IF NOT EXISTS idx_package_progress_status ON package_progress(status)",
                "CREATE INDEX IF NOT EXISTS idx_split_delivery_order_id ON split_delivery_progress(order_id)",
                "CREATE INDEX IF NOT EXISTS idx_commission_points_email ON commission_points(referrer_email)",
                "CREATE INDEX IF NOT EXISTS idx_commission_transactions_email ON commission_point_transactions(referrer_email)",
                "CREATE INDEX IF NOT EXISTS idx_withdrawal_requests_email ON commission_withdrawal_requests(referrer_email)",
                "CREATE INDEX IF NOT EXISTS idx_withdrawal_requests_status ON commission_withdrawal_requests(status)"
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
                "CREATE INDEX IF NOT EXISTS idx_referral_codes_user_email ON referral_codes(user_email)",
                "CREATE INDEX IF NOT EXISTS idx_scheduled_orders_user_id ON scheduled_orders(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_scheduled_orders_status ON scheduled_orders(status)",
                "CREATE INDEX IF NOT EXISTS idx_scheduled_orders_datetime ON scheduled_orders(scheduled_datetime)",
                "CREATE INDEX IF NOT EXISTS idx_package_progress_order_id ON package_progress(order_id)",
                "CREATE INDEX IF NOT EXISTS idx_package_progress_status ON package_progress(status)",
                "CREATE INDEX IF NOT EXISTS idx_split_delivery_order_id ON split_delivery_progress(order_id)",
                "CREATE INDEX IF NOT EXISTS idx_commission_points_email ON commission_points(referrer_email)",
                "CREATE INDEX IF NOT EXISTS idx_commission_transactions_email ON commission_point_transactions(referrer_email)",
                "CREATE INDEX IF NOT EXISTS idx_withdrawal_requests_email ON commission_withdrawal_requests(referrer_email)",
                "CREATE INDEX IF NOT EXISTS idx_withdrawal_requests_status ON commission_withdrawal_requests(status)"
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
    """헬스 체크 엔드포인트"""
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

@app.route('/api/deployment-status', methods=['GET'])
def deployment_status():
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
    """사용자 포인트 조회"""
    conn = None
    cursor = None
    
    try:
        user_id = request.args.get('user_id')
        print(f"🔍 포인트 조회 요청 - user_id: {user_id}")
        
        if not user_id:
            print(f"❌ user_id 누락")
            return jsonify({'error': 'user_id가 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("SELECT points FROM points WHERE user_id = %s", (user_id,))
        else:
            cursor.execute("SELECT points FROM points WHERE user_id = ?", (user_id,))
        
        result = cursor.fetchone()
        
        if result:
            points = result[0] if isinstance(result, tuple) else result['points']
            print(f"✅ 포인트 조회 성공: {points}")
        else:
            points = 0
            print(f"ℹ️ 포인트 데이터 없음, 기본값 0 설정")
        
        return jsonify({
            'user_id': user_id,
            'points': points
        }), 200
        
    except Exception as e:
        print(f"❌ 포인트 조회 오류: {e}")
        return jsonify({'error': f'포인트 조회 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 주문 생성
@app.route('/api/orders', methods=['POST'])
def create_order():
    """주문 생성 (할인 및 커미션 적용)"""
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
        
        # 사용자의 추천인 연결 확인
        if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT referral_code, referrer_email FROM user_referral_connections 
                WHERE user_id = %s
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT referral_code, referrer_email FROM user_referral_connections 
                WHERE user_id = ?
            """, (user_id,))
        
        referral_data = cursor.fetchone()
        discount_amount = 0
        final_price = price
        
        # 프론트엔드에서 전달받은 쿠폰 ID 확인
        coupon_id_from_request = data.get('coupon_id')
        
        # 쿠폰 사용 여부 확인
        if coupon_id_from_request:
            print(f"🎫 쿠폰 사용 요청 - 쿠폰 ID: {coupon_id_from_request}")
            
            # 쿠폰 유효성 확인
            if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    SELECT id, discount_value, referral_code FROM coupons 
                    WHERE id = %s AND user_id = %s AND is_used = false 
                    AND expires_at > NOW()
                """, (coupon_id_from_request, user_id))
            else:
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
                
                # 쿠폰 사용 처리
                if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
                    cursor.execute("""
                        UPDATE coupons SET is_used = true, used_at = NOW() 
                        WHERE id = %s
                    """, (coupon_id,))
                else:
                    cursor.execute("""
                        UPDATE coupons SET is_used = true, used_at = datetime('now') 
                        WHERE id = ?
                    """, (coupon_id,))
                
                print(f"✅ 쿠폰 사용 처리 완료 - 쿠폰 ID: {coupon_id}")
                
                # 사용자의 추천인 연결 정보 조회 (커미션 적립용)
                if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
                    cursor.execute("""
                        SELECT referral_code, referrer_email FROM user_referral_connections 
                        WHERE user_id = %s
                    """, (user_id,))
                else:
                    cursor.execute("""
                        SELECT referral_code, referrer_email FROM user_referral_connections 
                        WHERE user_id = ?
                    """, (user_id,))
                
                referral_data = cursor.fetchone()
            else:
                print(f"⚠️ 유효한 쿠폰을 찾을 수 없음 - 쿠폰 ID: {coupon_id_from_request}")
        else:
            # 쿠폰 미사용 시 추천인 연결 확인
            if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    SELECT referral_code, referrer_email FROM user_referral_connections 
                    WHERE user_id = %s
                """, (user_id,))
            else:
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
        
        # SMM Panel API 호출을 먼저 실행하여 실제 주문번호를 받아옴
        import time
        real_order_id = None
        smm_panel_order_id = None
        
        # 패키지 상품 여부 확인
        package_steps = data.get('package_steps', [])
        is_package = len(package_steps) > 0
        
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
                    real_order_id = smm_result.get('order')
                    smm_panel_order_id = real_order_id
                    print(f"✅ SMM Panel 주문 생성 성공: {real_order_id}")
                else:
                    print(f"❌ SMM Panel API 호출 실패: {smm_result.get('message')}")
                    return jsonify({'error': 'SMM Panel API 호출 실패'}), 500
            except Exception as e:
                print(f"❌ SMM Panel API 호출 실패: {e}")
                return jsonify({'error': 'SMM Panel API 호출 실패'}), 500
        elif is_package:
            # 패키지 주문은 임시 ID 사용 (패키지 단계별로 개별 처리)
            real_order_id = int(time.time())
            print(f"📦 패키지 주문 - 임시 ID 사용: {real_order_id} (패키지 단계별 개별 처리)")
        else:
            # 예약 주문은 임시 ID 사용 (나중에 예약 시간에 SMM Panel API 호출)
            real_order_id = int(time.time())
            print(f"📅 예약 주문 - 임시 ID 사용: {real_order_id}")
        
        # detailed_service 정보 가져오기
        detailed_service = data.get('detailed_service', '')
        
        # 주문 생성 (SMM Panel 주문번호 사용)
        if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                INSERT INTO orders (order_id, user_id, service_id, link, quantity, price, 
                                discount_amount, referral_code, status, created_at, updated_at,
                                is_scheduled, scheduled_datetime, is_split_delivery, split_days, split_quantity, smm_panel_order_id, detailed_service)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(),
                        %s, %s, %s, %s, %s, %s, %s)
            """, (real_order_id, user_id, service_id, link, quantity, final_price, discount_amount,
                referral_data[0] if referral_data else None, '주문발송' if not is_scheduled else 'pending_payment',
                is_scheduled, scheduled_datetime, is_split_delivery, split_days, split_quantity, smm_panel_order_id, detailed_service))
        else:
            cursor.execute("""
                INSERT INTO orders (order_id, user_id, service_id, link, quantity, price, 
                                discount_amount, referral_code, status, created_at, updated_at,
                                is_scheduled, scheduled_datetime, is_split_delivery, split_days, split_quantity, smm_panel_order_id, detailed_service)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                        ?, ?, ?, ?, ?, ?, ?)
            """, (real_order_id, user_id, service_id, link, quantity, final_price, discount_amount,
                referral_data[0] if referral_data else None, '주문발송' if not is_scheduled else 'pending_payment',
                is_scheduled, scheduled_datetime, is_split_delivery, split_days, split_quantity, smm_panel_order_id, detailed_service))
        
        order_id = real_order_id
        print(f"✅ 주문 생성 완료 - order_id: {order_id}, user_id: {user_id}, service_id: {service_id}, price: {final_price}")
        
        # 추천인이 있는 경우 10% 커미션 포인트 적립
        commission_amount = 0
        if referral_data:
            try:
                referrer_email = referral_data[1]
                commission_amount = final_price * 0.1  # 10% 커미션
                
                print(f"💰 커미션 계산 - 추천인: {referrer_email}, 구매금액: {final_price}, 커미션: {commission_amount}")
                
                # referral_code로 referrer_user_id 조회
                referral_code = referral_data[0]
                if DATABASE_URL.startswith('postgresql://'):
                    cursor.execute("SELECT user_id FROM referral_codes WHERE code = %s", (referral_code,))
                else:
                    cursor.execute("SELECT user_id FROM referral_codes WHERE code = ?", (referral_code,))
                referrer_user_result = cursor.fetchone()
                referrer_user_id = referrer_user_result[0] if referrer_user_result else referrer_email
                
                # commission_ledger에 커미션 적립 기록
                if DATABASE_URL.startswith('postgresql://'):
                    cursor.execute("""
                        INSERT INTO commission_ledger 
                        (referral_code, referrer_user_id, referred_user_id, order_id, event, base_amount, commission_rate, amount, status, notes, created_at, confirmed_at)
                        VALUES (%s, %s, %s, %s, 'earn', %s, %s, %s, 'confirmed', %s, NOW(), NOW())
                    """, (
                        referral_code, referrer_user_id, user_id, order_id,
                        final_price, 0.1, commission_amount,
                        f'추천인 커미션 적립 - 주문 ID: {order_id}'
                    ))
                else:
                    cursor.execute("""
                        INSERT INTO commission_ledger 
                        (referral_code, referrer_user_id, referred_user_id, order_id, event, base_amount, commission_rate, amount, status, notes, created_at, confirmed_at)
                        VALUES (?, ?, ?, ?, 'earn', ?, ?, ?, 'confirmed', ?, datetime('now'), datetime('now'))
                    """, (
                        referral_code, referrer_user_id, user_id, order_id,
                        final_price, 0.1, commission_amount,
                        f'추천인 커미션 적립 - 주문 ID: {order_id}'
                    ))
                
                print(f"✅ 커미션 포인트 적립 완료: {commission_amount}원")
            except Exception as commission_error:
                print(f"⚠️ 커미션 포인트 적립 실패 (주문은 계속 진행): {commission_error}")
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
            status = 'scheduled'
            message = '예약 주문이 생성되었습니다.'
        elif is_split_delivery:
            # 분할 주문은 나중에 처리하도록 스케줄링
            print(f"📅 분할 주문 - 즉시 처리하지 않음")
            status = 'split_scheduled'
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
            
            # 주문 상태를 package_processing으로 변경
            if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    UPDATE orders SET status = 'package_processing', updated_at = NOW()
                    WHERE order_id = %s
                """, (order_id,))
            else:
                cursor.execute("""
                    UPDATE orders SET status = 'package_processing', updated_at = CURRENT_TIMESTAMP
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
            
            status = 'package_processing'  # 패키지 처리 중 상태
            message = f'패키지 주문이 생성되었습니다. ({len(package_steps)}단계 순차 처리 중)'
        else:
            # 일반 주문은 이미 SMM Panel API 호출 완료됨
            status = '주문발송'
            message = '주문이 접수되어 진행중입니다.'
            
            # 2분 후 주문 실행중으로 변경하는 스케줄 설정
            schedule_order_status_update(order_id, '주문 실행중', 2)  # 2분 후
            
            # 24시간 후 주문 실행완료로 변경하는 스케줄 설정 (최대 대기시간)
            schedule_order_status_update(order_id, '주문 실행완료', 1440)  # 24시간 후
        
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
        import traceback
        print(f"❌ 스택 트레이스: {traceback.format_exc()}")
        if conn:
            conn.rollback()
        return jsonify({'error': f'주문 생성 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print("✅ 데이터베이스 연결 종료")

# 패키지 주문 처리 시작
@app.route('/api/orders/start-package-processing', methods=['POST'])
def start_package_processing():
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
        
        # 주문 정보 조회
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT order_id, user_id, link, package_steps, status 
                FROM orders 
                WHERE order_id = %s
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
        allowed_statuses = ['pending', 'pending_payment', 'package_processing', 'completed', '주문발송', '주문 실행중', '주문 실행완료', 'in_progress', 'processing']
        if status not in allowed_statuses:
            print(f"❌ 주문 {order_id} 상태가 처리 가능한 상태가 아닙니다. 현재 상태: {status}")
            return jsonify({'error': f'주문 상태가 처리할 수 없습니다. 현재 상태: {status}'}), 400
        
        # 이미 처리 중인 경우 성공으로 처리
        if status in ['package_processing', 'completed']:
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
        
        # 주문 상태를 package_processing으로 변경
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                UPDATE orders SET status = 'package_processing', updated_at = NOW()
                WHERE order_id = %s
            """, (order_id,))
        else:
            cursor.execute("""
                UPDATE orders SET status = 'package_processing', updated_at = CURRENT_TIMESTAMP
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
    """주문 목록 조회 (최적화된 버전)"""
    conn = None
    cursor = None
    
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id가 필요합니다.'}), 400
        
        print(f"🔍 주문 조회 시작 - user_id: {user_id}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 주문 정보 조회 - 최소한의 컬럼만 조회하여 성능 개선
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT order_id, service_id, link, quantity, price, status, created_at, 
                       smm_panel_order_id, detailed_service
                FROM orders 
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 10
            """, (user_id,))
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
                # 주문 데이터 처리
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
                remains = quantity
                
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
                
                # SMM Panel API에서 실제 사용 금액 조회 (성능을 위해 간소화)
                charge = 0
                if smm_panel_order_id and status in ['주문 실행중', '주문 실행완료']:
                    try:
                        # 처리 중이거나 완료된 주문만 SMM Panel API 호출
                        smm_status = call_smm_panel_api({
                            'action': 'status',
                            'order': smm_panel_order_id
                        })
                        
                        if smm_status.get('status') == 'success':
                            charge = smm_status.get('charge', 0)
                            print(f"✅ SMM Panel charge 조회 성공: {charge}")
                        else:
                            print(f"⚠️ SMM Panel charge 조회 실패: {smm_status.get('message')}")
                    except Exception as e:
                        print(f"⚠️ SMM Panel charge 조회 오류: {e}")
                        charge = 0
                
                # 서비스 이름 결정 (우선순위: detailed_service > get_service_name > 기본값)
                if detailed_service:
                    service_name = detailed_service
                else:
                    service_name = get_service_name(service_id)
                
                order_list.append({
                    'id': display_order_id,
                    'order_id': display_order_id,
                    'service_id': service_id,
                    'service_name': service_name,
                    'link': link,
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
    """포인트 구매 신청"""
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
                # 먼저 사용자가 이미 존재하는지 확인
                cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id_str,))
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
                                INSERT INTO users (user_id, email, name, created_at, updated_at)
                                VALUES (%s, %s, %s, NOW(), NOW())
                                ON CONFLICT (user_id) DO NOTHING
                            """, (user_id_str, user_email, buyer_name or 'User'))
                            print(f"✅ 재시도 성공: {user_id_str}", flush=True)
                        else:
                            # 다른 종류의 오류는 그대로 전파
                            raise
                
                # 사용자 존재 확인 (반드시 필요)
                cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id_str,))
                if not cursor.fetchone():
                    raise Exception(f"사용자 생성 실패: {user_id_str}가 users 테이블에 존재하지 않습니다.")
                print(f"✅ 사용자 확인 완료: {user_id_str}", flush=True)
                
                # 같은 트랜잭션 내에서 points 레코드 생성 (외래 키 제약 조건이 적용됨)
                cursor.execute("""
                    INSERT INTO points (user_id, points, created_at, updated_at)
                    VALUES (%s, 0, NOW(), NOW())
                    ON CONFLICT (user_id) DO NOTHING
                """, (user_id_str,))
                print(f"✅ 포인트 레코드 생성/확인 완료: {user_id_str}", flush=True)
                
                # 포인트 레코드 존재 확인
                cursor.execute("SELECT user_id FROM points WHERE user_id = %s", (user_id_str,))
                if not cursor.fetchone():
                    raise Exception(f"포인트 레코드 생성 실패: {user_id_str}가 points 테이블에 존재하지 않습니다.")
                
                # 같은 트랜잭션 내에서 point_purchases 삽입
                cursor.execute("""
                    INSERT INTO point_purchases (user_id, amount, price, status, buyer_name, bank_info, created_at, updated_at)
                    VALUES (%s, %s, %s, 'pending', %s, %s, NOW(), NOW())
                    RETURNING id
                """, (user_id_str, amount, price, buyer_name, bank_info))
                purchase_id = cursor.fetchone()[0]
                print(f"✅ 포인트 구매 삽입 완료: purchase_id={purchase_id}, user_id={user_id_str}", flush=True)
                
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
    """관리자 통계"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            # 총 사용자 수
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            # 총 주문 수
            cursor.execute("SELECT COUNT(*) FROM orders")
            total_orders = cursor.fetchone()[0]
            
            # 총 매출 (주문 + 포인트 구매)
            cursor.execute("""
                SELECT COALESCE(SUM(price), 0) FROM orders WHERE status = 'completed'
                UNION ALL
                SELECT COALESCE(SUM(price), 0) FROM point_purchases WHERE status = 'approved'
            """)
            order_revenue = cursor.fetchone()[0] if cursor.rowcount > 0 else 0
            cursor.execute("SELECT COALESCE(SUM(price), 0) FROM point_purchases WHERE status = 'approved'")
            purchase_revenue = cursor.fetchone()[0]
            total_revenue = order_revenue + purchase_revenue
            
            # 대기 중인 포인트 구매
            cursor.execute("SELECT COUNT(*) FROM point_purchases WHERE status = 'pending'")
            pending_purchases = cursor.fetchone()[0]
            
            # 오늘 주문 수
            cursor.execute("SELECT COUNT(*) FROM orders WHERE DATE(created_at) = CURRENT_DATE")
            today_orders = cursor.fetchone()[0]
            
            # 오늘 매출 (주문 + 포인트 구매)
            cursor.execute("SELECT COALESCE(SUM(price), 0) FROM orders WHERE DATE(created_at) = CURRENT_DATE AND status = 'completed'")
            today_order_revenue = cursor.fetchone()[0]
            cursor.execute("SELECT COALESCE(SUM(price), 0) FROM point_purchases WHERE DATE(created_at) = CURRENT_DATE AND status = 'approved'")
            today_purchase_revenue = cursor.fetchone()[0]
            today_revenue = today_order_revenue + today_purchase_revenue
        else:
            # SQLite 버전
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM orders")
            total_orders = cursor.fetchone()[0]
            
            # 총 매출 (주문 + 포인트 구매)
            cursor.execute("SELECT COALESCE(SUM(price), 0) FROM orders WHERE status = 'completed'")
            order_revenue = cursor.fetchone()[0]
            cursor.execute("SELECT COALESCE(SUM(price), 0) FROM point_purchases WHERE status = 'approved'")
            purchase_revenue = cursor.fetchone()[0]
            total_revenue = order_revenue + purchase_revenue
            
            cursor.execute("SELECT COUNT(*) FROM point_purchases WHERE status = 'pending'")
            pending_purchases = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM orders WHERE DATE(created_at) = DATE('now')")
            today_orders = cursor.fetchone()[0]
            
            # 오늘 매출 (주문 + 포인트 구매)
            cursor.execute("SELECT COALESCE(SUM(price), 0) FROM orders WHERE DATE(created_at) = DATE('now') AND status = 'completed'")
            today_order_revenue = cursor.fetchone()[0]
            cursor.execute("SELECT COALESCE(SUM(price), 0) FROM point_purchases WHERE DATE(created_at) = DATE('now') AND status = 'approved'")
            today_purchase_revenue = cursor.fetchone()[0]
            today_revenue = today_order_revenue + today_purchase_revenue
        
        conn.close()
        
        return jsonify({
            'total_users': total_users,
            'total_orders': total_orders,
            'total_revenue': float(total_revenue),
            'pending_purchases': pending_purchases,
            'today_orders': today_orders,
            'today_revenue': float(today_revenue)
        }), 200
            
    except Exception as e:
        return jsonify({'error': f'통계 조회 실패: {str(e)}'}), 500

# 관리자 포인트 구매 목록
@app.route('/api/admin/purchases', methods=['GET'])
def get_admin_purchases():
    """관리자 포인트 구매 목록"""
    try:
        print("🔍 관리자 포인트 구매 목록 조회 시작")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            # 테이블 존재 여부 확인
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'point_purchases'
                );
            """)
            purchases_table_exists = cursor.fetchone()[0]
            
            print(f"📊 point_purchases 테이블 존재 여부: {purchases_table_exists}")
            
            if purchases_table_exists:
                cursor.execute("""
                    SELECT pp.id, pp.user_id, pp.amount, pp.price, pp.status, 
                        pp.buyer_name, pp.bank_info, pp.created_at
                FROM point_purchases pp
                ORDER BY pp.created_at DESC
            """)
            else:
                print("⚠️ point_purchases 테이블이 존재하지 않습니다. 빈 배열을 반환합니다.")
                purchases = []
                conn.close()
                return jsonify({'purchases': []}), 200
        else:
            cursor.execute("""
                SELECT pp.id, pp.user_id, pp.amount, pp.price, pp.status, pp.created_at,
                       pp.buyer_name, pp.bank_info, u.email
                FROM point_purchases pp
                LEFT JOIN users u ON pp.user_id = u.user_id
                ORDER BY pp.created_at DESC
            """)
        
        purchases = cursor.fetchall()
        conn.close()
        
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
        
        return jsonify({
            'purchases': purchase_list
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'포인트 구매 목록 조회 실패: {str(e)}'}), 500

# 포인트 구매 승인/거절
@app.route('/api/admin/purchases/<int:purchase_id>', methods=['PUT'])
def update_purchase_status(purchase_id):
    """포인트 구매 승인/거절"""
    try:
        data = request.get_json()
        status = data.get('status')  # 'approved' 또는 'rejected'
        
        if status not in ['approved', 'rejected']:
            return jsonify({'error': '유효하지 않은 상태입니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 구매 신청 정보 조회
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT user_id, amount, status
                FROM point_purchases
                WHERE id = %s
            """, (purchase_id,))
        else:
            cursor.execute("""
                SELECT user_id, amount, status
                FROM point_purchases
                WHERE id = ?
            """, (purchase_id,))
        
        purchase = cursor.fetchone()
        
        if not purchase:
            return jsonify({'error': '구매 신청을 찾을 수 없습니다.'}), 404
        
        if purchase[2] != 'pending':
            return jsonify({'error': '이미 처리된 구매 신청입니다.'}), 400
        
        # 상태 업데이트
        if DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                UPDATE point_purchases
                SET status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (status, purchase_id))
        else:
            cursor.execute("""
                UPDATE point_purchases
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, purchase_id))
        
        # 승인된 경우 사용자 포인트 증가
        if status == 'approved':
            user_id = purchase[0]
            amount = purchase[1]
            
            # 사용자 포인트 조회
            if DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    SELECT points FROM points WHERE user_id = %s
                """, (user_id,))
            else:
                cursor.execute("""
                    SELECT points FROM points WHERE user_id = ?
                """, (user_id,))
            
            user_points = cursor.fetchone()
            current_points = user_points[0] if user_points else 0
            new_points = current_points + amount
            
            # 포인트 업데이트
            if DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    UPDATE points
                    SET points = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """, (new_points, user_id))
            else:
                cursor.execute("""
                    UPDATE points
                    SET points = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (new_points, user_id))
        
        conn.commit()
        
        return jsonify({
            'message': f'구매 신청이 {status}되었습니다.',
            'status': status
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'구매 신청 처리 실패: {str(e)}'}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 포인트 차감 (주문 결제용)
@app.route('/api/points/deduct', methods=['POST'])
def deduct_points():
    """포인트 차감 (주문 결제)"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        amount = data.get('amount')  # 차감할 포인트
        order_id = data.get('order_id')  # 주문 ID (선택사항)
        
        if not all([user_id, amount]):
            return jsonify({'error': '필수 필드가 누락되었습니다.'}), 400
        
        if amount <= 0:
            return jsonify({'error': '차감할 포인트는 0보다 커야 합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
            
        # 사용자 포인트 조회
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT points FROM points WHERE user_id = %s
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT points FROM points WHERE user_id = ?
            """, (user_id,))
        
        user_points = cursor.fetchone()
        
        if not user_points:
            return jsonify({'error': '사용자를 찾을 수 없습니다.'}), 404
        
        current_points = user_points[0]
        
        if current_points < amount:
            return jsonify({'error': '포인트가 부족합니다.'}), 400
        
        # 포인트 차감 (동시성 제어)
        new_points = current_points - amount
        
        if DATABASE_URL.startswith('postgresql://'):
            # PostgreSQL: SELECT FOR UPDATE로 락 설정
            cursor.execute("""
                UPDATE points
                SET points = %s, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s AND points = %s
            """, (new_points, user_id, current_points))
            
            if cursor.rowcount == 0:
                conn.rollback()
                return jsonify({'error': '포인트 잔액이 변경되었습니다. 다시 시도해주세요.'}), 409
        else:
            # SQLite: 트랜잭션으로 동시성 제어
            cursor.execute("""
                UPDATE points
                SET points = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND points = ?
            """, (new_points, user_id, current_points))
            
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
        return jsonify({'error': f'포인트 차감 실패: {str(e)}'}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 사용자 정보 조회
@app.route('/api/users/<path:user_id>', methods=['GET'])
def get_user(user_id):
    """사용자 정보 조회 (없으면 자동 생성) - 항상 200 반환"""
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
            cursor.execute("""
                SELECT user_id, email, name, created_at
                FROM users WHERE user_id = %s
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT user_id, email, name, created_at
                FROM users WHERE user_id = ?
            """, (user_id,))
        
        user = cursor.fetchone()
        print(f"🔍 사용자 조회 결과: {user}", flush=True)
        sys.stdout.flush()
        
        if user:
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
                    # 사용자 생성 시도
                    cursor.execute("""
                        INSERT INTO users (user_id, email, name, created_at, updated_at)
                        VALUES (%s, %s, %s, NOW(), NOW())
                        ON CONFLICT (user_id) DO NOTHING
                    """, (user_id, default_email, 'User'))
                    
                    # 사용자 생성 여부 확인
                    if cursor.rowcount > 0:
                        # points 테이블에도 초기 레코드 생성
                        cursor.execute("""
                            INSERT INTO points (user_id, points, created_at, updated_at)
                            VALUES (%s, 0, NOW(), NOW())
                            ON CONFLICT (user_id) DO NOTHING
                        """, (user_id,))
                        conn.commit()
                        print(f"✅ 사용자 자동 생성 완료: {user_id}")
                    else:
                        # 이미 존재하는 경우, 다시 조회
                        cursor.execute("""
                            SELECT user_id, email, name, created_at
                            FROM users WHERE user_id = %s
                        """, (user_id,))
                        user = cursor.fetchone()
                        if user:
                            user_data = {
                                'user_id': user[0],
                                'email': user[1],
                                'name': user[2],
                                'created_at': user[3].isoformat() if user[3] and hasattr(user[3], 'isoformat') else (str(user[3]) if user[3] else None)
                            }
                            return jsonify(user_data), 200
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
    """내 추천인 코드 조회"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id가 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 사용자의 추천인 코드 조회 (user_id 또는 user_email로 검색)
        print(f"🔍 추천인 코드 조회 - user_id: {user_id}")
        
        # 먼저 전체 코드 수 확인
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("SELECT COUNT(*) FROM referral_codes")
            total_codes = cursor.fetchone()[0]
            print(f"📊 전체 추천인 코드 수: {total_codes}")
            
            # 사용자별 코드 조회 (user_email 우선, user_id 보조)
            cursor.execute("""
                SELECT code, is_active, usage_count, total_commission, created_at
                FROM referral_codes 
                WHERE user_email = %s OR user_id = %s
                ORDER BY created_at DESC
            """, (user_id, user_id))
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
    """추천인 수수료 조회"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id가 필요합니다.'}), 400
        
        conn = None
        cursor = None
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
            SELECT id, referred_user, purchase_amount, commission_amount, 
                commission_rate, created_at
            FROM commissions 
            WHERE referrer_id = %s
            ORDER BY created_at DESC
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT id, referred_user, purchase_amount, commission_amount, 
                    commission_rate, created_at
                FROM commissions 
                WHERE referrer_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
        
        commissions = []
        for row in cursor.fetchall():
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
                'purchaseAmount': row[2],
                'commissionAmount': row[3],
                'commissionRate': f"{row[4] * 100}%" if row[4] else "0%",
                'paymentDate': payment_date,
                'isPaid': True  # 기본값으로 지급 완료 처리
            })
        
        return jsonify({
            'commissions': commissions
        }), 200
    except Exception as e:
        return jsonify({'error': f'수수료 조회 실패: {str(e)}'}), 500

# 추천인 코드로 쿠폰 발급
@app.route('/api/referral/issue-coupon', methods=['POST'])
def issue_referral_coupon():
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
    """추천인 코드 유효성 검증"""
    try:
        code = request.args.get('code')
        if not code:
            return jsonify({'valid': False, 'error': '코드가 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT id, code, is_active FROM referral_codes 
                WHERE code = %s
            """, (code,))
        else:
            cursor.execute("""
                SELECT id, code, is_active FROM referral_codes 
                WHERE code = ?
            """, (code,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return jsonify({'valid': True, 'code': result[1]}), 200
        else:
            return jsonify({'valid': False, 'error': '유효하지 않은 코드입니다.'}), 200
            
    except Exception as e:
        return jsonify({'valid': False, 'error': f'코드 검증 실패: {str(e)}'}), 500

# 사용자 쿠폰 조회
@app.route('/api/user/coupons', methods=['GET'])
def get_user_coupons():
    """사용자의 쿠폰 목록 조회"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id가 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT id, referral_code, discount_type, discount_value, is_used, 
                    created_at, expires_at, used_at
                FROM coupons 
                WHERE user_id = %s
                ORDER BY created_at DESC
            """, (user_id,))
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
            # 날짜 형식 처리
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
    """관리자용 추천인 커미션 현황 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            # 추천인별 커미션 현황 조회 (commission_ledger 사용)
            cursor.execute("""
                SELECT 
                    rc.user_email,
                    rc.name,
                    rc.code,
                    COUNT(DISTINCT cl.referred_user_id) as referral_count,
                    COALESCE(SUM(CASE WHEN cl.event = 'earn' THEN cl.amount ELSE 0 END), 0) as total_commission,
                    COALESCE(SUM(CASE 
                        WHEN cl.event = 'earn' AND cl.created_at >= DATE_TRUNC('month', CURRENT_DATE) 
                        THEN cl.amount 
                        ELSE 0 
                    END), 0) as this_month_commission,
                    COALESCE(SUM(CASE 
                        WHEN cl.event = 'earn' AND cl.created_at >= DATE_TRUNC('month', CURRENT_DATE)
                        AND cl.status = 'confirmed'
                        THEN cl.amount 
                        ELSE 0 
                    END), 0) as unpaid_commission
                FROM referral_codes rc
                LEFT JOIN commission_ledger cl ON rc.code = cl.referral_code AND cl.status = 'confirmed'
                WHERE rc.is_active = true
                GROUP BY rc.user_email, rc.name, rc.code
                ORDER BY total_commission DESC
            """)
        else:
            # SQLite 버전
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
        
        # 전체 통계
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT rc.user_email) as total_referrers,
                    COUNT(DISTINCT urc.user_id) as total_referrals,
                    COALESCE(SUM(c.commission_amount), 0) as total_commissions,
                    COALESCE(SUM(CASE 
                        WHEN c.payment_date >= DATE_TRUNC('month', CURRENT_DATE) 
                        THEN c.commission_amount 
                        ELSE 0 
                    END), 0) as this_month_commissions
                FROM referral_codes rc
                LEFT JOIN user_referral_connections urc ON rc.code = urc.referral_code
                LEFT JOIN commissions c ON rc.user_email = c.referrer_id
                WHERE rc.is_active = true
            """)
        else:
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
        
        conn.close()
        
        return jsonify({
            'overview': overview_data,
            'stats': total_stats
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'커미션 현황 조회 실패: {str(e)}'}), 500

# 관리자용 커미션 환급 처리
@app.route('/api/admin/referral/pay-commission', methods=['POST'])
def pay_commission():
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
    """관리자용 환급 내역 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT referrer_user_id, amount, notes, created_at
                FROM commission_ledger
                WHERE event = 'payout' AND status = 'confirmed'
                ORDER BY created_at DESC
            """)
        else:
            cursor.execute("""
                SELECT referrer_user_id, amount, notes, created_at
                FROM commission_ledger
                WHERE event = 'payout' AND status = 'confirmed'
                ORDER BY created_at DESC
            """)
        
        payments = []
        for row in cursor.fetchall():
            paid_at = row[3]
            if hasattr(paid_at, 'isoformat'):
                paid_at = paid_at.isoformat()
            else:
                paid_at = str(paid_at)
            
            payments.append({
                'referrer_user_id': row[0],
                'amount': abs(float(row[1])),  # payout은 음수이므로 절댓값
                'notes': row[2],
                'paid_at': paid_at
            })
        
        conn.close()
        return jsonify({'payments': payments}), 200
        
    except Exception as e:
        return jsonify({'error': f'환급 내역 조회 실패: {str(e)}'}), 500

# 사용자용 추천인 통계 조회
@app.route('/api/referral/stats', methods=['GET'])
def get_referral_stats():
    """사용자용 추천인 통계 조회"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id가 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # user_id가 이메일인지 확인하고 적절히 처리
        if '@' in user_id:
            # 이미 이메일인 경우
            user_email = user_id
        else:
            # user_id인 경우 이메일로 변환
            user_email = f"{user_id}@example.com"
        
        print(f"🔍 추천인 통계 조회 - user_id: {user_id}, user_email: {user_email}")
        
        if DATABASE_URL.startswith('postgresql://'):
            # 총 추천인 수 (user_referral_connections 테이블 사용)
            cursor.execute("""
                SELECT COUNT(*) FROM user_referral_connections 
                WHERE referrer_email = %s
            """, (user_email,))
            total_referrals = cursor.fetchone()[0] or 0
            
            # 활성 추천인 수 (모든 피추천인은 활성으로 간주)
            active_referrals = total_referrals
            
            # 총 커미션 (referrer_id로 조회)
            cursor.execute("""
                SELECT COALESCE(SUM(commission_amount), 0) FROM commissions 
                WHERE referrer_id = %s
            """, (user_id,))
            total_commission = cursor.fetchone()[0] or 0
            
            # 이번 달 추천인 수 (user_referral_connections 테이블 사용)
            cursor.execute("""
                SELECT COUNT(*) FROM user_referral_connections 
                WHERE referrer_email = %s 
                AND DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
            """, (user_email,))
            this_month_referrals = cursor.fetchone()[0] or 0
            
            # 이번 달 커미션
            cursor.execute("""
                SELECT COALESCE(SUM(commission_amount), 0) FROM commissions 
                WHERE referrer_id = %s 
                AND DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
            """, (user_id,))
            this_month_commission = cursor.fetchone()[0] or 0
        else:
            # SQLite 버전 (user_referral_connections 테이블 사용)
            cursor.execute("""
                SELECT COUNT(*) FROM user_referral_connections 
                WHERE referrer_email = ?
            """, (f"{user_id}@example.com",))
            total_referrals = cursor.fetchone()[0] or 0
            
            # 활성 추천인 수 (모든 피추천인은 활성으로 간주)
            active_referrals = total_referrals
            
            cursor.execute("""
                SELECT COALESCE(SUM(commission_amount), 0) FROM commissions 
                WHERE referrer_id = ?
            """, (user_id,))
            total_commission = cursor.fetchone()[0] or 0
            
            cursor.execute("""
                SELECT COUNT(*) FROM user_referral_connections 
                WHERE referrer_email = ? 
                AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
            """, (f"{user_id}@example.com",))
            this_month_referrals = cursor.fetchone()[0] or 0
            
            cursor.execute("""
                SELECT COALESCE(SUM(commission_amount), 0) FROM commissions 
                WHERE referrer_id = ? 
                AND strftime('%Y-%m', payment_date) = strftime('%Y-%m', 'now')
            """, (user_id,))
            this_month_commission = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return jsonify({
            'totalReferrals': total_referrals,
            'totalCommission': total_commission,
            'activeReferrals': active_referrals,
            'thisMonthReferrals': this_month_referrals,
            'thisMonthCommission': this_month_commission
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'통계 조회 실패: {str(e)}'}), 500

# 사용자용 추천인 목록 조회 (피추천인 목록)
@app.route('/api/referral/referrals', methods=['GET'])
def get_user_referrals():
    """사용자용 추천인 목록 조회 (내가 추천한 사용자들)"""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id가 필요합니다.'}), 400
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print(f"🔍 피추천인 목록 조회 - user_id: {user_id}")
        
        # user_id가 이메일인지 확인하고 적절히 처리
        if '@' in user_id:
            user_email = user_id
        else:
            user_email = f"{user_id}@example.com"
        
        print(f"🔍 검색할 이메일: {user_email}")
        
        # user_referral_connections 테이블에서 피추천인 목록 조회
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT urc.id, urc.user_id, urc.referral_code, urc.created_at,
                       u.name, u.email
                FROM user_referral_connections urc
                LEFT JOIN users u ON urc.user_id = u.user_id
                WHERE urc.referrer_email = %s
                ORDER BY urc.created_at DESC
            """, (user_email,))
        else:
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
            # 날짜 형식 처리
            join_date = row[3]
            if hasattr(join_date, 'strftime'):
                join_date = join_date.strftime('%Y-%m-%d')
            elif hasattr(join_date, 'isoformat'):
                join_date = join_date.isoformat()[:10]
            else:
                join_date = str(join_date)[:10]
            
            # 사용자 이름이 없으면 이메일 사용
            user_name = row[4] if row[4] else (row[5] if row[5] else row[1])
            
            referrals.append({
                'id': row[0],
                'user': user_name,
                'joinDate': join_date,
                'status': '활성',  # 피추천인은 기본적으로 활성
                'commission': 0  # 개별 커미션은 별도 계산 필요
            })
        
        print(f"✅ 피추천인 목록 조회 완료: {len(referrals)}명")
        
        return jsonify({
            'referrals': referrals
        }), 200
        
    except Exception as e:
        print(f"❌ 피추천인 목록 조회 실패: {e}")
        return jsonify({'error': f'추천인 목록 조회 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 관리자용 추천인 등록
@app.route('/api/admin/referral/register', methods=['POST'])
def admin_register_referral():
    """관리자용 추천인 등록"""
    try:
        data = request.get_json()
        print(f"🔍 관리자 추천인 등록 요청 데이터: {data}")
        
        # 다양한 필드명 지원
        email = data.get('email') or data.get('user_email')
        name = data.get('name')
        phone = data.get('phone')
        
        print(f"🔍 파싱된 필드 - email: {email}, name: {name}, phone: {phone}")
        
        if not email:
            print(f"❌ 이메일 필수 필드 누락: {email}")
            return jsonify({'error': '이메일은 필수입니다.'}), 400
        
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 추천인 코드 생성 - 고유한 UUID 기반
            import uuid
            import time
            import hashlib
            
            # 사용자별 고유 ID 생성 (이메일 기반 해시)
            user_unique_id = hashlib.md5(email.encode()).hexdigest()[:8].upper()
            code = f"REF{user_unique_id}"
            
            if DATABASE_URL.startswith('postgresql://'):
                # PostgreSQL - 먼저 기존 코드가 있는지 확인
                cursor.execute("SELECT id, code FROM referral_codes WHERE user_email = %s", (email,))
                existing_code = cursor.fetchone()
                
                if existing_code:
                    # 기존 코드 정보만 업데이트 (코드는 유지) - 강제로 활성화
                    cursor.execute("""
                        UPDATE referral_codes 
                        SET user_id = %s, name = %s, phone = %s, is_active = true, updated_at = CURRENT_TIMESTAMP
                        WHERE user_email = %s
                    """, (user_unique_id, name, phone, email))
                    print(f"✅ 기존 추천인 코드 활성화: {email} - {existing_code[1]}")
                else:
                    # 새 코드 생성 - 바로 활성화
                    cursor.execute("""
                        INSERT INTO referral_codes (user_id, user_email, code, name, phone, created_at, is_active)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (user_unique_id, email, code, name, phone, datetime.now(), True))
                    print(f"✅ 새 추천인 코드 생성 및 활성화: {email} - {code}")
                
                # 활성화 상태 확인
                cursor.execute("SELECT code, is_active FROM referral_codes WHERE user_email = %s", (email,))
                verification = cursor.fetchone()
                if verification:
                    print(f"🔍 활성화 확인: {verification[0]} - {verification[1]}")
                
                # 추천인 등록
                cursor.execute("""
                    INSERT INTO referrals (referrer_email, referral_code, name, phone, created_at, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (email, code, name, phone, datetime.now(), 'active'))
            else:
                # SQLite - 기존 코드가 있는지 확인 후 처리
                cursor.execute("SELECT id FROM referral_codes WHERE user_email = ?", (email,))
                existing_code = cursor.fetchone()
                
                if existing_code:
                    # 기존 코드 정보만 업데이트 (코드는 유지) - 강제로 활성화
                    cursor.execute("""
                        UPDATE referral_codes 
                        SET user_id = ?, name = ?, phone = ?, is_active = 1, updated_at = CURRENT_TIMESTAMP
                        WHERE user_email = ?
                    """, (user_unique_id, name, phone, email))
                    print(f"✅ 기존 추천인 코드 활성화 (SQLite): {email}")
                else:
                    # 새 코드 생성 - 바로 활성화
                    cursor.execute("""
                        INSERT INTO referral_codes (user_id, user_email, code, name, phone, created_at, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (user_unique_id, email, code, name, phone, datetime.now(), True))
                    print(f"✅ 새 추천인 코드 생성 및 활성화 (SQLite): {email} - {code}")
                
                cursor.execute("""
                    INSERT INTO referrals (referrer_email, referral_code, name, phone, created_at, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (email, code, name, phone, datetime.now(), 'active'))
            
            conn.commit()
            print(f"✅ 추천인 등록 완료: {email} - {code}")
            
        except Exception as db_error:
            if conn:
                conn.rollback()
            print(f"❌ 추천인 등록 실패: {db_error}")
            raise db_error
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        
        return jsonify({
            'id': str(uuid.uuid4()),
            'email': email,
            'referralCode': code,
            'name': name,
            'phone': phone,
            'message': '추천인 등록 성공'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'추천인 등록 실패: {str(e)}'}), 500

# 관리자용 추천인 목록 조회
@app.route('/api/admin/referral/list', methods=['GET'])
def admin_get_referrals():
    """관리자용 추천인 목록 조회"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT id, user_email, code, name, phone, created_at, is_active
                FROM referral_codes 
                ORDER BY created_at DESC
            """)
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
    """관리자용 추천인 코드 목록 조회"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            # 먼저 모든 코드를 강제로 활성화
            cursor.execute("UPDATE referral_codes SET is_active = true")
            print("🔄 관리자 API에서 모든 코드 강제 활성화")
            
            cursor.execute("""
                SELECT id, code, user_email, name, phone, created_at, is_active, 
                    COALESCE(usage_count, 0) as usage_count, 
                    COALESCE(total_commission, 0) as total_commission
                FROM referral_codes 
                ORDER BY created_at DESC
            """)
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
            # 날짜 형식 처리 강화
            created_at = row[5]
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
            is_active = row[6]
            if is_active is None:
                is_active = True  # None이면 True로 설정
            elif isinstance(is_active, str):
                is_active = is_active.lower() in ['true', '1', 'yes']
            else:
                is_active = bool(is_active)
            
            codes.append({
                'id': row[0],
                'code': row[1],
                'email': row[2],
                'name': row[3],
                'phone': row[4],
                'createdAt': created_at,
                'isActive': is_active,
                'usage_count': row[7],
                'total_commission': row[8]
            })
        
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
    """관리자용 커미션 내역 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT ledger_id, referred_user_id, base_amount, amount, 
                    commission_rate, created_at
                FROM commission_ledger 
                WHERE event = 'earn' AND status = 'confirmed'
                ORDER BY created_at DESC
            """)
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
    """포인트 구매 내역 조회"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id가 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT id, amount, price, status, created_at
                FROM point_purchases WHERE user_id = %s
                ORDER BY created_at DESC
            """, (user_id,))
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
    """관리자 사용자 목록"""
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
                    # 기본 컬럼만 조회
                    cursor.execute("""
                        SELECT user_id, email, name, created_at
                        FROM users
                        ORDER BY created_at DESC
                        LIMIT 50
                    """)
                    users = cursor.fetchall()
                    
                    for user in users:
                        user_list.append({
                            'user_id': user[0] if user[0] else 'N/A',
                            'email': user[1] if user[1] else 'N/A',
                            'name': user[2] if user[2] else 'N/A',
                            'created_at': user[3].isoformat() if user[3] and hasattr(user[3], 'isoformat') else str(user[3]) if user[3] else 'N/A',
                            'points': 0,  # 기본값
                            'last_activity': 'N/A'  # 기본값
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

# 관리자 거래 내역
@app.route('/api/admin/transactions', methods=['GET'])
def get_admin_transactions():
    """관리자 거래 내역"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT o.order_id, o.user_id, o.service_id, o.price, o.status, o.created_at,
                       o.platform, o.service_name, o.quantity, o.link, o.comments
                FROM orders o
                ORDER BY o.created_at DESC
            """)
        else:
            cursor.execute("""
                SELECT o.order_id, o.user_id, o.service_id, o.price, o.status, o.created_at,
                       o.platform, o.service_name, o.quantity, o.link, o.comments
                FROM orders o
                ORDER BY o.created_at DESC
            """)
        
        transactions = cursor.fetchall()
        conn.close()
        
        transaction_list = []
        for transaction in transactions:
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
    """관리자 페이지 서빙"""
    try:
        return app.send_static_file('index.html')
    except:
        return "Admin page not found", 404

# 정적 파일 서빙
@app.route('/<path:filename>')
def serve_static(filename):
    """정적 파일 서빙"""
    try:
        return app.send_static_file(filename)
    except:
        return "File not found", 404

@app.route('/', methods=['GET', 'POST'])
def serve_index():
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
    """추천인 커미션 포인트 조회"""
    try:
        referrer_email = request.args.get('referrer_email')
        if not referrer_email:
            return jsonify({'error': 'referrer_email이 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(CASE WHEN event = 'earn' THEN amount ELSE 0 END), 0) as total_earned,
                    COALESCE(SUM(CASE WHEN event = 'payout' THEN ABS(amount) ELSE 0 END), 0) as total_paid,
                    COALESCE(SUM(amount), 0) as current_balance
                FROM commission_ledger 
                WHERE referrer_user_id = %s AND status = 'confirmed'
            """, (referrer_email,))
        else:
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(CASE WHEN event = 'earn' THEN amount ELSE 0 END), 0) as total_earned,
                    COALESCE(SUM(CASE WHEN event = 'payout' THEN ABS(amount) ELSE 0 END), 0) as total_paid,
                    COALESCE(SUM(amount), 0) as current_balance
                FROM commission_ledger 
                WHERE referrer_user_id = ? AND status = 'confirmed'
            """, (referrer_email,))
        
        result = cursor.fetchone()
        conn.close()
        
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
        return jsonify({'error': f'커미션 포인트 조회 실패: {str(e)}'}), 500

# 커미션 포인트 거래 내역 조회
@app.route('/api/referral/commission-transactions', methods=['GET'])
def get_commission_transactions():
    """커미션 포인트 거래 내역 조회"""
    try:
        referrer_email = request.args.get('referrer_email')
        if not referrer_email:
            return jsonify({'error': 'referrer_email이 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT event, amount, notes, created_at,
                       (SELECT COALESCE(SUM(amount), 0) FROM commission_ledger 
                        WHERE referrer_user_id = %s AND status = 'confirmed' AND created_at <= cl.created_at) as balance_after
                FROM commission_ledger cl
                WHERE referrer_user_id = %s
                ORDER BY created_at DESC
            """, (referrer_email, referrer_email))
        else:
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
                'type': row[0],  # 'earn' or 'payout'
                'amount': float(row[1]),
                'balance_after': float(row[4]) if len(row) > 4 else 0,
                'description': row[2] if row[2] else '',
                'created_at': row[3].isoformat() if hasattr(row[3], 'isoformat') else str(row[3])
            })
        
        conn.close()
        return jsonify({'transactions': transactions}), 200
        
    except Exception as e:
        return jsonify({'error': f'거래 내역 조회 실패: {str(e)}'}), 500

# 환급 신청
@app.route('/api/referral/withdrawal-request', methods=['POST'])
def request_withdrawal():
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
        
        # 환급 신청 저장
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                INSERT INTO commission_withdrawal_requests 
                (referrer_email, referrer_name, bank_name, account_number, account_holder, amount, requested_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """, (referrer_email, referrer_name, bank_name, account_number, account_holder, amount))
        else:
            cursor.execute("""
                INSERT INTO commission_withdrawal_requests 
                (referrer_email, referrer_name, bank_name, account_number, account_holder, amount, requested_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """, (referrer_email, referrer_name, bank_name, account_number, account_holder, amount))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': '환급 신청이 접수되었습니다.'}), 200
        
    except Exception as e:
        return jsonify({'error': f'환급 신청 실패: {str(e)}'}), 500

# 관리자용 환급 신청 목록 조회
@app.route('/api/admin/withdrawal-requests', methods=['GET'])
def get_withdrawal_requests():
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
    """예약 주문 목록 조회 (관리자용)"""
    conn = None
    cursor = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT order_id, user_id, service_id, link, quantity, price, scheduled_datetime, status, created_at, updated_at
                FROM orders 
                WHERE is_scheduled = TRUE
                ORDER BY scheduled_datetime DESC
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
    """주문 상태 확인 및 수정"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        
        if not order_id:
            return jsonify({'error': '주문 ID가 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 주문 정보 조회
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT order_id, status, smm_panel_order_id, created_at, updated_at
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
    """공지사항 목록 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT id, title, content, image_url, is_active, created_at, updated_at
                FROM notices 
                ORDER BY created_at DESC
            """)
        else:
            cursor.execute("""
                SELECT id, title, content, image_url, is_active, created_at, updated_at
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
                'is_active': row[4],
                'created_at': row[5].isoformat() if row[5] else None,
                'updated_at': row[6].isoformat() if row[6] else None
            })
        
        conn.close()
        return jsonify({'notices': notices}), 200
        
    except Exception as e:
        return jsonify({'error': f'공지사항 조회 실패: {str(e)}'}), 500

@app.route('/api/admin/notices', methods=['POST'])
@require_admin_auth
def create_notice():
    """공지사항 생성"""
    try:
        data = request.get_json()
        title = data.get('title')
        content = data.get('content')
        image_url = data.get('image_url')
        is_active = data.get('is_active', True)
        
        if not title or not content:
            return jsonify({'error': '제목과 내용이 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                INSERT INTO notices (title, content, image_url, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, NOW(), NOW())
            """, (title, content, image_url, is_active))
        else:
            cursor.execute("""
                INSERT INTO notices (title, content, image_url, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
            """, (title, content, image_url, is_active))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': '공지사항이 생성되었습니다.'}), 200
        
    except Exception as e:
        return jsonify({'error': f'공지사항 생성 실패: {str(e)}'}), 500

@app.route('/api/admin/notices/<int:notice_id>', methods=['PUT'])
@require_admin_auth
def update_notice(notice_id):
    """공지사항 수정"""
    try:
        data = request.get_json()
        title = data.get('title')
        content = data.get('content')
        image_url = data.get('image_url')
        is_active = data.get('is_active')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                UPDATE notices 
                SET title = %s, content = %s, image_url = %s, is_active = %s, updated_at = NOW()
                WHERE id = %s
            """, (title, content, image_url, is_active, notice_id))
        else:
            cursor.execute("""
                UPDATE notices 
                SET title = ?, content = ?, image_url = ?, is_active = ?, updated_at = datetime('now')
                WHERE id = ?
            """, (title, content, image_url, is_active, notice_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': '공지사항이 수정되었습니다.'}), 200
        
    except Exception as e:
        return jsonify({'error': f'공지사항 수정 실패: {str(e)}'}), 500

@app.route('/api/admin/notices/<int:notice_id>', methods=['DELETE'])
@require_admin_auth
def delete_notice(notice_id):
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
    """활성화된 공지사항 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT id, title, content, image_url, created_at
                FROM notices 
                WHERE is_active = true
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
                'content': row[2],
                'image_url': row[3],
                'created_at': row[4].isoformat() if row[4] else None
            })
        
        conn.close()
        return jsonify({'notices': notices}), 200
        
    except Exception as e:
        return jsonify({'error': f'공지사항 조회 실패: {str(e)}'}), 500

# SMM Panel 서비스 목록 조회
@app.route('/api/smm-panel/services', methods=['GET'])
def get_smm_services():
    """SMM Panel에서 사용 가능한 서비스 목록 조회"""
    try:
        result = get_smm_panel_services()
        
        if result.get('status') == 'success':
            return jsonify({
                'success': True,
                'services': result.get('services', []),
                'service_ids': result.get('service_ids', [])
            }), 200
        else:
            error_message = result.get('message', 'Failed to get services')
            print(f"❌ SMM Panel 서비스 목록 조회 실패: {error_message}")
            
            # API 키 오류인 경우 더 명확한 메시지
            if 'Invalid API key' in error_message or '401' in error_message:
                error_message = 'API 키가 유효하지 않습니다. .env 파일에 올바른 SMMPANEL_API_KEY를 설정하세요.'
            
            return jsonify({
                'success': False,
                'error': error_message,
                'details': result.get('message', '')
            }), 500
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ SMM Panel 서비스 목록 조회 오류: {error_msg}")
        
        # API 키 관련 오류인 경우
        if 'Invalid API key' in error_msg or '401' in error_msg:
            error_msg = 'API 키가 유효하지 않습니다. .env 파일에 올바른 SMMPANEL_API_KEY를 설정하세요.'
        
        return jsonify({
            'error': f'서비스 목록 조회 실패: {error_msg}',
            'details': str(e)
        }), 500

# 스케줄러 작업: 예약/분할 주문 처리
@app.route('/api/cron/process-scheduled-orders', methods=['POST'])
def cron_process_scheduled_orders():
    """예약 주문 처리 크론잡"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 현재 시간이 지난 예약 주문 조회 (orders 테이블에서도 조회)
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"🔍 예약 주문 조회 중... (현재 시간: {current_time})")
        
        # orders 테이블에서 예약 주문 조회
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT order_id, user_id, service_id, link, quantity, price, package_steps, scheduled_datetime
                FROM orders 
                WHERE is_scheduled = TRUE 
                AND status IN ('scheduled', 'pending')
                AND scheduled_datetime <= NOW()
            """)
        else:
            cursor.execute("""
                SELECT order_id, user_id, service_id, link, quantity, price, package_steps, scheduled_datetime
                FROM orders 
                WHERE is_scheduled = 1 
                AND status IN ('scheduled', 'pending')
                AND scheduled_datetime <= datetime('now')
            """)
        
        scheduled_orders = cursor.fetchall()
        print(f"🔍 발견된 예약 주문: {len(scheduled_orders)}개")
        
        for order in scheduled_orders:
            print(f"🔍 예약 주문 상세: ID={order[0]}, 예약시간={order[7]}, 사용자={order[1]}")
        
        processed_count = 0
        
        for order in scheduled_orders:
            order_id = order[0]
            user_id = order[1]
            service_id = order[2]
            link = order[3]
            quantity = order[4]
            price = order[5]
            package_steps_json = order[6]
            package_steps = json.loads(package_steps_json) if package_steps_json else []
            
            print(f"🔄 예약 주문 처리 중: ID {order_id}, 사용자 {user_id}, 패키지: {len(package_steps)}단계")
            
            # 패키지 상품인 경우 패키지 처리 시작
            if package_steps and len(package_steps) > 0:
                print(f"📦 패키지 주문 처리 시작: {len(package_steps)}단계")
                
                # 반복 횟수 확인
                current_step = package_steps[0]
                step_repeat = current_step.get('repeat', 1)
                step_service_id = current_step.get('id')
                
                # 이미 완료된 반복 횟수 확인
                if DATABASE_URL.startswith('postgresql://'):
                    cursor.execute("""
                        SELECT COUNT(*) FROM execution_progress 
                        WHERE order_id = %s AND exec_type = 'package' AND step_number = 1 AND status = 'completed'
                    """, (order_id,))
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
                    # 패키지 처리 시작
                    if DATABASE_URL.startswith('postgresql://'):
                        cursor.execute("""
                            UPDATE orders SET status = 'package_processing', updated_at = NOW()
                            WHERE order_id = %s
                        """, (order_id,))
                    else:
                        cursor.execute("""
                            UPDATE orders SET status = 'package_processing', updated_at = CURRENT_TIMESTAMP
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
                AND o.status IN ('split_scheduled', 'in_progress')
            """)
        else:
            cursor.execute("""
                SELECT o.order_id, o.split_days, o.created_at
                FROM orders o
                WHERE o.is_split_delivery = 1
                AND o.status IN ('split_scheduled', 'in_progress')
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
                base_query += " AND (title ILIKE %s OR content ILIKE %s OR excerpt ILIKE %s)"
                count_query += " AND (title ILIKE %s OR content ILIKE %s OR excerpt ILIKE %s)"
            else:
                base_query += " AND (title LIKE ? OR content LIKE ? OR excerpt LIKE ?)"
                count_query += " AND (title LIKE ? OR content LIKE ? OR excerpt LIKE ?)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])
        
        if tag:
            if DATABASE_URL.startswith('postgresql://'):
                base_query += " AND tags::text ILIKE %s"
                count_query += " AND tags::text ILIKE %s"
            else:
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
    """블로그 카테고리 목록 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT category, COUNT(*) as count
                FROM blog_posts 
                WHERE is_published = true AND category IS NOT NULL
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
    """블로그 태그 목록 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT DISTINCT jsonb_array_elements_text(tags) as tag
                FROM blog_posts 
                WHERE is_published = true AND tags IS NOT NULL
            """)
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
    """SPA 라우팅 지원 - 모든 경로를 index.html로 서빙"""
    print(f"🔍 SPA 라우팅 요청: /{path}")
    
    # API 경로는 Flask가 자동으로 처리하므로 여기서는 처리하지 않음
    # Flask는 더 구체적인 라우트를 먼저 매칭하므로, API 라우트가 먼저 매칭됨
    # 여기서는 API 경로가 아닌 경우에만 처리
    if path.startswith('api/'):
        # API 경로인데 여기까지 왔다면 실제로 404임
        print(f"⚠️ API 경로를 찾을 수 없음: /{path}")
        return jsonify({'error': 'API endpoint not found'}), 404
    
    # 정적 파일 경로는 제외
    if path.startswith('static/') or path.startswith('assets/') or '.' in path:
        return jsonify({'error': 'Static file not found'}), 404
    
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

if __name__ == '__main__':
    # 개발 서버 실행 (PORT 환경 변수 우선)
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)