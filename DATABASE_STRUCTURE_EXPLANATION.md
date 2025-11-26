# 데이터베이스 구조 설명: 세부서비스와 패키지

## 1. 세부서비스 (product_variants 테이블)

### 저장되는 데이터:
```sql
INSERT INTO product_variants (
    product_id,        -- 상품 ID (필수)
    name,              -- 세부서비스 이름 (예: "KR 인스타그램 리얼 한국인 랜덤 댓글 [30대남자]")
    price,             -- 가격
    min_quantity,      -- 최소 수량
    max_quantity,      -- 최대 수량
    delivery_time_days,-- 배송 시간 (일)
    meta_json,         -- 메타데이터 JSON (SMM 서비스 ID, 설명 등)
    is_active,         -- 활성화 여부
    created_at,
    updated_at
)
```

### 특징:
- **product_id 필수**: 세부서비스는 반드시 특정 상품에 속함
- **category_id는 자동**: product_id를 통해 자동으로 category_id를 알 수 있음
- **세부서비스 = 상품의 옵션**: 하나의 상품에 여러 세부서비스가 있을 수 있음

### 예시:
```
상품: "인스타그램 팔로워"
├─ 세부서비스 1: "KR 인스타그램 리얼 한국인 랜덤 댓글 [30대남자]" (가격: 1,000원)
├─ 세부서비스 2: "KR 인스타그램 리얼 한국인 랜덤 댓글 [20대여성]" (가격: 1,200원)
└─ 세부서비스 3: "KR 인스타그램 리얼 한국인 랜덤 댓글 [40대남자]" (가격: 900원)
```

---

## 2. 패키지 (packages 테이블)

### 저장되는 데이터:
```sql
INSERT INTO packages (
    product_id,        -- 상품 ID (새로 추가됨, 선택사항)
    category_id,       -- 카테고리 ID (필수, product_id에서 자동 추출 또는 직접 입력)
    name,              -- 패키지 이름 (예: "인스타 계정 상위노출 [30일]")
    description,       -- 패키지 설명
    meta_json,         -- 메타데이터 JSON (가격, 최소/최대 수량, 시간 등)
    created_at,
    updated_at
)
```

### 패키지 추가 시 동작:

#### 시나리오 1: product_id가 있는 경우 (권장)
```javascript
// 프론트엔드에서 패키지 추가 시
{
  product_id: 123,        // 상품 선택
  name: "인스타 계정 상위노출 [30일]",
  items: [...]            // 패키지 단계들
}

// 백엔드에서:
1. product_id로 category_id 자동 조회
2. packages 테이블에 저장:
   - product_id: 123
   - category_id: 19 (자동으로 찾아서 저장)
   - name: "인스타 계정 상위노출 [30일]"
```

#### 시나리오 2: product_id가 없는 경우 (하위 호환성)
```javascript
// 프론트엔드에서 패키지 추가 시
{
  category_id: 19,        // 카테고리 직접 선택 (구버전)
  name: "인스타 계정 상위노출 [30일]",
  items: [...]
}

// 백엔드에서:
1. category_id 직접 사용
2. packages 테이블에 저장:
   - product_id: NULL
   - category_id: 19
   - name: "인스타 계정 상위노출 [30일]"
```

### 패키지 아이템 (package_items 테이블):
```sql
INSERT INTO package_items (
    package_id,          -- 패키지 ID
    variant_id,          -- 세부서비스 ID (어떤 세부서비스를 사용할지)
    step,                -- 단계 번호 (1, 2, 3, ...)
    quantity,            -- 수량
    term_value,          -- 지연 시간 값 (예: 1)
    term_unit,           -- 지연 시간 단위 (예: 'hour', 'minute')
    repeat_count,        -- 반복 횟수
    repeat_term_value,   -- 반복 간격 값
    repeat_term_unit     -- 반복 간격 단위
)
```

### 예시:
```
패키지: "인스타 계정 상위노출 [30일]"
├─ 단계 1: 세부서비스 A (variant_id: 100) - 수량: 15, 지연: 0분
├─ 단계 2: 세부서비스 B (variant_id: 101) - 수량: 11, 지연: 1시간
└─ 단계 3: 세부서비스 C (variant_id: 102) - 수량: 20, 지연: 2시간, 반복: 3회
```

---

## 3. 현재 구조 요약

### 세부서비스:
- ✅ **product_id 필수**: 항상 특정 상품에 속함
- ✅ **category_id 자동**: product_id를 통해 자동으로 알 수 있음
- ✅ **상품의 세부서비스로 표시**: 관리자 페이지에서 상품 아래에 표시됨

### 패키지:
- ✅ **product_id 추가됨**: 이제 패키지도 특정 상품에 속할 수 있음
- ✅ **category_id 유지**: 하위 호환성을 위해 유지
- ✅ **상품의 세부서비스로 표시**: product_id가 있으면 상품 아래에 표시됨
- ⚠️ **하위 호환성**: product_id가 없으면 category_id로 찾음

---

## 4. 데이터 흐름

### 세부서비스 추가:
```
관리자 페이지 → 상품 선택 → 세부서비스 추가
  ↓
product_variants 테이블에 저장
  - product_id: 선택한 상품 ID
  - name, price, meta_json 등
```

### 패키지 추가:
```
관리자 페이지 → 상품 선택 → 패키지 추가
  ↓
1. packages 테이블에 저장
   - product_id: 선택한 상품 ID
   - category_id: 상품의 category_id (자동)
   - name, description, meta_json
   
2. package_items 테이블에 저장
   - package_id: 생성된 패키지 ID
   - variant_id: 각 단계의 세부서비스 ID
   - step, quantity, term_value 등
```

---

## 5. 주의사항

1. **패키지 추가 시**: 
   - ✅ **product_id를 선택하면**: category_id는 자동으로 설정됨
   - ⚠️ **product_id를 선택하지 않으면**: category_id를 직접 입력해야 함 (구버전 방식)

2. **세부서비스 표시**:
   - 세부서비스는 항상 특정 상품에 속하므로 `product_id`가 필수
   - 패키지도 `product_id`가 있으면 상품의 세부서비스로 표시됨

3. **데이터 일관성**:
   - 패키지의 `product_id`와 `category_id`는 일치해야 함
   - 백엔드에서 `product_id`로 `category_id`를 자동으로 찾아서 저장함

