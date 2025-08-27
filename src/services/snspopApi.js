import axios from 'axios'

// SMM KINGS API 기본 설정
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || (window.location.hostname === 'localhost' ? 'http://localhost:8000/api' : 'https://snsinto.onrender.com/api')

// 기본 API 키 (SMM KINGS API 키)
const DEFAULT_API_KEY = import.meta.env.VITE_SMMKINGS_API_KEY || 'your_api_key_here'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  }
})

// API 요청 인터셉터
apiClient.interceptors.request.use(
  (config) => {
    // 우리 API 키를 자동으로 사용
    if (config.data && typeof config.data === 'object') {
      config.data.key = DEFAULT_API_KEY
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// API 응답 인터셉터
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// SNS SMM 서비스 API 함수들 (SMM KINGS API v2 구조)
export const smmkingsApi = {
  // 서비스 목록 조회
  getServices: () => apiClient.post('', { action: 'services' }),
  
  // 잔액 조회
  getBalance: () => apiClient.post('', { action: 'balance' }),
  
  // 주문 생성
  createOrder: (orderData, userId) => {
    // 보안상 민감한 정보는 로그에서 제거
    console.log("주문 생성 완료")

    const config = {
      headers: {
        'X-User-ID': userId
      }
    }

    return apiClient.post('', { 
      action: 'add',
      ...orderData 
    }, config)
  },
  
  // 주문 상태 조회
  getOrderStatus: (orderId) => apiClient.post('', { 
    action: 'status',
    order: orderId 
  }),
  
  // 여러 주문 상태 조회
  getMultiOrderStatus: (orderIds) => apiClient.post('', { 
    action: 'status',
    orders: orderIds.join(',') 
  }),
  
  // 주문 리필
  refillOrder: (orderId) => apiClient.post('', { 
    action: 'refill',
    order: orderId 
  }),
  
  // 여러 주문 리필
  refillMultipleOrders: (orderIds) => apiClient.post('', { 
    action: 'refill',
    orders: orderIds.join(',') 
  }),
  
  // 리필 상태 조회
  getRefillStatus: (refillId) => apiClient.post('', { 
    action: 'refill_status',
    refill: refillId 
  }),
  
  // 여러 리필 상태 조회
  getMultiRefillStatus: (refillIds) => apiClient.post('', { 
    action: 'refill_status',
    refills: refillIds.join(',') 
  }),
  
  // 주문 취소
  cancelOrders: (orderIds) => apiClient.post('', { 
    action: 'cancel',
    orders: orderIds.join(',') 
  }),
  
  // 사용자별 주문 목록 조회
  getUserOrders: (userId) => apiClient.get(`/orders?user_id=${userId}`),
  
  // 특정 주문 상세 정보 조회
  getOrderDetail: (orderId, userId) => apiClient.get(`/orders/${orderId}?user_id=${userId}`),
  
  // 포인트 관련 API
  // 사용자 포인트 조회
  getUserPoints: (userId) => apiClient.get(`/points?user_id=${userId}`),
  
  // 사용자 포인트 차감
  deductUserPoints: (userId, points) => apiClient.put('/points', { userId, points }),
  
  // 포인트 구매 신청
  createPurchase: (purchaseData) => apiClient.post('/purchases', purchaseData),
  
  // 구매 내역 조회
  getPurchaseHistory: (userId) => apiClient.get(`/purchases?user_id=${userId}`),
  
  // 관리자용 구매 신청 목록 조회
  getPendingPurchases: () => apiClient.get('/admin/purchases/pending'),
  
  // 구매 신청 승인/거절
  updatePurchaseStatus: (purchaseId, status) => apiClient.put(`/admin/purchases/${purchaseId}`, { status }),
  
  // 사용자 관련 API
  // 사용자 등록
  registerUser: (userData) => apiClient.post('/users/register', userData),
  
  // 사용자 로그인
  userLogin: (userId) => apiClient.post('/users/login', { userId }),
  
  // 사용자 활동 업데이트
  updateUserActivity: (userId) => apiClient.post('/users/activity', { userId }),
  
  // 관리자용 사용자 정보 조회
  getUsersInfo: () => apiClient.get('/admin/users'),
  
  // 개별 사용자 정보 조회
  getUserInfo: (userId) => apiClient.get(`/users/${userId}`),
  
  // 포인트 구매 내역 엑셀 다운로드
  exportPurchases: () => apiClient.get('/admin/export/purchases')
}

// 에러 처리 헬퍼 함수
export const handleApiError = (error) => {
  if (error.response) {
    // 서버 응답이 있는 경우
    const { status, data } = error.response
    switch (status) {
      case 400:
        return { type: 'validation_error', message: data.message || '잘못된 요청입니다.' }
      case 401:
        return { type: 'auth_error', message: '인증이 필요합니다.' }
      case 403:
        return { type: 'permission_error', message: '권한이 없습니다.' }
      case 404:
        return { type: 'not_found', message: '요청한 리소스를 찾을 수 없습니다.' }
      case 500:
        return { type: 'server_error', message: '서버 오류가 발생했습니다.' }
      default:
        return { type: 'unknown_error', message: '알 수 없는 오류가 발생했습니다.' }
    }
  } else if (error.request) {
    // 요청은 보냈지만 응답을 받지 못한 경우
    return { type: 'network_error', message: '네트워크 연결을 확인해주세요.' }
  } else {
    // 요청 설정 중 오류가 발생한 경우
    return { type: 'request_error', message: '요청 설정 중 오류가 발생했습니다.' }
  }
}

// 주문 데이터 변환 헬퍼 함수 (SMM KINGS API v2 구조)
export const transformOrderData = (orderData) => {
  return {
    service: orderData.serviceId, // SMM KINGS 서비스 ID
    link: orderData.link, // 대상 URL 또는 사용자명
    quantity: orderData.quantity,
    runs: orderData.runs || 1, // 실행 횟수 (기본값: 1)
    interval: orderData.interval || 0, // 간격 (분, 기본값: 0)
    comments: orderData.comments || '', // 커스텀 댓글
    username: orderData.username || '', // 사용자명 (구독 서비스용)
    min: orderData.min || 0, // 최소 수량
    max: orderData.max || 0, // 최대 수량
    posts: orderData.posts || 0, // 게시물 수
    delay: orderData.delay || 0, // 지연 시간
    expiry: orderData.expiry || '', // 만료일
    old_posts: orderData.oldPosts || 0, // 이전 게시물 수
    country: orderData.country || '', // 국가 (웹 트래픽용)
    device: orderData.device || '', // 디바이스 (웹 트래픽용)
    type_of_traffic: orderData.typeOfTraffic || '', // 트래픽 타입 (웹 트래픽용)
    google_keyword: orderData.googleKeyword || '' // 구글 키워드 (웹 트래픽용)
  }
}

export default smmkingsApi
