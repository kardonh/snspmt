# 스키마 불일치 분석 및 수정 계획

## 🔍 실제 데이터베이스 스키마 확인 결과

### 1. `orders` 테이블

#### 실제 DB 스키마:
- `order_id`: `bigint` (BIGSERIAL) ✅
- `user_id`: `bigint` ✅
- `total_amount`: `numeric(14,2)` ✅
- `final_amount`: `numeric(14,2)` ✅
- `discount_amount`: `numeric(14,2)` ✅
- `status`: `order_status` (ENUM) ✅
- 외래 키: `user_id` → `users.user_id`, `referrer_user_id` → `users.user_id`, `coupon_id` → `user_coupons.user_coupon_id`

#### `backend.py`의 잘못된 스키마 정의:
- `order_id`: `VARCHAR(255)` ❌
- `user_id`: `VARCHAR(255)` ❌
- `price`: `DECIMAL(10,2)` ❌ (실제 DB에는 없음)
- `total_price`: `DECIMAL(10,2)` ❌ (실제 DB에는 `total_amount` 사용)
- `amount`: `DECIMAL(10,2)` ❌ (실제 DB에는 없음)

**문제점**: `backend.py`의 `CREATE TABLE` 정의가 실제 DB와 다름. 하지만 `CREATE TABLE IF NOT EXISTS`를 사용하므로 실제로는 기존 테이블이 사용됨.

**코드에서 수정 필요**:
- ❌ `orders.price` 사용하는 부분 → `orders.total_amount` 또는 `orders.final_amount` 사용
- ❌ `orders.total_price` 사용하는 부분 → `orders.total_amount` 사용
- ❌ `orders.amount` 사용하는 부분 → 제거 또는 `orders.total_amount` 사용

---

### 2. `commissions` 테이블

#### 실제 DB 스키마:
- `commission_id`: `bigint` (BIGSERIAL) ✅
- `referral_id`: `bigint` ✅ (외래 키: `referrals.referral_id`)
- `order_id`: `bigint` ✅ (외래 키: `orders.order_id`)
- `amount`: `numeric(14,2)` ✅
- `status`: `commission_status` (ENUM, 기본값: 'accrued') ✅
- `paid_amount`: `numeric(14,2)` ✅
- `paid_out_at`: `timestamp` ✅

#### `backend.py`의 잘못된 스키마 정의:
- `id`: `SERIAL` ❌ (실제는 `commission_id`)
- `referred_user`: `VARCHAR(255)` ❌ (실제 DB에는 없음)
- `referrer_id`: `VARCHAR(255)` ❌ (실제는 `referral_id` 사용)
- `purchase_amount`: `DECIMAL(10,2)` ❌ (실제 DB에는 없음)
- `commission_amount`: `DECIMAL(10,2)` ❌ (실제는 `amount` 사용)
- `commission_rate`: `DECIMAL(5,4)` ❌ (실제 DB에는 없음)
- `is_paid`: `BOOLEAN` ❌ (실제는 `status` 사용)

**문제점**: `backend.py`의 `commissions` 테이블 정의가 완전히 다름. `CREATE TABLE IF NOT EXISTS`를 사용하므로 실제로는 기존 테이블이 사용됨.

**코드에서 수정 필요**:
- ❌ `commissions` 테이블에 INSERT 시 컬럼명 수정 필요
- ❌ `referred_user`, `referrer_id`, `purchase_amount`, `commission_amount`, `commission_rate`, `is_paid` 사용 부분
- ✅ `referral_id`, `order_id`, `amount`, `status` 사용

---

### 3. `coupons` 테이블

#### 실제 DB 스키마:
- `coupon_id`: `bigint` (BIGSERIAL) ✅
- `coupon_code`: `character varying(255)` ✅
- `coupon_name`: `character varying(255)` ✅
- `discount_type`: `coupon_discount_type` (ENUM) ✅
- `discount_value`: `numeric(14,2)` ✅
- `min_order_amount`: `numeric(14,2)` ✅
- `product_variant_id`: `bigint` (외래 키) ✅
- `valid_from`, `valid_until`: `timestamp` ✅

#### `backend.py`의 잘못된 스키마 정의:
- `id`: `SERIAL` ❌ (실제는 `coupon_id`)
- `user_id`: `VARCHAR(255)` ❌ (실제 DB에는 없음!)
- `referral_code`: `VARCHAR(50)` ❌ (실제 DB에는 없음!)
- `is_used`: `BOOLEAN` ❌ (실제 DB에는 없음!)
- `used_at`: `TIMESTAMP` ❌ (실제 DB에는 없음!)

**문제점**: `backend.py`에서 사용하는 `coupons` 테이블 구조가 실제 DB와 완전히 다름!

**실제 사용해야 할 구조**:
- 쿠폰 발급 시 `user_coupons` 테이블을 사용해야 함 (아직 확인 안 됨)
- 또는 별도의 쿠폰 발급 테이블 필요

---

### 4. `referrals` 테이블 ✅

#### 실제 DB 스키마:
- `referral_id`: `bigint` (BIGSERIAL) ✅
- `referrer_user_id`: `bigint` ✅
- `referred_user_id`: `bigint` ✅
- `status`: `referral_status` (ENUM, 기본값: 'approved') ✅

**상태**: ✅ `backend.py`의 사용법과 일치 (status 기본값만 'pending' vs 'approved')

---

## 🔧 수정 필요 사항

### 우선순위: 높음 🔴

1. **`orders` 테이블 관련 코드 수정**
   - `create_order` 함수에서 `price`, `total_price`, `amount` → `total_amount`, `final_amount`로 수정
   - `get_orders` 함수에서 스키마에 맞게 수정
   - 기타 `orders` 테이블 조회/수정하는 모든 부분

2. **`commissions` 테이블 관련 코드 수정**
   - `create_order` 함수에서 커미션 INSERT 시 컬럼명 수정
   - `get_commissions` 함수에서 스키마에 맞게 수정

3. **`coupons` 테이블 관련 코드 수정**
   - `sync_user` 함수에서 쿠폰 발급 로직 수정
   - `create_order` 함수에서 쿠폰 조회/사용 로직 수정
   - `user_coupons` 테이블 확인 필요

### 우선순위: 중간 🟡

4. **스키마 정의 정리**
   - `backend.py`의 `CREATE TABLE IF NOT EXISTS` 정의들을 실제 DB와 일치하도록 수정
   - (하지만 실제로는 기존 테이블이 사용되므로 코드 실행에는 영향 없음)

---

## 📝 수정 체크리스트

- [ ] `orders` 테이블 관련 코드 수정
  - [ ] `create_order` 함수 수정
  - [ ] `get_orders` 함수 수정
  - [ ] `get_commissions` 함수에서 `orders` 조회 부분 수정
  - [ ] 기타 `orders` 테이블 사용 부분 확인

- [ ] `commissions` 테이블 관련 코드 수정
  - [ ] `create_order` 함수에서 커미션 INSERT 수정
  - [ ] `get_commissions` 함수 수정

- [ ] `coupons` 테이블 관련 코드 수정
  - [ ] `user_coupons` 테이블 스키마 확인
  - [ ] `sync_user` 함수에서 쿠폰 발급 로직 수정
  - [ ] `create_order` 함수에서 쿠폰 조회/사용 로직 수정

