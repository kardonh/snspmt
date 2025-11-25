# 문제점 수정 이유 및 영향 분석

## 🔴 문제점 1: `execution_progress` 테이블 모순

### 📍 현재 상황
- **코드 위치**: `backend.py` 3613줄
- **문제**: "새 스키마에서는 work_jobs 사용하므로 execution_progress는 스킵"이라고 주석이 있지만, 실제로는 `execution_progress`를 계속 사용 중

### 🔍 실제 사용 위치
1. **1406줄**: 예약 주문 생성 시 `INSERT INTO execution_progress`
2. **2370줄**: 패키지 단계 처리 시 `INSERT INTO execution_progress` (다음 단계 예약)
3. **15819줄**: 크론잡에서 `FROM execution_progress` 조회
4. **2243줄**: 패키지 단계 건너뛰기 시 `INSERT INTO execution_progress`

### ❌ 왜 수정해야 하는가?
1. **테이블이 없으면 INSERT 실패**: 
   - 예약 주문 생성 시 오류 발생
   - 패키지 주문의 다음 단계 예약 실패
   - 크론잡이 실행되지 않음

2. **패키지 스케줄링 완전 실패**:
   - 스레드 기반 스케줄러는 서버 재시작 시 사라짐
   - `execution_progress`가 없으면 복구 불가능
   - 패키지 주문이 중간에 멈춤

3. **데이터 일관성 문제**:
   - 일부는 `execution_progress`에 저장, 일부는 저장 안 됨
   - 패키지 진행 상황 추적 불가능

### ✅ 수정 방법
**삭제할 코드:**
```python
# backend.py 3591-3616줄
# 기존: execution_progress 테이블 생성 스킵
print("ℹ️ execution_progress 테이블 생성 스킵 (새 스키마에서는 work_jobs 사용)")
```

**추가할 코드:**
```python
# execution_progress 테이블 생성 (PostgreSQL)
if is_postgresql:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS execution_progress (
            exec_id BIGSERIAL PRIMARY KEY,
            order_id VARCHAR(255) NOT NULL,
            exec_type VARCHAR(50) NOT NULL,
            step_number INTEGER NOT NULL,
            step_name VARCHAR(255),
            service_id VARCHAR(255),
            quantity INTEGER,
            scheduled_datetime TIMESTAMP,
            status VARCHAR(50) DEFAULT 'pending',
            smm_panel_order_id VARCHAR(255),
            error_message TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            completed_at TIMESTAMP,
            failed_at TIMESTAMP,
            UNIQUE(order_id, exec_type, step_number)
        )
    """)
    print("✅ execution_progress 테이블 생성 완료 (PostgreSQL)")
```

### 📊 수정 후 영향

#### ✅ 긍정적 영향
1. **패키지 스케줄링 정상 작동**:
   - 예약 주문 생성 시 `execution_progress`에 저장 성공
   - 패키지 단계 예약 정보 저장 성공
   - 크론잡이 정상적으로 단계 처리

2. **서버 재시작 후 복구 가능**:
   - 스레드가 사라져도 `execution_progress`에서 복구
   - `scheduled_datetime`을 확인하여 누락된 단계 처리

3. **데이터 추적 가능**:
   - 패키지 진행 상황을 DB에서 확인 가능
   - 관리자가 패키지 상태 모니터링 가능

#### ⚠️ 부정적 영향 (없음)
- 기존 코드는 이미 `execution_progress`를 사용 중이므로 추가 영향 없음
- 테이블만 생성하면 기존 코드가 정상 작동

#### 🔄 코드 삭제 시 영향
- **삭제하면 안 됨**: 테이블 생성 코드를 삭제하면 INSERT 실패
- **기존 INSERT 코드 삭제 시**: 패키지 스케줄링 완전 실패

#### ➕ 코드 추가 시 영향
- **테이블 생성 코드 추가**: 정상 작동, 영향 없음
- **인덱스 추가**: 성능 향상 (긍정적)

---

## 🔴 문제점 2: `commission_ledger` vs `commissions` 혼용

### 📍 현재 상황
- **코드 위치**: `backend.py` 3441줄
- **문제**: "새 스키마에서는 commissions 테이블 사용"이라고 주석이 있지만, 실제로는 `commission_ledger`를 사용

### 🔍 실제 사용 위치
1. **SQLite**: `commission_ledger` 테이블 생성 (3956줄)
2. **PostgreSQL**: `commissions` 테이블 사용 (12029줄)
3. **`get_commission_points()`**: `commission_ledger` 조회 (코드 확인 필요)

### ❌ 왜 수정해야 하는가?
1. **데이터베이스별 다른 테이블 사용**:
   - PostgreSQL: `commissions` 테이블
   - SQLite: `commission_ledger` 테이블
   - 코드에서 조건부 처리 필요

2. **커미션 잔액 계산 불일치**:
   - PostgreSQL과 SQLite에서 다른 로직 사용
   - 잔액이 다르게 계산될 수 있음

3. **출금 요청 처리 오류**:
   - `request_withdrawal()`에서 어떤 테이블을 사용하는지 불명확
   - 출금 요청이 제대로 기록되지 않을 수 있음

### ✅ 수정 방법
**옵션 1: `commission_ledger`로 통일 (권장)**
- 이유: SQLite에서 이미 사용 중, 통합 원장 개념
- PostgreSQL에서도 `commission_ledger` 사용

**옵션 2: `commissions`로 통일**
- 이유: 새 스키마 기준
- SQLite도 `commissions`로 마이그레이션

**권장: 옵션 1 (`commission_ledger`로 통일)**

**수정할 코드:**
```python
# backend.py 3441줄
# 기존:
print("ℹ️ commission_ledger 테이블 생성 스킵 (새 스키마에서는 commissions 테이블 사용)")

# 수정:
# commission_ledger 테이블 생성 (통합 원장)
if is_postgresql:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS commission_ledger (
            ledger_id BIGSERIAL PRIMARY KEY,
            referral_code VARCHAR(50) NOT NULL,
            referrer_user_id VARCHAR(255) NOT NULL,
            referred_user_id VARCHAR(255),
            order_id VARCHAR(255),
            event VARCHAR(50) NOT NULL,
            base_amount NUMERIC(10,2),
            commission_rate NUMERIC(5,4),
            amount NUMERIC(10,2) NOT NULL,
            status VARCHAR(50) DEFAULT 'confirmed',
            notes TEXT,
            external_ref VARCHAR(100),
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            confirmed_at TIMESTAMP
        )
    """)
    print("✅ commission_ledger 테이블 생성 완료 (PostgreSQL)")
```

### 📊 수정 후 영향

#### ✅ 긍정적 영향
1. **일관된 커미션 관리**:
   - PostgreSQL과 SQLite에서 동일한 테이블 사용
   - 커미션 잔액 계산 일관성

2. **통합 원장 개념**:
   - 모든 커미션 거래를 한 테이블에서 관리
   - `event` 필드로 거래 유형 구분 (earn, payout, adjust, reverse)

3. **출금 요청 처리 명확화**:
   - `event='payout'`으로 출금 기록
   - 잔액 계산: `SUM(amount) WHERE status='confirmed'`

#### ⚠️ 부정적 영향
1. **기존 `commissions` 테이블 데이터 마이그레이션 필요**:
   - PostgreSQL에 기존 `commissions` 데이터가 있으면 마이그레이션 필요
   - 마이그레이션 스크립트 작성 필요

2. **기존 코드 수정 필요**:
   - `commissions` 테이블을 사용하는 코드를 `commission_ledger`로 변경
   - 예: `admin_get_commissions()` (12029줄)

#### 🔄 코드 삭제 시 영향
- **`commissions` 테이블 사용 코드 삭제**: 
  - PostgreSQL에서 커미션 조회 실패
  - 관리자 커미션 내역 조회 실패

- **`commission_ledger` 테이블 생성 코드 삭제**:
  - SQLite에서 커미션 기능 완전 실패
  - 출금 요청 처리 실패

#### ➕ 코드 추가 시 영향
- **`commission_ledger` 테이블 생성 코드 추가**:
  - PostgreSQL에서도 `commission_ledger` 사용 가능
  - 통합 원장으로 일관성 확보

- **마이그레이션 스크립트 추가**:
  - 기존 `commissions` 데이터를 `commission_ledger`로 이동
  - 데이터 손실 없이 마이그레이션

---

## 🟡 문제점 3: `orders` 테이블 컬럼명 불일치

### 📍 현재 상황
- **PostgreSQL**: `total_amount`, `final_amount` 사용
- **SQLite**: `price`, `total_price` 사용
- **코드**: `COALESCE(o.final_amount, o.total_amount, 0)` 사용 (6503줄)

### ❌ 왜 수정해야 하는가?
1. **일부 코드에서 직접 `price` 사용 가능**:
   - 레거시 코드에서 `o.price` 직접 사용 시 오류
   - PostgreSQL에서 `price` 컬럼이 없으면 실패

2. **코드 복잡도 증가**:
   - 매번 `COALESCE` 패턴 사용 필요
   - 실수로 잘못된 컬럼명 사용 가능

### ✅ 수정 방법
**옵션 1: 컬럼명 통일 (권장)**
- PostgreSQL과 SQLite 모두 `total_amount`, `final_amount` 사용
- SQLite 스키마 수정 필요

**옵션 2: COALESCE 패턴 일관성 유지**
- 모든 코드에서 `COALESCE` 패턴 사용
- 컬럼명은 그대로 유지

**권장: 옵션 1 (컬럼명 통일)**

**수정할 코드:**
```python
# SQLite orders 테이블 생성 부분 (3851줄)
# 기존:
price REAL NOT NULL,
total_price REAL,

# 수정:
total_amount REAL NOT NULL,
discount_amount REAL DEFAULT 0,
final_amount REAL,
```

### 📊 수정 후 영향

#### ✅ 긍정적 영향
1. **코드 단순화**:
   - `COALESCE` 패턴 제거 가능
   - 직접 `o.final_amount` 또는 `o.total_amount` 사용

2. **일관성 확보**:
   - PostgreSQL과 SQLite에서 동일한 컬럼명
   - 코드 유지보수 용이

#### ⚠️ 부정적 영향
1. **기존 SQLite 데이터 마이그레이션 필요**:
   - `price` → `total_amount`로 컬럼명 변경
   - `total_price` → `final_amount`로 컬럼명 변경
   - 마이그레이션 스크립트 필요

2. **기존 코드 수정 필요**:
   - SQLite에서 `price` 사용하는 코드 수정
   - 모든 코드에서 `total_amount`, `final_amount` 사용

#### 🔄 코드 삭제 시 영향
- **`COALESCE` 패턴 삭제**: 
  - 컬럼명이 통일되지 않으면 오류 발생
  - PostgreSQL과 SQLite 호환성 문제

- **기존 컬럼명 사용 코드 삭제**:
  - SQLite에서 주문 금액 조회 실패

#### ➕ 코드 추가 시 영향
- **컬럼명 통일 코드 추가**:
  - 일관성 확보 (긍정적)
  - 마이그레이션 필요 (주의)

---

## 🟡 문제점 4: `order_id` 타입 불일치

### 📍 현재 상황
- **`backend.py`**: `order_id VARCHAR(255)`
- **`migrate_database.py`**: `order_id BIGSERIAL`
- **실제 사용**: `int(time.time() * 1000)` (문자열로 변환)

### ❌ 왜 수정해야 하는가?
1. **스키마 불일치**:
   - 코드와 마이그레이션 스크립트가 다름
   - 혼란 야기

2. **타입 변환 오버헤드**:
   - `BIGSERIAL`인데 문자열로 저장
   - 불필요한 타입 변환

### ✅ 수정 방법
**옵션 1: `VARCHAR(255)`로 통일 (권장)**
- 이유: 현재 코드가 문자열 사용 중
- 타임스탬프 기반 ID 사용

**옵션 2: `BIGSERIAL`로 통일**
- 이유: 마이그레이션 스크립트 기준
- 자동 증가 ID 사용

**권장: 옵션 1 (`VARCHAR(255)`로 통일)**

### 📊 수정 후 영향

#### ✅ 긍정적 영향
1. **일관성 확보**:
   - 코드와 스키마 일치
   - 혼란 제거

#### ⚠️ 부정적 영향
1. **기존 데이터 마이그레이션 필요**:
   - `BIGSERIAL` → `VARCHAR(255)`로 변경
   - 기존 숫자 ID를 문자열로 변환

#### 🔄 코드 삭제 시 영향
- **타입 변환 코드 삭제**: 영향 없음 (이미 문자열 사용)

#### ➕ 코드 추가 시 영향
- **타입 통일 코드 추가**: 일관성 확보 (긍정적)

---

## 🟡 문제점 5: `user_id` 타입 불일치

### 📍 현재 상황
- **`backend.py`**: `user_id VARCHAR(255)`
- **`migrate_database.py`**: `user_id BIGINT`
- **실제 사용**: Supabase UID (문자열)

### ❌ 왜 수정해야 하는가?
1. **Supabase UID는 문자열**:
   - `external_uid`는 문자열
   - `user_id`를 `BIGINT`로 하면 매핑 불가능

2. **외래 키 제약 조건 위반**:
   - `BIGINT`인데 문자열로 저장 시도
   - 외래 키 제약 조건 실패

### ✅ 수정 방법
**옵션 1: `user_id`를 `VARCHAR(255)`로 통일 (권장)**
- 이유: Supabase UID 사용
- `external_uid`와 일치

**옵션 2: `user_id`를 `BIGINT`로 유지, `external_uid` 사용**
- 이유: 마이그레이션 스크립트 기준
- 내부 ID와 외부 ID 분리

**권장: 옵션 1 (`VARCHAR(255)`로 통일)**

### 📊 수정 후 영향

#### ✅ 긍정적 영향
1. **Supabase UID 직접 사용**:
   - `external_uid`와 `user_id` 일치
   - 매핑 불필요

2. **외래 키 제약 조건 정상 작동**:
   - 타입 일치로 제약 조건 만족

#### ⚠️ 부정적 영향
1. **기존 데이터 마이그레이션 필요**:
   - `BIGINT` → `VARCHAR(255)`로 변경
   - 기존 숫자 ID를 문자열로 변환

#### 🔄 코드 삭제 시 영향
- **타입 변환 코드 삭제**: 영향 없음 (이미 문자열 사용)

#### ➕ 코드 추가 시 영향
- **타입 통일 코드 추가**: 일관성 확보 (긍정적)

---

## 📋 종합 수정 계획

### 우선순위 1: `execution_progress` 테이블 생성 복구
- **영향**: 패키지 스케줄링 정상 작동
- **위험도**: 낮음 (테이블만 생성)

### 우선순위 2: `commission_ledger`로 통일
- **영향**: 커미션 관리 일관성
- **위험도**: 중간 (마이그레이션 필요)

### 우선순위 3: 컬럼명 통일
- **영향**: 코드 단순화
- **위험도**: 중간 (마이그레이션 필요)

### 우선순위 4: 타입 통일
- **영향**: 일관성 확보
- **위험도**: 낮음 (현재 작동 중)

