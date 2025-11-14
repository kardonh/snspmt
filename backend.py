import os
import json
import re
import random
import string
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta 
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
import requests
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


def parse_user_identifier(raw_identifier):
    """문자열 또는 숫자인 사용자 식별자를 정규화"""
    if raw_identifier is None:
        return {
            'raw': None,
            'user_id': None,
            'external_uid': None
        }

    raw_str = str(raw_identifier).strip()
    if not raw_str:
        return {
            'raw': '',
            'user_id': None,
            'external_uid': None
        }

    try:
        numeric_id = int(raw_str)
    except ValueError:
        numeric_id = None

    return {
        'raw': raw_str,
        'user_id': numeric_id,
        'external_uid': raw_str
    }


def generate_placeholder_email(external_uid: str | None, attempt: int = 0) -> str:
    """외부 UID를 기반으로 임시 이메일 생성"""
    base_source = external_uid or 'user'
    base = re.sub(r'[^a-zA-Z0-9]+', '_', base_source).strip('_')
    if not base:
        base = 'user'
    suffix = f"_{attempt}" if attempt else ""
    return f"{base[:180]}{suffix}@placeholder.local"


USER_SELECT_COLUMNS = (
    "user_id, external_uid, email, username, referral_code, referral_status, "
    "is_admin, created_at, updated_at"
)


DEFAULT_COMMISSION_RATE = Decimal('0.10')
MAX_JOB_ATTEMPTS = 5


def generate_unique_referral_code(cursor, length: int = 8) -> str:
    """중복되지 않는 추천인 코드 생성"""
    while True:
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        code = f"REF{random_part}"
        cursor.execute("SELECT 1 FROM users WHERE referral_code = %s", (code,))
        if not cursor.fetchone():
            return code


def fetch_user_by_referral_code(cursor, referral_code: str):
    """추천인 코드로 사용자 레코드 조회"""
    if not referral_code:
        return None
    cursor.execute(
        f"SELECT {USER_SELECT_COLUMNS} FROM users WHERE referral_code = %s",
        (referral_code,)
    )
    return cursor.fetchone()


def get_user_by_id(cursor, user_id: int):
    """user_id로 사용자 조회"""
    cursor.execute(
        f"SELECT {USER_SELECT_COLUMNS} FROM users WHERE user_id = %s",
        (user_id,)
    )
    return cursor.fetchone()


def get_user_by_email(cursor, email: str):
    """이메일로 사용자 조회"""
    cursor.execute(
        f"SELECT {USER_SELECT_COLUMNS} FROM users WHERE email = %s",
        (email,)
    )
    return cursor.fetchone()


def get_active_referral(cursor, referred_user_id: int) -> dict | None:
    """사용자에 대한 활성 추천인 정보를 조회"""
    cursor.execute(
        """
        SELECT referral_id, referrer_user_id
          FROM referrals
         WHERE referred_user_id = %s
           AND status = 'approved'
         ORDER BY referral_id DESC
         LIMIT 1
        """,
        (referred_user_id,)
    )
    row = cursor.fetchone()
    if not row:
        return None
    return {
        'referral_id': row['referral_id'] if isinstance(row, dict) else row[0],
        'referrer_user_id': row['referrer_user_id'] if isinstance(row, dict) else row[1]
    }


def redeem_user_coupon(cursor, user_id: int, user_coupon_id: int | None, order_total: Decimal) -> tuple[Decimal, int | None]:
    """사용자 쿠폰을 검증/사용 처리 후 할인 금액과 coupon_id 반환"""
    if not user_coupon_id:
        return Decimal('0'), None

    cursor.execute(
        """
        SELECT uc.user_coupon_id,
               uc.status,
               c.coupon_id,
               c.discount_type,
               c.discount_value,
               c.min_order_amount
          FROM user_coupons uc
          JOIN coupons c ON uc.coupon_id = c.coupon_id
         WHERE uc.user_coupon_id = %s
           AND uc.user_id = %s
         FOR UPDATE
        """,
        (user_coupon_id, user_id)
    )
    row = cursor.fetchone()
    if not row:
        raise ValueError('유효하지 않은 쿠폰입니다.')

    status = row['status'] if isinstance(row, dict) else row[1]
    if status != 'active':
        raise ValueError('이미 사용되었거나 비활성화된 쿠폰입니다.')

    discount_type = row['discount_type'] if isinstance(row, dict) else row[3]
    discount_value = row['discount_value'] if isinstance(row, dict) else row[4]
    min_order_amount = row['min_order_amount'] if isinstance(row, dict) else row[5]

    if min_order_amount and order_total < min_order_amount:
        raise ValueError('쿠폰 사용을 위한 최소 주문 금액을 충족하지 않습니다.')

    discount_amount = Decimal('0')
    if discount_type == 'percentage':
        discount_amount = (order_total * Decimal(discount_value or 0) / Decimal('100')).quantize(Decimal('0.01'))
    elif discount_type == 'fixed':
        discount_amount = Decimal(discount_value or 0)

    discount_amount = min(discount_amount, order_total)

    cursor.execute(
        """
        UPDATE user_coupons
           SET status = 'used',
               used_at = NOW(),
               updated_at = NOW()
         WHERE user_coupon_id = %s
        """,
        (user_coupon_id,)
    )

    coupon_id = row['coupon_id'] if isinstance(row, dict) else row[2]
    return discount_amount, coupon_id


def ensure_wallet_balance(cursor, wallet: dict, amount: Decimal):
    """지갑 잔액이 충분한지 확인"""
    if wallet['balance'] < amount:
        raise ValueError('지갑 잔액이 부족합니다.')


def create_wallet_transaction(cursor, wallet_id: int, tx_type: str, amount: Decimal, status: str, meta: dict | None = None):
    """지갑 트랜잭션 기록"""
    cursor.execute(
        """
        INSERT INTO wallet_transactions (
            wallet_id, type, amount, status, locked, meta_json, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, FALSE, %s, NOW(), NOW())
        RETURNING transaction_id
        """,
        (wallet_id, tx_type, amount, status, json.dumps(meta, ensure_ascii=False) if meta else None)
    )
    return cursor.fetchone()['transaction_id']


def record_commission(cursor, referral_id: int, order_id: int, amount: Decimal):
    """커미션 적립 기록 생성"""
    cursor.execute(
        """
        INSERT INTO commissions (referral_id, order_id, amount, status, created_at)
        VALUES (%s, %s, %s, 'accrued', NOW())
        RETURNING commission_id
        """,
        (referral_id, order_id, amount)
    )
    return cursor.fetchone()['commission_id']


def fetch_user_record(cursor, identifier: dict, email: str | None = None):
    """식별자나 이메일로 사용자 레코드 조회"""
    if identifier.get('user_id') is not None:
        cursor.execute(
            f"SELECT {USER_SELECT_COLUMNS} FROM users WHERE user_id = %s",
            (identifier['user_id'],)
        )
        row = cursor.fetchone()
        if row:
            return row

    external_uid = identifier.get('external_uid')
    if external_uid:
        cursor.execute(
            f"SELECT {USER_SELECT_COLUMNS} FROM users WHERE external_uid = %s",
            (external_uid,)
        )
        row = cursor.fetchone()
        if row:
            return row

    if email:
        cursor.execute(
            f"SELECT {USER_SELECT_COLUMNS} FROM users WHERE email = %s",
            (email,)
        )
        row = cursor.fetchone()
        if row:
            return row

    return None


def ensure_user_record(cursor, identifier: dict, email: str | None = None, username: str | None = None):
    """사용자 레코드를 보장 (없으면 생성)"""
    user = fetch_user_record(cursor, identifier, email=email)
    if user:
        # referral_code가 없다면 새로 발급
        referral_code = user.get('referral_code') if isinstance(user, dict) else None
        if not referral_code:
            new_code = generate_unique_referral_code(cursor)
            cursor.execute(
                f"""
                UPDATE users
                   SET referral_code = %s,
                       referral_status = COALESCE(referral_status, 'approved'),
                       updated_at = NOW()
                 WHERE user_id = %s
                RETURNING {USER_SELECT_COLUMNS}
                """,
                (new_code, user['user_id'] if isinstance(user, dict) else user[0])
            )
            user = cursor.fetchone()
        return user

    external_uid = identifier.get('external_uid')
    if not external_uid and not email:
        raise ValueError("사용자 식별자 정보가 부족합니다.")

    attempt = 0
    candidate_email = email or generate_placeholder_email(external_uid, attempt)

    while True:
        cursor.execute("SELECT 1 FROM users WHERE email = %s", (candidate_email,))
        if cursor.fetchone():
            attempt += 1
            candidate_email = generate_placeholder_email(external_uid, attempt)
            continue

        referral_code = generate_unique_referral_code(cursor)
        cursor.execute(
            f"""
            INSERT INTO users (external_uid, email, username, referral_code, referral_status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING {USER_SELECT_COLUMNS}
            """,
            (
                external_uid,
                candidate_email,
                username or (external_uid[:50] if external_uid else 'User'),
                referral_code,
                'approved'
            )
        )
        user = cursor.fetchone()
        return user


def ensure_wallet_record(cursor, user_id: int):
    """지갑 레코드를 보장 (없으면 생성)"""
    cursor.execute(
        """
        INSERT INTO wallets (user_id, balance, created_at, updated_at)
        VALUES (%s, 0, NOW(), NOW())
        ON CONFLICT (user_id) DO NOTHING
        """,
        (user_id,)
    )

    cursor.execute(
        """
        SELECT wallet_id, user_id, balance, created_at, updated_at
        FROM wallets
        WHERE user_id = %s
        """,
        (user_id,)
    )
    return cursor.fetchone()


def to_decimal(amount) -> Decimal:
    """숫자 값을 Decimal(소수점 둘째 자리)로 변환"""
    decimal_value = Decimal(str(amount))
    return decimal_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def decimal_to_float(value) -> float:
    """Decimal 값을 float로 변환"""
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def parse_bool(value, default: bool | None = None) -> bool | None:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ('true', '1', 'yes', 'on')


def parse_int(value, default: int | None = None) -> int | None:
    if value is None or value == '':
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def to_isoformat_or_none(value):
    """datetime 값을 ISO 포맷 문자열로 변환"""
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)

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
        data = request.get_json() or {}
        print("=== 예약 발송 주문 생성 요청 ===")
        print(f"요청 데이터: {data}")

        raw_user_id = data.get('user_id')
        service_id = data.get('service_id')
        link = data.get('link')
        quantity = data.get('quantity')
        price = data.get('price') or data.get('total_price')
        scheduled_datetime = data.get('scheduled_datetime') or data.get('scheduled_at')
        package_steps = data.get('package_steps') or []
        runs = int(data.get('runs', 1) or 1)
        interval = int(data.get('interval', 0) or 0)
        comments = data.get('comments')

        missing_fields = []
        if raw_user_id is None:
            missing_fields.append('user_id')
        if not service_id:
            missing_fields.append('service_id')
        if not link:
            missing_fields.append('link')
        if quantity is None:
            missing_fields.append('quantity')
        if price is None:
            missing_fields.append('price')
        if not scheduled_datetime:
            missing_fields.append('scheduled_datetime')

        if missing_fields:
            return jsonify({'error': f"필수 필드가 누락되었습니다: {', '.join(missing_fields)}"}), 400

        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return jsonify({'error': 'quantity는 1 이상의 정수여야 합니다.'}), 400

        def parse_datetime(value: str) -> datetime:
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                return datetime.strptime(value, '%Y-%m-%d %H:%M')

        try:
            scheduled_dt = parse_datetime(str(scheduled_datetime))
        except ValueError:
            return jsonify({'error': 'scheduled_datetime 형식이 올바르지 않습니다.'}), 400

        now = datetime.now(tz=scheduled_dt.tzinfo) if scheduled_dt.tzinfo else datetime.now()
        time_diff_minutes = (scheduled_dt - now).total_seconds() / 60
        if time_diff_minutes < 5 or time_diff_minutes > 10080:
            return jsonify({'error': '예약 시간은 현재 시간으로부터 5분 이상 7일 이내여야 합니다.'}), 400

        identifier = parse_user_identifier(raw_user_id)

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        user = ensure_user_record(cursor, identifier)
        ensure_wallet_record(cursor, user['user_id'])

        total_amount = to_decimal(price)
        referral_info = get_active_referral(cursor, user['user_id'])

        notes = {
            'order_type': 'scheduled',
            'service_id': service_id,
            'link': link,
            'quantity': quantity,
            'scheduled_datetime': scheduled_dt.isoformat(),
            'package_steps': package_steps,
            'runs': runs,
            'interval': interval,
            'comments': comments,
            'raw_payload': data
        }

        cursor.execute(
            """
            INSERT INTO orders (
                user_id,
                referrer_user_id,
                total_amount,
                discount_amount,
                final_amount,
                status,
                notes,
                created_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, 'scheduled', %s, NOW(), NOW())
            RETURNING order_id
            """,
            (
                user['user_id'],
                referral_info['referrer_user_id'] if referral_info else None,
                total_amount,
                Decimal('0'),
                total_amount,
                json.dumps(notes, ensure_ascii=False)
            )
        )
        order_id = cursor.fetchone()['order_id']

        job_ids = []
        if package_steps:
            cumulative_delay = 0
            total_steps = len(package_steps)
            for index, step in enumerate(package_steps):
                step_delay = int(step.get('delay', 0) or 0)
                scheduled_at = scheduled_dt + timedelta(minutes=cumulative_delay)
                payload = {
                    'job_type': 'package_step',
                    'order_id': order_id,
                    'step_index': index,
                    'total_steps': total_steps,
                    'step': step,
                    'service_id': service_id,
                    'link': link,
                    'quantity': step.get('quantity', quantity),
                    'runs': runs,
                    'interval': interval,
                    'comments': comments
                }
                job_id = enqueue_work_job(cursor, user['user_id'], scheduled_at, payload)
                job_ids.append(job_id)
                cumulative_delay += step_delay if step_delay > 0 else 0
        else:
            payload = {
                'job_type': 'scheduled_order',
                'order_id': order_id,
                'service_id': service_id,
                'link': link,
                'quantity': quantity,
                'runs': runs,
                'interval': interval,
                'comments': comments
            }
            job_id = enqueue_work_job(cursor, user['user_id'], scheduled_dt, payload)
            job_ids.append(job_id)

        status_jobs = schedule_order_status_transitions(cursor, order_id, user['user_id'])
        if status_jobs:
            job_ids.extend(status_jobs)

        if job_ids:
            merge_order_notes(cursor, order_id, {'scheduled_job_ids': job_ids})

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'예약 발송이 설정되었습니다. ({scheduled_dt.isoformat()} 실행 예정)',
            'order_id': order_id,
            'scheduled_datetime': scheduled_dt.isoformat(),
            'job_ids': job_ids
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
    """패키지 상품 분할 발송 실행"""
    try:
        service_id = package_steps[0].get('id', 515) if package_steps else 515
        quantity = package_steps[0].get('quantity', 400) if package_steps else 400
        response = call_smm_panel_api({
            'service': service_id,
            'link': link,
            'quantity': quantity,
            'comments': f"{comments or ''} (패키지 분할 {day_number}일차)"
        })
        return {
            'success': response.get('status') == 'success',
            'response': response
        }
    except Exception as e:
        print(f"❌ 패키지 분할 발송 처리 실패: {e}")
        return {'success': False, 'error': str(e)}

def parse_user_identifier(raw_identifier):
    """문자열 또는 숫자인 사용자 식별자를 정규화"""
    if raw_identifier is None:
        return {
            'raw': None,
            'user_id': None,
            'external_uid': None
        }

    raw_str = str(raw_identifier).strip()
    if not raw_str:
        return {
            'raw': '',
            'user_id': None,
            'external_uid': None
        }

    try:
        numeric_id = int(raw_str)
    except ValueError:
        numeric_id = None

    return {
        'raw': raw_str,
        'user_id': numeric_id,
        'external_uid': raw_str
    }


def generate_placeholder_email(external_uid: str | None, attempt: int = 0) -> str:
    """외부 UID를 기반으로 임시 이메일 생성"""
    base_source = external_uid or 'user'
    base = re.sub(r'[^a-zA-Z0-9]+', '_', base_source).strip('_')
    if not base:
        base = 'user'
    suffix = f"_{attempt}" if attempt else ""
    return f"{base[:180]}{suffix}@placeholder.local"


USER_SELECT_COLUMNS = (
    "user_id, external_uid, email, username, referral_code, referral_status, "
    "is_admin, created_at, updated_at"
)


DEFAULT_COMMISSION_RATE = Decimal('0.10')


def generate_unique_referral_code(cursor, length: int = 8) -> str:
    """중복되지 않는 추천인 코드 생성"""
    while True:
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        code = f"REF{random_part}"
        cursor.execute("SELECT 1 FROM users WHERE referral_code = %s", (code,))
        if not cursor.fetchone():
            return code


def fetch_user_by_referral_code(cursor, referral_code: str):
    """추천인 코드로 사용자 레코드 조회"""
    if not referral_code:
        return None
    cursor.execute(
        f"SELECT {USER_SELECT_COLUMNS} FROM users WHERE referral_code = %s",
        (referral_code,)
    )
    return cursor.fetchone()


def get_user_by_id(cursor, user_id: int):
    """user_id로 사용자 조회"""
    cursor.execute(
        f"SELECT {USER_SELECT_COLUMNS} FROM users WHERE user_id = %s",
        (user_id,)
    )
    return cursor.fetchone()


def get_user_by_email(cursor, email: str):
    """이메일로 사용자 조회"""
    cursor.execute(
        f"SELECT {USER_SELECT_COLUMNS} FROM users WHERE email = %s",
        (email,)
    )
    return cursor.fetchone()


def get_active_referral(cursor, referred_user_id: int) -> dict | None:
    """사용자에 대한 활성 추천인 정보를 조회"""
    cursor.execute(
        """
        SELECT referral_id, referrer_user_id
          FROM referrals
         WHERE referred_user_id = %s
           AND status = 'approved'
         ORDER BY referral_id DESC
         LIMIT 1
        """,
        (referred_user_id,)
    )
    row = cursor.fetchone()
    if not row:
        return None
    return {
        'referral_id': row['referral_id'] if isinstance(row, dict) else row[0],
        'referrer_user_id': row['referrer_user_id'] if isinstance(row, dict) else row[1]
    }


def redeem_user_coupon(cursor, user_id: int, user_coupon_id: int | None, order_total: Decimal) -> tuple[Decimal, int | None]:
    """사용자 쿠폰을 검증/사용 처리 후 할인 금액과 coupon_id 반환"""
    if not user_coupon_id:
        return Decimal('0'), None

    cursor.execute(
        """
        SELECT uc.user_coupon_id,
               uc.status,
               c.coupon_id,
               c.discount_type,
               c.discount_value,
               c.min_order_amount
          FROM user_coupons uc
          JOIN coupons c ON uc.coupon_id = c.coupon_id
         WHERE uc.user_coupon_id = %s
           AND uc.user_id = %s
         FOR UPDATE
        """,
        (user_coupon_id, user_id)
    )
    row = cursor.fetchone()
    if not row:
        raise ValueError('유효하지 않은 쿠폰입니다.')

    status = row['status'] if isinstance(row, dict) else row[1]
    if status != 'active':
        raise ValueError('이미 사용되었거나 비활성화된 쿠폰입니다.')

    discount_type = row['discount_type'] if isinstance(row, dict) else row[3]
    discount_value = row['discount_value'] if isinstance(row, dict) else row[4]
    min_order_amount = row['min_order_amount'] if isinstance(row, dict) else row[5]

    if min_order_amount and order_total < min_order_amount:
        raise ValueError('쿠폰 사용을 위한 최소 주문 금액을 충족하지 않습니다.')

    discount_amount = Decimal('0')
    if discount_type == 'percentage':
        discount_amount = (order_total * Decimal(discount_value or 0) / Decimal('100')).quantize(Decimal('0.01'))
    elif discount_type == 'fixed':
        discount_amount = Decimal(discount_value or 0)

    discount_amount = min(discount_amount, order_total)

    cursor.execute(
        """
        UPDATE user_coupons
           SET status = 'used',
               used_at = NOW(),
               updated_at = NOW()
         WHERE user_coupon_id = %s
        """,
        (user_coupon_id,)
    )

    coupon_id = row['coupon_id'] if isinstance(row, dict) else row[2]
    return discount_amount, coupon_id


def ensure_wallet_balance(cursor, wallet: dict, amount: Decimal):
    """지갑 잔액이 충분한지 확인"""
    if wallet['balance'] < amount:
        raise ValueError('지갑 잔액이 부족합니다.')


def create_wallet_transaction(cursor, wallet_id: int, tx_type: str, amount: Decimal, status: str, meta: dict | None = None):
    """지갑 트랜잭션 기록"""
    cursor.execute(
        """
        INSERT INTO wallet_transactions (
            wallet_id, type, amount, status, locked, meta_json, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, FALSE, %s, NOW(), NOW())
        RETURNING transaction_id
        """,
        (wallet_id, tx_type, amount, status, json.dumps(meta, ensure_ascii=False) if meta else None)
    )
    return cursor.fetchone()['transaction_id']


def record_commission(cursor, referral_id: int, order_id: int, amount: Decimal):
    """커미션 적립 기록 생성"""
    cursor.execute(
        """
        INSERT INTO commissions (referral_id, order_id, amount, status, created_at)
        VALUES (%s, %s, %s, 'accrued', NOW())
        RETURNING commission_id
        """,
        (referral_id, order_id, amount)
    )
    return cursor.fetchone()['commission_id']


def enqueue_work_job(cursor, user_id: int, schedule_at: datetime | None, payload: dict, order_item_id: int | None = None, package_item_id: int | None = None):
    """work_jobs 테이블에 작업 추가"""
    cursor.execute(
        """
        INSERT INTO work_jobs (
            user_id,
            order_item_id,
            package_item_id,
            schedule_at,
            status,
            attempts,
            payload_json,
            created_at,
            updated_at
        )
        VALUES (
            %s, %s, %s, %s, 'pending', 0, %s, NOW(), NOW()
        )
        RETURNING job_id
        """,
        (
            user_id,
            order_item_id,
            package_item_id,
            schedule_at,
            json.dumps(payload, ensure_ascii=False)
        )
    )
    return cursor.fetchone()['job_id']


def ensure_order_status_job(cursor, order_id: int, user_id: int, target_status: str, delay_minutes: int) -> int | None:
    """중복 없이 주문 상태 업데이트 작업을 예약"""
    cursor.execute(
        """
        SELECT job_id
          FROM work_jobs
         WHERE payload_json->>'job_type' = 'order_status_update'
           AND payload_json->>'order_id' = %s
           AND payload_json->>'new_status' = %s
           AND status IN ('pending','processing')
        """,
        (str(order_id), target_status)
    )
    existing = cursor.fetchone()
    if existing:
        return None

    schedule_at = datetime.utcnow() + timedelta(minutes=delay_minutes)
    payload = {
        'job_type': 'order_status_update',
        'order_id': order_id,
        'new_status': target_status
    }
    return enqueue_work_job(cursor, user_id, schedule_at, payload)


def schedule_order_status_transitions(
    cursor,
    order_id: int,
    user_id: int,
    start_delay_minutes: int = 2,
    completion_delay_minutes: int = 1440
) -> list[int]:
    """주문 상태를 자동으로 processing/완료로 전환하도록 작업 예약"""
    job_ids: list[int] = []

    processing_job_id = ensure_order_status_job(cursor, order_id, user_id, 'processing', start_delay_minutes)
    if processing_job_id:
        job_ids.append(processing_job_id)

    completion_job_id = ensure_order_status_job(cursor, order_id, user_id, 'completed', completion_delay_minutes)
    if completion_job_id:
        job_ids.append(completion_job_id)

    return job_ids


def load_order_for_update(cursor, order_id: int) -> dict | None:
    """주문 정보를 잠금과 함께 로드"""
    cursor.execute(
        """
        SELECT order_id, user_id, status, notes
          FROM orders
         WHERE order_id = %s
         FOR UPDATE
        """,
        (order_id,)
    )
    row = cursor.fetchone()
    if not row:
        return None

    if isinstance(row, dict):
        notes = row.get('notes')
        order = dict(row)
    else:
        _, _, status, notes = row
        order = {
            'order_id': row[0],
            'user_id': row[1],
            'status': status,
            'notes': notes
        }

    if isinstance(order.get('notes'), str):
        try:
            order['notes'] = json.loads(order['notes'])
        except json.JSONDecodeError:
            order['notes'] = {}
    elif order.get('notes') is None:
        order['notes'] = {}

    return order


def load_order_items(cursor, order_id: int) -> list[dict]:
    """주문에 속한 아이템 목록 조회"""
    cursor.execute(
        """
        SELECT order_item_id,
               variant_id,
               quantity,
               unit_price,
               line_amount,
               link,
               status
          FROM order_items
         WHERE order_id = %s
        """,
        (order_id,)
    )
    rows = cursor.fetchall()
    if not rows:
        return []

    if isinstance(rows[0], dict):
        return rows

    items: list[dict] = []
    for row in rows:
        items.append({
            'order_item_id': row[0],
            'variant_id': row[1],
            'quantity': row[2],
            'unit_price': row[3],
            'line_amount': row[4],
            'link': row[5],
            'status': row[6]
        })
    return items


def update_order_status(cursor, order_id: int, new_status: str) -> None:
    """주문 상태 업데이트"""
    cursor.execute(
        """
        UPDATE orders
           SET status = %s,
               updated_at = NOW()
         WHERE order_id = %s
        """,
        (new_status, order_id)
    )


def update_order_items_status(cursor, order_id: int, new_status: str) -> None:
    """주문 내 아이템 상태 일괄 업데이트"""
    cursor.execute(
        """
        UPDATE order_items
           SET status = %s,
               updated_at = NOW()
         WHERE order_id = %s
        """,
        (new_status, order_id)
    )


def merge_order_notes(cursor, order_id: int, updates: dict) -> dict:
    """주문 notes JSON을 병합 업데이트"""
    order = load_order_for_update(cursor, order_id)
    if not order:
        raise ValueError('주문을 찾을 수 없습니다.')

    notes = order.get('notes') or {}
    notes.update(updates)

    cursor.execute(
        """
        UPDATE orders
           SET notes = %s::jsonb,
               updated_at = NOW()
         WHERE order_id = %s
        """,
        (json.dumps(notes, ensure_ascii=False), order_id)
    )
    order['notes'] = notes
    return order


def normalize_panel_status(status_text: str | None) -> str:
    """SMM Panel 상태 문자열을 내부 상태로 변환"""
    value = (status_text or '').strip().lower()
    if value in ('completed', 'success', 'delivered', 'finished', 'complete'):
        return 'completed'
    if value in ('processing', 'in progress', 'pending', 'running', 'queued', 'waiting'):
        return 'processing'
    if value in ('partial', 'partialling'):
        return 'partial'
    if value in ('canceled', 'cancelled', 'failed', 'error', 'refunded'):
        return 'failed'
    return 'unknown'


def schedule_package_jobs(
    cursor,
    order_id: int,
    user_id: int,
    link: str | None,
    package_steps: list[dict],
    comments: str | None = None,
    base_time: datetime | None = None
) -> list[int]:
    """패키지 단계별 작업을 예약"""
    if not package_steps:
        return []

    total_steps = len(package_steps)
    base_time = base_time or datetime.utcnow()
    cumulative_delay = 0
    job_ids: list[int] = []

    for index, step in enumerate(package_steps):
        delay_minutes = int(step.get('delay', 0) or 0)
        scheduled_at = base_time + timedelta(minutes=cumulative_delay)
        payload = {
            'job_type': 'package_step',
            'order_id': order_id,
            'step_index': index,
            'total_steps': total_steps,
            'step': step,
            'service_id': step.get('service_id') or step.get('id'),
            'link': link,
            'comments': comments,
            'quantity': step.get('quantity')
        }
        job_id = enqueue_work_job(cursor, user_id, scheduled_at, payload)
        job_ids.append(job_id)
        cumulative_delay += max(delay_minutes, 0)

    return job_ids


def schedule_split_delivery_jobs(
    cursor,
    order_id: int,
    user_id: int,
    link: str | None,
    service_id: int | str | None,
    total_days: int,
    split_quantity: int,
    comments: str | None = None,
    base_time: datetime | None = None
) -> list[int]:
    """분할 배송 작업 예약"""
    if total_days <= 0 or split_quantity <= 0:
        return []

    base_time = base_time or datetime.utcnow()
    job_ids: list[int] = []

    for day in range(1, total_days + 1):
        scheduled_at = base_time + timedelta(days=day - 1)
        payload = {
            'job_type': 'split_delivery_step',
            'order_id': order_id,
            'day_number': day,
            'total_days': total_days,
            'service_id': service_id,
            'link': link,
            'split_quantity': split_quantity,
            'comments': comments
        }
        job_id = enqueue_work_job(cursor, user_id, scheduled_at, payload)
        job_ids.append(job_id)

    return job_ids


def execute_smm_order_job(cursor, job: dict, payload: dict) -> dict:
    """단일 주문 또는 예약 주문을 SMM 패널에 전달"""
    order_id = payload.get('order_id')
    if not order_id:
        return {'success': False, 'error': 'order_id가 누락되었습니다.'}

    order = load_order_for_update(cursor, order_id)
    if not order:
        return {'success': False, 'error': '주문을 찾을 수 없습니다.'}

    notes = order.get('notes') or {}
    items = load_order_items(cursor, order_id)
    order_item_id = payload.get('order_item_id') or job.get('order_item_id')

    target_item = None
    if order_item_id:
        target_item = next((item for item in items if item['order_item_id'] == order_item_id), None)
    if not target_item and items:
        target_item = items[0]

    service_id = payload.get('service_id') or notes.get('smm_service_id')
    if not service_id and target_item:
        cursor.execute(
            """
            SELECT meta_json
              FROM product_variants
             WHERE variant_id = %s
            """,
            (target_item['variant_id'],)
        )
        meta_row = cursor.fetchone()
        raw_meta = None
        if meta_row:
            raw_meta = meta_row.get('meta_json') if isinstance(meta_row, dict) else meta_row[0]
        if isinstance(raw_meta, str):
            try:
                raw_meta = json.loads(raw_meta)
            except json.JSONDecodeError:
                raw_meta = {}
        if isinstance(raw_meta, dict):
            service_id = raw_meta.get('smm_service_id') or raw_meta.get('service_id') or raw_meta.get('panel_service_id')

    if not service_id:
        return {'success': False, 'error': 'SMM 서비스 ID를 찾을 수 없습니다.'}

    raw_quantity = payload.get('quantity')
    if raw_quantity is None and target_item:
        raw_quantity = target_item.get('quantity')
    try:
        quantity = int(raw_quantity or 0)
    except (TypeError, ValueError):
        quantity = 0
    if quantity <= 0:
        quantity = 1

    link = payload.get('link') or (target_item.get('link') if target_item else None) or notes.get('link')
    if not link:
        return {'success': False, 'error': '링크 정보가 없습니다.'}

    comments = payload.get('comments') or notes.get('comments')
    response = call_smm_panel_api({
        'service': service_id,
        'link': link,
        'quantity': quantity,
        'comments': comments
    })

    if response.get('status') == 'success':
        smm_order_id = response.get('order')
        update_order_status(cursor, order_id, 'processing')
        update_order_items_status(cursor, order_id, 'in_progress')

        notes = order.get('notes') or {}
        smm_orders = notes.get('smm_orders') or []
        smm_orders.append({
            'job_id': job['job_id'],
            'order_item_id': order_item_id,
            'service_id': service_id,
            'quantity': quantity,
            'smm_panel_order_id': smm_order_id,
            'executed_at': datetime.utcnow().isoformat()
        })
        notes['smm_orders'] = smm_orders
        if smm_order_id:
            notes['smm_panel_order_id'] = smm_order_id

        cursor.execute(
            """
            UPDATE orders
               SET notes = %s::jsonb,
                   updated_at = NOW()
             WHERE order_id = %s
            """,
            (json.dumps(notes, ensure_ascii=False), order_id)
        )

        return {
            'success': True,
            'smm_panel_order_id': smm_order_id,
            'quantity': quantity,
            'service_id': service_id
        }

    return {
        'success': False,
        'error': response.get('message') or 'SMM Panel 오류',
        'raw_response': response
    }


def execute_package_step_job(cursor, job: dict, payload: dict) -> dict:
    """패키지 단계 작업 실행"""
    order_id = payload.get('order_id')
    if not order_id:
        return {'success': False, 'error': 'order_id가 누락되었습니다.'}

    order = load_order_for_update(cursor, order_id)
    if not order:
        return {'success': False, 'error': '주문을 찾을 수 없습니다.'}

    step = payload.get('step') or {}
    step_index = int(payload.get('step_index', 0))
    total_steps = int(payload.get('total_steps', 0) or 0)
    step_name = step.get('name') or f'단계 {step_index + 1}'
    service_id = step.get('service_id') or step.get('id') or payload.get('service_id')
    quantity = step.get('quantity') or payload.get('quantity') or 0

    try:
        quantity = int(quantity or 0)
    except (TypeError, ValueError):
        quantity = 0
    if quantity <= 0:
        return {'success': False, 'error': '패키지 단계 수량이 유효하지 않습니다.'}

    link = payload.get('link') or (order.get('notes') or {}).get('link')
    if not link:
        return {'success': False, 'error': '링크 정보가 없습니다.'}

    comments = payload.get('comments') or step.get('comments')
    response = call_smm_panel_api({
        'service': service_id,
        'link': link,
        'quantity': quantity,
        'comments': f"{step_name} ({step_index + 1}/{max(total_steps, step_index + 1)}) - {comments}" if comments else f"{step_name} ({step_index + 1}/{max(total_steps, step_index + 1)})"
    })

    notes = order.get('notes') or {}
    progress = notes.get('package_progress') or []
    executed_at = datetime.utcnow().isoformat()

    entry = {
        'job_id': job['job_id'],
        'step_index': step_index,
        'total_steps': total_steps,
        'step_name': step_name,
        'service_id': service_id,
        'quantity': quantity,
        'executed_at': executed_at
    }

    if response.get('status') == 'success':
        smm_order_id = response.get('order')
        entry['status'] = 'completed'
        entry['smm_panel_order_id'] = smm_order_id
        update_order_status(cursor, order_id, 'processing')
    else:
        entry['status'] = 'failed'
        entry['error'] = response.get('message') or 'SMM Panel 오류'

    progress.append(entry)
    notes['package_progress'] = progress
    if entry.get('status') == 'completed' and total_steps and step_index + 1 >= total_steps:
        notes['package_completed_at'] = executed_at

    cursor.execute(
        """
        UPDATE orders
           SET notes = %s::jsonb,
               updated_at = NOW()
         WHERE order_id = %s
        """,
        (json.dumps(notes, ensure_ascii=False), order_id)
    )

    return {
        'success': entry['status'] == 'completed',
        'step_index': step_index,
        'total_steps': total_steps,
        'response': response
    }


def execute_split_delivery_job(cursor, job: dict, payload: dict) -> dict:
    """분할 주문 작업 실행"""
    order_id = payload.get('order_id')
    if not order_id:
        return {'success': False, 'error': 'order_id가 누락되었습니다.'}

    order = load_order_for_update(cursor, order_id)
    if not order:
        return {'success': False, 'error': '주문을 찾을 수 없습니다.'}

    day_number = int(payload.get('day_number', 0) or 0)
    total_days = int(payload.get('total_days', 0) or 0)
    service_id = payload.get('service_id')
    split_quantity = payload.get('split_quantity')

    try:
        split_quantity = int(split_quantity or 0)
    except (TypeError, ValueError):
        split_quantity = 0

    if split_quantity <= 0:
        return {'success': False, 'error': '분할 발송 수량이 유효하지 않습니다.'}

    link = payload.get('link') or (order.get('notes') or {}).get('link')
    if not link:
        return {'success': False, 'error': '링크 정보가 없습니다.'}

    comments = payload.get('comments')
    response = call_smm_panel_api({
        'service': service_id,
        'link': link,
        'quantity': split_quantity,
        'comments': f"{comments or ''} (분할 {day_number}/{max(total_days, day_number)}일차)".strip()
    })

    notes = order.get('notes') or {}
    progress = notes.get('split_progress') or []
    executed_at = datetime.utcnow().isoformat()

    entry = {
        'job_id': job['job_id'],
        'day_number': day_number,
        'total_days': total_days,
        'service_id': service_id,
        'quantity': split_quantity,
        'executed_at': executed_at
    }

    if response.get('status') == 'success':
        entry['status'] = 'completed'
        entry['smm_panel_order_id'] = response.get('order')
        update_order_status(cursor, order_id, 'processing')
    else:
        entry['status'] = 'failed'
        entry['error'] = response.get('message') or 'SMM Panel 오류'

    progress.append(entry)
    notes['split_progress'] = progress

    cursor.execute(
        """
        UPDATE orders
           SET notes = %s::jsonb,
               updated_at = NOW()
         WHERE order_id = %s
        """,
        (json.dumps(notes, ensure_ascii=False), order_id)
    )

    return {
        'success': entry['status'] == 'completed',
        'day_number': day_number,
        'total_days': total_days,
        'response': response
    }


def execute_order_status_job(cursor, job: dict, payload: dict) -> dict:
    """주문 상태 업데이트 작업 실행"""
    order_id = payload.get('order_id')
    new_status = payload.get('new_status')
    if not order_id or not new_status:
        return {'success': False, 'error': 'order_id 또는 new_status가 누락되었습니다.'}

    order = load_order_for_update(cursor, order_id)
    if not order:
        return {'success': False, 'error': '주문을 찾을 수 없습니다.'}

    current_status = order.get('status')
    notes = order.get('notes') or {}
    executed_at = datetime.utcnow().isoformat()
    transitioned = False

    if new_status == 'processing':
        if current_status not in ('completed', 'canceled', 'refunded'):
            if current_status != 'processing':
                update_order_status(cursor, order_id, 'processing')
                update_order_items_status(cursor, order_id, 'in_progress')
                transitioned = True
    elif new_status == 'completed':
        if current_status not in ('completed', 'canceled', 'refunded'):
            update_order_status(cursor, order_id, 'completed')
            update_order_items_status(cursor, order_id, 'done')
            notes['completed_at'] = executed_at
            transitioned = True
    else:
        if current_status != new_status:
            update_order_status(cursor, order_id, new_status)
            transitioned = True

    history = notes.get('status_history') or []
    history.append({
        'job_id': job['job_id'],
        'status': new_status,
        'executed_at': executed_at
    })
    notes['status_history'] = history

    cursor.execute(
        """
        UPDATE orders
           SET notes = %s::jsonb,
               updated_at = NOW()
         WHERE order_id = %s
        """,
        (json.dumps(notes, ensure_ascii=False), order_id)
    )

    return {
        'success': True,
        'new_status': new_status,
        'transitioned': transitioned
    }


def execute_job_payload(cursor, job: dict, payload: dict) -> dict:
    """작업 페이로드 타입에 따라 실행"""
    job_type = payload.get('job_type')
    if job_type in ('smm_order', 'scheduled_order'):
        return execute_smm_order_job(cursor, job, payload)
    if job_type == 'package_step':
        return execute_package_step_job(cursor, job, payload)
    if job_type == 'split_delivery_step':
        return execute_split_delivery_job(cursor, job, payload)
    if job_type == 'order_status_update':
        return execute_order_status_job(cursor, job, payload)
    return {'success': False, 'error': f'알 수 없는 작업 유형: {job_type}'}


def run_single_work_job(job_id: int) -> dict:
    """단일 작업 실행"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(
            """
            SELECT job_id,
                   user_id,
                   order_item_id,
                   package_item_id,
                   schedule_at,
                   status,
                   attempts,
                   payload_json
              FROM work_jobs
             WHERE job_id = %s
             FOR UPDATE
            """,
            (job_id,)
        )
        job = cursor.fetchone()
        if not job:
            conn.rollback()
            return {'job_id': job_id, 'success': False, 'error': '작업을 찾을 수 없습니다.'}

        if job['status'] not in ('pending', 'processing'):
            conn.rollback()
            return {'job_id': job_id, 'success': False, 'error': f"작업 상태가 실행 가능하지 않습니다: {job['status']}"}

        if job['attempts'] >= MAX_JOB_ATTEMPTS:
            cursor.execute(
                """
                UPDATE work_jobs
                   SET status = 'failed',
                       payload_json = COALESCE(payload_json, '{}'::jsonb) || %s::jsonb,
                       updated_at = NOW()
                 WHERE job_id = %s
                """,
                (
                    json.dumps({'last_error': 'max_attempts_exceeded'}, ensure_ascii=False),
                    job_id
                )
            )
            conn.commit()
            return {'job_id': job_id, 'success': False, 'status': 'failed', 'error': 'max_attempts_exceeded'}

        cursor.execute(
            """
            UPDATE work_jobs
               SET status = 'processing',
                   attempts = attempts + 1,
                   last_run_at = NOW(),
                   updated_at = NOW(),
                   schedule_at = NOW()
             WHERE job_id = %s
            """,
            (job_id,)
        )

        payload = job.get('payload_json') or {}
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                payload = {}
        result = execute_job_payload(cursor, job, payload)
        status = 'completed' if result.get('success') else 'failed'

        cursor.execute(
            """
            UPDATE work_jobs
               SET status = %s,
                   payload_json = COALESCE(payload_json, '{}'::jsonb) || %s::jsonb,
                   updated_at = NOW()
             WHERE job_id = %s
            """,
            (
                status,
                json.dumps({'last_result': result}, ensure_ascii=False),
                job_id
            )
        )

        conn.commit()
        result.update({'job_id': job_id, 'status': status})
        return result
    except Exception as exc:
        conn.rollback()
        cursor.execute(
            """
            UPDATE work_jobs
               SET status = 'failed',
                   payload_json = COALESCE(payload_json, '{}'::jsonb) || %s::jsonb,
                   updated_at = NOW()
             WHERE job_id = %s
            """,
            (
                json.dumps({'last_error': str(exc)}, ensure_ascii=False),
                job_id
            )
        )
        conn.commit()
        return {'job_id': job_id, 'success': False, 'status': 'failed', 'error': str(exc)}
    finally:
        cursor.close()
        conn.close()


def fetch_due_job_ids(limit: int) -> list[int]:
    """실행 가능한 작업 ID 조회"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT job_id
          FROM work_jobs
         WHERE status IN ('pending','processing')
           AND attempts < %s
           AND (schedule_at IS NULL OR schedule_at <= NOW())
         ORDER BY COALESCE(schedule_at, NOW()), job_id
         LIMIT %s
        """,
        (MAX_JOB_ATTEMPTS, limit)
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    job_ids: list[int] = []
    for row in rows:
        if isinstance(row, dict):
            job_ids.append(row['job_id'])
        else:
            job_ids.append(row[0])
    return job_ids


def fetch_user_record(cursor, identifier: dict, email: str | None = None):
    """식별자나 이메일로 사용자 레코드 조회"""
    if identifier.get('user_id') is not None:
        cursor.execute(
            f"SELECT {USER_SELECT_COLUMNS} FROM users WHERE user_id = %s",
            (identifier['user_id'],)
        )
        row = cursor.fetchone()
        if row:
            return row

    external_uid = identifier.get('external_uid')
    if external_uid:
        cursor.execute(
            f"SELECT {USER_SELECT_COLUMNS} FROM users WHERE external_uid = %s",
            (external_uid,)
        )
        row = cursor.fetchone()
        if row:
            return row

    if email:
        cursor.execute(
            f"SELECT {USER_SELECT_COLUMNS} FROM users WHERE email = %s",
            (email,)
        )
        row = cursor.fetchone()
        if row:
            return row

    return None


def ensure_user_record(cursor, identifier: dict, email: str | None = None, username: str | None = None):
    """사용자 레코드를 보장 (없으면 생성)"""
    user = fetch_user_record(cursor, identifier, email=email)
    if user:
        # referral_code가 없다면 새로 발급
        referral_code = user.get('referral_code') if isinstance(user, dict) else None
        if not referral_code:
            new_code = generate_unique_referral_code(cursor)
            cursor.execute(
                f"""
                UPDATE users
                   SET referral_code = %s,
                       referral_status = COALESCE(referral_status, 'approved'),
                       updated_at = NOW()
                 WHERE user_id = %s
                RETURNING {USER_SELECT_COLUMNS}
                """,
                (new_code, user['user_id'] if isinstance(user, dict) else user[0])
            )
            user = cursor.fetchone()
        return user

    external_uid = identifier.get('external_uid')
    if not external_uid and not email:
        raise ValueError("사용자 식별자 정보가 부족합니다.")

    attempt = 0
    candidate_email = email or generate_placeholder_email(external_uid, attempt)

    while True:
        cursor.execute("SELECT 1 FROM users WHERE email = %s", (candidate_email,))
        if cursor.fetchone():
            attempt += 1
            candidate_email = generate_placeholder_email(external_uid, attempt)
            continue

        referral_code = generate_unique_referral_code(cursor)
        cursor.execute(
            f"""
            INSERT INTO users (external_uid, email, username, referral_code, referral_status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING {USER_SELECT_COLUMNS}
            """,
            (
                external_uid,
                candidate_email,
                username or (external_uid[:50] if external_uid else 'User'),
                referral_code,
                'approved'
            )
        )
        user = cursor.fetchone()
        return user


def ensure_wallet_record(cursor, user_id: int):
    """지갑 레코드를 보장 (없으면 생성)"""
    cursor.execute(
        """
        INSERT INTO wallets (user_id, balance, created_at, updated_at)
        VALUES (%s, 0, NOW(), NOW())
        ON CONFLICT (user_id) DO NOTHING
        """,
        (user_id,)
    )

    cursor.execute(
        """
        SELECT wallet_id, user_id, balance, created_at, updated_at
        FROM wallets
        WHERE user_id = %s
        """,
        (user_id,)
    )
    return cursor.fetchone()


def to_decimal(amount) -> Decimal:
    """숫자 값을 Decimal(소수점 둘째 자리)로 변환"""
    decimal_value = Decimal(str(amount))
    return decimal_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def decimal_to_float(value) -> float:
    """Decimal 값을 float로 변환"""
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def to_isoformat_or_none(value):
    """datetime 값을 ISO 포맷 문자열로 변환"""
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)

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
        data = request.get_json() or {}
        print("=== 예약 발송 주문 생성 요청 ===")
        print(f"요청 데이터: {data}")

        raw_user_id = data.get('user_id')
        service_id = data.get('service_id')
        link = data.get('link')
        quantity = data.get('quantity')
        price = data.get('price') or data.get('total_price')
        scheduled_datetime = data.get('scheduled_datetime') or data.get('scheduled_at')
        package_steps = data.get('package_steps') or []
        runs = int(data.get('runs', 1) or 1)
        interval = int(data.get('interval', 0) or 0)
        comments = data.get('comments')

        missing_fields = []
        if raw_user_id is None:
            missing_fields.append('user_id')
        if not service_id:
            missing_fields.append('service_id')
        if not link:
            missing_fields.append('link')
        if quantity is None:
            missing_fields.append('quantity')
        if price is None:
            missing_fields.append('price')
        if not scheduled_datetime:
            missing_fields.append('scheduled_datetime')

        if missing_fields:
            return jsonify({'error': f"필수 필드가 누락되었습니다: {', '.join(missing_fields)}"}), 400

        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return jsonify({'error': 'quantity는 1 이상의 정수여야 합니다.'}), 400

        def parse_datetime(value: str) -> datetime:
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                return datetime.strptime(value, '%Y-%m-%d %H:%M')

        try:
            scheduled_dt = parse_datetime(str(scheduled_datetime))
        except ValueError:
            return jsonify({'error': 'scheduled_datetime 형식이 올바르지 않습니다.'}), 400

        now = datetime.now(tz=scheduled_dt.tzinfo) if scheduled_dt.tzinfo else datetime.now()
        time_diff_minutes = (scheduled_dt - now).total_seconds() / 60
        if time_diff_minutes < 5 or time_diff_minutes > 10080:
            return jsonify({'error': '예약 시간은 현재 시간으로부터 5분 이상 7일 이내여야 합니다.'}), 400

        identifier = parse_user_identifier(raw_user_id)

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        user = ensure_user_record(cursor, identifier)
        ensure_wallet_record(cursor, user['user_id'])

        total_amount = to_decimal(price)
        referral_info = get_active_referral(cursor, user['user_id'])

        notes = {
            'order_type': 'scheduled',
            'service_id': service_id,
            'link': link,
            'quantity': quantity,
            'scheduled_datetime': scheduled_dt.isoformat(),
            'package_steps': package_steps,
            'runs': runs,
            'interval': interval,
            'comments': comments,
            'raw_payload': data
        }

        cursor.execute(
            """
            INSERT INTO orders (
                user_id,
                referrer_user_id,
                total_amount,
                discount_amount,
                final_amount,
                status,
                notes,
                created_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, 'scheduled', %s, NOW(), NOW())
            RETURNING order_id
            """,
            (
                user['user_id'],
                referral_info['referrer_user_id'] if referral_info else None,
                total_amount,
                Decimal('0'),
                total_amount,
                json.dumps(notes, ensure_ascii=False)
            )
        )
        order_id = cursor.fetchone()['order_id']

        job_ids = []
        if package_steps:
            cumulative_delay = 0
            for index, step in enumerate(package_steps):
                step_delay = int(step.get('delay', 0) or 0)
                scheduled_at = scheduled_dt + timedelta(minutes=cumulative_delay)
                payload = {
                    'job_type': 'package_step',
                    'order_id': order_id,
                    'step_index': index,
                    'step': step,
                    'service_id': service_id,
                    'link': link,
                    'quantity': step.get('quantity', quantity),
                    'runs': runs,
                    'interval': interval,
                    'comments': comments
                }
                job_id = enqueue_work_job(cursor, user['user_id'], scheduled_at, payload)
                job_ids.append(job_id)
                cumulative_delay += step_delay if step_delay > 0 else 0
        else:
            payload = {
                'job_type': 'scheduled_order',
                'order_id': order_id,
                'service_id': service_id,
                'link': link,
                'quantity': quantity,
                'runs': runs,
                'interval': interval,
                'comments': comments
            }
            job_id = enqueue_work_job(cursor, user['user_id'], scheduled_dt, payload)
            job_ids.append(job_id)

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'예약 발송이 설정되었습니다. ({scheduled_dt.isoformat()} 실행 예정)',
            'order_id': order_id,
            'scheduled_datetime': scheduled_dt.isoformat(),
            'job_ids': job_ids
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

def sync_smm_panel_orders(limit: int = 50) -> list[dict]:
    """SMM Panel 상태와 주문 상태를 동기화"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    results: list[dict] = []

    try:
        cursor.execute(
            """
            SELECT order_id
              FROM orders
             WHERE status IN ('processing','paid')
               AND notes IS NOT NULL
             ORDER BY updated_at DESC
             LIMIT %s
            """,
            (limit,)
        )
        rows = cursor.fetchall()

        for row in rows:
            order_id = row['order_id'] if isinstance(row, dict) else row[0]
            order = load_order_for_update(cursor, order_id)
            if not order:
                continue

            notes = order.get('notes') or {}
            if isinstance(notes, str):
                try:
                    notes = json.loads(notes)
                except json.JSONDecodeError:
                    notes = {}

            smm_orders = notes.get('smm_orders')
            if not isinstance(smm_orders, list) or not smm_orders:
                continue

            entries_result = []

            for entry in smm_orders:
                smm_order_id = entry.get('smm_panel_order_id')
                if not smm_order_id:
                    continue

                status_response = call_smm_panel_api({'action': 'status', 'order': smm_order_id})
                entry_result = {'smm_panel_order_id': smm_order_id}

                if status_response.get('status') != 'success':
                    entry_result['status'] = 'error'
                    entry_result['error'] = status_response.get('message')
                    entry['status'] = 'error'
                    entry['last_sync_at'] = datetime.utcnow().isoformat()
                else:
                    panel_status = status_response.get('status_text')
                    normalized = normalize_panel_status(panel_status)
                    entry_result.update({
                        'status': normalized,
                        'status_text': panel_status,
                        'charge': status_response.get('charge'),
                        'start_count': status_response.get('start_count'),
                        'remains': status_response.get('remains')
                    })
                    entry.update({
                        'status': normalized,
                        'status_text': panel_status,
                        'charge': status_response.get('charge'),
                        'start_count': status_response.get('start_count'),
                        'remains': status_response.get('remains'),
                        'last_sync_at': datetime.utcnow().isoformat()
                    })

                entries_result.append(entry_result)

            notes['smm_orders'] = smm_orders
            notes['smm_sync_at'] = datetime.utcnow().isoformat()

            normalized_statuses = [entry.get('status') for entry in smm_orders if entry.get('status')]
            target_status = order.get('status')

            if normalized_statuses:
                if all(status == 'completed' for status in normalized_statuses):
                    target_status = 'completed'
                elif any(status in ('failed', 'unknown') for status in normalized_statuses):
                    target_status = 'canceled'
                elif target_status not in ('completed', 'canceled', 'refunded'):
                    target_status = 'processing'

            if target_status != order.get('status'):
                if target_status == 'completed':
                    update_order_status(cursor, order_id, 'completed')
                    update_order_items_status(cursor, order_id, 'done')
                    notes['completed_at'] = datetime.utcnow().isoformat()
                elif target_status == 'canceled':
                    update_order_status(cursor, order_id, 'canceled')
                    update_order_items_status(cursor, order_id, 'canceled')
                else:
                    update_order_status(cursor, order_id, target_status)

            history = notes.get('status_history') or []
            if not history or history[-1].get('status') != target_status:
                history.append({
                    'source': 'smm_sync',
                    'status': target_status,
                    'synced_at': notes['smm_sync_at']
                })
            notes['status_history'] = history

            cursor.execute(
                """
                UPDATE orders
                   SET notes = %s::jsonb,
                       updated_at = NOW()
                 WHERE order_id = %s
                """,
                (json.dumps(notes, ensure_ascii=False), order_id)
            )

            results.append({
                'order_id': order_id,
                'new_status': target_status,
                'entries': entries_result
            })

        conn.commit()
        return results
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def check_and_update_order_status():
    """SMM 상태 동기화 (호환성 래퍼)"""
    try:
        return sync_smm_panel_orders()
    except Exception as exc:
        print(f"❌ SMM 주문 동기화 실패: {exc}")
        return []


# 프로덕션 환경에서는 로그 최소화
if os.environ.get('FLASK_ENV') != 'production':
    pass

def get_db_connection():
    """PostgreSQL 연결을 반환합니다."""
    try:
        conn = psycopg2.connect(
            DATABASE_URL,
            connect_timeout=30,
            keepalives_idle=600,
            keepalives_interval=30,
            keepalives_count=3,
        )
        conn.autocommit = False
        return conn
    except psycopg2.Error as exc:
        print(f"❌ PostgreSQL 연결 실패: {exc}")
        raise


def init_database():
    """애플리케이션 시작 시 필수 테이블 존재 여부를 확인합니다."""
    conn = None
    cursor = None
    required_tables = {
        "merchants",
        "users",
        "categories",
        "products",
        "product_variants",
        "packages",
        "package_items",
        "coupons",
        "user_coupons",
        "orders",
        "order_items",
        "referrals",
        "commissions",
        "wallets",
        "wallet_transactions",
        "payout_requests",
        "payouts",
        "payout_commissions",
        "work_jobs",
        "user_sessions",
    }

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            """
        )
        existing_tables = {row[0] for row in cursor.fetchall()}

        missing_tables = sorted(required_tables - existing_tables)
        if missing_tables:
            message = f"필수 테이블이 누락되었습니다: {', '.join(missing_tables)}"
            print(f"❌ {message}")
            raise RuntimeError(message)

        print("✅ 데이터베이스 필수 테이블 확인 완료")

        cursor.execute(
            """
            SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1
            """
        )
        latest_migration = cursor.fetchone()
        if latest_migration:
            print(f"📦 최신 마이그레이션 버전: {latest_migration[0]}")
        else:
            print("⚠️ schema_migrations 테이블이 비어 있습니다. migrate_database.py 실행 여부를 확인하세요.")

        conn.commit()
    except Exception as exc:
        if conn:
            conn.rollback()
        print(f"❌ 데이터베이스 초기화 상태 확인 실패: {exc}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
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
        
        tables_to_check = ['users', 'orders', 'wallets', 'wallet_transactions']
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
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        identifier = parse_user_identifier(user_id)
        user = ensure_user_record(cursor, identifier)
        if not user:
            cursor.close()
            conn.close()
            return jsonify({'connected': False, 'message': '사용자를 찾을 수 없습니다.'}), 404

        cursor.execute(
            """
            SELECT referral_id, referrer_user_id, created_at, status
              FROM referrals
             WHERE referred_user_id = %s
             ORDER BY referral_id DESC
             LIMIT 1
            """,
            (user['user_id'],)
        )
        connection = cursor.fetchone()

        if not connection:
            cursor.close()
            conn.close()
            return jsonify({
                'connected': False,
                'message': '추천인 연결 정보가 없습니다.'
            }), 200

        referrer = None
        if connection.get('referrer_user_id'):
            referrer = get_user_by_id(cursor, connection['referrer_user_id'])

        response = {
            'connected': True,
            'referral_id': connection['referral_id'],
            'referrer_user_id': connection['referrer_user_id'],
            'referrer_email': referrer['email'] if referrer and referrer.get('email') else None,
            'referrer_code': referrer['referral_code'] if referrer and referrer.get('referral_code') else None,
            'status': connection['status'],
            'created_at': connection['created_at'].isoformat() if connection['created_at'] else None
        }

        cursor.close()
        conn.close()

        return jsonify(response), 200

    except Exception as e:
        print(f"❌ 추천인 연결 확인 오류: {e}")
        return jsonify({'error': str(e)}), 500

# 사용자 등록
@app.route('/api/register', methods=['POST'])
def register():
    """사용자 등록"""
    conn = None
    cursor = None

    try:
        data = request.get_json()
        print(f"🔍 등록 요청 데이터: {data}")

        raw_user_id = data.get('user_id')
        email = (data.get('email') or '').strip()
        name = (data.get('name') or '').strip()

        print(f"🔍 파싱된 데이터 - user_id: {raw_user_id}, email: {email}, name: {name}")
        print(f"🔍 데이터 타입 - user_id: {type(raw_user_id)}, email: {type(email)}, name: {type(name)}")

        if raw_user_id is None or (isinstance(raw_user_id, str) and not raw_user_id.strip()):
            print(f"❌ user_id 누락 또는 빈 값: {raw_user_id}")
            return jsonify({'error': '사용자 ID가 필요합니다.'}), 400

        if not email:
            print(f"❌ email 누락 또는 빈 값: {email}")
            return jsonify({'error': '이메일이 필요합니다.'}), 400

        if not name:
            print(f"❌ name 누락 또는 빈 값: {name}")
            return jsonify({'error': '이름을 입력해주세요.'}), 400

        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            print(f"❌ 유효하지 않은 이메일 형식: {email}")
            return jsonify({'error': '유효하지 않은 이메일 형식입니다.'}), 400

        identifier = parse_user_identifier(raw_user_id)

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
        existing_email_row = cursor.fetchone()
        if existing_email_row and existing_email_row['user_id'] != identifier.get('user_id'):
            print(f"❌ 이메일 중복: {email} (기존 user_id: {existing_email_row['user_id']}, 요청 user_id: {identifier.get('user_id')})")
            return jsonify({'error': '이미 사용 중인 이메일입니다.'}), 400

        existing_user = fetch_user_record(cursor, identifier, email=email)
        if existing_user:
            existing_user_id = existing_user['user_id'] if isinstance(existing_user, dict) else existing_user[0]
            cursor.execute(
                """
                UPDATE users
                   SET email = %s,
                       username = %s,
                       updated_at = NOW()
                 WHERE user_id = %s
                RETURNING user_id, external_uid, email, username, referral_code, referral_status, is_admin, created_at, updated_at
                """,
                (email, name, existing_user_id)
            )
            user_row = cursor.fetchone()
        else:
            user_row = ensure_user_record(cursor, identifier, email=email, username=name)

        wallet = ensure_wallet_record(cursor, user_row['user_id'])

        conn.commit()
        print(f"✅ 사용자 등록 완료 - user_id: {user_row['user_id']}, email: {email}, name: {name}")

        return jsonify({
            'success': True,
            'message': '사용자 등록이 완료되었습니다.',
            'user_id': user_row['user_id'],
            'external_uid': user_row['external_uid'],
            'wallet_balance': decimal_to_float(wallet['balance']) if wallet else 0.0
        }), 200

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ 사용자 등록 오류: {e}")
        print(f"❌ 오류 타입: {type(e)}")
        print(f"❌ 오류 상세: {str(e)}")
        return jsonify({'error': f'사용자 등록 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 사용자 포인트 조회
@app.route('/api/points', methods=['GET'])
def get_user_points():
    """사용자 지갑(포인트) 잔액 조회"""
    conn = None
    cursor = None

    try:
        raw_user_id = request.args.get('user_id')
        if not raw_user_id:
            return jsonify({'error': 'user_id가 필요합니다.'}), 400

        identifier = parse_user_identifier(raw_user_id)

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        user = ensure_user_record(cursor, identifier)
        wallet = ensure_wallet_record(cursor, user['user_id'])

        cursor.execute(
            """
            SELECT transaction_id,
                   amount,
                   status,
                   created_at,
                   meta_json
              FROM wallet_transactions
             WHERE wallet_id = %s
               AND type = 'topup'
             ORDER BY created_at DESC
            """,
            (wallet['wallet_id'],)
        )
        rows = cursor.fetchall()

        conn.commit()
        conn.close()

        balance = decimal_to_float(wallet['balance']) if wallet else 0.0

        return jsonify({
            'user_id': user['user_id'],
            'external_uid': user['external_uid'],
            'points': balance,
            'wallet_balance': balance,
        }), 200

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ 지갑 잔액 조회 오류: {e}")
        return jsonify({'error': f'지갑 잔액 조회 실패: {str(e)}'}), 500
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
        data = request.get_json() or {}
        print("=== 주문 생성 요청 ===")
        print(f"요청 데이터: {data}")

        raw_user_id = data.get('user_id')
        variant_id = data.get('variant_id') or data.get('service_id')
        link = data.get('link')
        quantity = data.get('quantity')
        unit_price = data.get('unit_price')
        total_price = data.get('price') or data.get('total_price')
        user_coupon_id = data.get('user_coupon_id') or data.get('coupon_id')
        use_wallet = data.get('use_wallet', True)
        package_steps = data.get('package_steps') or []
        split_days = data.get('split_days') or 0
        split_quantity = data.get('split_quantity')
        split_service_id = data.get('split_service_id')
        order_type = data.get('order_type')

        missing_fields = []
        if raw_user_id is None:
            missing_fields.append('user_id')
        if not variant_id:
            missing_fields.append('variant_id')
        if quantity in (None, ''):
            missing_fields.append('quantity')
        if unit_price is None and total_price is None:
            missing_fields.append('unit_price or total_price')

        if missing_fields:
            error_msg = f"필수 필드가 누락되었습니다: {', '.join(missing_fields)}"
            print(f"❌ {error_msg}")
            return jsonify({'error': error_msg}), 400

        quantity = int(quantity)
        if quantity <= 0:
            return jsonify({'error': 'quantity는 1 이상이어야 합니다.'}), 400

        if isinstance(package_steps, dict) and 'steps' in package_steps:
            package_steps = package_steps.get('steps') or []
        if package_steps and not isinstance(package_steps, list):
            return jsonify({'error': 'package_steps는 배열이어야 합니다.'}), 400

        try:
            split_days = int(split_days or 0)
        except (TypeError, ValueError):
            split_days = 0

        try:
            split_quantity = int(split_quantity or 0)
        except (TypeError, ValueError):
            split_quantity = 0

        if not order_type:
            if package_steps:
                order_type = 'package'
            elif split_days > 0 and split_quantity > 0:
                order_type = 'split'
            else:
                order_type = 'single'

        if unit_price is not None:
            unit_price_decimal = to_decimal(unit_price)
            total_amount = (unit_price_decimal * quantity).quantize(Decimal('0.01'))
        else:
            total_amount = to_decimal(total_price)
            unit_price_decimal = (total_amount / quantity).quantize(Decimal('0.01'))

        identifier = parse_user_identifier(raw_user_id)

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        user = ensure_user_record(cursor, identifier)
        wallet = ensure_wallet_record(cursor, user['user_id'])

        cursor.execute(
            """
            SELECT meta_json
              FROM product_variants
             WHERE variant_id = %s
            """,
            (int(variant_id),)
        )
        variant_row = cursor.fetchone()
        raw_variant_meta = None
        if variant_row:
            raw_variant_meta = variant_row.get('meta_json') if isinstance(variant_row, dict) else variant_row[0]

        if isinstance(raw_variant_meta, str):
            try:
                variant_meta = json.loads(raw_variant_meta)
            except json.JSONDecodeError:
                variant_meta = {}
        elif isinstance(raw_variant_meta, dict):
            variant_meta = raw_variant_meta
        else:
            variant_meta = {}

        variant_service_candidates = []
        if isinstance(variant_meta, dict):
            variant_service_candidates.extend([
                variant_meta.get('smm_service_id'),
                variant_meta.get('service_id'),
                variant_meta.get('panel_service_id')
            ])

        smm_service_id = (
            data.get('smm_service_id')
            or next((c for c in variant_service_candidates if c), None)
            or data.get('service_id')
            or data.get('variant_id')
        )

        discount_amount = Decimal('0')
        coupon_id = None
        if user_coupon_id:
            try:
                discount_amount, coupon_id = redeem_user_coupon(cursor, user['user_id'], int(user_coupon_id), total_amount)
            except ValueError as coupon_error:
                conn.rollback()
                return jsonify({'error': str(coupon_error)}), 400

        final_amount = (total_amount - discount_amount).quantize(Decimal('0.01'))
        if final_amount < 0:
            final_amount = Decimal('0')

        referral_info = get_active_referral(cursor, user['user_id'])

        if use_wallet and final_amount > 0:
            ensure_wallet_balance(cursor, wallet, final_amount)
            cursor.execute(
                """
                UPDATE wallets
                   SET balance = balance - %s,
                       updated_at = NOW()
                 WHERE wallet_id = %s
                RETURNING balance
                """,
                (final_amount, wallet['wallet_id'])
            )
            updated_wallet = cursor.fetchone()
            wallet['balance'] = updated_wallet['balance'] if updated_wallet else wallet['balance']

        notes = {
            'link': link,
            'comments': data.get('comments'),
            'metadata': data.get('metadata'),
            'raw_payload': data,
            'order_type': order_type,
            'smm_service_id': smm_service_id,
            'package_steps': package_steps if package_steps else None,
            'split_delivery': {
                'days': split_days,
                'quantity': split_quantity,
                'service_id': split_service_id or smm_service_id
            } if split_days > 0 and split_quantity > 0 else None
        }

        cursor.execute(
            """
            INSERT INTO orders (
                user_id,
                referrer_user_id,
                coupon_id,
                total_amount,
                discount_amount,
                final_amount,
                status,
                notes,
                created_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, NOW(), NOW())
            RETURNING order_id
            """,
            (
                user['user_id'],
                referral_info['referrer_user_id'] if referral_info else None,
                int(user_coupon_id) if coupon_id else None,
                total_amount,
                discount_amount,
                final_amount,
                'processing',
                json.dumps(notes, ensure_ascii=False)
            )
        )
        order_id = cursor.fetchone()['order_id']

        cursor.execute(
            """
            INSERT INTO order_items (
                order_id,
                variant_id,
                quantity,
                unit_price,
                line_amount,
                link,
                status,
                created_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING order_item_id
            """,
            (
                order_id,
                int(variant_id),
                quantity,
                unit_price_decimal,
                final_amount,
                link,
                'pending'
            )
        )
        order_item_id = cursor.fetchone()['order_item_id']

        scheduled_job_ids: list[int] = []
        now_utc = datetime.utcnow()

        is_split_order = split_days > 0 and split_quantity > 0

        if not package_steps and not is_split_order:
            smm_payload = {
                'job_type': 'smm_order',
                'order_id': order_id,
                'order_item_id': order_item_id,
                'variant_id': int(variant_id),
                'service_id': smm_service_id,
                'link': link,
                'quantity': quantity,
                'comments': data.get('comments'),
                'order_type': order_type
            }
            smm_job_id = enqueue_work_job(cursor, user['user_id'], now_utc, smm_payload, order_item_id=order_item_id)
            scheduled_job_ids.append(smm_job_id)

        if package_steps:
            scheduled_job_ids.extend(
                schedule_package_jobs(
                    cursor,
                    order_id,
                    user['user_id'],
                    link,
                    package_steps,
                    comments=data.get('comments'),
                    base_time=now_utc
                )
            )

        if is_split_order:
            scheduled_job_ids.extend(
                schedule_split_delivery_jobs(
                    cursor,
                    order_id,
                    user['user_id'],
                    link,
                    split_service_id or smm_service_id,
                    split_days,
                    split_quantity,
                    comments=data.get('comments'),
                    base_time=now_utc
                )
            )

        status_job_ids = schedule_order_status_transitions(cursor, order_id, user['user_id'])
        if status_job_ids:
            scheduled_job_ids.extend(status_job_ids)

        wallet_tx_id = None
        if use_wallet and final_amount > 0:
            wallet_tx_id = create_wallet_transaction(
                cursor,
                wallet['wallet_id'],
                'order_debit',
                final_amount,
                'approved',
                {
                    'order_id': order_id,
                    'order_item_id': order_item_id,
                    'variant_id': variant_id,
                    'quantity': quantity
                }
            )

        commission_amount = Decimal('0')
        commission_id = None
        if referral_info and final_amount > 0:
            commission_amount = (final_amount * DEFAULT_COMMISSION_RATE).quantize(Decimal('0.01'))
            if commission_amount > 0:
                commission_id = record_commission(cursor, referral_info['referral_id'], order_id, commission_amount)

        cursor.execute(
            """
            UPDATE orders
               SET status = 'processing',
                   updated_at = NOW()
             WHERE order_id = %s
            """,
            (order_id,)
        )

        if scheduled_job_ids:
            merge_order_notes(cursor, order_id, {'scheduled_job_ids': scheduled_job_ids})

        conn.commit()

        return jsonify({
            'success': True,
            'order_id': order_id,
            'order_item_id': order_item_id,
            'wallet_transaction_id': wallet_tx_id,
            'commission_id': commission_id,
            'total_amount': float(total_amount),
            'discount_amount': float(discount_amount),
            'final_amount': float(final_amount),
            'coupon_id': coupon_id,
            'use_wallet': use_wallet,
            'wallet_balance': decimal_to_float(wallet['balance']),
            'scheduled_job_ids': scheduled_job_ids
        }), 200

    except ValueError as ve:
        if conn:
            conn.rollback()
        print(f"❌ 주문 생성 실패 (검증 오류): {ve}")
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ 주문 생성 실패: {e}")
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
    """패키지 주문 처리 작업을 예약 또는 재예약"""
    conn = None
    cursor = None

    try:
        data = request.get_json() or {}
        raw_order_id = data.get('order_id')
        if raw_order_id is None:
            return jsonify({'error': 'order_id가 필요합니다.'}), 400

        try:
            order_id = int(raw_order_id)
        except (TypeError, ValueError):
            return jsonify({'error': 'order_id는 정수여야 합니다.'}), 400

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        order = load_order_for_update(cursor, order_id)
        if not order:
            conn.rollback()
            return jsonify({'error': '주문을 찾을 수 없습니다.'}), 404

        notes = order.get('notes') or {}
        package_steps = data.get('package_steps') or notes.get('package_steps')
        if not package_steps:
            raw_payload = notes.get('raw_payload')
            if isinstance(raw_payload, dict):
                package_steps = raw_payload.get('package_steps')

        if isinstance(package_steps, dict) and 'steps' in package_steps:
            package_steps = package_steps.get('steps')

        if not package_steps or not isinstance(package_steps, list):
            conn.rollback()
            return jsonify({'error': '패키지 단계 정보를 찾을 수 없습니다.'}), 400

        link = data.get('link') or notes.get('link')
        comments = data.get('comments') or notes.get('comments')

        job_ids = schedule_package_jobs(
            cursor,
            order_id,
            order['user_id'],
            link,
            package_steps,
            comments=comments
        )
        status_job_ids = schedule_order_status_transitions(cursor, order_id, order['user_id'])

        all_job_ids = job_ids + (status_job_ids or [])
        if all_job_ids:
            existing_jobs = notes.get('scheduled_job_ids') or []
            merge_order_notes(cursor, order_id, {
                'package_steps': package_steps,
                'scheduled_job_ids': existing_jobs + all_job_ids
            })

        update_order_status(cursor, order_id, 'processing')
        conn.commit()

        return jsonify({
            'success': True,
            'message': f'패키지 주문 처리가 {len(package_steps)} 단계로 예약되었습니다.',
            'job_ids': all_job_ids
        }), 200

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ 패키지 주문 처리 예약 실패: {e}")
        return jsonify({'error': f'패키지 주문 처리 예약 실패: {str(e)}'}), 500
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
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT status, notes
              FROM orders
             WHERE order_id = %s
            """,
            (order_id,)
        )
        order_row = cursor.fetchone()
        if not order_row:
            return jsonify({'error': '주문을 찾을 수 없습니다.'}), 404

        notes = order_row.get('notes')
        if isinstance(notes, str):
            try:
                notes = json.loads(notes)
            except json.JSONDecodeError:
                notes = {}
        elif notes is None:
            notes = {}

        package_steps = notes.get('package_steps')
        if isinstance(package_steps, dict) and 'steps' in package_steps:
            package_steps = package_steps.get('steps')
        if not isinstance(package_steps, list):
            package_steps = []

        progress = notes.get('package_progress')
        if not isinstance(progress, list):
            progress = []

        scheduled_job_ids = notes.get('scheduled_job_ids')
        if not isinstance(scheduled_job_ids, list):
            scheduled_job_ids = []

        status_history = notes.get('status_history')
        if not isinstance(status_history, list):
            status_history = []

        return jsonify({
            'success': True,
            'order_id': order_id,
            'order_status': order_row.get('status'),
            'total_steps': len(package_steps),
            'package_steps': package_steps,
            'progress': progress,
            'scheduled_job_ids': scheduled_job_ids,
            'status_history': status_history,
            'completed_at': notes.get('package_completed_at')
        }), 200

    except Exception as e:
        print(f"❌ 패키지 진행 상황 조회 실패: {str(e)}")
        return jsonify({'error': f'패키지 진행 상황 조회 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
@app.route('/api/orders', methods=['GET'])
def get_orders():
    """사용자 주문 목록 조회"""
    conn = None
    cursor = None

    try:
        raw_user_id = request.args.get('user_id')
        if raw_user_id is None:
            return jsonify({'error': 'user_id가 필요합니다.'}), 400

        limit = min(int(request.args.get('limit', 50)), 200)

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        identifier = parse_user_identifier(raw_user_id)
        user = ensure_user_record(cursor, identifier)
        if not user:
            cursor.close()
            conn.close()
            return jsonify({'error': '사용자를 찾을 수 없습니다.'}), 404

        cursor.execute(
            """
            SELECT 
                o.order_id,
                o.total_amount,
                o.discount_amount,
                o.final_amount,
                o.status,
                o.notes,
                o.created_at,
                o.updated_at,
                o.referrer_user_id,
                ref.email AS referrer_email
            FROM orders o
            LEFT JOIN users ref ON o.referrer_user_id = ref.user_id
            WHERE o.user_id = %s
            ORDER BY o.created_at DESC
            LIMIT %s
            """,
            (user['user_id'], limit)
        )
        order_rows = cursor.fetchall()
        order_ids = [row['order_id'] for row in order_rows]

        items_map = {}
        tx_map = {}
        if order_ids:
            cursor.execute(
                """
                SELECT 
                    oi.order_id,
                    oi.order_item_id,
                    oi.variant_id,
                    oi.quantity,
                    oi.unit_price,
                    oi.line_amount,
                    oi.link,
                    oi.status,
                    pv.name AS variant_name,
                    pv.meta_json
                FROM order_items oi
                LEFT JOIN product_variants pv ON oi.variant_id = pv.variant_id
                WHERE oi.order_id = ANY(%s)
                ORDER BY oi.order_item_id
                """,
                (order_ids,)
            )
            for item in cursor.fetchall():
                items_map.setdefault(item['order_id'], []).append(item)

            cursor.execute(
                """
                SELECT 
                    wt.meta_json,
                    wt.transaction_id,
                    wt.wallet_id,
                    wt.amount,
                    wt.status,
                    wt.created_at,
                    (wt.meta_json->>'order_id')::BIGINT AS order_id
                FROM wallet_transactions wt
                WHERE wt.type = 'order_debit'
                  AND (wt.meta_json->>'order_id')::BIGINT = ANY(%s)
                """,
                (order_ids,)
            )
            for tx in cursor.fetchall():
                order_id = tx.get('order_id')
                if order_id:
                    tx_map.setdefault(order_id, []).append(tx)

        orders = []
        for row in order_rows:
            order_id = row['order_id']
            notes = json.loads(row['notes']) if row.get('notes') else {}
            smm_panel_order_id = notes.get('smm_panel_order_id') or notes.get('raw_payload', {}).get('smm_panel_order_id')
            items = items_map.get(order_id, [])

            orders.append({
                'order_id': order_id,
                'user_id': user['user_id'],
                'total_amount': float(row['total_amount']) if row.get('total_amount') is not None else None,
                'discount_amount': float(row['discount_amount']) if row.get('discount_amount') is not None else None,
                'final_amount': float(row['final_amount']) if row.get('final_amount') is not None else None,
                'status': row.get('status'),
                'created_at': row['created_at'].isoformat() if row.get('created_at') else None,
                'updated_at': row['updated_at'].isoformat() if row.get('updated_at') else None,
                'referrer_user_id': row.get('referrer_user_id'),
                'referrer_email': row.get('referrer_email'),
                'notes': notes,
                'smm_panel_order_id': smm_panel_order_id,
                'items': [
                    {
                        'order_item_id': item['order_item_id'],
                        'variant_id': item['variant_id'],
                        'variant_name': item.get('variant_name'),
                        'quantity': item['quantity'],
                        'unit_price': float(item['unit_price']) if item.get('unit_price') is not None else None,
                        'line_amount': float(item['line_amount']) if item.get('line_amount') is not None else None,
                        'link': item.get('link'),
                        'status': item.get('status'),
                        'meta': json.loads(item['meta_json']) if item.get('meta_json') else None
                    }
                    for item in items
                ],
                'wallet_transactions': [
                    {
                        'transaction_id': tx['transaction_id'],
                        'wallet_id': tx['wallet_id'],
                        'amount': float(tx['amount']) if tx.get('amount') is not None else None,
                        'status': tx.get('status'),
                        'created_at': tx['created_at'].isoformat() if tx.get('created_at') else None,
                        'meta': json.loads(tx['meta_json']) if tx.get('meta_json') else None
                    }
                    for tx in tx_map.get(order_id, [])
                ]
            })

        cursor.close()
        conn.close()

        return jsonify({'orders': orders}), 200

    except Exception as e:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print(f"❌ 주문 조회 오류: {e}")
        import traceback
        print(f"❌ 스택 트레이스: {traceback.format_exc()}")
        return jsonify({'error': f'주문 목록 조회 실패: {str(e)}'}), 500
# KCP 표준결제 - 거래등록 (Mobile)
@app.route('/api/points/purchase-kcp/register', methods=['POST'])
def kcp_register_transaction():
    """KCP 표준결제 거래등록 (Mobile)"""
    conn = None
    cursor = None

    try:
        data = request.get_json()
        raw_user_id = data.get('user_id')
        amount = data.get('amount')
        price = data.get('price')
        good_name = data.get('good_name', '포인트 구매')
        pay_method = data.get('pay_method', 'CARD')  # CARD, BANK, MOBX, TPNT, GIFT

        if raw_user_id is None or amount is None or price is None:
            return jsonify({'error': '필수 정보가 누락되었습니다.'}), 400

        identifier = parse_user_identifier(raw_user_id)

        try:
            amount_decimal = to_decimal(amount)
            price_decimal = to_decimal(price)
        except Exception:
            return jsonify({'error': '잘못된 금액 형식입니다.'}), 400

        if amount_decimal <= 0 or amount_decimal > Decimal('1000000'):
            return jsonify({'error': '포인트 금액이 범위를 벗어났습니다.'}), 400

        if price_decimal <= 0 or price_decimal > Decimal('10000000'):
            return jsonify({'error': '결제 금액이 범위를 벗어났습니다.'}), 400

        import time
        ordr_idxx = f"POINT_{int(time.time())}"

        fwd_proto = request.headers.get('X-Forwarded-Proto', 'https')
        fwd_host = request.headers.get('X-Forwarded-Host') or request.host
        if fwd_host and fwd_host.endswith('sociality.co.kr'):
            fwd_proto = 'https'
        external_base = f"{fwd_proto}://{fwd_host}"

        kcp_site_cd = get_parameter_value('KCP_SITE_CD', 'ALFCQ')
        kcp_cert_info = get_parameter_value('KCP_CERT_INFO', '')
        if kcp_cert_info:
            kcp_cert_info = kcp_cert_info.replace('\\n', '\n').strip()
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
            'good_mny': str(int(price_decimal)),
            'good_name': good_name,
            'pay_method': pay_method,
            'currency': '410',
            'shop_name': 'SOCIALITY',
            'kcp_cert_info': kcp_cert_info,
            'Ret_URL': f"{external_base}/api/points/purchase-kcp/return"
        }

        import requests
        kcp_register_url = 'https://stg-spl.kcp.co.kr/std/tradeReg/register'
        print(f"🔍 KCP 거래등록 URL: {kcp_register_url}")
        print(f"🔍 KCP 거래등록 데이터: {register_data}")

        response = requests.post(
            kcp_register_url,
            json=register_data,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()

        print(f"🔍 KCP 거래등록 응답 상태: {response.status_code}")
        print(f"🔍 KCP 거래등록 응답 헤더: {dict(response.headers)}")
        print(f"🔍 KCP 거래등록 응답 내용: {response.text[:500]}")

        try:
            kcp_response = response.json()
            print(f"🔍 KCP JSON 응답: {kcp_response}")
        except ValueError as json_err:
            print(f"❌ JSON 파싱 실패, HTML 응답으로 처리: {json_err}")
            response_text = response.text
            print(f"🔍 HTML 응답 내용: {response_text[:1000]}")
            import re
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
                print("❌ HTML에서 필요한 데이터를 찾을 수 없음")
                return jsonify({'error': 'KCP 서버 응답에서 필요한 데이터를 찾을 수 없습니다.'}), 500

        if kcp_response.get('Code') != '0000':
            return jsonify({
                'success': False,
                'error': f"KCP 거래등록 실패: {kcp_response.get('Message', '알 수 없는 오류')}",
                'kcp_response': kcp_response,
                'kcp_raw': str(kcp_response)
            }), 400

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        user = ensure_user_record(cursor, identifier)
        wallet = ensure_wallet_record(cursor, user['user_id'])

        metadata = {
            'gateway': 'kcp',
            'ordr_idxx': ordr_idxx,
            'good_name': good_name,
            'pay_method': pay_method,
            'payment_amount': float(price_decimal),
            'buyer_name': data.get('buyer_name'),
            'bank_info': data.get('bank_info'),
            'channel': 'kcp',
            'memo': data.get('memo'),
            'approvalKey': kcp_response.get('approvalKey'),
            'PayUrl': kcp_response.get('PayUrl'),
            'status': 'registered'
        }

        cursor.execute(
            """
            INSERT INTO wallet_transactions (
                wallet_id, type, amount, status, meta_json, locked, created_at, updated_at
            )
            VALUES (%s, 'topup', %s, 'pending', %s, FALSE, NOW(), NOW())
            RETURNING transaction_id
            """,
            (
                wallet['wallet_id'],
                amount_decimal,
                json.dumps(metadata, ensure_ascii=False)
            )
        )
        transaction = cursor.fetchone()

        conn.commit()

        return jsonify({
            'success': True,
            'purchase_id': transaction['transaction_id'],
            'transaction_id': transaction['transaction_id'],
            'ordr_idxx': ordr_idxx,
            'kcp_response': kcp_response,
            'message': 'KCP 결제 준비가 완료되었습니다. 결제창을 호출합니다.'
        }), 200

    except requests.RequestException as e:
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
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# KCP 표준결제 - 결제창 호출 데이터 생성
@app.route('/api/points/purchase-kcp/payment-form', methods=['POST'])
def kcp_payment_form():
    """KCP 표준결제 결제창 호출 데이터 생성"""
    conn = None
    cursor = None

    try:
        data = request.get_json()
        ordr_idxx = data.get('ordr_idxx')

        if not ordr_idxx:
            return jsonify({'error': 'ordr_idxx가 필요합니다.'}), 400

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT transaction_id,
                   wallet_id,
                   amount,
                   status,
                   meta_json
              FROM wallet_transactions
             WHERE type = 'topup'
               AND meta_json->>'ordr_idxx' = %s
            """,
            (ordr_idxx,)
        )
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': '거래 정보를 찾을 수 없습니다.'}), 404

        meta = {}
        if row.get('meta_json'):
            try:
                meta = json.loads(row['meta_json'])
            except json.JSONDecodeError:
                meta = {}

        pay_url = meta.get('PayUrl')
        approval_key = meta.get('approvalKey')
        pay_method = data.get('pay_method') or meta.get('pay_method') or 'CARD'

        if not pay_url or not approval_key:
            return jsonify({'error': '결제창 정보를 찾을 수 없습니다. 거래를 다시 등록해주세요.'}), 400

        kcp_site_cd = get_parameter_value('KCP_SITE_CD', 'ALFCQ')
        payment_form_data = {
            'site_cd': kcp_site_cd,
            'pay_method': pay_method,
            'currency': '410',
            'shop_name': 'SNS PMT',
            'Ret_URL': f"{request.host_url}api/points/purchase-kcp/return",
            'approval_key': approval_key,
            'PayUrl': pay_url,
            'ordr_idxx': ordr_idxx,
            'good_name': meta.get('good_name', '포인트 구매'),
            'good_cd': meta.get('good_cd', '00'),
            'good_mny': str(int(float(meta.get('payment_amount') or row['amount'] or 0))),
            'buyr_name': meta.get('buyer_name', ''),
            'buyr_mail': meta.get('buyer_email', ''),
            'buyr_tel2': meta.get('buyer_phone', ''),
            'shop_user_id': meta.get('external_uid') or meta.get('shop_user_id', ''),
            'van_code': meta.get('van_code', '')
        }

        return jsonify({
            'success': True,
            'payment_form_data': payment_form_data,
            'message': '결제창을 호출합니다. 카드 정보를 입력해주세요.'
        }), 200

    except Exception as e:
        print(f"❌ KCP 결제창 데이터 생성 실패: {e}")
        return jsonify({'error': 'KCP 결제창 데이터 생성에 실패했습니다.'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# KCP 결제창 인증결과 처리 (Ret_URL)
@app.route('/api/points/purchase-kcp/return', methods=['POST'])
def kcp_payment_return():
    """KCP 결제창 인증결과 처리"""
    conn = None
    cursor = None

    try:
        enc_data = request.form.get('enc_data')
        enc_info = request.form.get('enc_info')
        tran_cd = request.form.get('tran_cd')
        ordr_idxx = request.form.get('ordr_idxx')
        res_cd = request.form.get('res_cd')
        res_msg = request.form.get('res_msg')

        print(f"🔍 KCP 결제창 인증결과 수신: {ordr_idxx}")
        print(f"📊 인증결과: {res_cd} - {res_msg}")

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT transaction_id,
                   wallet_id,
                   amount,
                   status,
                   meta_json
              FROM wallet_transactions
             WHERE type = 'topup'
               AND meta_json->>'ordr_idxx' = %s
            """,
            (ordr_idxx,)
        )
        transaction = cursor.fetchone()
        if not transaction:
            return jsonify({'error': '거래 정보를 찾을 수 없습니다.'}), 404

        meta = {}
        if transaction.get('meta_json'):
            try:
                meta = json.loads(transaction['meta_json'])
            except json.JSONDecodeError:
                meta = {}

        meta.update({
            'res_cd': res_cd,
            'res_msg': res_msg,
            'enc_data': enc_data,
            'enc_info': enc_info,
            'tran_cd': tran_cd
        })

        if res_cd == '0000' and enc_data and enc_info:
            meta['status'] = 'authenticated'
            cursor.execute(
                """
                UPDATE wallet_transactions
                   SET status = %s,
                       meta_json = %s,
                       updated_at = NOW()
                 WHERE transaction_id = %s
                """,
                ('pending', json.dumps(meta, ensure_ascii=False), transaction['transaction_id'])
            )
            conn.commit()

            return jsonify({
                'success': True,
                'ordr_idxx': ordr_idxx,
                'enc_data': enc_data,
                'enc_info': enc_info,
                'tran_cd': tran_cd,
                'message': '인증이 완료되었습니다. 결제를 진행합니다.'
            }), 200
        else:
            meta['status'] = 'auth_failed'
            cursor.execute(
                """
                UPDATE wallet_transactions
                   SET status = %s,
                       meta_json = %s,
                       updated_at = NOW()
                 WHERE transaction_id = %s
                """,
                ('rejected', json.dumps(meta, ensure_ascii=False), transaction['transaction_id'])
            )
            conn.commit()

            return jsonify({
                'success': False,
                'error': f'인증 실패: {res_msg}',
                'res_cd': res_cd
            }), 400

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ KCP 결제창 인증결과 처리 실패: {e}")
        return jsonify({'error': '인증결과 처리에 실패했습니다.'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
# KCP 결제요청 (승인)
@app.route('/api/points/purchase-kcp/approve', methods=['POST'])
def kcp_payment_approve():
    """KCP 결제요청 (승인)"""
    conn = None
    cursor = None

    try:
        data = request.get_json()
        ordr_idxx = data.get('ordr_idxx')
        enc_data = data.get('enc_data')
        enc_info = data.get('enc_info')
        tran_cd = data.get('tran_cd')

        if not all([ordr_idxx, enc_data, enc_info, tran_cd]):
            return jsonify({'error': '필수 파라미터가 누락되었습니다.'}), 400

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT wt.transaction_id,
                   wt.wallet_id,
                   wt.amount,
                   wt.status,
                   wt.meta_json,
                   w.user_id
              FROM wallet_transactions wt
              JOIN wallets w ON wt.wallet_id = w.wallet_id
             WHERE wt.type = 'topup'
               AND wt.meta_json->>'ordr_idxx' = %s
             FOR UPDATE
            """,
            (ordr_idxx,)
        )
        transaction = cursor.fetchone()
        if not transaction:
            return jsonify({'error': '거래 정보를 찾을 수 없습니다.'}), 404

        if transaction['status'] != 'pending':
            return jsonify({'error': '이미 처리된 거래입니다.'}), 409

        meta = {}
        if transaction.get('meta_json'):
            try:
                meta = json.loads(transaction['meta_json'])
            except json.JSONDecodeError:
                meta = {}

        payment_amount = meta.get('payment_amount') or decimal_to_float(transaction['amount'])

        kcp_site_cd = get_parameter_value('KCP_SITE_CD', 'ALFCQ')
        kcp_cert_info = get_parameter_value('KCP_CERT_INFO', '')
        payment_data = {
            'tran_cd': tran_cd,
            'kcp_cert_info': kcp_cert_info,
            'site_cd': kcp_site_cd,
            'enc_data': enc_data,
            'enc_info': enc_info,
            'ordr_mony': str(int(float(payment_amount))),
            'pay_type': 'PACA',
            'ordr_no': ordr_idxx
        }

        import requests
        kcp_payment_url = 'https://stg-spl.kcp.co.kr/gw/enc/v1/payment'

        response = requests.post(kcp_payment_url, json=payment_data, timeout=30)
        response.raise_for_status()
        kcp_response = response.json()

        print(f"📊 KCP 결제요청 응답: {kcp_response}")

        if kcp_response.get('res_cd') == '0000':
            cursor.execute(
                """
                UPDATE wallets
                   SET balance = balance + %s,
                       updated_at = NOW()
                 WHERE wallet_id = %s
                 RETURNING balance
                """,
                (transaction['amount'], transaction['wallet_id'])
            )
            wallet_row = cursor.fetchone()

            meta['status'] = 'approved'
            meta['kcp_response'] = kcp_response

            cursor.execute(
                """
                UPDATE wallet_transactions
                   SET status = %s,
                       meta_json = %s,
                       updated_at = NOW()
                 WHERE transaction_id = %s
                """,
                ('approved', json.dumps(meta, ensure_ascii=False), transaction['transaction_id'])
            )

            conn.commit()

            print(f"✅ KCP 포인트 구매 완료: {ordr_idxx} - {transaction['amount']}포인트")

            return jsonify({
                'success': True,
                'message': '포인트 구매가 성공적으로 완료되었습니다!',
                'amount': float(transaction['amount']),
                'wallet_balance': decimal_to_float(wallet_row['balance']) if wallet_row else None,
                'kcp_response': kcp_response
            }), 200
        else:
            meta['status'] = 'rejected'
            meta['kcp_response'] = kcp_response
            cursor.execute(
                """
                UPDATE wallet_transactions
                   SET status = %s,
                       meta_json = %s,
                       updated_at = NOW()
                 WHERE transaction_id = %s
                """,
                ('rejected', json.dumps(meta, ensure_ascii=False), transaction['transaction_id'])
            )
            conn.commit()

            print(f"❌ KCP 포인트 구매 실패: {ordr_idxx} - {kcp_response.get('res_msg')}")

            return jsonify({
                'success': False,
                'error': f"결제 실패: {kcp_response.get('res_msg')}",
                'res_cd': kcp_response.get('res_cd')
            }), 400

    except requests.RequestException as e:
        if conn:
            conn.rollback()
        print(f"❌ KCP 결제요청 API 호출 실패: {e}")
        return jsonify({'error': 'KCP 결제요청 API 호출에 실패했습니다.'}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ KCP 결제요청 실패: {e}")
        return jsonify({'error': 'KCP 결제요청에 실패했습니다.'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 관리자 작업 큐 실행
@app.route('/api/admin/work-jobs/run', methods=['POST'])
@require_admin_auth
def run_work_jobs_api():
    """대기 중인 작업을 실행"""
    try:
        data = request.get_json() or {}
    except Exception:
        data = {}

    job_id = data.get('job_id')
    if job_id is not None:
        try:
            job_id_int = int(job_id)
        except (TypeError, ValueError):
            return jsonify({'error': 'job_id는 정수여야 합니다.'}), 400
        result = run_single_work_job(job_id_int)
        return jsonify({
            'job_ids': [job_id_int],
            'results': [result],
            'processed': 1
        }), 200

    limit = data.get('limit', 10)
    try:
        limit_int = int(limit)
    except (TypeError, ValueError):
        limit_int = 10
    limit_int = max(1, min(limit_int, 50))

    job_ids = fetch_due_job_ids(limit_int)
    results = [run_single_work_job(job_id) for job_id in job_ids]

    return jsonify({
        'requested': limit_int,
        'processed': len(results),
        'job_ids': job_ids,
        'results': results
    }), 200


@app.route('/api/admin/work-jobs', methods=['GET'])
@require_admin_auth
def list_work_jobs():
    """작업 큐 목록 조회"""
    status = request.args.get('status')
    limit_param = request.args.get('limit', 50)
    try:
        limit = min(max(int(limit_param), 1), 200)
    except (TypeError, ValueError):
        limit = 50

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        params: list = []
        query = """
            SELECT job_id,
                   user_id,
                   order_item_id,
                   package_item_id,
                   schedule_at,
                   status,
                   attempts,
                   last_run_at,
                   payload_json,
                   created_at,
                   updated_at
              FROM work_jobs
        """
        if status:
            query += " WHERE status = %s"
            params.append(status)

        query += " ORDER BY updated_at DESC LIMIT %s"
        params.append(limit)

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

        jobs = []
        for row in rows:
            payload = row.get('payload_json')
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    payload = {}
            jobs.append({
                'job_id': row['job_id'],
                'user_id': row.get('user_id'),
                'order_item_id': row.get('order_item_id'),
                'package_item_id': row.get('package_item_id'),
                'status': row.get('status'),
                'attempts': row.get('attempts'),
                'schedule_at': row.get('schedule_at').isoformat() if row.get('schedule_at') else None,
                'last_run_at': row.get('last_run_at').isoformat() if row.get('last_run_at') else None,
                'created_at': row.get('created_at').isoformat() if row.get('created_at') else None,
                'updated_at': row.get('updated_at').isoformat() if row.get('updated_at') else None,
                'payload': payload
            })

        cursor.close()
        conn.close()

        return jsonify({'jobs': jobs, 'count': len(jobs)}), 200

    except Exception as exc:
        return jsonify({'error': f'작업 조회 실패: {str(exc)}'}), 500


@app.route('/api/admin/work-jobs/<int:job_id>/retry', methods=['POST'])
@require_admin_auth
def retry_work_job(job_id: int):
    """실패한 작업을 다시 대기열로 이동"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """
            SELECT status
              FROM work_jobs
             WHERE job_id = %s
             FOR UPDATE
            """,
            (job_id,)
        )
        job = cursor.fetchone()
        if not job:
            conn.rollback()
            return jsonify({'error': '작업을 찾을 수 없습니다.'}), 404

        if job['status'] == 'completed':
            conn.rollback()
            return jsonify({'error': '완료된 작업은 다시 실행할 수 없습니다.'}), 400

        cursor.execute(
            """
            UPDATE work_jobs
               SET status = 'pending',
                   schedule_at = NOW(),
                   attempts = 0,
                   updated_at = NOW(),
                   payload_json = COALESCE(payload_json, '{}'::jsonb) || %s::jsonb
             WHERE job_id = %s
            """,
            (
                json.dumps({'retry_requested_at': datetime.utcnow().isoformat()}, ensure_ascii=False),
                job_id
            )
        )
        conn.commit()
        return jsonify({'success': True, 'job_id': job_id}), 200

    except Exception as exc:
        if conn:
            conn.rollback()
        return jsonify({'error': f'작업 재시작 실패: {str(exc)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/api/admin/work-jobs/<int:job_id>/cancel', methods=['POST'])
@require_admin_auth
def cancel_work_job(job_id: int):
    """작업을 취소 상태로 표시"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """
            SELECT status
              FROM work_jobs
             WHERE job_id = %s
             FOR UPDATE
            """,
            (job_id,)
        )
        job = cursor.fetchone()
        if not job:
            conn.rollback()
            return jsonify({'error': '작업을 찾을 수 없습니다.'}), 404

        if job['status'] == 'completed':
            conn.rollback()
            return jsonify({'error': '완료된 작업은 취소할 수 없습니다.'}), 400

        cursor.execute(
            """
            UPDATE work_jobs
               SET status = 'canceled',
                   updated_at = NOW(),
                   payload_json = COALESCE(payload_json, '{}'::jsonb) || %s::jsonb
             WHERE job_id = %s
            """,
            (
                json.dumps({'canceled_at': datetime.utcnow().isoformat()}, ensure_ascii=False),
                job_id
            )
        )
        conn.commit()
        return jsonify({'success': True, 'job_id': job_id}), 200

    except Exception as exc:
        if conn:
            conn.rollback()
        return jsonify({'error': f'작업 취소 실패: {str(exc)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/api/admin/orders/sync-smm', methods=['POST'])
@require_admin_auth
def admin_sync_smm_orders():
    """SMM Panel 상태 동기화 실행"""
    payload = request.get_json(silent=True) or {}
    limit_param = payload.get('limit') or request.args.get('limit', 50)
    try:
        limit = min(max(int(limit_param), 1), 200)
    except (TypeError, ValueError):
        limit = 50

    try:
        results = sync_smm_panel_orders(limit)
        return jsonify({
            'success': True,
            'synced_orders': len(results),
            'results': results
        }), 200
    except Exception as exc:
        return jsonify({'error': f'SMM 동기화 실패: {str(exc)}'}), 500


# ------------------------------
# 관리자 카테고리/상품/패키지 관리
# ------------------------------

def serialize_category(row: dict) -> dict:
    return {
        'category_id': row.get('category_id'),
        'name': row.get('name'),
        'slug': row.get('slug'),
        'is_active': bool(row.get('is_active')),
        'image_url': row.get('image_url'),
        'created_at': to_isoformat_or_none(row.get('created_at')),
        'updated_at': to_isoformat_or_none(row.get('updated_at'))
    }


def serialize_product(row: dict) -> dict:
    return {
        'product_id': row.get('product_id'),
        'category_id': row.get('category_id'),
        'category_name': row.get('category_name'),
        'name': row.get('name'),
        'description': row.get('description'),
        'is_domestic': bool(row.get('is_domestic')),
        'auto_tag': bool(row.get('auto_tag')),
        'created_at': to_isoformat_or_none(row.get('created_at')),
        'updated_at': to_isoformat_or_none(row.get('updated_at'))
    }


def deserialize_meta(meta_value):
    if meta_value is None:
        return None
    if isinstance(meta_value, (dict, list)):
        return meta_value
    if isinstance(meta_value, str):
        try:
            return json.loads(meta_value)
        except json.JSONDecodeError:
            return meta_value
    return meta_value


def serialize_variant(row: dict) -> dict:
    return {
        'variant_id': row.get('variant_id'),
        'product_id': row.get('product_id'),
        'product_name': row.get('product_name'),
        'name': row.get('name'),
        'price': float(row.get('price')) if row.get('price') is not None else None,
        'min_quantity': row.get('min_quantity'),
        'max_quantity': row.get('max_quantity'),
        'delivery_time_days': row.get('delivery_time_days'),
        'is_active': bool(row.get('is_active')),
        'meta_json': deserialize_meta(row.get('meta_json')),
        'api_endpoint': row.get('api_endpoint'),
        'created_at': to_isoformat_or_none(row.get('created_at')),
        'updated_at': to_isoformat_or_none(row.get('updated_at'))
    }


def serialize_package(row: dict, items_map: dict[int, list[dict]]) -> dict:
    return {
        'package_id': row.get('package_id'),
        'category_id': row.get('category_id'),
        'category_name': row.get('category_name'),
        'name': row.get('name'),
        'description': row.get('description'),
        'created_at': to_isoformat_or_none(row.get('created_at')),
        'updated_at': to_isoformat_or_none(row.get('updated_at')),
        'items': items_map.get(row.get('package_id'), [])
    }


@app.route('/api/admin/categories', methods=['GET', 'POST'])
@require_admin_auth
def admin_categories():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        if request.method == 'GET':
            include_inactive = parse_bool(request.args.get('include_inactive'), False)
            query = """
                SELECT category_id, name, slug, is_active, image_url, created_at, updated_at
                  FROM categories
            """
            params: tuple = ()
            if not include_inactive:
                query += " WHERE is_active = TRUE"
            query += " ORDER BY name ASC"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            categories = [serialize_category(row) for row in rows]
            return jsonify({'categories': categories, 'count': len(categories)}), 200

        data = request.get_json() or {}
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'error': 'name은 필수입니다.'}), 400

        slug = data.get('slug')
        slug = slug.strip() if isinstance(slug, str) and slug.strip() else None
        image_url = data.get('image_url')
        is_active = parse_bool(data.get('is_active'), True)

        cursor.execute(
            """
            INSERT INTO categories (name, slug, is_active, image_url, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
            RETURNING category_id, name, slug, is_active, image_url, created_at, updated_at
            """,
            (name, slug, is_active, image_url)
        )
        row = cursor.fetchone()
        conn.commit()
        return jsonify({'category': serialize_category(row)}), 201

    except psycopg2.Error as exc:
        if conn:
            conn.rollback()
        return jsonify({'error': f'카테고리 저장 실패: {str(exc)}'}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/admin/categories/<int:category_id>', methods=['GET', 'PUT', 'DELETE'])
@require_admin_auth
def admin_category_detail(category_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        if request.method == 'GET':
            cursor.execute(
                """
                SELECT category_id, name, slug, is_active, image_url, created_at, updated_at
                  FROM categories
                 WHERE category_id = %s
                """,
                (category_id,)
            )
            row = cursor.fetchone()
            if not row:
                return jsonify({'error': '카테고리를 찾을 수 없습니다.'}), 404
            return jsonify({'category': serialize_category(row)}), 200

        if request.method == 'DELETE':
            cursor.execute(
                """
                UPDATE categories
                   SET is_active = FALSE,
                       updated_at = NOW()
                 WHERE category_id = %s
                RETURNING category_id, name, slug, is_active, image_url, created_at, updated_at
                """,
                (category_id,)
            )
            row = cursor.fetchone()
            if not row:
                conn.rollback()
                return jsonify({'error': '카테고리를 찾을 수 없습니다.'}), 404
            conn.commit()
            return jsonify({'category': serialize_category(row)}), 200

        data = request.get_json() or {}
        fields = []
        values = []

        if 'name' in data:
            name = (data.get('name') or '').strip()
            if not name:
                return jsonify({'error': 'name은 비워둘 수 없습니다.'}), 400
            fields.append("name = %s")
            values.append(name)

        if 'slug' in data:
            slug = data.get('slug')
            slug = slug.strip() if isinstance(slug, str) and slug.strip() else None
            fields.append("slug = %s")
            values.append(slug)

        if 'is_active' in data:
            fields.append("is_active = %s")
            values.append(parse_bool(data.get('is_active'), True))

        if 'image_url' in data:
            fields.append("image_url = %s")
            values.append(data.get('image_url'))

        if not fields:
            return jsonify({'error': '업데이트할 필드가 없습니다.'}), 400

        fields.append("updated_at = NOW()")
        query = f"""
            UPDATE categories
               SET {', '.join(fields)}
             WHERE category_id = %s
         RETURNING category_id, name, slug, is_active, image_url, created_at, updated_at
        """
        values.append(category_id)
        cursor.execute(query, tuple(values))
        row = cursor.fetchone()
        if not row:
            conn.rollback()
            return jsonify({'error': '카테고리를 찾을 수 없습니다.'}), 404
        conn.commit()
        return jsonify({'category': serialize_category(row)}), 200

    except psycopg2.Error as exc:
        if conn:
            conn.rollback()
        return jsonify({'error': f'카테고리 업데이트 실패: {str(exc)}'}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/admin/products', methods=['GET', 'POST'])
@require_admin_auth
def admin_products():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        if request.method == 'GET':
            category_id = request.args.get('category_id')
            params = []
            query = """
                SELECT p.product_id,
                       p.category_id,
                       c.name AS category_name,
                       p.name,
                       p.description,
                       p.is_domestic,
                       p.auto_tag,
                       p.created_at,
                       p.updated_at
                  FROM products p
             LEFT JOIN categories c ON p.category_id = c.category_id
            """
            if category_id:
                query += " WHERE p.category_id = %s"
                params.append(int(category_id))
            query += " ORDER BY p.created_at DESC"
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            products = [serialize_product(row) for row in rows]
            return jsonify({'products': products, 'count': len(products)}), 200

        data = request.get_json() or {}
        category_id = parse_int(data.get('category_id'))
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'error': 'name은 필수입니다.'}), 400

        cursor.execute(
            """
            INSERT INTO products (category_id, name, description, is_domestic, auto_tag, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING product_id, category_id, name, description, is_domestic, auto_tag, created_at, updated_at
            """,
            (
                category_id,
                name,
                data.get('description'),
                parse_bool(data.get('is_domestic'), True),
                parse_bool(data.get('auto_tag'), False)
            )
        )
        row = cursor.fetchone()
        conn.commit()

        cursor.execute(
            "SELECT name FROM categories WHERE category_id = %s",
            (row['category_id'],)
        )
        cat_row = cursor.fetchone()
        if cat_row:
            row['category_name'] = cat_row['name']

        return jsonify({'product': serialize_product(row)}), 201

    except psycopg2.Error as exc:
        if conn:
            conn.rollback()
        return jsonify({'error': f'상품 저장 실패: {str(exc)}'}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/admin/products/<int:product_id>', methods=['GET', 'PUT', 'DELETE'])
@require_admin_auth
def admin_product_detail(product_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        if request.method == 'GET':
            cursor.execute(
                """
                SELECT p.product_id,
                       p.category_id,
                       c.name AS category_name,
                       p.name,
                       p.description,
                       p.is_domestic,
                       p.auto_tag,
                       p.created_at,
                       p.updated_at
                  FROM products p
             LEFT JOIN categories c ON p.category_id = c.category_id
                 WHERE p.product_id = %s
                """,
                (product_id,)
            )
            row = cursor.fetchone()
            if not row:
                return jsonify({'error': '상품을 찾을 수 없습니다.'}), 404
            return jsonify({'product': serialize_product(row)}), 200

        if request.method == 'DELETE':
            cursor.execute(
                "SELECT 1 FROM product_variants WHERE product_id = %s LIMIT 1",
                (product_id,)
            )
            if cursor.fetchone():
                conn.rollback()
                return jsonify({'error': '연결된 상품 옵션이 있어 삭제할 수 없습니다.'}), 400

            cursor.execute("DELETE FROM products WHERE product_id = %s RETURNING product_id", (product_id,))
            row = cursor.fetchone()
            if not row:
                conn.rollback()
                return jsonify({'error': '상품을 찾을 수 없습니다.'}), 404
            conn.commit()
            return jsonify({'success': True}), 200

        data = request.get_json() or {}
        fields = []
        values = []

        if 'category_id' in data:
            fields.append("category_id = %s")
            values.append(parse_int(data.get('category_id')))

        if 'name' in data:
            name = (data.get('name') or '').strip()
            if not name:
                return jsonify({'error': 'name은 비워둘 수 없습니다.'}), 400
            fields.append("name = %s")
            values.append(name)

        if 'description' in data:
            fields.append("description = %s")
            values.append(data.get('description'))

        if 'is_domestic' in data:
            fields.append("is_domestic = %s")
            values.append(parse_bool(data.get('is_domestic'), True))

        if 'auto_tag' in data:
            fields.append("auto_tag = %s")
            values.append(parse_bool(data.get('auto_tag'), False))

        if not fields:
            return jsonify({'error': '업데이트할 필드가 없습니다.'}), 400

        fields.append("updated_at = NOW()")
        query = f"""
            UPDATE products
               SET {', '.join(fields)}
             WHERE product_id = %s
         RETURNING product_id, category_id, name, description, is_domestic, auto_tag, created_at, updated_at
        """
        values.append(product_id)
        cursor.execute(query, tuple(values))
        row = cursor.fetchone()
        if not row:
            conn.rollback()
            return jsonify({'error': '상품을 찾을 수 없습니다.'}), 404
        conn.commit()

        cursor.execute("SELECT name FROM categories WHERE category_id = %s", (row['category_id'],))
        cat = cursor.fetchone()
        if cat:
            row['category_name'] = cat['name']

        return jsonify({'product': serialize_product(row)}), 200

    except psycopg2.Error as exc:
        if conn:
            conn.rollback()
        return jsonify({'error': f'상품 업데이트 실패: {str(exc)}'}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/admin/product-variants', methods=['GET', 'POST'])
@require_admin_auth
def admin_product_variants():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        if request.method == 'GET':
            product_id = request.args.get('product_id')
            params = []
            query = """
                SELECT v.variant_id,
                       v.product_id,
                       p.name AS product_name,
                       v.name,
                       v.price,
                       v.min_quantity,
                       v.max_quantity,
                       v.delivery_time_days,
                       v.is_active,
                       v.meta_json,
                       v.api_endpoint,
                       v.created_at,
                       v.updated_at
                  FROM product_variants v
             LEFT JOIN products p ON v.product_id = p.product_id
            """
            if product_id:
                query += " WHERE v.product_id = %s"
                params.append(int(product_id))
            query += " ORDER BY v.created_at DESC"
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            variants = [serialize_variant(row) for row in rows]
            return jsonify({'variants': variants, 'count': len(variants)}), 200

        data = request.get_json() or {}
        product_id = parse_int(data.get('product_id'))
        name = (data.get('name') or '').strip()
        if not product_id or not name:
            return jsonify({'error': 'product_id와 name은 필수입니다.'}), 400

        price = to_decimal(data.get('price'))
        min_quantity = parse_int(data.get('min_quantity'))
        max_quantity = parse_int(data.get('max_quantity'))
        delivery_time_days = parse_int(data.get('delivery_time_days'))
        is_active = parse_bool(data.get('is_active'), True)
        meta_json = data.get('meta_json')
        if isinstance(meta_json, (dict, list)):
            meta_json = json.dumps(meta_json, ensure_ascii=False)

        cursor.execute(
            """
            INSERT INTO product_variants
                (product_id, name, price, min_quantity, max_quantity, delivery_time_days,
                 is_active, meta_json, api_endpoint, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING variant_id, product_id, name, price, min_quantity, max_quantity, delivery_time_days,
                      is_active, meta_json, api_endpoint, created_at, updated_at
            """,
            (
                product_id,
                name,
                price,
                min_quantity,
                max_quantity,
                delivery_time_days,
                is_active,
                meta_json,
                data.get('api_endpoint')
            )
        )
        row = cursor.fetchone()
        conn.commit()

        cursor.execute("SELECT name FROM products WHERE product_id = %s", (row['product_id'],))
        prod = cursor.fetchone()
        if prod:
            row['product_name'] = prod['name']

        return jsonify({'variant': serialize_variant(row)}), 201

    except (psycopg2.Error, InvalidOperation) as exc:
        if conn:
            conn.rollback()
        return jsonify({'error': f'상품 옵션 저장 실패: {str(exc)}'}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/admin/product-variants/<int:variant_id>', methods=['GET', 'PUT', 'DELETE'])
@require_admin_auth
def admin_product_variant_detail(variant_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        if request.method == 'GET':
            cursor.execute(
                """
                SELECT v.variant_id,
                       v.product_id,
                       p.name AS product_name,
                       v.name,
                       v.price,
                       v.min_quantity,
                       v.max_quantity,
                       v.delivery_time_days,
                       v.is_active,
                       v.meta_json,
                       v.api_endpoint,
                       v.created_at,
                       v.updated_at
                  FROM product_variants v
             LEFT JOIN products p ON v.product_id = p.product_id
                 WHERE v.variant_id = %s
                """,
                (variant_id,)
            )
            row = cursor.fetchone()
            if not row:
                return jsonify({'error': '상품 옵션을 찾을 수 없습니다.'}), 404
            return jsonify({'variant': serialize_variant(row)}), 200

        if request.method == 'DELETE':
            cursor.execute("DELETE FROM product_variants WHERE variant_id = %s RETURNING variant_id", (variant_id,))
            row = cursor.fetchone()
            if not row:
                conn.rollback()
                return jsonify({'error': '상품 옵션을 찾을 수 없습니다.'}), 404
            conn.commit()
            return jsonify({'success': True}), 200

        data = request.get_json() or {}
        fields = []
        values = []

        if 'product_id' in data:
            fields.append("product_id = %s")
            values.append(parse_int(data.get('product_id')))

        if 'name' in data:
            name = (data.get('name') or '').strip()
            if not name:
                return jsonify({'error': 'name은 비워둘 수 없습니다.'}), 400
            fields.append("name = %s")
            values.append(name)

        if 'price' in data:
            fields.append("price = %s")
            values.append(to_decimal(data.get('price')))

        if 'min_quantity' in data:
            fields.append("min_quantity = %s")
            values.append(parse_int(data.get('min_quantity')))

        if 'max_quantity' in data:
            fields.append("max_quantity = %s")
            values.append(parse_int(data.get('max_quantity')))

        if 'delivery_time_days' in data:
            fields.append("delivery_time_days = %s")
            values.append(parse_int(data.get('delivery_time_days')))

        if 'is_active' in data:
            fields.append("is_active = %s")
            values.append(parse_bool(data.get('is_active'), True))

        if 'meta_json' in data:
            meta_json = data.get('meta_json')
            if isinstance(meta_json, (dict, list)):
                meta_json = json.dumps(meta_json, ensure_ascii=False)
            fields.append("meta_json = %s")
            values.append(meta_json)

        if 'api_endpoint' in data:
            fields.append("api_endpoint = %s")
            values.append(data.get('api_endpoint'))

        if not fields:
            return jsonify({'error': '업데이트할 필드가 없습니다.'}), 400

        fields.append("updated_at = NOW()")
        query = f"""
            UPDATE product_variants
               SET {', '.join(fields)}
             WHERE variant_id = %s
         RETURNING variant_id, product_id, name, price, min_quantity, max_quantity, delivery_time_days,
                   is_active, meta_json, api_endpoint, created_at, updated_at
        """
        values.append(variant_id)
        cursor.execute(query, tuple(values))
        row = cursor.fetchone()
        if not row:
            conn.rollback()
            return jsonify({'error': '상품 옵션을 찾을 수 없습니다.'}), 404
        conn.commit()

        cursor.execute("SELECT name FROM products WHERE product_id = %s", (row['product_id'],))
        prod = cursor.fetchone()
        if prod:
            row['product_name'] = prod['name']

        return jsonify({'variant': serialize_variant(row)}), 200

    except (psycopg2.Error, InvalidOperation) as exc:
        if conn:
            conn.rollback()
        return jsonify({'error': f'상품 옵션 업데이트 실패: {str(exc)}'}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/admin/packages', methods=['GET', 'POST'])
@require_admin_auth
def admin_packages():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        if request.method == 'GET':
            cursor.execute(
                """
                SELECT pk.package_id,
                       pk.category_id,
                       c.name AS category_name,
                       pk.name,
                       pk.description,
                       pk.created_at,
                       pk.updated_at
                  FROM packages pk
             LEFT JOIN categories c ON pk.category_id = c.category_id
              ORDER BY pk.created_at DESC
                """
            )
            packages = cursor.fetchall()
            package_ids = [row['package_id'] for row in packages]
            items_map: dict[int, list[dict]] = {}

            if package_ids:
                cursor.execute(
                    """
                    SELECT pi.package_item_id,
                           pi.package_id,
                           pi.variant_id,
                           pv.name AS variant_name,
                           pi.step,
                           pi.term_value,
                           pi.term_unit,
                           pi.quantity,
                           pi.repeat_count,
                           pi.repeat_term_value,
                           pi.repeat_term_unit
                      FROM package_items pi
                 LEFT JOIN product_variants pv ON pi.variant_id = pv.variant_id
                     WHERE pi.package_id = ANY(%s)
                  ORDER BY pi.package_id, pi.step, pi.package_item_id
                    """,
                    (package_ids,)
                )
                for item in cursor.fetchall():
                    items_map.setdefault(item['package_id'], []).append({
                        'package_item_id': item['package_item_id'],
                        'variant_id': item['variant_id'],
                        'variant_name': item.get('variant_name'),
                        'step': item.get('step'),
                        'term_value': item.get('term_value'),
                        'term_unit': item.get('term_unit'),
                        'quantity': item.get('quantity'),
                        'repeat_count': item.get('repeat_count'),
                        'repeat_term_value': item.get('repeat_term_value'),
                        'repeat_term_unit': item.get('repeat_term_unit')
                    })

            serialized = [serialize_package(row, items_map) for row in packages]
            return jsonify({'packages': serialized, 'count': len(serialized)}), 200

        data = request.get_json() or {}
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'error': 'name은 필수입니다.'}), 400

        category_id = parse_int(data.get('category_id'))
        description = data.get('description')
        items = data.get('items') or []

        cursor.execute(
            """
            INSERT INTO packages (category_id, name, description, created_at, updated_at)
            VALUES (%s, %s, %s, NOW(), NOW())
            RETURNING package_id, category_id, name, description, created_at, updated_at
            """,
            (category_id, name, description)
        )
        package_row = cursor.fetchone()
        package_id = package_row['package_id']

        for idx, item in enumerate(items, start=1):
            variant_id = parse_int(item.get('variant_id'))
            if not variant_id:
                conn.rollback()
                return jsonify({'error': f'items[{idx-1}].variant_id는 필수입니다.'}), 400
            step = parse_int(item.get('step'), idx)
            cursor.execute(
                """
                INSERT INTO package_items (
                    package_id, variant_id, step, term_value, term_unit, quantity,
                    repeat_count, repeat_term_value, repeat_term_unit, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                """,
                (
                    package_id,
                    variant_id,
                    step,
                    parse_int(item.get('term_value')),
                    item.get('term_unit'),
                    parse_int(item.get('quantity')),
                    parse_int(item.get('repeat_count')),
                    parse_int(item.get('repeat_term_value')),
                    item.get('repeat_term_unit')
                )
            )

        conn.commit()
        return jsonify({'package': serialize_package(package_row, {})}), 201

    except psycopg2.Error as exc:
        if conn:
            conn.rollback()
        return jsonify({'error': f'패키지 저장 실패: {str(exc)}'}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/admin/packages/<int:package_id>', methods=['GET', 'PUT', 'DELETE'])
@require_admin_auth
def admin_package_detail(package_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(
            """
            SELECT pk.package_id,
                   pk.category_id,
                   c.name AS category_name,
                   pk.name,
                   pk.description,
                   pk.created_at,
                   pk.updated_at
              FROM packages pk
         LEFT JOIN categories c ON pk.category_id = c.category_id
             WHERE pk.package_id = %s
            """,
            (package_id,)
        )
        package_row = cursor.fetchone()
        if not package_row:
            return jsonify({'error': '패키지를 찾을 수 없습니다.'}), 404

        if request.method == 'GET':
            cursor.execute(
                """
                SELECT pi.package_item_id,
                       pi.package_id,
                       pi.variant_id,
                       pv.name AS variant_name,
                       pi.step,
                       pi.term_value,
                       pi.term_unit,
                       pi.quantity,
                       pi.repeat_count,
                       pi.repeat_term_value,
                       pi.repeat_term_unit
                  FROM package_items pi
             LEFT JOIN product_variants pv ON pi.variant_id = pv.variant_id
                 WHERE pi.package_id = %s
              ORDER BY pi.step, pi.package_item_id
                """,
                (package_id,)
            )
            items = cursor.fetchall()
            items_map = {package_id: [
                {
                    'package_item_id': item['package_item_id'],
                    'variant_id': item['variant_id'],
                    'variant_name': item.get('variant_name'),
                    'step': item.get('step'),
                    'term_value': item.get('term_value'),
                    'term_unit': item.get('term_unit'),
                    'quantity': item.get('quantity'),
                    'repeat_count': item.get('repeat_count'),
                    'repeat_term_value': item.get('repeat_term_value'),
                    'repeat_term_unit': item.get('repeat_term_unit')
                } for item in items
            ]}
            return jsonify({'package': serialize_package(package_row, items_map)}), 200

        if request.method == 'DELETE':
            cursor.execute("DELETE FROM package_items WHERE package_id = %s", (package_id,))
            cursor.execute("DELETE FROM packages WHERE package_id = %s", (package_id,))
            conn.commit()
            return jsonify({'success': True}), 200

        data = request.get_json() or {}
        category_id = data.get('category_id')
        name = data.get('name')
        description = data.get('description')
        items = data.get('items')

        fields = []
        values = []
        if category_id is not None:
            fields.append("category_id = %s")
            values.append(parse_int(category_id))
        if name is not None:
            if not name.strip():
                return jsonify({'error': 'name은 비워둘 수 없습니다.'}), 400
            fields.append("name = %s")
            values.append(name.strip())
        if description is not None:
            fields.append("description = %s")
            values.append(description)

        if fields:
            fields.append("updated_at = NOW()")
            query = f"""
                UPDATE packages
                   SET {', '.join(fields)}
                 WHERE package_id = %s
            """
            values.append(package_id)
            cursor.execute(query, tuple(values))

        if items is not None:
            cursor.execute("DELETE FROM package_items WHERE package_id = %s", (package_id,))
            for idx, item in enumerate(items, start=1):
                variant_id = parse_int(item.get('variant_id'))
                if not variant_id:
                    conn.rollback()
                    return jsonify({'error': f'items[{idx-1}].variant_id는 필수입니다.'}), 400
                step = parse_int(item.get('step'), idx)
                cursor.execute(
                    """
                    INSERT INTO package_items (
                        package_id, variant_id, step, term_value, term_unit, quantity,
                        repeat_count, repeat_term_value, repeat_term_unit, created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    """,
                    (
                        package_id,
                        variant_id,
                        step,
                        parse_int(item.get('term_value')),
                        item.get('term_unit'),
                        parse_int(item.get('quantity')),
                        parse_int(item.get('repeat_count')),
                        parse_int(item.get('repeat_term_value')),
                        item.get('repeat_term_unit')
                    )
                )

        conn.commit()
        return jsonify({'success': True}), 200

    except psycopg2.Error as exc:
        if conn:
            conn.rollback()
        return jsonify({'error': f'패키지 업데이트 실패: {str(exc)}'}), 500
    finally:
        cursor.close()
        conn.close()


# 관리자 통계
@app.route('/api/admin/stats', methods=['GET'])
@require_admin_auth
def get_admin_stats():
    """관리자 통계"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM orders")
        total_orders = cursor.fetchone()[0]

        cursor.execute("SELECT COALESCE(SUM(price), 0) FROM orders WHERE status = 'completed'")
        order_revenue = cursor.fetchone()[0] or 0

        cursor.execute(
            """
            SELECT COALESCE(SUM(amount), 0)
              FROM wallet_transactions
             WHERE type = 'topup'
               AND status = 'approved'
            """
        )
        purchase_revenue = cursor.fetchone()[0] or 0
        total_revenue = order_revenue + purchase_revenue

        cursor.execute(
            """
            SELECT COUNT(*)
              FROM wallet_transactions
             WHERE type = 'topup'
               AND status = 'pending'
            """
        )
        pending_purchases = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM orders WHERE DATE(created_at) = CURRENT_DATE")
        today_orders = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COALESCE(SUM(price), 0)
              FROM orders
             WHERE DATE(created_at) = CURRENT_DATE
               AND status = 'completed'
            """
        )
        today_order_revenue = cursor.fetchone()[0] or 0

        cursor.execute(
            """
            SELECT COALESCE(SUM(amount), 0)
              FROM wallet_transactions
             WHERE type = 'topup'
               AND status = 'approved'
               AND DATE(created_at) = CURRENT_DATE
            """
        )
        today_purchase_revenue = cursor.fetchone()[0] or 0
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
@require_admin_auth
def get_admin_purchases():
    """관리자 포인트 구매 목록"""
    try:
        print("🔍 관리자 포인트 구매 목록 조회 시작")
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT wt.transaction_id,
                   wt.amount,
                   wt.status,
                   wt.created_at,
                   wt.meta_json,
                   w.user_id,
                   u.email
              FROM wallet_transactions wt
              JOIN wallets w ON wt.wallet_id = w.wallet_id
         LEFT JOIN users u ON w.user_id = u.user_id
             WHERE wt.type = 'topup'
             ORDER BY wt.created_at DESC
            """
        )
        rows = cursor.fetchall()
        conn.close()

        purchases = []
        for row in rows:
            meta = {}
            if row.get('meta_json'):
                try:
                    meta = json.loads(row['meta_json'])
                except json.JSONDecodeError:
                    meta = {}

            purchases.append({
                'id': row['transaction_id'],
                'user_id': row['user_id'],
                'email': row.get('email'),
                'amount': float(row['amount']) if row['amount'] is not None else 0.0,
                'payment_amount': float(meta.get('payment_amount') or row['amount'] or 0),
                'status': row['status'],
                'created_at': to_isoformat_or_none(row['created_at']),
                'buyer_name': meta.get('buyer_name'),
                'bank_info': meta.get('bank_info'),
                'channel': meta.get('channel'),
                'memo': meta.get('memo')
            })

        return jsonify({'purchases': purchases}), 200

    except Exception as e:
        return jsonify({'error': f'포인트 구매 목록 조회 실패: {str(e)}'}), 500


@app.route('/api/admin/purchases/<int:transaction_id>/approve', methods=['POST'])
@require_admin_auth
def approve_admin_purchase(transaction_id: int):
    """관리자가 수동 승인하여 지갑 잔액을 충전"""
    conn = None
    cursor = None

    try:
        payload = request.get_json(silent=True) or {}
        admin_note = payload.get('admin_note')

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT wt.transaction_id,
                   wt.wallet_id,
                   wt.amount,
                   wt.status,
                   wt.meta_json,
                   w.user_id
              FROM wallet_transactions wt
              JOIN wallets w ON wt.wallet_id = w.wallet_id
             WHERE wt.transaction_id = %s
               AND wt.type = 'topup'
             FOR UPDATE
            """,
            (transaction_id,),
        )
        transaction = cursor.fetchone()
        if not transaction:
            return jsonify({'error': '거래 정보를 찾을 수 없습니다.'}), 404

        if transaction['status'] != 'pending':
            return jsonify({'error': '이미 처리된 거래입니다.'}), 409

        meta = {}
        if transaction.get('meta_json'):
            try:
                meta = json.loads(transaction['meta_json'])
            except json.JSONDecodeError:
                meta = {}

        if admin_note:
            meta['admin_note'] = admin_note
        meta['admin_action'] = 'approved'

        cursor.execute(
            """
            UPDATE wallets
               SET balance = balance + %s,
                   updated_at = NOW()
             WHERE wallet_id = %s
             RETURNING balance
            """,
            (transaction['amount'], transaction['wallet_id']),
        )
        wallet_row = cursor.fetchone()

        cursor.execute(
            """
            UPDATE wallet_transactions
               SET status = %s,
                   meta_json = %s,
                   updated_at = NOW()
             WHERE transaction_id = %s
            """,
            ('approved', json.dumps(meta, ensure_ascii=False), transaction_id),
        )

        conn.commit()

        return jsonify({
            'success': True,
            'transaction_id': transaction_id,
            'wallet_balance': decimal_to_float(wallet_row['balance']) if wallet_row else None
        }), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'error': f'거래 승인 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/api/admin/purchases/<int:transaction_id>/reject', methods=['POST'])
@require_admin_auth
def reject_admin_purchase(transaction_id: int):
    """관리자가 수동 거절"""
    conn = None
    cursor = None

    try:
        payload = request.get_json(silent=True) or {}
        admin_note = payload.get('admin_note')
        reject_reason = payload.get('reason')

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT wt.transaction_id,
                   wt.wallet_id,
                   wt.amount,
                   wt.status,
                   wt.meta_json,
                   w.user_id
              FROM wallet_transactions wt
              JOIN wallets w ON wt.wallet_id = w.wallet_id
             WHERE wt.transaction_id = %s
               AND wt.type = 'topup'
             FOR UPDATE
            """,
            (transaction_id,),
        )
        transaction = cursor.fetchone()
        if not transaction:
            return jsonify({'error': '거래 정보를 찾을 수 없습니다.'}), 404

        if transaction['status'] != 'pending':
            return jsonify({'error': '이미 처리된 거래입니다.'}), 409

        meta = {}
        if transaction.get('meta_json'):
            try:
                meta = json.loads(transaction['meta_json'])
            except json.JSONDecodeError:
                meta = {}

        if admin_note:
            meta['admin_note'] = admin_note
        if reject_reason:
            meta['reject_reason'] = reject_reason
        meta['admin_action'] = 'rejected'

        cursor.execute(
            """
            UPDATE wallet_transactions
               SET status = %s,
                   meta_json = %s,
                   updated_at = NOW()
             WHERE transaction_id = %s
            """,
            ('rejected', json.dumps(meta, ensure_ascii=False), transaction_id),
        )

        conn.commit()

        return jsonify({
            'success': True,
            'transaction_id': transaction_id
        }), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'error': f'거래 거절 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 포인트 차감 (주문 결제용)
@app.route('/api/points/deduct', methods=['POST'])
def deduct_points():
    """포인트 차감 (주문 결제)"""
    conn = None
    cursor = None

    try:
        data = request.get_json()
        raw_user_id = data.get('user_id')
        amount = data.get('amount')  # 차감할 포인트
        order_id = data.get('order_id')  # 주문 ID (선택사항)

        if raw_user_id is None or amount is None:
            return jsonify({'error': 'user_id와 amount는 필수입니다.'}), 400

        try:
            amount_decimal = to_decimal(amount)
        except Exception:
            return jsonify({'error': 'amount는 숫자여야 합니다.'}), 400

        if amount_decimal <= 0:
            return jsonify({'error': '차감할 포인트는 0보다 커야 합니다.'}), 400

        identifier = parse_user_identifier(raw_user_id)

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        user = ensure_user_record(cursor, identifier)
        wallet = ensure_wallet_record(cursor, user['user_id'])

        cursor.execute(
            """
            UPDATE wallets
               SET balance = balance - %s,
                   updated_at = NOW()
             WHERE wallet_id = %s
               AND balance >= %s
            RETURNING balance
            """,
            (amount_decimal, wallet['wallet_id'], amount_decimal)
        )
        result = cursor.fetchone()
        if not result:
            conn.rollback()
            return jsonify({'error': '포인트가 부족합니다.'}), 400

        cursor.execute(
            """
            INSERT INTO wallet_transactions (
                wallet_id, type, amount, status, meta_json, locked, created_at, updated_at
            )
            VALUES (%s, 'order_debit', %s, 'approved', %s, FALSE, NOW(), NOW())
            RETURNING transaction_id
            """,
            (
                wallet['wallet_id'],
                amount_decimal,
                json.dumps({
                    'order_id': order_id,
                    'reason': 'order_payment'
                }, ensure_ascii=False)
            )
        )
        transaction = cursor.fetchone()

        conn.commit()

        return jsonify({
            'message': '포인트가 성공적으로 차감되었습니다.',
            'remaining_points': decimal_to_float(result['balance']),
            'deducted_amount': float(amount_decimal),
            'transaction_id': transaction['transaction_id']
        }), 200

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ 포인트 차감 실패: {e}")
        return jsonify({'error': f'포인트 차감 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
# 사용자 정보 조회
@app.route('/api/users/<path:raw_user_id>', methods=['GET'])
def get_user(raw_user_id):
    """사용자 정보 조회 (없으면 자동 생성 후 반환)"""
    conn = None
    cursor = None

    try:
        identifier = parse_user_identifier(str(raw_user_id).rstrip('/'))

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        user = ensure_user_record(cursor, identifier)
        wallet = ensure_wallet_record(cursor, user['user_id'])

        cursor.execute(
            """
            SELECT transaction_id,
                   amount,
                   status,
                   created_at,
                   meta_json
              FROM wallet_transactions
             WHERE wallet_id = %s
               AND type = 'topup'
             ORDER BY created_at DESC
            """,
            (wallet['wallet_id'],)
        )
        rows = cursor.fetchall()

        conn.commit()
        conn.close()

        balance = decimal_to_float(wallet['balance']) if wallet else 0.0

        return jsonify({
            'user_id': user['user_id'],
            'external_uid': user['external_uid'],
            'email': user['email'],
            'username': user['username'],
            'referral_code': user['referral_code'],
            'referral_status': user['referral_status'],
            'is_admin': bool(user['is_admin']) if user.get('is_admin') is not None else False,
            'created_at': to_isoformat_or_none(user['created_at']),
            'updated_at': to_isoformat_or_none(user['updated_at']),
            'wallet_balance': balance,
            'purchase_history': [
                {
                    'id': row['transaction_id'],
                    'amount': float(row['amount']) if row['amount'] is not None else 0.0,
                    'status': row['status'],
                    'created_at': to_isoformat_or_none(row['created_at']),
                    'meta': json.loads(row['meta_json']) if row['meta_json'] else {}
                }
                for row in rows
            ]
        }), 200

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ 사용자 정보 조회 실패: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'사용자 정보 조회 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
# 추천인 코드로 쿠폰 발급
@app.route('/api/referral/issue-coupon', methods=['POST'])
def issue_referral_coupon():
    """추천인 코드로 5% 할인 쿠폰 발급"""
    conn = None
    cursor = None
    try:
        data = request.get_json() or {}
        print(f"🔍 쿠폰 발급 요청 데이터: {data}")

        raw_user_id = data.get('user_id')
        referral_code = data.get('referral_code')

        if not raw_user_id or not referral_code:
            print(f"❌ 쿠폰 발급 필수 필드 누락 - user_id: {raw_user_id}, referral_code: {referral_code}")
            return jsonify({'error': 'user_id와 referral_code가 필요합니다.'}), 400

        identifier = parse_user_identifier(raw_user_id)

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        user = ensure_user_record(cursor, identifier)
        if not user:
            return jsonify({'error': '사용자 정보를 찾을 수 없습니다.'}), 404

        referrer = fetch_user_by_referral_code(cursor, referral_code)
        if not referrer:
            print(f"❌ 유효하지 않은 추천인 코드: {referral_code}")
            return jsonify({'error': '유효하지 않은 추천인 코드입니다.'}), 400

        if referrer['user_id'] == user['user_id']:
            return jsonify({'error': '본인 추천 코드는 사용할 수 없습니다.'}), 400

        # 추천인 연결 생성 또는 갱신
        cursor.execute(
            """
            SELECT referral_id, status
              FROM referrals
             WHERE referrer_user_id = %s
               AND referred_user_id = %s
             ORDER BY referral_id DESC
             LIMIT 1
            """,
            (referrer['user_id'], user['user_id'])
        )
        referral_row = cursor.fetchone()

        if referral_row:
            referral_id = referral_row['referral_id']
            if referral_row['status'] != 'approved':
                cursor.execute(
                    """
                    UPDATE referrals
                       SET status = 'approved'
                     WHERE referral_id = %s
                    """,
                    (referral_id,)
                )
        else:
            cursor.execute(
                """
                INSERT INTO referrals (referrer_user_id, referred_user_id, status, created_at)
                VALUES (%s, %s, 'approved', NOW())
                RETURNING referral_id
                """,
                (referrer['user_id'], user['user_id'])
            )
            referral_id = cursor.fetchone()['referral_id']

        # 사용자 Referral 상태 갱신
        cursor.execute(
            """
            UPDATE users
               SET referral_status = 'approved',
                   updated_at = NOW()
             WHERE user_id = %s
            """,
            (user['user_id'],)
        )

        # 이미 활성화된 추천인 쿠폰이 있는지 확인
        cursor.execute(
            """
            SELECT 1
              FROM user_coupons uc
              JOIN coupons c ON uc.coupon_id = c.coupon_id
             WHERE uc.user_id = %s
               AND c.coupon_name = %s
               AND uc.status = 'active'
            """,
            (user['user_id'], 'Referral 5% Discount')
        )
        if cursor.fetchone():
            conn.commit()
            return jsonify({
                'success': True,
                'message': '이미 발급된 추천인 쿠폰이 존재합니다.'
            }), 200

        valid_until = datetime.now() + timedelta(days=30)
        coupon_code = f"REF-{referrer['referral_code']}-{user['user_id']}-{int(time.time())}"

        cursor.execute(
            """
            INSERT INTO coupons (
                coupon_code,
                coupon_name,
                discount_type,
                discount_value,
                min_order_amount,
                valid_from,
                valid_until,
                created_at,
                updated_at
            )
            VALUES (%s, %s, 'percentage', %s, NULL, NOW(), %s, NOW(), NOW())
            RETURNING coupon_id
            """,
            (coupon_code, 'Referral 5% Discount', Decimal('5.0'), valid_until)
        )
        coupon_id = cursor.fetchone()['coupon_id']

        cursor.execute(
            """
            INSERT INTO user_coupons (
                user_id,
                coupon_id,
                issued_at,
                status,
                created_at,
                updated_at
            )
            VALUES (%s, %s, NOW(), 'active', NOW(), NOW())
            RETURNING user_coupon_id
            """,
            (user['user_id'], coupon_id)
        )
        user_coupon_id = cursor.fetchone()['user_coupon_id']

        conn.commit()

        return jsonify({
            'success': True,
            'message': '5% 할인 쿠폰이 발급되었습니다!',
            'coupon_code': coupon_code,
            'coupon_id': coupon_id,
            'user_coupon_id': user_coupon_id,
            'referral': {
                'referral_id': referral_id,
                'referrer_user_id': referrer['user_id']
            },
            'discount': 5.0,
            'expires_at': valid_until.isoformat()
        }), 200

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ 쿠폰 발급 실패: {e}")
        return jsonify({'error': f'쿠폰 발급 실패: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
# 추천인 코드 검증
@app.route('/api/referral/validate-code', methods=['GET'])
def validate_referral_code():
    """추천인 코드 유효성 검증"""
    try:
        code = request.args.get('code')
        if not code:
            return jsonify({'valid': False, 'error': '코드가 필요합니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(
            f"SELECT {USER_SELECT_COLUMNS} FROM users WHERE referral_code = %s",
            (code,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return jsonify({'valid': True, 'code': code}), 200
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
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(
            """
            SELECT uc.user_coupon_id,
                   c.coupon_code,
                   c.coupon_name,
                   c.discount_type,
                   c.discount_value,
                   uc.status,
                   uc.issued_at,
                   uc.used_at,
                   c.valid_from,
                   c.valid_until
              FROM user_coupons uc
              JOIN coupons c ON uc.coupon_id = c.coupon_id
             WHERE uc.user_id = %s
             ORDER BY uc.created_at DESC
            """,
            (user_id,)
        )
        
        coupons = []
        for row in cursor.fetchall():
            coupons.append({
                'user_coupon_id': row['user_coupon_id'],
                'coupon_code': row['coupon_code'],
                'coupon_name': row['coupon_name'],
                'discount_type': row['discount_type'],
                'discount_value': float(row['discount_value']) if row['discount_value'] is not None else 0.0,
                'status': row['status'],
                'issued_at': row['issued_at'].isoformat() if row['issued_at'] else None,
                'used_at': row['used_at'].isoformat() if row['used_at'] else None,
                'valid_from': row['valid_from'].isoformat() if row['valid_from'] else None,
                'valid_until': row['valid_until'].isoformat() if row['valid_until'] else None
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
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT 
                u.user_id,
                u.email,
                u.username,
                u.referral_code,
                COUNT(DISTINCT r.referral_id) FILTER (WHERE r.status = 'approved') AS referral_count,
                COALESCE(SUM(c.amount), 0) AS total_commission,
                COALESCE(SUM(CASE WHEN c.status = 'accrued' THEN c.amount ELSE 0 END), 0) AS pending_commission,
                COALESCE(SUM(CASE WHEN c.status = 'paid_out' THEN c.amount ELSE 0 END), 0) AS paid_commission,
                COALESCE(SUM(CASE 
                    WHEN DATE_TRUNC('month', c.created_at) = DATE_TRUNC('month', NOW()) 
                    THEN c.amount 
                    ELSE 0 
                END), 0) AS this_month_commission
            FROM users u
            LEFT JOIN referrals r ON u.user_id = r.referrer_user_id
            LEFT JOIN commissions c ON r.referral_id = c.referral_id
            WHERE u.referral_code IS NOT NULL
            GROUP BY u.user_id
            ORDER BY total_commission DESC
            """
        )
        overview_rows = cursor.fetchall()

        cursor.execute(
            """
            SELECT 
                COUNT(DISTINCT u.user_id) FILTER (WHERE u.referral_code IS NOT NULL) AS total_referrers,
                COUNT(DISTINCT r.referred_user_id) FILTER (WHERE r.status = 'approved') AS total_referrals,
                COALESCE(SUM(c.amount), 0) AS total_commissions,
                COALESCE(SUM(CASE 
                    WHEN DATE_TRUNC('month', c.created_at) = DATE_TRUNC('month', NOW()) 
                    THEN c.amount 
                    ELSE 0 
                END), 0) AS this_month_commissions,
                COALESCE(SUM(CASE WHEN c.status = 'accrued' THEN c.amount ELSE 0 END), 0) AS pending_commissions,
                COALESCE(SUM(CASE WHEN c.status = 'paid_out' THEN c.amount ELSE 0 END), 0) AS paid_commissions
            FROM users u
            LEFT JOIN referrals r ON u.user_id = r.referrer_user_id
            LEFT JOIN commissions c ON r.referral_id = c.referral_id
            """
        )
        stats_row = cursor.fetchone() or {}

        cursor.close()
        conn.close()

        overview_data = []
        for row in overview_rows:
            overview_data.append({
                'referrer_user_id': row['user_id'],
                'referrer_email': row['email'],
                'referrer_name': row.get('username'),
                'referral_code': row.get('referral_code'),
                'referral_count': int(row.get('referral_count') or 0),
                'total_commission': float(row.get('total_commission') or 0),
                'pending_commission': float(row.get('pending_commission') or 0),
                'paid_commission': float(row.get('paid_commission') or 0),
                'this_month_commission': float(row.get('this_month_commission') or 0)
            })

        total_stats = {
            'total_referrers': int(stats_row.get('total_referrers') or 0),
            'total_referrals': int(stats_row.get('total_referrals') or 0),
            'total_commissions': float(stats_row.get('total_commissions') or 0),
            'pending_commissions': float(stats_row.get('pending_commissions') or 0),
            'paid_commissions': float(stats_row.get('paid_commissions') or 0),
            'this_month_commissions': float(stats_row.get('this_month_commissions') or 0)
        }

        return jsonify({'overview': overview_data, 'stats': total_stats}), 200
        
    except Exception as e:
        return jsonify({'error': f'커미션 현황 조회 실패: {str(e)}'}), 500
# 관리자용 커미션 환급 처리
@app.route('/api/admin/referral/pay-commission', methods=['POST'])
def pay_commission():
    """관리자용 커미션 환급 처리"""
    try:
        data = request.get_json() or {}
        print(f"🔍 커미션 환급 요청 데이터: {data}")

        commission_ids = data.get('commission_ids') or data.get('commissionIds')
        bank_name = data.get('bank_name') or data.get('bankName')
        account_number = data.get('account_number') or data.get('accountNumber')
        payment_method = data.get('payment_method', 'bank_transfer')
        notes = data.get('notes', '')

        if not commission_ids or not isinstance(commission_ids, list):
            return jsonify({'error': 'commission_ids 배열이 필요합니다.'}), 400

        try:
            commission_ids = [int(cid) for cid in commission_ids]
        except (TypeError, ValueError):
            return jsonify({'error': 'commission_ids는 정수 배열이어야 합니다.'}), 400

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT 
                c.commission_id,
                c.amount,
                c.status,
                r.referral_id,
                r.referrer_user_id,
                r.referred_user_id
            FROM commissions c
            JOIN referrals r ON c.referral_id = r.referral_id
            WHERE c.commission_id = ANY(%s)
            FOR UPDATE
            """,
            (commission_ids,)
        )
        rows = cursor.fetchall()
        if not rows or len(rows) != len(commission_ids):
            cursor.close()
            conn.close()
            return jsonify({'error': '일부 커미션을 찾을 수 없습니다.'}), 404

        referrer_user_id = rows[0]['referrer_user_id']
        if any(row['referrer_user_id'] != referrer_user_id for row in rows):
            cursor.close()
            conn.close()
            return jsonify({'error': '서로 다른 추천인의 커미션을 동시에 처리할 수 없습니다.'}), 400

        invalid = [row['commission_id'] for row in rows if row['status'] != 'accrued']
        if invalid:
            cursor.close()
            conn.close()
            return jsonify({'error': f'이미 처리된 커미션이 포함되어 있습니다: {invalid}'}), 400

        total_amount = sum(row['amount'] for row in rows)
        if total_amount <= 0:
            cursor.close()
            conn.close()
            return jsonify({'error': '커미션 금액이 0 이하입니다.'}), 400

        if not bank_name or not account_number:
            cursor.close()
            conn.close()
            return jsonify({'error': 'bank_name과 account_number가 필요합니다.'}), 400

        cursor.execute(
            """
            INSERT INTO payout_requests (
                user_id,
                amount,
                bank_name,
                account_number,
                status,
                requested_at,
                processed_at
            )
            VALUES (%s, %s, %s, %s, 'approved', NOW(), NOW())
            RETURNING request_id
            """,
            (referrer_user_id, total_amount, bank_name, account_number)
        )
        request_id = cursor.fetchone()['request_id']

        cursor.execute(
            """
            INSERT INTO payouts (
                request_id,
                paid_amount,
                status,
                processed_at
            )
            VALUES (%s, %s, 'paid', NOW())
            RETURNING payout_id
            """,
            (request_id, total_amount)
        )
        payout_id = cursor.fetchone()['payout_id']

        cursor.executemany(
            """
            INSERT INTO payout_commissions (payout_id, commission_id, amount_paid, created_at)
            VALUES (%s, %s, %s, NOW())
            """,
            [(payout_id, row['commission_id'], row['amount']) for row in rows]
        )

        cursor.executemany(
            """
            UPDATE commissions
               SET status = 'paid_out',
                   paid_amount = %s,
                   paid_out_at = NOW()
             WHERE commission_id = %s
            """,
            [(row['amount'], row['commission_id']) for row in rows]
        )

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'payout_id': payout_id,
            'request_id': request_id,
            'referrer_user_id': referrer_user_id,
            'commission_ids': commission_ids,
            'total_amount': float(total_amount),
            'payment_method': payment_method,
            'notes': notes
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
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(
            """
            SELECT 
                p.payout_id,
                pr.request_id,
                pr.user_id,
                pr.amount,
                pr.bank_name,
                pr.account_number,
                pr.status AS request_status,
                pr.requested_at,
                pr.processed_at,
                p.paid_amount,
                p.status AS payout_status,
                p.processed_at AS paid_at,
                u.email,
                u.username
            FROM payouts p
            JOIN payout_requests pr ON p.request_id = pr.request_id
            LEFT JOIN users u ON pr.user_id = u.user_id
            ORDER BY p.processed_at DESC
            """
        )
        payments = []
        for row in cursor.fetchall():
            payments.append({
                'payout_id': row['payout_id'],
                'request_id': row['request_id'],
                'user_id': row['user_id'],
                'email': row.get('email'),
                'name': row.get('username'),
                'amount': float(row['paid_amount']) if row.get('paid_amount') is not None else 0.0,
                'bank_name': row.get('bank_name'),
                'account_number': row.get('account_number'),
                'request_status': row.get('request_status'),
                'payout_status': row.get('payout_status'),
                'requested_at': row['requested_at'].isoformat() if row.get('requested_at') else None,
                'processed_at': row['processed_at'].isoformat() if row.get('processed_at') else None,
                'paid_at': row['paid_at'].isoformat() if row.get('paid_at') else None
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
        raw_user_id = request.args.get('user_id')
        if not raw_user_id:
            return jsonify({'error': 'user_id가 필요합니다.'}), 400

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        identifier = parse_user_identifier(raw_user_id)
        user = ensure_user_record(cursor, identifier)
        if not user:
            cursor.close()
            conn.close()
            return jsonify({'error': '사용자를 찾을 수 없습니다.'}), 404

        cursor.execute(
            """
            SELECT 
                COUNT(*) FILTER (WHERE r.status = 'approved') AS total_referrals,
                COUNT(*) FILTER (
                    WHERE r.status = 'approved'
                      AND DATE_TRUNC('month', r.created_at) = DATE_TRUNC('month', NOW())
                ) AS this_month_referrals
            FROM referrals r
            WHERE r.referrer_user_id = %s
            """,
            (user['user_id'],)
        )
        referral_row = cursor.fetchone() or {}

        cursor.execute(
            """
            SELECT 
                COALESCE(SUM(c.amount), 0) AS total_commission,
                COALESCE(SUM(CASE WHEN c.status = 'accrued' THEN c.amount ELSE 0 END), 0) AS pending_commission,
                COALESCE(SUM(CASE WHEN c.status = 'paid_out' THEN c.amount ELSE 0 END), 0) AS paid_commission,
                COALESCE(SUM(CASE 
                    WHEN DATE_TRUNC('month', c.created_at) = DATE_TRUNC('month', NOW()) 
                    THEN c.amount 
                    ELSE 0 
                END), 0) AS this_month_commission
            FROM commissions c
            JOIN referrals r ON c.referral_id = r.referral_id
            WHERE r.referrer_user_id = %s
            """,
            (user['user_id'],)
        )
        commission_row = cursor.fetchone() or {}

        cursor.close()
        conn.close()

        return jsonify({
            'totalReferrals': int(referral_row.get('total_referrals') or 0),
            'activeReferrals': int(referral_row.get('total_referrals') or 0),
            'thisMonthReferrals': int(referral_row.get('this_month_referrals') or 0),
            'totalCommission': float(commission_row.get('total_commission') or 0),
            'pendingCommission': float(commission_row.get('pending_commission') or 0),
            'paidCommission': float(commission_row.get('paid_commission') or 0),
            'thisMonthCommission': float(commission_row.get('this_month_commission') or 0)
        }), 200

    except Exception as e:
        return jsonify({'error': f'통계 조회 실패: {str(e)}'}), 500
# 사용자용 추천인 목록 조회 (피추천인 목록)
@app.route('/api/referral/referrals', methods=['GET'])
def get_user_referrals():
    """사용자용 추천인 목록 조회 (내가 추천한 사용자들)"""
    raw_user_id = request.args.get('user_id')
    if not raw_user_id:
        return jsonify({'error': 'user_id가 필요합니다.'}), 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        identifier = parse_user_identifier(raw_user_id)
        user = ensure_user_record(cursor, identifier)
        if not user:
            cursor.close()
            conn.close()
            return jsonify({'error': '사용자를 찾을 수 없습니다.'}), 404

        cursor.execute(
            """
            SELECT r.referral_id,
                   r.referred_user_id,
                   r.status,
                   r.created_at,
                   u.email,
                   u.username
              FROM referrals r
              LEFT JOIN users u ON r.referred_user_id = u.user_id
             WHERE r.referrer_user_id = %s
             ORDER BY r.created_at DESC
            """,
            (user['user_id'],)
        )

        referrals = []
        for row in cursor.fetchall():
            join_date = row['created_at'].strftime('%Y-%m-%d') if row.get('created_at') and hasattr(row.get('created_at'), 'strftime') else (
                row['created_at'].isoformat()[:10] if row.get('created_at') else None
            )
            referrals.append({
                'referral_id': row['referral_id'],
                'referred_user_id': row['referred_user_id'],
                'email': row.get('email'),
                'username': row.get('username'),
                'status': row.get('status'),
                'joined_at': join_date
            })

        cursor.close()
        conn.close()

        return jsonify({'referrals': referrals, 'count': len(referrals)}), 200

    except Exception as e:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print(f"❌ 피추천인 목록 조회 실패: {e}")
        return jsonify({'error': f'추천인 목록 조회 실패: {str(e)}'}), 500
# 관리자용 추천인 등록
@app.route('/api/admin/referral/register', methods=['POST'])
def admin_register_referral():
    """관리자용 추천인 등록"""
    try:
        data = request.get_json()
        print(f"🔍 관리자 추천인 등록 요청 데이터: {data}")
        
        # 다양한 필드명 지원
        email = data.get('email') or data.get('user_email')
        name = data.get('name') or data.get('username')
        phone = data.get('phone')
        
        print(f"🔍 파싱된 필드 - email: {email}, name: {name}, phone: {phone}")
        
        if not email:
            print(f"❌ 이메일 필수 필드 누락: {email}")
            return jsonify({'error': '이메일은 필수입니다.'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        user = get_user_by_email(cursor, email)

        if user:
            updated_name = name or user.get('username')
            cursor.execute(
                """
                UPDATE users
                   SET username = %s,
                       phone = %s,
                       updated_at = NOW()
                 WHERE user_id = %s
                RETURNING user_id, email, username, phone, referral_code, referral_status, created_at
                """,
                (updated_name, phone, user['user_id'])
            )
            user = cursor.fetchone()
        else:
            referral_code = generate_unique_referral_code(cursor)
            cursor.execute(
                """
                INSERT INTO users (email, username, phone, referral_code, referral_status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING user_id, email, username, phone, referral_code, referral_status, created_at
                """,
                (email, name, phone, referral_code, 'approved')
            )
            user = cursor.fetchone()

        if not user.get('referral_code'):
            referral_code = generate_unique_referral_code(cursor)
            cursor.execute(
                """
                UPDATE users
                   SET referral_code = %s,
                       referral_status = 'approved',
                       updated_at = NOW()
                 WHERE user_id = %s
                RETURNING user_id, email, username, phone, referral_code, referral_status, created_at
                """,
                (referral_code, user['user_id'])
            )
            user = cursor.fetchone()

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            'user_id': user['user_id'],
            'email': user['email'],
            'name': user.get('username'),
            'phone': user.get('phone'),
            'referralCode': user.get('referral_code'),
            'status': user.get('referral_status'),
            'created_at': user.get('created_at').isoformat() if user.get('created_at') else None
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'추천인 등록 실패: {str(e)}'}), 500

# 관리자용 추천인 목록 조회
@app.route('/api/admin/referral/list', methods=['GET'])
def admin_get_referrals():
    """관리자용 추천인 목록 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT 
                u.user_id,
                u.email,
                u.username,
                u.phone,
                u.referral_code,
                u.referral_status,
                u.created_at,
                COALESCE(COUNT(r.referral_id) FILTER (WHERE r.status = 'approved'), 0) AS referral_count,
                COALESCE(SUM(c.amount), 0) AS total_commission,
                COALESCE(SUM(CASE WHEN c.status = 'accrued' THEN c.amount ELSE 0 END), 0) AS pending_commission,
                COALESCE(SUM(CASE WHEN c.status = 'paid_out' THEN c.amount ELSE 0 END), 0) AS paid_commission
            FROM users u
            LEFT JOIN referrals r ON u.user_id = r.referrer_user_id
            LEFT JOIN commissions c ON r.referral_id = c.referral_id
            WHERE u.referral_code IS NOT NULL
            GROUP BY u.user_id, u.email, u.username, u.phone, u.referral_code, u.referral_status, u.created_at
            ORDER BY u.created_at DESC
            """
        )

        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        referrals = []
        for row in rows:
            referrals.append({
                'user_id': row['user_id'],
                'email': row['email'],
                'name': row.get('username'),
                'phone': row.get('phone'),
                'referralCode': row.get('referral_code'),
                'status': row.get('referral_status') or 'approved',
                'joinDate': row['created_at'].strftime('%Y-%m-%d') if row.get('created_at') and hasattr(row.get('created_at'), 'strftime') else None,
                'referralCount': int(row.get('referral_count') or 0),
                'totalCommission': float(row.get('total_commission') or 0),
                'pendingCommission': float(row.get('pending_commission') or 0),
                'paidCommission': float(row.get('paid_commission') or 0)
            })

        return jsonify({'referrals': referrals, 'count': len(referrals)}), 200

    except Exception as e:
        return jsonify({'error': f'추천인 목록 조회 실패: {str(e)}'}), 500
# 관리자용 추천인 코드 목록 조회
@app.route('/api/admin/referral/codes', methods=['GET'])
def admin_get_referral_codes():
    """관리자용 추천인 코드 목록 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT 
                u.user_id,
                u.email,
                u.username,
                u.phone,
                u.referral_code,
                u.created_at,
                COUNT(r.referral_id) FILTER (WHERE r.status = 'approved') AS referral_count,
                COALESCE(SUM(c.amount), 0) AS total_commission,
                COALESCE(SUM(CASE WHEN c.status = 'accrued' THEN c.amount ELSE 0 END), 0) AS pending_commission
            FROM users u
            LEFT JOIN referrals r ON u.user_id = r.referrer_user_id
            LEFT JOIN commissions c ON r.referral_id = c.referral_id
            WHERE u.referral_code IS NOT NULL
            GROUP BY u.user_id
            ORDER BY u.created_at DESC
            """
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        codes = []
        for row in rows:
            codes.append({
                'user_id': row['user_id'],
                'referralCode': row['referral_code'],
                'email': row['email'],
                'name': row.get('username'),
                'phone': row.get('phone'),
                'createdAt': row['created_at'].isoformat() if row.get('created_at') else None,
                'usage_count': int(row.get('referral_count') or 0),
                'total_commission': float(row.get('total_commission') or 0),
                'pending_commission': float(row.get('pending_commission') or 0)
            })

        return jsonify({'codes': codes, 'count': len(codes)}), 200

    except Exception as e:
        return jsonify({'error': f'추천인 코드 목록 조회 실패: {str(e)}'}), 500

# 관리자용 커미션 내역 조회
@app.route('/api/admin/referral/commissions', methods=['GET'])
def admin_get_commissions():
    """관리자용 커미션 내역 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(
            """
            SELECT 
                c.commission_id,
                c.order_id,
                c.amount,
                c.status,
                c.created_at,
                c.paid_amount,
                c.paid_out_at,
                r.referral_id,
                r.referrer_user_id,
                r.referred_user_id,
                referrer.email AS referrer_email,
                referrer.username AS referrer_name,
                referred.email AS referred_email,
                referred.username AS referred_name,
                o.final_amount
            FROM commissions c
            JOIN referrals r ON c.referral_id = r.referral_id
            LEFT JOIN users referrer ON r.referrer_user_id = referrer.user_id
            LEFT JOIN users referred ON r.referred_user_id = referred.user_id
            LEFT JOIN orders o ON c.order_id = o.order_id
            ORDER BY c.created_at DESC
            """
        )
        commissions = []
        for row in cursor.fetchall():
            commissions.append({
                'commission_id': row['commission_id'],
                'order_id': row['order_id'],
                'referral_id': row['referral_id'],
                'referrer_user_id': row['referrer_user_id'],
                'referrer_email': row.get('referrer_email'),
                'referrer_name': row.get('referrer_name'),
                'referred_user_id': row['referred_user_id'],
                'referred_email': row.get('referred_email'),
                'referred_name': row.get('referred_name'),
                'order_amount': float(row['final_amount']) if row.get('final_amount') is not None else None,
                'commission_amount': float(row['amount']) if row.get('amount') is not None else 0.0,
                'status': row.get('status'),
                'created_at': row['created_at'].isoformat() if row.get('created_at') else None,
                'paid_amount': float(row['paid_amount']) if row.get('paid_amount') is not None else None,
                'paid_out_at': row['paid_out_at'].isoformat() if row.get('paid_out_at') else None
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

        identifier = parse_user_identifier(user_id)

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        user = ensure_user_record(cursor, identifier)
        wallet = ensure_wallet_record(cursor, user['user_id'])

        cursor.execute(
            """
            SELECT transaction_id,
                   amount,
                   status,
                   created_at,
                   meta_json
              FROM wallet_transactions
             WHERE wallet_id = %s
               AND type = 'topup'
             ORDER BY created_at DESC
            """,
            (wallet['wallet_id'],)
        )
        rows = cursor.fetchall()
        conn.commit()
        conn.close()

        purchases = []
        for row in rows:
            meta = {}
            if row.get('meta_json'):
                try:
                    meta = json.loads(row['meta_json'])
                except json.JSONDecodeError:
                    meta = {}

            purchases.append({
                'id': row['transaction_id'],
                'amount': float(row['amount']) if row['amount'] is not None else 0.0,
                'payment_amount': float(meta.get('payment_amount') or row['amount'] or 0),
                'status': row['status'],
                'created_at': to_isoformat_or_none(row['created_at']),
                'buyer_name': meta.get('buyer_name'),
                'bank_info': meta.get('bank_info'),
                'channel': meta.get('channel'),
                'memo': meta.get('memo')
            })

        return jsonify({'purchases': purchases}), 200

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
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        params = []
        conditions = []
        user_id = request.args.get('user_id')
        status = request.args.get('status')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = min(int(request.args.get('limit', 100)), 500)

        if user_id:
            conditions.append("o.user_id = %s")
            params.append(int(user_id))

        if status:
            conditions.append("o.status = %s")
            params.append(status)

        if start_date:
            conditions.append("o.created_at >= %s")
            params.append(start_date)

        if end_date:
            conditions.append("o.created_at <= %s")
            params.append(end_date)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ''

        cursor.execute(
            f"""
            SELECT 
                o.order_id,
                o.user_id,
                o.total_amount,
                o.discount_amount,
                o.final_amount,
                o.status,
                o.notes,
                o.created_at,
                o.updated_at,
                u.email,
                u.username
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.user_id
            {where_clause}
            ORDER BY o.created_at DESC
            LIMIT %s
            """,
            (*params, limit)
        )
        orders = cursor.fetchall()

        order_ids = [order['order_id'] for order in orders]
        items_map = {}
        commission_map = {}
        wallet_map = {}

        if order_ids:
            cursor.execute(
                """
                SELECT 
                    oi.order_id,
                    oi.order_item_id,
                    oi.variant_id,
                    oi.quantity,
                    oi.unit_price,
                    oi.line_amount,
                    oi.link,
                    pv.name AS variant_name
                FROM order_items oi
                LEFT JOIN product_variants pv ON oi.variant_id = pv.variant_id
                WHERE oi.order_id = ANY(%s)
                ORDER BY oi.order_item_id
                """,
                (order_ids,)
            )
            for row in cursor.fetchall():
                items_map.setdefault(row['order_id'], []).append(row)

            cursor.execute(
                """
                SELECT 
                    c.order_id,
                    c.commission_id,
                    c.amount,
                    c.status,
                    c.paid_amount,
                    c.paid_out_at
                FROM commissions c
                WHERE c.order_id = ANY(%s)
                """,
                (order_ids,)
            )
            for row in cursor.fetchall():
                commission_map.setdefault(row['order_id'], []).append(row)

            cursor.execute(
                """
                SELECT 
                    (wt.meta_json->>'order_id')::BIGINT AS order_id,
                    wt.transaction_id,
                    wt.amount,
                    wt.status,
                    wt.created_at
                FROM wallet_transactions wt
                WHERE wt.type = 'order_debit'
                  AND (wt.meta_json->>'order_id')::BIGINT = ANY(%s)
                """,
                (order_ids,)
            )
            for row in cursor.fetchall():
                if row.get('order_id'):
                    wallet_map.setdefault(row['order_id'], []).append(row)

        transactions = []
        for order in orders:
            notes = json.loads(order['notes']) if order.get('notes') else {}
            transactions.append({
                'order_id': order['order_id'],
                'user_id': order['user_id'],
                'email': order.get('email'),
                'username': order.get('username'),
                'total_amount': float(order['total_amount']) if order.get('total_amount') is not None else None,
                'discount_amount': float(order['discount_amount']) if order.get('discount_amount') is not None else None,
                'final_amount': float(order['final_amount']) if order.get('final_amount') is not None else None,
                'status': order.get('status'),
                'created_at': order['created_at'].isoformat() if order.get('created_at') else None,
                'updated_at': order['updated_at'].isoformat() if order.get('updated_at') else None,
                'items': items_map.get(order['order_id'], []),
                'commissions': commission_map.get(order['order_id'], []),
                'wallet_transactions': wallet_map.get(order['order_id'], []),
                'notes': notes
            })

        conn.close()
        return jsonify({
            'status': 'success',
            'transactions': transactions,
            'total': len(transactions)
        }), 200

    except Exception as e:
        if 'conn' in locals():
            conn.close()
        print(f"❌ 관리자 거래 내역 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e),
            'traceback': traceback.format_exc()
        }), 500