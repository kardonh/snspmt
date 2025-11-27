# 커미션 환급 신청 시스템 전체 플로우

## 📋 전체 프로세스 개요

```
[추천인] → 환급 신청 → [관리자] → 승인/거절 → [데이터베이스]
```

---

## 1️⃣ 환급 신청 (추천인 측)

### 위치
- **프론트엔드**: `src/pages/ReferralDashboard.jsx`
- **백엔드 API**: `/api/referral/withdrawal-request` (POST)

### 프로세스

#### 1-1. 사용자 액션
1. 추천인 대시보드 (`ReferralDashboard.jsx`)에서 "환급 신청" 버튼 클릭
2. 모달에서 다음 정보 입력:
   - 이름 (referrer_name)
   - 은행명 (bank_name)
   - 계좌번호 (account_number)
   - 예금주명 (account_holder)
   - 환급 금액 (amount)

#### 1-2. 프론트엔드 처리 (`handleWithdrawalRequest`)
```javascript
POST /api/referral/withdrawal-request
{
  referrer_email: "user@example.com",
  referrer_name: "홍길동",
  bank_name: "국민은행",
  account_number: "123-456-789012",
  account_holder: "홍길동",
  amount: 50000
}
```

#### 1-3. 백엔드 처리 (`request_withdrawal`)
1. **사용자 확인**: 
   - `referrer_email`로 `referral_codes` 테이블에서 `referrer_user_id` 조회
   - 또는 `users` 테이블에서 직접 조회
   
2. **잔액 확인**:
   - `commission_ledger` 테이블에서 `SUM(amount)`로 현재 커미션 잔액 계산
   - 신청 금액이 잔액보다 크면 에러 반환

3. **환급 신청 저장**:
   - `payout_requests` 테이블에 레코드 생성
   - 상태: `'requested'` (대기중)
   - 저장 정보:
     - `user_id`: 추천인의 user_id
     - `amount`: 환급 신청 금액
     - `bank_name`: 은행명
     - `account_number`: 계좌번호
     - `status`: 'requested'
     - `requested_at`: 신청일시

#### 1-4. 결과
- ✅ 성공: "환급 신청이 접수되었습니다!" 메시지
- ❌ 실패: 에러 메시지 (잔액 부족, 필수 필드 누락 등)

---

## 2️⃣ 환급 신청 목록 조회 (관리자)

### 위치
- **프론트엔드**: `src/pages/AdminPage.jsx`
- **백엔드 API**: `/api/admin/payout-requests` (GET)

### 프로세스

#### 2-1. 자동 로드
- 관리자 페이지의 "추천인 관리" 탭 진입 시 자동으로 로드
- `loadReferralData()` 함수 실행

#### 2-2. 백엔드 조회 (`get_payout_requests`)
```sql
SELECT 
    pr.request_id,
    pr.user_id,
    u.email as referrer_email,
    u.username as referrer_name,
    u.phone as phone,
    pr.amount,
    pr.bank_name,
    pr.account_number,
    pr.status,
    pr.requested_at as created_at,
    pr.processed_at
FROM payout_requests pr
LEFT JOIN users u ON pr.user_id = u.user_id
ORDER BY pr.requested_at DESC
```

#### 2-3. 화면 표시
- 테이블에 다음 정보 표시:
  - 신청 ID
  - 이름 (referrer_name)
  - 이메일 (referrer_email)
  - 전화번호 (phone)
  - 은행명 (bank_name)
  - 계좌번호 (account_number)
  - 환급 금액 (amount)
  - 상태 (status: 대기중/승인됨/거절됨)
  - 신청일
  - 작업 (승인/거절 버튼)

---

## 3️⃣ 환급 신청 승인 (관리자)

### 위치
- **프론트엔드**: `src/pages/AdminPage.jsx` (승인 버튼 클릭)
- **백엔드 API**: `/api/admin/payout-requests/<request_id>/approve` (PUT)

### 프로세스

#### 3-1. 사용자 액션
- 관리자가 "승인" 버튼 (✅ 체크 아이콘) 클릭
- 확인 메시지: "환급신청을 승인하시겠습니까?"

#### 3-2. 백엔드 처리 (`approve_payout_request`)

**Step 1: 환급 신청 정보 조회**
```sql
SELECT pr.*, u.email as referrer_email
FROM payout_requests pr
LEFT JOIN users u ON pr.user_id = u.user_id
WHERE pr.request_id = ?
```

**Step 2: 상태 확인**
- 상태가 `'requested'` 또는 `'pending'`인지 확인
- 이미 처리된 신청이면 에러 반환

**Step 3: referral_code 조회**
```sql
SELECT referral_code FROM users WHERE user_id = ?
```
- `commission_ledger`에 기록하기 위해 필요

**Step 4: 데이터베이스 업데이트**

a) **환급 신청 상태 변경**:
```sql
UPDATE payout_requests 
SET status = 'approved', processed_at = NOW()
WHERE request_id = ?
```

b) **payout 레코드 생성**:
```sql
INSERT INTO payouts (request_id, user_id, paid_amount, processed_at, created_at, updated_at)
VALUES (?, ?, ?, NOW(), NOW(), NOW())
```
- 환급 지급 내역 기록용

c) **commission_ledger에 payout 이벤트 기록** (중요!):
```sql
INSERT INTO commission_ledger 
(referral_code, referrer_user_id, order_id, event, base_amount, commission_rate, amount, status, notes, created_at, confirmed_at)
VALUES (?, ?, NULL, 'payout', ?, 0, ?, 'confirmed', ?, NOW(), NOW())
```
- `event`: 'payout' (환급)
- `amount`: **음수 값** (예: -50000원) → 잔액 차감
- `base_amount`: 환급 금액 (양수)
- `notes`: 환급 정보 (신청 ID, 은행, 계좌번호)

**Step 5: 커밋**
- 모든 변경사항을 한 번에 커밋

#### 3-3. 결과
- ✅ 성공: 
  - 프론트엔드에서 "환급신청이 승인되었습니다!" 메시지
  - `loadReferralData()` 호출하여 목록 새로고침
  - 환급 신청 목록에서 상태가 "승인됨"으로 변경
  
- ❌ 실패: 에러 메시지 표시

#### 3-4. 영향
- `commission_ledger`에 음수 레코드 추가
- 추천인의 커미션 잔액 감소
- 환급 신청 테이블의 상태가 'approved'로 변경

---

## 4️⃣ 환급 신청 거절 (관리자)

### 위치
- **프론트엔드**: `src/pages/AdminPage.jsx` (거절 버튼 클릭)
- **백엔드 API**: `/api/admin/payout-requests/<request_id>/reject` (PUT)

### 프로세스

#### 4-1. 사용자 액션
- 관리자가 "거절" 버튼 (❌ X 아이콘) 클릭
- 확인 메시지: "환급신청을 거절하시겠습니까?"

#### 4-2. 백엔드 처리 (`reject_payout_request`)

**Step 1: 환급 신청 정보 조회**
```sql
SELECT * FROM payout_requests WHERE request_id = ?
```

**Step 2: 상태 확인**
- 상태가 `'requested'` 또는 `'pending'`인지 확인
- 이미 처리된 신청이면 에러 반환

**Step 3: 환급 신청 상태 변경**
```sql
UPDATE payout_requests 
SET status = 'rejected', processed_at = NOW()
WHERE request_id = ?
```

**Step 4: 커밋**
- 변경사항 커밋

#### 4-3. 결과
- ✅ 성공:
  - 프론트엔드에서 "환급신청이 거절되었습니다!" 메시지
  - `loadReferralData()` 호출하여 목록 새로고침
  - 환급 신청 목록에서 상태가 "거절됨"으로 변경

- ❌ 실패: 에러 메시지 표시

#### 4-4. 영향
- 환급 신청 테이블의 상태만 'rejected'로 변경
- **커미션 잔액에는 변화 없음** (거절이므로)
- `commission_ledger`에 기록되지 않음

---

## 📊 데이터베이스 테이블 구조

### `payout_requests` (환급 신청)
```sql
CREATE TABLE payout_requests (
    request_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    amount NUMERIC(14,2) NOT NULL,
    bank_name VARCHAR(100) NOT NULL,
    account_number VARCHAR(64) NOT NULL,
    status payout_request_status DEFAULT 'requested',
    requested_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP
)
```

### `payouts` (환급 지급 내역)
```sql
CREATE TABLE payouts (
    payout_id BIGSERIAL PRIMARY KEY,
    request_id BIGINT NOT NULL REFERENCES payout_requests(request_id),
    user_id BIGINT NOT NULL,
    paid_amount NUMERIC(14,2) NOT NULL,
    status payout_status DEFAULT 'processing',
    processed_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
)
```

### `commission_ledger` (커미션 원장)
```sql
CREATE TABLE commission_ledger (
    ledger_id BIGSERIAL PRIMARY KEY,
    referral_code VARCHAR(50) NOT NULL,
    referrer_user_id VARCHAR(255) NOT NULL,
    referred_user_id VARCHAR(255) NULL,
    order_id VARCHAR(255) NULL,
    event ENUM('earn','payout','adjust','reverse') NOT NULL,
    base_amount DECIMAL(10,2) NULL,
    commission_rate DECIMAL(5,4) NULL,
    amount DECIMAL(10,2) NOT NULL,  -- 양수(적립) 또는 음수(출금)
    status ENUM('pending','confirmed','cancelled') DEFAULT 'confirmed',
    notes TEXT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    confirmed_at TIMESTAMP
)
```

---

## 🔄 전체 데이터 흐름

### 1. 커미션 적립 (주문 생성 시)
```
주문 생성 → commission_ledger에 'earn' 이벤트 기록
→ amount: +10000원 (양수)
→ 추천인 잔액 증가
```

### 2. 환급 신청
```
추천인 신청 → payout_requests에 레코드 생성
→ status: 'requested'
→ 아직 잔액 변화 없음
```

### 3. 환급 승인
```
관리자 승인 → 3가지 동시 처리:
  1) payout_requests.status → 'approved'
  2) payouts 테이블에 레코드 생성
  3) commission_ledger에 'payout' 이벤트 기록
     → amount: -50000원 (음수)
     → 추천인 잔액 감소
```

### 4. 환급 거절
```
관리자 거절 → payout_requests.status → 'rejected'
→ 잔액 변화 없음
```

---

## 💡 주요 포인트

1. **잔액 계산**:
   - `commission_ledger` 테이블의 `SUM(amount)`로 계산
   - 양수 = 적립, 음수 = 출금

2. **환급 승인 시 자동 차감**:
   - `commission_ledger`에 음수 레코드 추가
   - 추천인 대시보드에서 잔액이 자동으로 감소

3. **상태 관리**:
   - `'requested'` / `'pending'`: 대기중 (승인/거절 가능)
   - `'approved'`: 승인됨 (처리 완료)
   - `'rejected'`: 거절됨 (처리 완료)

4. **데이터 무결성**:
   - 승인/거절은 한 번만 가능 (상태 확인)
   - 트랜잭션으로 원자적 처리
   - 잔액 부족 시 신청 불가



