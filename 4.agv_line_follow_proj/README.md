# AGV Line Follow Project

카메라 기반 라인 트레이싱 자동 주행 시스템입니다.

## 📁 프로젝트 구조

```
4.agv_line_follow_proj/
├── agv_line_follow_control.py    # 라인 추종 제어 프로그램
├── agv_state_disp.py             # 상태 디스플레이
├── Donkibot_i.py                 # AGV 하드웨어 인터페이스
├── AGV_Line_Follow_Control_Analysis.md   # 상세 분석 문서
├── AGV_Line_Follow_Control_Analysis.html # 분석 문서 (HTML)
└── README.md
```

## 🚀 주요 기능

- **라인 인식**: 카메라를 통한 라인 감지
- **PID 제어**: 정밀한 라인 추종 제어
- **실시간 상태 표시**: AGV 상태 모니터링
- **자동 주행**: 라인을 따라 자율 주행

## 💻 실행 방법

```bash
python agv_line_follow_control.py
```

## 📖 학습 자료

- `AGV_Line_Follow_Control_Analysis.md` - 제어 알고리즘 상세 분석
- PID 제어 파라미터 튜닝 가이드 포함

## 📝 개발 환경

- Python 3.x
- RealSense Camera
- OpenCV
- Donkibot AGV 하드웨어

## 📄 라이선스

Educational Use Only
