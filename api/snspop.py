import requests
import json
from ._utils import SNSPOP_API_URL, API_KEY, save_order_to_db, set_cors_headers

def handler(request):
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
        
        # snspop API로 요청 전달
        headers = {
            'Authorization': f'Bearer {API_KEY}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(
            f'{SNSPOP_API_URL}/add',
            json=request_data,
            headers=headers
        )
        
        if response.status_code == 200:
            snspop_response = response.json()
            
            # 주문을 데이터베이스에 저장
            if save_order_to_db(request_data, snspop_response):
                print("✅ Order saved to database")
            else:
                print("❌ Failed to save order to database")
            
            return {
                'statusCode': 200,
                'headers': set_cors_headers(),
                'body': json.dumps(snspop_response)
            }
        else:
            return {
                'statusCode': response.status_code,
                'headers': set_cors_headers(),
                'body': json.dumps({
                    'error': 'snspop API request failed',
                    'details': response.text
                })
            }
            
    except Exception as e:
        print(f"❌ Error in snspop proxy: {e}")
        return {
            'statusCode': 500,
            'headers': set_cors_headers(),
            'body': json.dumps({
                'error': 'Internal server error',
                'details': str(e)
            })
        }
