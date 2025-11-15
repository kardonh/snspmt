# Render 빌드 명령 설정 가이드

## 현재 문제
Render 대시보드의 빌드 명령이 `pip install -r requirements.txt`만 실행하고 있어서 프론트엔드(`dist` 폴더)가 생성되지 않습니다.

## 해결 방법

### 방법 1: Render 대시보드에서 직접 수정 (권장)

Render 대시보드의 **빌드 명령** 필드를 다음으로 변경:

```bash
npm install && npm run build && pip install -r requirements.txt
```

**설정 위치**:
1. Render 대시보드 → `snspmt-backend` 서비스 선택
2. **Settings** 탭
3. **Build Command** 필드 수정
4. **Save Changes** 클릭

### 방법 2: render.yml 사용 (자동 배포)

`render.yml` 파일이 있으면 자동으로 적용됩니다. 현재 설정:

```yaml
buildCommand: |
  which node || (curl -fsSL https://deb.nodesource.com/setup_18.x | sudo bash - && sudo apt-get install -y nodejs) || echo "Node.js 설치 실패, 프론트엔드 빌드 스킵"
  npm install && npm run build || echo "프론트엔드 빌드 실패, 계속 진행"
  pip install -r requirements.txt
```

### 방법 3: Node.js 설치 확인

Render의 Python 환경에 Node.js가 없을 수 있습니다. 다음 명령으로 확인:

```bash
which node || echo "Node.js 없음"
```

Node.js가 없다면:
1. **사전 배포 명령**에 Node.js 설치 추가:
   ```bash
   curl -fsSL https://deb.nodesource.com/setup_18.x | sudo bash - && sudo apt-get install -y nodejs
   ```

2. 또는 **빌드 명령**에 포함:
   ```bash
   (which node || (curl -fsSL https://deb.nodesource.com/setup_18.x | sudo bash - && sudo apt-get install -y nodejs)) && npm install && npm run build && pip install -r requirements.txt
   ```

## 권장 빌드 명령

### 최소 버전 (Node.js가 이미 있는 경우)
```bash
npm install && npm run build && pip install -r requirements.txt
```

### 안전한 버전 (Node.js 설치 포함)
```bash
(which node || (curl -fsSL https://deb.nodesource.com/setup_18.x | sudo bash - && sudo apt-get install -y nodejs)) && npm install && npm run build && pip install -r requirements.txt
```

### 오류 허용 버전 (빌드 실패해도 계속 진행)
```bash
npm install && npm run build || echo "프론트엔드 빌드 실패" && pip install -r requirements.txt
```

## 확인 방법

배포 후 로그에서 다음을 확인:
1. `npm install` 실행 여부
2. `npm run build` 실행 여부
3. `dist` 폴더 생성 여부
4. 정적 파일 404 오류 해결 여부

## 문제 해결

### Node.js 설치 실패
- Render의 Python 환경에서는 `sudo` 권한이 없을 수 있습니다
- 이 경우 `dist` 폴더를 Git에 포함시키는 방법을 고려하세요

### 프론트엔드 빌드 실패
- `package.json`의 `build` 스크립트 확인
- `vite.config.js` 설정 확인
- 빌드 로그에서 오류 메시지 확인

## 대안: dist 폴더를 Git에 포함

만약 Render에서 Node.js 설치가 계속 실패한다면:

1. `.gitignore`에서 `dist/` 제거
2. 로컬에서 `npm run build` 실행
3. `dist` 폴더를 Git에 커밋
4. Render는 빌드 없이 배포

**주의**: 이 방법은 빌드된 파일이 Git에 포함되므로 저장소 크기가 커집니다.

