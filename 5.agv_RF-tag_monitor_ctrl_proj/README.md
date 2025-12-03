
# AGV RF-Tag 기반 State Machine 제어 프로젝트

## 프로젝트 개요
RF-Tag 기반 AGV(무인운반차) 제어 시스템입니다. 서버-클라이언트 구조와 상태 머신 패턴을 활용하여 실시간 제어, 임무 수행, 안전 시스템, 웹 시각화 기능을 제공합니다.

---

## 🧭 상태 머신 (6개 주요 상태)

### 1. INITIAL (초기화)
- **목적**: 시스템 초기화 및 연결 테스트
- **동작**:
  1. 서버 연결 테스트
  2. 시리얼 통신 연결 테스트
  3. 성공 시 → READY 상태
  4. 실패 시 → ABNORMAL 상태

### 2. READY (준비)
- **목적**: 시작 명령 대기
- **상태**:
  - tag1 = 0 (시작 전)
  - tag2 = 100mm/s (기본 속도)
- **전이**: 서버 GO 명령 시 → RUNNING 상태

### 3. RUNNING (주행)
- **목적**: 라인 트레이싱 및 임무 수행
- **동작**:
  - 라인 트레이싱 지속 수행
  - tag1 = 0: 기본 속도(100mm/s)로 주행
  - tag1 ≥ 2: 사용자 속도(tag2 값)로 주행
  - 사용자 임무 로직 수행
- **전이**:
  - PAUSE 명령 → PAUSED (3-1)
  - ESTOP 명령 → ESTOP (3-3)
  - 하드웨어 ESTOP → PUSH_ESTOP (4-1)
  - 장애물 감지 → OBS_ESTOP (4-2)
  - tag1 = 10 → COMPLETED (5)

#### 3-1. PAUSED (일시정지)
- **동작**: 속도 0, 현재 위치 유지
- **전이**: RESUME 명령 → RUNNING

#### 3-2. RESUME (재개)
- **동작**: 이전 속도 복원
- **전이**: 즉시 → RUNNING

### 4. ESTOP 상태들

#### 4-1. PUSH_ESTOP (물리적 비상정지)
- **원인**: AGV의 비상정지 스위치 활성화
- **동작**: 완전 정지
- **전이**: 해제 시 → RESUME

#### 4-2. OBS_ESTOP (장애물 비상정지)
- **원인**: 라이다 거리 < 200mm
- **동작**: 완전 정지
- **전이**: 장애물 제거 시 → RESUME

#### 4-3. SRV_ESTOP (서버 비상정지)
- **원인**: 서버에서 ESTOP 명령
- **동작**: 완전 정지 및 프로그램 종료

### 5. COMPLETED (완료)
- **목적**: 임무 완료 상태
- **동작**: 정지 및 대기
- **전이**: 서버 GO 명령 시 → READY

### 6. ABNORMAL (비정상)
- **목적**: 오류 상태 처리
- **동작**: 완전 정지 및 프로그램 종료

## 📦 파일 구조

```
agv_station_server.py          # 서버 (State Machine + 웹 대시보드)
agv_control_client_simple.py   # AGV 클라이언트 (라인 트레이싱 + RF-Tag)
mission_planning.py            # 🎓 학생 편집용 임무 로직
Donkibot_i.py                  # Donkibot 하드웨어 통신 라이브러리
tag_num.json                   # RF-Tag 위치 정보
README.md                      # 이 문서
templates/index.html           # 웹 대시보드 UI
docs/state_machine.html        # 상태 머신 다이어그램
```

### 🎓 학생이 편집해야 할 파일
**`mission_planning.py`** - 각 RF-Tag에서 수행할 임무를 정의합니다.
- Tag 1: 시작점 (수정 금지)
- Tag 2~9: 자유롭게 임무 정의 가능
- Tag 10: 목적지 (수정 금지)

예시:
```python
def execute_mission(tag_id, agv_comm, tag2_speed):
    if tag_id == 3:
        print("🎯 Tag 3: 좌회전 실행")
        agv_comm.CLR(-50, 50)  # 좌회전
        time.sleep(1.0)
        return "left_turn", 100
```

## ⚙️ 시스템 아키텍처

### 서버-클라이언트 구조
```
┌─────────────────────────────────┐
│   agv_station_server.py         │
│   (포트 5000)                   │
│   - State Machine 관리          │
│   - 웹 대시보드                 │
│   - 웹 AGV 시뮬레이션          │
└───────────┬─────────────────────┘
            │ HTTP (POST/GET)
            │ 0.1초마다 데이터 교환
┌───────────▼─────────────────────┐
│   agv_control_client_simple.py  │
│   (포트 5001)                   │
│   - 라인 트레이싱               │
│   - RF-Tag 감지                │
│   - mission_planning 호출       │
│   - 모터 제어                   │
└───────────┬─────────────────────┘
            │
┌───────────▼─────────────────────┐
│   mission_planning.py           │
│   - Tag 1~10 임무 정의         │
│   - 학생 편집용                 │
└─────────────────────────────────┘
```

### 웹 AGV 시뮬레이션
1. **경로 따라 이동**: `driving_path`를 따라 2픽셀/프레임 속도로 부드럽게 이동
2. **태그 동기화**: 실제 AGV가 RF-Tag 감지 시 웹 AGV를 해당 태그 위치로 리셋
3. **대기 기능**: 웹 AGV가 다음 태그 근처(50px) 도달 시 실제 감지 대기

## 🛠️ 주요 기능

### 서버 (`agv_station_server.py`)
1. **`change_agv_state(new_state, reason)`**: AGV 상태 변경 및 명령 전송
2. **`process_server_state_machine()`**: 서버 측 상태 머신 처리
3. **`reset_agv_position_to_tag(tag_id)`**: 웹 AGV를 태그 위치로 리셋
4. **`update_web_agv_position()`**: 웹 AGV 시뮬레이션 업데이트
5. **`move_web_agv_smoothly()`**: 경로를 따라 부드럽게 이동
6. **`check_web_agv_near_tag()`**: 다음 태그 근처 대기 처리

### 클라이언트 (`agv_control_client_simple.py`)
1. **`line_following_control()`**: 라인 트레이싱 로직 (PID 제어)
2. **`process_mission()`**: RF-Tag 감지 시 임무 처리
3. **`send_data_to_server()`**: 센서 데이터를 서버로 전송
4. **Flask 엔드포인트**: `/start_line_follow`, `/stop_motors`, `/pause_motors`, `/emergency_stop`

### 임무 계획 (`mission_planning.py`)
1. **`execute_mission(tag_id, agv_comm, tag2_speed)`**: 각 태그별 임무 실행
   - Tag 1: 시작 - 직진 시작
   - Tag 2~9: 사용자 정의 임무
   - Tag 10: 완료 - 정지

## ⚠️ 주의사항
- AGV의 비상정지 스위치 및 소프트웨어 ESTOP 기능은 항상 작동 상태여야 합니다.
- 시스템 점검 및 유지보수 시, 반드시 전원을 차단하고 안전 절차를 준수해야 합니다.

## 📜 변경 이력
- **v1.0**: 초기 릴리스
- **v1.1**: 상태 머신 로직 개선 및 문서화
- **v1.2**: 사용자 인터페이스 개선 및 오류 처리 강화

## ❓ FAQ

### 1. 서버와 클라이언트를 반드시 순서대로 실행해야 하나요?
**네, 반드시 서버를 먼저 실행해야 합니다.** 클라이언트가 시작 시 서버에 연결을 시도하므로 서버가 먼저 실행되어 있어야 합니다.

### 2. 웹 대시보드에서 AGV가 움직이지 않아요
다음을 확인하세요:
1. 클라이언트가 실행 중인지 확인 (`agv_control_client_simple.py`)
2. 웹에서 **GO** 버튼을 클릭했는지 확인
3. 터미널에서 "AGV Data Received" 메시지가 나타나는지 확인
4. AGV 상태가 "Running"인지 확인

### 3. RF-Tag가 감지되지 않아요
- `tag_num.json` 파일에 태그 위치가 올바르게 설정되어 있는지 확인
- 클라이언트 터미널에서 "🏷️ RF-Tag X 감지" 메시지 확인
- 실제 하드웨어의 RF-Tag 센서 연결 상태 확인

### 4. 웹 AGV와 실제 AGV 위치가 다릅니다
- 이것은 정상입니다! 웹 AGV는 시뮬레이션이며, RF-Tag 감지 시 실제 위치로 동기화됩니다.
- RF-Tag를 통과할 때마다 웹 AGV가 해당 태그 위치로 리셋되어 동기화됩니다.

### 5. 임무 로직을 어떻게 수정하나요?
**`mission_planning.py`** 파일을 편집하세요:
```python
def execute_mission(tag_id, agv_comm, tag2_speed):
    if tag_id == 3:  # Tag 3에서 수행할 임무
        print("🎯 Tag 3: 나만의 임무!")
        agv_comm.CLR(100, 100)  # 직진
        time.sleep(2.0)
        return "my_mission", 150  # 동작명, 속도
```

### 6. AGV 속도를 전체적으로 변경하려면?
- `mission_planning.py`에서 각 태그의 반환값 두 번째 인자(속도)를 수정
- 또는 `agv_control_client_simple.py`의 `DEFAULT_SPEED` 변수 수정

## � 트러블슈팅

### 서버 실행 시 "Address already in use" 오류
```bash
# 5000번 포트를 사용 중인 프로세스 종료
sudo lsof -t -i:5000 | xargs kill -9
```

### 클라이언트 실행 시 "Connection refused" 오류
- 서버가 먼저 실행되어 있는지 확인
- 서버 주소가 올바른지 확인 (`SERVER_URL = "http://127.0.0.1:5000"`)

### 하드웨어 연결 오류
```bash
# 시리얼 포트 권한 확인
ls -l /dev/ttyUSB* 
sudo chmod 666 /dev/ttyUSB0
```

## 📚 참고 문서
- **State Machine 다이어그램**: `docs/state_machine.html` (브라우저로 열기)
- **Waypoints 가이드**: `WAYPOINTS_GUIDE.md`
- **보안 수정 사항**: `SECURITY_FIXES.md`

## 🎓 학습 포인트

이 프로젝트를 통해 배울 수 있는 내용:
1. **State Machine 패턴**: 복잡한 시스템을 명확한 상태로 분리
2. **서버-클라이언트 아키텍처**: HTTP 통신을 통한 분산 시스템
3. **실시간 제어**: 센서 데이터 수집 및 모터 제어
4. **웹 시각화**: Flask + HTML/JavaScript를 활용한 실시간 모니터링
5. **모듈화**: 임무 로직을 별도 파일로 분리하여 유지보수성 향상

---

## 📝 버전 정보
- **v2.0**: 서버-클라이언트 구조로 전면 개편
- **v2.1**: 웹 AGV 시뮬레이션 추가
- **v2.2**: mission_planning 모듈 분리 (학생 편집 용이)
5. **종료 방법 안내**: README에 상세한 종료 방법 추가

이제 4-3과 6 상태에서 프로그램이 자동 종료되지 않고, 사용자가 직접 'q' + Enter 또는 Ctrl+C로 안전하게 종료할 수 있습니다! 🛑✨

## 🧭 상태 머신 (6개 주요 상태)

### 1. INITIAL (초기화)
- **목적**: 시스템 초기화 및 연결 테스트
- **동작**:
  1. 서버 연결 테스트
  2. 시리얼 통신 연결 테스트
  3. 성공 시 → READY 상태
  4. 실패 시 → ABNORMAL 상태

### 2. READY (준비)
- **목적**: 시작 명령 대기
- **상태**:
  - tag1 = 0 (시작 전)
  - tag2 = 100mm/s (기본 속도)
- **전이**: 서버 GO 명령 시 → RUNNING 상태

### 3. RUNNING (주행)
- **목적**: 라인 트레이싱 및 임무 수행
- **동작**:
  - 라인 트레이싱 지속 수행
  - tag1 = 0: 기본 속도(100mm/s)로 주행
  - tag1 ≥ 2: 사용자 속도(tag2 값)로 주행
  - 사용자 임무 로직 수행
- **전이**:
  - PAUSE 명령 → PAUSED (3-1)
  - ESTOP 명령 → ESTOP (3-3)
  - 하드웨어 ESTOP → PUSH_ESTOP (4-1)
  - 장애물 감지 → OBS_ESTOP (4-2)
  - tag1 = 10 → COMPLETED (5)

#### 3-1. PAUSED (일시정지)
- **동작**: 속도 0, 현재 위치 유지
- **전이**: RESUME 명령 → RUNNING

#### 3-2. RESUME (재개)
- **동작**: 이전 속도 복원
- **전이**: 즉시 → RUNNING

### 4. ESTOP 상태들

#### 4-1. PUSH_ESTOP (물리적 비상정지)
- **원인**: AGV의 비상정지 스위치 활성화
- **동작**: 완전 정지
- **전이**: 해제 시 → RESUME

#### 4-2. OBS_ESTOP (장애물 비상정지)
- **원인**: 라이다 거리 < 200mm
- **동작**: 완전 정지
- **전이**: 장애물 제거 시 → RESUME

#### 4-3. SRV_ESTOP (서버 비상정지)
- **원인**: 서버에서 ESTOP 명령
- **동작**: 완전 정지 및 프로그램 종료

### 5. COMPLETED (완료)
- **목적**: 임무 완료 상태
- **동작**: 정지 및 대기
- **전이**: 서버 GO 명령 시 → READY

### 6. ABNORMAL (비정상)
- **목적**: 오류 상태 처리
- **동작**: 완전 정지 및 프로그램 종료

## 📦 파일 구조

```
agv_station_server.py          # 서버 (State Machine + 웹 대시보드)
agv_control_client_simple.py   # AGV 클라이언트 (라인 트레이싱 + RF-Tag)
mission_planning.py            # 🎓 학생 편집용 임무 로직
Donkibot_i.py                  # Donkibot 하드웨어 통신 라이브러리
tag_num.json                   # RF-Tag 위치 정보
README.md                      # 이 문서
templates/index.html           # 웹 대시보드 UI
docs/state_machine.html        # 상태 머신 다이어그램
```

### 🎓 학생이 편집해야 할 파일
**`mission_planning.py`** - 각 RF-Tag에서 수행할 임무를 정의합니다.
- Tag 1: 시작점 (수정 금지)
- Tag 2~9: 자유롭게 임무 정의 가능
- Tag 10: 목적지 (수정 금지)

예시:
```python
def execute_mission(tag_id, agv_comm, tag2_speed):
    if tag_id == 3:
        print("🎯 Tag 3: 좌회전 실행")
        agv_comm.CLR(-50, 50)  # 좌회전
        time.sleep(1.0)
        return "left_turn", 100
```

## ⚙️ 시스템 아키텍처

### 서버-클라이언트 구조
```
┌─────────────────────────────────┐
│   agv_station_server.py         │
│   (포트 5000)                   │
│   - State Machine 관리          │
│   - 웹 대시보드                 │
│   - 웹 AGV 시뮬레이션          │
└───────────┬─────────────────────┘
            │ HTTP (POST/GET)
            │ 0.1초마다 데이터 교환
┌───────────▼─────────────────────┐
│   agv_control_client_simple.py  │
│   (포트 5001)                   │
│   - 라인 트레이싱               │
│   - RF-Tag 감지                │
│   - mission_planning 호출       │
│   - 모터 제어                   │
└───────────┬─────────────────────┘
            │
┌───────────▼─────────────────────┐
│   mission_planning.py           │
│   - Tag 1~10 임무 정의         │
│   - 학생 편집용                 │
└─────────────────────────────────┘
```

### 웹 AGV 시뮬레이션
1. **경로 따라 이동**: `driving_path`를 따라 2픽셀/프레임 속도로 부드럽게 이동
2. **태그 동기화**: 실제 AGV가 RF-Tag 감지 시 웹 AGV를 해당 태그 위치로 리셋
3. **대기 기능**: 웹 AGV가 다음 태그 근처(50px) 도달 시 실제 감지 대기

## 🛠️ 주요 기능

### 서버 (`agv_station_server.py`)
1. **`change_agv_state(new_state, reason)`**: AGV 상태 변경 및 명령 전송
2. **`process_server_state_machine()`**: 서버 측 상태 머신 처리
3. **`reset_agv_position_to_tag(tag_id)`**: 웹 AGV를 태그 위치로 리셋
4. **`update_web_agv_position()`**: 웹 AGV 시뮬레이션 업데이트
5. **`move_web_agv_smoothly()`**: 경로를 따라 부드럽게 이동
6. **`check_web_agv_near_tag()`**: 다음 태그 근처 대기 처리

### 클라이언트 (`agv_control_client_simple.py`)
1. **`line_following_control()`**: 라인 트레이싱 로직 (PID 제어)
2. **`process_mission()`**: RF-Tag 감지 시 임무 처리
3. **`send_data_to_server()`**: 센서 데이터를 서버로 전송
4. **Flask 엔드포인트**: `/start_line_follow`, `/stop_motors`, `/pause_motors`, `/emergency_stop`

### 임무 계획 (`mission_planning.py`)
1. **`execute_mission(tag_id, agv_comm, tag2_speed)`**: 각 태그별 임무 실행
   - Tag 1: 시작 - 직진 시작
   - Tag 2~9: 사용자 정의 임무
   - Tag 10: 완료 - 정지

## ⚠️ 주의사항
- AGV의 비상정지 스위치 및 소프트웨어 ESTOP 기능은 항상 작동 상태여야 합니다.
- 시스템 점검 및 유지보수 시, 반드시 전원을 차단하고 안전 절차를 준수해야 합니다.

## 📜 변경 이력
- **v1.0**: 초기 릴리스
- **v1.1**: 상태 머신 로직 개선 및 문서화
- **v1.2**: 사용자 인터페이스 개선 및 오류 처리 강화

## ❓ FAQ

### 1. 서버와 클라이언트를 반드시 순서대로 실행해야 하나요?
**네, 반드시 서버를 먼저 실행해야 합니다.** 클라이언트가 시작 시 서버에 연결을 시도하므로 서버가 먼저 실행되어 있어야 합니다.

### 2. 웹 대시보드에서 AGV가 움직이지 않아요
다음을 확인하세요:
1. 클라이언트가 실행 중인지 확인 (`agv_control_client_simple.py`)
2. 웹에서 **GO** 버튼을 클릭했는지 확인
3. 터미널에서 "AGV Data Received" 메시지가 나타나는지 확인
4. AGV 상태가 "Running"인지 확인

### 3. RF-Tag가 감지되지 않아요
- `tag_num.json` 파일에 태그 위치가 올바르게 설정되어 있는지 확인
- 클라이언트 터미널에서 "🏷️ RF-Tag X 감지" 메시지 확인
- 실제 하드웨어의 RF-Tag 센서 연결 상태 확인

### 4. 웹 AGV와 실제 AGV 위치가 다릅니다
- 이것은 정상입니다! 웹 AGV는 시뮬레이션이며, RF-Tag 감지 시 실제 위치로 동기화됩니다.
- RF-Tag를 통과할 때마다 웹 AGV가 해당 태그 위치로 리셋되어 동기화됩니다.

### 5. 임무 로직을 어떻게 수정하나요?
**`mission_planning.py`** 파일을 편집하세요:
```python
def execute_mission(tag_id, agv_comm, tag2_speed):
    if tag_id == 3:  # Tag 3에서 수행할 임무
        print("🎯 Tag 3: 나만의 임무!")
        agv_comm.CLR(100, 100)  # 직진
        time.sleep(2.0)
        return "my_mission", 150  # 동작명, 속도
```

### 6. AGV 속도를 전체적으로 변경하려면?
- `mission_planning.py`에서 각 태그의 반환값 두 번째 인자(속도)를 수정
- 또는 `agv_control_client_simple.py`의 `DEFAULT_SPEED` 변수 수정

## � 트러블슈팅

### 서버 실행 시 "Address already in use" 오류
```bash
# 5000번 포트를 사용 중인 프로세스 종료
sudo lsof -t -i:5000 | xargs kill -9
```

### 클라이언트 실행 시 "Connection refused" 오류
- 서버가 먼저 실행되어 있는지 확인
- 서버 주소가 올바른지 확인 (`SERVER_URL = "http://127.0.0.1:5000"`)

### 하드웨어 연결 오류
```bash
# 시리얼 포트 권한 확인
ls -l /dev/ttyUSB* 
sudo chmod 666 /dev/ttyUSB0
```

## 📚 참고 문서
- **State Machine 다이어그램**: `docs/state_machine.html` (브라우저로 열기)
- **Waypoints 가이드**: `WAYPOINTS_GUIDE.md`
- **보안 수정 사항**: `SECURITY_FIXES.md`

## 🎓 학습 포인트

이 프로젝트를 통해 배울 수 있는 내용:
1. **State Machine 패턴**: 복잡한 시스템을 명확한 상태로 분리
2. **서버-클라이언트 아키텍처**: HTTP 통신을 통한 분산 시스템
3. **실시간 제어**: 센서 데이터 수집 및 모터 제어
4. **웹 시각화**: Flask + HTML/JavaScript를 활용한 실시간 모니터링
5. **모듈화**: 임무 로직을 별도 파일로 분리하여 유지보수성 향상

---

## 📝 버전 정보
- **v2.0**: 서버-클라이언트 구조로 전면 개편
- **v2.1**: 웹 AGV 시뮬레이션 추가
- **v2.2**: mission_planning 모듈 분리 (학생 편집 용이)
5. **종료 방법 안내**: README에 상세한 종료 방법 추가

이제 4-3과 6 상태에서 프로그램이 자동 종료되지 않고, 사용자가 직접 'q' + Enter 또는 Ctrl+C로 안전하게 종료할 수 있습니다! 🛑✨