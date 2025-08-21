import os

# SMM KINGS API 설정
SMMKINGS_API_URL = 'https://smmkings.com/api/v2'
API_KEY = os.environ.get('SMMKINGS_API_KEY', 'aa91dd380c10cf5fd875cb2b5626dd37')

# 데이터베이스 설정
DATABASE_PATH = '/tmp/orders.db'

# CORS 설정
CORS_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:5173',
    'https://snsinto.onrender.com',
    'https://yourdomain.com'  # 실제 도메인으로 변경
]

# 로깅 설정
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# API 타임아웃 설정
API_TIMEOUT = 30
REQUEST_TIMEOUT = 10

# 주문 설정
DEFAULT_ORDER_STATUS = 'pending'
MAX_QUANTITY = 100000
MIN_QUANTITY = 1

# 추천인 시스템 설정
REFERRAL_DISCOUNT_PERCENTAGE = 10.0  # 추천인 할인율
REFERRED_DISCOUNT_PERCENTAGE = 5.0   # 추천받은 사용자 할인율
REFERRAL_CODE_PREFIX = 'REF'
COUPON_CODE_PREFIX = 'COUPON'

# 쿠폰 설정
COUPON_EXPIRY_DAYS = 30
