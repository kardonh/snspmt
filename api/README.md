# API Routes 폴더

이 폴더는 `backend.py`에서 분리된 API 라우트들을 저장합니다.

## 사용 방법

### 1. 새로운 API 파일 생성

새로운 파일을 만들고 Blueprint를 사용합니다:

```python
from flask import Blueprint, request, jsonify

# Blueprint 생성
my_api_bp = Blueprint('my_api', __name__, url_prefix='/api/my-api')

@my_api_bp.route('/endpoint', methods=['GET'])
def my_endpoint():
    return jsonify({'message': 'Hello'}), 200
```

### 2. backend.py에 등록

`backend.py`의 Blueprint 등록 부분에 추가:

```python
from api.my_api_file import my_api_bp
app.register_blueprint(my_api_bp)
```

## 예시 파일

- `example_routes.py`: Blueprint 사용 예시

## 주의사항

- 데이터베이스 연결 함수는 각 파일에서 정의하거나 `backend.py`에서 import
- Swagger 문서화를 위해 docstring을 작성하세요
- 에러 처리를 반드시 포함하세요

