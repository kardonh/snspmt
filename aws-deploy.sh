#!/bin/bash

# AWS 배포 스크립트
set -e

# 설정 변수
AWS_REGION="us-east-1"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPOSITORY="snsinto"
ECS_CLUSTER="snsinto-cluster"
ECS_SERVICE="snsinto-service"
TASK_DEFINITION="snsinto"

echo "🚀 AWS 배포 시작..."
echo "📍 리전: $AWS_REGION"
echo "🏢 계정 ID: $AWS_ACCOUNT_ID"

# 1. ECR 리포지토리 생성 (없는 경우)
echo "📦 ECR 리포지토리 확인/생성..."
aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $AWS_REGION 2>/dev/null || \
aws ecr create-repository --repository-name $ECR_REPOSITORY --region $AWS_REGION

# 2. ECR 로그인
echo "🔐 ECR 로그인..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# 3. Docker 이미지 빌드
echo "🔨 Docker 이미지 빌드..."
docker build -t $ECR_REPOSITORY .

# 4. 이미지 태그
echo "🏷️ 이미지 태그..."
docker tag $ECR_REPOSITORY:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest

# 5. ECR에 푸시
echo "⬆️ ECR에 이미지 푸시..."
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest

# 6. Task Definition 업데이트
echo "📝 Task Definition 업데이트..."
sed -i "s/ACCOUNT_ID/$AWS_ACCOUNT_ID/g" aws-task-definition.json
sed -i "s/REGION/$AWS_REGION/g" aws-task-definition.json

aws ecs register-task-definition --cli-input-json file://aws-task-definition.json --region $AWS_REGION

# 7. ECS 클러스터 생성 (없는 경우)
echo "🏗️ ECS 클러스터 확인/생성..."
aws ecs describe-clusters --clusters $ECS_CLUSTER --region $AWS_REGION 2>/dev/null || \
aws ecs create-cluster --cluster-name $ECS_CLUSTER --region $AWS_REGION

# 8. ECS 서비스 업데이트 또는 생성
echo "🔄 ECS 서비스 업데이트..."
if aws ecs describe-services --cluster $ECS_CLUSTER --services $ECS_SERVICE --region $AWS_REGION 2>/dev/null | grep -q "ACTIVE"; then
    # 서비스가 존재하면 업데이트
    aws ecs update-service \
        --cluster $ECS_CLUSTER \
        --service $ECS_SERVICE \
        --task-definition $TASK_DEFINITION \
        --region $AWS_REGION
else
    # 서비스가 없으면 생성
    echo "⚠️ ECS 서비스가 존재하지 않습니다. 수동으로 생성해야 합니다."
    echo "다음 명령어로 서비스를 생성하세요:"
    echo "aws ecs create-service --cluster $ECS_CLUSTER --service-name $ECS_SERVICE --task-definition $TASK_DEFINITION --desired-count 1 --launch-type FARGATE --network-configuration 'awsvpcConfiguration={subnets=[subnet-xxxxx],securityGroups=[sg-xxxxx],assignPublicIp=ENABLED}' --region $AWS_REGION"
fi

echo "✅ 배포 완료!"
echo "🌐 애플리케이션 URL: https://yourdomain.com"
echo "📊 ECS 콘솔: https://console.aws.amazon.com/ecs/home?region=$AWS_REGION#/clusters/$ECS_CLUSTER"
으