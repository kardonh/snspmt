# 스케줄러 확인 방법

## 1. 데이터베이스에서 직접 확인

### execution_progress 테이블 확인
```sql
SELECT 
    exec_id,
    order_id,
    exec_type,
    step_number,
    step_name,
    service_id,
    quantity,
    scheduled_datetime,
    status,
    smm_panel_order_id,
    created_at,
    completed_at
FROM execution_progress
WHERE exec_type = 'package'
ORDER BY order_id, step_number;
```

### 특정 주문의 스케줄러 상태 확인
```sql
SELECT * FROM execution_progress 
WHERE order_id = '주문ID'
ORDER BY step_number;
```

## 2. Python 스크립트 사용

```bash
# 모든 패키지 주문 스케줄러 상태 확인
python check_scheduler.py

# 특정 주문 ID 확인
python check_scheduler.py 1764098196935
```

## 3. 백엔드 API 사용

### 크론잡 엔드포인트
- `POST /api/cron/process-package-steps`
- 실행 예약된 패키지 단계를 처리합니다

### 관리자 페이지
- Admin Dashboard → 주문 관리
- 패키지 주문의 진행 상황 확인 가능

## 4. 백그라운드 스케줄러

- **주기**: 5분마다 실행
- **처리 항목**:
  1. 예약 주문 처리
  2. 패키지 단계 처리 (`execution_progress` 확인)
  3. 분할 발송 처리 (자정에만)

## 스케줄러 확인 포인트

1. **execution_progress 테이블**: 패키지 단계별 실행 정보
2. **scheduled_datetime**: 각 단계의 실행 예약 시간
3. **status**: `pending`, `running`, `completed`, `failed`
4. **smm_panel_order_id**: SMM Panel 주문 ID

