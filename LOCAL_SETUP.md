# 로컬 개발 환경 설정 가이드

## 📋 빠른 시작

### 1단계: .env 파일 생성

```bash
# .env.local.example을 .env로 복사
cp .env.local.example .env
```

또는 직접 `.env` 파일을 생성하고 아래 내용을 복사하세요.

### 2단계: 필수 환경변수 설정

`.env` 파일을 열고 다음 값들을 실제 값으로 교체:

```env
# 필수: Supabase 데이터베이스 (이미 설정됨)
DATABASE_URL=postgresql://postgres.gvtrizwkstaznrlloixi:KARDONH0813%21@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres

# 필수: SMM Panel API 키 (실제 값으로 교체 필요)
SMMPANEL_API_KEY=your_smmpanel_api_key_here

# 필수: 관리자 토큰
ADMIN_TOKEN=admin_sociality_2024

# 필수: Flask 환경 (로컬 개발용)
FLASK_ENV=development

# 필수: CORS 설정 (로컬 개발용)
ALLOWED_ORIGINS=http://localhost:8000,http://localhost:5173,http://localhost:3000,http://127.0.0.1:8000,http://127.0.0.1:5173
```

### 3단계: Python 의존성 설치

```bash
pip install -r requirements.txt
```

### 4단계: 애플리케이션 실행

#### 방법 1: 직접 실행 (권장)

```bash
python backend.py
```

또는

```bash
python app.py
```

#### 방법 2: Gunicorn 사용 (프로덕션 모드)

```bash
gunicorn backend:app --bind 0.0.0.0:8000 --workers 2 --timeout 120 --reload
```

#### 방법 3: Docker Compose 사용

```bash
docker-compose up
```

## ✅ 확인

서버가 시작되면 다음 메시지가 보입니다:

```
✅ 환경 변수 검증 완료
🚀 Backend server starting on port 8000
```

브라우저에서 접속:
- http://localhost:8000
- http://localhost:8000/api/health

## 🔧 환경변수 설명

### 필수 환경변수

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `DATABASE_URL` | Supabase 데이터베이스 연결 문자열 | `postgresql://postgres.gvtrizwkstaznrlloixi:...` |
| `SMMPANEL_API_KEY` | SMM Panel API 키 | `your_api_key` |
| `ADMIN_TOKEN` | 관리자 인증 토큰 | `admin_sociality_2024` |
| `FLASK_ENV` | Flask 환경 (development/production) | `development` |
| `ALLOWED_ORIGINS` | CORS 허용 도메인 | `http://localhost:8000,...` |

### 선택적 환경변수

- `VITE_KAKAO_APP_KEY`: 카카오 로그인 앱 키
- `VITE_FIREBASE_*`: Firebase 설정 (프론트엔드 인증용)
- `KCP_*`: KCP 결제 설정
- `VITE_API_BASE_URL`: 프론트엔드 API URL

## 🎨 프론트엔드 환경변수

프론트엔드에서 사용하는 환경변수는 `VITE_` 접두사를 사용합니다.

프로젝트 루트의 `.env` 파일에 추가:

```env
# 카카오 로그인
VITE_KAKAO_APP_KEY=5a6e0106e9beafa7bd8199ab3c378ceb

# Firebase (실제 값으로 교체)
VITE_FIREBASE_API_KEY=your_firebase_api_key_here
VITE_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your_project_id
VITE_FIREBASE_STORAGE_BUCKET=your_project.firebasestorage.app
VITE_FIREBASE_MESSAGING_SENDER_ID=your_sender_id
VITE_FIREBASE_APP_ID=your_app_id

# API URL
VITE_API_BASE_URL=http://localhost:8000/api
```

**참고**: `FRONTEND_ENV_SETUP.md` 파일에 상세한 가이드가 있습니다.

## 🐛 문제 해결

### 데이터베이스 연결 실패

1. Supabase 대시보드에서 연결 문자열 확인
2. 비밀번호가 올바른지 확인
3. 네트워크 연결 확인

### 포트가 이미 사용 중

```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Mac/Linux
lsof -ti:8000 | xargs kill -9
```

### 모듈을 찾을 수 없음

```bash
# 가상환경 활성화 (권장)
python -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate  # Windows

# 의존성 재설치
pip install -r requirements.txt
```

## 📝 참고

- 로컬 개발 시 `FLASK_ENV=development`로 설정하면 디버그 모드가 활성화됩니다
- `.env` 파일은 `.gitignore`에 포함되어 있어 Git에 커밋되지 않습니다
- Supabase는 로컬에서도 동일하게 사용할 수 있습니다 (네트워크 연결 필요)

---

**다음 단계**: `.env` 파일 생성 후 `python backend.py` 실행

