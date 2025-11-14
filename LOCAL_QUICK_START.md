# 로컬 개발 빠른 시작 가이드

## ❌ 현재 문제

```
ERR_CONNECTION_REFUSED
Unexpected token '<', "<!DOCTYPE "... is not valid JSON
```

**원인**: 백엔드 서버가 실행되지 않아 프론트엔드가 API에 연결할 수 없습니다.

## ✅ 해결 방법

### 1단계: .env 파일 생성

프로젝트 루트에 `.env` 파일 생성:

```env
# ========================================================================
# 백엔드용 환경변수
# ========================================================================
DATABASE_URL=postgresql://postgres.gvtrizwkstaznrlloixi:KARDONH0813%21@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres
SMMPANEL_API_KEY=your_smmpanel_api_key_here
ADMIN_TOKEN=admin_sociality_2024
FLASK_ENV=development
ALLOWED_ORIGINS=http://localhost:8000,http://localhost:5173,http://localhost:3000

# ========================================================================
# 프론트엔드용 환경변수 (VITE_ 접두사 필수)
# ========================================================================
VITE_API_BASE_URL=http://localhost:8000/api
VITE_KAKAO_APP_KEY=5a6e0106e9beafa7bd8199ab3c378ceb
VITE_FIREBASE_API_KEY=your_firebase_api_key_here
VITE_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your_project_id
VITE_FIREBASE_STORAGE_BUCKET=your_project.firebasestorage.app
VITE_FIREBASE_MESSAGING_SENDER_ID=your_sender_id
VITE_FIREBASE_APP_ID=your_app_id
```

### 2단계: 백엔드 서버 실행

**터미널 1** (백엔드):

```bash
# Python 의존성 설치 (처음 한 번만)
pip install -r requirements.txt

# 백엔드 서버 실행
python backend.py
```

성공 메시지:
```
✅ 환경 변수 검증 완료
🚀 Backend server starting on port 8000
```

### 3단계: 프론트엔드 실행

**터미널 2** (프론트엔드):

```bash
# Node.js 의존성 설치 (처음 한 번만)
npm install

# 프론트엔드 개발 서버 실행
npm run dev
```

### 4단계: 확인

1. **백엔드 확인**: http://localhost:8000/api/health
   - JSON 응답이 보이면 성공

2. **프론트엔드 확인**: http://localhost:5173
   - 브라우저 콘솔에서 오류가 사라지면 성공

## 🔍 문제 해결

### 백엔드가 시작되지 않음

1. **환경변수 확인**
   ```bash
   # .env 파일이 있는지 확인
   ls .env
   
   # DATABASE_URL이 설정되어 있는지 확인
   cat .env | grep DATABASE_URL
   ```

2. **포트가 이미 사용 중**
   ```bash
   # Windows
   netstat -ano | findstr :8000
   taskkill /PID <PID> /F
   
   # Mac/Linux
   lsof -ti:8000 | xargs kill -9
   ```

3. **Python 의존성 확인**
   ```bash
   pip install -r requirements.txt
   ```

### 프론트엔드가 백엔드에 연결 안 됨

1. **VITE_API_BASE_URL 확인**
   ```bash
   # .env 파일에서 확인
   cat .env | grep VITE_API_BASE_URL
   ```
   값이 `http://localhost:8000/api`인지 확인

2. **백엔드 서버 실행 확인**
   - 백엔드 터미널에서 "Backend server starting on port 8000" 메시지 확인
   - http://localhost:8000/api/health 접속해서 JSON 응답 확인

3. **브라우저 새로고침**
   - 환경변수 변경 후 Vite 개발 서버 재시작 필요
   ```bash
   # Ctrl+C로 중지 후
   npm run dev
   ```

## 📋 실행 순서 요약

```bash
# 1. .env 파일 생성 (프로젝트 루트)
# 2. 백엔드 실행 (터미널 1)
pip install -r requirements.txt
python backend.py

# 3. 프론트엔드 실행 (터미널 2 - 새 터미널)
npm install
npm run dev
```

## ✅ 성공 확인

- ✅ 백엔드: http://localhost:8000/api/health → JSON 응답
- ✅ 프론트엔드: http://localhost:5173 → 오류 없음
- ✅ 브라우저 콘솔: `ERR_CONNECTION_REFUSED` 오류 없음

---

**중요**: 백엔드와 프론트엔드를 **동시에** 실행해야 합니다!

