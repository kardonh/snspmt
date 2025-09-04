# 🚀 도메인 연결 단계별 실행 가이드

## ⚡ 빠른 실행 순서

### 1️⃣ AWS Route 53 호스팅 영역 생성 (5분)
```
1. AWS 콘솔 → Route 53 → 호스팅 영역
2. "호스팅 영역 생성" 클릭
3. 도메인 이름: 소셜리티.co.kr
4. 유형: Public hosted zone
5. 생성 완료 후 NS 레코드 복사
```

### 2️⃣ Gabia DNS 서버 변경 (10분)
```
1. Gabia 로그인 → 도메인 관리 → DNS 관리
2. 소셜리티.co.kr 선택
3. DNS 서버 변경
4. AWS Route 53 NS 레코드 입력
5. 저장
```

### 3️⃣ Route 53 레코드 생성 (10분)
```
1. Route 53 호스팅 영역 선택
2. "레코드 생성" 클릭
3. A 레코드 생성:
   - 이름: (비워둠)
   - 유형: A
   - 별칭: 예
   - 대상: ALB 선택
4. www 서브도메인도 동일하게 생성
```

### 4️⃣ SSL 인증서 요청 (5분)
```
1. AWS Certificate Manager
2. "인증서 요청" 클릭
3. 도메인 추가:
   - 소셜리티.co.kr
   - www.소셜리티.co.kr
4. DNS 검증 선택
5. 검증 레코드 생성
```

### 5️⃣ ALB에 SSL 인증서 연결 (5분)
```
1. ALB 콘솔 → 리스너
2. "리스너 추가" 클릭
3. 포트: 443, 프로토콜: HTTPS
4. SSL 인증서 선택
5. 기본 작업: 포워드
```

## 🔧 자동화 스크립트 (선택사항)

### AWS CLI로 호스팅 영역 생성
```bash
# 호스팅 영역 생성
aws route53 create-hosted-zone \
  --name 소셜리티.co.kr \
  --caller-reference $(date +%s) \
  --hosted-zone-config Comment="SNS Panel Domain"

# NS 레코드 확인
aws route53 get-hosted-zone --id /hostedzone/ZONE_ID
```

### 레코드 생성
```bash
# A 레코드 생성
aws route53 change-resource-record-sets \
  --hosted-zone-id ZONE_ID \
  --change-batch file://change-batch.json
```

## 📋 체크리스트

### ✅ AWS 설정
- [ ] Route 53 호스팅 영역 생성
- [ ] NS 레코드 확인 및 복사
- [ ] A 레코드 생성 (루트 도메인)
- [ ] A 레코드 생성 (www 서브도메인)
- [ ] SSL 인증서 요청
- [ ] DNS 검증 레코드 생성
- [ ] ALB에 SSL 인증서 연결
- [ ] HTTP → HTTPS 리다이렉트 설정

### ✅ Gabia 설정
- [ ] DNS 서버를 AWS Route 53으로 변경
- [ ] 변경 사항 저장
- [ ] DNS 전파 확인

### ✅ 테스트
- [ ] DNS 전파 확인 (nslookup)
- [ ] HTTP 접속 테스트
- [ ] HTTPS 접속 테스트
- [ ] SSL 인증서 확인
- [ ] 리다이렉트 동작 확인

## ⏱️ 예상 소요 시간
- **전체 설정**: 30-45분
- **DNS 전파**: 24-48시간
- **SSL 인증서 발급**: 5-10분

## 🚨 주의사항
1. **DNS 변경 전**: 기존 서비스 백업
2. **비즈니스 시간**: 서비스 중단 최소화
3. **DNS 전파**: 24-48시간 대기 필요
4. **SSL 인증서**: 도메인 소유권 검증 필요

## 🔍 문제 해결
- **DNS 전파 안됨**: 24-48시간 대기
- **SSL 인증서 실패**: DNS 검증 레코드 확인
- **ALB 연결 안됨**: 보안 그룹 및 헬스 체크 확인
- **리다이렉트 안됨**: ALB 리스너 규칙 확인
