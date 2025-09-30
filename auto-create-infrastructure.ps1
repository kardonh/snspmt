# 완전 자동화 인프라 생성 스크립트
Write-Host "🚀 완전 자동화 인프라 생성 시작!" -ForegroundColor Green

# VPC ID 설정
$VPC_ID = "vpc-09732e804ee98e990"
$SUBNET_A = "subnet-03066e8a50a9a7972"
$SUBNET_B = "subnet-0d904a814cc870f7a"

Write-Host "🔒 보안 그룹 생성 중..." -ForegroundColor Yellow
$SG_ID = aws ec2 create-security-group --group-name snspmt-sg-ultimate --description "SNS PMT Ultimate Security Group" --vpc-id $VPC_ID --query 'GroupId' --output text
Write-Host "✅ 보안 그룹 생성 완료: $SG_ID" -ForegroundColor Green

Write-Host "🔒 보안 그룹 규칙 추가 중..." -ForegroundColor Yellow
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 80 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 443 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 5432 --cidr 10.0.0.0/16
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 8000 --cidr 10.0.0.0/16
Write-Host "✅ 보안 그룹 규칙 추가 완료" -ForegroundColor Green

Write-Host "🗄️ RDS 서브넷 그룹 생성 중..." -ForegroundColor Yellow
aws rds create-db-subnet-group --db-subnet-group-name snspmt-subnet-group-ultimate --db-subnet-group-description "SNS PMT Ultimate DB Subnet Group" --subnet-ids $SUBNET_A $SUBNET_B
Write-Host "✅ RDS 서브넷 그룹 생성 완료" -ForegroundColor Green

Write-Host "💾 RDS 데이터베이스 생성 중..." -ForegroundColor Yellow
aws rds create-db-instance --db-instance-identifier snspmt-db-ultimate --db-instance-class db.t3.micro --engine postgres --master-username postgres --master-user-password Snspmt2024! --allocated-storage 20 --vpc-security-group-ids $SG_ID --db-subnet-group-name snspmt-subnet-group-ultimate --backup-retention-period 0 --no-multi-az --no-publicly-accessible
Write-Host "✅ RDS 데이터베이스 생성 완료" -ForegroundColor Green

Write-Host "🌐 ALB 생성 중..." -ForegroundColor Yellow
$ALB_ARN = aws elbv2 create-load-balancer --name snspmt-alb-ultimate --subnets $SUBNET_A $SUBNET_B --security-groups $SG_ID --query 'LoadBalancers[0].LoadBalancerArn' --output text
Write-Host "✅ ALB 생성 완료: $ALB_ARN" -ForegroundColor Green

Write-Host "🎯 타겟 그룹 생성 중..." -ForegroundColor Yellow
$TG_ARN = aws elbv2 create-target-group --name snspmt-tg-ultimate --protocol HTTP --port 8000 --vpc-id $VPC_ID --target-type ip --health-check-path /api/health --query 'TargetGroups[0].TargetGroupArn' --output text
Write-Host "✅ 타겟 그룹 생성 완료: $TG_ARN" -ForegroundColor Green

Write-Host "🔗 ALB 리스너 생성 중..." -ForegroundColor Yellow
aws elbv2 create-listener --load-balancer-arn $ALB_ARN --protocol HTTP --port 80 --default-actions Type=forward,TargetGroupArn=$TG_ARN
Write-Host "✅ HTTP 리스너 생성 완료" -ForegroundColor Green

Write-Host "🚀 ECS 클러스터 생성 중..." -ForegroundColor Yellow
aws ecs create-cluster --cluster-name snspmt-cluster-ultimate
Write-Host "✅ ECS 클러스터 생성 완료" -ForegroundColor Green

Write-Host "📋 태스크 정의 생성 중..." -ForegroundColor Yellow
aws ecs register-task-definition --cli-input-json file://perfect-task-definition.json
Write-Host "✅ 태스크 정의 생성 완료" -ForegroundColor Green

Write-Host "🔄 ECS 서비스 생성 중..." -ForegroundColor Yellow
aws ecs create-service --cluster snspmt-cluster-ultimate --service-name snspmt-service-ultimate --task-definition snspmt-task-final --desired-count 1 --launch-type FARGATE --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_A,$SUBNET_B],securityGroups=[$SG_ID],assignPublicIp=ENABLED}" --load-balancers "targetGroupArn=$TG_ARN,containerName=snspmt-app,containerPort=8000"
Write-Host "✅ ECS 서비스 생성 완료" -ForegroundColor Green

Write-Host "🎉 완전 자동화 인프라 생성 완료!" -ForegroundColor Green
Write-Host "VPC ID: $VPC_ID" -ForegroundColor Cyan
Write-Host "ALB ARN: $ALB_ARN" -ForegroundColor Cyan
Write-Host "타겟 그룹 ARN: $TG_ARN" -ForegroundColor Cyan

