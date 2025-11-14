# Render 환경변수 설정 완료 가이드

## 📋 Render에 설정할 환경변수 목록

아래 환경변수들을 Render 대시보드의 **Environment** 탭에 추가하세요.

## ✅ 필수 환경변수 (반드시 설정 필요)

### 1. DATABASE_URL
```
postgresql://postgres.gvtrizwkstaznrlloixi:KARDONH0813%21@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres
```
**설명**: Supabase 데이터베이스 연결 문자열 (이미 생성됨)

### 2. SMMPANEL_API_KEY
```
your_smmpanel_api_key_here
```
**설명**: SMM Panel API 키 (실제 값으로 교체 필요)
**찾는 방법**: SMM Panel 대시보드에서 API 키 확인

### 3. ADMIN_TOKEN
```
admin_sociality_2024
```
**설명**: 관리자 API 인증 토큰 (변경 권장)

### 4. FLASK_ENV
```
production
```
**설명**: Flask 실행 환경

### 5. ALLOWED_ORIGINS
```
https://your-frontend-domain.onrender.com,https://your-custom-domain.com
```
**설명**: CORS 허용 도메인 (실제 프론트엔드 URL로 교체 필요)

## 🔧 선택적 환경변수 (기능 사용 시 설정)

### Firebase 설정 (프론트엔드 인증용)
```
VITE_FIREBASE_API_KEY=your_firebase_api_key_here
VITE_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your_project_id
VITE_FIREBASE_STORAGE_BUCKET=your_project.firebasestorage.app
VITE_FIREBASE_MESSAGING_SENDER_ID=your_sender_id
VITE_FIREBASE_APP_ID=your_app_id
VITE_FIREBASE_MEASUREMENT_ID=your_measurement_id
```

### KCP 결제 설정 (결제 기능 사용 시)
```
KCP_SITE_CD=your_site_cd
KCP_SITE_KEY=your_site_key
KCP_CERT_INFO=your_cert_info
KCP_CERT_PASSWORD=your_cert_password
KCP_ENCRYPT_KEY=your_encrypt_key
```

### 프론트엔드 API URL
```
VITE_API_BASE_URL=https://your-backend.onrender.com/api
```
**설명**: Render 백엔드 URL로 교체 (예: `https://snspmt.onrender.com/api`)

### 애플리케이션 정보
```
VITE_APP_NAME=SNSINTO
VITE_APP_VERSION=1.0.0
VITE_APP_ENV=production
```

## 📝 Render에서 설정하는 방법

### 1단계: Render 대시보드 접속
1. https://dashboard.render.com 접속
2. 로그인

### 2단계: 프로젝트 선택
- `snspmt` 프로젝트 선택

### 3단계: Environment 탭
- 왼쪽 메뉴에서 **Environment** 탭 클릭

### 4단계: 환경변수 추가
각 환경변수를 하나씩 추가:

1. **Add Environment Variable** 클릭
2. **Key** 입력 (예: `DATABASE_URL`)
3. **Value** 입력 (위의 값 복사)
4. **Save Changes** 클릭

또는 여러 개를 한 번에 추가하려면:
- 각 환경변수를 개별적으로 추가
- 모든 환경변수 추가 후 **Save Changes** 클릭

### 5단계: 재배포 확인
- Render가 자동으로 재배포 시작
- 배포 완료까지 몇 분 소요

## ✅ 최소 필수 설정 (빠른 시작)

가장 빠르게 시작하려면 다음 5개만 설정:

1. `DATABASE_URL` (이미 생성됨)
2. `SMMPANEL_API_KEY` (실제 값 필요)
3. `ADMIN_TOKEN` (기본값 사용 가능)
4. `FLASK_ENV=production`
5. `ALLOWED_ORIGINS` (프론트엔드 URL)

나머지는 필요에 따라 추가하세요.

## 🔍 설정 확인

### 배포 후 로그 확인
Render 대시보드 → **Logs** 탭에서:
```
✅ 환경 변수 검증 완료
```

이 메시지가 보이면 성공!

### API 테스트
```bash
curl https://your-backend.onrender.com/api/health
```

## ⚠️ 주의사항

1. **비밀번호 보안**: `DATABASE_URL`에 비밀번호가 포함되어 있으므로 안전하게 관리
2. **API 키 보안**: `SMMPANEL_API_KEY`는 절대 공개하지 마세요
3. **CORS 설정**: `ALLOWED_ORIGINS`에 실제 프론트엔드 도메인만 추가
4. **환경변수 업데이트**: 변경 후 반드시 **Save Changes** 클릭

---

**다음 단계**: 환경변수 설정 완료 후 `TEST_CHECKLIST.md`에 따라 기능 테스트 진행

