# 🔐 보안 가이드

## 🚨 출시 전 필수 보안 체크리스트

### 1. 환경 변수 설정 ✅
- [x] Firebase API 키를 환경 변수로 이동
- [x] SMM API 키를 환경 변수로 이동
- [x] 백엔드 API 키를 환경 변수로 이동
- [x] .env 파일이 .gitignore에 포함됨

### 2. 민감한 정보 제거 ✅
- [x] 하드코딩된 API 키 제거
- [x] 디버그 로그에서 민감한 정보 제거
- [x] localhost 참조 제거

### 3. 보안 헤더 추가 ✅
- [x] X-Content-Type-Options: nosniff
- [x] X-Frame-Options: DENY
- [x] X-XSS-Protection: 1; mode=block
- [x] Strict-Transport-Security 헤더
- [x] Content-Security-Policy 헤더

### 4. CORS 설정 강화 ✅
- [x] 프로덕션 환경에서 특정 도메인만 허용
- [x] 개발 환경과 프로덕션 환경 분리

### 5. 프로덕션 환경 설정

#### 환경 변수 설정
```bash
# Firebase 설정
VITE_FIREBASE_API_KEY=your_actual_firebase_api_key
VITE_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your_project_id
VITE_FIREBASE_STORAGE_BUCKET=your_project.firebasestorage.app
VITE_FIREBASE_MESSAGING_SENDER_ID=your_sender_id
VITE_FIREBASE_APP_ID=your_app_id
VITE_FIREBASE_MEASUREMENT_ID=your_measurement_id

# SMM API 설정
VITE_SMMKINGS_API_KEY=your_actual_smmkings_api_key
VITE_SMMPANEL_API_KEY=18b03d2cd9babd365fa9bd0c5635a781

# 백엔드 API 설정
VITE_API_BASE_URL=https://your-domain.com/api

# 환경 설정
VITE_APP_ENV=production
```

#### 서버 환경 변수 (Render/Heroku 등)
```bash
SMMPANEL_API_KEY=your_actual_smmpanel_api_key
FLASK_ENV=production
```

### 6. 추가 보안 권장사항

#### 데이터베이스 보안
- [ ] SQLite 대신 PostgreSQL/MySQL 사용
- [ ] 데이터베이스 연결 암호화
- [ ] 정기적인 백업 설정

#### 인증 보안
- [ ] Firebase Auth 보안 규칙 설정
- [ ] 비밀번호 정책 강화
- [ ] 2FA 인증 고려

#### API 보안
- [ ] Rate Limiting 구현
- [ ] API 키 로테이션 정책
- [ ] 요청 검증 강화

#### 모니터링
- [ ] 로그 모니터링 설정
- [ ] 에러 추적 시스템
- [ ] 성능 모니터링

### 7. 출시 전 최종 체크

#### 코드 검토
- [ ] 모든 API 키가 환경 변수로 설정됨
- [ ] 민감한 정보가 로그에 노출되지 않음
- [ ] CORS 설정이 올바름
- [ ] 보안 헤더가 적용됨

#### 환경 설정
- [ ] 프로덕션 환경 변수 설정
- [ ] SSL 인증서 적용
- [ ] 도메인 설정 완료

#### 테스트
- [ ] 인증 기능 테스트
- [ ] API 연동 테스트
- [ ] 결제 기능 테스트
- [ ] 관리자 기능 테스트

## 🛡️ 보안 모범 사례

### 1. API 키 관리
- 절대 소스코드에 API 키를 하드코딩하지 마세요
- 환경 변수를 사용하여 API 키를 관리하세요
- 정기적으로 API 키를 로테이션하세요

### 2. 로그 관리
- 민감한 정보를 로그에 기록하지 마세요
- 프로덕션 환경에서는 디버그 로그를 비활성화하세요
- 로그 파일에 대한 접근 권한을 제한하세요

### 3. CORS 설정
- 필요한 도메인만 허용하세요
- 개발 환경과 프로덕션 환경을 분리하세요
- 불필요한 HTTP 메서드는 허용하지 마세요

### 4. 인증 및 권한
- 강력한 비밀번호 정책을 적용하세요
- 세션 관리에 주의하세요
- 관리자 권한을 신중하게 부여하세요

## 🚨 보안 사고 대응

### 1. API 키 노출 시
1. 즉시 API 키를 재발급하세요
2. 노출된 키를 무효화하세요
3. 환경 변수를 업데이트하세요
4. 로그를 확인하여 악용 여부를 점검하세요

### 2. 데이터 유출 시
1. 영향을 받은 데이터를 식별하세요
2. 관련 사용자에게 알림하세요
3. 보안 취약점을 수정하세요
4. 재발 방지 대책을 수립하세요

## 📞 보안 문의

보안 관련 문의사항이 있으시면 즉시 연락주세요.
- 이메일: security@yourdomain.com
- 긴급 연락: +82-XXX-XXXX-XXXX
