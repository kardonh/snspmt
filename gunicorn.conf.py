import os
import tempfile

# 임시 디렉토리 설정
def setup_temp_directories():
    """임시 디렉토리 설정"""
    # 쓰기 가능한 디렉토리만 시도
    temp_dirs = ['/app/var']
    for temp_dir in temp_dirs:
        try:
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir, exist_ok=True)
            # 권한 설정
            os.chmod(temp_dir, 0o777)
            print(f"임시 디렉토리 생성 성공: {temp_dir}")
        except Exception as e:
            print(f"임시 디렉토리 생성 실패 {temp_dir}: {e}")
    
    # 환경 변수 설정 (쓰기 가능한 디렉토리 우선)
    os.environ['TMPDIR'] = '/app/var'
    os.environ['TEMP'] = '/app/var'
    os.environ['TMP'] = '/app/var'
    
    # tempfile 모듈 재설정
    tempfile.tempdir = '/app/var'

# 임시 디렉토리 설정 실행
setup_temp_directories()

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
worker_tmp_dir = "/app/var"  # 임시 디렉토리 명시적 설정

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
