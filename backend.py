from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import json
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)  # 모든 origin에서의 요청 허용

# snspop API 설정
SNSPOP_API_URL = 'https://snspop.com/api/v2'
API_KEY = '88a588af6f79647ac863be81835f3472'

# 주문 데이터 저장소 (실제 프로덕션에서는 데이터베이스 사용)
orders_db = {}

@app.route('/api', methods=['POST'])
def proxy_api():
    try:
        # 클라이언트로부터 받은 데이터
        data = request.get_json()
        
        # API 키 추가
        data['key'] = API_KEY
        
        # snspop API로 요청 전달
        response = requests.post(SNSPOP_API_URL, json=data, timeout=30)
        
        # 주문 생성인 경우 로컬에 저장
        if data.get('action') == 'add' and response.status_code == 200:
            response_data = response.json()
            if response_data.get('order'):
                order_id = response_data['order']
                user_id = request.headers.get('X-User-ID', 'anonymous')
                
                if user_id not in orders_db:
                    orders_db[user_id] = []
                
                order_info = {
                    'id': order_id,
                    'service': data.get('service'),
                    'link': data.get('link'),
                    'quantity': data.get('quantity'),
                    'status': 'pending',
                    'created_at': datetime.now().isoformat(),
                    'user_id': user_id
                }
                orders_db[user_id].append(order_info)
        
        # 응답 반환
        return jsonify(response.json()), response.status_code
        
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'API 요청 실패: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'서버 오류: {str(e)}'}), 500

@app.route('/api/orders', methods=['GET'])
def get_user_orders():
    """사용자별 주문 정보 조회"""
    try:
        user_id = request.args.get('user_id', 'anonymous')
        
        if user_id not in orders_db:
            return jsonify({'orders': []}), 200
        
        # 주문 상태 업데이트 (snspop API에서 최신 상태 조회)
        for order in orders_db[user_id]:
            try:
                status_response = requests.post(SNSPOP_API_URL, json={
                    'key': API_KEY,
                    'action': 'status',
                    'order': order['id']
                }, timeout=10)
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    if 'status' in status_data:
                        order['status'] = status_data['status']
                    if 'start_count' in status_data:
                        order['start_count'] = status_data['start_count']
                    if 'remains' in status_data:
                        order['remains'] = status_data['remains']
            except:
                pass  # 상태 조회 실패 시 기존 상태 유지
        
        return jsonify({'orders': orders_db[user_id]}), 200
        
    except Exception as e:
        return jsonify({'error': f'주문 조회 실패: {str(e)}'}), 500

@app.route('/api/orders/<order_id>', methods=['GET'])
def get_order_detail(order_id):
    """특정 주문 상세 정보 조회"""
    try:
        user_id = request.args.get('user_id', 'anonymous')
        
        if user_id not in orders_db:
            return jsonify({'error': '주문을 찾을 수 없습니다.'}), 404
        
        order = next((o for o in orders_db[user_id] if o['id'] == order_id), None)
        
        if not order:
            return jsonify({'error': '주문을 찾을 수 없습니다.'}), 404
        
        # snspop API에서 최신 상태 조회
        try:
            status_response = requests.post(SNSPOP_API_URL, json={
                'key': API_KEY,
                'action': 'status',
                'order': order_id
            }, timeout=10)
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                order.update(status_data)
        except:
            pass
        
        return jsonify(order), 200
        
    except Exception as e:
        return jsonify({'error': f'주문 상세 조회 실패: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'message': 'Backend server is running'})

# 프론트엔드 정적 파일 서빙
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """프론트엔드 정적 파일 서빙"""
    if path and os.path.exists(os.path.join('dist', path)):
        return send_from_directory('dist', path)
    else:
        return send_from_directory('dist', 'index.html')

if __name__ == '__main__':
    print("🚀 Backend server starting on http://localhost:8000")
    print("📡 Proxying requests to snspop API...")
    print("💾 Local order storage enabled...")
    print("🌐 Serving frontend from dist/ directory...")
    app.run(host='0.0.0.0', port=8000, debug=True)
