from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import json
from datetime import datetime, timedelta
import os
import sqlite3

app = Flask(__name__)
CORS(app)  # 모든 origin에서의 요청 허용

# snspop API 설정
SNSPOP_API_URL = 'https://snspop.com/api/v2'
API_KEY = '5fccf26387249db082e60791afd7c358'

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

@app.route('/api/services', methods=['GET'])
def get_snspop_services():
    """snspop API에서 실제 서비스 목록 조회"""
    try:
        response = requests.post(SNSPOP_API_URL, json={
            'key': API_KEY,
            'action': 'services'
        }, timeout=30)
        
        if response.status_code == 200:
            services_data = response.json()
            print(f"Snspop API Services Response: {services_data}")  # 디버깅용
            return jsonify(services_data), 200
        else:
            return jsonify({'error': f'Snspop API 오류: {response.status_code}'}), response.status_code
            
    except Exception as e:
        return jsonify({'error': f'서비스 조회 실패: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'message': 'Backend server is running'})

# 관리자 API 엔드포인트
def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), 'orders.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/api/admin/stats', methods=['GET'])
def get_admin_stats():
    """관리자 통계 데이터 제공"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 현재 날짜와 한 달 전 날짜 계산
        now = datetime.now()
        one_month_ago = now - timedelta(days=30)
        
        # 총 가입자 수 (Firebase Auth 사용자 수는 별도로 관리 필요)
        cursor.execute("SELECT COUNT(DISTINCT user_id) as total_users FROM orders")
        total_users = cursor.fetchone()['total_users']
        
        # 한 달 가입자 수
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id) as monthly_users 
            FROM orders 
            WHERE created_at >= ?
        """, (one_month_ago.strftime('%Y-%m-%d'),))
        monthly_users = cursor.fetchone()['monthly_users']
        
        # 총 매출액
        cursor.execute("SELECT SUM(total_amount) as total_revenue FROM orders WHERE status = 'completed'")
        total_revenue = cursor.fetchone()['total_revenue'] or 0
        
        # 한 달 매출액
        cursor.execute("""
            SELECT SUM(total_amount) as monthly_revenue 
            FROM orders 
            WHERE status = 'completed' AND created_at >= ?
        """, (one_month_ago.strftime('%Y-%m-%d'),))
        monthly_revenue = cursor.fetchone()['monthly_revenue'] or 0
        
        # 총 SMM KINGS 충전액 (실제 비용)
        cursor.execute("SELECT SUM(smmkings_cost) as total_smmkings_charge FROM orders WHERE status = 'completed'")
        total_smmkings_charge = cursor.fetchone()['total_smmkings_charge'] or 0
        
        # 한 달 SMM KINGS 충전액
        cursor.execute("""
            SELECT SUM(smmkings_cost) as monthly_smmkings_charge 
            FROM orders 
            WHERE status = 'completed' AND created_at >= ?
        """, (one_month_ago.strftime('%Y-%m-%d'),))
        monthly_smmkings_charge = cursor.fetchone()['monthly_smmkings_charge'] or 0
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'totalUsers': total_users,
                'monthlyUsers': monthly_users,
                'totalRevenue': total_revenue,
                'monthlyRevenue': monthly_revenue,
                'totalSMMKingsCharge': total_smmkings_charge,
                'monthlySMMKingsCharge': monthly_smmkings_charge
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/transactions', methods=['GET'])
def get_admin_transactions():
    """충전 및 환불 내역 제공"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 충전 내역 (완료된 주문)
        cursor.execute("""
            SELECT 
                id,
                user_id as user,
                total_amount as amount,
                created_at as date,
                status
            FROM orders 
            WHERE status = 'completed'
            ORDER BY created_at DESC
            LIMIT 20
        """)
        charges = []
        for row in cursor.fetchall():
            charges.append({
                'id': row['id'],
                'user': row['user'],
                'amount': row['amount'],
                'date': row['date'],
                'status': row['status']
            })
        
        # 환불 내역 (취소된 주문)
        cursor.execute("""
            SELECT 
                id,
                user_id as user,
                total_amount as amount,
                created_at as date,
                '고객 요청' as reason
            FROM orders 
            WHERE status = 'cancelled'
            ORDER BY created_at DESC
            LIMIT 20
        """)
        refunds = []
        for row in cursor.fetchall():
            refunds.append({
                'id': row['id'],
                'user': row['user'],
                'amount': row['amount'],
                'date': row['date'],
                'reason': row['reason']
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'charges': charges,
                'refunds': refunds
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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
    # Render 환경에서 포트 설정
    port = int(os.environ.get('PORT', 8000))
    
    print(f"🚀 Backend server starting on port {port}")
    print("📡 Proxying requests to snspop API...")
    print("💾 Local order storage enabled...")
    print("🌐 Serving frontend from dist/ directory...")
    
    # 프로덕션 환경에서는 debug=False
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
