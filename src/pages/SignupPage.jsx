import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import { useReferralCode } from '../services/snspopApi';
import './SignupPage.css';
import { auth } from '../firebase/config';

export default function SignupPage() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [referralCode, setReferralCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { signup } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    
    if (password !== confirmPassword) {
      setError('비밀번호가 일치하지 않습니다.');
      return;
    }
    
    try {
      setError('');
      setLoading(true);
      
      // 회원가입
      const userCredential = await signup(email, password, username);
      
      // Firebase Auth에서 사용자 정보 가져오기
      const user = auth.currentUser;
      if (!user) {
        throw new Error('사용자 정보를 가져올 수 없습니다.');
      }
      
      // 추천인 코드가 있는 경우 처리
      if (referralCode.trim()) {
        try {
          await useReferralCode(
            referralCode.trim(),
            user.uid,
            user.email
          );
          // 추천인 코드 성공 메시지 표시
          alert('추천인 코드가 성공적으로 적용되었습니다! 5% 할인 쿠폰이 지급되었습니다.');
        } catch (referralError) {
          console.error('추천인 코드 처리 오류:', referralError);
          // 추천인 코드 실패해도 회원가입은 성공
          alert('회원가입은 완료되었지만, 추천인 코드 처리에 실패했습니다.');
        }
      }
      
      // 사용자 고유 추천인 코드 자동 생성
      try {
        const response = await fetch('/api/referral/generate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            user_id: user.uid,
            user_email: user.email
          })
        });
        
        if (response.ok) {
          const data = await response.json();
          if (data.success) {
            console.log('사용자 고유 추천인 코드가 생성되었습니다:', data.referral_code);
            alert(`회원가입이 완료되었습니다! 당신의 추천인 코드는 ${data.referral_code}입니다.`);
          } else {
            console.error('추천인 코드 생성 실패:', data.error);
          }
        } else {
          console.error('추천인 코드 생성 API 호출 실패');
        }
      } catch (codeError) {
        console.error('추천인 코드 생성 중 오류:', codeError);
      }
      
      navigate('/');
    } catch (error) {
      if (error.code === 'auth/email-already-in-use') {
        setError('이미 사용 중인 이메일입니다.');
      } else {
        setError('회원가입에 실패했습니다. 다시 시도해주세요.');
      }
    }
    setLoading(false);
  }

  return (
    <div className="signup-container">
      <div className="signup-card">
        <h2>회원가입</h2>
        {error && <div className="error-message">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="username">사용자명</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="email">이메일</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="password">비밀번호</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="confirmPassword">비밀번호 확인</label>
            <input
              type="password"
              id="confirmPassword"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="referralCode">
              추천인 코드 <span className="optional">(선택사항)</span>
            </label>
            <input
              type="text"
              id="referralCode"
              value={referralCode}
              onChange={(e) => setReferralCode(e.target.value.toUpperCase())}
              placeholder="추천인 코드를 입력하세요"
              maxLength={8}
            />
            <small className="help-text">
              추천인 코드를 입력하면 5% 할인 쿠폰을 받을 수 있습니다!
            </small>
          </div>
          <button disabled={loading} type="submit" className="signup-button">
            {loading ? '가입 중...' : '회원가입'}
          </button>
        </form>
        <div className="login-link">
          이미 계정이 있으신가요? <Link to="/login">로그인</Link>
        </div>
      </div>
    </div>
  );
}
