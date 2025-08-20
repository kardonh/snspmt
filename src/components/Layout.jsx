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

  // 화면 크기 감지 및 사이드바 상태 조정
  useEffect(() => {
    const checkIsMobile = () => {
      const mobile = window.innerWidth <= 768
      setIsMobile(mobile)
      
      // 모바일에서는 사이드바를 닫고, 데스크톱에서는 열기
      if (mobile) {
        setSidebarOpen(false)
      } else {
        setSidebarOpen(true)
      }
    }
    
    checkIsMobile()
    window.addEventListener('resize', checkIsMobile)
    
    return () => window.removeEventListener('resize', checkIsMobile)
  }, [])

  const toggleSidebar = () => {
    console.log('Toggle sidebar clicked, current state:', sidebarOpen)
    const newState = !sidebarOpen
    setSidebarOpen(newState)
    console.log('New sidebar state:', newState)
    
    // 강제로 DOM 업데이트
    setTimeout(() => {
      const sidebar = document.querySelector('.sidebar-container')
      if (sidebar) {
        if (newState) {
          sidebar.style.transform = 'translateX(0)'
          sidebar.style.visibility = 'visible'
          sidebar.style.opacity = '1'
          sidebar.style.left = '0'
        } else {
          sidebar.style.transform = 'translateX(-100%)'
          sidebar.style.visibility = 'hidden'
          sidebar.style.opacity = '0'
          sidebar.style.left = '-280px'
        }
      }
    }, 100)
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
          <Sidebar onClose={isMobile ? () => setSidebarOpen(false) : undefined} />
        </div>
        
        <main className={`main-content ${sidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
          {children}
        </main>
        <GuidePanel />
        
        {/* 디버깅 정보 */}
        {isMobile && (
          <div style={{ 
            position: 'fixed', 
            top: '120px', 
            left: '16px', 
            background: 'rgba(0,0,0,0.8)', 
            color: 'white', 
            padding: '8px', 
            borderRadius: '4px',
            fontSize: '12px',
            zIndex: 1001
          }}>
            Sidebar: {sidebarOpen ? 'OPEN' : 'CLOSED'}
          </div>
        )}
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