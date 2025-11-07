# 데이터베이스 스키마 (Database Schema)

이 문서는 snspmt 프로젝트의 전체 데이터베이스 스키마를 문서화합니다.

## 테이블 목록 (Tables)

### 1. users (사용자)
**설명:** 사용자 정보를 저장하는 테이블

**컬럼:**
- `user_id` (VARCHAR(255) / TEXT) - PRIMARY KEY, 사용자 고유 ID
- `email` (VARCHAR(255) / TEXT) - UNIQUE, 이메일 주소
- `name` (VARCHAR(255) / TEXT) - 사용자 이름
- `display_name` (VARCHAR(255) / TEXT) - 표시 이름
- `google_id` (VARCHAR(255) / TEXT) - Google 로그인 ID
- `kakao_id` (VARCHAR(255) / TEXT) - 카카오 로그인 ID
- `profile_image` (TEXT) - 프로필 이미지 URL
- `last_login` (TIMESTAMP) - 마지막 로그인 시간
- `last_activity` (TIMESTAMP) - 마지막 활동 시간 (PostgreSQL만)
- `created_at` (TIMESTAMP) - 생성 시간
- `updated_at` (TIMESTAMP) - 수정 시간

---

### 2. points (포인트)
**설명:** 사용자 포인트 잔액을 저장하는 테이블

**컬럼:**
- `user_id` (VARCHAR(255) / TEXT) - PRIMARY KEY, 사용자 ID (users 참조)
- `points` (INTEGER) - DEFAULT 0, 보유 포인트
- `created_at` (TIMESTAMP) - 생성 시간
- `updated_at` (TIMESTAMP) - 수정 시간

---

### 3. orders (주문)
**설명:** 주문 정보를 저장하는 메인 테이블

**컬럼:**
- `order_id` (VARCHAR(255) / INTEGER) - PRIMARY KEY, 주문 고유 ID
- `user_id` (VARCHAR(255) / TEXT) - NOT NULL, 사용자 ID
- `user_email` (VARCHAR(255) / TEXT) - 사용자 이메일
- `service_id` (VARCHAR(255) / TEXT) - NOT NULL, 서비스 ID
- `platform` (VARCHAR(255) / TEXT) - 플랫폼명 (Instagram, TikTok 등)
- `service_name` (VARCHAR(255) / TEXT) - 서비스 이름
- `service_type` (VARCHAR(255) / TEXT) - 서비스 타입
- `service_platform` (VARCHAR(255) / TEXT) - 서비스 플랫폼
- `service_quantity` (INTEGER) - 서비스 수량
- `service_link` (TEXT) - 서비스 링크
- `link` (TEXT) - NOT NULL, 주문 대상 링크
- `quantity` (INTEGER) - NOT NULL, 주문 수량
- `price` (DECIMAL(10,2)) - NOT NULL, 가격
- `total_price` (DECIMAL(10,2)) - 총 가격
- `amount` (DECIMAL(10,2)) - 금액
- `discount_amount` (DECIMAL(10,2)) - DEFAULT 0, 할인 금액
- `referral_code` (VARCHAR(50) / TEXT) - 추천인 코드
- `status` (VARCHAR(50) / TEXT) - DEFAULT 'pending', 주문 상태
- `external_order_id` (VARCHAR(255) / TEXT) - 외부 주문 ID
- `smm_panel_order_id` (VARCHAR(255) / TEXT) - SMM Panel 주문 ID
- `remarks` (TEXT) - 비고
- `comments` (TEXT) - 코멘트
- `is_scheduled` (BOOLEAN) - DEFAULT FALSE, 예약 주문 여부
- `scheduled_datetime` (TIMESTAMP) - 예약 주문 시간
- `is_split_delivery` (BOOLEAN) - DEFAULT FALSE, 분할 배송 여부
- `split_days` (INTEGER) - DEFAULT 0, 분할 배송 일수
- `split_quantity` (INTEGER) - DEFAULT 0, 분할 배송 수량
- `package_steps` (JSONB / TEXT) - 패키지 주문 단계 정보
- `detailed_service` (TEXT) - 상세 서비스 정보
- `last_status_check` (TIMESTAMP) - 마지막 상태 확인 시간
- `quantity_delivered` (INTEGER) - 배송된 수량
- `created_at` (TIMESTAMP) - 생성 시간
- `updated_at` (TIMESTAMP) - 수정 시간

**주요 상태값:**
- `pending` - 대기중
- `주문발송` - 주문 발송됨
- `주문 실행중` - 실행 중
- `주문 실행완료` - 실행 완료
- `completed` - 완료
- `failed` - 실패
- `scheduled` - 예약됨
- `split_scheduled` - 분할 배송 예약됨
- `package_processing` - 패키지 처리 중

---

### 4. scheduled_orders (예약 주문)
**설명:** 예약된 주문을 저장하는 테이블

**컬럼:**
- `id` (SERIAL / INTEGER) - PRIMARY KEY, 예약 주문 ID
- `user_id` (VARCHAR(255) / TEXT) - NOT NULL, 사용자 ID
- `service_id` (VARCHAR(255) / TEXT) - NOT NULL, 서비스 ID
- `link` (TEXT) - NOT NULL, 주문 대상 링크
- `quantity` (INTEGER) - NOT NULL, 주문 수량
- `price` (DECIMAL(10,2)) - NOT NULL, 가격
- `scheduled_datetime` (TIMESTAMP) - NOT NULL, 예약 실행 시간
- `status` (VARCHAR(50) / TEXT) - DEFAULT 'pending', 상태
- `package_steps` (TEXT) - 패키지 단계 정보 (JSON 문자열)
- `runs` (INTEGER) - Drip-feed 반복 횟수
- `interval` (INTEGER) - Drip-feed 간격 (분)
- `created_at` (TIMESTAMP) - 생성 시간
- `processed_at` (TIMESTAMP) - 처리 완료 시간

---

### 5. split_delivery_progress (분할 배송 진행 상황)
**설명:** 분할 배송 주문의 진행 상황을 추적하는 테이블

**컬럼:**
- `id` (SERIAL / INTEGER) - PRIMARY KEY
- `order_id` (VARCHAR(255) / TEXT) - NOT NULL, 주문 ID (orders 참조)
- `day_number` (INTEGER) - NOT NULL, 일차 번호
- `scheduled_date` (DATE / TEXT) - 예약 날짜
- `quantity_delivered` (INTEGER) - DEFAULT 0, 배송된 수량
- `status` (VARCHAR(50) / TEXT) - DEFAULT 'pending', 상태
- `smm_panel_order_id` (VARCHAR(255) / TEXT) - SMM Panel 주문 ID
- `error_message` (TEXT) - 에러 메시지
- `created_at` (TIMESTAMP) - 생성 시간
- `completed_at` (TIMESTAMP) - 완료 시간
- `failed_at` (TIMESTAMP) - 실패 시간

---

### 6. package_progress (패키지 진행 상황)
**설명:** 패키지 주문의 각 단계 진행 상황을 추적하는 테이블

**컬럼:**
- `id` (SERIAL / INTEGER) - PRIMARY KEY
- `order_id` (VARCHAR(255) / TEXT) - NOT NULL, 주문 ID (orders 참조)
- `step_number` (INTEGER) - NOT NULL, 단계 번호
- `step_name` (VARCHAR(255) / TEXT) - NOT NULL, 단계 이름
- `service_id` (VARCHAR(255) / TEXT) - NOT NULL, 서비스 ID
- `quantity` (INTEGER) - NOT NULL, 수량
- `smm_panel_order_id` (VARCHAR(255) / TEXT) - SMM Panel 주문 ID
- `status` (VARCHAR(50) / TEXT) - DEFAULT 'pending', 상태
- `error_message` (TEXT) - 에러 메시지
- `created_at` (TIMESTAMP) - 생성 시간
- `completed_at` (TIMESTAMP) - 완료 시간

---

### 7. point_purchases (포인트 구매)
**설명:** 포인트 구매 신청 내역을 저장하는 테이블

**컬럼:**
- `id` (SERIAL / INTEGER) - PRIMARY KEY
- `purchase_id` (VARCHAR(255) / TEXT) - UNIQUE, 구매 고유 ID
- `user_id` (VARCHAR(255) / TEXT) - NOT NULL, 사용자 ID
- `user_email` (VARCHAR(255) / TEXT) - 사용자 이메일
- `amount` (INTEGER) - NOT NULL, 포인트 양
- `price` (DECIMAL(10,2)) - NOT NULL, 가격
- `status` (VARCHAR(50) / TEXT) - DEFAULT 'pending', 상태 (pending/approved/rejected)
- `depositor_name` (VARCHAR(255) / TEXT) - 입금자명
- `buyer_name` (VARCHAR(255) / TEXT) - 구매자명
- `bank_name` (VARCHAR(255) / TEXT) - 은행명
- `bank_info` (TEXT) - 은행 정보
- `receipt_type` (VARCHAR(50) / TEXT) - 영수증 타입
- `business_info` (TEXT) - 사업자 정보
- `created_at` (TIMESTAMP) - 생성 시간
- `updated_at` (TIMESTAMP) - 수정 시간

---

### 8. referral_codes (추천인 코드)
**설명:** 추천인 코드 정보를 저장하는 테이블

**컬럼:**
- `id` (SERIAL / INTEGER) - PRIMARY KEY
- `code` (VARCHAR(50) / TEXT) - UNIQUE NOT NULL, 추천인 코드
- `user_id` (VARCHAR(255) / TEXT) - 사용자 ID
- `user_email` (VARCHAR(255) / TEXT) - UNIQUE, 사용자 이메일
- `name` (VARCHAR(255) / TEXT) - 이름
- `phone` (VARCHAR(255) / TEXT) - 전화번호
- `is_active` (BOOLEAN / INTEGER) - DEFAULT true, 활성화 여부
- `usage_count` (INTEGER) - DEFAULT 0, 사용 횟수
- `total_commission` (DECIMAL(10,2)) - DEFAULT 0, 총 커미션
- `created_at` (TIMESTAMP) - 생성 시간
- `updated_at` (TIMESTAMP) - 수정 시간

---

### 9. referrals (추천인 관계)
**설명:** 추천인-피추천인 관계를 저장하는 테이블

**컬럼:**
- `id` (SERIAL / INTEGER) - PRIMARY KEY
- `referrer_email` (VARCHAR(255) / TEXT) - NOT NULL, 추천인 이메일
- `referral_code` (VARCHAR(50) / TEXT) - NOT NULL, 추천인 코드
- `name` (VARCHAR(255) / TEXT) - 이름
- `phone` (VARCHAR(255) / TEXT) - 전화번호
- `status` (VARCHAR(50) / TEXT) - DEFAULT 'active', 상태
- `created_at` (TIMESTAMP) - 생성 시간

---

### 10. commissions (커미션)
**설명:** 추천인 커미션 내역을 저장하는 테이블

**컬럼:**
- `id` (SERIAL / INTEGER) - PRIMARY KEY
- `referred_user` (VARCHAR(255) / TEXT) - NOT NULL, 피추천인
- `referrer_id` (VARCHAR(255) / TEXT) - NOT NULL, 추천인 ID
- `purchase_amount` (DECIMAL(10,2)) - NOT NULL, 구매 금액
- `commission_amount` (DECIMAL(10,2)) - NOT NULL, 커미션 금액
- `commission_rate` (DECIMAL(5,4)) - NOT NULL, 커미션 비율
- `is_paid` (BOOLEAN / INTEGER) - DEFAULT false, 지급 여부
- `payment_date` (TIMESTAMP) - 지급 예정일
- `paid_date` (TIMESTAMP) - 실제 지급일
- `created_at` (TIMESTAMP) - 생성 시간

---

### 11. coupons (쿠폰)
**설명:** 사용자 쿠폰 정보를 저장하는 테이블

**컬럼:**
- `id` (SERIAL / INTEGER) - PRIMARY KEY
- `user_id` (VARCHAR(255) / TEXT) - NOT NULL, 사용자 ID
- `referral_code` (VARCHAR(50) / TEXT) - 추천인 코드
- `discount_type` (VARCHAR(20) / TEXT) - DEFAULT 'percentage', 할인 타입 (percentage/fixed)
- `discount_value` (DECIMAL(5,2)) - NOT NULL, 할인 값
- `is_used` (BOOLEAN / INTEGER) - DEFAULT false, 사용 여부
- `used_at` (TIMESTAMP) - 사용 시간
- `created_at` (TIMESTAMP) - 생성 시간
- `expires_at` (TIMESTAMP) - 만료 시간

---

### 12. user_referral_connections (사용자 추천인 연결)
**설명:** 사용자와 추천인 코드의 연결을 저장하는 테이블

**컬럼:**
- `id` (SERIAL / INTEGER) - PRIMARY KEY
- `user_id` (VARCHAR(255) / TEXT) - NOT NULL, 사용자 ID
- `referral_code` (VARCHAR(50) / TEXT) - NOT NULL, 추천인 코드
- `referrer_email` (VARCHAR(255) / TEXT) - NOT NULL, 추천인 이메일
- `created_at` (TIMESTAMP) - 생성 시간

---

### 13. commission_payments (커미션 지급)
**설명:** 커미션 지급 내역을 저장하는 테이블

**컬럼:**
- `id` (SERIAL / INTEGER) - PRIMARY KEY
- `referrer_email` (VARCHAR(255) / TEXT) - NOT NULL, 추천인 이메일
- `amount` (DECIMAL(10,2)) - NOT NULL, 지급 금액
- `payment_method` (VARCHAR(50) / TEXT) - DEFAULT 'bank_transfer', 지급 방법
- `notes` (TEXT) - 비고
- `paid_at` (TIMESTAMP) - DEFAULT NOW(), 지급 시간

---

### 14. commission_points (커미션 포인트)
**설명:** 추천인 커미션 포인트 잔액을 저장하는 테이블

**컬럼:**
- `id` (SERIAL / INTEGER) - PRIMARY KEY
- `referrer_email` (VARCHAR(255) / TEXT) - NOT NULL, 추천인 이메일
- `referrer_name` (VARCHAR(255) / TEXT) - 추천인 이름
- `total_earned` (DECIMAL(10,2)) - DEFAULT 0, 총 적립액
- `total_paid` (DECIMAL(10,2)) - DEFAULT 0, 총 지급액
- `current_balance` (DECIMAL(10,2)) - DEFAULT 0, 현재 잔액
- `created_at` (TIMESTAMP) - 생성 시간
- `updated_at` (TIMESTAMP) - 수정 시간

---

### 15. commission_point_transactions (커미션 포인트 거래 내역)
**설명:** 커미션 포인트 거래 내역을 저장하는 테이블

**컬럼:**
- `id` (SERIAL / INTEGER) - PRIMARY KEY
- `referrer_email` (VARCHAR(255) / TEXT) - NOT NULL, 추천인 이메일
- `transaction_type` (VARCHAR(50) / TEXT) - NOT NULL, 거래 타입 (earn/withdraw)
- `amount` (DECIMAL(10,2)) - NOT NULL, 거래 금액
- `balance_after` (DECIMAL(10,2)) - NOT NULL, 거래 후 잔액
- `description` (TEXT) - 설명
- `created_at` (TIMESTAMP) - 생성 시간

---

### 16. commission_withdrawal_requests (커미션 환급 신청)
**설명:** 커미션 환급 신청을 저장하는 테이블

**컬럼:**
- `id` (SERIAL / INTEGER) - PRIMARY KEY
- `referrer_email` (VARCHAR(255) / TEXT) - NOT NULL, 추천인 이메일
- `referrer_name` (VARCHAR(255) / TEXT) - 추천인 이름
- `bank_name` (VARCHAR(255) / TEXT) - NOT NULL, 은행명
- `account_number` (VARCHAR(255) / TEXT) - NOT NULL, 계좌번호
- `account_holder` (VARCHAR(255) / TEXT) - NOT NULL, 예금주
- `amount` (DECIMAL(10,2)) - NOT NULL, 환급 신청 금액
- `status` (VARCHAR(50) / TEXT) - DEFAULT 'pending', 상태 (pending/approved/rejected)
- `admin_notes` (TEXT) - 관리자 메모
- `requested_at` (TIMESTAMP) - DEFAULT NOW(), 신청 시간
- `processed_at` (TIMESTAMP) - 처리 완료 시간
- `processed_by` (VARCHAR(255) / TEXT) - 처리자

---

### 17. notices (공지사항)
**설명:** 공지사항을 저장하는 테이블

**컬럼:**
- `id` (SERIAL / INTEGER) - PRIMARY KEY
- `title` (VARCHAR(255) / TEXT) - NOT NULL, 제목
- `content` (TEXT) - NOT NULL, 내용
- `image_url` (VARCHAR(500) / TEXT) - 이미지 URL
- `is_active` (BOOLEAN / INTEGER) - DEFAULT true, 활성화 여부
- `created_at` (TIMESTAMP) - 생성 시간
- `updated_at` (TIMESTAMP) - 수정 시간

---

### 18. blog_posts (블로그 포스트)
**설명:** 블로그 포스트를 저장하는 테이블

**컬럼:**
- `id` (SERIAL / INTEGER) - PRIMARY KEY
- `title` (VARCHAR(255) / TEXT) - NOT NULL, 제목
- `content` (TEXT) - NOT NULL, 내용
- `excerpt` (TEXT) - 요약
- `category` (VARCHAR(100) / TEXT) - 카테고리
- `thumbnail_url` (TEXT) - 썸네일 URL
- `tags` (JSONB / TEXT) - DEFAULT '[]', 태그 (PostgreSQL은 JSONB)
- `is_published` (BOOLEAN / INTEGER) - DEFAULT false, 게시 여부
- `created_at` (TIMESTAMP) - 생성 시간
- `updated_at` (TIMESTAMP) - 수정 시간
- `view_count` (INTEGER) - DEFAULT 0, 조회수

---

## 관계 (Relationships)

### 주요 외래키 관계:
- `orders.order_id` ← `split_delivery_progress.order_id`
- `orders.order_id` ← `package_progress.order_id`
- `points.user_id` → `users.user_id`
- `orders.user_id` → `users.user_id`
- `referrals.referrer_email` ↔ `referral_codes.user_email`
- `user_referral_connections.referral_code` → `referral_codes.code`

---

## 데이터베이스 타입별 차이점

### PostgreSQL vs SQLite

1. **Primary Key:**
   - PostgreSQL: `SERIAL` (자동 증가 정수) 또는 `VARCHAR(255)`
   - SQLite: `INTEGER PRIMARY KEY AUTOINCREMENT` 또는 `TEXT PRIMARY KEY`

2. **JSON 데이터:**
   - PostgreSQL: `JSONB` 타입 사용 (인덱싱 지원)
   - SQLite: `TEXT` 타입으로 JSON 문자열 저장

3. **Boolean:**
   - PostgreSQL: `BOOLEAN` 타입
   - SQLite: `INTEGER` 타입 (0 또는 1)

4. **Timestamp:**
   - PostgreSQL: `TIMESTAMP DEFAULT NOW()`
   - SQLite: `TIMESTAMP DEFAULT CURRENT_TIMESTAMP`

5. **DECIMAL:**
   - PostgreSQL: `DECIMAL(10,2)`
   - SQLite: `REAL` 또는 `NUMERIC`

---

## 인덱스 (Indexes)

현재 명시적인 인덱스 정의는 없지만, 다음 컬럼들에 인덱스가 필요할 수 있습니다:
- `orders.user_id`
- `orders.status`
- `orders.created_at`
- `referral_codes.code`
- `referrals.referrer_email`
- `scheduled_orders.scheduled_datetime`

---

## 주의사항

1. **scheduled_orders 테이블의 `runs`와 `interval` 컬럼:**
   - Drip-feed 주문을 위한 컬럼이며, 마이그레이션이 필요할 수 있습니다.
   - 만약 컬럼이 존재하지 않으면 `ALTER TABLE`로 추가해야 합니다.

2. **orders 테이블의 `package_steps`:**
   - PostgreSQL: `JSONB` 타입
   - SQLite: `TEXT` 타입 (JSON 문자열)

3. **날짜/시간 필드:**
   - 모든 타임스탬프는 서버의 시간대를 기준으로 합니다.

---

## 마이그레이션 이력

주요 컬럼 추가 이력:
- `orders.is_scheduled`, `orders.scheduled_datetime` - 예약 주문 지원
- `orders.is_split_delivery`, `orders.split_days`, `orders.split_quantity` - 분할 배송 지원
- `orders.package_steps` - 패키지 주문 지원
- `orders.smm_panel_order_id` - SMM Panel 연동
- `orders.last_status_check` - 상태 확인 추적
- `scheduled_orders.runs`, `scheduled_orders.interval` - Drip-feed 지원

