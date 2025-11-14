# 📚 AGV Line Following Control 시스템 분석

## 1. 📦 라이브러리 및 모듈 임포트 소개

### 1.1 표준 라이브러리
```python
import time     # 시간 관리 및 제어 주기 설정
import curses   # 터미널 기반 사용자 인터페이스 (TUI)
```

### 1.2 커스텀 모듈
```python
from Donkibot_i import Comm  # AGV 통신 클래스 (자체 개발 모듈)
```

### 각 모듈의 역할과 특징

|        모듈       |                            주요 기능                     |         특징         |            용도             |
|------------------|---------------------------------------------------------|---------------------|-----------------------------|
| **`time`**       | `time.time()`, `time.sleep()`, `time.strftime()`        | 정밀한 타이밍 제어     | 50ms 제어 주기 관리          |
| **`curses`**     | `stdscr.getch()`, `stdscr.addstr()`, `stdscr.nodelay()` |    실시간 콘솔 UI     | 키보드 제어 및 상태 표시       |
| **`Donkibot_i`** |       `Comm` 클래스, `STSFrame` 데이터클래스               | 시리얼 통신 + 멀티스레딩 | AGV 센서 데이터 및 제어 명령 |

---

## 2. 🎯 SW 구현 목적

### **LCU(Line Control Unit) 기반 라인 추종 AGV 제어 시스템**

이 소프트웨어의 핵심 목적:

1. **자율 라인 추종**: LCU 센서로 라인을 감지하여 자동으로 경로 추종
2. **실시간 안전 시스템**: 비상정지, 장애물 감지를 통한 안전 운행
3. **사용자 제어 인터페이스**: 키보드를 통한 직관적인 AGV 제어
4. **교육용 플랫폼**: 라인 추종 알고리즘의 이해와 실습

### **산업 응용 분야**
- 🏭 **공장 자동화**: 자재 운반 AGV 시스템
- 📦 **물류 창고**: 자동 피킹 및 배송 로봇
- 🏥 **병원**: 의료용품/약품 자동 운반 시스템
- 🎓 **교육**: 로봇공학 및 제어공학 실습 도구

---

## 3. 🔧 주요 함수 및 사용한 AGV 데이터 분석

### 3.1 `draw_menu(stdscr)` - 메뉴 시스템
```python
def draw_menu(stdscr):
    """메인 메뉴를 화면에 그립니다."""
    global agv_running, agv_paused
    
    # 현재 상태 표시
    if agv_running and not agv_paused:
        status = "[ON] 라인 추종 활성화 중"
    elif agv_running and agv_paused:
        status = "[PAUSE] 일시정지 중" 
    else:
        status = "[OFF] 정지됨"
```

#### **특징**:
- 📊 **실시간 상태 표시**: AGV의 현재 동작 상태를 시각적으로 표시
- 🎮 **직관적 메뉴**: 모니터링과 제어 모드를 명확하게 분리
- 🔄 **전역 상태 관리**: `agv_running`, `agv_paused` 변수로 상태 추적

### 3.2 `display_data_mode(stdscr, agv)` - 실시간 모니터링

#### **사용 AGV 데이터 분석**:
```python
agv_status = agv.get_latest_data()

# 표시되는 센서 데이터
stdscr.addstr(4, 0, f"라인 위치        | {agv_status.LinePos:^10d}")      # 핵심 데이터
stdscr.addstr(5, 0, f"비상정지 플래그  | {agv_status.EmgFlag:^10d}")      # 안전 시스템
stdscr.addstr(6, 0, f"라이다 거리      | {agv_status.LidarDistance:^10d} mm")  # 장애물 감지
stdscr.addstr(11, 0, f"RF_tag1 INDEX    | {agv_status.RF_tag1:^10d}")     # 미션 관리
stdscr.addstr(12, 0, f"RF_tag2 제한속도 | {agv_status.RF_tag2:^10d} mm/s") # 속도 관리
```

### 3.3 `line_follow_control_mode(stdscr, agv)` ⭐ **핵심 제어 함수**

#### **제어 파라미터**:
```python
BASE_SPEED = 150                    # 기본 전진 속도
MAX_SPEED = 200                     # 최대 속도 제한
TURN_SPEED_DIFF = 50               # 회전시 바퀴 속도 차이
OBSTACLE_E_STOP_DISTANCE = 150     # 장애물 감지 임계값 (mm)
CONTROL_INTERVAL = 0.05            # 제어 주기 (50ms = 20Hz)
```

#### **키보드 제어 시스템**:
```python
# 실시간 키 입력 처리
if key in [ord('s'), ord('S')]:      # S: 시작/재개
    agv_running = True
    agv_paused = False
elif key in [ord('p'), ord('P')]:    # P: 일시정지
    agv_paused = True
    agv.CLR(0, 0)
elif key in [ord('x'), ord('X')]:    # X: 완전정지
    agv_running = False
    agv_paused = False
    agv.CLR(0, 0)
```

#### **핵심 센서 데이터 활용**:

| 센서 데이터 | 용도 | 범위/조건 | 제어 반응 |
|-------------|------|-----------|-----------|
| **`LinePos`** | 라인 위치 감지 | -15 ~ +15 | 주 제어 알고리즘 |
| **`EmgFlag`** | 비상정지 | 0/1 | 즉시 정지 |
| **`LidarDistance`** | 장애물 감지 | < 150mm | 안전 정지 |
| **`SOC`** | 배터리 상태 | 0-100% | 상태 모니터링 |
| **`Speed`** | 현재 속도 | mm/s | 피드백 제어 |
| **`RF_tag1/2`** | 위치 및 속도 제한 | 임의값 | 구간별 제어 |

---

## 4. 🧠 제어 알고리즘 설명

### 4.1 **안전 우선 순위 시스템**
```python
# 1순위: 비상정지
if s.EmgFlag == 1:
    vl, vr = 0, 0
    status_msg = "🚨 비상정지 활성화"

# 2순위: 장애물 감지
elif s.LidarDistance < OBSTACLE_E_STOP_DISTANCE:
    vl, vr = 0, 0
    status_msg = "🚧 장애물 감지 - 정지"
```

### 4.2 **라인 추종 제어 알고리즘** 🎯

#### **핵심 아이디어**: LinePos 값에 따른 차동 구동 제어

```python
line_pos = s.LinePos  # -15(왼쪽) ~ 0(중앙) ~ +15(오른쪽)

if abs(line_pos) > 8:
    # ±8 초과: 제자리 회전 (Pivot Turn)
    if line_pos < -8:
        vl = -TURN_SPEED_DIFF  # 좌바퀴 후진
        vr = TURN_SPEED_DIFF   # 우바퀴 전진
        # → 제자리 좌회전
    else:
        vl = TURN_SPEED_DIFF   # 좌바퀴 전진
        vr = -TURN_SPEED_DIFF  # 우바퀴 후진
        # → 제자리 우회전

elif line_pos == 0:
    # 중앙: 직진
    vl = BASE_SPEED
    vr = BASE_SPEED

else:
    # ±8 이하: 부드러운 회전 (Differential Steering)
    turn_intensity = abs(line_pos) / 8.0  # 0~1 정규화
    speed_reduction = int(TURN_SPEED_DIFF * turn_intensity)
    
    if line_pos < 0:  # 라인이 왼쪽에 위치
        vl = BASE_SPEED - speed_reduction  # 좌바퀴 감속
        vr = BASE_SPEED                    # 우바퀴 정속
        # → 부드러운 좌회전
    else:  # 라인이 오른쪽에 위치
        vl = BASE_SPEED                    # 좌바퀴 정속
        vr = BASE_SPEED - speed_reduction  # 우바퀴 감속
        # → 부드러운 우회전
```

### 4.3 **제어 알고리즘 시각화**

```
LinePos 값에 따른 제어 전략:

┌─────────────────────────────────────────────────────────┐
│  -15    -8    -4    0    +4    +8    +15               │
│   │      │     │     │     │     │      │               │
│   └──────┼─────┼─────┼─────┼─────┼──────┘               │
│         제자리  부드러운   직진  부드러운   제자리         │
│         좌회전   좌회전          우회전    우회전         │
└─────────────────────────────────────────────────────────┘

제어 방식:
1. |LinePos| > 8: 제자리 회전 (Pivot Turn)
2. |LinePos| ≤ 8: 차등 속도 제어 (Differential Steering)
3. LinePos = 0: 직진 주행
```

### 4.4 **수학적 모델링**

#### **부드러운 회전 공식**:
```
turn_intensity = |LinePos| / 8.0  (0 ≤ turn_intensity ≤ 1)
speed_reduction = TURN_SPEED_DIFF × turn_intensity

if LinePos < 0:  // 왼쪽 편향
    vl = BASE_SPEED - speed_reduction
    vr = BASE_SPEED
else:  // 오른쪽 편향
    vl = BASE_SPEED
    vr = BASE_SPEED - speed_reduction
```

#### **제자리 회전 공식**:
```
if LinePos < -8:  // 심한 왼쪽 편향
    vl = -TURN_SPEED_DIFF
    vr = +TURN_SPEED_DIFF
else:  // 심한 오른쪽 편향
    vl = +TURN_SPEED_DIFF
    vr = -TURN_SPEED_DIFF
```

### 4.5 **라인 위치 시각화**
```python
# 실시간 라인 위치 표시
line_visual = "L" + "=" * 15 + "C" + "=" * 15 + "R"
marker_pos = 15 + s.LinePos + 1
marker_line = " " * marker_pos + "^"
stdscr.addstr(18, 4, line_visual)
stdscr.addstr(19, 4, marker_line)

# 출력 예시:
# L===============C===============R
#                     ^  (LinePos = +3일 때)
```

---

## 5. 📋 분석 요약 설명

### 5.1 시스템 아키텍처
```
AGV Line Following Control System
│
├── 🎮 사용자 인터페이스 계층
│   ├── 메뉴 시스템 (상태 표시)
│   ├── 실시간 데이터 모니터링
│   ├── 키보드 제어 인터페이스
│   └── 시각적 피드백 (라인 위치 표시)
│
├── 🧠 제어 알고리즘 계층
│   ├── 안전 우선순위 시스템
│   ├── 라인 추종 알고리즘
│   ├── 차동 구동 제어
│   └── 실시간 제어 루프 (50ms)
│
├── 📊 센서 데이터 처리 계층
│   ├── LinePos 기반 주 제어
│   ├── LiDAR 장애물 감지
│   ├── 비상정지 시스템
│   └── 배터리 및 속도 모니터링
│
└── 📡 하드웨어 통신 계층
    ├── 시리얼 통신 (Donkibot_i)
    ├── 실시간 데이터 수신
    ├── 제어 명령 전송 (CLR)
    └── 멀티스레딩 처리
```

### 5.2 핵심 기술 요소

#### **🎓 제어공학 개념**
1. **PD 제어와 유사**: 위치 오차(LinePos)에 비례한 제어 출력
2. **차동 구동 제어**: 두 바퀴의 속도 차이로 방향 제어
3. **실시간 제어**: 50ms 주기의 정밀한 타이밍 제어
4. **상태 기반 제어**: 다양한 조건에 따른 제어 모드 전환

#### **🤖 로봇공학 개념**
1. **센서 융합**: 다중 센서(LinePos, LiDAR, EMG) 통합 활용
2. **안전 시스템**: 계층적 안전 우선순위 구조
3. **사용자 인터페이스**: 실시간 모니터링 및 제어
4. **하드웨어 추상화**: 시리얼 통신을 통한 하드웨어 제어

#### **💻 소프트웨어 기법**
1. **실시간 프로그래밍**: 정확한 제어 주기 관리
2. **상태 머신**: agv_running, agv_paused 상태 관리
3. **예외 처리**: 견고한 오류 대응 시스템
4. **사용자 경험**: 직관적인 키보드 인터페이스

### 5.3 교육적 가치

#### **학습 목표**:
- ✅ **라인 추종 알고리즘**: 기본적인 자율주행 개념 이해
- ✅ **차동 구동 제어**: 로봇 이동 메커니즘 학습
- ✅ **실시간 제어**: 제어 주기와 안정성의 중요성
- ✅ **안전 시스템**: 로봇 시스템의 안전 설계 원칙

#### **실무 연결성**:
- 🚗 **자율주행차**: 차선 유지 보조 시스템 (LKA)
- 🏭 **산업용 AGV**: 공장 자동화 라인
- 📦 **물류 로봇**: 창고 자동화 시스템
- 🎓 **교육용 로봇**: STEM 교육 플랫폼

### 5.4 확장 가능성

#### **알고리즘 개선**:
```python
# PID 제어로 업그레이드
class PIDController:
    def __init__(self, kp=1.0, ki=0.1, kd=0.05):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.prev_error = 0
        self.integral = 0
    
    def compute(self, error, dt):
        self.integral += error * dt
        derivative = (error - self.prev_error) / dt
        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        self.prev_error = error
        return output
```

#### **센서 융합**:
```python
# 다중 센서 가중치 제어
def sensor_fusion(line_pos, tfs_angle, camera_offset):
    weights = [0.7, 0.2, 0.1]  # LinePos, TFS, Camera
    fused_error = (weights[0] * line_pos + 
                   weights[1] * tfs_angle + 
                   weights[2] * camera_offset)
    return fused_error
```

### 5.5 성능 지표

#### **제어 성능**:
- ⏱️ **응답 시간**: 50ms 제어 주기로 빠른 반응
- 🎯 **정확도**: ±8 범위 내에서 부드러운 제어
- 🛡️ **안전성**: 다층 안전 시스템 구축
- 📊 **가시성**: 실시간 상태 모니터링

---

## 결론

이 프로그램은 **실제 산업용 AGV의 라인 추종 시스템**을 충실히 구현한 것으로, 자율주행 로봇의 핵심 기술인 **경로 추종, 센서 융합, 실시간 제어**를 종합적으로 학습할 수 있는 excellent한 교육 자료입니다! 🚗🤖🎯✨

---

**문서 생성일**: 2025년 11월 3일  
**분석 대상**: agv_line_follow_control.py  
**프로젝트**: AGV Line Follow Control System  