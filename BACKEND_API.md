# 백엔드 API 문서 (Backend API Documentation)

이 문서는 snspmt 프로젝트의 백엔드 구조와 API 엔드포인트를 문서화합니다.

## 목차 (Table of Contents)

1. [백엔드 구조 개요](#백엔드-구조-개요)
2. [주요 모듈](#주요-모듈)
3. [데이터베이스 연결](#데이터베이스-연결)
4. [API 엔드포인트](#api-엔드포인트)
5. [인증 및 권한](#인증-및-권한)
6. [외부 API 통합](#외부-api-통합)
7. [주문 처리 로직](#주문-처리-로직)
8. [환경 변수](#환경-변수)

---

## 백엔드 구조 개요

### 기술 스택
- **프레임워크**: Flask (Python)
- **데이터베이스**: PostgreSQL (프로덕션), SQLite (개발)
- **ORM**: psycopg2 (PostgreSQL), sqlite3 (SQLite)
- **CORS**: flask-cors
- **배포**: AWS ECS (Elastic Container Service)

### 주요 파일 구조
```
backend.py              # 메인 Flask 애플리케이션
api/
  ├── __init__.py
  ├── _utils.py         # 유틸리티 함수
  ├── analytics.py      # 분석 관련 API
  ├── config.py         # 설정 관리
  ├── coupons.py        # 쿠폰 관리
  ├── notifications.py  # 알림 관리
  ├── orders.py         # 주문 관리
  ├── postgres_utils.py # PostgreSQL 유틸리티
  ├── referral.py       # 추천인 시스템
  ├── services.py       # 서비스 관리
  ├── smmkings.py       # SMM Kings API 통합
  └── snspop.py         # SNS Pop API 통합
```

---

## 주요 모듈

### 1. `backend.py` (메인 애플리케이션)
- Flask 앱 초기화 및 설정
- 모든 API 엔드포인트 정의
- 미들웨어 (CORS, 로깅, 에러 핸들링)
- 정적 파일 서빙
- 데이터베이스 연결 관리

### 2. `api/postgres_utils.py`
- PostgreSQL 연결 관리
- 데이터베이스 유틸리티 함수
- 추천인 코드 생성 (관리자용)

### 3. `api/config.py`
- SMM Kings API 설정
- 데이터베이스 설정
- CORS 설정
- 로깅 설정
- API 타임아웃 설정

### 4. `api/smmkings.py`
- SMM Kings API 클라이언트
- 서비스 목록 조회
- 주문 생성 및 관리

---

## 데이터베이스 연결

### 연결 함수
```python
def get_db_connection():
    """PostgreSQL 연결 반환"""
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database=os.getenv('DB_NAME', 'snspmt'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'password'),
        port=os.getenv('DB_PORT', '5432')
    )
    return conn
```

### 환경 변수
- `DB_HOST`: 데이터베이스 호스트
- `DB_NAME`: 데이터베이스 이름
- `DB_USER`: 데이터베이스 사용자
- `DB_PASSWORD`: 데이터베이스 비밀번호
- `DB_PORT`: 데이터베이스 포트

---

## API 엔드포인트

### 인증 (Authentication)

#### 1. 회원가입
- **URL**: `POST /api/register`
- **설명**: 새 사용자 등록
- **요청 본문**:
  ```json
  {
    "user_id": "string",
    "email": "string",
    "name": "string",
    "display_name": "string"
  }
  ```
- **응답**: `{ "success": true, "message": "회원가입 완료" }`

#### 2. 로그인
- **URL**: `POST /api/auth/login`
- **설명**: 일반 로그인
- **요청 본문**:
  ```json
  {
    "email": "string",
    "password": "string"
  }
  ```

#### 3. 카카오 로그인
- **URL**: `POST /api/auth/kakao-login`
- **설명**: 카카오 소셜 로그인
- **요청 본문**:
  ```json
  {
    "access_token": "string",
    "id_token": "string"
  }
  ```

#### 4. 구글 로그인
- **URL**: `POST /api/auth/google-login`
- **설명**: 구글 소셜 로그인
- **요청 본문**:
  ```json
  {
    "id_token": "string"
  }
  ```

#### 5. 구글 콜백
- **URL**: `GET /api/auth/google-callback`
- **설명**: 구글 OAuth 콜백 처리

---

### 포인트 (Points)

#### 1. 포인트 조회
- **URL**: `GET /api/points`
- **쿼리 파라미터**: `user_id` (필수)
- **응답**:
  ```json
  {
    "points": 1000,
    "user_id": "string"
  }
  ```

#### 2. 포인트 구매 (일반)
- **URL**: `POST /api/points/purchase`
- **설명**: 포인트 구매 신청
- **요청 본문**:
  ```json
  {
    "user_id": "string",
    "amount": 1000,
    "price": 10000
  }
  ```

#### 3. KCP 거래등록
- **URL**: `POST /api/points/purchase-kcp/register`
- **설명**: KCP 표준결제 거래등록 (Mobile 필수)
- **요청 본문**:
  ```json
  {
    "user_id": "string",
    "amount": 1000,
    "price": 10000,
    "good_name": "포인트 구매",
    "pay_method": "CARD"
  }
  ```
- **응답**:
  ```json
  {
    "success": true,
    "ordr_idxx": "POINT_1234567890",
    "approval_key": "string",
    "pay_url": "https://..."
  }
  ```

#### 4. KCP 결제창 호출 데이터 생성
- **URL**: `POST /api/points/purchase-kcp/payment-form`
- **설명**: 결제창 호출을 위한 폼 데이터 생성
- **요청 본문**:
  ```json
  {
    "ordr_idxx": "POINT_1234567890",
    "approval_key": "string",
    "pay_url": "https://..."
  }
  ```

#### 5. KCP 결제 인증결과 처리
- **URL**: `POST /api/points/purchase-kcp/return`
- **설명**: KCP에서 전달받은 인증결과 데이터 처리

#### 6. KCP 결제요청 (승인)
- **URL**: `POST /api/points/purchase-kcp/approve`
- **설명**: 인증된 데이터로 실제 결제 승인 요청
- **요청 본문**:
  ```json
  {
    "ordr_idxx": "POINT_1234567890",
    "enc_data": "string",
    "enc_info": "string",
    "tran_cd": "string"
  }
  ```

#### 7. 포인트 차감
- **URL**: `POST /api/points/deduct`
- **설명**: 사용자 포인트 차감
- **요청 본문**:
  ```json
  {
    "user_id": "string",
    "amount": 100,
    "description": "주문 결제"
  }
  ```

#### 8. 포인트 구매 내역
- **URL**: `GET /api/points/purchase-history`
- **쿼리 파라미터**: `user_id` (필수)
- **응답**: 포인트 구매 내역 배열

---

### 주문 (Orders)

#### 1. 주문 생성
- **URL**: `POST /api/orders`
- **설명**: 새 주문 생성 (할인 및 커미션 적용)
- **요청 본문**:
  ```json
  {
    "user_id": "string",
    "service_id": "string",
    "link": "string",
    "quantity": 100,
    "price": 10000,
    "comments": "string",
    "is_scheduled": false,
    "scheduled_datetime": "2024-01-01 12:00",
    "package_steps": [],
    "runs": 1,
    "interval": 0
  }
  ```
- **응답**:
  ```json
  {
    "success": true,
    "order_id": "string",
    "smm_panel_order_id": "string",
    "final_price": 10000,
    "discount_amount": 0,
    "commission_amount": 0
  }
  ```

#### 2. 주문 목록 조회
- **URL**: `GET /api/orders`
- **쿼리 파라미터**: `user_id` (필수)
- **응답**: 주문 목록 배열

#### 3. 주문 상태 확인
- **URL**: `POST /api/orders/check-status`
- **설명**: 주문 상태 일괄 확인
- **요청 본문**:
  ```json
  {
    "order_ids": ["order1", "order2"]
  }
  ```

#### 4. 주문 상태 업데이트
- **URL**: `PUT /api/orders/<order_id>/status`
- **설명**: 주문 상태 수동 업데이트
- **요청 본문**:
  ```json
  {
    "status": "completed",
    "smm_panel_order_id": "string"
  }
  ```

#### 5. 패키지 주문 처리 시작
- **URL**: `POST /api/orders/start-package-processing`
- **설명**: 패키지 주문의 첫 번째 단계 처리 시작
- **요청 본문**:
  ```json
  {
    "order_id": "string"
  }
  ```

#### 6. 패키지 주문 진행 상황 조회
- **URL**: `GET /api/orders/<order_id>/package-progress`
- **설명**: 패키지 주문의 단계별 진행 상황 조회
- **응답**:
  ```json
  {
    "order_id": "string",
    "current_step": 1,
    "total_steps": 30,
    "progress": [
      {
        "step_index": 0,
        "step_name": "Step 1",
        "status": "completed",
        "smm_order_id": "string",
        "completed_at": "2024-01-01T12:00:00"
      }
    ]
  }
  ```

---

### 예약 주문 (Scheduled Orders)

#### 1. 예약 주문 생성
- **URL**: `POST /api/scheduled-orders`
- **설명**: 예약 발송 주문 생성
- **요청 본문**:
  ```json
  {
    "user_id": "string",
    "service_id": "string",
    "link": "string",
    "quantity": 100,
    "price": 10000,
    "scheduled_datetime": "2024-01-01 12:00",
    "package_steps": [],
    "runs": 1,
    "interval": 0
  }
  ```
- **응답**:
  ```json
  {
    "success": true,
    "message": "예약 발송이 설정되었습니다.",
    "scheduled_datetime": "2024-01-01 12:00"
  }
  ```

#### 2. 예약 주문 목록 조회 (관리자)
- **URL**: `GET /api/admin/scheduled-orders`
- **설명**: 관리자용 예약 주문 목록 조회
- **헤더**: `X-Admin-Token` (필수)

---

### 추천인 시스템 (Referral)

#### 1. 내 추천인 코드 조회
- **URL**: `GET /api/referral/my-codes`
- **쿼리 파라미터**: `user_id` (필수)
- **응답**: 추천인 코드 목록

#### 2. 추천인 코드 사용
- **URL**: `POST /api/referral/use-code`
- **설명**: 추천인 코드 사용하여 쿠폰 발급
- **요청 본문**:
  ```json
  {
    "user_id": "string",
    "code": "REF12345678"
  }
  ```

#### 3. 추천인 코드 검증
- **URL**: `GET /api/referral/validate-code`
- **쿼리 파라미터**: `code` (필수)
- **응답**: 코드 유효성 검증 결과

#### 4. 커미션 조회
- **URL**: `GET /api/referral/commissions`
- **쿼리 파라미터**: `user_id` (필수)
- **응답**: 커미션 내역

#### 5. 커미션 포인트 조회
- **URL**: `GET /api/referral/commission-points`
- **쿼리 파라미터**: `user_id` (필수)
- **응답**: 커미션 포인트 잔액

#### 6. 커미션 거래 내역
- **URL**: `GET /api/referral/commission-transactions`
- **쿼리 파라미터**: `user_id` (필수)
- **응답**: 커미션 거래 내역

#### 7. 추천인 통계
- **URL**: `GET /api/referral/stats`
- **쿼리 파라미터**: `user_id` (필수)
- **응답**: 추천인 통계 정보

#### 8. 추천인 목록
- **URL**: `GET /api/referral/referrals`
- **쿼리 파라미터**: `user_id` (필수)
- **응답**: 추천인 목록

#### 9. 출금 요청
- **URL**: `POST /api/referral/withdrawal-request`
- **설명**: 커미션 출금 요청
- **요청 본문**:
  ```json
  {
    "user_id": "string",
    "amount": 10000,
    "bank_name": "string",
    "account_number": "string",
    "account_holder": "string"
  }
  ```

#### 10. 쿠폰 발급
- **URL**: `POST /api/referral/issue-coupon`
- **설명**: 추천인 코드 사용 시 쿠폰 발급
- **요청 본문**:
  ```json
  {
    "user_id": "string",
    "referral_code": "REF12345678"
  }
  ```

---

### 쿠폰 (Coupons)

#### 1. 사용자 쿠폰 조회
- **URL**: `GET /api/user/coupons`
- **쿼리 파라미터**: `user_id` (필수)
- **응답**: 사용 가능한 쿠폰 목록

---

### 관리자 (Admin)

#### 1. 관리자 통계
- **URL**: `GET /api/admin/stats`
- **설명**: 관리자 대시보드 통계
- **헤더**: `X-Admin-Token` (필수)
- **응답**: 전체 통계 정보

#### 2. 관리자 구매 내역
- **URL**: `GET /api/admin/purchases`
- **설명**: 전체 포인트 구매 내역 조회
- **헤더**: `X-Admin-Token` (필수)

#### 3. 관리자 구매 내역 수정
- **URL**: `PUT /api/admin/purchases/<purchase_id>`
- **설명**: 포인트 구매 내역 수정
- **헤더**: `X-Admin-Token` (필수)

#### 4. 관리자 사용자 목록
- **URL**: `GET /api/admin/users`
- **설명**: 전체 사용자 목록 조회
- **헤더**: `X-Admin-Token` (필수)

#### 5. 관리자 거래 내역
- **URL**: `GET /api/admin/transactions`
- **설명**: 전체 거래 내역 조회
- **헤더**: `X-Admin-Token` (필수)

#### 6. 패키지 주문 재처리
- **URL**: `POST /api/admin/reprocess-package-orders`
- **설명**: 멈춰있는 패키지 주문 재처리
- **헤더**: `X-Admin-Token` (필수)

#### 7. 추천인 코드 생성 (관리자)
- **URL**: `POST /api/admin/referral/register`
- **설명**: 관리자용 추천인 코드 생성
- **헤더**: `X-Admin-Token` (필수)

#### 8. 추천인 코드 목록 (관리자)
- **URL**: `GET /api/admin/referral/list`
- **설명**: 전체 추천인 코드 목록
- **헤더**: `X-Admin-Token` (필수)

#### 9. 추천인 코드 조회 (관리자)
- **URL**: `GET /api/admin/referral/codes`
- **설명**: 추천인 코드 상세 조회
- **헤더**: `X-Admin-Token` (필수)

#### 10. 커미션 개요 (관리자)
- **URL**: `GET /api/admin/referral/commission-overview`
- **설명**: 전체 커미션 개요
- **헤더**: `X-Admin-Token` (필수)

#### 11. 커미션 지급 (관리자)
- **URL**: `POST /api/admin/referral/pay-commission`
- **설명**: 커미션 수동 지급
- **헤더**: `X-Admin-Token` (필수)

#### 12. 커미션 지급 내역 (관리자)
- **URL**: `GET /api/admin/referral/payment-history`
- **설명**: 커미션 지급 내역 조회
- **헤더**: `X-Admin-Token` (필수)

#### 13. 출금 요청 목록 (관리자)
- **URL**: `GET /api/admin/withdrawal-requests`
- **설명**: 출금 요청 목록 조회
- **헤더**: `X-Admin-Token` (필수)

#### 14. 출금 처리 (관리자)
- **URL**: `POST /api/admin/process-withdrawal`
- **설명**: 출금 요청 처리
- **헤더**: `X-Admin-Token` (필수)

#### 15. 공지사항 목록 (관리자)
- **URL**: `GET /api/admin/notices`
- **설명**: 공지사항 목록 조회
- **헤더**: `X-Admin-Token` (필수)

#### 16. 공지사항 생성 (관리자)
- **URL**: `POST /api/admin/notices`
- **설명**: 공지사항 생성
- **헤더**: `X-Admin-Token` (필수)

#### 17. 공지사항 수정 (관리자)
- **URL**: `PUT /api/admin/notices/<notice_id>`
- **설명**: 공지사항 수정
- **헤더**: `X-Admin-Token` (필수)

#### 18. 공지사항 삭제 (관리자)
- **URL**: `DELETE /api/admin/notices/<notice_id>`
- **설명**: 공지사항 삭제
- **헤더**: `X-Admin-Token` (필수)

#### 19. 이미지 업로드 (관리자)
- **URL**: `POST /api/admin/upload-image`
- **설명**: 관리자용 이미지 업로드
- **헤더**: `X-Admin-Token` (필수)
- **Content-Type**: `multipart/form-data`

#### 20. 데이터베이스 마이그레이션 (관리자)
- **URL**: `POST /api/admin/migrate-database`
- **설명**: 데이터베이스 마이그레이션 실행
- **헤더**: `X-Admin-Token` (필수)

---

### 공지사항 (Notices)

#### 1. 활성 공지사항 조회
- **URL**: `GET /api/notices/active`
- **설명**: 활성화된 공지사항 목록 조회
- **응답**: 공지사항 목록

---

### SMM Panel API

#### 1. SMM Panel 서비스 목록 조회
- **URL**: `GET /api/smm-panel/services`
- **설명**: SMM Panel에서 제공하는 서비스 목록 조회

#### 2. SMM Panel API 호출
- **URL**: `POST /api/smm-panel`
- **설명**: SMM Panel API 프록시
- **요청 본문**:
  ```json
  {
    "action": "services|balance|add|status|refill|cancel",
    "service": "string",
    "link": "string",
    "quantity": 100,
    "comments": "string"
  }
  ```

#### 3. SMM Panel 테스트
- **URL**: `GET /api/smm-panel/test`
- **설명**: SMM Panel API 연결 테스트

---

### Cron 작업 (Scheduled Tasks)

#### 1. 예약 주문 처리
- **URL**: `POST /api/cron/process-scheduled-orders`
- **설명**: 예약된 주문들을 처리하는 Cron 작업
- **인증**: Cron 작업용 인증 필요

#### 2. 분할 발송 처리
- **URL**: `POST /api/cron/process-split-deliveries`
- **설명**: 분할 발송 주문들을 처리하는 Cron 작업
- **인증**: Cron 작업용 인증 필요

---

### 설정 (Config)

#### 1. 설정 조회
- **URL**: `GET /api/config`
- **설명**: 프론트엔드 설정 정보 조회
- **응답**:
  ```json
  {
    "firebase_api_key": "string",
    "firebase_auth_domain": "string",
    "firebase_project_id": "string"
  }
  ```

#### 2. 배포 상태 조회
- **URL**: `GET /api/deployment-status`
- **설명**: 배포 상태 정보 조회

---

### 건강 체크 (Health Check)

#### 1. 건강 체크
- **URL**: `GET /api/health` 또는 `GET /health`
- **설명**: 서버 상태 확인
- **응답**: `{ "status": "ok" }`

---

### 사용자 (Users)

#### 1. 사용자 정보 조회
- **URL**: `GET /api/users/<user_id>`
- **설명**: 특정 사용자 정보 조회
- **응답**: 사용자 정보 객체

---

### 블로그 (Blog)

#### 1. 블로그 포스트 목록
- **URL**: `GET /api/blog/posts`
- **설명**: 블로그 포스트 목록 조회

#### 2. 블로그 포스트 상세
- **URL**: `GET /api/blog/posts/<post_id>`
- **설명**: 블로그 포스트 상세 조회

#### 3. 블로그 카테고리 목록
- **URL**: `GET /api/blog/categories`
- **설명**: 블로그 카테고리 목록 조회

#### 4. 블로그 태그 목록
- **URL**: `GET /api/blog/tags`
- **설명**: 블로그 태그 목록 조회

#### 5. 블로그 포스트 생성 (관리자)
- **URL**: `POST /api/blog/posts`
- **설명**: 블로그 포스트 생성
- **헤더**: `X-Admin-Token` (필수)

#### 6. 블로그 포스트 수정 (관리자)
- **URL**: `PUT /api/blog/posts/<post_id>`
- **설명**: 블로그 포스트 수정
- **헤더**: `X-Admin-Token` (필수)

#### 7. 블로그 포스트 삭제 (관리자)
- **URL**: `DELETE /api/blog/posts/<post_id>`
- **설명**: 블로그 포스트 삭제
- **헤더**: `X-Admin-Token` (필수)

---

## 인증 및 권한

### 관리자 인증
관리자 권한이 필요한 API는 `X-Admin-Token` 헤더를 요구합니다.

```python
@require_admin_auth
def admin_endpoint():
    # 관리자 전용 로직
    pass
```

### 환경 변수
- `ADMIN_TOKEN`: 관리자 토큰 (기본값: `admin_sociality_2024`)

---

## 외부 API 통합

### 1. SMM Panel API
SMM Panel API를 통한 주문 처리 및 서비스 관리.

#### 주요 기능
- 서비스 목록 조회
- 주문 생성
- 주문 상태 조회
- 주문 리필
- 주문 취소

#### API 엔드포인트
- **주문 생성**: `POST /api/smm-panel` (action: `add`)
- **주문 상태**: `POST /api/smm-panel` (action: `status`)
- **리필**: `POST /api/smm-panel` (action: `refill`)
- **취소**: `POST /api/smm-panel` (action: `cancel`)

#### 환경 변수
- `SMMKINGS_API_KEY`: SMM Kings API 키
- `SMMKINGS_API_URL`: SMM Kings API URL (기본값: `https://smmkings.com/api/v2`)

### 2. KCP 표준결제
KCP를 통한 포인트 구매 결제 시스템.

#### 결제 플로우
1. **거래등록** (`POST /api/points/purchase-kcp/register`)
   - 주문 데이터를 KCP 서버에 등록
   - `approval_key` 및 `pay_url` 반환

2. **결제창 호출** (`POST /api/points/purchase-kcp/payment-form`)
   - 결제창 호출을 위한 폼 데이터 생성

3. **인증결과 처리** (`POST /api/points/purchase-kcp/return`)
   - KCP에서 전달받은 인증결과 데이터 처리

4. **결제 승인** (`POST /api/points/purchase-kcp/approve`)
   - 인증된 데이터로 실제 결제 승인 요청
   - 결제 성공 시 포인트 자동 추가

#### 환경 변수
- `KCP_SITE_CD`: KCP 사이트 코드
- `KCP_SITE_KEY`: KCP 사이트 키
- `KCP_CERT_INFO`: KCP 인증서 정보 (PEM 형식)
- `KCP_CERT_PASSWORD`: KCP 인증서 비밀번호
- `KCP_ENCRYPT_KEY`: KCP 암호화 키

#### API URLs
- **거래등록**: `https://testsmpay.kcp.co.kr/trade/register.do`
- **결제요청**: `https://stg-spl.kcp.co.kr/gw/enc/v1/payment`
- **결제 스크립트**: `https://testspay.kcp.co.kr/plugin/kcp_spay_hub.js`

---

## 주문 처리 로직

### 일반 주문
1. 주문 생성 (`POST /api/orders`)
2. 포인트 차감
3. 즉시 SMM Panel API 호출
4. 주문 상태 업데이트

### 패키지 주문
1. 주문 생성 (`POST /api/orders`)
   - `package_steps` 배열 포함
2. 첫 번째 단계 처리 시작 (`POST /api/orders/start-package-processing`)
3. 각 단계별 처리 (`process_package_step`)
   - SMM Panel API 호출
   - 진행 상황 기록
   - 다음 단계 예약 (24시간 후)
4. 진행 상황 조회 (`GET /api/orders/<order_id>/package-progress`)

### 예약 주문
1. 예약 주문 생성 (`POST /api/scheduled-orders`)
   - `scheduled_datetime` 지정
2. Cron 작업이 예약 시간에 주문 처리 (`POST /api/cron/process-scheduled-orders`)
3. 실제 주문 생성 및 SMM Panel API 호출

### 분할 발송 (Drip-feed)
1. 주문 생성 시 `runs`와 `interval` 파라미터 전달
2. SMM Panel API에 drip-feed 정보 포함
3. SMM Panel에서 자동으로 분할 발송 처리

---

## 환경 변수

### 데이터베이스
```bash
DB_HOST=localhost
DB_NAME=snspmt
DB_USER=postgres
DB_PASSWORD=password
DB_PORT=5432
DATABASE_URL=postgresql://user:password@host:port/database
```

### 인증
```bash
ADMIN_TOKEN=admin_sociality_2024
```

### KCP 결제
```bash
KCP_SITE_CD=ALFCQ
KCP_SITE_KEY=your_site_key
KCP_CERT_INFO=-----BEGIN CERTIFICATE-----...-----END CERTIFICATE-----
KCP_CERT_PASSWORD=your_cert_password
KCP_ENCRYPT_KEY=your_encrypt_key
```

### SMM Panel
```bash
SMMKINGS_API_KEY=your_api_key
SMMKINGS_API_URL=https://smmkings.com/api/v2
```

### Firebase (프론트엔드용)
```bash
FIREBASE_API_KEY=your_api_key
FIREBASE_AUTH_DOMAIN=your_auth_domain
FIREBASE_PROJECT_ID=your_project_id
```

---

## API 모니터링

### 요청/응답 로깅
모든 API 요청은 자동으로 로깅됩니다:
- 요청 메서드 및 경로
- 응답 상태 코드
- 응답 시간
- 느린 요청 경고 (5초 이상)

### 성능 모니터링
`@monitor_performance` 데코레이터를 사용하여 함수 실행 시간을 모니터링합니다:
- 1초 이상 실행 시 경고 로그 출력

---

## 에러 처리

### 전역 에러 핸들러
- `404`: 리소스를 찾을 수 없음
- `500`: 서버 내부 오류
- `Exception`: 예외 발생 시 상세 로그 출력

### 에러 응답 형식
```json
{
  "error": "에러 메시지",
  "message": "상세 메시지"
}
```

---

## 참고 자료

- [데이터베이스 스키마 문서](./DATABASE_SCHEMA.md)
- [KCP 결제 연동 가이드](./KCP_PAYMENT_INTEGRATION.md)
- [AWS 배포 가이드](./AWS_DEPLOYMENT_GUIDE.md)

