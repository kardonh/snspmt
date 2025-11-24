import axios from 'axios'
import { setupCache } from 'axios-cache-interceptor'
import { supabase } from '../supabase/client'

const VITE_API_BASE_URL = import.meta.env.VITE_API_BASE_URL

// Create axios instance
const axiosInstance = axios.create({
  baseURL: VITE_API_BASE_URL
})

// Token cache to avoid repeated localStorage scans
let tokenCache = {
  token: null,
  email: null,
  timestamp: 0,
  ttl: 5 * 60 * 1000 // 5 minutes cache
}

// Comprehensive token fetching (only runs when cache is invalid)
async function getAdminToken() {
  const now = Date.now()
  
  // Return cached token if still valid
  if (tokenCache.token && tokenCache.timestamp && (now - tokenCache.timestamp) < tokenCache.ttl) {
    return {
      token: tokenCache.token,
      email: tokenCache.email
    }
  }
  
  console.log(`🔍 토큰 캐시 만료 또는 없음. 새로 가져옵니다...`)
  
  let accessToken = null
  let userEmail = localStorage.getItem('userEmail')
  
  // 방법 1: Supabase 세션에서 가져오기 (빠른 타임아웃)
  try {
    const sessionPromise = supabase.auth.getSession()
    const timeoutPromise = new Promise((_, reject) => {
      setTimeout(() => reject(new Error('타임아웃')), 2000) // 2초로 단축
    })
    const session = await Promise.race([sessionPromise, timeoutPromise])
    accessToken = session.data?.session?.access_token
    if (accessToken) {
      console.log(`🔑 토큰 획득 (Supabase 세션)`)
    }
  } catch (tokenError) {
    // 조용히 실패, 다음 방법 시도
  }
  
  // 방법 2: 빠른 localStorage 체크 (우선순위 키만)
  if (!accessToken) {
    const priorityKeys = ['supabase_access_token', 'sb-access-token']
    for (const key of priorityKeys) {
      const stored = localStorage.getItem(key)
      if (stored && stored.startsWith('eyJ')) {
        accessToken = stored
        console.log(`🔑 토큰 획득 (localStorage: ${key})`)
        break
      }
    }
  }
  
  // 방법 3: 전체 localStorage 스캔 (마지막 수단)
  if (!accessToken) {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)
      if (key && (key.includes('supabase') || key.includes('auth') || key.includes('token'))) {
        const stored = localStorage.getItem(key)
        if (stored) {
          try {
            const parsed = JSON.parse(stored)
            if (parsed && parsed.access_token) {
              accessToken = parsed.access_token
              console.log(`🔑 토큰 획득 (localStorage 스캔: ${key})`)
              break
            }
          } catch (e) {
            if (stored.startsWith('eyJ')) {
              accessToken = stored
              console.log(`🔑 토큰 획득 (localStorage 스캔: ${key}, raw)`)
              break
            }
          }
        }
      }
    }
  }
  
  // Cache the result
  tokenCache = {
    token: accessToken,
    email: userEmail,
    timestamp: now
  }
  
  return { token: accessToken, email: userEmail }
}

// Clear token cache (call this on logout or auth errors)
export function clearTokenCache() {
  tokenCache = { token: null, email: null, timestamp: 0, ttl: 5 * 60 * 1000 }
  console.log('🗑️ 토큰 캐시 삭제됨')
}

// Add auth headers interceptor (admin endpoints only)
axiosInstance.interceptors.request.use(
  async (config) => {
    const url = config.url || ''
    const isAdminEndpoint = url.includes('/admin/')
    
    if (isAdminEndpoint) {
      // Get token from cache or fetch new one
      const { token, email } = await getAdminToken()
      
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
      if (email) {
        config.headers['X-User-Email'] = email
      }
    }
    // Non-admin endpoints: no headers needed
    
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor for error handling
axiosInstance.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    // Clear cache on 401/403 errors to force token refresh
    if (error.response?.status === 401 || error.response?.status === 403) {
      console.warn('⚠️ 인증 오류 감지. 토큰 캐시를 삭제합니다.')
      clearTokenCache()
    }
    
    if (error.config?.url?.includes('/admin/')) {
      console.error(`❌ Admin API 오류 (${error.config.url}):`, error.response?.status, error.message)
    }
    
    return Promise.reject(error)
  }
)

// Setup cache with 5-minute TTL
const cachedAxios = setupCache(axiosInstance, {
  ttl: 5 * 60 * 1000, // 5 minutes
  interpretHeader: false,
  methods: ['get'],
  cachePredicate: {
    statusCheck: (status) => status >= 200 && status < 300
  }
})

export default cachedAxios

