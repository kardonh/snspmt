import React, { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import smmpanelApi from '../services/snspopApi'
import { CreditCard, Building2, User, DollarSign, Receipt, FileText, X } from 'lucide-react'
import './PointsPage.css'

const PointsPage = () => {
  const { currentUser } = useAuth()
  const [userPoints, setUserPoints] = useState(0)
  const [selectedAmount, setSelectedAmount] = useState(10000)
  const [depositorName, setDepositorName] = useState('')
  const [bankName, setBankName] = useState('')
  const [receiptType, setReceiptType] = useState('none') // 'tax', 'cash', 'none'
  const [businessNumber, setBusinessNumber] = useState('')
  const [businessName, setBusinessName] = useState('')
  const [representative, setRepresentative] = useState('')
  const [contactPhone, setContactPhone] = useState('')
  const [contactEmail, setContactEmail] = useState('')
  const [cashReceiptPhone, setCashReceiptPhone] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [purchaseHistory, setPurchaseHistory] = useState([])
  const [userInfo, setUserInfo] = useState(null)
  const [referralCodes, setReferralCodes] = useState([])
  const [referralCommissions, setReferralCommissions] = useState([])

  const pointPackages = [
    { amount: 10000, price: 10000, bonus: 0 },
    { amount: 50000, price: 50000, bonus: 5000 },
    { amount: 100000, price: 100000, bonus: 15000 },
    { amount: 200000, price: 200000, bonus: 40000 },
    { amount: 500000, price: 500000, bonus: 125000 },
    { amount: 1000000, price: 1000000, bonus: 300000 }
  ]

  useEffect(() => {
    if (currentUser) {
      loadUserPoints()
      loadPurchaseHistory()
      loadUserInfo()
      loadReferralData()
    }
  }, [currentUser])

  // userInfo가 로드되고 세금계산서가 선택된 경우 자동 입력
  useEffect(() => {
    if (userInfo && receiptType === 'tax' && userInfo.accountType === 'business') {
      setBusinessNumber(userInfo.businessNumber || '')
      setBusinessName(userInfo.businessName || '')
      setRepresentative(userInfo.representative || '')
      setContactPhone(userInfo.contactPhone || '')
      setContactEmail(userInfo.contactEmail || '')
    }
  }, [userInfo, receiptType])

  const loadUserPoints = async () => {
    try {
      const response = await fetch(`/api/points?user_id=${currentUser.uid}`)
      if (response.ok) {
        const data = await response.json()
        setUserPoints(data.points || 0)
      }
    } catch (error) {
      console.error('포인트 조회 실패:', error)
    }
  }

  const loadPurchaseHistory = async () => {
    try {
      const response = await fetch(`/api/points/purchase-history?user_id=${currentUser.uid}`)
      if (response.ok) {
        const data = await response.json()
        setPurchaseHistory(data.purchases || [])
      }
    } catch (error) {
      console.error('구매 내역 조회 실패:', error)
    }
  }

  const loadUserInfo = async () => {
    try {
              const response = await smmpanelApi.getUserInfo(currentUser.uid)
      console.log('사용자 정보 로드:', response)
      setUserInfo(response.user || null)
    } catch (error) {
      console.error('사용자 정보 조회 실패:', error)
    }
  }

  const loadReferralData = async () => {
    try {
      // 추천인 코드 목록 로드
      const codesResponse = await fetch(`/api/referral/my-codes?user_id=${currentUser.uid}`)
      if (codesResponse.ok) {
        const codesData = await codesResponse.json()
        setReferralCodes(codesData.codes || [])
      }

      // 추천인 커미션 내역 로드
      const commissionsResponse = await fetch(`/api/referral/commissions?user_id=${currentUser.uid}`)
      if (commissionsResponse.ok) {
        const commissionsData = await commissionsResponse.json()
        setReferralCommissions(commissionsData.commissions || [])
      }
    } catch (error) {
      console.error('추천인 데이터 로드 실패:', error)
    }
  }

  const handleReceiptTypeChange = (type) => {
    setReceiptType(type)
    
    console.log('영수증 타입 변경:', type)
    console.log('현재 사용자 정보:', userInfo)
    
    // 비즈니스 계정이고 세금계산서를 선택한 경우 자동으로 정보 입력
    if (type === 'tax' && userInfo && userInfo.accountType === 'business') {
      console.log('비즈니스 계정 자동 입력 시작')
      setBusinessNumber(userInfo.businessNumber || '')
      setBusinessName(userInfo.businessName || '')
      setRepresentative(userInfo.representative || '')
      setContactPhone(userInfo.contactPhone || '')
      setContactEmail(userInfo.contactEmail || '')
      
      // 자동 입력 완료 메시지
      setTimeout(() => {
        alert('비즈니스 계정 정보가 자동으로 입력되었습니다.')
      }, 100)
    } else if (type === 'tax') {
      console.log('비즈니스 계정이 아님 또는 사용자 정보 없음')
      console.log('userInfo:', userInfo)
      console.log('accountType:', userInfo?.accountType)
    }
  }

  const handlePurchase = async () => {
    if (!depositorName.trim() || !bankName.trim()) {
      alert('입금자 명과 은행을 모두 입력해주세요.')
      return
    }

    // 세금계산서 선택 시 모든 필수 정보 입력 확인
    if (receiptType === 'tax' && (!businessNumber.trim() || !businessName.trim() || !representative.trim() || !contactPhone.trim() || !contactEmail.trim())) {
      alert('세금계산서 발급을 위해 모든 필수 정보를 입력해주세요.')
      return
    }

    // 현금영수증 선택 시 전화번호 필수
    if (receiptType === 'cash' && !cashReceiptPhone.trim()) {
      alert('현금영수증 발급을 위해 전화번호를 입력해주세요.')
      return
    }

    setIsLoading(true)
    try {
      const purchaseData = {
        user_id: currentUser.uid,
        depositorName: depositorName.trim(),
        bankName: bankName.trim(),
        receiptType: receiptType,
        businessNumber: businessNumber.trim(),
        businessName: businessName.trim(),
        representative: representative.trim(),
        contactPhone: contactPhone.trim(),
        contactEmail: contactEmail.trim(),
        cashReceiptPhone: cashReceiptPhone.trim(),
        amount: selectedAmount,
        price: pointPackages.find(pkg => pkg.amount === selectedAmount).price,
        status: 'pending'
      }

      // 내부 API로 포인트 구매 신청
      const response = await fetch('/api/points/purchase', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': currentUser.uid
        },
        body: JSON.stringify({
          user_id: currentUser.uid,
          amount: selectedAmount,
          price: pointPackages.find(pkg => pkg.amount === selectedAmount).price
        })
      })
      
      const result = await response.json()
      
      if (response.ok && result.purchase_id) {
        alert('포인트 구매 신청이 완료되었습니다. 관리자 승인 후 포인트가 추가됩니다.')
        setDepositorName('')
        setBankName('')
        setReceiptType('none')
        setBusinessNumber('')
        setBusinessName('')
        setRepresentative('')
        setContactPhone('')
        setContactEmail('')
        setCashReceiptPhone('')
        loadPurchaseHistory()
      } else {
        alert(`구매 신청 중 오류가 발생했습니다: ${result.error || '알 수 없는 오류'}`)
      }
    } catch (error) {
      console.error('구매 신청 실패:', error)
      alert('구매 신청 중 오류가 발생했습니다.')
    } finally {
      setIsLoading(false)
    }
  }

  const getSelectedPackage = () => {
    return pointPackages.find(pkg => pkg.amount === selectedAmount)
  }

  return (
    <div className="points-page">
      <div className="points-header">
        <h1>포인트 구매</h1>
        <div className="current-points">
          <DollarSign size={24} />
          <span>현재 포인트: {userPoints.toLocaleString()}P</span>
        </div>
      </div>

      <div className="points-content">
        {/* 포인트 패키지 선택 */}
        <div className="points-packages">
          <h2>포인트 패키지 선택</h2>
          <div className="package-grid">
            {pointPackages.map((pkg) => (
              <div
                key={pkg.amount}
                className={`package-item ${selectedAmount === pkg.amount ? 'selected' : ''}`}
                onClick={() => setSelectedAmount(pkg.amount)}
              >
                <div className="package-amount">{pkg.amount.toLocaleString()}P</div>
                <div className="package-price">{pkg.price.toLocaleString()}원</div>
                {pkg.bonus > 0 && (
                  <div className="package-bonus">+{pkg.bonus.toLocaleString()}P 보너스</div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* 구매 정보 입력 */}
        <div className="purchase-form">
          <h2>구매 정보 입력</h2>
          <div className="form-group">
            <label>
              <User size={16} />
              입금자 명
            </label>
            <input
              type="text"
              value={depositorName}
              onChange={(e) => setDepositorName(e.target.value)}
              placeholder="입금자 명을 입력하세요"
              className="form-input"
            />
          </div>
          
          <div className="form-group">
            <label>
              <Building2 size={16} />
              은행
            </label>
            <input
              type="text"
              value={bankName}
              onChange={(e) => setBankName(e.target.value)}
              placeholder="은행명을 입력하세요 (예: 신한은행)"
              className="form-input"
            />
          </div>

          {/* 영수증 계산서 선택 */}
          <div className="receipt-section">
            <h3>
              <Receipt size={20} />
              영수증 계산서
            </h3>
            <div className="receipt-options">
              <label className="receipt-option">
                <input
                  type="radio"
                  name="receiptType"
                  value="none"
                  checked={receiptType === 'none'}
                  onChange={(e) => handleReceiptTypeChange(e.target.value)}
                />
                <X className="receipt-option-icon" />
                <span className="receipt-label">선택안함</span>
              </label>
              <label className="receipt-option">
                <input
                  type="radio"
                  name="receiptType"
                  value="cash"
                  checked={receiptType === 'cash'}
                  onChange={(e) => handleReceiptTypeChange(e.target.value)}
                />
                <Receipt className="receipt-option-icon" />
                <span className="receipt-label">현금영수증</span>
              </label>
              <label className="receipt-option">
                <input
                  type="radio"
                  name="receiptType"
                  value="tax"
                  checked={receiptType === 'tax'}
                  onChange={(e) => handleReceiptTypeChange(e.target.value)}
                />
                <FileText className="receipt-option-icon" />
                <span className="receipt-label">세금계산서</span>
              </label>
            </div>
          </div>

          {/* 세금계산서 선택 시 추가 정보 */}
          {receiptType === 'tax' && (
            <>
              <div className="form-group">
                <label>
                  <User size={16} />
                  사업자등록번호
                  {userInfo && userInfo.accountType === 'business' && (
                    <span style={{ fontSize: '12px', color: '#10b981', marginLeft: '8px' }}>
                      (자동 입력됨)
                    </span>
                  )}
                </label>
                <input
                  type="text"
                  value={businessNumber}
                  onChange={(e) => setBusinessNumber(e.target.value)}
                  placeholder="사업자등록번호를 입력하세요 (예: 123-45-67890)"
                  className={`form-input ${userInfo && userInfo.accountType === 'business' ? 'auto-filled' : ''}`}
                  readOnly={userInfo && userInfo.accountType === 'business'}
                />
              </div>
              <div className="form-group">
                <label>
                  <Building2 size={16} />
                  회사명
                  {userInfo && userInfo.accountType === 'business' && (
                    <span style={{ fontSize: '12px', color: '#10b981', marginLeft: '8px' }}>
                      (자동 입력됨)
                    </span>
                  )}
                </label>
                <input
                  type="text"
                  value={businessName}
                  onChange={(e) => setBusinessName(e.target.value)}
                  placeholder="회사명을 입력하세요"
                  className={`form-input ${userInfo && userInfo.accountType === 'business' ? 'auto-filled' : ''}`}
                  readOnly={userInfo && userInfo.accountType === 'business'}
                />
              </div>
              <div className="form-group">
                <label>
                  <User size={16} />
                  대표자
                  {userInfo && userInfo.accountType === 'business' && (
                    <span style={{ fontSize: '12px', color: '#10b981', marginLeft: '8px' }}>
                      (자동 입력됨)
                    </span>
                  )}
                </label>
                <input
                  type="text"
                  value={representative}
                  onChange={(e) => setRepresentative(e.target.value)}
                  placeholder="대표자명을 입력하세요"
                  className={`form-input ${userInfo && userInfo.accountType === 'business' ? 'auto-filled' : ''}`}
                  readOnly={userInfo && userInfo.accountType === 'business'}
                />
              </div>
              <div className="form-group">
                <label>
                  <User size={16} />
                  담당자 연락처
                  {userInfo && userInfo.accountType === 'business' && (
                    <span style={{ fontSize: '12px', color: '#10b981', marginLeft: '8px' }}>
                      (자동 입력됨)
                    </span>
                  )}
                </label>
                <input
                  type="tel"
                  value={contactPhone}
                  onChange={(e) => setContactPhone(e.target.value)}
                  placeholder="담당자 연락처를 입력하세요 (예: 010-1234-5678)"
                  className={`form-input ${userInfo && userInfo.accountType === 'business' ? 'auto-filled' : ''}`}
                  readOnly={userInfo && userInfo.accountType === 'business'}
                />
              </div>
              <div className="form-group">
                <label>
                  <User size={16} />
                  메일주소
                  {userInfo && userInfo.accountType === 'business' && (
                    <span style={{ fontSize: '12px', color: '#10b981', marginLeft: '8px' }}>
                      (자동 입력됨)
                    </span>
                  )}
                </label>
                <input
                  type="email"
                  value={contactEmail}
                  onChange={(e) => setContactEmail(e.target.value)}
                  placeholder="메일주소를 입력하세요"
                  className={`form-input ${userInfo && userInfo.accountType === 'business' ? 'auto-filled' : ''}`}
                  readOnly={userInfo && userInfo.accountType === 'business'}
                />
              </div>
            </>
          )}

          {/* 현금영수증 선택 시 추가 정보 */}
          {receiptType === 'cash' && (
            <div className="form-group">
              <label>
                <User size={16} />
                전화번호
              </label>
              <input
                type="tel"
                value={cashReceiptPhone}
                onChange={(e) => setCashReceiptPhone(e.target.value)}
                placeholder="현금영수증 발급용 전화번호를 입력하세요 (예: 010-1234-5678)"
                className="form-input"
              />
            </div>
          )}

          <div className="purchase-summary">
            <div className="summary-item">
              <span>선택한 포인트:</span>
              <span>{getSelectedPackage().amount.toLocaleString()}P</span>
            </div>
            {getSelectedPackage().bonus > 0 && (
              <div className="summary-item bonus">
                <span>보너스 포인트:</span>
                <span>+{getSelectedPackage().bonus.toLocaleString()}P</span>
              </div>
            )}
            <div className="summary-item total">
              <span>총 포인트:</span>
              <span>{(getSelectedPackage().amount + getSelectedPackage().bonus).toLocaleString()}P</span>
            </div>
            <div className="summary-item">
              <span>결제 금액:</span>
              <span>{getSelectedPackage().price.toLocaleString()}원</span>
            </div>
          </div>

          <button
            onClick={handlePurchase}
            disabled={isLoading || !depositorName.trim() || !bankName.trim() || (receiptType === 'tax' && (!businessNumber.trim() || !businessName.trim() || !representative.trim() || !contactPhone.trim() || !contactEmail.trim())) || (receiptType === 'cash' && !cashReceiptPhone.trim())}
            className="purchase-btn"
          >
            {isLoading ? '처리중...' : '포인트 구매 신청'}
          </button>
        </div>

        {/* 구매 내역 */}
        <div className="purchase-history">
          <h2>구매 내역</h2>
          {purchaseHistory.length === 0 ? (
            <div className="no-history">구매 내역이 없습니다.</div>
          ) : (
            <div className="history-list">
              {purchaseHistory.map((purchase) => (
                <div key={purchase.id} className="history-item">
                  <div className="history-info">
                    <div className="history-amount">{purchase.amount.toLocaleString()}P</div>
                    <div className="history-date">
                      {purchase.createdAt || purchase.created_at || purchase.date ? 
                        new Date(purchase.createdAt || purchase.created_at || purchase.date).toLocaleDateString() : 
                        '날짜 없음'
                      }
                    </div>
                  </div>
                  <div className={`history-status ${purchase.status}`}>
                    {purchase.status === 'pending' && '승인 대기중'}
                    {purchase.status === 'approved' && '승인 완료'}
                    {purchase.status === 'rejected' && '승인 거절'}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 추천인 현황 */}
        <div className="referral-section">
          <h2>추천인 현황</h2>
          
          {referralCodes.length > 0 ? (
            <div className="referral-content">
              <div className="referral-codes">
                <h3>내 추천인 코드</h3>
                <div className="codes-list">
                  {referralCodes.map((code, index) => (
                    <div key={index} className="code-item">
                      <div className="code-info">
                        <span className="code-text">{code.code}</span>
                        <span className={`status-badge ${code.is_active ? 'active' : 'inactive'}`}>
                          {code.is_active ? '활성' : '비활성'}
                        </span>
                      </div>
                      <div className="code-stats">
                        <span>사용: {code.usage_count}회</span>
                        <span>커미션: {code.total_commission.toLocaleString()}원</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {referralCommissions.length > 0 && (
                <div className="referral-commissions">
                  <h3>커미션 내역</h3>
                  <div className="commissions-list">
                    {referralCommissions.map((commission, index) => (
                      <div key={index} className="commission-item">
                        <div className="commission-info">
                          <span className="referred-user">{commission.referred_user_id}</span>
                          <span className="commission-date">
                            {new Date(commission.created_at).toLocaleDateString()}
                          </span>
                        </div>
                        <div className="commission-amount">
                          +{commission.commission_amount.toLocaleString()}원
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="no-referral">
              <p>아직 발급받은 추천인 코드가 없습니다.</p>
              <p>관리자에게 문의하여 추천인 코드를 발급받으세요.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default PointsPage
