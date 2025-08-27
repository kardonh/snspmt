# 🚀 AWS 배포 가이드

## 📋 사전 준비사항

### 1. AWS 계정 및 도구 설치
- AWS 계정 생성
- AWS CLI 설치 및 설정
- Docker 설치
- Terraform 설치 (선택사항)

### 2. 도메인 및 SSL
- 도메인 구매 (예: `snsinto.com`)
- SSL 인증서 준비

## 🎯 배포 방법 선택

### 방법 1: Terraform (권장) - 완전 자동화
### 방법 2: 수동 배포 - 단계별 설정

---

## 🔧 방법 1: Terraform 자동 배포

### 1단계: Terraform 설정

```bash
# 1. Terraform 디렉토리로 이동
cd aws-terraform

# 2. 변수 파일 생성
cp terraform.tfvars.example terraform.tfvars

# 3. terraform.tfvars 파일 편집
# - domain_name: 실제 도메인으로 변경
# - smm_api_key: 실제 API 키 입력
# - database_url: PostgreSQL 연결 문자열 입력
```

### 2단계: 인프라 배포

```bash
# 1. Terraform 초기화
terraform init

# 2. 배포 계획 확인
terraform plan

# 3. 인프라 배포
terraform apply
```

### 3단계: 애플리케이션 배포

```bash
# 1. ECR 로그인
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com

# 2. Docker 이미지 빌드
docker build -t snsinto .

# 3. 이미지 태그 및 푸시
docker tag snsinto:latest $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com/snsinto:latest
docker push $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com/snsinto:latest

# 4. ECS 서비스 업데이트
aws ecs update-service --cluster snsinto-cluster --service snsinto-service --force-new-deployment
```

---

## 🔧 방법 2: 수동 배포

### 1단계: AWS 초기 설정

```bash
# 1. AWS CLI 설정
aws configure

# 2. 초기 설정 스크립트 실행
chmod +x aws-setup.sh
./aws-setup.sh
```

### 2단계: 데이터베이스 설정

#### 옵션 A: AWS RDS PostgreSQL
```bash
# RDS 인스턴스 생성
aws rds create-db-instance \
    --db-instance-identifier snsinto-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --master-username admin \
    --master-user-password your-password \
    --allocated-storage 20 \
    --vpc-security-group-ids sg-xxxxx \
    --db-subnet-group-name snsinto-db-subnet-group
```

#### 옵션 B: 외부 PostgreSQL 서비스
- Railway, Supabase, PlanetScale 등 사용

### 3단계: 애플리케이션 배포

```bash
# 1. 배포 스크립트 실행
chmod +x aws-deploy.sh
./aws-deploy.sh
```

### 4단계: ECS 서비스 생성

```bash
# 서브넷 및 보안 그룹 ID 확인
SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=tag:Name,Values=*public*" --query 'Subnets[*].SubnetId' --output text | tr '\t' ',')
SECURITY_GROUP_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=snsinto-ecs-sg" --query 'SecurityGroups[0].GroupId' --output text)

# ECS 서비스 생성
aws ecs create-service \
    --cluster snsinto-cluster \
    --service-name snsinto-service \
    --task-definition snsinto \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_IDS],securityGroups=[$SECURITY_GROUP_ID],assignPublicIp=ENABLED}" \
    --region us-east-1
```

---

## 🌐 도메인 및 SSL 설정

### 1. Route 53 설정

```bash
# 호스팅 영역 생성
aws route53 create-hosted-zone --name yourdomain.com --caller-reference $(date +%s)

# 네임서버 정보 확인
aws route53 get-hosted-zone --id Z1234567890
```

### 2. SSL 인증서 생성

```bash
# ACM에서 인증서 요청
aws acm request-certificate \
    --domain-name yourdomain.com \
    --subject-alternative-names "*.yourdomain.com" \
    --validation-method DNS
```

### 3. DNS 검증

```bash
# 검증 레코드 확인
aws acm describe-certificate --certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/xxxxx
```

---

## 📊 모니터링 설정

### 1. CloudWatch 대시보드

```bash
# 대시보드 생성
aws cloudwatch put-dashboard \
    --dashboard-name SNSINTO-Monitoring \
    --dashboard-body file://cloudwatch-dashboard.json
```

### 2. 알람 설정

```bash
# CPU 사용률 알람
aws cloudwatch put-metric-alarm \
    --alarm-name snsinto-cpu-high \
    --alarm-description "CPU usage is high" \
    --metric-name CPUUtilization \
    --namespace AWS/ECS \
    --statistic Average \
    --period 300 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 2
```

---

## 🔒 보안 강화

### 1. WAF 설정

```bash
# WAF 웹 ACL 생성
aws wafv2 create-web-acl \
    --name snsinto-waf \
    --scope REGIONAL \
    --default-action Allow={} \
    --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=snsinto-waf
```

### 2. VPC 엔드포인트

```bash
# S3 엔드포인트 생성
aws ec2 create-vpc-endpoint \
    --vpc-id vpc-xxxxx \
    --service-name com.amazonaws.us-east-1.s3 \
    --region us-east-1
```

---

## 📈 스케일링 설정

### 1. Auto Scaling

```bash
# ECS 서비스에 Auto Scaling 설정
aws application-autoscaling register-scalable-target \
    --service-namespace ecs \
    --scalable-dimension ecs:service:DesiredCount \
    --resource-id service/snsinto-cluster/snsinto-service \
    --min-capacity 1 \
    --max-capacity 10
```

### 2. 스케일링 정책

```bash
# CPU 기반 스케일링
aws application-autoscaling put-scaling-policy \
    --service-namespace ecs \
    --scalable-dimension ecs:service:DesiredCount \
    --resource-id service/snsinto-cluster/snsinto-service \
    --policy-name snsinto-cpu-scaling \
    --policy-type TargetTrackingScaling \
    --target-tracking-scaling-policy-configuration file://scaling-policy.json
```

---

## 🔄 CI/CD 파이프라인

### GitHub Actions 설정

```yaml
name: Deploy to AWS

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1
      
      - name: Build, tag, and push image to Amazon ECR
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          ECR_REPOSITORY: snsinto
          IMAGE_TAG: latest
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
      
      - name: Deploy to ECS
        run: |
          aws ecs update-service --cluster snsinto-cluster --service snsinto-service --force-new-deployment
```

---

## 🆘 문제 해결

### 일반적인 문제들:

1. **ECS 태스크가 시작되지 않음**
   ```bash
   # 로그 확인
   aws logs describe-log-streams --log-group-name /ecs/snsinto
   aws logs get-log-events --log-group-name /ecs/snsinto --log-stream-name ecs/snsinto-app/xxxxx
   ```

2. **데이터베이스 연결 오류**
   ```bash
   # 보안 그룹 확인
   aws ec2 describe-security-groups --group-ids sg-xxxxx
   ```

3. **SSL 인증서 오류**
   ```bash
   # 인증서 상태 확인
   aws acm describe-certificate --certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/xxxxx
   ```

### 로그 확인:

```bash
# ECS 서비스 로그
aws logs tail /ecs/snsinto --follow

# ALB 액세스 로그
aws logs describe-log-groups --log-group-name-prefix /aws/applicationloadbalancer
```

---

## 💰 비용 최적화

### 1. 리소스 크기 조정
- ECS 태스크: CPU 256MB, Memory 512MB (개발)
- RDS: db.t3.micro (개발), db.t3.small (프로덕션)

### 2. 예약 인스턴스
```bash
# RDS 예약 인스턴스 구매
aws rds describe-reserved-db-instances-offerings --db-instance-class db.t3.micro --product-description "PostgreSQL"
```

### 3. 비용 알람 설정
```bash
# 월별 비용 알람
aws cloudwatch put-metric-alarm \
    --alarm-name monthly-cost-alarm \
    --alarm-description "Monthly cost exceeds threshold" \
    --metric-name EstimatedCharges \
    --namespace AWS/Billing \
    --statistic Maximum \
    --period 86400 \
    --threshold 50 \
    --comparison-operator GreaterThanThreshold
```

---

## 📞 지원

문제가 발생하면 다음을 확인하세요:

1. **AWS 문서**: https://docs.aws.amazon.com/
2. **ECS 가이드**: https://docs.aws.amazon.com/ecs/
3. **Terraform 문서**: https://www.terraform.io/docs

---

## ✅ 배포 체크리스트

- [ ] AWS CLI 설정 완료
- [ ] 도메인 구매 및 DNS 설정
- [ ] SSL 인증서 발급
- [ ] 데이터베이스 생성
- [ ] ECR 리포지토리 생성
- [ ] ECS 클러스터 생성
- [ ] 보안 그룹 설정
- [ ] 로드 밸런서 설정
- [ ] 애플리케이션 배포
- [ ] 도메인 연결
- [ ] 모니터링 설정
- [ ] 백업 설정
- [ ] 알람 설정
