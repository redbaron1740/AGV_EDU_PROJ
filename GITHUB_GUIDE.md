# GitHub 사용 가이드 (초보자용)

## 📚 목차
1. [기본 개념](#기본-개념)
2. [처음 시작하기](#처음-시작하기)
3. [코드 올리기 (Push)](#코드-올리기-push)
4. [코드 가져오기 (Pull/Clone)](#코드-가져오기-pullclone)
5. [자주 사용하는 명령어](#자주-사용하는-명령어)
6. [문제 해결](#문제-해결)

---

## 기본 개념

### Git이란?
- 코드의 변경 이력을 관리하는 버전 관리 시스템
- 로컬 컴퓨터에서 작동

### GitHub란?
- Git 저장소를 온라인에 저장하는 서비스
- 코드 공유, 협업, 백업 가능

### 주요 용어
- **Repository (저장소)**: 프로젝트 폴더
- **Commit**: 변경사항 저장
- **Push**: 로컬 → GitHub 업로드
- **Pull**: GitHub → 로컬 다운로드
- **Clone**: 저장소 전체 복사

---

## 처음 시작하기

### 1. Git 설치 확인
```bash
git --version
```

### 2. 사용자 정보 설정 (최초 1회)
```bash
git config --global user.name "당신의이름"
git config --global user.email "your.email@example.com"
```

### 3. GitHub 계정 만들기
- https://github.com 에서 가입

---

## 코드 올리기 (Push)

### 방법 1: 새 프로젝트 시작

#### Step 1: 로컬에서 Git 초기화
```bash
cd /path/to/your/project
git init
git branch -m main
```

#### Step 2: 파일 추가 및 커밋
```bash
# 모든 파일 추가
git add .

# 또는 특정 파일만 추가
git add 파일이름.py

# 커밋 (변경사항 저장)
git commit -m "설명 메시지"
```

#### Step 3: GitHub에 저장소 만들기
1. https://github.com/new 접속
2. Repository name 입력
3. "Create repository" 클릭

#### Step 4: GitHub에 연결 및 푸시
```bash
# GitHub 저장소 연결
git remote add origin https://github.com/사용자명/저장소명.git

# 코드 업로드
git push -u origin main
```

### 방법 2: 기존 프로젝트 업데이트

```bash
cd /path/to/your/project

# 1. 변경된 파일 확인
git status

# 2. 파일 추가
git add .

# 3. 커밋
git commit -m "무엇을 변경했는지 설명"

# 4. 푸시
git push
```

---

## 코드 가져오기 (Pull/Clone)

### Clone: 처음 저장소 복사하기
```bash
# GitHub에서 프로젝트 전체 복사
git clone https://github.com/사용자명/저장소명.git

# 특정 폴더로 복사
git clone https://github.com/사용자명/저장소명.git 폴더이름
```

### Pull: 최신 변경사항 받기
```bash
cd /path/to/your/project

# GitHub에서 최신 코드 받기
git pull
```

### 실전 예제
```bash
# 1. 다른 컴퓨터에서 작업 시작
git clone https://github.com/redbaron1740/AGV_EDU_PROJ.git
cd AGV_EDU_PROJ

# 2. 코드 수정 후
git add .
git commit -m "수정 내용"
git push

# 3. 원래 컴퓨터에서 최신 코드 받기
cd /home/orangepi/KOPO_CLASS/Workspaces
git pull
```

---

## 자주 사용하는 명령어

### 기본 명령어
```bash
# 현재 상태 확인
git status

# 변경 이력 보기
git log
git log --oneline    # 한 줄로 보기

# 원격 저장소 확인
git remote -v

# 브랜치 확인
git branch
```

### 파일 관리
```bash
# 파일 추가
git add 파일명
git add .              # 모든 파일

# 파일 삭제
git rm 파일명

# 파일 이름 변경
git mv 옛이름 새이름

# 특정 파일 되돌리기
git checkout -- 파일명
```

### 커밋 관리
```bash
# 마지막 커밋 수정
git commit --amend -m "새로운 메시지"

# 커밋 취소 (파일은 유지)
git reset HEAD~1

# 모든 변경사항 취소 (주의!)
git reset --hard HEAD
```

---

## 문제 해결

### 문제 1: "Permission denied" 에러
```bash
# SSH 키 대신 HTTPS 사용
git remote set-url origin https://github.com/사용자명/저장소명.git
```

### 문제 2: Push가 거부됨 (rejected)
```bash
# GitHub에 새로운 변경사항이 있을 때
git pull --rebase
git push
```

### 문제 3: 충돌 (Conflict) 발생
```bash
# 1. 충돌 파일 확인
git status

# 2. 파일을 열어서 충돌 부분 수정
# (<<<<<<, =======, >>>>>> 표시된 부분)

# 3. 수정 후 추가 및 커밋
git add 충돌파일
git commit -m "충돌 해결"
git push
```

### 문제 4: 실수로 잘못 커밋함
```bash
# 마지막 커밋 취소 (파일은 유지)
git reset --soft HEAD~1

# 다시 커밋
git add .
git commit -m "올바른 메시지"
```

### 문제 5: .gitignore 추가 후 반영 안됨
```bash
# 캐시 삭제 후 다시 추가
git rm -r --cached .
git add .
git commit -m "gitignore 적용"
```

---

## 실전 시나리오

### 시나리오 1: 집에서 작업, 학교에서 이어하기

**집에서:**
```bash
cd /my/project
git add .
git commit -m "집에서 작업한 내용"
git push
```

**학교에서:**
```bash
# 처음이면
git clone https://github.com/사용자명/저장소명.git

# 이미 있으면
cd /my/project
git pull

# 작업 후
git add .
git commit -m "학교에서 작업한 내용"
git push
```

### 시나리오 2: 실수로 중요한 파일 삭제
```bash
# 최신 커밋으로 복구
git checkout HEAD -- 파일명

# 특정 커밋에서 복구
git checkout 커밋해시 -- 파일명
```

### 시나리오 3: 다른 사람의 프로젝트 사용
```bash
# 1. Fork (GitHub 웹에서)
# 2. 내 저장소로 Clone
git clone https://github.com/내계정/프로젝트명.git

# 3. 원본 저장소 추가
git remote add upstream https://github.com/원작자/프로젝트명.git

# 4. 원본 업데이트 받기
git fetch upstream
git merge upstream/main
```

---

## .gitignore 사용하기

### .gitignore 파일 만들기
```bash
# 프로젝트 루트에 생성
touch .gitignore
```

### 자주 사용하는 .gitignore 예시
```gitignore
# Python
__pycache__/
*.py[cod]
*.so
.venv/
venv/

# 로그 파일
*.log

# 백업 파일
*.bak
*.tar
*.zip

# 운영체제
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
```

---

## 유용한 팁

### 1. 별칭(Alias) 만들기
```bash
git config --global alias.st status
git config --global alias.cm commit
git config --global alias.co checkout

# 사용: git st (git status 대신)
```

### 2. 예쁘게 로그 보기
```bash
git log --graph --oneline --all --decorate
```

### 3. 특정 파일의 변경 이력 보기
```bash
git log --follow 파일명
```

### 4. 누가 어떤 줄을 수정했는지 보기
```bash
git blame 파일명
```

---

## 빠른 참조 카드

| 작업 | 명령어 |
|------|--------|
| 저장소 복사 | `git clone URL` |
| 상태 확인 | `git status` |
| 파일 추가 | `git add .` |
| 커밋 | `git commit -m "메시지"` |
| 업로드 | `git push` |
| 다운로드 | `git pull` |
| 이력 보기 | `git log` |
| 차이 보기 | `git diff` |

---

## 더 배우고 싶다면

- **GitHub 공식 가이드**: https://guides.github.com/
- **Git 공식 문서**: https://git-scm.com/doc
- **시각적 Git 배우기**: https://learngitbranching.js.org/

---

**💡 기억하세요:**
- 자주 커밋하세요 (작은 단위로)
- 의미 있는 커밋 메시지를 작성하세요
- 중요한 작업 전에는 백업하세요
- 궁금하면 `git status`로 확인하세요!
