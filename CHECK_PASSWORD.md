# 비밀번호 확인 가이드

## 현재 상황

비밀번호를 `VEOdjCwztZm4oynz`로 설정했지만 여전히 "Tenant or user not found" 오류가 발생합니다.

## 확인 방법

### 1. Supabase 대시보드에서 비밀번호 확인

1. [Supabase 대시보드](https://supabase.com/dashboard) 접속
2. 프로젝트 `sociality` 선택
3. **Settings** → **Database** 메뉴로 이동
4. **Database password** 섹션 확인

### 2. 비밀번호 재설정 (권장)

비밀번호를 모르거나 확인할 수 없는 경우:

1. **Settings** → **Database** 메뉴
2. **Database password** 섹션에서 **Reset database password** 클릭
3. 새 비밀번호 생성 (안전하게 저장)
4. 새 비밀번호를 `backend.py`에 반영

### 3. Connection Pooler 연결 문자열 확인

Direct Connection은 IPv6만 지원하므로 Windows에서 실패합니다.
Connection Pooler를 사용해야 합니다:

1. **Connect to your project** 모달 열기
2. **Connection String** 탭 선택
3. **Method** 드롭다운에서 **Connection Pooler** 선택
4. 표시되는 연결 문자열 확인:
   - Transaction mode (포트 6543)
   - Session mode (포트 5432)

### 4. 연결 문자열 형식

Connection Pooler 연결 문자열은 다음과 같은 형식입니다:

```
postgresql://postgres.gvtrizwkstaznrlloixi:[PASSWORD]@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres
```

또는

```
postgres://postgres.gvtrizwkstaznrlloixi:[PASSWORD]@aws-0-ap-southeast-2.pooler.supabase.com:5432/postgres
```

## 중요

- 비밀번호는 대소문자를 구분합니다
- 비밀번호에 특수문자가 포함되어 있을 수 있습니다
- Connection Pooler 사용자명은 `postgres.gvtrizwkstaznrlloixi` 형식입니다

