# Render.com 배포를 위한 WSGI 애플리케이션
from backend import app

# gunicorn your_application.wsgi 명령어에 대응
your_application = app

if __name__ == "__main__":
    app.run()
