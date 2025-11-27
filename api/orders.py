"""
주문 관련 API
"""

from flask import Blueprint, request, jsonify
import os
import json
import time
import threading
from urllib.parse import urlparse
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# Blueprint 생성
orders = Blueprint("orders", __name__, url_prefix="/api/new/orders")

# 데이터베이스 연결 함수
def get_db_connection():
    """데이터베이스 연결을 가져옵니다."""
    DATABASE_URL = os.environ.get("DATABASE_URL")

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
            cursor_factory=RealDictCursor,
        )
        return conn
    except Exception as e:
        print(f"❌ 데이터베이스 연결 오류: {e}")
        raise


@orders.route("", methods=["POST"])
def create_order():
    """
    주문 생성 API
    ---
    tags:
      - Orders
    summary: 주문 생성
    description: "새로운 주문을 생성합니다"
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            user_id:
              type: integer
              required: true
            referrer_user_id:
              type: integer
            coupon_id:
              type: integer
            total_amount:
              type: number
              required: true
            discount_amount:
              type: number
            final_amount:
              type: number
            notes:
              type: string
            is_scheduled:
              type: boolean
            scheduled_datetime:
              type: string
            is_split_delivery:
              type: boolean
            split_days:
              type: integer
            split_quantity:
              type: integer
            detailed_service:
              type: string
            package_steps:
              type: array
            link:
              type: string
            quantity:
              type: integer
            order_items:
              type: array
              required: true
    responses:
      201:
        description: 주문 생성 성공
      400:
        description: 잘못된 요청
      500:
        description: 서버 오류
    """
    conn = None
    cursor = None

    try:
        data = request.get_json()

        # 필수 필드 검증
        if not data.get("user_id"):
            return jsonify({"error": "user_id는 필수입니다."}), 400

        if not data.get("order_items") or len(data.get("order_items", [])) == 0:
            return jsonify({"error": "order_items는 필수입니다."}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # orders 테이블에 주문 생성
        order_data = {
            "user_id": data["user_id"],
            "referrer_user_id": data.get("referrer_user_id"),
            "coupon_id": data.get("coupon_id"),
            "total_amount": data.get("total_amount", 0),
            "discount_amount": data.get("discount_amount", 0),
            "final_amount": data.get("final_amount")
            or data.get("total_amount", 0) - data.get("discount_amount", 0),
            "status": "pending",
            "notes": data.get("notes"),
            "is_scheduled": data.get("is_scheduled", False),
            "scheduled_datetime": data.get("scheduled_datetime"),
            "is_split_delivery": data.get("is_split_delivery", False),
            "split_days": data.get("split_days", 0),
            "split_quantity": data.get("split_quantity", 0),
            "detailed_service": data.get("detailed_service"),
            "package_steps": (
                json.dumps(data.get("package_steps"))
                if data.get("package_steps")
                else None
            ),
            "link": data.get("link"),
            "quantity": data.get("quantity", 0),
        }

        cursor.execute(
            """
            INSERT INTO orders (
                user_id, referrer_user_id, coupon_id,
                total_amount, discount_amount, final_amount,
                status, notes, is_scheduled, scheduled_datetime,
                is_split_delivery, split_days, split_quantity,
                detailed_service, package_steps, link, quantity
            ) VALUES (
                %(user_id)s, %(referrer_user_id)s, %(coupon_id)s,
                %(total_amount)s, %(discount_amount)s, %(final_amount)s,
                %(status)s, %(notes)s, %(is_scheduled)s, %(scheduled_datetime)s,
                %(is_split_delivery)s, %(split_days)s, %(split_quantity)s,
                %(detailed_service)s, %(package_steps)s::jsonb, %(link)s, %(quantity)s
            ) RETURNING order_id
        """,
            order_data,
        )

        order_result = cursor.fetchone()
        order_id = order_result["order_id"]

        # order_items 테이블에 주문 아이템들 생성
        order_items = data.get("order_items", [])
        for item in order_items:
            item_data = {
                "order_id": order_id,
                "variant_id": item.get("variant_id"),
                "quantity": item.get("quantity", 0),
                "unit_price": item.get("unit_price", 0),
                "line_amount": item.get("line_amount")
                or (item.get("unit_price", 0) * item.get("quantity", 0)),
                "link": item.get("link") or data.get("link"),
                "status": "pending",
                "package_id": item.get("package_id"),
                "package_item_id": item.get("package_item_id"),
            }

            cursor.execute(
                """
                INSERT INTO order_items (
                    order_id, variant_id, quantity, unit_price,
                    line_amount, link, status, package_id, package_item_id
                ) VALUES (
                    %(order_id)s, %(variant_id)s, %(quantity)s, %(unit_price)s,
                    %(line_amount)s, %(link)s, %(status)s, %(package_id)s, %(package_item_id)s
                ) RETURNING order_item_id
            """,
                item_data,
            )

        conn.commit()

        return (
            jsonify(
                {
                    "success": True,
                    "order_id": order_id,
                    "message": "주문이 생성되었습니다.",
                }
            ),
            201,
        )

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ 주문 생성 오류: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": f"주문 생성 실패: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@orders.route("/<int:order_id>", methods=["GET"])
def get_order(order_id):
    """
    주문 조회 API
    ---
    tags:
      - Orders
    summary: 주문 조회
    description: "특정 주문의 상세 정보를 조회합니다"
    parameters:
      - name: order_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: 성공
      404:
        description: 주문을 찾을 수 없음
    """
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 주문 정보 조회
        cursor.execute(
            """
            SELECT * FROM orders WHERE order_id = %s
        """,
            (order_id,),
        )

        order = cursor.fetchone()

        if not order:
            return jsonify({"error": "주문을 찾을 수 없습니다."}), 404

        # 주문 아이템 조회
        cursor.execute(
            """
            SELECT * FROM order_items WHERE order_id = %s
            ORDER BY order_item_id ASC
        """,
            (order_id,),
        )

        items = cursor.fetchall()

        order_dict = dict(order)
        order_dict["order_items"] = [dict(item) for item in items]

        return jsonify({"order": order_dict}), 200

    except Exception as e:
        print(f"❌ 주문 조회 오류: {e}")
        return jsonify({"error": f"주문 조회 실패: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def check_smm_service(service_id, link, quantity, comments, runs, interval):
    from backend import get_smm_services
    data = ""
    smm_services = get_smm_services(service_id=service_id)
    smm_service_result = smm_services.get("exists")

    if smm_service_result:
        from backend import call_smm_panel_api
        smm_result = call_smm_panel_api(
            {
                "service": service_id,
                "link": link,
                "quantity": quantity,
                "comments": data.get("comments", ""),
                "runs": data.get(
                    "runs", 1
                ),  # Drip-feed: 30일간 하루에 1번씩 → runs: 30, interval: 1440
                "interval": data.get("interval", 0),  # interval 단위: 분 (1440 = 24시간)
            }
        )
    
    else:
        
        return jsonify({"error": "서비스를 찾을 수 없습니다."}), 404
    print(f"SMM Panel API 요청: {smm_result}")
    return smm_result


# ==================== Helper Functions ====================

def get_database_url():
    """Get DATABASE_URL from environment"""
    return os.environ.get("DATABASE_URL")


def is_postgresql():
    """Check if using PostgreSQL database"""
    db_url = get_database_url()
    return db_url and db_url.startswith("postgresql://")


def validate_order_data(data):
    """Validate required order fields"""
    required_fields = ["user_id", "service_id", "link", "quantity"]
    missing = [field for field in required_fields if not data.get(field)]
    
    # Check for price or total_price
    if not data.get("price") and not data.get("total_price"):
        missing.append("price or total_price")
    
    if missing:
        return False, f"필수 필드가 누락되었습니다: {', '.join(missing)}"
    return True, None


def get_db_user_id(cursor, external_uid):
    """Convert external_uid to internal user_id"""
    if not is_postgresql():
        return external_uid
    
    try:
        cursor.execute("""
            SELECT user_id FROM users 
            WHERE external_uid = %s OR email = %s 
            LIMIT 1
        """, (external_uid, external_uid))
        result = cursor.fetchone()
        return result[0] if result else external_uid
    except Exception as e:
        print(f"⚠️ 사용자 ID 변환 오류: {e}")
        return external_uid


def get_referral_info(cursor, user_id):
    """Get referral information for user"""
    if not is_postgresql():
        cursor.execute("""
            SELECT referral_code, referrer_email 
            FROM user_referral_connections 
            WHERE user_id = ?
        """, (user_id,))
        result = cursor.fetchone()
        return result if result else None
    
    cursor.execute("""
        SELECT r.referral_id, r.referrer_user_id, u.email, u.referral_code
        FROM referrals r
        JOIN users u ON r.referrer_user_id = u.user_id
        WHERE r.referred_user_id = (SELECT user_id FROM users WHERE external_uid = %s OR email = %s LIMIT 1)
        AND r.status = 'approved'
        ORDER BY r.created_at DESC
        LIMIT 1
    """, (user_id, user_id))
    return cursor.fetchone()


def process_coupon(cursor, user_id, coupon_id, price):
    """Process coupon and calculate discount"""
    if not coupon_id:
        return None, 0, price

    db_user_id = get_db_user_id(cursor, user_id)

    if is_postgresql():
        cursor.execute("""
            SELECT uc.user_coupon_id, c.discount_value, c.discount_type
            FROM user_coupons uc
            JOIN coupons c ON uc.coupon_id = c.coupon_id
            WHERE uc.user_coupon_id = %s 
            AND uc.user_id = %s
            AND uc.status = 'active'
            AND (c.valid_until IS NULL OR c.valid_until > NOW())
        """, (coupon_id, db_user_id))
        result = cursor.fetchone()

        if result:
            user_coupon_id, discount_value, discount_type = result
            discount = price * (float(discount_value) / 100) if discount_type == 'percentage' else float(discount_value)
            final_price = price - discount

            cursor.execute(
                """
                UPDATE user_coupons 
                SET status = 'used', used_at = NOW() 
                WHERE user_coupon_id = %s
            """,
                (user_coupon_id,),
            )

            return user_coupon_id, discount, final_price

    return None, 0, price


def get_variant_id(cursor, service_id):
    """Get variant_id from service_id"""
    if not is_postgresql() or not service_id:
        return None, 0
    
    try:
        if str(service_id).isdigit():
            cursor.execute("""
                SELECT variant_id, price 
                FROM product_variants 
                WHERE (meta_json->>'service_id')::text = %s 
                   OR (meta_json->>'smm_service_id')::text = %s
                LIMIT 1
            """, (str(service_id), str(service_id)))
            result = cursor.fetchone()
            if result:
                return result[0], float(result[1]) if result[1] else 0
    except Exception as e:
        print(f"⚠️ variant_id 조회 오류: {e}")
    
    return None, 0


def call_smm_api(service_id, link, quantity, comments, runs, interval):
    """Call SMM Panel API for order"""
    from backend import call_smm_panel_api
    try:
        result = call_smm_panel_api({
            "service": service_id,
            "link": link,
            "quantity": quantity,
            "comments": comments or "",
            "runs": runs or 1,
            "interval": interval or 0
        })
        return result.get("status") == "success", result.get("order"), result.get("message")
    except Exception as e:
        print(f"❌ SMM Panel API 오류: {e}")
        return False, None, str(e)


def create_order_record(cursor, order_data):
    """Create order record in database"""
    if is_postgresql():
        cursor.execute("""
            INSERT INTO orders (
                order_id, user_id, total_amount, discount_amount, final_amount,
                link, quantity, status, created_at, updated_at,
                is_scheduled, scheduled_datetime, is_split_delivery, 
                split_days, split_quantity, smm_panel_order_id, 
                detailed_service, referrer_user_id, coupon_id
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(),
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) RETURNING order_id
        """, (
            order_data["order_id"],
            order_data["user_id"],
            order_data["total_amount"],
            order_data["discount_amount"],
            order_data["final_amount"],
            order_data["link"],
            order_data["quantity"],
            order_data["status"],
            order_data["is_scheduled"],
            order_data["scheduled_datetime"],
            order_data["is_split_delivery"],
            order_data["split_days"],
            order_data["split_quantity"],
            order_data["smm_panel_order_id"],
            order_data["detailed_service"],
            order_data.get("referrer_user_id"),
            order_data.get("coupon_id")
        ))
        return cursor.fetchone()[0]
    else:
        cursor.execute("""
            INSERT INTO orders (
                order_id, user_id, service_id, link, quantity, price,
                discount_amount, referral_code, status, created_at, updated_at,
                is_scheduled, scheduled_datetime, is_split_delivery,
                split_days, split_quantity, smm_panel_order_id, detailed_service
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                      ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_data["order_id"],
            order_data["user_id"],
            order_data["service_id"],
            order_data["link"],
            order_data["quantity"],
            order_data["final_amount"],
            order_data["discount_amount"],
            order_data.get("referral_code"),
            order_data["status"],
            order_data["is_scheduled"],
            order_data["scheduled_datetime"],
            order_data["is_split_delivery"],
            order_data["split_days"],
            order_data["split_quantity"],
            order_data["smm_panel_order_id"],
            order_data["detailed_service"]
        ))
        return order_data["order_id"]


def create_order_items(cursor, order_id, order_type, data, variant_id, unit_price, link, quantity, final_price):
    """Create order items for order"""
    if not is_postgresql():
        return
    
    package_steps = data.get("package_steps", [])
    is_package = len(package_steps) > 0
    
    if is_package and package_steps:
        for step_idx, step in enumerate(package_steps, 1):
            step_service_id = step.get("id") or step.get("service_id")
            step_quantity = step.get("quantity", 0)
            step_variant_id, step_unit_price = get_variant_id(cursor, step_service_id)
            step_line_amount = step_unit_price * step_quantity if step_unit_price > 0 else 0
            
            cursor.execute("""
                INSERT INTO order_items (
                    order_id, variant_id, quantity, unit_price, 
                    line_amount, link, status, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, 'pending', NOW(), NOW())
                RETURNING order_item_id
            """, (order_id, step_variant_id, step_quantity, step_unit_price, step_line_amount, link))
    else:
        line_amount = unit_price * quantity if variant_id else final_price
        cursor.execute("""
            INSERT INTO order_items (
                order_id, variant_id, quantity, unit_price,
                line_amount, link, status, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, 'pending', NOW(), NOW())
            RETURNING order_item_id
        """, (order_id, variant_id, quantity, unit_price, line_amount, link))


def save_commission(cursor, referral_data, order_id, final_price, user_id):
    """Save commission for referrer"""
    if not referral_data or not is_postgresql():
        return 0
    
    try:
        referral_id = referral_data[0] if isinstance(referral_data, tuple) else referral_data.get("referral_id")
        commission_amount = final_price * 0.1
        
        cursor.execute("""
            INSERT INTO commissions (referral_id, order_id, amount, status, created_at)
            VALUES (%s, %s, %s, 'accrued', NOW())
            RETURNING commission_id
        """, (referral_id, order_id, commission_amount))
        
        print(f"✅ 커미션 저장 완료: {commission_amount}원")
        return commission_amount
    except Exception as e:
        print(f"⚠️ 커미션 저장 실패: {e}")
        return 0


def update_order_status(cursor, order_id, status):
    """Update order status"""
    if is_postgresql():
        cursor.execute("""
            UPDATE orders SET status = %s, updated_at = NOW()
            WHERE order_id = %s
        """, (status, order_id))
    else:
        cursor.execute("""
            UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE order_id = ?
        """, (status, order_id))


def save_package_steps(cursor, order_id, package_steps):
    """Save package steps to order"""
    if is_postgresql():
        cursor.execute("""
            UPDATE orders SET package_steps = %s, updated_at = NOW()
            WHERE order_id = %s
        """, (json.dumps(package_steps), order_id))
    else:
        cursor.execute("""
            UPDATE orders SET package_steps = ?, updated_at = CURRENT_TIMESTAMP
            WHERE order_id = ?
        """, (json.dumps(package_steps), order_id))


def start_package_processing_thread(order_id, package_steps):
    """Start package processing in background thread"""
    try:
        from backend import process_package_step
        def start_processing():
            process_package_step(order_id, 0)
        
        thread = threading.Thread(target=start_processing, daemon=True, name=f"PackageStart-{order_id}")
        thread.start()
        time.sleep(0.1)
        return thread.is_alive()
    except Exception as e:
        print(f"❌ 패키지 처리 시작 실패: {e}")
        return False


def format_order_response(order_id, status, price, discount, final_price, 
                         referral_data, commission, message, is_scheduled,
                         scheduled_datetime, is_split_delivery, split_days, split_quantity):
    """Format order response"""
    return jsonify({
        "success": True,
        "order_id": order_id,
        "status": status,
        "original_price": price,
        "discount_amount": discount,
        "final_price": final_price,
        "referral_discount": discount > 0,
        "commission_earned": commission if referral_data else 0,
        "message": message,
        "is_scheduled": is_scheduled,
        "is_split_delivery": is_split_delivery,
        "scheduled_datetime": scheduled_datetime,
        "split_days": split_days,
        "split_quantity": split_quantity
    }), 200


# ==================== Main Order Endpoint ====================

@orders.route("/purchase", methods=["POST"])
def test_orders_api():
    """주문 생성
    ---
    tags:
      - Orders-test
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
              description: "분할 발송 일수 (is_split_delivery가 true인 경우 필수)"
              example: 30
            split_quantity:
              type: integer
              description: "일일 발송 수량 (is_split_delivery가 true인 경우 필수)"
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
              description: "주문 메모 (선택사항)"
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
        # Get and validate request data
        data = request.get_json()
        print(f"=== 주문 생성 요청 ===")
        print(f"요청 데이터: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        # Validate required fields
        is_valid, error_msg = validate_order_data(data)
        if not is_valid:
            print(f"❌ {error_msg}")
            return jsonify({"error": error_msg}), 400
        
        # Extract order data
        user_id = data.get("user_id")
        service_id = data.get("service_id")
        link = data.get("link")
        quantity = data.get("quantity")
        price = data.get("price") or data.get("total_price")
        comments = data.get("comments", "")
        package_steps = data.get("package_steps", [])
        is_scheduled = data.get("is_scheduled", False)
        scheduled_datetime = data.get("scheduled_datetime")
        is_split_delivery = data.get("is_split_delivery", False)
        split_days = data.get("split_days", 0)
        split_quantity = data.get("split_quantity", 0)
        is_package = len(package_steps) > 0
        
        print(f"✅ 필수 필드 검증 통과")
        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor()
        print("✅ 데이터베이스 연결 성공")
        print(f"🗄️ {'PostgreSQL' if is_postgresql() else 'SQLite'} 데이터베이스 사용 중")
        
        # Get user ID in database
        db_user_id = get_db_user_id(cursor, user_id)
        print(f"✅ 사용자 ID: {user_id} -> {db_user_id}")
        
        # Process coupon if provided
        coupon_id = data.get("coupon_id") or data.get("user_coupon_id")
        user_coupon_id, discount_amount, final_price = process_coupon(cursor, user_id, coupon_id, price)
        
        # Get referral information
        referral_data = get_referral_info(cursor, user_id)
        if referral_data:
            print(f"✅ 추천인 정보 확인 완료")
        
        # Get variant ID
        variant_id, unit_price = get_variant_id(cursor, service_id)
        if variant_id:
            print(f"✅ Variant ID: {variant_id}, Unit Price: {unit_price}")
        
        # Call SMM Panel API for regular orders
        smm_success = False
        smm_panel_order_id = None
        smm_error = None
        
        if not is_scheduled and not is_package:
            print(f"🚀 일반 주문 - SMM Panel API 호출")
            smm_success, smm_panel_order_id, smm_error = call_smm_api(
                service_id, link, quantity, comments,
                data.get("runs", 1), data.get("interval", 0)
            )
            if smm_success:
                print(f"✅ SMM Panel 주문 생성 성공: {smm_panel_order_id}")
            else:
                print(f"❌ SMM Panel API 호출 실패: {smm_error}")
        
        # Generate order ID
        order_id = int(time.time() * 1000)
        if smm_panel_order_id:
            order_id = smm_panel_order_id
        
        # Determine order status
        order_status = "failed" if smm_error else ("pending" if is_scheduled else "pending")
        
        # Create order record
        order_data = {
            "order_id": order_id,
            "user_id": db_user_id,
            "total_amount": price,
            "discount_amount": discount_amount,
            "final_amount": final_price,
            "link": str(link) if link else "",
            "quantity": int(quantity) if quantity else 0,
            "status": order_status,
            "is_scheduled": is_scheduled,
            "scheduled_datetime": scheduled_datetime,
            "is_split_delivery": is_split_delivery,
            "split_days": split_days,
            "split_quantity": split_quantity,
            "smm_panel_order_id": smm_panel_order_id,
            "detailed_service": data.get("detailed_service", ""),
            "service_id": service_id,
            "referrer_user_id": referral_data[1] if referral_data and is_postgresql() else None,
            "coupon_id": user_coupon_id,
            "referral_code": referral_data[0] if referral_data and not is_postgresql() else None
        }
        
        try:
            created_order_id = create_order_record(cursor, order_data)
            print(f"✅ 주문 생성 완료 - order_id: {created_order_id}")
        except Exception as e:
            print(f"❌ 주문 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            conn.rollback()
            return jsonify({
                "error": f"주문 생성 실패: {str(e)}",
                "refund_required": True,
                "refund_amount": final_price
            }), 500
        
        # Handle SMM Panel failure
        if smm_error:
            try:
                update_order_status(cursor, created_order_id, "failed")
                if is_postgresql():
                    cursor.execute("""
                        UPDATE orders 
                        SET total_amount = 0, discount_amount = 0, final_amount = 0, updated_at = NOW()
                        WHERE order_id = %s
                    """, (created_order_id,))
                conn.commit()
                return jsonify({
                    "success": False,
                    "message": f"SMM Panel API 호출 실패: {smm_error}",
                    "order_id": created_order_id,
                    "status": "failed",
                    "refund_required": True,
                    "refund_amount": final_price
                }), 200
            except Exception as update_error:
                print(f"⚠️ 주문 상태 업데이트 실패: {update_error}")
                conn.rollback()
        
        # Create order items
        create_order_items(
            cursor, created_order_id, "package" if is_package else "single",
            data, variant_id, unit_price, link, quantity, final_price
        )
        
        # Save commission if referral exists
        commission_amount = 0
        if referral_data and not smm_error:
            commission_amount = save_commission(cursor, referral_data, created_order_id, final_price, user_id)
        
        # Handle package orders
        if is_package:
            save_package_steps(cursor, created_order_id, package_steps)
            update_order_status(cursor, created_order_id, "processing")
            start_package_processing_thread(created_order_id, package_steps)
            conn.commit()
            status = "processing"
            message = f"패키지 주문이 생성되었습니다. ({len(package_steps)}단계 순차 처리 중)"
        elif is_scheduled:
            conn.commit()
            status = "pending"
            message = "예약 주문이 생성되었습니다."
        elif is_split_delivery:
            conn.commit()
            status = "pending"
            message = "분할 주문이 생성되었습니다."
        else:
            status = "주문발송" if smm_success else "failed"
            message = "주문이 접수되어 진행중입니다." if smm_success else "주문 처리 중 오류가 발생했습니다."
        
        conn.commit()
        print(f"✅ 주문 처리 완료 - order_id: {created_order_id}, status: {status}")
        
        # Return response
        return format_order_response(
            created_order_id, status, price, discount_amount, final_price,
            referral_data, commission_amount, message, is_scheduled,
            scheduled_datetime, is_split_delivery, split_days, split_quantity
        )
        
    except Exception as e:
        print(f"❌ 주문 생성 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        
        if conn:
            conn.rollback()
        
        return jsonify({
            "error": f"주문 생성 실패: {str(e)}",
            "refund_required": True,
            "refund_amount": 0
        }), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print("✅ 데이터베이스 연결 종료")
