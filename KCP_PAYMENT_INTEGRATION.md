# KCP 표준결제 연동 가이드

## 개요
NHN KCP 표준결제 서비스를 통한 포인트 구매 시스템 연동 가이드입니다.

## 연동 플로우

### 1. 거래등록 (Mobile 필수)
- **API**: `POST /api/points/purchase-kcp/register`
- **목적**: 결제 요청 전 주문 데이터를 KCP 서버에 등록
- **필수 파라미터**:
  - `user_id`: 사용자 ID
  - `amount`: 포인트 수량
  - `price`: 결제 금액
  - `pay_method`: 결제수단 (CARD, BANK, MOBX, TPNT, GIFT)

### 2. 결제창 호출 데이터 생성
- **API**: `POST /api/points/purchase-kcp/payment-form`
- **목적**: 결제창 호출을 위한 폼 데이터 생성
- **필수 파라미터**:
  - `ordr_idxx`: 주문번호
  - `approval_key`: 거래 인증 키
  - `pay_url`: 결제창 호출 URL

### 3. 결제창 호출
- **Mobile**: 거래등록 후 받은 PayUrl로 폼 전송
- **PC**: KCP 스크립트를 통한 결제창 호출

### 4. 결제창 인증결과 처리
- **Ret_URL**: `POST /api/points/purchase-kcp/return`
- **목적**: KCP에서 전달받은 인증결과 데이터 처리

### 5. 결제요청 (승인)
- **API**: `POST /api/points/purchase-kcp/approve`
- **목적**: 인증된 데이터로 실제 결제 승인 요청
- **필수 파라미터**:
  - `ordr_idxx`: 주문번호
  - `enc_data`: 암호화된 인증 데이터
  - `enc_info`: 암호화 정보
  - `tran_cd`: 요청코드

## 환경 변수 설정

```bash
# KCP 표준결제 설정
KCP_SITE_CD=ALFCQ
KCP_SITE_KEY=2Lu3CSvPPLnuE34LaRWJR24__4
KCP_CERT_INFO=-----BEGIN CERTIFICATE-----MIIDgTCCAmmgAwIBAgIHkiG9w0...-----END CERTIFICATE-----
KCP_ENCRYPT_KEY=your_encrypt_key_here

# KCP API URLs
KCP_REGISTER_URL=https://testsmpay.kcp.co.kr/trade/register.do
KCP_PAYMENT_URL=https://stg-spl.kcp.co.kr/gw/enc/v1/payment
KCP_PAYMENT_SCRIPT=https://testspay.kcp.co.kr/plugin/kcp_spay_hub.js
```

## 사용 예시

### JavaScript (프론트엔드)
```javascript
// 1. 거래등록
const registerResult = await fetch('/api/points/purchase-kcp/register', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_id: 'user123',
    amount: 10000,
    price: 10000,
    pay_method: 'CARD'
  })
});

// 2. 결제창 호출 데이터 생성
const formData = await fetch('/api/points/purchase-kcp/payment-form', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    ordr_idxx: registerResult.ordr_idxx,
    approval_key: registerResult.kcp_response.approvalKey,
    pay_url: registerResult.kcp_response.PayUrl
  })
});

// 3. 결제창 호출
callKcpPaymentForm(formData.payment_form_data);
```

### Python (백엔드 테스트)
```python
import requests

# 거래등록
register_data = {
    'user_id': 'user123',
    'amount': 10000,
    'price': 10000,
    'pay_method': 'CARD'
}

response = requests.post('https://your-domain.com/api/points/purchase-kcp/register', 
                        json=register_data)
result = response.json()
```

## 결제수단별 파라미터

### 신용카드 (CARD)
- 기본 파라미터만 사용
- 할부 옵션: `quotaopt` (0-12개월)

### 계좌이체 (BANK)
- 기본 파라미터만 사용

### 휴대폰 (MOBX)
- `shop_user_id`: 필수 (회원 ID)
- `used_mobx`: 통신사 선택 (SKT:KTF:LGT)

### 포인트 (TPNT)
- `shop_user_id`: 필수 (회원 ID)
- `van_code`: 포인트 기관 코드
  - SCWB: 베네피아 복지 포인트
  - SCSK: OK캐쉬백

### 상품권 (GIFT)
- `shop_user_id`: 필수 (회원 ID)
- `van_code`: 상품권 기관 코드
  - SCBL: 도서상품권
  - SCHM: 해피머니
  - SCCL: 컬쳐랜드 상품권

## 오류 처리

### 거래등록 실패
- `Code != '0000'`: KCP 서버 오류
- `Message`: 오류 메시지

### 결제요청 실패
- `res_cd != '0000'`: 결제 승인 실패
- `res_msg`: 오류 메시지

### 일반적인 오류 코드
- `0000`: 정상 처리
- `0001`: 필수 파라미터 누락
- `0002`: 잘못된 파라미터
- `0003`: 인증 실패
- `0004`: 결제 실패

## 보안 고려사항

1. **서비스 인증서**: KCP에서 발급받은 인증서를 안전하게 보관
2. **HTTPS**: 모든 API 통신은 HTTPS 사용 필수
3. **데이터 검증**: 서버에서 모든 입력 데이터 검증
4. **로그 관리**: 결제 관련 로그는 안전하게 보관

## 테스트 환경

- **테스트 URL**: `https://testsmpay.kcp.co.kr`
- **테스트 사이트코드**: `ALFCQ`
- **테스트 카드번호**: `4673090000000032`

## 운영 환경

- **운영 URL**: `https://smpay.kcp.co.kr`
- **운영 사이트코드**: `ALFCQ`

## 지원

- KCP 기술지원: 1588-8700
- KCP 개발자센터: https://developers.kcp.co.kr
