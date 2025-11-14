# Supabase 이전 및 테스트 계획

이 문서는 Render PostgreSQL에서 Supabase PostgreSQL로 이전하기 위한 준비·이전·검증 절차를 정리합니다.

---

## 1. 사전 준비
1. **Supabase 프로젝트 생성**
   - Supabase 콘솔에서 새 프로젝트를 생성하고, `Project URL`, `anon`/`service_role` 키를 확보합니다.
2. **환경 변수 설계**
   - `SUPABASE_DB_URL` (PostgreSQL 연결 URL)
   - `SUPABASE_PROJECT_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
   - `.env`, Render/AWS Secrets, CI/CD 파이프라인에 반영 계획 수립
3. **네트워크/보안 확인**
   - Supabase DB 접근을 허용할 IP/보안 그룹 구성
   - 현재 애플리케이션 인프라에서 외부 DB 접근이 가능한지 확인
4. **권한/용량 점검**
   - 필요한 확장(pgcrypto 등)이 사용 가능한지 확인
   - 예상 데이터량/트래픽에 따라 플랜 및 기본 리소스 확인

---

## 2. 스키마 동기화
1. `migrate_database.py` 또는 `DATABASE_SCHEMA_FINAL_POSTGRESQL.sql`을 활용하여 Supabase DB에 스키마 적용
2. ENUM/DOMAIN 등 Supabase에서 추가 설정이 필요한 부분이 있는지 점검
3. `work_jobs`, `orders.notes` JSON 등 새 구조가 Supabase에 맞춰 정상 생성되는지 확인

---

## 3. 데이터 마이그레이션 전략
1. **전체 백업 & 복원**
   - Render PostgreSQL에서 `pg_dump` → Supabase로 `pg_restore`
   - 다운타임이 짧으면 전체 복사, 길면 테이블 단위 복사 후 `work_jobs` 등 큐 테이블은 비우고 시작
2. **증분 동기화(선택)**
   - cut-over 전에 변동 테이블(`orders`, `wallet_transactions`)만 추가 동기화
   - `last_updated_at` 기반으로 delta 적용
3. **비공개 테스트 환경에 복원**
   - 실제 서비스 전, 복사본으로 API 기능·데이터 무결성 점검

---

## 4. 애플리케이션 전환 절차
1. **환경 변수 스위치**
   - 애플리케이션에서 Supabase DB URL/키를 사용하도록 준비
2. **마이그레이션 스크립트 실행**
   - 새 DB를 최신 스키마로 맞추고, 필수 초기 데이터 삽입
3. **읽기 전용 점검**
   - 애플리케이션을 Supabase에 연결한 테스트 환경에서 API 호출 확인
4. **쓰기 테스트**
   - `orders`, `wallet_transactions`, `work_jobs`, `smm_sync` 흐름이 정상인지 실제 API 호출로 확인
5. **롤백 플랜**
   - 문제 발생 시 Render DB로 다시 되돌리는 절차 확보

---

## 5. 검증 체크리스트
1. **핵심 API**
   - 사용자 등록/로그인, 포인트 충전, 주문 생성, 패키지/분할 작업 예약
2. **관리자 기능**
   - 추천/커미션, 작업 큐 조회/재시작, SMM 상태 동기화
3. **비동기 작업**
   - `work_jobs` 실행, `sync_smm_panel_orders` 수동 실행 확인
4. **SMM 연동**
   - 실 주문 테스트 또는 모의 호출로 상태 갱신 흐름 확인
5. **모니터링**
   - Supabase 모니터링(쿼리 통계, 에러 로그), 애플리케이션 로그에 대한 대시보드 준비

---

## 6. 배포 및 모니터링
1. **점진적 배포**
   - 일부 인스턴스만 Supabase 연결로 전환 → 이상 없으면 전체 전환
2. **모니터링 지표**
   - DB 에러율, 응답 속도, 작업 큐 fail 건수 관찰
3. **사후 조치**
   - 문제 발생 시 롤백 절차에 따라 즉시 복귀
   - Supabase에서 제공하는 백업/Point-in-Time Recovery(PITR) 기능 설정

---

## 7. 문서화 및 운영
1. GitHub/Notion 등 운영 문서에 Supabase 접속 정보·절차 업데이트
2. 운영/개발팀 대상 교육: Supabase 콘솔 사용법, 권한 관리, 백업/복구 매뉴얼 공유
3. 정기 점검(예: 월간)으로 저장 공간, 쿼리 비용, 확장 필요성을 검토

---

### 추가 고려 사항
- Supabase Functions/Edge를 활용한 향후 확장 여지 검토
- 기존 Render DB와의 데이터 이중화가 필요한 경우 CDC(Change Data Capture) 도입 검토
- 생산성 향상을 위해 Supabase CLI를 활용한 자동 스키마 동기화 및 배포 파이프라인 구성


