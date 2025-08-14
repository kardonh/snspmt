import React, { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useLanguage } from '../contexts/LanguageContext'
import { useNavigate } from 'react-router-dom'
import { 
  User, 
  Bell, 
  Shield, 
  Palette, 
  Globe, 
  Save, 
  ArrowLeft,
  Eye,
  EyeOff,
  Trash2
} from 'lucide-react'
import './SettingsPage.css'

const SettingsPage = () => {
  const { currentUser, updateProfile, deleteAccount } = useAuth()
  const { language, changeLanguage } = useLanguage()
  const navigate = useNavigate()
  
  const [activeTab, setActiveTab] = useState('profile')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  
  // Profile settings
  const [displayName, setDisplayName] = useState(currentUser?.displayName || '')
  const [email, setEmail] = useState(currentUser?.email || '')
  
  // Notification settings
  const [emailNotifications, setEmailNotifications] = useState(true)
  const [orderUpdates, setOrderUpdates] = useState(true)
  const [promotionalEmails, setPromotionalEmails] = useState(false)
  
  // Privacy settings
  const [showProfile, setShowProfile] = useState(true)
  const [allowAnalytics, setAllowAnalytics] = useState(true)
  
  // Theme settings
  const [theme, setTheme] = useState('light')
  const [autoTheme, setAutoTheme] = useState(true)
  
  const handleSaveProfile = async () => {
    setLoading(true)
    setMessage('')
    
    try {
      await updateProfile({ displayName })
      setMessage('프로필이 성공적으로 업데이트되었습니다.')
    } catch (error) {
      setMessage('프로필 업데이트에 실패했습니다.')
    }
    
    setLoading(false)
  }
  
  const handleDeleteAccount = async () => {
    if (window.confirm('정말로 계정을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.')) {
      setLoading(true)
      try {
        await deleteAccount()
        navigate('/')
      } catch (error) {
        setMessage('계정 삭제에 실패했습니다.')
        setLoading(false)
      }
    }
  }
  
  const handleLanguageChange = (newLanguage) => {
    changeLanguage(newLanguage)
    setMessage('언어가 성공적으로 변경되었습니다.')
  }
  
  const tabs = [
    { id: 'profile', name: '프로필', icon: User },
    { id: 'notifications', name: '알림', icon: Bell },
    { id: 'privacy', name: '개인정보', icon: Shield },
    { id: 'appearance', name: '외관', icon: Palette },
    { id: 'language', name: '언어', icon: Globe }
  ]

  return (
    <div className="settings-page">
      <div className="settings-header">
        <button onClick={() => navigate(-1)} className="back-btn">
          <ArrowLeft size={20} />
          뒤로가기
        </button>
        <h1>설정</h1>
      </div>
      
      <div className="settings-container">
        <div className="settings-sidebar">
          {tabs.map(({ id, name, icon: Icon }) => (
            <button
              key={id}
              className={`tab-btn ${activeTab === id ? 'active' : ''}`}
              onClick={() => setActiveTab(id)}
            >
              <Icon size={20} />
              {name}
            </button>
          ))}
        </div>
        
        <div className="settings-content">
          {message && (
            <div className={`message ${message.includes('성공') ? 'success' : 'error'}`}>
              {message}
            </div>
          )}
          
          {/* Profile Tab */}
          {activeTab === 'profile' && (
            <div className="settings-section">
              <h2>프로필 설정</h2>
              <div className="form-group">
                <label>사용자명</label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="사용자명을 입력하세요"
                />
              </div>
              <div className="form-group">
                <label>이메일</label>
                <input
                  type="email"
                  value={email}
                  disabled
                  className="disabled"
                />
                <small>이메일은 변경할 수 없습니다.</small>
              </div>
              <button 
                onClick={handleSaveProfile} 
                disabled={loading}
                className="save-btn"
              >
                <Save size={16} />
                저장
              </button>
            </div>
          )}
          
          {/* Notifications Tab */}
          {activeTab === 'notifications' && (
            <div className="settings-section">
              <h2>알림 설정</h2>
              <div className="setting-item">
                <div>
                  <h3>이메일 알림</h3>
                  <p>주요 업데이트를 이메일로 받습니다.</p>
                </div>
                <label className="toggle">
                  <input
                    type="checkbox"
                    checked={emailNotifications}
                    onChange={(e) => setEmailNotifications(e.target.checked)}
                  />
                  <span className="slider"></span>
                </label>
              </div>
              
              <div className="setting-item">
                <div>
                  <h3>주문 업데이트</h3>
                  <p>주문 상태 변경 시 알림을 받습니다.</p>
                </div>
                <label className="toggle">
                  <input
                    type="checkbox"
                    checked={orderUpdates}
                    onChange={(e) => setOrderUpdates(e.target.checked)}
                  />
                  <span className="slider"></span>
                </label>
              </div>
              
              <div className="setting-item">
                <div>
                  <h3>프로모션 이메일</h3>
                  <p>특별 할인 및 이벤트 정보를 받습니다.</p>
                </div>
                <label className="toggle">
                  <input
                    type="checkbox"
                    checked={promotionalEmails}
                    onChange={(e) => setPromotionalEmails(e.target.checked)}
                  />
                  <span className="slider"></span>
                </label>
              </div>
            </div>
          )}
          
          {/* Privacy Tab */}
          {activeTab === 'privacy' && (
            <div className="settings-section">
              <h2>개인정보 설정</h2>
              <div className="setting-item">
                <div>
                  <h3>프로필 공개</h3>
                  <p>다른 사용자가 내 프로필을 볼 수 있습니다.</p>
                </div>
                <label className="toggle">
                  <input
                    type="checkbox"
                    checked={showProfile}
                    onChange={(e) => setShowProfile(e.target.checked)}
                  />
                  <span className="slider"></span>
                </label>
              </div>
              
              <div className="setting-item">
                <div>
                  <h3>분석 데이터 수집</h3>
                  <p>서비스 개선을 위한 익명 데이터를 수집합니다.</p>
                </div>
                <label className="toggle">
                  <input
                    type="checkbox"
                    checked={allowAnalytics}
                    onChange={(e) => setAllowAnalytics(e.target.checked)}
                  />
                  <span className="slider"></span>
                </label>
              </div>
              
              <div className="danger-zone">
                <h3>위험 구역</h3>
                <button 
                  onClick={handleDeleteAccount}
                  disabled={loading}
                  className="delete-account-btn"
                >
                  <Trash2 size={16} />
                  계정 삭제
                </button>
              </div>
            </div>
          )}
          
          {/* Appearance Tab */}
          {activeTab === 'appearance' && (
            <div className="settings-section">
              <h2>외관 설정</h2>
              <div className="setting-item">
                <div>
                  <h3>테마</h3>
                  <p>앱의 색상 테마를 선택하세요.</p>
                </div>
                <select 
                  value={theme} 
                  onChange={(e) => setTheme(e.target.value)}
                  disabled={autoTheme}
                >
                  <option value="light">라이트</option>
                  <option value="dark">다크</option>
                  <option value="auto">자동</option>
                </select>
              </div>
              
              <div className="setting-item">
                <div>
                  <h3>자동 테마</h3>
                  <p>시스템 설정에 따라 테마를 자동으로 변경합니다.</p>
                </div>
                <label className="toggle">
                  <input
                    type="checkbox"
                    checked={autoTheme}
                    onChange={(e) => setAutoTheme(e.target.checked)}
                  />
                  <span className="slider"></span>
                </label>
              </div>
            </div>
          )}
          
          {/* Language Tab */}
          {activeTab === 'language' && (
            <div className="settings-section">
              <h2>언어 설정</h2>
              <div className="setting-item">
                <div>
                  <h3>언어</h3>
                  <p>앱에서 사용할 언어를 선택하세요.</p>
                </div>
                <select 
                  value={language} 
                  onChange={(e) => handleLanguageChange(e.target.value)}
                >
                  <option value="ko">한국어</option>
                  <option value="en">English</option>
                  <option value="ja">日本語</option>
                  <option value="zh">中文</option>
                </select>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default SettingsPage
