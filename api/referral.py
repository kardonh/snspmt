import json
from ._utils import generate_referral_code, process_referral_code, set_cors_headers

def generate_referral(request):
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
        user_id = request_data.get('user_id')
        user_email = request_data.get('user_email')
        
        if not user_id or not user_email:
            return {
                'statusCode': 400,
                'headers': set_cors_headers(),
                'body': json.dumps({'error': 'user_id and user_email are required'})
            }
        
        # 추천인 코드 생성
        referral_code = generate_referral_code(user_id, user_email)
        
        if referral_code:
            return {
                'statusCode': 200,
                'headers': set_cors_headers(),
                'body': json.dumps({
                    'referral_code': referral_code,
                    'message': 'Referral code generated successfully'
                })
            }
        else:
            return {
                'statusCode': 500,
                'headers': set_cors_headers(),
                'body': json.dumps({'error': 'Failed to generate referral code'})
            }
            
    except Exception as e:
        print(f"❌ Error generating referral code: {e}")
        return {
            'statusCode': 500,
            'headers': set_cors_headers(),
            'body': json.dumps({
                'error': 'Internal server error',
                'details': str(e)
            })
        }

def use_referral(request):
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
        referral_code = request_data.get('referral_code')
        new_user_id = request_data.get('user_id')
        new_user_email = request_data.get('user_email')
        
        if not referral_code or not new_user_id or not new_user_email:
            return {
                'statusCode': 400,
                'headers': set_cors_headers(),
                'body': json.dumps({'error': 'referral_code, user_id, and user_email are required'})
            }
        
        # 추천인 코드 처리
        success, message = process_referral_code(referral_code, new_user_id, new_user_email)
        
        if success:
            return {
                'statusCode': 200,
                'headers': set_cors_headers(),
                'body': json.dumps({
                    'message': message,
                    'referral_code': referral_code
                })
            }
        else:
            return {
                'statusCode': 400,
                'headers': set_cors_headers(),
                'body': json.dumps({'error': message})
            }
            
    except Exception as e:
        print(f"❌ Error using referral code: {e}")
        return {
            'statusCode': 500,
            'headers': set_cors_headers(),
            'body': json.dumps({
                'error': 'Internal server error',
                'details': str(e)
            })
        }

def get_user_referral_code(request, user_email):
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
        if not user_email:
            return {
                'statusCode': 400,
                'headers': set_cors_headers(),
                'body': json.dumps({'error': 'user_email parameter is required'})
            }
        
        # 사용자의 추천인 코드 조회
        referral_code = generate_referral_code(user_email, user_email)
        
        if referral_code:
            return {
                'statusCode': 200,
                'headers': set_cors_headers(),
                'body': json.dumps({
                    'referral_code': referral_code,
                    'user_email': user_email
                })
            }
        else:
            return {
                'statusCode': 404,
                'headers': set_cors_headers(),
                'body': json.dumps({'error': 'Referral code not found'})
            }
            
    except Exception as e:
        print(f"❌ Error getting user referral code: {e}")
        return {
            'statusCode': 500,
            'headers': set_cors_headers(),
            'body': json.dumps({
                'error': 'Internal server error',
                'details': str(e)
            })
        }
