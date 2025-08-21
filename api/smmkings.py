import requests
import json
from ._utils import SMMKINGS_API_URL, API_KEY, save_order_to_db, set_cors_headers

class SMMKingsAPI:
    def __init__(self, api_key=None):
        self.api_url = SMMKINGS_API_URL
        self.api_key = api_key or API_KEY
    
    def _connect(self, post_data):
        """API 연결 및 요청 처리"""
        try:
            # POST 데이터 준비
            if isinstance(post_data, dict):
                post_data['key'] = self.api_key
                post_fields = '&'.join([f"{k}={requests.utils.quote(str(v))}" for k, v in post_data.items()])
            else:
                post_fields = post_data
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'Mozilla/4.0 (compatible; MSIE 5.01; Windows NT 5.0)'
            }
            
            response = requests.post(
                self.api_url,
                data=post_fields,
                headers=headers,
                timeout=30,
                verify=False  # SSL 검증 비활성화
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"API 요청 실패: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"API 연결 오류: {e}")
            return None
    
    def get_services(self):
        """서비스 목록 조회"""
        return self._connect({'action': 'services'})
    
    def get_balance(self):
        """잔액 조회"""
        return self._connect({'action': 'balance'})
    
    def add_order(self, order_data):
        """주문 추가"""
        order_data['action'] = 'add'
        return self._connect(order_data)
    
    def get_order_status(self, order_id):
        """주문 상태 조회"""
        return self._connect({
            'action': 'status',
            'order': order_id
        })
    
    def get_multi_status(self, order_ids):
        """여러 주문 상태 조회"""
        return self._connect({
            'action': 'status',
            'orders': ','.join(map(str, order_ids))
        })
    
    def refill_order(self, order_id):
        """주문 리필"""
        return self._connect({
            'action': 'refill',
            'order': order_id
        })
    
    def refill_orders(self, order_ids):
        """여러 주문 리필"""
        return self._connect({
            'action': 'refill',
            'orders': ','.join(map(str, order_ids))
        })
    
    def get_refill_status(self, refill_id):
        """리필 상태 조회"""
        return self._connect({
            'action': 'refill_status',
            'refill': refill_id
        })
    
    def get_multi_refill_status(self, refill_ids):
        """여러 리필 상태 조회"""
        return self._connect({
            'action': 'refill_status',
            'refills': ','.join(map(str, refill_ids))
        })
    
    def cancel_orders(self, order_ids):
        """주문 취소"""
        return self._connect({
            'action': 'cancel',
            'orders': ','.join(map(str, order_ids))
        })

def handler(request):
    """API 핸들러 함수"""
    # CORS preflight 요청 처리
    if request.method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': set_cors_headers(),
            'body': ''
        }
    
    if request.method != 'POST':
        return {
            'statusCode': 405,
            'headers': set_cors_headers(),
            'body': json.dumps({'error': 'Method not allowed'})
        }
    
    try:
        # 요청 데이터 파싱
        request_data = request.get_json()
        
        # SMM KINGS API 인스턴스 생성
        api = SMMKingsAPI()
        
        # 주문 데이터 준비
        order_data = {
            'service': request_data.get('service_id'),
            'link': request_data.get('link'),
            'quantity': request_data.get('quantity', 1)
        }
        
        # 추가 옵션들
        if request_data.get('comments'):
            order_data['comments'] = request_data['comments']
        
        if request_data.get('runs'):
            order_data['runs'] = request_data['runs']
        
        if request_data.get('interval'):
            order_data['interval'] = request_data['interval']
        
        if request_data.get('country'):
            order_data['country'] = request_data['country']
        
        if request_data.get('device'):
            order_data['device'] = request_data['device']
        
        if request_data.get('type_of_traffic'):
            order_data['type_of_traffic'] = request_data['type_of_traffic']
        
        if request_data.get('google_keyword'):
            order_data['google_keyword'] = request_data['google_keyword']
        
        # 주문 생성
        smmkings_response = api.add_order(order_data)
        
        if smmkings_response and smmkings_response.get('order'):
            # 주문을 데이터베이스에 저장
            if save_order_to_db(request_data, smmkings_response):
                print("✅ Order saved to database")
            else:
                print("❌ Failed to save order to database")
            
            return {
                'statusCode': 200,
                'headers': set_cors_headers(),
                'body': json.dumps(smmkings_response)
            }
        else:
            return {
                'statusCode': 400,
                'headers': set_cors_headers(),
                'body': json.dumps({
                    'error': 'SMM KINGS API request failed',
                    'details': smmkings_response or 'No response from API'
                })
            }
            
    except Exception as e:
        print(f"❌ Error in SMM KINGS proxy: {e}")
        return {
            'statusCode': 500,
            'headers': set_cors_headers(),
            'body': json.dumps({
                'error': 'Internal server error',
                'details': str(e)
            })
        }
