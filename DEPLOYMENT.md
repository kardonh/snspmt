# 🚀 배포 가이드

## 📋 사전 준비사항

1. **도메인 구매** (권장)
   - Namecheap, GoDaddy, AWS Route 53 등에서 도메인 구매
   - 예: `snsinto.com`, `snssmm.com`

2. **SSL 인증서**
   - Let's Encrypt (무료)
   - Cloudflare (무료 SSL + CDN)

## 🎯 추천 배포 플랫폼

### 1. AWS (Amazon Web Services) - 최고 추천

#### 장점:
- 무료 티어: 12개월 무료
- 확장성: Auto Scaling
- 보안: IAM, VPC, WAF
- 글로벌 CDN: CloudFront

#### 배포 단계:

```bash
# 1. AWS CLI 설치 및 설정
aws configure

# 2. ECR에 이미지 푸시
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin [ACCOUNT_ID].dkr.ecr.us-east-1.amazonaws.com
docker build -t snsinto .
docker tag snsinto:latest [ACCOUNT_ID].dkr.ecr.us-east-1.amazonaws.com/snsinto:latest
docker push [ACCOUNT_ID].dkr.ecr.us-east-1.amazonaws.com/snsinto:latest

# 3. ECS 클러스터 생성 및 서비스 배포
aws ecs create-cluster --cluster-name snsinto-cluster
aws ecs create-service --cluster snsinto-cluster --service-name snsinto-service --task-definition snsinto-task
```

#### 환경 변수 설정:
```bash
# AWS Systems Manager Parameter Store에 저장
aws ssm put-parameter --name "/snsinto/SMMPANEL_API_KEY" --value "your_api_key" --type SecureString
aws ssm put-parameter --name "/snsinto/DATABASE_URL" --value "postgresql://..." --type SecureString
```

### 2. DigitalOcean App Platform

#### 장점:
- 간단한 설정
- 자동 SSL
- 글로벌 CDN
- 데이터베이스 포함

#### 배포 단계:

1. **DigitalOcean 계정 생성**
2. **App Platform에서 새 앱 생성**
3. **GitHub 저장소 연결**
4. **환경 변수 설정**
5. **자동 배포 활성화**

#### 환경 변수:
```
FLASK_ENV=production
DATABASE_URL=postgresql://...
SMMPANEL_API_KEY=your_api_key
ALLOWED_ORIGINS=https://yourdomain.com
```

### 3. Railway

#### 장점:
- 간단한 배포
- PostgreSQL 포함
- 자동 SSL
- GitHub 연동

#### 배포 단계:

1. **Railway 계정 생성**
2. **GitHub 저장소 연결**
3. **PostgreSQL 서비스 추가**
4. **환경 변수 설정**

### 4. Heroku

#### 장점:
- 간단한 배포
- PostgreSQL 추가기능
- 자동 SSL

#### 배포 단계:

```bash
# 1. Heroku CLI 설치
npm install -g heroku

# 2. 로그인 및 앱 생성
heroku login
heroku create snsinto-app

# 3. PostgreSQL 추가
heroku addons:create heroku-postgresql:hobby-dev

# 4. 환경 변수 설정
heroku config:set FLASK_ENV=production
heroku config:set SMMPANEL_API_KEY=your_api_key
heroku config:set ALLOWED_ORIGINS=https://yourdomain.com

# 5. 배포
git push heroku main
```

## 🔧 로컬 테스트

```bash
# 1. Docker Compose로 로컬 테스트
docker-compose up -d

# 2. 데이터베이스 마이그레이션
docker-compose exec app python -c "from backend import init_database; init_database()"

# 3. 테스트
curl http://localhost:8000/api/health
```

## 🔒 보안 설정

### 1. 환경 변수 관리
```bash
# .env 파일 (로컬 개발용)
FLASK_ENV=development
DATABASE_URL=sqlite:///orders.db
SMMPANEL_API_KEY=your_api_key

# 프로덕션 환경 변수
FLASK_ENV=production
DATABASE_URL=postgresql://...
SMMPANEL_API_KEY=your_api_key
ALLOWED_ORIGINS=https://yourdomain.com
```

### 2. 방화벽 설정
```bash
# UFW (Ubuntu)
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

### 3. SSL 인증서 (Let's Encrypt)
```bash
# Certbot 설치
sudo apt install certbot python3-certbot-nginx

# 인증서 발급
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# 자동 갱신
sudo crontab -e
# 0 12 * * * /usr/bin/certbot renew --quiet
```

## 📊 모니터링 설정

### 1. 로그 관리
```bash
# 로그 로테이션
sudo logrotate -f /etc/logrotate.conf
```

### 2. 성능 모니터링
- **New Relic**: APM 모니터링
- **Datadog**: 인프라 모니터링
- **Sentry**: 에러 추적

## 🚀 성능 최적화

### 1. CDN 설정 (Cloudflare)
1. Cloudflare 계정 생성
2. 도메인 추가
3. DNS 설정
4. SSL/TLS 모드: Full (strict)
5. 캐싱 규칙 설정

### 2. 데이터베이스 최적화
```sql
-- 인덱스 생성
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_created_at ON orders(created_at);
CREATE INDEX idx_users_email ON users(email);
```

### 3. 캐싱 설정
```python
# Redis 캐싱 추가
import redis
redis_client = redis.Redis(host='localhost', port=6379, db=0)

def get_cached_data(key):
    return redis_client.get(key)

def set_cached_data(key, value, expire=3600):
    redis_client.setex(key, expire, value)
```

## 🔄 CI/CD 파이프라인

### GitHub Actions 예시:
```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to AWS
        run: |
          # 배포 스크립트
```

## 📈 스케일링 전략

### 1. 수평 스케일링
- 로드 밸런서 설정
- 여러 인스턴스 실행
- 세션 공유 (Redis)

### 2. 수직 스케일링
- CPU/메모리 증가
- 데이터베이스 최적화
- 캐싱 레이어 추가

## 🆘 문제 해결

### 일반적인 문제들:
1. **CORS 오류**: ALLOWED_ORIGINS 확인
2. **데이터베이스 연결 오류**: DATABASE_URL 확인
3. **SSL 오류**: 인증서 경로 확인
4. **메모리 부족**: 워커 수 조정

### 로그 확인:
```bash
# 애플리케이션 로그
docker-compose logs app

# Nginx 로그
docker-compose logs nginx

# 데이터베이스 로그
docker-compose logs db
```
