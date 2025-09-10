import os
import tempfile
import tempfile as tf

# 메모리 기반 임시 디렉토리 설정
def setup_temp_directories():
    """메모리 기반 임시 디렉토리 설정"""
    try:
        # 메모리 기반 임시 디렉토리 생성
        temp_dir = tempfile.mkdtemp(prefix='gunicorn_')
        print(f"메모리 기반 임시 디렉토리 생성 성공: {temp_dir}")
        
        # 환경 변수 설정
        os.environ['TMPDIR'] = temp_dir
        os.environ['TEMP'] = temp_dir
        os.environ['TMP'] = temp_dir
        
        # tempfile 모듈 재설정
        tempfile.tempdir = temp_dir
        
        return temp_dir
    except Exception as e:
        print(f"메모리 기반 임시 디렉토리 생성 실패: {e}")
        # 폴백: 시스템 기본 임시 디렉토리 사용
        return None

# 임시 디렉토리 설정 실행
temp_dir = setup_temp_directories()

# Gunicorn 설정 (메모리 최적화)
bind = "0.0.0.0:8000"
workers = 1  # 워커 수 최소화로 메모리 절약
timeout = 60  # 타임아웃 단축
worker_class = "sync"
preload_app = True
max_requests = 1000  # 워커 재시작으로 메모리 누수 방지
max_requests_jitter = 100
worker_connections = 1000
keepalive = 2
# worker_tmp_dir 제거 - 메모리 기반 임시 디렉토리 사용

def on_starting(server):
    """서버 시작 시 실행"""
    print("Gunicorn 서버 시작 중...")
    setup_temp_directories()

def worker_int(worker):
    """워커 인터럽트 시 실행"""
    print(f"워커 {worker.pid} 인터럽트됨")

def worker_abort(worker):
    """워커 중단 시 실행"""
    print(f"워커 {worker.pid} 중단됨")
