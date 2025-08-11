import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import Layout from './components/Layout'
import Home from './pages/Home'
import LoginPage from './pages/LoginPage'
import SignupPage from './pages/SignupPage'
import OrderPage from './pages/OrderPage'
import PaymentPage from './pages/PaymentPage'
import OrderCompletePage from './pages/OrderCompletePage'
import OrdersPage from './pages/OrdersPage'
import CouponPage from './pages/CouponPage'
import ProtectedRoute from './components/ProtectedRoute'
import './App.css'

function App() {
  return (
    <AuthProvider>
      <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Layout>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route path="/orders" element={
              <ProtectedRoute>
                <OrdersPage />
              </ProtectedRoute>
            } />
            <Route path="/coupons" element={
              <ProtectedRoute>
                <CouponPage />
              </ProtectedRoute>
            } />
            <Route path="/order/:platform" element={
              <ProtectedRoute>
                <OrderPage />
              </ProtectedRoute>
            } />
            <Route path="/payment/:platform" element={
              <ProtectedRoute>
                <PaymentPage />
              </ProtectedRoute>
            } />
            <Route path="/order-complete/:orderId" element={
              <ProtectedRoute>
                <OrderCompletePage />
              </ProtectedRoute>
            } />
          </Routes>
        </Layout>
      </Router>
    </AuthProvider>
  )
}

export default App
