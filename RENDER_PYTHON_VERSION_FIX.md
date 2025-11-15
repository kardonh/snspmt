# Render Python 버전 설정 가이드

## 문제
Render가 `runtime.txt`와 `render.yml`을 무시하고 Python 3.13.4를 사용하고 있습니다.

## 해결 방법

### 방법 1: Render 대시보드에서 직접 설정 (권장)

1. Render 대시보드에 로그인
2. `snspmt-backend` 서비스 선택
3. **Settings** 탭으로 이동
4. **Environment** 섹션에서 **Python Version** 찾기
5. **Python Version**을 `3.12.8`로 설정
6. **Save Changes** 클릭
7. 서비스 재배포

### 방법 2: 환경 변수로 설정

Render 대시보드에서:
1. **Environment** 섹션으로 이동
2. **Add Environment Variable** 클릭
3. Key: `PYTHON_VERSION`
4. Value: `3.12.8`
5. **Save Changes** 클릭
6. 서비스 재배포

### 방법 3: buildCommand에서 Python 버전 강제

`render.yml`의 `buildCommand`를 수정:
```yaml
buildCommand: python3.12 -m pip install -r requirements.txt
```

## 현재 설정 확인

- `runtime.txt`: `python-3.12.8` ✅
- `render.yml`: `runtime: python-3.12.8` ✅
- `requirements.txt`: `psycopg2-binary>=2.9.11` ✅

## 참고

Render가 `runtime.txt`를 무시하는 경우, 대시보드에서 직접 설정하는 것이 가장 확실한 방법입니다.
