# AWS 연결 가이드

## 1. AWS 콘솔에서 확인할 정보

### AWS 계정 정보
- **AWS 계정 ID**: `868812195478` ✅
- **리전**: `ap-northeast-2` (서울)
- **IAM 사용자**: `snspmt-admin`

### IAM 권한
다음 권한이 필요합니다:
- `AmazonECS-FullAccess`
- `AmazonECR-FullAccess`
- `AmazonRDS-FullAccess`
- `AmazonVPC-FullAccess`
- `AmazonRoute53-FullAccess`
- `AmazonCloudWatch-FullAccess`

### Access Keys
- **Access Key ID**: `AKIA...` (AWS 콘솔에서 생성)
- **Secret Access Key**: `...` (생성 시에만 확인 가능)

## 2. AWS CLI 설정

### 새 터미널 열기
PowerShell을 새로 열고 다음 명령 실행:

```powershell
aws configure
```

### 설정 정보 입력
```
AWS Access Key ID [None]: AKIA... (여기에 실제 Access Key 입력)
AWS Secret Access Key [None]: ... (여기에 실제 Secret Key 입력)
Default region name [None]: ap-northeast-2
Default output format [None]: json
```

## 3. 프로젝트 환경 변수 설정

### .env 파일에 추가할 변수들
```env
# AWS 설정
AWS_ACCOUNT_ID=868812195478
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=ap-northeast-2

# 데이터베이스
DATABASE_URL=postgresql://username:password@host:port/database

# Redis 캐시
REDIS_URL=redis://host:port

# API 키들
SMMPANEL_API_KEY=18b03d2cd9babd365fa9bd0c5635a781
VITE_SMMKINGS_API_KEY=your_smmkings_api_key

# Firebase 설정
VITE_FIREBASE_API_KEY=your_firebase_api_key
VITE_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your_project_id
VITE_FIREBASE_STORAGE_BUCKET=your_project.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=123456789
VITE_FIREBASE_APP_ID=1:123456789:web:abcdef

# 앱 설정
VITE_API_BASE_URL=https://your-domain.com/api
FLASK_ENV=production
```

## 4. AWS 서비스 생성 순서

### 1) VPC 및 네트워킹
- VPC 생성 (CIDR: 10.0.0.0/16)
- 퍼블릭/프라이빗 서브넷 생성
- 인터넷 게이트웨이 연결
- NAT 게이트웨이 생성

### 2) 데이터베이스 (RDS)
- PostgreSQL RDS 인스턴스 생성
- 다중 AZ 설정
- 보안 그룹 설정

### 3) 컨테이너 레지스트리 (ECR)
- ECR 리포지토리 생성
- Docker 이미지 푸시

### 4) 컨테이너 서비스 (ECS)
- ECS 클러스터 생성
- 태스크 정의 생성
- 서비스 생성

### 5) 로드 밸런서 (ALB)
- Application Load Balancer 생성
- 타겟 그룹 설정
- 리스너 규칙 설정

### 6) 도메인 및 SSL (Route 53 + ACM)
- 도메인 등록/연결
- SSL 인증서 발급
- DNS 레코드 설정

## 5. 배포 명령어

### Docker 이미지 빌드 및 푸시
```bash
# ECR 로그인
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin 868812195478.dkr.ecr.ap-northeast-2.amazonaws.com

# 이미지 빌드
docker build -t snspmt-app .

# 이미지 태그
docker tag snspmt-app:latest 868812195478.dkr.ecr.ap-northeast-2.amazonaws.com/snspmt-app:latest

# 이미지 푸시
docker push 868812195478.dkr.ecr.ap-northeast-2.amazonaws.com/snspmt-app:latest
```

### ECS 서비스 업데이트
```bash
aws ecs update-service --cluster snspmt-cluster --service snspmt-service --force-new-deployment
```

## 6. 모니터링 및 로그

### CloudWatch 로그 확인
```bash
aws logs describe-log-groups --log-group-name-prefix /ecs/snspmt
```

### ECS 서비스 상태 확인
```bash
aws ecs describe-services --cluster snspmt-cluster --services snspmt-service
```

## 7. 비용 최적화

### 예상 월 비용 (서울 리전)
- ECS Fargate: $50-100/월
- RDS PostgreSQL: $30-60/월
- ALB: $20-30/월
- CloudWatch: $10-20/월
- **총 예상 비용: $110-210/월**

### 비용 절약 팁
- RDS 예약 인스턴스 사용
- ECS Spot 인스턴스 활용
- CloudWatch 로그 보관 기간 단축
- 불필요한 리소스 정리

## 8. 보안 체크리스트

- [ ] IAM 사용자 최소 권한 원칙 적용
- [ ] 보안 그룹 인바운드 규칙 제한
- [ ] SSL/TLS 인증서 적용
- [ ] 데이터베이스 암호화 활성화
- [ ] CloudTrail 로깅 활성화
- [ ] WAF 적용 (선택사항)
- [ ] 정기적인 보안 업데이트

## 9. 문제 해결

### 일반적인 문제들
1. **ECS 태스크 시작 실패**: 메모리/CPU 설정 확인
2. **데이터베이스 연결 실패**: 보안 그룹 및 VPC 설정 확인
3. **SSL 인증서 오류**: ACM 인증서 상태 확인
4. **도메인 연결 실패**: Route 53 DNS 설정 확인

### 로그 확인 방법
```bash
# ECS 태스크 로그
aws logs tail /ecs/snspmt --follow

# ALB 액세스 로그
aws logs tail /aws/applicationloadbalancer/snspmt-alb --follow
```

## 10. 다음 단계

### AWS 콘솔에서 해야 할 일:
1. **IAM 사용자 생성**
   - AWS 콘솔 → IAM → 사용자 → 사용자 생성
   - 사용자명: `snspmt-admin`
   - 액세스 키 생성 (프로그래밍 방식)

2. **필요한 권한 정책 연결**
   - `AmazonECS-FullAccess`
   - `AmazonECR-FullAccess`
   - `AmazonRDS-FullAccess`
   - `AmazonVPC-FullAccess`

3. **Access Keys 생성 후 .env 파일 업데이트**
   - `AWS_ACCESS_KEY_ID=실제_액세스_키`
   - `AWS_SECRET_ACCESS_KEY=실제_시크릿_키`

### 새 터미널에서 AWS CLI 설정:
```powershell
aws configure
```
