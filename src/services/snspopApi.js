import axios from 'axios'

// SMM Panel API 기본 설정
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || (window.location.hostname === 'localhost' ? 'http://localhost:8000/api' : 'https://sociality.co.kr/api')

// SMM Panel API 키
const DEFAULT_API_KEY = import.meta.env.VITE_SMMPANEL_API_KEY || 'bc85538982fb27c6c0558be6cd669e67'

// SMM Panel API 엔드포인트
const SMM_PANEL_API_URL = 'https://smmpanel.kr/api/v2'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30초로 증가 (대량 주문 처리 고려)
  headers: {
    'Content-Type': 'application/json',
  }
})

// SMM Panel API 전용 클라이언트 (백엔드 프록시 사용)
const smmPanelClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30초로 증가
  headers: {
    'Content-Type': 'application/json',
  }
})

// API 요청 인터셉터
apiClient.interceptors.request.use(
  (config) => {
    // SMM Panel API 요청에만 키를 추가 (POST 요청이고 action이 있는 경우)
    if (config.method === 'post' && config.data && typeof config.data === 'object' && config.data.action) {
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
  (response) => {
    // 성공 응답 로깅
    // API 호출 성공
    return response.data
  },
  (error) => {
    // 에러 응답 로깅
    const errorInfo = {
      method: error.config?.method?.toUpperCase(),
      url: error.config?.url,
      status: error.response?.status,
      message: error.response?.data?.message || error.message,
      data: error.response?.data
    }
    
    // API 호출 오류
    
    return Promise.reject(error)
  }
)

// SMM Panel API 함수들
export const smmpanelApi = {
  // 서비스 목록 조회
  getServices: () => smmPanelClient.post('/smm-panel', { action: 'services' }),
  
  // 잔액 조회
  getBalance: () => smmPanelClient.post('/smm-panel', { action: 'balance' }),
  
  // 주문 생성
  createOrder: (orderData, userId) => {
    const config = {
      headers: {
        'X-User-ID': userId
      }
    }

    return smmPanelClient.post('/smm-panel', { 
      action: 'add',
      ...orderData 
    }, config)
  },
  
  // 주문 상태 조회
  getOrderStatus: (orderId) => smmPanelClient.post('/smm-panel', { 
    action: 'status',
    order: orderId 
  }),
  
  // 여러 주문 상태 조회
  getMultiOrderStatus: (orderIds) => smmPanelClient.post('/smm-panel', { 
    action: 'status',
    orders: orderIds.join(',') 
  }),
  
  // 주문 리필
  refillOrder: (orderId) => smmPanelClient.post('/smm-panel', { 
    action: 'refill',
    order: orderId 
  }),
  
  // 여러 주문 리필
  refillMultipleOrders: (orderIds) => smmPanelClient.post('/smm-panel', { 
    action: 'refill',
    orders: orderIds.join(',') 
  }),
  
  // 리필 상태 조회
  getRefillStatus: (refillId) => smmPanelClient.post('/smm-panel', { 
    action: 'refill_status',
    refill: refillId 
  }),
  
  // 여러 리필 상태 조회
  getMultiRefillStatus: (refillIds) => smmPanelClient.post('/smm-panel', { 
    action: 'refill_status',
    refills: refillIds.join(',') 
  }),
  
  // 주문 취소
  cancelOrders: (orderIds) => smmPanelClient.post('/smm-panel', { 
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
  createPurchase: (purchaseData, userId) => {
    const config = {
      headers: {
        'X-User-ID': userId
      }
    }
    return apiClient.post('/points/purchase', purchaseData, config)
  },
  
  // 구매 내역 조회
  getPurchaseHistory: (userId) => apiClient.get(`/points/purchase-history?user_id=${userId}`),
  
  // 관리자용 구매 신청 목록 조회
  getPendingPurchases: () => apiClient.get('/admin/purchases'),
  
  // 구매 신청 승인/거절
  updatePurchaseStatus: (purchaseId, status) => apiClient.put(`/admin/purchases/${purchaseId}`, { status }),
  
  // 사용자 관련 API
  // 사용자 등록
  registerUser: (userData) => {
    return apiClient.post('/register', userData)
  },
  
  
  // 사용자 활동 업데이트 (현재 백엔드에서 지원하지 않음)
  // updateUserActivity: (userId) => apiClient.post('/activity', { userId }),
  
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

// 주문 데이터 변환 헬퍼 함수 (SMM Panel API 구조)
export const transformOrderData = (orderData) => {
  // orderData가 undefined인 경우 기본값 사용
  const safeOrderData = orderData || {}
  
  // serviceId가 없거나 undefined인 경우 기본값 사용
  let serviceId = safeOrderData.service_id || safeOrderData.serviceId
  if (!serviceId || serviceId === 'undefined' || serviceId === undefined) {
    // 기본 서비스 ID 설정 (Instagram 한국인 팔로워)
    serviceId = 'followers_korean'
  }
  
  // 안전한 값 변환을 위한 헬퍼 함수
  const safeString = (value) => {
    try {
      if (value === undefined || value === null) return ''
      const str = String(value)
      return str ? str.trim() : ''
    } catch (error) {
      return ''
    }
  }

  const safeNumber = (value) => {
    try {
      if (value === undefined || value === null) return 0
      const num = Number(value)
      return isNaN(num) ? 0 : num
    } catch (error) {
      return 0
    }
  }

  const transformed = {
    service: serviceId, // SMM Panel 서비스 ID
    link: safeString(safeOrderData.link),
    quantity: safeNumber(safeOrderData.quantity),
    runs: safeNumber(safeOrderData.runs || 1),
    interval: safeNumber(safeOrderData.interval || 0),
    comments: safeString(safeOrderData.comments),
    username: safeString(safeOrderData.username),
    min: safeNumber(safeOrderData.min),
    max: safeNumber(safeOrderData.max),
    posts: safeNumber(safeOrderData.posts),
    delay: safeNumber(safeOrderData.delay),
    expiry: safeString(safeOrderData.expiry),
    old_posts: safeNumber(safeOrderData.old_posts),
    country: safeString(safeOrderData.country),
    device: safeString(safeOrderData.device),
    type_of_traffic: safeString(safeOrderData.type_of_traffic),
    google_keyword: safeString(safeOrderData.google_keyword),
    key: 'bc85538982fb27c6c0558be6cd669e67' // SMM Panel API 키
  }
  
  return transformed
}

export default smmpanelApi
