# AGV Educational Projects (AGV_EDU_PROJ)

한국폴리텍대학 AGV(Automated Guided Vehicle) 교육용 프로젝트 모음입니다.

## 📚 프로젝트 구성

### 1️⃣ AGV Basic Project (`1.agv_basic_proj/`)
- **목적**: AGV 기본 제어 학습
- **주요 기능**: 키보드를 통한 수동 제어
- **파일**: `agv_keyboard.py`, `Donkibot_i.py`

### 2️⃣ AGV TFS Project (`2.agv_tfs_proj/`)
- **목적**: Traffic Sign Following System
- **주요 기능**: 교통 신호 인식 및 제어
- **파일**: `agv_tfs_control.py`, `agv_tfs_lat_control.py`, `agv_tfs_long_control.py`

### 3️⃣ AGV Camera Web Project (`3.agv_cam_web_proj/`)
- **목적**: RealSense 카메라 웹 스트리밍
- **주요 기능**: 카메라 영상 실시간 스트리밍, 오버레이
- **파일**: `Sever.py`, `realsense_cam.py`, `rs_cam_overlay.py`

### 4️⃣ AGV Line Follow Project (`4.agv_line_follow_proj/`)
- **목적**: 라인 트레이싱 자동 주행
- **주요 기능**: 카메라 기반 라인 인식 및 추종
- **파일**: `agv_line_follow_control.py`, `agv_state_disp.py`

### 5️⃣ AGV RF-Tag Monitor & Control Project (`5.agv_RF-tag_monitor_ctrl_proj/`)
- **목적**: RF 태그 기반 미션 수행 시스템
- **주요 기능**: 태그 인식, 경로 추적, 미션 실행
- **파일**: `agv_station_server.py`, `agv_control_client_simple.py`, `mission_planning.py`

## 🚀 시작하기

각 프로젝트 폴더로 이동하여 README.md를 참조하세요.

```bash
cd 1.agv_basic_proj
python agv_keyboard.py
```

## 💻 개발 환경

- **Python**: 3.x
- **하드웨어**: Donkibot AGV Platform
- **센서**: RealSense Camera, RF Tag Reader

## 📝 학습 순서 (권장)

1. **1.agv_basic_proj** - AGV 기본 조작 익히기
2. **3.agv_cam_web_proj** - 카메라 시스템 이해하기
3. **4.agv_line_follow_proj** - 자동 주행 알고리즘 학습
4. **2.agv_tfs_proj** - 신호 인식 시스템 구현
5. **5.agv_RF-tag_monitor_ctrl_proj** - 통합 미션 수행

## 📄 라이선스

Educational Use Only - Korea Polytechnic University

## 👥 기여자

- 한국폴리텍대학 AGV 교육 과정

---

**Note**: 각 프로젝트의 상세 설명은 해당 프로젝트 폴더의 README.md를 참조하세요.
