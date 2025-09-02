#!/bin/bash

# AWS 도메인 설정 스크립트
# 소셜리티.co.kr 및 sociality.co.kr 도메인 연결

set -e

echo "🌐 AWS 도메인 설정 시작..."

# 환경 변수 설정
DOMAIN_MAIN="소셜리티.co.kr"
DOMAIN_SUB="sociality.co.kr"
REGION="ap-northeast-2"
ACCOUNT_ID="868812195478"
ALB_NAME="snspmt-alb-new"

echo "📋 설정 정보:"
echo "  메인 도메인: $DOMAIN_MAIN"
echo "  부도메인: $DOMAIN_SUB"
echo "  리전: $REGION"
echo "  계정 ID: $ACCOUNT_ID"
echo "  ALB 이름: $ALB_NAME"

# 1. Route 53 호스팅 영역 생성
echo "📝 Route 53 호스팅 영역 생성 중..."
HOSTED_ZONE_ID=$(aws route53 create-hosted-zone \
  --name "$DOMAIN_MAIN" \
  --caller-reference "$(date +%s)" \
  --region $REGION \
  --query 'HostedZone.Id' \
  --output text | sed 's/\/hostedzone\///')

echo "✅ 호스팅 영역 생성 완료: $HOSTED_ZONE_ID"

# 2. ALB 정보 가져오기
echo "🔍 ALB 정보 조회 중..."
ALB_ARN=$(aws elbv2 describe-load-balancers \
  --names $ALB_NAME \
  --region $REGION \
  --query 'LoadBalancers[0].LoadBalancerArn' \
  --output text)

ALB_DNS=$(aws elbv2 describe-load-balancers \
  --names $ALB_NAME \
  --region $REGION \
  --query 'LoadBalancers[0].DNSName' \
  --output text)

echo "✅ ALB 정보: $ALB_DNS"

# 3. SSL 인증서 요청
echo "🔒 SSL 인증서 요청 중..."
CERT_ARN=$(aws acm request-certificate \
  --domain-name "$DOMAIN_MAIN" \
  --subject-alternative-names "$DOMAIN_SUB" "*.${DOMAIN_MAIN}" "*.${DOMAIN_SUB}" \
  --validation-method DNS \
  --region $REGION \
  --query 'CertificateArn' \
  --output text)

echo "✅ SSL 인증서 요청 완료: $CERT_ARN"

# 4. DNS 검증 정보 출력
echo "📋 DNS 검증 정보:"
aws acm describe-certificate \
  --certificate-arn $CERT_ARN \
  --region $REGION \
  --query 'Certificate.DomainValidationOptions[].ResourceRecord' \
  --output table

# 5. A 레코드 생성 (메인 도메인)
echo "📝 A 레코드 생성 중..."
aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch "{
    \"Changes\": [
      {
        \"Action\": \"CREATE\",
        \"ResourceRecordSet\": {
          \"Name\": \"$DOMAIN_MAIN\",
          \"Type\": \"A\",
          \"AliasTarget\": {
            \"HostedZoneId\": \"ZWKZPGTI48KDX\",
            \"DNSName\": \"$ALB_DNS\",
            \"EvaluateTargetHealth\": true
          }
        }
      }
    ]
  }"

# 6. CNAME 레코드 생성 (부도메인)
echo "📝 CNAME 레코드 생성 중..."
aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch "{
    \"Changes\": [
      {
        \"Action\": \"CREATE\",
        \"ResourceRecordSet\": {
          \"Name\": \"$DOMAIN_SUB\",
          \"Type\": \"CNAME\",
          \"TTL\": 300,
          \"ResourceRecords\": [
            {
              \"Value\": \"$DOMAIN_MAIN\"
            }
          ]
        }
      }
    ]
  }"

echo "✅ 도메인 설정 완료!"
echo ""
echo "📋 다음 단계:"
echo "1. DNS 검증 완료까지 대기 (최대 24시간)"
echo "2. SSL 인증서 상태 확인:"
echo "   aws acm describe-certificate --certificate-arn $CERT_ARN --region $REGION"
echo "3. 도메인 연결 테스트:"
echo "   curl -I http://$DOMAIN_MAIN"
echo "   curl -I http://$DOMAIN_SUB"
echo ""
echo "🔗 호스팅 영역 ID: $HOSTED_ZONE_ID"
echo "🔒 인증서 ARN: $CERT_ARN"
