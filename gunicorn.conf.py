import os
import tempfile

# 임시 디렉토리 설정
def setup_temp_directories():
    """임시 디렉토리 설정"""
    temp_dirs = ['/tmp', '/var/tmp', '/usr/tmp', '/app/tmp']
    for temp_dir in temp_dirs:
        try:
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir, exist_ok=True)
        except Exception as e:
            print(f"임시 디렉토리 생성 실패 {temp_dir}: {e}")
    
    # 환경 변수 설정
    os.environ['TMPDIR'] = '/tmp'
    os.environ['TEMP'] = '/tmp'
    os.environ['TMP'] = '/tmp'
    
    # tempfile 모듈 재설정
    tempfile.tempdir = '/tmp'

# 임시 디렉토리 설정 실행
setup_temp_directories()

# Gunicorn 설정
bind = "0.0.0.0:8000"
workers = 4
timeout = 120
worker_class = "sync"
preload_app = True

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
