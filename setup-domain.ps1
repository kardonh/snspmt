# AWS 도메인 설정 스크립트 (PowerShell)
# 소셜리티.co.kr 및 sociality.co.kr 도메인 연결

Write-Host "🌐 AWS 도메인 설정 시작..." -ForegroundColor Green

# 환경 변수 설정
$DOMAIN_MAIN = "소셜리티.co.kr"
$DOMAIN_SUB = "sociality.co.kr"
$REGION = "ap-northeast-2"
$ACCOUNT_ID = "868812195478"
$ALB_NAME = "snspmt-alb-new"

Write-Host "📋 설정 정보:" -ForegroundColor Yellow
Write-Host "  메인 도메인: $DOMAIN_MAIN" -ForegroundColor White
Write-Host "  부도메인: $DOMAIN_SUB" -ForegroundColor White
Write-Host "  리전: $REGION" -ForegroundColor White
Write-Host "  계정 ID: $ACCOUNT_ID" -ForegroundColor White
Write-Host "  ALB 이름: $ALB_NAME" -ForegroundColor White

try {
    # 1. Route 53 호스팅 영역 생성
    Write-Host "📝 Route 53 호스팅 영역 생성 중..." -ForegroundColor Yellow
    $callerReference = [DateTime]::Now.Ticks.ToString()
    
    $hostedZone = aws route53 create-hosted-zone `
        --name "$DOMAIN_MAIN" `
        --caller-reference "$callerReference" `
        --region $REGION `
        --query 'HostedZone.Id' `
        --output text
    
    $HOSTED_ZONE_ID = $hostedZone.Replace("/hostedzone/", "")
    Write-Host "✅ 호스팅 영역 생성 완료: $HOSTED_ZONE_ID" -ForegroundColor Green

    # 2. ALB 정보 가져오기
    Write-Host "🔍 ALB 정보 조회 중..." -ForegroundColor Yellow
    $albInfo = aws elbv2 describe-load-balancers `
        --names $ALB_NAME `
        --region $REGION `
        --query 'LoadBalancers[0]' `
        --output json | ConvertFrom-Json
    
    $ALB_DNS = $albInfo.DNSName
    Write-Host "✅ ALB 정보: $ALB_DNS" -ForegroundColor Green

    # 3. SSL 인증서 요청
    Write-Host "🔒 SSL 인증서 요청 중..." -ForegroundColor Yellow
    $certInfo = aws acm request-certificate `
        --domain-name "$DOMAIN_MAIN" `
        --subject-alternative-names "$DOMAIN_SUB", "*.${DOMAIN_MAIN}", "*.${DOMAIN_SUB}" `
        --validation-method DNS `
        --region $REGION `
        --query 'CertificateArn' `
        --output text
    
    $CERT_ARN = $certInfo
    Write-Host "✅ SSL 인증서 요청 완료: $CERT_ARN" -ForegroundColor Green

    # 4. DNS 검증 정보 출력
    Write-Host "📋 DNS 검증 정보:" -ForegroundColor Yellow
    aws acm describe-certificate `
        --certificate-arn $CERT_ARN `
        --region $REGION `
        --query 'Certificate.DomainValidationOptions[].ResourceRecord' `
        --output table

    # 5. A 레코드 생성 (메인 도메인)
    Write-Host "📝 A 레코드 생성 중..." -ForegroundColor Yellow
    $aRecordBatch = @{
        Changes = @(
            @{
                Action = "CREATE"
                ResourceRecordSet = @{
                    Name = $DOMAIN_MAIN
                    Type = "A"
                    AliasTarget = @{
                        HostedZoneId = "ZWKZPGTI48KDX"
                        DNSName = $ALB_DNS
                        EvaluateTargetHealth = $true
                    }
                }
            }
        )
    } | ConvertTo-Json -Depth 10

    aws route53 change-resource-record-sets `
        --hosted-zone-id $HOSTED_ZONE_ID `
        --change-batch "$aRecordBatch"

    # 6. CNAME 레코드 생성 (부도메인)
    Write-Host "📝 CNAME 레코드 생성 중..." -ForegroundColor Yellow
    $cnameRecordBatch = @{
        Changes = @(
            @{
                Action = "CREATE"
                ResourceRecordSet = @{
                    Name = $DOMAIN_SUB
                    Type = "CNAME"
                    TTL = 300
                    ResourceRecords = @(
                        @{
                            Value = $DOMAIN_MAIN
                        }
                    )
                }
            }
        )
    } | ConvertTo-Json -Depth 10

    aws route53 change-resource-record-sets `
        --hosted-zone-id $HOSTED_ZONE_ID `
        --change-batch "$cnameRecordBatch"

    Write-Host "✅ 도메인 설정 완료!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 다음 단계:" -ForegroundColor Yellow
    Write-Host "1. DNS 검증 완료까지 대기 (최대 24시간)" -ForegroundColor White
    Write-Host "2. SSL 인증서 상태 확인:" -ForegroundColor White
    Write-Host "   aws acm describe-certificate --certificate-arn $CERT_ARN --region $REGION" -ForegroundColor Cyan
    Write-Host "3. 도메인 연결 테스트:" -ForegroundColor White
    Write-Host "   Invoke-WebRequest -Uri http://$DOMAIN_MAIN -Method Head" -ForegroundColor Cyan
    Write-Host "   Invoke-WebRequest -Uri http://$DOMAIN_SUB -Method Head" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "🔗 호스팅 영역 ID: $HOSTED_ZONE_ID" -ForegroundColor Magenta
    Write-Host "🔒 인증서 ARN: $CERT_ARN" -ForegroundColor Magenta

} catch {
    Write-Host "❌ 오류 발생: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "스크립트 실행을 중단합니다." -ForegroundColor Red
    exit 1
}
