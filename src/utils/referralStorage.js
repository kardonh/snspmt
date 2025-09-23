// 추천인 데이터 로컬 스토리지 관리
const STORAGE_KEYS = {
  REFERRAL_CODES: 'referral_codes',
  REFERRAL_COMMISSIONS: 'referral_commissions',
  REFERRALS: 'referrals'
}

// 추천인 코드 저장
export const saveReferralCode = (referralCode) => {
  try {
    const existingCodes = getReferralCodes()
    const newCode = {
      id: Date.now(),
      code: referralCode.code,
      email: referralCode.email,
      createdAt: new Date().toISOString(),
      isActive: true,
      usage_count: 0,
      total_commission: 0
    }
    
    const updatedCodes = [newCode, ...existingCodes]
    localStorage.setItem(STORAGE_KEYS.REFERRAL_CODES, JSON.stringify(updatedCodes))
    return newCode
  } catch (error) {
    console.error('추천인 코드 저장 실패:', error)
    throw error
  }
}

// 추천인 코드 목록 가져오기
export const getReferralCodes = () => {
  try {
    const codes = localStorage.getItem(STORAGE_KEYS.REFERRAL_CODES)
    return codes ? JSON.parse(codes) : []
  } catch (error) {
    console.error('추천인 코드 로드 실패:', error)
    return []
  }
}

// 추천인 등록
export const saveReferral = (referral) => {
  try {
    const existingReferrals = getReferrals()
    const newReferral = {
      id: referral.id || Date.now(),
      email: referral.email,
      referralCode: referral.referralCode,
      name: referral.name || '',
      phone: referral.phone || '',
      joinDate: new Date().toISOString().split('T')[0],
      status: '활성',
      registeredBy: 'admin'
    }
    
    const updatedReferrals = [newReferral, ...existingReferrals]
    localStorage.setItem(STORAGE_KEYS.REFERRALS, JSON.stringify(updatedReferrals))
    return newReferral
  } catch (error) {
    console.error('추천인 저장 실패:', error)
    throw error
  }
}

// 추천인 목록 가져오기
export const getReferrals = () => {
  try {
    const referrals = localStorage.getItem(STORAGE_KEYS.REFERRALS)
    return referrals ? JSON.parse(referrals) : []
  } catch (error) {
    console.error('추천인 목록 로드 실패:', error)
    return []
  }
}

// 커미션 내역 저장
export const saveCommission = (commission) => {
  try {
    const existingCommissions = getCommissions()
    const newCommission = {
      id: Date.now(),
      referredUser: commission.referredUser,
      purchaseAmount: commission.purchaseAmount,
      commissionAmount: commission.commissionAmount,
      commissionRate: commission.commissionRate,
      paymentDate: commission.paymentDate || new Date().toISOString().split('T')[0]
    }
    
    const updatedCommissions = [newCommission, ...existingCommissions]
    localStorage.setItem(STORAGE_KEYS.REFERRAL_COMMISSIONS, JSON.stringify(updatedCommissions))
    return newCommission
  } catch (error) {
    console.error('커미션 저장 실패:', error)
    throw error
  }
}

// 커미션 내역 가져오기
export const getCommissions = () => {
  try {
    const commissions = localStorage.getItem(STORAGE_KEYS.REFERRAL_COMMISSIONS)
    return commissions ? JSON.parse(commissions) : []
  } catch (error) {
    console.error('커미션 내역 로드 실패:', error)
    return []
  }
}

// 추천인 코드 업데이트
export const updateReferralCode = (id, updates) => {
  try {
    const codes = getReferralCodes()
    const updatedCodes = codes.map(code => 
      code.id === id ? { ...code, ...updates } : code
    )
    localStorage.setItem(STORAGE_KEYS.REFERRAL_CODES, JSON.stringify(updatedCodes))
    return updatedCodes.find(code => code.id === id)
  } catch (error) {
    console.error('추천인 코드 업데이트 실패:', error)
    throw error
  }
}

// 추천인 코드 삭제
export const deleteReferralCode = (id) => {
  try {
    const codes = getReferralCodes()
    const updatedCodes = codes.filter(code => code.id !== id)
    localStorage.setItem(STORAGE_KEYS.REFERRAL_CODES, JSON.stringify(updatedCodes))
    return true
  } catch (error) {
    console.error('추천인 코드 삭제 실패:', error)
    throw error
  }
}

// 모든 데이터 초기화
export const clearAllReferralData = () => {
  try {
    localStorage.removeItem(STORAGE_KEYS.REFERRAL_CODES)
    localStorage.removeItem(STORAGE_KEYS.REFERRAL_COMMISSIONS)
    localStorage.removeItem(STORAGE_KEYS.REFERRALS)
    return true
  } catch (error) {
    console.error('데이터 초기화 실패:', error)
    throw error
  }
}
