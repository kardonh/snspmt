# 관리자 카테고리 / 상품 / 패키지 API 사양

프런트엔드(관리자 UI)와 연동 시 참고할 수 있도록, 방금 추가한 관리자용 CRUD 엔드포인트와 예시 요청/응답을 정리했습니다. 모든 엔드포인트는 `X-Admin-Token` 헤더를 요구합니다.

---

## 공통 헤더
```
X-Admin-Token: <ADMIN_TOKEN 값>
Content-Type: application/json
```

---

## 1. 카테고리

### 목록 조회
```
GET /api/admin/categories?include_inactive=true
```
- `include_inactive` 없으면 활성 카테고리만 반환

Response:
```json
{
  "categories": [
    {
      "category_id": 1,
      "name": "Instagram",
      "slug": "instagram",
      "is_active": true,
      "image_url": null,
      "created_at": "2025-01-01T12:00:00",
      "updated_at": "2025-01-01T12:00:00"
    }
  ],
  "count": 1
}
```

### 생성
```
POST /api/admin/categories
{
  "name": "TikTok",
  "slug": "tiktok",
  "image_url": "https://example.com/tiktok.png",
  "is_active": true
}
```

### 상세 조회 / 수정 / 비활성화
```
GET    /api/admin/categories/{category_id}
PUT    /api/admin/categories/{category_id}
DELETE /api/admin/categories/{category_id}   // is_active=false 처리
```

---

## 2. 상품 (products)

### 목록 조회
```
GET /api/admin/products
GET /api/admin/products?category_id=1
```
- 응답에 `category_name` 포함

### 생성
```
POST /api/admin/products
{
  "category_id": 1,
  "name": "Instagram Likes",
  "description": "Increases likes",
  "is_domestic": true,
  "auto_tag": false
}
```

### 상세 조회 / 수정 / 삭제
```
GET    /api/admin/products/{product_id}
PUT    /api/admin/products/{product_id}
DELETE /api/admin/products/{product_id}   // 옵션 있는 경우 오류
```

---

## 3. 상품 옵션 (product_variants)

### 목록 조회
``+
GET /api/admin/product-variants
GET /api/admin/product-variants?product_id=1
``+
- `meta_json`은 JSON 문자열 또는 객체로 반환

### 생성
```
POST /api/admin/product-variants
{
  "product_id": 1,
  "name": "Base Package",
  "price": 10.50,
  "min_quantity": 100,
  "max_quantity": 10000,
  "delivery_time_days": 2,
  "is_active": true,
  "meta_json": {
    "smm_service_id": 12345,
    "panel": "providerA"
  },
  "api_endpoint": "https://provider/api"
}
```
- `price`는 소수 둘째 자리까지 허용
- `meta_json`은 객체/배열 전달 가능

### 상세 조회 / 수정 / 삭제
```
GET    /api/admin/product-variants/{variant_id}
PUT    /api/admin/product-variants/{variant_id}
DELETE /api/admin/product-variants/{variant_id}
```

---

## 4. 패키지 (packages)

### 목록 조회
```
GET /api/admin/packages
```
- 패키지별 `items` 배열 포함
- `term_unit`, `repeat_term_unit`은 ENUM (`package_term_unit`, `package_repeat_unit`)

### 생성
```
POST /api/admin/packages
{
  "category_id": 1,
  "name": "Starter Pack",
  "description": "30-day growth",
  "items": [
    {
      "variant_id": 10,
      "step": 1,
      "term_value": 1,
      "term_unit": "day",
      "quantity": 100,
      "repeat_count": 30
    },
    {
      "variant_id": 11,
      "step": 2,
      "term_value": 1,
      "term_unit": "day",
      "quantity": 200
    }
  ]
}
```

### 상세 조회 / 수정 / 삭제
```
GET    /api/admin/packages/{package_id}
PUT    /api/admin/packages/{package_id}    // items 배열 전달 시 전체 교체
DELETE /api/admin/packages/{package_id}
```

---

## 5. 응답 필드 요약

| 필드 | 설명 |
| ---- | ---- |
| `category_id` | 카테고리 PK |
| `product_id` | 상품 PK |
| `variant_id` | 상품 옵션 PK |
| `package_id` | 패키지 PK |
| `step` | 패키지 단계 순서 |
| `term_unit` | `package_term_unit` ENUM (`day`, `week`, `month` 등) |
| `repeat_term_unit` | `package_repeat_unit` ENUM |
| `meta_json` | 옵션별 추가 설정 (JSON) |

---

## 테스트 예시 (cURL)

```bash
# 카테고리 생성
curl -X POST https://api.example.com/api/admin/categories \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"name":"YouTube","slug":"youtube"}'

# 상품 옵션 목록
curl -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  https://api.example.com/api/admin/product-variants?product_id=1
```

---

## 로깅/디버깅 팁
- 중요 이벤트(`생성/수정/삭제`)는 backend 로그에 `"ADMIN_CATALOG"` 태그로 남기는 것을 권장합니다.
- `payload_json` 기록을 통해 어떤 관리자 작업이 언제 수행되었는지 추적할 수 있습니다.


