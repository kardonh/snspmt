import React, { useState, useEffect } from 'react'
import { Menu, X } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import StatusBar from './StatusBar'
import Sidebar from './Sidebar'
import GuidePanel from './GuidePanel'
import AuthModal from './AuthModal'
import './Layout.css'

const Layout = ({ children }) => {
  const { currentUser } = useAuth()
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [isMobile, setIsMobile] = useState(false)
  const [showAuthModal, setShowAuthModal] = useState(false)

  // 화면 크기 감지
  useEffect(() => {
    const checkIsMobile = () => {
      setIsMobile(window.innerWidth <= 768)
    }
    
    checkIsMobile()
    window.addEventListener('resize', checkIsMobile)
    
    return () => window.removeEventListener('resize', checkIsMobile)
  }, [])

  const toggleSidebar = () => {
    if (isMobile) {
      setSidebarOpen(!sidebarOpen)
    }
  }

  // 로그인 상태 체크
  useEffect(() => {
    // 로딩이 완료된 후에만 체크
    if (currentUser === null) {
      setShowAuthModal(true)
    } else if (currentUser) {
      setShowAuthModal(false)
    }
  }, [currentUser])

  return (
    <div className="layout">
      <StatusBar />
      <div className="layout-content">
        {/* Sidebar Toggle Button - 모바일에서만 표시 */}
        {isMobile && (
          <button className="sidebar-toggle" onClick={toggleSidebar}>
            {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        )}
        
        {/* Sidebar - 데스크톱에서는 항상 열림, 모바일에서는 토글 */}
        <div className={`sidebar-container ${sidebarOpen ? 'open' : 'closed'}`}>
          <Sidebar onClose={() => isMobile && setSidebarOpen(false)} />
        </div>
        
        <main className={`main-content ${sidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
          {children}
        </main>
        <GuidePanel />
      </div>

      {/* Auth Modal */}
      <AuthModal 
        isOpen={showAuthModal}
        onClose={() => {
          // 로그인하지 않은 상태에서는 모달을 닫을 수 없음
          if (!currentUser) {
            return
          }
          setShowAuthModal(false)
        }}
        onSuccess={() => {
          setShowAuthModal(false)
        }}
      />
    </div>
  )
}

export default Layout
