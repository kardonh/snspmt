# 프론트엔드 환경변수 설정 가이드

## ❌ 수정된 오류

`process is not defined` 오류를 해결했습니다:
- `src/utils/kakaoAuth.js`: `process.env.REACT_APP_KAKAO_APP_KEY` → `import.meta.env.VITE_KAKAO_APP_KEY`
- `src/components/ErrorBoundary.jsx`: `process.env.NODE_ENV` → `import.meta.env.PROD` / `import.meta.env.DEV`
- `src/utils/logger.js`: `process.env.NODE_ENV` → `import.meta.env.PROD`

## 📋 프론트엔드 환경변수 설정

Vite에서는 `VITE_` 접두사를 사용하는 환경변수만 클라이언트에서 접근 가능합니다.

### 프로젝트 루트에 `.env` 파일 생성

```env
# ========================================================================
# 카카오 로그인 설정
# ========================================================================
VITE_KAKAO_APP_KEY=5a6e0106e9beafa7bd8199ab3c378ceb

# ========================================================================
# Firebase 설정 (프론트엔드 사용자 인증용)
# ========================================================================
VITE_FIREBASE_API_KEY=your_firebase_api_key_here
VITE_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your_project_id
VITE_FIREBASE_STORAGE_BUCKET=your_project.firebasestorage.app
VITE_FIREBASE_MESSAGING_SENDER_ID=your_sender_id
VITE_FIREBASE_APP_ID=your_app_id
VITE_FIREBASE_MEASUREMENT_ID=your_measurement_id

# ========================================================================
# 백엔드 API 베이스 URL
# ========================================================================
# 로컬 개발용
VITE_API_BASE_URL=http://localhost:8000/api

# 프로덕션용 (Render 배포 후)
# VITE_API_BASE_URL=https://your-backend.onrender.com/api

# ========================================================================
# 애플리케이션 정보
# ========================================================================
VITE_APP_NAME=SNSINTO
VITE_APP_VERSION=1.0.0
VITE_APP_ENV=development
```

## 🔧 사용 방법

### 코드에서 사용

```javascript
// ✅ 올바른 방법 (Vite)
const apiKey = import.meta.env.VITE_KAKAO_APP_KEY
const apiUrl = import.meta.env.VITE_API_BASE_URL
const isDev = import.meta.env.DEV
const isProd = import.meta.env.PROD

// ❌ 잘못된 방법 (React/CRA)
// const apiKey = process.env.REACT_APP_KAKAO_APP_KEY
```

### 환경변수 접근

- `import.meta.env.VITE_*`: 사용자 정의 환경변수
- `import.meta.env.MODE`: 현재 모드 (development/production)
- `import.meta.env.DEV`: 개발 모드 여부 (boolean)
- `import.meta.env.PROD`: 프로덕션 모드 여부 (boolean)

## 🚀 프론트엔드 실행

```bash
# 의존성 설치
npm install

# 개발 서버 실행
npm run dev

# 프로덕션 빌드
npm run build
```

## ✅ 확인

브라우저 콘솔에서 오류가 사라지고 다음 메시지가 보이면 성공:
```
✅ Firebase 초기화 성공 (Analytics 포함)
카카오 SDK 초기화 완료
```

---

**참고**: `.env` 파일은 `.gitignore`에 포함되어 있어 Git에 커밋되지 않습니다.

