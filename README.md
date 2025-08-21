# SNSINTO - SNS SMM 서비스 플랫폼

이미지와 동일한 디자인의 SNS SMM(Social Media Marketing) 서비스 웹 애플리케이션입니다.

## 🚀 주요 기능

- **다양한 SNS 플랫폼 지원**: 인스타그램, 유튜브, 틱톡, 페이스북, 트위터, 카카오
- **서비스 유형**: 팔로워, 좋아요, 조회수, 구독자 등
- **할인 시스템**: 수량에 따른 자동 할인 적용
- **SMM KINGS API 연동**: PHP 백엔드와의 완벽한 연동
- **반응형 디자인**: 모바일과 데스크톱 모두 지원

## 🛠️ 기술 스택

- **Frontend**: React 18, Vite
- **Styling**: CSS3, Flexbox, Grid
- **Icons**: Lucide React
- **HTTP Client**: Axios
- **Routing**: React Router DOM

## 📦 설치 및 실행

### 1. 의존성 설치

```bash
npm install
```

### 2. 환경 변수 설정

`.env` 파일을 생성하고 SMM KINGS API 설정을 추가하세요:

```env
# SMM KINGS API 설정
SMMKINGS_API_KEY=your_actual_api_key_here
VITE_SMMKINGS_API_URL=https://smmkings.com/api/v2
```

**참고**: 
- Vite에서는 환경 변수 이름에 `VITE_` 접두사를 사용해야 합니다.
- 실제 SMM KINGS API 키를 발급받아 설정하세요.

### 3. 개발 서버 실행

```bash
npm run dev
```

브라우저에서 `http://localhost:3000`으로 접속하세요.

### 4. 프로덕션 빌드

```bash
npm run build
```

## 🔌 SMM KINGS API 연동

이 애플리케이션은 SMM KINGS의 PHP API v2와 완벽하게 연동됩니다:

### API 설정

1. **API 키 설정**: `api/config.py` 파일에서 SMM KINGS API 키를 설정하세요.
2. **API URL**: `https://smmkings.com/api/v2` (기본값)
3. **환경 변수**: `SMMKINGS_API_KEY` 환경 변수를 설정하세요.

### 주요 API 액션

- **서비스 조회**: `action: 'services'`
- **잔액 조회**: `action: 'balance'`
- **주문 생성**: `action: 'add'`
- **주문 상태**: `action: 'status'`
- **주문 리필**: `action: 'refill'`
- **주문 취소**: `action: 'cancel'`
- **리필 상태**: `action: 'refill_status'`

### API 연동 예시

```javascript
import { smmkingsApi } from './services/snspopApi'

// 서비스 목록 조회
const services = await smmkingsApi.getServices()

// 주문 생성
const order = await smmkingsApi.createOrder({
  service: 1,
  link: 'https://instagram.com/username',
  quantity: 1000
})

// 주문 상태 조회
const status = await smmkingsApi.getOrderStatus(orderId)
```

### 추가 기능

SMM KINGS API는 다음과 같은 추가 기능을 지원합니다:

- **Drip-feed 주문**: `runs`, `interval` 파라미터 사용
- **웹 트래픽**: `country`, `device`, `type_of_traffic`, `google_keyword` 파라미터
- **구독 서비스**: `username`, `min`, `max`, `posts`, `delay`, `expiry` 파라미터
- **폴 서비스**: `answer_number` 파라미터

## 📱 페이지 구조

- **홈페이지** (`/`): 플랫폼 선택 및 서비스 소개
- **주문페이지** (`/order/:platform`): 서비스 주문 및 설정

## 🎨 디자인 특징

- **미니멀한 디자인**: 깔끔하고 현대적인 UI
- **사용자 친화적**: 직관적인 네비게이션과 폼
- **반응형**: 모든 디바이스에서 최적화된 경험
- **접근성**: 키보드 네비게이션 및 스크린 리더 지원

## 🔧 커스터마이징

### 플랫폼 정보 수정

`src/utils/platformUtils.js`에서 플랫폼별 설정을 수정할 수 있습니다:

```javascript
export const getPlatformInfo = (platform) => {
  const platforms = {
    instagram: {
      name: '인스타그램',
      unitPrice: 25,
      services: ['followers_korean', 'followers_foreign', 'likes_korean', 'likes_foreign', 'comments_korean', 'comments_foreign', 'views']
    },
    // ... 다른 플랫폼들
  }
}
```

### 스타일 수정

각 컴포넌트의 CSS 파일을 수정하여 디자인을 커스터마이징할 수 있습니다.

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📞 지원

문의사항이 있으시면 이슈를 생성해주세요.

---

**SNSINTO** - 소셜미디어 마케팅의 새로운 시작
