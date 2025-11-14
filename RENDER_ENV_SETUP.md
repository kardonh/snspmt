# Render 환경변수 설정 완료 가이드

## ✅ 생성된 연결 문자열

비밀번호로 연결 문자열을 생성했습니다.

### Connection Pooler (권장)
```
postgresql://postgres.gvtrizwkstaznrlloixi:KARDONH0813%21@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres
```

### Direct Connection (대안)
```
postgresql://postgres:KARDONH0813%21@db.gvtrizwkstaznrlloixi.supabase.co:5432/postgres
```

**참고**: 특수문자 `!`는 URL 인코딩되어 `%21`로 변환되었습니다.

## 📋 Render 환경변수 설정 단계

### 1단계: Render 대시보드 접속
1. https://dashboard.render.com 접속
2. 로그인

### 2단계: 백엔드 서비스 선택
- 백엔드 서비스 선택

### 3단계: Environment 탭으로 이동
- 왼쪽 메뉴에서 **Environment** 탭 클릭

### 4단계: DATABASE_URL 환경변수 설정
1. `DATABASE_URL` 환경변수 찾기
   - 이미 있으면 편집
   - 없으면 **Add Environment Variable** 클릭

2. **Key**: `DATABASE_URL`

3. **Value**: 아래 연결 문자열 복사하여 붙여넣기
   ```
   postgresql://postgres.gvtrizwkstaznrlloixi:KARDONH0813%21@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres
   ```

4. **Save Changes** 클릭

### 5단계: 재배포 확인
- Render가 자동으로 재배포를 시작합니다
- 배포 완료까지 몇 분 소요될 수 있습니다

## 🔍 연결 테스트

### 배포 완료 후 확인

1. **Render 로그 확인**
   - Render 대시보드 → **Logs** 탭
   - 다음 메시지 확인:
     ```
     ✅ 환경 변수 검증 완료
     ```

2. **API 헬스 체크**
   ```bash
   curl https://your-backend.onrender.com/api/health
   ```

3. **관리자 통계 확인** (연결 테스트)
   ```bash
   curl -H "X-Admin-Token: YOUR_ADMIN_TOKEN" \
     https://your-backend.onrender.com/api/admin/stats
   ```

## ⚠️ 문제 해결

### 연결 실패 시

1. **비밀번호 확인**
   - Supabase 대시보드에서 비밀번호 재확인
   - `KARDONH0813!`가 맞는지 확인

2. **URL 인코딩 확인**
   - 특수문자 `!`는 `%21`로 인코딩되어야 함
   - 현재 연결 문자열에 이미 인코딩되어 있음

3. **로그 확인**
   - Render 로그에서 정확한 에러 메시지 확인
   - `psycopg2` 관련 에러는 연결 문자열 문제일 가능성

4. **네트워크 확인**
   - Render에서 Supabase로의 아웃바운드 연결 허용 확인

## ✅ 다음 단계

연결 성공 후:
1. `TEST_CHECKLIST.md`에 따라 기능 테스트 진행
2. 핵심 API 엔드포인트 테스트
3. 사용자 등록/로그인 테스트
4. 주문 생성 테스트

---

**지금 할 일**: Render 대시보드에서 위의 연결 문자열을 `DATABASE_URL` 환경변수로 설정하세요!

