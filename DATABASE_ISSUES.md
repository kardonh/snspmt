# 데이터베이스 스키마 문제점 분석

## 🚨 발견된 주요 문제점

### 1. ❌ `execution_progress` 테이블 모순

**문제:**
- `backend.py` 3613줄: "새 스키마에서는 work_jobs 사용하므로 execution_progress는 스킵"
- 하지만 실제 코드에서는 `execution_progress`를 **계속 사용 중**:
  - 1406줄: `INSERT INTO execution_progress` (예약 주문)
  - 2370줄: `INSERT INTO execution_progress` (패키지 단계)
  - 15765줄 이후: 크론잡에서 `execution_progress` 조회

**영향:**
- 테이블이 생성되지 않으면 INSERT 실패
- 패키지 스케줄링이 작동하지 않음
- 크론잡이 실행되지 않음

**해결 방안:**
1. `execution_progress` 테이블을 정상적으로 생성하도록 수정
2. 또는 `work_jobs` 테이블로 완전히 마이그레이션

---

### 2. ❌ `commission_ledger` vs `commissions` 혼용

**문제:**
- `backend.py` 3441줄: "새 스키마에서는 commissions 테이블 사용"
- 하지만 실제 코드에서는 `commission_ledger`를 사용:
  - `get_commission_points()`: `commission_ledger` 조회
  - `request_withdrawal()`: `commission_ledger`에 기록
  - SQLite: `commission_ledger` 테이블 생성

**영향:**
- PostgreSQL과 SQLite에서 다른 테이블 사용
- 커미션 잔액 계산 불일치
- 출금 요청 처리 오류 가능

**해결 방안:**
1. `commission_ledger`로 통일 (현재 코드 기준)
2. 또는 `commissions`로 완전히 마이그레이션

---

### 3. ❌ `orders` 테이블 스키마 불일치

**문제:**
- `backend.py` 3482줄: `order_id VARCHAR(255) PRIMARY KEY`
- `migrate_database.py` 334줄: `order_id BIGSERIAL PRIMARY KEY`
- 실제 PostgreSQL DB: `BIGSERIAL` (migrate_database.py 기준)

**영향:**
- `CREATE TABLE IF NOT EXISTS`로 인해 기존 테이블 사용
- 하지만 코드에서는 `VARCHAR(255)`로 가정
- 주문 ID 생성 시 타입 불일치 가능

**현재 상태:**
- 코드에서 `int(time.time() * 1000)`로 문자열 생성
- PostgreSQL에서는 `BIGSERIAL`이지만 문자열로 저장 가능

**해결 방안:**
- `order_id`를 문자열로 통일하거나
- `BIGSERIAL`로 완전히 마이그레이션

---

### 4. ❌ `orders` 테이블 컬럼명 불일치

**문제:**
- PostgreSQL: `total_amount`, `final_amount` 사용
- SQLite: `price`, `total_price` 사용
- 코드에서 `COALESCE(o.final_amount, o.total_amount, 0)` 사용하지만
- 일부 코드에서는 여전히 `o.price` 직접 사용 가능

**영향:**
- PostgreSQL에서 `price` 컬럼이 없으면 오류
- 주문 금액 조회 실패 가능

**현재 상태:**
- `get_orders()`: `COALESCE(o.final_amount, o.total_amount, 0)` ✅
- `create_order()`: `total_amount`, `final_amount` 사용 ✅
- 하지만 일부 레거시 코드에서 `price` 사용 가능

**해결 방안:**
- 모든 코드에서 `COALESCE` 패턴 사용
- 또는 컬럼명 통일

---

### 5. ❌ `user_id` 타입 불일치

**문제:**
- `backend.py`: `user_id VARCHAR(255)`
- `migrate_database.py`: `user_id BIGINT`
- 실제 PostgreSQL DB: `BIGINT` (migrate_database.py 기준)

**영향:**
- Supabase UID는 문자열인데 DB는 BIGINT
- 외래 키 제약 조건 위반 가능
- 사용자 조회 실패 가능

**현재 상태:**
- 코드에서 `external_uid VARCHAR(255)` 사용
- `user_id`는 내부 ID로 사용
- 하지만 일부 코드에서는 혼용

**해결 방안:**
- `user_id`를 `BIGINT`로 유지하고
- `external_uid`를 Supabase UID로 사용
- 또는 `user_id`를 `VARCHAR(255)`로 통일

---

### 6. ⚠️ 스키마 파일 불일치

**문제:**
- `DATABASE_SCHEMA_OPTIMIZED.sql`: MySQL/MariaDB용 (레거시)
- `migrate_database.py`: PostgreSQL 새 스키마
- `backend.py`의 `init_database()`: 실제 런타임 스키마

**영향:**
- 어떤 스키마가 실제로 사용되는지 불명확
- 마이그레이션 시 혼란

**해결 방안:**
- 실제 사용되는 스키마를 명확히 문서화
- 레거시 스키마 파일에 주석 추가

---

## 📊 문제점 우선순위

### 🔴 Critical (즉시 수정 필요)
1. **`execution_progress` 테이블 모순** - 패키지 스케줄링 실패
2. **`commission_ledger` vs `commissions` 혼용** - 커미션 계산 오류

### 🟡 High (빠른 시일 내 수정)
3. **`orders` 테이블 컬럼명 불일치** - 주문 금액 조회 오류 가능
4. **`user_id` 타입 불일치** - 사용자 조회 실패 가능

### 🟢 Medium (점진적 개선)
5. **`order_id` 타입 불일치** - 현재는 작동하지만 일관성 필요
6. **스키마 파일 불일치** - 문서화 문제

---

## 🔧 권장 수정 사항

### 1. `execution_progress` 테이블 생성 복구
```python
# backend.py 3613줄 수정
# 기존: "execution_progress 테이블 생성 스킵"
# 수정: execution_progress 테이블 정상 생성
```

### 2. `commission_ledger`로 통일
```python
# backend.py 3441줄 수정
# 기존: "새 스키마에서는 commissions 테이블 사용"
# 수정: "commission_ledger 테이블 사용 (통합 테이블)"
```

### 3. `orders` 테이블 컬럼명 통일
- PostgreSQL과 SQLite 모두 `total_amount`, `final_amount` 사용
- 또는 코드에서 `COALESCE` 패턴 일관성 유지

### 4. 스키마 문서화
- 실제 사용되는 스키마를 명확히 문서화
- 레거시 스키마 파일에 주석 추가

---

## 📝 체크리스트

- [ ] `execution_progress` 테이블 생성 복구
- [ ] `commission_ledger` vs `commissions` 통일
- [ ] `orders` 테이블 컬럼명 통일 또는 COALESCE 패턴 일관성
- [ ] `user_id` 타입 결정 및 통일
- [ ] 스키마 파일 문서화

