# Python 버전 호환성 문제 해결

## ❌ 발생한 오류

```
ImportError: /opt/render/project/src/.venv/lib/python3.13/site-packages/psycopg2/_psycopg.cpython-313-x86_64-linux-gnu.so: 정의되지 않은 심볼: _PyInterpreterState_Get
```

## 🔍 원인

Python 3.13은 매우 최신 버전이며, `psycopg2-binary==2.9.7`이 아직 완전히 지원하지 않습니다.

## ✅ 해결 방법

Python 버전을 3.12.8로 다운그레이드했습니다.

### 변경된 파일
- `runtime.txt`: `python-3.12.8`
- `render.yml`: `PYTHON_VERSION: 3.12.8`

## 📋 Render 대시보드에서도 확인

Render 대시보드 → Settings → Environment Variables에서:
- `PYTHON_VERSION` 환경변수가 `3.12.8`로 설정되어 있는지 확인
- 없으면 추가하거나 기존 값을 업데이트

## 🔄 다음 배포

다음 배포 시 Python 3.12.8이 사용되어 psycopg2-binary와 정상적으로 작동할 것입니다.

---

**참고**: Python 3.12는 psycopg2-binary와 완전히 호환되며 안정적입니다.

