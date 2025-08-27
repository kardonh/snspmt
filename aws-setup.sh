#!/bin/bash

# AWS 초기 설정 스크립트
set -e

AWS_REGION="us-east-1"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "🔧 AWS 초기 설정 시작..."
echo "📍 리전: $AWS_REGION"
echo "🏢 계정 ID: $AWS_ACCOUNT_ID"

# 1. IAM 역할 생성
echo "👤 IAM 역할 생성..."

# ECS Task Execution Role
aws iam create-role \
    --role-name ecsTaskExecutionRole \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "ecs-tasks.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }' 2>/dev/null || echo "ECS Task Execution Role이 이미 존재합니다."

# ECS Task Role
aws iam create-role \
    --role-name ecsTaskRole \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "ecs-tasks.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }' 2>/dev/null || echo "ECS Task Role이 이미 존재합니다."

# 2. 정책 연결
echo "🔗 정책 연결..."

# ECS Task Execution Role에 정책 연결
aws iam attach-role-policy \
    --role-name ecsTaskExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# SSM Parameter Store 접근 권한
aws iam put-role-policy \
    --role-name ecsTaskExecutionRole \
    --policy-name SSMParameterAccess \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "ssm:GetParameters",
                    "secretsmanager:GetSecretValue"
                ],
                "Resource": "*"
            }
        ]
    }'

# 3. CloudWatch Logs 그룹 생성
echo "📊 CloudWatch Logs 그룹 생성..."
aws logs create-log-group --log-group-name /ecs/snsinto --region $AWS_REGION 2>/dev/null || echo "Log group이 이미 존재합니다."

# 4. SSM Parameter Store에 시크릿 저장
echo "🔐 SSM Parameter Store에 시크릿 저장..."

# SMM Panel API Key 저장
read -p "SMM Panel API Key를 입력하세요: " SMM_API_KEY
aws ssm put-parameter \
    --name "/snsinto/SMMPANEL_API_KEY" \
    --value "$SMM_API_KEY" \
    --type SecureString \
    --region $AWS_REGION \
    --overwrite

# 데이터베이스 URL 저장
read -p "PostgreSQL 데이터베이스 URL을 입력하세요 (postgresql://user:pass@host:port/db): " DB_URL
aws ssm put-parameter \
    --name "/snsinto/DATABASE_URL" \
    --value "$DB_URL" \
    --type SecureString \
    --region $AWS_REGION \
    --overwrite

# 5. VPC 및 보안 그룹 생성 (기본값)
echo "🌐 VPC 설정 확인..."
echo "기본 VPC를 사용하거나 새로운 VPC를 생성하세요."
echo "보안 그룹에서 다음 포트를 열어주세요:"
echo "- 80 (HTTP)"
echo "- 443 (HTTPS)"
echo "- 8000 (애플리케이션)"

# 6. Application Load Balancer 생성 (선택사항)
read -p "Application Load Balancer를 생성하시겠습니까? (y/n): " CREATE_ALB
if [ "$CREATE_ALB" = "y" ]; then
    echo "🔗 Application Load Balancer 생성..."
    # ALB 생성 로직 (복잡하므로 수동으로 생성 권장)
    echo "ALB는 AWS 콘솔에서 수동으로 생성하는 것을 권장합니다."
fi

echo "✅ AWS 초기 설정 완료!"
echo "📋 다음 단계:"
echo "1. VPC 및 보안 그룹 설정"
echo "2. Application Load Balancer 생성 (선택사항)"
echo "3. 도메인 및 SSL 인증서 설정"
echo "4. ./aws-deploy.sh 실행"
