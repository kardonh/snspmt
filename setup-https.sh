#!/bin/bash

# HTTPS 설정 스크립트
echo "🔒 HTTPS 설정 시작..."

# 1. ALB DNS 이름 가져오기
ALB_DNS=$(aws elbv2 describe-load-balancers --query 'LoadBalancers[?contains(LoadBalancerName, `snspmt-alb-final`)].DNSName' --output text)
echo "ALB DNS: $ALB_DNS"

# 2. HTTPS 리스너 생성 (기본 인증서 사용)
aws elbv2 create-listener \
    --load-balancer-arn arn:aws:elasticloadbalancing:ap-northeast-2:868812195478:loadbalancer/app/snspmt-alb-final/0cf09e1f2ff6454c \
    --protocol HTTPS \
    --port 443 \
    --certificates CertificateArn=arn:aws:acm:ap-northeast-2:868812195478:certificate/$(aws acm list-certificates --query 'CertificateSummaryList[0].CertificateArn' --output text | cut -d'/' -f2) \
    --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:ap-northeast-2:868812195478:targetgroup/snspmt-tg-final-v2/1d7527595f425331

echo "✅ HTTPS 리스너 생성 완료!"
echo "🌐 HTTPS URL: https://$ALB_DNS"
