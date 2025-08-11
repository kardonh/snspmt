import React from 'react'
import { useLocation, Link } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header from './Header'
import './Layout.css'

const Layout = ({ children }) => {
  const location = useLocation()
  const isOrderPage = location.pathname.includes('/order')

  return (
    <div className="layout">
      <Header />
      <div className="layout-content">
        {isOrderPage && <Sidebar />}
        <main className="main-content">
          {children}
        </main>
      </div>
    </div>
  )
}

export default Layout
