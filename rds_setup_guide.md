# PostgreSQL 데이터베이스 설정 가이드

## 현재 상황
- RDS 인스턴스 `snspmt-db`는 존재하지만 데이터베이스가 없음
- 외부 접근이 제한되어 있어 CLI로 데이터베이스 생성 불가
- 현재 SQLite 메모리 기반으로 임시 운영 중

## 해결 방법

### 방법 1: AWS 콘솔에서 데이터베이스 생성 (권장)

1. **AWS RDS 콘솔** 접속: https://console.aws.amazon.com/rds/
2. **`snspmt-db` 인스턴스** 선택
3. **"데이터베이스"** 탭 클릭
4. **"데이터베이스 생성"** 버튼 클릭
5. **데이터베이스 이름**: `snspmt` 입력
6. **생성** 클릭

### 방법 2: 기존 RDS 인스턴스 삭제 후 새로 생성

1. **기존 RDS 인스턴스 삭제**
2. **새 RDS 인스턴스 생성**:
   - **DB 인스턴스 식별자**: `snspmt-db`
   - **데이터베이스 이름**: `snspmt`
   - **마스터 사용자 이름**: `snspmt_admin`
   - **마스터 암호**: `Snspmt2024!`
   - **DB 인스턴스 클래스**: `db.t3.micro`
   - **할당된 스토리지**: `20 GB`
   - **퍼블릭 액세스**: `예`

### 방법 3: 현재 상태로 계속 사용

- **장점**: 즉시 사용 가능, 추가 설정 불필요
- **단점**: 서버 재시작 시 데이터 손실
- **적용**: 개발/테스트 환경에 적합

## 데이터베이스 생성 후 할 일

1. **backend.py 수정**:
   ```python
   def get_db_connection():
       """PostgreSQL 데이터베이스 연결"""
       try:
           conn = psycopg2.connect(
               DATABASE_URL,
               cursor_factory=RealDictCursor,
               connect_timeout=30,
               application_name='snspmt-app'
           )
           conn.autocommit = False
           print("PostgreSQL 연결 성공")
           return conn
       except Exception as e:
           print(f"PostgreSQL 연결 실패: {e}")
           # SQLite 폴백
           conn = sqlite3.connect(':memory:')
           conn.row_factory = sqlite3.Row
           print("SQLite 메모리 기반 연결 성공")
           return conn
   ```

2. **배포**:
   ```bash
   git add backend.py
   git commit -m "Enable PostgreSQL connection after database creation"
   git push origin main
   ```

## 예상 결과

데이터베이스 생성 후:
- **데이터 지속성**: 서버 재시작 시에도 데이터 유지
- **성능 향상**: PostgreSQL의 고급 기능 활용
- **확장성**: 대용량 데이터 처리 가능
- **안정성**: 트랜잭션 지원 및 데이터 무결성 보장
