# 데이터베이스 스키마 설명

## 📌 현재 사용 중인 스키마

프로젝트는 **두 가지 데이터베이스**를 지원합니다:
- **PostgreSQL** (Supabase/프로덕션)
- **SQLite** (로컬 개발)

실제 스키마는 `backend.py`의 `init_database()` 함수에서 **동적으로 생성**됩니다.

---

## 🗂️ 주요 테이블 스키마

### 1. `users` 테이블

**PostgreSQL:**
```sql
CREATE TABLE users (
    user_id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    google_id VARCHAR(255),
    kakao_id VARCHAR(255),
    profile_image TEXT,
    last_login TIMESTAMP,
    last_activity TIMESTAMP DEFAULT NOW(),
    is_admin BOOLEAN DEFAULT FALSE,
    external_uid VARCHAR(255),  -- Supabase UID
    phone_number VARCHAR(255),
    signup_source VARCHAR(255),
    account_type VARCHAR(255),  -- 'individual' or 'business'
    business_number VARCHAR(255),
    business_name VARCHAR(255),
    representative VARCHAR(255),
    contact_phone VARCHAR(255),
    contact_email VARCHAR(255),
    referral_code VARCHAR(255),
    username VARCHAR(255),
    commission_rate REAL DEFAULT 0.1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
)
```

**SQLite:**
```sql
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    display_name TEXT,
    google_id TEXT,
    kakao_id TEXT,
    profile_image TEXT,
    last_login TIMESTAMP,
    is_admin INTEGER DEFAULT 0,  -- 0 or 1
    external_uid TEXT,
    phone_number TEXT,
    signup_source TEXT,
    account_type TEXT,
    business_number TEXT,
    business_name TEXT,
    representative TEXT,
    contact_phone TEXT,
    contact_email TEXT,
    referral_code TEXT,
    username TEXT,
    commission_rate REAL DEFAULT 0.1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

---

### 2. `orders` 테이블

**PostgreSQL:**
```sql
CREATE TABLE orders (
    order_id VARCHAR(255) PRIMARY KEY,  -- 타임스탬프 기반 (예: 1764079688102)
    user_id VARCHAR(255) NOT NULL,
    total_amount NUMERIC(14,2),
    discount_amount NUMERIC(14,2) DEFAULT 0,
    final_amount NUMERIC(14,2),
    status VARCHAR(50) DEFAULT 'pending',
    smm_panel_order_id VARCHAR(255),
    detailed_service TEXT,
    package_steps JSONB,  -- 패키지 단계 정보
    link TEXT,  -- 주문 링크
    quantity INTEGER DEFAULT 0,  -- 주문 수량
    is_scheduled BOOLEAN DEFAULT FALSE,
    scheduled_datetime TIMESTAMP,
    is_split_delivery BOOLEAN DEFAULT FALSE,
    split_days INTEGER DEFAULT 0,
    split_quantity INTEGER DEFAULT 0,
    referrer_user_id VARCHAR(255),
    coupon_id BIGINT,
    notes TEXT,  -- 주문 메모
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
)
```

**SQLite:**
```sql
CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 또는 VARCHAR(255)
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
```

**⚠️ 주의사항:**
- PostgreSQL과 SQLite의 스키마가 **다릅니다**
- PostgreSQL은 `total_amount`, `final_amount` 사용
- SQLite는 `price`, `total_price` 사용
- 코드에서 `COALESCE(o.final_amount, o.total_amount, 0)` 또는 `COALESCE(o.price, 0)`로 처리

---

### 3. `order_items` 테이블

**PostgreSQL:**
```sql
CREATE TABLE order_items (
    order_item_id BIGSERIAL PRIMARY KEY,
    order_id VARCHAR(255) NOT NULL,
    variant_id BIGINT,  -- product_variants 참조
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(14,2) NOT NULL,
    line_amount NUMERIC(14,2),
    link TEXT,  -- 주문 링크
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
)
```

**SQLite:**
```sql
CREATE TABLE order_items (
    order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,
    variant_id INTEGER,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    line_amount REAL,
    link TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

---

### 4. `products` 및 `product_variants` 테이블

**PostgreSQL:**
```sql
CREATE TABLE products (
    product_id BIGSERIAL PRIMARY KEY,
    category_id BIGINT REFERENCES categories(category_id),
    name VARCHAR(150) NOT NULL,
    description TEXT,
    is_domestic BOOLEAN DEFAULT TRUE,
    auto_tag BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
)

CREATE TABLE product_variants (
    variant_id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES products(product_id),
    name VARCHAR(255) NOT NULL,
    price NUMERIC(14,2) NOT NULL,
    original_cost NUMERIC(14,2) DEFAULT 0,  -- 원가
    min_quantity INTEGER,
    max_quantity INTEGER,
    delivery_time_days INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    meta_json JSONB,  -- SMM Panel 서비스 ID 등 메타 정보
    api_endpoint VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
)
```

**SQLite:**
```sql
CREATE TABLE products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER,
    name TEXT NOT NULL,
    description TEXT,
    is_domestic INTEGER DEFAULT 1,
    auto_tag INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

CREATE TABLE product_variants (
    variant_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    price REAL NOT NULL,
    original_cost REAL DEFAULT 0,
    min_quantity INTEGER,
    max_quantity INTEGER,
    delivery_time_days INTEGER,
    is_active INTEGER DEFAULT 1,
    meta_json TEXT,  -- JSON 문자열
    api_endpoint TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

---

### 5. `packages` 및 `package_items` 테이블

**PostgreSQL:**
```sql
CREATE TABLE packages (
    package_id BIGSERIAL PRIMARY KEY,
    category_id BIGINT REFERENCES categories(category_id),
    name VARCHAR(150) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
)

CREATE TABLE package_items (
    package_item_id BIGSERIAL PRIMARY KEY,
    package_id BIGINT NOT NULL REFERENCES packages(package_id),
    variant_id BIGINT NOT NULL REFERENCES product_variants(variant_id),
    step INTEGER NOT NULL,  -- 단계 번호
    term_value INTEGER,  -- 지연 시간 값
    term_unit VARCHAR(50),  -- 지연 시간 단위 (minute, hour, day)
    quantity INTEGER,  -- 수량
    repeat_count INTEGER,  -- 반복 횟수
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
)
```

---

### 6. `execution_progress` 테이블 (패키지 스케줄링)

**PostgreSQL:**
```sql
CREATE TABLE execution_progress (
    exec_id BIGSERIAL PRIMARY KEY,
    order_id VARCHAR(255) NOT NULL,
    exec_type VARCHAR(50) NOT NULL,  -- 'package'
    step_number INTEGER NOT NULL,
    step_name VARCHAR(255),
    service_id VARCHAR(255),
    quantity INTEGER,
    scheduled_datetime TIMESTAMP,  -- ⭐ 스케줄러가 확인하는 시간
    status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'running', 'completed', 'failed'
    smm_panel_order_id VARCHAR(255),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    failed_at TIMESTAMP
)
```

**용도:**
- 패키지 주문의 각 단계를 스케줄링
- `scheduled_datetime`이 지나면 크론잡(`/api/cron/process-package-steps`)이 처리
- 스레드 기반 스케줄러의 대체/보완 역할

---

### 7. `commission_ledger` 테이블 (커미션 원장)

**PostgreSQL:**
```sql
CREATE TABLE commission_ledger (
    ledger_id BIGSERIAL PRIMARY KEY,
    referral_code VARCHAR(50) NOT NULL,
    referrer_user_id VARCHAR(255) NOT NULL,
    referred_user_id VARCHAR(255),
    order_id VARCHAR(255),
    event VARCHAR(50) NOT NULL,  -- 'earn', 'payout', 'adjust', 'reverse'
    base_amount NUMERIC(10,2),
    commission_rate NUMERIC(5,4),
    amount NUMERIC(10,2) NOT NULL,  -- +credit / -debit
    status VARCHAR(50) DEFAULT 'confirmed',  -- 'pending', 'confirmed', 'cancelled'
    notes TEXT,
    external_ref VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    confirmed_at TIMESTAMP
)
```

**SQLite:**
```sql
CREATE TABLE commission_ledger (
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
```

**용도:**
- 모든 커미션 거래를 기록하는 통합 원장
- 잔액 계산: `SUM(amount) WHERE status='confirmed'`
- 출금 요청 시 `event='payout'`로 기록

---

## 🔄 스키마 버전 관리

### 현재 스키마 버전
- **PostgreSQL**: `backend.py`의 `init_database()`에서 동적 생성
- **SQLite**: `backend.py`의 `init_database()`에서 동적 생성
- **마이그레이션**: `migrate_database.py` (PostgreSQL 전용)

### 스키마 불일치 이슈

1. **`orders` 테이블:**
   - PostgreSQL: `total_amount`, `final_amount` 사용
   - SQLite: `price`, `total_price` 사용
   - **해결**: 코드에서 `COALESCE` 사용

2. **`order_id` 타입:**
   - PostgreSQL: `VARCHAR(255)` (타임스탬프 문자열)
   - SQLite: `INTEGER` 또는 `VARCHAR(255)`
   - **해결**: 코드에서 문자열로 통일

3. **`user_id` 타입:**
   - PostgreSQL: `VARCHAR(255)` (Supabase UID)
   - SQLite: `TEXT`
   - **해결**: 모두 문자열로 처리

---

## 📝 주요 ENUM 타입 (PostgreSQL)

```sql
-- order_status
CREATE TYPE order_status AS ENUM (
    'pending',
    'paid',
    'processing',
    'completed',
    'canceled',
    'refunded',
    'failed'
);

-- commission_status
CREATE TYPE commission_status AS ENUM (
    'accrued',
    'void',
    'paid_out'
);
```

---

## 🚨 주의사항

1. **스키마 불일치**: PostgreSQL과 SQLite의 스키마가 다르므로 코드에서 조건부 처리 필요
2. **동적 스키마**: `init_database()`에서 컬럼을 동적으로 추가하므로, 기존 데이터베이스에 컬럼이 없으면 자동 추가
3. **레거시 테이블**: `DATABASE_SCHEMA_OPTIMIZED.sql`은 참고용이며, 실제로는 `backend.py`의 스키마가 사용됨
4. **마이그레이션**: `migrate_database.py`는 PostgreSQL 전용이며, 새 스키마로 마이그레이션하는 용도

---

## 📊 스키마 파일 위치

1. **`DATABASE_SCHEMA_OPTIMIZED.sql`**: MySQL/MariaDB용 레거시 스키마 (참고용)
2. **`migrate_database.py`**: PostgreSQL 새 스키마 마이그레이션 스크립트
3. **`backend.py`의 `init_database()`**: 실제 런타임에서 사용되는 스키마 (PostgreSQL + SQLite)

