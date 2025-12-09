# AGV RF-Tag Monitor Control Project

이 프로젝트는 RF-Tag 기반 AGV(무인운반차) 시스템의 시뮬레이션 및 실제 제어를 위한 Python 예제 코드와 서버/클라이언트 구조를 제공합니다. 아래는 실제 코드와 파일 구조를 바탕으로 분석한 전체 설명입니다.

---

## 📦 실제 파일 구조

```
agv_station_server.py          # Flask 기반 AGV 서버 (상태 머신, REST API, 웹 대시보드)
agv_control_client.py          # AGV 클라이언트 (센서 데이터, 상태 머신, 서버 통신, curses UI)
agv_simulator.py               # AGV 센서/상태 시뮬레이터 (시리얼 송수신, curses UI)
Donkibot_i.py                  # Donkibot 하드웨어 통신 라이브러리
tag_num.json                   # RF-Tag 위치 정보
README.md                      # 프로젝트 설명 문서
requirements.txt               # Python 패키지 목록
templates/index.html           # 웹 대시보드 UI
docs/state_machine.html        # 상태 머신 다이어그램
```

---

## ⚙️ 시스템 아키텍처

### 서버-클라이언트 구조
```
┌─────────────────────────────────┐
│   agv_station_server.py         │
│   (포트 5000)                   │
│   - AGV 상태 머신 관리          │
│   - REST API 제공               │
│   - 웹 대시보드/시뮬레이션      │
└───────────┬─────────────────────┘
        │ HTTP (POST/GET)
        │ 0.1초마다 데이터 교환
┌───────────▼─────────────────────┐
│   agv_control_client.py         │
│   - AGV 센서 데이터 수집        │
│   - 서버와 통신                 │
│   - 상태 머신/제어              │
│   - curses 기반 UI              │
└───────────┬─────────────────────┘
        │
┌───────────▼─────────────────────┐
│   agv_simulator.py              │
│   - 센서/상태 값 직접 입력      │
│   - 시리얼 송수신               │
│   - curses 기반 UI              │
└─────────────────────────────────┘
```

---

## 🧭 AGV 상태 머신 구조

AGV는 아래와 같은 주요 상태로 동작합니다. (서버/클라이언트 모두 동일한 상태 값 사용)

- **INITIAL**: 하드웨어 및 센서 초기화
- **READY**: 서버와 연결 및 준비 상태
- **RUNNING**: 주행 및 센서/명령 모니터링
- **OBSTACLE_ESTOP**: 장애물 감지 시 정지
- **PUSH_BUTTON_ESTOP**: 비상 버튼 눌림 시 정지
- **SERVER_BUTTON_ESTOP**: 서버에서 비상정지 명령 수신 시 정지
- **ABNORMAL**: 비정상 상태 처리

각 상태는 센서 데이터, 서버 명령, 하드웨어 이벤트에 따라 전이됩니다.

---

## 주요 파일별 상세 설명

### 1. agv_station_server.py
- Flask 기반 AGV 서버
- 클라이언트로부터 센서/상태 데이터 수신 및 저장
- REST API로 웹 프론트엔드와 데이터 송수신
- AGV 상태 머신 관리 및 경고 메시지 박스 제공
- 경로 및 웨이포인트 관리, 시뮬레이션 지원

### 2. agv_control_client.py
- AGV 하드웨어와 시리얼 통신 (센서 데이터 수신, 제어 명령 송신)
- 서버와 REST API로 데이터 송수신 (상태 보고, 명령 수신)
- AGV 상태 머신 관리 (초기화, 준비, 주행, 비상정지 등)
- 장애물 감지 및 라인 추종 제어 알고리즘 구현
- curses 기반 터미널 UI로 AGV 상태 실시간 표시

### 3. agv_simulator.py
- 사용자가 직접 AGV 센서/상태 값을 입력하여 시리얼 포트로 송신
- 실제 AGV 없이 소프트웨어적으로 상태 메시지 생성 및 테스트
- curses 기반 메뉴 UI로 각 센서/상태 값 입력
- 송신/수신 스레드로 시리얼 통신 구현

### 4. Donkibot_i.py
- AGV 하드웨어와의 시리얼 통신을 위한 라이브러리
- 센서 데이터 파싱, 모터 제어 등 하드웨어 연동 기능 제공

---

## 실습 방법

1. **서버 실행**: `agv_station_server.py`를 실행하여 AGV 상태 관리 및 웹 대시보드 제공
  - Flask 서버가 5000번 포트에서 동작하며, 웹 브라우저에서 상태 확인 가능
2. **클라이언트 실행**: `agv_control_client.py`를 실행하여 AGV 센서 데이터 송수신 및 제어
  - 실제 AGV 하드웨어와 연결하거나, 시뮬레이터와 연동 가능
  - curses UI로 실시간 상태 모니터링
3. **시뮬레이터 실행**: `agv_simulator.py`로 센서 값을 직접 입력하여 테스트
  - 시리얼 포트로 메시지 송신, 실제 AGV 없이 소프트웨어적으로 동작 확인

---

## 주요 기능 요약

### 서버 (`agv_station_server.py`)
- AGV 상태 머신 관리 및 명령 전송
- 클라이언트와 REST API로 데이터 송수신
- 웹 대시보드 및 AGV 시뮬레이션 제공
- 장애물/비상정지 등 경고 메시지 박스 API

### 클라이언트 (`agv_control_client.py`)
- 센서 데이터 수집 및 서버 전송
- 서버 명령 수신 및 상태 머신 전이
- 라인 추종 제어, 장애물 감지, 비상정지 처리
- curses UI로 실시간 상태 표시

### 시뮬레이터 (`agv_simulator.py`)
- 센서/상태 값 직접 입력 및 시리얼 송신
- 실제 AGV 없이 소프트웨어 테스트 가능
- curses UI로 값 입력 및 상태 확인

---

## FAQ & 트러블슈팅

### 1. 서버와 클라이언트를 반드시 순서대로 실행해야 하나요?
**네, 반드시 서버를 먼저 실행해야 합니다.** 클라이언트가 시작 시 서버에 연결을 시도하므로 서버가 먼저 실행되어 있어야 합니다.

### 2. 웹 대시보드에서 AGV가 움직이지 않아요
다음을 확인하세요:
1. 클라이언트가 실행 중인지 확인 (`agv_control_client.py`)
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

### 5. AGV 속도를 전체적으로 변경하려면?
- 클라이언트 코드의 속도 관련 변수(`SPEED_LIMIT`, `CURRENT_SPEED`)를 수정하세요.
- 시뮬레이터에서 직접 속도 값을 입력하여 테스트할 수 있습니다.

### 6. 서버/클라이언트 실행 오류
- "Address already in use": 5000번 포트를 사용 중인 프로세스 종료
  ```bash
  sudo lsof -t -i:5000 | xargs kill -9
  ```
- "Connection refused": 서버가 먼저 실행되어 있는지 확인, 서버 주소(`SERVER_URL`)가 올바른지 확인

### 7. 하드웨어 연결 오류
```bash
# 시리얼 포트 권한 확인
ls -l /dev/ttyUSB* 
sudo chmod 666 /dev/ttyUSB0
```

---

## 📚 참고 문서
- **State Machine 다이어그램**: `docs/state_machine.html` (브라우저로 열기)
- **Waypoints 가이드**: `WAYPOINTS_GUIDE.md`
- **보안 수정 사항**: `SECURITY_FIXES.md`

---

## 🎓 학습 포인트

이 프로젝트를 통해 배울 수 있는 내용:
1. **State Machine 패턴**: 복잡한 시스템을 명확한 상태로 분리
2. **서버-클라이언트 아키텍처**: HTTP 통신을 통한 분산 시스템
3. **실시간 제어**: 센서 데이터 수집 및 모터 제어
4. **웹 시각화**: Flask + HTML/JavaScript를 활용한 실시간 모니터링
5. **멀티스레딩/병렬 처리**: 실시간성 확보
6. **curses 기반 터미널 UI**: 텍스트 기반 실시간 모니터링 및 입력

---

## 📝 버전 정보
- **v2.0**: 서버-클라이언트 구조로 전면 개편
- **v2.1**: 웹 AGV 시뮬레이션 추가
- **v2.2**: 시뮬레이터 및 UI 개선
- **v2.3**: README 전체 분석 기반으로 재작성

---

## 🛑 종료 방법 안내
프로그램 종료 시에는 Ctrl+C 또는 curses UI에서 'q' 입력 후 Enter로 안전하게 종료하세요.
# AGV RF-Tag Monitor Control Project

이 프로젝트는 AGV(무인 운반차) 시스템의 시뮬레이션 및 실제 제어를 위한 Python 기반 예제 코드와 서버/클라이언트 구조를 제공합니다. 아래는 각 주요 파일의 역할과 구조, 그리고 실습 및 학습 포인트에 대한 자세한 설명입니다.

---

## 1. agv_control_client.py

AGV의 센서 데이터를 수집하고, 서버와 통신하며, 상태를 관리하는 클라이언트 프로그램입니다.

- **주요 역할**:
  - AGV 하드웨어와 시리얼 통신(센서 데이터 수신, 제어 명령 송신)
  - 서버와 REST API로 데이터 송수신 (상태 보고, 명령 수신)
  - AGV의 상태(State Machine: 초기화, 준비, 주행, 비상정지 등) 관리
  - 장애물 감지 및 라인 추종 제어 알고리즘 구현
  - curses 기반 터미널 UI로 AGV 상태 실시간 표시

- **핵심 클래스/함수**:
  - `AGV_MACHINE_OPERATE`: AGV의 상태, 센서 데이터, 서버 통신, 제어 루프 관리. 내부적으로 하드웨어 초기화, 센서 데이터 수집, 서버와의 송수신 스레드, 메인 제어 루프, 장애물 감지, 라인 추종 제어 등 다양한 기능을 담당합니다.
  - `menu()`: curses UI를 통해 AGV의 현재 상태, 센서 값, 서버 명령, 에러 메시지 등을 실시간으로 표시합니다.

- **상태 머신 구조**:
  - INITIAL: 하드웨어 및 센서 초기화
  - READY: 서버와 연결 및 준비 상태
  - RUNNING: 주행 및 센서/명령 모니터링
  - OBSTACLE_ESTOP: 장애물 감지 시 정지
  - PUSH_BUTTON_ESTOP: 비상 버튼 눌림 시 정지
  - SERVER_BUTTON_ESTOP: 서버에서 비상정지 명령 수신 시 정지
  - ABNORMAL: 비정상 상태 처리

---

## 2. agv_station_server.py

AGV의 상태를 관리하고, 클라이언트와 웹 프론트엔드에 정보를 제공하는 Flask 기반 서버입니다.

- **주요 역할**:
  - AGV 클라이언트로부터 상태 데이터 수신 및 저장
  - 웹 프론트엔드에 AGV 상태, 경로, 경고 메시지 등 제공 (REST API)
  - AGV 제어 명령(GO, ESTOP, PAUSE, RESUME 등) 처리
  - AGV의 경로 및 웨이포인트 관리, 시뮬레이션 지원
  - 장애물/비상정지 등 경고 메시지 박스 API 제공

- **핵심 함수/구조**:
  - `on_operating_state()`: 서버의 AGV 상태 머신(상태 전이, 경고 처리 등)을 스레드로 실행하며, 클라이언트와의 상태 동기화 및 경고 메시지 관리

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
Donkibot_i.py                  # Donkibot 하드웨어 통신 라이브러리
tag_num.json                   # RF-Tag 위치 정보
README.md                      # 이 문서
templates/index.html           # 웹 대시보드 UI
docs/state_machine.html        # 상태 머신 다이어그램
```



## ⚙️ 시스템 아키텍처

### 서버-클라이언트 구조
```
┌─────────────────────────────────┐
│   agv_station_server.py         │
│   (포트 5000)                   │
│   - State Machine 관리          │
│   - 웹 대시보드                 │
│   - 웹 AGV 시뮬레이션           │
└───────────┬─────────────────────┘
            │ HTTP (POST/GET)
            │ 0.1초마다 데이터 교환
┌───────────▼─────────────────────┐
│   agv_control_client_simple.py  │
│   (포트 5001)                   │
│   - 라인 트레이싱               │
│   - RF-Tag 감지                │
│   - 모터 제어                   │
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