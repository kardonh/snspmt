# 기능 테스트 가이드

## 📋 테스트 전 확인 사항

### 1. 환경 설정 확인
- ✅ `.env.local` 파일에 Supabase 환경 변수 설정 확인
- ✅ `DATABASE_URL` 환경 변수가 올바르게 설정되었는지 확인
- ✅ 백엔드 서버가 `localhost:8000`에서 실행 중인지 확인
- ✅ 프론트엔드 서버가 `localhost:3000`에서 실행 중인지 확인

### 2. 데이터베이스 연결 확인
```bash
# 백엔드 서버 실행 시 데이터베이스 연결 로그 확인
python backend.py
```

---

## 🧪 테스트 항목

### 1. 사용자 동기화 및 쿠폰 발급 테스트

**엔드포인트**: `POST /api/users/sync`

**테스트 시나리오**:
1. **신규 사용자 회원가입 (추천인 코드 포함)**
   - 요청 데이터:
     ```json
     {
       "user_id": "test-user-123",
       "email": "test@example.com",
       "username": "Test User",
       "phone_number": "010-1234-5678",
       "referral_code": "REF123"
     }
     ```
   - 예상 결과:
     - ✅ 사용자가 `users` 테이블에 생성됨
     - ✅ `referrals` 테이블에 추천인 관계 저장 (status='pending')
     - ✅ `user_coupons` 테이블에 5% 할인 쿠폰 발급됨

2. **기존 사용자 업데이트 (추천인 코드 포함)**
   - 동일한 이메일로 다시 동기화 시도
   - 예상 결과:
     - ✅ 사용자 정보 업데이트
     - ✅ 추천인 관계 저장 (중복 체크)
     - ✅ 5% 할인 쿠폰 발급 (중복 체크)

**확인 방법**:
```sql
-- users 테이블 확인
SELECT * FROM users WHERE email = 'test@example.com';

-- referrals 테이블 확인
SELECT * FROM referrals WHERE referred_user_id = (SELECT user_id FROM users WHERE email = 'test@example.com');

-- user_coupons 테이블 확인
SELECT * FROM user_coupons WHERE user_id = (SELECT user_id FROM users WHERE email = 'test@example.com');
```

---

### 2. 주문 생성 테스트

**엔드포인트**: `POST /api/orders`

**테스트 시나리오**:
1. **일반 주문 생성**
   - 요청 데이터:
     ```json
     {
       "user_id": "test-user-123",
       "service_id": "100",
       "link": "https://instagram.com/test",
       "quantity": 100,
       "price": 10000
     }
     ```
   - 예상 결과:
     - ✅ `orders` 테이블에 주문 생성 (`total_amount`, `final_amount` 사용)
     - ✅ `order_items` 테이블에 상세 정보 저장 (`variant_id`, `link`, `quantity`, `unit_price`)
     - ✅ `commissions` 테이블에 커미션 적립 (추천인이 있는 경우, status='accrued')

2. **쿠폰 사용 주문 생성**
   - 요청 데이터에 `coupon_code` 포함
   - 예상 결과:
     - ✅ 쿠폰 검증 성공 (`user_coupons` 테이블 조회)
     - ✅ `discount_amount` 계산
     - ✅ `final_amount` = `total_amount` - `discount_amount`
     - ✅ `user_coupons.status` = 'used'로 업데이트

**확인 방법**:
```sql
-- orders 테이블 확인
SELECT order_id, user_id, total_amount, discount_amount, final_amount, status 
FROM orders 
ORDER BY created_at DESC 
LIMIT 1;

-- order_items 테이블 확인
SELECT * FROM order_items 
WHERE order_id = (SELECT order_id FROM orders ORDER BY created_at DESC LIMIT 1);

-- commissions 테이블 확인 (추천인이 있는 경우)
SELECT * FROM commissions 
WHERE order_id = (SELECT order_id FROM orders ORDER BY created_at DESC LIMIT 1);
```

---

### 3. 주문 조회 테스트

**엔드포인트**: `GET /api/orders?user_id={user_id}`

**테스트 시나리오**:
1. **사용자 주문 목록 조회**
   - `user_id`로 조회 (external_uid 또는 email)
   - 예상 결과:
     - ✅ `orders` 테이블과 `order_items` 테이블 조인
     - ✅ `product_variants` 테이블 조인하여 서비스 이름 가져오기
     - ✅ `variant_meta`에서 `service_id` 추출
     - ✅ 올바른 서비스 이름 반환

**확인 방법**:
- 브라우저 콘솔에서 응답 확인
- 각 주문의 `service_name`이 올바른지 확인
- `link`, `quantity`, `price` 값이 올바른지 확인

---

### 4. 커미션 조회 테스트

**엔드포인트**: `GET /api/referral/commissions?user_id={user_id}`

**테스트 시나리오**:
1. **추천인 커미션 내역 조회**
   - 추천인 `user_id`로 조회
   - 예상 결과:
     - ✅ `commissions` 테이블과 `referrals` 테이블 조인
     - ✅ `orders` 테이블과 조인하여 `purchase_amount` 계산
     - ✅ `COALESCE(o.final_amount, o.total_amount, 0)` 또는 역산 계산

**확인 방법**:
```sql
-- commissions 테이블 직접 확인
SELECT 
    c.commission_id,
    c.amount as commission_amount,
    o.final_amount,
    o.total_amount,
    (c.amount / 0.1) as calculated_purchase_amount
FROM commissions c
JOIN referrals r ON c.referral_id = r.referral_id
LEFT JOIN orders o ON c.order_id = o.order_id
WHERE r.referrer_user_id = {referrer_user_id};
```

---

### 5. 패키지 주문 처리 테스트

**엔드포인트**: `POST /api/orders/start-package-processing`

**테스트 시나리오**:
1. **패키지 주문 처리 시작**
   - `order_id` 전달
   - 예상 결과:
     - ✅ `orders` 테이블과 `order_items` 테이블 조인하여 `link` 가져오기
     - ✅ `package_steps` 파싱 성공
     - ✅ 첫 번째 단계 처리 시작

**확인 방법**:
- 백엔드 로그에서 `process_package_step` 호출 확인
- `orders` 테이블의 `status` 업데이트 확인

---

### 6. 예약 주문 처리 테스트

**엔드포인트**: `POST /api/cron/process-scheduled-orders`

**테스트 시나리오**:
1. **예약 주문 자동 처리**
   - `scheduled_datetime`이 현재 시간 이전인 주문들 조회
   - 예상 결과:
     - ✅ `orders` 테이블과 `order_items` 테이블 조인
     - ✅ `package_steps` 파싱 성공
     - ✅ 주문 처리 시작

**확인 방법**:
```sql
-- 예약 주문 확인
SELECT order_id, is_scheduled, scheduled_datetime, status, package_steps 
FROM orders 
WHERE is_scheduled = TRUE 
ORDER BY scheduled_datetime DESC;
```

---

## 🔍 문제 발생 시 확인 사항

### 1. 데이터베이스 연결 오류
- ✅ `DATABASE_URL` 환경 변수 확인
- ✅ Supabase 연결 정보 확인
- ✅ SSL 연결 설정 확인 (`sslmode='require'`)

### 2. 스키마 불일치 오류
- ✅ `orders` 테이블에 `service_id`, `link`, `quantity`, `price` 컬럼 직접 사용하지 않는지 확인
- ✅ `order_items` 테이블과 조인하여 사용하는지 확인
- ✅ `total_amount`, `final_amount` 사용하는지 확인

### 3. 외래 키 제약 오류
- ✅ `order_items.variant_id`가 `product_variants.variant_id`와 일치하는지 확인
- ✅ `orders.user_id`가 `users.user_id`와 일치하는지 확인
- ✅ `commissions.referral_id`가 `referrals.referral_id`와 일치하는지 확인

---

## 📊 테스트 결과 기록

### 테스트 일자: _____________

| 테스트 항목 | 결과 | 비고 |
|------------|------|------|
| 사용자 동기화 | ⬜ 통과 ⬜ 실패 | |
| 쿠폰 발급 | ⬜ 통과 ⬜ 실패 | |
| 주문 생성 | ⬜ 통과 ⬜ 실패 | |
| 주문 조회 | ⬜ 통과 ⬜ 실패 | |
| 커미션 조회 | ⬜ 통과 ⬜ 실패 | |
| 패키지 주문 | ⬜ 통과 ⬜ 실패 | |
| 예약 주문 | ⬜ 통과 ⬜ 실패 | |

### 발견된 문제점:
1. _________________________________________________
2. _________________________________________________
3. _________________________________________________

---

## ✅ 테스트 완료 후

모든 테스트가 통과하면:
1. ✅ 프로덕션 환경 배포 준비
2. ✅ 모니터링 설정
3. ✅ 백업 전략 수립

