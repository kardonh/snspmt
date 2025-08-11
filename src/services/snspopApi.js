import axios from 'axios'

// snspop API 기본 설정 (Render 백엔드 사용)
const API_BASE_URL = 'https://snspmt-backend.onrender.com/api/snspop'

// 기본 API 키
const DEFAULT_API_KEY = '284ff0e3bc3dfff934914d1f30535b3c'

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

// SNS SMM 서비스 API 함수들 (snspop API v2 구조)
export const snspopApi = {
  // 서비스 목록 조회
  getServices: () => apiClient.post('', { action: 'services' }),
  
  // 잔액 조회
  getBalance: () => apiClient.post('', { action: 'balance' }),
  
  // 주문 생성
  createOrder: (orderData) => apiClient.post('', { 
    action: 'add',
    ...orderData 
  }),
  
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
  })
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

// 주문 데이터 변환 헬퍼 함수 (snspop API v2 구조)
export const transformOrderData = (orderData) => {
  return {
    service: orderData.serviceId, // snspop 서비스 ID
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
    old_posts: orderData.oldPosts || 0 // 이전 게시물 수
  }
}

// 사용자 주문 조회
export const getUserOrders = async (userEmail) => {
  try {
    const response = await fetch(`https://snspmt-backend.onrender.com/api/orders?user_email=${encodeURIComponent(userEmail)}`)
    const data = await response.json()
    
    if (!response.ok) {
      throw new Error(data.error || '주문 조회에 실패했습니다')
    }
    
    return data.orders
  } catch (error) {
    console.error('주문 조회 오류:', error)
    throw error
  }
}

// 주문 상태 업데이트
export const updateOrderStatus = async (orderId, status) => {
  try {
    const response = await fetch(`https://snspmt-backend.onrender.com/api/orders/${orderId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ status })
    })
    
    const data = await response.json()
    
    if (!response.ok) {
      throw new Error(data.error || '주문 상태 업데이트에 실패했습니다')
    }
    
    return data
  } catch (error) {
    console.error('주문 상태 업데이트 오류:', error)
    throw error
  }
}

// 추천인 코드 생성
export const generateReferralCode = async (userId, userEmail) => {
  try {
    const response = await fetch('https://snspmt-backend.onrender.com/api/referral/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ user_id: userId, user_email: userEmail })
    })

    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.error || '추천인 코드 생성에 실패했습니다')
    }

    return data.referral_code
  } catch (error) {
    console.error('추천인 코드 생성 오류:', error)
    throw error
  }
}

// 추천인 코드 사용
export const useReferralCode = async (referralCode, userId, userEmail) => {
  try {
    const response = await fetch('https://snspmt-backend.onrender.com/api/referral/use', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        referral_code: referralCode, 
        user_id: userId, 
        user_email: userEmail 
      })
    })

    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.message || '추천인 코드 사용에 실패했습니다')
    }

    return data
  } catch (error) {
    console.error('추천인 코드 사용 오류:', error)
    throw error
  }
}

// 사용자 쿠폰 조회
export const getUserCoupons = async (userEmail) => {
  try {
    const response = await fetch(`https://snspmt-backend.onrender.com/api/coupons?user_email=${encodeURIComponent(userEmail)}`)
    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.error || '쿠폰 조회에 실패했습니다')
    }

    return data.coupons
  } catch (error) {
    console.error('쿠폰 조회 오류:', error)
    throw error
  }
}

// 쿠폰 사용
export const useCoupon = async (couponId, orderId) => {
  try {
    const response = await fetch(`https://snspmt-backend.onrender.com/api/coupons/${couponId}/use`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ order_id: orderId })
    })

    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.error || '쿠폰 사용에 실패했습니다')
    }

    return data
  } catch (error) {
    console.error('쿠폰 사용 오류:', error)
    throw error
  }
}

export default snspopApi
