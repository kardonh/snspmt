#!/bin/bash

# Docker 실행 스크립트
# AWS 없이 Docker만으로 프로젝트 실행

set -e

echo "🚀 SNSPMT Docker 실행 스크립트"
echo "================================"

# .env 파일 확인
if [ ! -f .env ]; then
    echo "⚠️  .env 파일이 없습니다."
    echo "📝 .env.example을 복사하여 .env 파일을 생성하세요:"
    echo "   cp env.example .env"
    echo ""
    echo "그리고 .env 파일에 다음 설정을 추가하세요:"
    echo "  - DATABASE_URL"
    echo "  - SMMKINGS_API_KEY"
    echo "  - VITE_FIREBASE_API_KEY (필요시)"
    echo "  - KCP 설정 (필요시)"
    exit 1
fi

# Docker 및 Docker Compose 확인
if ! command -v docker &> /dev/null; then
    echo "❌ Docker가 설치되어 있지 않습니다."
    echo "   https://docs.docker.com/get-docker/ 에서 설치하세요."
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose가 설치되어 있지 않습니다."
    exit 1
fi

# Docker Compose 명령어 확인 (docker compose 또는 docker-compose)
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
else
    DOCKER_COMPOSE_CMD="docker-compose"
fi

echo "✅ Docker 환경 확인 완료"
echo ""

# 메뉴 선택
echo "실행할 작업을 선택하세요:"
echo "1) 전체 서비스 시작 (앱 + DB + Redis)"
echo "2) 데이터베이스만 시작"
echo "3) 데이터베이스 초기화 (스키마 생성)"
echo "4) 서비스 중지"
echo "5) 서비스 재시작"
echo "6) 로그 확인"
echo "7) 서비스 상태 확인"
echo "8) 전체 삭제 (데이터 포함)"
echo ""
read -p "선택 (1-8): " choice

case $choice in
    1)
        echo "🚀 전체 서비스 시작 중..."
        $DOCKER_COMPOSE_CMD up -d
        echo ""
        echo "✅ 서비스 시작 완료!"
        echo ""
        echo "📊 서비스 상태:"
        $DOCKER_COMPOSE_CMD ps
        echo ""
        echo "🌐 애플리케이션 접속: http://localhost:8000"
        echo "📝 로그 확인: $DOCKER_COMPOSE_CMD logs -f app"
        ;;
    2)
        echo "🗄️  데이터베이스만 시작 중..."
        $DOCKER_COMPOSE_CMD up -d db redis
        echo "✅ 데이터베이스 시작 완료!"
        ;;
    3)
        echo "🗄️  데이터베이스 초기화 중..."
        
        # 데이터베이스가 실행 중인지 확인
        if ! $DOCKER_COMPOSE_CMD ps db | grep -q "Up"; then
            echo "📦 데이터베이스 시작 중..."
            $DOCKER_COMPOSE_CMD up -d db
            echo "⏳ 데이터베이스 준비 대기 중..."
            sleep 5
        fi
        
        # 스키마 파일 확인 (PostgreSQL 버전 우선)
        if [ -f "DATABASE_SCHEMA_FINAL_POSTGRESQL.sql" ]; then
            echo "📝 DATABASE_SCHEMA_FINAL_POSTGRESQL.sql 실행 중..."
            $DOCKER_COMPOSE_CMD exec -T db psql -U postgres -d snspmt < DATABASE_SCHEMA_FINAL_POSTGRESQL.sql
            echo "✅ 스키마 생성 완료!"
        elif [ -f "DATABASE_SCHEMA_FINAL.sql" ]; then
            echo "📝 DATABASE_SCHEMA_FINAL.sql 실행 중..."
            $DOCKER_COMPOSE_CMD exec -T db psql -U postgres -d snspmt < DATABASE_SCHEMA_FINAL.sql
            echo "✅ 스키마 생성 완료!"
        elif [ -f "DATABASE_SCHEMA_OPTIMIZED.sql" ]; then
            echo "📝 DATABASE_SCHEMA_OPTIMIZED.sql 실행 중..."
            $DOCKER_COMPOSE_CMD exec -T db psql -U postgres -d snspmt < DATABASE_SCHEMA_OPTIMIZED.sql
            echo "✅ 스키마 생성 완료!"
        else
            echo "📝 백엔드 init_database() 함수 실행 중..."
            $DOCKER_COMPOSE_CMD run --rm app python -c "from backend import init_database; init_database()"
            echo "✅ 데이터베이스 초기화 완료!"
        fi
        ;;
    4)
        echo "⏹️  서비스 중지 중..."
        $DOCKER_COMPOSE_CMD stop
        echo "✅ 서비스 중지 완료!"
        ;;
    5)
        echo "🔄 서비스 재시작 중..."
        $DOCKER_COMPOSE_CMD restart
        echo "✅ 서비스 재시작 완료!"
        ;;
    6)
        echo "📋 로그 확인 (Ctrl+C로 종료)"
        $DOCKER_COMPOSE_CMD logs -f
        ;;
    7)
        echo "📊 서비스 상태:"
        $DOCKER_COMPOSE_CMD ps
        echo ""
        echo "📈 리소스 사용량:"
        docker stats --no-stream
        ;;
    8)
        echo "⚠️  경고: 모든 컨테이너와 데이터가 삭제됩니다!"
        read -p "정말 삭제하시겠습니까? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            echo "🗑️  서비스 및 데이터 삭제 중..."
            $DOCKER_COMPOSE_CMD down -v
            echo "✅ 삭제 완료!"
        else
            echo "❌ 취소되었습니다."
        fi
        ;;
    *)
        echo "❌ 잘못된 선택입니다."
        exit 1
        ;;
esac


# Docker 실행 스크립트
# AWS 없이 Docker만으로 프로젝트 실행

set -e

echo "🚀 SNSPMT Docker 실행 스크립트"
echo "================================"

# .env 파일 확인
if [ ! -f .env ]; then
    echo "⚠️  .env 파일이 없습니다."
    echo "📝 .env.example을 복사하여 .env 파일을 생성하세요:"
    echo "   cp env.example .env"
    echo ""
    echo "그리고 .env 파일에 다음 설정을 추가하세요:"
    echo "  - DATABASE_URL"
    echo "  - SMMKINGS_API_KEY"
    echo "  - VITE_FIREBASE_API_KEY (필요시)"
    echo "  - KCP 설정 (필요시)"
    exit 1
fi

# Docker 및 Docker Compose 확인
if ! command -v docker &> /dev/null; then
    echo "❌ Docker가 설치되어 있지 않습니다."
    echo "   https://docs.docker.com/get-docker/ 에서 설치하세요."
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose가 설치되어 있지 않습니다."
    exit 1
fi

# Docker Compose 명령어 확인 (docker compose 또는 docker-compose)
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
else
    DOCKER_COMPOSE_CMD="docker-compose"
fi

echo "✅ Docker 환경 확인 완료"
echo ""

# 메뉴 선택
echo "실행할 작업을 선택하세요:"
echo "1) 전체 서비스 시작 (앱 + DB + Redis)"
echo "2) 데이터베이스만 시작"
echo "3) 데이터베이스 초기화 (스키마 생성)"
echo "4) 서비스 중지"
echo "5) 서비스 재시작"
echo "6) 로그 확인"
echo "7) 서비스 상태 확인"
echo "8) 전체 삭제 (데이터 포함)"
echo ""
read -p "선택 (1-8): " choice

case $choice in
    1)
        echo "🚀 전체 서비스 시작 중..."
        $DOCKER_COMPOSE_CMD up -d
        echo ""
        echo "✅ 서비스 시작 완료!"
        echo ""
        echo "📊 서비스 상태:"
        $DOCKER_COMPOSE_CMD ps
        echo ""
        echo "🌐 애플리케이션 접속: http://localhost:8000"
        echo "📝 로그 확인: $DOCKER_COMPOSE_CMD logs -f app"
        ;;
    2)
        echo "🗄️  데이터베이스만 시작 중..."
        $DOCKER_COMPOSE_CMD up -d db redis
        echo "✅ 데이터베이스 시작 완료!"
        ;;
    3)
        echo "🗄️  데이터베이스 초기화 중..."
        
        # 데이터베이스가 실행 중인지 확인
        if ! $DOCKER_COMPOSE_CMD ps db | grep -q "Up"; then
            echo "📦 데이터베이스 시작 중..."
            $DOCKER_COMPOSE_CMD up -d db
            echo "⏳ 데이터베이스 준비 대기 중..."
            sleep 5
        fi
        
        # 스키마 파일 확인 (PostgreSQL 버전 우선)
        if [ -f "DATABASE_SCHEMA_FINAL_POSTGRESQL.sql" ]; then
            echo "📝 DATABASE_SCHEMA_FINAL_POSTGRESQL.sql 실행 중..."
            $DOCKER_COMPOSE_CMD exec -T db psql -U postgres -d snspmt < DATABASE_SCHEMA_FINAL_POSTGRESQL.sql
            echo "✅ 스키마 생성 완료!"
        elif [ -f "DATABASE_SCHEMA_FINAL.sql" ]; then
            echo "📝 DATABASE_SCHEMA_FINAL.sql 실행 중..."
            $DOCKER_COMPOSE_CMD exec -T db psql -U postgres -d snspmt < DATABASE_SCHEMA_FINAL.sql
            echo "✅ 스키마 생성 완료!"
        elif [ -f "DATABASE_SCHEMA_OPTIMIZED.sql" ]; then
            echo "📝 DATABASE_SCHEMA_OPTIMIZED.sql 실행 중..."
            $DOCKER_COMPOSE_CMD exec -T db psql -U postgres -d snspmt < DATABASE_SCHEMA_OPTIMIZED.sql
            echo "✅ 스키마 생성 완료!"
        else
            echo "📝 백엔드 init_database() 함수 실행 중..."
            $DOCKER_COMPOSE_CMD run --rm app python -c "from backend import init_database; init_database()"
            echo "✅ 데이터베이스 초기화 완료!"
        fi
        ;;
    4)
        echo "⏹️  서비스 중지 중..."
        $DOCKER_COMPOSE_CMD stop
        echo "✅ 서비스 중지 완료!"
        ;;
    5)
        echo "🔄 서비스 재시작 중..."
        $DOCKER_COMPOSE_CMD restart
        echo "✅ 서비스 재시작 완료!"
        ;;
    6)
        echo "📋 로그 확인 (Ctrl+C로 종료)"
        $DOCKER_COMPOSE_CMD logs -f
        ;;
    7)
        echo "📊 서비스 상태:"
        $DOCKER_COMPOSE_CMD ps
        echo ""
        echo "📈 리소스 사용량:"
        docker stats --no-stream
        ;;
    8)
        echo "⚠️  경고: 모든 컨테이너와 데이터가 삭제됩니다!"
        read -p "정말 삭제하시겠습니까? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            echo "🗑️  서비스 및 데이터 삭제 중..."
            $DOCKER_COMPOSE_CMD down -v
            echo "✅ 삭제 완료!"
        else
            echo "❌ 취소되었습니다."
        fi
        ;;
    *)
        echo "❌ 잘못된 선택입니다."
        exit 1
        ;;
esac



