#!/bin/bash

# AWS ECS 배포 스크립트 (데이터 유지 포함)
# AWS에서 테스크 서비스 업데이트 시 데이터가 유지되도록 하는 스크립트

set -e

# 설정 변수
AWS_REGION="ap-northeast-2"
AWS_ACCOUNT_ID="868812195478"
ECR_REPOSITORY="snspmt"
ECS_CLUSTER="snspmt-cluster"
ECS_SERVICE="snspmt-service"
TASK_DEFINITION_FAMILY="snspmt-task"

echo "🚀 AWS ECS 배포 시작 (데이터 유지 포함)"

# 1. ECR 로그인
echo "📦 ECR 로그인 중..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# 2. Docker 이미지 빌드
echo "🔨 Docker 이미지 빌드 중..."
docker build -t $ECR_REPOSITORY:latest .

# 3. ECR에 이미지 푸시
echo "📤 ECR에 이미지 푸시 중..."
docker tag $ECR_REPOSITORY:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest

# 4. 데이터베이스 마이그레이션 실행
echo "🔄 데이터베이스 마이그레이션 실행 중..."
# ECS 태스크로 마이그레이션 실행
aws ecs run-task \
    --cluster $ECS_CLUSTER \
    --task-definition $TASK_DEFINITION_FAMILY \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" \
    --overrides '{
        "containerOverrides": [{
            "name": "snspmt-app",
            "command": ["python", "migrate_database.py"]
        }]
    }' \
    --region $AWS_REGION

echo "⏳ 마이그레이션 완료 대기 중..."
sleep 30

# 5. 새 태스크 정의 생성
echo "📝 새 태스크 정의 생성 중..."
aws ecs register-task-definition \
    --cli-input-json file://taskdef.json \
    --region $AWS_REGION

# 6. ECS 서비스 업데이트
echo "🔄 ECS 서비스 업데이트 중..."
aws ecs update-service \
    --cluster $ECS_CLUSTER \
    --service $ECS_SERVICE \
    --task-definition $TASK_DEFINITION_FAMILY \
    --region $AWS_REGION

# 7. 배포 상태 확인
echo "📊 배포 상태 확인 중..."
aws ecs wait services-stable \
    --cluster $ECS_CLUSTER \
    --services $ECS_SERVICE \
    --region $AWS_REGION

echo "✅ 배포 완료!"
echo "🌐 서비스 URL: https://your-domain.com"

# 8. 헬스 체크
echo "🏥 헬스 체크 실행 중..."
sleep 10
curl -f https://your-domain.com/api/health || echo "⚠️ 헬스 체크 실패"

echo "🎉 AWS ECS 배포 완료 (데이터 유지됨)"
