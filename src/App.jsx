import React, { Suspense, lazy } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { LanguageProvider } from './contexts/LanguageContext'
import { GuestProvider } from './contexts/GuestContext'
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
const InfoPage = lazy(() => import('./pages/InfoPage'))
const FAQPage = lazy(() => import('./pages/FAQPage'))
const ServicePage = lazy(() => import('./pages/ServicePage'))
const ServicesPage = lazy(() => import('./pages/ServicesPage'))
const AdminPage = lazy(() => import('./pages/AdminPage'))
const ReferralDashboard = lazy(() => import('./pages/ReferralDashboard'))
const LoginPage = lazy(() => import('./pages/LoginPage'))
const ProtectedRoute = lazy(() => import('./components/ProtectedRoute'))

import './App.css'
import './components/ErrorBoundary.css'

function App() {
  return (
    <ErrorBoundary>
      <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <AuthProvider>
          <LanguageProvider>
            <GuestProvider>
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
                    <Route path="/login" element={<LoginPage />} />
                    <Route path="/info" element={<InfoPage />} />
                    <Route path="/faq" element={<FAQPage />} />
                    <Route path="/service" element={<ServicePage />} />
                    <Route path="/services" element={<ServicesPage />} />
                  </Routes>
                </Suspense>
              </Layout>
              </div>
            </GuestProvider>
        </LanguageProvider>
      </AuthProvider>
    </Router>
    </ErrorBoundary>
  )
}

export default App
