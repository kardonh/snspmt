import React, { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'
import { 
  Users, 
  DollarSign, 
  TrendingUp, 
  TrendingDown, 
  CreditCard, 
  RefreshCw,
  BarChart3,
  Calendar,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react'
import './AdminPage.css'

const AdminPage = () => {
  const { currentUser } = useAuth()
  const navigate = useNavigate()
  const [stats, setStats] = useState({
    totalUsers: 0,
    monthlyUsers: 0,
    totalRevenue: 0,
    monthlyRevenue: 0,
    totalSMMKingsCharge: 0,
    monthlySMMKingsCharge: 0
  })
  const [transactions, setTransactions] = useState({
    charges: [],
    refunds: []
  })
  const [loading, setLoading] = useState(true)

  // 관리자 이메일 체크
  useEffect(() => {
    console.log('AdminPage useEffect - currentUser:', currentUser)
    
    if (!currentUser) {
      console.log('No currentUser, redirecting to home')
      navigate('/')
      return
    }

    console.log('Current user email:', currentUser.email)
    
    // 관리자 이메일 체크
    if (currentUser.email !== 'tambleofficial@gmail.com') {
      console.log('Not admin user, redirecting to home')
      alert('관리자만 접근할 수 있습니다.')
      navigate('/')
      return
    }

    console.log('Admin user confirmed, loading data')
    // 관리자 데이터 로드
    loadAdminData()
  }, [currentUser, navigate])

  const loadAdminData = async () => {
    try {
      setLoading(true)
      console.log('Loading admin data...')
      
      // 백엔드 서버 URL 확인
      const baseUrl = window.location.hostname === 'localhost' ? 'http://localhost:8000' : ''
      
      // 실제 API 호출
      const [statsResponse, transactionsResponse] = await Promise.all([
        fetch(`${baseUrl}/api/admin/stats`),
        fetch(`${baseUrl}/api/admin/transactions`)
      ])
      
      console.log('API responses:', { statsResponse, transactionsResponse })
      console.log('Stats response status:', statsResponse.status)
      console.log('Transactions response status:', transactionsResponse.status)
      
      // 응답 내용 확인
      const statsText = await statsResponse.text()
      const transactionsText = await transactionsResponse.text()
      
      console.log('Stats response text:', statsText.substring(0, 200))
      console.log('Transactions response text:', transactionsText.substring(0, 200))
      
      if (!statsResponse.ok || !transactionsResponse.ok) {
        throw new Error(`API 요청 실패: Stats ${statsResponse.status}, Transactions ${transactionsResponse.status}`)
      }
      
      // JSON 파싱 시도
      let statsData, transactionsData
      try {
        statsData = JSON.parse(statsText)
        transactionsData = JSON.parse(transactionsText)
      } catch (parseError) {
        console.error('JSON 파싱 실패:', parseError)
        throw new Error('API 응답이 유효한 JSON이 아닙니다')
      }
      
      console.log('API data:', { statsData, transactionsData })
      
      if (statsData.success) {
        setStats(statsData.data)
      }
      
      if (transactionsData.success) {
        setTransactions(transactionsData.data)
      }

    } catch (error) {
      console.error('관리자 데이터 로드 실패:', error)
      // API 실패 시 임시 데이터 사용
      const mockData = {
        totalUsers: 1250,
        monthlyUsers: 89,
        totalRevenue: 2500000,
        monthlyRevenue: 180000,
        totalSMMKingsCharge: 1800000,
        monthlySMMKingsCharge: 120000
      }
      
      setStats(mockData)
      setTransactions({
        charges: [
          { id: 1, user: 'user1@example.com', amount: 50000, date: '2024-01-15', status: 'completed' },
          { id: 2, user: 'user2@example.com', amount: 30000, date: '2024-01-14', status: 'completed' }
        ],
        refunds: [
          { id: 1, user: 'user4@example.com', amount: 25000, date: '2024-01-12', reason: '서비스 미제공' }
        ]
      })
    } finally {
      setLoading(false)
    }
  }

  const formatNumber = (num) => {
    return new Intl.NumberFormat('ko-KR').format(num)
  }

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('ko-KR', {
      style: 'currency',
      currency: 'KRW'
    }).format(amount)
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('ko-KR')
  }

  if (loading) {
    return (
      <div className="admin-loading">
        <div className="loading-spinner"></div>
        <p>관리자 데이터를 불러오는 중...</p>
        <p>현재 사용자: {currentUser ? currentUser.email : '로그인되지 않음'}</p>
      </div>
    )
  }

  return (
    <div className="admin-page">
      <div className="admin-header">
        <h1>관리자 대시보드</h1>
        <p>안녕하세요, 관리자님! 오늘의 통계를 확인하세요.</p>
        <p style={{fontSize: '0.9rem', opacity: 0.8}}>현재 사용자: {currentUser ? currentUser.email : '로그인되지 않음'}</p>
      </div>

      {/* 통계 카드 섹션 */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon users">
            <Users size={24} />
          </div>
          <div className="stat-content">
            <h3>총 가입자수</h3>
            <p className="stat-number">{formatNumber(stats.totalUsers)}명</p>
            <div className="stat-change positive">
              <ArrowUpRight size={16} />
              <span>이번 달 +{formatNumber(stats.monthlyUsers)}명</span>
            </div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon revenue">
            <DollarSign size={24} />
          </div>
          <div className="stat-content">
            <h3>총 매출액</h3>
            <p className="stat-number">{formatCurrency(stats.totalRevenue)}</p>
            <div className="stat-change positive">
              <ArrowUpRight size={16} />
              <span>이번 달 +{formatCurrency(stats.monthlyRevenue)}</span>
            </div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon charge">
            <CreditCard size={24} />
          </div>
          <div className="stat-content">
            <h3>총 SMM KINGS 충전액</h3>
            <p className="stat-number">{formatCurrency(stats.totalSMMKingsCharge)}</p>
            <div className="stat-change positive">
              <ArrowUpRight size={16} />
              <span>이번 달 +{formatCurrency(stats.monthlySMMKingsCharge)}</span>
            </div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon profit">
            <BarChart3 size={24} />
          </div>
          <div className="stat-content">
            <h3>순이익</h3>
            <p className="stat-number">{formatCurrency(stats.totalRevenue - stats.totalSMMKingsCharge)}</p>
            <div className="stat-change positive">
              <ArrowUpRight size={16} />
              <span>이번 달 +{formatCurrency(stats.monthlyRevenue - stats.monthlySMMKingsCharge)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* 상세 통계 섹션 */}
      <div className="detailed-stats">
        <div className="monthly-stats">
          <h2>이번 달 통계</h2>
          <div className="monthly-grid">
            <div className="monthly-item">
              <Calendar size={20} />
              <span>신규 가입자</span>
              <strong>{formatNumber(stats.monthlyUsers)}명</strong>
            </div>
            <div className="monthly-item">
              <TrendingUp size={20} />
              <span>월 매출액</span>
              <strong>{formatCurrency(stats.monthlyRevenue)}</strong>
            </div>
            <div className="monthly-item">
              <RefreshCw size={20} />
              <span>월 충전액</span>
              <strong>{formatCurrency(stats.monthlySMMKingsCharge)}</strong>
            </div>
            <div className="monthly-item">
              <TrendingDown size={20} />
              <span>월 순이익</span>
              <strong>{formatCurrency(stats.monthlyRevenue - stats.monthlySMMKingsCharge)}</strong>
            </div>
          </div>
        </div>
      </div>

      {/* 거래 내역 섹션 */}
      <div className="transactions-section">
        <div className="transactions-grid">
          {/* 충전 내역 */}
          <div className="transaction-card">
            <div className="transaction-header">
              <h3>충전 내역</h3>
              <span className="transaction-count">{transactions.charges.length}건</span>
            </div>
            <div className="transaction-list">
              {transactions.charges.map(charge => (
                <div key={charge.id} className="transaction-item">
                  <div className="transaction-info">
                    <span className="transaction-user">{charge.user}</span>
                    <span className="transaction-date">{formatDate(charge.date)}</span>
                  </div>
                  <div className="transaction-amount positive">
                    +{formatCurrency(charge.amount)}
                  </div>
                  <div className={`transaction-status ${charge.status}`}>
                    {charge.status === 'completed' ? '완료' : '대기중'}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 환불 내역 */}
          <div className="transaction-card">
            <div className="transaction-header">
              <h3>환불 내역</h3>
              <span className="transaction-count">{transactions.refunds.length}건</span>
            </div>
            <div className="transaction-list">
              {transactions.refunds.map(refund => (
                <div key={refund.id} className="transaction-item">
                  <div className="transaction-info">
                    <span className="transaction-user">{refund.user}</span>
                    <span className="transaction-date">{formatDate(refund.date)}</span>
                  </div>
                  <div className="transaction-amount negative">
                    -{formatCurrency(refund.amount)}
                  </div>
                  <div className="transaction-reason">
                    {refund.reason}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default AdminPage
