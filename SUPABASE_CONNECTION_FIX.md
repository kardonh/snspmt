# Supabase 연결 오류 해결 가이드

## ❌ 현재 오류

```
FATAL: Tenant or user not found
```

## 🔍 원인 분석

Supabase Pooler 연결 문자열 형식이 잘못되었을 수 있습니다.

## ✅ 해결 방법

### 방법 1: Direct Connection 사용 (권장)

`.env` 파일에서 `DATABASE_URL`을 Direct Connection 형식으로 변경:

```env
# Direct Connection (포트 5432)
DATABASE_URL=postgresql://postgres:KARDONH0813%21@db.gvtrizwkstaznrlloixi.supabase.co:5432/postgres
```

**차이점**:
- 사용자 이름: `postgres` (Pooler는 `postgres.gvtrizwkstaznrlloixi`)
- 호스트: `db.gvtrizwkstaznrlloixi.supabase.co` (Pooler는 `aws-0-ap-southeast-2.pooler.supabase.com`)
- 포트: `5432` (Pooler는 `6543`)

### 방법 2: Pooler Transaction Mode 사용

```env
# Pooler Transaction Mode (포트 5432)
DATABASE_URL=postgresql://postgres.gvtrizwkstaznrlloixi:KARDONH0813%21@aws-0-ap-southeast-2.pooler.supabase.com:5432/postgres
```

### 방법 3: 비밀번호 재확인

1. [Supabase 대시보드](https://supabase.com/dashboard) 접속
2. 프로젝트 `sociality` 선택
3. **Settings** → **Database**
4. **Database password** 확인
5. 비밀번호가 `KARDONH0813!`가 맞는지 확인
6. 다르다면 `.env` 파일의 비밀번호 부분 수정

## 📝 .env 파일 수정

프로젝트 루트의 `.env` 파일을 열고:

```env
# 기존 (오류 발생)
# DATABASE_URL=postgresql://postgres.gvtrizwkstaznrlloixi:KARDONH0813%21@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres

# 수정 (Direct Connection - 권장)
DATABASE_URL=postgresql://postgres:KARDONH0813%21@db.gvtrizwkstaznrlloixi.supabase.co:5432/postgres
```

## ✅ 테스트

수정 후 백엔드 재시작:

```bash
python backend.py
```

성공 메시지:
```
✅ 환경 변수 검증 완료
🚀 SNS PMT 앱 시작 중...
✅ 데이터베이스 초기화 완료
```

## 🔍 연결 문자열 형식 비교

| 연결 방식 | 사용자 이름 | 호스트 | 포트 |
|---------|----------|--------|------|
| **Direct Connection** | `postgres` | `db.gvtrizwkstaznrlloixi.supabase.co` | `5432` |
| **Pooler Session** | `postgres.gvtrizwkstaznrlloixi` | `aws-0-ap-southeast-2.pooler.supabase.com` | `6543` |
| **Pooler Transaction** | `postgres.gvtrizwkstaznrlloixi` | `aws-0-ap-southeast-2.pooler.supabase.com` | `5432` |

## ⚠️ 참고사항

- **비밀번호 특수문자**: `!`는 URL 인코딩하여 `%21`로 변환
- **Direct Connection**: 더 안정적이지만 동시 연결 수 제한 (Supabase 무료 플랜: 60개)
- **Pooler**: 더 많은 동시 연결 지원 (무료 플랜: 200개)

---

**권장**: Direct Connection으로 먼저 테스트하고, 문제가 없으면 Pooler로 전환

