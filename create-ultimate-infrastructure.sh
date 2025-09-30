#!/bin/bash

echo "🚀 완전히 새로운 인프라 생성 시작!"

# VPC ID 설정
VPC_ID="vpc-09732e804ee98e990"

echo "📦 서브넷 생성 중..."
# 서브넷 A 생성
SUBNET_A=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.10.0/24 --availability-zone ap-northeast-2a --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=snspmt-subnet-ultimate-a}]' --query 'Subnet.SubnetId' --output text)
echo "✅ 서브넷 A 생성 완료: $SUBNET_A"

# 서브넷 B 생성
SUBNET_B=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.20.0/24 --availability-zone ap-northeast-2b --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=snspmt-subnet-ultimate-b}]' --query 'Subnet.SubnetId' --output text)
echo "✅ 서브넷 B 생성 완료: $SUBNET_B"

echo "🌐 인터넷 게이트웨이 생성 중..."
# 인터넷 게이트웨이 생성
IGW_ID=$(aws ec2 create-internet-gateway --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=snspmt-igw-ultimate}]' --query 'InternetGateway.InternetGatewayId' --output text)
echo "✅ 인터넷 게이트웨이 생성 완료: $IGW_ID"

# VPC에 인터넷 게이트웨이 연결
aws ec2 attach-internet-gateway --vpc-id $VPC_ID --internet-gateway-id $IGW_ID
echo "✅ 인터넷 게이트웨이 연결 완료"

echo "🛣️ 라우트 테이블 생성 중..."
# 라우트 테이블 생성
RT_ID=$(aws ec2 create-route-table --vpc-id $VPC_ID --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=snspmt-rt-ultimate}]' --query 'RouteTable.RouteTableId' --output text)
echo "✅ 라우트 테이블 생성 완료: $RT_ID"

# 기본 라우트 추가
aws ec2 create-route --route-table-id $RT_ID --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW_ID
echo "✅ 기본 라우트 추가 완료"

# 서브넷을 라우트 테이블에 연결
aws ec2 associate-route-table --subnet-id $SUBNET_A --route-table-id $RT_ID
aws ec2 associate-route-table --subnet-id $SUBNET_B --route-table-id $RT_ID
echo "✅ 서브넷 라우트 테이블 연결 완료"

echo "🔒 보안 그룹 생성 중..."
# 보안 그룹 생성
SG_ID=$(aws ec2 create-security-group --group-name snspmt-sg-ultimate --description "SNS PMT Ultimate Security Group" --vpc-id $VPC_ID --query 'GroupId' --output text)
echo "✅ 보안 그룹 생성 완료: $SG_ID"

# 보안 그룹 규칙 추가
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 80 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 443 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 5432 --cidr 10.0.0.0/16
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 8000 --cidr 10.0.0.0/16
echo "✅ 보안 그룹 규칙 추가 완료"

echo "🗄️ RDS 서브넷 그룹 생성 중..."
# RDS 서브넷 그룹 생성
aws rds create-db-subnet-group --db-subnet-group-name snspmt-subnet-group-ultimate --db-subnet-group-description "SNS PMT Ultimate DB Subnet Group" --subnet-ids $SUBNET_A $SUBNET_B
echo "✅ RDS 서브넷 그룹 생성 완료"

echo "💾 RDS 데이터베이스 생성 중..."
# RDS 데이터베이스 생성
aws rds create-db-instance --db-instance-identifier snspmt-db-ultimate --db-instance-class db.t3.micro --engine postgres --master-username postgres --master-user-password Snspmt2024! --allocated-storage 20 --vpc-security-group-ids $SG_ID --db-subnet-group-name snspmt-subnet-group-ultimate --backup-retention-period 0 --no-multi-az --no-publicly-accessible
echo "✅ RDS 데이터베이스 생성 완료"

echo "🌐 ALB 생성 중..."
# ALB 생성
ALB_ARN=$(aws elbv2 create-load-balancer --name snspmt-alb-ultimate --subnets $SUBNET_A $SUBNET_B --security-groups $SG_ID --query 'LoadBalancers[0].LoadBalancerArn' --output text)
echo "✅ ALB 생성 완료: $ALB_ARN"

echo "🎯 타겟 그룹 생성 중..."
# 타겟 그룹 생성
TG_ARN=$(aws elbv2 create-target-group --name snspmt-tg-ultimate --protocol HTTP --port 8000 --vpc-id $VPC_ID --target-type ip --health-check-path /api/health --query 'TargetGroups[0].TargetGroupArn' --output text)
echo "✅ 타겟 그룹 생성 완료: $TG_ARN"

echo "🔗 ALB 리스너 생성 중..."
# HTTP 리스너 생성
aws elbv2 create-listener --load-balancer-arn $ALB_ARN --protocol HTTP --port 80 --default-actions Type=forward,TargetGroupArn=$TG_ARN
echo "✅ HTTP 리스너 생성 완료"

echo "🚀 ECS 클러스터 생성 중..."
# ECS 클러스터 생성
aws ecs create-cluster --cluster-name snspmt-cluster-ultimate
echo "✅ ECS 클러스터 생성 완료"

echo "📋 태스크 정의 생성 중..."
# 태스크 정의 생성 (기존 perfect-task-definition.json 사용)
aws ecs register-task-definition --cli-input-json file://perfect-task-definition.json
echo "✅ 태스크 정의 생성 완료"

echo "🔄 ECS 서비스 생성 중..."
# ECS 서비스 생성
aws ecs create-service --cluster snspmt-cluster-ultimate --service-name snspmt-service-ultimate --task-definition snspmt-task-final --desired-count 1 --launch-type FARGATE --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_A,$SUBNET_B],securityGroups=[$SG_ID],assignPublicIp=ENABLED}" --load-balancers "targetGroupArn=$TG_ARN,containerName=snspmt-app,containerPort=8000"
echo "✅ ECS 서비스 생성 완료"

echo "🎉 완전히 새로운 인프라 생성 완료!"
echo "VPC ID: $VPC_ID"
echo "ALB ARN: $ALB_ARN"
echo "타겟 그룹 ARN: $TG_ARN"

