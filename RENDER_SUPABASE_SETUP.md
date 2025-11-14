# Render에서 Supabase 연결 설정 가이드

## 현재 Supabase 프로젝트 정보
- **프로젝트 ID**: `gvtrizwkstaznrlloixi`
- **프로젝트 URL**: `https://gvtrizwkstaznrlloixi.supabase.co`
- **데이터베이스 호스트**: `db.gvtrizwkstaznrlloixi.supabase.co`
- **지역**: `ap-southeast-2`

## 1. Supabase 데이터베이스 비밀번호 확인

1. [Supabase 대시보드](https://supabase.com/dashboard)에 로그인
2. 프로젝트 `sociality` 선택
3. **Settings** → **Database** 메뉴로 이동
4. **Database password** 섹션에서 비밀번호 확인 또는 재설정
   - 비밀번호를 모르면 **Reset database password** 클릭하여 새 비밀번호 생성

## 2. Supabase 연결 문자열 구성

Supabase는 두 가지 연결 방식을 제공합니다:

### 방식 1: Connection Pooler (권장 - 성능 최적화)
```
postgresql://postgres.gvtrizwkstaznrlloixi:[PASSWORD]@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres
```

### 방식 2: Direct Connection (직접 연결)
```
postgresql://postgres:[PASSWORD]@db.gvtrizwkstaznrlloixi.supabase.co:5432/postgres
```

**참고**: `[PASSWORD]` 부분을 위에서 확인한 실제 비밀번호로 교체하세요.

## 3. Render 환경변수 설정

### Render 대시보드에서 설정

1. **Render 대시보드** → 백엔드 서비스 선택
2. **Environment** 탭으로 이동
3. 다음 환경변수 추가/수정:

#### 필수 환경변수
```
DATABASE_URL=postgresql://postgres.gvtrizwkstaznrlloixi:[PASSWORD]@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres
```

**중요**: `[PASSWORD]`를 실제 Supabase DB 비밀번호로 교체하세요.

#### 기존 환경변수 유지
```
SMMPANEL_API_KEY=your_smmpanel_api_key
ADMIN_TOKEN=your_admin_token
# 기타 필요한 환경변수들...
```

### 환경변수 설정 후

1. **Save Changes** 클릭
2. Render가 자동으로 서비스를 재배포합니다
3. 배포 완료 후 로그에서 연결 성공 여부 확인

## 4. 연결 테스트

배포 후 다음 방법으로 연결을 확인할 수 있습니다:

### 방법 1: Render 로그 확인
- Render 대시보드 → **Logs** 탭
- 다음 메시지가 보이면 성공:
  ```
  ✅ 환경 변수 검증 완료
  ✅ 데이터베이스 연결 성공
  ```

### 방법 2: API 엔드포인트 테스트
```bash
# 헬스 체크 (백엔드가 실행 중인지 확인)
curl https://your-backend.onrender.com/api/health

# 데이터베이스 연결 확인 (관리자 API)
curl -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  https://your-backend.onrender.com/api/admin/stats
```

## 5. 문제 해결

### 연결 실패 시 확인 사항

1. **비밀번호 확인**
   - Supabase 콘솔에서 비밀번호가 올바른지 확인
   - URL 인코딩 필요 시 특수문자 이스케이프 처리

2. **네트워크 접근**
   - Render에서 Supabase로의 아웃바운드 연결이 차단되지 않았는지 확인
   - Supabase IP 화이트리스트 설정이 있다면 Render IP 추가

3. **연결 문자열 형식**
   - Connection Pooler 사용 시 포트는 `6543`
   - Direct Connection 사용 시 포트는 `5432`
   - 프로토콜은 `postgresql://`로 시작

4. **로그 확인**
   - Render 로그에서 정확한 에러 메시지 확인
   - `psycopg2` 관련 에러가 있다면 연결 문자열 문제일 가능성 높음

## 6. 마이그레이션 스크립트 실행 (선택)

기존 데이터가 있다면 마이그레이션을 실행해야 합니다:

```bash
# Render 서비스에서 직접 실행하거나
# 로컬에서 DATABASE_URL을 Supabase로 설정 후 실행
python migrate_database.py
```

**참고**: 현재 Supabase에는 이미 새 스키마가 생성되어 있으므로, 기존 데이터 마이그레이션이 필요한 경우에만 실행하세요.

## 7. 다음 단계

1. ✅ Supabase 스키마 생성 완료
2. ✅ Render 환경변수 설정 가이드 작성
3. ⏭️ Render 환경변수 실제 설정 (수동 작업 필요)
4. ⏭️ 연결 테스트 및 검증
5. ⏭️ 기존 데이터 마이그레이션 (필요한 경우)
6. ⏭️ 전체 기능 테스트 (TEST_CHECKLIST.md 참고)

