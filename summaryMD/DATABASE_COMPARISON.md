# SQLite vs PostgreSQL 차이점

## 📊 기본 개념

### SQLite
- **타입**: 파일 기반 데이터베이스 (File-based Database)
- **구조**: 단일 파일에 모든 데이터 저장
- **설치**: 별도 서버 설치 불필요
- **용도**: 로컬 개발, 소규모 프로젝트, 임베디드 시스템

### PostgreSQL
- **타입**: 서버 기반 관계형 데이터베이스 (Server-based RDBMS)
- **구조**: 클라이언트-서버 아키텍처
- **설치**: 별도 데이터베이스 서버 필요
- **용도**: 프로덕션 환경, 대규모 애플리케이션, 멀티 사용자 환경

---

## 🔍 주요 차이점

### 1. **아키텍처**

#### SQLite
```
애플리케이션 → SQLite 라이브러리 → 데이터베이스 파일 (.db)
```
- 애플리케이션과 같은 프로세스에서 실행
- 네트워크 없이 직접 파일 접근
- 단일 프로세스만 동시 접근 가능

#### PostgreSQL
```
애플리케이션 → 네트워크 → PostgreSQL 서버 → 디스크
```
- 별도 서버 프로세스로 실행
- 네트워크를 통한 접근
- 여러 클라이언트가 동시 접근 가능

### 2. **동시성 (Concurrency)**

| 항목 | SQLite | PostgreSQL |
|------|--------|------------|
| 동시 읽기 | ✅ 지원 (제한적) | ✅ 완벽 지원 |
| 동시 쓰기 | ❌ 제한적 (하나씩만) | ✅ 완벽 지원 |
| 트랜잭션 | ✅ 지원 | ✅ 완벽 지원 |
| 락 (Lock) | 파일 락 사용 | 행/테이블 레벨 락 |

**SQLite**: 여러 읽기는 가능하지만, 쓰기는 동시에 하나만 가능
**PostgreSQL**: 여러 사용자가 동시에 읽기/쓰기 가능

### 3. **성능 (Performance)**

#### SQLite
- ✅ 단일 사용자 환경에서 매우 빠름
- ✅ 네트워크 오버헤드 없음
- ❌ 동시 쓰기 시 성능 저하
- ❌ 대용량 데이터에서 제한적

#### PostgreSQL
- ✅ 멀티 사용자 환경에서 최적화
- ✅ 인덱싱 및 쿼리 최적화 우수
- ✅ 대용량 데이터 처리 가능
- ⚠️ 네트워크 오버헤드 (최소화됨)

### 4. **데이터 타입**

#### SQLite
- 동적 타입 시스템 (Dynamic Typing)
- 모든 컬럼이 TEXT, INTEGER, REAL, BLOB, NULL 중 하나
- 타입 변환 자동 처리
- 예: `VARCHAR(255)`를 선언해도 실제로는 TEXT로 저장

#### PostgreSQL
- 강한 타입 시스템 (Strong Typing)
- 다양한 데이터 타입 지원:
  - `VARCHAR(n)`, `TEXT`, `CHAR(n)`
  - `INTEGER`, `BIGINT`, `SMALLINT`, `SERIAL`
  - `DECIMAL`, `NUMERIC`, `REAL`, `DOUBLE PRECISION`
  - `BOOLEAN`, `DATE`, `TIMESTAMP`, `JSON`, `JSONB`, `UUID`
- 타입 검증 엄격

### 5. **SQL 문법 차이**

#### SQLite
```sql
-- 자동 증가 ID
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT
);

-- 날짜/시간
INSERT INTO users (created_at) VALUES (datetime('now'));

-- 문자열 연결
SELECT first_name || ' ' || last_name AS full_name FROM users;
```

#### PostgreSQL
```sql
-- 자동 증가 ID
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    -- 또는
    id INTEGER GENERATED ALWAYS AS IDENTITY,
    name VARCHAR(255)
);

-- 날짜/시간
INSERT INTO users (created_at) VALUES (NOW());
-- 또는
INSERT INTO users (created_at) VALUES (CURRENT_TIMESTAMP);

-- 문자열 연결
SELECT first_name || ' ' || last_name AS full_name FROM users;
-- 또는
SELECT CONCAT(first_name, ' ', last_name) AS full_name FROM users;
```

### 6. **제약 조건 (Constraints)**

#### SQLite
```sql
-- CHECK 제약조건은 지원하지만 제한적
CREATE TABLE users (
    age INTEGER CHECK (age >= 0)
);

-- ENUM 직접 지원 안 함 (TEXT + CHECK 사용)
CREATE TABLE users (
    status TEXT CHECK (status IN ('active', 'inactive'))
);
```

#### PostgreSQL
```sql
-- CHECK 제약조건 완벽 지원
CREATE TABLE users (
    age INTEGER CHECK (age >= 0)
);

-- ENUM 타입 직접 지원
CREATE TYPE user_status AS ENUM ('active', 'inactive');
CREATE TABLE users (
    status user_status
);

-- 외래 키 제약조건 강력
CREATE TABLE orders (
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE
);
```

### 7. **함수 차이**

| 기능 | SQLite | PostgreSQL |
|------|--------|------------|
| 날짜 함수 | `datetime()`, `date()`, `strftime()` | `NOW()`, `CURRENT_TIMESTAMP`, `date_trunc()` |
| 문자열 함수 | `substr()`, `length()` | `SUBSTRING()`, `LENGTH()`, `CONCAT()` |
| 집계 함수 | 기본 제공 | 확장 가능 (사용자 정의) |
| 윈도우 함수 | 제한적 지원 | 완벽 지원 |

### 8. **스키마 관리**

#### SQLite
- 스키마 변경이 제한적
- `ALTER TABLE` 제한적 지원
- 컬럼 추가는 가능하지만 삭제는 불가능 (최신 버전에서는 가능)

#### PostgreSQL
- 스키마 변경 유연함
- `ALTER TABLE` 완벽 지원
- 마이그레이션 도구와 잘 통합 (Alembic, Flyway 등)

---

## 💻 현재 프로젝트에서의 사용

### 현재 코드 구조

```python
# DATABASE_URL 환경 변수로 데이터베이스 타입 결정
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL.startswith('postgresql://'):
    # PostgreSQL 사용
    conn = psycopg2.connect(...)
    cursor.execute("SELECT ... WHERE id = %s", (value,))  # %s 사용
else:
    # SQLite 사용 (로컬 개발)
    conn = sqlite3.connect('snspmt.db')
    cursor.execute("SELECT ... WHERE id = ?", (value,))   # ? 사용
```

### 환경별 사용

| 환경 | 데이터베이스 | DATABASE_URL |
|------|-------------|--------------|
| **로컬 개발** | SQLite | 없음 또는 파일 경로 |
| **프로덕션 (Render)** | PostgreSQL | `postgresql://user:pass@host:port/db` |

---

## 🎯 각각의 장단점

### SQLite

#### ✅ 장점
1. **설치 불필요**: 라이브러리만 포함하면 됨
2. **설정 간단**: 파일만 있으면 동작
3. **로컬 개발에 적합**: 빠른 프로토타이핑
4. **백업 쉬움**: 파일 복사만 하면 됨
5. **가볍음**: 메모리 사용량 적음

#### ❌ 단점
1. **동시 쓰기 제한**: 멀티 사용자 환경에 부적합
2. **네트워크 접근 불가**: 원격 접근 불가능
3. **확장성 제한**: 대규모 트래픽 처리 어려움
4. **고급 기능 부족**: 복잡한 쿼리, 뷰, 프로시저 제한

### PostgreSQL

#### ✅ 장점
1. **동시성 우수**: 멀티 사용자 환경 완벽 지원
2. **확장성**: 대규모 트래픽 처리 가능
3. **고급 기능**: 복잡한 쿼리, 인덱싱, 뷰, 프로시저 등
4. **데이터 무결성**: 강력한 제약 조건과 트랜잭션
5. **네트워크 접근**: 원격 접근 가능
6. **프로덕션 준비**: 엔터프라이즈급 기능

#### ❌ 단점
1. **설치 필요**: 별도 서버 설치 및 설정 필요
2. **리소스 사용**: 메모리와 CPU 사용량 높음
3. **복잡한 설정**: 초기 설정이 복잡할 수 있음
4. **네트워크 의존**: 네트워크 연결 필요

---

## 🔧 현재 프로젝트에서의 차이점 처리

### 1. **파라미터 바인딩**
```python
# PostgreSQL
cursor.execute("SELECT * FROM users WHERE email = %s", (email,))

# SQLite
cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
```

### 2. **날짜/시간 함수**
```python
# PostgreSQL
cursor.execute("SELECT NOW()")
cursor.execute("UPDATE orders SET updated_at = NOW()")

# SQLite
cursor.execute("SELECT datetime('now')")
cursor.execute("UPDATE orders SET updated_at = datetime('now')")
```

### 3. **자동 증가 ID**
```python
# PostgreSQL
cursor.execute("INSERT INTO users ... RETURNING user_id")
user_id = cursor.fetchone()[0]

# SQLite
cursor.execute("INSERT INTO users ...")
user_id = cursor.lastrowid
```

### 4. **타입 변환**
```python
# PostgreSQL: 타입 검증 엄격
cursor.execute("""
    CREATE TABLE orders (
        order_id VARCHAR(255) PRIMARY KEY,
        price DECIMAL(10, 2)
    )
""")

# SQLite: 타입이 자동 변환됨
cursor.execute("""
    CREATE TABLE orders (
        order_id TEXT PRIMARY KEY,
        price REAL
    )
""")
```

---

## 📝 언제 무엇을 사용할까?

### SQLite를 사용하는 경우
- ✅ 로컬 개발 및 테스트
- ✅ 소규모 애플리케이션
- ✅ 단일 사용자 애플리케이션
- ✅ 임베디드 시스템
- ✅ 프로토타입 개발
- ✅ 읽기 중심 애플리케이션

### PostgreSQL을 사용하는 경우
- ✅ 프로덕션 환경
- ✅ 멀티 사용자 웹 애플리케이션
- ✅ 대규모 데이터 처리
- ✅ 복잡한 쿼리와 트랜잭션
- ✅ 높은 동시성 요구사항
- ✅ 원격 접근 필요
- ✅ 데이터 무결성 중요

---

## 🚀 현재 프로젝트 권장사항

### 개발 환경
- **로컬**: SQLite 사용 (빠른 개발)
- **테스트**: SQLite 또는 PostgreSQL 둘 다 테스트

### 프로덕션 환경
- **Render 배포**: PostgreSQL 사용 (Supabase PostgreSQL)
- **확장성**: PostgreSQL이 필수

### 마이그레이션
- 로컬에서 개발 후 프로덕션 배포 시 PostgreSQL로 전환
- 스키마는 두 데이터베이스 모두 호환되도록 작성

---

## 📚 참고 자료

- [SQLite 공식 문서](https://www.sqlite.org/docs.html)
- [PostgreSQL 공식 문서](https://www.postgresql.org/docs/)
- [SQLite vs PostgreSQL 비교](https://www.postgresql.org/about/)

