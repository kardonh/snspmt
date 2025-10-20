// KCP 표준결제 연동 완전 예시 코드

// 1. 거래등록 (Mobile)
async function registerKcpTransaction(userId, amount, price, payMethod = 'CARD') {
  try {
    const response = await fetch('/api/points/purchase-kcp/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        user_id: userId,
        amount: amount,
        price: price,
        good_name: '포인트 구매',
        pay_method: payMethod  // CARD, BANK, MOBX, TPNT, GIFT
      })
    });
    
    const data = await response.json();
    
    if (data.success) {
      console.log('✅ KCP 거래등록 성공:', data);
      return data;
    } else {
      throw new Error(data.error);
    }
  } catch (error) {
    console.error('❌ KCP 거래등록 실패:', error);
    throw error;
  }
}

// 2. 결제창 호출 데이터 생성
async function createPaymentForm(ordrIdxx, kcpResponse) {
  try {
    const response = await fetch('/api/points/purchase-kcp/payment-form', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        ordr_idxx: ordrIdxx,
        approval_key: kcpResponse.approvalKey,
        pay_url: kcpResponse.PayUrl,
        pay_method: 'CARD',
        good_mny: kcpResponse.good_mny,
        buyr_name: '홍길동',
        buyr_mail: 'test@example.com',
        buyr_tel2: '010-1234-5678',
        shop_user_id: 'user123'
      })
    });
    
    const data = await response.json();
    
    if (data.success) {
      console.log('✅ 결제창 호출 데이터 생성 성공:', data);
      return data.payment_form_data;
    } else {
      throw new Error(data.error);
    }
  } catch (error) {
    console.error('❌ 결제창 데이터 생성 실패:', error);
    throw error;
  }
}

// 3. KCP 결제창 호출 (Mobile)
function callKcpPaymentForm(paymentFormData) {
  // 결제창 호출을 위한 폼 생성
  const form = document.createElement('form');
  form.method = 'POST';
  form.action = paymentFormData.PayUrl.substring(0, paymentFormData.PayUrl.lastIndexOf("/")) + "/jsp/encodingFilter/encodingFilter.jsp";
  form.target = '_blank';
  
  // 폼 데이터 추가
  Object.keys(paymentFormData).forEach(key => {
    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = key;
    input.value = paymentFormData[key];
    form.appendChild(input);
  });
  
  document.body.appendChild(form);
  form.submit();
  document.body.removeChild(form);
}

// 4. KCP 결제창 호출 (PC)
function callKcpPaymentFormPC(paymentFormData) {
  // PC용 KCP 스크립트 로드
  const script = document.createElement('script');
  script.src = 'https://testspay.kcp.co.kr/plugin/kcp_spay_hub.js';
  script.onload = function() {
    // KCP_Pay_Execute_Web 함수 호출
    if (typeof KCP_Pay_Execute_Web === 'function') {
      try {
        KCP_Pay_Execute_Web(paymentFormData);
      } catch (e) {
        console.log('KCP 결제창 정상 종료');
      }
    }
  };
  document.head.appendChild(script);
}

// 5. 결제요청 (승인)
async function approveKcpPayment(ordrIdxx, encData, encInfo, tranCd) {
  try {
    const response = await fetch('/api/points/purchase-kcp/approve', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        ordr_idxx: ordrIdxx,
        enc_data: encData,
        enc_info: encInfo,
        tran_cd: tranCd
      })
    });
    
    const data = await response.json();
    
    if (data.success) {
      console.log('✅ KCP 결제 승인 성공:', data);
      return data;
    } else {
      throw new Error(data.error);
    }
  } catch (error) {
    console.error('❌ KCP 결제 승인 실패:', error);
    throw error;
  }
}

// 6. 완전한 결제 플로우 (Mobile)
async function completeKcpPaymentFlow(userId, amount, price, payMethod = 'CARD') {
  try {
    // 1단계: 거래등록
    console.log('1단계: KCP 거래등록 시작');
    const registerResult = await registerKcpTransaction(userId, amount, price, payMethod);
    
    // 2단계: 결제창 호출 데이터 생성
    console.log('2단계: 결제창 호출 데이터 생성');
    const paymentFormData = await createPaymentForm(registerResult.ordr_idxx, registerResult.kcp_response);
    
    // 3단계: 결제창 호출
    console.log('3단계: KCP 결제창 호출');
    callKcpPaymentForm(paymentFormData);
    
    return {
      success: true,
      ordr_idxx: registerResult.ordr_idxx,
      message: '결제창이 호출되었습니다. 결제를 완료해주세요.'
    };
    
  } catch (error) {
    console.error('❌ KCP 결제 플로우 실패:', error);
    return {
      success: false,
      error: error.message
    };
  }
}

// 7. 결제창 인증결과 처리 (Ret_URL에서 호출)
async function handleKcpPaymentReturn() {
  try {
    // URL 파라미터에서 인증결과 데이터 추출
    const urlParams = new URLSearchParams(window.location.search);
    const encData = urlParams.get('enc_data');
    const encInfo = urlParams.get('enc_info');
    const tranCd = urlParams.get('tran_cd');
    const ordrIdxx = urlParams.get('ordr_idxx');
    const resCd = urlParams.get('res_cd');
    const resMsg = urlParams.get('res_msg');
    
    console.log('🔍 KCP 결제창 인증결과:', { ordrIdxx, resCd, resMsg });
    
    if (resCd === '0000' && encData && encInfo) {
      // 인증 성공 - 결제요청 진행
      console.log('4단계: KCP 결제요청 (승인) 시작');
      const approveResult = await approveKcpPayment(ordrIdxx, encData, encInfo, tranCd);
      
      if (approveResult.success) {
        alert(`포인트 구매가 완료되었습니다! (${approveResult.amount}포인트)`);
        // 포인트 잔액 새로고침
        window.location.href = '/orders';
      } else {
        alert('결제에 실패했습니다: ' + approveResult.error);
      }
    } else {
      alert('인증에 실패했습니다: ' + resMsg);
    }
    
  } catch (error) {
    console.error('❌ KCP 결제 인증결과 처리 실패:', error);
    alert('결제 처리 중 오류가 발생했습니다.');
  }
}

// 8. 사용 예시
document.addEventListener('DOMContentLoaded', function() {
  // 결제 버튼 이벤트
  const paymentButton = document.getElementById('kcp-payment-button');
  
  if (paymentButton) {
    paymentButton.addEventListener('click', async function() {
      const userId = 'current_user_id';
      const amount = 10000; // 10,000 포인트
      const price = 10000;  // 10,000원
      const payMethod = 'CARD'; // 신용카드
      
      try {
        const result = await completeKcpPaymentFlow(userId, amount, price, payMethod);
        
        if (result.success) {
          console.log('결제창 호출 완료:', result.message);
        } else {
          alert('결제 시작에 실패했습니다: ' + result.error);
        }
      } catch (error) {
        alert('결제 처리 중 오류가 발생했습니다: ' + error.message);
      }
    });
  }
  
  // 결제 완료 페이지에서 인증결과 처리
  if (window.location.pathname.includes('/payment/return')) {
    handleKcpPaymentReturn();
  }
});

// 9. 환경 변수 설정 예시
/*
KCP_SITE_CD=ALFCQ
KCP_SITE_KEY=2Lu3CSvPPLnuE34LaRWJR24__4
KCP_CERT_INFO=-----BEGIN CERTIFICATE-----MIIDgTCCAmmgAwIBAgIHkiG9w0...-----END CERTIFICATE-----
KCP_ENCRYPT_KEY=your_encrypt_key_here
*/

// 10. HTML 폼 예시 (결제창 호출용)
function createPaymentFormHTML(paymentFormData) {
  return `
    <form name="order_info" method="post" action="${paymentFormData.PayUrl.substring(0, paymentFormData.PayUrl.lastIndexOf("/"))}/jsp/encodingFilter/encodingFilter.jsp">
      <input type="hidden" name="site_cd" value="${paymentFormData.site_cd}">
      <input type="hidden" name="pay_method" value="${paymentFormData.pay_method}">
      <input type="hidden" name="currency" value="${paymentFormData.currency}">
      <input type="hidden" name="shop_name" value="${paymentFormData.shop_name}">
      <input type="hidden" name="Ret_URL" value="${paymentFormData.Ret_URL}">
      <input type="hidden" name="approval_key" value="${paymentFormData.approval_key}">
      <input type="hidden" name="PayUrl" value="${paymentFormData.PayUrl}">
      <input type="hidden" name="ordr_idxx" value="${paymentFormData.ordr_idxx}">
      <input type="hidden" name="good_name" value="${paymentFormData.good_name}">
      <input type="hidden" name="good_cd" value="${paymentFormData.good_cd}">
      <input type="hidden" name="good_mny" value="${paymentFormData.good_mny}">
      <input type="hidden" name="buyr_name" value="${paymentFormData.buyr_name}">
      <input type="hidden" name="buyr_mail" value="${paymentFormData.buyr_mail}">
      <input type="hidden" name="buyr_tel2" value="${paymentFormData.buyr_tel2}">
      <input type="hidden" name="shop_user_id" value="${paymentFormData.shop_user_id}">
      <input type="hidden" name="van_code" value="${paymentFormData.van_code}">
    </form>
  `;
}
