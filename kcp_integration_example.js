// KCP 간편결제 연동 예시 코드

// 1. 포인트 구매 요청
async function purchasePointsWithKcp(userId, amount, price) {
  try {
    const response = await fetch('/api/points/purchase-kcp', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        user_id: userId,
        amount: amount,
        price: price
      })
    });
    
    const data = await response.json();
    
    if (data.success) {
      // KCP 결제 페이지로 리다이렉트
      const kcpData = data.kcp_data;
      const kcpUrl = data.kcp_url;
      
      // KCP 결제 폼 생성 및 제출
      const form = document.createElement('form');
      form.method = 'POST';
      form.action = kcpUrl;
      form.target = '_blank';
      
      Object.keys(kcpData).forEach(key => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = key;
        input.value = kcpData[key];
        form.appendChild(input);
      });
      
      document.body.appendChild(form);
      form.submit();
      document.body.removeChild(form);
      
      return data;
    } else {
      throw new Error(data.error);
    }
  } catch (error) {
    console.error('KCP 포인트 구매 실패:', error);
    throw error;
  }
}

// 2. KCP 결제 완료 후 콜백 처리
async function handleKcpCallback(ordrNo, status, transactionId) {
  try {
    const response = await fetch('/api/points/purchase-kcp/callback', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        ordr_no: ordrNo,
        status: status,
        transaction_id: transactionId
      })
    });
    
    const data = await response.json();
    
    if (data.success) {
      console.log('결제 상태 업데이트 완료');
      // 포인트 잔액 새로고침 등 추가 처리
      return true;
    } else {
      throw new Error(data.error);
    }
  } catch (error) {
    console.error('KCP 콜백 처리 실패:', error);
    throw error;
  }
}

// 3. 사용 예시
document.addEventListener('DOMContentLoaded', function() {
  const purchaseButton = document.getElementById('purchase-button');
  
  if (purchaseButton) {
    purchaseButton.addEventListener('click', async function() {
      const userId = 'current_user_id';
      const amount = 10000; // 10,000 포인트
      const price = 10000;  // 10,000원
      
      try {
        await purchasePointsWithKcp(userId, amount, price);
      } catch (error) {
        alert('포인트 구매에 실패했습니다: ' + error.message);
      }
    });
  }
});

// 4. KCP 결제 완료 페이지에서 호출
// (KCP에서 결제 완료 후 리다이렉트되는 페이지)
if (window.location.search.includes('ordr_no=')) {
  const urlParams = new URLSearchParams(window.location.search);
  const ordrNo = urlParams.get('ordr_no');
  const status = urlParams.get('status') || 'success';
  
  handleKcpCallback(ordrNo, status, null)
    .then(() => {
      alert('포인트 구매가 완료되었습니다!');
      // 포인트 잔액 새로고침
      window.location.reload();
    })
    .catch(error => {
      alert('결제 처리 중 오류가 발생했습니다: ' + error.message);
    });
}
