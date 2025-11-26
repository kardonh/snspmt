# 수정 완료 사항 및 영향 분석

## ✅ 완료된 수정 사항

### 1. `execution_progress` 테이블 생성 복구

#### 📍 수정 위치
- **파일**: `backend.py`
- **줄 번호**: 3591-3616줄 → 수정됨

#### 🔧 수정 내용

**삭제된 코드:**
```python
# 기존: execution_progress 테이블 생성 스킵
print("ℹ️ execution_progress 테이블 생성 스킵 (새 스키마에서는 work_jobs 사용)")
print("ℹ️ execution_progress 인덱스 생성 스킵 (새 스키마에서는 work_jobs 사용)")
```

**추가된 코드:**
```python
# PostgreSQL용 execution_progress 테이블 생성
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

# SQLite용 execution_progress 테이블 생성
CREATE TABLE IF NOT EXISTS execution_progress (
    exec_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,
    exec_type TEXT NOT NULL,
    step_number INTEGER NOT NULL,
    ...
    UNIQUE(order_id, exec_type, step_number)
)
```

#### 📊 수정 후 영향

**✅ 긍정적 영향:**
1. **패키지 스케줄링 정상 작동**:
   - 예약 주문 생성 시 `execution_progress`에 저장 성공 (1406줄)
   - 패키지 단계 예약 정보 저장 성공 (2370줄)
   - 크론잡이 정상적으로 단계 처리 (15819줄)

2. **서버 재시작 후 복구 가능**:
   - 스레드가 사라져도 `execution_progress`에서 복구
   - `scheduled_datetime`을 확인하여 누락된 단계 처리

3. **데이터 추적 가능**:
   - 패키지 진행 상황을 DB에서 확인 가능
   - 관리자가 패키지 상태 모니터링 가능

**⚠️ 부정적 영향:**
- 없음 (기존 코드는 이미 `execution_progress`를 사용 중)

**🔄 코드 삭제 시 영향:**
- **테이블 생성 코드 삭제 시**: INSERT 실패, 패키지 스케줄링 완전 실패
- **기존 INSERT 코드 삭제 시**: 패키지 스케줄링 완전 실패

**➕ 코드 추가 시 영향:**
- **테이블 생성 코드 추가**: 정상 작동, 영향 없음
- **인덱스 추가**: 성능 향상 (긍정적)

---

### 2. `commission_ledger` 테이블 생성 복구 (PostgreSQL)

#### 📍 수정 위치
- **파일**: `backend.py`
- **줄 번호**: 3439-3447줄 → 수정됨

#### 🔧 수정 내용

**삭제된 코드:**
```python
# 기존: commission_ledger 테이블 생성 스킵
print("ℹ️ commission_ledger 테이블 생성 스킵 (새 스키마에서는 commissions 테이블 사용)")
print("ℹ️ commission_ledger 관련 코드 스킵 (새 스키마에서는 commissions 테이블 사용)")
print("ℹ️ commission_ledger 트리거 생성 스킵 (새 스키마에서는 commissions 테이블 사용)")
```

**추가된 코드:**
```python
# PostgreSQL용 commission_ledger 테이블 생성
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
```

#### 📊 수정 후 영향

**✅ 긍정적 영향:**
1. **PostgreSQL에서도 `commission_ledger` 사용 가능**:
   - `get_commission_points()` 함수가 정상 작동 (13791줄)
   - `request_withdrawal()` 함수가 정상 작동 (14190줄)

2. **통합 원장 개념**:
   - 모든 커미션 거래를 한 테이블에서 관리
   - `event` 필드로 거래 유형 구분 (earn, payout, adjust, reverse)

3. **일관성 확보**:
   - PostgreSQL과 SQLite에서 동일한 테이블 사용 가능
   - 커미션 잔액 계산 일관성

**⚠️ 부정적 영향:**
1. **기존 `commissions` 테이블과 혼용**:
   - 주문 생성 시 커미션 저장은 여전히 `commissions` 테이블 사용 (5947줄)
   - `admin_get_commissions()` 함수는 `commissions` 테이블 사용 (12142줄)

2. **데이터 불일치 가능**:
   - `commissions` 테이블과 `commission_ledger` 테이블에 데이터가 분산
   - 잔액 계산 시 불일치 가능

**🔄 코드 삭제 시 영향:**
- **테이블 생성 코드 삭제 시**: 
  - PostgreSQL에서 `get_commission_points()` 실패
  - `request_withdrawal()` 실패

**➕ 코드 추가 시 영향:**
- **테이블 생성 코드 추가**: 정상 작동, 영향 없음
- **인덱스 추가**: 성능 향상 (긍정적)

---

## ⚠️ 추가 수정 필요 사항

### 1. 주문 생성 시 커미션 저장을 `commission_ledger`로 변경

#### 📍 현재 상황
- **위치**: `backend.py` 5947줄 (PostgreSQL), 5959줄 (SQLite)
- **문제**: `commissions` 테이블에 저장 중

#### 🔧 수정 필요 코드

**PostgreSQL (5947줄):**
```python
# 기존:
INSERT INTO commissions (referral_id, order_id, amount, status, created_at)
VALUES (%s, %s, %s, 'accrued', NOW())

# 수정:
INSERT INTO commission_ledger 
(referral_code, referrer_user_id, referred_user_id, order_id, event, base_amount, commission_rate, amount, status, created_at)
VALUES (%s, %s, %s, %s, 'earn', %s, %s, %s, 'confirmed', NOW())
```

**SQLite (5959줄):**
```python
# 기존:
INSERT INTO commissions (referred_user, referrer_id, purchase_amount, commission_amount, commission_rate, is_paid, created_at)
VALUES (?, ?, ?, ?, ?, false, datetime('now'))

# 수정:
INSERT INTO commission_ledger 
(referral_code, referrer_user_id, referred_user_id, order_id, event, base_amount, commission_rate, amount, status, created_at)
VALUES (?, ?, ?, ?, 'earn', ?, ?, ?, 'confirmed', datetime('now'))
```

#### 📊 수정 후 영향

**✅ 긍정적 영향:**
1. **통합 원장으로 일관성 확보**:
   - 모든 커미션 거래가 `commission_ledger`에 기록
   - 잔액 계산 일관성

2. **출금 요청 처리 명확화**:
   - `event='payout'`으로 출금 기록
   - 잔액 계산: `SUM(amount) WHERE status='confirmed'`

**⚠️ 부정적 영향:**
1. **기존 `commissions` 데이터 마이그레이션 필요**:
   - 기존 `commissions` 데이터를 `commission_ledger`로 이동
   - 마이그레이션 스크립트 필요

2. **기존 코드 수정 필요**:
   - `admin_get_commissions()` 함수 수정 (12142줄)
   - `get_commissions()` 함수 수정 (9836줄)

---

### 2. `admin_get_commissions()` 함수 수정

#### 📍 현재 상황
- **위치**: `backend.py` 12142줄
- **문제**: `commissions` 테이블 사용 중

#### 🔧 수정 필요 코드

```python
# 기존:
FROM commissions c
JOIN referrals r ON c.referral_id = r.referral_id

# 수정:
FROM commission_ledger cl
WHERE cl.event = 'earn' AND cl.status = 'confirmed'
```

#### 📊 수정 후 영향

**✅ 긍정적 영향:**
- 관리자 커미션 내역 조회가 `commission_ledger`에서 일관되게 조회

**⚠️ 부정적 영향:**
- 기존 `commissions` 데이터는 조회되지 않음 (마이그레이션 필요)

---

## 📋 수정 우선순위

### ✅ 완료 (Critical)
1. ✅ `execution_progress` 테이블 생성 복구
2. ✅ `commission_ledger` 테이블 생성 복구 (PostgreSQL)

### 🔄 추가 수정 권장 (High)
3. 주문 생성 시 커미션 저장을 `commission_ledger`로 변경
4. `admin_get_commissions()` 함수를 `commission_ledger` 사용하도록 수정
5. `get_commissions()` 함수를 `commission_ledger` 사용하도록 수정

### 📝 선택적 개선 (Medium)
6. `orders` 테이블 컬럼명 통일
7. `order_id`, `user_id` 타입 통일

---

## 🎯 현재 상태 요약

### ✅ 정상 작동하는 기능
1. **패키지 스케줄링**: `execution_progress` 테이블 생성으로 정상 작동
2. **커미션 잔액 조회**: `get_commission_points()` - `commission_ledger` 사용 ✅
3. **출금 요청**: `request_withdrawal()` - `commission_ledger` 사용 ✅

### ⚠️ 부분적으로 작동하는 기능
1. **커미션 적립**: 주문 생성 시 `commissions` 테이블에 저장 (일관성 부족)
2. **관리자 커미션 조회**: `commissions` 테이블 사용 (일관성 부족)

### 📌 권장 사항
- 주문 생성 시 커미션 저장을 `commission_ledger`로 변경하여 완전한 통합 원장 구축
- 기존 `commissions` 데이터를 `commission_ledger`로 마이그레이션

