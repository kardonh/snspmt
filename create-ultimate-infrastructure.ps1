# 완전히 새로운 인프라 생성 스크립트
Write-Host "🚀 완전히 새로운 인프라 생성 시작!" -ForegroundColor Green

# VPC 생성
Write-Host "📦 VPC 생성 중..." -ForegroundColor Yellow
$VPC = aws ec2 create-vpc --cidr-block 10.0.0.0/16 --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=snspmt-vpc-ultimate}]' --query 'Vpc.VpcId' --output text
Write-Host "✅ VPC 생성 완료: $VPC" -ForegroundColor Green

# VPC DNS 설정 활성화
Write-Host "🔧 VPC DNS 설정 활성화 중..." -ForegroundColor Yellow
aws ec2 modify-vpc-attribute --vpc-id $VPC --enable-dns-support
aws ec2 modify-vpc-attribute --vpc-id $VPC --enable-dns-hostnames
Write-Host "✅ VPC DNS 설정 완료" -ForegroundColor Green

# 서브넷 생성
Write-Host "📦 서브넷 생성 중..." -ForegroundColor Yellow
$SUBNET_A = aws ec2 create-subnet --vpc-id $VPC --cidr-block 10.0.1.0/24 --availability-zone ap-northeast-2a --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=snspmt-subnet-ultimate-a}]' --query 'Subnet.SubnetId' --output text
$SUBNET_B = aws ec2 create-subnet --vpc-id $VPC --cidr-block 10.0.2.0/24 --availability-zone ap-northeast-2b --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=snspmt-subnet-ultimate-b}]' --query 'Subnet.SubnetId' --output text
Write-Host "✅ 서브넷 A 생성 완료: $SUBNET_A" -ForegroundColor Green
Write-Host "✅ 서브넷 B 생성 완료: $SUBNET_B" -ForegroundColor Green

# 인터넷 게이트웨이 생성
Write-Host "🌐 인터넷 게이트웨이 생성 중..." -ForegroundColor Yellow
$IGW = aws ec2 create-internet-gateway --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=snspmt-igw-ultimate}]' --query 'InternetGateway.InternetGatewayId' --output text
aws ec2 attach-internet-gateway --vpc-id $VPC --internet-gateway-id $IGW
Write-Host "✅ 인터넷 게이트웨이 생성 완료: $IGW" -ForegroundColor Green

# 라우트 테이블 생성
Write-Host "🛣️ 라우트 테이블 생성 중..." -ForegroundColor Yellow
$RT = aws ec2 create-route-table --vpc-id $VPC --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=snspmt-rt-ultimate}]' --query 'RouteTable.RouteTableId' --output text
aws ec2 create-route --route-table-id $RT --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW
aws ec2 associate-route-table --subnet-id $SUBNET_A --route-table-id $RT
aws ec2 associate-route-table --subnet-id $SUBNET_B --route-table-id $RT
Write-Host "✅ 라우트 테이블 생성 완료: $RT" -ForegroundColor Green

# 보안 그룹 생성
Write-Host "🔒 보안 그룹 생성 중..." -ForegroundColor Yellow
$SG = aws ec2 create-security-group --group-name snspmt-sg-ultimate --description "SNS PMT Ultimate Security Group" --vpc-id $VPC --query 'GroupId' --output text
aws ec2 authorize-security-group-ingress --group-id $SG --protocol tcp --port 80 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $SG --protocol tcp --port 443 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $SG --protocol tcp --port 5432 --cidr 10.0.0.0/16
aws ec2 authorize-security-group-ingress --group-id $SG --protocol tcp --port 8000 --cidr 10.0.0.0/16
Write-Host "✅ 보안 그룹 생성 완료: $SG" -ForegroundColor Green

# VPC 엔드포인트 생성 (ECR용)
Write-Host "🔗 VPC 엔드포인트 생성 중..." -ForegroundColor Yellow
aws ec2 create-vpc-endpoint --vpc-id $VPC --service-name com.amazonaws.ap-northeast-2.ecr.dkr --vpc-endpoint-type Interface --subnet-ids $SUBNET_A $SUBNET_B --private-dns-enabled
Write-Host "✅ VPC 엔드포인트 생성 완료" -ForegroundColor Green

# RDS 서브넷 그룹 생성
Write-Host "🗄️ RDS 서브넷 그룹 생성 중..." -ForegroundColor Yellow
aws rds create-db-subnet-group --db-subnet-group-name snspmt-subnet-group-ultimate --db-subnet-group-description "SNS PMT Ultimate DB Subnet Group" --subnet-ids $SUBNET_A $SUBNET_B
Write-Host "✅ RDS 서브넷 그룹 생성 완료" -ForegroundColor Green

# RDS 데이터베이스 생성
Write-Host "💾 RDS 데이터베이스 생성 중..." -ForegroundColor Yellow
aws rds create-db-instance --db-instance-identifier snspmt-db-ultimate --db-instance-class db.t3.micro --engine postgres --master-username postgres --master-user-password Snspmt2024! --allocated-storage 20 --vpc-security-group-ids $SG --db-subnet-group-name snspmt-subnet-group-ultimate --backup-retention-period 0 --no-multi-az --no-publicly-accessible
Write-Host "✅ RDS 데이터베이스 생성 완료" -ForegroundColor Green

# ALB 생성
Write-Host "🌐 ALB 생성 중..." -ForegroundColor Yellow
$ALB_ARN = aws elbv2 create-load-balancer --name snspmt-alb-ultimate --subnets $SUBNET_A $SUBNET_B --security-groups $SG --query 'LoadBalancers[0].LoadBalancerArn' --output text
Write-Host "✅ ALB 생성 완료: $ALB_ARN" -ForegroundColor Green

# 타겟 그룹 생성
Write-Host "🎯 타겟 그룹 생성 중..." -ForegroundColor Yellow
$TG_ARN = aws elbv2 create-target-group --name snspmt-tg-ultimate --protocol HTTP --port 8000 --vpc-id $VPC --target-type ip --health-check-path /api/health --query 'TargetGroups[0].TargetGroupArn' --output text
Write-Host "✅ 타겟 그룹 생성 완료: $TG_ARN" -ForegroundColor Green

# ALB 리스너 생성
Write-Host "🔗 ALB 리스너 생성 중..." -ForegroundColor Yellow
aws elbv2 create-listener --load-balancer-arn $ALB_ARN --protocol HTTP --port 80 --default-actions Type=forward,TargetGroupArn=$TG_ARN
Write-Host "✅ HTTP 리스너 생성 완료" -ForegroundColor Green

# ECS 클러스터 생성
Write-Host "🚀 ECS 클러스터 생성 중..." -ForegroundColor Yellow
aws ecs create-cluster --cluster-name snspmt-cluster-ultimate
Write-Host "✅ ECS 클러스터 생성 완료" -ForegroundColor Green

# 태스크 정의 생성
Write-Host "📋 태스크 정의 생성 중..." -ForegroundColor Yellow
aws ecs register-task-definition --cli-input-json file://perfect-task-definition.json
Write-Host "✅ 태스크 정의 생성 완료" -ForegroundColor Green

# ECS 서비스 생성
Write-Host "🔄 ECS 서비스 생성 중..." -ForegroundColor Yellow
aws ecs create-service --cluster snspmt-cluster-ultimate --service-name snspmt-service-ultimate --task-definition snspmt-task-final --desired-count 1 --launch-type FARGATE --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_A,$SUBNET_B],securityGroups=[$SG],assignPublicIp=ENABLED}" --load-balancers "targetGroupArn=$TG_ARN,containerName=snspmt-app,containerPort=8000"
Write-Host "✅ ECS 서비스 생성 완료" -ForegroundColor Green

Write-Host "🎉 완전히 새로운 인프라 생성 완료!" -ForegroundColor Green
Write-Host "VPC ID: $VPC" -ForegroundColor Cyan
Write-Host "ALB ARN: $ALB_ARN" -ForegroundColor Cyan
Write-Host "타겟 그룹 ARN: $TG_ARN" -ForegroundColor Cyan

