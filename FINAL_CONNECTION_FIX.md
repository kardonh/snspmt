# 최종 연결 문제 해결 방법

## 현재 상황

비밀번호를 `VEOdjCwztZm4oynz`로 업데이트했지만 여전히 "Tenant or user not found" 오류가 발생합니다.

## 해결 방법: Supabase 대시보드에서 정확한 연결 문자열 복사

### 1. Supabase 대시보드에서 연결 문자열 확인

1. [Supabase 대시보드](https://supabase.com/dashboard) 접속
2. 프로젝트 `sociality` 선택
3. **Settings** → **Database** 메뉴로 이동
4. **Connection string** 섹션에서 **Connection Pooler** 탭 선택
5. **Transaction mode** 또는 **Session mode** 연결 문자열 복사

### 2. 연결 문자열 형식 예시

대시보드에서 복사한 연결 문자열은 다음과 같은 형식일 것입니다:

```
postgresql://postgres.gvtrizwkstaznrlloixi:[YOUR-PASSWORD]@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres
```

또는

```
postgres://postgres.gvtrizwkstaznrlloixi:[YOUR-PASSWORD]@aws-0-ap-southeast-2.pooler.supabase.com:5432/postgres
```

### 3. 연결 문자열에서 정보 추출

연결 문자열에서 다음 정보를 추출:
- **사용자명**: `postgres.gvtrizwkstaznrlloixi` (또는 다른 형식일 수 있음)
- **비밀번호**: `VEOdjCwztZm4oynz` (또는 대시보드에 표시된 정확한 비밀번호)
- **호스트**: `aws-0-ap-southeast-2.pooler.supabase.com`
- **포트**: `6543` (Transaction mode) 또는 `5432` (Session mode)

### 4. backend.py 업데이트

대시보드에서 확인한 정확한 사용자명 형식을 `backend.py`에 반영하세요.

## 중요 확인사항

1. **사용자명 형식**: 대시보드에서 복사한 연결 문자열의 사용자명이 정확한지 확인
2. **비밀번호**: 대시보드에 표시된 비밀번호가 `VEOdjCwztZm4oynz`와 정확히 일치하는지 확인
3. **포트 번호**: Transaction mode는 `6543`, Session mode는 `5432`

## 대안: 환경 변수 사용

하드코딩 대신 환경 변수를 사용하는 것도 고려해볼 수 있습니다:

```python
# .env 파일
DATABASE_URL=postgresql://postgres.gvtrizwkstaznrlloixi:VEOdjCwztZm4oynz@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres
```

그리고 `backend.py`에서 환경 변수를 읽어 사용합니다.

