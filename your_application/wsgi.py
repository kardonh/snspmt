# your_application 패키지의 WSGI 애플리케이션
from . import your_application

# gunicorn your_application.wsgi 명령어에 대응
app = your_application

if __name__ == "__main__":
    app.run()
