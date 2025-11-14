# .env 파일 인코딩 오류 해결

## ❌ 오류

```
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xbe in position 80: invalid start byte
```

## 🔍 원인

`.env` 파일이 UTF-8이 아닌 다른 인코딩(Windows 기본 인코딩)으로 저장되어 발생한 문제입니다.

## ✅ 해결 방법

### 방법 1: PowerShell로 UTF-8로 재저장 (자동 수정됨)

이미 수정되었습니다. 다시 실행해보세요:

```bash
python backend.py
```

### 방법 2: 수동으로 UTF-8로 저장

1. `.env` 파일을 텍스트 에디터로 엽니다 (VS Code, Notepad++ 등)
2. **다른 이름으로 저장** 또는 **Save As**
3. **인코딩**을 **UTF-8**로 선택
4. 저장

### 방법 3: VS Code에서 수정

1. VS Code에서 `.env` 파일 열기
2. 우측 하단의 인코딩 표시 클릭 (예: "UTF-16 LE")
3. **"Save with Encoding"** 선택
4. **UTF-8** 선택

## ✅ 확인

수정 후:

```bash
python backend.py
```

성공 메시지:
```
✅ 환경 변수 검증 완료
🚀 SNS PMT 앱 시작 중...
✅ 데이터베이스 초기화 완료
```

## 🔍 참고

- Windows PowerShell의 `Set-Content`는 기본적으로 UTF-16을 사용할 수 있습니다
- `.env` 파일은 반드시 **UTF-8**로 저장해야 합니다
- `python-dotenv`는 UTF-8 인코딩을 기대합니다

