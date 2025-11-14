# .env 파일 DATABASE_URL 수정 가이드

## 🔧 수정 방법

### 1단계: .env 파일 열기

프로젝트 루트의 `.env` 파일을 텍스트 에디터로 엽니다.

### 2단계: DATABASE_URL 수정

**기존 (오류 발생)**:
```env
DATABASE_URL=postgresql://postgres.gvtrizwkstaznrlloixi:KARDONH0813%21@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres
```

**수정 (Direct Connection - 권장)**:
```env
DATABASE_URL=postgresql://postgres:KARDONH0813%21@db.gvtrizwkstaznrlloixi.supabase.co:5432/postgres
```

### 3단계: 저장 후 재시작

```bash
python backend.py
```

## ✅ 성공 확인

다음 메시지가 보이면 성공:
```
✅ 환경 변수 검증 완료
🚀 SNS PMT 앱 시작 중...
✅ 데이터베이스 초기화 완료
```

## 🔍 차이점

| 항목 | Pooler (오류) | Direct Connection (수정) |
|------|--------------|-------------------------|
| 사용자 이름 | `postgres.gvtrizwkstaznrlloixi` | `postgres` |
| 호스트 | `aws-0-ap-southeast-2.pooler.supabase.com` | `db.gvtrizwkstaznrlloixi.supabase.co` |
| 포트 | `6543` | `5432` |

## ⚠️ 참고

- 비밀번호의 `!`는 `%21`로 URL 인코딩되어 있습니다
- Direct Connection은 더 안정적입니다
- Supabase MCP로 테스트한 결과 데이터베이스는 정상입니다

