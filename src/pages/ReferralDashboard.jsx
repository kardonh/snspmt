import React, { useState, useEffect } from 'react'
import './ReferralDashboard.css'

const ReferralDashboard = () => {
  const [referralCode, setReferralCode] = useState('')
  const [referralStats, setReferralStats] = useState({
    totalReferrals: 0,
    totalCommission: 0,
    activeReferrals: 0,
    thisMonthReferrals: 0,
    thisMonthCommission: 0
  })
  const [referralHistory, setReferralHistory] = useState([])
  const [commissionHistory, setCommissionHistory] = useState([])

  useEffect(() => {
    loadReferralData()
  }, [])

  const loadReferralData = async () => {
    try {
      // 사용자 ID 가져오기 (실제로는 인증된 사용자 ID 사용)
      const userId = localStorage.getItem('userId') || 'demo_user'
      
      // 추천인 코드 조회
      const codeResponse = await fetch(`/api/referral/my-codes?user_id=${userId}`)
      if (codeResponse.ok) {
        const codeData = await codeResponse.json()
        if (codeData.codes && codeData.codes.length > 0) {
          setReferralCode(codeData.codes[0].code)
        } else {
          // 코드가 없으면 새로 생성
          const generateResponse = await fetch('/api/referral/generate-code', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, user_email: `${userId}@example.com` })
          })
          if (generateResponse.ok) {
            const generateData = await generateResponse.json()
            setReferralCode(generateData.code)
          }
        }
      }

      // 추천인 통계 조회
      const statsResponse = await fetch(`/api/referral/stats?user_id=${userId}`)
      if (statsResponse.ok) {
        const statsData = await statsResponse.json()
        setReferralStats(statsData)
      } else {
        // 폴백 데이터
        setReferralStats({
          totalReferrals: 0,
          totalCommission: 0,
          activeReferrals: 0,
          thisMonthReferrals: 0,
          thisMonthCommission: 0,
        })
      }

      // 추천인 목록 조회
      const referralsResponse = await fetch(`/api/referral/referrals?user_id=${userId}`)
      if (referralsResponse.ok) {
        const referralsData = await referralsResponse.json()
        setReferralHistory(referralsData.referrals || [])
      }

      // 커미션 내역 조회
      const commissionsResponse = await fetch(`/api/referral/commissions?user_id=${userId}`)
      if (commissionsResponse.ok) {
        const commissionsData = await commissionsResponse.json()
        setCommissionHistory(commissionsData.commissions || [])
      }
    } catch (error) {
      console.error('추천인 데이터 로드 실패:', error)
      // 폴백으로 기본 데이터 사용
      setReferralStats({
        totalReferrals: 0,
        totalCommission: 0,
        activeReferrals: 0,
        thisMonthReferrals: 0,
        thisMonthCommission: 0,
      })
    }
  }

  const copyReferralCode = () => {
    navigator.clipboard.writeText(referralCode)
    alert('추천인 코드가 복사되었습니다!')
  }

  const shareReferralCode = () => {
    const shareText = `추천인 코드: ${referralCode}\n이 코드로 가입하시면 혜택을 받으실 수 있습니다!`
    if (navigator.share) {
      navigator.share({
        title: '추천인 코드',
        text: shareText
      })
    } else {
      navigator.clipboard.writeText(shareText)
      alert('추천인 코드가 복사되었습니다!')
    }
  }

  return (
    <div className="referral-dashboard">
      <div className="dashboard-header">
        <h1>추천인 대시보드</h1>
        <p>추천 현황과 수익을 확인하세요</p>
      </div>

      {/* 추천인 코드 섹션 */}
      <div className="referral-code-section">
        <div className="code-card">
          <h2>내 추천인 코드</h2>
          <div className="code-display">
            <span className="code-text">{referralCode}</span>
            <button className="copy-btn" onClick={copyReferralCode}>
              복사
            </button>
          </div>
          <button className="share-btn" onClick={shareReferralCode}>
            공유하기
          </button>
        </div>
      </div>

      {/* 통계 카드 */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon">👥</div>
          <div className="stat-content">
            <h3>총 추천인</h3>
            <p className="stat-number">{referralStats.totalReferrals}</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">💰</div>
          <div className="stat-content">
            <h3>총 커미션</h3>
            <p className="stat-number">{referralStats.totalCommission.toLocaleString()}원</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">✅</div>
          <div className="stat-content">
            <h3>활성 추천인</h3>
            <p className="stat-number">{referralStats.activeReferrals}</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">📅</div>
          <div className="stat-content">
            <h3>이번 달 추천</h3>
            <p className="stat-number">{referralStats.thisMonthReferrals}</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">💎</div>
          <div className="stat-content">
            <h3>이번 달 수익</h3>
            <p className="stat-number">{referralStats.thisMonthCommission.toLocaleString()}원</p>
          </div>
        </div>
      </div>

      {/* 추천인 목록 */}
      <div className="referral-list-section">
        <div className="section-card">
          <h2>추천인 목록</h2>
          <div className="table-container">
            <table className="referral-table">
              <thead>
                <tr>
                  <th>사용자</th>
                  <th>가입일</th>
                  <th>상태</th>
                  <th>커미션</th>
                </tr>
              </thead>
              <tbody>
                {referralHistory.map((referral) => (
                  <tr key={referral.id}>
                    <td>{referral.user}</td>
                    <td>{referral.joinDate}</td>
                    <td>
                      <span className={`status-badge ${referral.status === '활성' ? 'active' : 'inactive'}`}>
                        {referral.status}
                      </span>
                    </td>
                    <td>{referral.commission.toLocaleString()}원</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* 커미션 내역 */}
      <div className="commission-section">
        <div className="section-card">
          <h2>커미션 내역</h2>
          <div className="table-container">
            <table className="commission-table">
              <thead>
                <tr>
                  <th>피추천인</th>
                  <th>구매 금액</th>
                  <th>커미션 금액</th>
                  <th>커미션율</th>
                  <th>지급일</th>
                </tr>
              </thead>
              <tbody>
                {commissionHistory.map((commission) => (
                  <tr key={commission.id}>
                    <td>{commission.referredUser}</td>
                    <td>{commission.purchaseAmount.toLocaleString()}원</td>
                    <td className="commission-amount">{commission.commissionAmount.toLocaleString()}원</td>
                    <td>{commission.commissionRate}</td>
                    <td>{commission.paymentDate}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* 추천인 혜택 안내 */}
      <div className="benefits-section">
        <div className="section-card">
          <h2>추천인 혜택</h2>
          <div className="benefits-grid">
            <div className="benefit-item">
              <div className="benefit-icon">🎁</div>
              <h3>추천인 보상</h3>
              <p>추천한 사용자가 구매할 때마다 5% 커미션 지급</p>
            </div>
            <div className="benefit-item">
              <div className="benefit-icon">💎</div>
              <h3>추천인 할인</h3>
              <p>추천인 본인도 10% 할인 혜택 제공</p>
            </div>
            <div className="benefit-item">
              <div className="benefit-icon">🏆</div>
              <h3>등급 혜택</h3>
              <p>추천 수에 따라 등급별 추가 혜택 제공</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ReferralDashboard
