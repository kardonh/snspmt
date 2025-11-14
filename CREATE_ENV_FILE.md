# .env 파일 생성 가이드

## ✅ 빠른 생성 방법

프로젝트 루트에 `.env` 파일을 생성하고 아래 내용을 복사하세요:

```env
# ========================================================================
# 필수: 데이터베이스 설정 (Supabase)
# ========================================================================
DATABASE_URL=postgresql://postgres.gvtrizwkstaznrlloixi:KARDONH0813%21@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres

# ========================================================================
# 필수: SMM Panel API 설정
# ========================================================================
SMMPANEL_API_KEY=your_smmpanel_api_key_here

# ========================================================================
# 필수: 관리자 인증 토큰
# ========================================================================
ADMIN_TOKEN=admin_sociality_2024

# ========================================================================
# 필수: Flask 환경 설정 (로컬 개발용)
# ========================================================================
FLASK_ENV=development

# ========================================================================
# 필수: 허용된 오리진 (CORS) - 로컬 개발용
# ========================================================================
ALLOWED_ORIGINS=http://localhost:8000,http://localhost:5173,http://localhost:3000,http://127.0.0.1:8000,http://127.0.0.1:5173

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
VITE_FIREBASE_MEASUREMENT_ID=your_measurement_id
```

## 📝 Windows PowerShell에서 생성

```powershell
# .env 파일 생성
@"
DATABASE_URL=postgresql://postgres.gvtrizwkstaznrlloixi:KARDONH0813%21@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres
SMMPANEL_API_KEY=your_smmpanel_api_key_here
ADMIN_TOKEN=admin_sociality_2024
FLASK_ENV=development
ALLOWED_ORIGINS=http://localhost:8000,http://localhost:5173,http://localhost:3000
VITE_API_BASE_URL=http://localhost:8000/api
VITE_KAKAO_APP_KEY=5a6e0106e9beafa7bd8199ab3c378ceb
"@ | Out-File -FilePath .env -Encoding utf8
```

## ✅ 확인

```bash
# .env 파일이 생성되었는지 확인
ls .env

# 내용 확인 (일부만)
cat .env | head -5
```

## 🚀 실행

`.env` 파일 생성 후:

```bash
python backend.py
```

이제 환경변수를 읽어서 실행됩니다!

---

**참고**: `backend.py`에 `load_dotenv()`를 추가했으므로 `.env` 파일이 자동으로 로드됩니다.

