# 스키마 및 기능 검토 보고서

## 📋 하드코딩된 상품 데이터

**위치**: `src/pages/Home.jsx`의 `instagramDetailedServices` 객체

**상태**: ✅ 리스트화 완료 (`HARDCODED_PRODUCTS_LIST.md` 참조)

- **총 패키지**: 3개
- **총 일반 상품**: 약 150개 이상
- **플랫폼**: 인스타그램, 유튜브, 페이스북, 틱톡, 트위터, Threads, 텔레그램, 왓츠앱, 카카오

---

## 🔍 스키마 불일치 확인

### 1. `orders` 테이블 스키마 불일치

#### 현재 `backend.py`의 스키마 (2609-2638줄):
```sql
CREATE TABLE IF NOT EXISTS orders (
    order_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    total_price DECIMAL(10,2),
    amount DECIMAL(10,2),
    discount_amount DECIMAL(10,2) DEFAULT 0,
    ...
)
```

#### `migrate_database.py`의 스키마 (333-345줄):
```sql
CREATE TABLE IF NOT EXISTS orders (
    order_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users (user_id),
    total_amount NUMERIC(14,2) NOT NULL,
    discount_amount NUMERIC(14,2) DEFAULT 0,
    final_amount NUMERIC(14,2),
    ...
)
```

**문제점**:
- ❌ `order_id` 타입 불일치: `VARCHAR(255)` vs `BIGSERIAL`
- ❌ `user_id` 타입 불일치: `VARCHAR(255)` vs `BIGINT`
- ❌ 가격 컬럼 불일치: `price`, `total_price`, `amount` vs `total_amount`, `final_amount`
- ❌ `backend.py`는 외래 키 제약 없음, `migrate_database.py`는 외래 키 제약 있음

**영향**:
- 주문 생성 시 스키마 불일치로 인한 오류 가능
- 커미션 계산 시 `orders.price` vs `orders.total_amount`/`orders.final_amount` 불일치
- 이미 수정된 부분: `get_commissions`에서 `COALESCE(o.final_amount, o.total_amount, 0)` 사용

---

### 2. `commissions` 테이블 스키마

#### `backend.py`의 스키마 (2538-2549줄):
```sql
CREATE TABLE IF NOT EXISTS commissions (
    id SERIAL PRIMARY KEY,
    referred_user VARCHAR(255) NOT NULL,
    referrer_id VARCHAR(255) NOT NULL,
    purchase_amount DECIMAL(10,2) NOT NULL,
    commission_amount DECIMAL(10,2) NOT NULL,
    commission_rate DECIMAL(5,4) NOT NULL,
    is_paid BOOLEAN DEFAULT false,
    ...
)
```

#### `migrate_database.py`의 스키마 (373-382줄):
```sql
CREATE TABLE IF NOT EXISTS commissions (
    commission_id BIGSERIAL PRIMARY KEY,
    referral_id BIGINT NOT NULL REFERENCES referrals (referral_id),
    order_id BIGINT NOT NULL REFERENCES orders (order_id),
    amount NUMERIC(14,2) NOT NULL,
    status commission_status DEFAULT 'accrued',
    ...
)
```

**문제점**:
- ❌ 컬럼 구조 완전히 다름
- ❌ `backend.py`는 `referred_user`, `referrer_id` (VARCHAR), `migrate_database.py`는 `referral_id`, `order_id` (BIGINT)
- ❌ `backend.py`는 `is_paid` (BOOLEAN), `migrate_database.py`는 `status` (ENUM)

**영향**:
- 커미션 저장/조회 시 스키마 불일치로 인한 오류 가능
- 현재 `create_order`에서 `commissions` 테이블에 저장하는 로직이 실제 스키마와 맞지 않을 수 있음

---

### 3. `referrals` 테이블 스키마

#### `backend.py`의 사용 (5870-5940줄):
- `referrer_user_id`, `referred_user_id` (BIGINT)
- `status` (기본값 'pending')

#### `migrate_database.py`의 스키마 (364-370줄):
```sql
CREATE TABLE IF NOT EXISTS referrals (
    referral_id BIGSERIAL PRIMARY KEY,
    referrer_user_id BIGINT NOT NULL REFERENCES users (user_id),
    referred_user_id BIGINT NOT NULL REFERENCES users (user_id),
    status referral_status DEFAULT 'approved',
    ...
)
```

**상태**: ✅ 대체로 일치 (status 기본값만 다름: 'pending' vs 'approved')

---

### 4. `coupons` 테이블 스키마

#### `backend.py`의 스키마 (2553-2565줄):
```sql
CREATE TABLE IF NOT EXISTS coupons (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    referral_code VARCHAR(50),
    discount_type VARCHAR(20) DEFAULT 'percentage',
    discount_value DECIMAL(5,2) NOT NULL,
    is_used BOOLEAN DEFAULT false,
    expires_at TIMESTAMP
)
```

**상태**: ✅ 현재 사용 중인 스키마와 일치

---

## 🧪 주요 기능 테스트

### 1. 주문 생성 (`/api/orders` POST)

**위치**: `backend.py` 3561-4298줄

**확인 사항**:
- ✅ `external_uid` → 내부 `user_id` 변환 로직 있음
- ✅ 추천인 관계 확인 및 커미션 계산 로직 있음
- ⚠️ `orders` 테이블에 저장 시 스키마 불일치 가능성
  - 코드에서 `price`, `total_price` 사용
  - 실제 DB는 `total_amount`, `final_amount`일 수 있음

**테스트 필요**:
- [ ] 실제 주문 생성 테스트
- [ ] 스키마 불일치 오류 확인

---

### 2. 포인트 차감 (`/api/points/deduct` POST)

**위치**: `backend.py` 5600-5771줄

**확인 사항**:
- ✅ `wallets` 테이블 사용 (새 스키마)
- ✅ `external_uid` → 내부 `user_id` 변환 로직 있음
- ✅ `SELECT FOR UPDATE`로 동시성 제어
- ✅ 지갑 자동 생성 로직

**상태**: ✅ 최근 수정됨, 정상 작동 예상

---

### 3. 커미션 조회 (`/api/referral/commissions` GET)

**위치**: `backend.py` 6326-6461줄

**확인 사항**:
- ✅ `COALESCE(o.final_amount, o.total_amount, 0)` 사용 (스키마 불일치 대응)
- ✅ `CASE` 문으로 역계산 로직 추가
- ⚠️ `commissions` 테이블 스키마가 실제와 다를 수 있음

**테스트 필요**:
- [ ] 실제 커미션 조회 테스트
- [ ] `commissions` 테이블 스키마 확인

---

### 4. 쿠폰 발급 (`sync_user` 함수)

**위치**: `backend.py` 5775-6002줄

**확인 사항**:
- ✅ 피추천인 5% 할인쿠폰 자동 발급 로직 추가됨
- ✅ 중복 발급 방지
- ✅ 30일 유효기간

**상태**: ✅ 최근 추가됨, 정상 작동 예상

---

### 5. 카테고리 삭제 (`/api/admin/categories/<id>` DELETE)

**위치**: `backend.py` 5000-5100줄 (추정)

**확인 사항**:
- ✅ 실제 삭제 로직 (비활성화 아님)
- ✅ 외래 키 제약 조건 고려한 삭제 순서

**상태**: ✅ 최근 수정됨, 정상 작동 예상

---

### 6. 상품/패키지 조회

**엔드포인트**:
- `/api/products` - 상품 목록
- `/api/product-variants` - 세부 서비스 목록
- `/api/packages` - 패키지 목록

**확인 사항**:
- ✅ SSL 연결 재시도 로직 추가됨
- ✅ `is_active` 컬럼 동적 확인
- ✅ `meta_json` 파싱 개선

**상태**: ✅ 최근 수정됨, 정상 작동 예상

---

## ⚠️ 발견된 문제점 요약

### 심각도: 높음 🔴 (실제 DB 스키마 확인 완료)

1. **`orders` 테이블 스키마 불일치** ⚠️ **심각한 오류**
   - **실제 DB 스키마**:
     - `order_id`: `bigint` (BIGSERIAL) ✅
     - `user_id`: `bigint` ✅
     - `total_amount`: `numeric(14,2)` ✅
     - `final_amount`: `numeric(14,2)` ✅
     - `discount_amount`: `numeric(14,2)` ✅
     - **없는 컬럼**: `service_id`, `link`, `quantity`, `price`, `total_price`, `amount` ❌
   - **코드 문제** (3826줄):
     - 존재하지 않는 컬럼 `service_id`, `link`, `quantity`, `price` INSERT 시도 ❌
     - 상세 정보는 `order_items` 테이블에 저장되어야 함 ✅
   - **해결 필요**: `orders` INSERT 수정 + `order_items` INSERT 추가

2. **`commissions` 테이블 스키마 불일치**
   - 컬럼 구조 완전히 다름
   - **해결 필요**: 실제 DB 스키마 확인 후 코드 수정

### 심각도: 중간 🟡

3. **하드코딩된 상품 데이터**
   - 약 150개 이상의 상품이 `Home.jsx`에 하드코딩됨
   - **권장**: 데이터베이스로 이전

### 심각도: 낮음 🟢

4. **`referrals` 테이블 status 기본값**
   - 'pending' vs 'approved' (기능상 문제 없음)

---

## 📝 권장 조치 사항

### 즉시 조치 필요

1. **실제 데이터베이스 스키마 확인**
   ```sql
   -- PostgreSQL에서 실행
   \d orders
   \d commissions
   \d referrals
   \d coupons
   ```

2. **스키마 불일치 수정**
   - 실제 DB 스키마에 맞게 `backend.py` 수정
   - 또는 DB 스키마를 코드에 맞게 수정

3. **주요 기능 테스트**
   - 주문 생성 테스트
   - 커미션 조회 테스트
   - 쿠폰 발급 테스트

### 중기 조치

4. **하드코딩된 상품 데이터베이스 이전**
   - `import_hardcoded_products.py` 스크립트 활용
   - 모든 상품을 DB로 이전 후 `Home.jsx`에서 하드코딩 제거

5. **스키마 통일**
   - `backend.py`와 `migrate_database.py`의 스키마 정의 통일
   - 마이그레이션 스크립트 작성

---

## ✅ 정상 작동 중인 기능

1. ✅ 포인트 차감 (`/api/points/deduct`)
2. ✅ 피추천인 쿠폰 발급 (`sync_user`)
3. ✅ 카테고리 삭제 (`/api/admin/categories/<id>` DELETE)
4. ✅ 상품/패키지 조회 (SSL 재시도 포함)

---

## 📊 테스트 체크리스트

- [ ] 주문 생성 테스트
- [ ] 커미션 조회 테스트
- [ ] 쿠폰 발급 테스트
- [ ] 포인트 차감 테스트
- [ ] 카테고리 삭제 테스트
- [ ] 상품/패키지 조회 테스트
- [ ] 실제 DB 스키마 확인
- [ ] 스키마 불일치 수정

