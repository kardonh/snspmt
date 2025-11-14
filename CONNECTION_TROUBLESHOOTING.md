# Supabase 연결 문제 해결 가이드

## 현재 오류

1. **Direct Connection**: `could not translate host name "db.gvtrizwkstaznrlloixi.supabase.co" to address`
   - Windows에서 IPv6 DNS 해석 실패
   
2. **Pooler**: `FATAL: Tenant or user not found`
   - 사용자명 형식 또는 비밀번호 오류 가능성

## 해결 방법

### 1. Supabase 대시보드에서 정확한 연결 문자열 확인

1. [Supabase 대시보드](https://supabase.com/dashboard) 접속
2. 프로젝트 `sociality` (gvtrizwkstaznrlloixi) 선택
3. **Settings** → **Database** 메뉴로 이동
4. **Connection string** 섹션에서 다음 확인:
   - **Direct connection** (IPv6)
   - **Connection Pooler** (Session mode - 포트 5432)
   - **Connection Pooler** (Transaction mode - 포트 6543)

### 2. 비밀번호 확인/재설정

1. **Settings** → **Database** 메뉴
2. **Database password** 섹션
3. 현재 비밀번호 확인 또는 **Reset database password** 클릭
4. 새 비밀번호 생성 후 `.env` 파일과 `backend.py`에 반영

### 3. 연결 문자열 형식 확인

#### Direct Connection (IPv6 필요)
```
postgresql://postgres:[PASSWORD]@db.gvtrizwkstaznrlloixi.supabase.co:5432/postgres
```

#### Pooler Session Mode (포트 5432)
```
postgresql://postgres.gvtrizwkstaznrlloixi:[PASSWORD]@aws-0-ap-southeast-2.pooler.supabase.com:5432/postgres
```

#### Pooler Transaction Mode (포트 6543)
```
postgresql://postgres.gvtrizwkstaznrlloixi:[PASSWORD]@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres
```

### 4. Windows IPv6 문제 해결

Windows에서 IPv6가 제대로 작동하지 않는 경우:

1. **방법 1**: Pooler만 사용 (권장)
   - Direct Connection을 시도하지 않고 Pooler만 사용
   
2. **방법 2**: IPv6 활성화
   - Windows 네트워크 설정에서 IPv6 활성화 확인
   - `netsh interface ipv6 show interfaces` 명령으로 확인

3. **방법 3**: IPv4 Add-On 구매 (Supabase Pro 플랜 이상)
   - Supabase 대시보드에서 IPv4 Add-On 활성화
   - Direct Connection이 IPv4로 작동

## 다음 단계

1. Supabase 대시보드에서 정확한 연결 문자열 복사
2. 비밀번호 확인/재설정
3. `backend.py`의 하드코딩된 연결 정보 업데이트
4. 테스트

## 참고

- 프로젝트 참조: `gvtrizwkstaznrlloixi`
- 지역: `ap-southeast-2`
- 현재 하드코딩된 비밀번호: `KARDONH0813!`

