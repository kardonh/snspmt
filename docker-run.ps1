# Docker 실행 스크립트 (PowerShell)
# AWS 없이 Docker만으로 프로젝트 실행

Write-Host "🚀 SNSPMT Docker 실행 스크립트" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# .env 파일 확인
if (-not (Test-Path .env)) {
    Write-Host "⚠️  .env 파일이 없습니다." -ForegroundColor Yellow
    Write-Host "📝 .env.example을 복사하여 .env 파일을 생성하세요:" -ForegroundColor Yellow
    Write-Host "   Copy-Item env.example .env" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "그리고 .env 파일에 다음 설정을 추가하세요:" -ForegroundColor Yellow
    Write-Host "  - DATABASE_URL" -ForegroundColor Yellow
    Write-Host "  - SMMKINGS_API_KEY" -ForegroundColor Yellow
    Write-Host "  - VITE_FIREBASE_API_KEY (필요시)" -ForegroundColor Yellow
    Write-Host "  - KCP 설정 (필요시)" -ForegroundColor Yellow
    exit 1
}

# Docker 확인
try {
    docker --version | Out-Null
} catch {
    Write-Host "❌ Docker가 설치되어 있지 않습니다." -ForegroundColor Red
    Write-Host "   https://docs.docker.com/get-docker/ 에서 설치하세요." -ForegroundColor Red
    exit 1
}

# Docker Compose 명령어 확인
$dockerComposeCmd = "docker compose"
try {
    docker compose version | Out-Null
} catch {
    $dockerComposeCmd = "docker-compose"
    try {
        docker-compose --version | Out-Null
    } catch {
        Write-Host "❌ Docker Compose가 설치되어 있지 않습니다." -ForegroundColor Red
        exit 1
    }
}

Write-Host "✅ Docker 환경 확인 완료" -ForegroundColor Green
Write-Host ""

# 메뉴 선택
Write-Host "실행할 작업을 선택하세요:" -ForegroundColor Cyan
Write-Host "1) 전체 서비스 시작 (앱 + DB + Redis)"
Write-Host "2) 데이터베이스만 시작"
Write-Host "3) 데이터베이스 초기화 (스키마 생성)"
Write-Host "4) 서비스 중지"
Write-Host "5) 서비스 재시작"
Write-Host "6) 로그 확인"
Write-Host "7) 서비스 상태 확인"
Write-Host "8) 전체 삭제 (데이터 포함)"
Write-Host ""
$choice = Read-Host "선택 (1-8)"

switch ($choice) {
    "1" {
        Write-Host "🚀 전체 서비스 시작 중..." -ForegroundColor Cyan
        Invoke-Expression "$dockerComposeCmd up -d"
        Write-Host ""
        Write-Host "✅ 서비스 시작 완료!" -ForegroundColor Green
        Write-Host ""
        Write-Host "📊 서비스 상태:" -ForegroundColor Cyan
        Invoke-Expression "$dockerComposeCmd ps"
        Write-Host ""
        Write-Host "🌐 애플리케이션 접속: http://localhost:8000" -ForegroundColor Green
        Write-Host "📝 로그 확인: $dockerComposeCmd logs -f app" -ForegroundColor Yellow
    }
    "2" {
        Write-Host "🗄️  데이터베이스만 시작 중..." -ForegroundColor Cyan
        Invoke-Expression "$dockerComposeCmd up -d db redis"
        Write-Host "✅ 데이터베이스 시작 완료!" -ForegroundColor Green
    }
    "3" {
        Write-Host "🗄️  데이터베이스 초기화 중..." -ForegroundColor Cyan
        
        # 데이터베이스가 실행 중인지 확인
        $dbStatus = Invoke-Expression "$dockerComposeCmd ps db" | Select-String "Up"
        if (-not $dbStatus) {
            Write-Host "📦 데이터베이스 시작 중..." -ForegroundColor Yellow
            Invoke-Expression "$dockerComposeCmd up -d db"
            Write-Host "⏳ 데이터베이스 준비 대기 중..." -ForegroundColor Yellow
            Start-Sleep -Seconds 5
        }
        
        # 스키마 파일 확인 (PostgreSQL 버전 우선)
        if (Test-Path "DATABASE_SCHEMA_FINAL_POSTGRESQL.sql") {
            Write-Host "📝 DATABASE_SCHEMA_FINAL_POSTGRESQL.sql 실행 중..." -ForegroundColor Cyan
            Get-Content DATABASE_SCHEMA_FINAL_POSTGRESQL.sql | docker exec -i (docker-compose ps -q db) psql -U postgres -d snspmt
            Write-Host "✅ 스키마 생성 완료!" -ForegroundColor Green
        } elseif (Test-Path "DATABASE_SCHEMA_FINAL.sql") {
            Write-Host "📝 DATABASE_SCHEMA_FINAL.sql 실행 중..." -ForegroundColor Cyan
            Get-Content DATABASE_SCHEMA_FINAL.sql | docker exec -i (docker-compose ps -q db) psql -U postgres -d snspmt
            Write-Host "✅ 스키마 생성 완료!" -ForegroundColor Green
        } elseif (Test-Path "DATABASE_SCHEMA_OPTIMIZED.sql") {
            Write-Host "📝 DATABASE_SCHEMA_OPTIMIZED.sql 실행 중..." -ForegroundColor Cyan
            Get-Content DATABASE_SCHEMA_OPTIMIZED.sql | docker exec -i (docker-compose ps -q db) psql -U postgres -d snspmt
            Write-Host "✅ 스키마 생성 완료!" -ForegroundColor Green
        } else {
            Write-Host "📝 백엔드 init_database() 함수 실행 중..." -ForegroundColor Cyan
            Invoke-Expression "$dockerComposeCmd run --rm app python -c 'from backend import init_database; init_database()'"
            Write-Host "✅ 데이터베이스 초기화 완료!" -ForegroundColor Green
        }
    }
    "4" {
        Write-Host "⏹️  서비스 중지 중..." -ForegroundColor Cyan
        Invoke-Expression "$dockerComposeCmd stop"
        Write-Host "✅ 서비스 중지 완료!" -ForegroundColor Green
    }
    "5" {
        Write-Host "🔄 서비스 재시작 중..." -ForegroundColor Cyan
        Invoke-Expression "$dockerComposeCmd restart"
        Write-Host "✅ 서비스 재시작 완료!" -ForegroundColor Green
    }
    "6" {
        Write-Host "📋 로그 확인 (Ctrl+C로 종료)" -ForegroundColor Cyan
        Invoke-Expression "$dockerComposeCmd logs -f"
    }
    "7" {
        Write-Host "📊 서비스 상태:" -ForegroundColor Cyan
        Invoke-Expression "$dockerComposeCmd ps"
        Write-Host ""
        Write-Host "📈 리소스 사용량:" -ForegroundColor Cyan
        docker stats --no-stream
    }
    "8" {
        Write-Host "⚠️  경고: 모든 컨테이너와 데이터가 삭제됩니다!" -ForegroundColor Red
        $confirm = Read-Host "정말 삭제하시겠습니까? (yes/no)"
        if ($confirm -eq "yes") {
            Write-Host "🗑️  서비스 및 데이터 삭제 중..." -ForegroundColor Yellow
            Invoke-Expression "$dockerComposeCmd down -v"
            Write-Host "✅ 삭제 완료!" -ForegroundColor Green
        } else {
            Write-Host "❌ 취소되었습니다." -ForegroundColor Red
        }
    }
    default {
        Write-Host "❌ 잘못된 선택입니다." -ForegroundColor Red
        exit 1
    }
}



Write-Host "🚀 SNSPMT Docker 실행 스크립트" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# .env 파일 확인
if (-not (Test-Path .env)) {
    Write-Host "⚠️  .env 파일이 없습니다." -ForegroundColor Yellow
    Write-Host "📝 .env.example을 복사하여 .env 파일을 생성하세요:" -ForegroundColor Yellow
    Write-Host "   Copy-Item env.example .env" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "그리고 .env 파일에 다음 설정을 추가하세요:" -ForegroundColor Yellow
    Write-Host "  - DATABASE_URL" -ForegroundColor Yellow
    Write-Host "  - SMMKINGS_API_KEY" -ForegroundColor Yellow
    Write-Host "  - VITE_FIREBASE_API_KEY (필요시)" -ForegroundColor Yellow
    Write-Host "  - KCP 설정 (필요시)" -ForegroundColor Yellow
    exit 1
}

# Docker 확인
try {
    docker --version | Out-Null
} catch {
    Write-Host "❌ Docker가 설치되어 있지 않습니다." -ForegroundColor Red
    Write-Host "   https://docs.docker.com/get-docker/ 에서 설치하세요." -ForegroundColor Red
    exit 1
}

# Docker Compose 명령어 확인
$dockerComposeCmd = "docker compose"
try {
    docker compose version | Out-Null
} catch {
    $dockerComposeCmd = "docker-compose"
    try {
        docker-compose --version | Out-Null
    } catch {
        Write-Host "❌ Docker Compose가 설치되어 있지 않습니다." -ForegroundColor Red
        exit 1
    }
}

Write-Host "✅ Docker 환경 확인 완료" -ForegroundColor Green
Write-Host ""

# 메뉴 선택
Write-Host "실행할 작업을 선택하세요:" -ForegroundColor Cyan
Write-Host "1) 전체 서비스 시작 (앱 + DB + Redis)"
Write-Host "2) 데이터베이스만 시작"
Write-Host "3) 데이터베이스 초기화 (스키마 생성)"
Write-Host "4) 서비스 중지"
Write-Host "5) 서비스 재시작"
Write-Host "6) 로그 확인"
Write-Host "7) 서비스 상태 확인"
Write-Host "8) 전체 삭제 (데이터 포함)"
Write-Host ""
$choice = Read-Host "선택 (1-8)"

switch ($choice) {
    "1" {
        Write-Host "🚀 전체 서비스 시작 중..." -ForegroundColor Cyan
        Invoke-Expression "$dockerComposeCmd up -d"
        Write-Host ""
        Write-Host "✅ 서비스 시작 완료!" -ForegroundColor Green
        Write-Host ""
        Write-Host "📊 서비스 상태:" -ForegroundColor Cyan
        Invoke-Expression "$dockerComposeCmd ps"
        Write-Host ""
        Write-Host "🌐 애플리케이션 접속: http://localhost:8000" -ForegroundColor Green
        Write-Host "📝 로그 확인: $dockerComposeCmd logs -f app" -ForegroundColor Yellow
    }
    "2" {
        Write-Host "🗄️  데이터베이스만 시작 중..." -ForegroundColor Cyan
        Invoke-Expression "$dockerComposeCmd up -d db redis"
        Write-Host "✅ 데이터베이스 시작 완료!" -ForegroundColor Green
    }
    "3" {
        Write-Host "🗄️  데이터베이스 초기화 중..." -ForegroundColor Cyan
        
        # 데이터베이스가 실행 중인지 확인
        $dbStatus = Invoke-Expression "$dockerComposeCmd ps db" | Select-String "Up"
        if (-not $dbStatus) {
            Write-Host "📦 데이터베이스 시작 중..." -ForegroundColor Yellow
            Invoke-Expression "$dockerComposeCmd up -d db"
            Write-Host "⏳ 데이터베이스 준비 대기 중..." -ForegroundColor Yellow
            Start-Sleep -Seconds 5
        }
        
        # 스키마 파일 확인 (PostgreSQL 버전 우선)
        if (Test-Path "DATABASE_SCHEMA_FINAL_POSTGRESQL.sql") {
            Write-Host "📝 DATABASE_SCHEMA_FINAL_POSTGRESQL.sql 실행 중..." -ForegroundColor Cyan
            Get-Content DATABASE_SCHEMA_FINAL_POSTGRESQL.sql | docker exec -i (docker-compose ps -q db) psql -U postgres -d snspmt
            Write-Host "✅ 스키마 생성 완료!" -ForegroundColor Green
        } elseif (Test-Path "DATABASE_SCHEMA_FINAL.sql") {
            Write-Host "📝 DATABASE_SCHEMA_FINAL.sql 실행 중..." -ForegroundColor Cyan
            Get-Content DATABASE_SCHEMA_FINAL.sql | docker exec -i (docker-compose ps -q db) psql -U postgres -d snspmt
            Write-Host "✅ 스키마 생성 완료!" -ForegroundColor Green
        } elseif (Test-Path "DATABASE_SCHEMA_OPTIMIZED.sql") {
            Write-Host "📝 DATABASE_SCHEMA_OPTIMIZED.sql 실행 중..." -ForegroundColor Cyan
            Get-Content DATABASE_SCHEMA_OPTIMIZED.sql | docker exec -i (docker-compose ps -q db) psql -U postgres -d snspmt
            Write-Host "✅ 스키마 생성 완료!" -ForegroundColor Green
        } else {
            Write-Host "📝 백엔드 init_database() 함수 실행 중..." -ForegroundColor Cyan
            Invoke-Expression "$dockerComposeCmd run --rm app python -c 'from backend import init_database; init_database()'"
            Write-Host "✅ 데이터베이스 초기화 완료!" -ForegroundColor Green
        }
    }
    "4" {
        Write-Host "⏹️  서비스 중지 중..." -ForegroundColor Cyan
        Invoke-Expression "$dockerComposeCmd stop"
        Write-Host "✅ 서비스 중지 완료!" -ForegroundColor Green
    }
    "5" {
        Write-Host "🔄 서비스 재시작 중..." -ForegroundColor Cyan
        Invoke-Expression "$dockerComposeCmd restart"
        Write-Host "✅ 서비스 재시작 완료!" -ForegroundColor Green
    }
    "6" {
        Write-Host "📋 로그 확인 (Ctrl+C로 종료)" -ForegroundColor Cyan
        Invoke-Expression "$dockerComposeCmd logs -f"
    }
    "7" {
        Write-Host "📊 서비스 상태:" -ForegroundColor Cyan
        Invoke-Expression "$dockerComposeCmd ps"
        Write-Host ""
        Write-Host "📈 리소스 사용량:" -ForegroundColor Cyan
        docker stats --no-stream
    }
    "8" {
        Write-Host "⚠️  경고: 모든 컨테이너와 데이터가 삭제됩니다!" -ForegroundColor Red
        $confirm = Read-Host "정말 삭제하시겠습니까? (yes/no)"
        if ($confirm -eq "yes") {
            Write-Host "🗑️  서비스 및 데이터 삭제 중..." -ForegroundColor Yellow
            Invoke-Expression "$dockerComposeCmd down -v"
            Write-Host "✅ 삭제 완료!" -ForegroundColor Green
        } else {
            Write-Host "❌ 취소되었습니다." -ForegroundColor Red
        }
    }
    default {
        Write-Host "❌ 잘못된 선택입니다." -ForegroundColor Red
        exit 1
    }
}



