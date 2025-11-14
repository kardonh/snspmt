# Render Python 버전 설정 가이드

## ❌ 현재 문제

Render가 여전히 Python 3.13.4를 사용하고 있어 `psycopg2-binary`와 호환성 문제가 발생합니다.

## ✅ 해결 방법: Render 대시보드에서 Python 버전 설정

### 1단계: Render 대시보드 접속
1. https://dashboard.render.com 접속
2. `snspmt` 프로젝트 선택

### 2단계: Settings 탭으로 이동
- 왼쪽 메뉴에서 **Settings** 탭 클릭

### 3단계: Python Version 설정
1. **Python Version** 섹션 찾기
2. 현재 값: `3.13.4` (또는 비어있음)
3. 다음 값으로 변경:
   ```
   3.12.8
   ```
4. **Save Changes** 클릭

### 4단계: 재배포
- Render가 자동으로 Python 3.12.8로 재배포를 시작합니다
- 배포 완료까지 몇 분 소요

## 📋 대안: 환경변수로 설정

Settings → Environment Variables에서:
- **Key**: `PYTHON_VERSION`
- **Value**: `3.12.8`
- **Save Changes** 클릭

## ✅ 확인 방법

배포 완료 후 로그에서:
```
==> Python 버전 3.12.8 설치 중 ...
==> Python 버전 3.12.8 사용
```

이 메시지가 보이면 성공!

## 🔍 참고

- `runtime.txt` 파일도 `python-3.12.8`로 설정되어 있습니다
- 하지만 Render 대시보드 설정이 우선 적용됩니다
- 두 곳 모두 설정하는 것을 권장합니다

---

**지금 할 일**: Render 대시보드 → Settings → Python Version을 `3.12.8`로 변경하세요!

