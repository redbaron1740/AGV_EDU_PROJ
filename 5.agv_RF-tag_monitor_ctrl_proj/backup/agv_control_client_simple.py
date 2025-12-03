#!/usr/bin/env python3
"""
단순화된 AGV 제어 클라이언트
- 서버의 상태 관리에 종속
- 라인 트레이싱, 모터 제어, 센서 데이터 전송에 집중
- Mission Planning은 별도 모듈에서 처리
"""

import requests
import time
import threading
from datetime import datetime
from flask import Flask, jsonify
import curses
import sys

# Mission Planning 모듈 임포트
try:
    from mission_planning import execute_mission, validate_mission_parameters, log_mission_result, set_line_tracing_callbacks
    MISSION_MODULE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Mission Planning 모듈 로드 실패: {e}")
    MISSION_MODULE_AVAILABLE = False

# Donkibot 하드웨어 통신
try:
    from Donkibot_i import Comm
    HW_AVAILABLE = True
    print("✅ Donkibot_i 하드웨어 모듈 로드 완료")
except ImportError:
    HW_AVAILABLE = False
    print("⚠️ Donkibot_i 모듈 없음 - 시뮬레이션 모드")

# === 설정 ===
SERVER_URL = "http://127.0.0.1:5000/update"
CLIENT_HOST = "127.0.0.1"
CLIENT_PORT = 5001
AGV_PORT = '/dev/ttyUSB0'

# === 전역 변수 ===
agv_comm = None
comm_lock = threading.Lock()
shutdown_flag = False

# AGV 기본 데이터
agv_data = {
    "position": {"x": 1491, "y": 620},  # 실제 위치 (참고용)
    "rotation": 0,
    "speed": 0,
    "battery_soc": 100,
    "tag1": 0,
    "tag2": 200,
    "line_pos": 0,
    "lidar_distance": 5000,
    "emg_flag": 0,
    "estop_status": "",
    "timestamp": datetime.now().isoformat()  # 초기 타임스탬프
}

# 제어 상태
is_line_following = False
was_line_following_before_obstacle = False  # 장애물 발생 전 주행 상태 저장
current_mission_result = None
last_tag_processed = 0
mission_max_speed = 200  # Mission Planning에서 설정 가능한 최대 속도 (기본값 200)

# 장애물 감지 및 복구 상태
obstacle_detected = False
obstacle_clear_start_time = None
OBSTACLE_THRESHOLD = 150  # 긴급정지 임계값 (mm)
OBSTACLE_RECOVERY_THRESHOLD = 300  # 복구 임계값 (mm)
OBSTACLE_RECOVERY_TIME = 2.0  # 복구 대기 시간 (초)

# Curses 디버깅 디스플레이
stdscr = None
USE_CURSES = False  # curses 사용 여부 (False로 기본 설정 - 부하 방지)
last_display_update = 0  # 마지막 디스플레이 업데이트 시간

# Flask 앱 (서버에서 오는 명령 수신용)
app = Flask(__name__)

# === 라인 트레이싱 제어 함수 (Mission Planning용) ===
def pause_line_tracing_for_mission():
    """Mission Planning에서 호출: 라인 트레이싱 일시 중단"""
    global is_line_following
    is_line_following = False
    send_motor_command(0, 0)

def resume_line_tracing_for_mission():
    """Mission Planning에서 호출: 라인 트레이싱 재개"""
    global is_line_following
    is_line_following = True

def set_mission_max_speed(speed):
    """Mission Planning에서 호출: 최대 속도 설정"""
    global mission_max_speed
    mission_max_speed = max(50, min(speed, 200))  # 50~200 범위로 제한
    print(f"🚀 Mission 최대 속도 설정: {mission_max_speed}mm/s")

# === HTTP 엔드포인트 (서버에서 호출) ===
@app.route('/start', methods=['POST'])
@app.route('/start_line_follow', methods=['POST'])
def start_line_follow():
    """라인 트레이싱 시작"""
    global is_line_following
    is_line_following = True
    print("🚗 라인 트레이싱 시작")
    return jsonify({"status": "success"}), 200

@app.route('/stop', methods=['POST'])
@app.route('/stop_motors', methods=['POST'])
def stop_motors():
    """모터 정지"""
    global is_line_following
    is_line_following = False
    send_motor_command(0, 0)
    print("🛑 모터 정지")
    return jsonify({"status": "success"}), 200

@app.route('/pause', methods=['POST'])
@app.route('/pause_motors', methods=['POST'])
def pause_motors():
    """모터 일시정지"""
    global is_line_following
    is_line_following = False
    send_motor_command(0, 0)
    print("⏸️ 모터 일시정지")
    return jsonify({"status": "success"}), 200

@app.route('/estop', methods=['POST'])
@app.route('/emergency_stop', methods=['POST'])
def emergency_stop():
    """비상정지"""
    global is_line_following
    is_line_following = False
    send_motor_command(0, 0)
    print("🚨 비상정지")
    return jsonify({"status": "success"}), 200

@app.route('/reset_pose', methods=['POST'])
def reset_pose():
    """위치 리셋"""
    global agv_data
    agv_data["position"] = {"x": 1491, "y": 620}
    agv_data["rotation"] = 0
    print("📍 위치 리셋")
    return jsonify({"status": "success"}), 200

@app.route('/health_check', methods=['GET'])
def health_check():
    """AGV 상태 점검 (서버 초기화용)"""
    global agv_comm, agv_data
    
    health_status = {
        "hardware_connected": agv_comm is not None,
        "serial_port": AGV_PORT if agv_comm else None,
        "data_updating": agv_data.get("timestamp") is not None,
        "emergency_flag": agv_data.get("emg_flag", False),
        "battery_soc": agv_data.get("battery_soc", 0),
        "last_update": agv_data.get("timestamp"),
        "communication_ok": True,  # 이 응답 자체가 통신 성공을 의미
        "mission_module_available": MISSION_MODULE_AVAILABLE
    }
    
    # 모든 체크 통과 여부 (INITIAL 단계에서는 emergency_flag 무시)
    all_checks_pass = (
        health_status["hardware_connected"] and
        health_status["data_updating"] and
        # emergency_flag는 RUNNING 상태에서만 체크
        health_status["battery_soc"] > 10  # 배터리 10% 이상
    )
    
    health_status["ready"] = all_checks_pass
    
    return jsonify(health_status), 200

@app.route('/status', methods=['GET'])
def get_status():
    """간단한 상태 확인"""
    return jsonify({
        "status": "running",
        "hardware": agv_comm is not None,
        "timestamp": agv_data.get("timestamp")
    }), 200

def run_flask_server():
    """Flask 서버 실행"""
    app.run(host=CLIENT_HOST, port=CLIENT_PORT, debug=False)

# === Curses 디버그 디스플레이 ===
def debug_print(msg):
    """curses 사용 시 화면 업데이트, 아니면 일반 print"""
    if USE_CURSES and stdscr:
        # curses 모드에서는 update_debug_display()에서 처리
        pass
    else:
        print(msg)

def update_debug_display():
    """curses 화면 업데이트 (최적화: 0.5초마다만 업데이트)"""
    global stdscr, last_display_update
    if not USE_CURSES or not stdscr:
        return
    
    # 부하 방지: 0.5초마다만 업데이트
    now = time.time()
    if now - last_display_update < 0.5:
        return
    last_display_update = now
    
    try:
        h, w = stdscr.getmaxyx()
        
        # clear() 대신 개별 라인만 업데이트 (성능 개선)
        row = 0
        
        # 헤더
        stdscr.addstr(0, 0, "=" * min(70, w-1), curses.A_BOLD)
        stdscr.addstr(1, 0, " AGV 실시간 디버그 모니터" + " " * (min(70, w-1) - 25), curses.A_BOLD | curses.A_REVERSE)
        stdscr.addstr(2, 0, "=" * min(70, w-1), curses.A_BOLD)
        
        row = 4
        # 센서 데이터
        stdscr.addstr(row, 0, "[ 센서 데이터 ]" + " " * 50, curses.A_BOLD)
        row += 1
        line_info = " " * 40
        if abs(agv_data['line_pos']) > 12:
            line_info = "⚠️ 급회전!"
        elif abs(agv_data['line_pos']) > 5:
            line_info = "← 조정 중"
        stdscr.addstr(row, 0, f"  Line Position : {agv_data['line_pos']:>4}  {line_info}" + " " * 20)
        row += 1
        
        obs_info = ""
        if agv_data['lidar_distance'] < OBSTACLE_THRESHOLD:
            obs_info = "🚨 장애물!"
        stdscr.addstr(row, 0, f"  Lidar Distance: {agv_data['lidar_distance']:>4} mm  {obs_info}" + " " * 20)
        row += 1
        
        stdscr.addstr(row, 0, f"  Battery SOC   : {agv_data['battery_soc']:>3}%" + " " * 40)
        row += 1
        stdscr.addstr(row, 0, f"  Speed         : {agv_data['speed']:>3} mm/s" + " " * 40)
        row += 2
        
        # RF 태그 정보
        stdscr.addstr(row, 0, "[ RF-Tag 정보 ]" + " " * 50, curses.A_BOLD)
        row += 1
        stdscr.addstr(row, 0, f"  Current Tag   : {agv_data['tag1']:>2}" + " " * 40)
        row += 1
        stdscr.addstr(row, 0, f"  Speed Limit   : {agv_data['tag2']:>3} mm/s" + " " * 40)
        row += 2
        
        # 제어 상태
        stdscr.addstr(row, 0, "[ 제어 상태 ]" + " " * 50, curses.A_BOLD)
        row += 1
        line_following_str = "주행 중" if is_line_following else "정지   "
        stdscr.addstr(row, 0, f"  Line Following: {line_following_str}" + " " * 40)
        row += 1
        
        estop_str = agv_data.get('estop_status', '') or "정상   "
        stdscr.addstr(row, 0, f"  E-Stop Status : {estop_str}" + " " * 40)
        row += 1
        
        obstacle_str = "감지됨!" if obstacle_detected else "정상   "
        stdscr.addstr(row, 0, f"  Obstacle      : {obstacle_str}" + " " * 40)
        row += 2
        
        # 모터 출력 (최근 명령)
        stdscr.addstr(row, 0, "[ 모터 출력 ]" + " " * 50, curses.A_BOLD)
        row += 1
        vl, vr = line_following_control() if is_line_following else (0, 0)
        stdscr.addstr(row, 0, f"  Left Wheel    : {vl:>4} mm/s" + " " * 40)
        row += 1
        stdscr.addstr(row, 0, f"  Right Wheel   : {vr:>4} mm/s" + " " * 40)
        row += 2
        
        # 푸터
        stdscr.addstr(row, 0, "=" * min(70, w-1), curses.A_DIM)
        row += 1
        stdscr.addstr(row, 0, "Press Ctrl+C to exit" + " " * 40, curses.A_DIM)
        
        stdscr.refresh()
    except curses.error:
        pass  # 화면 크기 문제 등 무시

# === 하드웨어 제어 ===
def initialize_hardware():
    """AGV 하드웨어 초기화"""
    global agv_comm
    if not HW_AVAILABLE:
        return False
    
    try:
        agv_comm = Comm(port=AGV_PORT, baudrate=115200)
        print(f"✅ AGV 하드웨어 연결 성공: {AGV_PORT}")
        return True
    except Exception as e:
        print(f"❌ AGV 연결 실패: {e}")
        return False

def send_motor_command(vl, vr):
    """모터 제어 명령 전송"""
    with comm_lock:
        if agv_comm:
            try:
                agv_comm.CLR(vl, vr)
            except Exception as e:
                print(f"모터 제어 오류: {e}")

def get_sensor_data():
    """센서 데이터 획득"""
    global agv_data
    with comm_lock:
        if agv_comm:
            try:
                frame = agv_comm.get_latest_data()
                agv_data.update({
                    "line_pos": frame.LinePos,
                    "lidar_distance": frame.LidarDistance,
                    "emg_flag": frame.EmgFlag,
                    "speed": frame.Speed,
                    "tag1": frame.RF_tag1,
                    "tag2": frame.RF_tag2,
                    "battery_soc": frame.SOC,
                    "rotation": frame.TfsAngle % 360  # TfsAngle 그대로 사용 (0 = 위쪽)
                })
                
                # EStop 상태 감지 (Push-EStop만 여기서 처리, OBS-EStop은 check_obstacle()에서)
                if frame.EmgFlag == 1:
                    agv_data["estop_status"] = "Push-EStop"
                elif frame.EmgFlag == 0 and agv_data.get("estop_status") == "Push-EStop":
                    # 비상정지 버튼 해제됨
                    agv_data["estop_status"] = ""
                # OBS-EStop은 check_obstacle()에서 관리하므로 여기서 덮어쓰지 않음
                
                return True
            except Exception as e:
                print(f"센서 데이터 오류: {e}")
    return False

# === 라인 트레이싱 제어 ===
_last_speed_log_tag = -1  # 속도 로그 출력용 (변경 시에만 출력)

def line_following_control():
    """라인 트레이싱 제어"""
    global _last_speed_log_tag
    
    if not is_line_following:
        return 0, 0
    
    line_pos = agv_data["line_pos"]
    current_tag = agv_data["tag1"]
    tag2_speed = agv_data["tag2"]
    
    # Tag 1 감지 전: 무조건 200mm/s로 직진
    if current_tag == 0:
        base_speed = 200
        max_speed = 200
        effective_speed = 200
        if _last_speed_log_tag != 0:
            print(f"🚀 Tag 1 이전 구간: 200mm/s 고정 속도")
            _last_speed_log_tag = 0
    else:
        # Tag 1 이후: tag2는 최대 제한 속도, base_speed는 기본 주행 속도
        base_speed = 150  # 기본 주행 속도
        max_speed = min(tag2_speed, mission_max_speed)  # tag2와 mission_max_speed 중 작은 값
        effective_speed = min(base_speed, max_speed)  # 둘 중 작은 값
        if _last_speed_log_tag != current_tag:
            print(f"🏷️ Tag {current_tag} 구간: 기본={base_speed}, 최대제한={max_speed}, 실제={effective_speed}mm/s")
            _last_speed_log_tag = current_tag
    
    # 조향 제어
    if abs(line_pos) > 8:  # 급회전 (임계값 완화: 8→12)
        if line_pos < -8:
            vl, vr = -50, 50  # 좌회전 (spot turn)
        else:
            vl, vr = 50, -50  # 우회전 (spot turn)
    elif line_pos == 0:  # 직진
        vl = vr = effective_speed
    else:  # 미세 조정
        # correction을 속도에 비례하도록 조정 (최대 30% 감속)
        max_correction = int(effective_speed * 0.3)
        correction = min(int(abs(line_pos) * 8), max_correction)
        
        if line_pos < 0:  # 좌측 보정 (왼쪽으로 치우침 → 왼쪽 바퀴 느리게)
            vl, vr = effective_speed - correction, effective_speed
        else:  # 우측 보정 (오른쪽으로 치우침 → 오른쪽 바퀴 느리게)
            vl, vr = effective_speed, effective_speed - correction
    
    # 속도 제한
    vl = max(-200, min(200, vl))
    vr = max(-200, min(200, vr))
    
    return vl, vr

def check_obstacle():
    """장애물 감지 및 복구 처리"""
    global obstacle_detected, obstacle_clear_start_time, is_line_following, was_line_following_before_obstacle
    
    lidar_dist = agv_data["lidar_distance"]
    
    # 장애물 감지 (150mm 이하)
    if lidar_dist < OBSTACLE_THRESHOLD and not obstacle_detected:
        obstacle_detected = True
        was_line_following_before_obstacle = is_line_following  # 현재 주행 상태 저장
        is_line_following = False  # 라인 트레이싱 중지
        send_motor_command(0, 0)  # 긴급정지
        agv_data["estop_status"] = "OBS-EStop"
        print(f"🚨 장애물 감지! 거리: {lidar_dist}mm - 긴급정지 (주행 중: {was_line_following_before_obstacle})")
        return True
    
    # 장애물 복구 감지 (300mm 이상 2초 유지)
    if obstacle_detected:
        if lidar_dist > OBSTACLE_RECOVERY_THRESHOLD:
            if obstacle_clear_start_time is None:
                obstacle_clear_start_time = time.time()
                print(f"⏳ 장애물 제거 감지 ({lidar_dist}mm) - 2초 대기 중...")
            else:
                elapsed = time.time() - obstacle_clear_start_time
                if elapsed >= OBSTACLE_RECOVERY_TIME:
                    # 복구 완료
                    obstacle_detected = False
                    obstacle_clear_start_time = None
                    # 장애물 발생 전에 주행 중이었다면 재개
                    if was_line_following_before_obstacle:
                        is_line_following = True
                        print(f"✅ 장애물 제거 확인 - 주행 재개")
                    else:
                        print(f"✅ 장애물 제거 확인 - 대기 상태 유지")
                    agv_data["estop_status"] = ""
                    was_line_following_before_obstacle = False
                    return False
        else:
            # 거리가 다시 가까워짐 - 타이머 리셋
            if obstacle_clear_start_time is not None:
                print(f"⚠️ 장애물 여전히 가까움 ({lidar_dist}mm) - 대기 취소")
                obstacle_clear_start_time = None
    
    return obstacle_detected

def process_mission():
    """Mission Planning 모듈을 이용한 임무 처리"""
    global last_tag_processed, current_mission_result
    
    current_tag = agv_data["tag1"]
    
    # 새로운 태그 감지시에만 임무 실행
    if current_tag > 0 and current_tag != last_tag_processed:
        last_tag_processed = current_tag
        
        if MISSION_MODULE_AVAILABLE:
            # 임무 파라미터 검증
            valid, msg = validate_mission_parameters(current_tag, agv_data["tag2"])
            if valid:
                # 임무 실행
                result = execute_mission(current_tag, agv_comm, agv_data["tag2"])
                current_mission_result = result
                log_mission_result(current_tag, result)
                
                # 임무 결과에 따른 후처리
                if result.get("status") == "completed":
                    print("🏆 전체 임무 완료!")
                elif result.get("status") == "error":
                    print(f"❌ 임무 실행 오류: {result.get('error')}")
            else:
                print(f"❌ 임무 파라미터 오류: {msg}")
        else:
            print(f"📝 Tag {current_tag} 감지 (Mission Planning 모듈 없음)")

def send_data_to_server():
    """서버로 데이터 전송"""
    payload = {
        "timestamp": datetime.now().isoformat(),
        "position": agv_data["position"],
        "rotation": agv_data["rotation"],
        "speed": agv_data["speed"],
        "battery_soc": agv_data["battery_soc"],
        "status": agv_data.get("estop_status", ""),  # EStop 상태만 보고
        "is_line_following": is_line_following,  # 라인 트레이싱 상태 추가
        "rf_tag": {
            "tag_id": agv_data["tag1"] if agv_data["tag1"] > 0 else None,
            "speed_limit": agv_data["tag2"] if agv_data["tag2"] > 0 else None
        },
        "sensors": {
            "line_position": agv_data["line_pos"],
            "lidar_distance": agv_data["lidar_distance"],
            "emergency_flag": agv_data["emg_flag"],
            "tfs_angle": agv_data["rotation"],
            "tfs_distance": 0
        },
        "odometry": {
            "left": 0,
            "right": 0,
            "total_distance": 0
        }
    }
    
    try:
        response = requests.post(SERVER_URL, json=payload, timeout=3)
        if response.status_code != 200:
            print(f"서버 응답 오류: {response.status_code}")
    except requests.exceptions.RequestException as e:
        # 연결 오류는 조용히 처리 (너무 많은 로그 방지)
        pass

def check_user_input():
    """사용자 입력 체크 (종료 감지)"""
    global shutdown_flag
    import sys
    import select
    
    print("💡 종료하려면 'q' + Enter 키를 누르거나 Ctrl+C를 사용하세요")
    
    while not shutdown_flag:
        try:
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                user_input = sys.stdin.readline().strip().lower()
                if user_input == 'q':
                    print("🛑 사용자 종료 요청")
                    shutdown_flag = True
                    break
        except:
            pass
        time.sleep(0.1)

# === 메인 제어 루프 ===
def main_control_loop():
    """메인 제어 루프"""
    global shutdown_flag
    
    debug_print("🚀 AGV 제어 루프 시작")
    debug_print(f"📡 서버 통신: {SERVER_URL}")
    
    while not shutdown_flag:
        try:
            # 센서 데이터 획득
            get_sensor_data()
            
            # 장애물 감지 (최우선)
            check_obstacle()
            
            # Mission Planning 처리
            process_mission()
            
            # 라인 트레이싱 제어 (장애물 없을 때만)
            if not obstacle_detected:
                vl, vr = line_following_control()
                if is_line_following:
                    send_motor_command(vl, vr)
            
            # 서버로 데이터 전송
            send_data_to_server()
            
            # Curses 디스플레이 업데이트
            if USE_CURSES and stdscr:
                update_debug_display()
            
            # 제어 주기 (100ms)
            time.sleep(0.1)
            
        except Exception as e:
            debug_print(f"제어 루프 오류: {e}")
            time.sleep(1)

# === 메인 실행부 ===
def main_wrapper(screen=None):
    """Curses 래퍼 함수"""
    global stdscr, shutdown_flag
    
    if USE_CURSES and screen:
        stdscr = screen
        curses.curs_set(0)  # 커서 숨기기
        stdscr.nodelay(1)   # non-blocking 입력
        stdscr.clear()
    
    print("=" * 60)
    print("         단순화된 AGV 제어 클라이언트")
    print("=" * 60)
    print("🔧 서버 종속 모드: 상태 관리는 서버에서 담당")
    print("🎯 Mission Planning: mission_planning.py에서 처리")
    if USE_CURSES:
        print("📊 Curses 디버그 모드 활성화")
    print("=" * 60)
    
    # 하드웨어 초기화
    hardware_connected = initialize_hardware()
    
    if hardware_connected:
        print("🔧 실제 하드웨어 모드로 실행")
    else:
        print("💭 시뮬레이션 모드로 실행")

    # Flask 서버 시작 (서버 명령 수신용)
    server_thread = threading.Thread(target=run_flask_server, daemon=True)
    server_thread.start()
    
    # Mission Planning 콜백 설정
    if MISSION_MODULE_AVAILABLE:
        set_line_tracing_callbacks(
            pause_line_tracing_for_mission, 
            resume_line_tracing_for_mission,
            set_mission_max_speed
        )
        print("✅ Mission Planning 라인 트레이싱 제어 콜백 설정 완료")
    
    # 사용자 입력 체크 스레드 (curses 모드에서는 비활성화)
    if not USE_CURSES:
        input_thread = threading.Thread(target=check_user_input, daemon=True)
        input_thread.start()
    
    print("✅ 클라이언트 준비 완료")
    print(f"📡 명령 대기 중: http://{CLIENT_HOST}:{CLIENT_PORT}")
    
    if USE_CURSES:
        print("\n⏳ Curses 디스플레이 초기화 중...")
        time.sleep(2)  # 메시지 읽을 시간

    # 메인 제어 루프 시작
    try:
        main_control_loop()
    except KeyboardInterrupt:
        if not USE_CURSES:
            print("\n🛑 Ctrl+C 감지 - 프로그램 종료")
        shutdown_flag = True
    finally:
        if not USE_CURSES:
            print("🔧 시스템 종료 중...")
        send_motor_command(0, 0)
        
        with comm_lock:
            if agv_comm:
                try:
                    agv_comm.destroy()
                    if not USE_CURSES:
                        print("✅ 하드웨어 연결 해제 완료")
                except:
                    pass
        
        if not USE_CURSES:
            print("👋 프로그램 종료")

if __name__ == "__main__":
    if USE_CURSES:
        try:
            curses.wrapper(main_wrapper)
        except Exception as e:
            print(f"Curses 오류: {e}")
            print("일반 모드로 재시작합니다...")
            USE_CURSES = False
            main_wrapper()
    else:
        main_wrapper()
