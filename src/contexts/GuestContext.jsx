import React, { createContext, useContext, useState, useEffect } from 'react'
import { useAuth } from './AuthContext'

const GuestContext = createContext()

export const useGuest = () => {
  const context = useContext(GuestContext)
  if (!context) {
    throw new Error('useGuest must be used within a GuestProvider')
  }
  return context
}

export const GuestProvider = ({ children }) => {
  const { currentUser } = useAuth()
  const [guestData, setGuestData] = useState({
    guestId: null,
    tempOrders: [],
    tempCart: []
  })

  // 로그인 상태에 따라 자동으로 게스트 모드 결정
  const isGuest = !currentUser

  // 게스트 데이터 초기화 및 관리
  useEffect(() => {
    if (isGuest) {
      // 게스트 모드일 때
      const savedGuestId = localStorage.getItem('guest_id')
      const savedTempOrders = localStorage.getItem('guest_temp_orders')
      const savedTempCart = localStorage.getItem('guest_temp_cart')
      
      if (savedGuestId) {
        // 저장된 게스트 데이터가 있으면 복원
        setGuestData({
          guestId: savedGuestId,
          tempOrders: savedTempOrders ? JSON.parse(savedTempOrders) : [],
          tempCart: savedTempCart ? JSON.parse(savedTempCart) : []
        })
      } else {
        // 저장된 게스트 데이터가 없으면 새로 생성
        const guestId = `guest_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
        setGuestData({
          guestId,
          tempOrders: [],
          tempCart: []
        })
        
        localStorage.setItem('guest_id', guestId)
        localStorage.setItem('guest_temp_orders', JSON.stringify([]))
        localStorage.setItem('guest_temp_cart', JSON.stringify([]))
      }
    } else {
      // 로그인 모드일 때 - 게스트 데이터 초기화
      setGuestData({
        guestId: null,
        tempOrders: [],
        tempCart: []
      })
      
      localStorage.removeItem('guest_id')
      localStorage.removeItem('guest_temp_orders')
      localStorage.removeItem('guest_temp_cart')
    }
  }, [isGuest])

  // 게스트 모드 활성화 (수동으로 게스트 모드로 전환할 때 사용)
  const enableGuestMode = () => {
    // 로그아웃을 통해 게스트 모드로 전환
    // 이 함수는 필요시에만 사용
  }

  // 게스트 모드 비활성화 (수동으로 게스트 모드를 비활성화할 때 사용)
  const disableGuestMode = () => {
    // 로그인을 통해 게스트 모드를 비활성화
    // 이 함수는 필요시에만 사용
  }

  // 게스트 주문 데이터 저장
  const saveGuestOrder = (orderData) => {
    const newOrders = [...guestData.tempOrders, orderData]
    setGuestData(prev => ({
      ...prev,
      tempOrders: newOrders
    }))
    localStorage.setItem('guest_temp_orders', JSON.stringify(newOrders))
  }

  // 게스트 장바구니 데이터 저장
  const saveGuestCartItem = (cartItem) => {
    const newCart = [...guestData.tempCart, cartItem]
    setGuestData(prev => ({
      ...prev,
      tempCart: newCart
    }))
    localStorage.setItem('guest_temp_cart', JSON.stringify(newCart))
  }

  // 게스트 데이터 초기화
  const clearGuestData = () => {
    setGuestData({
      guestId: null,
      tempOrders: [],
      tempCart: []
    })
    localStorage.removeItem('guest_id')
    localStorage.removeItem('guest_temp_orders')
    localStorage.removeItem('guest_temp_cart')
  }

  const value = {
    isGuest,
    guestData,
    enableGuestMode,
    disableGuestMode,
    saveGuestOrder,
    saveGuestCartItem,
    clearGuestData
  }

  return (
    <GuestContext.Provider value={value}>
      {children}
    </GuestContext.Provider>
  )
}

export default GuestContext
