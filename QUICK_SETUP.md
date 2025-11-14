# 빠른 설정 가이드

## 현재 상태
✅ Supabase 데이터베이스 스키마 생성 완료 (23개 테이블)  
✅ Render MCP 설정 완료  
⏳ Render 환경변수 설정 필요  

## 1단계: Supabase 비밀번호 확인

1. [Supabase 대시보드](https://supabase.com/dashboard) 로그인
2. 프로젝트 `sociality` 선택
3. **Settings** → **Database**
4. **Database password** 확인 또는 **Reset database password** 클릭

## 2단계: 연결 문자열 생성

### 방법 A: Python 스크립트 사용 (권장)

```bash
python setup_render_env.py
```

비밀번호를 입력하면 연결 문자열이 자동 생성됩니다.

### 방법 B: 수동 생성

비밀번호를 `YOUR_PASSWORD`로 교체:

**Connection Pooler (권장)**:
```
postgresql://postgres.gvtrizwkstaznrlloixi:YOUR_PASSWORD@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres
```

**Direct Connection**:
```
postgresql://postgres:YOUR_PASSWORD@db.gvtrizwkstaznrlloixi.supabase.co:5432/postgres
```

## 3단계: Render 환경변수 설정

1. [Render 대시보드](https://dashboard.render.com) 로그인
2. 백엔드 서비스 선택
3. **Environment** 탭
4. `DATABASE_URL` 환경변수 추가/수정
5. 위에서 생성한 연결 문자열 붙여넣기
6. **Save Changes** 클릭

## 4단계: 연결 테스트

배포 완료 후:

1. **Render 로그 확인**
   - 다음 메시지 확인:
     ```
     ✅ 환경 변수 검증 완료
     ```

2. **API 테스트**
   ```bash
   curl https://your-backend.onrender.com/api/health
   ```

## 문제 해결

### 연결 실패 시
- 비밀번호 재확인 (Supabase 대시보드)
- 연결 문자열 형식 확인 (특수문자 URL 인코딩)
- Render 로그에서 정확한 에러 메시지 확인

---

**다음**: 연결 성공 후 `TEST_CHECKLIST.md`에 따라 기능 테스트 진행

