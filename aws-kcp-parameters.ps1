# AWS KCP 파라미터 추가 PowerShell 스크립트
# 실행 전에 AWS CLI가 설정되어 있어야 합니다.

Write-Host "🔧 AWS Parameter Store에 KCP 설정 추가 중..." -ForegroundColor Green

# KCP 기본 설정
aws ssm put-parameter `
    --name "/snspmt/KCP_SITE_CD" `
    --value "ALFCQ" `
    --type "String" `
    --description "KCP 사이트코드" `
    --overwrite

aws ssm put-parameter `
    --name "/snspmt/KCP_SITE_KEY" `
    --value "2Lu3CSvPPLnuE34LaRWJR24__4" `
    --type "SecureString" `
    --description "KCP 사이트키" `
    --overwrite

aws ssm put-parameter `
    --name "/snspmt/KCP_CERT_INFO" `
    --value "-----BEGIN CERTIFICATE-----MIIDgTCCAmmgAwIBAgIHkiG9w0...-----END CERTIFICATE-----" `
    --type "SecureString" `
    --description "KCP 서비스 인증서" `
    --overwrite

aws ssm put-parameter `
    --name "/snspmt/KCP_ENCRYPT_KEY" `
    --value "your_encrypt_key_here" `
    --type "SecureString" `
    --description "KCP 암호화 키" `
    --overwrite

# KCP API URLs
aws ssm put-parameter `
    --name "/snspmt/KCP_REGISTER_URL" `
    --value "https://testsmpay.kcp.co.kr/trade/register.do" `
    --type "String" `
    --description "KCP 거래등록 URL" `
    --overwrite

aws ssm put-parameter `
    --name "/snspmt/KCP_PAYMENT_URL" `
    --value "https://stg-spl.kcp.co.kr/gw/enc/v1/payment" `
    --type "String" `
    --description "KCP 결제요청 URL" `
    --overwrite

aws ssm put-parameter `
    --name "/snspmt/KCP_PAYMENT_SCRIPT" `
    --value "https://testspay.kcp.co.kr/plugin/kcp_spay_hub.js" `
    --type "String" `
    --description "KCP 결제창 스크립트 URL" `
    --overwrite

Write-Host "✅ KCP 파라미터 추가 완료!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 추가된 파라미터 목록:" -ForegroundColor Yellow
Write-Host "- /snspmt/KCP_SITE_CD"
Write-Host "- /snspmt/KCP_SITE_KEY"
Write-Host "- /snspmt/KCP_CERT_INFO"
Write-Host "- /snspmt/KCP_ENCRYPT_KEY"
Write-Host "- /snspmt/KCP_REGISTER_URL"
Write-Host "- /snspmt/KCP_PAYMENT_URL"
Write-Host "- /snspmt/KCP_PAYMENT_SCRIPT"
Write-Host ""
Write-Host "⚠️  주의: KCP_CERT_INFO와 KCP_ENCRYPT_KEY는 실제 값으로 업데이트해야 합니다." -ForegroundColor Red
