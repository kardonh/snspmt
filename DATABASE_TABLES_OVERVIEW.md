# 데이터베이스 테이블 개요

## ✅ 실제로 사용되는 테이블 (Active Tables)

### 1. 사용자 및 인증 관련
- **`users`** ⭐ **핵심 테이블**
  - 사용자 기본 정보 (이메일, 이름, 소셜 로그인 ID 등)
  - 비즈니스 계정 정보 (사업자번호, 대표자명 등)
  - 관리자 권한 (`is_admin`)
  - **사용 위치**: 모든 인증, 사용자 정보 조회/수정

- **`points`** ⭐ **핵심 테이블**
  - 사용자 포인트 잔액
  - **사용 위치**: 포인트 조회, 차감, 충전

- **`point_purchases`** ⭐ **핵심 테이블**
  - 포인트 구매 내역
  - 입금 정보, 승인 상태
  - **사용 위치**: 포인트 구매 요청, 관리자 승인

### 2. 상품 및 주문 관련
- **`categories`** ⭐ **핵심 테이블**
  - 상품 카테고리
  - **사용 위치**: 카테고리 목록 조회

- **`products`** ⭐ **핵심 테이블**
  - 상품 기본 정보
  - **사용 위치**: 상품 목록, 상세 조회

- **`product_variants`** ⭐ **핵심 테이블**
  - 상품 옵션 (가격, 수량, SMM Panel 서비스 ID 등)
  - **사용 위치**: 상품 옵션 조회, 주문 생성

- **`packages`** ⭐ **핵심 테이블**
  - 패키지 상품 정보
  - **사용 위치**: 패키지 상품 목록 조회

- **`package_items`** ⭐ **핵심 테이블**
  - 패키지 상품의 각 단계 정보
  - **사용 위치**: 패키지 상품 상세 조회

- **`orders`** ⭐ **핵심 테이블**
  - 주문 헤더 정보
  - 주문 상태, 금액, 예약 정보, 패키지 단계 정보
  - **사용 위치**: 주문 생성, 조회, 상태 업데이트

- **`order_items`** ⭐ **핵심 테이블**
  - 주문 상세 항목 (링크, 수량, 가격 등)
  - **사용 위치**: 주문 상세 조회, 패키지 주문 단계별 저장

### 3. 추천인 및 커미션 관련
- **`referral_codes`** ⭐ **핵심 테이블**
  - 추천인 코드 정보
  - **사용 위치**: 추천인 코드 생성, 검증, 커미션 조회

- **`commissions`** (PostgreSQL만)
  - 커미션 내역
  - **사용 위치**: 커미션 조회 (PostgreSQL)

- **`commission_ledger`** ⭐ **핵심 테이블**
  - 커미션 원장 (통합 테이블)
  - **사용 위치**: 커미션 적립, 출금, 잔액 조회 (SQLite 및 PostgreSQL)

- **`payouts`** (PostgreSQL만)
  - 출금 내역
  - **사용 위치**: 출금 내역 조회 (PostgreSQL)

- **`payout_requests`** ⭐ **핵심 테이블**
  - 출금 요청 정보
  - **사용 위치**: 출금 요청, 관리자 승인

### 4. 주문 처리 및 스케줄링 관련
- **`execution_progress`** ⭐ **핵심 테이블**
  - 패키지 주문 단계별 진행 상황
  - 예약된 단계의 `scheduled_datetime` 저장
  - **사용 위치**: 패키지 단계 스케줄링, 크론잡에서 단계 처리

- **`work_jobs`** (PostgreSQL 새 스키마)
  - 작업 내역 (새 스키마)
  - **사용 위치**: 작업 상태 추적 (PostgreSQL)

- **`split_delivery_progress`** ⭐ **사용 중**
  - 분할 발송 진행 상황
  - **사용 위치**: 분할 발송 크론잡

### 5. 기타 기능
- **`wallets`** (PostgreSQL 새 스키마)
  - 지갑 정보 (새 스키마)
  - **사용 위치**: 지갑 관리 (PostgreSQL)

- **`coupons`** ⭐ **사용 중**
  - 쿠폰 정보
  - **사용 위치**: 쿠폰 생성, 사용, 관리

- **`notices`** ⭐ **사용 중**
  - 공지사항
  - **사용 위치**: 공지사항 조회, 관리

- **`blog_posts`** ⭐ **사용 중**
  - 블로그 포스트
  - **사용 위치**: 블로그 조회, 관리

---

## ❌ 사용되지 않는 테이블 (Deprecated/Unused Tables)

### 1. 레거시 테이블 (코드에 생성되지만 실제 사용 안 함)
- **`services`**
  - DATABASE_SCHEMA_OPTIMIZED.sql에 정의되어 있음
  - **실제 사용**: ❌ `products`와 `product_variants`로 대체됨
  - **상태**: 사용 안 함

- **`scheduled_orders`** (SQLite만)
  - SQLite에서만 생성됨
  - **실제 사용**: ❌ `orders.is_scheduled` 컬럼으로 대체됨
  - **상태**: 사용 안 함

- **`package_progress`** (SQLite만)
  - SQLite에서만 생성됨
  - **실제 사용**: ❌ `execution_progress`로 대체됨
  - **상태**: 사용 안 함

- **`merchants`**
  - migrate_database.py에 정의되어 있음
  - **실제 사용**: ❌ 코드에서 사용되지 않음
  - **상태**: 사용 안 함

---

## 📊 테이블 사용 현황 요약

### PostgreSQL (새 스키마)
- ✅ **사용 중**: users, points, orders, order_items, products, categories, product_variants, packages, package_items, point_purchases, referral_codes, commission_ledger, payouts, payout_requests, execution_progress, work_jobs, wallets, coupons, notices, blog_posts, split_delivery_progress
- ❌ **사용 안 함**: services, scheduled_orders, package_progress, merchants

### SQLite
- ✅ **사용 중**: users, points, orders, order_items, products, categories, product_variants, packages, package_items, point_purchases, referral_codes, commission_ledger, payout_requests, execution_progress, coupons, notices, blog_posts, split_delivery_progress
- ❌ **사용 안 함**: services, merchants
- ⚠️ **생성되지만 사용 안 함**: scheduled_orders, package_progress

---

## 🔄 테이블 관계도

```
users (사용자)
├── points (포인트)
├── point_purchases (포인트 구매)
├── referral_codes (추천인 코드)
├── orders (주문)
│   ├── order_items (주문 상세)
│   ├── execution_progress (패키지 단계 진행)
│   └── commission_ledger (커미션 원장)
└── payout_requests (출금 요청)

products (상품)
├── product_variants (상품 옵션)
└── packages (패키지 상품)
    └── package_items (패키지 단계)

categories (카테고리)
└── products (상품)
```

---

## 💡 주요 변경 사항

1. **서비스 테이블 제거**: `services` → `products` + `product_variants`로 대체
2. **예약 주문 통합**: `scheduled_orders` → `orders.is_scheduled` 컬럼으로 통합
3. **패키지 진행 통합**: `package_progress` → `execution_progress`로 통합
4. **커미션 통합**: `commissions` (PostgreSQL) + `commission_ledger` (SQLite) → `commission_ledger`로 통합 추세

---

## 🚨 주의사항

1. **SQLite의 레거시 테이블**: `scheduled_orders`, `package_progress`는 생성되지만 실제로는 사용되지 않음
2. **PostgreSQL 새 스키마**: `work_jobs`, `wallets`는 새 스키마에서만 사용
3. **execution_progress**: 패키지 단계 스케줄링의 핵심 테이블로, `scheduled_datetime`을 통해 크론잡이 처리

