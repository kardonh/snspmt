import React, { Suspense, lazy } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { LanguageProvider } from './contexts/LanguageContext'
import { GuestProvider } from './contexts/GuestContext'
import { NoticeProvider } from './contexts/NoticeContext'
import Layout from './components/Layout'
import ErrorBoundary from './components/ErrorBoundary'
import LoadingSpinner from './components/LoadingSpinner'
import Home from './pages/Home'

// 지연 로딩으로 성능 최적화
const PaymentPage = lazy(() => import('./pages/PaymentPage'))
const OrderCompletePage = lazy(() => import('./pages/OrderCompletePage'))
const OrdersPage = lazy(() => import('./pages/OrdersPage'))
const PointsPage = lazy(() => import('./pages/PointsPage'))
const SettingsPage = lazy(() => import('./pages/SettingsPage'))
const FAQPage = lazy(() => import('./pages/FAQPage'))
const AdminPage = lazy(() => import('./pages/AdminPage'))
const ReferralDashboard = lazy(() => import('./pages/ReferralDashboard'))
const KakaoCallback = lazy(() => import('./pages/KakaoCallback'))
const BlogPage = lazy(() => import('./pages/BlogPage'))
const BlogDetailPage = lazy(() => import('./pages/BlogDetailPage'))
const AdminBlogPage = lazy(() => import('./pages/AdminBlogPage'))
import ProtectedRoute from './components/ProtectedRoute'

import './App.css'
import './components/ErrorBoundary.css'

function App() {
  return (
    <ErrorBoundary>
      <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <AuthProvider>
          <LanguageProvider>
            <GuestProvider>
              <NoticeProvider>
                <div className="App">
                  <Layout>
                <Suspense fallback={<LoadingSpinner message="페이지를 로딩하는 중..." size="large" />}>
                  <Routes>
                    <Route path="/" element={<Home />} />
                    <Route path="/payment/:platform" element={<ProtectedRoute><PaymentPage /></ProtectedRoute>} />
                    <Route path="/order-complete/:orderId" element={<ProtectedRoute><OrderCompletePage /></ProtectedRoute>} />
                    <Route path="/order-complete" element={<ProtectedRoute><OrderCompletePage /></ProtectedRoute>} />
                    <Route path="/orders" element={<ProtectedRoute><OrdersPage /></ProtectedRoute>} />
                    <Route path="/points" element={<ProtectedRoute><PointsPage /></ProtectedRoute>} />
                    <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
                    <Route path="/admin" element={<ProtectedRoute><AdminPage /></ProtectedRoute>} />
                    <Route path="/referral" element={<ProtectedRoute><ReferralDashboard /></ProtectedRoute>} />
                    <Route path="/faq" element={<FAQPage />} />
                    <Route path="/blog" element={<BlogPage />} />
                    <Route path="/blog/:id" element={<BlogDetailPage />} />
                    <Route path="/admin/blog" element={<ProtectedRoute><AdminBlogPage /></ProtectedRoute>} />
                    <Route path="/kakao-callback" element={<KakaoCallback />} />
                  </Routes>
                </Suspense>
              </Layout>
              </div>
              </NoticeProvider>
            </GuestProvider>
        </LanguageProvider>
      </AuthProvider>
    </Router>
    </ErrorBoundary>
  )
}

export default App
