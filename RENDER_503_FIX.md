# Render 503 Service Unavailable 오류 해결 가이드

## 🔴 문제
```
GET https://snspmt.onrender.com/ 503 (Service Unavailable)
```

## 🔍 원인 분석

503 오류는 일반적으로 다음 이유로 발생합니다:

1. **서비스가 시작되지 않음** (가장 흔함)
2. **데이터베이스 연결 실패**
3. **환경 변수 누락**
4. **빌드 실패**
5. **헬스 체크 실패**

## ✅ 해결 방법

### 1단계: Render 대시보드에서 로그 확인

1. https://dashboard.render.com 접속
2. `snspmt` 프로젝트 선택
3. **Logs** 탭 클릭
4. 최근 오류 메시지 확인

**확인할 오류 메시지:**
- `ModuleNotFoundError`
- `Connection refused`
- `FATAL: database connection failed`
- `ImportError`
- `psycopg2` 관련 오류

### 2단계: 환경 변수 확인

Render 대시보드 → **Environment** 탭에서 다음 변수들이 설정되어 있는지 확인:

**필수 환경 변수:**
```
DATABASE_URL=postgresql://postgres.gvtrizwkstaznrlloixi:VEOdjCwztZm4oynz@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres
SMMPANEL_API_KEY=your_api_key
ADMIN_TOKEN=admin_sociality_2024
PORT=8000
```

**Supabase 연결 문자열 형식:**
```
postgresql://postgres.gvtrizwkstaznrlloixi:VEOdjCwztZm4oynz@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres
```

### 3단계: 시작 명령어 확인

Render 대시보드 → **Settings** 탭에서 **Start Command** 확인:

**올바른 시작 명령어:**
```
gunicorn backend:app --bind 0.0.0.0:$PORT --workers 4 --timeout 120
```

### 4단계: 빌드 명령어 확인

Render 대시보드 → **Settings** 탭에서 **Build Command** 확인:

**올바른 빌드 명령어:**
```
npm install && npx vite build || echo "프론트엔드 빌드 실패, 계속 진행" && pip install -r requirements.txt
```

또는 더 안전한 버전:
```
which node || (curl -fsSL https://deb.nodesource.com/setup_18.x | sudo bash - && sudo apt-get install -y nodejs) || echo "Node.js 설치 실패" && npm install && npm run build || echo "프론트엔드 빌드 실패, 계속 진행" && pip install -r requirements.txt
```

### 5단계: Python 버전 확인

Render 대시보드 → **Settings** 탭에서 **Python Version** 확인:

**올바른 Python 버전:**
```
3.12.8
```

또는 `runtime.txt` 파일에:
```
python-3.12.8
```

### 6단계: 데이터베이스 연결 테스트

백엔드가 시작될 때 데이터베이스 연결을 시도합니다. 연결 실패 시 서비스가 시작되지 않을 수 있습니다.

**확인 사항:**
- `DATABASE_URL` 환경 변수가 올바른지
- Supabase 데이터베이스가 활성화되어 있는지
- 방화벽 규칙이 올바른지

### 7단계: 헬스 체크 확인

Render는 기본적으로 루트 경로(`/`)에 헬스 체크를 수행합니다.

**백엔드 헬스 체크 엔드포인트:**
- `GET /api/health` 또는 `GET /health`

이 엔드포인트가 정상적으로 응답하는지 확인하세요.

### 8단계: 재배포

모든 설정을 확인한 후:

1. Render 대시보드 → **Manual Deploy** → **Deploy latest commit** 클릭
2. 배포 로그를 실시간으로 확인
3. 오류 메시지가 나타나면 해당 오류를 해결

## 🔧 일반적인 오류 및 해결 방법

### 오류 1: `ModuleNotFoundError: No module named 'backend'`
**해결:** 시작 명령어가 `gunicorn backend:app`인지 확인

### 오류 2: `FATAL: database connection failed`
**해결:** 
- `DATABASE_URL` 환경 변수 확인
- Supabase 데이터베이스가 활성화되어 있는지 확인
- 연결 문자열 형식 확인

### 오류 3: `ImportError: undefined symbol: _PyInterpreterState_Get`
**해결:**
- Python 버전을 3.12.8로 설정
- `psycopg2-binary>=2.9.11` 사용

### 오류 4: `vite: Permission denied`
**해결:**
- 빌드 명령어에서 `npx vite build` 또는 `node node_modules/vite/bin/vite.js build` 사용

### 오류 5: `npm: command not found`
**해결:**
- 빌드 명령어에 Node.js 설치 단계 추가

## 📋 체크리스트

배포 전 확인 사항:

- [ ] `render.yml` 파일이 올바르게 설정되어 있음
- [ ] `Procfile`이 올바르게 설정되어 있음
- [ ] `requirements.txt`에 모든 의존성이 포함되어 있음
- [ ] `runtime.txt`에 Python 버전이 명시되어 있음
- [ ] 모든 필수 환경 변수가 Render에 설정되어 있음
- [ ] `DATABASE_URL`이 올바른 형식으로 설정되어 있음
- [ ] 시작 명령어가 `gunicorn backend:app --bind 0.0.0.0:$PORT --workers 4 --timeout 120`인지 확인
- [ ] 빌드 명령어에 Node.js 설치 및 프론트엔드 빌드가 포함되어 있음

## 🚀 빠른 해결 방법

1. **Render 대시보드 → Logs 탭**에서 오류 메시지 확인
2. **가장 최근 오류 메시지**를 복사
3. 오류 메시지를 기반으로 위의 해결 방법 적용
4. **Manual Deploy**로 재배포

## 📞 추가 도움

여전히 문제가 해결되지 않으면:
1. Render 로그의 전체 오류 메시지를 복사
2. 오류 메시지를 공유하면 더 정확한 해결 방법을 제시할 수 있습니다

