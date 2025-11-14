# 통합 테스트 체크리스트

Supabase 이전 전/후 및 주요 개발 완료 시 반복 점검할 수 있는 수동/자동 테스트 목록입니다.

---

## 1. 기본 환경
- [ ] `.env` 또는 배포 환경에 필수 환경 변수 설정 (`DATABASE_URL`, `SMMPANEL_API_KEY`, `ADMIN_TOKEN`, KCP 관련 등)
- [ ] `migrate_database.py` 실행 또는 마이그레이션 스크립트 적용
- [ ] 앱 부팅 (`backend.py`) 정상 여부, 헬스 체크 `/api/test/db` 확인

---

## 2. 사용자 & 지갑
1. `POST /api/register` 또는 소셜 로그인 시 사용자 생성
2. `GET /api/users/{user_id}` → 사용자 정보 & 지갑 존재 확인
3. `GET /api/wallet/balance?user_id=...` → 잔액 0 확인

---

## 3. 포인트 충전 (KCP)
1. `POST /api/points/purchase-kcp/register`
   - 응답에서 `ordr_idxx` 확인
2. `POST /api/points/purchase-kcp/payment-form`
   - 결제창 파라미터 반환
3. (실/모의 결제 완료 후) `POST /api/points/purchase-kcp/approve`
   - `wallet_transactions` 상태 `approved` 확인
4. 관리자 승인 플로우 (`POST /api/admin/purchases/{id}/approve`)
   - 지갑 잔액 증가 확인

---

## 4. 주문 생성
1. `POST /api/orders`
   - 지갑 잔액 차감, 쿠폰/추천 할인, 커미션 적립 확인
   - `work_jobs`에 주문 관련 작업 등록 여부 확인
2. `GET /api/orders?user_id=...` → 방금 주문 조회
3. 관리자 거래 목록 `GET /api/admin/transactions`

---

## 5. 패키지 / 예약 / 분할
1. 패키지 주문 데이터로 `POST /api/orders`
   - `orders.notes.package_steps` 기록 확인
   - `work_jobs`에 `package_step` 다수 생성 확인
2. 예약 주문 `POST /api/scheduled-orders`
   - 예약 시간·job IDs 기록 확인
3. 필요시 `POST /api/admin/work-jobs/run`으로 작업 실행 → 상태/잔액 변화 확인

---

## 6. SMM 동기화
1. `orders.notes.smm_orders`가 있는 주문 준비
2. `POST /api/admin/orders/sync-smm` 실행
   - SMM 패널 응답에 따라 `orders.status` 업데이트 확인
   - `status_history`에 기록되는지 확인

---

## 7. 추천/커미션
1. 추천 코드 검증/발급 → `POST /api/referral/validate-code`, `POST /api/referral/issue-coupon`
2. 추천인이 있는 상태에서 주문 → `commissions` 적립
3. 관리자 커미션 대시보드 (`/api/admin/referral/*`) → 금액 집계 확인
4. 커미션 지급 `POST /api/admin/referral/pay-commission` → `payout_requests`, `payouts`, `payout_commissions` 업데이트 검증

---

## 8. 작업 큐 API
- [ ] `GET /api/admin/work-jobs` → 상태별 필터링
- [ ] `POST /api/admin/work-jobs/{id}/retry` → `attempts` 초기화 및 `pending`
- [ ] `POST /api/admin/work-jobs/{id}/cancel` → `status = canceled`
- [ ] 실패 시 `MAX_JOB_ATTEMPTS` 초과 처리 확인

---

## 9. 관리자 카테고리/상품/패키지
1. 카테고리 생성/조회/수정/비활성화 (`ADMIN_CATALOG_API.md` 참조)
2. 상품·옵션 CRUD 후 `packages`에 조합 → 목록에 항목이 반영되는지 확인
3. 삭제 시 연관 데이터(옵션·패키지) 처리 규칙 검증

---

## 10. Supabase 전환 시 추가 점검
1. `SUPABASE_MIGRATION_PLAN.md` 순서대로 스키마/데이터 이전
2. 위 체크리스트 항목을 Supabase 연결 환경에서 반복
3. 에러 로그/Slow Query/Audit 로그 등 Supabase 모니터링 대시보드 확인

---

### 자동화 제안
- Postman/Newman 또는 pytest 기반 API 테스트 스크립트 작성
- GitHub Actions/CI에서 `SUPABASE_DB_URL`을 사용해 스키마/기능 smoke 테스트
- `work_jobs` 실행 결과를 Sentry/CloudWatch에 기록해 이상 감지


