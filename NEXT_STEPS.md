# 다음 단계: Render + Supabase 연결 완료하기

## 현재 상태
✅ Supabase 데이터베이스 스키마 생성 완료  
✅ Render MCP 설정 완료  
⏳ Render 환경변수 설정 필요  
⏳ 연결 테스트 필요  

## 1단계: Supabase DB 비밀번호 확인

### 방법 1: Supabase 대시보드에서 확인
1. [Supabase 대시보드](https://supabase.com/dashboard) 로그인
2. 프로젝트 `sociality` 선택
3. **Settings** → **Database** 메뉴
4. **Database password** 섹션에서 비밀번호 확인
   - 비밀번호를 모르면 **Reset database password** 클릭하여 새 비밀번호 생성
   - **중요**: 새 비밀번호를 안전한 곳에 저장하세요!

### 방법 2: Supabase CLI 사용 (선택)
```bash
# Supabase CLI 설치 후
supabase db dump --password
```

## 2단계: Render 환경변수 설정

### 옵션 A: Render 대시보드에서 직접 설정 (권장)

1. [Render 대시보드](https://dashboard.render.com) 로그인
2. 백엔드 서비스 선택
3. **Environment** 탭 클릭
4. `DATABASE_URL` 환경변수 찾기 또는 새로 추가
5. 다음 값으로 설정 (비밀번호 부분 교체):
   ```
   postgresql://postgres.gvtrizwkstaznrlloixi:[YOUR_PASSWORD]@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres
   ```
6. **Save Changes** 클릭
7. Render가 자동으로 재배포 시작

### 옵션 B: Render MCP 사용 (실험적)

Render MCP를 통해 환경변수를 설정할 수 있는지 확인 중입니다.  
현재는 Render 대시보드에서 직접 설정하는 것을 권장합니다.

## 3단계: 연결 테스트

### 배포 완료 후 확인

1. **Render 로그 확인**
   - Render 대시보드 → **Logs** 탭
   - 다음 메시지 확인:
     ```
     ✅ 환경 변수 검증 완료
     ✅ 데이터베이스 연결 성공
     ```

2. **API 테스트**
   ```bash
   # 헬스 체크
   curl https://your-backend.onrender.com/api/health
   
   # 관리자 통계 (연결 확인)
   curl -H "X-Admin-Token: YOUR_ADMIN_TOKEN" \
     https://your-backend.onrender.com/api/admin/stats
   ```

## 4단계: 기능 테스트

`TEST_CHECKLIST.md` 파일에 따라 핵심 기능 테스트:

- ✅ 사용자 등록/로그인
- ✅ 지갑 잔액 조회
- ✅ 포인트 충전 (KCP)
- ✅ 주문 생성 (단일/패키지/예약)
- ✅ 추천인/커미션 시스템
- ✅ 관리자 카탈로그 관리

## 문제 해결

### 연결 실패 시

1. **비밀번호 확인**
   - Supabase 콘솔에서 비밀번호 재확인
   - URL 인코딩 필요 시 특수문자 이스케이프 처리

2. **연결 문자열 형식 확인**
   - Connection Pooler: 포트 `6543` 사용
   - Direct Connection: 포트 `5432` 사용
   - 프로토콜: `postgresql://`로 시작

3. **네트워크 확인**
   - Render에서 Supabase로의 아웃바운드 연결 허용 확인
   - Supabase IP 화이트리스트 설정 확인

4. **로그 확인**
   - Render 로그에서 정확한 에러 메시지 확인
   - `psycopg2` 관련 에러는 연결 문자열 문제일 가능성 높음

## 다음 작업

1. ⏭️ Supabase DB 비밀번호 확인
2. ⏭️ Render 환경변수 설정
3. ⏭️ 연결 테스트
4. ⏭️ 전체 기능 테스트

---

**지금 해야 할 일**: Supabase 대시보드에서 DB 비밀번호를 확인한 후, Render의 `DATABASE_URL` 환경변수를 업데이트하세요!

