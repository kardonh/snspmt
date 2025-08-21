import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { LanguageProvider } from './contexts/LanguageContext'
import Layout from './components/Layout'
import Home from './pages/Home'
import OrderPage from './pages/OrderPage'
import PaymentPage from './pages/PaymentPage'
import OrderCompletePage from './pages/OrderCompletePage'
import OrdersPage from './pages/OrdersPage'
import SettingsPage from './pages/SettingsPage'
import InfoPage from './pages/InfoPage'
import FAQPage from './pages/FAQPage'
import ServicePage from './pages/ServicePage'
import AdminPage from './pages/AdminPage'
import ProtectedRoute from './components/ProtectedRoute'
import './App.css'

function App() {
  return (
    <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider>
        <LanguageProvider>
          <div className="App">
            <Layout>
              <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/order/:platform/:serviceId" element={<ProtectedRoute><OrderPage /></ProtectedRoute>} />
                <Route path="/payment/:platform" element={<ProtectedRoute><PaymentPage /></ProtectedRoute>} />
                <Route path="/order-complete" element={<ProtectedRoute><OrderCompletePage /></ProtectedRoute>} />
                <Route path="/orders" element={<ProtectedRoute><OrdersPage /></ProtectedRoute>} />
                <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
                <Route path="/admin" element={<AdminPage />} />
                <Route path="/info" element={<InfoPage />} />
                <Route path="/faq" element={<FAQPage />} />
                <Route path="/service" element={<ServicePage />} />
              </Routes>
            </Layout>
          </div>
        </LanguageProvider>
      </AuthProvider>
    </Router>
  )
}

export default App
