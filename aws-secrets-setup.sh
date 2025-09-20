#!/bin/bash

# AWS Secrets Manager 및 Parameter Store 설정 스크립트
# 민감한 정보를 안전하게 관리하기 위한 스크립트

set -e

AWS_REGION="ap-northeast-2"
AWS_ACCOUNT_ID="868812195478"

echo "🔐 AWS 시크릿 및 파라미터 설정 시작"

# 1. Secrets Manager에 민감한 정보 저장
echo "📝 Secrets Manager에 민감한 정보 저장 중..."

# 데이터베이스 연결 정보
aws secretsmanager create-secret \
    --name "snspmt/database" \
    --description "SNS PMT 데이터베이스 연결 정보" \
    --secret-string '{
        "DATABASE_URL": "postgresql://postgres:Snspmt2024!@snspmt-cluste.cluster-cvmiee0q0zhs.ap-northeast-2.rds.amazonaws.com:5432/snspmt",
        "DB_HOST": "snspmt-cluste.cluster-cvmiee0q0zhs.ap-northeast-2.rds.amazonaws.com",
        "DB_PORT": "5432",
        "DB_NAME": "snspmt",
        "DB_USER": "postgres",
        "DB_PASSWORD": "Snspmt2024!"
    }' \
    --region $AWS_REGION \
    --no-cli-pager

# API 키들
aws secretsmanager create-secret \
    --name "snspmt/api-keys" \
    --description "SNS PMT API 키들" \
    --secret-string '{
        "SMMPANEL_API_KEY": "5efae48d287931cf9bd80a1bc6fdfa6d",
        "FIREBASE_API_KEY": "your-firebase-api-key",
        "FIREBASE_AUTH_DOMAIN": "your-project.firebaseapp.com",
        "FIREBASE_PROJECT_ID": "your-project-id"
    }' \
    --region $AWS_REGION \
    --no-cli-pager

echo "✅ Secrets Manager 설정 완료"

# 2. Parameter Store에 일반 설정 저장
echo "📋 Parameter Store에 일반 설정 저장 중..."

# 애플리케이션 설정
aws ssm put-parameter \
    --name "/snspmt/app/flask-env" \
    --value "production" \
    --type "String" \
    --description "Flask 환경 설정" \
    --region $AWS_REGION \
    --overwrite

aws ssm put-parameter \
    --name "/snspmt/app/allowed-origins" \
    --value "*" \
    --type "String" \
    --description "허용된 오리진" \
    --region $AWS_REGION \
    --overwrite

aws ssm put-parameter \
    --name "/snspmt/app/aws-region" \
    --value $AWS_REGION \
    --type "String" \
    --description "AWS 리전" \
    --region $AWS_REGION \
    --overwrite

# 데이터베이스 설정
aws ssm put-parameter \
    --name "/snspmt/database/pool-size" \
    --value "10" \
    --type "String" \
    --description "데이터베이스 연결 풀 크기" \
    --region $AWS_REGION \
    --overwrite

aws ssm put-parameter \
    --name "/snspmt/database/timeout" \
    --value "30" \
    --type "String" \
    --description "데이터베이스 타임아웃" \
    --region $AWS_REGION \
    --overwrite

aws ssm put-parameter \
    --name "/snspmt/database/ssl-mode" \
    --value "require" \
    --type "String" \
    --description "PostgreSQL SSL 모드" \
    --region $AWS_REGION \
    --overwrite

echo "✅ Parameter Store 설정 완료"

# 3. IAM 정책 생성 (ECS 태스크가 시크릿에 접근할 수 있도록)
echo "🔑 IAM 정책 생성 중..."

# 정책 문서 생성
cat > snspmt-secrets-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": [
                "arn:aws:secretsmanager:${AWS_REGION}:${AWS_ACCOUNT_ID}:secret:snspmt/database*",
                "arn:aws:secretsmanager:${AWS_REGION}:${AWS_ACCOUNT_ID}:secret:snspmt/api-keys*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "ssm:GetParameter",
                "ssm:GetParameters",
                "ssm:GetParametersByPath"
            ],
            "Resource": [
                "arn:aws:ssm:${AWS_REGION}:${AWS_ACCOUNT_ID}:parameter/snspmt/*"
            ]
        }
    ]
}
EOF

# 정책 생성
aws iam create-policy \
    --policy-name "SNS-PMT-SecretsAccess" \
    --policy-document file://snspmt-secrets-policy.json \
    --description "SNS PMT 애플리케이션용 시크릿 접근 정책" \
    --region $AWS_REGION \
    --no-cli-pager

echo "✅ IAM 정책 생성 완료"

# 4. ECS 태스크 역할에 정책 연결
echo "🔗 ECS 태스크 역할에 정책 연결 중..."

# 정책 ARN 생성
POLICY_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:policy/SNS-PMT-SecretsAccess"

# ECS 태스크 역할에 정책 연결
aws iam attach-role-policy \
    --role-name "ecsTaskRole" \
    --policy-arn $POLICY_ARN \
    --region $AWS_REGION

echo "✅ ECS 태스크 역할 정책 연결 완료"

# 5. 정리
rm snspmt-secrets-policy.json

echo "🎉 AWS 시크릿 및 파라미터 설정 완료!"
echo ""
echo "📋 설정된 리소스:"
echo "  - Secrets Manager: snspmt/database, snspmt/api-keys"
echo "  - Parameter Store: /snspmt/app/*, /snspmt/database/*"
echo "  - IAM 정책: SNS-PMT-SecretsAccess"
echo ""
echo "🔧 다음 단계:"
echo "  1. ECS 태스크 정의를 업데이트하여 시크릿을 참조하도록 수정"
echo "  2. 애플리케이션 코드에서 시크릿을 동적으로 로드하도록 수정"
