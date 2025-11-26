# 환급 신청 시 저장되는 데이터

## 1. 프론트엔드에서 전송하는 데이터

### 요청 본문 (`/api/referral/withdrawal-request` POST):
```json
{
  "referrer_email": "user@example.com",      // 사용자 이메일 (필수)
  "referrer_name": "홍길동",                  // 사용자 이름 (필수)
  "bank_name": "국민은행",                    // 은행명 (필수)
  "account_number": "123-456-789012",        // 계좌번호 (필수)
  "account_holder": "홍길동",                 // 예금주 (필수)
  "amount": 50000                            // 환급 금액 (필수, 최소 1,000원)
}
```

## 2. 백엔드에서 처리 및 저장되는 데이터

### `payout_requests` 테이블에 저장되는 필드:

#### 필수 필드:
- **`user_id`**: 사용자 ID (users 테이블에서 조회)
  - `referrer_email`로 `users` 테이블에서 조회
  - 없으면 `referral_codes` 테이블에서 조회

- **`amount`**: 환급 신청 금액
  - 최소 금액: 1,000원
  - 현재 잔액보다 작거나 같아야 함

- **`bank_name`**: 은행명
  - 예: "국민은행", "신한은행", "우리은행" 등

- **`account_number`**: 계좌번호
  - 예: "123-456-789012"

- **`status`**: 상태
  - 기본값: `'requested'` (신청됨)
  - 관리자 승인 시: `'approved'`
  - 관리자 거절 시: `'rejected'`

- **`requested_at`**: 신청 일시
  - PostgreSQL: `NOW()`
  - SQLite: `datetime('now')`

#### 선택적 필드 (컬럼이 있으면 저장):
- **`account_holder`**: 예금주
  - 컬럼이 있으면 저장
  - 없으면 저장하지 않음 (레거시 스키마 호환)

#### 자동으로 설정되는 필드 (관리자 처리 시):
- **`processed_at`**: 처리 일시
  - 승인/거절 시 `NOW()`로 설정

## 3. 데이터 검증 과정

### 1단계: 필수 필드 검증
```python
if not all([referrer_email, referrer_name, bank_name, account_number, account_holder, amount]):
    return jsonify({'error': '모든 필드가 필요합니다.'}), 400
```

### 2단계: 금액 검증
```python
amount = float(amount)
if amount <= 0:
    return jsonify({'error': '환급 금액은 0보다 커야 합니다.'}), 400
if amount < 1000:
    return jsonify({'error': '최소 환급 금액은 1,000원입니다.'}), 400
```

### 3단계: 사용자 조회
- `referrer_email`로 `users` 테이블에서 `user_id` 조회
- 없으면 `referral_codes` 테이블에서 조회

### 4단계: 잔액 확인
```python
# commission_ledger에서 현재 잔액 계산
SELECT COALESCE(SUM(amount), 0) FROM commission_ledger 
WHERE referrer_user_id = ? AND status = 'confirmed'

if current_balance < amount:
    return jsonify({'error': '잔액이 부족합니다.'}), 400
```

## 4. 저장 예시

### PostgreSQL:
```sql
INSERT INTO payout_requests 
(user_id, amount, bank_name, account_number, account_holder, status, requested_at)
VALUES (4, 50000, '국민은행', '123-456-789012', '홍길동', 'requested', NOW())
```

### SQLite:
```sql
INSERT INTO payout_requests 
(user_id, amount, bank_name, account_number, account_holder, status, requested_at)
VALUES (4, 50000, '국민은행', '123-456-789012', '홍길동', 'requested', datetime('now'))
```

## 5. 저장된 데이터 조회

### 관리자가 조회할 때 (`/api/admin/payout-requests`):
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
    pr.account_holder,  -- 있으면
    pr.status,
    pr.requested_at as created_at,
    pr.processed_at
FROM payout_requests pr
LEFT JOIN users u ON pr.user_id = u.user_id
ORDER BY pr.requested_at DESC
```

## 6. 환급 승인 시 추가 저장되는 데이터

### `payouts` 테이블:
- `request_id`: 환급 신청 ID
- `user_id`: 사용자 ID
- `paid_amount`: 지급 금액
- `processed_at`: 처리 일시

### `commission_ledger` 테이블:
- `referral_code`: 추천인 코드
- `referrer_user_id`: 추천인 사용자 ID
- `event`: `'payout'`
- `base_amount`: 환급 금액
- `amount`: **음수** (잔액 차감)
- `status`: `'confirmed'`
- `notes`: 환급 정보 (은행, 계좌 등)

## 7. 데이터 흐름 요약

```
사용자 입력
  ↓
[referrer_email, referrer_name, bank_name, account_number, account_holder, amount]
  ↓
백엔드 검증
  ↓
user_id 조회 (users 또는 referral_codes 테이블)
  ↓
잔액 확인 (commission_ledger 테이블)
  ↓
payout_requests 테이블에 저장
  ↓
{
  user_id: 4,
  amount: 50000,
  bank_name: '국민은행',
  account_number: '123-456-789012',
  account_holder: '홍길동',  // 있으면
  status: 'requested',
  requested_at: '2025-01-17 10:30:00'
}
```

## 8. 주의사항

1. **`account_holder` 컬럼**: 
   - 새 스키마에는 있지만, 레거시 스키마에는 없을 수 있음
   - 없으면 저장하지 않고 계속 진행

2. **`referrer_name`**: 
   - 프론트엔드에서 전송되지만 `payout_requests` 테이블에는 저장되지 않음
   - `users.username`으로 조회 가능

3. **`referrer_email`**: 
   - `payout_requests` 테이블에는 저장되지 않음
   - `users` 테이블과 JOIN하여 조회

4. **잔액 계산**: 
   - `commission_ledger` 테이블의 `SUM(amount)`로 계산
   - `status = 'confirmed'`인 항목만 포함

