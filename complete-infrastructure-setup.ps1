# Complete Infrastructure Setup Script
# This script will create all AWS resources from scratch

Write-Host "🚀 Starting Complete Infrastructure Setup..." -ForegroundColor Green

# 1. Create Security Group
Write-Host "📋 Creating Security Group..." -ForegroundColor Yellow
$securityGroupId = aws ec2 create-security-group --group-name snspmt-sg-final --description "Final security group for snspmt" --vpc-id vpc-0ba3d521458a8769c --query 'GroupId' --output text
Write-Host "✅ Security Group Created: $securityGroupId" -ForegroundColor Green

# 2. Add Security Group Rules
Write-Host "🔧 Adding Security Group Rules..." -ForegroundColor Yellow
aws ec2 authorize-security-group-ingress --group-id $securityGroupId --protocol tcp --port 80 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $securityGroupId --protocol tcp --port 443 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $securityGroupId --protocol tcp --port 8000 --cidr 172.31.0.0/16
aws ec2 authorize-security-group-ingress --group-id $securityGroupId --protocol tcp --port 5432 --cidr 172.31.0.0/16
Write-Host "✅ Security Group Rules Added" -ForegroundColor Green

# 3. Create RDS Database
Write-Host "🗄️ Creating RDS Database..." -ForegroundColor Yellow
aws rds create-db-instance --db-instance-identifier snspmt-db-final --db-instance-class db.t3.micro --engine postgres --master-username postgres --master-user-password "Snspmt2024!" --allocated-storage 20 --vpc-security-group-ids $securityGroupId --db-subnet-group-name default --backup-retention-period 0 --no-multi-az --no-publicly-accessible --storage-encrypted
Write-Host "✅ RDS Database Created" -ForegroundColor Green

# 4. Wait for RDS to be available
Write-Host "⏳ Waiting for RDS to be available..." -ForegroundColor Yellow
aws rds wait db-instance-available --db-instance-identifier snspmt-db-final
Write-Host "✅ RDS Database Available" -ForegroundColor Green

# 5. Get RDS Endpoint
$rdsEndpoint = aws rds describe-db-instances --db-instance-identifier snspmt-db-final --query 'DBInstances[0].Endpoint.Address' --output text
Write-Host "✅ RDS Endpoint: $rdsEndpoint" -ForegroundColor Green

# 6. Create Target Group
Write-Host "🎯 Creating Target Group..." -ForegroundColor Yellow
$targetGroupArn = aws elbv2 create-target-group --name snspmt-tg-final --protocol HTTP --port 8000 --vpc-id vpc-0ba3d521458a8769c --target-type ip --health-check-path /api/health --health-check-interval-seconds 30 --health-check-timeout-seconds 5 --healthy-threshold-count 2 --unhealthy-threshold-count 3 --query 'TargetGroups[0].TargetGroupArn' --output text
Write-Host "✅ Target Group Created: $targetGroupArn" -ForegroundColor Green

# 7. Create Application Load Balancer
Write-Host "⚖️ Creating Application Load Balancer..." -ForegroundColor Yellow
$albArn = aws elbv2 create-load-balancer --name snspmt-alb-final --subnets subnet-0db02a53bbcceda41 subnet-053d122996a41f0c4 --security-groups $securityGroupId --query 'LoadBalancers[0].LoadBalancerArn' --output text
Write-Host "✅ ALB Created: $albArn" -ForegroundColor Green

# 8. Wait for ALB to be available
Write-Host "⏳ Waiting for ALB to be available..." -ForegroundColor Yellow
aws elbv2 wait load-balancer-available --load-balancer-arns $albArn
Write-Host "✅ ALB Available" -ForegroundColor Green

# 9. Get ALB DNS Name
$albDns = aws elbv2 describe-load-balancers --load-balancer-arns $albArn --query 'LoadBalancers[0].DNSName' --output text
Write-Host "✅ ALB DNS: $albDns" -ForegroundColor Green

# 10. Create HTTP Listener
Write-Host "🔗 Creating HTTP Listener..." -ForegroundColor Yellow
$listenerArn = aws elbv2 create-listener --load-balancer-arn $albArn --protocol HTTP --port 80 --default-actions Type=forward,TargetGroupArn=$targetGroupArn --query 'Listeners[0].ListenerArn' --output text
Write-Host "✅ HTTP Listener Created" -ForegroundColor Green

# 11. Update Task Definition with RDS Endpoint
Write-Host "📝 Updating Task Definition..." -ForegroundColor Yellow
$taskDefJson = Get-Content -Path "database-connected-task-definition.json" -Raw
$taskDefJson = $taskDefJson -replace "snspmt-cluste\.cluster-cvmiee0q0zhs\.ap-northeast-2\.rds\.amazonaws\.com", $rdsEndpoint
$taskDefJson | Out-File -FilePath "final-task-definition.json" -Encoding UTF8

# 12. Register Updated Task Definition
$newTaskDefArn = aws ecs register-task-definition --cli-input-json file://final-task-definition.json --query 'taskDefinition.taskDefinitionArn' --output text
Write-Host "✅ Task Definition Updated: $newTaskDefArn" -ForegroundColor Green

# 13. Create ECS Service
Write-Host "🚀 Creating ECS Service..." -ForegroundColor Yellow
aws ecs create-service --cluster snspmt-cluster --service-name snspmt-service-final --task-definition $newTaskDefArn --desired-count 1 --launch-type FARGATE --network-configuration "awsvpcConfiguration={subnets=[subnet-0db02a53bbcceda41,subnet-053d122996a41f0c4],securityGroups=[$securityGroupId],assignPublicIp=ENABLED}" --load-balancers "targetGroupArn=$targetGroupArn,containerName=snspmt-app,containerPort=8000"
Write-Host "✅ ECS Service Created" -ForegroundColor Green

# 14. Wait for Service to be Stable
Write-Host "⏳ Waiting for Service to be Stable..." -ForegroundColor Yellow
aws ecs wait services-stable --cluster snspmt-cluster --services snspmt-service-final
Write-Host "✅ ECS Service Stable" -ForegroundColor Green

# 15. Test Health Check
Write-Host "🔍 Testing Health Check..." -ForegroundColor Yellow
Start-Sleep -Seconds 30
try {
    $healthResponse = Invoke-WebRequest -Uri "http://$albDns/api/health" -Method GET -TimeoutSec 10
    Write-Host "✅ Health Check Successful: $($healthResponse.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Health Check Failed: $($_.Exception.Message)" -ForegroundColor Yellow
}

# 16. Final Status
Write-Host "🎉 Infrastructure Setup Complete!" -ForegroundColor Green
Write-Host "🌐 Website URL: http://$albDns" -ForegroundColor Cyan
Write-Host "🔍 Health Check URL: http://$albDns/api/health" -ForegroundColor Cyan
Write-Host "📊 ALB DNS: $albDns" -ForegroundColor Cyan
Write-Host "🗄️ RDS Endpoint: $rdsEndpoint" -ForegroundColor Cyan
Write-Host "🎯 Target Group: $targetGroupArn" -ForegroundColor Cyan
Write-Host "🔒 Security Group: $securityGroupId" -ForegroundColor Cyan

Write-Host "`n🚀 Your website is now live at: http://$albDns" -ForegroundColor Green
