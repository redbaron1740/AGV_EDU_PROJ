# AGV 시스템 빠른 참조 가이드 (Quick Reference)

> 📌 **빠른 문제 해결 및 설정 변경 가이드**

---

## 🚀 빠른 시작

```bash
# 1. 서버 실행 (터미널 1)
cd /home/omorobot/KOPO_CLASS/Workspaces/5.agv_RF-tag_monitor_ctrl_proj
python3 agv_station_server.py

# 2. 클라이언트 실행 (터미널 2)
python3 agv_control_client_simple.py

# 3. 브라우저 열기
http://localhost:5000
```

---

## ⚙️ 주요 설정 변경

### 속도 조정

#### 1. 기본 주행 속도 변경
**파일**: `agv_control_client_simple.py`  
**위치**: 라인 ~365
```python
base_speed = 150  # 기본 주행 속도 (mm/s)
                  # 권장: 100-200
```

#### 2. 웹 AGV 애니메이션 속도 변경
**파일**: `templates/index.html`  
**위치**: 라인 ~285
```javascript
AGV_ANIMATION_SPEED_BASE: 3.0  // 기준 속도
                                // 느림: 1.5, 보통: 3.0, 빠름: 6.0
```

#### 3. 태그별 속도 제한 변경
**파일**: `agv_station_server.py`  
**위치**: 라인 ~120
```python
tag_nums = {
    1: {'x': 1491, 'y': 620, 'speed_limit': 200},
    4: {'x': 680, 'y': 248, 'speed_limit': 150},  # ← 여기 수정
    # ...
}
```

---

### 라인 트레이싱 조정

#### 1. 급회전 감지 임계값
**파일**: `agv_control_client_simple.py`  
**위치**: 라인 ~373
```python
if abs(line_pos) > 12:  # Sharp turn 임계값
                        # 낮음: 8, 보통: 12, 높음: 15
```

#### 2. 조향 보정 강도
**파일**: `agv_control_client_simple.py`  
**위치**: 라인 ~380
```python
max_correction = int(effective_speed * 0.3)  # 30% 제한
correction = min(int(abs(line_pos) * 8), max_correction)
                                    # ↑ 게인 (권장: 5-10)
```

---

### 장애물 감지 조정

**파일**: `agv_control_client_simple.py`  
**위치**: 라인 ~42
```python
OBSTACLE_THRESHOLD = 150          # 긴급정지 거리 (mm)
OBSTACLE_RECOVERY_THRESHOLD = 300 # 복구 거리 (mm)
OBSTACLE_RECOVERY_TIME = 2.0      # 복구 대기 시간 (초)
```

---

## 🐛 문제 해결

### 문제 1: 왼쪽 커브에서 라인을 잃어버림
**해결책**:
```python
# agv_control_client_simple.py, 라인 ~373
if abs(line_pos) > 12:  # 값을 높임 (12 → 15)
```

---

### 문제 2: AGV가 너무 느림
**해결책**:
```python
# agv_control_client_simple.py, 라인 ~365
base_speed = 150  # 값을 높임 (150 → 180)

# mission_planning.py, 모든 태그에서
set_max_speed(200)  # 최대값 사용
```

---

### 문제 3: 급회전에서 정지함
**해결책**:
```python
# agv_station_server.py, 급회전 태그 속도 증가
4: {'x': 680, 'y': 248, 'speed_limit': 150},  # 150 → 180
```

---

### 문제 4: 웹 AGV가 실제 AGV와 동기화 안 됨 (Phase 8 완료)
**증상**:
- Tag 10에서 정지해도 웹 AGV 계속 움직임
- 점프(Jump) 안 됨 (1, 2번만 작동)
- 대기(Wait) 안 됨
- 상태 패널이 IDLE 고정

**해결 완료** ✅:
1. **실행 순서 수정** (라인 395~465)
   ```javascript
   // 0. 상태 패널 업데이트
   // 1. 센서 태그 동기화
   // 2. 라인 트레이싱 상태 확인
   // 3. AGV 상태 변경
   // 4. 애니메이션 업데이트
   ```

2. **tag_nums 키 타입 수정**
   ```javascript
   // Before: tag_nums[3] → undefined
   // After: tag_nums["3"] → 정상
   const tagPos = tag_nums[sensorTagId.toString()];
   ```

3. **대기 로직 추가** (라인 760~780)
   ```javascript
   // 서버 AGV가 다음 태그 도착 시
   if (currentSensorTag < nextServerTag) {
       waitingForTag = true;
       isAnimating = false;
   }
   ```

**F12 콘솔 정상 로그**:
```
📡 센서: 0 → 1, 서버: 0
⚡ 점프: Tag 1 (1491, 620)
🚩 서버 AGV가 Tag 2에 도착
⏳ 대기 시작: 서버 Tag 2 도착, 센서는 Tag 1
📡 센서: 1 → 2, 서버: 2
✅ 대기 해제: Tag 2
```

**아직도 안 되면**:
- 브라우저 강력 새로고침 (Ctrl+Shift+R)
- 서버 재시작
- F12 콘솔 에러 확인

---

### 문제 5: Tag 10에서 정지 안 함
**해결책**:
```python
# mission_planning.py, Tag 10 확인
if tag_id == 10:
    pause_line_tracing()  # 이 줄이 있는지 확인
    return {"status": "completed", "action": "pause", "speed": 0}
```

**웹 AGV도 정지하는지 확인**:
```javascript
// F12 콘솔에서 확인
// ⏸️ 라인 트레이싱 중단  ← 이 로그가 나와야 함
```

---

### 문제 6: E-Stop 상태가 표시 안 됨
**해결책**:
- 서버와 클라이언트 모두 재시작
- 브라우저 F12 → Network 탭에서 `/update` 호출 확인

---

## 🔧 디버깅 도구

### Curses 디버그 모드 활성화
**파일**: `agv_control_client_simple.py`  
**위치**: 라인 ~78
```python
USE_CURSES = True  # False → True
```

**주의**: CPU 사용률 증가 (디버깅 시에만 사용)

---

### 브라우저 콘솔 로그
**F12 → Console 탭**에서 확인 가능한 로그:
- `✅ Tag 위치 정보 로드`
- `📡 센서 태그 업데이트`
- `⚡ 점프 완료` / `⏳ 대기 시작` / `✅ 대기 해제`
- `⏸️ 라인 트레이싱 중단`
- `▶️ 라인 트레이싱 재개`

---

## 📝 Mission Planning 예제

### 예제 1: 특정 태그에서 속도 제한
```python
# mission_planning.py
def execute_mission(tag_id, agv_comm, tag2_speed):
    if tag_id == 5:
        set_max_speed(120)  # 느린 속도로 주행
        return {"status": "success", "action": "continue"}
```

---

### 예제 2: 특정 태그에서 2초 정지
```python
def execute_mission(tag_id, agv_comm, tag2_speed):
    if tag_id == 4:
        pause_line_tracing()      # 정지
        time.sleep(2)
        resume_line_tracing()     # 재개
        return {"status": "success", "action": "continue"}
```

---

### 예제 3: 조건부 임무
```python
def execute_mission(tag_id, agv_comm, tag2_speed):
    if tag_id == 7:
        # 배터리가 낮으면 느리게
        if agv_comm.get_battery() < 30:
            set_max_speed(100)
        else:
            set_max_speed(200)
        
        return {"status": "success", "action": "continue"}
```

---

## 🎯 성능 튜닝 팁

### 1. 최적 속도 조합
```python
# 안정성 우선
base_speed = 120
tag4_limit = 120

# 균형
base_speed = 150  # ← 권장
tag4_limit = 150  # ← 권장

# 속도 우선
base_speed = 180
tag4_limit = 180
```

---

### 2. 조향 튜닝
```python
# 부드러운 조향 (느린 반응)
correction = int(abs(line_pos) * 5)

# 적극적 조향 (빠른 반응)
correction = int(abs(line_pos) * 10)

# 균형 (권장)
correction = int(abs(line_pos) * 8)  # ← 권장
```

---

### 3. 장애물 감지 튜닝
```python
# 보수적 (멀리서 정지)
OBSTACLE_THRESHOLD = 200
OBSTACLE_RECOVERY_THRESHOLD = 400

# 공격적 (가까이서 정지)
OBSTACLE_THRESHOLD = 100
OBSTACLE_RECOVERY_THRESHOLD = 200

# 균형 (권장)
OBSTACLE_THRESHOLD = 150           # ← 권장
OBSTACLE_RECOVERY_THRESHOLD = 300  # ← 권장
```

---

## 📊 주요 파일 위치

```
```
5.agv_RF-tag_monitor_ctrl_proj/
├── agv_station_server.py           # 서버 (State Machine)
│   ├── 라인 120: tag_nums (태그 위치/속도)
│   └── 라인 500: State Machine 상태 전이
│
├── agv_control_client_simple.py    # 클라이언트 (라인 트레이싱)
│   ├── 라인 42: 장애물 임계값
│   ├── 라인 74: mission_max_speed
│   ├── 라인 365: base_speed
│   ├── 라인 373: Sharp turn 임계값
│   └── 라인 380: 조향 보정 게인
│
├── mission_planning.py             # Mission Planning
│   └── 라인 55+: execute_mission() 함수
│
└── templates/index.html            # 웹 대시보드 (Phase 8 재구현)
    ├── 라인 285: 애니메이션 속도 (AGV_ANIMATION_SPEED_BASE = 3.0)
    ├── 라인 395~465: updateAgvData() 함수
    │   ├── 라인 398: 상태 패널 업데이트 (0단계)
    │   ├── 라인 408: 센서 태그 동기화 (1단계)
    │   ├── 라인 438: 라인 트레이싱 상태 (2단계)
    │   ├── 라인 447: AGV 상태 변경 (3단계)
    │   └── 라인 450: 애니메이션 업데이트 (4단계)
    │
    └── 라인 760~780: updateAGVAnimation() - 서버 태그 도착 시 대기 로직
```

---

## 🔍 로그 확인 방법

### 서버 로그 (터미널)
```
✅ AGV 하드웨어 연결 성공
🚀 AGV 제어 루프 시작
🎯 Tag X 임무 시작
⚠️ 장애물 감지! 거리: XXXmm
✅ 장애물 제거 확인 - 주행 재개
```

### 웹 AGV 로그 (F12 콘솔) - Phase 8 추가
```
✅ Tag 위치 정보 로드: 10개
📡 센서: 0 → 1, 서버: 0
⚡ 점프: Tag 1 (1491, 620)
🚩 서버 AGV가 Tag 2에 도착
⏳ 대기 시작: 서버 Tag 2 도착, 센서는 Tag 1
📡 센서: 1 → 2, 서버: 2
✅ 대기 해제: Tag 2
⏸️ 라인 트레이싱 중단
▶️ 라인 트레이싱 재개
```

**로그 의미**:
- 📡 = 센서 태그 변경
- ⚡ = 점프 (서버 AGV를 센서 위치로 리셋)
- ⏳ = 대기 (서버 AGV가 센서보다 앞서감)
- ✅ = 대기 해제 (센서가 서버를 따라잡음)
- 🚩 = 서버 AGV가 다음 태그 도착
- ⏸️ = pause_line_tracing() 호출
- ▶️ = resume_line_tracing() 호출

````
```

---

## 🔍 로그 확인 방법

### 서버 로그 (터미널)
```
✅ AGV 하드웨어 연결 성공
🚀 AGV 제어 루프 시작
🎯 Tag X 임무 시작
⚠️ 장애물 감지! 거리: XXXmm
✅ 장애물 제거 확인 - 주행 재개
```

---

### 클라이언트 로그 (터미널)
```
🚀 Tag 1 이전 구간: 200mm/s 고정 속도
🏷️ Tag X 구간: 기본=150, 최대제한=200, 실제=150mm/s
🚨 장애물 감지! 거리: 120mm - 긴급정지
⏳ 장애물 제거 감지 (350mm) - 2초 대기 중...
```

---

### 웹 콘솔 로그 (F12)
```
✅ Tag 위치 정보 로드: 10개
📡 센서 태그 업데이트: 0 → 1, 서버 AGV: 0
⚡ 점프 완료: 서버 AGV를 Tag 1로 이동, 애니메이션 시작
⏳ 대기 시작: 서버(2) > 센서(1) - Tag 2에서 대기
✅ 대기 해제: 센서가 Tag 2에 도착 - 애니메이션 재개
```

---

## 📞 지원 및 문의

### 문서 위치
- **개발 로그**: `docs/DEVELOPMENT_LOG.md`
- **코드 점검**: `docs/CODE_REVIEW.md`
- **빠른 참조**: `docs/QUICK_REFERENCE.md` (이 문서)
- **README**: `README.md`

### 백업 파일
- `_backup/`: 백업 및 보안 패치 이력

---

**작성자**: AI Assistant  
**작성일**: 2025-11-13  
**버전**: 1.0.0
