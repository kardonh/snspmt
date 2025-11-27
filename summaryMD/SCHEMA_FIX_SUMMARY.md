# 스키마 수정 완료 요약

## ✅ 완료된 수정 사항

### 1. `create_order` 함수 (POST /api/orders)
- ✅ `orders` 테이블 INSERT를 실제 스키마에 맞게 수정
  - `total_amount`, `final_amount`, `discount_amount` 사용
  - 존재하지 않는 컬럼 (`service_id`, `link`, `quantity`, `price`) 제거
- ✅ `order_items` 테이블에 상세 정보 저장 추가
  - `variant_id`, `link`, `quantity`, `unit_price`, `line_amount` 저장
  - `service_id`를 `variant_id`로 변환하는 로직 추가

### 2. `get_orders` 함수 (GET /api/orders)
- ✅ 실제 스키마에 맞게 쿼리 수정
  - `COALESCE(o.final_amount, o.total_amount, 0)` 사용
  - `order_items`와 조인하여 상세 정보 조회
  - `detailed_service` 필드 추가

### 3. 쿠폰 사용 로직 (`create_order` 내부)
- ✅ `user_coupons` 테이블 사용
  - `coupons`와 `user_coupons` 조인하여 조회
  - 쿠폰 사용 시 `user_coupons.status`를 'used'로 변경

### 4. `sync_user` 함수 (POST /api/users/sync)
- ✅ 쿠폰 발급 로직을 `user_coupons` 테이블 사용하도록 수정
  - `coupons` 테이블에 쿠폰 생성 (없으면)
  - `user_coupons` 테이블에 사용자에게 쿠폰 발급
  - 중복 발급 방지 로직 추가

---

### 5. `create_scheduled_order` 함수 (POST /api/scheduled-orders)
- ✅ `orders` 테이블 INSERT를 실제 스키마에 맞게 수정
  - `total_amount`, `final_amount` 사용
  - 존재하지 않는 컬럼 제거
- ✅ `order_items` 테이블에 상세 정보 저장 추가
  - `variant_id`, `link`, `quantity`, `unit_price` 저장
  - `service_id`를 `variant_id`로 변환하는 로직 추가

### 6. `create_actual_order_from_scheduled` 함수
- ✅ `orders` 테이블 INSERT를 실제 스키마에 맞게 수정
  - `total_amount`, `final_amount` 사용
  - 존재하지 않는 컬럼 (`platform`, `service_name`, `service_id`, `link`, `quantity`, `price`) 제거
- ✅ `order_items` 테이블에 상세 정보 저장 추가
  - `variant_id`, `link`, `quantity`, `unit_price` 저장

---

## ✅ 모든 주요 스키마 수정 완료!

---

## 📋 다음 단계 권장 사항

1. **나머지 orders INSERT/UPDATE 쿼리 수정**
   - `/api/scheduled-orders` 엔드포인트
   - `create_actual_order_from_scheduled` 함수

2. **실제 DB에서 테스트**
   - 주문 생성 테스트
   - 쿠폰 발급/사용 테스트
   - 주문 조회 테스트

3. **에러 처리 강화**
   - 스키마 불일치 시 명확한 에러 메시지
   - 롤백 로직 확인

---

## 🎯 우선순위

1. **높음**: `/api/scheduled-orders` 엔드포인트 수정 (예약 주문 생성 기능)
2. **높음**: `create_actual_order_from_scheduled` 함수 수정 (예약 주문 실행 기능)
3. **중간**: 나머지 UPDATE 쿼리 확인 및 수정
4. **낮음**: 에러 메시지 개선

