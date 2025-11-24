// Supabase 클라이언트 설정
import { createClient } from '@supabase/supabase-js'

// 환경 변수에서 Supabase 설정 읽기
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

// 환경 변수 확인 및 디버깅
console.log('🔍 Supabase 환경 변수 확인:', {
  'import.meta.env': import.meta.env,
  'VITE_SUPABASE_URL': supabaseUrl || 'NOT SET',
  'VITE_SUPABASE_ANON_KEY': supabaseAnonKey ? `${supabaseAnonKey.substring(0, 20)}...` : 'NOT SET',
  'hasUrl': !!supabaseUrl,
  'hasKey': !!supabaseAnonKey
})

if (!supabaseUrl || !supabaseAnonKey) {
  const errorMsg = `Supabase 환경 변수가 설정되지 않았습니다. 
VITE_SUPABASE_URL: ${supabaseUrl ? '✅' : '❌'}
VITE_SUPABASE_ANON_KEY: ${supabaseAnonKey ? '✅' : '❌'}
.env.local 파일을 확인하고 프론트엔드 서버를 재시작하세요.`
  console.error('❌', errorMsg)
  throw new Error(errorMsg)
}

console.log('✅ Supabase 클라이언트 초기화:', {
  url: supabaseUrl || 'NOT SET',
  key: supabaseAnonKey ? `${supabaseAnonKey.substring(0, 20)}...` : 'NOT SET',
  hasUrl: !!supabaseUrl,
  hasKey: !!supabaseAnonKey
})

// 원래 기본 설정으로 복원 - Supabase SDK의 기본 동작 사용
// 커스텀 fetch를 제거하면 Supabase가 자동으로 CORS를 처리합니다
export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true
  }
})

