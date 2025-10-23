#!/bin/bash

# AWS 비용 최적화 적용 스크립트
echo "💰 AWS 비용 최적화 적용 시작..."

# 1. 최적화된 태스크 정의 등록
echo "📋 최적화된 태스크 정의 등록 중..."
aws ecs register-task-definition --cli-input-json file://optimized-task-definition.json

if [ $? -eq 0 ]; then
    echo "✅ 최적화된 태스크 정의 등록 완료"
else
    echo "❌ 태스크 정의 등록 실패"
    exit 1
fi

# 2. ECS 서비스 업데이트
echo "🔄 ECS 서비스 업데이트 중..."
aws ecs update-service \
    --cluster snspmt-cluster-ultimate \
    --service snspmt-service \
    --task-definition snspmt-task:latest

if [ $? -eq 0 ]; then
    echo "✅ ECS 서비스 업데이트 완료"
else
    echo "❌ ECS 서비스 업데이트 실패"
    exit 1
fi

# 3. 비용 모니터링 설정
echo "📊 비용 모니터링 설정 중..."

# CloudWatch 비용 알람 생성
aws cloudwatch put-metric-alarm \
    --alarm-name "snspmt-daily-cost-alarm" \
    --alarm-description "일일 비용이 $30을 초과하면 알림" \
    --metric-name EstimatedCharges \
    --namespace AWS/Billing \
    --statistic Maximum \
    --period 86400 \
    --threshold 30.0 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 1

echo "✅ 비용 최적화 적용 완료!"
echo "📊 예상 비용 절약: $100-150/월"
echo "🎯 목표 월 비용: $600-650"
