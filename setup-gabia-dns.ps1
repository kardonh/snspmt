# 가비아 DNS 설정 스크립트 (PowerShell)
# 소셜리티.co.kr 및 sociality.co.kr 도메인 연결

Write-Host "🌐 가비아 DNS 설정 시작..." -ForegroundColor Green

# 환경 변수 설정
$DOMAIN_MAIN = "소셜리티.co.kr"
$DOMAIN_SUB = "sociality.co.kr"
$ALB_DNS = "snspmt-alb-new-404094515.ap-northeast-2.elb.amazonaws.com"

Write-Host "📋 설정 정보:" -ForegroundColor Yellow
Write-Host "  메인 도메인: $DOMAIN_MAIN" -ForegroundColor White
Write-Host "  부도메인: $DOMAIN_SUB" -ForegroundColor White
Write-Host "  ALB DNS: $ALB_DNS" -ForegroundColor White

Write-Host ""
Write-Host "📝 가비아 DNS 설정 방법:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1️⃣ 가비아 마이페이지 접속" -ForegroundColor Yellow
Write-Host "   https://mypage.gabia.com" -ForegroundColor Blue
Write-Host ""
Write-Host "2️⃣ 도메인 관리 → 소셜리티.co.kr 선택" -ForegroundColor Yellow
Write-Host ""
Write-Host "3️⃣ DNS 관리 → DNS 레코드 관리" -ForegroundColor Yellow
Write-Host ""
Write-Host "4️⃣ 다음 레코드 추가:" -ForegroundColor Yellow
Write-Host ""

Write-Host "   📍 메인 도메인 설정:" -ForegroundColor Green
Write-Host "   타입: CNAME" -ForegroundColor White
Write-Host "   호스트: @" -ForegroundColor White
Write-Host "   값: $ALB_DNS" -ForegroundColor White
Write-Host "   TTL: 300" -ForegroundColor White
Write-Host ""

Write-Host "   📍 부도메인 설정:" -ForegroundColor Green
Write-Host "   타입: CNAME" -ForegroundColor White
Write-Host "   호스트: sociality" -ForegroundColor White
Write-Host "   값: 소셜리티.co.kr" -ForegroundColor White
Write-Host "   TTL: 300" -ForegroundColor White
Write-Host ""

Write-Host "5️⃣ DNS 전파 대기 (최대 24시간)" -ForegroundColor Yellow
Write-Host ""
Write-Host "6️⃣ 도메인 연결 테스트:" -ForegroundColor Yellow
Write-Host "   Test-NetConnection -ComputerName $DOMAIN_MAIN -Port 80" -ForegroundColor Cyan
Write-Host "   Test-NetConnection -ComputerName $DOMAIN_SUB -Port 80" -ForegroundColor Cyan
Write-Host ""

Write-Host "⚠️  주의사항:" -ForegroundColor Red
Write-Host "   - 가비아에서 DNS 설정 후 전파까지 시간이 걸립니다" -ForegroundColor White
Write-Host "   - ALB 보안 그룹에서 80/443 포트가 열려있어야 합니다" -ForegroundColor White
Write-Host "   - SSL 인증서는 별도로 설정해야 합니다" -ForegroundColor White
Write-Host ""

Write-Host "🔗 유용한 링크:" -ForegroundColor Magenta
Write-Host "   - 가비아 DNS 관리: https://mypage.gabia.com" -ForegroundColor Blue
Write-Host "   - DNS 전파 확인: https://www.whatsmydns.net" -ForegroundColor Blue
Write-Host "   - SSL 인증서: Let's Encrypt 또는 가비아 SSL 서비스" -ForegroundColor Blue
