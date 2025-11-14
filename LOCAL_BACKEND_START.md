# 로컬 백엔드 실행 가이드

## 문제
프론트엔드에서 `ERR_CONNECTION_REFUSED` 오류가 발생하는 경우, 백엔드가 실행되지 않았습니다.

## 해결 방법

### 1. 백엔드 실행

터미널에서 다음 명령어를 실행하세요:

```bash
python backend.py
```

백엔드가 정상적으로 시작되면 다음과 같은 메시지가 표시됩니다:

```
✅ 환경 변수 검증 완료
🚀 SNS PMT 앱 시작 중...
✅ 데이터베이스 초기화 완료
✅ 앱 시작 완료
🚀 백그라운드 스케줄러 시작됨
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:8000
 * Running on http://172.30.1.40:8000
Press CTRL+C to quit
```

### 2. 프론트엔드 실행

**새 터미널 창**에서 다음 명령어를 실행하세요:

```bash
npm run dev
```

프론트엔드는 `http://localhost:3000`에서 실행됩니다.

### 3. 환경 변수 확인

백엔드가 실행되려면 `.env` 파일이 필요합니다. 프로젝트 루트에 `.env` 파일을 생성하고 다음 내용을 추가하세요:

```env
DATABASE_URL=postgresql://postgres.gvtrizwkstaznrlloixi:VEOdjCwztZm4oynz@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres?pgbouncer=true
SMMPANEL_API_KEY=your_smmpanel_api_key_here
ADMIN_TOKEN=your_admin_token_here
```

### 4. 두 터미널 실행

로컬 개발 시에는 **두 개의 터미널**이 필요합니다:

1. **터미널 1**: 백엔드 실행 (`python backend.py`)
2. **터미널 2**: 프론트엔드 실행 (`npm run dev`)

### 5. Vite 프록시 설정

`vite.config.js`에 프록시 설정이 추가되었습니다. 이제 프론트엔드에서 `/api/*` 요청이 자동으로 `http://localhost:8000/api/*`로 프록시됩니다.

## 문제 해결

### 백엔드가 시작되지 않는 경우

1. **Python 버전 확인**: Python 3.11 이상이 필요합니다.
   ```bash
   python --version
   ```

2. **의존성 설치 확인**:
   ```bash
   pip install -r requirements.txt
   ```

3. **환경 변수 확인**: `.env` 파일이 올바르게 설정되었는지 확인하세요.

4. **포트 충돌 확인**: 다른 프로세스가 포트 8000을 사용하고 있는지 확인하세요.
   ```bash
   # Windows
   netstat -ano | findstr :8000
   
   # Mac/Linux
   lsof -i :8000
   ```

### 프론트엔드가 백엔드에 연결되지 않는 경우

1. **백엔드 실행 확인**: 백엔드가 `http://localhost:8000`에서 실행 중인지 확인하세요.

2. **브라우저 콘솔 확인**: 개발자 도구(F12)에서 네트워크 탭을 확인하세요.

3. **CORS 오류**: 백엔드의 CORS 설정이 올바른지 확인하세요.

## 빠른 시작

```bash
# 터미널 1: 백엔드 실행
python backend.py

# 터미널 2: 프론트엔드 실행
npm run dev
```

이제 브라우저에서 `http://localhost:3000`을 열면 정상적으로 작동합니다!

