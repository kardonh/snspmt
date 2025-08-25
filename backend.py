from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import json
from datetime import datetime, timedelta
import os
import sqlite3
import csv
import io

app = Flask(__name__)
CORS(app)  # 모든 origin에서의 요청 허용

# smmpanel.kr API 설정
SMMPANEL_API_URL = 'https://smmpanel.kr/api/v2'
API_KEY = '9c86d44a161840eb7dfc7396fb1ecf94'

# 주문 데이터 저장소 (실제 프로덕션에서는 데이터베이스 사용)
orders_db = {}

# 포인트 관련 데이터베이스
points_db = {}  # 사용자별 포인트
purchases_db = {}  # 구매 신청 내역

# 사용자 관련 데이터베이스
users_db = {}  # 사용자 정보
user_sessions = {}  # 실시간 접속 사용자

@app.route('/api', methods=['POST'])
def proxy_api():
    try:
        # 클라이언트로부터 받은 데이터
        data = request.get_json()
        
        # API 키 추가
        data['key'] = API_KEY
        
        # smmpanel.kr API로 요청 전달
        response = requests.post(SMMPANEL_API_URL, json=data, timeout=30)
        
        # 주문 생성인 경우 로컬에 저장
        if data.get('action') == 'add' and response.status_code == 200:
            response_data = response.json()
            if response_data.get('order'):
                order_id = response_data['order']
                user_id = request.headers.get('X-User-ID', 'anonymous')
                
                # 디버깅용 로그
                print(f"주문 생성: order_id={order_id}, user_id={user_id}")
                print(f"주문 데이터: {data}")
                
                if user_id not in orders_db:
                    orders_db[user_id] = []
                
                # snspop API 지원 파라미터들 추가
                order_info = {
                    'id': order_id,
                    'service': data.get('service'),
                    'link': data.get('link'),
                    'quantity': data.get('quantity'),
                    'runs': data.get('runs', 1),
                    'interval': data.get('interval', 0),
                    'comments': data.get('comments', ''),
                    'username': data.get('username', ''),
                    'min': data.get('min', 0),
                    'max': data.get('max', 0),
                    'posts': data.get('posts', 0),
                    'delay': data.get('delay', 0),
                    'expiry': data.get('expiry', ''),
                    'old_posts': data.get('old_posts', 0),
                    'status': 'pending',
                    'created_at': datetime.now().isoformat(),
                    'user_id': user_id
                }
                orders_db[user_id].append(order_info)
                print(f"저장된 주문: {order_info}")
                print(f"현재 orders_db: {orders_db}")
        
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
        
        # 디버깅용 로그
        print(f"주문 조회 요청: user_id={user_id}")
        print(f"현재 orders_db: {orders_db}")
        
        if user_id not in orders_db:
            print(f"사용자 {user_id}의 주문이 없음")
            return jsonify({'orders': []}), 200
        
        # 주문 상태 업데이트 (smmpanel.kr API에서 최신 상태 조회)
        for order in orders_db[user_id]:
            try:
                status_response = requests.post(SMMPANEL_API_URL, json={
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
        
        # smmpanel.kr API에서 최신 상태 조회
        try:
            status_response = requests.post(SMMPANEL_API_URL, json={
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
def get_smmpanel_services():
    """smmpanel.kr API에서 실제 서비스 목록 조회"""
    try:
        response = requests.post(SMMPANEL_API_URL, json={
            'key': API_KEY,
            'action': 'services'
        }, timeout=30)
        
        if response.status_code == 200:
            services_data = response.json()
            print(f"smmpanel.kr API Services Response: {services_data}")  # 디버깅용
            return jsonify(services_data), 200
        else:
            return jsonify({'error': f'smmpanel.kr API 오류: {response.status_code}'}), response.status_code
            
    except Exception as e:
        return jsonify({'error': f'서비스 조회 실패: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'message': 'Backend server is running'})

# smmpanel.kr API 추가 기능들
@app.route('/api/balance', methods=['GET'])
def get_balance():
    """smmpanel.kr API에서 잔액 조회"""
    try:
        response = requests.post(SMMPANEL_API_URL, json={
            'key': API_KEY,
            'action': 'balance'
        }, timeout=30)
        
        if response.status_code == 200:
            balance_data = response.json()
            print(f"smmpanel.kr API Balance Response: {balance_data}")
            return jsonify(balance_data), 200
        else:
            return jsonify({'error': f'smmpanel.kr API 오류: {response.status_code}'}), response.status_code
            
    except Exception as e:
        return jsonify({'error': f'잔액 조회 실패: {str(e)}'}), 500

@app.route('/api/refill', methods=['POST'])
def refill_order():
    """주문 리필"""
    try:
        data = request.get_json()
        data['key'] = API_KEY
        data['action'] = 'refill'
        
        response = requests.post(SMMPANEL_API_URL, json=data, timeout=30)
        return jsonify(response.json()), response.status_code
        
    except Exception as e:
        return jsonify({'error': f'리필 실패: {str(e)}'}), 500

@app.route('/api/cancel', methods=['POST'])
def cancel_orders():
    """주문 취소"""
    try:
        data = request.get_json()
        data['key'] = API_KEY
        data['action'] = 'cancel'
        
        response = requests.post(SMMPANEL_API_URL, json=data, timeout=30)
        return jsonify(response.json()), response.status_code
        
    except Exception as e:
        return jsonify({'error': f'취소 실패: {str(e)}'}), 500

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

# 포인트 관련 API
@app.route('/api/points', methods=['GET', 'PUT'])
def points_endpoint():
    """포인트 관련 엔드포인트"""
    if request.method == 'PUT':
        return update_user_points()
    else:
        return get_user_points()

def update_user_points():
    """사용자 포인트 차감"""
    try:
        data = request.get_json()
        user_id = data.get('userId')
        points_to_deduct = data.get('points')
        
        if not user_id or points_to_deduct is None:
            return jsonify({'error': 'userId and points are required'}), 400
        
        current_points = points_db.get(user_id, 0)
        
        if current_points < points_to_deduct:
            return jsonify({'error': 'Insufficient points'}), 400
        
        points_db[user_id] = current_points - points_to_deduct
        
        print(f"포인트 차감: 사용자 {user_id}에서 {points_to_deduct}P 차감 (잔액: {points_db[user_id]}P)")
        
        return jsonify({
            'success': True,
            'remainingPoints': points_db[user_id],
            'message': '포인트가 성공적으로 차감되었습니다.'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_user_points():
    """사용자 포인트 조회"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        points = points_db.get(user_id, 0)
        return jsonify({'points': points}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)        }), 500

@app.route('/api/purchases', methods=['GET', 'POST'])
def purchases_endpoint():
    """구매 관련 엔드포인트"""
    if request.method == 'POST':
        return create_purchase()
    else:
        return get_purchase_history()

def create_purchase():
    """포인트 구매 신청"""
    try:
        data = request.get_json()
        user_id = data.get('userId')
        depositor_name = data.get('depositorName')
        bank_name = data.get('bankName')
        receipt_type = data.get('receiptType', 'none')
        business_number = data.get('businessNumber', '')
        business_name = data.get('businessName', '')
        representative = data.get('representative', '')
        contact_phone = data.get('contactPhone', '')
        contact_email = data.get('contactEmail', '')
        cash_receipt_phone = data.get('cashReceiptPhone', '')
        amount = data.get('amount')
        price = data.get('price')
        
        if not all([user_id, depositor_name, bank_name, amount, price]):
            return jsonify({'error': '모든 필수 정보를 입력해주세요'}), 400
        
        purchase_id = f"purchase_{len(purchases_db) + 1}_{int(datetime.now().timestamp())}"
        
        purchase_info = {
            'id': purchase_id,
            'userId': user_id,
            'depositorName': depositor_name,
            'bankName': bank_name,
            'receiptType': receipt_type,
            'businessNumber': business_number,
            'businessName': business_name,
            'representative': representative,
            'contactPhone': contact_phone,
            'contactEmail': contact_email,
            'cashReceiptPhone': cash_receipt_phone,
            'amount': amount,
            'price': price,
            'status': 'pending',
            'createdAt': datetime.now().isoformat()
        }
        
        if user_id not in purchases_db:
            purchases_db[user_id] = []
        
        purchases_db[user_id].append(purchase_info)
        
        print(f"구매 신청 생성: {purchase_info}")
        
        return jsonify({
            'success': True,
            'purchaseId': purchase_id,
            'message': '구매 신청이 완료되었습니다.'
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_purchase_history():
    """구매 내역 조회"""
    try:
        user_id = request.args.get('user_id')
        
        if user_id:
            # 특정 사용자의 구매 내역 조회
            history = purchases_db.get(user_id, [])
            return jsonify({'history': history}), 200
        else:
            # 관리자용: 모든 구매 내역 조회
            all_history = {}
            for uid, purchases in purchases_db.items():
                all_history[uid] = purchases
            return jsonify({'history': all_history}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/purchases/pending', methods=['GET'])
def get_pending_purchases():
    """관리자용 대기중인 구매 신청 목록"""
    try:
        pending_purchases = []
        for user_id, purchases in purchases_db.items():
            for purchase in purchases:
                if purchase['status'] == 'pending':
                    pending_purchases.append(purchase)
        
        return jsonify({'purchases': pending_purchases}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/register', methods=['POST'])
def register_user():
    """사용자 등록 (로그인 시 호출)"""
    try:
        data = request.get_json()
        user_id = data.get('userId')
        email = data.get('email')
        display_name = data.get('displayName', '')
        
        # 비즈니스 계정 정보
        account_type = data.get('accountType', 'personal')
        business_number = data.get('businessNumber', '')
        business_name = data.get('businessName', '')
        representative = data.get('representative', '')
        contact_phone = data.get('contactPhone', '')
        contact_email = data.get('contactEmail', '')
        
        if not user_id or not email:
            return jsonify({'error': 'userId and email are required'}), 400
        
        # 사용자 정보 저장/업데이트
        users_db[user_id] = {
            'id': user_id,
            'email': email,
            'displayName': display_name,
            'accountType': account_type,
            'businessNumber': business_number,
            'businessName': business_name,
            'representative': representative,
            'contactPhone': contact_phone,
            'contactEmail': contact_email,
            'registeredAt': datetime.now().isoformat(),
            'lastLoginAt': datetime.now().isoformat(),
            'totalOrders': 0,
            'totalSpent': 0,
            'currentPoints': points_db.get(user_id, 0)
        }
        
        print(f"사용자 등록/업데이트: {user_id} ({email}) - 계정타입: {account_type}")
        if account_type == 'business':
            print(f"비즈니스 정보: {business_name} ({business_number})")
        
        return jsonify({
            'success': True,
            'message': '사용자 정보가 저장되었습니다.'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/login', methods=['POST'])
def user_login():
    """사용자 로그인"""
    try:
        data = request.get_json()
        user_id = data.get('userId')
        
        if not user_id:
            return jsonify({'error': 'userId is required'}), 400
        
        # 마지막 로그인 시간 업데이트
        if user_id in users_db:
            users_db[user_id]['lastLoginAt'] = datetime.now().isoformat()
        
        # 실시간 접속 사용자에 추가
        user_sessions[user_id] = {
            'loginTime': datetime.now().isoformat(),
            'lastActivity': datetime.now().isoformat()
        }
        
        print(f"사용자 로그인: {user_id}")
        
        return jsonify({
            'success': True,
            'message': '로그인 정보가 기록되었습니다.'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/activity', methods=['POST'])
def update_user_activity():
    """사용자 활동 업데이트"""
    try:
        data = request.get_json()
        user_id = data.get('userId')
        
        if not user_id:
            return jsonify({'error': 'userId is required'}), 400
        
        # 실시간 접속 사용자 활동 시간 업데이트
        if user_id in user_sessions:
            user_sessions[user_id]['lastActivity'] = datetime.now().isoformat()
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/users', methods=['GET'])
def get_users_info():
    """관리자용 사용자 정보 조회"""
    try:
        # 실시간 접속 사용자 필터링 (30분 이내 활동)
        now = datetime.now()
        active_users = {}
        for user_id, session in user_sessions.items():
            last_activity = datetime.fromisoformat(session['lastActivity'])
            if (now - last_activity).total_seconds() < 1800:  # 30분
                active_users[user_id] = session
        
        # 사용자 통계 계산
        total_users = len(users_db)
        active_users_count = len(active_users)
        
        # 오늘 신규 가입자 수 계산
        today = now.date()
        new_users_today = 0
        for user_data in users_db.values():
            registered_date = datetime.fromisoformat(user_data['registeredAt']).date()
            if registered_date == today:
                new_users_today += 1
        
        # 이번 주 신규 가입자 수 계산
        week_ago = today - timedelta(days=7)
        new_users_week = 0
        for user_data in users_db.values():
            registered_date = datetime.fromisoformat(user_data['registeredAt']).date()
            if registered_date >= week_ago:
                new_users_week += 1
        
        # 사용자 목록 (최근 50명)
        recent_users = list(users_db.values())
        recent_users.sort(key=lambda x: x['lastLoginAt'], reverse=True)
        recent_users = recent_users[:50]
        
        return jsonify({
            'totalUsers': total_users,
            'activeUsers': active_users_count,
            'newUsersToday': new_users_today,
            'newUsersWeek': new_users_week,
            'recentUsers': recent_users,
            'activeUsersList': list(active_users.keys())
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<user_id>', methods=['GET'])
def get_user_info(user_id):
    """개별 사용자 정보 조회"""
    try:
        if user_id not in users_db:
            return jsonify({'error': 'User not found'}), 404
        
        user_data = users_db[user_id].copy()
        
        # 민감한 정보 제거
        if 'password' in user_data:
            del user_data['password']
        
        return jsonify({
            'success': True,
            'user': user_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/purchases/<purchase_id>', methods=['PUT'])
def update_purchase_status(purchase_id):
    """구매 신청 승인/거절"""
    try:
        data = request.get_json()
        status = data.get('status')  # 'approved' or 'rejected'
        
        if status not in ['approved', 'rejected']:
            return jsonify({'error': 'Invalid status'}), 400
        
        # 구매 신청 찾기
        purchase = None
        for user_id, purchases in purchases_db.items():
            for p in purchases:
                if p['id'] == purchase_id:
                    purchase = p
                    break
            if purchase:
                break
        
        if not purchase:
            return jsonify({'error': 'Purchase not found'}), 404
        
        # 상태 업데이트
        purchase['status'] = status
        purchase['updatedAt'] = datetime.now().isoformat()
        
        # 승인된 경우 포인트 추가
        if status == 'approved':
            user_id = purchase['userId']
            current_points = points_db.get(user_id, 0)
            points_db[user_id] = current_points + purchase['amount']
            
            print(f"포인트 승인: 사용자 {user_id}에게 {purchase['amount']}P 추가 (총 {points_db[user_id]}P)")
        
        return jsonify({
            'success': True,
            'message': f'구매 신청이 {status}되었습니다.'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/export/purchases', methods=['GET'])
def export_purchases():
    """포인트 구매 내역 엑셀 다운로드"""
    try:
        # 모든 구매 내역 수집
        all_purchases = []
        for user_id, purchases in purchases_db.items():
            for purchase in purchases:
                all_purchases.append({
                    '구매ID': purchase['id'],
                    '사용자ID': purchase['userId'],
                    '입금자명': purchase.get('depositorName', ''),
                    '은행': purchase.get('bankName', ''),
                    '영수증타입': purchase.get('receiptType', 'none'),
                    '사업자등록번호': purchase.get('businessNumber', ''),
                    '회사명': purchase.get('businessName', ''),
                    '대표자': purchase.get('representative', ''),
                    '담당자연락처': purchase.get('contactPhone', ''),
                    '메일주소': purchase.get('contactEmail', ''),
                    '현금영수증전화번호': purchase.get('cashReceiptPhone', ''),
                    '포인트': purchase['amount'],
                    '금액': purchase['price'],
                    '상태': purchase['status'],
                    '신청일': purchase['createdAt'],
                    '처리일': purchase.get('updatedAt', '')
                })
        
        # 날짜순으로 정렬
        all_purchases.sort(key=lambda x: x['신청일'], reverse=True)
        
        # CSV 데이터 생성
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 헤더 작성
        writer.writerow(['구매ID', '사용자ID', '입금자명', '은행', '영수증타입', '사업자등록번호', '회사명', '대표자', '담당자연락처', '메일주소', '현금영수증전화번호', '포인트', '금액', '상태', '신청일', '처리일'])
        
        # 데이터 작성
        for purchase in all_purchases:
            writer.writerow([
                purchase['구매ID'],
                purchase['사용자ID'],
                purchase['입금자명'],
                purchase['은행'],
                purchase['영수증타입'],
                purchase['사업자등록번호'],
                purchase['회사명'],
                purchase['대표자'],
                purchase['담당자연락처'],
                purchase['메일주소'],
                purchase['현금영수증전화번호'],
                purchase['포인트'],
                purchase['금액'],
                purchase['상태'],
                purchase['신청일'],
                purchase['처리일']
            ])
        
        # CSV 파일 생성
        output.seek(0)
        csv_data = output.getvalue()
        
        # 파일명에 현재 날짜 추가
        filename = f"포인트구매내역_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return jsonify({
            'success': True,
            'filename': filename,
            'data': csv_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
