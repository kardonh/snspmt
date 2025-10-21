import os
import json
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
        print(f"🔍 예약 주문 저장: 사용자={user_id}, 서비스={service_id}, 예약시간={scheduled_datetime}, 패키지단계={len(package_steps)}개")
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                INSERT INTO scheduled_orders 
                (user_id, service_id, link, quantity, price, scheduled_datetime, status, created_at, package_steps)
                VALUES (%s, %s, %s, %s, %s, %s, 'pending', NOW(), %s)
            """, (
                user_id, service_id, link, quantity, price, scheduled_datetime,
                json.dumps(package_steps)
            ))
        else:
            cursor.execute("""
                INSERT INTO scheduled_orders 
                (user_id, service_id, link, quantity, price, scheduled_datetime, status, created_at, package_steps)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', datetime('now'), ?)
            """, (
                user_id, service_id, link, quantity, price, scheduled_datetime,
                json.dumps(package_steps)
            ))
        
        conn.commit()
        
        print(f"✅ 예약 발송 주문 생성 완료: {scheduled_datetime}")
        print(f"✅ 예약 주문이 {time_diff_minutes:.1f}분 후에 처리됩니다.")
        
        return jsonify({
            'success': True,
            'message': f'예약 발송이 설정되었습니다. ({scheduled_datetime}에 처리됩니다)',
            'scheduled_datetime': scheduled_datetime
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
    return jsonify({'error': 'Not Found', 'message': '요청한 리소스를 찾을 수 없습니다.'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal Server Error', 'message': '서버 내부 오류가 발생했습니다.'}), 500

@app.errorhandler(Exception)
def handle_exception(e):
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
            payload = {
                'key': SMMPANEL_API_KEY,
                'action': 'add',
                'service': order_data.get('service'),
                'link': order_data.get('link'),
                'quantity': order_data.get('quantity'),
                'runs': 1,
                'interval': 0,
                'comments': order_data.get('comments', ''),
                'username': '',
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
    
    # SMM Panel API에서 서비스 정보를 가져와서 더 정확한 이름 제공
    try:
        smm_services = get_smm_panel_services()
        if smm_services:
            for service in smm_services:
                if str(service.get('service')) == str(service_id):
                    return service.get('name', service_name)
    except:
        pass  # SMM API 호출 실패 시 기본 매핑 사용
    
    return service_name

# SMM Panel 서비스 목록 조회 함수
def get_smm_panel_services():
    """SMM Panel에서 사용 가능한 서비스 목록 조회"""
    try:
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
        else:
            return {
                'status': 'error',
                'message': f'HTTP {response.status_code}'
            }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
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
        
        # 패키지 상품의 경우 하루에 400개씩 처리
        daily_quantity = 400
        
        # SMM Panel API 호출 (인스타그램 프로필 방문)
        smm_result = call_smm_panel_api({
            'service': 515,  # 인스타그램 프로필 방문
            'link': link,
            'quantity': daily_quantity,
            'comments': f"{comments} (패키지 {day_number}/30일차)"
        })
        
        if smm_result.get('status') == 'success':
            # 성공 시 진행 상황 업데이트
            if DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    UPDATE split_delivery_progress 
                    SET status = 'completed', quantity_delivered = %s, 
                        smm_panel_order_id = %s, completed_at = NOW()
                    WHERE order_id = %s AND day_number = %s
                """, (daily_quantity, smm_result.get('order'), order_id, day_number))
            else:
                cursor.execute("""
                    UPDATE split_delivery_progress 
                    SET status = 'completed', quantity_delivered = ?, 
                        smm_panel_order_id = ?, completed_at = datetime('now')
                    WHERE order_id = ? AND day_number = ?
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
                    UPDATE split_delivery_progress 
                    SET status = 'completed', quantity_delivered = %s, 
                        smm_panel_order_id = %s, completed_at = NOW()
                    WHERE order_id = %s AND day_number = %s
                """, (split_quantity, smm_result.get('order'), order_id, day_number))
            else:
                cursor.execute("""
                    UPDATE split_delivery_progress 
                    SET status = 'completed', quantity_delivered = ?, 
                        smm_panel_order_id = ?, completed_at = datetime('now')
                    WHERE order_id = ? AND day_number = ?
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
                    UPDATE split_delivery_progress 
                    SET status = 'failed', error_message = %s, failed_at = NOW()
                    WHERE order_id = %s AND day_number = %s
                """, (smm_result.get('message', 'Unknown error'), order_id, day_number))
            else:
                cursor.execute("""
                    UPDATE split_delivery_progress 
                    SET status = 'failed', error_message = ?, failed_at = datetime('now')
                    WHERE order_id = ? AND day_number = ?
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
                    INSERT INTO package_progress 
                    (order_id, step_number, step_name, service_id, quantity, smm_panel_order_id, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, 'skipped', NOW())
                """, (order_id, step_index + 1, step_name, step_service_id, step_quantity, None))
            else:
                cursor.execute("""
                    INSERT INTO package_progress 
                    (order_id, step_number, step_name, service_id, quantity, smm_panel_order_id, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'skipped', datetime('now'))
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
            
            # SMM Panel에서 받은 실제 주문번호로 order_id 업데이트 (성공한 경우만)
            if smm_order_id and status == 'completed':
                print(f"🔄 주문번호 업데이트: {order_id} -> {smm_order_id}")
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
            
            if DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    INSERT INTO package_progress 
                    (order_id, step_number, step_name, service_id, quantity, smm_panel_order_id, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                """, (order_id, f"{step_index + 1}-{repeat_count + 1}", f"{step_name} ({repeat_count + 1}/{step_repeat})", step_service_id, step_quantity, smm_order_id, status))
            else:
                cursor.execute("""
                    INSERT INTO package_progress 
                    (order_id, step_number, step_name, service_id, quantity, smm_panel_order_id, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """, (order_id, f"{step_index + 1}-{repeat_count + 1}", f"{step_name} ({repeat_count + 1}/{step_repeat})", step_service_id, step_quantity, smm_order_id, status))
            
            conn.commit()
            
            # 마지막 반복이 아니면 delay 시간만큼 대기
            if repeat_count < step_repeat - 1:
                print(f"⏳ {step_delay}분 대기 후 다음 반복 실행...")
                import time
                time.sleep(step_delay * 60)  # 분을 초로 변환
        
        print(f"🎉 패키지 단계 {step_index + 1} 모든 반복 완료: {step_name} ({step_repeat}회)")
        
        # 다음 단계가 있으면 스케줄링
        schedule_next_package_step(order_id, step_index + 1, package_steps)
        
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
            
            # 실제 대기 시간을 초 단위로 변환
            wait_seconds = next_delay * 60
            print(f"⏰ 대기 시간: {wait_seconds}초 ({next_delay}분)")
            
            # 1초씩 나누어서 대기 (중간에 중단되지 않도록)
            for i in range(wait_seconds):
                time.sleep(1)
                if i % 60 == 0 and i > 0:  # 매분마다 로그
                    remaining_minutes = (wait_seconds - i) // 60
                    print(f"⏰ 남은 시간: {remaining_minutes}분")
            
            print(f"⏰ {next_delay}분 대기 완료, 다음 단계 실행: {next_step_name}")
            print(f"⏰ 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            process_package_step(order_id, next_step_index)
        except Exception as e:
            print(f"❌ 지연 실행 중 오류 발생: {str(e)}")
    
    thread = threading.Thread(target=delayed_next_step, daemon=False, name=f"PackageStep-{order_id}-{next_step_index}")
    thread.start()
    print(f"✅ 패키지 단계 {next_step_index + 1} 스케줄링 완료 (스레드 ID: {thread.ident})")

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
            # 일반 주문인 경우 SMM Panel API 호출
            print(f"🚀 일반 예약 주문 - SMM Panel API 호출")
            smm_result = call_smm_panel_api({
                'service': service_id,
                'link': link,
                'quantity': quantity,
                'comments': f'Scheduled order from {scheduled_id}'
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

# AWS Secrets Manager 시도 (선택사항)
try:
    from aws_secrets_manager import get_database_url, get_smmpanel_api_key
    aws_db_url = get_database_url()
    aws_api_key = get_smmpanel_api_key()
    if aws_db_url and aws_db_url != DATABASE_URL:
        DATABASE_URL = aws_db_url
    if aws_api_key and aws_api_key != SMMPANEL_API_KEY:
        SMMPANEL_API_KEY = aws_api_key
except ImportError as e:
    pass
except Exception as e:
    pass

# 프로덕션 환경에서는 로그 최소화
if os.environ.get('FLASK_ENV') != 'production':
    pass

def get_db_connection():
    """데이터베이스 연결을 가져옵니다."""
    try:
        # 프로덕션 환경에서는 로그 최소화
        if os.environ.get('FLASK_ENV') != 'production':
            pass
        
        if DATABASE_URL.startswith('postgresql://'):
            # PostgreSQL 연결 설정 최적화
            conn = psycopg2.connect(
                DATABASE_URL,
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
        # SQLite 폴백 시도
        try:
            db_path = os.path.join(os.getcwd(), 'data', 'snspmt.db')
            os.makedirs(os.path.dirname(db_path), exist_ok=True)  # 디렉토리 생성
            conn = sqlite3.connect(db_path, timeout=30)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as fallback_error:
            raise fallback_error
    except Exception as e:
        raise e

def init_database():
    """데이터베이스 테이블을 초기화합니다."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # PostgreSQL인지 SQLite인지 확인
        is_postgresql = DATABASE_URL.startswith('postgresql://')
        
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
            
            # 기존 테이블에 컬럼 추가 (PostgreSQL)
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id VARCHAR(255)")
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS kakao_id VARCHAR(255)")
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_image TEXT")
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP")
                print("✅ 사용자 테이블 컬럼 추가 완료 (PostgreSQL)")
            except Exception as e:
                print(f"⚠️ 사용자 테이블 컬럼 추가 실패 (이미 존재할 수 있음): {e}")
            
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
            
            # 사용자 추천인 코드 연결 테이블 생성 (기존 데이터 보존)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_referral_connections (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    referral_code VARCHAR(50) NOT NULL,
                    referrer_email VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # 커미션 환급 내역 테이블 생성 (기존 데이터 보존)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS commission_payments (
                    id SERIAL PRIMARY KEY,
                    referrer_email VARCHAR(255) NOT NULL,
                    amount DECIMAL(10,2) NOT NULL,
                    payment_method VARCHAR(50) DEFAULT 'bank_transfer',
                    notes TEXT,
                    paid_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # 추천인 커미션 포인트 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS commission_points (
                    id SERIAL PRIMARY KEY,
                    referrer_email VARCHAR(255) NOT NULL,
                    referrer_name VARCHAR(255),
                    total_earned DECIMAL(10,2) DEFAULT 0,
                    total_paid DECIMAL(10,2) DEFAULT 0,
                    current_balance DECIMAL(10,2) DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # 커미션 포인트 거래 내역 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS commission_point_transactions (
                    id SERIAL PRIMARY KEY,
                    referrer_email VARCHAR(255) NOT NULL,
                    transaction_type VARCHAR(50) NOT NULL,
                    amount DECIMAL(10,2) NOT NULL,
                    balance_after DECIMAL(10,2) NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # 환급 신청 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS commission_withdrawal_requests (
                    id SERIAL PRIMARY KEY,
                    referrer_email VARCHAR(255) NOT NULL,
                    referrer_name VARCHAR(255),
                    bank_name VARCHAR(255) NOT NULL,
                    account_number VARCHAR(255) NOT NULL,
                    account_holder VARCHAR(255) NOT NULL,
                    amount DECIMAL(10,2) NOT NULL,
                    status VARCHAR(50) DEFAULT 'pending',
                    admin_notes TEXT,
                    requested_at TIMESTAMP DEFAULT NOW(),
                    processed_at TIMESTAMP,
                    processed_by VARCHAR(255)
                )
            """)
            
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
            
        # order_id 컬럼 타입 확인 (기존 INTEGER 유지)
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
            
            # 기존 테이블에 예약/분할 필드 추가 (이미 존재하는 경우 무시)
            try:
                cursor.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS is_scheduled BOOLEAN DEFAULT FALSE")
                cursor.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS scheduled_datetime TIMESTAMP")
                cursor.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS is_split_delivery BOOLEAN DEFAULT FALSE")
                cursor.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS split_days INTEGER DEFAULT 0")
                cursor.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS split_quantity INTEGER DEFAULT 0")
                print("✅ 예약/분할 필드 추가 완료")
            except Exception as e:
                print(f"⚠️ 예약/분할 필드 추가 실패 (이미 존재할 수 있음): {e}")
            
            # 분할 발송 진행 상황 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS split_delivery_progress (
                    id SERIAL PRIMARY KEY,
                    order_id VARCHAR(255) NOT NULL,
                    day_number INTEGER NOT NULL,
                    scheduled_date DATE,
                    quantity_delivered INTEGER DEFAULT 0,
                    status VARCHAR(50) DEFAULT 'pending',
                    smm_panel_order_id VARCHAR(255),
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    completed_at TIMESTAMP,
                    failed_at TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES orders(order_id)
                )
            """)
            print("✅ 분할 발송 진행 상황 테이블 생성 완료")
            
            # 패키지 진행 상황 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS package_progress (
                id SERIAL PRIMARY KEY,
                    order_id VARCHAR(255) NOT NULL,
                    step_number INTEGER NOT NULL,
                    step_name VARCHAR(255) NOT NULL,
                    service_id VARCHAR(255) NOT NULL,
                    quantity INTEGER NOT NULL,
                    smm_panel_order_id VARCHAR(255),
                    status VARCHAR(50) DEFAULT 'pending',
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    completed_at TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES orders(order_id)
                )
            """)
            print("✅ 패키지 진행 상황 테이블 생성 완료")
            
            # 예약 주문 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_orders (
                id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    service_id VARCHAR(255) NOT NULL,
                    link TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price DECIMAL(10,2) NOT NULL,
                    scheduled_datetime TIMESTAMP NOT NULL,
                    status VARCHAR(50) DEFAULT 'pending',
                    package_steps TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    processed_at TIMESTAMP
                )
            """)
            print("✅ 예약 주문 테이블 생성 완료")
            
            # orders 테이블에 필요한 컬럼들 추가 (존재 여부 확인 후)
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
                    print("✅ smm_panel_order_id 필드 추가 완료")
                else:
                    print("ℹ️ smm_panel_order_id 필드 이미 존재")
            except Exception as e:
                print(f"⚠️ smm_panel_order_id 필드 추가 실패: {e}")
                conn.rollback()
            
            # last_status_check 컬럼 추가
            try:
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='orders' AND column_name='last_status_check'
                """)
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE orders ADD COLUMN last_status_check TIMESTAMP")
                    conn.commit()
                    print("✅ last_status_check 필드 추가 완료")
                else:
                    print("ℹ️ last_status_check 필드 이미 존재")
            except Exception as e:
                print(f"⚠️ last_status_check 필드 추가 실패: {e}")
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
                    print("✅ detailed_service 필드 추가 완료")
                else:
                    print("ℹ️ detailed_service 필드 이미 존재")
            except Exception as e:
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
                    print("✅ package_steps 필드 추가 완료")
                else:
                    print("ℹ️ package_steps 필드 이미 존재")
            except Exception as e:
                print(f"⚠️ package_steps 필드 추가 실패: {e}")
                conn.rollback()
            
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
            
        else:
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
            
            # 기존 테이블에 컬럼 추가 (SQLite)
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN google_id TEXT")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN kakao_id TEXT")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN profile_image TEXT")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN last_login TIMESTAMP")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN display_name TEXT")
            except:
                pass
            print("✅ 사용자 테이블 컬럼 추가 완료 (SQLite)")
            
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
            
            # 커미션 환급 내역 테이블 생성 (SQLite)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS commission_payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_email TEXT NOT NULL,
                    amount REAL NOT NULL,
                    payment_method TEXT DEFAULT 'bank_transfer',
                    notes TEXT,
                    paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("✅ 커미션 환급 내역 테이블 생성 완료 (SQLite)")
        
        conn.commit()
        print("✅ 데이터베이스 테이블 초기화 완료")
        
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
    finally:
        if 'conn' in locals():
            conn.close()

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
        if DATABASE_URL.startswith('postgresql://'):
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
            if DATABASE_URL.startswith('postgresql://'):
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
                if DATABASE_URL.startswith('postgresql://'):
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
                if DATABASE_URL.startswith('postgresql://'):
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
            if DATABASE_URL.startswith('postgresql://'):
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
        
        # 패키지 상품 여부 확인
        package_steps = data.get('package_steps', [])
        is_package = len(package_steps) > 0
        
        # SMM Panel API 호출을 먼저 실행하여 실제 주문번호를 받아옴
        import time
        real_order_id = None
        smm_panel_order_id = None
        
        # 일반 주문인 경우 즉시 SMM Panel API 호출 (패키지가 아닌 경우만)
        if not is_scheduled and not is_package:
            print(f"🚀 일반 주문 - 즉시 SMM Panel API 호출")
            try:
                # SMM Panel에서 사용 가능한 서비스 목록 확인
                smm_services_result = get_smm_panel_services()
                if smm_services_result.get('status') == 'success':
                    available_service_ids = smm_services_result.get('service_ids', [])
                    if str(service_id) not in available_service_ids:
                        print(f"❌ 서비스 ID {service_id}가 SMM Panel에서 사용 불가능합니다.")
                        print(f"📋 사용 가능한 서비스 ID: {available_service_ids[:10]}...")  # 처음 10개만 표시
                        return jsonify({'error': f'서비스 ID {service_id}가 SMM Panel에서 사용 불가능합니다. 사용 가능한 서비스를 확인해주세요.'}), 400
                    else:
                        print(f"✅ 서비스 ID {service_id} 검증 완료")
                else:
                    print(f"⚠️ SMM Panel 서비스 목록 조회 실패, 서비스 ID 검증 건너뜀: {smm_services_result.get('message')}")
                
                smm_result = call_smm_panel_api({
                    'service': service_id,
                    'link': link,
                    'quantity': quantity,
                    'comments': data.get('comments', '')
                })
                
                if smm_result.get('status') == 'success':
                    real_order_id = smm_result.get('order')
                    smm_panel_order_id = real_order_id
                    print(f"✅ SMM Panel 주문 생성 성공: {real_order_id}")
                else:
                    print(f"❌ SMM Panel API 호출 실패: {smm_result.get('message')}")
                    return jsonify({'error': f'SMM Panel API 호출 실패: {smm_result.get("message")}'}), 500
            except Exception as e:
                print(f"❌ SMM Panel API 호출 실패: {e}")
                return jsonify({'error': f'SMM Panel API 호출 실패: {str(e)}'}), 500
        elif is_package:
            # 패키지 주문은 임시 ID 사용 (패키지 단계별로 개별 처리)
            real_order_id = int(time.time())
            print(f"📦 패키지 주문 - 임시 ID 사용: {real_order_id} (패키지 단계별 개별 처리)")
        else:
            # 예약 주문은 임시 ID 사용 (나중에 예약 시간에 SMM Panel API 호출)
            real_order_id = int(time.time())
            print(f"📅 예약 주문 - 임시 ID 사용: {real_order_id}")
        
        # 주문 생성 (SMM Panel 주문번호 사용)
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                INSERT INTO orders (order_id, user_id, service_id, link, quantity, price, 
                                discount_amount, referral_code, status, created_at, updated_at,
                                is_scheduled, scheduled_datetime, is_split_delivery, split_days, split_quantity, smm_panel_order_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(),
                        %s, %s, %s, %s, %s, %s)
            """, (real_order_id, user_id, service_id, link, quantity, final_price, discount_amount,
                referral_data[0] if referral_data else None, '주문발송' if not is_scheduled else 'pending_payment',
                is_scheduled, scheduled_datetime, is_split_delivery, split_days, split_quantity, smm_panel_order_id))
        else:
            cursor.execute("""
                INSERT INTO orders (order_id, user_id, service_id, link, quantity, price, 
                                discount_amount, referral_code, status, created_at, updated_at,
                                is_scheduled, scheduled_datetime, is_split_delivery, split_days, split_quantity, smm_panel_order_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                        ?, ?, ?, ?, ?, ?)
            """, (real_order_id, user_id, service_id, link, quantity, final_price, discount_amount,
                referral_data[0] if referral_data else None, '주문발송' if not is_scheduled else 'pending_payment',
                is_scheduled, scheduled_datetime, is_split_delivery, split_days, split_quantity, smm_panel_order_id))
        
        order_id = real_order_id
        print(f"✅ 주문 생성 완료 - order_id: {order_id}, user_id: {user_id}, service_id: {service_id}, price: {final_price}")
        
        # 추천인이 있는 경우 10% 커미션 포인트 적립
        commission_amount = 0
        if referral_data:
            try:
                referrer_email = referral_data[1]
                commission_amount = final_price * 0.1  # 10% 커미션
                
                print(f"💰 커미션 계산 - 추천인: {referrer_email}, 구매금액: {final_price}, 커미션: {commission_amount}")
                
                # 기존 커미션 테이블에 기록
                if DATABASE_URL.startswith('postgresql://'):
                    cursor.execute("""
                        INSERT INTO commissions (referred_user, referrer_id, purchase_amount, 
                                                commission_amount, commission_rate, created_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                    """, (user_id, referrer_email, final_price, commission_amount, 0.1))
                else:
                    cursor.execute("""
                        INSERT INTO commissions (referred_user, referrer_id, purchase_amount, 
                                                commission_amount, commission_rate, created_at)
                        VALUES (?, ?, ?, ?, ?, datetime('now'))
                    """, (user_id, referrer_email, final_price, commission_amount, 0.1))
                
                print(f"✅ 커미션 기록 완료 - 추천인: {referrer_email}, 커미션: {commission_amount}")
                
                # 커미션 포인트 적립 처리
                if DATABASE_URL.startswith('postgresql://'):
                    # 추천인 포인트 계정이 있는지 확인
                    cursor.execute("SELECT id FROM commission_points WHERE referrer_email = %s", (referrer_email,))
                    existing_account = cursor.fetchone()
                    
                    if existing_account:
                        # 기존 계정 업데이트
                        cursor.execute("""
                            UPDATE commission_points 
                            SET total_earned = total_earned + %s, 
                                current_balance = current_balance + %s,
                                updated_at = NOW()
                            WHERE referrer_email = %s
                        """, (commission_amount, commission_amount, referrer_email))
                    else:
                        # 새 계정 생성
                        cursor.execute("""
                            INSERT INTO commission_points 
                            (referrer_email, total_earned, current_balance, created_at, updated_at)
                            VALUES (%s, %s, %s, NOW(), NOW())
                        """, (referrer_email, commission_amount, commission_amount))
                    
                    # 거래 내역 기록
                    cursor.execute("""
                        INSERT INTO commission_point_transactions 
                        (referrer_email, transaction_type, amount, balance_after, description, created_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                    """, (referrer_email, 'earned', commission_amount, commission_amount, f'추천인 커미션 적립 - 주문 ID: {order_id}'))
                else:
                    # SQLite 버전
                    cursor.execute("SELECT id FROM commission_points WHERE referrer_email = ?", (referrer_email,))
                    existing_account = cursor.fetchone()
                    
                    if existing_account:
                        cursor.execute("""
                            UPDATE commission_points 
                            SET total_earned = total_earned + ?, 
                                current_balance = current_balance + ?,
                                updated_at = datetime('now')
                            WHERE referrer_email = ?
                        """, (commission_amount, commission_amount, referrer_email))
                    else:
                        cursor.execute("""
                            INSERT INTO commission_points 
                            (referrer_email, total_earned, current_balance, created_at, updated_at)
                            VALUES (?, ?, ?, datetime('now'), datetime('now'))
                        """, (referrer_email, commission_amount, commission_amount))
                    
                    cursor.execute("""
                        INSERT INTO commission_point_transactions 
                        (referrer_email, transaction_type, amount, balance_after, description, created_at)
                        VALUES (?, ?, ?, ?, ?, datetime('now'))
                    """, (referrer_email, 'earned', commission_amount, commission_amount, f'추천인 커미션 적립 - 주문 ID: {order_id}'))
                
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
        
        # 패키지 상품인 경우 자동으로 분할 발송 설정 (30일간 하루 400개씩)
        if is_package and len(package_steps) > 0 and package_steps[0].get('id') == 515:
            print(f"📦 인스타 계정 상위노출 패키지 - 30일간 분할 발송 설정")
            is_split_delivery = True
            split_days = 30
            split_quantity = 400
            
            # 주문 정보 업데이트 (분할 발송 정보 추가)
            if DATABASE_URL.startswith('postgresql://'):
                cursor.execute("""
                    UPDATE orders SET is_split_delivery = %s, split_days = %s, split_quantity = %s
                    WHERE order_id = %s
                """, (True, 30, 400, order_id))
            else:
                cursor.execute("""
                    UPDATE orders SET is_split_delivery = ?, split_days = ?, split_quantity = ?
                    WHERE order_id = ?
                """, (True, 30, 400, order_id))
            
            conn.commit()
            print(f"✅ 패키지 상품 분할 발송 설정 완료 - 30일간 하루 400개씩")
        
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
            if DATABASE_URL.startswith('postgresql://'):
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
            
            # 모든 패키지 주문은 결제 완료 후에만 처리되도록 변경
            print(f"📦 패키지 주문 생성 완료 - 결제 완료 후 처리 예정")
            print(f"📦 주문 ID: {order_id}, 사용자: {user_id}, 단계 수: {len(package_steps)}")
            
            status = 'pending'  # 결제 완료 전까지는 pending 상태
            message = f'패키지 주문이 생성되었습니다. 결제 완료 후 {len(package_steps)}단계 순차 처리됩니다.'
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
        # pending_payment 상태도 처리 가능하도록 추가
        if status not in ['pending', 'pending_payment', 'package_processing', 'completed']:
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
            return jsonify({'error': '패키지 단계 정보가 없습니다.'}), 400
        
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
        
        # 별도 스레드에서 실행
        thread = threading.Thread(target=start_package_processing, daemon=False, name=f"PackageStart-{order_id}")
        thread.start()
        
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
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT step_number, step_name, service_id, quantity, smm_panel_order_id, status, created_at
                FROM package_progress 
                WHERE order_id = %s
                ORDER BY step_number ASC
            """, (order_id,))
        else:
            cursor.execute("""
                SELECT step_number, step_name, service_id, quantity, smm_panel_order_id, status, created_at
                FROM package_progress 
                WHERE order_id = ?
                ORDER BY step_number ASC
            """, (order_id,))
        
        progress_data = cursor.fetchall()
        
        # 주문 정보도 함께 조회
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT order_id, status, package_steps, created_at
                FROM orders 
                WHERE order_id = %s
            """, (order_id,))
        else:
            cursor.execute("""
                SELECT order_id, status, package_steps, created_at
                FROM orders 
                WHERE order_id = ?
            """, (order_id,))
        
        order_data = cursor.fetchone()
        
        if not order_data:
            return jsonify({'error': '주문을 찾을 수 없습니다.'}), 404
        
        # 패키지 단계 정보 파싱
        package_steps = []
        if order_data[2]:  # package_steps 컬럼
            try:
                package_steps = json.loads(order_data[2])
            except:
                package_steps = []
        
        # 진행 상황 데이터 포맷팅
        progress_list = []
        for row in progress_data:
            progress_list.append({
                'step_number': row[0],
                'step_name': row[1],
                'service_id': row[2],
                'quantity': row[3],
                'smm_panel_order_id': row[4],
                'status': row[5],
                'created_at': row[6].isoformat() if row[6] else None
            })
        
        return jsonify({
            'success': True,
            'order_id': order_id,
            'order_status': order_data[1],
            'package_steps': package_steps,
            'progress': progress_list,
            'total_steps': len(package_steps),
            'completed_steps': len([p for p in progress_list if p['status'] == 'completed']),
            'skipped_steps': len([p for p in progress_list if p['status'] == 'skipped'])
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
        
        # 주문 정보 조회 - 필요한 컬럼 모두 포함
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT order_id, service_id, link, quantity, price, status, created_at, 
                       smm_panel_order_id, detailed_service
                FROM orders 
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 20
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT order_id, service_id, link, quantity, price, status, created_at, 
                       smm_panel_order_id, detailed_service
                FROM orders 
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 20
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
                
                # SMM Panel API에서 실제 사용 금액 조회
                charge = 0
                if smm_panel_order_id:
                    try:
                        # SMM Panel API로 주문 상태 조회하여 실제 charge 값 가져오기
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
                
                order_list.append({
                    'id': display_order_id,
                    'order_id': display_order_id,
                    'service_id': service_id,
                    'service_name': detailed_service or f'서비스 {service_id}',
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
        
        # 사용자 ID 검증 (SQL 인젝션 방지)
        if not user_id.replace('_', '').replace('-', '').isalnum():
            return jsonify({'error': '잘못된 사용자 ID 형식입니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                INSERT INTO point_purchases (user_id, amount, price, status, buyer_name, bank_info, created_at, updated_at)
                VALUES (%s, %s, %s, 'pending', %s, %s, NOW(), NOW())
                RETURNING id
            """, (user_id, amount, price, buyer_name, bank_info))
        else:
            cursor.execute("""
                INSERT INTO point_purchases (user_id, amount, price, status, buyer_name, bank_info, created_at, updated_at)
                VALUES (?, ?, ?, 'pending', ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (user_id, amount, price, buyer_name, bank_info))
            cursor.execute("SELECT last_insert_rowid()")
        
        purchase_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'purchase_id': purchase_id,
            'status': 'pending',
            'message': '포인트 구매 신청이 완료되었습니다.'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'포인트 구매 신청 실패: {str(e)}'}), 500

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
            return jsonify({
                'success': False,
                'error': 'KCP 거래등록 실패: KCP_CERT_INFO(서비스 인증서)가 비어있거나 너무 짧습니다. PEM 전체를 저장하세요.',
            }), 400
        if not (kcp_cert_info.startswith('-----BEGIN') and 'END CERTIFICATE' in kcp_cert_info):
            return jsonify({
                'success': False,
                'error': 'KCP 거래등록 실패: KCP_CERT_INFO 형식 오류(PEM 구분자 누락). BEGIN/END CERTIFICATE 포함해 저장하세요.',
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
                    'kcp_response': kcp_response
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
        return jsonify({'success': False, 'error': f'KCP 거래등록에 실패했습니다: {str(e)}'}), 500

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
@app.route('/api/users/<user_id>', methods=['GET'])
def get_user(user_id):
    """사용자 정보 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
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
        conn.close()
        
        if user:
            return jsonify({
                'user_id': user[0],
                'email': user[1],
                'name': user[2],
                'created_at': user[3].isoformat() if hasattr(user[3], 'isoformat') else str(user[3])
            }), 200
        else:
            return jsonify({'error': '사용자를 찾을 수 없습니다.'}), 404
        
    except Exception as e:
        return jsonify({'error': f'사용자 정보 조회 실패: {str(e)}'}), 500

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
            # 추천인별 커미션 현황 조회
            cursor.execute("""
                SELECT 
                    rc.user_email,
                    rc.name,
                    rc.code,
                    COUNT(DISTINCT urc.user_id) as referral_count,
                    COALESCE(SUM(c.commission_amount), 0) as total_commission,
                    COALESCE(SUM(CASE 
                        WHEN c.payment_date >= DATE_TRUNC('month', CURRENT_DATE) 
                        THEN c.commission_amount 
                        ELSE 0 
                    END), 0) as this_month_commission,
                    COALESCE(SUM(CASE 
                        WHEN c.payment_date >= DATE_TRUNC('month', CURRENT_DATE) 
                        AND c.is_paid = false
                        THEN c.commission_amount 
                        ELSE 0 
                    END), 0) as unpaid_commission
                FROM referral_codes rc
                LEFT JOIN user_referral_connections urc ON rc.code = urc.referral_code
                LEFT JOIN commissions c ON rc.user_email = c.referrer_id
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
                    COUNT(DISTINCT urc.user_id) as referral_count,
                    COALESCE(SUM(c.commission_amount), 0) as total_commission,
                    COALESCE(SUM(CASE 
                        WHEN date(c.payment_date) >= date('now', 'start of month') 
                        THEN c.commission_amount 
                        ELSE 0 
                    END), 0) as this_month_commission,
                    COALESCE(SUM(CASE 
                        WHEN date(c.payment_date) >= date('now', 'start of month') 
                        AND c.is_paid = 0
                        THEN c.commission_amount 
                        ELSE 0 
                    END), 0) as unpaid_commission
                FROM referral_codes rc
                LEFT JOIN user_referral_connections urc ON rc.code = urc.referral_code
                LEFT JOIN commissions c ON rc.user_email = c.referrer_id
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
        
        # 환급 전 잔액 확인
        print(f"🔍 추천인 잔액 조회: {referrer_email}")
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT current_balance FROM commission_points WHERE referrer_email = %s
            """, (referrer_email,))
        else:
            cursor.execute("""
                SELECT current_balance FROM commission_points WHERE referrer_email = ?
            """, (referrer_email,))
        
        balance_result = cursor.fetchone()
        print(f"🔍 잔액 조회 결과: {balance_result}")
        if not balance_result:
            print(f"❌ 추천인을 찾을 수 없음: {referrer_email}")
            return jsonify({'error': '추천인을 찾을 수 없습니다.'}), 404
        
        current_balance = float(balance_result[0])
        if current_balance < float(amount):
            return jsonify({'error': f'잔액이 부족합니다. 현재 잔액: {current_balance}원'}), 400
        
        # 해당 추천인의 미지급 커미션을 지급 처리
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                UPDATE commissions 
                SET is_paid = true, paid_date = NOW()
                WHERE referrer_id = %s AND is_paid = false
            """, (referrer_email,))
        else:
            cursor.execute("""
                UPDATE commissions 
                SET is_paid = 1, paid_date = datetime('now')
                WHERE referrer_id = ? AND is_paid = 0
            """, (referrer_email,))
        
        # 환급 내역 저장 (새로운 테이블 필요)
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                INSERT INTO commission_payments (referrer_email, amount, payment_method, notes, paid_at)
                VALUES (%s, %s, %s, %s, NOW())
            """, (referrer_email, amount, payment_method, notes))
        else:
            cursor.execute("""
                INSERT INTO commission_payments (referrer_email, amount, payment_method, notes, paid_at)
                VALUES (?, ?, ?, ?, datetime('now'))
            """, (referrer_email, amount, payment_method, notes))
        
        # current_balance와 total_paid 업데이트 (환급 처리)
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                UPDATE commission_points 
                SET current_balance = current_balance - %s, total_paid = total_paid + %s, updated_at = NOW()
                WHERE referrer_email = %s
            """, (amount, amount, referrer_email))
        else:
            cursor.execute("""
                UPDATE commission_points 
                SET current_balance = current_balance - ?, total_paid = total_paid + ?, updated_at = CURRENT_TIMESTAMP
                WHERE referrer_email = ?
            """, (amount, amount, referrer_email))
        
        # 환급 후 잔액 조회
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT current_balance FROM commission_points WHERE referrer_email = %s
            """, (referrer_email,))
        else:
            cursor.execute("""
                SELECT current_balance FROM commission_points WHERE referrer_email = ?
            """, (referrer_email,))
        
        balance_result = cursor.fetchone()
        balance_after = balance_result[0] if balance_result else 0
        
        # 환급 거래 내역 기록
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                INSERT INTO commission_point_transactions 
                (referrer_email, transaction_type, amount, balance_after, description, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, (referrer_email, 'withdrawal', -float(amount), balance_after, f'관리자 환급 처리 - {amount}원'))
        else:
            cursor.execute("""
                INSERT INTO commission_point_transactions 
                (referrer_email, transaction_type, amount, balance_after, description, created_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (referrer_email, 'withdrawal', -float(amount), balance_after, f'관리자 환급 처리 - {amount}원'))
        
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
                SELECT referrer_email, amount, payment_method, notes, paid_at
                FROM commission_payments
                ORDER BY paid_at DESC
            """)
        else:
            cursor.execute("""
                SELECT referrer_email, amount, payment_method, notes, paid_at
                FROM commission_payments
                ORDER BY paid_at DESC
            """)
        
        payments = []
        for row in cursor.fetchall():
            paid_at = row[4]
            if hasattr(paid_at, 'isoformat'):
                paid_at = paid_at.isoformat()
            else:
                paid_at = str(paid_at)
            
            payments.append({
                'referrer_email': row[0],
                'amount': float(row[1]),
                'payment_method': row[2],
                'notes': row[3],
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
                SELECT id, referrer_email, referral_code, name, phone, created_at, status
                FROM referrals 
                ORDER BY created_at DESC
            """)
        else:
            cursor.execute("""
                SELECT id, referrer_email, referral_code, name, phone, created_at, status
                FROM referrals 
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
                'status': row[6]
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
                SELECT id, referred_user, purchase_amount, commission_amount, 
                    commission_rate, payment_date
                FROM commissions 
                ORDER BY payment_date DESC
            """)
        else:
            cursor.execute("""
                SELECT id, referred_user, purchase_amount, commission_amount, 
                    commission_rate, payment_date
                FROM commissions 
                ORDER BY payment_date DESC
            """)
        
        commissions = []
        for row in cursor.fetchall():
            commissions.append({
                'id': row[0],
                'referredUser': row[1],
                'purchaseAmount': row[2],
                'commissionAmount': row[3],
                'commissionRate': f"{row[4] * 100}%" if row[4] else "0%",
                'paymentDate': row[5].strftime('%Y-%m-%d') if hasattr(row[5], 'strftime') else row[5]
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

@app.route('/')
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
                SELECT total_earned, total_paid, current_balance, created_at, updated_at
                FROM commission_points 
                WHERE referrer_email = %s
            """, (referrer_email,))
        else:
            cursor.execute("""
                SELECT total_earned, total_paid, current_balance, created_at, updated_at
                FROM commission_points 
                WHERE referrer_email = ?
            """, (referrer_email,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return jsonify({
                'total_earned': float(result[0]),
                'total_paid': float(result[1]),
                'current_balance': float(result[2]),
                'created_at': result[3].isoformat() if hasattr(result[3], 'isoformat') else str(result[3]),
                'updated_at': result[4].isoformat() if hasattr(result[4], 'isoformat') else str(result[4])
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
                SELECT transaction_type, amount, balance_after, description, created_at
                FROM commission_point_transactions 
                WHERE referrer_email = %s
                ORDER BY created_at DESC
            """, (referrer_email,))
        else:
            cursor.execute("""
                SELECT transaction_type, amount, balance_after, description, created_at
                FROM commission_point_transactions 
                WHERE referrer_email = ?
                ORDER BY created_at DESC
            """, (referrer_email,))
        
        transactions = []
        for row in cursor.fetchall():
            transactions.append({
                'type': row[0],
                'amount': float(row[1]),
                'balance_after': float(row[2]),
                'description': row[3],
                'created_at': row[4].isoformat() if hasattr(row[4], 'isoformat') else str(row[4])
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
        
        # 현재 잔액 확인
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
        
        result = cursor.fetchone()
        if not result or float(result[0]) < float(amount):
            return jsonify({'error': '잔액이 부족합니다.'}), 400
        
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
                SELECT id, user_id, service_id, link, quantity, price, scheduled_datetime, status, created_at, processed_at
                FROM scheduled_orders 
                ORDER BY scheduled_datetime DESC
                LIMIT 50
            """)
        else:
            cursor.execute("""
                SELECT id, user_id, service_id, link, quantity, price, scheduled_datetime, status, created_at, processed_at
                FROM scheduled_orders 
                ORDER BY scheduled_datetime DESC
                LIMIT 50
            """)
        
        orders = cursor.fetchall()
        
        order_list = []
        for order in orders:
            order_list.append({
                'id': order[0],
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
            return jsonify({
                'success': False,
                'error': result.get('message', 'Failed to get services')
            }), 500
            
    except Exception as e:
        print(f"❌ SMM Panel 서비스 목록 조회 오류: {str(e)}")
        return jsonify({'error': f'서비스 목록 조회 실패: {str(e)}'}), 500

# 스케줄러 작업: 예약/분할 주문 처리
@app.route('/api/cron/process-scheduled-orders', methods=['POST'])
def cron_process_scheduled_orders():
    """예약 주문 처리 크론잡"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 현재 시간이 지난 예약 주문 조회 (scheduled_orders 테이블에서)
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"🔍 예약 주문 조회 중... (현재 시간: {current_time})")
        
        # 먼저 모든 pending 예약 주문을 확인
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT id, user_id, service_id, link, quantity, price, package_steps, scheduled_datetime, status
                FROM scheduled_orders 
                WHERE status = 'pending'
                ORDER BY scheduled_datetime ASC
            """)
        else:
            cursor.execute("""
                SELECT id, user_id, service_id, link, quantity, price, package_steps, scheduled_datetime, status
                FROM scheduled_orders 
                WHERE status = 'pending'
                ORDER BY scheduled_datetime ASC
            """)
        
        all_pending_orders = cursor.fetchall()
        print(f"🔍 모든 pending 예약 주문: {len(all_pending_orders)}개")
        
        for order in all_pending_orders:
            order_id, user_id, service_id, link, quantity, price, package_steps, scheduled_datetime, status = order
            print(f"🔍 예약 주문: ID={order_id}, 예약시간={scheduled_datetime}, 상태={status}, 현재시간={current_time}")
        
        # 현재 시간이 지난 예약 주문만 조회
        if DATABASE_URL.startswith('postgresql://'):
            cursor.execute("""
                SELECT id, user_id, service_id, link, quantity, price, package_steps, scheduled_datetime
                FROM scheduled_orders 
                WHERE status = 'pending'
                AND scheduled_datetime <= NOW()
            """)
        else:
            cursor.execute("""
                SELECT id, user_id, service_id, link, quantity, price, package_steps, scheduled_datetime
                FROM scheduled_orders 
                WHERE status = 'pending'
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
            package_steps = json.loads(order[6]) if order[6] else []
            
            print(f"🔄 예약 주문 처리 중: ID {order_id}, 사용자 {user_id}")
            
            # 실제 주문 생성
            success = create_actual_order_from_scheduled(
                order_id, user_id, service_id, link, quantity, price, package_steps
            )
            
            if success:
                # 예약 주문 상태를 처리 완료로 변경
                if DATABASE_URL.startswith('postgresql://'):
                    cursor.execute("""
                        UPDATE scheduled_orders 
                        SET status = 'completed', processed_at = NOW()
                        WHERE id = %s
                    """, (order_id,))
                else:
                    cursor.execute("""
                        UPDATE scheduled_orders 
                        SET status = 'completed', processed_at = datetime('now')
                        WHERE id = ?
                    """, (order_id,))
                
                conn.commit()
                processed_count += 1
                print(f"✅ 예약 주문 {order_id} 처리 완료")
            else:
                print(f"❌ 예약 주문 {order_id} 처리 실패")
        
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
            # 기존 사용자 업데이트
            user_id, user_email, user_name, user_google_id, last_login = existing_user
            
            # 구글 ID가 없으면 추가
            if not user_google_id:
                cursor.execute("""
                    UPDATE users 
                    SET google_id = %s, last_login = %s
                    WHERE user_id = %s
                """, (google_id, datetime.now(), user_id))
            else:
                cursor.execute("""
                    UPDATE users 
                    SET last_login = %s
                    WHERE user_id = %s
                """, (datetime.now(), user_id))
            
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
            # 새 사용자 생성
            user_id = f"google_{google_id}"
            
            cursor.execute("""
                INSERT INTO users (
                    user_id, email, name, google_id, profile_image, last_login, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id, email, display_name, google_id, photo_url, 
                datetime.now(), datetime.now(), datetime.now()
            ))
            
            # 포인트 테이블에도 초기 레코드 생성
            cursor.execute("""
                INSERT INTO points (user_id, points, created_at, updated_at)
                VALUES (%s, %s, %s, %s)
            """, (user_id, 0, datetime.now(), datetime.now()))
            
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

def require_admin_auth(f):
    """관리자 인증 데코레이터"""
    def decorated_function(*args, **kwargs):
        admin_token = request.headers.get('X-Admin-Token')
        if admin_token != 'admin_sociality_2024':
            return jsonify({
                'success': False,
                'error': '관리자 권한이 필요합니다.'
            }), 403
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

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
    # 개발 서버 실행
    app.run(host='0.0.0.0', port=8000, debug=False)