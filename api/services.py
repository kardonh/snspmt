import json
from ._utils import set_cors_headers
from .smmkings import SMMKingsAPI

def handler(request):
    """서비스 목록 조회 핸들러"""
    # CORS preflight 요청 처리
    if request.method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': set_cors_headers(),
            'body': ''
        }
    
    if request.method != 'GET':
        return {
            'statusCode': 405,
            'headers': set_cors_headers(),
            'body': json.dumps({'error': 'Method not allowed'})
        }
    
    try:
        # SMM KINGS API 인스턴스 생성
        api = SMMKingsAPI()
        
        # 서비스 목록 조회
        services_response = api.get_services()
        
        if services_response:
            return {
                'statusCode': 200,
                'headers': set_cors_headers(),
                'body': json.dumps(services_response)
            }
        else:
            return {
                'statusCode': 400,
                'headers': set_cors_headers(),
                'body': json.dumps({
                    'error': 'Failed to fetch services from SMM KINGS API'
                })
            }
            
    except Exception as e:
        print(f"❌ Error fetching services: {e}")
        return {
            'statusCode': 500,
            'headers': set_cors_headers(),
            'body': json.dumps({
                'error': 'Internal server error',
                'details': str(e)
            })
        }
