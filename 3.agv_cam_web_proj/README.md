# AGV Camera Web Project

RealSense 카메라 웹 스트리밍 및 오버레이 시스템입니다.

## 📁 프로젝트 구조

```
3.agv_cam_web_proj/
├── Sever.py                 # 웹 서버 (카메라 + 제어)
├── Sever_only_video.py      # 비디오 전용 서버
├── realsense_cam.py         # RealSense 카메라 인터페이스
├── rs_cam_overlay.py        # 카메라 오버레이 처리
├── rs_cam_test.py           # 카메라 테스트
├── Donkibot_i.py            # AGV 하드웨어 인터페이스
└── README.md
```

## 🚀 주요 기능

- **실시간 비디오 스트리밍**: RealSense 카메라 영상을 웹으로 스트리밍
- **오버레이 기능**: 영상에 정보 표시
- **원격 제어**: 웹 인터페이스를 통한 AGV 제어
- **Depth 정보**: 깊이 센서 데이터 활용

## 💻 실행 방법

```bash
# 전체 기능 서버
python Sever.py

# 비디오 전용 서버
python Sever_only_video.py

# 카메라 테스트
python rs_cam_test.py
```

## 📝 개발 환경

- Python 3.x
- Intel RealSense Camera
- Flask (웹 서버)
- OpenCV

## 📄 라이선스

Educational Use Only
