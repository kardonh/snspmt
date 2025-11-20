// Supabase 클라이언트 설정
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Missing Supabase environment variables')
}

// 환경 변수 확인 및 디버깅
if (!supabaseUrl) {
  console.error('❌ VITE_SUPABASE_URL이 설정되지 않았습니다.')
  console.error('현재 import.meta.env:', import.meta.env)
}
if (!supabaseAnonKey) {
  console.error('❌ VITE_SUPABASE_ANON_KEY가 설정되지 않았습니다.')
  console.error('현재 import.meta.env:', import.meta.env)
}

console.log('✅ Supabase 클라이언트 초기화:', {
  url: supabaseUrl || 'NOT SET',
  key: supabaseAnonKey ? `${supabaseAnonKey.substring(0, 20)}...` : 'NOT SET',
  hasUrl: !!supabaseUrl,
  hasKey: !!supabaseAnonKey
})

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true
  }
})

