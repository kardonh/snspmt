# 🌐 도메인 연결 가이드

## 현재 상황
- **도메인**: 소셜리티.co.kr, sociality.co.kr, sociality.kr (Gabia 등록)
- **AWS ALB**: snspmt-alb-new-404094515.ap-northeast-2.elb.amazonaws.com

## 1단계: AWS Route 53에서 호스팅 영역 생성

### 1.1 AWS 콘솔 접속
1. AWS 콘솔에 로그인
2. Route 53 서비스로 이동
3. "호스팅 영역" 클릭

### 1.2 호스팅 영역 생성
각 도메인별로 호스팅 영역 생성:

**소셜리티.co.kr**
- 도메인 이름: `소셜리티.co.kr`
- 유형: Public hosted zone
- VPC 연결: 선택하지 않음

**sociality.co.kr**
- 도메인 이름: `sociality.co.kr`
- 유형: Public hosted zone
- VPC 연결: 선택하지 않음

**sociality.kr**
- 도메인 이름: `sociality.kr`
- 유형: Public hosted zone
- VPC 연결: 선택하지 않음

### 1.3 NS 레코드 확인
각 호스팅 영역 생성 후 NS 레코드를 확인하고 기록해두세요.

## 2단계: Gabia에서 DNS 설정 변경

### 2.1 Gabia 관리자 페이지 접속
1. Gabia 홈페이지 로그인
2. "도메인 관리" → "DNS 관리" 이동

### 2.2 DNS 서버 변경
각 도메인별로 DNS 서버를 AWS Route 53으로 변경:

**소셜리티.co.kr**
- DNS 서버 1: `ns-xxx.awsdns-xx.com`
- DNS 서버 2: `ns-xxx.awsdns-xx.co.uk`
- DNS 서버 3: `ns-xxx.awsdns-xx.org`
- DNS 서버 4: `ns-xxx.awsdns-xx.net`

**sociality.co.kr**
- 동일한 NS 레코드 사용

**sociality.kr**
- 동일한 NS 레코드 사용

## 3단계: AWS Route 53에서 레코드 생성

### 3.1 A 레코드 생성 (ALB 연결)
각 호스팅 영역에서:

**루트 도메인 (소셜리티.co.kr)**
- 레코드 이름: (비워둠)
- 레코드 유형: A
- 별칭: 예
- 별칭 대상: ALB 선택
- ALB: snspmt-alb-new-404094515.ap-northeast-2.elb.amazonaws.com

**www 서브도메인 (www.소셜리티.co.kr)**
- 레코드 이름: www
- 레코드 유형: A
- 별칭: 예
- 별칭 대상: ALB 선택
- ALB: snspmt-alb-new-404094515.ap-northeast-2.elb.amazonaws.com

### 3.2 CNAME 레코드 생성 (서브도메인)
**sociality.co.kr (서브도메인으로 사용)**
- 레코드 이름: sociality
- 레코드 유형: CNAME
- 값: snspmt-alb-new-404094515.ap-northeast-2.elb.amazonaws.com

**sociality.kr (추가 도메인)**
- 레코드 이름: (비워둠)
- 레코드 유형: A
- 별칭: 예
- 별칭 대상: ALB 선택
- ALB: snspmt-alb-new-404094515.ap-northeast-2.elb.amazonaws.com

## 4단계: SSL 인증서 설정

### 4.1 AWS Certificate Manager에서 인증서 요청
1. AWS Certificate Manager 콘솔 접속
2. "인증서 요청" 클릭
3. 도메인 추가:
   - 소셜리티.co.kr
   - www.소셜리티.co.kr
   - sociality.co.kr
   - sociality.kr

### 4.2 DNS 검증
각 도메인에 대해 DNS 검증 레코드를 Route 53에 추가

### 4.3 ALB에 SSL 인증서 연결
1. ALB 콘솔 접속
2. 리스너 편집
3. HTTPS 리스너 추가 (포트 443)
4. SSL 인증서 선택

## 5단계: ALB 리스너 규칙 설정

### 5.1 HTTP → HTTPS 리다이렉트
- HTTP (포트 80) → HTTPS (포트 443) 리다이렉트 규칙 추가

### 5.2 호스트 헤더 기반 라우팅
각 도메인별로 다른 타겟 그룹으로 라우팅 (필요시)

## 6단계: DNS 전파 확인

### 6.1 DNS 전파 테스트
```bash
# DNS 전파 확인
nslookup 소셜리티.co.kr
nslookup www.소셜리티.co.kr
nslookup sociality.co.kr
nslookup sociality.kr
```

### 6.2 웹사이트 접속 테스트
- http://소셜리티.co.kr
- https://소셜리티.co.kr
- http://www.소셜리티.co.kr
- https://www.소셜리티.co.kr
- http://sociality.co.kr
- https://sociality.co.kr
- http://sociality.kr
- https://sociality.kr

## 예상 소요 시간
- DNS 전파: 24-48시간
- SSL 인증서 발급: 5-10분
- 전체 설정 완료: 1-2시간

## 주의사항
1. DNS 변경 후 전파 시간이 필요합니다
2. SSL 인증서는 도메인 소유권 검증이 필요합니다
3. ALB 헬스 체크가 정상 작동하는지 확인하세요
4. 방화벽 설정에서 80, 443 포트가 열려있는지 확인하세요

## 문제 해결
- DNS 전파가 안 될 경우: 24-48시간 대기
- SSL 인증서 발급 실패: DNS 검증 레코드 확인
- ALB 연결 실패: 보안 그룹 및 헬스 체크 확인
