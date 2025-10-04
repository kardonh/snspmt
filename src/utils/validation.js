// 입력 검증 유틸리티 함수들

// 이메일 검증
export const validateEmail = (email) => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

// 비밀번호 검증 (최소 6자)
export const validatePassword = (password) => {
  return password && password.length >= 6
}

// 전화번호 검증 (한국 형식)
export const validatePhone = (phone) => {
  const phoneRegex = /^010-\d{4}-\d{4}$/
  return phoneRegex.test(phone)
}

// URL 검증
export const validateUrl = (url) => {
  try {
    new URL(url)
    return true
  } catch {
    return false
  }
}

// 인스타그램 링크 검증
export const validateInstagramUrl = (url) => {
  const instagramRegex = /^https:\/\/www\.instagram\.com\/([a-zA-Z0-9._]+)\/?$/
  return instagramRegex.test(url)
}

// 양수 검증
export const validatePositiveNumber = (num) => {
  return Number.isInteger(num) && num > 0
}

// 수량 범위 검증
export const validateQuantity = (quantity, min = 1, max = 100000) => {
  return Number.isInteger(quantity) && quantity >= min && quantity <= max
}

// 가격 검증
export const validatePrice = (price) => {
  return typeof price === 'number' && price > 0
}

// 사용자 ID 검증
export const validateUserId = (userId) => {
  return userId && userId.length > 0 && userId.length <= 255
}

// 서비스 ID 검증
export const validateServiceId = (serviceId) => {
  return serviceId && (Number.isInteger(serviceId) || (typeof serviceId === 'string' && serviceId.length > 0))
}

// 날짜 형식 검증 (YYYY-MM-DD)
export const validateDate = (dateString) => {
  const dateRegex = /^\d{4}-\d{2}-\d{2}$/
  if (!dateRegex.test(dateString)) return false
  
  const date = new Date(dateString)
  return date instanceof Date && !isNaN(date)
}

// 시간 형식 검증 (HH:MM)
export const validateTime = (timeString) => {
  const timeRegex = /^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/
  return timeRegex.test(timeString)
}

// 예약 시간 검증 (현재 시간보다 미래인지)
export const validateScheduledTime = (dateString, timeString) => {
  if (!validateDate(dateString) || !validateTime(timeString)) return false
  
  const scheduledDateTime = new Date(`${dateString} ${timeString}`)
  const now = new Date()
  
  return scheduledDateTime > now
}

// 추천인 코드 검증
export const validateReferralCode = (code) => {
  const codeRegex = /^[A-Z0-9]{6,12}$/
  return codeRegex.test(code)
}

// 사업자등록번호 검증 (10자리 숫자)
export const validateBusinessNumber = (number) => {
  const businessRegex = /^\d{10}$/
  return businessRegex.test(number)
}

// 통합 입력 검증 함수
export const validateOrderData = (orderData) => {
  const errors = []
  
  if (!validateUserId(orderData.user_id)) {
    errors.push('유효하지 않은 사용자 ID입니다.')
  }
  
  if (!validateServiceId(orderData.service_id)) {
    errors.push('유효하지 않은 서비스 ID입니다.')
  }
  
  if (!validateUrl(orderData.link)) {
    errors.push('유효하지 않은 링크입니다.')
  }
  
  if (!validateQuantity(orderData.quantity)) {
    errors.push('유효하지 않은 수량입니다.')
  }
  
  if (!validatePrice(orderData.price || orderData.total_price)) {
    errors.push('유효하지 않은 가격입니다.')
  }
  
  if (orderData.is_scheduled) {
    if (!orderData.scheduled_datetime) {
      errors.push('예약 시간이 필요합니다.')
    } else {
      const [date, time] = orderData.scheduled_datetime.split(' ')
      if (!validateScheduledTime(date, time)) {
        errors.push('예약 시간은 현재 시간보다 미래여야 합니다.')
      }
    }
  }
  
  return {
    isValid: errors.length === 0,
    errors
  }
}

// 포인트 구매 데이터 검증
export const validatePurchaseData = (purchaseData) => {
  const errors = []
  
  if (!validateUserId(purchaseData.user_id)) {
    errors.push('유효하지 않은 사용자 ID입니다.')
  }
  
  if (!validatePositiveNumber(purchaseData.amount)) {
    errors.push('유효하지 않은 충전 금액입니다.')
  }
  
  if (purchaseData.amount < 1000) {
    errors.push('최소 충전 금액은 1,000원입니다.')
  }
  
  if (purchaseData.amount > 10000000) {
    errors.push('최대 충전 금액은 10,000,000원입니다.')
  }
  
  if (!purchaseData.depositor_name || purchaseData.depositor_name.trim().length === 0) {
    errors.push('입금자명을 입력해주세요.')
  }
  
  return {
    isValid: errors.length === 0,
    errors
  }
}

// 추천인 데이터 검증
export const validateReferralData = (referralData) => {
  const errors = []
  
  if (!validateEmail(referralData.email)) {
    errors.push('유효하지 않은 이메일입니다.')
  }
  
  if (!referralData.name || referralData.name.trim().length < 2) {
    errors.push('이름은 2자 이상이어야 합니다.')
  }
  
  if (referralData.phone && !validatePhone(referralData.phone)) {
    errors.push('유효하지 않은 전화번호 형식입니다.')
  }
  
  if (referralData.business_number && !validateBusinessNumber(referralData.business_number)) {
    errors.push('유효하지 않은 사업자등록번호입니다.')
  }
  
  return {
    isValid: errors.length === 0,
    errors
  }
}
